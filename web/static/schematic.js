// SVG schematic editor on the 20 px grid of the desktop circuit board: place, drag, rotate, delete, wire terminals,
// toggle switches, and show live voltages (wire colour) and per-component readouts. Edits go to a CircuitDoc.
import { esc } from './core.js';
import { symbol, hitBox } from './symbols.js';
import { formatValue } from './units.js';

export const G = 20, COLS = 44, ROWS = 24;
const NS = 'http://www.w3.org/2000/svg';
const VALUE_KEY = { Resistor: ['resistance', 'Ω'], Capacitor: ['capacitance', 'F'], Inductor: ['inductance', 'H'],
  DCVoltageSource: ['voltage', 'V'], ACVoltageSource: ['amplitude', 'V'], DCCurrentSource: ['current', 'A'],
  Diode: ['forward_voltage', 'V'], LED: ['forward_voltage', 'V'], BJT: ['gain', ''] };

export function valueLabel(c) {
  const p = c.properties;
  if (c.type === 'ACVoltageSource') return `${formatValue(+p.amplitude, 'V')} ${formatValue(+p.frequency, 'Hz')}`;
  if (c.type === 'BJT') return `${String(p.type || 'npn').toUpperCase()} β${p.gain}`;
  if (c.type === 'Switch') return p.state ? 'closed' : 'open';
  const k = VALUE_KEY[c.type];
  return k ? formatValue(Number(p[k[0]]), k[1]) : '';
}

// Colour for a node voltage relative to the largest magnitude on the board (blue negative, grey 0, red/amber positive).
function voltColor(v, vmax) {
  if (!Number.isFinite(v) || vmax <= 0) return 'var(--wire)';
  const f = Math.max(-1, Math.min(1, v / vmax));
  if (Math.abs(f) < 0.02) return 'var(--wire)';
  return f > 0 ? `hsl(${50 - 50 * f}, 100%, ${62 - 8 * f}%)` : `hsl(205, 100%, ${62 + 8 * f}%)`;
}

export class Schematic {
  constructor(host, doc, { onSelect = () => {}, onChange = () => {}, onStatus = () => {} } = {}) {
    Object.assign(this, { host, doc, onSelect, onChange, onStatus });
    this.mode = 'select';        // 'select' | 'place'
    this.placeType = null;
    this.selected = null;        // { kind: 'comp', id } | { kind: 'wire', w: [a, ta, b, tb] }
    this.pending = null;         // first terminal of a wire being drawn: [id, term]
    this.live = null;
    this.svg = document.createElementNS(NS, 'svg');
    this.svg.setAttribute('viewBox', `0 0 ${COLS * G} ${ROWS * G}`);
    this.svg.setAttribute('class', 'board');
    this.svg.setAttribute('tabindex', '0');
    this.svg.setAttribute('role', 'application');
    this.svg.setAttribute('aria-label', 'Circuit board: click a terminal then another to wire, R rotates, Delete removes');
    host.appendChild(this.svg);
    this.bind();
    this.render();
  }

  setPlace(type) {
    this.mode = type ? 'place' : 'select';
    this.placeType = type;
    this.pending = null;
    this.onStatus(type ? `Click on the board to place a ${type}. Esc cancels.` : '');
    this.render();
  }

  select(sel) { this.selected = sel; this.onSelect(sel); this.render(); }

  point(ev) {
    const pt = this.svg.createSVGPoint();
    pt.x = ev.clientX; pt.y = ev.clientY;
    const p = pt.matrixTransform(this.svg.getScreenCTM().inverse());
    return [p.x / G, p.y / G];
  }

  snap([x, y]) { return [Math.max(1, Math.min(COLS - 1, Math.round(x))), Math.max(1, Math.min(ROWS - 1, Math.round(y)))]; }

  bind() {
    const svg = this.svg;
    svg.addEventListener('pointerdown', ev => {
      const t = ev.target.closest('[data-kind]');
      svg.focus({ preventScroll: true });
      if (this.mode === 'place') {
        const [x, y] = this.snap(this.point(ev));
        const id = this.doc.add(this.placeType, x, y);
        this.setPlace(null);
        this.select({ kind: 'comp', id });
        this.onChange('add');
        return;
      }
      if (t?.dataset.kind === 'term') { this.clickTerminal(t.dataset.id, t.dataset.term); ev.preventDefault(); return; }
      if (t?.dataset.kind === 'wire') { this.select({ kind: 'wire', w: JSON.parse(t.dataset.w) }); return; }
      if (t?.dataset.kind === 'comp') {
        const id = t.dataset.id, c = this.doc.components[id], [px, py] = this.point(ev);
        this.select({ kind: 'comp', id });
        this.drag = { id, dx: c.position[0] - px, dy: c.position[1] - py, moved: false };
        svg.setPointerCapture(ev.pointerId);
        ev.preventDefault();
        return;
      }
      this.pending = null;
      this.select(null);
    });
    svg.addEventListener('pointermove', ev => {
      if (this.pending) { this.cursor = this.point(ev); this.drawRubber(); }
      if (!this.drag) return;
      const [px, py] = this.point(ev), c = this.doc.components[this.drag.id];
      const [x, y] = this.snap([px + this.drag.dx, py + this.drag.dy]);
      if (x !== c.position[0] || y !== c.position[1]) { this.doc.move(this.drag.id, x, y); this.drag.moved = true; this.render(); }
    });
    svg.addEventListener('pointerup', () => {
      if (this.drag?.moved) this.onChange('move');
      this.drag = null;
    });
    svg.addEventListener('dblclick', ev => {
      const t = ev.target.closest('[data-kind=comp]');
      if (t && this.doc.components[t.dataset.id]?.type === 'Switch') this.toggleSwitch(t.dataset.id);
    });
    this.onKey = ev => {
      if (ev.target.closest?.('input, select, textarea')) return;
      if (ev.key === 'Escape') { this.pending = null; this.setPlace(null); return; }
      if (ev.key === 'r' || ev.key === 'R') { this.rotateSelected(); ev.preventDefault(); }
      if (ev.key === 'Delete' || ev.key === 'Backspace') { this.deleteSelected(); ev.preventDefault(); }
      if (ev.key === ' ' && this.selected?.kind === 'comp' && this.doc.components[this.selected.id].type === 'Switch') {
        this.toggleSwitch(this.selected.id); ev.preventDefault();
      }
    };
    document.addEventListener('keydown', this.onKey);
  }

  destroy() { document.removeEventListener('keydown', this.onKey); }

  clickTerminal(id, term) {
    if (!this.pending) {
      this.pending = [id, term];
      this.onStatus('Now click the terminal to wire it to (Esc cancels).');
      this.render();
      return;
    }
    const [a, ta] = this.pending;
    this.pending = null;
    if (a === id && ta === term) { this.onStatus(''); this.render(); return; }
    if (this.doc.connect(a, ta, id, term)) { this.onStatus(`Wired ${a}.${ta} to ${id}.${term}.`); this.onChange('wire'); }
    else this.onStatus(a === id ? 'A component cannot be wired to itself.' : 'Those terminals are already wired.');
    this.render();
  }

  toggleSwitch(id) {
    const c = this.doc.components[id];
    c.properties.state = !c.properties.state;
    this.onChange('switch');
    this.select({ kind: 'comp', id });
  }

  rotateSelected() {
    if (this.selected?.kind !== 'comp') return;
    this.doc.rotate(this.selected.id, 90);
    this.onChange('rotate');
    this.render();
  }

  deleteSelected() {
    const s = this.selected;
    if (!s) return;
    if (s.kind === 'comp') this.doc.remove(s.id);
    else this.doc.disconnect(...s.w);
    this.select(null);
    this.onChange('delete');
  }

  route(a, ta, b, tb) {
    const p = this.doc.terminals(a)[ta], q = this.doc.terminals(b)[tb];
    const vert = this.isVertical(a, ta);
    const mid = vert ? [p[0], q[1]] : [q[0], p[1]];
    return [p, mid, q].map(([x, y]) => `${x * G},${y * G}`).join(' ');
  }

  isVertical(id, term) {
    const c = this.doc.components[id], t = this.doc.terminals(id)[term];
    return t[0] === c.position[0] && t[1] !== c.position[1];
  }

  drawRubber() {
    const line = this.svg.querySelector('.rubber');
    if (!line || !this.pending || !this.cursor) return;
    const [x, y] = this.doc.terminals(this.pending[0])[this.pending[1]];
    line.setAttribute('x1', x * G); line.setAttribute('y1', y * G);
    line.setAttribute('x2', this.cursor[0] * G); line.setAttribute('y2', this.cursor[1] * G);
  }

  // live: { readouts: {id: {...}}, vmax } from the running engine, or null.
  render(live = this.live) {
    this.live = live;
    const doc = this.doc, R = live?.readouts || {}, vmax = live?.vmax || 0, parts = [];
    parts.push(`<rect class="bg" x="0" y="0" width="${COLS * G}" height="${ROWS * G}"/>`);
    parts.push('<g class="wires">');
    for (const w of doc.wires()) {
      const [a, ta] = w, v = R[a]?.voltages?.[ta];
      const sel = this.selected?.kind === 'wire' && JSON.stringify(this.selected.w) === JSON.stringify(w);
      const pts = this.route(...w);
      parts.push(`<polyline class="wire${sel ? ' sel' : ''}" points="${pts}" style="stroke:${sel ? 'var(--accent)' : voltColor(v, vmax)}"/>`,
        `<polyline class="wire-hit" data-kind="wire" data-w='${esc(JSON.stringify(w))}' points="${pts}"><title>${esc(`${w[0]}.${w[1]} – ${w[2]}.${w[3]}`)}${v !== undefined ? esc(` ${formatValue(v, 'V')}`) : ''}</title></polyline>`);
    }
    parts.push('</g><g class="comps">');
    for (const c of Object.values(doc.components)) {
      const sel = this.selected?.kind === 'comp' && this.selected.id === c.id;
      const [hx, hy, hw, hh] = hitBox(c), [x, y] = c.position;
      const r = R[c.id], over = r?.overload;
      parts.push(`<g class="comp${sel ? ' sel' : ''}${over ? ' over' : ''}" data-kind="comp" data-id="${esc(c.id)}" transform="translate(${x * G},${y * G}) rotate(${c.rotation}) scale(${G})">`
        + `<rect class="hit" x="${hx}" y="${hy}" width="${hw}" height="${hh}"/><title>${esc(c.id)}</title>${symbol(c, r || {})}</g>`);
      const tp = Object.values(doc.terminals(c.id));
      const vertical = c.type !== 'Ground' && Math.max(...tp.map(q => q[1])) - Math.min(...tp.map(q => q[1]))
        > Math.max(...tp.map(q => q[0])) - Math.min(...tp.map(q => q[0]));
      const lx = (x + (vertical ? 1.6 : 0)) * G, ly = (y + (vertical ? 0.3 : -1.1)) * G;
      parts.push(`<text class="val" x="${lx}" y="${ly}" text-anchor="${vertical ? 'start' : 'middle'}">${esc(valueLabel(c))}</text>`);
      if (r && c.type !== 'Ground') {
        const [vt, it] = readoutTerms(c.type);
        const across = r.voltages[vt[0]] - r.voltages[vt[1]];
        const txt = `${formatValue(across, 'V')} · ${formatValue(r.currents[it], 'A')}`;
        parts.push(`<text class="live" x="${lx}" y="${ly + (vertical ? 13 : 2.3 * G)}" text-anchor="${vertical ? 'start' : 'middle'}">${esc(txt)}</text>`);
      }
    }
    parts.push('</g><g class="terms">');
    for (const c of Object.values(doc.components)) {
      for (const [term, [tx, ty]] of Object.entries(doc.terminals(c.id))) {
        const on = this.pending && this.pending[0] === c.id && this.pending[1] === term;
        const linked = (c.connected_to[term] || []).length > 0;
        parts.push(`<circle class="term${on ? ' on' : ''}${linked ? ' linked' : ''}" data-kind="term" data-id="${esc(c.id)}" data-term="${term}" cx="${tx * G}" cy="${ty * G}" r="${linked ? 3.5 : 5}"><title>${esc(`${c.id}.${term}`)}${r0(R, c.id, term)}</title></circle>`);
      }
    }
    parts.push('</g><line class="rubber" x1="0" y1="0" x2="0" y2="0"/>');
    this.svg.innerHTML = parts.join('');
    this.svg.classList.toggle('placing', this.mode === 'place');
    this.svg.classList.toggle('wiring', !!this.pending);
    if (!this.pending) this.svg.querySelector('.rubber').style.display = 'none';
    else this.drawRubber();
  }
}

const r0 = (R, id, term) => (R[id] ? ` ${formatValue(R[id].voltages[term], 'V')}` : '');

// Terminals used for the "V across · I" readout: [[plus, minus], current terminal].
export function readoutTerms(type) {
  if (['DCVoltageSource', 'ACVoltageSource', 'DCCurrentSource'].includes(type)) return [['pos', 'neg'], 'neg'];
  if (type === 'Diode' || type === 'LED') return [['anode', 'cathode'], 'anode'];
  if (type === 'BJT') return [['collector', 'emitter'], 'collector'];
  if (type === 'Ground') return [['gnd', 'gnd'], 'gnd'];
  return [['p1', 'p2'], 'p1'];
}

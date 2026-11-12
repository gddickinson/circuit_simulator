// Side panel of the simulator page: component palette, property editor (values with SI units) and live readouts of
// the selected component, with buttons that add its voltage / current to the oscilloscope.
import { esc } from './core.js';
import { symbol } from './symbols.js';
import { parseValue, formatValue } from './units.js';
import { readoutTerms } from './schematic.js';

const UNIT_OF = { voltages: 'V', currents: 'A' };

export function paletteHtml(catalog) {
  const groups = {};
  for (const c of catalog) (groups[c.group] ||= []).push(c);
  return Object.entries(groups).map(([g, items]) => `<h3>${esc(g)}</h3><div class="palette">${items.map(c => {
    const vb = c.type === 'BJT' || c.type.endsWith('Source') ? '-2.4 -2.4 4.8 4.8' : c.type === 'Ground' ? '-1.5 -0.6 3 2.2' : '-2.3 -1.2 4.6 2.4';
    return `<button class="pal" data-type="${c.type}" title="${esc(c.label)}" aria-label="Place ${esc(c.label)}">
      <svg viewBox="${vb}" aria-hidden="true"><g class="sym">${symbol({ type: c.type, properties: c.defaults })}</g></svg>
      <span>${esc(c.label.replace(' source', '').replace(' transistor', ''))}</span></button>`;
  }).join('')}</div>`).join('');
}

function propInput(c, p, defaults) {
  const v = c.properties[p.name] ?? defaults[p.name], id = `pp-${p.name}`;
  if (p.choices) {
    return `<label for="${id}">${esc(p.label)}</label><select id="${id}" data-prop="${p.name}">${p.choices.map(o =>
      `<option${String(v) === o ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
  }
  if (p.unit === 'bool') {
    return `<label class="chk"><input type="checkbox" id="${id}" data-prop="${p.name}"${v ? ' checked' : ''}> ${esc(p.label)}</label>`;
  }
  // shown with its unit ("500 mA", "1 kΩ"); parseValue accepts the unit back
  const shown = v === undefined ? '' : (p.unit && p.unit !== '°' ? formatValue(Number(v), p.unit, 6) : String(v));
  return `<label for="${id}">${esc(p.label)}${p.unit ? ` <span class="mute">(${esc(p.unit)})</span>` : ''}</label>
    <input id="${id}" data-prop="${p.name}" data-unit="${esc(p.unit)}" value="${esc(shown)}" inputmode="decimal" autocomplete="off">`;
}

// Property editor for one component; onEdit(name, value) is called with parsed values.
export function renderProps(host, c, spec, { onEdit, onRotate, onDelete, onToggle }) {
  host.innerHTML = `<div class="selhead"><b>${esc(spec.label)}</b> <span class="mute mono small">${esc(c.id)}</span></div>
    ${spec.props.map(p => propInput(c, p, spec.defaults)).join('')}
    <p class="err small" id="pp-err" role="alert"></p>
    <div class="bar">${c.type === 'Switch' ? '<button id="pp-toggle">Toggle switch</button>' : ''}
      <button class="alt" id="pp-rot" title="Rotate 90° (R)">Rotate</button><button class="alt" id="pp-del" title="Delete">Delete</button></div>
    <div id="pp-live"></div>`;
  for (const el of host.querySelectorAll('[data-prop]')) {
    el.addEventListener('change', () => {
      const name = el.dataset.prop, p = spec.props.find(q => q.name === name);
      let val;
      if (el.type === 'checkbox') val = el.checked;
      else if (p.choices) val = el.value;
      else {
        val = parseValue(el.value, p.unit === 'Ω' ? 'Ω' : p.unit);
        const err = host.querySelector('#pp-err');
        if (!Number.isFinite(val)) { err.textContent = `${p.label}: "${el.value}" is not a number (try 4.7k, 10u, 1m).`; return; }
        if (['resistance', 'capacitance', 'inductance', 'frequency', 'gain'].includes(name) && val <= 0) {
          err.textContent = `${p.label} must be positive.`; return;
        }
        err.textContent = '';
      }
      onEdit(name, val);
    });
  }
  host.querySelector('#pp-rot').onclick = onRotate;
  host.querySelector('#pp-del').onclick = onDelete;
  const tg = host.querySelector('#pp-toggle');
  if (tg) tg.onclick = onToggle;
}

// Live readout table for the selected component (+ buttons that add probes to the scope).
export function renderLive(host, c, r, onProbe) {
  if (!host) return;
  if (!r) { host.innerHTML = '<p class="mute small">Run the simulation to see voltages and currents.</p>'; return; }
  const rows = Object.keys(r.voltages).map(term => `<tr><td>${esc(term)}</td><td class="num">${formatValue(r.voltages[term], 'V', 4)}</td>
    <td class="num">${formatValue(r.currents[term], 'A', 4)}</td></tr>`).join('');
  const extras = [];
  if (r.region) extras.push(`region <b>${esc(r.region)}</b>`);
  if ('conducting' in r) extras.push(r.conducting ? '<b>conducting</b>' : 'off');
  if ('brightness' in r) extras.push(`brightness ${(100 * r.brightness).toFixed(0)} %`);
  if ('charge' in r) extras.push(`Q ${formatValue(r.charge, 'C')}`);
  if ('flux' in r) extras.push(`Φ ${formatValue(r.flux, 'Wb')}`);
  if ('energy' in r) extras.push(`E ${formatValue(r.energy, 'J')}`);
  if (r.overload) extras.push(`<span class="err">⚠ over rating: ${esc(r.overload)}</span>`);
  const html = `<table class="live-tab"><tr><th>terminal</th><th>voltage</th><th>current in</th></tr>${rows}</table>
    <p class="small">power ${r.power >= 0 ? 'absorbed' : 'delivered'} <b>${formatValue(Math.abs(r.power), 'W', 4)}</b>${extras.length ? ' · ' + extras.join(' · ') : ''}</p>`;
  if (host.dataset.for !== c.id) {
    host.dataset.for = c.id;
    host.innerHTML = `<div class="tab-live"></div><div class="bar" id="probe-bar">
      ${c.type === 'Ground' ? '' : '<button class="alt" data-probe="v">Scope: V across</button><button class="alt" data-probe="i">Scope: current</button>'}</div>`;
    for (const b of host.querySelectorAll('[data-probe]')) b.onclick = () => onProbe(c, b.dataset.probe);
  }
  host.querySelector('.tab-live').innerHTML = html;
}

// Probe definition for the scope: V across the readout terminals or the current into the readout terminal.
export function makeProbe(c, kind) {
  const [[a, b], it] = readoutTerms(c.type);
  if (kind === 'v') {
    return { key: `${c.id}/v`, label: `V(${c.id}) ${a}−${b}`, unit: UNIT_OF.voltages,
      get: R => R[c.id].voltages[a] - R[c.id].voltages[b] };
  }
  return { key: `${c.id}/i`, label: `I(${c.id}) into ${it}`, unit: UNIT_OF.currents, get: R => R[c.id].currents[it] };
}

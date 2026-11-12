// Oscilloscope-style plot on a canvas: up to 4 probe traces (volts or amps) against simulated time, 10 x 8 divisions,
// a sweep window of the last N seconds, and auto-scaled 1-2-5 volts/div and amps/div.
import { formatValue } from './units.js';

export const TRACE_COLORS = ['#ffe14a', '#3dd9ff', '#ff5ad1', '#7dff6a'];
const MAX_POINTS = 4000;

function niceDiv(span) {  // smallest 1-2-5 step with 4 divisions covering +-span with some headroom
  const raw = Math.max(span, 1e-15) / 3.6, p = 10 ** Math.floor(Math.log10(raw));
  for (const m of [1, 2, 5, 10]) if (m * p >= raw * 0.999) return m * p;
  return 10 * p;
}

export class Scope {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.traces = [];
    this.window = 0.01;
  }

  // probe: { key, label, unit: 'V'|'A', get: readouts -> number }
  add(probe) {
    if (this.traces.some(t => t.key === probe.key)) return false;
    if (this.traces.length >= TRACE_COLORS.length) this.traces.shift();
    const used = new Set(this.traces.map(t => t.color));
    this.traces.push({ ...probe, color: TRACE_COLORS.find(c => !used.has(c)), t: [], y: [] });
    return true;
  }

  remove(key) { this.traces = this.traces.filter(t => t.key !== key); }
  clearData() { for (const tr of this.traces) { tr.t = []; tr.y = []; } }

  sample(time, readouts) {
    for (const tr of this.traces) {
      let v;
      try { v = tr.get(readouts); } catch { v = NaN; }
      tr.t.push(time); tr.y.push(v);
      if (tr.t.length > MAX_POINTS) { tr.t.splice(0, tr.t.length - MAX_POINTS); tr.y.splice(0, tr.y.length - MAX_POINTS); }
    }
  }

  scales(t0) {
    const out = {};
    for (const tr of this.traces) {
      let m = 0;
      tr.t.forEach((t, k) => { if (t >= t0 && Number.isFinite(tr.y[k])) m = Math.max(m, Math.abs(tr.y[k])); });
      out[tr.unit] = Math.max(out[tr.unit] || 0, m);
    }
    for (const u of Object.keys(out)) out[u] = niceDiv(out[u] || (u === 'V' ? 1 : 1e-3));
    return out;
  }

  draw(now) {
    const { canvas, ctx } = this, dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 600, h = canvas.clientHeight || 240;
    if (canvas.width !== Math.round(w * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#020806'; ctx.fillRect(0, 0, w, h);
    const padL = 6, padB = 18, pw = w - padL * 2, ph = h - padB - 6, top = 6;
    ctx.strokeStyle = 'rgba(80,255,170,.13)'; ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) { const x = padL + pw * i / 10; ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + ph); ctx.stroke(); }
    for (let j = 0; j <= 8; j++) { const y = top + ph * j / 8; ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + pw, y); ctx.stroke(); }
    ctx.strokeStyle = 'rgba(80,255,170,.35)';
    ctx.beginPath(); ctx.moveTo(padL, top + ph / 2); ctx.lineTo(padL + pw, top + ph / 2); ctx.stroke();
    const t1 = Math.max(now, this.window), t0 = t1 - this.window, sc = this.scales(t0);
    for (const tr of this.traces) {
      const div = sc[tr.unit];
      ctx.strokeStyle = tr.color; ctx.lineWidth = 1.6; ctx.beginPath();
      let pen = false;
      for (let k = 0; k < tr.t.length; k++) {
        if (tr.t[k] < t0 || !Number.isFinite(tr.y[k])) { pen = false; continue; }
        const x = padL + pw * (tr.t[k] - t0) / this.window;
        const y = top + ph / 2 - (tr.y[k] / div) * (ph / 8);
        const yc = Math.max(top - 2, Math.min(top + ph + 2, y));
        if (pen) ctx.lineTo(x, yc); else ctx.moveTo(x, yc);
        pen = true;
      }
      ctx.stroke();
    }
    ctx.font = '11px ui-monospace, Menlo, monospace'; ctx.fillStyle = '#8fb8a6';
    const scaleTxt = Object.entries(sc).map(([u, d]) => `${formatValue(d, u)}/div`).join('  ');
    ctx.fillText(`${formatValue(this.window / 10, 's')}/div  ${scaleTxt}`, padL + 2, h - 4);
    ctx.textAlign = 'right';
    ctx.fillText(`t = ${formatValue(now, 's')}`, w - padL, h - 4);
    ctx.textAlign = 'left';
  }
}

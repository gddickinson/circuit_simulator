// Transient analysis on top of circuit_engine.js: a port of simulation/transient.py.
// new Transient(circuit).advance(T) integrates by T seconds in sub-steps of at most maxStep (default 10 us, and at most
// 1/50 of any AC period) and returns per-component readouts. Trapezoidal steps, except BE_STEPS backward-Euler steps
// after a discontinuity (start, edits via discontinuity(), a diode/BJT changing region) to stop trapezoidal ringing.
import { G_OFF, R_ON, R_SAT, R_BE, R_CLOSED, R_OPEN, DEFAULT_MAX_STEP, Netlist, bjtParams, initialState, prop, solvePoint, sourceVoltage } from './circuit_engine.js';

export const BE_STEPS = 3;

// Python '%.4g'
const g4 = v => { const a = Math.abs(v); if (a !== 0 && (a < 1e-4 || a >= 1e4)) { const [m, e] = a.toExponential(3).split('e');
  return `${String(Number(m))}e${e[0]}${e.slice(1).padStart(2, '0')}`; } return String(Number(a.toPrecision(4))); };
function over(value, limit, unit, what) {
  if (limit === undefined || limit === null || Math.abs(value) <= Number(limit)) return '';
  return `${what} ${g4(value)} ${unit} > rating ${g4(Number(limit))} ${unit}`;
}

export function stepLimit(net, maxStep = DEFAULT_MAX_STEP) {
  let h = maxStep;
  for (const c of net.components) {
    if (c.type === 'ACVoltageSource') {
      const f = Math.abs(Number(prop(c, 'frequency')));
      if (f > 0) h = Math.min(h, 1.0 / (50.0 * f));
    }
  }
  return h;
}

// Terminal voltages, currents INTO each terminal, absorbed power and extras; commits capacitor v / inductor i into st.
export function readouts(net, st, v, x, h, t, trap = false) {
  const out = {};
  let groundSum = 0.0;
  for (const c of net.components) {
    const nd = net.nodes[c.id], s0 = st[c.id], V = {};
    for (const [term, k] of Object.entries(nd)) V[term] = v[k];
    let I = {}, extra = {}, ov = '';
    const n = name => Number(prop(c, name));
    switch (c.type) {
      case 'Resistor': case 'Switch': {
        const r = c.type === 'Resistor' ? Math.max(n('resistance'), 1e-6) : (prop(c, 'state') ? R_CLOSED : R_OPEN);
        const i = (V.p1 - V.p2) / r;
        I = { p1: i, p2: -i };
        if (c.type === 'Switch') { extra.closed = !!prop(c, 'state'); ov = over(i, prop(c, 'max_current'), 'A', 'current'); }
        else ov = over(i * (V.p1 - V.p2), prop(c, 'max_power'), 'W', 'power');
        break;
      }
      case 'Capacitor': {
        const cap = Math.max(n('capacitance'), 1e-18), vc = V.p1 - V.p2;
        const i = trap ? 2.0 * cap / h * (vc - s0.v) - s0.i : cap / h * (vc - s0.v);
        s0.v = vc; s0.i = i;
        ov = over(vc, prop(c, 'max_voltage'), 'V', 'voltage');
        I = { p1: i, p2: -i };
        extra = { charge: cap * vc, energy: 0.5 * cap * vc * vc };
        break;
      }
      case 'Inductor': {
        const ind = Math.max(n('inductance'), 1e-15), vl = V.p1 - V.p2;
        const i = trap ? s0.i + h / (2.0 * ind) * (vl + s0.v) : s0.i + h / ind * vl;
        s0.i = i; s0.v = vl;
        ov = over(i, prop(c, 'max_current'), 'A', 'current');
        I = { p1: i, p2: -i };
        extra = { flux: ind * i, energy: 0.5 * ind * i * i };
        break;
      }
      case 'DCVoltageSource': case 'ACVoltageSource': {
        const j = x[net.n + net.vsources.indexOf(c)];
        I = { pos: j, neg: -j };
        ov = over(j, prop(c, 'max_current'), 'A', 'current');
        if (c.type === 'ACVoltageSource') extra.instantaneous_voltage = sourceVoltage(c, t);
        break;
      }
      case 'DCCurrentSource': { const cur = n('current'); I = { pos: -cur, neg: cur }; ov = over(V.pos - V.neg, prop(c, 'max_voltage'), 'V', 'voltage'); break; }
      case 'Diode': case 'LED': {
        const vd = V.anode - V.cathode, vf = n('forward_voltage');
        const i = s0.on ? (vd - vf) / R_ON : G_OFF * vd, imax = n('max_current');
        I = { anode: i, cathode: -i };
        extra = { conducting: !!s0.on && i > 1e-6 };
        ov = over(i, imax, 'A', 'current');
        if (c.type === 'LED') extra.brightness = imax > 0 ? Math.min(1.0, Math.max(0.0, i) / imax) : 0.0;
        break;
      }
      case 'BJT': {
        const [s, beta, vth, vsat] = bjtParams(c);
        const vbe = s * (V.base - V.emitter), vce = s * (V.collector - V.emitter);
        let ib, ic;
        if (s0.region === 'cutoff') { ib = G_OFF * vbe; ic = 0.0; }
        else if (s0.region === 'active') { ib = (vbe - vth) / R_BE; ic = beta * ib; }
        else { ib = (vbe - vth) / R_BE; ic = (vce - vsat) / R_SAT; }
        ic += G_OFF * vce;
        I = { collector: s * ic, base: s * ib, emitter: -s * (ic + ib) };
        extra = { region: s0.region };
        ov = over(ic, prop(c, 'max_collector_current'), 'A', 'collector current');
        break;
      }
      case 'Ground': I = { gnd: 0.0 }; break;
      default: break;
    }
    if (ov) extra.overload = ov;
    if (c.type !== 'Ground') for (const [term, k] of Object.entries(nd)) if (k === 0) groundSum += I[term];
    let power = 0;
    for (const term of Object.keys(I)) power += V[term] * I[term];
    out[c.id] = { type: c.type, voltages: V, currents: I, power, ...extra };
  }
  const g = net.components.find(c => c.type === 'Ground');
  if (g) out[g.id].currents.gnd = -groundSum;
  return out;
}

export class Transient {
  constructor(circuit, maxStep = DEFAULT_MAX_STEP, state = null) {
    this.net = new Netlist(circuit);
    this.state = state || initialState(this.net);
    this.maxStep = maxStep;
    this.t = 0.0;
    this.last = {};
    this.converged = true;
    this.nodeVoltages = [0];
    this.beLeft = BE_STEPS;
  }

  // The circuit changed suddenly (switch flipped, value edited): take backward-Euler steps next.
  discontinuity() { this.beLeft = BE_STEPS; }

  advance(duration) {
    const hLim = stepLimit(this.net, this.maxStep);
    const nsub = Math.max(1, Math.ceil(duration / hLim - 1e-9)), h = duration / nsub, t0 = this.t;
    for (let k = 1; k <= nsub; k++) {
      const t = t0 + k * h, trap = this.beLeft <= 0, r = solvePoint(this.net, this.state, h, t, trap);
      this.converged = this.converged && r.converged;
      this.last = readouts(this.net, this.state, r.v, r.x, h, t, trap);
      this.nodeVoltages = r.v;
      if (r.iterations > 1) this.beLeft = BE_STEPS;
      else if (!trap) this.beLeft -= 1;
    }
    this.t = t0 + duration;
    return this.last;
  }

  // probes: [[componentId, 'v'|'i', terminal], ...] -> { t: [...], 'id/v/term': [...] }
  run(frame, frames, probes) {
    const trace = { t: [] };
    for (const p of probes) trace[p.join('/')] = [];
    for (let f = 0; f < frames; f++) {
      const r = this.advance(frame);
      trace.t.push(this.t);
      for (const [cid, kind, term] of probes) trace[[cid, kind, term].join('/')].push(r[cid][kind === 'v' ? 'voltages' : 'currents'][term]);
    }
    return trace;
  }
}

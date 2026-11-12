// Circuit engine: Modified Nodal Analysis + backward-Euler transient, a line-by-line port of simulation/mna.py and
// simulation/transient.py (node-tested against fixtures made by scripts/make_engine_fixture.py from the Python).
// Conventions: terminal current = current INTO the component at that terminal; power = absorbed (negative = delivered);
// a DCCurrentSource pushes `current` out of its pos terminal. Pure module: no DOM.

export const TERMINALS = {
  Resistor: ['p1', 'p2'], Capacitor: ['p1', 'p2'], Inductor: ['p1', 'p2'], Switch: ['p1', 'p2'], Ground: ['gnd'],
  DCVoltageSource: ['pos', 'neg'], ACVoltageSource: ['pos', 'neg'], DCCurrentSource: ['pos', 'neg'],
  Diode: ['anode', 'cathode'], LED: ['anode', 'cathode'], BJT: ['collector', 'base', 'emitter'],
};
export const DEFAULTS = {
  Resistor: { resistance: 1000.0 }, Capacitor: { capacitance: 1e-6 }, Inductor: { inductance: 1e-3 },
  Switch: { state: false }, Ground: {}, DCVoltageSource: { voltage: 5.0 },
  ACVoltageSource: { amplitude: 5.0, frequency: 1000.0, phase: 0.0 }, DCCurrentSource: { current: 0.01 },
  Diode: { forward_voltage: 0.7, max_current: 1.0 }, LED: { forward_voltage: 2.0, max_current: 0.02, color: 'red' },
  BJT: { type: 'npn', gain: 100, vbe_threshold: 0.7, vce_saturation: 0.2, max_collector_current: 0.5 },
};
export const GMIN = 1e-12, G_OFF = 1e-9, R_ON = 0.1, R_BE = 1000.0, R_SAT = 0.1, MAX_PWL_ITER = 60;
export const DEFAULT_MAX_STEP = 1e-5;

export class CircuitError extends Error {}

// Class name of a saved component: 'type' if present, else the same inference as utils/file_manager.py.
export function componentType(d) {
  const t = d.type || d.component_type;
  if (TERMINALS[t]) return t;
  const p = d.properties || {};
  if ('resistance' in p) return 'Resistor';
  if ('capacitance' in p) return 'Capacitor';
  if ('inductance' in p) return 'Inductor';
  if ('voltage' in p) return 'DCVoltageSource';
  if ('amplitude' in p && 'frequency' in p) return 'ACVoltageSource';
  if ('current' in p) return 'DCCurrentSource';
  if ('forward_voltage' in p) return 'color' in p ? 'LED' : 'Diode';
  if ('gain' in p) return 'BJT';
  return null;
}

export const prop = (c, name) => (name in c.properties ? c.properties[name] : DEFAULTS[c.type][name]);
const num = (c, name) => Number(prop(c, name));

export class Netlist {
  constructor(circuit) {
    const comps = [];
    for (const [cid, d] of Object.entries(circuit.components || {})) {
      const t = componentType(d);
      if (!t) continue;
      comps.push({ id: d.id || cid, type: t, properties: { ...(d.properties || {}) }, connected_to: d.connected_to || {} });
    }
    this.components = comps;
    const known = new Set(comps.map(c => c.id));
    const parent = new Map();
    const key = (id, term) => id + '\u0000' + term;
    const find = k => { while (parent.get(k) !== k) { parent.set(k, parent.get(parent.get(k))); k = parent.get(k); } return k; };
    for (const c of comps) for (const term of TERMINALS[c.type]) parent.set(key(c.id, term), key(c.id, term));
    for (const c of comps) {
      for (const [term, others] of Object.entries(c.connected_to)) {
        if (!parent.has(key(c.id, term))) continue;
        for (const [oid, oterm] of others) {
          if (known.has(oid) && parent.has(key(oid, oterm))) {
            const ra = find(key(c.id, term)), rb = find(key(oid, oterm));
            if (ra !== rb) parent.set(rb, ra);
          }
        }
      }
    }
    let ground = new Set(comps.filter(c => c.type === 'Ground').map(c => find(key(c.id, 'gnd'))));
    if (!ground.size) {
      const vs = comps.find(c => c.type === 'DCVoltageSource' || c.type === 'ACVoltageSource');
      if (vs) ground = new Set([find(key(vs.id, 'neg'))]);
    }
    if (!ground.size && comps.length) ground = new Set([find(key(comps[0].id, TERMINALS[comps[0].type][0]))]);
    const index = new Map();
    this.nodeNames = ['gnd'];
    for (const c of comps) {
      for (const term of TERMINALS[c.type]) {
        const r = find(key(c.id, term));
        if (ground.has(r)) index.set(r, 0);
        else if (!index.has(r)) { index.set(r, this.nodeNames.length); this.nodeNames.push(`${c.id}:${term}`); }
      }
    }
    this.nodes = {};
    for (const c of comps) {
      const nd = {};
      for (const term of TERMINALS[c.type]) nd[term] = index.get(find(key(c.id, term)));
      this.nodes[c.id] = nd;
    }
    this.n = this.nodeNames.length - 1;
    this.vsources = comps.filter(c => c.type === 'DCVoltageSource' || c.type === 'ACVoltageSource');
  }
}

export function sourceVoltage(c, t) {
  if (c.type === 'DCVoltageSource') return num(c, 'voltage');
  const a = num(c, 'amplitude'), f = num(c, 'frequency'), ph = num(c, 'phase');
  return a * Math.sin(2 * Math.PI * f * t + ph * Math.PI / 180);
}

export function initialState(net) {
  const st = {};
  for (const c of net.components) {
    if (c.type === 'Capacitor') st[c.id] = { v: 0.0 };
    else if (c.type === 'Inductor') st[c.id] = { i: 0.0 };
    else if (c.type === 'Diode' || c.type === 'LED') st[c.id] = { on: false };
    else if (c.type === 'BJT') st[c.id] = { region: 'cutoff' };
  }
  return st;
}

class Stamp {
  constructor(size) { this.size = size; this.A = Array.from({ length: size }, () => new Float64Array(size)); this.b = new Float64Array(size); }
  g(a, c, g) {
    if (a) this.A[a - 1][a - 1] += g;
    if (c) this.A[c - 1][c - 1] += g;
    if (a && c) { this.A[a - 1][c - 1] -= g; this.A[c - 1][a - 1] -= g; }
  }
  i(a, c, cur) { if (a) this.b[a - 1] -= cur; if (c) this.b[c - 1] += cur; }
  vccs(op, on, ip, inn, gm) {
    for (const [row, sign] of [[op, 1.0], [on, -1.0]]) {
      if (!row) continue;
      if (ip) this.A[row - 1][ip - 1] += sign * gm;
      if (inn) this.A[row - 1][inn - 1] -= sign * gm;
    }
  }
}

export function bjtParams(c) {
  return [String(prop(c, 'type')).toLowerCase() === 'npn' ? 1.0 : -1.0, num(c, 'gain'), num(c, 'vbe_threshold'), num(c, 'vce_saturation')];
}
const resistance = c => (c.type === 'Resistor' ? Math.max(num(c, 'resistance'), 1e-6) : (prop(c, 'state') ? 0.01 : 1e9));

function assemble(net, st, h, t) {
  const n = net.n, m = net.vsources.length, S = new Stamp(n + m);
  for (let k = 1; k <= n; k++) S.A[k - 1][k - 1] += GMIN;
  for (const c of net.components) {
    const nd = net.nodes[c.id], s0 = st[c.id];
    switch (c.type) {
      case 'Resistor': case 'Switch': S.g(nd.p1, nd.p2, 1.0 / resistance(c)); break;
      case 'Capacitor': { const g = Math.max(num(c, 'capacitance'), 1e-18) / h; S.g(nd.p1, nd.p2, g); S.i(nd.p2, nd.p1, g * s0.v); break; }
      case 'Inductor': { const g = h / Math.max(num(c, 'inductance'), 1e-15); S.g(nd.p1, nd.p2, g); S.i(nd.p1, nd.p2, s0.i); break; }
      case 'DCCurrentSource': S.i(nd.neg, nd.pos, num(c, 'current')); break;
      case 'Diode': case 'LED':
        if (s0.on) { const g = 1.0 / R_ON; S.g(nd.anode, nd.cathode, g); S.i(nd.cathode, nd.anode, g * num(c, 'forward_voltage')); }
        else S.g(nd.anode, nd.cathode, G_OFF);
        break;
      case 'BJT': {
        const [s, beta, vth, vsat] = bjtParams(c), col = nd.collector, base = nd.base, em = nd.emitter;
        S.g(col, em, G_OFF);
        if (s0.region === 'cutoff') { S.g(base, em, G_OFF); break; }
        const gbe = 1.0 / R_BE;
        S.g(base, em, gbe); S.i(em, base, s * gbe * vth);
        if (s0.region === 'active') { S.vccs(col, em, base, em, beta * gbe); S.i(em, col, s * beta * gbe * vth); }
        else { S.g(col, em, 1.0 / R_SAT); S.i(em, col, s * vsat / R_SAT); }
        break;
      }
      default: break;
    }
  }
  net.vsources.forEach((c, j) => {
    const row = n + j, p = net.nodes[c.id].pos, q = net.nodes[c.id].neg;
    if (p) { S.A[p - 1][row] += 1.0; S.A[row][p - 1] += 1.0; }
    if (q) { S.A[q - 1][row] -= 1.0; S.A[row][q - 1] -= 1.0; }
    S.b[row] = sourceVoltage(c, t);
  });
  return S;
}

// Dense LU solve with partial pivoting (as LAPACK gesv); throws CircuitError if singular.
export function solveLinear(A, b) {
  const n = b.length, M = A.map(r => Float64Array.from(r)), x = Float64Array.from(b);
  let scale = 0;
  for (const r of M) for (const v of r) scale = Math.max(scale, Math.abs(v));
  for (let k = 0; k < n; k++) {
    let p = k, best = Math.abs(M[k][k]);
    for (let r = k + 1; r < n; r++) if (Math.abs(M[r][k]) > best) { best = Math.abs(M[r][k]); p = r; }
    if (!(best > scale * 1e-300) || best === 0) throw new CircuitError('singular circuit matrix (a loop of voltage sources or shorted source?)');
    if (p !== k) { [M[p], M[k]] = [M[k], M[p]]; [x[p], x[k]] = [x[k], x[p]]; }
    const Mk = M[k], piv = Mk[k];
    for (let r = k + 1; r < n; r++) {
      const Mr = M[r], f = Mr[k] / piv;
      if (f === 0) continue;
      Mr[k] = f;
      for (let c = k + 1; c < n; c++) Mr[c] -= f * Mk[c];
      x[r] -= f * x[k];
    }
  }
  for (let k = n - 1; k >= 0; k--) {
    let s = x[k];
    for (let c = k + 1; c < n; c++) s -= M[k][c] * x[c];
    x[k] = s / M[k][k];
  }
  return x;
}

function updateRegions(net, st, v) {
  let changed = false;
  for (const c of net.components) {
    const nd = net.nodes[c.id], s0 = st[c.id];
    if (c.type === 'Diode' || c.type === 'LED') {
      const vd = v[nd.anode] - v[nd.cathode], vf = num(c, 'forward_voltage');
      const on = s0.on ? (vd - vf) / R_ON > 0 : vd > vf;
      if (on !== s0.on) { s0.on = on; changed = true; }
    } else if (c.type === 'BJT') {
      const [s, beta, vth, vsat] = bjtParams(c);
      const vbe = s * (v[nd.base] - v[nd.emitter]), vce = s * (v[nd.collector] - v[nd.emitter]);
      const ib = (vbe - vth) / R_BE;
      let nw;
      if (ib <= 0) nw = 'cutoff';
      else if (s0.region === 'saturation') nw = (vce - vsat) / R_SAT > beta * ib ? 'active' : 'saturation';
      else nw = vce < vsat ? 'saturation' : 'active';
      if (nw !== s0.region) { s0.region = nw; changed = true; }
    }
  }
  return changed;
}

// One backward-Euler step ending at time t; iterates PWL regions. Returns { v, x, iterations, converged }.
export function solvePoint(net, st, h, t) {
  const size = net.n + net.vsources.length;
  let v, x;
  for (let it = 1; it <= MAX_PWL_ITER; it++) {
    const S = assemble(net, st, h, t);
    if (size === 0) return { v: [0.0], x: [], iterations: it, converged: true };
    x = solveLinear(S.A, S.b);
    if (!x.every(Number.isFinite)) throw new CircuitError('circuit has no finite solution');
    v = [0.0, ...x.slice(0, net.n)];
    if (!updateRegions(net, st, v)) return { v, x, iterations: it, converged: true };
  }
  return { v, x, iterations: MAX_PWL_ITER, converged: false };
}

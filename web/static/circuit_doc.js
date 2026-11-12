// The circuit being edited, in the desktop app's .circuit file format (CircuitSimulator.to_dict + "type"):
// { components: { id: { id, type, component_id, position:[x,y], rotation, properties, connected_to:{term:[[id,term]]},
//   size, state } }, simulation_time, time_step, ground_node, metadata }. Wires are terminal-to-terminal connections
// stored on both components, exactly like BaseComponent.connect(). Pure module: no DOM.
import { TERMINALS, componentType } from './circuit_engine.js';

export const ID_PREFIX = { Resistor: 'resistor_', Capacitor: 'capacitor_', Inductor: 'inductor_', Ground: 'ground_',
  DCVoltageSource: 'dc_source_', ACVoltageSource: 'ac_source_', DCCurrentSource: 'dc_current_', Diode: 'diode_', LED: 'led_',
  BJT: 'bjt_', Switch: 'switch_' };

// Python's round(): halves go to the even neighbour (BaseComponent._rotate_point rounds offsets like 1.5 -> 2).
export function pyRound(x) {
  const f = Math.floor(x), d = x - f;
  if (d > 0.5) return f + 1;
  if (d < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

// Rotated, rounded connection offset (BaseComponent._rotate_point) for a rotation in degrees.
export function rotateOffset([x, y], deg) {
  const r = deg * Math.PI / 180, c = Math.round(Math.cos(r)), s = Math.round(Math.sin(r));
  return [pyRound(x * c - y * s), pyRound(x * s + y * c)];
}

export class CircuitDoc {
  constructor(catalog) {
    this.catalog = Object.fromEntries(catalog.map(c => [c.type, c]));
    this.clear();
  }

  clear() { this.components = {}; this.meta = { version: '1.0', description: '' }; this.timeStep = 0.001; }

  newId(type) {
    const prefix = ID_PREFIX[type];
    let k = 1;
    while (this.components[prefix + k]) k++;
    return prefix + k;
  }

  add(type, x, y, rotation = 0, properties = null) {
    const spec = this.catalog[type], id = this.newId(type);
    this.components[id] = { id, type, component_id: null, position: [x, y], rotation, properties: properties || { ...spec.defaults },
      connected_to: {}, size: [...spec.size], state: {} };
    return id;
  }

  // Absolute grid position of every terminal: { term: [x, y] } (BaseComponent.connection_points).
  terminals(id) {
    const c = this.components[id], spec = this.catalog[c.type], out = {};
    for (const [term, off] of Object.entries(spec.connections)) {
      const [dx, dy] = rotateOffset(off, c.rotation);
      out[term] = [c.position[0] + dx, c.position[1] + dy];
    }
    return out;
  }

  move(id, x, y) { this.components[id].position = [x, y]; }
  rotate(id, delta = 90) { const c = this.components[id]; c.rotation = ((c.rotation + delta) % 360 + 360) % 360; }

  remove(id) {
    for (const [term, list] of Object.entries(this.components[id].connected_to)) {
      for (const [oid, oterm] of list) this.unlinkOne(oid, oterm, id, term);
    }
    delete this.components[id];
  }

  unlinkOne(id, term, oid, oterm) {
    const c = this.components[id];
    if (!c || !c.connected_to[term]) return;
    c.connected_to[term] = c.connected_to[term].filter(([a, b]) => !(a === oid && b === oterm));
    if (!c.connected_to[term].length) delete c.connected_to[term];
  }

  connected(a, ta, b, tb) { return (this.components[a]?.connected_to[ta] || []).some(([o, t]) => o === b && t === tb); }

  // Wire two terminals (both directions, as CircuitSimulator.connect_components_at). False if invalid or present.
  connect(a, ta, b, tb) {
    if (a === b || !this.components[a] || !this.components[b] || this.connected(a, ta, b, tb)) return false;
    for (const [id, t, o, ot] of [[a, ta, b, tb], [b, tb, a, ta]]) (this.components[id].connected_to[t] ||= []).push([o, ot]);
    return true;
  }

  disconnect(a, ta, b, tb) { this.unlinkOne(a, ta, b, tb); this.unlinkOne(b, tb, a, ta); }

  // Unique wires [[a, ta, b, tb], ...] (each stored pair once).
  wires() {
    const seen = new Set(), out = [];
    for (const c of Object.values(this.components)) {
      for (const [term, list] of Object.entries(c.connected_to)) {
        for (const [oid, oterm] of list) {
          if (!this.components[oid]) continue;
          const k = [c.id + ':' + term, oid + ':' + oterm].sort().join('|');
          if (!seen.has(k)) { seen.add(k); out.push([c.id, term, oid, oterm]); }
        }
      }
    }
    return out;
  }

  // The circuit as a .circuit file (opens in the desktop app with File > Open).
  toFile(simTime = 0) {
    const components = {};
    // no "state": the desktop loader then starts each component from its own _init_state()
    for (const [id, c] of Object.entries(this.components)) { const { state, ...rest } = structuredClone(c); components[id] = rest; }
    return { components, simulation_time: simTime, time_step: this.timeStep, ground_node: null,
      metadata: { ...this.meta, created: new Date().toISOString() } };
  }

  // Load a .circuit file (also files saved before the "type" field: type inferred as utils/file_manager.py does).
  load(data) {
    if (!data || typeof data.components !== 'object') throw new Error('not a .circuit file: no "components"');
    const comps = {};
    let skipped = 0;
    for (const [key, d] of Object.entries(data.components)) {
      const type = componentType({ ...d, id: d.id || key }) || idType(d.id || key);
      if (!type || !this.catalog[type]) { skipped++; continue; }
      const id = d.id || key;
      comps[id] = { id, type, component_id: d.component_id ?? null, position: [...(d.position || [0, 0])].map(Number),
        rotation: Number(d.rotation || 0), properties: { ...(d.properties || {}) }, connected_to: {},
        size: [...(d.size || this.catalog[type].size)], state: {} };
      for (const [term, list] of Object.entries(d.connected_to || {})) {
        if (TERMINALS[type].includes(term)) comps[id].connected_to[term] = list.map(([o, t]) => [o, t]);
      }
    }
    // keep only links whose other end exists, and make every link two-sided
    this.components = comps;
    for (const c of Object.values(comps)) {
      for (const [term, list] of Object.entries(c.connected_to)) {
        c.connected_to[term] = list.filter(([o, t]) => comps[o] && TERMINALS[comps[o].type].includes(t));
        for (const [o, t] of c.connected_to[term]) if (!this.connected(o, t, c.id, term)) (comps[o].connected_to[t] ||= []).push([c.id, term]);
        if (!c.connected_to[term].length) delete c.connected_to[term];
      }
    }
    this.timeStep = Number(data.time_step) || 0.001;
    this.meta = { version: '1.0', description: '', ...(data.metadata || {}) };
    return skipped;
  }

  // Plain circuit for the engine (no positions needed).
  engineCircuit() { return { components: structuredClone(this.components) }; }
}

// Id-prefix inference of FileManager._map_component_type (files from the desktop app before the "type" field).
function idType(id) {
  for (const [type, prefix] of Object.entries(ID_PREFIX)) if (String(id).startsWith(prefix)) return type;
  if (String(id).startsWith('dc_voltage_')) return 'DCVoltageSource';
  if (String(id).startsWith('ac_voltage_')) return 'ACVoltageSource';
  return null;
}

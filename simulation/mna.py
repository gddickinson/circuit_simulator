"""
Circuit Simulator - Modified Nodal Analysis engine (Qt-free, pure NumPy)
-----------------------------------------------------------------------
Solves a circuit given in the saved-file format ({'components': {id: {'type', 'properties', 'connected_to', ...}}})
by Modified Nodal Analysis with trapezoidal (or, right after a discontinuity, backward-Euler) companion models for
capacitors and inductors and piecewise-linear (PWL) models for diodes, LEDs and BJTs, iterated until every device's
region is self-consistent: at most config.MAX_ITERATIONS passes, and a device only changes region when the solution
violates its current region by more than config.CONVERGENCE_THRESHOLD volts (hysteresis against chattering).

Unknowns x = [node voltages (ground excluded) | voltage-source branch currents]; A x = b.
Sign conventions (used everywhere, including the web engine static/mna_engine.js which mirrors this file):
  * terminal current = current flowing INTO the component at that terminal (so a resistor has i_p1 = -i_p2 = (V1-V2)/R
    and a source delivering power has a negative current at its + terminal);
  * power = sum(v_t * i_t) = power absorbed (negative = delivered);
  * DCCurrentSource pushes 'current' amperes OUT of its pos terminal into the external circuit.
Models (component defaults match components/*.py):
  Resistor R; Switch 0.01 ohm closed / 1 Gohm open; Capacitor i = C dv/dt; Inductor v = L di/dt;
  Diode/LED: off -> 1 nS leak, on -> i = (v - Vf) / 0.1 ohm;
  BJT (npn/pnp): base-emitter like a diode with Vth = vbe_threshold and 1 kohm (as BJT.calculate: ib = (vbe-Vth)/1k),
  active: ic = gain * ib, saturation: vce clamped at vce_saturation through 0.1 ohm.
Every node also has gmin = 1e-12 S to ground so floating nodes do not make A singular.
"""

import math

import numpy as np

import config

TERMINALS = {
    'Resistor': ('p1', 'p2'), 'Capacitor': ('p1', 'p2'), 'Inductor': ('p1', 'p2'), 'Switch': ('p1', 'p2'),
    'Ground': ('gnd',), 'DCVoltageSource': ('pos', 'neg'), 'ACVoltageSource': ('pos', 'neg'),
    'DCCurrentSource': ('pos', 'neg'), 'Diode': ('anode', 'cathode'), 'LED': ('anode', 'cathode'),
    'BJT': ('collector', 'base', 'emitter'),
}
DEFAULTS = {
    'Resistor': {'resistance': 1000.0}, 'Capacitor': {'capacitance': 1e-6}, 'Inductor': {'inductance': 1e-3},
    'Switch': {'state': False}, 'Ground': {}, 'DCVoltageSource': {'voltage': 5.0},
    'ACVoltageSource': {'amplitude': 5.0, 'frequency': 1000.0, 'phase': 0.0},
    'DCCurrentSource': {'current': 0.01}, 'Diode': {'forward_voltage': 0.7, 'max_current': 1.0},
    'LED': {'forward_voltage': 2.0, 'max_current': 0.02, 'color': 'red'},
    'BJT': {'type': 'npn', 'gain': 100, 'vbe_threshold': 0.7, 'vce_saturation': 0.2, 'max_collector_current': 0.5},
}
# Ratings (desktop defaults: components/*.py get_property(..., default) and gui/component_panel.py). They do not
# change the solution; a part driven past its rating is flagged 'overload' (shown as over rating / burnt out).
RATINGS = {
    'Resistor': {'max_power': 0.25}, 'Capacitor': {'max_voltage': 50.0}, 'Inductor': {'max_current': 1.0},
    'DCVoltageSource': {'max_current': 1.0}, 'ACVoltageSource': {'max_current': 1.0},
    'DCCurrentSource': {'max_voltage': 12.0}, 'Switch': {'max_current': 5.0},
}
GMIN = 1e-12
G_OFF = 1e-9
R_ON = 0.1
R_BE = 1000.0
R_SAT = 0.1
MAX_PWL_ITER = int(config.MAX_ITERATIONS)       # 100
REGION_TOL = float(config.CONVERGENCE_THRESHOLD)  # 1e-6 V


class CircuitError(Exception):
    """The circuit cannot be solved (e.g. a loop of voltage sources)."""


def component_type(data):
    """Class name of a saved component: 'type' if present, else the same inference as FileManager."""
    t = data.get('type') or data.get('component_type')
    if t in TERMINALS:
        return t
    p = data.get('properties', {}) or {}
    for key, name in (('resistance', 'Resistor'), ('capacitance', 'Capacitor'), ('inductance', 'Inductor')):
        if key in p:
            return name
    if 'voltage' in p:
        return 'DCVoltageSource'
    if 'amplitude' in p and 'frequency' in p:
        return 'ACVoltageSource'
    if 'current' in p:
        return 'DCCurrentSource'
    if 'forward_voltage' in p:
        return 'LED' if 'color' in p else 'Diode'
    if 'gain' in p:
        return 'BJT'
    return None


def prop(comp, name):
    """Property with the component's default (as get_property(name, default) in components/*.py)."""
    if name in comp['properties']:
        return comp['properties'][name]
    return DEFAULTS[comp['type']].get(name, RATINGS.get(comp['type'], {}).get(name))


class Netlist:
    """Nodes and elements of a circuit; node 0 is ground."""

    def __init__(self, circuit):
        comps = []
        for cid, data in (circuit.get('components') or {}).items():
            t = component_type(data)
            if t is None:
                continue
            comps.append({'id': data.get('id', cid), 'type': t, 'properties': dict(data.get('properties') or {}),
                          'connected_to': data.get('connected_to') or {}})
        self.components = comps
        known = {c['id'] for c in comps}
        parent = {}

        def find(k):
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        for c in comps:
            for term in TERMINALS[c['type']]:
                parent[(c['id'], term)] = (c['id'], term)
        for c in comps:
            for term, others in c['connected_to'].items():
                if (c['id'], term) not in parent:
                    continue
                for other_id, other_term in others:
                    if other_id in known and (other_id, other_term) in parent:
                        ra, rb = find((c['id'], term)), find((other_id, other_term))
                        if ra != rb:
                            parent[rb] = ra
        # ground roots: every Ground terminal; else the neg terminal of the first voltage source; else the first node
        ground = {find((c['id'], 'gnd')) for c in comps if c['type'] == 'Ground'}
        if not ground:
            for c in comps:
                if c['type'] in ('DCVoltageSource', 'ACVoltageSource'):
                    ground = {find((c['id'], 'neg'))}
                    break
        if not ground and comps:
            ground = {find((comps[0]['id'], TERMINALS[comps[0]['type']][0]))}
        index = {}
        self.node_names = ['gnd']
        for c in comps:
            for term in TERMINALS[c['type']]:
                r = find((c['id'], term))
                if r in ground:
                    index[r] = 0
                elif r not in index:
                    index[r] = len(self.node_names)
                    self.node_names.append(f'{c["id"]}:{term}')
        self.nodes = {}
        for c in comps:
            self.nodes[c['id']] = {term: index[find((c['id'], term))] for term in TERMINALS[c['type']]}
        self.n = len(self.node_names) - 1
        self.vsources = [c for c in comps if c['type'] in ('DCVoltageSource', 'ACVoltageSource')]


def source_voltage(comp, t):
    """Voltage of a voltage source at time t (AC: amplitude * sin(2 pi f t + phase_deg))."""
    if comp['type'] == 'DCVoltageSource':
        return float(prop(comp, 'voltage'))
    a, f, ph = float(prop(comp, 'amplitude')), float(prop(comp, 'frequency')), float(prop(comp, 'phase'))
    return a * math.sin(2 * math.pi * f * t + math.radians(ph))


def initial_state(netlist):
    """Circuit at rest: capacitors uncharged, inductors without current, diodes off, BJTs in cutoff."""
    st = {}
    for c in netlist.components:
        t = c['type']
        if t == 'Capacitor':
            st[c['id']] = {'v': 0.0, 'i': 0.0}
        elif t == 'Inductor':
            st[c['id']] = {'i': 0.0, 'v': 0.0}
        elif t in ('Diode', 'LED'):
            st[c['id']] = {'on': False}
        elif t == 'BJT':
            st[c['id']] = {'region': 'cutoff'}
    return st


class _Stamp:
    def __init__(self, size):
        self.A = np.zeros((size, size))
        self.b = np.zeros(size)

    def g(self, a, c, g):
        """Conductance g between nodes a and c (0 = ground)."""
        if a:
            self.A[a - 1, a - 1] += g
        if c:
            self.A[c - 1, c - 1] += g
        if a and c:
            self.A[a - 1, c - 1] -= g
            self.A[c - 1, a - 1] -= g

    def i(self, a, c, cur):
        """Current source pushing cur from node a through itself into node c (leaves a, enters c)."""
        if a:
            self.b[a - 1] -= cur
        if c:
            self.b[c - 1] += cur

    def vccs(self, out_p, out_n, in_p, in_n, gm):
        """Current gm*(V(in_p)-V(in_n)) leaving node out_p and entering node out_n through the element."""
        for row, sign in ((out_p, 1.0), (out_n, -1.0)):
            if not row:
                continue
            if in_p:
                self.A[row - 1, in_p - 1] += sign * gm
            if in_n:
                self.A[row - 1, in_n - 1] -= sign * gm


def _bjt(comp):
    s = 1.0 if str(prop(comp, 'type')).lower() == 'npn' else -1.0
    return s, float(prop(comp, 'gain')), float(prop(comp, 'vbe_threshold')), float(prop(comp, 'vce_saturation'))


def _assemble(net, st, h, t, trap):
    n, m = net.n, len(net.vsources)
    S = _Stamp(n + m)
    for k in range(1, n + 1):
        S.A[k - 1, k - 1] += GMIN
    for c in net.components:
        ty, nd, cid = c['type'], net.nodes[c['id']], c['id']
        if ty in ('Resistor', 'Switch'):
            r = max(float(prop(c, 'resistance')), 1e-6) if ty == 'Resistor' else (0.01 if prop(c, 'state') else 1e9)
            S.g(nd['p1'], nd['p2'], 1.0 / r)
        elif ty == 'Capacitor':  # BE: i = C/h (v - v0); trapezoidal: i = 2C/h (v - v0) - i0
            g = (2.0 if trap else 1.0) * max(float(prop(c, 'capacitance')), 1e-18) / h
            S.g(nd['p1'], nd['p2'], g)
            S.i(nd['p2'], nd['p1'], g * st[cid]['v'] + (st[cid]['i'] if trap else 0.0))
        elif ty == 'Inductor':  # BE: i = i0 + h/L v; trapezoidal: i = i0 + h/2L (v + v0)
            g = h / ((2.0 if trap else 1.0) * max(float(prop(c, 'inductance')), 1e-15))
            S.g(nd['p1'], nd['p2'], g)
            S.i(nd['p1'], nd['p2'], st[cid]['i'] + (g * st[cid]['v'] if trap else 0.0))
        elif ty == 'DCCurrentSource':
            S.i(nd['neg'], nd['pos'], float(prop(c, 'current')))
        elif ty in ('Diode', 'LED'):
            a, k = nd['anode'], nd['cathode']
            if st[cid]['on']:
                g = 1.0 / R_ON
                S.g(a, k, g)
                S.i(k, a, g * float(prop(c, 'forward_voltage')))
            else:
                S.g(a, k, G_OFF)
        elif ty == 'BJT':
            s, beta, vth, vsat = _bjt(c)
            col, base, em = nd['collector'], nd['base'], nd['emitter']
            region = st[cid]['region']
            S.g(col, em, G_OFF)
            if region == 'cutoff':
                S.g(base, em, G_OFF)
                continue
            gbe = 1.0 / R_BE  # base-emitter: i_b (npn frame) = gbe * (s*(Vb-Ve) - vth)
            S.g(base, em, gbe)
            S.i(em, base, s * gbe * vth)
            if region == 'active':  # i_c = beta * i_b, flowing collector -> emitter (npn frame)
                S.vccs(col, em, base, em, beta * gbe)
                S.i(em, col, s * beta * gbe * vth)
            else:  # saturation: i_c = (s*(Vc-Ve) - vsat) / R_SAT
                S.g(col, em, 1.0 / R_SAT)
                S.i(em, col, s * vsat / R_SAT)
    for j, c in enumerate(net.vsources):
        row = n + j
        p, q = net.nodes[c['id']]['pos'], net.nodes[c['id']]['neg']
        if p:
            S.A[p - 1, row] += 1.0
            S.A[row, p - 1] += 1.0
        if q:
            S.A[q - 1, row] -= 1.0
            S.A[row, q - 1] -= 1.0
        S.b[row] = source_voltage(c, t)
    return S


def _update_regions(net, st, v):
    """Move PWL devices to the region consistent with the solution v (with REGION_TOL volts of hysteresis);
    return True if any changed."""
    changed = False
    tol = REGION_TOL
    for c in net.components:
        ty, nd, cid = c['type'], net.nodes[c['id']], c['id']
        if ty in ('Diode', 'LED'):
            vd = v[nd['anode']] - v[nd['cathode']]
            vf = float(prop(c, 'forward_voltage'))
            on = vd > vf - tol if st[cid]['on'] else vd > vf + tol
            if on != st[cid]['on']:
                st[cid]['on'] = on
                changed = True
        elif ty == 'BJT':
            s, beta, vth, vsat = _bjt(c)
            vbe = s * (v[nd['base']] - v[nd['emitter']])
            vce = s * (v[nd['collector']] - v[nd['emitter']])
            ib = (vbe - vth) / R_BE
            region = st[cid]['region']
            if region == 'cutoff':
                new = 'cutoff' if vbe <= vth + tol else ('saturation' if vce < vsat else 'active')
            elif vbe < vth - tol:
                new = 'cutoff'
            elif region == 'saturation':
                new = 'active' if vce - vsat > R_SAT * beta * ib + tol else 'saturation'
            else:
                new = 'saturation' if vce < vsat - tol else 'active'
            if new != region:
                st[cid]['region'] = new
                changed = True
    return changed


def solve_point(net, st, h, t, trap=False):
    """One step of length h ending at time t (trapezoidal if trap else backward Euler): iterate PWL regions,
    return (v, x, iterations, converged); iterations > 1 means some device changed region during the step."""
    size = net.n + len(net.vsources)
    for it in range(1, MAX_PWL_ITER + 1):
        S = _assemble(net, st, h, t, trap)
        if size == 0:
            return np.zeros(1), np.zeros(0), it, True
        try:
            x = np.linalg.solve(S.A, S.b)
        except np.linalg.LinAlgError as exc:
            raise CircuitError('singular circuit matrix (a loop of voltage sources or shorted source?)') from exc
        if not np.all(np.isfinite(x)):
            raise CircuitError('circuit has no finite solution')
        v = np.concatenate(([0.0], x[:net.n]))
        if not _update_regions(net, st, v):
            return v, x, it, True
    return v, x, MAX_PWL_ITER, False

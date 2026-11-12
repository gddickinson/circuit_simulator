"""
Circuit Simulator - transient analysis on top of the MNA engine (Qt-free)
------------------------------------------------------------------------
Transient(circuit).advance(T) integrates the circuit by T seconds in backward-Euler sub-steps no longer than
max_step (default 10 us, and at most 1/50 of the period of any AC source), then returns per-component readouts.
Mirrored in JS by web/static/circuit_engine.js (node-tested against fixtures made from this module).
"""

import math

from simulation.mna import (DEFAULTS, G_OFF, R_BE, R_ON, R_SAT, Netlist, _bjt, initial_state, prop,
                            solve_point, source_voltage)

DEFAULT_MAX_STEP = 1e-5


def step_limit(net, max_step=DEFAULT_MAX_STEP):
    """Largest allowed internal step: max_step, and 50 steps per period of every AC source."""
    h = max_step
    for c in net.components:
        if c['type'] == 'ACVoltageSource':
            f = abs(float(prop(c, 'frequency')))
            if f > 0:
                h = min(h, 1.0 / (50.0 * f))
    return h


def readouts(net, st, v, x, h, t):
    """Per-component terminal voltages, currents INTO each terminal, absorbed power and extras.

    Also commits the capacitor voltages and inductor currents of this step into st.
    """
    out = {}
    ground_sum = 0.0
    for c in net.components:
        ty, nd, cid = c['type'], net.nodes[c['id']], c['id']
        V = {term: float(v[k]) for term, k in nd.items()}
        I, extra = {}, {}
        if ty in ('Resistor', 'Switch'):
            r = max(float(prop(c, 'resistance')), 1e-6) if ty == 'Resistor' else (0.01 if prop(c, 'state') else 1e9)
            i = (V['p1'] - V['p2']) / r
            I = {'p1': i, 'p2': -i}
            if ty == 'Switch':
                extra['closed'] = bool(prop(c, 'state'))
        elif ty == 'Capacitor':
            cap = max(float(prop(c, 'capacitance')), 1e-18)
            vc = V['p1'] - V['p2']
            i = cap / h * (vc - st[cid]['v'])
            st[cid]['v'] = vc
            I = {'p1': i, 'p2': -i}
            extra = {'charge': cap * vc, 'energy': 0.5 * cap * vc * vc}
        elif ty == 'Inductor':
            ind = max(float(prop(c, 'inductance')), 1e-15)
            i = st[cid]['i'] + h / ind * (V['p1'] - V['p2'])
            st[cid]['i'] = i
            I = {'p1': i, 'p2': -i}
            extra = {'flux': ind * i, 'energy': 0.5 * ind * i * i}
        elif ty in ('DCVoltageSource', 'ACVoltageSource'):
            j = float(x[net.n + net.vsources.index(c)])
            I = {'pos': j, 'neg': -j}
            if ty == 'ACVoltageSource':
                extra['instantaneous_voltage'] = source_voltage(c, t)
        elif ty == 'DCCurrentSource':
            cur = float(prop(c, 'current'))
            I = {'pos': -cur, 'neg': cur}
        elif ty in ('Diode', 'LED'):
            vd = V['anode'] - V['cathode']
            vf = float(prop(c, 'forward_voltage'))
            i = (vd - vf) / R_ON if st[cid]['on'] else G_OFF * vd
            I = {'anode': i, 'cathode': -i}
            imax = float(prop(c, 'max_current'))
            extra = {'conducting': bool(st[cid]['on']) and i > 1e-6, 'over_current': i > imax}
            if ty == 'LED':
                extra['brightness'] = min(1.0, max(0.0, i) / imax) if imax > 0 else 0.0
        elif ty == 'BJT':
            s, beta, vth, vsat = _bjt(c)
            vbe = s * (V['base'] - V['emitter'])
            vce = s * (V['collector'] - V['emitter'])
            region = st[cid]['region']
            if region == 'cutoff':
                ib, ic = G_OFF * vbe, 0.0
            elif region == 'active':
                ib = (vbe - vth) / R_BE
                ic = beta * ib
            else:
                ib = (vbe - vth) / R_BE
                ic = (vce - vsat) / R_SAT
            ic += G_OFF * vce
            I = {'collector': s * ic, 'base': s * ib, 'emitter': -s * (ic + ib)}
            extra = {'region': region,
                     'over_current': abs(ic) > float(prop(c, 'max_collector_current'))}
        elif ty == 'Ground':
            I = {'gnd': 0.0}
        if ty != 'Ground':
            ground_sum += sum(I[term] for term, k in nd.items() if k == 0)
        power = sum(V[term] * I[term] for term in I)
        out[cid] = {'type': ty, 'voltages': V, 'currents': I, 'power': power, **extra}
    grounds = [c['id'] for c in net.components if c['type'] == 'Ground']
    if grounds:  # the ground symbol absorbs whatever the reference node needs to satisfy KCL
        out[grounds[0]]['currents']['gnd'] = -ground_sum
    return out


class Transient:
    """Time-stepping simulation of one circuit (file-format dict)."""

    def __init__(self, circuit, max_step=DEFAULT_MAX_STEP, state=None):
        self.net = Netlist(circuit)
        self.state = state if state is not None else initial_state(self.net)
        self.max_step = max_step
        self.t = 0.0
        self.last = {}
        self.converged = True

    def advance(self, duration):
        """Integrate by `duration` seconds; return the readouts at the end."""
        h_lim = step_limit(self.net, self.max_step)
        nsub = max(1, int(math.ceil(duration / h_lim - 1e-9)))
        h = duration / nsub
        t0 = self.t
        for k in range(1, nsub + 1):
            t = t0 + k * h
            v, x, _, ok = solve_point(self.net, self.state, h, t)
            self.converged = self.converged and ok
            self.last = readouts(self.net, self.state, v, x, h, t)
            self.node_voltages = [float(a) for a in v]
        self.t = t0 + duration
        return self.last

    def run(self, frame, frames, probes):
        """Advance `frames` times by `frame` seconds; return {'t': [...], probe: [...]} where a probe is
        (component_id, 'v'|'i', terminal) -> terminal voltage or current into that terminal."""
        trace = {'t': []}
        for p in probes:
            trace['/'.join(p)] = []
        for _ in range(frames):
            r = self.advance(frame)
            trace['t'].append(self.t)
            for cid, kind, term in probes:
                trace['/'.join((cid, kind, term))].append(r[cid]['voltages' if kind == 'v' else 'currents'][term])
        return trace


__all__ = ['Transient', 'readouts', 'step_limit', 'DEFAULTS', 'DEFAULT_MAX_STEP']

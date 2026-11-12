"""
Circuit Simulator - transient analysis on top of the MNA engine (Qt-free)
------------------------------------------------------------------------
Transient(circuit).advance(T) integrates the circuit by T seconds in sub-steps no longer than max_step (default
10 us, and at most 1/50 of the period of any AC source), then returns per-component readouts. Steps are trapezoidal
(second order, ~1e-5 relative error at one RC time constant) except for BE_STEPS backward-Euler steps after every
discontinuity -- the start, any edit (call discontinuity()), and any step in which a diode/BJT changes region --
which damp the ringing the trapezoidal rule shows after a sudden change.
Mirrored in JS by web/static/circuit_engine.js (node-tested against fixtures made from this module).
"""

import math

from simulation.mna import (DEFAULTS, G_OFF, R_BE, R_CLOSED, R_ON, R_OPEN, R_SAT, RATINGS, Netlist, _bjt, initial_state, prop,
                            solve_point, source_voltage)

DEFAULT_MAX_STEP = 1e-5
BE_STEPS = 3


def _over(value, limit, unit, what):
    """Overload message if |value| exceeds the rating, else ''."""
    if limit is None or abs(value) <= float(limit):
        return ''
    return f'{what} {abs(value):.4g} {unit} > rating {float(limit):.4g} {unit}'


def step_limit(net, max_step=DEFAULT_MAX_STEP):
    """Largest allowed internal step: max_step, and 50 steps per period of every AC source."""
    h = max_step
    for c in net.components:
        if c['type'] == 'ACVoltageSource':
            f = abs(float(prop(c, 'frequency')))
            if f > 0:
                h = min(h, 1.0 / (50.0 * f))
    return h


def readouts(net, st, v, x, h, t, trap=False):
    """Per-component terminal voltages, currents INTO each terminal, absorbed power and extras.

    Also commits the capacitor voltages and inductor currents of this step into st.
    """
    out = {}
    ground_sum = 0.0
    for c in net.components:
        ty, nd, cid = c['type'], net.nodes[c['id']], c['id']
        V = {term: float(v[k]) for term, k in nd.items()}
        I, extra, over = {}, {}, ''
        if ty in ('Resistor', 'Switch'):
            r = max(float(prop(c, 'resistance')), 1e-6) if ty == 'Resistor' else (R_CLOSED if prop(c, 'state') else R_OPEN)
            i = (V['p1'] - V['p2']) / r
            I = {'p1': i, 'p2': -i}
            if ty == 'Switch':
                extra['closed'] = bool(prop(c, 'state'))
                over = _over(i, prop(c, 'max_current'), 'A', 'current')
            else:
                over = _over(i * (V['p1'] - V['p2']), prop(c, 'max_power'), 'W', 'power')
        elif ty == 'Capacitor':
            cap = max(float(prop(c, 'capacitance')), 1e-18)
            vc = V['p1'] - V['p2']
            if trap:
                i = 2.0 * cap / h * (vc - st[cid]['v']) - st[cid]['i']
            else:
                i = cap / h * (vc - st[cid]['v'])
            st[cid]['v'], st[cid]['i'] = vc, i
            over = _over(vc, prop(c, 'max_voltage'), 'V', 'voltage')
            I = {'p1': i, 'p2': -i}
            extra = {'charge': cap * vc, 'energy': 0.5 * cap * vc * vc}
        elif ty == 'Inductor':
            ind = max(float(prop(c, 'inductance')), 1e-15)
            vl = V['p1'] - V['p2']
            if trap:
                i = st[cid]['i'] + h / (2.0 * ind) * (vl + st[cid]['v'])
            else:
                i = st[cid]['i'] + h / ind * vl
            st[cid]['i'], st[cid]['v'] = i, vl
            over = _over(i, prop(c, 'max_current'), 'A', 'current')
            I = {'p1': i, 'p2': -i}
            extra = {'flux': ind * i, 'energy': 0.5 * ind * i * i}
        elif ty in ('DCVoltageSource', 'ACVoltageSource'):
            j = float(x[net.n + net.vsources.index(c)])
            I = {'pos': j, 'neg': -j}
            over = _over(j, prop(c, 'max_current'), 'A', 'current')
            if ty == 'ACVoltageSource':
                extra['instantaneous_voltage'] = source_voltage(c, t)
        elif ty == 'DCCurrentSource':
            cur = float(prop(c, 'current'))
            I = {'pos': -cur, 'neg': cur}
            over = _over(V['pos'] - V['neg'], prop(c, 'max_voltage'), 'V', 'voltage')
        elif ty in ('Diode', 'LED'):
            vd = V['anode'] - V['cathode']
            vf = float(prop(c, 'forward_voltage'))
            i = (vd - vf) / R_ON if st[cid]['on'] else G_OFF * vd
            I = {'anode': i, 'cathode': -i}
            imax = float(prop(c, 'max_current'))
            extra = {'conducting': bool(st[cid]['on']) and i > 1e-6}
            over = _over(i, imax, 'A', 'current')
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
            extra = {'region': region}
            over = _over(ic, prop(c, 'max_collector_current'), 'A', 'collector current')
        elif ty == 'Ground':
            I = {'gnd': 0.0}
        if over:
            extra['overload'] = over
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
        self.be_left = BE_STEPS
        self.iterations = 0  # linear solves so far (sub-steps x region passes)

    def discontinuity(self):
        """The circuit changed suddenly (switch flipped, value edited): take backward-Euler steps next."""
        self.be_left = BE_STEPS

    def advance(self, duration):
        """Integrate by `duration` seconds; return the readouts at the end."""
        h_lim = step_limit(self.net, self.max_step)
        nsub = max(1, int(math.ceil(duration / h_lim - 1e-9)))
        h = duration / nsub
        t0 = self.t
        for k in range(1, nsub + 1):
            t = t0 + k * h
            trap = self.be_left <= 0
            v, x, iters, ok = solve_point(self.net, self.state, h, t, trap)
            self.iterations += iters
            self.converged = self.converged and ok
            self.last = readouts(self.net, self.state, v, x, h, t, trap)
            self.node_voltages = [float(a) for a in v]
            if iters > 1:  # a diode/BJT changed region: a kink in the waveform
                self.be_left = BE_STEPS
            elif not trap:
                self.be_left -= 1
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


__all__ = ['Transient', 'readouts', 'step_limit', 'DEFAULTS', 'RATINGS', 'DEFAULT_MAX_STEP', 'BE_STEPS']

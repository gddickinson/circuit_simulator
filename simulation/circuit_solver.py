"""
Circuit Simulator - Circuit Solver
--------------------------------
Binds the Modified Nodal Analysis engine (simulation/mna.py + simulation/transient.py) to a CircuitSimulator.

Each call to solve_circuit() advances the circuit by simulator.time_step (one GUI frame) in backward-Euler
sub-steps, then writes node voltages and every component's state (terminal voltages, currents INTO each terminal,
absorbed power, plus conducting/brightness/region/charge/flux/energy) back into the simulator, so the GUI panels
read a consistent solution. Dynamic state between frames (capacitor voltage, inductor current, diode/BJT region)
is kept in the components' own state dicts, so reset_simulation() (component._init_state) starts from rest.
"""

import json
import logging
import time

from simulation.mna import CircuitError
from simulation.transient import Transient

logger = logging.getLogger(__name__)


def circuit_dict(simulator):
    """The simulator's components in the saved-file format the MNA engine reads."""
    return {'components': {cid: {'id': cid, 'type': type(c).__name__, 'properties': c.properties,
                                 'connected_to': c.connected_to}
                           for cid, c in simulator.components.items()}}


def dynamic_state(simulator, net):
    """Engine state (capacitor v, inductor i, diode on, BJT region) read from the components' state dicts."""
    st = {}
    for comp in net.components:
        c = simulator.components[comp['id']]
        volts, amps = c.state.get('voltages', {}), c.state.get('currents', {})
        if comp['type'] == 'Capacitor':
            st[c.id] = {'v': float(volts.get('p1', 0.0)) - float(volts.get('p2', 0.0)), 'i': float(amps.get('p1', 0.0))}
        elif comp['type'] == 'Inductor':
            st[c.id] = {'i': float(amps.get('p1', 0.0)), 'v': float(volts.get('p1', 0.0)) - float(volts.get('p2', 0.0))}
        elif comp['type'] in ('Diode', 'LED'):
            st[c.id] = {'on': bool(c.state.get('_on', c.state.get('conducting', False)))}
        elif comp['type'] == 'BJT':
            st[c.id] = {'region': c.state.get('region', 'cutoff')}
    return st


class CircuitSolver:
    """Solver for circuit analysis using Modified Nodal Analysis (MNA)."""

    def __init__(self, simulator):
        """Initialize the circuit solver and bind it to the simulator.

        Args:
            simulator: CircuitSimulator instance
        """
        self.simulator = simulator
        self.last_error = None
        self._signature = None   # circuit as last solved: a change (switch toggled, value edited) is a discontinuity
        self._be_left = 0
        self.simulator.solve_circuit = self.solve_circuit

    def solve_circuit(self):
        """Advance the circuit by one simulator time step and store the solution in the components."""
        start_time = time.time()
        sim = self.simulator
        if not sim.components:
            return {'iterations': 0, 'node_update_time': 0.0}
        circuit = circuit_dict(sim)
        signature = json.dumps(circuit, sort_keys=True, default=str)
        tr = Transient(circuit)
        tr.state = dynamic_state(sim, tr.net)
        tr.t = sim.simulation_time
        if signature == self._signature and sim.simulation_time > 0:
            tr.be_left = self._be_left
        else:
            tr.discontinuity()
        self._signature = signature
        try:
            results = tr.advance(sim.time_step)
        except CircuitError as exc:
            self.last_error = str(exc)
            logger.warning(f"Circuit cannot be solved: {exc}")
            return {'iterations': 0, 'node_update_time': time.time() - start_time, 'error': str(exc)}
        self.last_error = None
        self._be_left = tr.be_left
        if not tr.converged:
            logger.warning("Diode/BJT operating regions did not settle in this step")

        for cid, res in results.items():
            comp = sim.components[cid]
            for key, value in res.items():
                if key == 'type':
                    continue
                if isinstance(value, dict):
                    comp.state.setdefault(key, {}).update(value)
                else:
                    comp.state[key] = value
            if res['type'] in ('Diode', 'LED'):
                comp.state['_on'] = tr.state[cid]['on']
            if 'overload' not in res:
                comp.state.pop('overload', None)
            if res['type'] == 'Resistor':  # same heating model as Resistor.calculate()
                p_max = float(comp.get_property('max_power', 0.25))
                comp.state['temperature'] = 25.0 + (res['power'] / p_max) * 50.0 if res['power'] > 0 else 25.0

        for node in sim.nodes.values():
            for comp, conn in node.get_connected_components():
                if comp.id in results:
                    node.voltage = results[comp.id]['voltages'][conn]
                    break

        return {'iterations': tr.iterations, 'node_update_time': time.time() - start_time, 'states_updated': True,
                'converged': tr.converged}

    def solve_circuit_nonlinear(self):
        """Diodes and BJTs are piecewise linear and already iterated inside solve_circuit()."""
        return self.solve_circuit()

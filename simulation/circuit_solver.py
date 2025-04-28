"""
Circuit Simulator - Circuit Solver
--------------------------------
This module provides the mathematical solver for circuit analysis.
It uses Modified Nodal Analysis (MNA) to solve for node voltages and branch currents.
"""

import time
import logging
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

import config

logger = logging.getLogger(__name__)


class CircuitSolver:
    """Solver for circuit analysis using Modified Nodal Analysis (MNA)."""

    def __init__(self, simulator):
        """Initialize the circuit solver.

        Args:
            simulator: CircuitSimulator instance
        """
        self.simulator = simulator
        self.max_iterations = config.MAX_ITERATIONS
        self.convergence_threshold = config.CONVERGENCE_THRESHOLD

        # Bind the solver to the simulator
        self.simulator.solve_circuit = self.solve_circuit

    def solve_circuit(self):
        """Solve the circuit using Modified Nodal Analysis."""
        # Start timing
        start_time = time.time()

        # If there's no ground node, we can't solve the circuit
        if not self.simulator.ground_node:
            logger.warning("No ground node found - cannot solve circuit")
            return {'iterations': 0, 'node_update_time': 0.0}
        else:
            logger.info(f"Ground node: {self.simulator.ground_node.id}")

        # Set ground node voltage to 0V
        self.simulator.ground_node.voltage = 0.0


        # IMPORTANT: Add this debugging to understand the connections
        logger.info("Solving circuit...")
        logger.info(f"Number of components: {len(self.simulator.components)}")
        logger.info(f"Number of nodes: {len(self.simulator.nodes)}")
        logger.info(f"Ground node: {self.simulator.ground_node.id if self.simulator.ground_node else 'None'}")


        # Process voltage sources first to set initial node voltages
        for component_id, component in self.simulator.components.items():
            if component.__class__.__name__ in ['DCVoltageSource', 'ACVoltageSource']:
                # Get the nodes
                node_pos = self.simulator.get_node_for_component(component_id, 'pos')
                node_neg = self.simulator.get_node_for_component(component_id, 'neg')

                # Get the voltage
                if component.__class__.__name__ == 'DCVoltageSource':
                    voltage = component.get_property('voltage', config.DEFAULT_VOLTAGE)
                    logger.info(f"DC Source {component_id[:8]}...: voltage={voltage}V")

                    # Set node voltages
                    if node_pos:
                        node_pos.voltage = voltage
                        logger.info(f"Setting {node_pos.id} voltage to {voltage}V")

                    if node_neg:
                        node_neg.voltage = 0.0
                        logger.info(f"Setting {node_neg.id} voltage to 0.0V")

        # Now propagate voltages to connected components
        # For each node, we need to set the voltages of all connected components
        for node_id, node in self.simulator.nodes.items():
            node_voltage = node.voltage
            logger.info(f"Node {node_id} has voltage {node_voltage}V")

            # Set this voltage for all component connections at this node
            for component, connection_name in node.get_connected_components():
                if hasattr(component, 'state') and 'voltages' in component.state:
                    component.state['voltages'][connection_name] = node_voltage
                    logger.info(f"  Setting {component.__class__.__name__} {component.id[:8]}... {connection_name} to {node_voltage}V")

        # Process diodes and LEDs to check forward bias
        for component_id, component in self.simulator.components.items():
            if component.__class__.__name__ in ['Diode', 'LED']:
                v_anode = component.state.get('voltages', {}).get('anode', 0.0)
                v_cathode = component.state.get('voltages', {}).get('cathode', 0.0)
                voltage_drop = v_anode - v_cathode
                forward_voltage = component.get_property('forward_voltage', 0.7 if component.__class__.__name__ == 'Diode' else 2.0)

                logger.info(f"{component.__class__.__name__} {component_id[:8]}...: anode={v_anode:.2f}V, cathode={v_cathode:.2f}V, drop={voltage_drop:.2f}V, threshold={forward_voltage:.2f}V")

                # Check if forward biased
                if voltage_drop > forward_voltage * 0.9:
                    # Forward biased - calculate current
                    resistance = 0.1  # Small resistance when conducting
                    current = (voltage_drop - forward_voltage) / resistance
                    max_current = component.get_property('max_current', 1.0)

                    if current > max_current:
                        current = max_current

                    logger.info(f"  CONDUCTING: current={current*1000:.2f}mA")

                    # Update component state
                    component.state['currents'] = {'anode': current, 'cathode': -current}
                    component.state['conducting'] = True

                    # For LED, update brightness
                    if component.__class__.__name__ == 'LED':
                        max_led_current = component.get_property('max_current', 0.02)
                        brightness = min(1.0, current / max_led_current)
                        component.state['brightness'] = brightness
                        logger.info(f"  LED brightness: {brightness:.2f}")
                else:
                    # Not conducting
                    logger.info(f"  NOT CONDUCTING: insufficient voltage")
                    component.state['currents'] = {'anode': 0.0, 'cathode': 0.0}
                    component.state['conducting'] = False
                    if component.__class__.__name__ == 'LED':
                        component.state['brightness'] = 0.0

        # Log all node voltages after solving
        logger.info("Final node voltages:")
        for node_id, node in self.simulator.nodes.items():
            logger.info(f"  Node {node_id}: {node.voltage}V")

        # Return stats
        return {
            'iterations': 1,
            'node_update_time': time.time() - start_time
        }

    def _add_resistor_to_mna(self, resistor, node_indices, G, b):
        """Add a resistor to the MNA matrices.

        Args:
            resistor: Resistor component
            node_indices: Dictionary mapping node IDs to indices
            G: Conductance matrix to update
            b: Right-hand side vector to update
        """
        # Get the resistor value
        resistance = resistor.get_property('resistance', config.DEFAULT_RESISTANCE)

        # Calculate conductance (G = 1/R)
        conductance = 1.0 / resistance if resistance > 0 else 0.0

        # Get the nodes connected to the resistor
        node_p1 = self.simulator.get_node_for_component(resistor.id, 'p1')
        node_p2 = self.simulator.get_node_for_component(resistor.id, 'p2')

        # Skip if either node is not found
        if not node_p1 or not node_p2:
            return

        # If either node is ground, we handle it differently
        if node_p1 == self.simulator.ground_node:
            # p1 is ground, only p2 contributes
            if node_p2.id in node_indices:
                idx_p2 = node_indices[node_p2.id]
                G[idx_p2, idx_p2] += conductance
        elif node_p2 == self.simulator.ground_node:
            # p2 is ground, only p1 contributes
            if node_p1.id in node_indices:
                idx_p1 = node_indices[node_p1.id]
                G[idx_p1, idx_p1] += conductance
        else:
            # Neither node is ground, both contribute
            if node_p1.id in node_indices and node_p2.id in node_indices:
                idx_p1 = node_indices[node_p1.id]
                idx_p2 = node_indices[node_p2.id]

                # Update the conductance matrix
                G[idx_p1, idx_p1] += conductance
                G[idx_p2, idx_p2] += conductance
                G[idx_p1, idx_p2] -= conductance
                G[idx_p2, idx_p1] -= conductance

    def solve_circuit_nonlinear(self):
        """Solve a nonlinear circuit using Newton-Raphson iteration.

        For circuits with nonlinear elements like diodes and transistors,
        we use Newton-Raphson iteration to find the solution.

        Returns:
            Dictionary of solution statistics
        """
        # This is a placeholder for a more advanced solver
        # The nonlinear solver would use Newton-Raphson iteration to solve the circuit

        # For now, we just use the linear solver
        return self.solve_circuit()



    def _add_capacitor_to_mna(self, capacitor, node_indices, G, b):
        """Add a capacitor to the MNA matrices.

        For DC analysis, a capacitor is treated as an open circuit.
        For transient analysis, a capacitor is modeled using the companion model.

        Args:
            capacitor: Capacitor component
            node_indices: Dictionary mapping node IDs to indices
            G: Conductance matrix to update
            b: Right-hand side vector to update
        """
        # For DC analysis, a capacitor is an open circuit
        # For transient analysis, we would use a companion model

        # Get the capacitor value
        capacitance = capacitor.get_property('capacitance', config.DEFAULT_CAPACITANCE)

        # Get the time step
        time_step = self.simulator.time_step

        # Calculate the equivalent conductance for the companion model
        conductance = capacitance / time_step

        # Get the nodes connected to the capacitor
        node_p1 = self.simulator.get_node_for_component(capacitor.id, 'p1')
        node_p2 = self.simulator.get_node_for_component(capacitor.id, 'p2')

        # Skip if either node is not found
        if not node_p1 or not node_p2:
            return

        # Get the current state of the capacitor
        voltages = capacitor.state.get('voltages', {})
        v_p1_prev = voltages.get('p1', 0.0)
        v_p2_prev = voltages.get('p2', 0.0)

        # Calculate the companion model current source value
        i_eq = conductance * (v_p1_prev - v_p2_prev)

        # If either node is ground, we handle it differently
        if node_p1 == self.simulator.ground_node:
            # p1 is ground, only p2 contributes
            if node_p2.id in node_indices:
                idx_p2 = node_indices[node_p2.id]
                G[idx_p2, idx_p2] += conductance
                b[idx_p2] -= i_eq
        elif node_p2 == self.simulator.ground_node:
            # p2 is ground, only p1 contributes
            if node_p1.id in node_indices:
                idx_p1 = node_indices[node_p1.id]
                G[idx_p1, idx_p1] += conductance
                b[idx_p1] += i_eq
        else:
            # Neither node is ground, both contribute
            if node_p1.id in node_indices and node_p2.id in node_indices:
                idx_p1 = node_indices[node_p1.id]
                idx_p2 = node_indices[node_p2.id]

                # Update the conductance matrix
                G[idx_p1, idx_p1] += conductance
                G[idx_p2, idx_p2] += conductance
                G[idx_p1, idx_p2] -= conductance
                G[idx_p2, idx_p1] -= conductance

                # Update the right-hand side
                b[idx_p1] += i_eq
                b[idx_p2] -= i_eq

    def _add_inductor_to_mna(self, inductor, node_indices, G, b):
        """Add an inductor to the MNA matrices.

        For DC analysis, an inductor is treated as a short circuit.
        For transient analysis, an inductor is modeled using the companion model.

        Args:
            inductor: Inductor component
            node_indices: Dictionary mapping node IDs to indices
            G: Conductance matrix to update
            b: Right-hand side vector to update
        """
        # For DC analysis, an inductor is a short circuit
        # For transient analysis, we would use a companion model

        # Get the inductor value
        inductance = inductor.get_property('inductance', config.DEFAULT_INDUCTANCE)

        # Get the time step
        time_step = self.simulator.time_step

        # Calculate the equivalent conductance for the companion model
        conductance = time_step / inductance if inductance > 0 else 1e6

        # Get the nodes connected to the inductor
        node_p1 = self.simulator.get_node_for_component(inductor.id, 'p1')
        node_p2 = self.simulator.get_node_for_component(inductor.id, 'p2')

        # Skip if either node is not found
        if not node_p1 or not node_p2:
            return

        # Get the current state of the inductor
        currents = inductor.state.get('currents', {})
        i_prev = currents.get('p1', 0.0)

        # Calculate the companion model voltage source value
        v_eq = i_prev / conductance

        # If either node is ground, we handle it differently
        if node_p1 == self.simulator.ground_node:
            # p1 is ground, only p2 contributes
            if node_p2.id in node_indices:
                idx_p2 = node_indices[node_p2.id]
                # In DC analysis, this is just a short to ground
                G[idx_p2, idx_p2] += conductance
                b[idx_p2] += i_prev
        elif node_p2 == self.simulator.ground_node:
            # p2 is ground, only p1 contributes
            if node_p1.id in node_indices:
                idx_p1 = node_indices[node_p1.id]
                # In DC analysis, this is just a short to ground
                G[idx_p1, idx_p1] += conductance
                b[idx_p1] -= i_prev
        else:
            # Neither node is ground, both contribute
            if node_p1.id in node_indices and node_p2.id in node_indices:
                idx_p1 = node_indices[node_p1.id]
                idx_p2 = node_indices[node_p2.id]

                # Update the conductance matrix
                G[idx_p1, idx_p1] += conductance
                G[idx_p2, idx_p2] += conductance
                G[idx_p1, idx_p2] -= conductance
                G[idx_p2, idx_p1] -= conductance

                # Update the right-hand side
                b[idx_p1] -= i_prev
                b[idx_p2] += i_prev



    def _add_ac_voltage_source_to_mna(self, voltage_source, node_indices, G, b):
        """Add an AC voltage source to the MNA matrices.

        Args:
            voltage_source: ACVoltageSource component
            node_indices: Dictionary mapping node IDs to indices
            G: Conductance matrix to update
            b: Right-hand side vector to update
        """
        # Get the voltage source parameters
        amplitude = voltage_source.get_property('amplitude', config.DEFAULT_VOLTAGE)
        frequency = voltage_source.get_property('frequency', config.DEFAULT_FREQUENCY)
        phase = voltage_source.get_property('phase', 0.0)  # Phase in degrees

        # Calculate the instantaneous voltage at this time
        simulation_time = self.simulator.simulation_time
        omega = 2 * np.pi * frequency
        phase_rad = np.radians(phase)
        voltage = amplitude * np.sin(omega * simulation_time + phase_rad)

        # Now treat it like a DC voltage source with this instantaneous voltage
        # Get the nodes connected to the voltage source
        node_pos = self.simulator.get_node_for_component(voltage_source.id, 'pos')
        node_neg = self.simulator.get_node_for_component(voltage_source.id, 'neg')

        # Skip if either node is not found
        if not node_pos or not node_neg:
            return

        # If either node is ground, we handle it differently
        if node_pos == self.simulator.ground_node:
            # pos is ground, only neg contributes
            if node_neg.id in node_indices:
                idx_neg = node_indices[node_neg.id]
                # Set the negative terminal to -V relative to ground
                G[idx_neg, idx_neg] += 1e9  # Very high conductance
                b[idx_neg] += -voltage * 1e9
        elif node_neg == self.simulator.ground_node:
            # neg is ground, only pos contributes
            if node_pos.id in node_indices:
                idx_pos = node_indices[node_pos.id]
                # Set the positive terminal to V relative to ground
                G[idx_pos, idx_pos] += 1e9  # Very high conductance
                b[idx_pos] += voltage * 1e9
        else:
            # Neither node is ground, both contribute
            if node_pos.id in node_indices and node_neg.id in node_indices:
                idx_pos = node_indices[node_pos.id]
                idx_neg = node_indices[node_neg.id]

                # Add voltage constraint: V_pos - V_neg = V
                G[idx_pos, idx_pos] += 1e9
                G[idx_neg, idx_neg] += 1e9
                G[idx_pos, idx_neg] -= 1e9
                G[idx_neg, idx_pos] -= 1e9

                b[idx_pos] += voltage * 1e9
                b[idx_neg] -= voltage * 1e9


    def _add_diode_to_mna(self, diode, node_indices, G, b):
        """Add a diode to the MNA matrices."""
        # Get the diode parameters
        forward_voltage = diode.get_property('forward_voltage', 0.7)

        # LED typically has higher forward voltage
        if diode.__class__.__name__ == 'LED':
            forward_voltage = diode.get_property('forward_voltage', 2.0)

        # Get the current state of the diode
        voltages = diode.state.get('voltages', {})
        v_anode = voltages.get('anode', 0.0)
        v_cathode = voltages.get('cathode', 0.0)
        voltage_drop = v_anode - v_cathode

        # Determine if the diode is conducting based on voltage
        # This helps bootstrap the solution
        conducting = voltage_drop > forward_voltage * 0.9  # Use 90% threshold for numerical stability

        # Get the nodes connected to the diode
        node_anode = self.simulator.get_node_for_component(diode.id, 'anode')
        node_cathode = self.simulator.get_node_for_component(diode.id, 'cathode')

        # Add debug logging for MNA matrix construction
        logger.debug(f"Adding {diode.__class__.__name__} {diode.id} to MNA matrix: conducting={conducting}")


        # Skip if either node is not found
        if not node_anode or not node_cathode:
            return

        # Determine the resistance based on the diode state
        # If conducting, use a low resistance and voltage source model
        # If not conducting, use a high resistance
        if conducting:
            # Conducting diode - low resistance plus voltage source
            conductance = 10.0  # High conductance (0.1 ohm)

            # Handle nodes like a voltage source with value = forward_voltage
            if node_anode == self.simulator.ground_node:
                # anode is ground, only cathode contributes
                if node_cathode.id in node_indices:
                    idx_cathode = node_indices[node_cathode.id]
                    # Cathode is at -forward_voltage relative to ground
                    G[idx_cathode, idx_cathode] += conductance
                    b[idx_cathode] += -forward_voltage * conductance
            elif node_cathode == self.simulator.ground_node:
                # cathode is ground, only anode contributes
                if node_anode.id in node_indices:
                    idx_anode = node_indices[node_anode.id]
                    # Anode is at forward_voltage relative to ground
                    G[idx_anode, idx_anode] += conductance
                    b[idx_anode] += forward_voltage * conductance
            else:
                # Neither node is ground, both contribute
                if node_anode.id in node_indices and node_cathode.id in node_indices:
                    idx_anode = node_indices[node_anode.id]
                    idx_cathode = node_indices[node_cathode.id]

                    # Add the diode constraints
                    G[idx_anode, idx_anode] += conductance
                    G[idx_cathode, idx_cathode] += conductance
                    G[idx_anode, idx_cathode] -= conductance
                    G[idx_cathode, idx_anode] -= conductance

                    b[idx_anode] += forward_voltage * conductance
                    b[idx_cathode] -= forward_voltage * conductance
        else:
            # Non-conducting diode - high resistance
            conductance = 1e-9  # Very low conductance (1 Gohm)

            # Add like a resistor
            if node_anode == self.simulator.ground_node:
                # anode is ground, only cathode contributes
                if node_cathode.id in node_indices:
                    idx_cathode = node_indices[node_cathode.id]
                    G[idx_cathode, idx_cathode] += conductance
            elif node_cathode == self.simulator.ground_node:
                # cathode is ground, only anode contributes
                if node_anode.id in node_indices:
                    idx_anode = node_indices[node_anode.id]
                    G[idx_anode, idx_anode] += conductance
            else:
                # Neither node is ground, both contribute
                if node_anode.id in node_indices and node_cathode.id in node_indices:
                    idx_anode = node_indices[node_anode.id]
                    idx_cathode = node_indices[node_cathode.id]

                    G[idx_anode, idx_anode] += conductance
                    G[idx_cathode, idx_cathode] += conductance
                    G[idx_anode, idx_cathode] -= conductance
                    G[idx_cathode, idx_anode] -= conductance

    def _add_bjt_to_mna(self, bjt, node_indices, G, b):
        """Add a BJT to the MNA matrices.

        For linear analysis, a BJT is approximated using the Ebers-Moll model
        with resistances based on its current operating region.

        Args:
            bjt: BJT component
            node_indices: Dictionary mapping node IDs to indices
            G: Conductance matrix to update
            b: Right-hand side vector to update
        """
        # Get the BJT parameters
        gain = bjt.get_property('gain', 100)  # Beta (hFE)
        is_npn = bjt.get_property('type', 'npn') == 'npn'
        vbe_threshold = bjt.get_property('vbe_threshold', 0.7)  # Base-emitter threshold voltage

        # Get the current state of the BJT
        region = bjt.state.get('region', 'cutoff')

        # Get the nodes connected to the BJT
        node_collector = self.simulator.get_node_for_component(bjt.id, 'collector')
        node_base = self.simulator.get_node_for_component(bjt.id, 'base')
        node_emitter = self.simulator.get_node_for_component(bjt.id, 'emitter')

        # Skip if any node is not found
        if not node_collector or not node_base or not node_emitter:
            return

        # Determine the resistances based on the BJT region
        if region == 'cutoff':
            # Cutoff region - high resistances
            rbe = 1e9  # Base-emitter resistance (very high)
            rce = 1e9  # Collector-emitter resistance (very high)

            # No controlled source in cutoff region
            controlled_source_factor = 0.0
        elif region == 'saturation':
            # Saturation region - low resistances
            rbe = 100.0  # Base-emitter resistance (low)
            rce = 0.1   # Collector-emitter resistance (very low)

            # Controlled source in saturation is limited
            controlled_source_factor = 1.0
        else:  # region == 'active'
            # Active region - medium resistances
            rbe = 1000.0  # Base-emitter resistance (medium)
            rce = 1e6     # Collector-emitter resistance (high)

            # Controlled source in active region
            controlled_source_factor = gain

        # For PNP, swap some connections in the model
        if not is_npn:
            # For PNP, swap emitter and collector in the model
            node_collector, node_emitter = node_emitter, node_collector

        # Base-emitter junction
        if node_base == self.simulator.ground_node:
            # Base is ground, only emitter contributes
            if node_emitter.id in node_indices:
                idx_emitter = node_indices[node_emitter.id]
                G[idx_emitter, idx_emitter] += 1.0 / rbe
        elif node_emitter == self.simulator.ground_node:
            # Emitter is ground, only base contributes
            if node_base.id in node_indices:
                idx_base = node_indices[node_base.id]
                G[idx_base, idx_base] += 1.0 / rbe
        else:
            # Neither is ground, both contribute
            if node_base.id in node_indices and node_emitter.id in node_indices:
                idx_base = node_indices[node_base.id]
                idx_emitter = node_indices[node_emitter.id]

                G[idx_base, idx_base] += 1.0 / rbe
                G[idx_emitter, idx_emitter] += 1.0 / rbe
                G[idx_base, idx_emitter] -= 1.0 / rbe
                G[idx_emitter, idx_base] -= 1.0 / rbe

        # Collector-emitter controlled source (ic = beta * ib)
        # This is approximated using a resistance and voltage source
        if controlled_source_factor > 0:
            # Get the base current
            ib = bjt.state.get('currents', {}).get('base', 0.0)

            # Calculate the collector current from the controlled source
            ic = controlled_source_factor * ib

            # Add this as a current source between collector and emitter
            if node_collector != self.simulator.ground_node and node_collector.id in node_indices:
                idx_collector = node_indices[node_collector.id]
                b[idx_collector] -= ic  # Current flowing out of collector

            if node_emitter != self.simulator.ground_node and node_emitter.id in node_indices:
                idx_emitter = node_indices[node_emitter.id]
                b[idx_emitter] += ic  # Current flowing into emitter

        # Collector-emitter resistance (output resistance)
        if node_collector == self.simulator.ground_node:
            # Collector is ground, only emitter contributes
            if node_emitter.id in node_indices:
                idx_emitter = node_indices[node_emitter.id]
                G[idx_emitter, idx_emitter] += 1.0 / rce
        elif node_emitter == self.simulator.ground_node:
            # Emitter is ground, only collector contributes
            if node_collector.id in node_indices:
                idx_collector = node_indices[node_collector.id]
                G[idx_collector, idx_collector] += 1.0 / rce
        else:
            # Neither is ground, both contribute
            if node_collector.id in node_indices and node_emitter.id in node_indices:
                idx_collector = node_indices[node_collector.id]
                idx_emitter = node_indices[node_emitter.id]

                G[idx_collector, idx_collector] += 1.0 / rce
                G[idx_emitter, idx_emitter] += 1.0 / rce
                G[idx_collector, idx_emitter] -= 1.0 / rce
                G[idx_emitter, idx_collector] -= 1.0 / rce

    def _add_switch_to_mna(self, switch, node_indices, G, b):
        """Add a switch to the MNA matrices.

        Args:
            switch: Switch component
            node_indices: Dictionary mapping node IDs to indices
            G: Conductance matrix to update
            b: Right-hand side vector to update
        """
        # Get the switch state
        closed = switch.state.get('closed', False)

        # Get the nodes connected to the switch
        node_p1 = self.simulator.get_node_for_component(switch.id, 'p1')
        node_p2 = self.simulator.get_node_for_component(switch.id, 'p2')

        # Skip if either node is not found
        if not node_p1 or not node_p2:
            return

        # Determine the resistance based on the switch state
        if closed:
            # Closed switch - low resistance
            resistance = 0.01  # Small but non-zero resistance
        else:
            # Open switch - high resistance
            resistance = 1e9  # 1 Gohm

        # Calculate conductance
        conductance = 1.0 / resistance

        # Add the switch like a resistor
        if node_p1 == self.simulator.ground_node:
            # p1 is ground, only p2 contributes
            if node_p2.id in node_indices:
                idx_p2 = node_indices[node_p2.id]
                G[idx_p2, idx_p2] += conductance
        elif node_p2 == self.simulator.ground_node:
            # p2 is ground, only p1 contributes
            if node_p1.id in node_indices:
                idx_p1 = node_indices[node_p1.id]
                G[idx_p1, idx_p1] += conductance
        else:
            # Neither node is ground, both contribute
            if node_p1.id in node_indices and node_p2.id in node_indices:
                idx_p1 = node_indices[node_p1.id]
                idx_p2 = node_indices[node_p2.id]

                G[idx_p1, idx_p1] += conductance
                G[idx_p2, idx_p2] += conductance
                G[idx_p1, idx_p2] -= conductance
                G[idx_p2, idx_p1] -= conductance

    def _add_dc_current_source_to_mna(self, current_source, node_indices, G, b):
        """Add a DC current source to the MNA matrices.

        Args:
            current_source: DCCurrentSource component
            node_indices: Dictionary mapping node IDs to indices
            G: Conductance matrix to update
            b: Right-hand side vector to update
        """
        # Get the current source value
        current = current_source.get_property('current', config.DEFAULT_CURRENT)

        # Get the nodes connected to the current source
        node_pos = self.simulator.get_node_for_component(current_source.id, 'pos')
        node_neg = self.simulator.get_node_for_component(current_source.id, 'neg')

        # Skip if either node is not found
        if not node_pos or not node_neg:
            return

        # Count the number of connections at each terminal
        num_pos_connections = 0
        num_neg_connections = 0

        if 'pos' in current_source.connected_to:
            num_pos_connections = len(current_source.connected_to['pos'])
        if 'neg' in current_source.connected_to:
            num_neg_connections = len(current_source.connected_to['neg'])

        # If there are multiple connections, distribute the current
        # This is a simple equal distribution model
        # A more accurate model would consider the resistance of each path
        pos_current_per_connection = current
        neg_current_per_connection = -current

        # Current flows out of pos and into neg
        # Add the current contribution to the right-hand side
        if node_pos != self.simulator.ground_node and node_pos.id in node_indices:
            idx_pos = node_indices[node_pos.id]
            b[idx_pos] -= pos_current_per_connection  # Current flowing out of the node is negative

        if node_neg != self.simulator.ground_node and node_neg.id in node_indices:
            idx_neg = node_indices[node_neg.id]
            b[idx_neg] += neg_current_per_connection  # Current flowing into the node is positive

    def _add_dc_voltage_source_to_mna(self, voltage_source, node_indices, G, b):
        """Add a DC voltage source to the MNA matrices.

        Args:
            voltage_source: DCVoltageSource component
            node_indices: Dictionary mapping node IDs to indices
            G: Conductance matrix to update
            b: Right-hand side vector to update
        """
        # Get the voltage source value
        voltage = voltage_source.get_property('voltage', config.DEFAULT_VOLTAGE)

        # Get the nodes connected to the voltage source
        node_pos = self.simulator.get_node_for_component(voltage_source.id, 'pos')
        node_neg = self.simulator.get_node_for_component(voltage_source.id, 'neg')

        # Skip if either node is not found
        if not node_pos or not node_neg:
            return

        # For voltage sources, we don't need to handle multiple connections differently
        # The voltage constraint applies to the nodes, and all connections to those nodes
        # will have the same voltage

        # If either node is ground, we handle it differently
        if node_pos == self.simulator.ground_node:
            # pos is ground, only neg contributes
            if node_neg.id in node_indices:
                idx_neg = node_indices[node_neg.id]
                # Set the negative terminal to -V relative to ground
                G[idx_neg, idx_neg] += 1e9  # Very high conductance
                b[idx_neg] += -voltage * 1e9
        elif node_neg == self.simulator.ground_node:
            # neg is ground, only pos contributes
            if node_pos.id in node_indices:
                idx_pos = node_indices[node_pos.id]
                # Set the positive terminal to V relative to ground
                G[idx_pos, idx_pos] += 1e9  # Very high conductance
                b[idx_pos] += voltage * 1e9
        else:
            # Neither node is ground, both contribute
            if node_pos.id in node_indices and node_neg.id in node_indices:
                idx_pos = node_indices[node_pos.id]
                idx_neg = node_indices[node_neg.id]

                # Add voltage constraint: V_pos - V_neg = V
                # This is done by adding a high conductance between the nodes
                # and a current source equal to the voltage times that conductance
                G[idx_pos, idx_pos] += 1e9
                G[idx_neg, idx_neg] += 1e9
                G[idx_pos, idx_neg] -= 1e9
                G[idx_neg, idx_pos] -= 1e9

                b[idx_pos] += voltage * 1e9
                b[idx_neg] -= voltage * 1e9

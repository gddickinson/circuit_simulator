"""
Circuit Simulator - Active Components
-----------------------------------
This module defines active electronic components such as voltage and current sources,
transistors, diodes, etc.
"""

import math
import logging
import numpy as np

from components.base_component import BaseComponent
import config

logger = logging.getLogger(__name__)


class DCVoltageSource(BaseComponent):
    """DC Voltage source component."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a DC voltage source.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)
        self.size = (2, 3)  # Size in grid cells

    def _init_connections(self):
        """Initialize the connection points."""
        # Define connection points relative to component position
        self.connections = {
            'pos': (0, 1.5),   # Positive terminal (top)
            'neg': (0, -1.5)   # Negative terminal (bottom)
        }

    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'pos': 0.0, 'neg': 0.0},
            'currents': {'pos': 0.0, 'neg': 0.0},
            'power': 0.0
        }

    def calculate(self, simulator, time_step):
        """Calculate the voltage source state for the current time step."""
        # Get component values
        voltage = self.get_property('voltage', config.DEFAULT_VOLTAGE)
        max_current = self.get_property('max_current', 1.0)

        # Get connected nodes
        node_pos = simulator.get_node_for_component(self.id, 'pos')
        node_neg = simulator.get_node_for_component(self.id, 'neg')

        # Log the nodes
        logger.info(f"DCVoltageSource {self.id}: pos_node={node_pos.id if node_pos else 'None'}, neg_node={node_neg.id if node_neg else 'None'}")

        # For a voltage source, we set the voltages directly
        v_pos = voltage
        v_neg = 0.0

        # If we have nodes, set their voltages directly
        if node_pos:
            node_pos.voltage = v_pos
            logger.info(f"Setting pos node voltage to {v_pos}V")
        if node_neg:
            node_neg.voltage = v_neg
            logger.info(f"Setting neg node voltage to {v_neg}V")

        # Get current flowing through the source
        current = 0.0
        if node_pos and 'currents' in self.state:
            current = self.state['currents'].get('pos', 0.0)

        # Apply current limiting if needed
        if abs(current) > max_current:
            current = max_current if current > 0 else -max_current

        # Calculate power
        power = voltage * current

        # Update the state
        state_updates = {
            'voltages': {'pos': v_pos, 'neg': v_neg},
            'currents': {'pos': current, 'neg': -current},
            'power': power
        }

        logger.info(f"DCVoltageSource state: v_pos={v_pos}V, v_neg={v_neg}V, current={current}A")

        return state_updates

    def apply(self, state_updates):
        """Apply state updates to the component.

        Args:
            state_updates: Dictionary of state updates
        """
        for category, values in state_updates.items():
            if category in self.state:
                if isinstance(values, dict):
                    # Update nested dictionary
                    for key, value in values.items():
                        self.state[category][key] = value
                else:
                    # Update direct value
                    self.state[category] = values


class ACVoltageSource(BaseComponent):
    """AC Voltage source component."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize an AC voltage source.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)
        self.size = (2, 3)  # Size in grid cells

        # Initial simulation time
        self.simulation_time = 0.0

    def _init_connections(self):
        """Initialize the connection points."""
        # Define connection points relative to component position
        self.connections = {
            'pos': (0, 1.5),   # Positive terminal (top)
            'neg': (0, -1.5)   # Negative terminal (bottom)
        }

    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'pos': 0.0, 'neg': 0.0},
            'currents': {'pos': 0.0, 'neg': 0.0},
            'power': 0.0,
            'instantaneous_voltage': 0.0,
            'time': 0.0
        }

    def calculate(self, simulator, time_step):
        """Calculate the AC voltage source state for the current time step.

        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds

        Returns:
            Dictionary of updated state values
        """
        # Get component values
        amplitude = self.get_property('amplitude', config.DEFAULT_VOLTAGE)
        frequency = self.get_property('frequency', config.DEFAULT_FREQUENCY)
        phase = self.get_property('phase', 0.0)  # Phase in degrees
        max_current = self.get_property('max_current', 1.0)

        # Update simulation time
        self.simulation_time += time_step

        # Calculate angular frequency (omega)
        omega = 2 * math.pi * frequency

        # Calculate instantaneous voltage: v(t) = A * sin(ωt + φ)
        phase_rad = math.radians(phase)
        voltage = amplitude * math.sin(omega * self.simulation_time + phase_rad)

        # For an AC source, we set the voltages directly
        v_pos = voltage
        v_neg = 0.0

        # Calculate total current through the voltage source
        # Sum currents from all components connected to positive terminal
        current = 0.0
        node_pos = simulator.get_node_for_component(self.id, 'pos')
        if node_pos:
            for component, conn_name in node_pos.get_connected_components():
                if component.id != self.id:  # Skip self
                    conn_current = component.get_current(conn_name)
                    if conn_current is not None:
                        current -= conn_current  # Negate because current flows out of voltage source

        # Apply current limiting if needed
        if abs(current) > max_current:
            current = max_current if current > 0 else -max_current

        # Calculate power (instantaneous)
        power = voltage * current

        # Update the state
        state_updates = {
            'voltages': {'pos': v_pos, 'neg': v_neg},
            'currents': {'pos': current, 'neg': -current},
            'power': power,
            'instantaneous_voltage': voltage,
            'time': self.simulation_time
        }

        return state_updates

    def apply(self, state_updates):
        """Apply state updates to the component.

        Args:
            state_updates: Dictionary of state updates
        """
        for category, values in state_updates.items():
            if category in self.state:
                if isinstance(values, dict):
                    # Update nested dictionary
                    for key, value in values.items():
                        self.state[category][key] = value
                else:
                    # Update direct value
                    self.state[category] = values


class DCCurrentSource(BaseComponent):
    """DC Current source component."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a DC current source.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)
        self.size = (2, 3)  # Size in grid cells

    def _init_connections(self):
        """Initialize the connection points."""
        # Define connection points relative to component position
        self.connections = {
            'pos': (0, 1.5),   # Positive terminal (top, current flows out)
            'neg': (0, -1.5)   # Negative terminal (bottom, current flows in)
        }

    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'pos': 0.0, 'neg': 0.0},
            'currents': {'pos': 0.0, 'neg': 0.0},
            'power': 0.0
        }

    def calculate(self, simulator, time_step):
        """Calculate the current source state for the current time step.

        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds

        Returns:
            Dictionary of updated state values
        """
        # Get component values
        current = self.get_property('current', config.DEFAULT_CURRENT)
        max_voltage = self.get_property('max_voltage', 12.0)

        # Get connected components
        node_pos = simulator.get_node_for_component(self.id, 'pos')
        node_neg = simulator.get_node_for_component(self.id, 'neg')

        # Get node voltages
        v_pos = node_pos.voltage if node_pos else 0.0
        v_neg = node_neg.voltage if node_neg else 0.0

        # Calculate voltage across the source
        voltage_drop = v_pos - v_neg

        # Check if voltage exceeds maximum (compliance voltage)
        if abs(voltage_drop) > max_voltage:
            # Current source becomes voltage limited
            voltage_drop = max_voltage if voltage_drop > 0 else -max_voltage
            v_pos = v_neg + voltage_drop

            # Calculate the total resistance of the circuit
            total_resistance = simulator.get_resistance_between(self.id, 'pos', 'neg')
            current = voltage_drop / total_resistance if total_resistance > 0 else 0.0

        # For multiple connections, current is divided among the connections
        # based on their relative resistances. For now, we'll use a simplified approach.
        num_pos_connections = 0
        num_neg_connections = 0

        if 'pos' in self.connected_to:
            num_pos_connections = len(self.connected_to['pos'])
        if 'neg' in self.connected_to:
            num_neg_connections = len(self.connected_to['neg'])

        # Calculate power
        power = voltage_drop * current

        # Update the state
        state_updates = {
            'voltages': {'pos': v_pos, 'neg': v_neg},
            'currents': {'pos': current, 'neg': -current},
            'power': power,
            'num_pos_connections': num_pos_connections,
            'num_neg_connections': num_neg_connections
        }

        return state_updates

    def apply(self, state_updates):
        """Apply state updates to the component.

        Args:
            state_updates: Dictionary of state updates
        """
        for category, values in state_updates.items():
            if category in self.state:
                if isinstance(values, dict):
                    # Update nested dictionary
                    for key, value in values.items():
                        self.state[category][key] = value
                else:
                    # Update direct value
                    self.state[category] = values


class Diode(BaseComponent):
    """Diode component."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a diode.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)
        self.size = (2, 1)  # Size in grid cells

    def _init_connections(self):
        """Initialize the connection points."""
        # Define connection points relative to component position
        self.connections = {
            'anode': (-1, 0),    # Anode (left)
            'cathode': (1, 0)    # Cathode (right)
        }

    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'anode': 0.0, 'cathode': 0.0},
            'currents': {'anode': 0.0, 'cathode': 0.0},
            'power': 0.0,
            'conducting': False
        }


    def calculate(self, simulator, time_step):
        """Calculate the diode state for the current time step."""
        # Get component values
        forward_voltage = self.get_property('forward_voltage', 0.7)
        max_current = self.get_property('max_current', 1.0)

        # Get connected nodes
        node_anode = simulator.get_node_for_component(self.id, 'anode')
        node_cathode = simulator.get_node_for_component(self.id, 'cathode')

        # Get node voltages
        v_anode = node_anode.voltage if node_anode else 0.0
        v_cathode = node_cathode.voltage if node_cathode else 0.0

        # Calculate voltage across the diode
        voltage_drop = v_anode - v_cathode

        # Log values
        logger.info(f"Diode {self.id} voltage: anode={v_anode:.3f}V, cathode={v_cathode:.3f}V, drop={voltage_drop:.3f}V")

        # Check if the diode is forward biased
        if voltage_drop > forward_voltage * 0.9:  # Slightly lower threshold for stability
            # Forward biased - conducting
            resistance = 0.1  # Small resistance when conducting
            current = (voltage_drop - forward_voltage) / resistance
            logger.info(f"Diode {self.id} is conducting ({voltage_drop:.3f}V > {forward_voltage:.3f}V)")

            # Limit current
            if current > max_current:
                current = max_current

            conducting = True
        else:
            # Not conducting
            logger.info(f"Diode {self.id} is NOT conducting ({voltage_drop:.3f}V < {forward_voltage:.3f}V)")
            current = 0.0
            conducting = False

        # Calculate power
        power = voltage_drop * current

        # Update the state
        state_updates = {
            'voltages': {'anode': v_anode, 'cathode': v_cathode},
            'currents': {'anode': current, 'cathode': -current},
            'power': power,
            'conducting': conducting
        }

        return state_updates

    def apply(self, state_updates):
        """Apply state updates to the component.

        Args:
            state_updates: Dictionary of state updates
        """
        for category, values in state_updates.items():
            if category in self.state:
                if isinstance(values, dict):
                    # Update nested dictionary
                    for key, value in values.items():
                        self.state[category][key] = value
                else:
                    # Update direct value
                    self.state[category] = values


class LED(Diode):
    """Light Emitting Diode component."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize an LED.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)
        self.size = (2, 1)  # Size in grid cells

    def _init_state(self):
        """Initialize the component state."""
        # Inherit the diode state
        super()._init_state()

        # Add LED-specific state
        self.state.update({
            'brightness': 0.0,
            'color': self.get_property('color', 'red')
        })


    def calculate(self, simulator, time_step):
        """Calculate the LED state for the current time step."""
        # Get component values
        forward_voltage = self.get_property('forward_voltage', 2.0)  # Default 2V for LED
        max_current = self.get_property('max_current', 0.02)  # Default 20 mA

        # Get the nodes connected to the LED
        node_anode = simulator.get_node_for_component(self.id, 'anode')
        node_cathode = simulator.get_node_for_component(self.id, 'cathode')

        # Get node voltages
        v_anode = node_anode.voltage if node_anode else 0.0
        v_cathode = node_cathode.voltage if node_cathode else 0.0

        # Calculate voltage across the LED
        voltage_drop = v_anode - v_cathode

        # Log the voltage information
        logger.info(f"LED {self.id} voltage: anode={v_anode:.3f}V, cathode={v_cathode:.3f}V, drop={voltage_drop:.3f}V")

        # Check if the LED is forward biased
        if voltage_drop > forward_voltage * 0.9:  # Use 90% of forward voltage as threshold
            # Forward biased - conducting
            resistance = 0.1  # Small resistance when conducting
            current = (voltage_drop - forward_voltage) / resistance
            conducting = True

            # Apply current limiting
            if current > max_current:
                current = max_current

            logger.info(f"LED {self.id} is conducting ({voltage_drop:.3f}V > {forward_voltage:.3f}V)")
        else:
            # Reverse biased or not enough forward voltage
            if voltage_drop < 0:
                # Reverse biased - small leakage current
                current = -1e-9  # Almost zero
            else:
                # Not enough forward voltage
                current = 0.0
            conducting = False
            logger.info(f"LED {self.id} is NOT conducting ({voltage_drop:.3f}V < {forward_voltage:.3f}V)")

        # Calculate brightness based on current
        logger.info(f"LED {self.id} current: {current:.6f}A, max: {max_current:.6f}A")
        if current > 0 and voltage_drop >= forward_voltage * 0.9:
            brightness = min(1.0, current / max_current)
            logger.info(f"LED is ON: brightness={brightness:.2f}")
        else:
            brightness = 0.0
            logger.info(f"LED is OFF: insufficient current or voltage")

        # Calculate power
        power = voltage_drop * current

        # Update the state
        state_updates = {
            'voltages': {'anode': v_anode, 'cathode': v_cathode},
            'currents': {'anode': current, 'cathode': -current},
            'power': power,
            'conducting': conducting,
            'brightness': brightness,
            'color': self.get_property('color', 'red')
        }

        return state_updates

    def update(self):
        """Update the LED display based on state."""
        super().update()

        # Log LED state
        brightness = self.state.get('brightness', 0.0)
        conducting = self.state.get('conducting', False)
        anode_v = self.state.get('voltages', {}).get('anode', 0.0)
        cathode_v = self.state.get('voltages', {}).get('cathode', 0.0)

        logger.info(f"LED {self.id[:8]}... state: brightness={brightness:.2f}, conducting={conducting}, anode={anode_v:.2f}V, cathode={cathode_v:.2f}V")


class Transistor(BaseComponent):
    """Base class for transistors."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a transistor.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)
        self.size = (3, 3)  # Size in grid cells

    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {},
            'currents': {},
            'power': 0.0
        }


class BJT(Transistor):
    """Bipolar Junction Transistor (BJT) component."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a BJT.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)

    def _init_connections(self):
        """Initialize the connection points."""
        # Define connection points relative to component position
        self.connections = {
            'collector': (0, 1.5),     # Collector (top)
            'base': (-1.5, 0),         # Base (left)
            'emitter': (0, -1.5)       # Emitter (bottom)
        }

    def _init_state(self):
        """Initialize the component state."""
        # Inherit from base class
        super()._init_state()

        # Add BJT-specific state
        self.state.update({
            'voltages': {'collector': 0.0, 'base': 0.0, 'emitter': 0.0},
            'currents': {'collector': 0.0, 'base': 0.0, 'emitter': 0.0},
            'region': 'cutoff'  # Operating region: cutoff, active, saturation
        })

    def calculate(self, simulator, time_step):
        """Calculate the BJT state for the current time step.

        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds

        Returns:
            Dictionary of updated state values
        """
        # Get component values
        gain = self.get_property('gain', 100)  # Beta (hFE)
        is_npn = self.get_property('type', 'npn') == 'npn'
        vbe_threshold = self.get_property('vbe_threshold', 0.7)  # Base-emitter threshold voltage
        vce_saturation = self.get_property('vce_saturation', 0.2)  # Collector-emitter saturation voltage
        max_collector_current = self.get_property('max_collector_current', 0.5)

        # Get connected components
        node_collector = simulator.get_node_for_component(self.id, 'collector')
        node_base = simulator.get_node_for_component(self.id, 'base')
        node_emitter = simulator.get_node_for_component(self.id, 'emitter')

        # Get node voltages
        v_collector = node_collector.voltage if node_collector else 0.0
        v_base = node_base.voltage if node_base else 0.0
        v_emitter = node_emitter.voltage if node_emitter else 0.0

        # Calculate junction voltages
        vbe = v_base - v_emitter if is_npn else v_emitter - v_base
        vce = v_collector - v_emitter if is_npn else v_emitter - v_collector
        vbc = v_base - v_collector if is_npn else v_collector - v_base

        # Determine the operating region and calculate currents
        if vbe < vbe_threshold:
            # Cutoff region - negligible current flow
            region = 'cutoff'
            ib = 0.0
            ic = 0.0
            ie = 0.0
        elif vbc > 0:
            # Saturation region - both junctions forward biased
            region = 'saturation'
            ib = (vbe - vbe_threshold) / 1000.0  # Base current with a 1k resistor model
            ic = min(gain * ib, max_collector_current)  # Collector current limited by saturation
            ie = ib + ic
        else:
            # Active region - base-emitter junction forward biased, collector-base junction reverse biased
            region = 'active'
            ib = (vbe - vbe_threshold) / 1000.0  # Base current with a 1k resistor model
            ic = min(gain * ib, max_collector_current)  # Collector current proportional to base current
            ie = ib + ic

        # Handle multiple connections at each terminal:
        # In reality, current distribution would depend on the resistances
        # of the connected components. For simplicity, we'll track the total
        # currents and leave the distribution to the circuit solver.

        # Calculate power
        power = vce * ic + vbe * ib

        # For PNP, invert the currents
        if not is_npn:
            ib = -ib
            ic = -ic
            ie = -ie

        # Update the state
        state_updates = {
            'voltages': {'collector': v_collector, 'base': v_base, 'emitter': v_emitter},
            'currents': {'collector': ic, 'base': ib, 'emitter': ie},
            'power': power,
            'region': region
        }

        return state_updates

    def apply(self, state_updates):
        """Apply state updates to the component.

        Args:
            state_updates: Dictionary of state updates
        """
        for category, values in state_updates.items():
            if category in self.state:
                if isinstance(values, dict):
                    # Update nested dictionary
                    for key, value in values.items():
                        self.state[category][key] = value
                else:
                    # Update direct value
                    self.state[category] = values


class Switch(BaseComponent):
    """Switch component."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a switch.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)
        self.size = (3, 1)  # Size in grid cells

    def _init_connections(self):
        """Initialize the connection points."""
        # Define connection points relative to component position
        self.connections = {
            'p1': (-1, 0),  # Left connection
            'p2': (1, 0)    # Right connection
        }

    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'p1': 0.0, 'p2': 0.0},
            'currents': {'p1': 0.0, 'p2': 0.0},
            'closed': self.get_property('state', False)  # Default to open
        }

    def calculate(self, simulator, time_step):
        """Calculate the switch state for the current time step.

        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds

        Returns:
            Dictionary of updated state values
        """
        # Get component values
        closed = self.get_property('state', False)
        max_current = self.get_property('max_current', 5.0)

        # Get connected components
        node_p1 = simulator.get_node_for_component(self.id, 'p1')
        node_p2 = simulator.get_node_for_component(self.id, 'p2')

        # Get node voltages
        v_p1 = node_p1.voltage if node_p1 else 0.0
        v_p2 = node_p2.voltage if node_p2 else 0.0

        # Calculate current
        if closed:
            # Closed switch - low resistance
            resistance = 0.01  # Small but non-zero resistance
            current = (v_p1 - v_p2) / resistance

            # Apply current limiting
            if abs(current) > max_current:
                current = max_current if current > 0 else -max_current
        else:
            # Open switch - high resistance (essentially infinite)
            current = 0.0

        # For a switch with multiple connections, we need to distribute current
        # among the connected components. For simplicity, we'll use the same
        # current for all connections.

        # Update the state
        state_updates = {
            'voltages': {'p1': v_p1, 'p2': v_p2},
            'currents': {'p1': current, 'p2': -current},
            'closed': closed
        }

        return state_updates

    def apply(self, state_updates):
        """Apply state updates to the component.

        Args:
            state_updates: Dictionary of state updates
        """
        for category, values in state_updates.items():
            if category in self.state:
                if isinstance(values, dict):
                    # Update nested dictionary
                    for key, value in values.items():
                        self.state[category][key] = value
                else:
                    # Update direct value
                    self.state[category] = values

    def toggle(self):
        """Toggle the switch state between open and closed."""
        current_state = self.get_property('state', False)
        self.set_property('state', not current_state)
        self.state['closed'] = not current_state
        return not current_state

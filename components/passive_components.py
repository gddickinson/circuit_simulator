"""
Circuit Simulator - Passive Components
------------------------------------
This module defines passive electronic components such as resistors,
capacitors, and inductors.
"""

import math
import logging

from components.base_component import BaseComponent
import config

logger = logging.getLogger(__name__)


class Resistor(BaseComponent):
    """Resistor component."""
    
    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a resistor.
        
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
        # For a horizontal resistor, connections are at the left and right ends
        self.connections = {
            'p1': (-1.5, 0),  # Left connection
            'p2': (1.5, 0)    # Right connection
        }
    
    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'p1': 0.0, 'p2': 0.0},
            'currents': {'p1': 0.0, 'p2': 0.0},
            'power': 0.0,
            'temperature': 25.0  # Celsius
        }
    
    def calculate(self, simulator, time_step):
        """Calculate the resistor state for the current time step.
        
        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds
            
        Returns:
            Dictionary of updated state values
        """
        # Get component values
        resistance = self.get_property('resistance', config.DEFAULT_RESISTANCE)
        max_power = self.get_property('max_power', 0.25)  # Default 1/4 watt
        
        # Get connected components
        node_p1 = simulator.get_node_for_component(self.id, 'p1')
        node_p2 = simulator.get_node_for_component(self.id, 'p2')
        
        # Get node voltages
        v_p1 = node_p1.voltage if node_p1 else 0.0
        v_p2 = node_p2.voltage if node_p2 else 0.0
        
        # Calculate voltage across the resistor
        voltage_drop = v_p1 - v_p2
        
        # Calculate current through the resistor (positive current flows from p1 to p2)
        current = voltage_drop / resistance if resistance > 0 else 0.0
        
        # Calculate power dissipation
        power = voltage_drop * current
        
        # Update the state
        state_updates = {
            'voltages': {'p1': v_p1, 'p2': v_p2},
            'currents': {'p1': current, 'p2': -current},  # Current in = current out (opposite direction)
            'power': power,
            'temperature': 25.0 + (power / max_power) * 50.0 if power > 0 else 25.0
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


class Capacitor(BaseComponent):
    """Capacitor component."""
    
    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a capacitor.
        
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
            'p1': (-1, 0),  # Left connection
            'p2': (1, 0)    # Right connection
        }
    
    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'p1': 0.0, 'p2': 0.0},
            'currents': {'p1': 0.0, 'p2': 0.0},
            'charge': 0.0,
            'energy': 0.0
        }
    
    def calculate(self, simulator, time_step):
        """Calculate the capacitor state for the current time step.
        
        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds
            
        Returns:
            Dictionary of updated state values
        """
        # Get component values
        capacitance = self.get_property('capacitance', config.DEFAULT_CAPACITANCE)
        max_voltage = self.get_property('max_voltage', 50.0)
        
        # Get connected components
        node_p1 = simulator.get_node_for_component(self.id, 'p1')
        node_p2 = simulator.get_node_for_component(self.id, 'p2')
        
        # Get node voltages
        v_p1 = node_p1.voltage if node_p1 else 0.0
        v_p2 = node_p2.voltage if node_p2 else 0.0
        
        # Calculate voltage across the capacitor
        voltage_drop = v_p1 - v_p2
        
        # Get the previous charge
        previous_charge = self.state['charge']
        
        # Calculate the new charge: Q = C * V
        new_charge = capacitance * voltage_drop
        
        # Calculate the current: I = dQ/dt
        charge_delta = new_charge - previous_charge
        current = charge_delta / time_step if time_step > 0 else 0.0
        
        # Calculate energy stored: E = 0.5 * C * V²
        energy = 0.5 * capacitance * (voltage_drop ** 2)
        
        # Update the state
        state_updates = {
            'voltages': {'p1': v_p1, 'p2': v_p2},
            'currents': {'p1': current, 'p2': -current},
            'charge': new_charge,
            'energy': energy
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


class Inductor(BaseComponent):
    """Inductor component."""
    
    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize an inductor.
        
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
            'p1': (-1.5, 0),  # Left connection
            'p2': (1.5, 0)    # Right connection
        }
    
    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'p1': 0.0, 'p2': 0.0},
            'currents': {'p1': 0.0, 'p2': 0.0},
            'flux': 0.0,
            'energy': 0.0
        }
    
    def calculate(self, simulator, time_step):
        """Calculate the inductor state for the current time step.
        
        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds
            
        Returns:
            Dictionary of updated state values
        """
        # Get component values
        inductance = self.get_property('inductance', config.DEFAULT_INDUCTANCE)
        max_current = self.get_property('max_current', 1.0)
        
        # Get connected components
        node_p1 = simulator.get_node_for_component(self.id, 'p1')
        node_p2 = simulator.get_node_for_component(self.id, 'p2')
        
        # Get node voltages
        v_p1 = node_p1.voltage if node_p1 else 0.0
        v_p2 = node_p2.voltage if node_p2 else 0.0
        
        # Calculate voltage across the inductor
        voltage_drop = v_p1 - v_p2
        
        # Calculate new current: V = L * dI/dt => dI = V * dt / L
        current_delta = voltage_drop * time_step / inductance if inductance > 0 else 0.0
        
        # Get previous current
        previous_current = self.state['currents']['p1']
        
        # Calculate new current
        new_current = previous_current + current_delta
        
        # Calculate magnetic flux: Φ = L * I
        flux = inductance * new_current
        
        # Calculate energy stored: E = 0.5 * L * I²
        energy = 0.5 * inductance * (new_current ** 2)
        
        # Update the state
        state_updates = {
            'voltages': {'p1': v_p1, 'p2': v_p2},
            'currents': {'p1': new_current, 'p2': -new_current},
            'flux': flux,
            'energy': energy
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


class Ground(BaseComponent):
    """Ground connection component."""
    
    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize a ground connection.
        
        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        super().__init__(component_id, position, rotation, properties)
        self.size = (1, 2)  # Size in grid cells
    
    def _init_connections(self):
        """Initialize the connection points."""
        # Ground has only one connection point
        self.connections = {
            'gnd': (0, -0.5)  # Top connection
        }
    
    def _init_state(self):
        """Initialize the component state."""
        self.state = {
            'voltages': {'gnd': 0.0},
            'currents': {'gnd': 0.0}
        }
    
    def calculate(self, simulator, time_step):
        """Calculate the ground state.
        
        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds
            
        Returns:
            Dictionary of updated state values
        """
        # Ground always has 0V potential
        node_gnd = simulator.get_node_for_component(self.id, 'gnd')
        
        # Current is the sum of all currents flowing into the ground
        # This is calculated in the simulator, so just set it to 0 here
        current = 0.0
        
        # Update the state
        state_updates = {
            'voltages': {'gnd': 0.0},
            'currents': {'gnd': current}
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

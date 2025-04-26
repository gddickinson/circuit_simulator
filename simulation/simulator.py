"""
Circuit Simulator - Simulation Engine
-----------------------------------
This module provides the core simulation functionality for the circuit simulator.
"""

import time
import logging
import numpy as np
from collections import defaultdict, deque

import config
from utils.logger import SimulationEvent

logger = logging.getLogger(__name__)


class Node:
    """A node in the circuit representing a junction of components."""
    
    def __init__(self, node_id):
        """Initialize a node.
        
        Args:
            node_id: Unique node ID
        """
        self.id = node_id
        self.components = {}  # Dictionary of {(component_id, connection_name): component}
        self.voltage = 0.0
        self.current_sum = 0.0  # Sum of currents flowing into the node
    
    def add_component(self, component, connection_name):
        """Add a component to the node.
        
        Args:
            component: Component object
            connection_name: Connection name on the component
        """
        self.components[(component.id, connection_name)] = component
    
    def remove_component(self, component_id, connection_name):
        """Remove a component from the node.
        
        Args:
            component_id: Component ID
            connection_name: Connection name on the component
        """
        if (component_id, connection_name) in self.components:
            del self.components[(component_id, connection_name)]
    
    def get_connected_components(self):
        """Get all components connected to this node.
        
        Returns:
            List of (component, connection_name) tuples
        """
        return [(component, conn_name) for (_, conn_name), component in self.components.items()]
    
    def __str__(self):
        return f"Node({self.id}, {len(self.components)} components, {self.voltage:.3f}V)"


class CircuitSimulator:
    """Core simulation engine for the circuit simulator."""
    
    def __init__(self):
        """Initialize the simulator."""
        self.components = {}  # Dictionary of {component_id: component}
        self.nodes = {}  # Dictionary of {node_id: node}
        self.ground_node = None  # Reference node (ground)
        
        # Simulation parameters
        self.time_step = config.SIMULATION_TIMESTEP
        self.simulation_time = 0.0
        self.running = False
        self.paused = False
        self.max_iterations = config.MAX_ITERATIONS
        self.convergence_threshold = config.CONVERGENCE_THRESHOLD
        
        # Performance tracking
        self.last_update_time = 0.0
        self.update_count = 0
        self.fps = 0.0
        
        # Event listeners
        self.event_listeners = []
        
        # Simulation statistics
        self.stats = {
            'iterations': 0,
            'solve_time': 0.0,
            'component_update_time': 0.0,
            'node_update_time': 0.0,
            'total_time': 0.0
        }
        
        # Simulation history for analysis
        self.history = defaultdict(lambda: defaultdict(list))
        self.history_length = 1000  # Number of time steps to store in history
    
    def clear(self):
        """Clear all components and nodes."""
        self.components = {}
        self.nodes = {}
        self.ground_node = None
        self.simulation_time = 0.0
        self.history = defaultdict(lambda: defaultdict(list))
    
    def add_component(self, component):
        """Add a component to the simulator.
        
        Args:
            component: Component object
            
        Returns:
            True if component added successfully, False otherwise
        """
        if component.id in self.components:
            logger.warning(f"Component {component.id} already exists")
            return False
        
        self.components[component.id] = component
        logger.debug(f"Added component {component}")
        return True
    
    def remove_component(self, component_id):
        """Remove a component from the simulator.
        
        Args:
            component_id: Component ID
            
        Returns:
            True if component removed successfully, False otherwise
        """
        if component_id not in self.components:
            logger.warning(f"Component {component_id} not found")
            return False
        
        # Get the component
        component = self.components[component_id]
        
        # Disconnect the component from all nodes
        connection_points = component.connection_points
        for connection_name, position in connection_points.items():
            # Find the node at this position
            node_id = self._get_node_id_at_position(position)
            if node_id in self.nodes:
                # Remove the component from the node
                self.nodes[node_id].remove_component(component_id, connection_name)
                
                # If the node has no more components, remove it
                if not self.nodes[node_id].components:
                    del self.nodes[node_id]
        
        # Remove the component
        del self.components[component_id]
        logger.debug(f"Removed component {component_id}")
        return True
    
    def get_component(self, component_id):
        """Get a component by ID.
        
        Args:
            component_id: Component ID
            
        Returns:
            Component object or None if not found
        """
        return self.components.get(component_id)
    
    def get_all_components(self):
        """Get all components.
        
        Returns:
            Dictionary of {component_id: component}
        """
        return self.components
    
    def _get_node_id_at_position(self, position):
        """Get the node ID at the given position.
        
        Args:
            position: (x, y) tuple of grid coordinates
            
        Returns:
            Node ID string
        """
        # Use the position as the node ID
        return f"node_{position[0]}_{position[1]}"
    
    def _get_or_create_node(self, position):
        """Get the node at the given position, or create it if it doesn't exist.
        
        Args:
            position: (x, y) tuple of grid coordinates
            
        Returns:
            Node object
        """
        node_id = self._get_node_id_at_position(position)
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id)
        return self.nodes[node_id]
    
    def get_node_at_position(self, position):
        """Get the node at the given position.
        
        Args:
            position: (x, y) tuple of grid coordinates
            
        Returns:
            Node object or None if no node at the position
        """
        node_id = self._get_node_id_at_position(position)
        return self.nodes.get(node_id)
    
    def get_node_for_component(self, component_id, connection_name):
        """Get the node connected to the given component connection.
        
        Args:
            component_id: Component ID
            connection_name: Connection name
            
        Returns:
            Node object or None if not found
        """
        component = self.get_component(component_id)
        if not component:
            return None
        
        # Get the position of the connection
        connection_points = component.connection_points
        if connection_name not in connection_points:
            return None
        
        position = connection_points[connection_name]
        return self.get_node_at_position(position)
    
    def connect_components_at(self, component1_id, connection1, component2_id, connection2):
        """Connect two components at the specified connection points.
        
        Args:
            component1_id: First component ID
            connection1: First component connection name
            component2_id: Second component ID
            connection2: Second component connection name
            
        Returns:
            True if connection successful, False otherwise
        """
        component1 = self.get_component(component1_id)
        component2 = self.get_component(component2_id)
        
        if not component1 or not component2:
            logger.warning(f"Component not found: {component1_id} or {component2_id}")
            return False
        
        # Get the positions of the connections
        connection1_points = component1.connection_points
        connection2_points = component2.connection_points
        
        if connection1 not in connection1_points or connection2 not in connection2_points:
            logger.warning(f"Connection not found: {connection1} or {connection2}")
            return False
        
        # Connect the components in their internal state
        component1.connect(connection1, component2, connection2)
        component2.connect(connection2, component1, connection1)
        
        # Get the nodes for both connections
        node1_position = connection1_points[connection1]
        node2_position = connection2_points[connection2]
        
        # Make sure connections are at the same position
        if node1_position != node2_position:
            logger.warning(f"Connection points not at same position: {node1_position} != {node2_position}")
            return False
        
        # Get or create the node at this position
        node = self._get_or_create_node(node1_position)
        
        # Add both components to the node
        node.add_component(component1, connection1)
        node.add_component(component2, connection2)
        
        logger.debug(f"Connected {component1_id}.{connection1} to {component2_id}.{connection2} at {node1_position}")
        return True
    
    def build_circuit_from_components(self):
        """Build the circuit by connecting components at the same position.
        
        This method finds all components with connection points at the same position
        and connects them to the same node.
        
        Returns:
            Number of nodes created
        """
        # Clear existing nodes
        self.nodes = {}
        self.ground_node = None
        
        # Create nodes for all connection points
        for component_id, component in self.components.items():
            connection_points = component.connection_points
            for connection_name, position in connection_points.items():
                node = self._get_or_create_node(position)
                node.add_component(component, connection_name)
        
        # Find the ground node (look for a Ground component)
        for component in self.components.values():
            if component.__class__.__name__ == 'Ground':
                gnd_connection = component.connection_points.get('gnd')
                if gnd_connection:
                    self.ground_node = self.get_node_at_position(gnd_connection)
                    self.ground_node.voltage = 0.0
                    logger.debug(f"Found ground node: {self.ground_node}")
                    break
        
        # If no ground node found, use the first node as ground
        if not self.ground_node and self.nodes:
            self.ground_node = next(iter(self.nodes.values()))
            self.ground_node.voltage = 0.0
            logger.debug(f"Using {self.ground_node} as default ground node")
        
        logger.info(f"Built circuit with {len(self.nodes)} nodes and {len(self.components)} components")
        
        # Notify listeners that the circuit has been built
        self._notify_listeners(SimulationEvent.CIRCUIT_BUILT, {
            'nodes': len(self.nodes),
            'components': len(self.components),
            'ground_node': self.ground_node.id if self.ground_node else None
        })
        
        return len(self.nodes)
    
    def get_current_for_component(self, component_id, connection_name):
        """Get the current flowing through a component connection.
        
        Args:
            component_id: Component ID
            connection_name: Connection name
            
        Returns:
            Current value (positive means current flowing into the component)
        """
        component = self.get_component(component_id)
        if not component:
            return 0.0
        
        return component.get_current(connection_name)
    
    def get_voltage_for_component(self, component_id, connection_name):
        """Get the voltage at a component connection.
        
        Args:
            component_id: Component ID
            connection_name: Connection name
            
        Returns:
            Voltage value
        """
        component = self.get_component(component_id)
        if not component:
            return 0.0
        
        return component.get_voltage(connection_name)
    
    def get_resistance_between(self, component_id, connection1, connection2):
        """Get the equivalent resistance between two component connections.
        
        This is a simplified implementation that just returns a typical value.
        
        Args:
            component_id: Component ID
            connection1: First connection name
            connection2: Second connection name
            
        Returns:
            Resistance value in ohms
        """
        # For simplicity, just return a typical value
        # In a real implementation, this would compute the actual resistance
        return 1000.0  # Default to 1k ohm
    
    def start_simulation(self):
        """Start the simulation."""
        if not self.running:
            self.running = True
            self.simulation_time = 0.0
            logger.info("Simulation started")
            self._notify_listeners(SimulationEvent.SIMULATION_STARTED, {
                'time': self.simulation_time
            })
    
    def stop_simulation(self):
        """Stop the simulation."""
        if self.running:
            self.running = False
            logger.info("Simulation stopped")
            self._notify_listeners(SimulationEvent.SIMULATION_STOPPED, {
                'time': self.simulation_time
            })
    
    def pause_simulation(self):
        """Pause the simulation."""
        if self.running and not self.paused:
            self.paused = True
            logger.info("Simulation paused")
            self._notify_listeners(SimulationEvent.SIMULATION_PAUSED, {
                'time': self.simulation_time
            })
    
    def resume_simulation(self):
        """Resume the simulation."""
        if self.running and self.paused:
            self.paused = False
            logger.info("Simulation resumed")
            self._notify_listeners(SimulationEvent.SIMULATION_RESUMED, {
                'time': self.simulation_time
            })
    
    def reset_simulation(self):
        """Reset the simulation."""
        self.simulation_time = 0.0
        self.history = defaultdict(lambda: defaultdict(list))
        
        # Reset component states
        for component in self.components.values():
            component._init_state()
        
        logger.info("Simulation reset")
        self._notify_listeners(SimulationEvent.SIMULATION_RESET, {
            'time': self.simulation_time
        })
    
    def update(self, elapsed_time=None):
        """Update the simulation by one time step.
        
        Args:
            elapsed_time: Elapsed real time since last update (None to use fixed time step)
            
        Returns:
            Dictionary of simulation statistics
        """
        if not self.running or self.paused or not self.components:
            return self.stats
        
        # Use fixed time step if elapsed_time not provided
        if elapsed_time is None:
            elapsed_time = self.time_step
        
        # Update performance tracking
        current_time = time.time()
        if self.update_count > 0:
            dt = current_time - self.last_update_time
            if dt > 0:
                self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt)  # Exponential moving average
        self.last_update_time = current_time
        self.update_count += 1
        
        # Start timing
        start_time = time.time()
        
        # Solve the circuit
        self.solve_circuit()
        
        # Record time taken for circuit solving
        solve_time = time.time() - start_time
        
        # Update component states
        component_start_time = time.time()
        for component in self.components.values():
            # Calculate new state
            state_updates = component.calculate(self, self.time_step)
            
            # Apply updates
            component.apply(state_updates)
            
            # Record state in history
            for key, value in component.state.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if len(self.history[component.id][f"{key}.{sub_key}"]) >= self.history_length:
                            self.history[component.id][f"{key}.{sub_key}"].pop(0)
                        self.history[component.id][f"{key}.{sub_key}"].append((self.simulation_time, sub_value))
                else:
                    if len(self.history[component.id][key]) >= self.history_length:
                        self.history[component.id][key].pop(0)
                    self.history[component.id][key].append((self.simulation_time, value))
        
        # Record time taken for component updates
        component_update_time = time.time() - component_start_time
        
        # Increment simulation time
        self.simulation_time += self.time_step
        
        # Record total time taken
        total_time = time.time() - start_time
        
        # Update statistics
        self.stats = {
            'iterations': 0,  # This will be set by the solver
            'solve_time': solve_time,
            'component_update_time': component_update_time,
            'node_update_time': 0.0,  # This will be set by the solver
            'total_time': total_time,
            'fps': self.fps,
            'simulation_time': self.simulation_time
        }
        
        # Notify listeners
        self._notify_listeners(SimulationEvent.SIMULATION_UPDATED, self.stats)
        
        return self.stats
    
    def solve_circuit(self):
        """Solve the circuit using nodal analysis.
        
        This is a placeholder that will be implemented by the circuit_solver module.
        """
        # This will be implemented by the circuit_solver
        pass
    
    def add_event_listener(self, listener):
        """Add an event listener.
        
        Args:
            listener: Function that takes an event type and data
        """
        if listener not in self.event_listeners:
            self.event_listeners.append(listener)
    
    def remove_event_listener(self, listener):
        """Remove an event listener.
        
        Args:
            listener: Function that was previously added
        """
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)
    
    def _notify_listeners(self, event_type, data):
        """Notify all event listeners.
        
        Args:
            event_type: Event type (from SimulationEvent enum)
            data: Event data
        """
        for listener in self.event_listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
    
    def get_history(self, component_id, state_key, sub_key=None):
        """Get the history of a component state value.
        
        Args:
            component_id: Component ID
            state_key: State key (e.g., 'voltages', 'currents')
            sub_key: Sub-key for nested state (e.g., 'p1', 'p2')
            
        Returns:
            List of (time, value) tuples
        """
        if sub_key:
            return self.history.get(component_id, {}).get(f"{state_key}.{sub_key}", [])
        else:
            return self.history.get(component_id, {}).get(state_key, [])
    
    def get_wires(self):
        """Get all wires in the circuit.
        
        A wire is a connection between two nodes that doesn't go through a component.
        
        Returns:
            List of (node1_id, node2_id) tuples
        """
        # For now, there are no explicit wires in the circuit
        return []
    
    def to_dict(self):
        """Convert the circuit to a dictionary for saving.
        
        Returns:
            Dictionary representation of the circuit
        """
        return {
            'components': {cid: component.to_dict() for cid, component in self.components.items()},
            'simulation_time': self.simulation_time,
            'time_step': self.time_step,
            'ground_node': self.ground_node.id if self.ground_node else None
        }
    
    def from_dict(self, data, component_factory):
        """Load the circuit from a dictionary.
        
        Args:
            data: Dictionary representation of the circuit
            component_factory: Function that creates components from dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        # Clear existing circuit
        self.clear()
        
        # Set simulation parameters
        self.simulation_time = data.get('simulation_time', 0.0)
        self.time_step = data.get('time_step', config.SIMULATION_TIMESTEP)
        
        # Load components
        components_data = data.get('components', {})
        for component_id, component_data in components_data.items():
            component = component_factory(component_data)
            if component:
                self.add_component(component)
        
        # Build the circuit
        self.build_circuit_from_components()
        
        # If ground_node was specified, find it
        ground_node_id = data.get('ground_node')
        if ground_node_id and ground_node_id in self.nodes:
            self.ground_node = self.nodes[ground_node_id]
            self.ground_node.voltage = 0.0
        
        logger.info(f"Loaded circuit with {len(self.components)} components and {len(self.nodes)} nodes")
        return True
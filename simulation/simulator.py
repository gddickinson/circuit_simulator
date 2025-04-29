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
        key = (component.id, connection_name)
        if key not in self.components:
            self.components[key] = component
            logger.debug(f"Added {component.__class__.__name__} ({component.id[:8]}...) {connection_name} to node {self.id}")

    def remove_component(self, component_id, connection_name):
        """Remove a component from the node.

        Args:
            component_id: Component ID
            connection_name: Connection name on the component

        Returns:
            True if component was removed, False if not found
        """
        key = (component_id, connection_name)
        if key in self.components:
            del self.components[key]
            logger.debug(f"Removed component {component_id[:8]}... {connection_name} from node {self.id}")
            return True
        return False

    def get_connected_components(self):
        """Get all components connected to this node.

        Returns:
            List of (component, connection_name) tuples
        """
        return [(component, conn_name) for (_, conn_name), component in self.components.items()]

    def calculate_current_sum(self):
        """Calculate the sum of currents flowing into this node.

        Returns:
            Sum of currents (should be close to zero for a valid circuit)
        """
        current_sum = 0.0
        for (component_id, connection_name), component in self.components.items():
            # Get current flowing into this node from the component
            current = component.get_current(connection_name)
            if current is not None:
                current_sum += current
                logger.debug(f"Node {self.id}: {component.__class__.__name__} {connection_name} current: {current*1000:.2f}mA")

        self.current_sum = current_sum
        logger.debug(f"Node {self.id}: total current sum: {current_sum*1000:.2f}mA")
        return current_sum

    def __str__(self):
        num_components = len(self.components)
        return f"Node({self.id}, {num_components} components, {self.voltage:.3f}V)"


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
        # Search all nodes for this component and connection
        for node_id, node in self.nodes.items():
            for comp, conn_name in node.get_connected_components():
                if comp.id == component_id and conn_name == connection_name:
                    logger.debug(f"Found node {node_id} for component {component_id[:8]}... {connection_name}")
                    return node

        # Log when a node is not found
        logger.debug(f"No node found for component {component_id[:8]}... {connection_name}")
        return None

    def connect_components_at(self, component1_id, connection1, component2_id, connection2):
        """Connect two components at the specified connection points."""
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
        success1 = component1.connect(connection1, component2, connection2)
        success2 = component2.connect(connection2, component1, connection1)

        if not (success1 and success2):
            logger.warning(f"Failed to connect components: internal state update failed")
            return False

        # Log connection info
        logger.info(f"Connected {component1.__class__.__name__} {connection1} to {component2.__class__.__name__} {connection2}")
        logger.info(f"Connected {component1_id}.{connection1} to {component2_id}.{connection2}")

        # Log position differences
        node1_position = connection1_points[connection1]
        node2_position = connection2_points[connection2]
        if node1_position != node2_position:
            logger.info(f"Connected points at different positions: {node1_position} and {node2_position}")

        return True

    def disconnect_components_at(self, component1_id, connection1, component2_id, connection2):
        """Disconnect two components at the specified connection points.

        Args:
            component1_id: First component ID
            connection1: First component connection name
            component2_id: Second component ID
            connection2: Second component connection name

        Returns:
            True if disconnection successful, False otherwise
        """
        component1 = self.get_component(component1_id)
        component2 = self.get_component(component2_id)

        if not component1 or not component2:
            logger.warning(f"Component not found: {component1_id} or {component2_id}")
            return False

        # Disconnect the components in their internal state
        success1 = component1.disconnect(connection1, component2.id, connection2)
        success2 = component2.disconnect(connection2, component1.id, connection1)

        # Get the nodes for both connections
        connection1_points = component1.connection_points
        connection2_points = component2.connection_points

        node1_position = connection1_points.get(connection1)
        node2_position = connection2_points.get(connection2)

        # If positions match, update the node
        if node1_position and node1_position == node2_position:
            node_id = self._get_node_id_at_position(node1_position)
            if node_id in self.nodes:
                node = self.nodes[node_id]
                # The node will keep track of components, but not necessarily connections
                # To fully remove a component from a node, all connections must be removed

                # Only remove component from node if it has no more connections at this position
                if not component1.is_connected(connection1):
                    node.remove_component(component1.id, connection1)

                if not component2.is_connected(connection2):
                    node.remove_component(component2.id, connection2)

                # If node has no more components, remove it
                if not node.components:
                    del self.nodes[node_id]

        return success1 and success2



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

    def would_create_circular_connection(self, component1_id, connection1, component2_id, connection2):
        """Check if connecting these two components would create a circular connection.

        Args:
            component1_id: First component ID
            connection1: First component connection name
            component2_id: Second component ID
            connection2: Second component connection name

        Returns:
            True if a circular connection would be created, False otherwise
        """
        # Simplest check: ensure we're not connecting a component to itself
        if component1_id == component2_id:
            return True

        # More complex check: ensure this wouldn't create a circular connection
        # This would require traversing the connection graph
        # For simplicity, we'll skip this for now

        return False

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

        # Get the current from the component's state
        # This will include the summed current for all connections at this point
        return component.get_current(connection_name)

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

        # Verify that current is conserved at each node
        node_update_start_time = time.time()

        for node_id, node in self.nodes.items():
            current_sum = node.calculate_current_sum()
            # If the sum is significantly different from zero, log a warning
            if abs(current_sum) > 1e-9:
                logger.debug(f"Current not conserved at node {node_id}: sum = {current_sum:.6g} A")

        node_update_time = time.time() - node_update_start_time

        # Increment simulation time
        self.simulation_time += self.time_step

        # Record total time taken
        total_time = time.time() - start_time

        # Update statistics
        self.stats = {
            'iterations': 0,  # This will be set by the solver
            'solve_time': solve_time,
            'component_update_time': component_update_time,
            'node_update_time': node_update_time,
            'total_time': total_time,
            'fps': self.fps,
            'simulation_time': self.simulation_time
        }

        # Notify listeners
        self._notify_listeners(SimulationEvent.SIMULATION_UPDATED, self.stats)

        return self.stats


    def build_circuit_from_components(self):
        """Build the circuit by creating a proper connection graph based on component connections."""
        # Clear existing nodes
        self.nodes = {}
        self.ground_node = None

        # First create a mapping of (component_id, connection_name) to a unique node ID
        # This helps us group all connected points to the same node
        connection_map = {}
        connection_groups = {}  # Groups of connected points
        next_group_id = 0

        # Step 1: Analyze connections in each component to create groups
        for component_id, component in self.components.items():
            # Look at each connection in this component
            for conn_name, connected_to in component.connected_to.items():
                # This will be a list of (other_id, other_conn) tuples
                for other_id, other_conn in connected_to:
                    # Create keys for both sides of this connection
                    key1 = (component_id, conn_name)
                    key2 = (other_id, other_conn)

                    # Check if either is already in a group
                    group_id1 = connection_map.get(key1)
                    group_id2 = connection_map.get(key2)

                    if group_id1 is not None and group_id2 is not None:
                        # Both already have groups - merge if different
                        if group_id1 != group_id2:
                            # Merge group2 into group1
                            for k in list(connection_map.keys()):
                                if connection_map[k] == group_id2:
                                    connection_map[k] = group_id1
                            # Merge the connection lists
                            if group_id2 in connection_groups:
                                connections2 = connection_groups.pop(group_id2)
                                connection_groups[group_id1].extend(connections2)
                    elif group_id1 is not None:
                        # Only first has a group - add second to it
                        connection_map[key2] = group_id1
                        connection_groups[group_id1].append(key2)
                    elif group_id2 is not None:
                        # Only second has a group - add first to it
                        connection_map[key1] = group_id2
                        connection_groups[group_id2].append(key1)
                    else:
                        # Neither has a group - create new group
                        new_group_id = f"group_{next_group_id}"
                        next_group_id += 1
                        connection_map[key1] = new_group_id
                        connection_map[key2] = new_group_id
                        connection_groups[new_group_id] = [key1, key2]

        # Step 2: Add any unconnected terminals as their own groups
        for component_id, component in self.components.items():
            for conn_name in component.connections.keys():
                key = (component_id, conn_name)
                if key not in connection_map:
                    # Create a new group for this unconnected terminal
                    new_group_id = f"group_{next_group_id}"
                    next_group_id += 1
                    connection_map[key] = new_group_id
                    connection_groups[new_group_id] = [key]

        # Step 3: Create nodes from these connection groups
        for group_id, connections in connection_groups.items():
            # Create a node for this group
            node = Node(group_id)
            self.nodes[group_id] = node

            # Add all connections to this node
            for comp_id, conn_name in connections:
                component = self.components.get(comp_id)
                if component:
                    node.add_component(component, conn_name)

            logger.info(f"Created node {group_id} with {len(connections)} connections")

        # Step 4: Find ground node
        # First look for a Ground component
        for component in self.components.values():
            if component.__class__.__name__ == 'Ground':
                # Find which node this ground component is connected to
                gnd_connection = 'gnd'  # The connection name for ground components

                # Find the node with this component and connection
                for node_id, node in self.nodes.items():
                    for comp, conn_name in node.get_connected_components():
                        if comp.id == component.id and conn_name == gnd_connection:
                            self.ground_node = node
                            self.ground_node.voltage = 0.0
                            logger.info(f"Found ground node from Ground component: {node_id}")
                            break
                    if self.ground_node:
                        break
                if self.ground_node:
                    break

        # If no ground node found, use the negative terminal of a voltage source
        if not self.ground_node:
            for component in self.components.values():
                if component.__class__.__name__ in ['DCVoltageSource', 'ACVoltageSource']:
                    # Find the node connected to the negative terminal
                    neg_connection = 'neg'  # The negative terminal

                    # Find the node with this component and connection
                    for node_id, node in self.nodes.items():
                        for comp, conn_name in node.get_connected_components():
                            if comp.id == component.id and conn_name == neg_connection:
                                self.ground_node = node
                                self.ground_node.voltage = 0.0
                                logger.info(f"Using voltage source negative terminal as ground: {node_id}")
                                break
                        if self.ground_node:
                            break
                    if self.ground_node:
                        break

        # If still no ground node, use the first node
        if not self.ground_node and self.nodes:
            self.ground_node = next(iter(self.nodes.values()))
            self.ground_node.voltage = 0.0
            logger.info(f"Using {self.ground_node.id} as default ground node")

        # SAFETY CHECK: If we still have no ground node (empty circuit), create one
        if not self.ground_node:
            node_id = "default_ground"
            self.nodes[node_id] = Node(node_id)
            self.ground_node = self.nodes[node_id]
            self.ground_node.voltage = 0.0
            logger.warning(f"Created default ground node as no other ground was found")

        # Log circuit nodes and components
        logger.info(f"Built circuit with {len(self.nodes)} nodes and {len(self.components)} components")
        for node_id, node in self.nodes.items():
            components_str = ", ".join([f"{c.__class__.__name__}({c.id[:8]}...)" for c, _ in node.get_connected_components()])
            logger.info(f"Node {node_id} connects: {components_str}")

        # Notify listeners
        self._notify_listeners(SimulationEvent.CIRCUIT_BUILT, {
            'nodes': len(self.nodes),
            'components': len(self.components),
            'ground_node': self.ground_node.id if self.ground_node else None
        })

        return len(self.nodes)

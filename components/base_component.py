"""
Circuit Simulator - Base Component
---------------------------------
This module defines the base Component class from which all components inherit.
"""

import uuid
import math
import logging
from abc import ABC, abstractmethod

import config

logger = logging.getLogger(__name__)


class BaseComponent(ABC):
    """Abstract base class for all circuit components."""

    def __init__(self, component_id=None, position=(0, 0), rotation=0, properties=None):
        """Initialize the component.

        Args:
            component_id: Database ID of the component type
            position: (x, y) tuple of grid coordinates
            rotation: Rotation in degrees (0, 90, 180, 270)
            properties: Dictionary of component properties
        """
        self.id = str(uuid.uuid4())  # Unique instance ID
        self.component_id = component_id  # Database component type ID
        self.position = position
        self.rotation = rotation
        self.properties = properties or {}
        self.connections = {}  # Dictionary of connection points {name: (x, y)}
        self.connected_to = {}  # Dictionary of {connection_name: [(component_id, connection_name), ...]}
        self.state = {}  # Component state values (voltage, current, etc.)
        self.size = (1, 1)  # Size in grid cells
        self.selected = False
        self.visible = True
        self.debug = False

        # Initialize the component
        self._init_connections()
        self._init_state()

    @abstractmethod
    def _init_connections(self):
        """Initialize the connection points."""
        pass

    @abstractmethod
    def _init_state(self):
        """Initialize the component state."""
        pass

    @property
    def connection_points(self):
        """Get all connection points in absolute coordinates.

        Returns:
            Dictionary of {name: (x, y)} connection points
        """
        points = {}
        for name, offset in self.connections.items():
            # Apply rotation and calculate absolute position
            x, y = self._rotate_point(offset[0], offset[1], self.rotation)
            abs_x, abs_y = self.position[0] + x, self.position[1] + y
            points[name] = (abs_x, abs_y)
        return points

    def _rotate_point(self, x, y, angle):
        """Rotate a point around the origin.

        Args:
            x, y: Point coordinates
            angle: Rotation angle in degrees

        Returns:
            (x, y) rotated coordinates
        """
        # Convert to radians
        rad = math.radians(angle)

        # Apply rotation
        new_x = x * math.cos(rad) - y * math.sin(rad)
        new_y = x * math.sin(rad) + y * math.cos(rad)

        # Round to nearest grid position
        return round(new_x), round(new_y)

    def set_position(self, x, y):
        """Set the component position.

        Args:
            x, y: Grid coordinates
        """
        self.position = (x, y)

    def set_rotation(self, angle):
        """Set the component rotation.

        Args:
            angle: Rotation angle in degrees (0, 90, 180, 270)
        """
        # Normalize angle to 0, 90, 180, 270
        self.rotation = angle % 360

    def rotate(self, delta=90):
        """Rotate the component.

        Args:
            delta: Rotation increment in degrees
        """
        self.set_rotation(self.rotation + delta)

    def get_connection_at(self, x, y):
        """Get the connection name at the given coordinates.

        Args:
            x, y: Grid coordinates

        Returns:
            Connection name or None if no connection at the coordinates
        """
        points = self.connection_points
        for name, point in points.items():
            if point == (x, y):
                return name
        return None

    # In components/base_component.py
    def connect(self, connection_name, other_component, other_connection):
        """Connect this component to another component."""
        if connection_name not in self.connections:
            logger.warning(f"Connection {connection_name} not found on {self}")
            return False

        if other_connection not in other_component.connections:
            logger.warning(f"Connection {other_connection} not found on {other_component}")
            return False

        # Initialize the connection list if it doesn't exist
        if connection_name not in self.connected_to:
            self.connected_to[connection_name] = []

        # Check if this connection already exists
        connection_pair = (other_component.id, other_connection)
        if connection_pair in self.connected_to[connection_name]:
            logger.warning(f"Connection already exists: {self} {connection_name} to {other_component} {other_connection}")
            return False

        # Add the connection
        self.connected_to[connection_name].append(connection_pair)

        logger.info(f"Connected {self.__class__.__name__} {connection_name} to {other_component.__class__.__name__} {other_connection}")
        return True

    def disconnect(self, connection_name, other_component_id=None, other_connection=None):
        """Disconnect from the given connection point.

        Args:
            connection_name: Name of the connection point
            other_component_id: (Optional) ID of the component to disconnect from
            other_connection: (Optional) Name of the connection on the other component

        Returns:
            True if disconnection successful, False otherwise
        """
        if connection_name not in self.connected_to:
            logger.warning(f"No connections at {connection_name} to disconnect")
            return False

        # If other_component_id is provided, disconnect only that specific connection
        if other_component_id and other_connection:
            connection_pair = (other_component_id, other_connection)
            if connection_pair in self.connected_to[connection_name]:
                self.connected_to[connection_name].remove(connection_pair)
                logger.debug(f"Disconnected {self} {connection_name} from {other_component_id} {other_connection}")

                # Remove the empty list if no more connections
                if not self.connected_to[connection_name]:
                    del self.connected_to[connection_name]

                return True
            else:
                logger.warning(f"Connection not found: {self} {connection_name} to {other_component_id} {other_connection}")
                return False

        # If no specific connection provided, disconnect all connections at this point
        del self.connected_to[connection_name]
        logger.debug(f"Disconnected all connections from {self} {connection_name}")
        return True

    def get_connected_components(self):
        """Get all connected components.

        Returns:
            List of tuples (component_id, connection_name, other_connection)
        """
        connections = []
        for connection_name, conn_list in self.connected_to.items():
            for other_id, other_connection in conn_list:
                connections.append((other_id, connection_name, other_connection))
        return connections

    def is_connected(self, connection_name):
        """Check if the given connection has any connections.

        Args:
            connection_name: Name of the connection point

        Returns:
            True if connected, False otherwise
        """
        return connection_name in self.connected_to and len(self.connected_to[connection_name]) > 0


    @abstractmethod
    def calculate(self, simulator, time_step):
        """Calculate the component state for the current time step.

        Args:
            simulator: CircuitSimulator instance
            time_step: Time step in seconds

        Returns:
            Dictionary of updated state values
        """
        pass

    @abstractmethod
    def apply(self, state_updates):
        """Apply state updates to the component.

        Args:
            state_updates: Dictionary of state updates
        """
        pass

    def get_voltage(self, connection_name):
        """Get the voltage at the given connection.

        Args:
            connection_name: Name of the connection point

        Returns:
            Voltage value or None if not available
        """
        if 'voltages' in self.state and connection_name in self.state['voltages']:
            return self.state['voltages'][connection_name]
        return None

    def get_current(self, connection_name):
        """Get the current at the given connection.

        Args:
            connection_name: Name of the connection point

        Returns:
            Current value or None if not available
        """
        if 'currents' in self.state and connection_name in self.state['currents']:
            return self.state['currents'][connection_name]
        return None

    def get_property(self, name, default=None):
        """Get a component property.

        Args:
            name: Property name
            default: Default value if property not found

        Returns:
            Property value or default if not found
        """
        return self.properties.get(name, default)

    def set_property(self, name, value):
        """Set a component property.

        Args:
            name: Property name
            value: Property value
        """
        self.properties[name] = value

    def to_dict(self):
        """Convert component to dictionary.

        Returns:
            Dictionary representation of the component
        """
        return {
            'id': self.id,
            'component_id': self.component_id,
            'position': self.position,
            'rotation': self.rotation,
            'properties': self.properties,
            'connected_to': self.connected_to,
            'size': self.size,
            'state': self.state
        }

    @classmethod
    def from_dict(cls, data):
        """Create component from dictionary.

        Args:
            data: Dictionary representation of the component

        Returns:
            Component instance
        """
        component = cls(
            component_id=data.get('component_id'),
            position=tuple(data.get('position', (0, 0))),
            rotation=data.get('rotation', 0),
            properties=data.get('properties', {})
        )
        component.id = data.get('id', component.id)
        component.connected_to = data.get('connected_to', {})
        component.size = tuple(data.get('size', (1, 1)))
        component.state = data.get('state', {})
        return component

    def __str__(self):
        return f"{self.__class__.__name__}({self.id})"

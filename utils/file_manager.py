"""
Circuit Simulator - File Manager
-----------------------------
This module handles saving and loading circuits to/from files.
"""

import os
import json
import logging
import datetime
from pathlib import Path

import config
from components.passive_components import Resistor, Capacitor, Inductor, Ground
from components.active_components import (
    DCVoltageSource, ACVoltageSource, DCCurrentSource, Diode, LED, BJT, Switch
)

logger = logging.getLogger(__name__)


class FileManager:
    """File manager for saving and loading circuits."""

    def __init__(self, simulator, db_manager):
        """Initialize the file manager.

        Args:
            simulator: CircuitSimulator instance
            db_manager: DatabaseManager instance
        """
        self.simulator = simulator
        self.db_manager = db_manager

        # Current file path
        self.current_file = None

        # Recent files list
        self.recent_files = []
        self._load_recent_files()

    def save_circuit(self):
        """Save the current circuit to the current file.

        Returns:
            True if successful, False otherwise
        """
        if not self.current_file:
            # No current file, use save as
            return self.save_circuit_as()

        return self._save_to_file(self.current_file)

    def save_circuit_as(self, file_path=None):
        """Save the current circuit to a new file.

        Args:
            file_path: Path to save the circuit to

        Returns:
            True if successful, False otherwise
        """
        if file_path:
            self.current_file = file_path
            return self._save_to_file(file_path)

        return False

    def load_circuit(self, file_path):
        """Load a circuit from a file.

        Args:
            file_path: Path to the circuit file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read the file
            with open(file_path, "r") as f:
                data = json.load(f)

            # Clear the current circuit
            self.simulator.clear()

            # Load components manually first
            components_data = data.get('components', {})
            for component_id, component_data in components_data.items():
                # Determine component type
                component_type = self._map_component_type(component_data)

                if component_type:
                    # Create the component with the right properties
                    component = self._create_component(component_type, component_data.get('properties', {}))

                    if component:
                        # Set the same ID
                        component.id = component_id

                        # Set position and rotation
                        component.position = tuple(component_data.get('position', (0, 0)))
                        component.set_rotation(component_data.get('rotation', 0))

                        # Set connected_to information
                        component.connected_to = component_data.get('connected_to', {})

                        # Set state if available
                        if 'state' in component_data:
                            component.state = component_data['state']

                        # Add to simulator
                        self.simulator.add_component(component)
                    else:
                        logger.error(f"Failed to create component of type {component_type}")
                else:
                    logger.error(f"Unknown component type: {component_data}")

            # Build the circuit from the loaded components
            self.simulator.build_circuit_from_components()

            # Set current file
            self.current_file = file_path

            # Add to recent files
            self.add_recent_file(file_path)

            return True

        except Exception as e:
            logger.error(f"Error loading circuit from {file_path}: {e}")
            return False

    def load_example(self, example_name):
        """Load an example circuit.

        Args:
            example_name: Name of the example circuit

        Returns:
            True if successful, False otherwise
        """
        # Find the example file
        examples_dir = config.EXAMPLES_DIR
        example_file = None

        # Check if the example_name is a file path
        if os.path.isfile(example_name):
            example_file = example_name
        else:
            # Look for a file with the example name
            for file in os.listdir(examples_dir):
                if file.endswith(".circuit") and example_name in file:
                    example_file = os.path.join(examples_dir, file)
                    break

        if not example_file:
            logger.error(f"Example circuit not found: {example_name}")
            return False

        # Load the circuit
        return self.load_circuit(example_file)

    def _save_to_file(self, file_path):
        """Save the circuit to a file.

        Args:
            file_path: Path to save the circuit to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get circuit data
            data = self.simulator.to_dict()

            # Add metadata
            data["metadata"] = {
                "version": "1.0",
                "created": datetime.datetime.now().isoformat(),
                "description": ""
            }

            # Write to file
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Circuit saved to {file_path}")

            # Add to recent files
            self.add_recent_file(file_path)

            return True

        except Exception as e:
            logger.error(f"Error saving circuit to {file_path}: {e}")
            return False

    def add_recent_file(self, file_path):
        """Add a file to the recent files list.

        Args:
            file_path: Path to the file
        """
        # Convert to absolute path
        file_path = os.path.abspath(file_path)

        # Remove if already in the list
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)

        # Add to the beginning of the list
        self.recent_files.insert(0, file_path)

        # Keep only the N most recent files
        self.recent_files = self.recent_files[:10]

        # Save the list
        self._save_recent_files()

    def get_recent_files(self):
        """Get the list of recent files.

        Returns:
            List of file paths
        """
        # Filter out files that don't exist
        valid_files = [f for f in self.recent_files if os.path.isfile(f)]

        # Update the list if files were removed
        if len(valid_files) != len(self.recent_files):
            self.recent_files = valid_files
            self._save_recent_files()

        return valid_files

    def clear_recent_files(self):
        """Clear the recent files list."""
        self.recent_files = []
        self._save_recent_files()

    def _load_recent_files(self):
        """Load the recent files list from disk."""
        recent_files_path = Path(config.USER_DATA_DIR) / "recent_files.json"

        if recent_files_path.exists():
            try:
                with open(recent_files_path, "r") as f:
                    self.recent_files = json.load(f)
            except Exception as e:
                logger.error(f"Error loading recent files: {e}")
                self.recent_files = []

    def _save_recent_files(self):
        """Save the recent files list to disk."""
        recent_files_path = Path(config.USER_DATA_DIR) / "recent_files.json"

        try:
            with open(recent_files_path, "w") as f:
                json.dump(self.recent_files, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving recent files: {e}")

    def get_example_circuits(self):
        """Get a list of example circuits.

        Returns:
            List of (name, path) tuples
        """
        examples_dir = config.EXAMPLES_DIR
        examples = []

        if not os.path.isdir(examples_dir):
            return examples

        # Find all .circuit files in the examples directory
        for file in os.listdir(examples_dir):
            if file.endswith(".circuit"):
                name = file.replace(".circuit", "").replace("_", " ").title()
                path = os.path.join(examples_dir, file)
                examples.append((name, path))

        return sorted(examples)

    def _create_component_from_dict(self, data):
        """Create a component from a dictionary.

        Args:
            data: Dictionary with component data

        Returns:
            Component object or None if creation failed
        """
        # Determine component type
        component_type = data.get("component_type")

        if not component_type:
            # Try to determine the type from the data
            component_type = self._map_component_type(data)

        if not component_type:
            logger.error(f"Unknown component type: {data}")
            return None

        # Create the component
        component = self._create_component(component_type, data.get("properties", {}))

        if not component:
            return None

        # Set component ID, position, and rotation
        if "id" in data:
            component.id = data["id"]

        if "position" in data:
            component.position = tuple(data["position"])

        if "rotation" in data:
            component.set_rotation(data["rotation"])

        # Set connected_to information if available
        if "connected_to" in data:
            component.connected_to = data["connected_to"]

        # Set state if available
        if "state" in data:
            component.state = data["state"]

        return component

    def _create_component(self, component_type, properties):
        """Create a component of the given type.

        Args:
            component_type: Component type string (class name)
            properties: Component properties dictionary

        Returns:
            Component instance or None if creation failed
        """
        try:
            if component_type == "Resistor":
                return Resistor(properties=properties)
            elif component_type == "Capacitor":
                return Capacitor(properties=properties)
            elif component_type == "Inductor":
                return Inductor(properties=properties)
            elif component_type == "Ground":
                return Ground(properties=properties)
            elif component_type == "DCVoltageSource":
                return DCVoltageSource(properties=properties)
            elif component_type == "ACVoltageSource":
                return ACVoltageSource(properties=properties)
            elif component_type == "DCCurrentSource":
                return DCCurrentSource(properties=properties)
            elif component_type == "Diode":
                return Diode(properties=properties)
            elif component_type == "LED":
                return LED(properties=properties)
            elif component_type == "BJT":
                return BJT(properties=properties)
            elif component_type == "Switch":
                return Switch(properties=properties)
            else:
                logger.error(f"Unknown component type: {component_type}")
                return None
        except Exception as e:
            logger.error(f"Error creating component of type {component_type}: {e}")
            return None

    def _map_component_type(self, data):
        """Map component type from saved data to class name.

        Args:
            data: Component data dictionary

        Returns:
            Component class name or None if unknown
        """
        # Extract component ID to determine type
        component_id = data.get('id', '')

        # Map based on ID prefix
        if component_id.startswith('resistor_'):
            return 'Resistor'
        elif component_id.startswith('capacitor_'):
            return 'Capacitor'
        elif component_id.startswith('inductor_'):
            return 'Inductor'
        elif component_id.startswith('dc_source_') or component_id.startswith('dc_voltage_'):
            return 'DCVoltageSource'
        elif component_id.startswith('ac_source_') or component_id.startswith('ac_voltage_'):
            return 'ACVoltageSource'
        elif component_id.startswith('dc_current_'):
            return 'DCCurrentSource'
        elif component_id.startswith('diode_'):
            return 'Diode'
        elif component_id.startswith('led_'):
            return 'LED'
        elif component_id.startswith('bjt_'):
            return 'BJT'
        elif component_id.startswith('switch_'):
            return 'Switch'
        elif component_id.startswith('ground_'):
            return 'Ground'

        # Check for properties that might indicate the type
        properties = data.get('properties', {})

        if 'resistance' in properties:
            return 'Resistor'
        elif 'capacitance' in properties:
            return 'Capacitor'
        elif 'inductance' in properties:
            return 'Inductor'
        elif 'voltage' in properties:
            return 'DCVoltageSource'
        elif 'amplitude' in properties and 'frequency' in properties:
            return 'ACVoltageSource'
        elif 'current' in properties:
            return 'DCCurrentSource'
        elif 'forward_voltage' in properties:
            if 'color' in properties:
                return 'LED'
            else:
                return 'Diode'
        elif 'gain' in properties:
            return 'BJT'

        # If we can't determine the type, log a warning and return None
        logger.warning(f"Could not determine component type for: {component_id}")
        return None

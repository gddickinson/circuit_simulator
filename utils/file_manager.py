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
            
            # Load the circuit
            success = self.simulator.from_dict(data, self._create_component_from_dict)
            
            if success:
                # Set current file
                self.current_file = file_path
                
                # Add to recent files
                self.add_recent_file(file_path)
                
                return True
            
            return False
        
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
        component_type = data.get("component_type")
        
        if not component_type:
            # Try to infer from the component class name
            component_classes = {
                "Resistor": Resistor,
                "Capacitor": Capacitor,
                "Inductor": Inductor,
                "Ground": Ground,
                "DCVoltageSource": DCVoltageSource,
                "ACVoltageSource": ACVoltageSource,
                "DCCurrentSource": DCCurrentSource,
                "Diode": Diode,
                "LED": LED,
                "BJT": BJT,
                "Switch": Switch
            }
            
            for class_name, component_class in component_classes.items():
                if class_name.lower() in data.get("class_name", "").lower():
                    component_type = class_name
                    break
        
        if not component_type:
            logger.error(f"Unknown component type: {data}")
            return None
        
        # Create the component based on type
        if component_type == "Resistor":
            component = Resistor(properties=data.get("properties"))
        elif component_type == "Capacitor":
            component = Capacitor(properties=data.get("properties"))
        elif component_type == "Inductor":
            component = Inductor(properties=data.get("properties"))
        elif component_type == "Ground":
            component = Ground(properties=data.get("properties"))
        elif component_type == "DCVoltageSource":
            component = DCVoltageSource(properties=data.get("properties"))
        elif component_type == "ACVoltageSource":
            component = ACVoltageSource(properties=data.get("properties"))
        elif component_type == "DCCurrentSource":
            component = DCCurrentSource(properties=data.get("properties"))
        elif component_type == "Diode":
            component = Diode(properties=data.get("properties"))
        elif component_type == "LED":
            component = LED(properties=data.get("properties"))
        elif component_type == "BJT":
            component = BJT(properties=data.get("properties"))
        elif component_type == "Switch":
            component = Switch(properties=data.get("properties"))
        else:
            logger.error(f"Unknown component type: {component_type}")
            return None
        
        # Set component ID, position, and rotation
        if "id" in data:
            component.id = data["id"]
        
        if "position" in data:
            component.position = tuple(data["position"])
        
        if "rotation" in data:
            component.set_rotation(data["rotation"])
        
        return component

"""
Circuit Simulator - Configuration
--------------------------------
This module contains configuration settings for the circuit simulator.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Application paths
BASE_DIR = Path(__file__).resolve().parent
RESOURCES_DIR = BASE_DIR / "gui" / "resources"
EXAMPLES_DIR = BASE_DIR / "examples" / "saved_circuits"
USER_DATA_DIR = Path.home() / ".circuit_simulator"
DATABASE_PATH = USER_DATA_DIR / "circuit_simulator.db"

# Ensure directories exist
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# Simulation settings
SIMULATION_TIMESTEP = 0.001  # seconds
MAX_SIMULATION_STEPS = 10000
CONVERGENCE_THRESHOLD = 1e-6
MAX_ITERATIONS = 100

# GUI settings
GRID_SIZE = 20  # pixels
COMPONENT_SIZE = 60  # pixels
WIRE_THICKNESS = 2  # pixels
ZOOM_FACTOR_MIN = 0.5
ZOOM_FACTOR_MAX = 2.0
ZOOM_STEP = 0.1

# Colors
BACKGROUND_COLOR = "#FFFFFF"
GRID_COLOR = "#EEEEEE"
WIRE_COLOR = "#000000"
SELECTED_COLOR = "#3498DB"
VOLTAGE_HIGH_COLOR = "#E74C3C"
VOLTAGE_LOW_COLOR = "#2ECC71"
CURRENT_COLOR = "#F39C12"

# Component default properties
DEFAULT_RESISTANCE = 1000.0  # ohms
DEFAULT_CAPACITANCE = 1e-6  # farads 
DEFAULT_INDUCTANCE = 1e-3  # henries
DEFAULT_VOLTAGE = 5.0  # volts
DEFAULT_CURRENT = 0.01  # amperes
DEFAULT_FREQUENCY = 1000.0  # hertz

# Database settings
DB_TIMEOUT = 30  # seconds


def load_config(config_file):
    """Load configuration from a JSON file."""
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Update globals with values from config file
        globals().update(config_data)
        logger.info(f"Loaded configuration from {config_file}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")


def save_config(config_file=None):
    """Save current configuration to a JSON file."""
    if config_file is None:
        config_file = USER_DATA_DIR / "config.json"
    
    config_data = {k: v for k, v in globals().items() 
                  if k.isupper() and not k.startswith('_')}
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        logger.info(f"Saved configuration to {config_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False


# Create default config if it doesn't exist
default_config_path = USER_DATA_DIR / "config.json"
if not default_config_path.exists():
    save_config(default_config_path)

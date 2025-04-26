"""
Circuit Simulator - Logger
------------------------
This module provides logging functionality for the circuit simulator.
"""

import os
import logging
import datetime
from enum import Enum, auto
from pathlib import Path

import config


class SimulationEvent(Enum):
    """Enum for simulation events."""
    SIMULATION_STARTED = auto()
    SIMULATION_PAUSED = auto()
    SIMULATION_RESUMED = auto()
    SIMULATION_STOPPED = auto()
    SIMULATION_RESET = auto()
    SIMULATION_UPDATED = auto()
    CIRCUIT_BUILT = auto()
    COMPONENT_ADDED = auto()
    COMPONENT_REMOVED = auto()
    CONNECTION_ADDED = auto()
    CONNECTION_REMOVED = auto()
    ERROR_OCCURRED = auto()


def setup_logger(level=logging.INFO):
    """Set up the root logger.
    
    Args:
        level: Logging level
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set level
    root_logger.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    root_logger.addHandler(console_handler)
    
    # Log startup message
    root_logger.info(f"Logger initialized at level {logging.getLevelName(level)}")
    
    return root_logger


def setup_file_logger(logger_name, level=logging.DEBUG):
    """Set up a file logger for a specific module.
    
    Args:
        logger_name: Logger name (usually __name__)
        level: Logging level
        
    Returns:
        Logger instance
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(config.USER_DATA_DIR) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file path with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{logger_name}_{timestamp}.log"
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(file_handler)
    
    # Log startup message
    logger.info(f"File logger initialized at level {logging.getLevelName(level)}")
    logger.info(f"Logging to {log_file}")
    
    return logger

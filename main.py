#!/usr/bin/env python3
"""
Circuit Simulator - Main Entry Point
-----------------------------------
This module initializes and runs the circuit simulator application.
"""

import sys
import os
import argparse
import logging
from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow
from database.db_manager import DatabaseManager
from simulation.simulator import CircuitSimulator
from utils.logger import setup_logger
import config


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Circuit Simulator')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--load', type=str, help='Load a saved circuit file')
    parser.add_argument('--example', type=str, help='Load an example circuit')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    return parser.parse_args()


def main():
    """Main application entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logger(log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting Circuit Simulator")
    
    # Load configuration
    if args.config:
        config.load_config(args.config)
    
    # Initialize the database
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    
    # Initialize the simulator
    simulator = CircuitSimulator()
    
    # Create and run the application
    app = QApplication(sys.argv)
    app.setApplicationName("Circuit Simulator")
    
    # Create main window
    main_window = MainWindow(simulator, db_manager)
    
    # Load circuit if specified
    if args.load:
        main_window.load_circuit(args.load)
    elif args.example:
        main_window.load_example(args.example)
    
    # Show the main window
    main_window.show()
    
    # Run the application event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

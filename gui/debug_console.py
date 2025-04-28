"""
Circuit Simulator - Debug Console
-------------------------------
This module provides a debug console for the circuit simulator.
"""

import logging
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QCheckBox, QGroupBox,
    QSplitter, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

from components.active_components import (
    DCVoltageSource, ACVoltageSource, DCCurrentSource, Diode, LED, BJT, Switch
)
from components.passive_components import Resistor, Capacitor, Inductor, Ground
import config
from utils.logger import SimulationEvent

logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """Logging handler that emits signals for log messages."""

    def __init__(self, parent=None):
        """Initialize the log handler."""
        super().__init__()
        # The PyQt signal needs to be a class attribute, not an instance attribute
        # This is a crucial distinction in PyQt

    def emit(self, record):
        """Emit a log record.

        Args:
            record: LogRecord instance
        """
        # Format the record
        message = self.format(record)

        # Emit the signal
        # Instead of using a signal, we'll use a callback function
        if hasattr(self, 'callback') and callable(self.callback):
            self.callback(message, record.levelno)


class LogPanel(QTextEdit):
    """Panel for displaying log messages."""

    def __init__(self, parent=None):
        """Initialize the log panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Set up the text edit
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setFont(QFont("Courier", 9))

        # Log colors
        self.log_colors = {
            logging.DEBUG: QColor(100, 100, 100),    # Gray
            logging.INFO: QColor(0, 0, 0),          # Black
            logging.WARNING: QColor(255, 165, 0),    # Orange
            logging.ERROR: QColor(255, 0, 0),        # Red
            logging.CRITICAL: QColor(128, 0, 128)    # Purple
        }

        # Create a log handler
        self.log_handler = LogHandler()
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        # Set the callback function
        self.log_handler.callback = self.append_log

        # Add the handler to the root logger
        logging.getLogger().addHandler(self.log_handler)

    def append_log(self, message, level):
        """Append a log message.

        Args:
            message: Log message text
            level: Log level (DEBUG, INFO, etc.)
        """
        # Create a text format with the appropriate color
        text_format = QTextCharFormat()
        if level in self.log_colors:
            text_format.setForeground(self.log_colors[level])

        # Create a cursor and set its format
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(message + '\n', text_format)

        # Keep the cursor at the end
        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class CommandLineWidget(QLineEdit):
    """Command line for entering debug commands."""

    # Signal emitted when a command is entered
    command_entered = pyqtSignal(str)

    def __init__(self, parent=None):
        """Initialize the command line.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Set up the line edit
        self.setPlaceholderText("Enter debug command...")

        # Command history
        self.command_history = []
        self.history_index = -1

    def keyPressEvent(self, event):
        """Handle key press events.

        Args:
            event: QKeyEvent
        """
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Get the command
            command = self.text().strip()

            if command:
                # Add to history
                self.command_history.append(command)
                self.history_index = len(self.command_history)

                # Emit the signal
                self.command_entered.emit(command)

                # Clear the input
                self.clear()

            event.accept()

        elif event.key() == Qt.Key_Up:
            # Navigate up in command history
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                self.setText(self.command_history[self.history_index])
            event.accept()

        elif event.key() == Qt.Key_Down:
            # Navigate down in command history
            if self.command_history and self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.setText(self.command_history[self.history_index])
            else:
                # Clear the input if at the end of history
                self.history_index = len(self.command_history)
                self.clear()
            event.accept()

        else:
            # Pass to base class for normal handling
            super().keyPressEvent(event)


class DebugConsoleWidget(QWidget):
    """Debug console for the circuit simulator."""

    def __init__(self, simulator):
        """Initialize the debug console.

        Args:
            simulator: CircuitSimulator instance
        """
        super().__init__()

        self.simulator = simulator

        # Set up the UI
        self._create_ui()

        # Connect to simulator events
        self.simulator.add_event_listener(self._on_simulation_event)

    def _create_ui(self):
        """Create the UI elements."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create splitter
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # Create log panel
        self.log_panel = LogPanel()
        splitter.addWidget(self.log_panel)

        # Create control panel
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        splitter.addWidget(control_panel)

        # Command line
        command_layout = QHBoxLayout()
        control_layout.addLayout(command_layout)

        command_layout.addWidget(QLabel("Command:"))

        self.command_line = CommandLineWidget()
        self.command_line.command_entered.connect(self._execute_command)
        command_layout.addWidget(self.command_line)

        # Create controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        controls_group.setLayout(controls_layout)
        control_layout.addWidget(controls_group)

        # Create buttons
        buttons_layout = QHBoxLayout()
        controls_layout.addLayout(buttons_layout)

        # Print components button
        print_components_button = QPushButton("Print Components")
        print_components_button.clicked.connect(self._print_components)
        buttons_layout.addWidget(print_components_button)

        # Print nodes button
        print_nodes_button = QPushButton("Print Nodes")
        print_nodes_button.clicked.connect(self._print_nodes)
        buttons_layout.addWidget(print_nodes_button)

        # Clear log button
        clear_log_button = QPushButton("Clear Log")
        clear_log_button.clicked.connect(self.log_panel.clear)
        buttons_layout.addWidget(clear_log_button)

        # Test LED circuit button
        test_led_button = QPushButton("Test LED Circuit")
        test_led_button.clicked.connect(self.test_led_circuit)
        buttons_layout.addWidget(test_led_button)

        # Test resistor circuit button
        test_resistor_button = QPushButton("Test resistor Circuit")
        test_resistor_button.clicked.connect(self.test_resistor_circuit)
        buttons_layout.addWidget(test_resistor_button)

        # Log level combo
        log_level_layout = QHBoxLayout()
        controls_layout.addLayout(log_level_layout)

        log_level_layout.addWidget(QLabel("Log Level:"))

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.currentTextChanged.connect(self._set_log_level)
        log_level_layout.addWidget(self.log_level_combo)

        # Set initial log level
        self._set_log_level("INFO")

        # Create debug options group
        debug_group = QGroupBox("Debug Options")
        debug_layout = QVBoxLayout()
        debug_group.setLayout(debug_layout)
        control_layout.addWidget(debug_group)

        # Debug checkboxes
        self.show_node_voltages_check = QCheckBox("Show Node Voltages")
        self.show_node_voltages_check.setChecked(False)
        debug_layout.addWidget(self.show_node_voltages_check)

        self.show_component_values_check = QCheckBox("Show Component Values")
        self.show_component_values_check.setChecked(True)
        debug_layout.addWidget(self.show_component_values_check)

        self.pause_on_error_check = QCheckBox("Pause Simulation on Error")
        self.pause_on_error_check.setChecked(True)
        debug_layout.addWidget(self.pause_on_error_check)

        # Create stats display
        stats_group = QGroupBox("Simulation Statistics")
        stats_layout = QVBoxLayout()
        stats_group.setLayout(stats_layout)
        control_layout.addWidget(stats_group)

        # Stats labels
        stats_form_layout = QHBoxLayout()
        stats_layout.addLayout(stats_form_layout)

        # Left column
        stats_left_layout = QVBoxLayout()
        stats_form_layout.addLayout(stats_left_layout)

        stats_left_layout.addWidget(QLabel("Time:"))
        stats_left_layout.addWidget(QLabel("FPS:"))
        stats_left_layout.addWidget(QLabel("Iterations:"))
        stats_left_layout.addWidget(QLabel("Solve Time:"))

        # Right column (values)
        stats_right_layout = QVBoxLayout()
        stats_form_layout.addLayout(stats_right_layout)

        self.time_value = QLabel("0.000 s")
        stats_right_layout.addWidget(self.time_value)

        self.fps_value = QLabel("0.0")
        stats_right_layout.addWidget(self.fps_value)

        self.iterations_value = QLabel("0")
        stats_right_layout.addWidget(self.iterations_value)

        self.solve_time_value = QLabel("0.000 ms")
        stats_right_layout.addWidget(self.solve_time_value)

        # Set up timer for updating stats
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(100)  # Update every 100 ms

    def _execute_command(self, command):
        """Execute a debug command.

        Args:
            command: Command string
        """
        logger.info(f"Executing command: {command}")

        # Parse the command
        parts = command.split()
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd == "help":
                self._print_help()

            elif cmd == "print":
                if not args:
                    logger.warning("Missing argument for 'print' command")
                    return

                what = args[0].lower()
                if what == "components":
                    self._print_components()
                elif what == "nodes":
                    self._print_nodes()
                elif what == "stats":
                    self._print_stats()
                elif what == "history":
                    if len(args) > 1:
                        self._print_history(args[1])
                    else:
                        logger.warning("Missing component ID for 'print history'")
                else:
                    logger.warning(f"Unknown print target: {what}")

            elif cmd == "clear":
                self.log_panel.clear()

            elif cmd == "reset":
                self.simulator.reset_simulation()
                logger.info("Simulation reset")

            elif cmd == "start":
                if not self.simulator.running:
                    self.simulator.start_simulation()
                    logger.info("Simulation started")
                else:
                    logger.info("Simulation already running")

            elif cmd == "stop":
                if self.simulator.running:
                    self.simulator.stop_simulation()
                    logger.info("Simulation stopped")
                else:
                    logger.info("Simulation not running")

            elif cmd == "pause":
                if self.simulator.running and not self.simulator.paused:
                    self.simulator.pause_simulation()
                    logger.info("Simulation paused")
                else:
                    logger.info("Simulation not running or already paused")

            elif cmd == "resume":
                if self.simulator.running and self.simulator.paused:
                    self.simulator.resume_simulation()
                    logger.info("Simulation resumed")
                else:
                    logger.info("Simulation not running or not paused")

            elif cmd == "step":
                # Perform a single simulation step
                self.simulator.update()
                logger.info(f"Stepped simulation to t={self.simulator.simulation_time:.3f} s")

            elif cmd == "log":
                if not args:
                    logger.warning("Missing log level")
                    return

                level = args[0].upper()
                self.log_level_combo.setCurrentText(level)

            elif cmd == "debug":
                if not args:
                    logger.warning("Missing debug option")
                    return

                option = args[0].lower()
                enabled = len(args) < 2 or args[1].lower() not in ("false", "off", "0")

                if option == "voltages":
                    self.show_node_voltages_check.setChecked(enabled)
                    logger.info(f"Node voltages display: {'enabled' if enabled else 'disabled'}")

                elif option == "values":
                    self.show_component_values_check.setChecked(enabled)
                    logger.info(f"Component values display: {'enabled' if enabled else 'disabled'}")

                elif option == "pause_on_error":
                    self.pause_on_error_check.setChecked(enabled)
                    logger.info(f"Pause on error: {'enabled' if enabled else 'disabled'}")

                else:
                    logger.warning(f"Unknown debug option: {option}")

            elif cmd == "exit":
                # This would close the application, but we'll just log for now
                logger.info("Exit command received - use the application's close button to exit")

            else:
                logger.warning(f"Unknown command: {cmd}")

        except Exception as e:
            logger.error(f"Error executing command: {e}")

    def _print_help(self):
        """Print help information."""
        help_text = """
Available commands:
  help                         - Show this help
  print components             - Print all components
  print nodes                  - Print all nodes
  print stats                  - Print simulation statistics
  print history <component_id> - Print history for a component
  clear                        - Clear the log
  reset                        - Reset the simulation
  start                        - Start the simulation
  stop                         - Stop the simulation
  pause                        - Pause the simulation
  resume                       - Resume the simulation
  step                         - Perform a single simulation step
  log <level>                  - Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  debug voltages [on|off]      - Show/hide node voltages
  debug values [on|off]        - Show/hide component values
  debug pause_on_error [on|off]- Enable/disable pausing on errors
  exit                         - Exit the application
"""
        logger.info(help_text)

    def _print_components(self):
        """Print all components."""
        components = self.simulator.components

        if not components:
            logger.info("No components in circuit")
            return

        logger.info(f"Circuit has {len(components)} components:")

        for component_id, component in components.items():
            logger.info(f"  {component.__class__.__name__} (ID: {component_id[:8]}...), Position: {component.position}")

    def _print_nodes(self):
        """Print all nodes in the circuit."""
        nodes = self.simulator.nodes

        if not nodes:
            logger.info("No nodes in circuit")
            return

        logger.info(f"Circuit has {len(nodes)} nodes:")

        for node_id, node in nodes.items():
            # Format components connected to this node
            connected_components = []
            for component_id, component in node.components.items():
                class_name = component.__class__.__name__
                connected_components.append(f"{class_name} ({component_id[0][:8]}...)")

            components_str = ", ".join(connected_components)

            logger.info(f"  Node {node_id}: Voltage = {node.voltage:.3f} V, Connected to: {components_str}")

    def _print_stats(self):
        """Print simulation statistics."""
        stats = self.simulator.stats

        logger.info("Simulation Statistics:")
        logger.info(f"  Time: {self.simulator.simulation_time:.3f} s")
        logger.info(f"  FPS: {stats.get('fps', 0.0):.1f}")
        logger.info(f"  Iterations: {stats.get('iterations', 0)}")
        logger.info(f"  Solve Time: {stats.get('solve_time', 0.0) * 1000:.3f} ms")
        logger.info(f"  Component Update Time: {stats.get('component_update_time', 0.0) * 1000:.3f} ms")
        logger.info(f"  Node Update Time: {stats.get('node_update_time', 0.0) * 1000:.3f} ms")
        logger.info(f"  Total Time: {stats.get('total_time', 0.0) * 1000:.3f} ms")

    def _print_history(self, component_id):
        """Print history for a component.

        Args:
            component_id: Component ID
        """
        # Find the component
        component = None
        for cid, c in self.simulator.components.items():
            if cid.startswith(component_id):
                component = c
                component_id = cid
                break

        if not component:
            logger.warning(f"Component not found: {component_id}")
            return

        logger.info(f"History for {component.__class__.__name__} (ID: {component_id[:8]}...):")

        # Print history for each state value
        for key, history in self.simulator.history.get(component_id, {}).items():
            if not history:
                continue

            # Format the values
            formatted_history = []
            for time, value in history[-10:]:  # Show only the last 10 entries
                if isinstance(value, bool):
                    formatted_history.append(f"(t={time:.3f}, {value})")
                elif isinstance(value, (int, float)):
                    formatted_history.append(f"(t={time:.3f}, {value:.3g})")
                else:
                    formatted_history.append(f"(t={time:.3f}, {value})")

            values_str = ", ".join(formatted_history)

            logger.info(f"  {key}: {values_str}")

    def _set_log_level(self, level_name):
        """Set the log level.

        Args:
            level_name: Log level name (DEBUG, INFO, etc.)
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }

        if level_name in level_map:
            level = level_map[level_name]
            logging.getLogger().setLevel(level)
            logger.info(f"Log level set to {level_name}")

    def _update_stats(self):
        """Update the statistics display."""
        # Get simulation stats
        stats = self.simulator.stats

        # Update labels
        self.time_value.setText(f"{self.simulator.simulation_time:.3f} s")
        self.fps_value.setText(f"{stats.get('fps', 0.0):.1f}")
        self.iterations_value.setText(f"{stats.get('iterations', 0)}")
        self.solve_time_value.setText(f"{stats.get('solve_time', 0.0) * 1000:.3f} ms")

    def _on_simulation_event(self, event_type, data):
        """Handle simulation events.

        Args:
            event_type: Event type from SimulationEvent enum
            data: Event data
        """
        if event_type == SimulationEvent.SIMULATION_STARTED:
            logger.info("Simulation started")

        elif event_type == SimulationEvent.SIMULATION_PAUSED:
            logger.info("Simulation paused")

        elif event_type == SimulationEvent.SIMULATION_STOPPED:
            logger.info("Simulation stopped")

        elif event_type == SimulationEvent.SIMULATION_RESET:
            logger.info("Simulation reset")

        elif event_type == SimulationEvent.CIRCUIT_BUILT:
            logger.info(f"Circuit built: {data.get('nodes', 0)} nodes, {data.get('components', 0)} components")

    def test_led_circuit(self):
        """Create a simple test circuit."""
        logger.info("Creating test circuit...")

        # Clear existing circuit
        self.simulator.clear()

        # Create a DC voltage source
        dc_source = DCVoltageSource(properties={'voltage': 5.0})
        dc_source.position = (0, 5)
        self.simulator.add_component(dc_source)
        logger.info(f"Added DC source: {dc_source.id}")

        # Create an LED
        led = LED(properties={'forward_voltage': 2.0, 'color': 'red'})
        led.position = (0, -5)
        self.simulator.add_component(led)
        logger.info(f"Added LED: {led.id}")

        # Connect the DC source positive terminal to the LED anode
        success1 = self.simulator.connect_components_at(
            dc_source.id, 'pos',
            led.id, 'anode'
        )
        logger.info(f"Connection 1 created: {success1}")

        # Connect the DC source negative terminal to the LED cathode
        success2 = self.simulator.connect_components_at(
            dc_source.id, 'neg',
            led.id, 'cathode'
        )
        logger.info(f"Connection 2 created: {success2}")

        # Build the circuit
        self.simulator.build_circuit_from_components()

        # Start the simulation
        self.simulator.start_simulation()

        logger.info("Test circuit created and simulation started")

    def test_resistor_circuit(self):
        """Create a test circuit with a DC voltage source and resistor."""
        logger.info("Creating resistor test circuit...")

        # Clear existing circuit
        self.simulator.clear()

        # Create DC voltage source
        dc_source = DCVoltageSource(properties={'voltage': 5.0})
        dc_source.position = (0, 3)
        dc_id = dc_source.id
        self.simulator.add_component(dc_source)
        logger.info(f"Added DC source: {dc_id}")

        # Create resistor
        resistor = Resistor(properties={'resistance': 1000.0})  # 1 kΩ
        resistor.position = (0, -3)
        res_id = resistor.id
        self.simulator.add_component(resistor)
        logger.info(f"Added resistor: {res_id}")

        # Connect them
        conn1 = self.simulator.connect_components_at(
            dc_id, 'pos',
            res_id, 'p1'
        )
        logger.info(f"Connected DCVoltageSource pos to resistor p1: {conn1}")

        conn2 = self.simulator.connect_components_at(
            dc_id, 'neg',
            res_id, 'p2'
        )
        logger.info(f"Connected DCVoltageSource neg to resistor p2: {conn2}")

        # Build the circuit
        self.simulator.build_circuit_from_components()

        # Start the simulation
        self.simulator.start_simulation()
        logger.info("Test circuit created and simulation started")

        # Run for a few steps
        for i in range(10):
            self.simulator.update()

        # Print results
        logger.info("Test Circuit Results:")
        logger.info(f"Resistor p1 voltage: {resistor.state.get('voltages', {}).get('p1', 0.0)}")
        logger.info(f"Resistor p2 voltage: {resistor.state.get('voltages', {}).get('p2', 0.0)}")
        logger.info(f"Resistor current: {resistor.state.get('currents', {}).get('p1', 0.0)}")
        logger.info(f"Resistor power: {resistor.state.get('power', 0.0)}")

        # Return success if there's a current flowing
        return abs(resistor.state.get('currents', {}).get('p1', 0.0)) > 1e-6

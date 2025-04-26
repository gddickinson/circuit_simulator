"""
Circuit Simulator - Analysis Panel
--------------------------------
This module provides a panel for displaying circuit analysis and measurements.
"""

import logging
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTabWidget, QSplitter, QFrame, QScrollArea,
    QGroupBox, QFormLayout, QCheckBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import config
from utils.logger import SimulationEvent

logger = logging.getLogger(__name__)


class MatplotlibCanvas(FigureCanvas):
    """Canvas for displaying matplotlib plots."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """Initialize a matplotlib canvas.

        Args:
            parent: Parent widget
            width: Figure width in inches
            height: Figure height in inches
            dpi: Figure resolution (dots per inch)
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)

        super().__init__(self.fig)
        self.setParent(parent)

        # Set up figure
        self.fig.tight_layout()

        # Make the canvas expandable
        FigureCanvas.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        FigureCanvas.updateGeometry(self)


class TimeSeriesPlot(QWidget):
    """Widget for displaying time series plots."""

    def __init__(self, simulator, parent=None):
        """Initialize a time series plot widget.

        Args:
            simulator: CircuitSimulator instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.simulator = simulator

        # Tracked components and signals
        self.tracked_components = {}  # {component_id: component}
        self.tracked_signals = {}     # {component_id: {signal_name: enabled}}

        # Set up the UI
        self._create_ui()

        # Initialize the plot
        self._init_plot()

    def _create_ui(self):
        """Create the UI elements."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create the matplotlib canvas
        self.canvas = MatplotlibCanvas(self, width=5, height=4, dpi=100)
        layout.addWidget(self.canvas)

        # Create the toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)

        # Create signal selection area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Create signal selection widget
        self.signal_widget = QWidget()
        scroll_area.setWidget(self.signal_widget)

        # Signal layout
        self.signal_layout = QVBoxLayout()
        self.signal_widget.setLayout(self.signal_layout)

        # Add a refresh button
        refresh_button = QPushButton("Refresh Components")
        refresh_button.clicked.connect(self._refresh_components)
        layout.addWidget(refresh_button)

    def _init_plot(self):
        """Initialize the plot."""
        # Clear the axes
        self.canvas.axes.clear()

        # Set up labels
        self.canvas.axes.set_xlabel('Time (s)')
        self.canvas.axes.set_ylabel('Value')
        self.canvas.axes.set_title('Circuit Signals')

        # Display grid
        self.canvas.axes.grid(True)

        # Update the canvas
        self.canvas.draw()

    def _refresh_components(self):
        """Refresh the list of components."""
        # Clear the signal layout
        for i in reversed(range(self.signal_layout.count())):
            item = self.signal_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        # Get all components from the simulator
        components = self.simulator.components

        # Update tracked components
        self.tracked_components = components

        # Add a group for each component
        for component_id, component in components.items():
            # Create a group box
            group = QGroupBox(f"{component.__class__.__name__} ({component_id[:8]})")
            group_layout = QVBoxLayout()
            group.setLayout(group_layout)

            # Add checkboxes for each signal
            signals = self._get_component_signals(component)

            # Initialize signal tracking for this component if needed
            if component_id not in self.tracked_signals:
                self.tracked_signals[component_id] = {}

            for signal_name, signal_label in signals:
                # Create checkbox
                checkbox = QCheckBox(signal_label)

                # Set initial state
                if signal_name in self.tracked_signals[component_id]:
                    checkbox.setChecked(self.tracked_signals[component_id][signal_name])
                else:
                    checkbox.setChecked(False)
                    self.tracked_signals[component_id][signal_name] = False

                # Connect checkbox to signal handler
                checkbox.stateChanged.connect(
                    lambda state, cid=component_id, sname=signal_name:
                    self._on_signal_toggled(cid, sname, state)
                )

                # Add to layout
                group_layout.addWidget(checkbox)

            # Add the group to the signal layout
            self.signal_layout.addWidget(group)

        # Add a stretch to push everything to the top
        self.signal_layout.addStretch()

    def _get_component_signals(self, component):
        """Get a list of signals available for a component.

        Args:
            component: Component object

        Returns:
            List of (signal_name, signal_label) tuples
        """
        signals = []

        # Common signals based on component type
        component_type = component.__class__.__name__

        if component_type in ['Resistor', 'Capacitor', 'Inductor', 'Diode', 'LED', 'Switch']:
            # Two-terminal components
            signals.append(('voltages.p1', 'Voltage P1'))
            signals.append(('voltages.p2', 'Voltage P2'))
            signals.append(('currents.p1', 'Current P1'))

            # Component-specific signals
            if component_type == 'Resistor':
                signals.append(('power', 'Power'))
            elif component_type == 'Capacitor':
                signals.append(('charge', 'Charge'))
                signals.append(('energy', 'Energy'))
            elif component_type == 'Inductor':
                signals.append(('flux', 'Flux'))
                signals.append(('energy', 'Energy'))
            elif component_type == 'Diode' or component_type == 'LED':
                signals.append(('power', 'Power'))
                signals.append(('conducting', 'Conducting State'))
                if component_type == 'LED':
                    signals.append(('brightness', 'Brightness'))

        elif component_type in ['DCVoltageSource', 'ACVoltageSource', 'DCCurrentSource']:
            # Source components
            signals.append(('voltages.pos', 'Voltage Pos'))
            signals.append(('voltages.neg', 'Voltage Neg'))
            signals.append(('currents.pos', 'Current Pos'))
            signals.append(('power', 'Power'))

            if component_type == 'ACVoltageSource':
                signals.append(('instantaneous_voltage', 'Instantaneous Voltage'))

        elif component_type == 'BJT':
            # Transistor signals
            signals.append(('voltages.collector', 'Voltage Collector'))
            signals.append(('voltages.base', 'Voltage Base'))
            signals.append(('voltages.emitter', 'Voltage Emitter'))
            signals.append(('currents.collector', 'Current Collector'))
            signals.append(('currents.base', 'Current Base'))
            signals.append(('currents.emitter', 'Current Emitter'))
            signals.append(('power', 'Power'))
            signals.append(('region', 'Operating Region'))

        return signals

    def _on_signal_toggled(self, component_id, signal_name, state):
        """Handle toggling a signal.

        Args:
            component_id: Component ID
            signal_name: Signal name
            state: Qt.Checked or Qt.Unchecked
        """
        # Update tracked signals
        self.tracked_signals[component_id][signal_name] = (state == Qt.Checked)

        # Redraw the plot
        self.update_plot()

    def update_plot(self):
        """Update the plot with current data."""
        # Clear the axes
        self.canvas.axes.clear()

        # Set up labels
        self.canvas.axes.set_xlabel('Time (s)')
        self.canvas.axes.set_ylabel('Value')
        self.canvas.axes.set_title('Circuit Signals')

        # Get data from simulator history
        for component_id, signals in self.tracked_signals.items():
            component = self.tracked_components.get(component_id)
            if not component:
                continue

            component_type = component.__class__.__name__

            for signal_name, enabled in signals.items():
                if not enabled:
                    continue

                # Get history data
                if '.' in signal_name:
                    category, sub_key = signal_name.split('.')
                    history = self.simulator.get_history(component_id, category, sub_key)
                else:
                    history = self.simulator.get_history(component_id, signal_name)

                if not history:
                    continue

                # Extract time and values
                times, values = zip(*history) if history else ([], [])

                # Skip non-numeric values (e.g. 'region' for transistors)
                if not all(isinstance(v, (int, float)) for v in values):
                    continue

                # Plot the data
                label = f"{component_type} - {signal_name}"
                self.canvas.axes.plot(times, values, label=label)

        # Add legend
        self.canvas.axes.legend()

        # Display grid
        self.canvas.axes.grid(True)

        # Update the canvas
        self.canvas.draw()


class MeasurementPanel(QWidget):
    """Widget for displaying real-time measurements."""

    def __init__(self, simulator, parent=None):
        """Initialize a measurement panel.

        Args:
            simulator: CircuitSimulator instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.simulator = simulator

        # Set up the UI
        self._create_ui()

    def _create_ui(self):
        """Create the UI elements."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Create measurement widget
        self.measurement_widget = QWidget()
        scroll_area.setWidget(self.measurement_widget)

        # Measurement layout
        self.measurement_layout = QVBoxLayout()
        self.measurement_widget.setLayout(self.measurement_layout)

        # Component measurements
        self.component_measurements = {}

        # Add a refresh button
        refresh_button = QPushButton("Refresh Measurements")
        refresh_button.clicked.connect(self.update_measurements)
        layout.addWidget(refresh_button)

        # Create initial measurements
        self.update_measurements()

    def update_measurements(self):
        """Update the measurements display."""
        # Clear the measurement layout
        for i in reversed(range(self.measurement_layout.count())):
            item = self.measurement_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        # Clear component measurements
        self.component_measurements = {}

        # Get all components from the simulator
        components = self.simulator.components

        # Add a group for each component
        for component_id, component in components.items():
            # Create a group box
            group = QGroupBox(f"{component.__class__.__name__} ({component_id[:8]})")
            group_layout = QFormLayout()
            group.setLayout(group_layout)

            # Add measurements based on component type
            self._add_component_measurements(component, group_layout)

            # Store the group layout reference
            self.component_measurements[component_id] = group_layout

            # Add the group to the measurement layout
            self.measurement_layout.addWidget(group)

        # Add circuit-wide measurements
        self._add_circuit_measurements()

        # Add a stretch to push everything to the top
        self.measurement_layout.addStretch()

    def _add_component_measurements(self, component, layout):
        """Add measurements for a component.

        Args:
            component: Component object
            layout: QFormLayout to add measurements to
        """
        component_type = component.__class__.__name__

        # Common measurements based on component type
        if component_type in ['Resistor', 'Capacitor', 'Inductor', 'Diode', 'LED', 'Switch']:
            # Voltages
            v_p1 = component.state.get('voltages', {}).get('p1', 0.0)
            v_p2 = component.state.get('voltages', {}).get('p2', 0.0)
            layout.addRow("Voltage P1:", QLabel(f"{v_p1:.3f} V"))
            layout.addRow("Voltage P2:", QLabel(f"{v_p2:.3f} V"))
            layout.addRow("Voltage Drop:", QLabel(f"{abs(v_p1 - v_p2):.3f} V"))

            # Current
            current = component.state.get('currents', {}).get('p1', 0.0)
            if abs(current) >= 1:
                layout.addRow("Current:", QLabel(f"{current:.3f} A"))
            elif abs(current) >= 1e-3:
                layout.addRow("Current:", QLabel(f"{current*1e3:.3f} mA"))
            else:
                layout.addRow("Current:", QLabel(f"{current*1e6:.3f} µA"))

            # Component-specific measurements
            if component_type == 'Resistor':
                # Power
                power = component.state.get('power', 0.0)
                if power >= 1:
                    layout.addRow("Power:", QLabel(f"{power:.3f} W"))
                elif power >= 1e-3:
                    layout.addRow("Power:", QLabel(f"{power*1e3:.3f} mW"))
                else:
                    layout.addRow("Power:", QLabel(f"{power*1e6:.3f} µW"))

                # Temperature
                temp = component.state.get('temperature', 25.0)
                layout.addRow("Temperature:", QLabel(f"{temp:.1f} °C"))

                # Resistance
                resistance = component.get_property('resistance', config.DEFAULT_RESISTANCE)
                if resistance >= 1e6:
                    layout.addRow("Resistance:", QLabel(f"{resistance/1e6:.1f} MΩ"))
                elif resistance >= 1e3:
                    layout.addRow("Resistance:", QLabel(f"{resistance/1e3:.1f} kΩ"))
                else:
                    layout.addRow("Resistance:", QLabel(f"{resistance:.1f} Ω"))

            elif component_type == 'Capacitor':
                # Charge
                charge = component.state.get('charge', 0.0)
                if abs(charge) >= 1:
                    layout.addRow("Charge:", QLabel(f"{charge:.3f} C"))
                elif abs(charge) >= 1e-3:
                    layout.addRow("Charge:", QLabel(f"{charge*1e3:.3f} mC"))
                elif abs(charge) >= 1e-6:
                    layout.addRow("Charge:", QLabel(f"{charge*1e6:.3f} µC"))
                else:
                    layout.addRow("Charge:", QLabel(f"{charge*1e9:.3f} nC"))

                # Energy
                energy = component.state.get('energy', 0.0)
                if energy >= 1:
                    layout.addRow("Energy:", QLabel(f"{energy:.3f} J"))
                elif energy >= 1e-3:
                    layout.addRow("Energy:", QLabel(f"{energy*1e3:.3f} mJ"))
                else:
                    layout.addRow("Energy:", QLabel(f"{energy*1e6:.3f} µJ"))

                # Capacitance
                capacitance = component.get_property('capacitance', config.DEFAULT_CAPACITANCE)
                if capacitance >= 1:
                    layout.addRow("Capacitance:", QLabel(f"{capacitance:.3f} F"))
                elif capacitance >= 1e-3:
                    layout.addRow("Capacitance:", QLabel(f"{capacitance*1e3:.3f} mF"))
                elif capacitance >= 1e-6:
                    layout.addRow("Capacitance:", QLabel(f"{capacitance*1e6:.3f} µF"))
                elif capacitance >= 1e-9:
                    layout.addRow("Capacitance:", QLabel(f"{capacitance*1e9:.3f} nF"))
                else:
                    layout.addRow("Capacitance:", QLabel(f"{capacitance*1e12:.3f} pF"))

            elif component_type == 'Inductor':
                # Flux
                flux = component.state.get('flux', 0.0)
                if abs(flux) >= 1:
                    layout.addRow("Flux:", QLabel(f"{flux:.3f} Wb"))
                elif abs(flux) >= 1e-3:
                    layout.addRow("Flux:", QLabel(f"{flux*1e3:.3f} mWb"))
                else:
                    layout.addRow("Flux:", QLabel(f"{flux*1e6:.3f} µWb"))

                # Energy
                energy = component.state.get('energy', 0.0)
                if energy >= 1:
                    layout.addRow("Energy:", QLabel(f"{energy:.3f} J"))
                elif energy >= 1e-3:
                    layout.addRow("Energy:", QLabel(f"{energy*1e3:.3f} mJ"))
                else:
                    layout.addRow("Energy:", QLabel(f"{energy*1e6:.3f} µJ"))

                # Inductance
                inductance = component.get_property('inductance', config.DEFAULT_INDUCTANCE)
                if inductance >= 1:
                    layout.addRow("Inductance:", QLabel(f"{inductance:.3f} H"))
                elif inductance >= 1e-3:
                    layout.addRow("Inductance:", QLabel(f"{inductance*1e3:.3f} mH"))
                elif inductance >= 1e-6:
                    layout.addRow("Inductance:", QLabel(f"{inductance*1e6:.3f} µH"))
                else:
                    layout.addRow("Inductance:", QLabel(f"{inductance*1e9:.3f} nH"))

            elif component_type == 'Diode' or component_type == 'LED':
                # Conducting state
                conducting = component.state.get('conducting', False)
                layout.addRow("Conducting:", QLabel("Yes" if conducting else "No"))

                # Forward voltage
                vf = component.get_property('forward_voltage', 0.7)
                layout.addRow("Forward Voltage:", QLabel(f"{vf:.2f} V"))

                # Power
                power = component.state.get('power', 0.0)
                if power >= 1:
                    layout.addRow("Power:", QLabel(f"{power:.3f} W"))
                elif power >= 1e-3:
                    layout.addRow("Power:", QLabel(f"{power*1e3:.3f} mW"))
                else:
                    layout.addRow("Power:", QLabel(f"{power*1e6:.3f} µW"))

                if component_type == 'LED':
                    # LED-specific
                    brightness = component.state.get('brightness', 0.0)
                    layout.addRow("Brightness:", QLabel(f"{brightness*100:.1f}%"))

                    color = component.get_property('color', 'red')
                    layout.addRow("Color:", QLabel(color))

            elif component_type == 'Switch':
                # Switch state
                closed = component.state.get('closed', False)
                layout.addRow("State:", QLabel("Closed" if closed else "Open"))

        elif component_type in ['DCVoltageSource', 'ACVoltageSource', 'DCCurrentSource']:
            # Voltages
            v_pos = component.state.get('voltages', {}).get('pos', 0.0)
            v_neg = component.state.get('voltages', {}).get('neg', 0.0)
            layout.addRow("Voltage Pos:", QLabel(f"{v_pos:.3f} V"))
            layout.addRow("Voltage Neg:", QLabel(f"{v_neg:.3f} V"))
            layout.addRow("Voltage Drop:", QLabel(f"{abs(v_pos - v_neg):.3f} V"))

            # Current
            current = component.state.get('currents', {}).get('pos', 0.0)
            if abs(current) >= 1:
                layout.addRow("Current:", QLabel(f"{current:.3f} A"))
            elif abs(current) >= 1e-3:
                layout.addRow("Current:", QLabel(f"{current*1e3:.3f} mA"))
            else:
                layout.addRow("Current:", QLabel(f"{current*1e6:.3f} µA"))

            # Power
            power = component.state.get('power', 0.0)
            if abs(power) >= 1:
                layout.addRow("Power:", QLabel(f"{power:.3f} W"))
            elif abs(power) >= 1e-3:
                layout.addRow("Power:", QLabel(f"{power*1e3:.3f} mW"))
            else:
                layout.addRow("Power:", QLabel(f"{power*1e6:.3f} µW"))

            # Source-specific properties
            if component_type == 'DCVoltageSource':
                voltage = component.get_property('voltage', config.DEFAULT_VOLTAGE)
                layout.addRow("Source Voltage:", QLabel(f"{voltage:.3f} V"))

                max_current = component.get_property('max_current', 1.0)
                layout.addRow("Max Current:", QLabel(f"{max_current:.3f} A"))

            elif component_type == 'ACVoltageSource':
                amplitude = component.get_property('amplitude', config.DEFAULT_VOLTAGE)
                layout.addRow("Amplitude:", QLabel(f"{amplitude:.3f} V"))

                frequency = component.get_property('frequency', config.DEFAULT_FREQUENCY)
                if frequency >= 1e6:
                    layout.addRow("Frequency:", QLabel(f"{frequency/1e6:.3f} MHz"))
                elif frequency >= 1e3:
                    layout.addRow("Frequency:", QLabel(f"{frequency/1e3:.3f} kHz"))
                else:
                    layout.addRow("Frequency:", QLabel(f"{frequency:.3f} Hz"))

                phase = component.get_property('phase', 0.0)
                layout.addRow("Phase:", QLabel(f"{phase:.1f}°"))

                inst_voltage = component.state.get('instantaneous_voltage', 0.0)
                layout.addRow("Instantaneous Voltage:", QLabel(f"{inst_voltage:.3f} V"))

            elif component_type == 'DCCurrentSource':
                current_setting = component.get_property('current', config.DEFAULT_CURRENT)
                if abs(current_setting) >= 1:
                    layout.addRow("Source Current:", QLabel(f"{current_setting:.3f} A"))
                elif abs(current_setting) >= 1e-3:
                    layout.addRow("Source Current:", QLabel(f"{current_setting*1e3:.3f} mA"))
                else:
                    layout.addRow("Source Current:", QLabel(f"{current_setting*1e6:.3f} µA"))

                max_voltage = component.get_property('max_voltage', 12.0)
                layout.addRow("Max Voltage:", QLabel(f"{max_voltage:.3f} V"))

        elif component_type == 'BJT':
            # Voltages
            v_c = component.state.get('voltages', {}).get('collector', 0.0)
            v_b = component.state.get('voltages', {}).get('base', 0.0)
            v_e = component.state.get('voltages', {}).get('emitter', 0.0)
            layout.addRow("Voltage Collector:", QLabel(f"{v_c:.3f} V"))
            layout.addRow("Voltage Base:", QLabel(f"{v_b:.3f} V"))
            layout.addRow("Voltage Emitter:", QLabel(f"{v_e:.3f} V"))
            layout.addRow("V<sub>CE</sub>:", QLabel(f"{abs(v_c - v_e):.3f} V"))
            layout.addRow("V<sub>BE</sub>:", QLabel(f"{abs(v_b - v_e):.3f} V"))
            layout.addRow("V<sub>BC</sub>:", QLabel(f"{abs(v_b - v_c):.3f} V"))

            # Currents
            i_c = component.state.get('currents', {}).get('collector', 0.0)
            i_b = component.state.get('currents', {}).get('base', 0.0)
            i_e = component.state.get('currents', {}).get('emitter', 0.0)

            if abs(i_c) >= 1:
                layout.addRow("Current Collector:", QLabel(f"{i_c:.3f} A"))
            elif abs(i_c) >= 1e-3:
                layout.addRow("Current Collector:", QLabel(f"{i_c*1e3:.3f} mA"))
            else:
                layout.addRow("Current Collector:", QLabel(f"{i_c*1e6:.3f} µA"))

            if abs(i_b) >= 1:
                layout.addRow("Current Base:", QLabel(f"{i_b:.3f} A"))
            elif abs(i_b) >= 1e-3:
                layout.addRow("Current Base:", QLabel(f"{i_b*1e3:.3f} mA"))
            else:
                layout.addRow("Current Base:", QLabel(f"{i_b*1e6:.3f} µA"))

            if abs(i_e) >= 1:
                layout.addRow("Current Emitter:", QLabel(f"{i_e:.3f} A"))
            elif abs(i_e) >= 1e-3:
                layout.addRow("Current Emitter:", QLabel(f"{i_e*1e3:.3f} mA"))
            else:
                layout.addRow("Current Emitter:", QLabel(f"{i_e*1e6:.3f} µA"))

            # Power
            power = component.state.get('power', 0.0)
            if power >= 1:
                layout.addRow("Power:", QLabel(f"{power:.3f} W"))
            elif power >= 1e-3:
                layout.addRow("Power:", QLabel(f"{power*1e3:.3f} mW"))
            else:
                layout.addRow("Power:", QLabel(f"{power*1e6:.3f} µW"))

            # Operating region
            region = component.state.get('region', 'cutoff')
            layout.addRow("Region:", QLabel(region))

            # Gain and type
            gain = component.get_property('gain', 100)
            layout.addRow("Gain (β):", QLabel(f"{gain}"))

            type_str = component.get_property('type', 'npn')
            layout.addRow("Type:", QLabel(type_str.upper()))

        elif component_type == 'Ground':
            # Ground has only one connection
            v_gnd = component.state.get('voltages', {}).get('gnd', 0.0)
            layout.addRow("Voltage:", QLabel(f"{v_gnd:.3f} V"))

            i_gnd = component.state.get('currents', {}).get('gnd', 0.0)
            if abs(i_gnd) >= 1:
                layout.addRow("Current:", QLabel(f"{i_gnd:.3f} A"))
            elif abs(i_gnd) >= 1e-3:
                layout.addRow("Current:", QLabel(f"{i_gnd*1e3:.3f} mA"))
            else:
                layout.addRow("Current:", QLabel(f"{i_gnd*1e6:.3f} µA"))

    def _add_circuit_measurements(self):
        """Add circuit-wide measurements."""
        # Create a group box
        group = QGroupBox("Circuit Measurements")
        group_layout = QFormLayout()
        group.setLayout(group_layout)

        # Total power
        total_power = sum(
            component.state.get('power', 0.0)
            for component in self.simulator.components.values()
        )

        if abs(total_power) >= 1:
            group_layout.addRow("Total Power:", QLabel(f"{total_power:.3f} W"))
        elif abs(total_power) >= 1:
            group_layout.addRow("Total Power:", QLabel(f"{total_power:.3f} W"))
        elif abs(total_power) >= 1e-3:
            group_layout.addRow("Total Power:", QLabel(f"{total_power*1e3:.3f} mW"))
        else:
            group_layout.addRow("Total Power:", QLabel(f"{total_power*1e6:.3f} µW"))

        # Number of components
        num_components = len(self.simulator.components)
        group_layout.addRow("Component Count:", QLabel(f"{num_components}"))

        # Number of nodes
        num_nodes = len(self.simulator.nodes)
        group_layout.addRow("Node Count:", QLabel(f"{num_nodes}"))

        # Simulation time
        sim_time = self.simulator.simulation_time
        group_layout.addRow("Simulation Time:", QLabel(f"{sim_time:.3f} s"))

        # Add the group to the measurement layout
        self.measurement_layout.addWidget(group)

    def update(self):
        """Update the display."""
        # Update all measurements
        for component_id, layout in self.component_measurements.items():
            # Get the component
            component = self.simulator.components.get(component_id)
            if not component:
                continue

            # Clear the layout
            while layout.rowCount() > 0:
                layout.removeRow(0)

            # Re-add measurements
            self._add_component_measurements(component, layout)

class AnalysisPanelWidget(QWidget):
    """Panel for circuit analysis and measurements."""

    def __init__(self, simulator):
        """Initialize the analysis panel.

        Args:
            simulator: CircuitSimulator instance
        """
        super().__init__()

        self.simulator = simulator

        # Set up the UI
        self._create_ui()

    def _create_ui(self):
        """Create the UI elements."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create measurement panel
        self.measurement_panel = MeasurementPanel(self.simulator)
        self.tabs.addTab(self.measurement_panel, "Measurements")

        # Create time series plot
        self.time_series_plot = TimeSeriesPlot(self.simulator)
        self.tabs.addTab(self.time_series_plot, "Time Series")

        # Add other tabs (to be implemented later)
        # For now, just add placeholders
        self.frequency_response_tab = QWidget()
        self.tabs.addTab(self.frequency_response_tab, "Frequency Response")

        self.dc_sweep_tab = QWidget()
        self.tabs.addTab(self.dc_sweep_tab, "DC Sweep")

        # Add simulation statistics display
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.StyledPanel)
        stats_layout = QHBoxLayout()
        stats_frame.setLayout(stats_layout)

        # Simulation statistics labels
        self.time_label = QLabel("Time: 0.000 s")
        stats_layout.addWidget(self.time_label)

        stats_layout.addWidget(QLabel("|"))

        self.fps_label = QLabel("FPS: 0.0")
        stats_layout.addWidget(self.fps_label)

        stats_layout.addWidget(QLabel("|"))

        self.solver_label = QLabel("Solver: N/A")
        stats_layout.addWidget(self.solver_label)

        stats_layout.addStretch()

        # Add statistics to layout
        layout.addWidget(stats_frame)

    def update(self):
        """Update the display."""
        # Update tabs based on the current tab
        current_tab = self.tabs.currentWidget()

        if current_tab == self.measurement_panel:
            self.measurement_panel.update()
        elif current_tab == self.time_series_plot:
            self.time_series_plot.update_plot()

        # Update statistics
        stats = self.simulator.stats

        self.time_label.setText(f"Time: {self.simulator.simulation_time:.3f} s")
        self.fps_label.setText(f"FPS: {stats.get('fps', 0.0):.1f}")

        # Solver info
        iterations = stats.get('iterations', 0)
        solve_time = stats.get('solve_time', 0.0) * 1000  # Convert to ms
        self.solver_label.setText(f"Solver: {iterations} iterations, {solve_time:.1f} ms")

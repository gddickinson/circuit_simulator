"""
Circuit Simulator - Component Panel
---------------------------------
This module provides a panel for selecting and placing components.
"""

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QToolButton, QSizePolicy, QGroupBox,
    QListWidget, QListWidgetItem, QTabWidget, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QColorDialog, QSpinBox
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPainter, QPen, QBrush, QPainterPath

import config
from components.passive_components import Resistor, Capacitor, Inductor, Ground
from components.active_components import (
    DCVoltageSource, ACVoltageSource, DCCurrentSource, Diode, LED, BJT, Switch
)

logger = logging.getLogger(__name__)



class ComponentButton(QToolButton):
    """Button for a component in the component panel."""

    def __init__(self, component_type, name, parent=None):
        """Initialize a component button.

        Args:
            component_type: Component type string (class name)
            name: Display name
            parent: Parent widget
        """
        super().__init__(parent)

        self.component_type = component_type
        self.component_name = name

        # Set up the button
        self.setText(name)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumSize(80, 70)

        # Create an icon based on component type
        self._create_icon()

    def _create_icon(self):
        """Create an icon for the button based on component type."""
        # Create a pixmap
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.white)

        # Create a painter
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Draw component symbol based on type
        if self.component_type == "Resistor":
            self._draw_resistor(painter)
        elif self.component_type == "Capacitor":
            self._draw_capacitor(painter)
        elif self.component_type == "Inductor":
            self._draw_inductor(painter)
        elif self.component_type == "Ground":
            self._draw_ground(painter)
        elif self.component_type == "DCVoltageSource":
            self._draw_dc_voltage_source(painter)
        elif self.component_type == "ACVoltageSource":
            self._draw_ac_voltage_source(painter)
        elif self.component_type == "DCCurrentSource":
            self._draw_dc_current_source(painter)
        elif self.component_type == "Diode":
            self._draw_diode(painter)
        elif self.component_type == "LED":
            self._draw_led(painter)
        elif self.component_type == "BJT":
            self._draw_bjt(painter)
        elif self.component_type == "Switch":
            self._draw_switch(painter)

        painter.end()

        # Set the icon
        self.setIcon(QIcon(pixmap))
        self.setIconSize(QSize(48, 48))

    def _draw_resistor(self, painter):
        """Draw a resistor symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw zigzag
        # Draw left lead
        painter.drawLine(10, 24, 15, 24)

        # Zigzag body
        points = [
            (15, 24), (18, 18), (24, 30),
            (30, 18), (36, 30), (42, 18),
            (45, 24)
        ]

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1],
                             points[i+1][0], points[i+1][1])

        painter.drawLine(45, 24, 50, 24)  # Right lead

    def _draw_capacitor(self, painter):
        """Draw a capacitor symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw plates
        painter.drawLine(20, 14, 20, 34)  # Left plate
        painter.drawLine(28, 14, 28, 34)  # Right plate

        # Draw leads
        painter.drawLine(10, 24, 20, 24)  # Left lead
        painter.drawLine(28, 24, 38, 24)  # Right lead

    def _draw_inductor(self, painter):
        """Draw an inductor symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw leads
        painter.drawLine(10, 24, 15, 24)  # Left lead
        painter.drawLine(45, 24, 50, 24)  # Right lead

        # Draw coils
        for i in range(4):
            center_x = 20 + i * 8
            painter.drawArc(center_x - 5, 19, 10, 10, 0, -180 * 16)

    def _draw_ground(self, painter):
        """Draw a ground symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw vertical line
        painter.drawLine(24, 10, 24, 25)

        # Draw horizontal lines
        painter.drawLine(14, 25, 34, 25)
        painter.drawLine(17, 30, 31, 30)
        painter.drawLine(20, 35, 28, 35)

    def _draw_dc_voltage_source(self, painter):
        """Draw a DC voltage source symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw circle
        painter.drawEllipse(14, 14, 20, 20)

        # Draw + and - symbols
        painter.drawLine(20, 20, 28, 20)  # Horizontal line for both + and -
        painter.drawLine(24, 16, 24, 24)  # Vertical line for +

    def _draw_ac_voltage_source(self, painter):
        """Draw an AC voltage source symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw circle
        painter.drawEllipse(14, 14, 20, 20)

        # Draw sine wave
        painter.drawLine(18, 24, 22, 18)
        painter.drawLine(22, 18, 26, 30)
        painter.drawLine(26, 30, 30, 24)

    def _draw_dc_current_source(self, painter):
        """Draw a DC current source symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw circle
        painter.drawEllipse(14, 14, 20, 20)

        # Draw arrow
        painter.drawLine(24, 18, 24, 30)

        # Arrow head
        painter.drawLine(24, 30, 21, 26)
        painter.drawLine(24, 30, 27, 26)

    def _draw_diode(self, painter):
        """Draw a diode symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw leads
        painter.drawLine(10, 24, 18, 24)  # Left lead
        painter.drawLine(38, 24, 50, 24)  # Right lead

        # Draw triangle
        points = [
            (18, 14), (18, 34), (38, 24)
        ]

        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        path.lineTo(points[1][0], points[1][1])
        path.lineTo(points[2][0], points[2][1])
        path.lineTo(points[0][0], points[0][1])

        painter.setBrush(QBrush(Qt.white))
        painter.drawPath(path)

        # Draw cathode line
        painter.drawLine(38, 14, 38, 34)

    def _draw_led(self, painter):
        """Draw an LED symbol.

        Args:
            painter: QPainter object
        """
        # Draw basic diode
        self._draw_diode(painter)

        # Add arrows for light emission
        painter.setPen(QPen(Qt.black, 1))

        # Draw arrows
        for angle, pos in [(45, (32, 10)), (0, (40, 15)), (-45, (48, 10))]:
            x, y = pos

            if angle == 45:
                painter.drawLine(x, y, x - 5, y + 5)
                painter.drawLine(x, y, x + 5, y + 5)
            elif angle == 0:
                painter.drawLine(x, y, x - 5, y + 5)
                painter.drawLine(x, y, x - 5, y - 5)
            else:  # -45
                painter.drawLine(x, y, x - 5, y - 5)
                painter.drawLine(x, y, x + 5, y - 5)

    def _draw_bjt(self, painter):
        """Draw a BJT symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw circle
        painter.drawEllipse(14, 14, 20, 20)

        # Draw collector-emitter line
        painter.drawLine(24, 14, 24, 34)

        # Draw base line
        painter.drawLine(10, 24, 19, 24)

        # Draw emitter arrow (NPN)
        painter.drawLine(24, 29, 34, 34)

        # Arrow head
        painter.drawLine(34, 34, 30, 31)
        painter.drawLine(34, 34, 31, 37)

    def _draw_switch(self, painter):
        """Draw a switch symbol.

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw connection points
        painter.setBrush(QBrush(Qt.black))
        painter.drawEllipse(13, 21, 6, 6)
        painter.drawEllipse(29, 21, 6, 6)

        # Draw leads
        painter.drawLine(5, 24, 13, 24)   # Left lead
        painter.drawLine(35, 24, 43, 24)  # Right lead

        # Draw switch (open position)
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(16, 24, 35, 15)

    def sizeHint(self):
        """Get the suggested size for the button.

        Returns:
            QSize
        """
        return QSize(80, 70)


class ComponentPropertiesDialog(QDialog):
    """Dialog for editing component properties."""

    def __init__(self, component_type, parent=None):
        """Initialize a component properties dialog.

        Args:
            component_type: Component type string (class name)
            parent: Parent widget
        """
        super().__init__(parent)

        self.component_type = component_type
        self.properties = {}

        # Set up the dialog
        self.setWindowTitle("Component Properties")
        self.setMinimumWidth(300)

        # Create layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Form layout for properties
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)

        # Create property widgets based on component type
        self._create_property_widgets()

        # Add OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

    def _create_property_widgets(self):
        """Create widgets for editing component properties."""
        self.property_widgets = {}

        if self.component_type == "Resistor":
            # Resistance
            resistance_widget = QDoubleSpinBox()
            resistance_widget.setRange(0.1, 10e6)
            resistance_widget.setValue(config.DEFAULT_RESISTANCE)
            resistance_widget.setSuffix(" Ω")
            resistance_widget.setDecimals(1)
            self.form_layout.addRow("Resistance:", resistance_widget)
            self.property_widgets["resistance"] = resistance_widget

            # Max power
            power_widget = QDoubleSpinBox()
            power_widget.setRange(0.1, 100)
            power_widget.setValue(0.25)  # Default 1/4 watt
            power_widget.setSuffix(" W")
            power_widget.setDecimals(2)
            self.form_layout.addRow("Max Power:", power_widget)
            self.property_widgets["max_power"] = power_widget

        elif self.component_type == "Capacitor":
            # Capacitance
            cap_widget = QDoubleSpinBox()
            cap_widget.setRange(1e-12, 1)
            cap_widget.setValue(config.DEFAULT_CAPACITANCE)
            cap_widget.setSuffix(" F")
            cap_widget.setDecimals(9)
            self.form_layout.addRow("Capacitance:", cap_widget)
            self.property_widgets["capacitance"] = cap_widget

            # Max voltage
            voltage_widget = QDoubleSpinBox()
            voltage_widget.setRange(1, 1000)
            voltage_widget.setValue(50)
            voltage_widget.setSuffix(" V")
            voltage_widget.setDecimals(1)
            self.form_layout.addRow("Max Voltage:", voltage_widget)
            self.property_widgets["max_voltage"] = voltage_widget

        elif self.component_type == "Inductor":
            # Inductance
            ind_widget = QDoubleSpinBox()
            ind_widget.setRange(1e-9, 1)
            ind_widget.setValue(config.DEFAULT_INDUCTANCE)
            ind_widget.setSuffix(" H")
            ind_widget.setDecimals(6)
            self.form_layout.addRow("Inductance:", ind_widget)
            self.property_widgets["inductance"] = ind_widget

            # Max current
            current_widget = QDoubleSpinBox()
            current_widget.setRange(0.1, 100)
            current_widget.setValue(1.0)
            current_widget.setSuffix(" A")
            current_widget.setDecimals(2)
            self.form_layout.addRow("Max Current:", current_widget)
            self.property_widgets["max_current"] = current_widget

        elif self.component_type == "DCVoltageSource":
            # Voltage
            voltage_widget = QDoubleSpinBox()
            voltage_widget.setRange(-1000, 1000)
            voltage_widget.setValue(config.DEFAULT_VOLTAGE)
            voltage_widget.setSuffix(" V")
            voltage_widget.setDecimals(1)
            self.form_layout.addRow("Voltage:", voltage_widget)
            self.property_widgets["voltage"] = voltage_widget

            # Max current
            current_widget = QDoubleSpinBox()
            current_widget.setRange(0.001, 100)
            current_widget.setValue(1.0)
            current_widget.setSuffix(" A")
            current_widget.setDecimals(3)
            self.form_layout.addRow("Max Current:", current_widget)
            self.property_widgets["max_current"] = current_widget

        elif self.component_type == "ACVoltageSource":
            # Amplitude
            amplitude_widget = QDoubleSpinBox()
            amplitude_widget.setRange(0, 1000)
            amplitude_widget.setValue(config.DEFAULT_VOLTAGE)
            amplitude_widget.setSuffix(" V")
            amplitude_widget.setDecimals(1)
            self.form_layout.addRow("Amplitude:", amplitude_widget)
            self.property_widgets["amplitude"] = amplitude_widget

            # Frequency
            freq_widget = QDoubleSpinBox()
            freq_widget.setRange(0.1, 10e6)
            freq_widget.setValue(config.DEFAULT_FREQUENCY)
            freq_widget.setSuffix(" Hz")
            freq_widget.setDecimals(1)
            self.form_layout.addRow("Frequency:", freq_widget)
            self.property_widgets["frequency"] = freq_widget

            # Phase
            phase_widget = QDoubleSpinBox()
            phase_widget.setRange(-360, 360)
            phase_widget.setValue(0)
            phase_widget.setSuffix(" °")
            phase_widget.setDecimals(1)
            self.form_layout.addRow("Phase:", phase_widget)
            self.property_widgets["phase"] = phase_widget

        elif self.component_type == "DCCurrentSource":
            # Current
            current_widget = QDoubleSpinBox()
            current_widget.setRange(-10, 10)
            current_widget.setValue(config.DEFAULT_CURRENT)
            current_widget.setSuffix(" A")
            current_widget.setDecimals(3)
            self.form_layout.addRow("Current:", current_widget)
            self.property_widgets["current"] = current_widget

            # Max voltage
            voltage_widget = QDoubleSpinBox()
            voltage_widget.setRange(0.1, 1000)
            voltage_widget.setValue(12.0)
            voltage_widget.setSuffix(" V")
            voltage_widget.setDecimals(1)
            self.form_layout.addRow("Max Voltage:", voltage_widget)
            self.property_widgets["max_voltage"] = voltage_widget

        elif self.component_type == "Diode":
            # Forward voltage
            vf_widget = QDoubleSpinBox()
            vf_widget.setRange(0.1, 10)
            vf_widget.setValue(0.7)  # Default for silicon diode
            vf_widget.setSuffix(" V")
            vf_widget.setDecimals(2)
            self.form_layout.addRow("Forward Voltage:", vf_widget)
            self.property_widgets["forward_voltage"] = vf_widget

            # Max current
            current_widget = QDoubleSpinBox()
            current_widget.setRange(0.001, 100)
            current_widget.setValue(1.0)
            current_widget.setSuffix(" A")
            current_widget.setDecimals(3)
            self.form_layout.addRow("Max Current:", current_widget)
            self.property_widgets["max_current"] = current_widget

        elif self.component_type == "LED":
            # Forward voltage
            vf_widget = QDoubleSpinBox()
            vf_widget.setRange(0.1, 10)
            vf_widget.setValue(2.0)  # Default for LED
            vf_widget.setSuffix(" V")
            vf_widget.setDecimals(2)
            self.form_layout.addRow("Forward Voltage:", vf_widget)
            self.property_widgets["forward_voltage"] = vf_widget

            # Max current
            current_widget = QDoubleSpinBox()
            current_widget.setRange(0.001, 1)
            current_widget.setValue(0.02)  # 20 mA typical for LED
            current_widget.setSuffix(" A")
            current_widget.setDecimals(3)
            self.form_layout.addRow("Max Current:", current_widget)
            self.property_widgets["max_current"] = current_widget

            # Color
            color_combo = QComboBox()
            color_combo.addItems(["red", "green", "blue", "yellow", "white"])
            self.form_layout.addRow("Color:", color_combo)
            self.property_widgets["color"] = color_combo

        elif self.component_type == "BJT":
            # Type (NPN/PNP)
            type_combo = QComboBox()
            type_combo.addItems(["npn", "pnp"])
            self.form_layout.addRow("Type:", type_combo)
            self.property_widgets["type"] = type_combo

            # Gain (beta)
            gain_widget = QSpinBox()
            gain_widget.setRange(10, 1000)
            gain_widget.setValue(100)
            self.form_layout.addRow("Gain (β):", gain_widget)
            self.property_widgets["gain"] = gain_widget

            # Max collector current
            current_widget = QDoubleSpinBox()
            current_widget.setRange(0.001, 10)
            current_widget.setValue(0.5)
            current_widget.setSuffix(" A")
            current_widget.setDecimals(3)
            self.form_layout.addRow("Max Collector Current:", current_widget)
            self.property_widgets["max_collector_current"] = current_widget

        elif self.component_type == "Switch":
            # Initial state
            state_combo = QComboBox()
            state_combo.addItems(["Open", "Closed"])
            self.form_layout.addRow("Initial State:", state_combo)
            self.property_widgets["state"] = state_combo

            # Max current
            current_widget = QDoubleSpinBox()
            current_widget.setRange(0.1, 100)
            current_widget.setValue(5.0)
            current_widget.setSuffix(" A")
            current_widget.setDecimals(1)
            self.form_layout.addRow("Max Current:", current_widget)
            self.property_widgets["max_current"] = current_widget

    def get_properties(self):
        """Get the properties from the dialog widgets.

        Returns:
            Dictionary of properties
        """
        properties = {}

        for name, widget in self.property_widgets.items():
            if isinstance(widget, QComboBox):
                if name == "state":
                    # Convert Open/Closed to boolean
                    properties[name] = (widget.currentText() == "Closed")
                else:
                    properties[name] = widget.currentText()
            elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                properties[name] = widget.value()
            elif isinstance(widget, QLineEdit):
                properties[name] = widget.text()

        return properties


class ComponentPanelWidget(QWidget):
    """Panel for selecting and placing components."""

    def __init__(self, db_manager, circuit_board):
        """Initialize the component panel.

        Args:
            db_manager: DatabaseManager instance
            circuit_board: CircuitBoardWidget
        """
        super().__init__()

        self.db_manager = db_manager
        self.circuit_board = circuit_board

        # Set up the UI
        self._create_ui()

    def _create_ui(self):
        """Create the UI elements."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tabs for different component categories
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tab pages
        self.passive_tab = self._create_passive_tab()
        self.active_tab = self._create_active_tab()
        self.sources_tab = self._create_sources_tab()
        self.ics_tab = self._create_ics_tab()

        # Add tabs
        self.tabs.addTab(self.passive_tab, "Passive")
        self.tabs.addTab(self.active_tab, "Active")
        self.tabs.addTab(self.sources_tab, "Sources")
        self.tabs.addTab(self.ics_tab, "ICs")

        # Add recently used components list
        self.recent_components = QListWidget()
        self.recent_components.setMaximumHeight(100)
        layout.addWidget(QLabel("Recent Components:"))
        layout.addWidget(self.recent_components)

        # Populate the recent components list
        self._populate_recent_components()

    def _create_passive_tab(self):
        """Create the passive components tab.

        Returns:
            QWidget tab page
        """
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # Resistors group
        resistors_group = QGroupBox("Resistors")
        resistors_layout = QHBoxLayout()
        resistors_group.setLayout(resistors_layout)

        # Resistor button
        resistor_button = ComponentButton("Resistor", "Resistor")
        resistor_button.clicked.connect(
            lambda: self._component_clicked("Resistor")
        )
        resistors_layout.addWidget(resistor_button)

        # Add resistors group to layout
        layout.addWidget(resistors_group)

        # Capacitors group
        capacitors_group = QGroupBox("Capacitors")
        capacitors_layout = QHBoxLayout()
        capacitors_group.setLayout(capacitors_layout)

        # Capacitor button
        capacitor_button = ComponentButton("Capacitor", "Capacitor")
        capacitor_button.clicked.connect(
            lambda: self._component_clicked("Capacitor")
        )
        capacitors_layout.addWidget(capacitor_button)

        # Add capacitors group to layout
        layout.addWidget(capacitors_group)

        # Inductors group
        inductors_group = QGroupBox("Inductors")
        inductors_layout = QHBoxLayout()
        inductors_group.setLayout(inductors_layout)

        # Inductor button
        inductor_button = ComponentButton("Inductor", "Inductor")
        inductor_button.clicked.connect(
            lambda: self._component_clicked("Inductor")
        )
        inductors_layout.addWidget(inductor_button)

        # Add inductors group to layout
        layout.addWidget(inductors_group)

        # Ground and other
        other_group = QGroupBox("Other")
        other_layout = QHBoxLayout()
        other_group.setLayout(other_layout)

        # Ground button
        ground_button = ComponentButton("Ground", "Ground")
        ground_button.clicked.connect(
            lambda: self._component_clicked("Ground")
        )
        other_layout.addWidget(ground_button)

        # Add other group to layout
        layout.addWidget(other_group)

        # Add a stretch to push everything to the top
        layout.addStretch()

        return tab

    def _create_active_tab(self):
        """Create the active components tab.

        Returns:
            QWidget tab page
        """
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # Diodes group
        diodes_group = QGroupBox("Diodes")
        diodes_layout = QHBoxLayout()
        diodes_group.setLayout(diodes_layout)

        # Diode button
        diode_button = ComponentButton("Diode", "Diode")
        diode_button.clicked.connect(
            lambda: self._component_clicked("Diode")
        )
        diodes_layout.addWidget(diode_button)

        # LED button
        led_button = ComponentButton("LED", "LED")
        led_button.clicked.connect(
            lambda: self._component_clicked("LED")
        )
        diodes_layout.addWidget(led_button)

        # Add diodes group to layout
        layout.addWidget(diodes_group)

        # Transistors group
        transistors_group = QGroupBox("Transistors")
        transistors_layout = QHBoxLayout()
        transistors_group.setLayout(transistors_layout)

        # BJT button
        bjt_button = ComponentButton("BJT", "BJT")
        bjt_button.clicked.connect(
            lambda: self._component_clicked("BJT")
        )
        transistors_layout.addWidget(bjt_button)

        # Add transistors group to layout
        layout.addWidget(transistors_group)

        # Switches group
        switches_group = QGroupBox("Switches")
        switches_layout = QHBoxLayout()
        switches_group.setLayout(switches_layout)

        # Switch button
        switch_button = ComponentButton("Switch", "Switch")
        switch_button.clicked.connect(
            lambda: self._component_clicked("Switch")
        )
        switches_layout.addWidget(switch_button)

        # Add switches group to layout
        layout.addWidget(switches_group)

        # Add a stretch to push everything to the top
        layout.addStretch()

        return tab

    def _create_sources_tab(self):
        """Create the sources components tab.

        Returns:
            QWidget tab page
        """
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # Voltage sources group
        voltage_group = QGroupBox("Voltage Sources")
        voltage_layout = QHBoxLayout()
        voltage_group.setLayout(voltage_layout)

        # DC voltage source button
        dc_vs_button = ComponentButton("DCVoltageSource", "DC")
        dc_vs_button.clicked.connect(
            lambda: self._component_clicked("DCVoltageSource")
        )
        voltage_layout.addWidget(dc_vs_button)

        # AC voltage source button
        ac_vs_button = ComponentButton("ACVoltageSource", "AC")
        ac_vs_button.clicked.connect(
            lambda: self._component_clicked("ACVoltageSource")
        )
        voltage_layout.addWidget(ac_vs_button)

        # Add voltage sources group to layout
        layout.addWidget(voltage_group)

        # Current sources group
        current_group = QGroupBox("Current Sources")
        current_layout = QHBoxLayout()
        current_group.setLayout(current_layout)

        # DC current source button
        dc_cs_button = ComponentButton("DCCurrentSource", "DC")
        dc_cs_button.clicked.connect(
            lambda: self._component_clicked("DCCurrentSource")
        )
        current_layout.addWidget(dc_cs_button)

        # Add current sources group to layout
        layout.addWidget(current_group)

        # Add a stretch to push everything to the top
        layout.addStretch()

        return tab

    def _create_ics_tab(self):
        """Create the ICs components tab.

        Returns:
            QWidget tab page
        """
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # Coming soon label
        label = QLabel("Coming soon - Integrated Circuits will be available in a future update.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # Add a stretch to push everything to the top
        layout.addStretch()

        return tab

    def _populate_recent_components(self):
        """Populate the recent components list."""
        # For now, we'll just add some default components
        # In a real implementation, this would use the database to get recently used components
        for component_type in ["Resistor", "Capacitor", "DCVoltageSource"]:
            item = QListWidgetItem(component_type)
            item.setData(Qt.UserRole, component_type)
            self.recent_components.addItem(item)

        # Connect the item click signal
        self.recent_components.itemClicked.connect(self._recent_component_clicked)

    def _component_clicked(self, component_type):
        """Handle component button click.

        Args:
            component_type: Component type string (class name)
        """
        # Show properties dialog
        properties = self._show_properties_dialog(component_type)

        if properties:
            # Place the component on the circuit board
            self.circuit_board.place_component(component_type, properties)

            # Update recent components
            self._update_recent_components(component_type)

    def _recent_component_clicked(self, item):
        """Handle click on a recent component item.

        Args:
            item: QListWidgetItem
        """
        # Get the component type
        component_type = item.data(Qt.UserRole)

        # Show properties dialog
        properties = self._show_properties_dialog(component_type)

        if properties:
            # Place the component on the circuit board
            self.circuit_board.place_component(component_type, properties)

    def _show_properties_dialog(self, component_type):
        """Show the properties dialog for a component.

        Args:
            component_type: Component type string (class name)

        Returns:
            Dictionary of properties or None if cancelled
        """
        dialog = ComponentPropertiesDialog(component_type, self)

        # Show the dialog
        result = dialog.exec_()

        if result == QDialog.Accepted:
            # Get the properties
            return dialog.get_properties()

        return None

    def _update_recent_components(self, component_type):
        """Update the recent components list.

        Args:
            component_type: Component type string (class name)
        """
        # Check if the component is already in the list
        for i in range(self.recent_components.count()):
            item = self.recent_components.item(i)
            if item.data(Qt.UserRole) == component_type:
                # Move it to the top
                self.recent_components.takeItem(i)
                self.recent_components.insertItem(0, item)
                self.recent_components.setCurrentItem(item)
                return

        # Add new item at the top
        item = QListWidgetItem(component_type)
        item.setData(Qt.UserRole, component_type)
        self.recent_components.insertItem(0, item)
        self.recent_components.setCurrentItem(item)

        # Keep the list size manageable
        while self.recent_components.count() > 10:
            self.recent_components.takeItem(self.recent_components.count() - 1)

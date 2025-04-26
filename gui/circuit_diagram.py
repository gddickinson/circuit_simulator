"""
Circuit Simulator - Circuit Diagram Widget
---------------------------------------
This module provides a widget for displaying a schematic diagram of the circuit.
"""

import math
import logging
from PyQt5.QtWidgets import (
    QWidget, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsEllipseItem
)
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QFont, QTransform
)

import config

logger = logging.getLogger(__name__)


class SchematicSymbolItem(QGraphicsItem):
    """Base class for schematic symbols in the circuit diagram."""

    def __init__(self, component, diagram):
        """Initialize a schematic symbol.

        Args:
            component: Component object
            diagram: CircuitDiagramWidget
        """
        super().__init__()

        self.component = component
        self.diagram = diagram
        self.setZValue(10)

        # Text to display
        self.label = None
        self.value_text = None

        # Update the symbol
        self.update_symbol()

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        # Default size - override in subclasses
        return QRectF(-30, -30, 60, 60)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Override in subclasses
        pass

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Override in subclasses
        pass


class ResistorSymbol(SchematicSymbolItem):
    """Schematic symbol for a resistor."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-40, -15, 80, 30)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw resistor symbol (zigzag)
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.NoBrush)

        # Create zigzag path
        path = QPainterPath()
        path.moveTo(-30, 0)

        # Draw zigzag
        zigzag_width = 60
        zigzag_steps = 6
        step_width = zigzag_width / zigzag_steps
        half_height = 10

        for i in range(zigzag_steps + 1):
            x = -30 + i * step_width
            y = half_height if i % 2 == 0 else -half_height
            path.lineTo(x, y)

        path.lineTo(30, 0)

        # Draw the path
        painter.drawPath(path)

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 15, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format resistance value
        resistance = self.component.get_property('resistance', config.DEFAULT_RESISTANCE)

        if resistance >= 1e6:
            self.value_text = f"{resistance/1e6:.1f} MΩ"
        elif resistance >= 1e3:
            self.value_text = f"{resistance/1e3:.1f} kΩ"
        else:
            self.value_text = f"{resistance:.1f} Ω"

        # Update power value if simulation is running
        if self.diagram.simulator.running:
            power = self.component.state.get('power', 0.0)

            if power >= 1:
                p_text = f"{power:.2f} W"
            elif power >= 1e-3:
                p_text = f"{power*1e3:.2f} mW"
            else:
                p_text = f"{power*1e6:.2f} µW"

            # Add power to the label
            self.value_text += f", {p_text}"


class CapacitorSymbol(SchematicSymbolItem):
    """Schematic symbol for a capacitor."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-40, -15, 80, 30)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw capacitor symbol (two parallel plates)
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.NoBrush)

        # Draw connection lines
        painter.drawLine(-30, 0, -5, 0)
        painter.drawLine(5, 0, 30, 0)

        # Draw plates
        painter.drawLine(-5, -15, -5, 15)
        painter.drawLine(5, -15, 5, 15)

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 15, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format capacitance value
        capacitance = self.component.get_property('capacitance', config.DEFAULT_CAPACITANCE)

        if capacitance >= 1:
            self.value_text = f"{capacitance:.1f} F"
        elif capacitance >= 1e-3:
            self.value_text = f"{capacitance*1e3:.1f} mF"
        elif capacitance >= 1e-6:
            self.value_text = f"{capacitance*1e6:.1f} µF"
        elif capacitance >= 1e-9:
            self.value_text = f"{capacitance*1e9:.1f} nF"
        else:
            self.value_text = f"{capacitance*1e12:.1f} pF"


class InductorSymbol(SchematicSymbolItem):
    """Schematic symbol for an inductor."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-40, -15, 80, 30)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw inductor symbol (coil)
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.NoBrush)

        # Create coil path
        path = QPainterPath()
        path.moveTo(-30, 0)

        # Draw connection line to first arc
        path.lineTo(-25, 0)

        # Draw arcs
        for i in range(4):
            center_x = -15 + i * 10
            path.arcTo(center_x - 5, -5, 10, 10, 180, 180)

        # Draw connection line from last arc
        path.lineTo(30, 0)

        # Draw the path
        painter.drawPath(path)

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 15, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format inductance value
        inductance = self.component.get_property('inductance', config.DEFAULT_INDUCTANCE)

        if inductance >= 1:
            self.value_text = f"{inductance:.1f} H"
        elif inductance >= 1e-3:
            self.value_text = f"{inductance*1e3:.1f} mH"
        elif inductance >= 1e-6:
            self.value_text = f"{inductance*1e6:.1f} µH"
        else:
            self.value_text = f"{inductance*1e9:.1f} nH"


class DCVoltageSourceSymbol(SchematicSymbolItem):
    """Schematic symbol for a DC voltage source."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-25, -25, 50, 70)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw DC voltage source symbol (circle with + and -)
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.white)

        # Draw circle
        painter.drawEllipse(-15, -15, 30, 30)

        # Draw + and - symbols
        painter.setPen(QPen(Qt.black, 2))

        # + symbol
        painter.drawLine(-5, -5, 5, -5)
        painter.drawLine(0, -10, 0, 0)

        # - symbol
        painter.drawLine(-5, 5, 5, 5)

        # Draw connection lines
        painter.setPen(QPen(Qt.black, 1.5))
        painter.drawLine(0, -15, 0, -30)  # Top connection
        painter.drawLine(0, 15, 0, 30)    # Bottom connection

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 30, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format voltage value
        voltage = self.component.get_property('voltage', config.DEFAULT_VOLTAGE)
        self.value_text = f"{voltage:.1f} V"


class ACVoltageSourceSymbol(SchematicSymbolItem):
    """Schematic symbol for an AC voltage source."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-25, -25, 50, 70)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw AC voltage source symbol (circle with sine wave)
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.white)

        # Draw circle
        painter.drawEllipse(-15, -15, 30, 30)

        # Draw sine wave
        path = QPainterPath()
        path.moveTo(-10, 0)

        # Draw one cycle of a sine wave
        steps = 20
        for i in range(steps + 1):
            x = -10 + i * 20 / steps
            y = -5 * math.sin(i * 2 * math.pi / steps)
            path.lineTo(x, y)

        painter.drawPath(path)

        # Draw connection lines
        painter.drawLine(0, -15, 0, -30)  # Top connection
        painter.drawLine(0, 15, 0, 30)    # Bottom connection

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 30, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format amplitude and frequency values
        amplitude = self.component.get_property('amplitude', config.DEFAULT_VOLTAGE)
        frequency = self.component.get_property('frequency', config.DEFAULT_FREQUENCY)

        if frequency >= 1e6:
            self.value_text = f"{amplitude:.1f}V, {frequency/1e6:.1f}MHz"
        elif frequency >= 1e3:
            self.value_text = f"{amplitude:.1f}V, {frequency/1e3:.1f}kHz"
        else:
            self.value_text = f"{amplitude:.1f}V, {frequency:.1f}Hz"


class DCCurrentSourceSymbol(SchematicSymbolItem):
    """Schematic symbol for a DC current source."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-25, -25, 50, 70)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw DC current source symbol (circle with arrow)
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.white)

        # Draw circle
        painter.drawEllipse(-15, -15, 30, 30)

        # Draw arrow
        painter.setPen(QPen(Qt.black, 1.5))
        painter.drawLine(0, -10, 0, 10)

        # Arrow head
        painter.setBrush(Qt.black)
        points = [QPointF(0, 10), QPointF(-5, 0), QPointF(5, 0)]
        painter.drawPolygon(points)

        # Draw connection lines
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(0, -15, 0, -30)  # Top connection
        painter.drawLine(0, 15, 0, 30)    # Bottom connection

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 30, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format current value
        current = self.component.get_property('current', config.DEFAULT_CURRENT)

        if abs(current) >= 1:
            self.value_text = f"{current:.1f} A"
        elif abs(current) >= 1e-3:
            self.value_text = f"{current*1e3:.1f} mA"
        else:
            self.value_text = f"{current*1e6:.1f} µA"


class DiodeSymbol(SchematicSymbolItem):
    """Schematic symbol for a diode."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-40, -15, 80, 30)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw diode symbol (triangle with line)
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw triangle
        painter.setBrush(Qt.white)
        points = [QPointF(-5, -10), QPointF(-5, 10), QPointF(5, 0)]
        painter.drawPolygon(points)

        # Draw cathode line
        painter.drawLine(5, -10, 5, 10)

        # Draw connection lines
        painter.drawLine(-30, 0, -5, 0)
        painter.drawLine(5, 0, 30, 0)

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 15, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format forward voltage
        vf = self.component.get_property('forward_voltage', 0.7)
        self.value_text = f"Vf={vf:.1f}V"

        # Update current if simulation is running
        if self.diagram.simulator.running:
            current = self.component.state.get('currents', {}).get('anode', 0.0)

            if abs(current) >= 1:
                i_text = f"{current:.1f}A"
            elif abs(current) >= 1e-3:
                i_text = f"{current*1e3:.1f}mA"
            else:
                i_text = f"{current*1e6:.1f}µA"

            # Add current to value text
            self.value_text += f", {i_text}"


class LEDSymbol(DiodeSymbol):
    """Schematic symbol for an LED."""

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw base diode symbol
        super().paint(painter, option, widget)

        # Draw arrows for light emission
        painter.setPen(QPen(Qt.black, 1))

        # Get LED color
        led_color = self.component.get_property("color", "red")
        brightness = self.component.state.get("brightness", 0.0)

        if brightness > 0.01:
            painter.setPen(QPen(QColor(led_color), 1))

            # Draw two arrows
            for angle, length in [(-30, 10), (0, 12), (30, 10)]:
                rad = math.radians(angle)
                dx = math.cos(rad) * length
                dy = math.sin(rad) * length

                # Start point
                start_x = 0
                start_y = -5

                # End point
                end_x = start_x + dx
                end_y = start_y - dy

                # Draw arrow line
                painter.drawLine(start_x, start_y, end_x, end_y)

                # Draw arrow head
                arrow_head_size = 3
                painter.drawLine(end_x, end_y, end_x - arrow_head_size, end_y - arrow_head_size)
                painter.drawLine(end_x, end_y, end_x - arrow_head_size, end_y + arrow_head_size)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format forward voltage and color
        vf = self.component.get_property('forward_voltage', 2.0)
        color = self.component.get_property('color', 'red')
        self.value_text = f"{color} LED, Vf={vf:.1f}V"

        # Update current and brightness if simulation is running
        if self.diagram.simulator.running:
            current = self.component.state.get('currents', {}).get('anode', 0.0)
            brightness = self.component.state.get('brightness', 0.0)

            if abs(current) >= 1:
                i_text = f"{current:.1f}A"
            elif abs(current) >= 1e-3:
                i_text = f"{current*1e3:.1f}mA"
            else:
                i_text = f"{current*1e6:.1f}µA"

            # Add current and brightness to value text
            self.value_text += f", {i_text}"
            if brightness > 0:
                self.value_text += f" ({brightness*100:.0f}%)"


class BJTSymbol(SchematicSymbolItem):
    """Schematic symbol for a BJT transistor."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-40, -30, 80, 60)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw BJT symbol (circle with lines)
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.white)

        # Check if NPN or PNP
        is_npn = self.component.get_property("type", "npn") == "npn"

        # Draw circle
        painter.drawEllipse(-10, -10, 20, 20)

        # Draw collector-emitter line
        painter.drawLine(0, -10, 0, 10)

        # Draw base line
        painter.drawLine(-30, 0, -10, 0)

        # Draw emitter and collector lines
        painter.drawLine(0, -10, 0, -30)  # Collector
        painter.drawLine(0, 10, 0, 30)    # Emitter

        # Draw emitter arrow
        if is_npn:
            # NPN - arrow points away from the base line
            points = [QPointF(0, 10), QPointF(-5, 15), QPointF(5, 15)]
        else:
            # PNP - arrow points toward the base line
            points = [QPointF(0, 0), QPointF(-5, 5), QPointF(5, 5)]

        painter.setBrush(Qt.black)
        painter.drawPolygon(points)

        # Draw labels
        painter.setFont(QFont("Arial", 8))
        painter.drawText(-15, -15, "C")  # Collector
        painter.drawText(-35, 5, "B")    # Base
        painter.drawText(-15, 30, "E")   # Emitter

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 30, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Format gain and type
        gain = self.component.get_property('gain', 100)
        is_npn = self.component.get_property("type", "npn") == "npn"

        if is_npn:
            self.value_text = f"NPN, β={gain}"
        else:
            self.value_text = f"PNP, β={gain}"

        # Update region if simulation is running
        if self.diagram.simulator.running:
            region = self.component.state.get('region', 'cutoff')
            self.value_text += f", {region}"


class SwitchSymbol(SchematicSymbolItem):
    """Schematic symbol for a switch."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-40, -15, 80, 30)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw switch symbol
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(Qt.black)

        # Draw connection dots
        painter.drawEllipse(-20, -3, 6, 6)
        painter.drawEllipse(14, -3, 6, 6)

        # Draw switch state
        closed = self.component.state.get('closed', False)

        painter.setPen(QPen(Qt.black, 2))
        if closed:
            # Closed switch - horizontal line
            painter.drawLine(-17, 0, 17, 0)
        else:
            # Open switch - angled line
            painter.drawLine(-17, 0, 15, -10)

        # Draw connection lines
        painter.setPen(QPen(Qt.black, 1.5))
        painter.drawLine(-30, 0, -20, 0)
        painter.drawLine(20, 0, 30, 0)

        # Draw value text if available
        if self.value_text:
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(-40, 15, 80, 15), Qt.AlignCenter, self.value_text)

    def update_symbol(self):
        """Update the symbol based on the component state."""
        # Show switch state
        closed = self.component.state.get('closed', False)
        self.value_text = "Closed" if closed else "Open"


class GroundSymbol(SchematicSymbolItem):
    """Schematic symbol for a ground connection."""

    def boundingRect(self):
        """Get the bounding rectangle of the symbol.

        Returns:
            QRectF bounding rectangle
        """
        return QRectF(-20, -10, 40, 30)

    def paint(self, painter, option, widget):
        """Paint the symbol.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Draw ground symbol
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw vertical line
        painter.drawLine(0, -10, 0, 0)

        # Draw horizontal lines
        painter.drawLine(-15, 0, 15, 0)
        painter.drawLine(-10, 5, 10, 5)
        painter.drawLine(-5, 10, 5, 10)


class WireSymbol(QGraphicsPathItem):
    """Schematic symbol for a wire connection."""

    def __init__(self, start_pos, end_pos, diagram):
        """Initialize a wire symbol.

        Args:
            start_pos: Start position as QPointF
            end_pos: End position as QPointF
            diagram: CircuitDiagramWidget
        """
        super().__init__()

        self.start_pos = start_pos
        self.end_pos = end_pos
        self.diagram = diagram

        # Create the path
        self.update_path()

        # Set up appearance
        self.setPen(QPen(Qt.black, 1.5))
        self.setZValue(5)  # Lower than components

    def update_path(self):
        """Update the wire path based on start and end positions."""
        path = QPainterPath()
        path.moveTo(self.start_pos)

        # If this is a straight wire, use a simple line
        if (self.start_pos.x() == self.end_pos.x() or
            self.start_pos.y() == self.end_pos.y()):
            path.lineTo(self.end_pos)
        else:
            # For angled wires, use two segments with a right angle
            # Determine which direction to go first (horizontal or vertical)
            dx = self.end_pos.x() - self.start_pos.x()
            dy = self.end_pos.y() - self.start_pos.y()

            if abs(dx) > abs(dy):
                # Go horizontal first
                mid_point = QPointF(self.end_pos.x(), self.start_pos.y())
            else:
                # Go vertical first
                mid_point = QPointF(self.start_pos.x(), self.end_pos.y())

            path.lineTo(mid_point)
            path.lineTo(self.end_pos)

        self.setPath(path)


class JunctionDotSymbol(QGraphicsEllipseItem):
    """Symbol for a junction between multiple wires."""

    def __init__(self, pos):
        """Initialize a junction dot.

        Args:
            pos: Position as QPointF
        """
        # Create a small filled circle
        radius = 3
        super().__init__(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2)

        # Set up appearance
        self.setPen(QPen(Qt.black, 1))
        self.setBrush(QBrush(Qt.black))
        self.setZValue(6)  # Above wires


class CircuitDiagramWidget(QGraphicsView):
    """Widget for displaying a schematic diagram of the circuit."""

    def __init__(self, simulator):
        """Initialize the circuit diagram widget.

        Args:
            simulator: CircuitSimulator instance
        """
        # Create a scene
        self.scene = QGraphicsScene()
        super().__init__(self.scene)

        # Store reference to simulator
        self.simulator = simulator

        # Set up the view
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        # Set the scene rect
        self.scene.setSceneRect(-500, -500, 1000, 1000)

        # For tracking symbols
        self.component_symbols = {}  # {component_id: SchematicSymbolItem}
        self.wire_symbols = []       # List of WireSymbol
        self.junction_dots = []      # List of JunctionDotSymbol

        # Layout properties
        self.auto_layout = True      # Whether to auto-layout components
        self.component_spacing = 100 # Spacing between components

        # Center the view initially
        self.centerOn(0, 0)

    def clear(self):
        """Clear the diagram."""
        self.scene.clear()
        self.component_symbols = {}
        self.wire_symbols = []
        self.junction_dots = []

    def update(self):
        """Update the diagram based on the current circuit state."""
        # Clear existing diagram
        self.clear()

        # Get all components from the simulator
        components = self.simulator.components

        # If no components, nothing to do
        if not components:
            return

        # Create symbols for all components
        for component_id, component in components.items():
            self._add_component_symbol(component)

        # Layout the components
        if self.auto_layout:
            self._layout_components()

        # Create wires between connected components
        self._create_wires()

        # Add junction dots where multiple wires meet
        self._add_junction_dots()

        # Update the scene
        self.scene.update()

    def _add_component_symbol(self, component):
        """Add a symbol for a component.

        Args:
            component: Component object

        Returns:
            SchematicSymbolItem or None if component type not supported
        """
        # Create the appropriate symbol based on component type
        component_type = component.__class__.__name__
        symbol = None

        if component_type == 'Resistor':
            symbol = ResistorSymbol(component, self)
        elif component_type == 'Capacitor':
            symbol = CapacitorSymbol(component, self)
        elif component_type == 'Inductor':
            symbol = InductorSymbol(component, self)
        elif component_type == 'Ground':
            symbol = GroundSymbol(component, self)
        elif component_type == 'DCVoltageSource':
            symbol = DCVoltageSourceSymbol(component, self)
        elif component_type == 'ACVoltageSource':
            symbol = ACVoltageSourceSymbol(component, self)
        elif component_type == 'DCCurrentSource':
            symbol = DCCurrentSourceSymbol(component, self)
        elif component_type == 'Diode':
            symbol = DiodeSymbol(component, self)
        elif component_type == 'LED':
            symbol = LEDSymbol(component, self)
        elif component_type == 'BJT':
            symbol = BJTSymbol(component, self)
        elif component_type == 'Switch':
            symbol = SwitchSymbol(component, self)
        else:
            # Unsupported component type
            return None

        # Add the symbol to the scene
        self.scene.addItem(symbol)

        # Store it
        self.component_symbols[component.id] = symbol

        return symbol

    def _layout_components(self):
        """Layout the components in the diagram.

        This implements a simple auto-layout algorithm.
        """
        # Sort components by type
        components_by_type = {}

        for component_id, symbol in self.component_symbols.items():
            component_type = symbol.component.__class__.__name__
            if component_type not in components_by_type:
                components_by_type[component_type] = []
            components_by_type[component_type].append(symbol)

        # Position components based on type
        x = -200
        y = -200
        max_height = 0

        # Layout order - sources first, then passive components, then active, then ground
        layout_order = [
            'DCVoltageSource', 'ACVoltageSource', 'DCCurrentSource',
            'Resistor', 'Capacitor', 'Inductor',
            'Diode', 'LED', 'BJT', 'Switch',
            'Ground'
        ]

        # Layout components in the specified order
        for component_type in layout_order:
            if component_type in components_by_type:
                symbols = components_by_type[component_type]

                for symbol in symbols:
                    # Set position
                    symbol.setPos(x, y)

                    # Update position for next component
                    x += self.component_spacing

                    # Track max height for this row
                    max_height = max(max_height, symbol.boundingRect().height())

                    # Move to next row if we've reached the edge
                    if x > 300:
                        x = -200
                        y += max_height + 50
                        max_height = 0

                # Add some space between component types
                if x > -200:  # If we added any components of this type
                    x += 50

                # Move to next row if we've reached the edge
                if x > 300:
                    x = -200
                    y += max_height + 50
                    max_height = 0

    def _create_wires(self):
        """Create wires between connected components."""
        # Clear existing wires
        self.wire_symbols = []

        # Track connections to avoid duplicates
        processed_connections = set()

        # Process each component
        for component_id, symbol in self.component_symbols.items():
            component = symbol.component

            # Get all connected components
            connected_components = component.get_connected_components()

            for other_id, connection_name, other_connection in connected_components:
                # Create a unique key for this connection
                connection_key = frozenset([(component_id, connection_name), (other_id, other_connection)])

                # Skip if we've already processed this connection
                if connection_key in processed_connections:
                    continue

                # Mark this connection as processed
                processed_connections.add(connection_key)

                # Get the other component symbol
                if other_id in self.component_symbols:
                    other_symbol = self.component_symbols[other_id]

                    # Create a wire between them
                    self._add_wire_between_symbols(
                        symbol, connection_name,
                        other_symbol, other_connection
                    )

    def _add_wire_between_symbols(self, symbol1, conn1, symbol2, conn2):
        """Add a wire between two component symbols.

        Args:
            symbol1: First SchematicSymbolItem
            conn1: First connection name
            symbol2: Second SchematicSymbolItem
            conn2: Second connection name

        Returns:
            WireSymbol
        """
        # Determine connection points based on component types and connection names
        pos1 = self._get_connection_position(symbol1, conn1)
        pos2 = self._get_connection_position(symbol2, conn2)

        # Create a wire
        wire = WireSymbol(pos1, pos2, self)

        # Add it to the scene
        self.scene.addItem(wire)

        # Store it
        self.wire_symbols.append(wire)

        return wire

    def _get_connection_position(self, symbol, connection_name):
        """Get the position of a connection point.

        Args:
            symbol: SchematicSymbolItem
            connection_name: Connection name

        Returns:
            QPointF position in scene coordinates
        """
        # Get symbol position
        symbol_pos = symbol.pos()

        # Determine connection point based on component type and connection name
        component_type = symbol.component.__class__.__name__

        if component_type == 'Resistor' or component_type == 'Capacitor' or component_type == 'Inductor':
            # Horizontal components with p1 on left, p2 on right
            if connection_name == 'p1':
                return symbol_pos + QPointF(0, 30)

        elif component_type == 'Diode' or component_type == 'LED':
            # Horizontal components with anode on left, cathode on right
            if connection_name == 'anode':
                return symbol_pos + QPointF(-30, 0)
            else:  # cathode
                return symbol_pos + QPointF(30, 0)

        elif component_type == 'BJT':
            # Transistor with collector on top, base on left, emitter on bottom
            if connection_name == 'collector':
                return symbol_pos + QPointF(0, -30)
            elif connection_name == 'base':
                return symbol_pos + QPointF(-30, 0)
            else:  # emitter
                return symbol_pos + QPointF(0, 30)

        elif component_type == 'Switch':
            # Horizontal switch with p1 on left, p2 on right
            if connection_name == 'p1':
                return symbol_pos + QPointF(-30, 0)
            else:  # p2
                return symbol_pos + QPointF(30, 0)

        elif component_type == 'Ground':
            # Ground with one connection on top
            return symbol_pos + QPointF(0, -10)

        # Default - just use symbol position
        return symbol_pos

    def _add_junction_dots(self):
        """Add junction dots where multiple wires meet."""
        # Find all wire endpoints
        wire_endpoints = {}

        for wire in self.wire_symbols:
            # Add start and end points
            start_pos = wire.start_pos
            end_pos = wire.end_pos

            # Round positions to nearest pixel to handle floating point differences
            start_key = (round(start_pos.x()), round(start_pos.y()))
            end_key = (round(end_pos.x()), round(end_pos.y()))

            for key in [start_key, end_key]:
                if key not in wire_endpoints:
                    wire_endpoints[key] = 0
                wire_endpoints[key] += 1

        # Create junction dots where 3 or more wires meet
        for (x, y), count in wire_endpoints.items():
            if count >= 3:
                # Create a junction dot
                junction = JunctionDotSymbol(QPointF(x, y))

                # Add it to the scene
                self.scene.addItem(junction)

                # Store it
                self.junction_dots.append(junction)

    def zoom_in(self):
        """Zoom in."""
        self.scale(1.2, 1.2)

    def zoom_out(self):
        """Zoom out."""
        self.scale(1/1.2, 1/1.2)

    def zoom_reset(self):
        """Reset zoom level."""
        self.resetTransform()

    def mouseDoubleClickEvent(self, event):
        """Handle mouse double-click events.

        Args:
            event: QMouseEvent
        """
        # On double-click, center on the clicked point
        self.centerOn(self.mapToScene(event.pos()))

        # Accept the event
        event.accept()

    def wheelEvent(self, event):
        """Handle mouse wheel events.

        Args:
            event: QWheelEvent
        """
        # Zoom on wheel scroll
        factor = 1.2
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor

        self.scale(factor, factor)
        event.accept()

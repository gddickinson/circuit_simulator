"""
Circuit Simulator - Circuit Board Widget
--------------------------------------
This module provides the interactive circuit board where components are placed.
"""

import os
import math
import logging
from enum import Enum, auto
from PyQt5.QtWidgets import (
    QWidget, QMenu, QAction, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsPixmapItem, QGraphicsLineItem,
    QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem,
    QSizePolicy
)
from PyQt5.QtCore import (
    Qt, QPointF, QRectF, QLineF, QTimer, pyqtSignal, QSize, QBuffer, QEvent
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap, QImage, QPainterPath,
    QTransform, QFont, QCursor, QDrag, QPolygonF, QPainterPathStroker
)

import config
from components.base_component import BaseComponent
from components.passive_components import Resistor, Capacitor, Inductor, Ground
from components.active_components import (
    DCVoltageSource, ACVoltageSource, DCCurrentSource, Diode, LED, BJT, Switch
)
from utils.logger import setup_logger, SimulationEvent

logger = logging.getLogger(__name__)


class CircuitBoardMode(Enum):
    """Modes for the circuit board."""
    SELECT = auto()
    PLACE = auto()
    CONNECT = auto()
    MOVE = auto()
    DELETE = auto()


class ComponentGraphicsItem(QGraphicsItem):
    """Graphics item for a circuit component."""

    def __init__(self, component, board):
        """Initialize a component graphics item.

        Args:
            component: Component object
            board: CircuitBoardWidget
        """
        super().__init__()

        self.component = component
        self.board = board
        self.selected = False
        self.highlighted = False
        self.connection_radius = 5  # Radius of connection points

        # Visual properties
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        # Set position
        self.update_position()

        # Set Z-value (components are above grid, below wires)
        self.setZValue(10)

    def boundingRect(self):
        """Get the bounding rectangle of the component.

        Returns:
            QRectF bounding rectangle
        """
        grid_size = self.board.grid_size

        # Calculate component size in pixels
        width = self.component.size[0] * grid_size
        height = self.component.size[1] * grid_size

        # Add margin for connections and selection border
        margin = max(10, self.connection_radius * 2)

        return QRectF(-width/2 - margin, -height/2 - margin,
                     width + margin*2, height + margin*2)

    def shape(self):
        """Get the shape of the component for selection and collision detection.

        Returns:
            QPainterPath shape
        """
        grid_size = self.board.grid_size

        # Calculate component size in pixels
        width = self.component.size[0] * grid_size
        height = self.component.size[1] * grid_size

        # Create the shape
        path = QPainterPath()
        path.addRect(-width/2, -height/2, width, height)

        # Add connection points to the shape
        for name, offset in self.component.connections.items():
            x, y = offset
            pos_x = x * grid_size
            pos_y = y * grid_size
            path.addEllipse(pos_x - self.connection_radius,
                           pos_y - self.connection_radius,
                           self.connection_radius * 2,
                           self.connection_radius * 2)

        return path

    def paint(self, painter, option, widget):
        """Paint the component.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        grid_size = self.board.grid_size

        # Calculate component size in pixels
        width = self.component.size[0] * grid_size
        height = self.component.size[1] * grid_size

        # Draw selection border if selected
        if self.selected or self.isSelected():
            painter.setPen(QPen(QColor(config.SELECTED_COLOR), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(-width/2, -height/2, width, height))

        # Draw highlight if highlighted
        if self.highlighted:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(config.SELECTED_COLOR, 50))
            painter.drawRect(QRectF(-width/2, -height/2, width, height))

        # Draw component based on its type
        component_type = self.component.__class__.__name__
        painter.setPen(QPen(Qt.black, 1))

        if component_type == 'Resistor':
            self.draw_resistor(painter, width, height)
        elif component_type == 'Capacitor':
            self.draw_capacitor(painter, width, height)
        elif component_type == 'Inductor':
            self.draw_inductor(painter, width, height)
        elif component_type == 'Ground':
            self.draw_ground(painter, width, height)
        elif component_type == 'DCVoltageSource':
            self.draw_dc_voltage_source(painter, width, height)
        elif component_type == 'ACVoltageSource':
            self.draw_ac_voltage_source(painter, width, height)
        elif component_type == 'DCCurrentSource':
            self.draw_dc_current_source(painter, width, height)
        elif component_type == 'Diode':
            self.draw_diode(painter, width, height)
        elif component_type == 'LED':
            self.draw_led(painter, width, height)
        elif component_type == 'BJT':
            self.draw_bjt(painter, width, height)
        elif component_type == 'Switch':
            self.draw_switch(painter, width, height)
        else:
            # Generic component
            painter.setBrush(QBrush(Qt.white))
            painter.drawRect(-width/2, -height/2, width, height)

            # Draw component name
            painter.setFont(QFont("Arial", 8))
            painter.drawText(-width/2, -height/2, width, height,
                            Qt.AlignCenter, component_type)

        # Draw connection points
        self.draw_connections(painter)

        # Draw component values
        self.draw_values(painter, width, height)

        # Draw debug info if enabled
        if self.board.debug_mode:
            self.draw_debug_info(painter)

    def draw_resistor(self, painter, width, height):
        """Draw a resistor.
        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw component body
        painter.setBrush(QBrush(Qt.white))
        painter.drawRect(QRectF(-width/2 + 10, -height/2, width - 20, height))

        # Draw zigzag symbol
        painter.setPen(QPen(Qt.black, 1.5))
        path = QPainterPath()
        path.moveTo(-width/2 + 10, 0)

        zigzag_width = width - 20
        zigzag_steps = 6
        step_width = zigzag_width / zigzag_steps
        half_height = height / 4

        for i in range(zigzag_steps + 1):
            x = -width/2 + 10 + i * step_width
            y = half_height if i % 2 == 0 else -half_height
            path.lineTo(x, y)

        path.lineTo(width/2 - 10, 0)
        painter.drawPath(path)

        # Draw connection lines - use QLineF objects for float coordinates
        painter.drawLine(QLineF(-width/2, 0, -width/2 + 10, 0))
        painter.drawLine(QLineF(width/2 - 10, 0, width/2, 0))

    def draw_capacitor(self, painter, width, height):
        """Draw a capacitor.
        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw plates
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(Qt.black, 1.5))

        # Left plate
        painter.drawLine(QLineF(-5, -height/2, -5, height/2))

        # Right plate
        painter.drawLine(QLineF(5, -height/2, 5, height/2))

        # Draw connection lines
        painter.drawLine(QLineF(-width/2, 0, -5, 0))
        painter.drawLine(QLineF(5, 0, width/2, 0))

    def draw_inductor(self, painter, width, height):
        """Draw an inductor.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw component body
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw inductor coil symbol
        coil_width = width - 20
        coil_steps = 4
        step_width = coil_width / (coil_steps * 2)
        coil_radius = height / 3

        path = QPainterPath()
        path.moveTo(-width/2, 0)
        path.lineTo(-width/2 + 10, 0)

        start_x = -width/2 + 10
        for i in range(coil_steps):
            # Draw semi-circle
            center_x = start_x + step_width + i * 2 * step_width
            # Use QRectF for the arcTo parameters
            path.arcTo(QRectF(center_x - coil_radius, -coil_radius,
                             coil_radius * 2, coil_radius * 2),
                      180, -180)

        path.lineTo(width/2, 0)
        painter.drawPath(path)

    def draw_ground(self, painter, width, height):
        """Draw a ground symbol.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw ground symbol
        painter.setBrush(QBrush(Qt.black))
        painter.setPen(QPen(Qt.black, 1.5))

        # Vertical line
        painter.drawLine(QLineF(0, -height/2, 0, height/4))

        # Horizontal lines
        line_width = width * 0.8

        # Draw three horizontal lines of decreasing width
        for i in range(3):
            y = height/4 + i * height/8
            curr_width = line_width * (3-i) / 3
            painter.drawLine(QLineF(-curr_width/2, y, curr_width/2, y))

    def draw_dc_voltage_source(self, painter, width, height):
        """Draw a DC voltage source.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw circle
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(Qt.black, 1.5))

        radius = min(width, height) / 2 - 5
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # Draw + and - symbols
        painter.setPen(QPen(Qt.black, 2))

        # + symbol at top
        plus_size = radius / 3
        painter.drawLine(QLineF(0, -plus_size, 0, plus_size))
        painter.drawLine(QLineF(-plus_size, 0, plus_size, 0))

        # - symbol at bottom
        minus_size = radius / 3
        painter.drawLine(QLineF(-minus_size, -radius/2, plus_size, -radius/2))

        # Draw connection lines
        painter.setPen(QPen(Qt.black, 1.5))
        painter.drawLine(QLineF(0, -radius, 0, -height/2))
        painter.drawLine(QLineF(0, radius, 0, height/2))

    def draw_ac_voltage_source(self, painter, width, height):
        """Draw an AC voltage source.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw circle
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(Qt.black, 1.5))

        radius = min(width, height) / 2 - 5
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # Draw sine wave symbol
        painter.setPen(QPen(Qt.black, 1.5))

        wave_width = radius * 1.2
        wave_height = radius / 2

        path = QPainterPath()
        path.moveTo(-wave_width/2, 0)

        # Draw one cycle of a sine wave
        steps = 20
        for i in range(steps + 1):
            x = -wave_width/2 + i * wave_width / steps
            y = -wave_height * math.sin(i * 2 * math.pi / steps)
            path.lineTo(x, y)

        painter.drawPath(path)

        # Draw connection lines
        painter.drawLine(QLineF(0, -radius, 0, -height/2))
        painter.drawLine(QLineF(0, radius, 0, height/2))

    def draw_dc_current_source(self, painter, width, height):
        """Draw a DC current source.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw circle
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(Qt.black, 1.5))

        radius = min(width, height) / 2 - 5
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # Draw arrow symbol
        painter.setPen(QPen(Qt.black, 1.5))

        # Arrow line
        arrow_height = radius * 1.2
        painter.drawLine(QLineF(0, -arrow_height/2, 0, arrow_height/2))

        # Arrow head
        arrow_head_size = radius / 3
        arrow_head = QPolygonF([
            QPointF(0, arrow_height/2),
            QPointF(-arrow_head_size, arrow_height/2 - arrow_head_size),
            QPointF(arrow_head_size, arrow_height/2 - arrow_head_size)
        ])
        painter.setBrush(QBrush(Qt.black))
        painter.drawPolygon(arrow_head)

        # Draw connection lines
        painter.setPen(QPen(Qt.black, 1.5))
        painter.drawLine(QLineF(0, -radius, 0, -height/2))
        painter.drawLine(QLineF(0, radius, 0, height/2))

    def draw_diode(self, painter, width, height):
        """Draw a diode.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw diode symbol
        painter.setPen(QPen(Qt.black, 1.5))

        # Triangle
        triangle = QPolygonF([
            QPointF(-10, -height/3),
            QPointF(10, 0),
            QPointF(-10, height/3)
        ])
        painter.setBrush(QBrush(Qt.white))
        painter.drawPolygon(triangle)

        # Line
        painter.drawLine(QLineF(10, -height/3, 10, height/3))

        # Draw connection lines
        painter.drawLine(QLineF(-width/2, 0, -10, 0))
        painter.drawLine(QLineF(10, 0, width/2, 0))

    def draw_led(self, painter, width, height):
        """Draw an LED.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw diode symbol
        painter.setPen(QPen(Qt.black, 1.5))

        # Triangle
        triangle = QPolygonF([
            QPointF(-10, -height/3),
            QPointF(10, 0),
            QPointF(-10, height/3)
        ])

        # Use LED color if available
        led_color = self.component.get_property("color", "red")
        if self.component.state.get("brightness", 0.0) > 0.01:
            # LED is lit, use color with brightness
            brightness = self.component.state.get("brightness", 0.0)
            color = QColor(led_color)
            color.setAlphaF(0.3 + 0.7 * brightness)  # Vary transparency with brightness
            painter.setBrush(QBrush(color))
        else:
            # LED is off, use white
            painter.setBrush(QBrush(Qt.white))

        painter.drawPolygon(triangle)

        # Line
        painter.drawLine(QLineF(10, -height/3, 10, height/3))

        # Draw arrows for light emission
        if self.component.state.get("brightness", 0.0) > 0.01:
            painter.setPen(QPen(QColor(led_color), 1, Qt.DashLine))
            arrow_size = height/3 + self.component.state.get("brightness", 0.0) * height/3

            # Draw two arrows
            for angle in [30, 0, -30]:
                rad = math.radians(angle)
                dx = math.cos(rad) * arrow_size
                dy = math.sin(rad) * arrow_size

                # Arrow line
                painter.drawLine(QLineF(10, 0, 10 + dx, -dy))

                # Arrow head
                arrow_head = QPolygonF([
                    QPointF(10 + dx, -dy),
                    QPointF(10 + dx - arrow_size/6, -dy - arrow_size/6),
                    QPointF(10 + dx - arrow_size/6, -dy + arrow_size/6)
                ])
                painter.setBrush(QBrush(QColor(led_color)))
                painter.drawPolygon(arrow_head)

        # Draw connection lines
        painter.setPen(QPen(Qt.black, 1.5))
        painter.drawLine(QLineF(-width/2, 0, -10, 0))
        painter.drawLine(QLineF(10, 0, width/2, 0))

    def draw_bjt(self, painter, width, height):
        """Draw a BJT transistor.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Check if NPN or PNP
        is_npn = self.component.get_property("type", "npn") == "npn"

        # Draw transistor symbol
        painter.setPen(QPen(Qt.black, 1.5))

        # Draw circle
        radius = min(width, height) / 2 - 10
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # Draw collector-emitter line
        painter.drawLine(QLineF(0, -radius * 0.7, 0, radius * 0.7))

        # Draw base line
        painter.drawLine(QLineF(-radius * 0.7, 0, 0, 0))

        # Draw emitter and collector leads with arrows
        if is_npn:
            # Emitter arrow points away from the line (NPN)
            arrow = QPolygonF([
                QPointF(0, radius * 0.5),
                QPointF(radius * 0.3, radius * 0.7),
                QPointF(radius * 0.1, radius * 0.9)
            ])
        else:
            # Emitter arrow points toward the line (PNP)
            arrow = QPolygonF([
                QPointF(radius * 0.3, radius * 0.7),
                QPointF(0, radius * 0.5),
                QPointF(radius * 0.1, radius * 0.3)
            ])

        painter.setBrush(QBrush(Qt.black))
        painter.drawPolygon(arrow)

        # Draw connection lines
        painter.drawLine(QLineF(0, -radius, 0, -height/2))  # Collector
        painter.drawLine(QLineF(-radius, 0, -width/2, 0))   # Base
        painter.drawLine(QLineF(0, radius, 0, height/2))    # Emitter

        # Draw labels
        painter.setFont(QFont("Arial", 8))
        painter.drawText(-5, -radius - 5, "C")
        painter.drawText(-radius - 10, 5, "B")
        painter.drawText(-5, radius + 15, "E")

    def draw_switch(self, painter, width, height):
        """Draw a switch.

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        # Draw switch symbol
        painter.setPen(QPen(Qt.black, 1.5))

        # Get switch state
        closed = self.component.state.get("closed", False)

        # Draw connection dots
        painter.setBrush(QBrush(Qt.black))
        painter.drawEllipse(QRectF(-width/3, -height/4, height/2, height/2))
        painter.drawEllipse(QRectF(width/3, -height/4, height/2, height/2))

        # Draw switch arm
        painter.setPen(QPen(Qt.black, 2))
        if closed:
            # Closed switch - straight line
            painter.drawLine(QLineF(-width/3 + height/4, 0, width/3 + height/4, 0))
        else:
            # Open switch - angled line
            painter.drawLine(QLineF(-width/3 + height/4, 0, width/3, -height * 0.4))

        # Draw connection lines
        painter.setPen(QPen(Qt.black, 1.5))
        painter.drawLine(QLineF(-width/2, 0, -width/3, 0))
        painter.drawLine(QLineF(width/3 + height/2, 0, width/2, 0))

    def draw_connections(self, painter):
        """Draw component connection points.

        Args:
            painter: QPainter object
        """
        grid_size = self.board.grid_size

        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QBrush(Qt.white))

        for name, offset in self.component.connections.items():
            x, y = offset
            pos_x = x * grid_size
            pos_y = y * grid_size

            # Draw connection point - use QRectF for float coordinates
            painter.drawEllipse(QRectF(
                pos_x - self.connection_radius,
                pos_y - self.connection_radius,
                self.connection_radius * 2,
                self.connection_radius * 2
            ))

            # If this connection is connected to another component,
            # fill the circle to indicate connection
            if self.component.is_connected(name):
                painter.setBrush(QBrush(Qt.black))
                painter.drawEllipse(QRectF(
                    pos_x - self.connection_radius/2,
                    pos_y - self.connection_radius/2,
                    self.connection_radius,
                    self.connection_radius
                ))
                painter.setBrush(QBrush(Qt.white))  # Reset brush

    def draw_values(self, painter, width, height):
        """Draw component values (voltage, current, etc.).

        Args:
            painter: QPainter object
            width, height: Component dimensions
        """
        if not self.board.show_values:
            return

        grid_size = self.board.grid_size
        component_type = self.component.__class__.__name__

        # Set up text rendering
        painter.setPen(QPen(Qt.black, 1))
        painter.setFont(QFont("Arial", 8))

        # Position for values
        text_y = height/2 + 15

        # Show different values based on component type
        if component_type == 'Resistor':
            resistance = self.component.get_property('resistance', config.DEFAULT_RESISTANCE)
            power = self.component.state.get('power', 0.0)

            if resistance >= 1e6:
                r_text = f"{resistance/1e6:.1f} MΩ"
            elif resistance >= 1e3:
                r_text = f"{resistance/1e3:.1f} kΩ"
            else:
                r_text = f"{resistance:.1f} Ω"

            if power >= 1:
                p_text = f"{power:.2f} W"
            elif power >= 1e-3:
                p_text = f"{power*1e3:.2f} mW"
            else:
                p_text = f"{power*1e6:.2f} µW"

            painter.drawText(QRectF(-width/2, text_y, width, 20),
                            Qt.AlignCenter, f"{r_text}, {p_text}")

        elif component_type in ['Capacitor', 'Inductor']:
            # Get the property name based on component type
            if component_type == 'Capacitor':
                prop_name = 'capacitance'
                default_val = config.DEFAULT_CAPACITANCE
                unit = 'F'
            else:  # Inductor
                prop_name = 'inductance'
                default_val = config.DEFAULT_INDUCTANCE
                unit = 'H'

            value = self.component.get_property(prop_name, default_val)

            # Format with appropriate prefix
            if value >= 1:
                v_text = f"{value:.1f} {unit}"
            elif value >= 1e-3:
                v_text = f"{value*1e3:.1f} m{unit}"
            elif value >= 1e-6:
                v_text = f"{value*1e6:.1f} µ{unit}"
            elif value >= 1e-9:
                v_text = f"{value*1e9:.1f} n{unit}"
            else:
                v_text = f"{value*1e12:.1f} p{unit}"

            painter.drawText(QRectF(-width/2, text_y, width, 20),
                            Qt.AlignCenter, v_text)

        elif component_type in ['DCVoltageSource', 'ACVoltageSource']:
            # Get voltage
            if component_type == 'DCVoltageSource':
                voltage = self.component.get_property('voltage', config.DEFAULT_VOLTAGE)
                v_text = f"{voltage:.1f} V"
            else:  # ACVoltageSource
                amplitude = self.component.get_property('amplitude', config.DEFAULT_VOLTAGE)
                frequency = self.component.get_property('frequency', config.DEFAULT_FREQUENCY)

                if frequency >= 1e6:
                    f_text = f"{frequency/1e6:.1f} MHz"
                elif frequency >= 1e3:
                    f_text = f"{frequency/1e3:.1f} kHz"
                else:
                    f_text = f"{frequency:.1f} Hz"

                v_text = f"{amplitude:.1f} V, {f_text}"

            painter.drawText(QRectF(-width/2, text_y, width, 20),
                            Qt.AlignCenter, v_text)

        elif component_type == 'DCCurrentSource':
            current = self.component.get_property('current', config.DEFAULT_CURRENT)

            if abs(current) >= 1:
                i_text = f"{current:.1f} A"
            elif abs(current) >= 1e-3:
                i_text = f"{current*1e3:.1f} mA"
            else:
                i_text = f"{current*1e6:.1f} µA"

            painter.drawText(QRectF(-width/2, text_y, width, 20),
                            Qt.AlignCenter, i_text)

        elif component_type in ['Diode', 'LED']:
            # Show forward voltage and current
            vf = self.component.get_property('forward_voltage', 0.7)
            current = self.component.state.get('currents', {}).get('anode', 0.0)

            if abs(current) >= 1:
                i_text = f"{current:.1f} A"
            elif abs(current) >= 1e-3:
                i_text = f"{current*1e3:.1f} mA"
            else:
                i_text = f"{current*1e6:.1f} µA"

            v_text = f"Vf={vf:.1f}V, {i_text}"

            painter.drawText(QRectF(-width/2, text_y, width, 20),
                            Qt.AlignCenter, v_text)

        elif component_type == 'BJT':
            # Show gain
            gain = self.component.get_property('gain', 100)
            region = self.component.state.get('region', 'cutoff')

            gain_text = f"β={gain}, {region}"

            painter.drawText(QRectF(-width/2, text_y, width, 20),
                            Qt.AlignCenter, gain_text)

    def draw_debug_info(self, painter):
        """Draw debug information.

        Args:
            painter: QPainter object
        """
        # Set up text rendering
        painter.setPen(QPen(Qt.darkGray, 1))
        painter.setFont(QFont("Arial", 7))

        # Draw component ID
        painter.drawText(-50, -30, f"ID: {self.component.id[:8]}")

        # Draw position and rotation
        pos = self.component.position
        rot = self.component.rotation
        painter.drawText(-50, -20, f"Pos: ({pos[0]}, {pos[1]}), Rot: {rot}°")

        # Draw connections
        conn_str = ", ".join(f"{k}" for k in self.component.connections.keys())
        painter.drawText(-50, -10, f"Conn: {conn_str}")

    def update_position(self):
        """Update the position and rotation from the component model."""
        grid_size = self.board.grid_size

        # Convert grid coordinates to scene coordinates
        x = self.component.position[0] * grid_size
        y = self.component.position[1] * grid_size

        # Set the position
        self.setPos(x, y)

        # Set the rotation
        self.setRotation(self.component.rotation)

    def mousePressEvent(self, event):
        """Handle mouse press events.

        Args:
            event: QGraphicsSceneMouseEvent
        """
        # Select the component
        self.selected = True
        self.scene().clearSelection()
        self.setSelected(True)

        # Store the original position
        self.drag_start_pos = self.pos()
        self.component_start_pos = self.component.position

        # Check if a connection point was clicked
        self.clicked_connection = self._get_connection_at(event.pos())

        # If in connect mode and a connection was clicked, start a connection
        if self.board.mode == CircuitBoardMode.CONNECT and self.clicked_connection:
            self.board._start_connection(self.component, self.clicked_connection)
            event.accept()
            return

        # Call the base class implementation for regular dragging
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events.

        Args:
            event: QGraphicsSceneMouseEvent
        """
        # If in connect mode and a connection is being created, update it
        if self.board.mode == CircuitBoardMode.CONNECT and self.board.creating_connection:
            connection_pos = self.mapToScene(self._get_connection_pos(self.clicked_connection))
            self.board._update_connection(connection_pos, event.scenePos())
            event.accept()
            return

        # Call the base class implementation for regular dragging
        super().mouseMoveEvent(event)

        # Snap to grid if moving
        if self.board.mode == CircuitBoardMode.MOVE:
            grid_size = self.board.grid_size

            # Get current scene position
            x = self.pos().x()
            y = self.pos().y()

            # Calculate grid-aligned position
            grid_x = round(x / grid_size) * grid_size
            grid_y = round(y / grid_size) * grid_size

            # Snap to grid
            self.setPos(grid_x, grid_y)

            # Update component position
            self.component.position = (int(grid_x / grid_size), int(grid_y / grid_size))

            # Update any connected wires
            self.board._update_connected_wires(self.component)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events.

        Args:
            event: QGraphicsSceneMouseEvent
        """
        # If in connect mode and a connection is being created, finish it
        if self.board.mode == CircuitBoardMode.CONNECT and self.board.creating_connection:
            # Check if the mouse is over another connection point
            item = self.scene().itemAt(event.scenePos(), QTransform())
            if isinstance(item, ComponentGraphicsItem):
                connection = item._get_connection_at(item.mapFromScene(event.scenePos()))
                if connection:
                    self.board._finish_connection(item.component, connection)

            # Clean up
            self.board._cancel_connection()
            event.accept()
            return

        # Check if the component was moved
        if (self.board.mode == CircuitBoardMode.MOVE and
            self.component_start_pos != self.component.position):
            # Record the move for undo
            self.board._add_to_undo_stack(
                "move_component",
                component_id=self.component.id,
                old_position=self.component_start_pos,
                new_position=self.component.position
            )

            # Mark changes
            self.board.set_unsaved_changes(True)

        # Call the base class implementation
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle mouse double-click events.

        Args:
            event: QGraphicsSceneMouseEvent
        """
        # Toggle switch state if this is a switch
        if self.component.__class__.__name__ == 'Switch':
            self.component.toggle()

            # Record the change for undo
            self.board._add_to_undo_stack(
                "toggle_switch",
                component_id=self.component.id,
                old_state=not self.component.state['closed'],
                new_state=self.component.state['closed']
            )

            # Mark changes
            self.board.set_unsaved_changes(True)

            # Update the component
            self.update()

            # Accept the event
            event.accept()
            return

        # Edit component properties
        self.board._show_component_properties(self.component)

        # Accept the event
        event.accept()

    def _get_connection_at(self, pos):
        """Get the connection name at the given position.

        Args:
            pos: Position in item coordinates

        Returns:
            Connection name or None if no connection at the position
        """
        grid_size = self.board.grid_size

        for name, offset in self.component.connections.items():
            x, y = offset
            conn_x = x * grid_size
            conn_y = y * grid_size

            # Check if the position is within the connection circle
            distance = math.sqrt((pos.x() - conn_x)**2 + (pos.y() - conn_y)**2)
            if distance <= self.connection_radius:
                return name

        return None

    def _get_connection_pos(self, connection_name):
        """Get the position of a connection point.

        Args:
            connection_name: Connection name

        Returns:
            QPointF position in item coordinates
        """
        grid_size = self.board.grid_size

        if connection_name in self.component.connections:
            x, y = self.component.connections[connection_name]
            return QPointF(x * grid_size, y * grid_size)

        return QPointF(0, 0)

    def itemChange(self, change, value):
        """Handle item change events.

        Args:
            change: GraphicsItemChange type
            value: Value of the change

        Returns:
            Adjusted value
        """
        if change == QGraphicsItem.ItemSelectedChange:
            # Update selected state
            self.selected = bool(value)

        return super().itemChange(change, value)


class WireGraphicsItem(QGraphicsItem):
    """Graphics item for a wire connection between components."""

    def __init__(self, start_component, start_connection, end_component, end_connection, board):
        """Initialize a wire graphics item.

        Args:
            start_component: Start component object
            start_connection: Start connection name
            end_component: End component object
            end_connection: End connection name
            board: CircuitBoardWidget
        """
        super().__init__()

        self.start_component = start_component
        self.start_connection = start_connection
        self.end_component = end_component
        self.end_connection = end_connection
        self.board = board

        self.selected = False
        self.highlighted = False

        # Visual properties
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        # Set Z-value (wires are above components)
        self.setZValue(5)

        # Calculate endpoints
        self.start_pos = self._get_start_pos()
        self.end_pos = self._get_end_pos()

    def boundingRect(self):
        """Get the bounding rectangle of the wire.

        Returns:
            QRectF bounding rectangle
        """
        # Get current endpoints
        self.start_pos = self._get_start_pos()
        self.end_pos = self._get_end_pos()

        # Calculate bounding rect with a margin
        margin = 5
        return QRectF(
            min(self.start_pos.x(), self.end_pos.x()) - margin,
            min(self.start_pos.y(), self.end_pos.y()) - margin,
            abs(self.end_pos.x() - self.start_pos.x()) + margin * 2,
            abs(self.end_pos.y() - self.start_pos.y()) + margin * 2
        )

    def shape(self):
        """Get the shape of the wire for selection and collision detection.

        Returns:
            QPainterPath shape
        """
        # Get current endpoints
        self.start_pos = self._get_start_pos()
        self.end_pos = self._get_end_pos()

        # Create a path for the wire with some thickness
        path = QPainterPath()
        path.moveTo(self.start_pos)

        # If this is a straight wire, we can use a simple line
        if self.start_pos.x() == self.end_pos.x() or self.start_pos.y() == self.end_pos.y():
            path.lineTo(self.end_pos)
        else:
            # For angled wires, use two segments with a right angle
            # Determine which direction to go first (horizontal or vertical)
            # Use a simple heuristic - go horizontal first if the horizontal distance is greater
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

        # Create a stroker to give the path thickness
        stroker = QPainterPathStroker()
        stroker.setWidth(8)  # Make it thicker than the visual wire for easier selection
        return stroker.createStroke(path)

    def paint(self, painter, option, widget):
        """Paint the wire.

        Args:
            painter: QPainter object
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Get current endpoints
        self.start_pos = self._get_start_pos()
        self.end_pos = self._get_end_pos()

        # Determine wire color and style based on state
        color = QColor(config.WIRE_COLOR)
        pen_width = config.WIRE_THICKNESS

        # If selected, use a different color and thickness
        if self.selected or self.isSelected():
            color = QColor(config.SELECTED_COLOR)
            pen_width += 1

        # If highlighted, use a highlighted color
        if self.highlighted:
            color = QColor(config.SELECTED_COLOR)

        # Create pen with the determined properties
        pen = QPen(color, pen_width)
        painter.setPen(pen)

        # Draw the wire
        if self.start_pos.x() == self.end_pos.x() or self.start_pos.y() == self.end_pos.y():
            # Straight wire
            painter.drawLine(self.start_pos, self.end_pos)
        else:
            # Angled wire with right angle
            # Determine which direction to go first (horizontal or vertical)
            dx = self.end_pos.x() - self.start_pos.x()
            dy = self.end_pos.y() - self.start_pos.y()

            if abs(dx) > abs(dy):
                # Go horizontal first
                mid_point = QPointF(self.end_pos.x(), self.start_pos.y())
            else:
                # Go vertical first
                mid_point = QPointF(self.start_pos.x(), self.end_pos.y())

            # Draw the two segments
            painter.drawLine(self.start_pos, mid_point)
            painter.drawLine(mid_point, self.end_pos)

    def _get_start_pos(self):
        """Get the starting position of the wire.

        Returns:
            QPointF position in scene coordinates
        """
        # Get the component graphics item for the start component
        start_item = self.board._get_component_item(self.start_component.id)
        if start_item:
            # Get the position of the connection point in scene coordinates
            conn_pos = start_item.mapToScene(
                start_item._get_connection_pos(self.start_connection)
            )
            return conn_pos

        # Fallback to using the component's connection point directly
        grid_size = self.board.grid_size
        connection_points = self.start_component.connection_points
        if self.start_connection in connection_points:
            x, y = connection_points[self.start_connection]
            return QPointF(x * grid_size, y * grid_size)

        return QPointF(0, 0)

    def _get_end_pos(self):
        """Get the ending position of the wire.

        Returns:
            QPointF position in scene coordinates
        """
        # Get the component graphics item for the end component
        end_item = self.board._get_component_item(self.end_component.id)
        if end_item:
            # Get the position of the connection point in scene coordinates
            conn_pos = end_item.mapToScene(
                end_item._get_connection_pos(self.end_connection)
            )
            return conn_pos

        # Fallback to using the component's connection point directly
        grid_size = self.board.grid_size
        connection_points = self.end_component.connection_points
        if self.end_connection in connection_points:
            x, y = connection_points[self.end_connection]
            return QPointF(x * grid_size, y * grid_size)

        return QPointF(0, 0)

    def mousePressEvent(self, event):
        """Handle mouse press events.

        Args:
            event: QGraphicsSceneMouseEvent
        """
        # Select the wire
        self.selected = True
        self.scene().clearSelection()
        self.setSelected(True)

        # Call the base class implementation
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle mouse double-click events.

        Args:
            event: QGraphicsSceneMouseEvent
        """
        # Delete the wire on double-click
        self.board._delete_wire(self)

        # Accept the event
        event.accept()

    def itemChange(self, change, value):
        """Handle item change events.

        Args:
            change: GraphicsItemChange type
            value: Value of the change

        Returns:
            Adjusted value
        """
        if change == QGraphicsItem.ItemSelectedChange:
            # Update selected state
            self.selected = bool(value)

        return super().itemChange(change, value)


class CircuitBoardWidget(QGraphicsView):
    """Interactive circuit board widget where components are placed and connected."""

    # Signal emitted when the mouse position changes (in grid coordinates)
    mouse_position_changed = pyqtSignal(int, int)

    def __init__(self, simulator, db_manager):
        """Initialize the circuit board widget.

        Args:
            simulator: CircuitSimulator instance
            db_manager: DatabaseManager instance
        """
        # Create a scene
        self.scene = QGraphicsScene()
        super().__init__(self.scene)

        # Store references
        self.simulator = simulator
        self.db_manager = db_manager

        # Set up the view
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        # Set the scene rect (will be updated later)
        self.scene.setSceneRect(-2000, -2000, 4000, 4000)

        # Grid properties
        self.grid_size = config.GRID_SIZE
        self.show_grid = True

        # Component display properties
        self.show_values = True
        self.debug_mode = False

        # Interaction state
        self.mode = CircuitBoardMode.SELECT
        self.creating_connection = False
        self.connection_start_component = None
        self.connection_start_point = None
        self.connection_line = None

        # Component for placement
        self.placement_component = None
        self.placement_item = None

        # Component items
        self.component_items = {}  # Dictionary of {component_id: ComponentGraphicsItem}
        self.wire_items = []       # List of WireGraphicsItem

        # Undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []

        # Clipboard
        self.clipboard = []

        # Unsaved changes flag
        self.unsaved_changes = False

        # Set up context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Set up the grid
        self._draw_grid()

        # Center the view
        self.center_view()

        # Set up event filter for key handling
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Filter events for key handling.

        Args:
            obj: Object that received the event
            event: Event object

        Returns:
            True if event was handled, False otherwise
        """
        # Check the event type first
        if event.type() == QEvent.KeyPress:
            # Handle key presses
            key = event.key()

            if key == Qt.Key_Delete:
                self.delete_selection()
                return True
            elif key == Qt.Key_Escape:
                if self.creating_connection:
                    self._cancel_connection()
                    return True
                elif self.mode == CircuitBoardMode.PLACE:
                    self._cancel_placement()
                    return True
            elif key == Qt.Key_R and self.scene.selectedItems():
                # Rotate selected components 90 degrees clockwise
                for item in self.scene.selectedItems():
                    if isinstance(item, ComponentGraphicsItem):
                        self._rotate_component(item.component, 90)
                return True

        # Pass the event to the parent class
        return super().eventFilter(obj, event)

    def set_mode(self, mode):
        """Set the current interaction mode.

        Args:
            mode: CircuitBoardMode value
        """
        self.mode = mode

        # Change cursor based on mode
        if mode == CircuitBoardMode.SELECT:
            self.setCursor(Qt.ArrowCursor)
        elif mode == CircuitBoardMode.PLACE:
            self.setCursor(Qt.CrossCursor)
        elif mode == CircuitBoardMode.CONNECT:
            self.setCursor(Qt.CrossCursor)  # Or a custom connector cursor

        # Cancel any ongoing operations
        if mode != CircuitBoardMode.PLACE and self.placement_component:
            self._cancel_placement()
        if mode != CircuitBoardMode.CONNECT and self.creating_connection:
            self._cancel_connection()

        # Log the mode change
        logger.info(f"Mode changed to {mode.name}")

    def _draw_grid(self):
        """Draw the grid background."""
        # Create a pixmap for the grid
        grid_size = self.grid_size
        pixmap_size = grid_size * 10  # 10x10 grid cells

        pixmap = QPixmap(pixmap_size, pixmap_size)
        pixmap.fill(QColor(config.BACKGROUND_COLOR))

        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(config.GRID_COLOR), 1))

        # Draw grid lines
        for i in range(0, pixmap_size + 1, grid_size):
            painter.drawLine(i, 0, i, pixmap_size)
            painter.drawLine(0, i, pixmap_size, i)

        painter.end()

        # Set the pixmap as the background brush
        self.setBackgroundBrush(QBrush(pixmap))

    def center_view(self):
        """Center the view on the origin."""
        self.centerOn(0, 0)

    def toggle_grid(self, show):
        """Toggle grid visibility.

        Args:
            show: Whether to show the grid
        """
        self.show_grid = show
        if show:
            self._draw_grid()
        else:
            self.setBackgroundBrush(QBrush(QColor(config.BACKGROUND_COLOR)))

    def zoom_in(self):
        """Zoom in."""
        self.scale(1.2, 1.2)

    def zoom_out(self):
        """Zoom out."""
        self.scale(1/1.2, 1/1.2)

    def zoom_reset(self):
        """Reset zoom level."""
        self.resetTransform()

    def clear(self):
        """Clear the circuit board."""
        # Remove all items from the scene
        self.scene.clear()

        # Clear component tracking
        self.component_items = {}
        self.wire_items = []

        # Clear undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []

        # Reset mode
        self.mode = CircuitBoardMode.SELECT
        self.creating_connection = False

        # Reset unsaved changes flag
        self.unsaved_changes = False

    def update(self):
        """Update the circuit board display."""
        # Update all component items
        for component_id, component in self.simulator.components.items():
            # Check if we already have an item for this component
            if component_id in self.component_items:
                # Update existing item
                self.component_items[component_id].update()
            else:
                # Create a new item
                self._add_component_item(component)

        # Remove any items for components that have been removed
        component_ids = list(self.component_items.keys())
        for component_id in component_ids:
            if component_id not in self.simulator.components:
                self._remove_component_item(component_id)

        # Update all wire items
        for wire in self.wire_items:
            wire.update()

        # Update the scene
        self.scene.update()

    def _add_component_item(self, component):
        """Add a graphics item for a component.

        Args:
            component: Component object

        Returns:
            ComponentGraphicsItem
        """
        # Create a graphics item for the component
        item = ComponentGraphicsItem(component, self)

        # Add it to the scene
        self.scene.addItem(item)

        # Store it
        self.component_items[component.id] = item

        return item

    def _remove_component_item(self, component_id):
        """Remove a component graphics item.

        Args:
            component_id: Component ID

        Returns:
            True if removed, False if not found
        """
        if component_id in self.component_items:
            # Remove it from the scene
            self.scene.removeItem(self.component_items[component_id])

            # Remove it from our tracking
            del self.component_items[component_id]

            return True

        return False

    def _get_component_item(self, component_id):
        """Get the graphics item for a component.

        Args:
            component_id: Component ID

        Returns:
            ComponentGraphicsItem or None if not found
        """
        return self.component_items.get(component_id)

    def _add_wire(self, start_component, start_connection, end_component, end_connection):
        """Add a wire between two components.

        Args:
            start_component: Start component object
            start_connection: Start connection name
            end_component: End component object
            end_connection: End connection name

        Returns:
            WireGraphicsItem
        """
        # Create a wire graphics item
        wire = WireGraphicsItem(
            start_component, start_connection,
            end_component, end_connection,
            self
        )

        # Add it to the scene
        self.scene.addItem(wire)

        # Store it
        self.wire_items.append(wire)

        # Connect the components in the simulator
        self.simulator.connect_components_at(
            start_component.id, start_connection,
            end_component.id, end_connection
        )

        return wire

    def _remove_wire(self, wire):
        """Remove a wire.

        Args:
            wire: WireGraphicsItem

        Returns:
            True if removed, False if not found
        """
        if wire in self.wire_items:
            # Disconnect the components in the simulator
            start_component = wire.start_component
            start_connection = wire.start_connection
            end_component = wire.end_component
            end_connection = wire.end_connection

            # Remove the connection in the component's state
            start_component.disconnect(start_connection)
            end_component.disconnect(end_connection)

            # Remove it from the scene
            self.scene.removeItem(wire)

            # Remove it from our tracking
            self.wire_items.remove(wire)

            return True

        return False

    def _delete_wire(self, wire):
        """Delete a wire and add to the undo stack.

        Args:
            wire: WireGraphicsItem

        Returns:
            True if deleted, False if not found
        """
        if wire in self.wire_items:
            # Add to undo stack
            self._add_to_undo_stack(
                "delete_wire",
                start_component_id=wire.start_component.id,
                start_connection=wire.start_connection,
                end_component_id=wire.end_component.id,
                end_connection=wire.end_connection
            )

            # Remove the wire
            result = self._remove_wire(wire)

            # Mark changes
            self.set_unsaved_changes(True)

            return result

        return False

    def _update_connected_wires(self, component):
        """Update all wires connected to a component.

        Args:
            component: Component object
        """
        # Find all wires connected to this component
        for wire in self.wire_items[:]:  # Copy the list since we might modify it
            if wire.start_component.id == component.id or wire.end_component.id == component.id:
                # Just update the wire - it will recalculate its endpoints
                wire.update()

    def _start_connection(self, component, connection_name):
        """Start creating a connection from a component.

        Args:
            component: Source component
            connection_name: Source connection name
        """
        self.creating_connection = True
        self.connection_start_component = component
        self.connection_start_point = connection_name

        # Create a temporary line for the connection
        start_pos = self._get_component_item(component.id).mapToScene(
            self._get_component_item(component.id)._get_connection_pos(connection_name)
        )
        self.connection_line = QGraphicsLineItem(start_pos.x(), start_pos.y(), start_pos.x(), start_pos.y())
        self.connection_line.setPen(QPen(QColor(config.SELECTED_COLOR), 2, Qt.DashLine))
        self.scene.addItem(self.connection_line)

    def _update_connection(self, start_pos, end_pos):
        """Update the temporary connection line.

        Args:
            start_pos: Start position (scene coordinates)
            end_pos: End position (scene coordinates)
        """
        if self.connection_line:
            self.connection_line.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())

    def _finish_connection(self, end_component, end_connection):
        """Finish creating a connection.

        Args:
            end_component: Target component
            end_connection: Target connection name

        Returns:
            True if connection was successful, False otherwise
        """
        if not self.creating_connection or not self.connection_start_component:
            return False

        # Check if the connection is valid
        if end_component.id == self.connection_start_component.id:
            # Can't connect a component to itself
            return False

        # Check if either connection is already connected
        if self.connection_start_component.is_connected(self.connection_start_point):
            return False

        if end_component.is_connected(end_connection):
            return False

        # Add a wire between the components
        wire = self._add_wire(
            self.connection_start_component, self.connection_start_point,
            end_component, end_connection
        )

        # Add to undo stack
        self._add_to_undo_stack(
            "add_wire",
            start_component_id=self.connection_start_component.id,
            start_connection=self.connection_start_point,
            end_component_id=end_component.id,
            end_connection=end_connection
        )

        # Mark changes
        self.set_unsaved_changes(True)

        return True

    def _cancel_connection(self):
        """Cancel the current connection creation."""
        self.creating_connection = False
        self.connection_start_component = None
        self.connection_start_point = None

        if self.connection_line:
            self.scene.removeItem(self.connection_line)
            self.connection_line = None

    def place_component(self, component_type, properties=None):
        """Start placing a component on the board.

        Args:
            component_type: Component type string (class name)
            properties: Optional component properties
        """
        # Cancel any existing placement or connection
        if self.creating_connection:
            self._cancel_connection()

        if self.placement_component:
            self._cancel_placement()

        # Create the component
        component = self._create_component(component_type, properties)
        if not component:
            logger.error(f"Failed to create component of type {component_type}")
            return

        # Set placement mode
        self.mode = CircuitBoardMode.PLACE
        self.placement_component = component

        # Create a graphics item for preview
        self.placement_item = ComponentGraphicsItem(component, self)
        self.placement_item.setOpacity(0.7)  # Semi-transparent
        self.scene.addItem(self.placement_item)

        # Initial position at center of view
        center = self.mapToScene(self.viewport().rect().center())
        grid_x = round(center.x() / self.grid_size)
        grid_y = round(center.y() / self.grid_size)
        component.position = (grid_x, grid_y)
        self.placement_item.update_position()

    def _cancel_placement(self):
        """Cancel the current component placement."""
        self.mode = CircuitBoardMode.SELECT
        self.placement_component = None

        if self.placement_item:
            self.scene.removeItem(self.placement_item)
            self.placement_item = None

    def _create_component(self, component_type, properties=None):
        """Create a component of the given type.

        Args:
            component_type: Component type string (class name)
            properties: Optional component properties

        Returns:
            Component object or None if creation failed
        """
        # Create the component based on type
        if component_type == "Resistor":
            component = Resistor(properties=properties)
        elif component_type == "Capacitor":
            component = Capacitor(properties=properties)
        elif component_type == "Inductor":
            component = Inductor(properties=properties)
        elif component_type == "Ground":
            component = Ground(properties=properties)
        elif component_type == "DCVoltageSource":
            component = DCVoltageSource(properties=properties)
        elif component_type == "ACVoltageSource":
            component = ACVoltageSource(properties=properties)
        elif component_type == "DCCurrentSource":
            component = DCCurrentSource(properties=properties)
        elif component_type == "Diode":
            component = Diode(properties=properties)
        elif component_type == "LED":
            component = LED(properties=properties)
        elif component_type == "BJT":
            component = BJT(properties=properties)
        elif component_type == "Switch":
            component = Switch(properties=properties)
        else:
            logger.error(f"Unknown component type: {component_type}")
            return None

        return component

    def _rotate_component(self, component, angle):
        """Rotate a component by the given angle.

        Args:
            component: Component object
            angle: Rotation angle in degrees

        Returns:
            True if rotation was successful
        """
        # Store original rotation for undo
        old_rotation = component.rotation

        # Apply rotation
        component.rotate(angle)

        # Update the component item
        component_item = self._get_component_item(component.id)
        if component_item:
            component_item.update_position()

        # Update connected wires
        self._update_connected_wires(component)

        # Add to undo stack
        self._add_to_undo_stack(
            "rotate_component",
            component_id=component.id,
            old_rotation=old_rotation,
            new_rotation=component.rotation
        )

        # Mark changes
        self.set_unsaved_changes(True)

        return True

    def _show_component_properties(self, component):
        """Show a dialog to edit component properties.

        Args:
            component: Component object
        """
        # This would be implemented to show a properties dialog
        # For now, we'll just log the component properties
        logger.info(f"Component properties: {component.properties}")

    def mousePressEvent(self, event):
        """Handle mouse press events.

        Args:
            event: QMouseEvent
        """
        if event.button() == Qt.LeftButton:
            # Convert mouse position to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Handle based on mode
            if self.mode == CircuitBoardMode.PLACE and self.placement_component:
                # Place the component
                component = self.placement_component

                # Add the component to the simulator
                if self.simulator.add_component(component):
                    # Add a graphics item for the component
                    self._add_component_item(component)

                    # Add to undo stack
                    self._add_to_undo_stack(
                        "add_component",
                        component_type=component.__class__.__name__,
                        properties=component.properties.copy(),
                        position=component.position,
                        rotation=component.rotation,
                        component_id=component.id
                    )

                    # Create a new component of the same type for continued placement
                    self.place_component(component.__class__.__name__, component.properties.copy())

                    # Mark changes
                    self.set_unsaved_changes(True)

            # Pass the event to the base class for selection, etc.
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events.

        Args:
            event: QMouseEvent
        """
        # Convert mouse position to scene coordinates
        scene_pos = self.mapToScene(event.pos())

        # Convert to grid coordinates
        grid_x = int(round(scene_pos.x() / self.grid_size))
        grid_y = int(round(scene_pos.y() / self.grid_size))

        # Emit signal with grid coordinates
        self.mouse_position_changed.emit(grid_x, grid_y)

        # Handle based on mode
        if self.mode == CircuitBoardMode.PLACE and self.placement_component:
            # Update the placement component position
            self.placement_component.position = (grid_x, grid_y)
            self.placement_item.update_position()

        # Pass the event to the base class
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events.

        Args:
            event: QMouseEvent
        """
        # Convert mouse position to scene coordinates
        scene_pos = self.mapToScene(event.pos())

        # Pass the event to the base class
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Handle key press events.

        Args:
            event: QKeyEvent
        """
        # Check for mode switching keys
        if event.key() == Qt.Key_S:
            # Select mode
            self.set_mode(CircuitBoardMode.SELECT)
            event.accept()
            return
        elif event.key() == Qt.Key_P:
            # Place mode
            self.set_mode(CircuitBoardMode.PLACE)
            event.accept()
            return
        elif event.key() == Qt.Key_C:
            # Connect mode
            self.set_mode(CircuitBoardMode.CONNECT)
            event.accept()
            return

        # Handle escape to cancel placement or connection
        if event.key() == Qt.Key_Escape:
            if self.creating_connection:
                self._cancel_connection()
                event.accept()
                return
            elif self.mode == CircuitBoardMode.PLACE:
                self._cancel_placement()
                event.accept()
                return

        # Handle rotate with R key
        if event.key() == Qt.Key_R and self.mode == CircuitBoardMode.PLACE and self.placement_component:
            self.placement_component.rotate(90)
            self.placement_item.update_position()
            event.accept()
            return

        # Pass the event to the base class
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle mouse double-click events at the board level.

        Args:
            event: QMouseEvent
        """
        # Convert mouse position to scene coordinates
        scene_pos = self.mapToScene(event.pos())

        # Check if there's a component at this position
        item = self.scene.itemAt(scene_pos, self.transform())

        if isinstance(item, ComponentGraphicsItem):
            # Let the component handle the double click
            item.mouseDoubleClickEvent(event)
        else:
            # Handle board-level double click
            super().mouseDoubleClickEvent(event)

    def _show_context_menu(self, pos):
        """Show the context menu.

        Args:
            pos: Position in view coordinates
        """
        # Convert position to scene coordinates
        scene_pos = self.mapToScene(pos)

        # Check if there are any items at this position
        items = self.scene.items(scene_pos)

        # Create menu
        menu = QMenu(self)

        if items:
            # Find the top-most item (highest Z-value)
            item = None
            for i in items:
                if isinstance(i, ComponentGraphicsItem) or isinstance(i, WireGraphicsItem):
                    item = i
                    break

            if item:
                # Item-specific actions
                if isinstance(item, ComponentGraphicsItem):
                    # Component actions
                    component = item.component

                    # Rotate action
                    rotate_action = QAction("Rotate 90° Clockwise", self)
                    rotate_action.triggered.connect(lambda: self._rotate_component(component, 90))
                    menu.addAction(rotate_action)

                    # Delete action
                    delete_action = QAction("Delete Component", self)
                    delete_action.triggered.connect(lambda: self.delete_component(component.id))
                    menu.addAction(delete_action)

                    # Properties action
                    props_action = QAction("Properties...", self)
                    props_action.triggered.connect(lambda: self._show_component_properties(component))
                    menu.addAction(props_action)

                    # If this is a switch, add toggle action
                    if component.__class__.__name__ == 'Switch':
                        toggle_action = QAction("Toggle Switch", self)
                        toggle_action.triggered.connect(lambda: self._toggle_switch(component))
                        menu.addAction(toggle_action)

                elif isinstance(item, WireGraphicsItem):
                    # Wire actions
                    delete_action = QAction("Delete Wire", self)
                    delete_action.triggered.connect(lambda: self._delete_wire(item))
                    menu.addAction(delete_action)
        else:
            # General actions
            paste_action = QAction("Paste", self)
            paste_action.triggered.connect(self.paste)
            paste_action.setEnabled(len(self.clipboard) > 0)
            menu.addAction(paste_action)

        # Show the menu
        menu.exec_(self.mapToGlobal(pos))

    def _toggle_switch(self, component):
        """Toggle a switch component.

        Args:
            component: Switch component
        """
        if component.__class__.__name__ == 'Switch':
            # Store original state for undo
            old_state = component.state.get('closed', False)

            # Toggle the switch
            component.toggle()

            # Update the component item
            component_item = self._get_component_item(component.id)
            if component_item:
                component_item.update()

            # Add to undo stack
            self._add_to_undo_stack(
                "toggle_switch",
                component_id=component.id,
                old_state=old_state,
                new_state=component.state.get('closed', False)
            )

            # Mark changes
            self.set_unsaved_changes(True)

    def _add_to_undo_stack(self, action_type, **kwargs):
        """Add an action to the undo stack.

        Args:
            action_type: Action type string
            **kwargs: Action parameters
        """
        # Clear the redo stack when a new action is performed
        self.redo_stack = []

        # Add the action to the undo stack
        self.undo_stack.append({
            'action': action_type,
            'params': kwargs
        })

    def undo(self):
        """Undo the last action."""
        if not self.undo_stack:
            return

        # Get the last action
        action = self.undo_stack.pop()

        # Add to redo stack
        self.redo_stack.append(action)

        # Perform the undo based on action type
        action_type = action['action']
        params = action['params']

        if action_type == "add_component":
            # Undo add component by removing it
            component_id = params['component_id']
            self.delete_component(component_id, add_to_undo=False)

        elif action_type == "delete_component":
            # Undo delete component by adding it back
            component_type = params['component_type']
            properties = params['properties']
            position = params['position']
            rotation = params['rotation']
            component_id = params['component_id']

            # Create the component
            component = self._create_component(component_type, properties)
            if component:
                # Set the same ID
                component.id = component_id

                # Set position and rotation
                component.position = position
                component.set_rotation(rotation)

                # Add to simulator
                self.simulator.add_component(component)

                # Add graphics item
                self._add_component_item(component)

        elif action_type == "move_component":
            # Undo move component by moving it back
            component_id = params['component_id']
            old_position = params['old_position']

            component = self.simulator.get_component(component_id)
            if component:
                # Set the original position
                component.position = old_position

                # Update the component item
                component_item = self._get_component_item(component_id)
                if component_item:
                    component_item.update_position()

                # Update connected wires
                self._update_connected_wires(component)

        elif action_type == "rotate_component":
            # Undo rotate component by rotating it back
            component_id = params['component_id']
            old_rotation = params['old_rotation']

            component = self.simulator.get_component(component_id)
            if component:
                # Set the original rotation
                component.set_rotation(old_rotation)

                # Update the component item
                component_item = self._get_component_item(component_id)
                if component_item:
                    component_item.update_position()

                # Update connected wires
                self._update_connected_wires(component)

        elif action_type == "add_wire":
            # Undo add wire by removing it
            start_component_id = params['start_component_id']
            start_connection = params['start_connection']
            end_component_id = params['end_component_id']
            end_connection = params['end_connection']

            # Find the wire
            for wire in self.wire_items[:]:
                if (wire.start_component.id == start_component_id and
                    wire.start_connection == start_connection and
                    wire.end_component.id == end_component_id and
                    wire.end_connection == end_connection):
                    # Remove the wire
                    self._remove_wire(wire)
                    break

        elif action_type == "delete_wire":
            # Undo delete wire by adding it back
            start_component_id = params['start_component_id']
            start_connection = params['start_connection']
            end_component_id = params['end_component_id']
            end_connection = params['end_connection']

            # Get the components
            start_component = self.simulator.get_component(start_component_id)
            end_component = self.simulator.get_component(end_component_id)

            if start_component and end_component:
                # Add the wire
                self._add_wire(
                    start_component, start_connection,
                    end_component, end_connection
                )

        elif action_type == "toggle_switch":
            # Undo toggle switch by toggling it back
            component_id = params['component_id']
            old_state = params['old_state']

            component = self.simulator.get_component(component_id)
            if component and component.__class__.__name__ == 'Switch':
                # Set the original state
                component.set_property('state', old_state)
                component.state['closed'] = old_state

                # Update the component item
                component_item = self._get_component_item(component_id)
                if component_item:
                    component_item.update()

        # Mark changes
        self.set_unsaved_changes(True)

    def redo(self):
        """Redo the last undone action."""
        if not self.redo_stack:
            return

        # Get the last undone action
        action = self.redo_stack.pop()

        # Add to undo stack
        self.undo_stack.append(action)

        # Perform the redo based on action type
        action_type = action['action']
        params = action['params']

        if action_type == "add_component":
            # Redo add component
            component_type = params['component_type']
            properties = params['properties']
            position = params['position']
            rotation = params['rotation']
            component_id = params['component_id']

            # Create the component
            component = self._create_component(component_type, properties)
            if component:
                # Set the same ID
                component.id = component_id

                # Set position and rotation
                component.position = position
                component.set_rotation(rotation)

                # Add to simulator
                self.simulator.add_component(component)

                # Add graphics item
                self._add_component_item(component)

        elif action_type == "delete_component":
            # Redo delete component
            component_id = params['component_id']
            self.delete_component(component_id, add_to_undo=False)

        elif action_type == "move_component":
            # Redo move component
            component_id = params['component_id']
            new_position = params['new_position']

            component = self.simulator.get_component(component_id)
            if component:
                # Set the new position
                component.position = new_position

                # Update the component item
                component_item = self._get_component_item(component_id)
                if component_item:
                    component_item.update_position()

                # Update connected wires
                self._update_connected_wires(component)

        elif action_type == "rotate_component":
            # Redo rotate component
            component_id = params['component_id']
            new_rotation = params['new_rotation']

            component = self.simulator.get_component(component_id)
            if component:
                # Set the new rotation
                component.set_rotation(new_rotation)

                # Update the component item
                component_item = self._get_component_item(component_id)
                if component_item:
                    component_item.update_position()

                # Update connected wires
                self._update_connected_wires(component)

        elif action_type == "add_wire":
            # Redo add wire
            start_component_id = params['start_component_id']
            start_connection = params['start_connection']
            end_component_id = params['end_component_id']
            end_connection = params['end_connection']

            # Get the components
            start_component = self.simulator.get_component(start_component_id)
            end_component = self.simulator.get_component(end_component_id)

            if start_component and end_component:
                # Add the wire
                self._add_wire(
                    start_component, start_connection,
                    end_component, end_connection
                )

        elif action_type == "delete_wire":
            # Redo delete wire
            start_component_id = params['start_component_id']
            start_connection = params['start_connection']
            end_component_id = params['end_component_id']
            end_connection = params['end_connection']

            # Find the wire
            for wire in self.wire_items[:]:
                if (wire.start_component.id == start_component_id and
                    wire.start_connection == start_connection and
                    wire.end_component.id == end_component_id and
                    wire.end_connection == end_connection):
                    # Remove the wire
                    self._remove_wire(wire)
                    break

        elif action_type == "toggle_switch":
            # Redo toggle switch
            component_id = params['component_id']
            new_state = params['new_state']

            component = self.simulator.get_component(component_id)
            if component and component.__class__.__name__ == 'Switch':
                # Set the new state
                component.set_property('state', new_state)
                component.state['closed'] = new_state

                # Update the component item
                component_item = self._get_component_item(component_id)
                if component_item:
                    component_item.update()

        # Mark changes
        self.set_unsaved_changes(True)

    def delete_component(self, component_id, add_to_undo=True):
        """Delete a component.

        Args:
            component_id: Component ID
            add_to_undo: Whether to add to the undo stack

        Returns:
            True if deleted, False if not found
        """
        component = self.simulator.get_component(component_id)
        if not component:
            return False

        # Add to undo stack
        if add_to_undo:
            self._add_to_undo_stack(
                "delete_component",
                component_id=component_id,
                component_type=component.__class__.__name__,
                properties=component.properties.copy(),
                position=component.position,
                rotation=component.rotation
            )

        # Remove all connected wires
        for wire in self.wire_items[:]:  # Copy the list since we'll modify it
            if wire.start_component.id == component_id or wire.end_component.id == component_id:
                self._remove_wire(wire)

        # Remove the component item
        self._remove_component_item(component_id)

        # Remove from simulator
        self.simulator.remove_component(component_id)

        # Mark changes
        self.set_unsaved_changes(True)

        return True

    def delete_selection(self):
        """Delete all selected items."""
        # Get all selected items
        selected_items = self.scene.selectedItems()

        if not selected_items:
            return

        # Delete components first, then wires
        for item in selected_items:
            if isinstance(item, ComponentGraphicsItem):
                self.delete_component(item.component.id)

        for item in selected_items:
            if isinstance(item, WireGraphicsItem):
                self._delete_wire(item)

    def cut_selection(self):
        """Cut selected components to clipboard."""
        # Copy first
        self.copy_selection()

        # Then delete
        self.delete_selection()

    def copy_selection(self):
        """Copy selected components to clipboard."""
        # Clear the clipboard
        self.clipboard = []

        # Get all selected component items
        selected_items = [
            item for item in self.scene.selectedItems()
            if isinstance(item, ComponentGraphicsItem)
        ]

        if not selected_items:
            return

        # Add components to clipboard
        for item in selected_items:
            component = item.component
            self.clipboard.append({
                'component_type': component.__class__.__name__,
                'properties': component.properties.copy(),
                'position_offset': component.position  # Position relative to selection center will be calculated during paste
            })

        # Calculate center of selection
        center_x = sum(item.component.position[0] for item in selected_items) / len(selected_items)
        center_y = sum(item.component.position[1] for item in selected_items) / len(selected_items)
        self.selection_center = (center_x, center_y)

        # Calculate position offsets relative to center
        for i, item in enumerate(selected_items):
            component = item.component
            offset_x = component.position[0] - center_x
            offset_y = component.position[1] - center_y
            self.clipboard[i]['position_offset'] = (offset_x, offset_y)

    def paste(self):
        """Paste components from clipboard."""
        if not self.clipboard:
            return

        # Get mouse position in grid coordinates
        center = self.mapToScene(self.viewport().rect().center())
        center_x = round(center.x() / self.grid_size)
        center_y = round(center.y() / self.grid_size)

        # Clear selection
        self.scene.clearSelection()

        # Create components from clipboard
        for item in self.clipboard:
            component_type = item['component_type']
            properties = item['properties']
            offset = item['position_offset']

            # Create the component
            component = self._create_component(component_type, properties)
            if component:
                # Calculate position
                pos_x = center_x + offset[0]
                pos_y = center_y + offset[1]
                component.position = (pos_x, pos_y)

                # Add to simulator
                self.simulator.add_component(component)

                # Add graphics item
                item = self._add_component_item(component)

                # Select the new item
                item.setSelected(True)

                # Add to undo stack
                self._add_to_undo_stack(
                    "add_component",
                    component_type=component_type,
                    properties=properties.copy(),
                    position=component.position,
                    rotation=component.rotation,
                    component_id=component.id
                )

        # Mark changes
        self.set_unsaved_changes(True)

    def select_all(self):
        """Select all components."""
        for item in self.component_items.values():
            item.setSelected(True)

    def has_unsaved_changes(self):
        """Check if there are unsaved changes.

        Returns:
            True if there are unsaved changes
        """
        return self.unsaved_changes

    def set_unsaved_changes(self, unsaved):
        """Set the unsaved changes flag.

        Args:
            unsaved: Whether there are unsaved changes
        """
        self.unsaved_changes = unsaved

    def export_to_file(self, file_path, format):
        """Export the circuit to an image file.

        Args:
            file_path: Path to save the file
            format: File format ('png', 'svg', 'pdf')

        Returns:
            True if successful, False otherwise
        """
        # Create an image to render to
        if format == 'png':
            # Create a pixmap
            rect = self.scene.itemsBoundingRect()
            if rect.isEmpty():
                rect = QRectF(-100, -100, 200, 200)

            # Add some margin
            margin = 50
            rect.adjust(-margin, -margin, margin, margin)

            # Create a pixmap
            pixmap = QPixmap(rect.width(), rect.height())
            pixmap.fill(Qt.white)

            # Create a painter to render the scene
            painter = QPainter(pixmap)
            self.scene.render(painter, QRectF(), rect)
            painter.end()

            # Save the pixmap
            if not pixmap.save(file_path, format):
                return False

        elif format == 'svg':
            # Create a file
            return False  # Not implemented yet

        elif format == 'pdf':
            # Create a file
            return False  # Not implemented yet

        else:
            return False

        return True

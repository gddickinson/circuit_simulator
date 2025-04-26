"""
Circuit Simulator - Main Window
-----------------------------
This module defines the main application window.
"""

import os
import time
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QAction, QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QDockWidget, QTabWidget, QLabel, QComboBox, QPushButton, QActionGroup
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon, QKeySequence

from gui.circuit_board import CircuitBoardWidget, CircuitBoardMode
from gui.circuit_diagram import CircuitDiagramWidget
from gui.component_panel import ComponentPanelWidget
from gui.analysis_panel import AnalysisPanelWidget
from gui.debug_console import DebugConsoleWidget
from simulation.circuit_solver import CircuitSolver
from simulation.simulator import CircuitSimulator
from utils.file_manager import FileManager
from utils.logger import SimulationEvent, setup_file_logger
import config

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for the circuit simulator."""

    def __init__(self, simulator, db_manager):
        """Initialize the main window.

        Args:
            simulator: CircuitSimulator instance
            db_manager: DatabaseManager instance
        """
        super().__init__()

        # Store references
        self.simulator = simulator
        self.db_manager = db_manager
        self.file_manager = FileManager(self.simulator, self.db_manager)

        # Initialize the circuit solver
        self.circuit_solver = CircuitSolver(self.simulator)

        # Setup the UI
        self.setWindowTitle("Circuit Simulator")
        self.setMinimumSize(1200, 800)

        # Add the simulator event listener
        self.simulator.add_event_listener(self._on_simulation_event)

        # Create the central widget
        self._create_central_widget()

        # Create the dock widgets
        self._create_dock_widgets()

        # Create actions and menus
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()

        # Setup simulation timer
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self._update_simulation)
        self.simulation_fps = 30  # Target FPS

        # Load GUI state
        self._load_settings()

        # Update status
        self.status_bar.showMessage("Ready")

        logger.info("Main window initialized")

    def _create_central_widget(self):
        """Create the central widget (splitter with circuit board and diagram)."""
        # Create the central splitter
        self.central_splitter = QSplitter(Qt.Horizontal)

        # Create circuit board
        self.circuit_board = CircuitBoardWidget(self.simulator, self.db_manager)

        # Create circuit diagram
        self.circuit_diagram = CircuitDiagramWidget(self.simulator)

        # Add widgets to splitter
        self.central_splitter.addWidget(self.circuit_board)
        self.central_splitter.addWidget(self.circuit_diagram)

        # Set initial sizes
        self.central_splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])

        # Set the central widget
        self.setCentralWidget(self.central_splitter)

    def _create_dock_widgets(self):
        """Create the dock widgets (component panel, analysis, debug console)."""
        # Create the component panel dock
        self.component_dock = QDockWidget("Components", self)
        self.component_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.component_panel = ComponentPanelWidget(self.db_manager, self.circuit_board)
        self.component_dock.setWidget(self.component_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.component_dock)

        # Create the analysis panel dock
        self.analysis_dock = QDockWidget("Analysis", self)
        self.analysis_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.analysis_panel = AnalysisPanelWidget(self.simulator)
        self.analysis_dock.setWidget(self.analysis_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.analysis_dock)

        # Create the debug console dock
        self.debug_dock = QDockWidget("Debug Console", self)
        self.debug_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea)
        self.debug_console = DebugConsoleWidget(self.simulator)
        self.debug_dock.setWidget(self.debug_console)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.debug_dock)

        # Tabify analysis and debug panels
        self.tabifyDockWidget(self.analysis_dock, self.debug_dock)

        # Raise analysis panel to front
        self.analysis_dock.raise_()

    def _create_actions(self):
        """Create actions for menus and toolbars."""
        # File actions
        self.new_action = QAction("&New Circuit", self)
        self.new_action.setShortcut(QKeySequence.New)
        self.new_action.setStatusTip("Create a new circuit")
        self.new_action.triggered.connect(self.new_circuit)

        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.setStatusTip("Open an existing circuit")
        self.open_action.triggered.connect(self.open_circuit)

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.setStatusTip("Save the current circuit")
        self.save_action.triggered.connect(self.save_circuit)

        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_as_action.setStatusTip("Save the current circuit with a new name")
        self.save_as_action.triggered.connect(self.save_circuit_as)

        self.export_action = QAction("&Export...", self)
        self.export_action.setStatusTip("Export the current circuit as an image or other format")
        self.export_action.triggered.connect(self.export_circuit)

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(self.close)

        # Edit actions
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.setStatusTip("Undo the last action")
        self.undo_action.triggered.connect(self.circuit_board.undo)

        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence.Redo)
        self.redo_action.setStatusTip("Redo the last undone action")
        self.redo_action.triggered.connect(self.circuit_board.redo)

        self.cut_action = QAction("Cu&t", self)
        self.cut_action.setShortcut(QKeySequence.Cut)
        self.cut_action.setStatusTip("Cut the selected components")
        self.cut_action.triggered.connect(self.circuit_board.cut_selection)

        self.copy_action = QAction("&Copy", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_action.setStatusTip("Copy the selected components")
        self.copy_action.triggered.connect(self.circuit_board.copy_selection)

        self.paste_action = QAction("&Paste", self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        self.paste_action.setStatusTip("Paste the copied components")
        self.paste_action.triggered.connect(self.circuit_board.paste)

        self.delete_action = QAction("&Delete", self)
        self.delete_action.setShortcut(QKeySequence.Delete)
        self.delete_action.setStatusTip("Delete the selected components")
        self.delete_action.triggered.connect(self.circuit_board.delete_selection)

        self.select_all_action = QAction("Select &All", self)
        self.select_all_action.setShortcut(QKeySequence.SelectAll)
        self.select_all_action.setStatusTip("Select all components")
        self.select_all_action.triggered.connect(self.circuit_board.select_all)

        # View actions
        self.zoom_in_action = QAction("Zoom &In", self)
        self.zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        self.zoom_in_action.setStatusTip("Zoom in the circuit view")
        self.zoom_in_action.triggered.connect(self.circuit_board.zoom_in)

        self.zoom_out_action = QAction("Zoom &Out", self)
        self.zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        self.zoom_out_action.setStatusTip("Zoom out the circuit view")
        self.zoom_out_action.triggered.connect(self.circuit_board.zoom_out)

        self.zoom_reset_action = QAction("&Reset Zoom", self)
        self.zoom_reset_action.setStatusTip("Reset the zoom level")
        self.zoom_reset_action.triggered.connect(self.circuit_board.zoom_reset)

        self.toggle_grid_action = QAction("Show &Grid", self)
        self.toggle_grid_action.setCheckable(True)
        self.toggle_grid_action.setChecked(True)
        self.toggle_grid_action.setStatusTip("Toggle the grid visibility")
        self.toggle_grid_action.triggered.connect(self.circuit_board.toggle_grid)

        # Simulation actions
        self.start_action = QAction("&Start Simulation", self)
        self.start_action.setStatusTip("Start the simulation")
        self.start_action.triggered.connect(self.start_simulation)

        self.pause_action = QAction("&Pause Simulation", self)
        self.pause_action.setStatusTip("Pause the simulation")
        self.pause_action.setEnabled(False)
        self.pause_action.triggered.connect(self.pause_simulation)

        self.stop_action = QAction("S&top Simulation", self)
        self.stop_action.setStatusTip("Stop the simulation")
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self.stop_simulation)

        self.reset_action = QAction("&Reset Simulation", self)
        self.reset_action.setStatusTip("Reset the simulation")
        self.reset_action.triggered.connect(self.reset_simulation)

        # Tools actions
        self.toggle_console_action = QAction("Debug &Console", self)
        self.toggle_console_action.setCheckable(True)
        self.toggle_console_action.setChecked(True)
        self.toggle_console_action.setStatusTip("Toggle the debug console visibility")
        self.toggle_console_action.triggered.connect(self._toggle_debug_console)

        self.toggle_component_panel_action = QAction("&Component Panel", self)
        self.toggle_component_panel_action.setCheckable(True)
        self.toggle_component_panel_action.setChecked(True)
        self.toggle_component_panel_action.setStatusTip("Toggle the component panel visibility")
        self.toggle_component_panel_action.triggered.connect(self._toggle_component_panel)

        self.toggle_analysis_panel_action = QAction("&Analysis Panel", self)
        self.toggle_analysis_panel_action.setCheckable(True)
        self.toggle_analysis_panel_action.setChecked(True)
        self.toggle_analysis_panel_action.setStatusTip("Toggle the analysis panel visibility")
        self.toggle_analysis_panel_action.triggered.connect(self._toggle_analysis_panel)

        # Examples actions
        self.example_menu_actions = []

        # Help actions
        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("Show the application's About box")
        self.about_action.triggered.connect(self.about)

        self.help_action = QAction("&Help", self)
        self.help_action.setShortcut(QKeySequence.HelpContents)
        self.help_action.setStatusTip("Show the application's Help")
        self.help_action.triggered.connect(self.show_help)

    def _create_menus(self):
        """Create the menus."""
        # File menu
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.export_action)
        self.file_menu.addSeparator()

        # Add recent files submenu
        self.recent_menu = self.file_menu.addMenu("Recent Files")
        self._update_recent_files_menu()

        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        # Edit menu
        self.edit_menu = self.menuBar().addMenu("&Edit")
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.cut_action)
        self.edit_menu.addAction(self.copy_action)
        self.edit_menu.addAction(self.paste_action)
        self.edit_menu.addAction(self.delete_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.select_all_action)

        # View menu
        self.view_menu = self.menuBar().addMenu("&View")
        self.view_menu.addAction(self.zoom_in_action)
        self.view_menu.addAction(self.zoom_out_action)
        self.view_menu.addAction(self.zoom_reset_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.toggle_grid_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.toggle_component_panel_action)
        self.view_menu.addAction(self.toggle_analysis_panel_action)
        self.view_menu.addAction(self.toggle_console_action)

        # Simulation menu
        self.simulation_menu = self.menuBar().addMenu("&Simulation")
        self.simulation_menu.addAction(self.start_action)
        self.simulation_menu.addAction(self.pause_action)
        self.simulation_menu.addAction(self.stop_action)
        self.simulation_menu.addAction(self.reset_action)

        # Examples menu
        self.examples_menu = self.menuBar().addMenu("E&xamples")
        self._update_examples_menu()

        # Help menu
        self.help_menu = self.menuBar().addMenu("&Help")
        self.help_menu.addAction(self.help_action)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.about_action)

    def _create_toolbars(self):
        """Create the toolbars."""
        # File toolbar
        self.file_toolbar = self.addToolBar("File")
        self.file_toolbar.addAction(self.new_action)
        self.file_toolbar.addAction(self.open_action)
        self.file_toolbar.addAction(self.save_action)

        # Edit toolbar
        self.edit_toolbar = self.addToolBar("Edit")
        self.edit_toolbar.addAction(self.undo_action)
        self.edit_toolbar.addAction(self.redo_action)
        self.edit_toolbar.addAction(self.cut_action)
        self.edit_toolbar.addAction(self.copy_action)
        self.edit_toolbar.addAction(self.paste_action)
        self.edit_toolbar.addAction(self.delete_action)


        self.mode_toolbar = self.addToolBar("Mode")
        self.select_mode_action = QAction("Select Mode", self)
        self.select_mode_action.setCheckable(True)
        self.select_mode_action.setChecked(True)  # Default mode
        self.select_mode_action.triggered.connect(lambda: self.circuit_board.set_mode(CircuitBoardMode.SELECT))

        self.place_mode_action = QAction("Place Mode", self)
        self.place_mode_action.setCheckable(True)
        self.place_mode_action.triggered.connect(lambda: self.circuit_board.set_mode(CircuitBoardMode.PLACE))

        self.connect_mode_action = QAction("Connect Mode", self)
        self.connect_mode_action.setCheckable(True)
        self.connect_mode_action.triggered.connect(lambda: self.circuit_board.set_mode(CircuitBoardMode.CONNECT))

        # Create action group to ensure only one mode is active
        self.mode_action_group = QActionGroup(self)
        self.mode_action_group.addAction(self.select_mode_action)
        self.mode_action_group.addAction(self.place_mode_action)
        self.mode_action_group.addAction(self.connect_mode_action)
        self.mode_action_group.setExclusive(True)

        # Add to toolbar
        self.mode_toolbar.addAction(self.select_mode_action)
        self.mode_toolbar.addAction(self.place_mode_action)
        self.mode_toolbar.addAction(self.connect_mode_action)


        # View toolbar
        self.view_toolbar = self.addToolBar("View")
        self.view_toolbar.addAction(self.zoom_in_action)
        self.view_toolbar.addAction(self.zoom_out_action)
        self.view_toolbar.addAction(self.zoom_reset_action)
        self.view_toolbar.addAction(self.toggle_grid_action)

        # Simulation toolbar
        self.simulation_toolbar = self.addToolBar("Simulation")
        self.simulation_toolbar.addAction(self.start_action)
        self.simulation_toolbar.addAction(self.pause_action)
        self.simulation_toolbar.addAction(self.stop_action)
        self.simulation_toolbar.addAction(self.reset_action)

        # Add simulation speed control
        self.simulation_toolbar.addSeparator()
        speed_label = QLabel("Speed: ")
        self.simulation_toolbar.addWidget(speed_label)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x", "4x", "10x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._set_simulation_speed)
        self.simulation_toolbar.addWidget(self.speed_combo)

    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add simulation time display
        self.time_label = QLabel("Time: 0.000 s")
        self.status_bar.addPermanentWidget(self.time_label)

        # Add FPS display
        self.fps_label = QLabel("FPS: 0.0")
        self.status_bar.addPermanentWidget(self.fps_label)

        # Add mouse position display
        self.position_label = QLabel("Position: (0, 0)")
        self.status_bar.addPermanentWidget(self.position_label)

        # Connect mouse position signal from circuit board
        self.circuit_board.mouse_position_changed.connect(self._update_mouse_position)

    def _update_mouse_position(self, x, y):
        """Update the mouse position display.

        Args:
            x, y: Mouse coordinates
        """
        self.position_label.setText(f"Position: ({x}, {y})")

    def _update_recent_files_menu(self):
        """Update the recent files menu."""
        self.recent_menu.clear()
        recent_files = self.file_manager.get_recent_files()

        if not recent_files:
            self.recent_menu.addAction("No recent files")
            return

        for path in recent_files:
            action = QAction(os.path.basename(path), self)
            action.setData(path)
            action.setStatusTip(path)
            action.triggered.connect(self._open_recent_file)
            self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        clear_action = QAction("Clear Recent Files", self)
        clear_action.triggered.connect(self.file_manager.clear_recent_files)
        clear_action.triggered.connect(self._update_recent_files_menu)
        self.recent_menu.addAction(clear_action)

    def _open_recent_file(self):
        """Open a file from the recent files menu."""
        action = self.sender()
        if action:
            path = action.data()
            self.open_circuit(path)

    def _update_examples_menu(self):
        """Update the examples menu."""
        self.examples_menu.clear()
        examples = self.file_manager.get_example_circuits()

        if not examples:
            self.examples_menu.addAction("No example circuits")
            return

        for name, path in examples:
            action = QAction(name, self)
            action.setData(path)
            action.setStatusTip(f"Load the {name} example circuit")
            action.triggered.connect(self._load_example_circuit)
            self.examples_menu.addAction(action)
            self.example_menu_actions.append(action)

    def _load_example_circuit(self):
        """Load an example circuit from the examples menu."""
        action = self.sender()
        if action:
            path = action.data()
            self.load_example(path)

    def _toggle_debug_console(self, checked):
        """Toggle the debug console visibility."""
        self.debug_dock.setVisible(checked)

    def _toggle_component_panel(self, checked):
        """Toggle the component panel visibility."""
        self.component_dock.setVisible(checked)

    def _toggle_analysis_panel(self, checked):
        """Toggle the analysis panel visibility."""
        self.analysis_dock.setVisible(checked)

    def _set_simulation_speed(self, speed_text):
        """Set the simulation speed.

        Args:
            speed_text: Speed as text (e.g., "1x")
        """
        # Parse the speed multiplier
        speed = float(speed_text.rstrip("x"))

        # Calculate the timer interval (ms)
        interval = int(1000.0 / (self.simulation_fps * speed))

        # Update the timer
        if self.simulation_timer.isActive():
            self.simulation_timer.stop()
            self.simulation_timer.setInterval(interval)
            self.simulation_timer.start()
        else:
            self.simulation_timer.setInterval(interval)

    def _on_simulation_event(self, event_type, data):
        """Handle simulation events.

        Args:
            event_type: Event type from SimulationEvent enum
            data: Event data
        """
        if event_type == SimulationEvent.SIMULATION_STARTED:
            self.start_action.setEnabled(False)
            self.pause_action.setEnabled(True)
            self.stop_action.setEnabled(True)
            self.status_bar.showMessage("Simulation running")
            self.simulation_timer.start()

        elif event_type == SimulationEvent.SIMULATION_PAUSED:
            self.start_action.setEnabled(True)
            self.pause_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.status_bar.showMessage("Simulation paused")
            self.simulation_timer.stop()

        elif event_type == SimulationEvent.SIMULATION_STOPPED:
            self.start_action.setEnabled(True)
            self.pause_action.setEnabled(False)
            self.stop_action.setEnabled(False)
            self.status_bar.showMessage("Simulation stopped")
            self.simulation_timer.stop()

        elif event_type == SimulationEvent.SIMULATION_RESET:
            self.time_label.setText("Time: 0.000 s")
            self.fps_label.setText("FPS: 0.0")
            self.status_bar.showMessage("Simulation reset")

        elif event_type == SimulationEvent.SIMULATION_UPDATED:
            # Update the time display
            simulation_time = data.get('simulation_time', 0.0)
            self.time_label.setText(f"Time: {simulation_time:.3f} s")

            # Update the FPS display
            fps = data.get('fps', 0.0)
            self.fps_label.setText(f"FPS: {fps:.1f}")

    def _update_simulation(self):
        """Update the simulation."""
        # Calculate elapsed time since last update
        current_time = time.time()
        if hasattr(self, '_last_update_time'):
            elapsed = current_time - self._last_update_time
        else:
            elapsed = 1.0 / self.simulation_fps

        self._last_update_time = current_time

        # Update the simulation
        stats = self.simulator.update(elapsed)

        # Update the circuit board and diagram
        self.circuit_board.update()
        self.circuit_diagram.update()

        # Update the analysis panel
        self.analysis_panel.update()

    def _load_settings(self):
        """Load application settings."""
        # This would load settings from a QSettings object
        # or from the database
        self.simulation_fps = 30  # Default FPS

    def _save_settings(self):
        """Save application settings."""
        # This would save settings to a QSettings object
        # or to the database
        pass

    def new_circuit(self):
        """Create a new circuit."""
        # Check if current circuit has unsaved changes
        if self.circuit_board.has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The current circuit has unsaved changes. Do you want to save them?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                if not self.save_circuit():
                    # User cancelled save, abort new circuit
                    return
            elif reply == QMessageBox.Cancel:
                # User cancelled, abort new circuit
                return

        # Clear the simulator
        self.simulator.clear()

        # Clear the circuit board
        self.circuit_board.clear()

        # Clear the circuit diagram
        self.circuit_diagram.clear()

        # Reset simulation
        self.reset_simulation()

        # Update UI
        self.status_bar.showMessage("New circuit created")
        self.circuit_board.set_unsaved_changes(False)

    def open_circuit(self, path=None):
        """Open a circuit from a file.

        Args:
            path: Path to the circuit file. If None, show a file dialog.
        """
        # Check if current circuit has unsaved changes
        if self.circuit_board.has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The current circuit has unsaved changes. Do you want to save them?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                if not self.save_circuit():
                    # User cancelled save, abort open
                    return
            elif reply == QMessageBox.Cancel:
                # User cancelled, abort open
                return

        # If no path provided, show file dialog
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Circuit", "", "Circuit Files (*.circuit);;All Files (*)"
            )

            if not path:
                # User cancelled, abort open
                return

        # Load the circuit
        success = self.file_manager.load_circuit(path)

        if success:
            # Update the circuit board
            self.circuit_board.update()

            # Update the circuit diagram
            self.circuit_diagram.update()

            # Reset simulation
            self.reset_simulation()

            # Update UI
            self.status_bar.showMessage(f"Opened circuit from {path}")
            self.circuit_board.set_unsaved_changes(False)

            # Add to recent files
            self.file_manager.add_recent_file(path)
            self._update_recent_files_menu()

            return True
        else:
            # Show error message
            QMessageBox.critical(
                self, "Error",
                f"Failed to open circuit from {path}",
                QMessageBox.Ok
            )
            return False

    def save_circuit(self):
        """Save the current circuit to the current file.

        Returns:
            True if successful, False otherwise
        """
        # If no current file, use save as
        if not self.file_manager.current_file:
            return self.save_circuit_as()

        # Save the circuit
        success = self.file_manager.save_circuit()

        if success:
            # Update UI
            self.status_bar.showMessage(f"Saved circuit to {self.file_manager.current_file}")
            self.circuit_board.set_unsaved_changes(False)

            # Add to recent files
            self.file_manager.add_recent_file(self.file_manager.current_file)
            self._update_recent_files_menu()

            return True
        else:
            # Show error message
            QMessageBox.critical(
                self, "Error",
                f"Failed to save circuit to {self.file_manager.current_file}",
                QMessageBox.Ok
            )
            return False

    def save_circuit_as(self):
        """Save the current circuit to a new file.

        Returns:
            True if successful, False otherwise
        """
        # Show file dialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Circuit As", "", "Circuit Files (*.circuit);;All Files (*)"
        )

        if not path:
            # User cancelled, abort save
            return False

        # Ensure the path has the correct extension
        if not path.endswith('.circuit'):
            path += '.circuit'

        # Save the circuit
        success = self.file_manager.save_circuit_as(path)

        if success:
            # Update UI
            self.status_bar.showMessage(f"Saved circuit to {path}")
            self.circuit_board.set_unsaved_changes(False)

            # Add to recent files
            self.file_manager.add_recent_file(path)
            self._update_recent_files_menu()

            return True
        else:
            # Show error message
            QMessageBox.critical(
                self, "Error",
                f"Failed to save circuit to {path}",
                QMessageBox.Ok
            )
            return False

    def export_circuit(self):
        """Export the current circuit to an image or other format."""
        # Show file dialog
        path, filter_type = QFileDialog.getSaveFileName(
            self, "Export Circuit", "", "PNG Image (*.png);;SVG Image (*.svg);;PDF Document (*.pdf)"
        )

        if not path:
            # User cancelled, abort export
            return

        # Determine export format from filter
        if "PNG" in filter_type:
            fmt = "png"
            if not path.endswith(".png"):
                path += ".png"
        elif "SVG" in filter_type:
            fmt = "svg"
            if not path.endswith(".svg"):
                path += ".svg"
        elif "PDF" in filter_type:
            fmt = "pdf"
            if not path.endswith(".pdf"):
                path += ".pdf"
        else:
            # Unknown format
            QMessageBox.critical(
                self, "Error",
                "Unknown export format",
                QMessageBox.Ok
            )
            return

        # Export the circuit
        success = self.circuit_board.export_to_file(path, fmt)

        if success:
            # Update UI
            self.status_bar.showMessage(f"Exported circuit to {path}")
        else:
            # Show error message
            QMessageBox.critical(
                self, "Error",
                f"Failed to export circuit to {path}",
                QMessageBox.Ok
            )

    def load_example(self, example_path):
        """Load an example circuit.

        Args:
            example_path: Path to the example circuit file
        """
        return self.open_circuit(example_path)

    def start_simulation(self):
        """Start or resume the simulation."""
        if self.simulator.paused:
            self.simulator.resume_simulation()
        else:
            # Build the circuit
            self.simulator.build_circuit_from_components()
            self.simulator.start_simulation()

        # Start the simulation timer
        self.simulation_timer.start()

    def pause_simulation(self):
        """Pause the simulation."""
        self.simulator.pause_simulation()

    def stop_simulation(self):
        """Stop the simulation."""
        self.simulator.stop_simulation()

    def reset_simulation(self):
        """Reset the simulation."""
        self.simulator.reset_simulation()

        # Update the circuit board
        self.circuit_board.update()

        # Update the circuit diagram
        self.circuit_diagram.update()

        # Update the analysis panel
        self.analysis_panel.update()

    def about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self, "About Circuit Simulator",
            "<h1>Circuit Simulator</h1>"
            "<p>Version 1.0</p>"
            "<p>A circuit simulation tool for education and prototyping.</p>"
            "<p>Created with PyQt5.</p>"
        )

    def show_help(self):
        """Show the help dialog."""
        QMessageBox.information(
            self, "Circuit Simulator Help",
            "<h1>Circuit Simulator Help</h1>"
            "<p>To create a circuit:</p>"
            "<ol>"
            "<li>Drag components from the Component Panel to the Circuit Board.</li>"
            "<li>Connect components by clicking and dragging from one connection point to another.</li>"
            "<li>Use the Simulation menu to start, pause, and stop the simulation.</li>"
            "<li>Use the Analysis Panel to view graphs and measurements.</li>"
            "</ol>"
            "<p>For more help, please refer to the documentation.</p>"
        )

    def closeEvent(self, event):
        """Handle the window close event.

        Args:
            event: Close event
        """
        # Check if current circuit has unsaved changes
        if self.circuit_board.has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The current circuit has unsaved changes. Do you want to save them?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                if not self.save_circuit():
                    # User cancelled save, abort close
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                # User cancelled, abort close
                event.ignore()
                return

        # Save settings
        self._save_settings()

        # Close the database connection
        self.db_manager.close_connection()

        # Accept the close event
        event.accept()

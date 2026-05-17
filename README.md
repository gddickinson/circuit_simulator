# Circuit Simulator

An interactive electronic circuit simulator built with Python and PyQt5. Place components on a grid-based circuit board, wire them together, and run real-time simulations with visual feedback, automatic schematic generation, and measurement tools.

## Features

### Interactive Circuit Board
- Grid-based component placement with snap-to-grid
- Click-and-drag wiring between connection points
- Zoom (0.5x--2.0x) and pan controls
- Component selection, rotation, and deletion
- Multiple board modes for placing, wiring, and selecting

### Real-Time Simulation
- Modified Nodal Analysis (MNA) circuit solver
- Configurable timestep (default 1ms), convergence threshold, and iteration limits
- Live voltage and current visualization with color-coded feedback
- 30 FPS simulation update loop

### Automatic Schematic Diagram
- Auto-generated circuit schematic view alongside the board layout

### Analysis Tools
- Built-in analysis panel for measurements
- Debug console for simulation events and logging

### Component Library
- **Passive**: Resistors (1k default), Capacitors (1uF), Inductors (1mH), Ground
- **Active**: Diodes, LEDs, BJTs, Switches
- **Sources**: DC Voltage (5V), AC Voltage (5V, 1kHz), DC Current (10mA)
- **Meters**: Voltmeter, Ammeter
- All components stored in an SQLite database with configurable default properties

### File Operations
- Save and load circuit designs (JSON format)
- Example circuits included
- User configuration stored in `~/.circuit_simulator/`

## Project Structure

```
circuit_simulator/
  main.py                  # Entry point: argument parsing, app initialization
  config.py                # Configuration: paths, simulation params, GUI settings, colors, defaults
  requirements.txt         # Python dependencies
  components/              # Component definitions
    base_component.py      # Abstract base class (connections, state, properties)
    passive_components.py  # Resistor, Capacitor, Inductor, Ground
    active_components.py   # Diode, LED, BJT, Switch
    sources.py             # DC/AC Voltage, DC Current sources
    meters.py              # Voltmeter, Ammeter
    wires.py               # Wire connections
  simulation/              # Simulation engine
    simulator.py           # CircuitSimulator: node management, event system
    circuit_solver.py      # MNA-based circuit solver
    physics.py             # Component physics models
    analysis.py            # Circuit analysis utilities
  gui/                     # User interface
    main_window.py         # Main window: menus, toolbars, layout, simulation timer
    circuit_board.py       # Interactive circuit board widget
    circuit_diagram.py     # Auto-generated schematic view
    component_panel.py     # Component selection panel
    analysis_panel.py      # Measurement and analysis display
    debug_console.py       # Debug/logging console
    resources/             # Icons and UI assets
  database/                # Data persistence
    db_manager.py          # SQLite database manager
    models.py              # Database models
    schema.sql             # Database schema definition
  utils/                   # Utilities
    circuit_parser.py      # Circuit file parsing
    file_manager.py        # Save/load file operations
    logger.py              # Logging setup and simulation event tracking
  examples/                # Example circuits
    basic_circuits.py      # Programmatic example circuit definitions
    saved_circuits/        # Saved circuit JSON files
```

## Requirements

- Python 3.7+
- PyQt5 >= 5.15.0
- NumPy >= 1.19.0
- SciPy >= 1.5.0
- Matplotlib >= 3.3.0

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

### Command-Line Options

| Flag | Description |
|------|-------------|
| `--debug` | Enable debug mode (verbose logging) |
| `--load <file>` | Load a saved circuit file on startup |
| `--example <name>` | Load a built-in example circuit |
| `--config <file>` | Path to a custom JSON configuration file |

### Getting Started

1. Launch the application
2. Select a component from the component panel on the left
3. Click on the circuit board to place it; right-click or use toolbar to rotate
4. Switch to wiring mode and click-drag between connection points to wire components
5. Open the Simulation menu and start the simulation
6. View live voltage/current in the analysis panel; check the debug console for events

### Configuration

Default settings are stored in `~/.circuit_simulator/config.json` and can be overridden with `--config`. Key parameters:

- **Simulation**: timestep (1ms), max steps (10000), convergence (1e-6), max iterations (100)
- **GUI**: grid size (20px), component size (60px), wire thickness (2px)
- **Colors**: background, grid, wire, selection, voltage high/low, current

## License

This project is open-source and available under the MIT License.


---
*Built with AI assistance from [Claude (Anthropic)](https://claude.com/).*

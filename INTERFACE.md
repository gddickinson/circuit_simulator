# Circuit Simulator -- Interface Map

## Project Structure

| Directory / File | Purpose |
|------------------|---------|
| `main.py` | Application entry point (arg parsing, init) |
| `config.py` | All configurable constants, paths, colors |
| `components/` | Circuit component models |
| `simulation/` | Solver, physics, analysis, simulator engine |
| `gui/` | PyQt5 UI: main window, circuit board, diagram, panels |
| `database/` | SQLite component database (schema + manager) |
| `utils/` | File I/O, circuit parser, logger |
| `examples/` | Example circuits (saved JSON) |
| `tests/` | Unit and integration tests |

## Key Modules

### components/
- `base_component.py` -- `BaseComponent` ABC, connection model
- `passive_components.py` -- Resistor, Capacitor, Inductor
- `active_components.py` -- Diode, BJT, LED, Zener
- `sources.py` -- DC/AC voltage and current sources
- `meters.py` -- Voltmeter, Ammeter, Ohmmeter
- `wires.py` -- Wire, Junction, Ground

### simulation/
- `circuit_solver.py` -- `CircuitSolver` (MNA matrix construction + sparse solve)
- `physics.py` -- `Physics` static methods (Ohm's law, diode I-V, RLC, etc.)
- `simulator.py` -- `CircuitSimulator` (time-stepping, event dispatch)
- `analysis.py` -- DC sweep, AC analysis helpers

### gui/
- `main_window.py` -- `MainWindow` (menu bar, toolbar, tab container)
- `circuit_board.py` -- `CircuitBoard` (grid canvas, component placement, wiring)
- `circuit_diagram.py` -- `CircuitDiagram` (auto-generated schematic view)
- `component_panel.py` -- Component palette / property editor
- `analysis_panel.py` -- Simulation results display
- `debug_console.py` -- Log viewer / REPL

### database/
- `db_manager.py` -- `DatabaseManager` (CRUD for components)
- `models.py` -- ORM-like data classes
- `schema.sql` -- Table definitions

### utils/
- `circuit_parser.py` -- JSON / netlist import-export
- `file_manager.py` -- Save / load circuit files
- `logger.py` -- Logging setup

## Module Connections

```
main.py
  -> config.py
  -> gui/main_window.py
       -> gui/circuit_board.py
       -> gui/circuit_diagram.py
       -> gui/component_panel.py
       -> gui/analysis_panel.py
       -> gui/debug_console.py
  -> simulation/simulator.py
       -> simulation/circuit_solver.py
       -> simulation/physics.py
       -> simulation/analysis.py
  -> database/db_manager.py
       -> database/models.py
       -> database/schema.sql
  -> utils/*
  -> components/*
```

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
| `tests/` | Unit and integration tests (physics, solver, file format, web, JS-vs-Python fixture) |
| `web/` | Web interface: FastAPI app + browser simulator (JS port of the MNA engine) |
| `scripts/` | `build_static.py` (GitHub Pages export), `screenshots.py`, `make_engine_fixture.py` |
| `run_web.py` | Starts the web app on 127.0.0.1:8234 |

## Key Modules

### components/
- `base_component.py` -- `BaseComponent` ABC, connection model
- `passive_components.py` -- Resistor, Capacitor, Inductor
- `active_components.py` -- DCVoltageSource, ACVoltageSource, DCCurrentSource, Diode, LED, BJT, Switch (the classes the board uses)
- `sources.py` -- alternative source classes (VoltageSource, Battery, FunctionGenerator, ...; not used by the board)
- `meters.py` -- Voltmeter, Ammeter, Oscilloscope, Multimeter (not placeable yet)
- `wires.py` -- Wire, JumperWire, BusWire (not used: wires are terminal-to-terminal `connected_to` links)
- `passive_components.py` also holds `Ground`; `BaseComponent.to_dict()` saves the class name as `type`

### simulation/
- `mna.py` -- Qt-free MNA engine: `Netlist` (union-find of `connected_to` into nodes, ground selection), `solve_point()` (stamps, PWL diode/BJT region iteration, `np.linalg.solve`), `TERMINALS`, `DEFAULTS`, `CircuitError`
- `transient.py` -- `Transient(circuit).advance(T)` backward-Euler sub-steps, `readouts()` (terminal V, current INTO terminal, absorbed power)
- `circuit_solver.py` -- `CircuitSolver.solve_circuit()`: builds the circuit dict from the simulator, advances one `time_step`, writes component states and node voltages back
- `physics.py` -- `Physics` static methods (Ohm's law, diode I-V, RLC, etc.)
- `simulator.py` -- `CircuitSimulator` (nodes, time-stepping, event dispatch; skips component `calculate()` when the solver wrote the states)
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

### web/ (web interface; see README "Web interface")
- `app.py` -- FastAPI: `/api/info`, `/api/components`, `/api/examples[/<name>]` (all in `STATIC_ENDPOINTS`), `POST /api/simulate` (Python engine)
- `catalog.py` -- component catalog (connections, defaults, editable props/units) and the `examples/basic_circuits.py` circuits as `.circuit` dicts with a tidy board layout
- `static/` -- ES modules, no build step:
  - `circuit_engine.js` (port of `mna.py`), `transient_engine.js` (port of `transient.py`), `circuit_engine.test.mjs` (node test vs `tests/fixtures/engine_fixture.json`)
  - `circuit_doc.js` (circuit document in `.circuit` format: add/move/rotate/connect, load/save), `units.js` (SI parse/format)
  - `schematic.js` (SVG editor), `symbols.js` (component symbols), `scope.js` (oscilloscope canvas)
  - `sim.js` + `sim_panel.js` (simulator page), `home.js`, `examples.js`, `about.js`, `main.js`, `core.js` (router, shared kit), `static_api.js` (static-site data layer)

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
       -> simulation/circuit_solver.py -> simulation/transient.py -> simulation/mna.py
       -> simulation/physics.py
       -> simulation/analysis.py
  -> database/db_manager.py
       -> database/models.py
       -> database/schema.sql
  -> utils/*
  -> components/*

web/app.py -> web/catalog.py -> examples/basic_circuits.py, simulation/transient.py
web/static/sim.js -> schematic.js, scope.js, sim_panel.js, circuit_doc.js, transient_engine.js -> circuit_engine.js
```

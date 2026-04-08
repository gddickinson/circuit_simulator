# Circuit Simulator -- Roadmap

## Current State
A full-featured interactive circuit simulator built with PyQt5. Excellent modular architecture with 31 Python modules organized into `components/` (6 modules), `simulation/` (4 modules), `gui/` (6 modules), `database/` (2 modules + schema), `utils/` (4 modules), and `examples/`. Features MNA-based solver, grid-based component placement, wiring, real-time simulation at 30 FPS, auto-generated schematics, and SQLite component storage. Has `requirements.txt` and `config.py`.

## Short-term Improvements
- [ ] Add unit tests for `simulation/circuit_solver.py` (MNA matrix construction, basic RLC circuits)
- [x] Add integration tests for `simulation/physics.py` component models (diode I-V, capacitor charging)
- [ ] Add input validation in `gui/circuit_board.py` for overlapping component placement
- [ ] Improve error messages when simulation fails to converge (show node voltages, iteration count)
- [ ] Add keyboard shortcut reference panel in `gui/main_window.py`
- [ ] Document the MNA formulation in `simulation/circuit_solver.py` with inline math comments

## Feature Enhancements
- [ ] Add AC frequency sweep analysis with Bode plot output in `simulation/analysis.py`
- [ ] Implement transient analysis with waveform display (oscilloscope view)
- [ ] Add MOSFET and op-amp components in `components/active_components.py`
- [ ] Implement subcircuit/module support for hierarchical designs
- [ ] Add SPICE netlist import/export in `utils/circuit_parser.py`
- [ ] Implement wire routing algorithm to avoid crossing other components
- [ ] Add component value editing via double-click on the circuit board

## Long-term Vision
- [ ] Add SPICE-compatible simulation engine for industry-standard accuracy
- [ ] Implement PCB layout generation from schematic
- [ ] Add collaborative editing via WebSocket for remote pair design
- [ ] Create a component library browser with parametric search
- [ ] Support mixed-signal (analog + digital) simulation
- [ ] Port to a web-based interface using WebAssembly + Canvas

## Technical Debt
- [ ] `gui/circuit_board.py` and `gui/circuit_diagram.py` are likely the largest files -- audit line counts
- [ ] `database/schema.sql` and component defaults may diverge from `config.py` -- add validation
- [ ] `examples/basic_circuits.py` creates circuits programmatically but may not match JSON format in `saved_circuits/`
- [x] `__pycache__` in project root suggests missing `.gitignore`
- [ ] No CI/CD pipeline -- add tests for solver convergence and component physics
- [ ] Event system in `simulation/simulator.py` should use proper observer pattern, not ad-hoc callbacks

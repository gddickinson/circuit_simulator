# Session log

## 2026-11-11 — web interface + GitHub Pages simulator (branch `web-interface`)

**Bugs found and fixed (separate commits, regression tests first):**
- *Circuit solver did not solve the circuit.* `CircuitSolver.solve_circuit()` never built the MNA system (the
  `_add_*_to_mna` stamp helpers were unused): it set each source's + node to V and copied node voltages around, so
  every node not touching a source read 0 V (divider midpoint 0 V instead of 5 V; RC capacitor never charged;
  diodes, LEDs and BJTs never conducted; AC and current sources ignored; only the first Ground symbol's net grounded).
  `simulator.update()` then let each component's `calculate()` overwrite the result (DC sources forced their −
  node to 0 V; inductors integrated their current twice). Replaced by `simulation/mna.py` + `simulation/transient.py`
  (MNA, backward-Euler companion models in ≤10 µs sub-steps, PWL diode/LED/BJT region iteration); `update()` skips
  `calculate()` when the solver wrote the states. `tests/test_solver.py` (11 hand-calculated circuits).
- *Saved circuits lost Ground and Switch.* `to_dict()` did not save the class and the loader inferred it from
  properties, so Ground/Switch were dropped on reopen. Files now carry `"type"`; `tests/test_file_format.py`.

**Docs corrected:** README listed meters as part of the component library (classes exist in `components/meters.py`
but the board cannot place them); INTERFACE.md listed a Zener, an Ohmmeter and a "Junction"/"Ground" in wires.py that
do not exist, and the wrong file for the sources the board uses.

**Web interface:** `web/` (FastAPI app, catalog, static front end), `run_web.py` (port 8234), `scripts/build_static.py`,
`scripts/screenshots.py`, `scripts/make_engine_fixture.py`, `.github/workflows/pages.yml`. The static site is the
working simulator: SVG schematic editor, JS port of the MNA engine (matches Python to ~2e-13 on 12 circuits, fixture
`tests/fixtures/engine_fixture.json`), live readouts, oscilloscope, the 7 examples, `.circuit` save/load compatible
with the desktop app.

**Tests:** `python -m pytest -q tests` (68 passed), `node web/static/circuit_engine.test.mjs` (ok).
**Not done / open:** see the "needs George's decision" list in the web-interface report: diode/LED/BJT current
limiting (the old component code clamped reported current at `max_current`; the solver now reports an over-current
flag instead), and `CONVERGENCE_THRESHOLD`/`MAX_ITERATIONS` in config.py are unused by the new solver.

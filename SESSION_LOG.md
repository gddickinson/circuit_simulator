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

## 2026-11-11 (later) — George: "fix the circuit app and any other problems"

**Engine (Python + JS, fixtures regenerated, JS = Python to 2e-13 on 14 circuits):**
- Trapezoidal integration with 3 backward-Euler steps after any discontinuity (start, edit/switch flip, diode/BJT
  region change): RC/RL error at one time constant ~1e-5 (was ~1 %); no ringing after a switch shorts a capacitor
  (`tests/test_integration_accuracy.py`, including a guard that plain trapezoidal would ring).
- Region iteration uses `config.MAX_ITERATIONS` (cap) and `config.CONVERGENCE_THRESHOLD` (hysteresis, volts).
- Ratings: real current kept, parts over max power/voltage/current flagged `overload` with the reason (web: red glow
  + "⚠ over rating"; desktop: red dashed frame, ⚠, tooltip, red row in Measurements).
- Open switch 1 TΩ (was 1 GΩ, which held the LED behind an open switch at 2 V).

**Desktop GUI (checked offscreen on every example):** BJT painting crashed every frame (float args to drawText);
Measurements stayed empty while running (rows never shown, only built on Refresh); diode/LED rows read p1/p2 (always
0); one unwrapped label + the debug console made the docks 560/700 px wide so the board was ~75 px; solver
iteration count always 0 in the status bar.

**Web editor (Playwright on the live site and the local build):** every example and five circuits built from scratch
(divider, RC, LED+R, BJT switch saturated/active, AC RC at the corner frequency) match hand values; rotation, delete,
wiring, units k/m/µ/Ω, scope, save→load all exercised. Fixed: undo/redo added (buttons + Ctrl/⌘+Z/Shift+Z/Y);
property inputs show units ("500 mA"); diode/LED labels say "Vf"; BJT labels no longer sit on the base wire; BJT
example layout no longer runs a wire through a resistor; empty-scope hint; bigger terminal hit areas and a board
that scrolls sideways on phones instead of shrinking to 8 px cells; stray console errors from pointer capture.
Tests: pytest 75 passed; node engine + circuit_doc tests ok.

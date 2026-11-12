"""Write tests/fixtures/engine_fixture.json: Python MNA results that web/static/circuit_engine.test.mjs must reproduce.

Every case is a circuit in the .circuit file format, simulated with simulation/transient.py for `frames` frames of
`frame` seconds; every terminal voltage and terminal current of every component is recorded after each frame.
Run: python scripts/make_engine_fixture.py   (tests/test_engine_fixture.py checks the committed file is current)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from simulation.mna import DEFAULTS, MAX_PWL_ITER, RATINGS, REGION_TOL, TERMINALS  # noqa: E402
from simulation.transient import BE_STEPS  # noqa: E402
from simulation.transient import Transient  # noqa: E402
from web.catalog import TITLES, example  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "engine_fixture.json"


def comp(cid, ty, props, conns):
    return {"id": cid, "type": ty, "position": [0, 0], "rotation": 0, "properties": props, "connected_to": conns}


def extra_cases():
    rl = {"components": {
        "v": comp("v", "DCVoltageSource", {"voltage": 1.0}, {"pos": [["r", "p1"]], "neg": [["g", "gnd"]]}),
        "r": comp("r", "Resistor", {"resistance": 10.0}, {"p1": [["v", "pos"]], "p2": [["l", "p1"]]}),
        "l": comp("l", "Inductor", {"inductance": 0.01}, {"p1": [["r", "p2"]], "p2": [["g", "gnd"]]}),
        "g": comp("g", "Ground", {}, {"gnd": [["l", "p2"], ["v", "neg"]]})}}
    isrc = {"components": {
        "i": comp("i", "DCCurrentSource", {"current": 0.01}, {"pos": [["r", "p1"]], "neg": [["g2", "gnd"]]}),
        "r": comp("r", "Resistor", {"resistance": 1000.0}, {"p1": [["i", "pos"]], "p2": [["g1", "gnd"]]}),
        "c": comp("c", "Capacitor", {"capacitance": 1e-6}, {"p1": [["r", "p1"]], "p2": [["g1", "gnd"]]}),
        "g1": comp("g1", "Ground", {}, {}), "g2": comp("g2", "Ground", {}, {})}}
    pnp = {"components": {
        "v": comp("v", "DCVoltageSource", {"voltage": 9.0}, {"pos": [["q", "emitter"]], "neg": [["g", "gnd"]]}),
        "q": comp("q", "BJT", {"type": "pnp", "gain": 100}, {"collector": [["rc", "p1"]], "base": [["rb", "p1"]]}),
        "rc": comp("rc", "Resistor", {"resistance": 1000.0}, {"p2": [["g", "gnd"]]}),
        "rb": comp("rb", "Resistor", {"resistance": 1e5}, {"p2": [["g", "gnd"]]}),
        "g": comp("g", "Ground", {}, {})}}
    rlc = {"components": {  # no Ground symbol: the source's neg terminal becomes the reference
        "a": comp("a", "ACVoltageSource", {"amplitude": 2.0, "frequency": 500.0, "phase": 30.0},
                  {"pos": [["r", "p1"]], "neg": [["c", "p2"]]}),
        "r": comp("r", "Resistor", {"resistance": 47.0}, {"p2": [["l", "p1"]]}),
        "l": comp("l", "Inductor", {"inductance": 0.1}, {"p2": [["c", "p1"]]}),
        "c": comp("c", "Capacitor", {"capacitance": 1e-6}, {}),
        "d": comp("d", "Diode", {}, {"anode": [["l", "p2"]], "cathode": [["c", "p2"]]})}}
    closed = example("switch_circuit")
    for c in closed["components"].values():
        if c["type"] == "Switch":
            c["properties"]["state"] = True
    led_over = example("led_circuit")
    led_over["components"]["resistor_1"]["properties"]["resistance"] = 50.0  # 60 mA in a 20 mA LED
    flip = {"components": {  # RC with a switch across the capacitor, closed at frame 12 (tau 10 ns discharge)
        "v": comp("v", "DCVoltageSource", {"voltage": 5.0}, {"pos": [["r", "p1"]], "neg": [["g", "gnd"]]}),
        "r": comp("r", "Resistor", {"resistance": 1000.0}, {"p2": [["c", "p1"]]}),
        "c": comp("c", "Capacitor", {"capacitance": 1e-6}, {"p2": [["g", "gnd"]]}),
        "s": comp("s", "Switch", {"state": False}, {"p1": [["c", "p1"]], "p2": [["g", "gnd"]]}),
        "g": comp("g", "Ground", {}, {})}}
    return {"rl": rl, "current_source_two_grounds": isrc, "pnp": pnp, "ac_rlc_diode_no_ground": rlc,
            "switch_closed": closed, "led_over_rating": led_over, "switch_flip": (flip, {"frame": 12, "id": "s"})}


def record(circuit, frame, frames, toggle=None):
    """Readouts after every frame; `toggle` {'frame': k, 'id': switch} flips that switch before frame k, keeping
    the dynamic state and time and marking a discontinuity (as the web editor and CircuitSolver do)."""
    circuit = json.loads(json.dumps(circuit))
    tr = Transient(circuit)
    rows = []
    for f in range(frames):
        if toggle and f == toggle["frame"]:
            props = circuit["components"][toggle["id"]]["properties"]
            props["state"] = not props.get("state", False)
            new = Transient(circuit, state=tr.state)
            new.t, tr = tr.t, new
            tr.discontinuity()
        r = tr.advance(frame)
        rows.append({cid: {"v": o["voltages"], "i": o["currents"], "p": o["power"],
                           **{k: o[k] for k in ("region", "conducting", "brightness", "overload") if k in o}}
                     for cid, o in r.items()})
    return rows


def build():
    cases = {}
    for name in TITLES:
        cases[name] = {"circuit": example(name), "frame": 2e-4, "frames": 30}
    for name, circ in extra_cases().items():
        circ, toggle = circ if isinstance(circ, tuple) else (circ, None)
        cases[name] = {"circuit": circ, "frame": 2.5e-4, "frames": 40}
        if toggle:
            cases[name].update(toggle=toggle, frame=1e-5, frames=30)
    for c in cases.values():
        c["results"] = record(c["circuit"], c["frame"], c["frames"], c.get("toggle"))
    return {"terminals": {k: list(v) for k, v in TERMINALS.items()}, "defaults": DEFAULTS, "ratings": RATINGS,
            "constants": {"MAX_PWL_ITER": MAX_PWL_ITER, "REGION_TOL": REGION_TOL, "BE_STEPS": BE_STEPS},
            "cases": cases}


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), separators=(",", ":")))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e3:.0f} kB)")

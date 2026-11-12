"""Accuracy and stability of the time integration (simulation/transient.py) and device ratings."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config  # noqa: E402
from simulation import mna  # noqa: E402
from simulation.transient import Transient  # noqa: E402


def comp(cid, ty, props, conns):
    return {"id": cid, "type": ty, "properties": props, "connected_to": conns}


def rc(r=1000.0, c=1e-6, switch=False):
    comps = {
        "v": comp("v", "DCVoltageSource", {"voltage": 5.0}, {"pos": [["r", "p1"]], "neg": [["g", "gnd"]]}),
        "r": comp("r", "Resistor", {"resistance": r}, {"p2": [["c", "p1"]]}),
        "c": comp("c", "Capacitor", {"capacitance": c}, {"p2": [["g", "gnd"]]}),
        "g": comp("g", "Ground", {}, {}),
    }
    if switch:  # a switch straight across the capacitor
        comps["s"] = comp("s", "Switch", {"state": False}, {"p1": [["c", "p1"]], "p2": [["g", "gnd"]]})
    return {"components": comps}


def test_rc_error_at_one_time_constant_below_0_1_percent():
    tr = Transient(rc())
    vc = tr.advance(1e-3)["c"]["voltages"]["p1"]  # default step: 10 us, tau = 1 ms
    exact = 5.0 * (1 - math.exp(-1))
    assert abs(vc / exact - 1) < 1e-3
    for _ in range(4):
        vc = tr.advance(1e-3)["c"]["voltages"]["p1"]
    assert abs(vc / (5.0 * (1 - math.exp(-5))) - 1) < 1e-4


def test_rl_error_below_0_1_percent():
    circ = {"components": {
        "v": comp("v", "DCVoltageSource", {"voltage": 1.0}, {"pos": [["r", "p1"]], "neg": [["g", "gnd"]]}),
        "r": comp("r", "Resistor", {"resistance": 10.0}, {"p2": [["l", "p1"]]}),
        "l": comp("l", "Inductor", {"inductance": 0.01}, {"p2": [["g", "gnd"]]}),
        "g": comp("g", "Ground", {}, {})}}
    i = Transient(circ).advance(1e-3)["l"]["currents"]["p1"]
    assert abs(i / (0.1 * (1 - math.exp(-1))) - 1) < 1e-3


def test_no_ringing_after_switch_flip():
    tr = Transient(rc(switch=True))
    tr.advance(5e-3)
    circ = rc(switch=True)
    circ["components"]["s"]["properties"]["state"] = True  # close the switch: tau of the discharge is 10 ns
    tr2 = Transient(circ, state=tr.state)
    tr2.t = tr.t
    tr2.discontinuity()
    trace = [tr2.advance(1e-5)["c"]["voltages"]["p1"] for _ in range(20)]
    floor = 5.0 * 0.01 / 1000.01
    assert all(v >= 0 for v in trace), trace
    assert all(abs(v - floor) < 1e-7 for v in trace[3:]), trace


def test_trapezoidal_alone_would_ring():
    """Guard that the previous test is meaningful: without the backward-Euler restart the voltage oscillates."""
    tr = Transient(rc(switch=True))
    tr.advance(5e-3)
    circ = rc(switch=True)
    circ["components"]["s"]["properties"]["state"] = True
    tr2 = Transient(circ, state=tr.state)
    tr2.be_left = 0
    trace = [tr2.advance(1e-5)["c"]["voltages"]["p1"] for _ in range(4)]
    assert min(trace) < -1e-3  # alternates about +-10 mV


def test_led_over_rating_is_flagged_not_clamped():
    circ = {"components": {
        "v": comp("v", "DCVoltageSource", {"voltage": 5.0}, {"pos": [["r", "p1"]], "neg": [["g", "gnd"]]}),
        "r": comp("r", "Resistor", {"resistance": 50.0}, {"p2": [["d", "anode"]]}),
        "d": comp("d", "LED", {"forward_voltage": 2.0}, {"cathode": [["g", "gnd"]]}),
        "g": comp("g", "Ground", {}, {})}}
    r = Transient(circ).advance(1e-3)
    assert r["d"]["currents"]["anode"] == pytest.approx(3.0 / 50.1, rel=1e-6)  # real current, not 20 mA
    assert "rating 0.02 A" in r["d"]["overload"]
    assert "overload" not in r["r"] or "power" in r["r"]["overload"]  # 0.18 W < 0.25 W: no flag
    assert "overload" not in r["r"]


def test_resistor_power_rating():
    r = Transient(rc(r=10.0, c=1e-9)).advance(1e-3)  # 2.5 W in a 0.25 W resistor at t=0 ... settles to 0
    assert "overload" not in r["r"]
    circ = rc(r=50.0)
    circ["components"]["c"]["type"] = "Resistor"
    circ["components"]["c"]["properties"] = {"resistance": 50.0}
    r = Transient(circ).advance(1e-3)  # 50 mA through 50 ohm: 0.125 W each, under rating
    assert "overload" not in r["r"]
    circ["components"]["r"]["properties"]["resistance"] = 10.0
    r = Transient(circ).advance(1e-3)
    assert "power" in r["c"]["overload"]  # 83 mA through 50 ohm = 0.35 W > 0.25 W


def test_region_iteration_uses_config_limits():
    assert mna.MAX_PWL_ITER == config.MAX_ITERATIONS
    assert mna.REGION_TOL == config.CONVERGENCE_THRESHOLD

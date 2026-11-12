"""
Regression tests for the circuit solver against hand-calculable circuits.

They drive the real desktop pipeline (CircuitSimulator + CircuitSolver + examples/basic_circuits.py), exactly as
gui/main_window.py does: build_circuit_from_components(), start_simulation(), update() once per frame.
"""

import logging
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.disable(logging.CRITICAL)

from components.active_components import BJT, DCCurrentSource, DCVoltageSource  # noqa: E402
from components.passive_components import Ground, Inductor, Resistor  # noqa: E402
from examples import basic_circuits  # noqa: E402
from simulation.circuit_solver import CircuitSolver  # noqa: E402
from simulation.simulator import CircuitSimulator  # noqa: E402


def make(builder):
    sim = CircuitSimulator()
    CircuitSolver(sim)
    if isinstance(builder, str):
        basic_circuits.create_example_circuit(sim, builder)
    else:
        builder(sim)
    sim.build_circuit_from_components()
    sim.start_simulation()
    return sim


def run(sim, frames):
    for _ in range(frames):
        sim.update()
    return {type(c).__name__ + str(i): c for i, c in enumerate(sim.components.values())}


def by_type(sim, name):
    return [c for c in sim.components.values() if type(c).__name__ == name]


def wire(sim, *pairs):
    for (a, ta), (b, tb) in pairs:
        sim.connect_components_at(a.id, ta, b.id, tb)


def test_voltage_divider_midpoint_is_half():
    sim = make('voltage_divider')
    run(sim, 3)
    r1, r2 = by_type(sim, 'Resistor')
    assert r1.state['voltages']['p2'] == pytest.approx(5.0, rel=1e-6)
    assert r2.state['voltages']['p1'] == pytest.approx(5.0, rel=1e-6)
    assert r1.state['currents']['p1'] == pytest.approx(10.0 / 2000.0, rel=1e-6)
    src = by_type(sim, 'DCVoltageSource')[0]
    # the source delivers the current: current INTO its + terminal is negative
    assert src.state['currents']['pos'] == pytest.approx(-0.005, rel=1e-6)


def test_rc_charges_with_time_constant():
    sim = make('rc_circuit')  # 5 V, 1 kohm, 1 uF: tau = 1 ms, one frame = 1 ms
    run(sim, 1)
    cap = by_type(sim, 'Capacitor')[0]
    vc = cap.state['voltages']['p1'] - cap.state['voltages']['p2']
    assert vc == pytest.approx(5.0 * (1 - math.exp(-1)), rel=0.01)
    run(sim, 4)
    vc = cap.state['voltages']['p1'] - cap.state['voltages']['p2']
    assert vc == pytest.approx(5.0 * (1 - math.exp(-5)), rel=0.002)


def test_diode_drops_forward_voltage():
    sim = make('diode_circuit')
    run(sim, 2)
    d = by_type(sim, 'Diode')[0]
    vd = d.state['voltages']['anode'] - d.state['voltages']['cathode']
    assert vd == pytest.approx(0.7, abs=0.01)
    assert d.state['currents']['anode'] == pytest.approx((5 - 0.7) / 1000.1, rel=1e-6)
    assert d.state['conducting']


def test_led_current_and_brightness():
    sim = make('led_circuit')
    run(sim, 2)
    led = by_type(sim, 'LED')[0]
    i = (5 - 2.0) / 220.1
    assert led.state['currents']['anode'] == pytest.approx(i, rel=1e-6)
    assert led.state['brightness'] == pytest.approx(i / 0.02, rel=1e-6)


def test_switch_controls_led():
    sim = make('switch_circuit')
    run(sim, 2)
    led = by_type(sim, 'LED')[0]
    assert abs(led.state['currents']['anode']) < 1e-9
    assert not led.state['conducting']
    assert led.state['voltages']['anode'] < 0.1  # an open switch must not hold the LED at its forward voltage
    sw = by_type(sim, 'Switch')[0]
    sw.toggle()
    run(sim, 2)
    assert led.state['currents']['anode'] == pytest.approx(3.0 / 1000.11, rel=1e-6)


def test_ac_rc_lowpass_amplitude_and_phase():
    sim = make('oscillator_circuit')  # 5 V, 1 kHz into 1 kohm / 1 uF
    run(sim, 10)
    cap = by_type(sim, 'Capacitor')[0]
    wrc = 2 * math.pi * 1000 * 1e-3
    # steady state at t = n ms (source phase 0): v = A/sqrt(1+(wRC)^2) * sin(-atan(wRC))
    expected = 5 / math.sqrt(1 + wrc ** 2) * math.sin(-math.atan(wrc))
    assert cap.state['voltages']['p1'] == pytest.approx(expected, abs=0.03)


def test_bjt_saturates_with_hand_values():
    sim = make('bjt_circuit')
    run(sim, 2)
    q = by_type(sim, 'BJT')[0]
    ib = (9 - 0.7) / 11000.0  # 10 k base resistor + 1 k base-emitter model
    assert q.state['currents']['base'] == pytest.approx(ib, rel=1e-4)
    assert q.state['region'] == 'saturation'
    assert q.state['currents']['collector'] == pytest.approx((9 - 0.2) / 1000.1, rel=1e-4)


def _rl(sim):
    src, r, ind, gnd = DCVoltageSource(properties={'voltage': 1.0}), Resistor(properties={'resistance': 10.0}), \
        Inductor(properties={'inductance': 0.01}), Ground()
    for c in (src, r, ind, gnd):
        sim.add_component(c)
    wire(sim, ((src, 'pos'), (r, 'p1')), ((r, 'p2'), (ind, 'p1')), ((ind, 'p2'), (gnd, 'gnd')),
         ((src, 'neg'), (gnd, 'gnd')))


def test_rl_current_rises_with_l_over_r():
    sim = make(_rl)  # tau = L/R = 1 ms
    run(sim, 1)
    ind = by_type(sim, 'Inductor')[0]
    assert ind.state['currents']['p1'] == pytest.approx(0.1 * (1 - math.exp(-1)), rel=0.01)


def _isrc(sim):
    src, r, g1, g2 = DCCurrentSource(properties={'current': 0.01}), Resistor(properties={'resistance': 1000.0}), \
        Ground(), Ground()
    for c in (src, r, g1, g2):
        sim.add_component(c)
    # two separate ground symbols: both nets must be at 0 V
    wire(sim, ((src, 'pos'), (r, 'p1')), ((r, 'p2'), (g1, 'gnd')), ((src, 'neg'), (g2, 'gnd')))


def test_current_source_pushes_out_of_pos_and_all_grounds_are_zero():
    sim = make(_isrc)
    run(sim, 1)
    r = by_type(sim, 'Resistor')[0]
    assert r.state['voltages']['p1'] == pytest.approx(10.0, rel=1e-6)
    assert r.state['voltages']['p2'] == pytest.approx(0.0, abs=1e-9)


def test_pnp_mirrors_npn():
    def build(sim):
        src, rc, rb, q, gnd = DCVoltageSource(properties={'voltage': 9.0}), Resistor(properties={'resistance': 1e3}), \
            Resistor(properties={'resistance': 1e5}), BJT(properties={'type': 'pnp', 'gain': 100}), Ground()
        for c in (src, rc, rb, q, gnd):
            sim.add_component(c)
        wire(sim, ((src, 'pos'), (q, 'emitter')), ((q, 'collector'), (rc, 'p1')), ((rc, 'p2'), (gnd, 'gnd')),
             ((q, 'base'), (rb, 'p1')), ((rb, 'p2'), (gnd, 'gnd')), ((src, 'neg'), (gnd, 'gnd')))
    sim = make(build)
    run(sim, 2)
    q = by_type(sim, 'BJT')[0]
    ib = (9 - 0.7) / (1e5 + 1e3)
    assert q.state['region'] == 'active'
    assert q.state['currents']['base'] == pytest.approx(-ib, rel=1e-4)  # current flows OUT of a pnp base
    assert q.state['currents']['collector'] == pytest.approx(-100 * ib, rel=1e-4)


def test_kcl_holds_at_every_node():
    sim = make('bjt_circuit')
    run(sim, 2)
    for node in sim.nodes.values():
        total = sum(c.state['currents'][t] for c, t in node.get_connected_components())
        assert abs(total) < 1e-9

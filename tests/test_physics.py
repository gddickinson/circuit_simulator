"""
Unit tests for simulation/physics.py component models.

Covers Ohm's law, power calculations, capacitor/inductor equations,
series/parallel combinations, diode I-V, and RLC impedance.
"""

import math
import sys
import os

import pytest

# Add project root to path so imports work without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation.physics import Physics


# ── Ohm's law ─────────────────────────────────────────────────────────

class TestOhmsLaw:
    def test_voltage(self):
        assert Physics.ohms_law_voltage(2.0, 100.0) == 200.0

    def test_current(self):
        assert Physics.ohms_law_current(10.0, 5.0) == 2.0

    def test_current_zero_resistance(self):
        result = Physics.ohms_law_current(5.0, 0)
        assert result == float("inf")

    def test_resistance(self):
        assert Physics.ohms_law_resistance(10.0, 2.0) == 5.0

    def test_resistance_zero_current(self):
        assert Physics.ohms_law_resistance(5.0, 0) == float("inf")


# ── Power ─────────────────────────────────────────────────────────────

class TestPower:
    def test_power_vi(self):
        assert Physics.power_vi(10.0, 2.0) == 20.0

    def test_power_i2r(self):
        assert Physics.power_i2r(3.0, 4.0) == 36.0

    def test_power_v2r(self):
        assert Physics.power_v2r(10.0, 5.0) == 20.0

    def test_power_v2r_zero_resistance(self):
        assert Physics.power_v2r(5.0, 0) == float("inf")


# ── Capacitor ─────────────────────────────────────────────────────────

class TestCapacitor:
    def test_charge(self):
        assert Physics.capacitor_charge(1e-6, 5.0) == pytest.approx(5e-6)

    def test_energy(self):
        assert Physics.capacitor_energy(1e-6, 10.0) == pytest.approx(50e-6)

    def test_current(self):
        # I = C * dV/dt
        assert Physics.capacitor_current(1e-6, 1000.0) == pytest.approx(1e-3)


# ── Inductor ──────────────────────────────────────────────────────────

class TestInductor:
    def test_voltage(self):
        assert Physics.inductor_voltage(1e-3, 2.0) == pytest.approx(2e-3)

    def test_energy(self):
        assert Physics.inductor_energy(1e-3, 1.0) == pytest.approx(0.5e-3)

    def test_flux(self):
        assert Physics.inductor_flux(1e-3, 2.0) == pytest.approx(2e-3)


# ── Series / parallel combinations ───────────────────────────────────

class TestCombinations:
    def test_series_resistance(self):
        assert Physics.series_resistance(100, 200, 300) == 600

    def test_parallel_resistance(self):
        # Two identical resistors in parallel = half
        assert Physics.parallel_resistance(100, 100) == pytest.approx(50.0)

    def test_parallel_resistance_with_zero(self):
        assert Physics.parallel_resistance(100, 0) == 0

    def test_series_capacitance(self):
        # Two 1uF in series = 0.5uF
        assert Physics.series_capacitance(1e-6, 1e-6) == pytest.approx(0.5e-6)

    def test_parallel_capacitance(self):
        assert Physics.parallel_capacitance(1e-6, 2e-6) == pytest.approx(3e-6)

    def test_series_inductance(self):
        assert Physics.series_inductance(1e-3, 2e-3) == pytest.approx(3e-3)

    def test_parallel_inductance(self):
        assert Physics.parallel_inductance(1e-3, 1e-3) == pytest.approx(0.5e-3)


# ── Dividers ──────────────────────────────────────────────────────────

class TestDividers:
    def test_voltage_divider(self):
        # 10V with 1k / 1k -> 5V
        assert Physics.voltage_divider(10.0, 1000, 1000) == pytest.approx(5.0)

    def test_voltage_divider_zero_sum(self):
        assert Physics.voltage_divider(10.0, 0, 0) == 0

    def test_current_divider(self):
        # 1A through 1k / 1k -> 0.5A each
        assert Physics.current_divider(1.0, 1000, 1000) == pytest.approx(0.5)


# ── Time constants & resonance ────────────────────────────────────────

class TestTimeConstants:
    def test_rc_time_constant(self):
        assert Physics.rc_time_constant(1000, 1e-6) == pytest.approx(1e-3)

    def test_rl_time_constant(self):
        assert Physics.rl_time_constant(100, 1e-3) == pytest.approx(1e-5)

    def test_rl_time_constant_zero_r(self):
        assert Physics.rl_time_constant(0, 1e-3) == float("inf")

    def test_lcr_resonant_frequency(self):
        # f = 1 / (2*pi*sqrt(L*C))
        L, C = 1e-3, 1e-6
        expected = 1 / (2 * math.pi * math.sqrt(L * C))
        assert Physics.lcr_resonant_frequency(L, C) == pytest.approx(expected)


# ── Diode I-V ─────────────────────────────────────────────────────────

class TestDiode:
    def test_zero_voltage(self):
        # At V=0, I = Is*(exp(0)-1) = 0
        assert Physics.diode_current(0, 1e-12) == pytest.approx(0.0)

    def test_forward_bias(self):
        # Forward biased diode should conduct positive current
        I = Physics.diode_current(0.7, 1e-12)
        assert I > 0

    def test_reverse_bias(self):
        # Reverse biased: current should be close to -Is
        I = Physics.diode_current(-1.0, 1e-12)
        assert I == pytest.approx(-1e-12, abs=1e-15)

    def test_large_voltage_no_overflow(self):
        # Should not raise OverflowError
        I = Physics.diode_current(100.0, 1e-12)
        assert math.isfinite(I)


# ── Impedance ─────────────────────────────────────────────────────────

class TestImpedance:
    def test_rlc_impedance_at_resonance(self):
        L, C = 1e-3, 1e-6
        f_res = 1 / (2 * math.pi * math.sqrt(L * C))
        R = 100
        Z = Physics.resonant_circuit_impedance(R, L, C, f_res)
        # At resonance, imaginary part should be ~0
        assert abs(Z.imag) < 1.0  # tolerance for floating point
        assert Z.real == pytest.approx(R)

    def test_impedance_magnitude(self):
        z = complex(3, 4)
        assert Physics.impedance_magnitude(z) == pytest.approx(5.0)

    def test_impedance_phase(self):
        z = complex(1, 1)
        assert Physics.impedance_phase(z) == pytest.approx(math.pi / 4)

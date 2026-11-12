"""
Saving and re-loading a circuit (.circuit JSON written by utils/file_manager.py) keeps every component.
"""

import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.disable(logging.CRITICAL)

import config  # noqa: E402
from examples import basic_circuits  # noqa: E402
from simulation.simulator import CircuitSimulator  # noqa: E402
from utils.file_manager import FileManager  # noqa: E402


def roundtrip(name, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "USER_DATA_DIR", tmp_path)  # keep recent_files.json out of the home folder
    sim = CircuitSimulator()
    basic_circuits.create_example_circuit(sim, name)
    path = tmp_path / f"{name}.circuit"
    assert FileManager(sim, None)._save_to_file(str(path))
    loaded = CircuitSimulator()
    assert FileManager(loaded, None).load_circuit(str(path))
    return sim, loaded, json.loads(path.read_text())


def kinds(sim):
    return sorted(type(c).__name__ for c in sim.components.values())


def test_switch_and_ground_survive_save_and_load(tmp_path, monkeypatch):
    sim, loaded, data = roundtrip("switch_circuit", tmp_path, monkeypatch)
    assert kinds(loaded) == kinds(sim)
    assert all(c["type"] for c in data["components"].values())


def test_every_example_roundtrips(tmp_path, monkeypatch):
    for name in ("voltage_divider", "rc_circuit", "diode_circuit", "led_circuit", "bjt_circuit",
                 "oscillator_circuit", "switch_circuit"):
        sim, loaded, _ = roundtrip(name, tmp_path, monkeypatch)
        assert kinds(loaded) == kinds(sim), name

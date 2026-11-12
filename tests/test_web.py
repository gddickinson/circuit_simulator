"""Web interface tests: every exported endpoint answers, the static build is complete, and the JS engine tests pass.

Run: python -m pytest -q tests/test_web.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import STATIC, STATIC_ENDPOINTS, app  # noqa: E402

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "static/main.js" in r.text


@pytest.mark.parametrize("path", STATIC_ENDPOINTS)
def test_endpoint(path):
    r = client.get("/api" + path)
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_static_build(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_static
    build_static.build(tmp_path / "site")
    assert (tmp_path / "site" / "index.html").read_text().count("APP_STATIC") == 1
    for path in STATIC_ENDPOINTS:
        assert (tmp_path / "site" / "api" / (path.strip("/") + ".json")).exists()


def test_static_assets_referenced_exist():
    html = (STATIC / "index.html").read_text()
    for name in ("style.css", "main.js"):
        assert f"static/{name}" in html and (STATIC / name).exists()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine():
    tests = sorted(STATIC.glob("*.test.mjs"))
    for t in tests:
        r = subprocess.run(["node", str(t)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# --- project-specific ---------------------------------------------------------------------------------------------

def test_components_cover_every_placeable_class():
    types = {c["type"] for c in client.get("/api/components").json()}
    assert types == {"Resistor", "Capacitor", "Inductor", "Ground", "DCVoltageSource", "ACVoltageSource",
                     "DCCurrentSource", "Diode", "LED", "BJT", "Switch"}


def test_example_files_open_in_desktop_loader(tmp_path, monkeypatch):
    """Every example served to the browser is a .circuit file the desktop FileManager opens and solves the same."""
    import json
    import config
    from simulation.circuit_solver import CircuitSolver
    from simulation.simulator import CircuitSimulator
    from simulation.transient import Transient
    from utils.file_manager import FileManager
    monkeypatch.setattr(config, "USER_DATA_DIR", tmp_path)
    for ex in client.get("/api/examples").json():
        data = client.get(f"/api/examples/{ex['name']}").json()
        path = tmp_path / f"{ex['name']}.circuit"
        path.write_text(json.dumps(data))
        sim = CircuitSimulator()
        CircuitSolver(sim)
        assert FileManager(sim, None).load_circuit(str(path))
        assert len(sim.components) == len(data["components"])
        sim.start_simulation()
        sim.update()
        direct = Transient(data).advance(sim.time_step)
        for cid, res in direct.items():
            for term, v in res["voltages"].items():
                assert sim.components[cid].state["voltages"][term] == pytest.approx(v, abs=1e-9)


def test_simulate_endpoint_matches_hand_value():
    data = client.get("/api/examples/voltage_divider").json()
    r = client.post("/api/simulate", json={"circuit": data, "frame": 1e-3, "frames": 2})
    assert r.status_code == 200
    assert r.json()["results"][-1]["resistor_1"]["voltages"]["p2"] == pytest.approx(5.0, rel=1e-6)


def test_simulate_reports_unsolvable_circuit():
    data = client.get("/api/examples/voltage_divider").json()
    src = dict(data["components"]["dc_source_1"], id="dc_source_2", properties={"voltage": 3.0})
    data["components"]["dc_source_2"] = src
    r = client.post("/api/simulate", json={"circuit": data})
    assert r.status_code == 422

"""FastAPI web app for the circuit simulator: serves the front end in static/ and the JSON API under /api.

Run with `python run_web.py` (http://127.0.0.1:8234, local only). `scripts/build_static.py` exports every path in
STATIC_ENDPOINTS to JSON for the GitHub Pages site, so keep that list in step with the GET routes below. The
simulator itself runs in the browser (static/circuit_engine.js); POST /api/simulate runs the same circuit through the
Python engine (simulation/transient.py) so the two can be compared on the local app.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from simulation.mna import CircuitError
from simulation.transient import DEFAULT_MAX_STEP, Transient
from web.catalog import TITLES, catalog, example, examples

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Circuit Simulator")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/info")
def info():
    """Project summary for the home page."""
    cat = catalog()
    return {"title": "Circuit Simulator", "components": len(cat), "examples": len(TITLES),
            "timestep": 1e-3, "max_step": DEFAULT_MAX_STEP,
            "description": "An interactive electronic circuit simulator built with Python and PyQt5. Create, "
                           "simulate, and analyze electronic circuits in real-time."}


@app.get("/api/components")
def components():
    """Every placeable component: connection offsets, size, defaults and editable properties with units."""
    return catalog()


@app.get("/api/examples")
def example_list():
    return examples()


@app.get("/api/examples/{name}")
def example_circuit(name: str):
    """One example circuit in the .circuit file format (opens in the desktop app with File > Open)."""
    if name not in TITLES:
        raise HTTPException(404, f"unknown example {name}")
    return example(name)


class SimRequest(BaseModel):
    circuit: dict
    frame: float = Field(1e-3, gt=0, le=1.0)
    frames: int = Field(10, ge=1, le=2000)


@app.post("/api/simulate")
def simulate(req: SimRequest):
    """Run a circuit through the Python engine; returns the readouts after every frame."""
    try:
        tr = Transient(req.circuit)
        rows = [tr.advance(req.frame) for _ in range(req.frames)]
    except CircuitError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"t": [req.frame * (k + 1) for k in range(req.frames)], "results": rows, "converged": tr.converged}


# GET paths (without the /api prefix) written to the static site as api/<path>.json.
STATIC_ENDPOINTS = ["/info", "/components", "/examples"] + [f"/examples/{n}" for n in TITLES]

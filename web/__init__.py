"""Web interface for the circuit simulator (FastAPI + plain ES modules, no build step).

Contents:
    app.py      FastAPI app: JSON API under /api (info, components, examples, simulate) and the static front end
    catalog.py  component catalog and the examples of examples/basic_circuits.py in the .circuit file format
    static/     front end; circuit_engine.js + transient_engine.js are the JS port of simulation/mna.py and
                simulation/transient.py that runs the simulator in the browser (also on the GitHub Pages site)
"""

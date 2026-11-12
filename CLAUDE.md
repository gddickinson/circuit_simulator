# Circuit Simulator

See @INTERFACE.md for the project navigation map.

## Quick Start
```bash
pip install -r requirements.txt
python main.py
```

## Testing
```bash
python -m pytest tests/ -v
```

## Web interface
```bash
pip install -r requirements-web.txt
python run_web.py                          # http://127.0.0.1:8234
node web/static/circuit_engine.test.mjs    # JS engine vs Python fixture
python scripts/make_engine_fixture.py      # after changing simulation/mna.py or transient.py (port the change to JS too)
```

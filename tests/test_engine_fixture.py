"""The committed Python-vs-JS fixture (tests/fixtures/engine_fixture.json) is what the Python engine produces now."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import make_engine_fixture  # noqa: E402


def _flat(obj, out):
    if isinstance(obj, dict):
        for k in sorted(obj):
            _flat(obj[k], out)
    elif isinstance(obj, list):
        for v in obj:
            _flat(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append(float(obj))
    else:
        out.append(obj)
    return out


def test_fixture_is_current():
    committed = json.loads(make_engine_fixture.OUT.read_text())
    fresh = json.loads(json.dumps(make_engine_fixture.build()))
    a, b = _flat(committed, []), _flat(fresh, [])
    assert len(a) == len(b)
    nums = [(x, y) for x, y in zip(a, b) if isinstance(x, float)]
    assert all(x == y for x, y in zip(a, b) if not isinstance(x, float)), "run scripts/make_engine_fixture.py"
    x, y = np.array(nums).T
    np.testing.assert_allclose(x, y, rtol=1e-9, atol=1e-12)

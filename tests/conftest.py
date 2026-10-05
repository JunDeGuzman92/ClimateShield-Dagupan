"""Shared test setup.

Every test runs inside a sandbox: runtime state files in data/app_layers are backed up before the test and
restored afterwards, so running the suite never touches the user's prefs, requests, shelters or exercise history.
"""
import ast
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
APP = str(APP_DIR / "climateshield_command_center.py")
LAY = ROOT / "data" / "app_layers"
ARTIFACTS = ROOT / "tests" / "_artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)   # pytest --basetemp lives in here (system temp is restricted)
sys.path.insert(0, str(APP_DIR))

RUNTIME_FILES = [
    "ui_prefs.json", "live_cache.json", "rescue_requests.csv", "sim_inbox.csv", "sim_outbox.csv", "sim_contacts.csv",
    "resources.csv", "shelters.csv", "response_directory.csv", "exercise.json", "exercise_history.csv",
    "crowd_reports.csv", "pantal_gauge_log.csv", "philsensors_cache.json",
]
DEFAULT_PREFS = {
    "kiosk": False, "wall_seconds": 15, "last_cycle_ts": 0.0, "cycle_idx": 0, "lang": "English", "theme2": "day",
    "pilot": ["Pantal"], "deck_panels": {"kpis": True, "cinema": True, "calendar": True, "watchlist": True},
}


def nav_labels():
    """Read the NAV list straight from the app source (importing the app would start Streamlit)."""
    tree = ast.parse(Path(APP).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "NAV":
            return [ast.literal_eval(e) for e in node.value.elts]
    raise RuntimeError("NAV not found in app")


@pytest.fixture(autouse=True)
def sandbox(tmp_path):
    bak = tmp_path / "runtime_backup"
    bak.mkdir()
    for f in RUNTIME_FILES:
        if (LAY / f).exists():
            shutil.copy2(LAY / f, bak / f)
    # clean, known starting state (keep the PhilSensors cache so tests don't hit the network)
    for f in RUNTIME_FILES:
        if f not in ("philsensors_cache.json", "live_cache.json"):
            (LAY / f).unlink(missing_ok=True)
    (LAY / "ui_prefs.json").write_text(json.dumps(DEFAULT_PREFS), encoding="utf-8")
    yield
    for f in RUNTIME_FILES:
        (LAY / f).unlink(missing_ok=True)
        if (bak / f).exists():
            shutil.copy2(bak / f, LAY / f)


@pytest.fixture
def prefs():
    def _set(**kw):
        p = dict(DEFAULT_PREFS)
        p.update(kw)
        (LAY / "ui_prefs.json").write_text(json.dumps(p), encoding="utf-8")
    return _set


@pytest.fixture(scope="session")
def layers():
    import data_core as dc
    return dc.Layers()


def boot(timeout=1500):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=timeout)
    at.run()
    return at


def goto(at, label):
    at.sidebar.radio[0].set_value(label)
    at.run()
    return at


def no_exc(at):
    assert not at.exception, " | ".join(e.value[:500] for e in at.exception)


def button(at, label=None, startswith=None, enabled=True):
    for b in at.button:
        if (label and b.label == label) or (startswith and b.label.startswith(startswith)):
            if not enabled or not b.disabled:
                return b
    raise AssertionError(f"button not found: {label or startswith!r}; have {[b.label for b in at.button][:30]}")

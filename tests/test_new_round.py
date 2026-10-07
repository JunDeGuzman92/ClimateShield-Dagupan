"""Facilitator screen, anchors override, feedback loop, run-history comparison."""
import json
import sys
from pathlib import Path

import pandas as pd

from conftest import LAY


def test_facilitator_screen_shows_live_clock(layers):
    import cinema
    from streamlit.testing.v1 import AppTest
    import exercise
    import response as rsp
    from test_missions import _units, _start

    _units([dict(type="🚤 Rubber boat", name="Boat 1", location="Pantal")])
    _start(layers)
    rsp.add_request("Pantal", 4, "🚤 Rescue boat / evacuation", "critical", "sim", "")
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app" / "climateshield_command_center.py"),
                            default_timeout=1200)
    at.session_state["facilitator"] = True   # same code path as ?facilitator=1
    at.run()
    assert not at.exception, " | ".join(e.value[:300] for e in at.exception)
    md = " ".join(m.value for m in at.markdown)
    assert "FACILITATOR SCREEN" in md
    assert "WATER LEVEL" in md and "EVENT FEED" in md
    assert "People waiting for pickup" in md
    assert len(at.sidebar) == 0, "sidebar must be hidden on the projector"


def test_facilitator_screen_stopped_state():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app" / "climateshield_command_center.py"),
                            default_timeout=1200)
    at.session_state["facilitator"] = True
    at.run()
    assert not at.exception
    assert any("NO EXERCISE RUNNING" in m.value for m in at.markdown)


def test_manual_anchor_override_applies_and_backfills(tmp_path):
    import data_core as dc
    (LAY / "manual_anchors.json").write_text(json.dumps(
        {"Barangay II": {"lon": 120.3362, "lat": 16.0430}}), encoding="utf-8")
    try:
        L2 = dc.Layers()
        ent = next(b for b in L2.brgy_anchors if b["barangay"] == "Barangay II")
        assert ent["anchor"] is not None, "manual anchor must take effect"
        assert abs(ent["anchor"]["lon"] - 120.3362) < 1e-9
        row = L2.brgy[L2.brgy["barangay"] == "Barangay II"].iloc[0]
        assert pd.notna(row["elev_m"]) and pd.notna(row["bldg_600m"]), "poisoned stats must be recomputed"
        assert any(n == "Barangay II" and "manual" in d for n, d in L2.re_anchored)
    finally:
        (LAY / "manual_anchors.json").unlink(missing_ok=True)


def test_manual_anchor_json_is_garbage_tolerant():
    import data_core as dc
    (LAY / "manual_anchors.json").write_text("{\"broken\": true, \"Barangay II\": {\"lon\": \"x\"}}",
                                             encoding="utf-8")
    try:
        L2 = dc.Layers()
        ent = next(b for b in L2.brgy_anchors if b["barangay"] == "Barangay II")
        assert ent["anchor"] is None or isinstance(ent["anchor"], dict)
    finally:
        (LAY / "manual_anchors.json").unlink(missing_ok=True)


def test_feedback_log_and_summary_roundtrip():
    import feedback
    for i in range(3):
        feedback.log(context="exercise: A · story", barangay="Pantal", rating=5 - i,
                     worked="clear queue", change="more boats", author=f"team{i}")
    s = feedback.summary()
    assert s["n"] >= 3 and 3.9 < s["avg"] < 4.1, f"avg over 5,4,3 should be 4: {s}"
    notes = feedback.list_notes(context="exercise")
    assert all(n["context"].startswith("exercise") for _, n in notes.iterrows())


def test_run_history_compares_teams():
    import exercise
    hist = pd.DataFrame([
        dict(finished="2026-10-01 10:00", team="Bangus", scenario="a", storm_hours=40.0, score=52.0, grade="C",
             requests=9, resolved_pct=44, intake_min=2.0, assign_min=4.0, critical_resolved_pct=50,
             events_acked_pct=30, people_waiting=20, penalties=0),
        dict(finished="2026-10-02 10:00", team="Bangus", scenario="b", storm_hours=40.0, score=71.0, grade="B",
             requests=9, resolved_pct=70, intake_min=1.2, assign_min=3.0, critical_resolved_pct=80,
             events_acked_pct=60, people_waiting=5, penalties=0),
        dict(finished="2026-10-03 10:00", team="Milkfish", scenario="a", storm_hours=40.0, score=64.0, grade="C",
             requests=8, resolved_pct=60, intake_min=1.5, assign_min=3.5, critical_resolved_pct=70,
             events_acked_pct=45, people_waiting=8, penalties=0),
    ])
    hist.to_csv(Path(exercise.HISTORY), index=False)
    try:
        s = exercise.history_summary()
        assert s["n"] == 3
        assert s["best"]["team"] == "Bangus" and s["best"]["score"] == 71.0
        pt = s["per_team"].set_index("team")
        assert pt.loc["Bangus", "best"] == 71.0 and pt.loc["Milkfish", "runs"] == 1
    finally:
        Path(exercise.HISTORY).unlink(missing_ok=True)

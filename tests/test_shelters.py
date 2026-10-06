"""Shelter dynamics: mission deliveries land evacuees in shelters; centres mark FULL on arrival."""
import pandas as pd


def test_deliveries_fill_shelters_and_mark_full(layers):
    import exercise
    import ops
    import response as rsp
    from test_missions import _start, _tick_all, _units

    _units([dict(type="🚤 Rubber boat", name="Boat 1", location="Pantal")])
    _start(layers)
    sh = ops.load_shelters(layers)
    a = next(b["anchor"] for b in layers.brgy_anchors if b["barangay"] == "Pantal")
    d = (sh["lat"].astype(float) - a["lat"]) ** 2 + ((sh["lon"].astype(float) - a["lon"]) * 0.96) ** 2
    pick = d.nsmallest(2).index
    sh.loc[pick[0], "status"] = "open"
    sh.loc[pick[0], "capacity"] = "6"
    sh.loc[pick[1], "status"] = "open"
    sh.loc[pick[1], "capacity"] = "200"
    ops.save_shelters(sh)
    rid = rsp.add_request("Pantal", 6, "🚤 Rescue boat / evacuation", "critical", "sim", "")
    exercise.assign(layers, exercise.load(), "U001", rid)
    notes = _tick_all(layers, n=7, mins=0.09)
    sh = ops.load_shelters(layers)
    row = sh.loc[pick[0]]
    tot = int(pd.to_numeric(sh["headcount"], errors="coerce").fillna(0).sum())
    assert tot == 6, "6 delivered people must be sheltered"
    assert row["status"] == "full" and int(row["headcount"]) == 6, "small centre full at capacity 6"
    assert any("FULL" in n or "shelter" in n.lower() for n in notes)
    assert exercise.load()["unit_stats"]["U001"]["people"] == 6

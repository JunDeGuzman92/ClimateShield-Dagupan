"""Unit mission physics: travel time, trip capacity, auto-resolve, flooded-request feasibility, unit-down."""
import json
from datetime import datetime, timedelta

import pandas as pd

from conftest import LAY


def _units(rows):
    pd.DataFrame([dict(unit_id=f"U{i + 1:03d}", **r, owner="practice", status="available", assigned_request="",
                       contact="", updated_at="") for i, r in enumerate(rows)]).to_csv(LAY / "resources.csv", index=False)


def _start(layers, story="king_tide", speed=8):
    import cinema
    import exercise
    return exercise.start(layers, cinema.FLOOD_STORIES[story], speed, ["Pantal"], "T")


def _shift(mins):
    p = LAY / "exercise.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["started_at"] = (datetime.fromisoformat(s["started_at"]) - timedelta(minutes=mins)).isoformat(timespec="seconds")
    p.write_text(json.dumps(s), encoding="utf-8")


def _tick_all(layers, n=4, mins=0.25):
    """Advance the clock and tick — in the live app the 5-second auto-refresh plays this role."""
    import exercise
    notes = []
    for _ in range(n):
        _shift(mins)
        st, _f = exercise.tick(layers)
        notes += (st.get("phys_notes") or [])
        if st.get("phys_notes"):
            st["phys_notes"] = []
            exercise.save(st)
    return notes


def test_boat_travels_delivers_and_frees_up(layers):
    import exercise
    import ops
    import response as rsp
    _units([dict(type="🚤 Rubber boat", name="Boat 1", location="Pantal")])
    _start(layers)
    rid = rsp.add_request("Pantal", 6, "🚤 Rescue boat / evacuation", "critical", "sim", "")
    ok, det = exercise.assign(layers, exercise.load(), "U001", rid)
    assert ok and "en route" in det and "1 trip(s)" in det
    assert ops.load_resources().iloc[0]["status"] == "en route"
    # small steps: the full round trip needs ~0.9 storm-hours; staying under hour 8 keeps the
    # "boat engine failure" complication out of this test's way
    notes = _tick_all(layers, n=6, mins=0.09)
    assert exercise.load()["delivered"][rid] == 6
    rq = rsp.load_requests()
    assert rq.iloc[0]["status"] == "resolved" and rq.iloc[0]["resolved_at"]
    rs = ops.load_resources()
    assert rs.iloc[0]["status"] == "available", "boat must come home"
    assert any("delivered 6" in n for n in notes)


def test_small_boat_needs_multiple_trips(layers):
    import exercise
    import response as rsp
    _units([dict(type="🛶 Banca", name="Banca 1", location="Pantal")])  # capacity 6
    _start(layers)
    rid = rsp.add_request("Pantal", 12, "🚤 Rescue boat / evacuation", "critical", "sim", "")
    ok, det = exercise.assign(layers, exercise.load(), "U001", rid)
    assert ok and "2 trip(s)" in det
    _tick_all(layers, n=8, mins=0.09)
    assert exercise.load()["delivered"][rid] == 12
    assert rsp.load_requests().iloc[0]["status"] == "resolved"


def test_two_boats_do_not_double_lift(layers):
    import exercise
    import response as rsp
    _units([dict(type="🚤 Rubber boat", name="Boat 1", location="Pantal"),
            dict(type="🚤 Rubber boat", name="Boat 2", location="Pantal")])
    _start(layers)
    rid = rsp.add_request("Pantal", 12, "🚤 Rescue boat / evacuation", "critical", "sim", "")
    for u in ("U001", "U002"):
        ok, det = exercise.assign(layers, exercise.load(), u, rid)
        assert ok, det
    _tick_all(layers, n=6, mins=0.09)
    assert exercise.load()["delivered"][rid] == 12, "second boat should board only the remaining 4"
    assert rsp.load_requests().iloc[0]["status"] == "resolved"


def test_vehicles_refused_at_flooded_requests_boats_are_not(layers):
    import cinema
    import exercise
    import ops
    import response as rsp
    _units([dict(type="🚑 Ambulance", name="Amb 1", location="Pantal"),
            dict(type="🚤 Rubber boat", name="Boat 1", location="Pantal")])
    _start(layers)
    _shift(1.25)  # storm hour 10 ≈ the king-tide peak
    st = exercise.load()
    W = exercise.water_at(layers, st["story"], exercise.sim_hour(st))
    deep = next(b for b in layers.brgy["barangay"].tolist()
                if (exercise.depth_at_anchor(layers, b, W) or 0) > 0.5)
    rid = rsp.add_request(deep, 3, "🩹 Medical", "critical", "sim", "")
    no, why = exercise.assign(layers, exercise.load(), "U001", rid)
    assert not no and "boat" in why.lower()
    assert ops.load_resources().iloc[0]["status"] == "available", "refused unit must stay available"
    yes, det = exercise.assign(layers, exercise.load(), "U002", rid)
    assert yes


def test_unit_down_requeues_the_request(layers):
    import exercise
    import ops
    import response as rsp
    _units([dict(type="🚤 Rubber boat", name="Boat 1", location="Pantal"),
            dict(type="🚤 Rubber boat", name="Boat 2", location="Pantal")])
    _start(layers)
    rid = rsp.add_request("Pantal", 5, "🚤 Rescue boat / evacuation", "critical", "sim", "")
    exercise.assign(layers, exercise.load(), "U001", rid)
    ops.assign_resource("U001", "", status="maintenance")   # goes down before reaching the scene
    _tick_all(layers, n=1)
    assert not (exercise.load()["missions"] or {})
    rq = rsp.load_requests()
    assert rq.iloc[0]["status"] == "acknowledged", "request must return to the queue"
    ok, det = exercise.assign(layers, exercise.load(), "U002", rid)
    assert ok, "the second boat can take over"

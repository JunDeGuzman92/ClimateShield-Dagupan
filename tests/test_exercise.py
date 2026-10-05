"""Timed exercise: storm clock, injected events acting on live state, scoring, history."""
import json
from datetime import datetime, timedelta

import pandas as pd

from conftest import LAY, boot, button, goto, nav_labels, no_exc

RESP = next(label for label in nav_labels() if "Response" in label)


def _shift(minutes):
    p = LAY / "exercise.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["started_at"] = (datetime.fromisoformat(s["started_at"]) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    p.write_text(json.dumps(s), encoding="utf-8")


def _state():
    return json.loads((LAY / "exercise.json").read_text(encoding="utf-8"))


def test_full_exercise_run(layers):
    import ops
    pd.DataFrame([dict(unit_id=f"U00{i}", type="🚤 Rubber boat", name=f"Practice Boat {i}", owner="practice",
                       status="available", location="Pantal", assigned_request="", contact="", updated_at="")
                  for i in (1, 2, 3)]).to_csv(LAY / "resources.csv", index=False)
    sh = ops.load_shelters(layers)
    sh.loc[sh.index[:2], "status"] = "open"
    sh.loc[sh.index[:2], "capacity"] = "100"
    ops.save_shelters(sh)

    at = goto(boot(), RESP)
    at.text_input(key="ex_team").input("Team Test")
    button(at, label="▶ Start").click(); at.run(); no_exc(at)
    s = _state()
    assert s["running"] and len(s["events"]) == 9
    assert len(pd.read_csv(LAY / "resources.csv")) == 3, "start must keep registered units"
    assert pd.to_numeric(pd.read_csv(LAY / "shelters.csv")["capacity"], errors="coerce").notna().sum() == 2

    _shift(1.5)                                   # ≈ storm hour 6 at ×4
    at.run(); no_exc(at)
    fired = [e["id"] for e in _state()["events"] if e.get("fired_at")]
    assert fired == ["E1", "E2", "E3"], fired
    assert any("Exercise running" in c.value for c in at.caption), "flood conditions not synced to the storm clock"
    for _ in range(3):
        button(at, label="➕ Create request").click(); at.run()
    for _ in range(2):
        button(at, startswith="Assign to ").click(); at.run()
    button(at, label="Acknowledge").click(); at.run(); no_exc(at)

    _shift(1.5)                                   # ≈ storm hour 12
    at.run(); no_exc(at)
    s = _state()
    kinds = {e["kind"] for e in s["events"] if e.get("fired_at")}
    assert {"shelter_power", "unit_down", "facility_flooded"} <= kinds
    assert (pd.read_csv(LAY / "shelters.csv")["status"] == "unsafe").sum() == 1
    assert (pd.read_csv(LAY / "resources.csv")["status"] == "maintenance").sum() == 1

    button(at, label="⏹ Stop & score").click(); at.run(); no_exc(at)
    sc = _state()["final_score"]
    assert 0 <= sc["total"] <= 100 and sc["grade"] in "ABCDE"
    assert sc["kpis"]["requests"] == 3 and sc["kpis"]["events_acked_pct"] < 1
    hist = pd.read_csv(LAY / "exercise_history.csv")
    assert len(hist) == 1 and hist.iloc[0]["team"] == "Team Test"
    assert any(m.label == "Score" for m in at.metric)


def test_score_rewards_better_response(layers):
    """A team that answers and resolves everything must outscore one that does nothing."""
    import exercise
    import response as rsp
    import sms
    exercise.start(layers, "unprepared", 4, ["Pantal"], "idle")
    _shift(1.5)
    exercise.tick(layers)
    idle = exercise.score(layers)["total"]

    exercise.start(layers, "unprepared", 4, ["Pantal"], "active")
    _shift(1.5)
    exercise.tick(layers)
    inbox = sms.load_log(sms.INBOX)
    for _, m in inbox.iterrows():
        p = sms.parse_request(m["body"], layers.brgy["barangay"].tolist())
        rsp.add_request(p["barangay"], p["people"], p["need"], p["urgency"], m["sender"], p["note"], received_at=m["at"])
        sms.mark_handled(m["msg_id"])
    old = rsp.load_requests()
    new = old.copy()
    new["status"] = "resolved"
    rsp.save_requests(rsp.stamp_status_changes(new, old))
    for e in exercise.load()["events"]:
        if e.get("fired_at"):
            exercise.acknowledge(e["id"])
    active = exercise.score(layers)["total"]
    assert active > idle + 40, (idle, active)

"""Response simulator: simulated texts → requests → units → simulated dispatch → reset."""
import pandas as pd

from conftest import LAY, boot, button, goto, nav_labels, no_exc

RESP = next(label for label in nav_labels() if "Response" in label)


def _units(n=1):
    pd.DataFrame([dict(unit_id=f"U00{i}", type="🚤 Rubber boat", name=f"Practice Boat {i}", owner="practice",
                       status="available", location="Pantal", assigned_request="", contact="", updated_at="")
                  for i in range(1, n + 1)]).to_csv(LAY / "resources.csv", index=False)


def test_simulated_response_loop():
    _units(1)
    at = goto(boot(), RESP)
    no_exc(at)
    assert any("SIMULATOR" in m.value for m in at.markdown)
    button(at, startswith="🎲 Simulate 6 incoming").click(); at.run(); no_exc(at)
    assert next(m.value for m in at.metric if "Unread" in m.label) == "6"
    button(at, label="➕ Create request").click(); at.run(); no_exc(at)
    rq = pd.read_csv(LAY / "rescue_requests.csv", dtype=str).fillna("")
    assert len(rq) == 1 and rq.iloc[0]["source"] == "sms" and rq.iloc[0]["received_at"]
    assert rq.iloc[0]["contact"].startswith("Simulated resident")
    button(at, startswith="Assign to ").click(); at.run(); no_exc(at)
    assert pd.read_csv(LAY / "resources.csv", dtype=str).iloc[0]["status"] == "assigned"
    rq = pd.read_csv(LAY / "rescue_requests.csv", dtype=str).fillna("")
    assert rq.iloc[0]["status"] == "assigned" and rq.iloc[0]["assigned_at"]
    button(at, label="📤 Simulate send").click(); at.run(); no_exc(at)
    ob = pd.read_csv(LAY / "sim_outbox.csv", dtype=str)
    assert ob.iloc[0]["status"] == "simulated — not sent" and ob.iloc[0]["body"].startswith("[SIM]")
    button(at, startswith="🧹 Reset simulation").click(); at.run(); no_exc(at)
    assert not (LAY / "rescue_requests.csv").exists()
    assert pd.read_csv(LAY / "resources.csv", dtype=str).iloc[0]["status"] == "available"


def test_assignments_move_to_next_waiting_request():
    _units(2)
    at = goto(boot(), RESP)
    button(at, startswith="🎲 Simulate 6 incoming").click(); at.run()
    for _ in range(2):
        button(at, label="➕ Create request").click(); at.run()
    for _ in range(2):
        button(at, startswith="Assign to ").click(); at.run()
    rq = pd.read_csv(LAY / "rescue_requests.csv", dtype=str).fillna("")
    assert (rq["status"] == "assigned").sum() == 2, "second assignment went to the same request"


def test_shelter_space_routing(layers):
    import ops
    import response as rsp
    sh = ops.load_shelters(layers)
    hi = sh.sort_values("elev_m", ascending=False).index[0]
    sh.loc[hi, "status"] = "open"
    sh.loc[hi, "capacity"] = "200"
    sh.loc[hi, "headcount"] = 20
    ops.save_shelters(sh)
    rsp.add_request("Pantal", 6, "🏠 Shelter space", "normal", "", "test", drill=True)
    at = goto(boot(), RESP)
    no_exc(at)
    assert any("Shelter with space" in m.value and "180 free" in m.value for m in at.markdown)

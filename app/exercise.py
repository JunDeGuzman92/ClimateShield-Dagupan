"""Timed response exercises for the simulator: storm clock, injected events, scoring, run history.

A running exercise maps real time → storm time (speed = storm-hours per real minute). The Response page reads
the current storm water level from here, so flood conditions worsen and recede as the exercise runs.
Everything is local and simulated.
"""
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import cinema
import kit
import ops
import replay
import response as rsp
import sms

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
STATE = LAY / "exercise.json"
HISTORY = LAY / "exercise_history.csv"
MAX_H = 40.0


# ----------------------------------------------------------------------------- storm physics at an hour
def water_at(L, story, h):
    """Water level at a storm hour. Scripted stories use the proxy rise/recession curve; replay stories
    carry their own series from the historical rainfall record (replay.py)."""
    if story.get("replay"):
        return replay.water_at(story, h)
    peak = (L.water_level_for_share(story["share"]) + story["tide"] + 0.45 * story["clog"]
            - (0.22 if story["pumps"] else 0.0))
    W = kit.curve_W(peak, -0.35, float(h), rise_h=10.0, tau=16.0 + 32.0 * story["clog"])
    if story.get("surge", 0) > 0 and h >= 10:
        W += story["surge"] * np.exp(-((h - 13.0) ** 2) / 18.0)
    return float(W)


def story_max_h(story):
    if story.get("replay"):
        return float(story["hours"][-1])
    return MAX_H


def caption_at(story, h):
    text = story["beats"][0][1]
    for bh, t in story["beats"]:
        if h >= bh:
            text = t
    return text


# ----------------------------------------------------------------------------- state
def load():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"running": False}


def save(state):
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def sim_hour(state, now=None):
    if not state.get("running"):
        return float(state.get("final_hour", 0.0))
    now = now or datetime.now()
    mins = (now - datetime.fromisoformat(state["started_at"])).total_seconds() / 60.0
    return float(min(state.get("max_h", MAX_H), mins * float(state["speed"])))


def build_events(L, story, pilot):
    """Scripted complications, positioned around the storm's peak. Targets that depend on live state
    are resolved when the event fires."""
    if story.get("replay"):
        max_h = story_max_h(story)
        peak = max(story["peak_h"], 10.0)
        onset = next((hh for hh in story["hours"] if water_at(L, story, hh) > 0), peak * 0.5)
        up, down = max(peak - onset, 1.0), max(max_h - peak, 1.0)
        sched = [max(1.0, round(onset + f * up, 1)) for f in (0.05, 0.35, 0.55, 0.70, 0.85)] \
            + [round(peak, 1)] \
            + [round(peak + f * down, 1) for f in (0.15, 0.50, 0.90)]
    else:
        sched = [1.0, 4.0, 6.0, 7.0, 9.0, 10.0, 12.0, 16.0, 24.0]
    W_peak = water_at(L, story, story.get("peak_h", 10.0))
    exp = L.exposure(L.depth_grid(W_peak)[0], W_peak)
    road = (exp["roads_cut_worst"][0]["name"] if exp["roads_cut_worst"] else "the main road").title()
    p0 = pilot[0] if pilot else "Pantal"
    peak_day = ""
    if story.get("replay"):
        import pandas as pd
        peak_day = f" (storm peak {pd.Series(story['W_series'], story['hours']).idxmax():.0f} h into the replay)"
    return [
        dict(id="E1", h=sched[0], kind="texts", n=3, title="First help texts arrive",
             detail="Residents in low streets report rising water.", hint="Turn each text into a request."),
        dict(id="E2", h=sched[1], kind="road", title=f"{road} impassable",
             detail=f"Water over {road}; light vehicles stall.", hint="Re-route trucks; prefer boats for that area."),
        dict(id="E3", h=sched[2], kind="texts", n=4, title="Second wave of texts", detail="More households cut off.",
             hint="Prioritise critical (rooftop, child, elderly)."),
        dict(id="E4", h=sched[3], kind="shelter_power", title="Evacuation centre loses power",
             detail="Generator failed; centre marked UNSAFE.", hint="Move evacuees elsewhere; stop sending people there."),
        dict(id="E5", h=sched[4], kind="unit_down", title="Boat engine failure",
             detail="A unit is out of service (maintenance).", hint="Reassign its request to another unit."),
        dict(id="E6", h=sched[5], kind="texts", n=6, title="PEAK — surge of rescue texts" + peak_day,
             detail=f"Rooftop reports concentrated near {p0}.", hint="Triage: critical first."),
        dict(id="E7", h=sched[6], kind="facility_flooded", title="Clinic takes water",
             detail="A health facility near the practice area is flooded.", hint="Route medical requests to a dry hospital."),
        dict(id="E8", h=sched[7], kind="texts", n=3, title="Late texts: food and water",
             detail="Stranded families now need supplies.", hint="Use halls/shelters for relief goods."),
        dict(id="E9", h=sched[8], kind="info", title="Water receding",
             detail="Roads reopening as stored rain drains away.", hint="Plan returns; resolve finished requests."),
    ]


def start(L, story, speed, pilot, team):
    """story: a full story dict — a scripted one (cinema.FLOOD_STORIES[key]) or a replay (replay.build_story)."""
    ops.reset_simulation(L)
    st = dict(running=True, team=team or "Team", story=story, speed=float(speed), pilot=pilot or ["Pantal"],
              max_h=story_max_h(story),
              started_at=datetime.now().isoformat(timespec="seconds"), events=build_events(L, story, pilot))
    save(st)
    return st


def _apply(L, ev, state, W):
    pilot = state.get("pilot") or ["Pantal"]
    if ev["kind"] == "texts":
        for snd, body in ops.drill_messages(pilot, int(ev.get("n", 3))):
            sms.simulate_inbound(snd, body)
    elif ev["kind"] == "shelter_power":
        sh = ops.load_shelters(L)
        cand = sh[sh["status"] == "open"]
        if cand.empty:
            cand = sh[sh["barangay_hint"].isin(pilot)]
        if not cand.empty:
            i = cand.index[0]
            sh.loc[i, "status"] = "unsafe"
            ops.save_shelters(sh)
            ev["detail"] = f"{sh.loc[i, 'name']}: generator failed — marked UNSAFE."
            ev["target"] = str(sh.loc[i, "shelter_id"])
    elif ev["kind"] == "unit_down":
        rs = ops.load_resources()
        cand = rs[rs["status"].isin(["assigned", "en route", "on scene"])]
        cand = cand if len(cand) else rs[rs["status"] == "available"]
        if len(cand):
            i = cand.index[0]
            ev["detail"] = f"{rs.loc[i, 'name'] or rs.loc[i, 'unit_id']} out of service" + (
                f" while on {rs.loc[i, 'assigned_request']}" if rs.loc[i, "assigned_request"] else "") + "."
            ev["target"] = str(rs.loc[i, "unit_id"])
            rs.loc[i, ["status", "updated_at"]] = ["maintenance", datetime.now().isoformat(timespec="minutes")]
            ops.save_resources(rs)
        else:
            ev["detail"] = "No units registered — a real team would have lost a boat here."
    elif ev["kind"] == "facility_flooded":
        a = next((b["anchor"] for b in L.brgy_anchors if b["barangay"] == pilot[0]), None)
        if a:
            near = rsp.nearest_services(L, a["lat"], a["lon"], W, per_type=5,
                                        kinds=["🩺 Clinic / health station", "🏥 Hospital"])
            wet = near[near["state"] != "dry"] if len(near) else near
            pick = (wet if len(wet) else near)
            if len(pick):
                ev["detail"] = f"{pick.iloc[0]['name']} ({pick.iloc[0]['state']}) — medical requests must go elsewhere."


def tick(L, state=None):
    """Fire any due events; returns (state, newly_fired_list)."""
    state = state or load()
    if not state.get("running"):
        return state, []
    h = sim_hour(state)
    story = state["story"]
    fired = []
    for ev in state["events"]:
        if not ev.get("fired_at") and ev["h"] <= h:
            _apply(L, ev, state, water_at(L, story, ev["h"]))
            ev["fired_at"] = datetime.now().isoformat(timespec="seconds")
            fired.append(ev)
    if fired:
        save(state)
    return state, fired


def acknowledge(event_id):
    state = load()
    for ev in state.get("events", []):
        if ev["id"] == event_id and not ev.get("acked_at"):
            ev["acked_at"] = datetime.now().isoformat(timespec="seconds")
    save(state)


# ----------------------------------------------------------------------------- scoring
def _mins(a, b):
    try:
        return (pd.to_datetime(b) - pd.to_datetime(a)).total_seconds() / 60.0
    except Exception:
        return np.nan


def _band(x, good, bad):
    """1.0 at/below `good` minutes, 0.0 at/above `bad`, linear between; NaN → 0."""
    if x is None or not np.isfinite(x):
        return 0.0
    return float(np.clip((bad - x) / (bad - good), 0, 1))


def score(L, state=None):
    state = state or load()
    if "started_at" not in state:
        return None
    t0 = pd.to_datetime(state["started_at"])
    reqs = rsp.load_requests()
    reqs = reqs[pd.to_datetime(reqs["logged_at"], errors="coerce") >= t0.floor("min")] if len(reqs) else reqs
    n = len(reqs)
    intake = [_mins(r["received_at"] or r["logged_at"], r["logged_at"]) for _, r in reqs.iterrows()]
    assign = [_mins(r["logged_at"], r["assigned_at"]) for _, r in reqs.iterrows() if r.get("assigned_at")]
    resolve = [_mins(r["logged_at"], r["resolved_at"]) for _, r in reqs.iterrows() if r.get("resolved_at")]
    resolved = reqs[reqs["status"] == "resolved"] if n else reqs
    crit = reqs[reqs["urgency"] == "critical"] if n else reqs
    crit_res = crit[crit["status"] == "resolved"] if len(crit) else crit
    waiting = int(pd.to_numeric(reqs[reqs["status"] != "resolved"]["people"], errors="coerce").fillna(0).sum()) if n else 0
    fired = [e for e in state.get("events", []) if e.get("fired_at")]
    acked = [e for e in fired if e.get("acked_at")]
    ack_t = [_mins(e["fired_at"], e["acked_at"]) for e in acked]
    sh = ops.load_shelters(L)
    cap = pd.to_numeric(sh["capacity"], errors="coerce")
    hc = pd.to_numeric(sh["headcount"], errors="coerce").fillna(0)
    overfilled = int(((cap > 0) & (hc > cap)).sum())
    unsafe_occ = int(((sh["status"] == "unsafe") & (hc > 0)).sum())
    inbox = sms.load_log(sms.INBOX)
    if len(inbox):
        inbox = inbox[pd.to_datetime(inbox["at"], errors="coerce") >= t0]
    ignored = int((inbox["handled"].astype(str) != "True").sum()) if len(inbox) else 0
    texts = len(inbox)

    m = lambda xs: float(np.nanmean(xs)) if len(xs) and np.isfinite(np.nanmean(xs)) else np.nan  # noqa: E731
    k = dict(
        requests=n, texts_received=texts, texts_ignored=ignored,
        intake_min=m(intake), assign_min=m(assign), resolve_min=m(resolve),
        resolved_pct=(len(resolved) / n) if n else 0.0,
        critical=len(crit), critical_resolved_pct=(len(crit_res) / len(crit)) if len(crit) else 1.0,
        people_waiting=waiting, events_fired=len(fired), events_acked_pct=(len(acked) / len(fired)) if fired else 1.0,
        ack_min=m(ack_t), shelters_overfilled=overfilled, unsafe_shelters_occupied=unsafe_occ,
    )
    pts = dict(
        intake=15 * _band(k["intake_min"], 2, 10) if n else 0.0,
        assignment=20 * _band(k["assign_min"], 3, 15),
        resolved=25 * k["resolved_pct"],
        critical=15 * k["critical_resolved_pct"] if n else 0.0,
        events=15 * k["events_acked_pct"] * (0.5 + 0.5 * _band(k["ack_min"], 1, 6)) if fired else 15.0,
        coverage=10 * (1 - min(1.0, ignored / texts)) if texts else 10.0,
    )
    penalty = 5 * overfilled + 8 * unsafe_occ
    total = float(np.clip(sum(pts.values()) - penalty, 0, 100))
    grade = "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D" if total >= 40 else "E"
    return dict(kpis=k, points=pts, penalty=penalty, total=round(total, 1), grade=grade,
                hour=round(sim_hour(state), 1))


def stop(L):
    state = load()
    if not state.get("running"):
        return state, None
    state["final_hour"] = sim_hour(state)
    state["running"] = False
    state["stopped_at"] = datetime.now().isoformat(timespec="seconds")
    save(state)
    sc = score(L, state)
    k = sc["kpis"]
    row = dict(finished=state["stopped_at"], team=state["team"], scenario=state["story"]["title"],
               storm_hours=round(state["final_hour"], 1), score=sc["total"], grade=sc["grade"], requests=k["requests"],
               resolved_pct=round(100 * k["resolved_pct"]), intake_min=round(k["intake_min"], 1) if np.isfinite(k["intake_min"]) else "",
               assign_min=round(k["assign_min"], 1) if np.isfinite(k["assign_min"]) else "",
               critical_resolved_pct=round(100 * k["critical_resolved_pct"]),
               events_acked_pct=round(100 * k["events_acked_pct"]), people_waiting=k["people_waiting"],
               penalties=sc["penalty"])
    hist = pd.read_csv(HISTORY) if HISTORY.exists() else pd.DataFrame()
    pd.concat([pd.DataFrame([row]), hist], ignore_index=True).to_csv(HISTORY, index=False)
    state["final_score"] = sc
    save(state)
    return state, sc


def history():
    return pd.read_csv(HISTORY) if HISTORY.exists() else pd.DataFrame()

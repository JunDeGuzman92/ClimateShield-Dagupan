"""Timed response exercises for the simulator: storm clock, injected events, scoring, run history.

A running exercise maps real time → storm time (speed = storm-hours per real minute). The Response page reads
the current storm water level from here, so flood conditions worsen and recede as the exercise runs.
Everything is local and simulated.
"""
import io
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
from geo import haversine

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
    """Fire due events, advance unit missions; returns (state, newly_fired_list). Physics notes land in
    state['phys_notes'] for the UI to toast."""
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
    changed = _physics(L, state, h)
    esc = _escalations(L, state, h)
    if esc:
        state["phys_notes"] = state.get("phys_notes", []) + esc
        changed = True
    if fired or changed:
        save(state)
    return state, fired


def acknowledge(event_id):
    state = load()
    for ev in state.get("events", []):
        if ev["id"] == event_id and not ev.get("acked_at"):
            ev["acked_at"] = datetime.now().isoformat(timespec="seconds")
    save(state)


# ----------------------------------------------------------------------------- unit mission physics
# Missions advance with the STORM clock (not wall time), so travel takes real storm-hours at any speed.
# state["missions"][unit_id] = {req, phase(out|back|home), eta_out/eta_back/eta_home, travel_h, km, cap,
#                              load, need, people, delivered}
# state["delivered"][req_id] = people delivered so far (across all units serving that request).
NEED_CARRIES = {"🚤 Rescue boat / evacuation", "🏠 Shelter space", "🩹 Medical"}
LOAD_H = 0.30     # time to board people / hand over aid, in storm-hours
PREP_H = 0.10     # launch / prep before rolling


def anchor_of(L, brgy):
    return next((b["anchor"] for b in L.brgy_anchors if b["barangay"] == brgy), None)


def depth_at_anchor(L, brgy, W):
    """Flood depth at a barangay's anchor cell (None if no anchor)."""
    a = anchor_of(L, brgy)
    if a is None:
        return None
    from geo import Transformer
    x, y = L.to_utm(a["lon"], a["lat"])
    ci = int(np.clip(round((x - L.transform.c) / 30 - 0.5), 0, L.w - 1))
    ri = int(np.clip(round((L.transform.f - y) / 30 - 0.5), 0, L.h - 1))
    return max(W - float(L.dem[ri, ci]), 0.0)


def can_serve(L, unit_type, brgy, W):
    """(ok, reason) — vehicles/teams cannot cross flooded requests; boats/suports are not gated by depth."""
    ph = ops.UNIT_PHYSICS.get(unit_type, {})
    if ph.get("kind") in ("vehicle", "team") and ph.get("max_water_m") is not None:
        d = depth_at_anchor(L, brgy, W)
        if d is not None and d > ph["max_water_m"]:
            return False, f"{unit_type} can't cross {d:.2f} m of water at that request — send a boat (max {ph['max_water_m']:.2f} m)"
    return True, ""


def _stamp_request(req_id, **fields):
    df = rsp.load_requests()
    m = df["id"] == req_id
    if m.any():
        for k, v in fields.items():
            df.loc[m, k] = v
        rsp.save_requests(df)


def assign(L, state, unit_id, req_id):
    """Assign a unit to a request during a running exercise. Creates a mission with travel time and
    capacity; the request is auto-resolved when enough people have been delivered (or the support
    unit returns). Returns (ok, detail)."""
    reqs = rsp.load_requests()
    rq = reqs[reqs["id"] == req_id]
    if rq.empty:
        return False, "request not found"
    rq = rq.iloc[0]
    rs = ops.load_resources()
    un = rs[(rs["unit_id"] == unit_id) & (rs["status"] == "available")]
    if un.empty:
        return False, f"{unit_id} is not available"
    un = un.iloc[0]
    ph = ops.UNIT_PHYSICS.get(un["type"], dict(speed_kmh=20, capacity=0, kind="vehicle"))
    h = sim_hour(state)
    W = water_at(L, state["story"], h)
    ok, reason = can_serve(L, un["type"], rq["barangay"], W)
    if not ok:
        return False, reason
    a_req = anchor_of(L, rq["barangay"])
    a_unit = anchor_of(L, un["location"])
    if a_req and a_unit:
        km = max(0.3, haversine(a_unit["lat"], a_unit["lon"], a_req["lat"], a_req["lon"]) / 1000.0)
    else:
        km = 0.5  # co-located / unknown base
    travel = max(0.25, PREP_H + km / max(float(ph.get("speed_kmh", 20)), 1))
    cap = int(ph.get("capacity", 0))
    state.setdefault("missions", {})[unit_id] = dict(
        req=req_id, phase="out", start_h=h, eta_out=h + travel, km=round(km, 1), travel_h=round(travel, 2),
        cap=cap if rq["need"] in NEED_CARRIES else 0, need=rq["need"], people=int(rq["people"] or 1),
        brgy=rq["barangay"], delivered=0, unit_name=str(un.get("name") or unit_id))
    state.setdefault("delivered", {}).setdefault(req_id, 0)
    ops.assign_resource(unit_id, req_id, status="en route")
    _stamp_request(req_id, status="assigned" if rq["status"] in ("new", "acknowledged") else rq["status"],
                   assigned_to=unit_id, assigned_at=rsp._now(), updated_at=rsp._now())
    trips = " · support (carries nobody)" if cap == 0 or rq["need"] not in NEED_CARRIES else \
        f" · {max(1, -(-int(rq['people'] or 1) // max(cap, 1)))} trip(s) of {cap}"
    save(state)
    return True, f"{un['type']} en route · {km:.1f} km · ~{travel:.1f} storm-hours out{trips}"


def _physics(L, state, h):
    """Advance missions one tick; appends human-readable notes to state['phys_notes']."""
    notes = []
    missions = state.setdefault("missions", {})
    delivered = state.setdefault("delivered", {})
    rs = ops.load_resources()
    rstat = rs.set_index("unit_id")["status"].to_dict() if len(rs) else {}
    reqs = rsp.load_requests()
    rstat_req = reqs.set_index("id")["status"].to_dict() if len(reqs) else {}
    for uid, m in list(missions.items()):
        # unit lost to maintenance (E5): mid-outbound the trip is aborted (request back to the queue);
        # mid-return the people aboard reach safety first, then the unit stands down.
        if m["phase"] != "home" and rstat.get(uid) == "maintenance" and m["phase"] != "back":
            _stamp_request(m["req"], status="acknowledged")
            del missions[uid]
            notes.append(f"⚠ {m['unit_name']} went down before reaching {m['req']} — back in the queue")
            continue
        if rstat_req.get(m["req"]) == "resolved":
            if rstat.get(uid) == "maintenance":
                del missions[uid]
                notes.append(f"⚠ {m['unit_name']} down — request served by others")
                continue
            ops.assign_resource(uid, "", status="available")
            del missions[uid]
            notes.append(f"✅ {m['unit_name']} freed — {m['req']} resolved")
            continue
        if m["phase"] == "out" and h >= m["eta_out"]:
            if m["cap"] and m["need"] in NEED_CARRIES:
                # loads already aboard other units serving this request are not boardable again
                inflight = sum((mm.get("load") or 0) for mm in missions.values()
                               if mm is not m and mm["req"] == m["req"] and mm["phase"] == "back")
                remaining = max(m["people"] - delivered.get(m["req"], 0) - inflight, 0)
                m["load"] = int(min(m["cap"], remaining))
                m["phase"], m["eta_back"] = "back", h + LOAD_H + m["travel_h"]
                notes.append(f"📍 {m['unit_name']} on scene at {m['req']} — boarding {m['load']}")
            else:
                m["phase"], m["eta_back"] = "back", h + LOAD_H + m["travel_h"]
                notes.append(f"📍 {m['unit_name']} reached {m['req']}")
        elif m["phase"] == "back" and h >= m["eta_back"]:
            stats = state.setdefault("unit_stats", {}).setdefault(uid, dict(trips=0, people=0))
            if m["cap"] and m.get("load"):
                delivered[m["req"]] = delivered.get(m["req"], 0) + m["load"]
                m["delivered"] += m["load"]
                stats["people"] = int(stats.get("people", 0)) + m["load"]
                stats["trips"] = int(stats.get("trips", 0)) + 1
                sh_ok, sh_note = ops.admit_evacuees(L, m["brgy"], water_at(L, state["story"], h), m["load"])
                rem = m["people"] - delivered[m["req"]]
                notes.append(f"🎽 {m['unit_name']} delivered {m['load']} to safety — {sh_note}"
                             + (f" — {rem} still waiting" if rem > 0 else f" — {m['req']} complete"))
                m["load"] = 0
                if rem <= 0:
                    _stamp_request(m["req"], status="resolved", resolved_at=rsp._now(), updated_at=rsp._now())
                    if rstat.get(uid) == "maintenance":
                        # the unit went down (E5) on this trip — it must not come back as "returning"
                        del missions[uid]
                        notes.append(f"⚠ {m['unit_name']} down after drop-off — stays out of service")
                    else:
                        ops.assign_resource(uid, "", status="returning")
                        m["phase"], m["eta_home"] = "home", h + m["travel_h"]
                elif rstat.get(uid) == "maintenance":
                    del missions[uid]
                    notes.append(f"⚠ {m['unit_name']} down after drop-off — not making another trip")
                else:
                    m["phase"], m["eta_out"] = "out", h + m["travel_h"]
            else:
                stats["trips"] = int(stats.get("trips", 0)) + 1
                _stamp_request(m["req"], status="resolved", resolved_at=rsp._now(), updated_at=rsp._now())
                if rstat.get(uid) == "maintenance":
                    del missions[uid]
                    notes.append(f"⚠ {m['unit_name']} down at {m['req']} — stays out of service")
                else:
                    ops.assign_resource(uid, "", status="returning")
                    m["phase"], m["eta_home"] = "home", h + m["travel_h"]
                    notes.append(f"✅ {m['unit_name']} finished at {m['req']}")
        elif m["phase"] == "home" and h >= m["eta_home"]:
            if rstat.get(uid) != "maintenance":
                ops.assign_resource(uid, "", status="available")
            del missions[uid]
            notes.append(f"🏠 {m['unit_name']} is back at base" if rstat.get(uid) != "maintenance"
                         else f"🏠 {m['unit_name']} home — in maintenance")
    if notes:
        state["phys_notes"] = state.get("phys_notes", []) + notes
    return bool(notes)


def people_remaining(state, reqs=None):
    """People still waiting for pickup across open requests (delivered people excluded)."""
    reqs = reqs if reqs is not None else rsp.load_requests()
    delivered = state.get("delivered") or {}
    total = 0
    if len(reqs):
        opn = reqs[reqs["status"] != "resolved"]
        for _, r in opn.iterrows():
            total += max(0, int(pd.to_numeric(r["people"], errors="coerce") or 0) - int(delivered.get(r["id"], 0)))
    return total


# ----------------------------------------------------------------------------- resident escalation
ESCALATE_H = (6.0, 12.0)      # storm-hours of being ignored before the 1st/2nd follow-up text
_KW_OF = {"🚤 Rescue boat / evacuation": "BANGKA", "🩹 Medical": "GAMOT", "🔥 Fire": "SUNOG",
          "🍚 Food / water": "PAGKAIN", "🏠 Shelter space": "SHELTER", "🚓 Security": "HELP"}


def _escalations(L, state, h):
    """Ignored residents text again — louder. Max 2 follow-ups per message, then they give up."""
    notes = []
    esc = state.setdefault("escalations", {})
    inbox = sms.load_log(sms.INBOX)
    if not len(inbox):
        return notes
    started = datetime.fromisoformat(state["started_at"])
    pend = inbox[inbox["handled"].astype(str) != "True"]
    for _, m in pend.iterrows():
        try:
            msg_h = (datetime.fromisoformat(m["at"]) - started).total_seconds() / 60.0 * float(state["speed"])
        except Exception:
            continue
        lag = h - msg_h
        want = 2 if lag >= ESCALATE_H[1] else 1 if lag >= ESCALATE_H[0] else 0
        if want <= esc.get(m["msg_id"], 0):
            continue
        parsed = sms.parse_request(m["body"], L.brgy["barangay"].tolist())
        if not parsed or not parsed["barangay"]:
            continue    # non-emergency or unparseable: leave it for manual handling
        esc[m["msg_id"]] = want
        kw = _KW_OF.get(parsed["need"], "BANGKA")
        if want == 1:
            body = f"TUMATAAS PA RIN ANG TUBIG — TULONG ULI {parsed['barangay']} {parsed['people']} {kw}"
        else:
            body = (f"[HINDI NA PO KAMI LIGTAS] SAKLOLO ULI {parsed['barangay']} {parsed['people']} {kw} "
                    "MAY BATA AT MATANDA")
        sms.simulate_inbound(m["sender"], body)
        notes.append(f"📞 Same resident texts again — {parsed['barangay']}, {parsed['people']} "
                     f"({'worse now' if want == 2 else 'no reply yet'})")
    return notes


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
    waiting = people_remaining(state, reqs)
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
    state["missions"] = {}      # a stopped run leaves no ghost mission timeline
    state["delivered"] = {}
    save(state)
    return state, sc


def history():
    return pd.read_csv(HISTORY) if HISTORY.exists() else pd.DataFrame()


def history_summary():
    """(None) or dict: hist (chronological df), run numbers, best (row dict), per_team, trend."""
    h = history()
    if not len(h):
        return None
    h = h.copy()
    h["finished"] = pd.to_datetime(h["finished"], errors="coerce")
    h["score"] = pd.to_numeric(h["score"], errors="coerce")
    h = h.dropna(subset=["score"]).sort_values("finished").reset_index(drop=True)
    if not len(h):
        return None
    best = h.loc[h["score"].idxmax()].to_dict()
    per_team = (h.groupby("team", dropna=False)["score"]
                .agg(best="max", runs="count").reset_index())
    return dict(hist=h, n=len(h), best=best, per_team=per_team)


# ----------------------------------------------------------------------------- debrief (item 10)
def debrief_figure(L, state, sc=None):
    """One-page run timeline: water level, requests logged/assigned/resolved, complications fired.

    Returns (matplotlib figure, PNG bytes) for display and download. X-axis is real minutes into the
    run; the water curve uses the storm→real mapping so teams see how they did against the storm.
    """
    import matplotlib.pyplot as plt
    started = datetime.fromisoformat(state["started_at"])
    end = state.get("stopped_at") and datetime.fromisoformat(state["stopped_at"]) or datetime.now()
    total_min = max((end - started).total_seconds() / 60.0, 1.0)
    speed = float(state.get("speed", 4))
    story = state["story"]

    def mins(ts):
        try:
            return (pd.to_datetime(ts) - started).total_seconds() / 60.0
        except Exception:
            return np.nan

    fig, (ax, ax_leg, ax2) = plt.subplots(3, 1, figsize=(9, 7.6), height_ratios=[2.6, 0.30, 1],
                                        gridspec_kw=dict(hspace=0.30))
    t = np.linspace(0, total_min, 240)
    Ws = [water_at(L, story, tm * speed) for tm in t]
    ax.plot(t, Ws, color="#2563eb", lw=2.2)
    ax.fill_between(t, Ws, 0, where=np.array(Ws) > 0, color="#2563eb", alpha=0.18)
    ax.axhline(0, color="#9ca3af", lw=0.8)
    ax.set_ylabel("water level (m)")
    ax.set_title(f"Run timeline — {state.get('team', 'Team')} · {story['title']}", fontsize=11, color="#1f2937")
    reqs = rsp.load_requests()
    if len(reqs):
        logged = pd.to_datetime(reqs["logged_at"], errors="coerce")
        # run window only: requests logged after stop belong to a later session, and one marker
        # outside the axis stretches the tight-bbox crop to hundreds of millions of pixels
        reqs = reqs[(logged >= started - pd.Timedelta(minutes=1)) & (logged <= end + pd.Timedelta(seconds=1))]

    def mark(x, y, **kw):
        if np.isfinite(x) and -0.5 <= x <= total_min + 0.5:
            ax.plot(x, y, **kw)

    for _, r in reqs.iterrows():
        mark(mins(r["logged_at"]), 0.02, marker="v", color="#6b7280", ms=7, clip_on=False)
        if r.get("assigned_at"):
            mark(mins(r["assigned_at"]), 0.06, marker="o", color="#f59e0b", ms=6, clip_on=False)
        if r.get("resolved_at"):
            mark(mins(r["resolved_at"]), 0.10, marker="*", color="#16a34a", ms=11, clip_on=False)
    fired = [e for e in state.get("events", []) if e.get("fired_at")]
    fired = [e for e in fired if np.isfinite(x := mins(e["fired_at"])) and 0 <= x <= total_min]
    for i, e in enumerate(fired):
        x = mins(e["fired_at"])
        ax.axvline(x, color="#dc2626", lw=0.8, ls=":", alpha=0.8)
        # alternate label heights so neighbouring complications never print on top of each other;
        # storm hour included so labels carry meaning even where dense
        ylab = 0.97 if i % 2 == 0 else 0.89
        ax.text(x, ylab, f"{e['id']}·h{e['h']:,.0f}", color="#dc2626", fontsize=7, rotation=90,
                va="top", ha="right" if x / max(total_min, 1e-9) > 0.92 else "left",
                transform=ax.get_xaxis_transform())
    ax.set_xlim(0, total_min)
    # legend gets its own strip between chart and score table: nothing to collide with by construction.
    # (fractional offsets below/above the axes kept drifting into the title, the ticks, then the table —
    # the strip below is where every other chart in the app puts its key.)
    ax_leg.axis("off")
    ax_leg.legend(handles=[
        plt.Line2D([], [], color="#2563eb", lw=2, label="storm water (m)"),
        plt.Line2D([], [], marker="v", ls="", color="#6b7280", label="text → request"),
        plt.Line2D([], [], marker="o", ls="", color="#f59e0b", label="unit assigned"),
        plt.Line2D([], [], marker="*", ls="", color="#16a34a", label="delivered / resolved"),
    ], fontsize=9, loc="center", ncol=4, frameon=False,
        handletextpad=0.4, columnspacing=2.0)
    sc = sc or state.get("final_score") or {}
    k = sc.get("kpis", {})
    rows = [
        ("Score", f"{sc.get('total', 0):.0f} / 100 (grade {sc.get('grade', '—')})"),
        ("Text → request", f"{k.get('intake_min', np.nan):.1f} min avg" if np.isfinite(k.get("intake_min", np.nan)) else "—"),
        ("Request → unit", f"{k.get('assign_min', np.nan):.1f} min avg" if np.isfinite(k.get("assign_min", np.nan)) else "—"),
        ("Resolved", f"{100 * k.get('resolved_pct', 0):.0f}% (critical {100 * k.get('critical_resolved_pct', 0):.0f}%)"),
        ("Texts ignored", f"{k.get('texts_ignored', 0)} of {k.get('texts_received', 0)}"),
        ("Complications ack", f"{100 * k.get('events_acked_pct', 0):.0f}%"),
        ("People still waiting", f"{k.get('people_waiting', 0):,}"),
        ("Pitfalls", f"{k.get('shelters_overfilled', 0)} overfilled · {k.get('unsafe_shelters_occupied', 0)} unsafe occupied"),
    ]
    ax2.axis("off")
    # auto-layout table for the score rows — hand-stacked text once printed over the footer line
    tbl = ax2.table(
        cellText=[[label, val] for label, val in rows], colWidths=[0.30, 0.70], loc="upper center",
        cellLoc="left", bbox=[0.0, 0.06, 1.0, 0.90])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("none")
        cell.set_text_props(color="#1f2937" if c == 1 else "#111827",
                            weight="normal" if c == 1 else "bold")
    fig.text(0.02, 0.01, "ClimateShield-Dagupan exercise debrief · simulator only · "
             f"storm hour {state.get('final_hour', 0):.0f} at ×{speed:g}", fontsize=7.5, color="#6b7280")
    buf = io.BytesIO()
    # one artist outside the axis multiplies the tight crop until a single render allocates GBs
    # (367M px / ~10 s seen from a request logged after the run) - crop only while it stays sane
    try:
        w, h = fig.get_tightbbox(fig.canvas.get_renderer()).size
        crop = "tight" if w * h * 140 ** 2 <= 40e6 else None
    except Exception:
        crop = "tight"
    fig.savefig(buf, format="png", dpi=140, bbox_inches=crop, facecolor="white")
    return fig, buf.getvalue()

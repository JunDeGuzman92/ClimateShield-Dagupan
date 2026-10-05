"""Response layer: nearest services (from OSM), agency directory, stranded-community request queue.

Contact numbers are NEVER invented here: only national lines are pre-filled; every local entry starts
blank and `verified=False` until a user confirms it with the CDRRMO.
"""
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import pandas as pd

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
DIRECTORY = LAY / "response_directory.csv"
REQUESTS = LAY / "rescue_requests.csv"

# OSM class -> responder service
SERVICE_OF = {
    "hospital": "🏥 Hospital",
    "clinic": "🩺 Clinic / health station", "health_post": "🩺 Clinic / health station",
    "doctors": "🩺 Clinic / health station",
    "fire_station": "🚒 Fire station (BFP)",
    "police": "🚓 Police (PNP)",
    "townhall": "🏛 City / barangay hall",
    "shelter": "🏠 Evacuation shelter",
    "community_centre": "🏠 Evacuation shelter",
    "school": "🏫 School (evacuation centre candidate)", "college": "🏫 School (evacuation centre candidate)",
    "university": "🏫 School (evacuation centre candidate)",
}
SERVICE_COLORS = {
    "🏥 Hospital": "#dc2626", "🩺 Clinic / health station": "#f97316", "🚒 Fire station (BFP)": "#b91c1c",
    "🚓 Police (PNP)": "#1d4ed8", "🏛 City / barangay hall": "#7c3aed", "🏠 Evacuation shelter": "#059669",
    "🏫 School (evacuation centre candidate)": "#0891b2",
}
NEEDS = {
    "🚤 Rescue boat / evacuation": ["🚒 Fire station (BFP)", "🏛 City / barangay hall", "🚓 Police (PNP)"],
    "🩹 Medical": ["🏥 Hospital", "🩺 Clinic / health station"],
    "🔥 Fire": ["🚒 Fire station (BFP)"],
    "🍚 Food / water": ["🏛 City / barangay hall", "🏠 Evacuation shelter"],
    "🏠 Shelter space": ["🏠 Evacuation shelter", "🏫 School (evacuation centre candidate)"],
    "🚓 Security": ["🚓 Police (PNP)"],
}
STATUSES = ["new", "acknowledged", "assigned", "en route", "resolved"]

SRC_CITY = "dagupan.gov.ph/contact-us (retrieved 2026-10-05)"
SRC_HEADS = "dagupan.gov.ph/the-city/department-heads (retrieved 2026-10-05)"
DIR_COLS = ["service", "organisation", "mobile", "landline_075", "channel", "notes", "source", "confirmed_by_call",
            "sms_dispatch_ok"]
SEED_DIRECTORY = [
    # national
    ("Emergency (all services)", "National Emergency Hotline", "", "911", "call", "Nationwide", "national", True, False),
    ("Medical / disaster relief", "Philippine Red Cross (national)", "", "143", "call / text", "PRC national hotline", "national", True, False),
    # published on the official City Government of Dagupan website — test-call before relying on them
    ("Disaster coordination", "Dagupan CDRRMO", "0968-444-9598", "540-0363", "call / SMS",
     "Primary coordinator for rescue & evacuation", SRC_CITY + "; " + SRC_HEADS, False, False),
    ("Fire & rescue", "BFP Dagupan", "0917-184-2611", "522-2772", "call / SMS", "Fire, water rescue", SRC_CITY + "; " + SRC_HEADS, False, False),
    ("Police", "PNP Dagupan", "0916-525-6802 / 0933-502-4899", "529-5604", "call / SMS", "Security, traffic, search",
     SRC_CITY + "; " + SRC_HEADS, False, False),
    ("Volunteer rescue", "PANDA Volunteers", "0932-548-1545", "522-2808 / 522-8202", "call / SMS", "Volunteer rescue group", SRC_CITY, False, False),
    ("Health", "City Health Office (CHO)", "0933-861-6088 / 0997-840-1377", "522-8206", "call / SMS", "City health, medical teams",
     SRC_CITY + "; " + SRC_HEADS, False, False),
    ("Medical / relief", "Red Cross Dagupan", "0928-559-2701", "632-3296", "call / SMS", "Local Red Cross chapter", SRC_CITY, False, False),
    ("Social welfare", "CSWDO Dagupan", "", "515-3140 / 632-2566", "call", "Relief goods, evacuee welfare", SRC_CITY + "; " + SRC_HEADS, False, False),
    ("Public order", "POSO Dagupan", "0967-435-7097 / 0919-248-2531", "", "call / SMS", "Traffic, road closures", SRC_CITY + "; " + SRC_HEADS, False, False),
    ("Alert centre", "Public Alert Response & Management Center", "0927-601-6758", "", "call / SMS", "City alert/response centre", SRC_HEADS, False, False),
    ("Electric utility", "DECORP", "0925-726-9546", "522-5433 / 522-4145 / 515-2870", "call", "Power isolation in flooded zones", SRC_CITY, False, False),
    ("Engineering", "City Engineering Office", "", "522-1048", "call", "Roads, drainage, pumps", SRC_HEADS, False, False),
    # not published on the city site — fill from official sources
    ("Hospital", "Region 1 Medical Center", "", "", "call", "Government tertiary hospital", "", False, False),
    ("Social welfare (regional)", "DSWD Field Office I", "", "", "call", "Family food packs", "", False, False),
    ("Maritime / water rescue", "Philippine Coast Guard — Pangasinan", "", "", "call / radio", "Coastal & river rescue", "", False, False),
    ("Provincial coordination", "Pangasinan PDRRMO", "", "", "call", "Provincial assets, river gauges", "", False, False),
    ("Private — boats", "Registered banca / boat operators (per barangay)", "", "", "call / SMS", "Add names per barangay", "", False, False),
    ("Private — supplies", "Water refill / hardware / grocery partners", "", "", "call", "MOA partners for relief", "", False, False),
]


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = p2 - p1, radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * 6371000 * asin(sqrt(a))


def services(L):
    out = []
    for f in L.facilities:
        svc = SERVICE_OF.get(f["class"])
        if svc:
            out.append(dict(service=svc, name=f["name"] or f"(unnamed {f['class']})", lat=f["lat"], lon=f["lon"],
                            elev_m=float(f["elev_m"])))
    return out


def nearest_services(L, lat, lon, W, per_type=3, kinds=None):
    rows = []
    for s in services(L):
        if kinds and s["service"] not in kinds:
            continue
        d = haversine_m(lat, lon, s["lat"], s["lon"])
        depth = max(W - s["elev_m"], 0.0)
        state = "dry" if depth < 0.15 else ("water at door" if depth < 0.5 else "flooded — avoid")
        rows.append({**s, "distance_m": d, "depth_m": depth, "state": state})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(["service", "distance_m"]).groupby("service").head(per_type)
    return df.sort_values("distance_m").reset_index(drop=True)


def suggest_responder(L, lat, lon, need, W, urgency="normal"):
    kinds = NEEDS.get(need, [])
    if need == "🩹 Medical" and urgency == "critical":
        kinds = ["🏥 Hospital"]
    df = nearest_services(L, lat, lon, W, per_type=5, kinds=kinds)
    if df.empty:
        return None
    usable = df[df["state"] != "flooded — avoid"]
    return (usable if len(usable) else df).iloc[0].to_dict()


# ----------------------------------------------------------------------------- directory
def load_directory():
    if DIRECTORY.exists():
        df = pd.read_csv(DIRECTORY, dtype=str).fillna("")
        if all(c in df for c in DIR_COLS):
            for c in ("confirmed_by_call", "sms_dispatch_ok"):
                df[c] = df[c].astype(str).str.lower() == "true"
            return df[DIR_COLS]
    df = pd.DataFrame(SEED_DIRECTORY, columns=DIR_COLS)
    df.to_csv(DIRECTORY, index=False)
    return df


def dispatch_numbers(df=None):
    """Mobiles cleared for SMS dispatch: confirmed by a test call AND ticked sms_dispatch_ok."""
    df = load_directory() if df is None else df
    ok = df[df["confirmed_by_call"] & df["sms_dispatch_ok"] & (df["mobile"].str.len() > 0)]
    return {r["organisation"]: r["mobile"].split("/")[0].strip() for _, r in ok.iterrows()}


def save_directory(df):
    df.to_csv(DIRECTORY, index=False)


# ----------------------------------------------------------------------------- requests
REQ_COLS = ["id", "logged_at", "barangay", "people", "need", "urgency", "contact", "location_note",
            "status", "assigned_to", "updated_at", "source", "drill", "received_at", "assigned_at", "resolved_at"]


def load_requests():
    if REQUESTS.exists():
        df = pd.read_csv(REQUESTS, dtype=str).fillna("")
        for c in REQ_COLS:
            if c not in df:
                df[c] = ""
        return df[REQ_COLS]
    return pd.DataFrame(columns=REQ_COLS)


def save_requests(df):
    df.to_csv(REQUESTS, index=False)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def add_request(barangay, people, need, urgency, contact, note, assigned_to="", source="manual", drill=False,
                received_at=""):
    df = load_requests()
    now = _now()
    rid = f"R{len(df) + 1:04d}"
    row = dict(id=rid, logged_at=now, barangay=barangay, people=int(people), need=need, urgency=urgency,
               contact=contact, location_note=note, status="new", assigned_to=assigned_to, updated_at=now,
               source=source, drill=str(bool(drill)), received_at=received_at or now, assigned_at="", resolved_at="")
    df = pd.concat([pd.DataFrame([row]), df.astype(str)], ignore_index=True)
    save_requests(df)
    return rid


def stamp_status_changes(new_df, old_df):
    """Fill assigned_at / resolved_at when a request moves into those states (for exercise scoring)."""
    now = _now()
    before = old_df.set_index("id")["status"].to_dict() if len(old_df) else {}
    new_df = new_df.copy().astype(str).replace("nan", "")
    for i, r in new_df.iterrows():
        prev = before.get(r["id"], "")
        if r["status"] in ("assigned", "en route", "resolved") and not r["assigned_at"]:
            new_df.at[i, "assigned_at"] = now
        if r["status"] == "resolved" and prev != "resolved" and not r["resolved_at"]:
            new_df.at[i, "resolved_at"] = now
        if r["status"] != prev:
            new_df.at[i, "updated_at"] = now
    return new_df


def dispatch_message(req, responder, lang="English"):
    who = responder["name"] if responder else "nearest available unit"
    tag = "[SIM] "
    if lang == "Tagalog":
        return (f"{tag}[ClimateShield {req['id']}] {req['urgency'].upper()} · Brgy. {req['barangay']} · "
                f"{req['people']} katao · kailangan: {req['need']} · lokasyon: {req['location_note'] or '—'} · "
                f"contact: {req['contact'] or '—'} · itinalaga: {who}")
    return (f"{tag}[ClimateShield {req['id']}] {req['urgency'].upper()} · Brgy. {req['barangay']} · "
            f"{req['people']} people · need: {req['need']} · location: {req['location_note'] or '—'} · "
            f"contact: {req['contact'] or '—'} · suggested unit: {who}")

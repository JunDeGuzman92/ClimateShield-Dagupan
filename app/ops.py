"""Operations boards: shelter capacity, response resources, drill generator.

Shelters are seeded from OpenStreetMap (shelters, community centres, schools inside Dagupan's land area).
Capacities start BLANK — they must come from the CDRRMO evacuation-centre list, never guessed.
"""
import random
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
SHELTERS = LAY / "shelters.csv"
RESOURCES = LAY / "resources.csv"

SHELTER_COLS = ["shelter_id", "name", "kind", "barangay_hint", "lat", "lon", "elev_m", "capacity", "headcount",
                "status", "contact", "updated_at"]
SHELTER_STATUS = ["closed", "open", "full", "unsafe"]
RESOURCE_COLS = ["unit_id", "type", "name", "owner", "status", "location", "assigned_request", "contact", "updated_at"]
RESOURCE_TYPES = ["🚤 Rubber boat", "🛶 Banca", "🚚 Truck", "🚑 Ambulance", "🚒 Fire truck", "🚐 Van / transport",
                  "🔦 Generator / lights", "👥 Rescue team"]
RESOURCE_STATUS = ["available", "assigned", "en route", "on scene", "returning", "maintenance"]

# Practice physics for the response simulator (no engineering claims):
#   speed_kmh  — cruise speed used for ETA (straight-line distance)
#   capacity   — people carried per trip; 0 = support unit (delivers, carries nobody)
#   kind       — boat: works in floodwater · vehicle/team: refuses when water at the request > max_water_m
#   max_water_m — for vehicles/teams (boats are not gated)
UNIT_PHYSICS = {
    "🚤 Rubber boat": dict(speed_kmh=8, capacity=8, kind="boat", max_water_m=None),
    "🛶 Banca": dict(speed_kmh=6, capacity=6, kind="boat", max_water_m=None),
    "🚑 Ambulance": dict(speed_kmh=30, capacity=4, kind="vehicle", max_water_m=0.30),
    "🚒 Fire truck": dict(speed_kmh=28, capacity=0, kind="vehicle", max_water_m=0.30),
    "🚚 Truck": dict(speed_kmh=25, capacity=15, kind="vehicle", max_water_m=0.30),
    "🚐 Van / transport": dict(speed_kmh=30, capacity=10, kind="vehicle", max_water_m=0.30),
    "🔦 Generator / lights": dict(speed_kmh=25, capacity=0, kind="vehicle", max_water_m=0.05),
    "👥 Rescue team": dict(speed_kmh=5, capacity=4, kind="team", max_water_m=0.30),
}


def merge_edits(ed_state, base, fresh, id_col):
    """Apply ONLY the cells a user changed in a Streamlit data_editor onto the latest data on disk.

    ed_state: the editor's session state {edited_rows, added_rows, deleted_rows};
    base: the DataFrame that was displayed (row positions); fresh: a fresh reload from disk.
    Prevents a stale table from overwriting changes made meanwhile (e.g. an exercise event marking a shelter UNSAFE).
    """
    out = fresh.copy().astype(object)
    for ri, changes in (ed_state.get("edited_rows") or {}).items():
        rid = base.iloc[int(ri)][id_col]
        m = out[id_col].astype(str) == str(rid)
        for col, val in changes.items():
            if col in out.columns:
                out.loc[m, col] = val
    gone = [str(base.iloc[int(ri)][id_col]) for ri in (ed_state.get("deleted_rows") or [])]
    if gone:
        out = out[~out[id_col].astype(str).isin(gone)]
    added = [r for r in (ed_state.get("added_rows") or []) if any(str(v).strip() for v in r.values())]
    if added:
        out = pd.concat([out, pd.DataFrame(added)], ignore_index=True)
    return out.reset_index(drop=True)


def _now():
    return datetime.now().isoformat(timespec="minutes")


def seed_shelters(L):
    rows = []
    for f in L.facilities:
        if f["class"] not in ("shelter", "community_centre", "school", "college", "university", "townhall"):
            continue
        ri, ci = L.fac_cells[L.facilities.index(f)]
        if not L.land_mask[ri, ci]:
            continue
        kind = {"shelter": "designated shelter", "community_centre": "community centre",
                "townhall": "barangay/city hall"}.get(f["class"], "school")
        rows.append(dict(name=f["name"] or f"(unnamed {f['class']})", kind=kind, lat=round(f["lat"], 6),
                         lon=round(f["lon"], 6), elev_m=round(float(f["elev_m"]), 2)))
    df = pd.DataFrame(rows).drop_duplicates(subset=["name", "lat", "lon"]).reset_index(drop=True)
    # nearest barangay anchor as a hint
    anc = [(b["barangay"], b["anchor"]) for b in L.brgy_anchors if b["anchor"]]
    hints = []
    for _, r in df.iterrows():
        d = [((a["lat"] - r["lat"]) ** 2 + ((a["lon"] - r["lon"]) * 0.96) ** 2, n) for n, a in anc]
        hints.append(min(d)[1] if d else "")
    df["barangay_hint"] = hints
    df["shelter_id"] = [f"S{i + 1:03d}" for i in range(len(df))]
    df["capacity"] = ""
    df["headcount"] = 0
    df["status"] = "closed"
    df["contact"] = ""
    df["updated_at"] = _now()
    df = df[SHELTER_COLS]
    df.to_csv(SHELTERS, index=False)
    return df


def load_shelters(L):
    if not SHELTERS.exists():
        return seed_shelters(L)
    df = pd.read_csv(SHELTERS, dtype={"contact": str, "capacity": str}).fillna("")
    for c in SHELTER_COLS:
        if c not in df:
            df[c] = ""
    return df[SHELTER_COLS]


def save_shelters(df):
    df = df.copy()
    df["updated_at"] = _now()
    df.to_csv(SHELTERS, index=False)


def occupancy(df):
    cap = pd.to_numeric(df["capacity"], errors="coerce")
    hc = pd.to_numeric(df["headcount"], errors="coerce").fillna(0)
    return (hc / cap).where(cap > 0)


def shelter_with_space(L, lat, lon, W, people=1):
    """Nearest OPEN shelter with known free space ≥ people and dry ground."""
    df = load_shelters(L)
    if df.empty:
        return None
    cap = pd.to_numeric(df["capacity"], errors="coerce")
    hc = pd.to_numeric(df["headcount"], errors="coerce").fillna(0)
    ok = df[(df["status"] == "open") & (cap - hc >= people) & (pd.to_numeric(df["elev_m"], errors="coerce") > W - 0.15)]
    if ok.empty:
        return None
    d = (ok["lat"].astype(float) - lat) ** 2 + ((ok["lon"].astype(float) - lon) * 0.96) ** 2
    r = ok.loc[d.idxmin()].to_dict()
    r["free"] = int(float(r["capacity"]) - float(r["headcount"] or 0))
    r["distance_m"] = float(np.sqrt(d.min()) * 111000)
    return r


def admit_evacuees(L, brgy, W, people, exclude_ids=()):
    """Delivered people go to the best shelter available near `brgy`.

    Priority: nearest OPEN shelter with free space on dry ground → nearest open with space (wet site) →
    nearest open at all (over-capacity; the score penalises it) → none (unsheltered — a real planning gap).
    Returns an (ok, detail) note for the mission timeline. Only exercise deliveries call this.
    """
    df = load_shelters(L)
    if df.empty or people <= 0:
        return False, "no shelter board — evacuees wait at the drop-off"
    a = None
    for b in L.brgy_anchors:
        if b["barangay"] == brgy and b["anchor"]:
            a = b["anchor"]
    lat, lon = (a["lat"], a["lon"]) if a else (16.04, 120.33)
    cap = pd.to_numeric(df["capacity"], errors="coerce")
    hc = pd.to_numeric(df["headcount"], errors="coerce").fillna(0)
    dry = pd.to_numeric(df["elev_m"], errors="coerce") > (W - 0.15)
    openm = (df["status"] == "open") & (~df["shelter_id"].isin(exclude_ids))
    d2 = (df["lat"].astype(float) - lat) ** 2 + ((df["lon"].astype(float) - lon) * 0.96) ** 2
    for cand, why in (
        (df[openm & (cap - hc >= people) & dry], "space + dry"),
        (df[openm & (cap - hc >= people)], "space (wet site)"),
        (df[openm], "over capacity"),
    ):
        if len(cand):
            i = d2[cand.index].idxmin()
            new_hc = int(hc.loc[i] + people)
            df.loc[i, "headcount"] = new_hc
            cap_i = pd.to_numeric(pd.Series([df.loc[i, "capacity"]]), errors="coerce").iloc[0]
            if pd.notna(cap_i) and new_hc >= float(cap_i) and df.loc[i, "status"] == "open":
                df.loc[i, "status"] = "full"
                save_shelters(df)
                return True, f"→ {df.loc[i, 'name']} is now FULL ({new_hc}/{int(cap_i)})"
            save_shelters(df)
            return True, f"→ {df.loc[i, 'name']} ({why})"
    return False, "no OPEN shelter — open one on the 🏠 Shelters board (set its status to 'open')"


def load_resources():
    if RESOURCES.exists():
        df = pd.read_csv(RESOURCES, dtype=str).fillna("")
        for c in RESOURCE_COLS:
            if c not in df:
                df[c] = ""
        return df[RESOURCE_COLS]
    df = pd.DataFrame(columns=RESOURCE_COLS)
    df.to_csv(RESOURCES, index=False)
    return df


def save_resources(df):
    df = df.copy()
    df.to_csv(RESOURCES, index=False)


def assign_resource(unit_id, request_id, status="assigned"):
    df = load_resources()
    df.loc[df["unit_id"] == unit_id, ["status", "assigned_request", "updated_at"]] = [status, request_id, _now()]
    save_resources(df)


def release_resources_for(request_id):
    df = load_resources()
    m = df["assigned_request"] == request_id
    df.loc[m, ["status", "assigned_request", "updated_at"]] = ["returning", "", _now()]
    save_resources(df)


# ----------------------------------------------------------------------------- reset
def reset_simulation(L):
    """Clear all simulated activity: requests, messages, unit assignments, shelter headcounts/status."""
    for f in ("rescue_requests.csv", "sim_inbox.csv", "sim_outbox.csv",
              "sms_inbox.csv", "sms_outbox.csv", "sms_contacts.csv"):
        (LAY / f).unlink(missing_ok=True)
    rs = load_resources()
    if len(rs):
        rs["status"], rs["assigned_request"], rs["updated_at"] = "available", "", _now()
        save_resources(rs)
    sh = load_shelters(L)
    sh["headcount"], sh["status"] = 0, "closed"
    save_shelters(sh)


# ----------------------------------------------------------------------------- drill
DRILL_LINES = [
    ("HELP {b} {n} BOAT nasa bubong na kami", "critical"),
    ("SAKLOLO {b} {n} gamot may matanda", "high"),
    ("TULONG {b} {n} PAGKAIN TUBIG", "normal"),
    ("HELP {b} {n} RESCUE baha hanggang dibdib", "critical"),
    ("SAKLOLO {b} {n} SHELTER", "normal"),
]


def drill_messages(pilot_barangays, n=6, seed=None):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        tpl, _ = rnd.choice(DRILL_LINES)
        b = rnd.choice(pilot_barangays)
        out.append((f"Simulated resident #{rnd.randint(100, 999)}", tpl.format(b=b.upper(), n=rnd.randint(2, 12))))
    return out

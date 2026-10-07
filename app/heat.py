"""Heat operations: official-protocol engine, advisory board, danger ranking, cooling layer.

Every rule here is a planning translation of a PUBLIC rule, with its source attached.
Nothing is invented policy and the dashboard claims no new authority.

Sources (reused on the Methods page):
  PAGASA bands  — Caution 27–32 · Extreme Caution 33–41 · DANGER 42–51 · EXTREME DANGER 52+
  (PAGASA heat-index categories; the app's gauge already uses these cuts)
  DepEd DO37    — DepEd Order No. 37, s. 2022, class/work suspension rules for disasters,
  calamities and power interruptions (TY/flood/brownout machinery)
  DepEd-2024    — DepEd statement, 4 Apr 2024: school heads may suspend face-to-face classes and
  shift to Alternative Delivery Modes (ADM) in extreme heat and other health-threatening calamities
  DepEd-draft   — July 2026 DRAFT automatic-suspension proposal (heat index ≥40°C); reported, NOT policy
  DOLE-08-23    — DOLE Labor Advisory No. 08, s. 2023: risk/comorbidity assessment, ventilation,
  rest breaks & locations, uniforms/PPE, ≥2–3 L drinking water, info campaigns, emergency
  procedures, flexible hours by agreement
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
COOLING = LAY / "cooling.csv"
COOL_COLS = ["center_id", "name", "kind", "capacity", "headcount", "status", "barangay_hint",
             "lat", "lon", "contact", "updated_at"]
COOL_STATUS = ["closed", "open", "full"]
COOL_KINDS = ["school", "hall", "church / worship", "health post", "mall / commercial"]

SOURCES = {
    "PAGASA bands": "PAGASA heat-index categories (Caution 27–32 · Extreme Caution 33–41 · "
                    "DANGER 42–51 · EXTREME DANGER 52+)",
    "DepEd DO37": "DepEd Order No. 37, s. 2022 — suspension rules for disasters, calamities, "
                  "power outages (flood/TY machinery, applied to heat by analogy)",
    "DepEd-2024": "DepEd statement, 4 Apr 2024 — school heads may suspend face-to-face classes "
                  "and shift to ADM in extreme heat",
    "DepEd-draft": "DRAFT 2026 automatic-suspension proposal (heat index ≥40°C) — reported Jul 2026, "
                   "not policy",
    "DOLE-08-23": "DOLE Labor Advisory No. 08, s. 2023 — heat-stress prevention at the workplace",
}

PROTOCOLS = [
    dict(band="Caution · 27–32°C", lo=27, color="#fde047",
         headline="Routine heat day — fatigue possible with long exposure.",
         actions=[
             ("Households", "Water within reach for everyone working or playing outside."),
             ("Workplaces", "DOLE baseline: free drinking water on site; check ventilation (DOLE-08-23)."),
         ], sources=["PAGASA bands", "DOLE-08-23"]),
    dict(band="Extreme Caution · 33–41°C", lo=33, color="#fb923c",
         headline="Heat cramps and exhaustion become likely with exertion — plan the day around it.",
         actions=[
             ("Schools", "Heads may shorten classes, move PE/sports to shade or morning hours, or shift the "
                         "hottest hours to ADM — their discretion under DepEd-2024 (authority: DepEd DO37)."),
             ("Workplaces", "DOLE package: shaded rest areas, adjusted rest breaks, hats/light uniforms, "
                             "≥2–3 L water per worker, buddy checks for outdoor crews (DOLE-08-23)."),
             ("Barangay", "Remind households with elderly, infants and pregnant residents to stay shaded; "
                           "post the respite points that are open today."),
         ], sources=["PAGASA bands", "DepEd-2024", "DepEd DO37", "DOLE-08-23"]),
    dict(band="DANGER · 42–51°C", lo=42, color="#ef4444",
         headline="Heat cramps/exhaustion likely, heat stroke possible — run the hot-hours protocol.",
         actions=[
             ("Schools", "Shift to ADM for the day (DepEd-2024 discretion). Note: a 2026 draft rule would make "
                         "≥40°C automatic — DepEd-draft, NOT policy yet, so the decision still sits with heads."),
             ("Workplaces", "No strenuous outdoor labor 10:00–16:00; shaded 15-minute breaks each hour; "
                             "water stations on site; consider the flexible-hours option (DOLE-08-23)."),
             ("Barangay", "Hourly buddy checks on elderly living alone and pregnant residents; open every "
                           "registered cooling point; sari-sari water points active."),
             ("CDRRMO / CHO", "Pre-position rehydration supplies; health posts watch for cramps→exhaustion "
                               "escalation calls."),
         ], sources=["PAGASA bands", "DepEd-2024", "DepEd-draft", "DOLE-08-23"]),
    dict(band="EXTREME DANGER · 52°C+", lo=52, color="#be123c",
         headline="Heat stroke imminent — emergency posture for the duration.",
         actions=[
             ("Everyone", "Avoid outdoor activity. Any exertion outdoors is a medical risk (PAGASA bands)."),
             ("Schools", "ADM day; no outdoor activities at any hour."),
             ("Barangay + CHO", "Twice-daily checks on single-dwelling elderly; cooling centers open with water; "
                                 "heat-illness cases go to hospital, not the pharmacy."),
         ], sources=["PAGASA bands", "DepEd-2024"]),
]


def protocol_for(hi):
    """Protocol entries in force at a heat index (°C). Empty below 27."""
    return [p for p in PROTOCOLS if hi >= p["lo"]]


def day_blocks(hours, his):
    """Group (hour, HI) series into six parts of day with band + headline for the board."""
    bounds = [(0, 6, "Overnight"), (6, 9, "Morning"), (9, 12, "Late morning"),
              (12, 15, "Midday"), (15, 18, "Afternoon"), (18, 24, "Evening")]
    rows = []
    for a, b, name in bounds:
        sel = [(h, v) for h, v in zip(hours, his) if a <= h < b or (b == 24 and h == 23)]
        if not sel:
            continue
        mx = max(v for _, v in sel)
        ps = protocol_for(mx)
        top = ps[-1] if ps else PROTOCOLS[0]
        rows.append(dict(block=name, hours=f"{a:02d}:00–{b:02d}:00", peak_hi=round(mx),
                         band=top["band"], color=top["color"], headline=top["headline"],
                         n_actions=sum(len(p["actions"]) for p in ps)))
    return rows


def hi_hours_by_barangay(L, hours, hi_city):
    """Danger-hours per barangay from the city curve + urban-heat offsets (see cinema.heat_barangay_points).

    Returns DataFrame ranked by people × danger-hours: where respite points save the most first.
    """
    import cinema
    rows = []
    for hi in hi_city:
        pts = cinema.heat_barangay_points(L, hi)
        for p in pts:
            rows.append((p["name"], 1 if p["hi"] >= 41 else 0, p["pop"]))
    df = pd.DataFrame(rows, columns=["name", "danger", "pop"]).groupby("name").agg(
        danger_h=("danger", "sum"), pop=("pop", "first")).reset_index()
    df["people_hours"] = df["pop"] * df["danger_h"]
    return df.sort_values("people_hours", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------------- cooling layer
def _now():
    return datetime.now().isoformat(timespec="minutes")


def load_cooling():
    if COOLING.exists():
        df = pd.read_csv(COOLING, dtype=str).fillna("")
        for c in COOL_COLS:
            if c not in df:
                df[c] = ""
        return df[COOL_COLS]
    df = pd.DataFrame(columns=COOL_COLS)
    df.to_csv(COOLING, index=False)
    return df


def save_cooling(df):
    df = df.copy()
    df["updated_at"] = _now()
    df.to_csv(COOLING, index=False)


def seed_cooling_from_shelters(L, kinds=("school",)):
    """One-click practice setup: open shelters of these kinds double as cooling points."""
    import ops
    sh = ops.load_shelters(L)
    df = load_cooling()
    have = set(df["name"].astype(str)) if len(df) else set()
    added = 0
    for _, r in sh[sh["status"].isin(["open", "full"])].iterrows():
        if r["name"] in have or r.get("kind") not in kinds:
            continue
        df = pd.concat([df, pd.DataFrame([dict(
            center_id=f"C{len(df) + 1:03d}", name=r["name"], kind=r.get("kind", "school"),
            capacity=r.get("capacity", ""), headcount=0,
            status="open" if r["status"] == "open" else "full",
            barangay_hint=r.get("barangay_hint", ""), lat=r.get("lat", ""), lon=r.get("lon", ""),
            contact="", updated_at=_now())])],
            ignore_index=True)
        added += 1
    save_cooling(df)
    return added


def open_cooling(L):
    df = load_cooling()
    df = df[df["status"] == "open"]
    cap = pd.to_numeric(df["capacity"], errors="coerce")
    return df.assign(_cap=cap)


def nearest_cooling(L, lat, lon, need=1):
    """Nearest OPEN cooling center with room; dry-ground rule doesn't apply (heat ≠ flood)."""
    import math
    df = open_cooling(L)
    if df.empty:
        return None
    hc = pd.to_numeric(df["headcount"], errors="coerce").fillna(0)
    ok = df[(df["_cap"].isna()) | (df["_cap"] - hc >= need)]
    pool = ok if len(ok) else df
    pool = pool.copy()
    pool["_lat"] = pd.to_numeric(pool["lat"], errors="coerce")
    pool["_lon"] = pd.to_numeric(pool["lon"], errors="coerce")
    pool = pool.dropna(subset=["_lat", "_lon"])
    if pool.empty:
        return None

    def _d(r):
        p1, p2 = math.radians(lat), math.radians(float(r["_lat"]))
        a = (math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2)
             * math.sin(math.radians(float(r["_lon"]) - lon) / 2) ** 2)
        return 12742 * math.asin(math.sqrt(a)) * 1000.0
    pool["_d"] = [_d(r) for _, r in pool.iterrows()]
    r = pool.loc[pool["_d"].idxmin()].to_dict()
    r["distance_m"] = float(r["_d"])
    free = (r["_cap"] - hc.loc[pool["_d"].idxmin()]) if pd.notna(r["_cap"]) else None
    r["free"] = int(free) if free is not None else None
    return r


def cooling_stats():
    df = load_cooling()
    if not len(df):
        return dict(open=0, full=0, closed=0, capacity_known=0)
    cap = pd.to_numeric(df["capacity"], errors="coerce")
    return dict(open=int((df["status"] == "open").sum()), full=int((df["status"] == "full").sum()),
                closed=int((df["status"] == "closed").sum()), capacity_known=int(cap.notna().sum()))

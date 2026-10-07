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

import numpy as np
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

HUD = {"w": "🌡️ feels like (city)", "p": "🧍 residents in DANGER zones",
       "e": "❄ near a cooling point", "s": "⚠ no cooling point within 2.5 km", "bad": "s",
       "b": "❄ cooling points open", "r": "barangays in DANGER", "r_suffix": "",
       "legend": "felt heat °C — by PAGASA band",
       "legend_gradient": "linear-gradient(90deg,#e2e8f0,#fde047,#fb923c,#ef4444,#be123c)",
       "w_line": "residents beyond a cooling point over the"}

WATER_TIPS_EN = [
    ("Water", "Drink before you feel thirsty. Outdoor workers: 2–3 litres across the day (DOLE-08-23); "
              "in DANGER hours add a glass (≈250 ml) every 20–30 minutes of work."),
    ("Rest", "Shade or ventilated breaks every hour in DANGER hours; new/returning workers need "
             "shorter first shifts to acclimatize."),
    ("Clothing", "Loose, light-coloured, long-sleeved light fabric; wide brim hats."),
    ("Buddy", "Check elderly neighbours living alone, pregnant women, and infants — they feel heat "
              "first and fail quietly."),
    ("Danger signs → act", "Cramps: water, salt, shade. Exhaustion (pale, dizzy, sweating hard): lie "
                           "down, cool, water, do not return to work. Heat stroke (hot skin, confusion, "
                           "collapse): COOL IMMEDIATELY — wet cloths, fan, ice packs to armpits/groin — "
                           "and call 911 (or Red Cross 143). Minutes decide outcomes."),
    ("Never", "Do not leave children or pets in parked vehicles — cabin heat crosses 52°C in minutes."),
]
WATER_TIPS_TL = [
    ("Tubig", "Uminom bago mag-uhaw. Mga manggagawa sa labas: 2–3 litro bawat araw (DOLE); sa oras ng "
              "panganib, isang baso kada 20–30 minuto."),
    ("Pahinga", "Kada oras, mag-shade at magpalamig sa maaliwalas na lugar."),
    ("Damit", "Malwag, maliwanag ang kulay, manipis na mahabang manggas; sombrero na malapad."),
    ("Kaagaw / buddy system", "Tignan ang matatanda na mag-isa, buntis, at mga sanggol — sila ang "
                              "unang natamaan ng init."),
    ("Babala", "Pasmado o hilo? Higa sa shade, tubig, at bawal bumalik sa trabaho. Heat stroke (mainit "
               "ang balat, litoko)? Bilisang palamigin at tumawag ng 911 o Red Cross 143."),
    ("Huwag", "Huwag mag-iiwan ng bata o alagang hayop sa sasakyan."),
]


def tips(lang="English"):
    return WATER_TIPS_TL if lang == "Tagalog" else WATER_TIPS_EN

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


# ----------------------------------------------------------------------------- felt-heat raster & film
def felt_png(L, hi_by_idx, alpha=205):
    """Per-cell PNG colored by the barangay's felt heat (band color), land cells only."""
    import io as _io
    import base64 as _b64
    from PIL import Image
    import cinema
    if L.brgy_cells is None:
        raise ValueError("boundary masks not built — run `python app/brgypoly.py`")
    cmap = {i: cinema._hi_color(hi) for i, hi in hi_by_idx.items()}
    rgb = {"94a3b8": (0x94, 0xa3, 0xb8), "fde047": (0xfd, 0xe0, 0x47), "fb923c": (0xfb, 0x92, 0x3c),
           "ef4444": (0xef, 0x44, 0x44), "be123c": (0xbe, 0x12, 0x3c)}
    rgba = np.zeros((L.h, L.w, 4), dtype=np.uint8)
    idx = L.brgy_cells
    land = L.land_mask & (idx >= 0)
    # map band color hex to rgb tuple robustly
    def _rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    for i in np.unique(idx[land]):
        sel = (idx == i)
        col = _rgb(cinema._hi_color(hi_by_idx.get(int(i), 27.0)))
        rgba[..., 0][sel] = col[0]
        rgba[..., 1][sel] = col[1]
        rgba[..., 2][sel] = col[2]
    rgba[..., 3][land] = alpha
    buf = _io.BytesIO()
    Image.fromarray(rgba).save(buf, format="PNG")
    return buf.getvalue()


def cooling_reach(L):
    """Per-anchored-barangay: (distance to nearest OPEN cooling point or None) dictionary."""
    import cinema
    import response as rsp
    df = open_cooling(L)
    centers = []
    if len(df):
        lat = pd.to_numeric(df["lat"], errors="coerce")
        lon = pd.to_numeric(df["lon"], errors="coerce")
        for _, r in df.iterrows():
            try:
                centers.append((float(r["lat"]), float(r["lon"]), r["name"], "open"))
            except Exception:
                continue
    out = {}
    for p in cinema.heat_barangay_points(L, 30):   # 'hi' unused here
        best = None
        for la, lo, nm, st_ in centers:
            d = rsp.haversine_m(p["lat"], p["lon"], la, lo)
            if best is None or d < best[0]:
                best = (d, nm, st_)
        out[p["name"]] = best
    return {k: v for k, v in out.items()}


def film_frames(L, plan, story, reach=None):
    """Hourly frames for the heat day film: PNG overlay + survivor stats + caption.

    HUD fields (see mapfilm.FLOOD_HUD / heat.HUD): pop_in=residents in DANGER-band barangays,
    evacuated=residents near a cooling point, stranded=DANGER residents beyond 2.5 km of one,
    bldg=cooling points open, roads_km=barangays in DANGER (r_suffix ''), W=string 'feels like'.
    """
    import base64 as _b64
    import cinema
    reach = reach if reach is not None else {}
    open_cool = open_cooling(L)
    n_open = int(len(open_cool)) if len(open_cool) else 0
    frames = []
    for f in plan:
        hi = f["hi"]
        pts = {p["name"]: p for p in cinema.heat_barangay_points(L, hi)}
        covered_pop = 0
        pop_danger = 0
        n_danger_brgy = 0
        for nm, p in pts.items():
            r = reach.get(nm)
            near = bool(r and r[0] <= 2500)
            if p["hi"] >= 42:
                pop_danger += p["pop"]
                n_danger_brgy += 1
                if near:
                    covered_pop += p["pop"]
        filmy = {i: p["hi"] for i, p in enumerate(pts.values())}
        png = felt_png(L, filmy)
        ps = protocol_for(hi)
        top = ps[-1] if ps else PROTOCOLS[0]
        frames.append(dict(
            hour=float(f["hour"]), label=f"{f['hour']:02d}:00",
            W=f"{hi:.0f}°C · {top['band'].split(' ·')[0]}",
            caption=top["headline"],
            pop_in=pop_danger, evacuated=covered_pop,
            stranded=max(0, pop_danger - covered_pop),
            bldg=n_open, roads_km=n_danger_brgy,
            png=_b64.b64encode(png).decode(),
        ))
    return frames


# ----------------------------------------------------------------------------- heat briefing card
def briefing_png(L, row, anchor, hi, cat, story_note, reach_row, lang="English"):
    """One-page community heat card (PNG) — protocol call, nearest relief/health, hydration table."""
    import io as _io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tips_ = tips(lang)
    fig = plt.figure(figsize=(8.27, 11.0))
    fig.patch.set_facecolor("#ffffff")
    hdr = fig.add_axes([0, 0.90, 1, 0.10]); hdr.axis("off")
    hdr.add_patch(plt.Rectangle((0, 0), 1, 1, transform=hdr.transAxes, color="#c0392b"))
    hdr.text(0.03, 0.62, "CLIMATESHIELD — HEAT SURVIVAL CARD", color="white", fontsize=18, fontweight="bold")
    hdr.text(0.03, 0.20, f"{str(row['barangay']).upper()} · feels like ≈{hi:.0f}°C ({cat}) · "
             f"{datetime.now().strftime('%b %d, %Y')}", color="#fde2e2", fontsize=11)
    top = (protocol_for(hi)[-1] if protocol_for(hi) else PROTOCOLS[0])
    call = fig.add_axes([0.05, 0.76, 0.90, 0.10]); call.axis("off")
    call.text(0, 0.9, f"TODAY'S CALL — {top['band']}", fontsize=13, fontweight="bold", color="#7f1d1d")
    call.text(0, 0.45, top["headline"], fontsize=11, wrap=True, va="top")
    svcs = fig.add_axes([0.05, 0.53, 0.90, 0.19]); svcs.axis("off")
    svcs.text(0, 0.95, "Where to go / who to call", fontsize=13, fontweight="bold", color="#1f2937")
    yy = 0.75
    dcool = reach_row or (None, None, None)
    if dcool[0] is not None:
        svcs.text(0, yy, f"• Nearest OPEN cooling point: {dcool[1]} — {dcool[0]/1000:.1f} km away", fontsize=10.5)
    else:
        svcs.text(0, yy, "• No OPEN cooling point registered within 2.5 km — register relief points "
                         "(Deck → ❄️ Cooling register)", fontsize=10.5, color="#b91c1c")
    yy -= 0.12
    if anchor is not None:
        import response as rsp
        near = rsp.nearest_services(L, anchor["lat"], anchor["lon"], hi, per_type=1)
        for _, r in near.iterrows():
            svcs.text(0, yy, f"• Nearest {r['service']}: {r['name']} — {r['distance_m']/1000:.1f} km · "
                              f"site {r['state']}", fontsize=10.5)
            yy -= 0.12
    svcs.text(0, yy, "• Emergencies: 911 · Red Cross 143", fontsize=10.5, color="#7f1d1d", fontweight="bold")
    hyd = fig.add_axes([0.05, 0.08, 0.90, 0.42]); hyd.axis("off")
    hyd.text(0, 1.00, "Staying alive today", fontsize=13, fontweight="bold", color="#1f2937")
    y = 0.88
    for name, text_ in tips_:
        hyd.text(0, y, f"{name}:", fontsize=10.5, fontweight="bold")
        for j, wl in enumerate(__import__("textwrap").wrap(text_, 88)):
            hyd.text(0, y - (0.052 * (j + 1)), wl, fontsize=10)
        y -= 0.052 * (__import__("textwrap").wrap(text_, 88).__len__() + 1) + 0.01
    foot = fig.add_axes([0, 0, 1, 0.04]); foot.axis("off")
    foot.text(0.03, 0.45, "Community planning translation of PAGASA bands, DepEd ADM guidance & DOLE LA-08-23 · "
                          "official warnings: PAGASA / CDRRMO · simulator, not a warning", fontsize=7, color="#6b7280")
    buf = _io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()



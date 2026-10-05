"""Scenario stories and proxy physics (flood + heat).

Rendering lives in mapfilm.py (map time-lapse on the satellite basemap) and heat_chart() below. No 3D.
"""
import numpy as np
import plotly.graph_objects as go

import kit

# ----------------------------------------------------------------------------- stories
FLOOD_STORIES = {
    "unprepared": {
        "title": "Unprepared city · Calamity-class storm",
        "share": 45, "tide": 0.45, "clog": 0.85, "pumps": False, "warning_h": 0, "surge": 0.0,
        "beats": [
            (0, "A rain band stalls over Pangasinan. Drains are still half-blocked with plastics — nobody cleared them."),
            (2, "High tide meets the swollen Pantal. Canals back up; first water on the lowest streets."),
            (5, "Knee-deep in Pantal, Carael and Calmay. Families stay home — no early-warning call went out."),
            (8, "Roads cut. Tricycles stall. Shelters still locked; the rescue request queue is already long."),
            (10, "PEAK. Clogged drains hold the water high. Boats are the only way through low barangays."),
            (14, "Recession is slow — blocked outfalls drain at a trickle. Floodwater sits for days."),
            (22, "Day 2: stagnant water, leptospirosis risk, classes suspended citywide, markets closed."),
            (34, "Water finally leaves the streets. Clean-up begins — one week of lost income for most households."),
        ],
    },
    "prepared": {
        "title": "Prepared city · same storm",
        "share": 45, "tide": 0.45, "clog": 0.15, "pumps": True, "warning_h": 12, "surge": 0.0,
        "beats": [
            (0, "72-hour PAGASA rainfall outlook triggers the city plan: crews clear drains, pumps are staged at outfalls."),
            (2, "Pre-emptive evacuation begins for the six lowest barangays, while roads are still dry."),
            (5, "Water enters the same streets — but households are already in schools and gyms on higher ground."),
            (8, "Pumps and clear drains keep the peak lower. Main roads stay passable for ambulances."),
            (10, "PEAK — lower, shorter. Shelters report full headcounts; nobody is waiting on a roof."),
            (14, "Fast recession: open outfalls let the tide pull water out. Streets reappear by evening."),
            (22, "Day 2: most families return home. Health teams spray and inspect wells."),
            (34, "Back to normal. Lost days: one, not seven. The difference was decided before the first raindrop."),
        ],
    },
    "king_tide": {
        "title": "King tide + clogged drains · Alert-level rain",
        "share": 30, "tide": 0.85, "clog": 0.9, "pumps": False, "warning_h": 4, "surge": 0.0,
        "beats": [
            (0, "Only an Alert-level rain forecast — but a king tide of +0.85 m is due at the same time."),
            (3, "Tide comes in. Rivers cannot drain into Lingayen Gulf; the whole city becomes a bathtub."),
            (6, "Modest rain, serious flood: tide + blocked drains do what a bigger storm would."),
            (10, "PEAK. Coastal barangays — Bonuan, Pugaro, Pantal — flood from the sea side first."),
            (16, "Tide ebbs; water drains quickly where outfalls are clear, slowly where they are not."),
            (30, "Lesson: watch the tide table as closely as the rain gauge."),
        ],
    },
    "surge": {
        "title": "Upstream surge · Extreme 3-day event",
        "share": 65, "tide": 0.4, "clog": 0.5, "pumps": True, "warning_h": 8, "surge": 0.45,
        "beats": [
            (0, "Three days of rain across the Agno basin. Dagupan sits at the bottom of it all."),
            (4, "Local flooding first. Then the upstream rivers arrive — a second wave is coming."),
            (12, "SURGE. Upstream water reaches the city as a pulse; levels jump within hours."),
            (14, "PEAK. Even prepared pumps are overwhelmed at this scale — this is a regional evacuation."),
            (20, "Slow recession: the basin is still draining through Dagupan."),
            (36, "Day 3. The worst case in 45 years of records. Planning for this is why the maps exist."),
        ],
    },
}

HEAT_STORIES = {
    "april_typical": {
        "title": "Typical April day", "tmax": 34.0, "tmin": 25.5, "rh_day": 62, "rh_night": 84,
        "brownout": False,
        "beats": [
            (6, "Sunrise. Fish ports and markets open while the air is still cool."),
            (9, "Heat index enters Extreme Caution. Outdoor workers: water every 20 minutes."),
            (12, "Noon. Schoolyards and tricycle queues are the hot spots; dense barangays run 1–2°C hotter."),
            (14, "Peak heat. Pedicab and construction crews should be in shade rotation."),
            (17, "Cooling begins; the sea breeze helps coastal barangays first."),
        ],
    },
    "heatwave": {
        "title": "2024-type heat wave", "tmax": 37.5, "tmin": 27.0, "rh_day": 58, "rh_night": 80,
        "brownout": False,
        "beats": [
            (6, "Already 27°C at dawn — the night gave no relief."),
            (9, "Heat index 40°C+. DepEd heat protocol: shorten classes, move to shade."),
            (11, "DANGER band. Classes suspended; outdoor work paused until 15:00."),
            (13, "Peak ~46°C heat index in dense urban barangays. Heat stroke risk is real, not theoretical."),
            (15, "Still in DANGER. Barangay health workers check the elderly who live alone."),
            (18, "Relief only after sunset. The next day starts hotter than this one did."),
        ],
    },
    "heatwave_brownout": {
        "title": "Heat wave + brownout (no fans, no cold water)", "tmax": 37.5, "tmin": 27.0,
        "rh_day": 58, "rh_night": 80, "brownout": True,
        "beats": [
            (6, "Rotating brownout announced for 10:00–16:00. The same heat wave — minus every electric fan."),
            (9, "Indoor temperatures climb with the sun; corrugated-roof homes become ovens."),
            (11, "Power cut. Refrigerators warm, ice sells out, water stations close pumps."),
            (13, "Peak. Indoors is now worse than shade outdoors. Infants and elderly most at risk."),
            (15, "Cooling centers (schools, churches with generators) are the only refuge — are they open?"),
            (18, "Power returns. The city needs cooling-center plans the way it has evacuation plans."),
        ],
    },
}

HOURS = 40
N_FRAMES = 20


# ----------------------------------------------------------------------------- flood physics (proxy)
def flood_plan(L, story):
    """Returns per-frame hour, water level, pop in water, pop evacuated, narration.

    Water-level convention matches the Simulator: base(share) + tide; factors add/subtract on top.
    The pre-storm stage is below land (`DRY`) so the film starts dry and recedes to dry.
    """
    DRY = -0.35
    base_W = L.water_level_for_share(story["share"])
    tide = story["tide"]
    clog_add = 0.45 * story["clog"]
    pump_cut = 0.22 if story["pumps"] else 0.0
    tau = 16.0 + 32.0 * story["clog"]
    peak = base_W + tide + clog_add - pump_cut
    rise_h = 10.0
    hours = np.linspace(0, HOURS, N_FRAMES)
    beats = story["beats"]
    frames = []
    for h in hours:
        W = kit.curve_W(peak, DRY, h, rise_h=rise_h, tau=tau)
        if story["surge"] > 0 and h >= 10:
            W += story["surge"] * np.exp(-((h - 13.0) ** 2) / 18.0)
        depth, _ = L.depth_grid(W)
        inwater = depth > 0.15
        pop_in = float(L.pop_psa[inwater & L.land_mask].sum())
        if story["warning_h"] > 0:
            start = rise_h - story["warning_h"]
            evac_frac = float(np.clip((h - start) / max(story["warning_h"], 1), 0, 1)) * 0.88
        else:
            evac_frac = float(np.clip((h - 7.0) / 10.0, 0, 1)) * 0.35
        evacuated = pop_in * evac_frac
        bl = int((L.bldg_elev < W - 0.15).sum())
        text = beats[0][1]
        for bh, t in beats:
            if h >= bh:
                text = t
        frames.append(dict(hour=float(h), W=float(W), pop_in=pop_in, evacuated=evacuated,
                           stranded=pop_in - evacuated, bldg=bl, text=text))
    return frames


def custom_story(share, tide, clog, pumps, warning_h, surge):
    base = FLOOD_STORIES["prepared"] if warning_h >= 6 else FLOOD_STORIES["unprepared"]
    s = dict(base)
    s.update(share=share, tide=tide, clog=clog, pumps=pumps, warning_h=warning_h, surge=surge,
             title="Your scenario")
    return s


def heat_plan(L, story):
    hours = np.arange(5, 21)
    tmax, tmin = story["tmax"], story["tmin"]
    out = []
    stress = 0.0
    beats = story["beats"]
    for h in hours:
        phase = np.cos((h - 14.5) / 24.0 * 2 * np.pi)
        t = tmin + (tmax - tmin) * (phase + 1) / 2
        rh = story["rh_night"] + (story["rh_day"] - story["rh_night"]) * (phase + 1) / 2
        hi = kit_hi(t, rh)
        if story["brownout"] and 10 <= h <= 16:
            hi_indoor = hi + 3.0
        else:
            hi_indoor = hi - 1.5
        if hi >= 41:
            stress += 1.0
        elif hi >= 33:
            stress += 0.4
        text = beats[0][1]
        for bh, tx in beats:
            if h >= bh:
                text = tx
        out.append(dict(hour=int(h), t=float(t), rh=float(rh), hi=float(hi), hi_indoor=float(hi_indoor),
                        stress=float(stress), text=text))
    return out


def kit_hi(t, rh):
    import data_core as dc
    return float(dc.hi_c(t, rh)) if t >= 26 else float(t)


def _hi_color(hi):
    if hi < 27:
        return "#94a3b8"
    if hi <= 32:
        return "#fde047"
    if hi <= 41:
        return "#fb923c"
    if hi <= 51:
        return "#ef4444"
    return "#be123c"


def heat_chart(L, story, theme_text="#1f2937", grid="#e5e7eb", height=360):
    """Hour-by-hour heat index with PAGASA bands, indoor line and protocol captions."""
    plan = heat_plan(L, story)
    hrs = [f["hour"] for f in plan]
    hi = [f["hi"] for f in plan]
    hin = [f["hi_indoor"] for f in plan]
    fig = go.Figure()
    bands = [(20, 27, "#f1f5f9", "No caution"), (27, 33, "#fef9c3", "Caution"),
             (33, 42, "#fed7aa", "Extreme caution"), (42, 52, "#fecaca", "DANGER"), (52, 60, "#fda4af", "Extreme danger")]
    for y0, y1, c, lab in bands:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=c, opacity=0.55, line_width=0,
                      annotation_text=lab, annotation_position="left", annotation_font_size=10)
    fig.add_trace(go.Scatter(x=hrs, y=hin, mode="lines", name="indoors" + (" (brownout)" if story["brownout"] else ""),
                             line=dict(color="#7c3aed", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=hrs, y=hi, mode="lines+markers", name="heat index (shade)",
                             line=dict(color="#dc2626", width=3.5),
                             marker=dict(size=8, color=[_hi_color(v) for v in hi], line=dict(width=1, color="white")),
                             customdata=[f["text"] for f in plan],
                             hovertemplate="%{x}:00 · HI %{y:.0f}°C<br>%{customdata}<extra></extra>"))
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=theme_text, size=12),
                      legend=dict(orientation="h", y=1.08, x=0), hovermode="x unified",
                      xaxis=dict(title="hour of day", dtick=2, gridcolor=grid, range=[5, 20]),
                      yaxis=dict(title="heat index °C", range=[22, 58], gridcolor=grid))
    return fig, plan


def heat_barangay_points(L, hi_city):
    """Per-barangay felt heat index at a given city-wide HI, using an urban-heat offset."""
    anc = {b["barangay"]: b["anchor"] for b in L.brgy_anchors}
    dens = L.brgy["bldg_600m"].fillna(0).astype(float) if "bldg_600m" in L.brgy else None
    dmax = max(float(dens.max()), 1.0) if dens is not None else 1.0
    out = []
    for i, row in L.brgy.iterrows():
        a = anc.get(row["barangay"])
        if a is None:
            continue
        urban = str(row.get("urban", "")).strip().upper() == "U"
        uhi = (1.2 if urban else 0.2) + (1.6 * float(dens[i]) / dmax if dens is not None else 0.0)
        out.append(dict(name=row["barangay"], lat=a["lat"], lon=a["lon"], hi=hi_city + uhi, pop=int(row["popn"]),
                        color=_hi_color(hi_city + uhi)))
    return out

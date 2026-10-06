"""Historical storm replay: drive the flood model with the real daily rainfall record (NASA POWER, 1981–2026).

Model (transparent, calibrated — not a hydraulic forecast):
  storage S_d = S_{d-1}·exp(-1/τ) + rain_d          τ = 6 days (Dagupan water sits for a week)
  flooded share of land = piecewise-linear in S through calibration anchors:
      S ≤ 120 mm → 0 %  ·  Aug 2026 habagat peak → 45 % (Calamity class, CDRRMO SitRep 15)
      Pepeng Oct 2009 peak → 65 % (Extreme class)  ·  capped at 80 %
  water level = level that floods that share (+0.20 m tide), ± city-readiness adjustments.
Daily rain is spread across each day (no hourly record); NASA POWER is a ~50 km reanalysis grid, not a station.
"""
import numpy as np
import pandas as pd

TAU_DAYS = 6.0
ONSET_MM = 120.0
TIDE_M = 0.0        # calibration events already include their real tides — don't add more
DRY = -0.35         # pre-storm (and post-storm) stage: below all land, so films start and end dry
CAP_SHARE = 80.0
STEP_H = 6

EVENTS = {
    "pepeng_2009": dict(label="Typhoon Pepeng (Parma) · Oct 2009", start="2009-10-01", end="2009-10-16",
                        note="The record: 253 mm on Oct 8 and 469 mm in 3 days. Calibration anchor for the Extreme class."),
    "habagat_2026": dict(label="Habagat · Aug 2026 (state of calamity)", start="2026-08-01", end="2026-09-05",
                         note="847 mm over three weeks. Rain peaked Aug 6–10 and stored water stayed high to ~Aug 20, "
                              "then a second wave hit Aug 28–30; the state of calamity followed weeks of sustained "
                              "flooding (23/31 barangays, 90,015 residents — CDRRMO SitRep 15). Calibration anchor for "
                              "the Calamity class."),
    "egay_2023": dict(label="Typhoon Egay (Doksuri) · Jul 2023", start="2023-07-20", end="2023-08-06",
                      note="507 mm across the event; enhanced habagat after Egay."),
    "juan_2010": dict(label="Typhoon Juan (Megi) · Oct 2010", start="2010-10-14", end="2010-10-28",
                      note="339 mm in 3 days around Oct 18–20."),
    "aug_2004": dict(label="Monsoon rains · Aug 2004", start="2004-08-18", end="2004-09-03",
                     note="459 mm in 3 days ending Aug 26 — second-wettest 3-day spell in the record."),
}
READINESS = {
    "as_happened": dict(label="As it happened", clog=0.0, pumps=False, warning_h=0,
                        note="Model calibrated to these conditions."),
    "prepared": dict(label="If the city had prepared", clog=-0.10, pumps=True, warning_h=12,
                     note="Drains cleared beforehand (−0.10 m), pumps staged at outfalls (−0.12 m), "
                          "12 h evacuation head start. Illustrative assumptions, not engineering estimates."),
}
PUMP_M = 0.12


_CACHE = {}


def storage(L):
    if id(L) not in _CACHE:
        rain = L.daily["RAIN"].fillna(0.0)
        k = np.exp(-1.0 / TAU_DAYS)
        S = np.zeros(len(rain))
        for i, r in enumerate(rain.values):
            S[i] = (S[i - 1] * k if i else 0.0) + r
        _CACHE[id(L)] = pd.Series(S, index=rain.index)
    return _CACHE[id(L)]


def anchors(L):
    S = storage(L)
    s_cal = float(S[EVENTS["habagat_2026"]["start"]:EVENTS["habagat_2026"]["end"]].max())
    s_ext = float(S[EVENTS["pepeng_2009"]["start"]:EVENTS["pepeng_2009"]["end"]].max())
    return [(0.0, 0.0), (ONSET_MM, 0.0), (s_cal, 45.0), (s_ext, 65.0)]


def share_from_storage(L, s):
    a = anchors(L)
    xs, ys = [p[0] for p in a], [p[1] for p in a]
    if s <= xs[-1]:
        return float(np.interp(s, xs, ys))
    slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
    return float(min(CAP_SHARE, ys[-1] + slope * (s - xs[-1])))


def build_story(L, key, readiness="as_happened"):
    ev, rd = EVENTS[key], READINESS[readiness]
    rain = L.daily["RAIN"].fillna(0.0)[ev["start"]:ev["end"]]
    S = storage(L)[ev["start"]:ev["end"]]
    days = list(S.index)
    # value at local noon of each day, linearly interpolated across hours
    t_day = np.array([i * 24 + 12 for i in range(len(days))], dtype=float)
    hours = np.arange(0, len(days) * 24 + 1, STEP_H, dtype=float)
    S_h = np.interp(hours, t_day, S.values)
    adj = rd["clog"] - (PUMP_M if rd["pumps"] else 0.0)
    W = []
    for s in S_h:
        sh = share_from_storage(L, s)
        # Floor at the dry stage: tiny shares sit in the raw DEM's negative sliver (down to −2 m),
        # which would read as "water at −1.8 m" — nonsense. The scripted branch floors the same way.
        W.append(max((L.water_level_for_share(sh) if sh > 0 else DRY) + TIDE_M + adj, DRY))
    W = np.array(W)
    beats, labels = [], []
    for i, d in enumerate(days):
        r = float(rain.iloc[i])
        cls = ("intense" if r >= 100 else "heavy" if r >= 50 else "moderate" if r >= 15 else "light" if r >= 2 else "dry")
        beats.append((i * 24, f"{d:%a %b %d, %Y} — {r:.0f} mm of rain ({cls}); water stored in the city: {S.iloc[i]:.0f} mm."))
    for h in hours:
        d = days[min(int(h // 24), len(days) - 1)]
        labels.append(f"{d:%b %d} {int(h % 24):02d}:00")
    peak_h = float(hours[int(np.argmax(W))])
    return dict(title=f"{ev['label']} — {rd['label'].lower()}", replay=True, key=key, readiness=readiness,
                hours=hours.tolist(), W_series=W.tolist(), labels=labels, beats=beats, peak_h=peak_h,
                warning_h=rd["warning_h"], tide=TIDE_M, clog=max(0.0, 0.6 + rd["clog"]), pumps=rd["pumps"],
                share=None, surge=0.0, daily_rain=[(f"{d:%b %d}", float(rain.iloc[i])) for i, d in enumerate(days)],
                note=ev["note"])


def water_at(story, h):
    return float(np.interp(h, story["hours"], story["W_series"]))

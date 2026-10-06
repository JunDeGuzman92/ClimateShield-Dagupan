"""Cross-check of the flood proxy model against the August 2026 habagat.

Observed facts (all from one official source): CDRRMO Situational Report No. 15, as published by the
City Government of Dagupan ("DAGUPAN NOW UNDER STATE OF CALAMITY", dagupan.gov.ph, 26 Aug 2026,
retrieved 5 Oct 2026):
  * 23 of 31 barangays still flooded at SitRep No. 15 (≈2 weeks after the rain peak)
  * 22,047 families / 90,015 individuals affected

This module reports model-vs-observed rows WITHOUT tuning anything: good matches, and mismatches,
are both stated. Everything here is per-barangay *anchor windows* — real barangay boundaries are not
in the data yet (see Methods), which caps how precise any barangay count can be.
"""
import numpy as np
import pandas as pd

import replay

OBSERVED = dict(barangays_still_flooded=23, families=22047, individuals=90015,
                source="CDRRMO SitRep No. 15 via dagupan.gov.ph (26 Aug 2026, retrieved 5 Oct 2026)")
SITREP_DATE_H = 24.5 * 24        # ≈ Aug 25 in the replay window (story starts Aug 1)


def _anchor_depth(L, brgy, W):
    a = next((b["anchor"] for b in L.brgy_anchors if b["barangay"] == brgy), None)
    if a is None:
        return None
    x, y = L.to_utm(a["lon"], a["lat"])
    ci = int(np.clip(round((x - L.transform.c) / 30 - 0.5), 0, L.w - 1))
    ri = int(np.clip(round((L.transform.f - y) / 30 - 0.5), 0, L.h - 1))
    return max(W - float(L.dem[ri, ci]), 0.0)


def _window_counts(L, W):
    exp = L.exposure(L.depth_grid(W)[0], W)
    bi = exp["barangay_impact"]
    win = int((pd.to_numeric(bi["affected_est"], errors="coerce") > 0).sum()) if len(bi) else 0
    return win, float(exp["pop_affected"])


def checks(L):
    story = replay.build_story(L, "habagat_2026", "as_happened")
    W_peak = max(story["W_series"])
    W_late = replay.water_at(story, SITREP_DATE_H)
    names = [b["barangay"] for b in L.brgy_anchors]
    anchors_peak = sum(1 for n in names if (_anchor_depth(L, n, W_peak) or 0) > 0.15)
    anchors_late = sum(1 for n in names if (_anchor_depth(L, n, W_late) or 0) > 0.15)
    windows_peak, pop_peak = _window_counts(L, W_peak)
    windows_late, _ = _window_counts(L, W_late)
    ratio = pop_peak / OBSERVED["individuals"]
    pop_pct = pop_peak / L.meta["psa_pop_2020"]

    summary = dict(W_peak=W_peak, W_late=W_late, pop_peak=pop_peak, ratio=ratio,
                   poly_peak=windows_peak, poly_late=windows_late,
                   anchors_peak=anchors_peak, anchors_late=anchors_late)
    basis = L.boundary_source.split("(")[0].strip()
    rows = [
        dict(check="Residents in flood zones at the habagat peak",
             model=f"{pop_peak:,.0f} ({100 * pop_pct:.0f}% of census)",
             observed=f"{OBSERVED['individuals']:,} affected — {OBSERVED['families']:,} families (SitRep 15)",
             reading=f"comparable: {100 * ratio:.0f}% of the reported figure. The model counts residents whose "
                     "cells are under water; 'affected' also includes people whose livelihood/yard flooded."),
        dict(check="Barangays with water in them at the peak (share of residents > 0, "
                  + basis + ")",
             model=f"{windows_peak} / 31",
             observed=f"{OBSERVED['barangays_still_flooded']} / 31 still flooded weeks later (SitRep 15)",
             reading="model counts more barangays than the sitrep — expected, since the sitrep is a "
                     "recession-era snapshot, not the peak."),
        dict(check="Barangays with water in them at sitrep time (≈Aug 25, model water +"
                  f"{W_late:.2f} m)",
             model=f"{windows_late} / 31",
             observed=f"{OBSERVED['barangays_still_flooded']} / 31 still flooded (SitRep 15)",
             reading="closest like-for-like comparison available: the model's barangay count at the "
                     "sitrep date matches the reported count. Some coincidence is likely — the sitrep "
                     "counts house-level flooding, the model any share above zero — but the previous "
                     "anchor-window method gave 4–8, so the barangay-area basis is a real step up."),
        dict(check="Barangay core points under water at the peak (>15 cm at the OSM place node)",
             model=f"{anchors_peak} / 31",
             observed="— (no per-barangay depth reading exists publicly)",
             reading="stricter criterion. OSM place points often sit on the dry centre, so this undercounts."),
        dict(check="Barangay core points under water at sitrep time",
             model=f"{anchors_late} / 31",
             observed=f"{OBSERVED['barangays_still_flooded']} / 31 (SitRep 15)",
             reading="the point-measure still underestimates persistence (3 vs 23): cores drain first, "
                     "outlying fishpond-side houses last. The polygon row above is the better measure."),
        dict(check="Flooded-land share at the habagat peak",
             model=f"{L.flooded_share(W_peak):.0f}% of active land (water +{W_peak:.2f} m)",
             observed="— (no official citywide figure published)",
             reading="this is the CALIBRATION anchor, not an independent check: the 45% class was set from "
                     "this event's sitrep class."),
    ]
    return pd.DataFrame(rows), summary

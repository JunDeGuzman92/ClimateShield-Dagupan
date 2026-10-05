import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from affine import Affine
from geo import Transformer

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "data" / "app_layers"
PROC = ROOT / "data" / "processed"

FAC_COLORS = {"school": "#4da3ff", "health": "#ff5d5d", "civic_protective": "#ffc93c", "worship": "#c39bff"}
FLOOD_DEPTH_M = 0.15       # a cell counts as flooded when water is deeper than this
PLATEAU_SPREAD_M = 0.5     # 0 m plateau cells are spread over 0 … this, ordered by susceptibility

_alias = {
    "bonuan binloc": ["binloc"], "bonuan boquig": ["boquig"], "bonuan gueset": ["gueset"],
    "pogo chico": ["pogo chico"], "pogo grande": ["pogo grande"], "lasip chico": ["lasip chico"],
    "lasip grande": ["lasip grande"], "bacayao norte": ["bacayao norte"], "bacayao sur": ["bacayao sur"],
    "barangay i (t. bugallon)": ["bugallon"], "barangay ii (nueva)": ["nueva"],
    "barangay iv (zamora)": ["zamora"], "pugaro suit": ["pugaro"], "poblacion oeste": ["oeste"],
    "mamalingling": ["mamalingling"], "salapingao": ["salapingao"],
}

def _norm(s):
    s = str(s).lower().strip()
    for tok in ["barangay", "brgy.", "brgy", "district", "poblacion"]:
        s = s.replace(tok, "")
    return " ".join(s.split())


class Layers:
    def __init__(self):
        self.meta = json.load(open(LAYERS / "grid_meta.json"))
        t = self.meta["utm_transform"]
        self.transform = Affine(t[0], t[1], t[2], t[3], t[4], t[5])
        self.crs = self.meta["crs"]
        self.h, self.w = self.meta["height"], self.meta["width"]
        self.dem = np.load(LAYERS / "dem_utm.npy")
        self.susc = np.load(LAYERS / "susc.npy")
        self.land_mask = np.load(LAYERS / "land_mask.npy").astype(bool)
        self.dist_river = np.load(LAYERS / "dist_river.npy")
        self.dist_coast = np.load(LAYERS / "dist_coast.npy")
        self.pop = np.load(LAYERS / "pop_utm.npy")
        self.hillshade = np.load(LAYERS / "hillshade.npy")
        self.basemap = np.load(LAYERS / "basemap_utm.npy")
        cal = np.load(LAYERS / "elev_calibration.npz")
        self.elev_sorted = cal["sorted"]
        self.daily = pd.read_csv(LAYERS / "daily.csv", parse_dates=["date"]).set_index("date")
        self.daily["MONTH"] = self.daily.index.month
        self.brgy = pd.read_csv(LAYERS / "barangay_table.csv")
        self.roads = pickle.load(open(LAYERS / "roads.pkl", "rb"))
        self.facilities = pickle.load(open(LAYERS / "facilities.pkl", "rb"))
        self.buildings = pickle.load(open(LAYERS / "buildings.pkl", "rb"))
        self.places = pickle.load(open(LAYERS / "places.pkl", "rb"))
        self.rivers = pickle.load(open(LAYERS / "rivers.pkl", "rb"))
        self.coast = pickle.load(open(LAYERS / "coast.pkl", "rb"))

        city_pop = self.pop[self.land_mask].sum()
        self.pop_psa = self.pop * (self.meta["psa_pop_2020"] / city_pop)
        self.bldg_elev = np.array([b["elev_m"] for b in self.buildings])
        self.fac_df = pd.DataFrame(self.facilities)
        self.road_len_km = sum(r["length_m"] for r in self.roads) / 1000.0
        self.to_utm = Transformer.from_crs("EPSG:4326", self.crs, always_xy=True).transform

        def cell_of(lon, lat):
            x, y = self.to_utm(lon, lat)
            ci = int(np.clip(round((x - self.transform.c) / 30 - 0.5), 0, self.w - 1))
            ri = int(np.clip(round((self.transform.f - y) / 30 - 0.5), 0, self.h - 1))
            return ri, ci

        self.bldg_cells = np.array([cell_of(b["lon"], b["lat"]) for b in self.buildings])
        self.fac_cells = np.array([cell_of(f["lon"], f["lat"]) for f in self.facilities])
        self.road_cells = []
        for r in self.roads:
            xs, ys = self.to_utm(*np.array(r["ll"]).T)
            cis = np.clip(np.round((xs - self.transform.c) / 30 - 0.5), 0, self.w - 1).astype(int)
            ris = np.clip(np.round((self.transform.f - ys) / 30 - 0.5), 0, self.h - 1).astype(int)
            self.road_cells.append((ris, cis))

        self.brgy_anchors = []
        places = [p for p in self.places if p["name"]]
        for _, row in self.brgy.iterrows():
            keys = [_norm(row["barangay"])] + _alias.get(str(row["barangay"]).lower(), [])
            hit = None
            for k in keys:
                if not k:
                    continue
                cands = [p for p in places if k in _norm(p["name"])]
                if cands:
                    hit = cands[0]
                    break
            self.brgy_anchors.append({"barangay": row["barangay"], "anchor": hit,
                                      "census": int(row["popn"]),
                                      "urban": str(row["urban"]).strip().upper() == "U",
                                      "csri": row["CSRI"] if "CSRI" in row and pd.notna(row.get("CSRI")) else None})

        # ---- optional better elevation model (see demimport.py)
        self.dem_source = "Copernicus GLO-30 (30 m DSM)"
        ov = LAYERS / "dem_override.npy"
        if ov.exists():
            try:
                d2 = np.load(ov)
                if d2.shape == self.dem.shape:
                    self.dem = d2
                    rep = LAYERS / "dem_override.json"
                    lab = json.load(open(rep)).get("label", "imported DTM") if rep.exists() else "imported DTM"
                    self.dem_source = f"{lab} merged over GLO-30"
                    self.elev_sorted = np.sort(self.dem[self.land_mask & np.isfinite(self.dem)])
                    self.bldg_elev = self.dem[self.bldg_cells[:, 0], self.bldg_cells[:, 1]].astype(float)
                    for f, (ri, ci) in zip(self.facilities, self.fac_cells):
                        f["elev_m"] = float(self.dem[ri, ci])
                    for b, bc in zip(self.buildings, self.bldg_cells):
                        b["elev_m"] = float(self.dem[bc[0], bc[1]])
            except Exception:
                self.dem_source = "Copernicus GLO-30 (override file unreadable — ignored)"

        # ---- 0 m plateau tie-break (documented modelling assumption; see Methods page)
        # GLO-30 flattens Dagupan's fishpond/wetland belt to exactly 0 m, so a share-of-land flood target cannot
        # tell those cells apart. Within that plateau we order cells by the project's flood-susceptibility index
        # (most susceptible floods first) and spread them over 0 … PLATEAU_SPREAD_M. Real elevations are untouched.
        plateau = self.land_mask & (np.abs(self.dem) < 1e-6)
        self.plateau_share = float(plateau.sum() / max(self.land_mask.sum(), 1))
        if plateau.any():
            s = np.nan_to_num(self.susc[plateau], nan=float(np.nanmedian(self.susc)))
            order = np.argsort(np.argsort(-s, kind="stable"), kind="stable")   # 0 = most susceptible
            dem2 = self.dem.astype("float64").copy()
            dem2[plateau] = PLATEAU_SPREAD_M * order / max(len(order) - 1, 1)
            self.dem = dem2.astype("float32")
            self.elev_sorted = np.sort(self.dem[self.land_mask & np.isfinite(self.dem)])
            self.bldg_elev = self.dem[self.bldg_cells[:, 0], self.bldg_cells[:, 1]].astype(float)
            for f, (ri, ci) in zip(self.facilities, self.fac_cells):
                f["elev_m"] = float(self.dem[ri, ci])
            for b, bc in zip(self.buildings, self.bldg_cells):
                b["elev_m"] = float(self.dem[bc[0], bc[1]])

    def water_level_for_share(self, share_pct):
        """Water level at which `share_pct` % of active land is flooded deeper than FLOOD_DEPTH_M."""
        return float(np.percentile(self.elev_sorted, share_pct)) + FLOOD_DEPTH_M

    def flooded_share(self, W):
        """Inverse of water_level_for_share: % of active land deeper than FLOOD_DEPTH_M at water level W."""
        return 100.0 * float(np.searchsorted(self.elev_sorted, W - FLOOD_DEPTH_M) / len(self.elev_sorted))

    def depth_grid(self, W, dredge_m=0.0, drainage_m=0.0):
        W_eff = W
        if drainage_m > 0:
            W_eff = W_eff - drainage_m
        if dredge_m > 0:
            W_eff = W_eff - dredge_m * np.exp(-self.dist_river / 600.0)
        depth = np.maximum(W_eff - self.dem, 0.0)
        depth[~self.land_mask] = np.nan
        return np.where(np.isnan(depth), 0.0, depth), W_eff

    def exposure(self, depth, label_m=None):
        flooded = depth > 0.15
        pop_affected = float(self.pop_psa[flooded & self.land_mask].sum())

        bd = depth[self.bldg_cells[:, 0], self.bldg_cells[:, 1]]
        bldg_flooded = int((bd > 0.15).sum())

        fd = depth[self.fac_cells[:, 0], self.fac_cells[:, 1]]
        fac_flooded_mask = fd > 0.15
        fac_counts = self.fac_df.loc[fac_flooded_mask, "category"].value_counts().to_dict()
        fac_flooded_total = int(fac_flooded_mask.sum())

        cut_km = 0.0
        roads_cut = []
        for r, (ris, cis) in zip(self.roads, self.road_cells):
            vd = depth[ris, cis]
            vd = vd[np.isfinite(vd)]
            if len(vd) == 0:
                continue
            frac = float((vd > 0.30).mean())
            if frac > 0:
                km = r["length_m"] / 1000.0
                cut_km += km if frac >= 0.999 else km * frac
                if frac >= 0.25:
                    roads_cut.append({"name": r["name"] or r["class"], "class": r["class"],
                                      "km": km, "frac": frac})

        rows = []
        for b in self.brgy_anchors:
            a = b["anchor"]
            est = None
            if a is not None:
                x, y = self.to_utm(a["lon"], a["lat"])
                col = (x - self.transform.c) / 30 - 0.5
                rowi = (self.transform.f - y) / 30 - 0.5
                ri, ci = int(np.clip(round(rowi), 0, self.h - 1)), int(np.clip(round(col), 0, self.w - 1))
                r0, r1 = max(0, ri - 10), min(self.h, ri + 11)
                c0, c1 = max(0, ci - 10), min(self.w, ci + 11)
                win = depth[r0:r1, c0:c1]
                win_land = self.land_mask[r0:r1, c0:c1]
                if win_land.any():
                    fr = float((win[win_land] > 0.15).mean())
                    est = int(round(fr * b["census"]))
            rows.append({"barangay": b["barangay"], "census": b["census"], "affected_est": est,
                         "anchor": bool(a is not None)})
        impact = pd.DataFrame(rows).sort_values("affected_est", ascending=False, na_position="last")

        area_km2 = float((flooded & self.land_mask).sum()) * 0.0009
        return {
            "water_level_m": float(label_m) if label_m is not None else float("nan"),
            "pop_affected": pop_affected,
            "pop_total": float(self.meta["psa_pop_2020"]),
            "bldg_flooded": bldg_flooded, "bldg_total": self.meta["n_buildings"],
            "fac_counts": fac_counts, "fac_flooded_total": fac_flooded_total,
            "fac_total": self.meta["n_facilities"],
            "road_km_cut": cut_km, "road_km_total": self.road_len_km,
            "roads_cut_worst": sorted(roads_cut, key=lambda r: -r["km"])[:12],
            "barangay_impact": impact, "area_flooded_km2": area_km2,
        }


SCENARIOS = {
    "PAGASA Advisory-level (localized flooding)": 12,
    "PAGASA Alert-level (widespread threat)": 30,
    "Calamity-class (Aug 2026-type event)": 45,
    "Extreme (Oct 2009-type: 469 mm in 3 days)": 65,
}


def live_weather():
    import urllib.request
    url = ("https://api.open-meteo.com/v1/forecast?latitude=16.0432&longitude=120.3342"
           "&current=temperature_2m,relative_humidity_2m,precipitation,apparent_temperature,weather_code"
           "&hourly=temperature_2m,relative_humidity_2m,precipitation,precipitation_probability"
           "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
           "&forecast_days=7&past_days=1&timezone=Asia%2FManila")
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def hi_c(t, rh):
    tf = t * 9 / 5 + 32
    return ((-42.379 + 2.04901523 * tf + 10.14333127 * rh - 0.22475541 * tf * rh
             - 6.83783e-3 * tf ** 2 - 5.481717e-2 * rh ** 2 + 1.22874e-3 * tf ** 2 * rh
             + 8.5282e-4 * tf * rh ** 2 - 1.99e-6 * tf ** 2 * rh ** 2) - 32) * 5 / 9


def hi_category(hi):
    if hi < 27:
        return ("No Caution", "#9aa5b1", "#0e1117")
    if hi <= 32:
        return ("Caution", "#ffe699", "#1a1c22")
    if hi <= 41:
        return ("Extreme Caution", "#f6b26b", "#241d15")
    if hi <= 51:
        return ("DANGER", "#e06666", "#2a1414")
    return ("EXTREME DANGER", "#ff4d6d", "#38101c")


def action_card_flood(brgy_row, water_level, affected_est, trigger_class):
    lines = [
        f"CLIMATESHIELD ADVISORY - {str(brgy_row['barangay']).upper()} (flood trigger: {trigger_class})",
        "",
        f"Estimated residents in flood zones right now: {affected_est if affected_est is not None else 'n/a (no spatial anchor)'} / {int(brgy_row['popn']):,} census population",
        f"Scenario water level: +{water_level:.2f} m above sea datum",
        "",
        "KAPIT-BAHAYAN ACTIONS (works even before LGU aid arrives):",
        "1. Move vehicles, bangus harvest, feed sacks to above +1 m ground NOW",
        "2. Charge phones/power banks; fill containers with clean water",
        "3. Check on households on your elderly/PWD/buntis list - assign a buddy",
        "4. Ready banca or pickups for the sick, elderly, small children",
        "5. Clear drainage inlets along your street before the peak",
        "",
        "BARANGAY RESPONSE DESK:",
        "- Activate evacuation center roster (nearest school/townhall/church)",
        "- Monitor Pantal River bulletins; Alert(40%)/Alarm(60%)/Critical(100%) protocol",
        "- Post crowd depth reports to ClimateShield so neighbors see the real map",
    ]
    return "\n".join(lines)


def action_card_heat(brgy_row, hi_value, category):
    lines = [
        f"CLIMATESHIELD HEAT BULLETIN - {str(brgy_row['barangay']).upper()} (heat index {category})",
        "",
        f"Heat index: {hi_value:.0f} C",
        "",
        f"Residents: {int(brgy_row['popn']):,} (census 2020)",
        "",
        "COMMUNITY ACTIONS:",
        "1. Reschedule outdoor work/sports before 10am or after 4pm",
        "2. Open sari-sari water stations and shaded rest points (tarp + benches)",
        "3. Buddy-check elderly, PWD, buntis, and bangus-pond workers hourly",
        "4. Watch for heat cramps/exhaustion: shade, elevate legs, sip water,",
        "   cool packs on armpits/wrists/ankles/groin; hospital if confusion/vomiting",
        "5. Schools: suspend or shift to early-morning classes per DepEd guidance",
    ]
    return "\n".join(lines)

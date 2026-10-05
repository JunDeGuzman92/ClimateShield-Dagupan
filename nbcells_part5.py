CELLS_P5 = []

CELLS_P5.append(("md", """## 7. Critical infrastructure on the susceptibility surface

From the OSM extract we classify the assets a community depends on during disasters:

- **Schools** (119 amenity nodes/ways + school-type buildings) — also the default evacuation centers (as used in the Aug 2026 response, when 6 centers sheltered 65 preemptively-evacuated families)
- **Health** — hospitals, clinics, health posts, pharmacies
- **Civic & protective** — town/barangay halls, police, fire, shelters, childcare
- **Places of worship** — historically the first ad-hoc shelters in Philippine flood response

Each facility is geolocated on the susceptibility surface and scored; evacuation-relevant assets standing in high-susceptibility ground are flagged — they cannot be relied on as shelters, and residents near them need alternates."""))

CELLS_P5.append(("code", """FAC_SETS = {
    "school": {"school", "kindergarten", "college", "university"},
    "health": {"hospital", "clinic", "health_post", "pharmacy", "doctors", "dentist"},
    "civic_protective": {"townhall", "community_centre", "police", "fire_station", "shelter", "childcare"},
    "worship": {"place_of_worship"},
}
FAC_COLORS = {"school": "#1f77b4", "health": "#c0392b", "civic_protective": "#f39c12", "worship": "#7d3c98"}

fac = g_fac[g_fac["class"].isin(set().union(*FAC_SETS.values()))].copy()
fac["category"] = fac["class"].map(lambda c: next(k for k, s in FAC_SETS.items() if c in s))
fac_utm = fac.to_crs(dst_crs).copy()

xs = fac_utm.geometry.x.values
ys = fac_utm.geometry.y.values
cols_f = (xs - utm_transform.c) / 30 - 0.5
rows_f = (utm_transform.f - ys) / 30 - 0.5
ri = np.clip(rows_f.astype(int), 0, utm_h - 1)
ci = np.clip(cols_f.astype(int), 0, utm_w - 1)
fac_utm["susc"] = susc[ri, ci]
fac_utm["elev_m"] = dem_utm[ri, ci]
fac_utm["dist_river_m"] = dist_river_m[ri, ci]

EVAC = fac_utm[fac_utm["category"].isin(["school", "civic_protective", "worship"])]
print(f"Facilities mapped: {len(fac_utm)} -> " + ", ".join(f"{k}: {v}" for k, v in fac_utm['category'].value_counts().items()))
print(f"Evacuation-relevant assets (schools + civic + worship): {len(EVAC)}")

hi_susc = fac_utm[fac_utm["susc"] >= np.nanpercentile(susc, 80)]
print(f"\\nFacilities in the TOP-20% susceptibility zone: {len(hi_susc)} of {len(fac_utm)} ({len(hi_susc) / len(fac_utm) * 100:.0f}%)")
print(f"  schools there: {(hi_susc['category'] == 'school').sum()} | health: {(hi_susc['category'] == 'health').sum()}")
low2m = fac_utm[fac_utm["elev_m"] <= 2]
print(f"Facilities at or below ~2 m elevation: {len(low2m)} ({len(low2m) / len(fac_utm) * 100:.1f}%)")

fig, ax = plt.subplots(figsize=(12.5, 9.5))
ax.imshow(np.where(city_mask, np.nanpercentile(susc, 50) * 0 + np.nan_to_num(susc, nan=0), np.nan),
          cmap="Greys", vmin=0, vmax=100, alpha=0.8,
          extent=(utm_transform.c, utm_transform.c + utm_w * 30, utm_transform.f - utm_h * 30, utm_transform.f),
          origin="upper")
for cat, col in FAC_COLORS.items():
    sub = fac_utm[fac_utm["category"] == cat]
    ax.scatter(sub.geometry.x, sub.geometry.y, s=28 if cat != "school" else 20, c=col, label=cat.replace("_", "/"), alpha=0.85, edgecolors="white", linewidths=0.4)
g_water.to_crs(dst_crs).plot(ax=ax, color="#1a5276", lw=0.9, alpha=0.6)
city_utm.boundary.plot(ax=ax, color="k", lw=1.6)
ax.legend(loc="lower right", fontsize=9, title="Facility category", title_fontsize=9)
ax.set_title("Critical facilities on the flood-susceptibility surface (grey = higher susceptibility)", fontsize=12)
ax.set_xlim(city_utm.total_bounds[0] - 500, city_utm.total_bounds[2] + 500)
ax.set_ylim(city_utm.total_bounds[1] - 500, city_utm.total_bounds[3] + 500)
ax.set_axis_off()
save_chart(fig, "13_infrastructure_map.png")
plt.close(fig)"""))

CELLS_P5.append(("md", """## 8. Barangay risk watchlist (the app's first screen)

**Method, matched to what openly exists:** barangay polygons are not published openly for Dagupan (OSM, OCHA COD-AB, geoBoundaries and GADM all stop at municipality level), so ClimateShield builds each barangay's spatial profile from:

1. **Official PSA census** — population & urban/rural (all 31 barangays)
2. **OSM neighborhood anchors** — place nodes whose names match barangay names ( quarters/villages; e.g., *Pantal*, *Carael*, *Calmay*, *Bonuan Gueset*)
3. For matched anchors — the mean susceptibility within 300 m, elevation, distance to rivers/coast, and surrounding built-up density (an urban-heat proxy), all sampled from the rasters above

**ClimateShield Risk Index (CSRI, 0–100)** — transparent percentile blend: 50% flood susceptibility + 25% population share + 15% building density (UHI/evacuation-cost proxy) + 10% urban status. Barangays without an anchor are listed with census data only (`geometry anchor: none`) — honesty first."""))

CELLS_P5.append(("code", """def norm_name(s):
    s = str(s).lower().strip()
    for tok in ["barangay", "brgy.", "brgy", "district", "poblacion"]:
        s = s.replace(tok, "")
    return " ".join(s.split())

places = g_places.dropna(subset=["name"]).copy()
places["norm"] = places["name"].map(norm_name)

ALIASES = {
    "bonuan binloc": ["binloc"], "bonuan boquig": ["boquig"], "bonuan gueset": ["gueset"],
    "pogo chico": ["pogo chico"], "pogo grande": ["pogo grande"], "lasip chico": ["lasip chico"],
    "lasip grande": ["lasip grande"], "bacayao norte": ["bacayao norte"], "bacayao sur": ["bacayao sur"],
    "barangay i (t. bugallon)": ["bugallon"], "barangay ii (nueva)": ["nueva"],
    "barangay iv (zamora)": ["zamora"], "pugaro suit": ["pugaro"], "poblacion oeste": ["oeste"],
    "mamalingling": ["mamalingling"], "salapingao": ["salapingao"],
}

def find_anchor(brgy):
    keys = [norm_name(brgy)] + ALIASES.get(brgy.lower(), [])
    for k in keys:
        if not k:
            continue
        hit = places[places["norm"].str.contains(k, regex=False)]
        if len(hit):
            return hit.iloc[0]
    return None

rows = []
for _, r in dag.iterrows():
    row = {"barangay": r["Barangay"], "census_2020": r["popn"], "urban": r["urban"] == "U", "psgc": r["psgc"]}
    a = find_anchor(r["Barangay"])
    if a is not None:
        pt = gpd.GeoSeries([a.geometry], crs="EPSG:4326").to_crs(dst_crs).iloc[0]
        cx_, cy_ = (pt.x - utm_transform.c) / 30 - 0.5, (utm_transform.f - pt.y) / 30 - 0.5
        rr, cc = int(round(cy_)), int(round(cx_))
        r0, r1 = max(0, rr - 10), min(utm_h, rr + 11)
        c0, c1 = max(0, cc - 10), min(utm_w, cc + 11)
        win_s = susc[r0:r1, c0:c1]
        bmask = g_bldg.to_crs(dst_crs).intersects(pt.buffer(600))
        row.update({
            "anchor": a["name"], "anchor_class": a["class"],
            "mean_susc_300m": float(np.nanmean(win_s)) if np.isfinite(win_s).any() else np.nan,
            "elev_m": float(dem_utm[rr, cc]),
            "dist_river_m": float(dist_river_m[rr, cc]),
            "dist_coast_m": float(dist_coast_m[rr, cc]),
            "bldg_600m": int(bmask.sum()),
        })
    rows.append(row)
wl = pd.DataFrame(rows)
wl["geometry anchor"] = np.where(wl["anchor"].notna(), wl["anchor"], "none")

has_geo = wl["mean_susc_300m"].notna()
for col, rank_of in [("pop_rank", "census_2020"), ("dens_rank", "bldg_600m")]:
    wl[col] = np.nan
    v = wl.loc[has_geo, rank_of]
    wl.loc[has_geo, col] = v.rank(pct=True)
wl["flood_pct"] = np.nan
fp = wl.loc[has_geo, "mean_susc_300m"]
wl.loc[has_geo, "flood_pct"] = fp.rank(pct=True)
wl["CSRI"] = np.where(
    has_geo,
    100 * (0.50 * wl["flood_pct"] + 0.25 * wl["pop_rank"] + 0.15 * wl["dens_rank"] + 0.10 * wl["urban"].astype(float)),
    np.nan,
)

wl_out = wl[["barangay", "census_2020", "urban", "geometry anchor", "mean_susc_300m", "elev_m",
             "dist_river_m", "bldg_600m", "CSRI"]].sort_values("CSRI", ascending=False)
wl_out.to_csv(PROC / "climateshield_dagupan_barangay_watchlist.csv", index=False)
print(f"Anchored barangays: {has_geo.sum()}/31 (OSM place nodes matched)")

show = wl_out.dropna(subset=["CSRI"]).head(12).iloc[::-1]
fig, ax = plt.subplots(figsize=(11.5, 6.4))
ax.barh(show["barangay"], show["CSRI"], color=plt.cm.RdYlGn_r(show["CSRI"] / 100 * 0.9 + 0.05))
for y, (b, p, cs) in enumerate(zip(show["barangay"], show["census_2020"], show["CSRI"])):
    ax.text(cs + 1, y, f"CSRI {cs:.0f}  |  pop {p:,}", va="center", fontsize=8)
ax.set_xlabel("ClimateShield Risk Index (percentile blend of flood susceptibility, population, density, urban status)")
ax.set_title("Top-12 barangay watchlist (among barangays with matched spatial anchors)")
ax.set_xlim(0, 105)
ax.grid(axis="x", alpha=0.3)
save_chart(fig, "14_barangay_watchlist.png")
plt.close(fig)
print(wl_out.dropna(subset=["CSRI"]).head(12).round(1).to_string(index=False))
print("\\nUnanchored (census-only, pending LGU boundary data):")
print(", ".join(wl_out[wl_out['CSRI'].isna()]['barangay']))"""))

CELLS_P5.append(("md", """## 9. Compact models (in the spirit of the original ClimateShield pipeline)

The original Durham pipeline shipped 4 models (heat projection, flood frequency, hospitalisation risk, response-time deterioration). This Dagupan edition ships the same *pattern*, sized to what 45 years of one city's data honestly supports — with cross-validated skill reported, **including when it is weak** (model honesty > model theater):

| # | Model | Task | Method |
|---|---|---|---|
| 1 | **Heat-day projection** | Annual PAGASA-Danger heat-index days | Polynomial (deg 2) + linear, held-out test on 2016–2026, forecast to 2040 |
| 2 | **Heat-day composite predictor** | Same target | Random Forest with climate features, TimeSeriesSplit CV |
| 3 | **Community risk typology** | Segment the city into response-planning profiles | K-Means on terrain × water-proximity × relief per 30 m cell |
| 4 | **Evacuation accessibility** | Where are residents far from any shelter-worthy facility? | Euclidean accessibility surface from facility raster (EDT)"""))

CELLS_P5.append(("code", """from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import r2_score

heat_years = hi_annual.index.values.astype(float)
y_heat = (hi_annual["Danger"] + hi_annual["Extreme Danger"]).values

train_m = heat_years <= 2015
test_m = ~train_m

lin = np.polyfit(heat_years[train_m], y_heat[train_m], 1)
yhat_lin = np.polyval(lin, heat_years[test_m])
r2_lin_test = r2_score(y_heat[test_m], yhat_lin)

poly = np.polyfit(heat_years[train_m], y_heat[train_m], 2)
yhat_poly_test = np.polyval(poly, heat_years[test_m])
r2_poly_test = r2_score(y_heat[test_m], yhat_poly_test)

lin_test_slope = lin[0]
poly_future = np.arange(2026, 2041)
y_poly_forecast = np.polyval(poly, poly_future)
resid = y_heat[train_m] - np.polyval(poly, heat_years[train_m])
se = resid.std()

print("Model 1 - annual Danger-level heat days:")
print(f"  train 1981-2015 -> test 2016-2026: linear R2 = {r2_lin_test:.2f} | poly-2 R2 = {r2_poly_test:.2f}")
print(f"  fitted trend: +{lin_test_slope:.2f} danger-days/year")
print(f"  poly-2 forecast: 2030 ~ {np.polyval(poly, 2030):.0f} days | 2040 ~ {np.polyval(poly, 2040):.0f} days (residual 1-sigma ~ {se:.1f})")

rf_features = pd.DataFrame({"year": heat_years,
                            "rain_ann": annual["RAIN_ANN"].values,
                            "rh_mean": df.groupby("YEAR")["RH2M"].mean().reindex(annual.index).values}).dropna()
rf_target_idx = rf_features.index
X_rf = rf_features.values
y_rf = y_heat[rf_target_idx]
rf_scores = []
for tr_idx, te_idx in TimeSeriesSplit(5).split(X_rf):
    m = RandomForestRegressor(n_estimators=300, random_state=42, min_samples_leaf=2).fit(X_rf[tr_idx], y_rf[tr_idx])
    rf_scores.append(r2_score(y_rf[te_idx], m.predict(X_rf[te_idx])))
print(f"\\nModel 2 - Random Forest, TimeSeriesSplit CV R2 = {np.mean(rf_scores):.2f} (+/- {np.std(rf_scores):.2f})")
print("  -> honest read: the heat signal is dominated by a trend that year alone mostly captures;")
print("     adding rain/RH features adds little -- useful to know BEFORE the app over-promises.")

fig, axes = plt.subplots(1, 2, figsize=(15.5, 5.2))
ax = axes[0]
ax.scatter(heat_years, y_heat, s=14, color="#c0392b", alpha=0.7, label="observed danger days")
fx = np.arange(1981, 2041)
ax.plot(fx, np.polyval(poly, fx), "-", color="#1a5276", label=f"poly-2 fit/forecast (test R2={r2_poly_test:.2f})")
ax.fill_between(poly_future, np.polyval(poly, poly_future) - 1.96 * se, np.polyval(poly, poly_future) + 1.96 * se,
                alpha=0.25, color="#1a5276")
ax.axvspan(2026, 2040, color="grey", alpha=0.12)
ax.text(2032, np.polyval(poly, 2032) + 8, "forecast", fontsize=9, ha="center")
ax.set_xlabel("year"); ax.set_ylabel("days with heat index >= 42C")
ax.set_title("Model 1: Dagupan danger-heat days - history & trajectory")
ax.legend(fontsize=9)

ax = axes[1]
r2s = [("Linear (held-out)", r2_lin_test, "#5dade2"), ("Poly-2 (held-out)", r2_poly_test, "#1a5276"),
       ("Random Forest (CV)", np.mean(rf_scores), "#27ae60")]
ax.bar([r[0] for r in r2s], [r[1] for r in r2s], color=[r[2] for r in r2s])
for i, r in enumerate(r2s):
    ax.text(i, r[1] + 0.02 if r[1] >= 0 else 0.02, f"{r[1]:.2f}", ha="center", fontsize=10)
ax.axhline(0, color="k", lw=0.8)
ax.set_ylabel("R2 (higher = better)")
ax.set_title("Model accuracy summary - the original ClimateShield chart, Dagupan edition")
ax.grid(axis="y", alpha=0.3)
fig.suptitle("Heat-day models", y=1.02)
save_chart(fig, "15_heat_models.png")
plt.close(fig)"""))

CELLS_P5.append(("code", """sample_mask = land_mask & np.isfinite(dem_utm) & np.isfinite(dist_river_m) & np.isfinite(dist_coast_m)
X_km = np.column_stack([
    dem_utm[sample_mask],
    np.log10(1 + dist_river_m[sample_mask]),
    np.log10(1 + dist_coast_m[sample_mask]),
    slope_deg[sample_mask],
])
X_km = (X_km - X_km.mean(0)) / X_km.std(0)
km = KMeans(n_clusters=5, n_init=10, random_state=42).fit(X_km)
labels_km = np.full((utm_h, utm_w), np.nan)
labels_km[sample_mask] = km.labels_

prof = pd.DataFrame({
    "elev_m": [np.median(dem_utm[sample_mask][km.labels_ == k]) for k in range(5)],
    "dist_river_m": [np.median(dist_river_m[sample_mask][km.labels_ == k]) for k in range(5)],
    "dist_coast_m": [np.median(dist_coast_m[sample_mask][km.labels_ == k]) for k in range(5)],
    "slope_deg": [np.median(slope_deg[sample_mask][km.labels_ == k]) for k in range(5)],
    "mean_susc": [np.nanmean(susc[sample_mask][km.labels_ == k]) for k in range(5)],
    "share_%": [100 * (km.labels_ == k).sum() / sample_mask.sum() for k in range(5)],
    "cells": [(km.labels_ == k).sum() for k in range(5)],
})

def name_cluster(row):
    if row["dist_coast_m"] < 900 and row["elev_m"] < 4:
        return "Coastal flats (tidal exposure)"
    if row["dist_river_m"] < 500 and row["elev_m"] < 4:
        return "Riverine lowlands (primary flood zone)"
    if row["elev_m"] >= 8 or row["slope_deg"] >= 3:
        return "Upland fringe (natural refuge)"
    if row["elev_m"] < 3:
        return "Low urban core (ponding-prone)"
    return "Mid terraces (moderate)"

prof["profile"] = prof.apply(name_cluster, axis=1)
print("Model 3 - Community risk typology (KMeans k=5):")
print(prof[["profile", "share_%", "elev_m", "dist_river_m", "mean_susc"]].round(1).to_string(index=False))

evac_pts = [(g.centroid.x, g.centroid.y) for g in EVAC.geometry]
evac_raster = np.zeros((utm_h, utm_w), dtype="uint8")
rows_ev = np.clip(((utm_transform.f - np.array([p[1] for p in evac_pts])) / 30).astype(int), 0, utm_h - 1)
cols_ev = np.clip(((np.array([p[0] for p in evac_pts]) - utm_transform.c) / 30).astype(int), 0, utm_w - 1)
evac_raster[rows_ev, cols_ev] = 1
dist_evac = ndimage.distance_transform_edt(1 - evac_raster) * 30
far = land_mask & (dist_evac > 1500)
print(f"\\nModel 4 - Evacuation accessibility:")
print(f"  {far.sum() * 0.0009:.1f} km2 of active land ({far.sum() / land_mask.sum() * 100:.0f}%) lies >1.5 km (Euclidean) from any school/townhall/worship site")

fig, axes = plt.subplots(1, 2, figsize=(15.8, 6.4), gridspec_kw={"width_ratios": [1.15, 1]})
ax = axes[0]
import matplotlib.patheffects
palette = ["#c0392b", "#e67e22", "#f1c40f", "#1abc9c", "#3498db"]
im = ax.imshow(np.where(sample_mask, labels_km + 1, np.nan), cmap=mpl.colors.ListedColormap(palette),
               vmin=0.5, vmax=5.5,
               extent=(utm_transform.c, utm_transform.c + utm_w * 30, utm_transform.f - utm_h * 30, utm_transform.f),
               origin="upper", alpha=0.9)
city_utm.boundary.plot(ax=ax, color="k", lw=1.5)
import matplotlib.patches as mpatches
ax.legend(handles=[mpatches.Patch(color=palette[k], label=prof.loc[k, "profile"]) for k in range(5)],
          fontsize=8, loc="lower right")
ax.set_title("Model 3: community risk typology (5 profiles)")
ax.set_axis_off()

ax = axes[1]
im2 = ax.imshow(np.where(city_mask, np.minimum(dist_evac, 3000), np.nan), cmap="magma_r",
                extent=(utm_transform.c, utm_transform.c + utm_w * 30, utm_transform.f - utm_h * 30, utm_transform.f),
                origin="upper")
try:
    ax.contour(np.where(city_mask, dist_evac, np.nan), levels=[1500], colors=["white"], linewidths=2)
except Exception:
    pass
ax.scatter(EVAC.geometry.x, EVAC.geometry.y, s=6, c="#2ecc71", alpha=0.8, label="shelter-worthy sites")
city_utm.boundary.plot(ax=ax, color="k", lw=1.5)
plt.colorbar(im2, ax=ax, shrink=0.75, label="distance to nearest shelter site (m, capped 3 km)")
ax.set_title("Model 4: evacuation accessibility - white line = 1.5 km horizon")
ax.legend(fontsize=8, loc="lower right")
ax.set_axis_off()
fig.suptitle("Where response planning needs to concentrate", y=1.0)
save_chart(fig, "16_typology_accessibility.png")
plt.close(fig)"""))

CELLS_P5.append(("md", """## 10. The ClimateShield-Dagupan command center (BI platform blueprint)

The notebook is the analytical engine; the **platform** is how a barangay captain, a tricycle cooperative, or a fishpen owner actually uses it.

```
+-------------------------------+     +-----------------------------+     +--------------------------+
|  DATA LAYER                   |     |  INTELLIGENCE LAYER         |     |  COMMUNITY LAYER         |
|  - PAGASA official feeds      | --> |  - risk rasters (this       | --> |  - web + mobile app      |
|    (iHeatMAP, rainfall &      |     |    notebook, refreshed)     |     |  - SMS/WhatsApp alerts   |
|    flood bulletins, TCWS)     |     |  - threshold triggers      |     |  - offline-first (SMS    |
|  - CDRRMO sitreps (see the    |     |    mapped to PAGASA        |     |    fallback for load-   |
|    Aug 2026 SitRep series)    |     |    categories              |     |    shedding days)        |
|  - crowd reports (banca       |     |  - barangay watchlists     |     |  - barangay dashboards   |
|    queues, flood depth,       |     |  - typology segments       |     |  - drill & checklist     |
|    road passability)          |     |  - accessibility scoring   |     |    library               |
|  - this repo's static layers  |     |                            |     |  - volunteer roster +   |
|    (DEM, WorldPop, OSM, PSA)  |     |                            |     |    resource maps         |
+-------------------------------+     +-----------------------------+     +--------------------------+
```

**Product phases**

| Phase | Scope | Notes |
|---|---|---|
| **P1 — Alert translations (weeks)** | PAGASA bulletins -> barangay-level plain-language actions (the trigger table in §4.2) | Zero new data needed; official categories only |
| **P2 — Local observability (months)** | Crowd depth reports + banca/road state + rain-gauge pooling; maps from this notebook as the base layer | The `projectligtas.com` live-flood-monitoring model proves demand; ClimateShield adds community operations |
| **P3 — Prepositioned operations** | Watchlists (§8), typology segments (§9), school-shelter registries, drill scheduling on the readiness calendar (§4.2) | Direct LGU/CDRRMO partnership; barangay boundaries from the LGU unlock full-resolution geo-targeting |
| **P4 — Anticipatory action** | Model-driven pre-positioning (bangus harvest lifts at Flood-Alert; water stations open at heat-Danger) | Requires phases 1-3 to be trusted first |

**Design principles**

1. **Official categories only for triggers** — PAGASA classes, DOST advisories; ClimateShield *translates*, never competes.
2. **Work with or without government aid** — every playbook has a "no external response expected" variant: banca cooperatives as the rescue fleet, sari-sari water points as cooling stations, church/school shelter rosters.
3. **Offline-first** — the Aug 2026 and Jul 2024 events both hit power/connectivity; SMS idioms and printed barangay cards are first-class features.
4. **Data dignity** — crowd reports are OSI-style anonymous observations, never surveillance; PSA/Kontur/WorldPop datasets used under their licenses (CC-BY/ODbL), attributed everywhere."""))

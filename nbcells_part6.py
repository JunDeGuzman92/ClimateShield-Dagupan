CELLS_P6 = []

CELLS_P6.append(("md", """## 11. The one-screen ClimateShield dashboard

The composite every command-center TV screen shows — climate pressure, terrain reality, population exposure, and the seasonal clock in a single frame (the direct descendant of the original Durham pipeline's Chart 09)."""))

CELLS_P6.append(("code", """fig, axes = plt.subplots(2, 3, figsize=(19.5, 10.2))

ax = axes[0, 0]
power_rain_g = df.loc["1991":"2020"].groupby("MONTH")["RAIN"].sum() / 30
ax.bar(np.arange(1, 13), power_rain_g.values, color="#5499c7")
ax.set_xticks(np.arange(1, 13))
ax.set_xticklabels(PAG_MONTHS, fontsize=7)
ax.set_title("Rainfall climatology (mm/month)")
ax.grid(axis="y", alpha=0.3)

ax = axes[0, 1]
ax.plot(hi_annual.index, hi_annual["Danger"] + hi_annual["Extreme Danger"], color="#c0392b", lw=2)
zfit = np.polyfit(heat_years, y_heat, 1)
ax.plot(heat_years, np.polyval(zfit, heat_years), "k--", lw=1.2, label=f"+{zfit[0]:.1f} d/yr")
ax.set_title("Danger heat-index days per year")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

ax = axes[0, 2]
ax.bar(annual.index, annual["D50"], color="#2471a3")
ax.set_title("Heavy-rain days (>= 50 mm)")
ax.grid(axis="y", alpha=0.3)

ax = axes[1, 0]
ax.barh([b[2] for b in BANDS][::-1], band_pct[::-1], color=["#fef9e7", "#d6eaf8", "#85c1e9", "#5499c7", "#2874a6", "#1a5276"])
ax.set_title("Active land by elevation band (%)")
for i, p in enumerate(band_pct[::-1]):
    ax.text(p + 1, i, f"{p:.0f}%", va="center", fontsize=8)

ax = axes[1, 1]
if pop is not None:
    ax.bar([f"Q{q + 1}" for q in range(5)], pop_by_quint, color=["#eafaf1", "#f9e79f", "#f5b041", "#e67e22", "#c0392b"])
    ax.set_title("Residents by susceptibility quintile")
else:
    band_area_share.plot.bar(ax=ax, color="#85c1e9")
    ax.set_title("Area by elevation band")
ax.grid(axis="y", alpha=0.3)

ax = axes[1, 2]
ax.bar(mon - 0.2, rain_monthly.reindex(mon, fill_value=0).values, 0.4, color="#2471a3", label="heavy-rain days/yr")
ax.bar(mon + 0.2, hi_monthly.reindex(mon, fill_value=0).values, 0.4, color="#c0392b", label="danger heat days/yr")
ax.set_xticks(mon)
ax.set_xticklabels(PAG_MONTHS, fontsize=7)
ax.set_title("Readiness calendar (danger by month)")
ax.legend(fontsize=7)

fig.suptitle(f"ClimateShield - Dagupan City disaster intelligence dashboard  |  climate data through {df.index.max():%b %Y}", fontsize=14, y=1.0)
fig.tight_layout()
save_chart(fig, "17_climateshield_dashboard.png")
plt.close(fig)"""))

CELLS_P6.append(("md", """## 12. Interactive geo-map (for the app's map screen)

The static rasters above become a browsable product layer: city boundary, hydrology, coastline, every shelter-relevant facility, and the susceptibility surface — saved as standalone HTML to `outputs/maps/`, openable by any barangay laptop or phone browser, no GIS required."""))

CELLS_P6.append(("code", """import folium
from folium.plugins import Fullscreen
from matplotlib import cm as mcm
from rasterio.warp import transform_bounds

susc_show = np.where(land_mask, np.clip(susc, 0, 100), np.nan)
rgba = np.zeros((utm_h, utm_w, 4), dtype=np.uint8)
norm_s = (susc_show - 0) / 100.0
cmap_s = mpl.colormaps["YlOrRd"]
rgb = (cmap_s(np.nan_to_num(norm_s, nan=0.0))[:, :, :3] * 255).astype(np.uint8)
rgba[..., 0:3] = rgb
rgba[..., 3] = (np.nan_to_num(norm_s, nan=0) * 255 * 0.75).astype(np.uint8)

map_dir = ROOT / "outputs" / "maps"
map_dir.mkdir(parents=True, exist_ok=True)
overlay_png = map_dir / "susceptibility_overlay.png"
plt.imsave(overlay_png, rgba)

bounds_4326 = transform_bounds("EPSG:32651", "EPSG:4326",
                               utm_transform.c, utm_transform.f - utm_h * 30,
                               utm_transform.c + utm_w * 30, utm_transform.f)

import numpy as _np
west_b, south_b, east_b, north_b = bounds_4326

center = [float(city_gdf.geometry.iloc[0].centroid.y), float(city_gdf.geometry.iloc[0].centroid.x)]
ESRI_ATTR = "Esri, HERE, Garmin, (c) OpenStreetMap contributors, and the GIS User Community"

m = folium.Map(location=center, zoom_start=12, tiles=None)

CARTO_API_KEY = ""  # optional: paste a free key from https://carto.com/basemaps/apikey to restore true Carto Positron

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    attr=ESRI_ATTR,
    name="Light Gray Canvas (default)",
).add_to(m)
if CARTO_API_KEY:
    folium.TileLayer(
        tiles=f"https://basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png?api_key={CARTO_API_KEY}",
        attr="(c) OpenStreetMap contributors, (c) CARTO",
        name="Carto Positron",
    ).add_to(m)

folium.GeoJson(city_gdf.__geo_interface__, name="Dagupan City boundary",
               style_function=lambda x: {"color": "black", "fillOpacity": 0.02, "weight": 2.5}).add_to(m)

main_water = g_water[g_water["class"].isin(["river", "canal"])]
for _, r in main_water.head(220).iterrows():
    pts = [(lat, lon) for lon, lat in r.geometry.coords]
    folium.PolyLine(pts, color="#1a5276", weight=4 if r["class"] == "river" else 2.5,
                    opacity=0.8, tooltip=f"waterway: {r['class']}").add_to(m)
for _, r in g_coast.head(12).iterrows():
    pts = [(lat, lon) for lon, lat in r.geometry.coords]
    folium.PolyLine(pts, color="#117864", weight=5, opacity=0.9, tooltip="Lingayen Gulf coastline").add_to(m)

fac_color = {"school": "#1f77b4", "health": "#c0392b", "civic_protective": "#f39c12", "worship": "#7d3c98"}
for _, r in fac_utm.iterrows():
    p4326 = gpd.GeoSeries([r.geometry], crs=dst_crs).to_crs("EPSG:4326").iloc[0]
    folium.CircleMarker(
        location=[p4326.y, p4326.x], radius=4, color=fac_color.get(r["category"], "#555"),
        fill=True, fill_opacity=0.8, weight=1,
        popup=folium.Popup(f"<b>{r.get('name') or r['category']}</b><br>category: {r['category']}<br>"
                           f"susceptibility at site: {r['susc']:.0f}/100<br>elevation: {r['elev_m']:.1f} m"
                           if np.isfinite(r['susc']) else f"<b>{r['category']}</b>", max_width=220),
    ).add_to(m)

folium.raster_layers.ImageOverlay(
    image=str(overlay_png),
    bounds=[[south_b, west_b], [north_b, east_b]],
    opacity=0.65, name="Flood-susceptibility surface",
).add_to(m)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri, Maxar, Earthstar Geographics",
    name="Esri Satellite",
).add_to(m)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
    attr=ESRI_ATTR,
    name="Place labels (overlay)",
    overlay=True,
).add_to(m)

folium.LayerControl().add_to(m)
Fullscreen().add_to(m)
m.save(map_dir / "climateshield_dagupan_interactive.html")
print(f"Interactive map saved: outputs/maps/climateshield_dagupan_interactive.html "
      f"({(map_dir / 'climateshield_dagupan_interactive.html').stat().st_size / 1e6:.1f} MB)")
m"""))

CELLS_P6.append(("md", """## 13. Limitations, ethics, and what the app phase must add

**What this analysis is — and is not**

1. **Reanalysis ≠ station records.** NASA POWER (MERRA-2) and ERA5 are ~9–60 km grids over a small coastal city; they agree strongly with each other (correlations printed in §4.1) and with the *category* of official PAGASA events (Apr 28, 2024 → Danger both ways), but station-point extremes like PAGASA's 51°C reading will exceed gridded reanalysis. The app must ingest PAGASA's synoptic-station feed (Dagupan agromet/synoptic), with this notebook's reanalysis as the 45-year trend backbone.
2. **The susceptibility surface is a planning proxy.** It is transparent (weights printed), satellite-based (Copernicus GLO-30 DSM — rooftop bias documented), and deliberately *not* a hydraulic model. Official flood-depth maps (DOST-Project NOAH legacy / DPWH studies) and PDRRMO stage records (Pantal Alert/Alarm/Critical) supersede it for engineering.
3. **Barangay geometry is the app's #1 data partnership.** Open portals stop at municipality level for Dagupan; the LGU (CPDO/CDRRMO) and the CBMS household surveys unlock true per-barangay targeting. Everything else is already in hand.
4. **Models are honest-size.** Annual heat-day models reach held-out R² values printed in §9; the RF's cross-validated gain over trend alone is small — these are *planning heuristics*, clearly labeled, not event forecasts. Forecast credibility in the app comes from PAGASA's own products; ClimateShield's edge is translation-to-action.
5. **Exposure rasters age.** WorldPop 2020 + the 2020 census under-count new construction since; OSM coverage of Dagupan is strong on schools/hydrology but imperfect — crowd-validation loops (photo-tagged infrastructure checks) are product features, not bugs.
6. **Data dignity & licensing.** Crowd reports are anonymous, per-informed-consent; all datasets are used under their licenses (PSA data via OCHA HDX open license; WorldPop/ERA5 CC-BY 4.0; OSM ODbL; Copernicus free & open) with attribution carried into every artifact of the future app.

**Headline numbers the command center ships with (all computed above):**"""))

CELLS_P6.append(("code", """files = sorted(CHARTS.glob("*")) + sorted(PROC.glob("*")) + sorted(map_dir.glob("*.html"))
print("=== ARTIFACT MANIFEST ===")
for f in files:
    print(f"  {f.relative_to(ROOT)}  ({f.stat().st_size / 1e6:.2f} MB)")

print("")
print("=== HEADLINE FINDINGS (ClimateShield - Dagupan edition) ===")
print("")

below2 = band_pct[0] + band_pct[1] + band_pct[2]
print(f"1. TERRAIN: {below2:.0f}% of Dagupan's land sits at or below ~2 m above sea level;")
print(f"   city median elevation is {np.nanmedian(dem_utm[city_mask]):.1f} m (Copernicus GLO-30, sea-calibrated).")
if pop is not None:
    print(f"2. EXPOSURE: ~{pop_by_band[:3].sum():,.0f} residents live below the ~2 m line "
          f"({pop_by_band[:3].sum() / tot * 100:.0f}% of the WorldPop 2020 total).")
d_now = hi_annual['Danger'].iloc[-10:].mean()
d_then = hi_annual['Danger'].iloc[:10].mean()
print(f"3. HEAT: danger-level heat-index days rose from ~{d_then:.0f}/yr (1981-1990 avg) to ~{d_now:.0f}/yr "
      f"(2017-2026 avg); PAGASA station records crest at 51C (Apr 2024, May 2021).")
w7 = df['RAIN'].rolling(7).sum().groupby(df.index.year).max()
print(f"4. RAIN: 2026's worst week so far dumped {w7.loc[2026]:.0f} mm - perspective: the all-time record is "
      f"{w7.max():.0f} mm ({w7.idxmax()}). The Aug 2026 habagat alone affected 90,015 residents (CDRRMO SitRep 15).")
print(f"5. FUTURE (labeled projection, poly-2): ~{np.polyval(poly, 2035):.0f} danger-heat days annually by 2035 "
      f"if the 45-year trend persists (residual sigma ~ {se:.0f} days).")
hi_n = (fac_utm["susc"] >= np.nanpercentile(susc, 80)).sum()
hi_den = fac_utm["susc"].notna().sum()
if far.sum() > 0:
    print(f"6. ACTION: {far.sum() * 0.0009:.1f} km2 of active land sits >1.5 km from any school/townhall/worship anchor "
          f"-> needs dedicated banca/shelter-site protocols before the next habagat peak.")
else:
    print("6. ACTION: shelter DISTANCE is not Dagupan's gap - every active-land cell is within 1.5 km of a "
          "school/townhall/worship site;")
    print(f"   the real gap is shelter SUITABILITY: {hi_n} of {hi_den} sampled facilities "
          f"({hi_n / hi_den * 100:.0f}%) stand in top-20% susceptibility ground -> flood-proof those, "
          "designate alternates, and pre-position banca rescue fleets there.")
print("")
print("Reproduce: jupyter nbconvert --to notebook --execute ClimateShield_Dagupan_Analysis.ipynb")
print("Contact: ClimateShield-Dagupan community project (github.com/JunDeGuzman92)")"""))

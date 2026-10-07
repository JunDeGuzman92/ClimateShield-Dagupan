CELLS_P3 = []

CELLS_P3.append(("md", """## 5. Terrain and flood susceptibility (satellite geomapping)

Dagupan is famously one of the Philippines' lowest-lying cities. After the 1990 earthquake dropped parts of the downtown below sea level (Ishihara et al. 1993), every heavy-rain event contends with a gravity problem: water that arrives faster than a near-flat, tide-influenced delta can drain it.

Method (a fully transparent proxy, not a hydraulic model):

1. Elevation: Copernicus GLO-30 (30 m digital surface model, ESA). Heights are calibrated in-notebook against the Lingayen Gulf sea surface; the city is masked by its official boundary (OSM).
2. Proximity to waterways: every OSM river/canal/ditch/drain segment is rasterized; Euclidean distance computed per cell.
3. Proximity to coast: same, using the OSM coastline of Lingayen Gulf.
4. Flatness (local relief): surface slope; Dagupan's ponding zones are the flattest ground in the flattest city.
5. Weighted composite: elevation 45% + river proximity 25% + coastal proximity 15% + flatness 15% = the *ClimateShield Flood-Susceptibility Index* (0–100, city-normalized).

Caveats printed and respected: GLO-30 is a surface model (rooftops read ~2–5 m above ground in dense construction); distances are Euclidean, not flow-path; pumping and drainage-line capacity are not modeled. This is a community-planning susceptibility surface, complementary to (never a substitute for) official DOST-PAGASA / DPWH flood-hazard maps."""))

CELLS_P3.append(("code", """import geopandas as gpd
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.features import geometry_mask, rasterize
from shapely.geometry import LineString, Point, Polygon, box

city_gdf = gpd.read_file(RAW / "dagupan_city_boundary.geojson")
print("City boundary:", city_gdf.iloc[0]["name"], "| geometry:", city_gdf.iloc[0].geometry.geom_type)

with rasterio.open(PROC / "dem_glo30_dagupan_raw.tif") as src:
    dem_4326 = src.read(1)
    tr = src.transform
    nodata = src.nodata

rows, cols = np.indices(dem_4326.shape)
lons = tr.c + (cols + 0.5) * tr.a
lats = tr.f + (rows + 0.5) * tr.e

offshore = (lons < 120.26) & (lats > 15.97) & (lats < 16.21)
sea_ref = np.nanmedian(dem_4326[offshore])
print(f"Copernicus GLO-30 sea-surface reference over Lingayen Gulf: {sea_ref:.2f} m ({int(offshore.sum()):,} offshore pixels)")
dem_sl = dem_4326 - sea_ref
dem_sl[dem_4326 <= nodata if nodata is not None else dem_4326 < -900] = np.nan
print("Interpretation: DEM grid-cell values rest on a WGS84 ellipsoidal datum;")
print(f"we shift heights by the observed sea reference ({sea_ref:.2f} m) so bands read approximately above sea level.")

ws = 120.0
west, east = 120.215, 120.415
south, north = 15.955, 16.215
src_crs = "EPSG:4326"
dst_crs = "EPSG:32651"

with rasterio.open(PROC / "dem_glo30_dagupan_raw.tif") as src:
    d_tr, dw, dh = calculate_default_transform(src_crs, dst_crs, src.width, src.height,
                                               left=west, bottom=south, right=east, top=north, resolution=30)
    dem_utm = np.full((dh, dw), np.nan, dtype=np.float32)
    reproject(dem_sl, dem_utm,
              src_transform=tr, src_crs=src_crs,
              dst_transform=d_tr, dst_crs=dst_crs,
              resampling=Resampling.bilinear)
utm_transform, utm_h, utm_w = d_tr, dh, dw
print(f"UTM 51N analysis grid: {utm_w} x {utm_h} cells @ 30 m")

city_utm = city_gdf.to_crs(dst_crs)
city_mask = geometry_mask(city_utm.geometry.values, out_shape=(utm_h, utm_w), transform=utm_transform, invert=True)
poly_km2 = city_utm.geometry.iloc[0].area / 1e6
print(f"OSM admin polygon area: {poly_km2:.0f} km2 - it extends into Lingayen Gulf municipal waters;")
print(f"official Dagupan land area is 44.47 km2, so an 'active land' footprint (OSM land use + buildings +")
print(f"WorldPop occupancy) is derived after the OSM feature parse; all area/exposure stats use that footprint.")

with rasterio.open(PROC / "cs_dagupan_dem_30m_utm.tif", "w", driver="GTiff", height=utm_h, width=utm_w,
                   count=1, dtype="float32", crs=dst_crs, transform=utm_transform, nodata=np.nan, compress="lzw") as dst:
    dst.write(dem_utm, 1)"""))

CELLS_P3.append(("code", """osm = json.load(open(RAW / "osm_dagupan_features_raw.json"))
nodes = osm["nodes"]
ways = osm["ways"]

def way_coords(w):
    pts = []
    for nid in w.get("nodes", []):
        n = nodes.get(str(nid))
        if n:
            pts.append((n["lon"], n["lat"]))
    return pts

water_lines, coast_lines, road_lines, place_pts, fac_pts, bldg_polys = [], [], [], [], [], []
for w in ways.values():
    t = w.get("tags", {})
    pts = way_coords(w)
    if len(pts) < 2:
        continue
    if "waterway" in t:
        water_lines.append({"geometry": LineString(pts), "class": t["waterway"]})
    if t.get("natural") == "coastline":
        coast_lines.append({"geometry": LineString(pts)})
    if t.get("highway") in ("trunk", "primary", "secondary", "tertiary"):
        road_lines.append({"geometry": LineString(pts), "class": t["highway"]})
    if "building" in t and len(pts) > 3 and pts[0] == pts[-1]:
        bldg_polys.append({"geometry": Polygon(pts),
                           "type": t.get("building", "yes") if t.get("building") != "yes" else "generic"})
    if "amenity" in t:
        fac_pts.append({"geometry": LineString(pts).centroid, "class": t["amenity"], "name": t.get("name", ""), "src": "way"})
for n in nodes.values():
    t = n.get("tags", {})
    if "place" in t:
        place_pts.append({"geometry": Point(n["lon"], n["lat"]), "class": t["place"], "name": t.get("name", "")})
    if "amenity" in t:
        fac_pts.append({"geometry": Point(n["lon"], n["lat"]), "class": t["amenity"], "name": t.get("name", ""), "src": "node"})

g_water = gpd.GeoDataFrame(water_lines, crs="EPSG:4326")
g_coast = gpd.GeoDataFrame(coast_lines, crs="EPSG:4326")
g_roads = gpd.GeoDataFrame(road_lines, crs="EPSG:4326")
g_places = gpd.GeoDataFrame(place_pts, crs="EPSG:4326")
g_fac = gpd.GeoDataFrame(fac_pts, crs="EPSG:4326").drop_duplicates(subset=["geometry"])
g_bldg = gpd.GeoDataFrame(bldg_polys, crs="EPSG:4326")

city_bounds_4326 = city_gdf.total_bounds
inside = g_water.intersects(box(*city_bounds_4326).buffer(0.02))
g_water = g_water[inside]
print(f"OSM features parsed: {len(g_water)} waterways | {len(g_coast)} coast segments | {len(g_roads)} major roads | "
      f"{len(g_bldg)} building footprints | {len(g_fac)} amenities | {len(g_places)} place labels")

colors = {"river": "#1a5276", "canal": "#2874a6", "stream": "#5499c7", "ditch": "#7fb3d5", "drain": "#a9cce3"}

fig, ax = plt.subplots(figsize=(12.5, 9.5))
city_utm.boundary.plot(ax=ax, color="k", lw=2.5)
if len(g_coast):
    g_coast.to_crs(dst_crs).plot(ax=ax, color="#0e6251", lw=3.5)
g_roads.to_crs(dst_crs).plot(ax=ax, color="#b3a186", lw=1.4, alpha=0.85)
for cls, col in colors.items():
    sub = g_water[g_water["class"] == cls]
    if len(sub):
        sub.to_crs(dst_crs).plot(ax=ax, color=col, lw=1.1 if cls != "river" else 2.4, label=f"waterway: {cls}")
if len(g_bldg):
    g_bldg.to_crs(dst_crs).plot(ax=ax, color="#d5d8dc", alpha=0.5, lw=0.1)
labels = g_places[g_places["class"].isin(["quarter", "suburb", "town", "city"])]
for _, r in labels.drop_duplicates(subset=["name"]).iterrows():
    p = gpd.GeoSeries([r.geometry], crs="EPSG:4326").to_crs(dst_crs).iloc[0]
    ax.text(p.x, p.y, r["name"], fontsize=7.5, ha="center", color="#1b2631",
            path_effects=[mpl.patheffects.withStroke(linewidth=2.5, foreground="white")])
ctx_ok = True
try:
    import contextily as cx
    cx.add_basemap(ax, crs=dst_crs, source=getattr(cx.providers.Esri, "WorldGrayCanvas", None) or cx.providers.OpenStreetMap.Mapnik, alpha=0.95,
                   attribution="(c) OpenStreetMap contributors, Esri")
except Exception as e:
    ctx_ok = False
    print("basemap skipped (offline):", type(e).__name__)
ax.set_title("Dagupan City study area - OSM hydrology, roads, built footprints", fontsize=13)
ax.set_axis_off()
save_chart(fig, "08_study_area_map.png")
plt.close(fig)

print("City rendered with rivers/canals network, gulf coastline, trunk roads, and", len(g_bldg), "OSM building footprints")

LAND_USE_TAGS = {"residential", "industrial", "commercial", "retail", "farmland", "aquaculture", "farmyard",
                 "cemetery", "grass", "construction", "greenfield", "brownfield", "landfill", "recreation_ground",
                 "religious", "flowerbed", "forest", "garages", "salt_pond"}
land_shapes = []
for w in ways.values():
    t = w.get("tags", {})
    if t.get("landuse") in LAND_USE_TAGS or "building" in t or t.get("amenity") in (
            "school", "hospital", "university", "college"):
        pts = way_coords(w)
        if len(pts) > 3 and pts[0] == pts[-1]:
            land_shapes.append(Polygon(pts))
g_landuse = gpd.GeoDataFrame(geometry=land_shapes, crs="EPSG:4326").to_crs(dst_crs)
landuse_raster = rasterize([(g, 1) for g in g_landuse.geometry], out_shape=(utm_h, utm_w),
                           transform=utm_transform, fill=0, dtype="uint8")
with rasterio.open(PROC / "worldpop100m_dagupan_2020.tif") as psrc:
    pop_raw = psrc.read(1).astype("float32")
    pop_raw_tr, pop_raw_crs = psrc.transform, psrc.crs
pop_raw[pop_raw < 0] = 0
pop_presence = np.zeros((utm_h, utm_w), dtype="uint8")
reproject((pop_raw > 0).astype("float32"), pop_presence,
          src_transform=pop_raw_tr, src_crs=pop_raw_crs,
          dst_transform=utm_transform, dst_crs=dst_crs, resampling=Resampling.nearest)
land_mask = city_mask & ((landuse_raster > 0) | (pop_presence > 0))
active_km2 = land_mask.sum() * 0.0009
print(f"ACTIVE-LAND footprint: {land_mask.sum():,} cells = {active_km2:.1f} km2 "
      f"({active_km2 / 44.47 * 100:.0f}% of the official 44.47 km2 land area)")"""))

CELLS_P3.append(("code", """BANDS = [(-np.inf, 0.0, "< 0 m (below sea level)"),
         (0.0, 1.0, "0-1 m"),
         (1.0, 2.0, "1-2 m"),
         (2.0, 4.0, "2-4 m"),
         (4.0, 8.0, "4-8 m"),
         (8.0, np.inf, "> 8 m")]
band_cells = []
for lo, hi, label in BANDS:
    m = land_mask & (dem_utm >= lo) & (dem_utm < hi)
    band_cells.append(m.sum() * 0.0009)
band_cells = np.array(band_cells)
band_pct = band_cells / (land_mask.sum() * 0.0009) * 100

stats_tbl = pd.DataFrame({
    "elevation band": [b[2] for b in BANDS],
    "area_km2": band_cells.round(2),
    "percent_of_active_land": band_pct.round(1),
})
print(stats_tbl.to_string(index=False))
print(f"\\nHEADLINE: {band_pct[0]:.0f}% + {band_pct[1]:.0f}% + {band_pct[2]:.0f}% = {band_pct[0] + band_pct[1] + band_pct[2]:.0f}% of Dagupan's active land lies at or below ~2 m above sea level")
print(f"Active-land median elevation: {np.nanmedian(dem_utm[land_mask]):.2f} m | 95th pct: {np.nanpercentile(dem_utm[land_mask], 95):.2f} m")

fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))
ax = axes[0]
vals = dem_utm[land_mask]
vals = vals[np.isfinite(vals)]
clip_lo, clip_hi = np.percentile(vals, 0.5), np.percentile(vals, 99.5)
n, bins, patches = ax.hist(np.clip(vals, clip_lo, clip_hi), bins=60, edgecolor="white")
for patch, left in zip(patches, bins[:-1]):
    if left < 0:
        patch.set_facecolor("#1a5276")
    elif left < 1:
        patch.set_facecolor("#2874a6")
    elif left < 2:
        patch.set_facecolor("#5499c7")
    elif left < 4:
        patch.set_facecolor("#85c1e9")
    else:
        patch.set_facecolor("#d6eaf8")
ax.axvline(0, color="k", lw=2)
ax.axvline(2, color="k", lw=1, ls="--")
ax.set_xlabel("Elevation above sea level (m, GLO-30 DSM, sea-calibrated)")
ax.set_ylabel("30-m cells in city")
ax.set_title("The vertical profile of Dagupan")

ax = axes[1]
order = np.arange(len(BANDS))
cum = np.cumsum(band_pct)
ax.bar(order, band_pct, color=["#1a5276", "#2874a6", "#5499c7", "#85c1e9", "#d6eaf8", "#fef9e7"])
for i, (p, c) in enumerate(zip(band_pct, cum)):
    ax.text(i, p + 0.6, f"{p:.1f}%", ha="center", fontsize=10)
ax.set_xticks(order)
ax.set_xticklabels([b[2] for b in BANDS], rotation=20, fontsize=8)
ax.set_ylabel("% of active land")
ax.set_title("Share of active land by elevation band")
fig.suptitle("Dagupan terrain analysis - Copernicus GLO-30, 30 m", y=1.02)
save_chart(fig, "09_elevation_bands.png")
plt.close(fig)"""))

CELLS_P3.append(("code", """riv_raster = rasterize(
    [(g, 1) for g in g_water.to_crs(dst_crs).geometry],
    out_shape=(utm_h, utm_w), transform=utm_transform, fill=0, dtype="uint8", all_touched=True
)
coast_raster = rasterize(
    [(g, 1) for g in g_coast.to_crs(dst_crs).geometry],
    out_shape=(utm_h, utm_w), transform=utm_transform, fill=0, dtype="uint8", all_touched=True
)
dist_river_m = ndimage.distance_transform_edt(1 - riv_raster) * 30.0
dist_coast_m = ndimage.distance_transform_edt(1 - coast_raster) * 30.0

gy, gx = np.gradient(np.nan_to_num(dem_utm, nan=0.0), 30.0)
slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))

def pct_rank(arr, mask):
    v = arr[mask]
    r = np.argsort(np.argsort(v))
    ranks = np.empty_like(v)
    ranks[np.argsort(v)] = r / (len(v) - 1)
    out = np.full(arr.shape, np.nan)
    out[mask] = ranks
    return out

elev_inv = pct_rank(-dem_utm, land_mask)
riv_inv = pct_rank(-dist_river_m, land_mask)
coast_inv = pct_rank(-dist_coast_m, land_mask)
flat_inv = pct_rank(-slope_deg, land_mask)

W_ELEV, W_RIV, W_COAST, W_FLAT = 0.45, 0.25, 0.15, 0.15
susc = (W_ELEV * elev_inv + W_RIV * riv_inv + W_COAST * coast_inv + W_FLAT * flat_inv) * 100
susc = np.where(land_mask, susc, np.nan)
print(f"Susceptibility index built on {int(land_mask.sum()):,} active-land cells; weights: elev {W_ELEV}, river {W_RIV}, coast {W_COAST}, flatness {W_FLAT}")
print(f"Distribution: p25={np.nanpercentile(susc, 25):.0f} median={np.nanpercentile(susc, 50):.0f} p75={np.nanpercentile(susc, 75):.0f} max={np.nanmax(susc):.0f}")

with rasterio.open(PROC / "cs_dagupan_susceptibility_30m_utm.tif", "w", driver="GTiff", height=utm_h, width=utm_w,
                   count=1, dtype="float32", crs=dst_crs, transform=utm_transform, nodata=np.nan, compress="lzw") as dst:
    dst.write(susc.astype("float32"), 1)

from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("cs", ["#eafaf1", "#f9e79f", "#f5b041", "#e67e22", "#c0392b", "#641e16"])

fig, ax = plt.subplots(figsize=(12.5, 9.5))
im = ax.imshow(susc, cmap=cmap, vmin=0, vmax=100, extent=(
    utm_transform.c, utm_transform.c + utm_w * 30,
    utm_transform.f + utm_h * -30, utm_transform.f
), origin="upper")
g_water.to_crs(dst_crs).plot(ax=ax, color="#1a5276", lw=1.0, alpha=0.65)
g_coast.to_crs(dst_crs).plot(ax=ax, color="#0e6251", lw=3)
city_utm.boundary.plot(ax=ax, color="k", lw=1.8)
for _, r in labels.drop_duplicates(subset=["name"]).iterrows():
    pt_anchor = gpd.GeoSeries([r.geometry], crs="EPSG:4326").to_crs(dst_crs).iloc[0]
    ax.text(pt_anchor.x, pt_anchor.y, r["name"], fontsize=7,
            ha="center", color="#1b2631",
            path_effects=[mpl.patheffects.withStroke(linewidth=2.5, foreground="white")])
plt.colorbar(im, ax=ax, shrink=0.7, label="ClimateShield Flood-Susceptibility Index (0-100)")
ax.set_title("ClimateShield Flood-Susceptibility Index (30 m, community-planning proxy)", fontsize=12)
ax.set_xlim(city_utm.total_bounds[0] - 500, city_utm.total_bounds[2] + 500)
ax.set_ylim(city_utm.total_bounds[1] - 500, city_utm.total_bounds[3] + 500)
ax.set_axis_off()
save_chart(fig, "10_susceptibility_map.png")
plt.close(fig)"""))



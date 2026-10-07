import json
import pickle
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, rasterize
from rasterio.warp import reproject, Resampling
from shapely.geometry import LineString, Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "data" / "app_layers"
OUT.mkdir(parents=True, exist_ok=True)

DST_CRS = "EPSG:32651"
WEST, EAST, SOUTH, NORTH = 120.215, 120.415, 15.955, 16.215
LAND_USE_TAGS = {"residential", "industrial", "commercial", "retail", "farmland", "aquaculture", "farmyard",
                 "cemetery", "grass", "construction", "greenfield", "brownfield", "landfill", "recreation_ground",
                 "religious", "flowerbed", "forest", "garages", "salt_pond"}

print("== ClimateShield app layer prep ==")

with rasterio.open(PROC / "cs_dagupan_dem_30m_utm.tif") as src:
    dem = src.read(1)
    utm_transform = src.transform
    utm_h, utm_w = src.height, src.width
with rasterio.open(PROC / "cs_dagupan_susceptibility_30m_utm.tif") as src:
    susc = src.read(1)

def sample_grid(arr, x, y):
    col = (x - utm_transform.c) / 30 - 0.5
    row = (utm_transform.f - y) / 30 - 0.5
    ri = int(np.clip(round(row), 0, utm_h - 1))
    ci = int(np.clip(round(col), 0, utm_w - 1))
    return arr[ri, ci]

city = gpd.read_file(RAW / "dagupan_city_boundary.geojson")
city_utm = city.to_crs(DST_CRS)
city_mask = geometry_mask(city_utm.geometry.values, out_shape=(utm_h, utm_w), transform=utm_transform, invert=True)

osm = json.load(open(RAW / "osm_dagupan_features_raw.json"))
nodes, ways = osm["nodes"], osm["ways"]

def way_coords(w):
    return [(nodes[str(n)]["lon"], nodes[str(n)]["lat"]) for n in w.get("nodes", []) if str(n) in nodes]

def to_utm_pts(pts):
    g = gpd.GeoSeries([Point(p) for p in pts], crs="EPSG:4326").to_crs(DST_CRS)
    return list(zip(g.x, g.y))

water_lines, coast_lines, roads, buildings, facilities, places = [], [], [], [], [], []
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
        roads.append({"geometry_ll": LineString(pts), "class": t["highway"], "name": t.get("name", "")})
    if len(pts) > 3 and pts[0] == pts[-1]:
        poly = Polygon(pts)
        if "building" in t:
            buildings.append({"geometry_ll": poly, "type": "bldg"})
        if t.get("amenity"):
            facilities.append({"geometry_ll": LineString(pts).centroid, "class": t["amenity"], "name": t.get("name", "")})
for n in nodes.values():
    t = n.get("tags", {})
    if "place" in t:
        places.append({"lon": n["lon"], "lat": n["lat"], "name": t.get("name", ""), "class": t["place"]})
    if "amenity" in t and "place" not in t:
        facilities.append({"geometry_ll": Point(n["lon"], n["lat"]), "class": t["amenity"], "name": t.get("name", "")})

g_water = gpd.GeoDataFrame(water_lines, crs="EPSG:4326")
g_coast = gpd.GeoDataFrame(coast_lines, crs="EPSG:4326")

riv_raster = rasterize([(g, 1) for g in g_water.to_crs(DST_CRS).geometry],
                       out_shape=(utm_h, utm_w), transform=utm_transform, fill=0, dtype="uint8", all_touched=True)
coast_raster = rasterize([(g, 1) for g in g_coast.to_crs(DST_CRS).geometry],
                         out_shape=(utm_h, utm_w), transform=utm_transform, fill=0, dtype="uint8", all_touched=True)
from scipy import ndimage
dist_river_m = (ndimage.distance_transform_edt(1 - riv_raster) * 30.0).astype("float32")
dist_coast_m = (ndimage.distance_transform_edt(1 - coast_raster) * 30.0).astype("float32")

land_shapes = []
for w in ways.values():
    t = w.get("tags", {})
    if t.get("landuse") in LAND_USE_TAGS or "building" in t or t.get("amenity") in ("school", "hospital", "university", "college"):
        pts = way_coords(w)
        if len(pts) > 3 and pts[0] == pts[-1]:
            land_shapes.append(Polygon(pts))
g_landuse = gpd.GeoDataFrame(geometry=land_shapes, crs="EPSG:4326").to_crs(DST_CRS)
landuse_raster = rasterize([(g, 1) for g in g_landuse.geometry],
                           out_shape=(utm_h, utm_w), transform=utm_transform, fill=0, dtype="uint8")

with rasterio.open(PROC / "worldpop100m_dagupan_2020.tif") as psrc:
    pop_raw = psrc.read(1).astype("float32")
    pop_tr, pop_crs = psrc.transform, psrc.crs
pop_raw[pop_raw < 0] = 0
pop_presence = np.zeros((utm_h, utm_w), dtype="uint8")
reproject((pop_raw > 0).astype("float32"), pop_presence,
          src_transform=pop_tr, src_crs=pop_crs,
          dst_transform=utm_transform, dst_crs=DST_CRS, resampling=Resampling.nearest)

pop_utm = np.zeros((utm_h, utm_w), dtype="float32")
reproject(pop_raw, pop_utm, src_transform=pop_tr, src_crs=pop_crs,
          dst_transform=utm_transform, dst_crs=DST_CRS, resampling=Resampling.nearest)
pop_utm = pop_utm / 11.11
pop_utm[pop_utm < 1e-3] = 0

land_mask = (city_mask & ((landuse_raster > 0) | (pop_presence > 0))).astype("uint8")
print(f"land mask: {land_mask.sum():,} cells = {land_mask.sum() * 0.0009:.1f} km2")

gy, gx = np.gradient(np.nan_to_num(dem, nan=0.0), 30.0)
slr = np.arctan(np.hypot(gx, gy))
aspr = np.arctan2(-gx, gy)
zen, az = np.radians(45.0), np.radians(315.0)
hillshade = np.clip(255.0 * (np.cos(zen) * np.cos(slr) + np.sin(zen) * np.sin(slr) * np.cos(az - aspr)), 0, 255)
hillshade = hillshade.astype("uint8")

roads_out = []
for r in roads:
    utm_pts = to_utm_pts(list(r["geometry_ll"].coords))
    elevs = np.array([sample_grid(dem, x, y) for x, y in utm_pts], dtype="float32")
    length_m = 0.0
    for i in range(len(utm_pts) - 1):
        length_m += float(np.hypot(utm_pts[i + 1][0] - utm_pts[i][0], utm_pts[i + 1][1] - utm_pts[i][1]))
    roads_out.append({"ll": list(r["geometry_ll"].coords), "elevs": elevs,
                      "class": r["class"], "name": r["name"], "length_m": length_m})

FAC_SETS = {
    "school": {"school", "kindergarten", "college", "university"},
    "health": {"hospital", "clinic", "health_post", "pharmacy", "doctors", "dentist"},
    "civic_protective": {"townhall", "community_centre", "police", "fire_station", "shelter", "childcare"},
    "worship": {"place_of_worship"},
}
fac_out = []
seen = set()
for f in facilities:
    cat = next((k for k, s in FAC_SETS.items() if f["class"] in s), None)
    if not cat:
        continue
    key = (round(f["geometry_ll"].x, 6), round(f["geometry_ll"].y, 6), f["class"])
    if key in seen:
        continue
    seen.add(key)
    (x, y) = to_utm_pts([(f["geometry_ll"].x, f["geometry_ll"].y)])[0]
    fac_out.append({"lon": f["geometry_ll"].x, "lat": f["geometry_ll"].y, "utm": (x, y),
                    "category": cat, "class": f["class"], "name": f["name"],
                    "elev_m": float(sample_grid(dem, x, y)),
                    "susc": float(sample_grid(susc, x, y)),
                    "dist_river_m": float(sample_grid(dist_river_m, x, y))})

bldg_out = []
for b in buildings:
    c = b["geometry_ll"].centroid
    (x, y) = to_utm_pts([(c.x, c.y)])[0]
    e = float(sample_grid(dem, x, y))
    if np.isfinite(e):
        bldg_out.append({"lon": c.x, "lat": c.y, "elev_m": e})

places_out = [{"lon": p["lon"], "lat": p["lat"], "name": p["name"], "class": p["class"]}
              for p in places if p["name"] and p["class"] in (
                  "quarter", "suburb", "town", "city", "village", "neighbourhood", "hamlet")]

with open(RAW / "nasa_power_dagupan_daily_1981_2026.json") as f:
    power = json.load(f)["properties"]["parameter"]
daily = pd.DataFrame({
    "date": pd.to_datetime(list(power["T2M"].keys()), format="%Y%m%d"),
    "RAIN": list(power["PRECTOTCORR"].values()),
    "T2M_MAX": list(power["T2M_MAX"].values()),
    "T2M_MIN": list(power["T2M_MIN"].values()),
    "RH2M": list(power["RH2M"].values()),
    "T2M": list(power["T2M"].values()),
}).set_index("date").sort_index()
daily = daily[(daily > -900).all(axis=1)]

def hi_c(t, rh):
    tf = t * 9 / 5 + 32
    return ((-42.379 + 2.04901523 * tf + 10.14333127 * rh - 0.22475541 * tf * rh
             - 6.83783e-3 * tf ** 2 - 5.481717e-2 * rh ** 2 + 1.22874e-3 * tf ** 2 * rh
             + 8.5282e-4 * tf * rh ** 2 - 1.99e-6 * tf ** 2 * rh ** 2) - 32) * 5 / 9

daily["HI"] = hi_c(daily["T2M_MAX"].values, daily["RH2M"].values)

census = pd.read_csv(PROC / "psa_2020_dagupan_barangay_population.csv").rename(columns={"Barangay": "barangay"})
watch = pd.read_csv(PROC / "climateshield_dagupan_barangay_watchlist.csv")
brgy = census.merge(
    watch.drop(columns=["census_2020", "urban"]).rename(columns={"geometry anchor": "anchor"}),
    on="barangay", how="left")

land_elevs = dem[(land_mask == 1) & np.isfinite(dem)]
land_elevs_sorted = np.sort(land_elevs[~np.isnan(land_elevs)])

MOTORABLE = ("trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "service")
from pyproj import Transformer as _Tr
_to_utm = _Tr.from_crs("EPSG:4326", DST_CRS, always_xy=True).transform

_gnodes, _gedges = {}, {}
for w in ways.values():
    t = w.get("tags", {})
    if t.get("highway") not in MOTORABLE:
        continue
    ids = [str(n) for n in w.get("nodes", []) if str(n) in nodes]
    for a, b in zip(ids[:-1], ids[1:]):
        for nid in (a, b):
            if nid not in _gnodes:
                n = nodes[nid]
                x, y = _to_utm(n["lon"], n["lat"])
                ri = int(np.clip(round((utm_transform.f - y) / 30 - 0.5), 0, utm_h - 1))
                ci = int(np.clip(round((x - utm_transform.c) / 30 - 0.5), 0, utm_w - 1))
                _gnodes[nid] = {"lon": n["lon"], "lat": n["lat"],
                                "elev": float(dem[ri, ci]) if np.isfinite(dem[ri, ci]) else 0.0}
        xa, ya, xb, yb = _gnodes[a]["lon"], _gnodes[a]["lat"], _gnodes[b]["lon"], _gnodes[b]["lat"]
        import math
        seg = math.hypot((xb - xa) * 111320 * np.cos(np.radians((ya + yb) / 2)), (yb - ya) * 110540)
        for s_, e_ in ((a, b), (b, a)):
            _gedges.setdefault(s_, []).append((e_, seg, t["highway"], t.get("name", "")))
with open(OUT / "street_graph.pkl", "wb") as f:
    pickle.dump({"nodes": _gnodes, "edges": _gedges}, f)
print(f"street graph: {len(_gnodes):,} nodes, "
      f"{sum(len(v) for v in _gedges.values()) // 2:,} undirected segments")

# chart-background canvas, synthesized from layers this repo may distribute
# (Copernicus hillshade + land/water/river masks). The earlier version bulk-downloaded
# Esri Light Gray Canvas tiles; Esri's terms allow live use with attribution, not stored
# copies, so the raster stopped shipping with the repo (docs/SOURCES.md section 9).
_rel = hillshade.astype("float32") / 255.0
basemap_utm = np.array([245, 239, 227], dtype="float32")[None, None, :] * \
    (0.80 + 0.20 * _rel)[:, :, None]
_water = ((city_mask > 0) & (land_mask == 0)) | (dist_river_m <= 0) | (dist_coast_m <= 0)
basemap_utm[_water] = np.array([199, 209, 220], dtype="float32")[None, :] * \
    (0.90 + 0.10 * np.clip(_rel[_water], 0, 1))[:, None]
basemap_utm = np.clip(basemap_utm, 0, 255).astype("uint8")
np.save(OUT / "basemap_utm.npy", basemap_utm)
print(f"basemap synthesized from hillshade + land/water masks ({int(_water.sum()):,} water cells)")

meta = {
    "utm_transform": [utm_transform.a, utm_transform.b, utm_transform.c, utm_transform.d, utm_transform.e, utm_transform.f],
    "crs": DST_CRS, "height": int(utm_h), "width": int(utm_w),
    "city_bounds_4326": [float(v) for v in city.total_bounds],
    "active_land_km2": float(land_mask.sum() * 0.0009),
    "official_land_km2": 44.47,
    "psa_pop_2020": int(census["popn"].sum()),
    "n_buildings": len(bldg_out), "n_facilities": len(fac_out), "n_roads": len(roads_out),
    "avg_hh_size": 4.15,
}
pct_cal = {p: float(np.percentile(land_elevs_sorted, p)) for p in [5, 10, 25, 40, 50, 58, 70, 85, 95]}

np.save(OUT / "dem_utm.npy", dem)
np.save(OUT / "susc.npy", susc)
np.save(OUT / "land_mask.npy", land_mask)
np.save(OUT / "dist_river.npy", dist_river_m)
np.save(OUT / "dist_coast.npy", dist_coast_m)
np.save(OUT / "pop_utm.npy", pop_utm)
np.save(OUT / "hillshade.npy", hillshade.astype("uint8"))
np.savez(OUT / "elev_calibration.npz", sorted=land_elevs_sorted, percentiles=np.array(list(pct_cal.values())),
         percent_labels=np.array(list(pct_cal.keys())))
np.save(OUT / "city_mask.npy", city_mask.astype("uint8"))

with open(OUT / "grid_meta.json", "w") as f:
    json.dump(meta, f, indent=1)
with open(OUT / "roads.pkl", "wb") as f:
    pickle.dump(roads_out, f)
with open(OUT / "facilities.pkl", "wb") as f:
    pickle.dump(fac_out, f)
with open(OUT / "buildings.pkl", "wb") as f:
    pickle.dump(bldg_out, f)
with open(OUT / "places.pkl", "wb") as f:
    pickle.dump(places_out, f)
with open(OUT / "rivers.pkl", "wb") as f:
    pickle.dump([{"ll": list(r.geometry.coords), "class": r["class"]} for _, r in g_water.iterrows()], f)
with open(OUT / "coast.pkl", "wb") as f:
    pickle.dump([{"ll": list(r.geometry.coords)} for _, r in g_coast.iterrows()], f)
daily.to_csv(OUT / "daily.csv")
brgy.to_csv(OUT / "barangay_table.csv", index=False)
live_cache = {"ok": False}
with open(OUT / "live_cache.json", "w") as f:
    json.dump(live_cache, f)

print(f"artifacts written to {OUT}")
print(f"  dem {dem.shape} | land cells {int(land_mask.sum()):,} | active-land {meta['active_land_km2']:.1f} km2")
print(f"  roads {len(roads_out)} | buildings {len(bldg_out)} | facilities {len(fac_out)} | places {len(places_out)}")
print(f"  daily rows {len(daily):,} | barangay rows {len(brgy)}")
print(f"  calibration water levels by land-flood share: " + ", ".join(f"p{k}={v:.2f}m" for k, v in pct_cal.items()))

"""Build the heat-support layers (water sources + shade/green areas) from the raw OSM extract.

Run:  python -m app.heatlayers
Writes (only what actually exists in the extract):
  data/app_layers/heat_water_points.csv   refilling stations, wells, towers, fountains
  data/app_layers/heat_water_areas.geojson  ponds / fishponds / open water polygons
  data/app_layers/heat_shade.geojson      parks, gardens, grass, forest, scrub polygons
  data/app_layers/heat_shade_points.csv   individual shade trees
Everything is stdlib-only and clipped to the Dagupan city boundary polygon.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
LAY = ROOT / "data" / "app_layers"

WATER_POINT_KIND = {
    "shop=water": "water refilling station",
    "amenity=drinking_water": "drinking water",
    "amenity=water_point": "water point",
    "amenity=fountain": "fountain",
    "man_made=water_well": "well",
    "man_made=water_tower": "water tower",
    "man_made=water_tank": "water tank",
    "emergency=water_tank": "emergency water tank",
    "man_made=reservoir_covered": "reservoir",
    "man_made=water_works": "waterworks",
    "natural=spring": "spring",
}
SHADE_TAGS = {
    ("leisure", "park"): "park",
    ("leisure", "garden"): "garden",
    ("leisure", "recreation_ground"): "recreation ground",
    ("leisure", "nature_reserve"): "nature reserve",
    ("leisure", "playground"): "playground",
    ("landuse", "grass"): "grass",
    ("landuse", "forest"): "forest",
    ("landuse", "wood"): "wood",
    ("landuse", "meadow"): "meadow",
    ("landuse", "village_green"): "village green",
    ("landuse", "greenfield"): "green field",
    ("landuse", "orchard"): "orchard",
    ("landuse", "cemetery"): "cemetery green",
    ("landcover", "trees"): "tree cover",
    ("natural", "wood"): "wood",
    ("natural", "scrub"): "scrub",
    ("natural", "grassland"): "grassland",
    ("natural", "wetland"): "wetland / mangrove",
}
MIN_AREA = 2e-9


def _city_ring() -> list[list[float]]:
    d = json.loads((RAW / "dagupan_city_boundary.geojson").read_text(encoding="utf-8"))
    geom = d.get("geometry") or d["features"][0]["geometry"]
    return geom["coordinates"][0]


def _inside(lon: float, lat: float, ring: list[list[float]]) -> bool:
    hit = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def _way_coords(w: dict, nodes: dict) -> list[list[float]]:
    return [[nodes[str(n)]["lon"], nodes[str(n)]["lat"]] for n in w.get("nodes", []) if str(n) in nodes]


def _closed(pts: list[list[float]]) -> bool:
    return len(pts) > 3 and pts[0] == pts[-1]


def _area(pts: list[list[float]]) -> float:
    s = 0.0
    for i in range(len(pts) - 1):
        s += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return abs(s) / 2.0


def _centroid(pts: list[list[float]]) -> tuple[float, float]:
    return (sum(p[0] for p in pts[:-1]) / max(1, len(pts) - 1),
            sum(p[1] for p in pts[:-1]) / max(1, len(pts) - 1))


def _stitch(polys: list[list[list[float]]]) -> list[list[float]] | None:
    if not polys:
        return None
    segs = [list(p) for p in polys]
    ring = segs.pop(0)
    while ring[0] != ring[-1] and segs:
        for i, s in enumerate(segs):
            if s[0] == ring[-1]:
                ring += s[1:]
            elif s[-1] == ring[-1]:
                ring += list(reversed(s))[1:]
            elif ring[0] == s[-1]:
                ring = s[:-1] + ring
            elif ring[0] == s[0]:
                ring = list(reversed(s))[:-1] + ring
            else:
                continue
            segs.pop(i)
            break
        else:
            break
    return ring if len(ring) > 3 and ring[0] == ring[-1] else None


def build() -> dict:
    osm = json.loads((RAW / "osm_dagupan_features_raw.json").read_text(encoding="utf-8"))
    nodes, ways = osm["nodes"], osm["ways"]
    ring = _city_ring()

    water_pts: list[dict] = []
    water_area_feats: list[dict] = []
    shade_feats: list[dict] = []
    trees: list[dict] = []

    def add_point(kind: str, name: str, lon: float, lat: float, bucket: list[dict]) -> None:
        if _inside(lon, lat, ring):
            bucket.append({"kind": kind, "name": name, "lat": round(lat, 6), "lon": round(lon, 6)})

    for src in (nodes, ways):
        for e in src.values():
            t = e.get("tags") or {}
            if t.get("natural") == "tree":
                if "lat" in e:
                    add_point("shade tree", t.get("name", ""), e["lon"], e["lat"], trees)
                else:
                    pts = _way_coords(e, nodes)
                    if pts:
                        lon, lat = _centroid(pts)
                        add_point("shade tree", t.get("name", ""), lon, lat, trees)
            if t.get("natural") == "water" and "lat" not in e:
                pts = _way_coords(e, nodes)
                if _closed(pts) and _inside(*_centroid(pts), ring):
                    water_area_feats.append({
                        "type": "Feature",
                        "properties": {"kind": t.get("water", "water"), "name": t.get("name", "")},
                        "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in pts]]},
                    })
            for tag, kind in WATER_POINT_KIND.items():
                k, v = tag.split("=", 1)
                if t.get(k) != v:
                    continue
                name = t.get("name", "")
                if "lat" in e:
                    add_point(kind, name, e["lon"], e["lat"], water_pts)
                else:
                    pts = _way_coords(e, nodes)
                    if pts:
                        lon, lat = _centroid(pts)
                        add_point(kind, name, lon, lat, water_pts)
                break

    for w in ways.values():
        t = w.get("tags") or {}
        kind = SHADE_TAGS.get(("landuse", t.get("landuse", ""))) or \
            SHADE_TAGS.get(("leisure", t.get("leisure", ""))) or \
            SHADE_TAGS.get(("natural", t.get("natural", ""))) or \
            SHADE_TAGS.get(("landcover", t.get("landcover", "")))
        if not kind:
            continue
        pts = _way_coords(w, nodes)
        if not _closed(pts) or not _inside(*_centroid(pts), ring):
            continue
        if _area(pts) < MIN_AREA:
            continue
        shade_feats.append({
            "type": "Feature",
            "properties": {"kind": kind, "name": t.get("name", "")},
            "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in pts]]},
        })

    for rel in (osm.get("relations") or {}).values():
        t = rel.get("tags") or {}
        if t.get("type") != "multipolygon":
            continue
        outers = []
        for mem in rel.get("members", []):
            if mem.get("type") != "way" or mem.get("role", "outer") not in ("outer", ""):
                continue
            w = ways.get(str(mem.get("ref")))
            if w is None:
                continue
            pts = _way_coords(w, nodes)
            if len(pts) >= 2:
                outers.append(pts)
        pts = _stitch(outers)
        if not pts or not _inside(*_centroid(pts), ring):
            continue
        kind = SHADE_TAGS.get(("landuse", t.get("landuse", ""))) or \
            SHADE_TAGS.get(("leisure", t.get("leisure", ""))) or \
            SHADE_TAGS.get(("natural", t.get("natural", ""))) or \
            SHADE_TAGS.get(("landcover", t.get("landcover", "")))
        if kind:
            if _area(pts) >= MIN_AREA:
                shade_feats.append({
                    "type": "Feature",
                    "properties": {"kind": kind, "name": t.get("name", "")},
                    "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in pts]]},
                })
        elif t.get("natural") == "water" and _area(pts) >= MIN_AREA:
            water_area_feats.append({
                "type": "Feature",
                "properties": {"kind": t.get("water", "water"), "name": t.get("name", "")},
                "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in pts]]},
            })

    LAY.mkdir(parents=True, exist_ok=True)
    with open(LAY / "heat_water_points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kind", "name", "lat", "lon"])
        w.writeheader()
        w.writerows(sorted(water_pts, key=lambda r: r["kind"]))
    with open(LAY / "heat_shade_points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kind", "name", "lat", "lon"])
        w.writeheader()
        w.writerows(sorted(trees, key=lambda r: r["kind"]))
    for fn, feats in (("heat_water_areas.geojson", water_area_feats), ("heat_shade.geojson", shade_feats)):
        (LAY / fn).write_text(
            json.dumps({"type": "FeatureCollection", "features": sorted(
                feats, key=lambda f: (f["properties"]["name"], f["properties"]["kind"]))},
                ensure_ascii=False), encoding="utf-8")
    return {
        "water_points": len(water_pts),
        "water_areas": len(water_area_feats),
        "shade_areas": len(shade_feats),
        "shade_trees": len(trees),
        "water_kinds": {k: sum(1 for r in water_pts if r["kind"] == k) for k in sorted({r["kind"] for r in water_pts})},
        "shade_kinds": {k: sum(1 for f in shade_feats if f["properties"]["kind"] == k)
                        for k in sorted({f["properties"]["kind"] for f in shade_feats})},
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=False))

"""Barangay boundaries: official-polygon import + derived interim neighborhoods.

Reality (checked 2026-10-07): no public dataset carries Dagupan's barangay polygons.
Overpass queries inside the city found no admin_level=10 relations for Dagupan (only fishpond
patches with names like China/Korea/Russia); PSA/NAMRIA barangay boundaries are released through
LGU/agency requests — letters drafted in docs/future_real_operations/.

Thus the module serves TWO layers, used transparently by the app:
  1) OFFICIAL — drop a boundary file at data/app_layers/brgy_boundaries.geojson (one Polygon
     Feature per barangay, properties {"name": ...} resolvable to the census list) and run
     `python app/brgypoly.py`; everything (masks, impact, choropleth) switches to it.
  2) DERIVED-INTERIM (what ships today) — anchor-based Voronoi neighborhoods clipped to the city
     boundary: contiguous city-wide coverage (every land cell belongs to exactly one barangay),
     a real upgrade over the old 600 m anchor circles. Labeled DERIVED wherever visible.

Rasterization is pure PIL/shapely/scipy — rasterio/GDAL are not used (blocked on this machine).
"""
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np

import geo

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OFFICIAL_GEOJSON = LAY / "brgy_boundaries.geojson"     # user-dropped official/admin file (input)
OFFICIAL_PROCESSED = LAY / "brgy_boundaries_processed.geojson"  # map layer once official is processed
DERIVED_NPZ = LAY / "brgy_cells.npz"                    # mask grid + census-ordered names (either source)
DERIVED_GEOJSON = LAY / "brgy_boundaries_derived.geojson"  # map layer for the derived variant
META = LAY / "brgy_boundaries_meta.json"

_ALIAS = {"barangayi": "barangayi"}  # (poblacion) suffixes are stripped by _norm anyway


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def match_official_name(census_name, feature_names):
    n = _norm(census_name)
    for f in feature_names:
        if _norm(f) == n:
            return f
    for f in feature_names:
        if n and n in _norm(f):
            return f
    return None


def _city_polygon_utm():
    """OSM city outline in UTM. Interior holes in the source polygon swallow three real barangay
    anchors (Barangay I/II, Lomboy sit inside river-arm cutouts), so clip to the outline with a
    100 m tolerance buffer."""
    from shapely.geometry import Polygon, shape
    d = json.load(open(RAW / "dagupan_city_boundary.geojson", encoding="utf-8"))
    g = shape(d["geometry"])
    if g.geom_type != "Polygon":
        raise ValueError(f"unexpected city geometry {g.geom_type}")
    outline = Polygon(np.asarray(g.exterior.coords, float))
    return Polygon(_ring_to_utm(outline.exterior.coords)).buffer(100.0)


def _ring_to_utm(ring):
    pts = np.asarray(ring, float)
    X, Y = geo.ll_to_utm51(pts[:, 0], pts[:, 1])
    return np.column_stack([X, Y])


def _voronoi_cells_utm(anchors_utm, radius_factor=12.0):
    """Voronoi cell polygon per anchor, made finite by adding mirror points far outside."""
    from scipy.spatial import Voronoi
    from shapely.geometry import Polygon
    pts = np.asarray(anchors_utm, float)
    centre = pts.mean(axis=0)
    vec = pts - centre
    dist = np.maximum(np.linalg.norm(vec, axis=1, keepdims=True), 1e-9)
    span = float(np.abs(vec).max()) * radius_factor
    far = centre + vec / dist * span
    vor = Voronoi(np.vstack([pts, far]))
    cells = []
    for i in range(len(pts)):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg or len(reg) < 3:
            cells.append(None)
            continue
        cells.append(Polygon(vor.vertices[reg]))
    return cells


def _iter_polygons(p):
    if p is None or p.is_empty:
        return []
    if p.geom_type == "Polygon":
        return [p]
    return [g for g in getattr(p, "geoms", []) if g.geom_type == "Polygon"]


def _utm_poly_to_lonlat(poly, simplify_m=40.0):
    out = []
    for g in _iter_polygons(poly):
        p = g.simplify(simplify_m, preserve_topology=True)
        if p.is_empty:
            continue
        rings = [np.array(p.exterior.coords)] + [np.array(r.coords) for r in p.interiors]
        coords = []
        for ring in rings:
            LON, LAT = geo.utm51_to_ll(ring[:, 0], ring[:, 1])
            coords.append([[float(a), float(b)] for a, b in zip(LON, LAT)])
        out.append(dict(type="Polygon", coordinates=coords))
    if not out:
        return None
    return out[0] if len(out) == 1 else dict(type="MultiPolygon", coordinates=[f["coordinates"] for f in out])


def _rasterize(polys_utm, h, w, transform):
    """Grid of barangay index or -1; ties broken by painting small cells last (they win)."""
    from PIL import Image, ImageDraw
    S = 4
    img = Image.new("L", (w * S, h * S), 0)
    draw = ImageDraw.ImageDraw(img)

    def to_px(x, y):
        return ((x - transform.c) / 30.0 - 0.5) * S, ((transform.f - y) / 30.0 - 0.5) * S

    order = sorted(range(len(polys_utm)), key=lambda i: (min(g.area for g in _iter_polygons(polys_utm[i]))
                                                        if polys_utm[i] else 0, ))
    for bi in order:  # ascending area: small downtown quarters painted last, so they win
        for p in _iter_polygons(polys_utm[bi]):
            ext = [to_px(x, y) for x, y in p.exterior.coords]
            if len(ext) < 3:
                continue
            draw.polygon(ext, fill=bi + 1)
            for ring in p.interiors:
                draw.polygon([to_px(x, y) for x, y in ring.coords], fill=0)
    arr = np.asarray(img, dtype=np.float32).reshape(h, S, w, S).mean(axis=(1, 3))
    idx = np.rint(arr).astype(np.int16)
    idx[arr <= 0.5] = -1          # majority coverage: small barangays keep their core cells
    idx[idx > 0] -= 1
    idx[idx >= len(polys_utm)] = -1
    return idx


def _write(census_names, polys, idx, source, provenance, map_path):
    feats = []
    for nm, p in zip(census_names, polys):
        g = _utm_poly_to_lonlat(p) if p is not None else None
        if g:
            feats.append(dict(type="Feature", properties=dict(name=nm, source=source), geometry=g))
    gj = dict(type="FeatureCollection",
              properties=dict(source=source, provenance=provenance,
                              built_at=datetime.now().isoformat(timespec="minutes")),
              features=feats)
    map_path.write_text(json.dumps(gj), encoding="utf-8")
    np.savez_compressed(DERIVED_NPZ, idx=idx.astype(np.int16),
                        names=np.array(census_names, dtype=object), allow_pickle=True)
    META.write_text(json.dumps(dict(source=source, provenance=provenance, barangays=len(feats),
                                    polygons_file=map_path.name, built=gj["properties"]["built_at"]),
                               indent=1), encoding="utf-8")
    return len(feats)


def _pair(anchor):
    X, Y = geo.ll_to_utm51(anchor["lon"], anchor["lat"])
    return float(X), float(Y)


def _census_frame(L):
    """(names census-ordered, anchors as lon/lat dicts, has_anchor mask) — index-aligned with L.brgy_anchors."""
    names = [b["barangay"] for b in L.brgy_anchors]
    anchor_xy = [(_pair(b["anchor"]) if b["anchor"] else None) for b in L.brgy_anchors]
    return names, anchor_xy


def _assign_nearest(h, w, transform, anchor_xy):
    """Every cell → nearest anchor (exact Voronoi partition, no rasterization aliasing)."""
    from scipy.spatial import cKDTree
    have = [i for i, a in enumerate(anchor_xy) if a is not None]
    if not have:
        return np.full((h, w), -1, np.int16)
    pts = np.asarray([anchor_xy[i] for i in have], float)
    tree = cKDTree(pts)
    rows, cols = np.mgrid[0:h, 0:w]
    X = transform.c + (cols + 0.5) * 30.0
    Y = transform.f - (rows + 0.5) * 30.0
    idx = np.full((h, w), -1, np.int16)
    d, k = tree.query(np.column_stack([X.ravel(), Y.ravel()]), workers=-1)
    nearest = np.asarray(have)[k]
    ok = np.isfinite(d)  # all finite when tree non-empty; guard anyway
    idx.ravel()[ok] = nearest[ok]
    return idx


def build_derived(L, city=None):
    """Voronoi neighborhoods from the anchors, clipped to the buffered OSM city outline.

    Masks come from exact nearest-anchor assignment (identical partition to the Voronoi polygons,
    but with none of the rasterization sliver-loss that starved the tiny downtown quarters);
    polygons (Voronoi ∩ city outline) are kept for the map layer."""
    city = city or _city_polygon_utm()
    names, anchor_xy = _census_frame(L)
    have = [i for i, a in enumerate(anchor_xy) if a is not None]
    pts = np.asarray([anchor_xy[i] for i in have], float)
    vor = _voronoi_cells_utm(pts)
    clipped_all = [None] * len(names)
    for k, i in enumerate(have):
        p = vor[k].intersection(city) if vor[k] is not None else None
        clipped_all[i] = p if (p is not None and not p.is_empty) else None
    idx = _assign_nearest(L.h, L.w, L.transform, anchor_xy)
    # keep only cells inside the buffered city outline; everything else stays unassigned
    from PIL import Image, ImageDraw
    S = 2
    cov_img = Image.new("L", (L.w * S, L.h * S), 0)
    draw = ImageDraw.ImageDraw(cov_img)
    for p in _iter_polygons(city):
        pixels = [(((x - L.transform.c) / 30.0 - 0.5) * S, ((L.transform.f - y) / 30.0 - 0.5) * S)
                  for x, y in p.exterior.coords]
        draw.polygon(list(pixels), fill=1)
    cov = np.asarray(cov_img, dtype=np.float32).reshape(L.h, S, L.w, S).mean(axis=(1, 3)) > 0.3
    idx[~cov] = -1
    n = _write(names, clipped_all, idx,
               source="derived (voronoi from OSM place anchors)",
               provenance="Interim: anchor Voronoi clipped to the buffered OSM city outline. "
                          "Dagupan has no published barangay polygons (OSM admin check 2026-10-07); "
                          "LGU/PSA request in progress. Drop an official "
                          "data/app_layers/brgy_boundaries.geojson and re-run to switch.",
               map_path=DERIVED_GEOJSON)
    return idx, n


def build_official(L, path=OFFICIAL_GEOJSON):
    """Import an official per-barangay boundary GeoJSON; unmatched barangays keep interim cells."""
    from shapely.geometry import shape
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = d.get("features", [])
    fnames = [str((f.get("properties") or {}).get("name") or "") for f in feats]
    names, coords = _census_frame_geojson(L, path)
    polys = []
    unmatched = []
    for nm, gll in zip(names, coords):
        p = None
        if gll is not None:
            from shapely.geometry import Polygon
            rings = [np.asarray(gll[0], float)] + [np.asarray(r, float) for r in gll[1:]]
            utm = [_ring_to_utm(r) for r in rings]
            p = Polygon(utm[0], utm[1:])
        if p is not None and p.is_empty:
            p = None
        if p is None:
            unmatched.append(nm)
        polys.append(p)
    city = _city_polygon_utm()
    idx = _rasterize(polys, L.h, L.w, L.transform)
    if unmatched:  # patch interim Voronoi cells where the official file has no match
        names_d, anchor_xy = _census_frame(L)
        have = [i for i, a in enumerate(anchor_xy) if a is not None]
        pts = np.asarray([anchor_xy[i] for i in have], float)
        vor = _voronoi_cells_utm(pts)
        dcells = [None] * len(names)
        for k, i in enumerate(have):
            c = vor[k].intersection(city) if vor[k] is not None else None
            dcells[i] = c if (c is not None and not c.is_empty) else None
        didx = _rasterize(dcells, L.h, L.w, L.transform)
        fill = (idx < 0) & (didx >= 0)
        idx[fill] = didx[fill]
    n = _write(names, polys, idx,
               source=f"official ({Path(path).name})",
               provenance="Boundaries from an official/administrative file; barangays without a "
                          "matching feature keep interim Voronoi cells."
                          + (" UNMATCHED: " + "; ".join(unmatched) if unmatched else ""),
               map_path=OFFICIAL_PROCESSED)
    return idx, n


def _census_frame_geojson(L, path):
    """names census-ordered + lon/lat rings per barangay matched from `path` features."""
    from shapely.geometry import shape as _shape
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = d.get("features", [])
    fnames = [str((f.get("properties") or {}).get("name") or "") for f in feats]
    names, rings = [], []
    for b in L.brgy_anchors:
        names.append(b["barangay"])
        rings.append(None)
        nm = match_official_name(b["barangay"], fnames)
        if not nm:
            continue
        g = _shape(feats[fnames.index(nm)]["geometry"])
        gg = g if g.geom_type == "Polygon" else g.convex_hull
        rings[-1] = [list(gg.exterior.coords)] + [list(r.coords) for r in gg.interiors]
    return names, rings


def load():
    """(idx census-ordered grid, names, meta) or (None, None, None) if never built."""
    if not (DERIVED_NPZ.exists() and META.exists()):
        return None, None, None
    try:
        with np.load(DERIVED_NPZ, allow_pickle=True) as z:
            idx = z["idx"].astype(np.int16)
            names = [str(x) for x in z["names"]]
        meta = json.loads(META.read_text(encoding="utf-8"))
        return idx, names, meta
    except Exception:
        return None, None, None


def map_layer():
    """GeoJSON dict for map drawing: processed official layer when present, else the derived file."""
    for p in (OFFICIAL_GEOJSON, OFFICIAL_PROCESSED, DERIVED_GEOJSON):
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8")), p
            except Exception:
                continue
    return None, None


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import pandas as pd
    import data_core as dc
    lay = dc.Layers()
    if OFFICIAL_GEOJSON.exists():
        idx, n = build_official(lay)
        print(f"built from OFFICIAL file: {n} map features")
    else:
        idx, n = build_derived(lay)
        print(f"built DERIVED interim neighborhoods: {n} map features, "
              f"{int((idx >= 0).sum()):,} grid cells assigned")
    counts = pd.Series(idx[idx >= 0]).value_counts().sort_index()
    print(f"barangays with cells: {len(counts)} | min {int(counts.min())} | "
          f"median {int(counts.median())} | max {int(counts.max())}")

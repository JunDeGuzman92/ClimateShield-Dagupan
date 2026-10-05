"""Import a better elevation model (e.g. Phil-LiDAR / NAMRIA IfSAR DTM GeoTIFF) without GDAL.

Reads GeoTIFF georeferencing tags with Pillow (ModelPixelScale 33550, ModelTiepoint 33922,
GeoKeyDirectory 34735), supports EPSG:4326 and EPSG:32651, and resamples onto the app's 30 m UTM grid.
Cells the new model covers replace GLO-30; the rest keep GLO-30. The result is saved as dem_override.npy
and picked up by data_core.Layers on next start. Vertical datum is NOT converted — note it in the report.
"""
import io
from pathlib import Path

import numpy as np

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
OVERRIDE = LAY / "dem_override.npy"
REPORT = LAY / "dem_override.json"


def read_geotiff(data):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data)
    tags = im.tag_v2
    arr = np.array(im).astype("float64")
    scale = tags.get(33550)
    tie = tags.get(33922)
    if not scale or not tie:
        raise ValueError("Not a GeoTIFF (missing pixel-scale / tiepoint tags).")
    geokeys = tags.get(34735) or ()
    epsg = None
    for i in range(4, len(geokeys) - 3, 4):
        key, loc, cnt, val = geokeys[i:i + 4]
        if loc != 0:
            continue
        if key == 3072:                      # ProjectedCSTypeGeoKey wins
            epsg = int(val)
        elif key == 2048 and epsg is None:   # GeographicTypeGeoKey
            epsg = int(val)
    nod = tags.get(42113)
    if nod is not None:
        try:
            arr[arr == float(str(nod).strip("\x00"))] = np.nan
        except ValueError:
            pass
    arr[arr < -1000] = np.nan
    sx, sy = float(scale[0]), float(scale[1])
    i0, j0, x0, y0 = float(tie[0]), float(tie[1]), float(tie[3]), float(tie[4])
    return arr, dict(x0=x0 - i0 * sx, y0=y0 + j0 * sy, sx=sx, sy=sy, epsg=epsg)


def resample_to_grid(L, arr, geo):
    import geo as _geo
    rows, cols = np.indices((L.h, L.w))
    X = L.transform.c + (cols + 0.5) * 30.0
    Y = L.transform.f - (rows + 0.5) * 30.0
    if geo["epsg"] in (32651, None) and geo["sx"] > 0.5:
        px, py = X, Y
    elif geo["epsg"] == 4326 or geo["sx"] < 0.01:
        px, py = _geo.utm51_to_ll(X, Y)
    else:
        raise ValueError(f"Unsupported CRS EPSG:{geo['epsg']} — reproject to EPSG:32651 or EPSG:4326 first.")
    fc = (px - geo["x0"]) / geo["sx"] - 0.5
    fr = (geo["y0"] - py) / geo["sy"] - 0.5
    h, w = arr.shape
    c0, r0 = np.floor(fc).astype(int), np.floor(fr).astype(int)
    inside = (c0 >= 0) & (r0 >= 0) & (c0 < w - 1) & (r0 < h - 1)
    out = np.full((L.h, L.w), np.nan)
    a, b = fc - c0, fr - r0
    c0i, r0i = np.clip(c0, 0, w - 2), np.clip(r0, 0, h - 2)
    v = ((1 - a) * (1 - b) * arr[r0i, c0i] + a * (1 - b) * arr[r0i, c0i + 1]
         + (1 - a) * b * arr[r0i + 1, c0i] + a * b * arr[r0i + 1, c0i + 1])
    out[inside] = v[inside]
    return out


def import_dem(L, data, label="uploaded DTM"):
    import json
    arr, geo = read_geotiff(data)
    new = resample_to_grid(L, arr, geo)
    cover = np.isfinite(new) & L.land_mask
    if cover.sum() == 0:
        raise ValueError("The file does not overlap Dagupan's land area.")
    merged = np.where(np.isfinite(new), new, L.dem).astype("float32")
    np.save(OVERRIDE, merged)
    old_land = L.dem[cover]
    rep = dict(label=label, epsg=geo["epsg"], pixel=geo["sx"], land_cells_covered=int(cover.sum()),
               coverage_pct=round(100 * cover.sum() / L.land_mask.sum(), 1),
               old_zero_pct=round(100 * float((old_land == 0).mean()), 1),
               new_zero_pct=round(100 * float((np.abs(new[cover]) < 1e-6).mean()), 1),
               new_median=round(float(np.nanmedian(new[cover])), 2), old_median=round(float(np.median(old_land)), 2),
               note="Vertical datum not converted; check the source's datum (MSL vs ellipsoid).")
    REPORT.write_text(json.dumps(rep), encoding="utf-8")
    return rep


def remove_override():
    for p in (OVERRIDE, REPORT):
        if p.exists():
            p.unlink()

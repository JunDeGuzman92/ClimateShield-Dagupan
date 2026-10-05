"""Pure-numpy WGS84 <-> UTM zone 51N (EPSG:32651) transforms.

Drop-in for the two pyproj calls the app used; accuracy ~1 mm (Krüger series, n^4).
Lets the app run where native PROJ/GDAL DLLs are unavailable or blocked.
"""
import numpy as np

_A = 6378137.0
_F = 1 / 298.257223563
_K0 = 0.9996
_E0 = 500000.0
_LON0 = np.radians(123.0)  # zone 51 central meridian

_n = _F / (2 - _F)
_AA = _A / (1 + _n) * (1 + _n ** 2 / 4 + _n ** 4 / 64)
_alpha = [_n / 2 - 2 * _n ** 2 / 3 + 5 * _n ** 3 / 16,
          13 * _n ** 2 / 48 - 3 * _n ** 3 / 5,
          61 * _n ** 3 / 240]
_beta = [_n / 2 - 2 * _n ** 2 / 3 + 37 * _n ** 3 / 96,
         _n ** 2 / 48 + _n ** 3 / 15,
         17 * _n ** 3 / 480]
_delta = [2 * _n - 2 * _n ** 2 / 3 - 2 * _n ** 3,
          7 * _n ** 2 / 3 - 8 * _n ** 3 / 5,
          56 * _n ** 3 / 15]


def ll_to_utm51(lon, lat):
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    phi = np.radians(lat)
    lam = np.radians(lon) - _LON0
    e = np.sqrt(_F * (2 - _F))
    t = np.sinh(np.arctanh(np.sin(phi)) - e * np.arctanh(e * np.sin(phi)))
    xi = np.arctan2(t, np.cos(lam))
    eta = np.arctanh(np.sin(lam) / np.sqrt(1 + t ** 2))
    xs, ys = xi.copy(), eta.copy()
    for j, a in enumerate(_alpha, start=1):
        xs = xs + a * np.sin(2 * j * xi) * np.cosh(2 * j * eta)
        ys = ys + a * np.cos(2 * j * xi) * np.sinh(2 * j * eta)
    E = _E0 + _K0 * _AA * ys
    N = _K0 * _AA * xs
    return E, N


def utm51_to_ll(E, N):
    E = np.asarray(E, dtype=float)
    N = np.asarray(N, dtype=float)
    xi = N / (_K0 * _AA)
    eta = (E - _E0) / (_K0 * _AA)
    xs, ys = xi.copy(), eta.copy()
    for j, b in enumerate(_beta, start=1):
        xs = xs - b * np.sin(2 * j * xi) * np.cosh(2 * j * eta)
        ys = ys - b * np.cos(2 * j * xi) * np.sinh(2 * j * eta)
    chi = np.arcsin(np.sin(xs) / np.cosh(ys))
    phi = chi.copy()
    for j, d in enumerate(_delta, start=1):
        phi = phi + d * np.sin(2 * j * chi)
    lam = _LON0 + np.arctan2(np.sinh(ys), np.cos(xs))
    return np.degrees(lam), np.degrees(phi)


class Transformer:
    """Minimal pyproj.Transformer shim for EPSG:4326 <-> EPSG:32651."""

    def __init__(self, fn):
        self._fn = fn

    @classmethod
    def from_crs(cls, src, dst, always_xy=True):
        s, d = str(src).upper(), str(dst).upper()
        if s == "EPSG:4326" and d == "EPSG:32651":
            return cls(ll_to_utm51)
        if s == "EPSG:32651" and d == "EPSG:4326":
            return cls(utm51_to_ll)
        raise ValueError(f"geo.Transformer supports only 4326<->32651, got {src}->{dst}")

    def transform(self, x, y):
        a, b = self._fn(x, y)
        if np.ndim(a) == 0:
            return float(a), float(b)
        return a, b

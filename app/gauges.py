"""River/rain gauge adapter for DOST-ASTI PhilSensors (public data page).

PhilSensors has no documented public API; this calls the same JSON endpoints its public web page uses
(session cookie + CSRF token), at most once per 30 minutes (cached). For operational use, file a formal
data request (philsensors.asti.dost.gov.ph/datarequest/terms) or an FOI request.

Finding (Oct 2026): no water-level station inside Dagupan; Pangasinan stations' last public readings are
2015–2022. The adapter reports each station's real last-reading time so stale data is never shown as live.
"""
import http.cookiejar
import json
import math
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
CACHE = LAY / "philsensors_cache.json"
BASE = "https://philsensors.asti.dost.gov.ph"
DAGUPAN = (16.0432, 120.3342)
PARAM = {"1": ("rain", "mm"), "4": ("water level", "m"), "6": ("pressure", "hPa"), "5": ("air temp", "°C")}


class _Session:
    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.op.addheaders = [("User-Agent", "ClimateShieldDagupan/1.0 (community disaster-awareness; low-rate)")]
        html = self.op.open(BASE + "/site/data", timeout=30).read().decode("utf-8", "replace")
        self.tok = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)

    def post(self, path, timeout=40, **kw):
        req = urllib.request.Request(BASE + path, data=urllib.parse.urlencode({"_csrf-frontend": self.tok, **kw}).encode(),
                                     headers={"X-Requested-With": "XMLHttpRequest", "X-CSRF-Token": self.tok}, method="POST")
        return json.loads(self.op.open(req, timeout=timeout).read().decode("utf-8", "replace"))


def _km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))


def fetch_pangasinan(max_age_s=1800, force=False):
    """Returns dict(fetched_at, stations=[...]) — each with last reading, age, distance to Dagupan."""
    if CACHE.exists() and not force:
        c = json.loads(CACHE.read_text(encoding="utf-8"))
        if time.time() - c.get("ts", 0) < max_age_s:
            return c
    try:
        s = _Session()
        rows = s.post("/station/data-visualization", timeout=120)
    except Exception as e:
        if CACHE.exists():
            c = json.loads(CACHE.read_text(encoding="utf-8"))
            c["error"] = f"PhilSensors unreachable ({type(e).__name__}) — showing cache from {c.get('fetched_at')}"
            return c
        return dict(ts=0, fetched_at=None, stations=[], error=f"PhilSensors unreachable ({type(e).__name__})")
    pang = [r for r in rows if "pangasinan" in str(r.get("province", "")).lower()]
    keep = [r for r in pang if "water" in str(r.get("type_name", "")).lower() or "rain" in str(r.get("type_name", "")).lower()
            or "vaisala" in str(r.get("type_name", "")).lower()]
    out = []
    for r in keep:
        try:
            meta = s.post("/station/modal", station_id=r["station_id"])
            st = meta.get("station", {})
            data = meta.get("data", []) or []
            last = max(data, key=lambda x: x.get("datetime_read", "")) if data else {}
            lat, lon = float(st.get("latitude") or 0), float(st.get("longitude") or 0)
            ts = last.get("datetime_read", "")
            age_h = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600 if ts else None
            vals = {PARAM[k][0]: f"{v} {PARAM[k][1]}" for k, v in last.items() if k in PARAM and v not in (None, "ERR")}
            out.append(dict(station_id=r["station_id"], location=r["location"], type=r["type_name"], lat=lat, lon=lon,
                            km_from_dagupan=round(_km(*DAGUPAN, lat, lon), 1) if lat else None,
                            last_reading=ts, age_hours=round(age_h, 1) if age_h is not None else None,
                            live=bool(age_h is not None and age_h < 3), values=vals,
                            water_level_m=float(last["4"]) if last.get("4") not in (None, "ERR", "") else None,
                            status=st.get("status_description", "")))
            time.sleep(0.3)
        except Exception as e:
            out.append(dict(station_id=r.get("station_id"), location=r.get("location"), type=r.get("type_name"),
                            error=f"{type(e).__name__}"))
    res = dict(ts=time.time(), fetched_at=datetime.now().isoformat(timespec="minutes"), stations=out)
    CACHE.write_text(json.dumps(res), encoding="utf-8")
    return res

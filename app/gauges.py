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

import pandas as pd

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
CACHE = LAY / "philsensors_cache.json"
METAR_CACHE = LAY / "metar_cache.json"
DAM_CACHE = LAY / "dam_cache.json"
BASE = "https://philsensors.asti.dost.gov.ph"
DAGUPAN = (16.0432, 120.3342)
UA = "ClimateShieldDagupan/1.0 (community disaster-awareness; low-rate polling)"

# aviation stations near enough to sanity-check the model grid (name, ICAO, lat, lon, note)
METAR_STATIONS = [
    ("Laoag Intl (RPLI)", "16.0432-north", "RPLI", 18.1817, 120.5311, "north coast, sea-level"),
    ("Clark Intl (RPLC)", "15.19-south", "RPLC", 15.1858, 120.5590, "central plain, sea-level"),
]


def _ua():
    return {"User-Agent": UA}


def read_json_cache(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def fetch_metar(max_age_s=1800, force=False):
    """Nearest real station observations (aviationweather.gov, free, no key, ~30–60 min cadence).

    Neither station is Dagupan — Laoag ≈238 km NNW, Clark ≈95 km S — so these read as a
    *sanity check on the model*, not city truth. Returns cached dict with per-station obs time.
    """
    prev = read_json_cache(METAR_CACHE)
    if prev and not force and time.time() - prev.get("ts", 0) < max_age_s and prev.get("stations"):
        return prev
    out = []
    for label, _key, icao, la, lo, note in METAR_STATIONS:
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(
                        f"https://aviationweather.gov/api/data/metar?ids={icao}&format=json",
                        headers=_ua()), timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            m = (d or [None])[0] or {}
            obs = m.get("obsTime")
            t, td = m.get("temp"), m.get("dewp")
            rh = None
            if t is not None and td is not None:
                try:
                    rh = round(100 * math.exp((17.625 * td) / (243.04 + td)
                                             - (17.625 * t) / (243.04 + t)), 1)
                except Exception:
                    rh = None
            out.append(dict(station=label, icao=icao, lat=la, lon=lo, note=note,
                            km_from_dagupan=round(_km(*DAGUPAN, la, lo), 0),
                            obs_time=obs, temp_c=t, dewpoint_c=td, rh_pct=rh,
                            wind_kt=m.get("wspd"), visib=m.get("visib"), raw=(m.get("rawOb") or "")[:90]))
        except Exception as e:
            out.append(dict(station=label, icao=icao, lat=la, lon=lo, note=note, error=f"{type(e).__name__}"))
    res = dict(ts=time.time(), fetched_at=datetime.now().isoformat(timespec="minutes"), stations=out)
    try:
        METAR_CACHE.write_text(json.dumps(res), encoding="utf-8")
    except Exception:
        pass
    if not any(s.get("temp_c") is not None for s in out) and prev and prev.get("stations"):
        prev = dict(prev)
        prev["error"] = "aviationweather.gov unreachable — showing the stored check"
        return prev
    return res


AGNO_DAMS = ("Ambuklao", "Binga", "San Roque")
FLOOD_PAGE = "https://www.pagasa.dost.gov.ph/flood"


def _dam_table_rows(html):
    from html.parser import HTMLParser

    class T(HTMLParser):
        def __init__(self):
            super().__init__()
            self.rows, self.cur, self.cell, self.in_td = [], [], "", False

        def handle_starttag(self, tag, attrs):
            if tag in ("td", "th"):
                self.in_td = True
                self.cell = dict(attrs).get("class", "")

        def handle_endtag(self, tag):
            if tag in ("td", "th"):
                self.in_td = False
            if tag == "tr" and self.cur:
                self.rows.append(self.cur)
                self.cur = []

        def handle_data(self, data):
            if self.in_td:
                self.cur.append((self.cell, data.strip()))

    p = T()
    p.feed(html)
    return p.rows


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return None


def parse_dams(html, fetched_at):
    """Parse the PAGASA dam table + Agno basin status out of the flood page HTML.

    Pure function (no network) — tested against saved page fixtures in tests/.
    Each data row is accepted only if RWL − NHWL matches the table's own deviation
    column within 0.03 m; anything else is dropped, never shown.
    Returns dict(dams=[...], basin={...}|None, obs_label).
    """
    rows = _dam_table_rows(html)
    dams = []
    for r in rows:
        cells = [t for _, t in r]
        if not cells or cells[0] not in AGNO_DAMS or len(cells) < 9:
            continue
        name, tcell, rwl, a24, dev, nhwl, dev_nhwl, rule, dev_rule = cells[:9]
        rwl, dev24, nhwl, devn = _num(rwl), _num(dev) if a24.strip() == "24" else None, _num(nhwl), _num(dev_nhwl)
        if rwl is None or nhwl is None:
            continue
        if devn is not None and abs((rwl - nhwl) - devn) > 0.03:
            continue  # cross-check failed: don't trust this row
        gate = " · ".join(c for c in cells[9:] if c) or None
        dams.append(dict(name=name, obs_time=tcell, rwl_m=rwl, dev24h_m=dev24, nhwl_m=nhwl,
                         over_nhwl_m=round(rwl - nhwl, 2), rule_m=_num(rule), dev_rule_m=_num(dev_rule),
                         gates=gate))
    basin = None
    for m in re.finditer(r"<a([^>]*)>([^<]{0,60})</a>", html):
        attrs, txt = m.group(1), m.group(2).strip()
        if "agno.pdf" in attrs:
            level = "non-flood" if "non-flood" in attrs else (
                "flood-advisory" if "advisory" in attrs else "flood-watch" if "watch" in attrs else "unknown")
            basin = dict(status=txt.strip() or None, level=level,
                         target="Agno river basin", link="https://pubfiles.pagasa.dost.gov.ph/pagasaweb/files/hmd/riverbasin/agno.pdf")
            break
    # no reliable observation date is published — only e.g. '08:00 AM'. Assume same-day,
    # rolling back a day if we fetch before the stated hour.
    obs_label = (dams[0]["obs_time"] if dams else None)
    obs_date = None
    if obs_label:
        m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)", obs_label, re.I)
        if m:
            import datetime as _dt
            now = _dt.datetime.now()
            hr = int(m.group(1)) % 12 + (12 if m.group(3).upper() == "PM" else 0)
            obs = now.replace(hour=hr, minute=int(m.group(2)), second=0, microsecond=0)
            if obs > now:
                obs = obs - _dt.timedelta(days=1)
            obs_date = obs.strftime("%b %d %H:%M")
    return dict(dams=dams, basin=basin, obs_label=obs_date)


def fetch_dams(max_age_s=6 * 3600, force=False):
    """PAGASA dam table + Agno basin status, parsed from the public /flood page (slow server: tolerant).

    Agno chain dams Ambuklao→Binga→San Roque. Columns verified by cross-check
    (RWL − NHWL == the table's own Deviation column, e.g. San Roque 283.15 − 280.00 = 3.15).
    Gate/outflow cells parse when present. Basin status anchor (agno.pdf, e.g. 'Non-Flood Watch')
    included. No reliable observation *date* is published, only e.g. '08:00 AM' — date is assumed
    same-day, rolling back a day if we fetch before the stated hour.
    """
    prev = read_json_cache(DAM_CACHE)
    if prev and not force and time.time() - prev.get("ts", 0) < max_age_s and prev.get("dams"):
        return prev
    try:
        with urllib.request.urlopen(urllib.request.Request(FLOOD_PAGE, headers=_ua()), timeout=75) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:
        if prev and prev.get("dams"):
            prev = dict(prev)
            prev["error"] = f"pagasa.dost.gov.ph unreachable ({type(e).__name__}) — showing the stored check"
            return prev
        return dict(ts=0, fetched_at=None, obs_label=None, dams=[], basin=None,
                    error=f"pagasa.dost.gov.ph unreachable ({type(e).__name__})")
    parsed = parse_dams(html, fetched_at=None)
    dams, basin, obs_date = parsed["dams"], parsed["basin"], parsed["obs_label"]
    res = dict(ts=time.time(), fetched_at=datetime.now().isoformat(timespec="minutes"),
               obs_label=obs_date, dams=dams, basin=basin,
               note="Dam tables: PAGASA Flood page · San Roque releases flow down the Agno toward Dagupan")
    try:
        DAM_CACHE.write_text(json.dumps(res), encoding="utf-8")
    except Exception:
        pass
    if not dams and prev and prev.get("dams"):
        prev = dict(prev)
        prev["error"] = "dam table unparseable this check — showing the stored check"
        return prev
    return res
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


def read_cache():
    """Instant, no network: whatever the last successful (or partial) check stored."""
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _save(cache):
    CACHE.write_text(json.dumps(cache), encoding="utf-8")


def _station_row(s, r):
    meta = s.post("/station/modal", station_id=r["station_id"], timeout=25)
    st = meta.get("station", {})
    data = meta.get("data", []) or []
    last = max(data, key=lambda x: x.get("datetime_read", "")) if data else {}
    lat, lon = float(st.get("latitude") or 0), float(st.get("longitude") or 0)
    ts = last.get("datetime_read", "")
    age_h = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600 if ts else None
    vals = {PARAM[k][0]: f"{v} {PARAM[k][1]}" for k, v in last.items() if k in PARAM and v not in (None, "ERR")}
    return dict(station_id=r["station_id"], location=r["location"], type=r["type_name"], lat=lat, lon=lon,
                km_from_dagupan=round(_km(*DAGUPAN, lat, lon), 1) if lat else None,
                last_reading=ts, age_hours=round(age_h, 1) if age_h is not None else None,
                live=bool(age_h is not None and age_h < 3), values=vals,
                water_level_m=float(last["4"]) if last.get("4") not in (None, "ERR", "") else None,
                status=st.get("status_description", ""))


def summary(ps):
    """Panel-ready view of a cached check: split good/error rows, live count, newest reading,
    and a km-sorted table with human ages. Pure function — no network."""
    sts = [x for x in (ps or {}).get("stations", []) if "error" not in x]
    errs = [x for x in (ps or {}).get("stations", []) if "error" in x]
    live_n = sum(1 for x in sts if x.get("live"))
    newest = max((x["last_reading"] for x in sts if x.get("last_reading")), default="—")

    def age(x):
        ah = x.get("age_hours")
        if ah is None:
            return "—"
        return f"{ah / 24 / 365:.1f} yr" if ah > 24 * 365 else f"{ah / 24:.0f} d"

    rows = pd.DataFrame([dict(station=x["location"], type=x["type"], km=x.get("km_from_dagupan"),
                              last_reading=x.get("last_reading") or "—", age=age(x),
                              latest_values=", ".join(f"{k} {v}" for k, v in (x.get("values") or {}).items()))
                         for x in sts],
                        columns=["station", "type", "km", "last_reading", "age", "latest_values"])
    rows = rows.sort_values("km", na_position="last")
    return dict(sts=sts, errs=errs, live_n=live_n,
                water_n=sum(1 for x in sts if "water" in str(x.get("type", "")).lower()),
                newest=newest, rows=rows)
def fetch_pangasinan(max_age_s=1800, force=False, nearest=8, progress=None):
    """Refreshed check of Pangasinan PhilSensors stations.

    The page NEVER waits for this on load — it renders `read_cache()` instantly and only calls this when the
    user presses Refresh (or the cache is empty). The 2,878-station catalogue is cached for 7 days and re-used;
    live readings are pulled only for the `nearest` water/rain stations, since the panel's question is
    'is anything alive near Dagupan?'. Failures degrade per-station, never aborting the run.
    Returns dict(ts, fetched_at, stations=[...], error?) in the same shape as before.
    """
    def say(i, n, label):
        try:
            progress(i, n, label)
        except Exception:
            pass

    prev = read_cache() or {}
    if not force and time.time() - prev.get("ts", 0) < max_age_s and prev.get("stations"):
        return prev
    try:
        s = _Session()
        cat = prev.get("catalog")
        if not cat or time.time() - prev.get("catalog_ts", 0) > 7 * 86400:
            say(0, 1, "downloading station list (~3,000 stations, slow)")
            cat = s.post("/station/data-visualization", timeout=150)
        pang = [r for r in cat if "pangasinan" in str(r.get("province", "")).lower()]
        keep = [r for r in pang if "water" in str(r.get("type_name", "")).lower()
                or "rain" in str(r.get("type_name", "")).lower() or "vaisala" in str(r.get("type_name", "")).lower()]
        coords, meta_fail = {}, []
        for i, r in enumerate(keep):
            say(i, len(keep) + nearest, f"locating {r.get('location', '')[:34]}")
            try:
                meta = s.post("/station/modal", station_id=r["station_id"], timeout=25)
                st = meta.get("station", {})
                coords[r["station_id"]] = (float(st.get("latitude") or 0), float(st.get("longitude") or 0))
            except Exception as e:
                meta_fail.append(r["station_id"])
            time.sleep(0.2)
        order = sorted(keep, key=lambda r: _km(*DAGUPAN, *(coords.get(r["station_id"]) or (0, 0)))
                       if coords.get(r["station_id"]) else 1e9)
        targets = [r for r in order if coords.get(r["station_id"])]
        rest = [r for r in order if not coords.get(r["station_id"])]
        out = []
        for j, r in enumerate(targets[:nearest] + rest[: max(0, 2)]):
            say(len(keep) + j, len(keep) + nearest, f"reading {r.get('location', '')[:34]}")
            try:
                out.append(_station_row(s, r))
            except Exception as e:
                out.append(dict(station_id=r.get("station_id"), location=r.get("location"),
                                type=r.get("type_name"), error=f"{type(e).__name__}"))
            time.sleep(0.2)
        res = dict(ts=time.time(), fetched_at=datetime.now().isoformat(timespec="minutes"), stations=out,
                   catalog=cat, catalog_ts=prev.get("catalog_ts") if prev.get("catalog_ts") else time.time(),
                   nearest=nearest)
        _save(res)
        return res
    except Exception as e:
        if prev.get("stations"):
            prev["error"] = (f"PhilSensors refresh failed ({type(e).__name__}) — showing the check from "
                             f"{prev.get('fetched_at')}")
            return prev
        return dict(ts=0, fetched_at=None, stations=[],
                    error=f"PhilSensors unreachable ({type(e).__name__}) — no check stored yet")

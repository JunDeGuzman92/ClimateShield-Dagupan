import base64
import json
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.patheffects
import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
import data_core as dc
import kit
import cinema
import mapfilm
import response as rsp
import sms
import ops
import gauges
import demimport
import exercise
import feedback
import field
import heat
import replay
import validation

ROOT = APP_DIR.parent
CHARTS = ROOT / "outputs" / "charts"
ASSETS = ROOT / "assets"
PREFS_PATH = ROOT / "data" / "app_layers" / "ui_prefs.json"

st.set_page_config(page_title="ClimateShield · Dagupan Command Center", page_icon="🌊", layout="wide")

APP_VERSION = "v1.0"

try:
    _app_pw = st.secrets["app_password"]
except Exception:
    _app_pw = None
if _app_pw and not st.session_state.get("cs_authed"):
    st.title("ClimateShield · Dagupan Command Center")
    pwd = st.text_input("Access code", type="password")
    if pwd == _app_pw:
        st.session_state["cs_authed"] = True
        st.rerun()
    st.stop()

BEIGE_BG = "#f7f8fa"
BEIGE_PANEL = "#ffffff"
BEIGE_BORDER = "#e5e7eb"
BEIGE_TEXT = "#1f2937"
BEIGE_MUTED = "#6b7280"
ACCENT = "#2563eb"
WATER = "#2f7fb8"

DEFAULT_PREFS = {
    "kiosk": False, "wall_seconds": 15, "last_cycle_ts": 0.0, "cycle_idx": 0,
    "lang": "English", "theme2": "day",
    "deck_panels": {"kpis": True, "cinema": True, "calendar": True, "watchlist": True},
}


def _theme():
    return kit.THEMES.get(PREFS.get("theme2", "day"), kit.THEMES["day"])


def _apply_theme_tokens():
    t = _theme()
    globals()["BEIGE_BG"] = t["BG"]
    globals()["BEIGE_PANEL"] = t["PANEL"]
    globals()["BEIGE_BORDER"] = t["BORDER"]
    globals()["BEIGE_TEXT"] = t["TEXT"]
    globals()["BEIGE_MUTED"] = t["MUTED"]
    globals()["ACCENT"] = t["ACCENT"]
    globals()["ACCENT2"] = t["ACCENT2"]
    globals()["PLOT_TEMPLATE"] = t["PLOT_TEMPLATE"]
    globals()["PLOT_GRID"] = t["GRID"]



def load_prefs():
    try:
        return {**DEFAULT_PREFS, **json.load(open(PREFS_PATH))}
    except Exception:
        return dict(DEFAULT_PREFS)


def save_prefs(p):
    try:
        json.dump(p, open(PREFS_PATH, "w"), indent=1)
    except Exception:
        pass


PREFS = load_prefs()
_apply_theme_tokens()
NAV = ["🏠 Command Deck", "🌊 Flood Scenario Simulator", "☀️ Heat Scenario Simulator", "🛡️ Countermeasure Lab",
       "📡 Live Telemetry", "🗺️ Barangay Walkthrough", "🚑 Response & Dispatch", "ℹ️ Methods & Sources",
       "📱 Field Report"]


def apply_theme_and_kiosk():
    kiosk = PREFS.get("kiosk", False)
    t = _theme()
    css = f"""
    <style>
    .stApp {{ background: {BEIGE_BG}; color: {BEIGE_TEXT}; }}
    section[data-testid="stSidebar"] {{ background: {BEIGE_PANEL}; border-right: 1px solid {BEIGE_BORDER}; }}
    h1, h2, h3, h4 {{ color: {BEIGE_TEXT} !important; letter-spacing: -0.01em; }}
    div[data-testid="stMetric"] {{
        background: {BEIGE_PANEL}; border: 1px solid {BEIGE_BORDER}; border-top: 3px solid {ACCENT};
        border-radius: 12px; padding: 0.7rem 0.9rem; box-shadow: {t['CARD_SHADOW']}; }}
    div[data-testid="stMetricValue"] {{ font-weight: 800; color: {BEIGE_TEXT}; letter-spacing: -0.02em; }}
    div[data-testid="stMetricLabel"] p {{ color: {BEIGE_MUTED} !important; font-size: .78rem;
        text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }}
    div[data-testid="stMetricDelta"] {{ color: {BEIGE_MUTED} !important; }}
    .stTabs [data-baseweb="tab"] {{ background: {BEIGE_PANEL}; border: 1px solid {BEIGE_BORDER};
        border-radius: 999px; padding: 4px 14px; margin-right: 4px; }}
    .stTabs [aria-selected="true"] {{ background: {ACCENT}1a !important; border-color: {ACCENT} !important; }}
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}
    div[data-testid="stDataFrame"] {{ background: {BEIGE_PANEL}; border: 1px solid {BEIGE_BORDER}; border-radius: 10px; }}
    .stCaption, p.stCaption, small {{ color: {BEIGE_MUTED}; }}
    .block-container {{ padding-top: 1rem; padding-bottom: 1.5rem; gap: 0.5rem; max-width: 1480px; }}
    .stButton>button {{ background: {BEIGE_PANEL}; color: {BEIGE_TEXT}; border: 1px solid {BEIGE_BORDER};
        border-radius: 10px; font-weight: 600; }}
    .stButton>button:hover {{ border-color: {ACCENT}; color: {BEIGE_TEXT}; }}
    .stButton>button[kind="primary"] {{ background: {ACCENT}; color: white; border: none; }}
    iframe {{ border-radius: 12px; }}
    .cs-banner {{ background: {ACCENT}14; border-left: 4px solid {ACCENT}; padding: 12px 16px; border-radius: 10px;
        margin-bottom: 8px; color: {BEIGE_TEXT}; font-size: 15px; }}
    .cs-warn {{ background: #f9731618; border-left: 4px solid #f97316; padding: 12px 16px; border-radius: 10px;
        margin-bottom: 8px; color: {BEIGE_TEXT}; font-size: 14px; }}
    .cs-live {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: #22c55e;
        animation: cspulse 1.8s infinite; margin-right: 7px; vertical-align: middle; }}
    .cs-stale {{ background: #9ca3af !important; animation: none !important; }}
    @keyframes cspulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(34,197,94,.6); }}
        70% {{ box-shadow: 0 0 0 10px rgba(34,197,94,0); }} 100% {{ box-shadow: 0 0 0 0 rgba(34,197,94,0); }} }}
    .cs-kicker {{ font-size: .74rem; text-transform: uppercase; letter-spacing: .12em; color: {BEIGE_MUTED}; font-weight: 700; }}
    .cs-factor {{ display: flex; flex-direction: column; gap: 2px; padding: 12px 14px; border-radius: 12px;
        background: {BEIGE_PANEL}; border: 1px solid {BEIGE_BORDER}; box-shadow: {t['CARD_SHADOW']}; min-height: 86px; }}
    .cs-factor b {{ font-size: 1.25rem; letter-spacing: -0.01em; color: {BEIGE_TEXT}; }}
    .cs-factor span {{ color: {BEIGE_MUTED}; font-size: .74rem; text-transform: uppercase; letter-spacing: .08em; }}
    .cs-factor small {{ color: {BEIGE_MUTED}; }}
    .cs-badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 700;
        color: #fff; vertical-align: middle; }}
    @media (max-width: 640px) {{
      .block-container {{ padding-left: .5rem !important; padding-right: .5rem !important; }}
      .stButton>button {{ min-height: 46px; font-size: 15px; }}
      div[data-testid="stMetricValue"] {{ font-size: 1.35rem; }}
      h1 {{ font-size: 1.45rem !important; }}
      iframe {{ max-width: 100% !important; }}
    }}
    """
    if kiosk:
        css += """
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stStatusWidget"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        .block-container { padding-top: 0.4rem !important; padding-bottom: 0 !important;
                           padding-left: 0.7rem !important; padding-right: 0.7rem !important; max-width: 100% !important; }
        div[data-testid="stMetric"] { padding: 0.4rem 0.6rem !important; }
        .stButton { display: none; }
        """
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)


def banner(text, style="info"):
    cls = "cs-banner" if style == "info" else "cs-warn"
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def cooling_empty_state(key, style="warning", where="this page"):
    """Empty cooling register: say so right where the rings should be, then offer the one-click practice set."""
    if heat.cooling_stats()["open"]:
        return
    msg = ("**No cooling points registered** — the ❄ layer, the 2.5 km rings and every coverage number on "
           f"{where} are empty. Register the practice set to see the picture: roster shelters become "
           "**practice candidates**, labelled as such on every map, not as sites verified open today.")
    if style == "warning":
        st.warning(msg)
    else:
        st.info(msg)
    if st.button("❄ Register practice cooling points", key=key, use_container_width=True):
        added = heat.seed_practice_cooling(L)
        st.toast(f"Added {added} practice cooling point(s)" if added else "Nothing new to register")
        st.rerun()


@st.cache_resource
def get_layers():
    return dc.Layers()


def _urlopen_tls(req, timeout=12):
    """urlopen with certifi's CA bundle when available (met.no's chain needs it on some Python installs)."""
    import urllib.request
    try:
        import certifi
        import ssl
        return urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context(cafile=certifi.where()))
    except Exception:
        return urllib.request.urlopen(req, timeout=timeout)


_LIVE_TTL = 120.0            # refresh the feed at most this often (seconds)
_LIVE_OK = 20 * 60.0         # a reading younger than this still counts as live


def _live_state():
    """Feed state lives on the imported data_core module, so it survives script reruns
    (this file is re-executed on every rerun - a plain module global would reset each time)."""
    st_ = getattr(dc, "_cs_live_state", None)
    if st_ is None:
        st_ = {"data": None, "ts": "", "busy": False, "lock": threading.Lock()}
        dc._cs_live_state = st_
    return st_


def _live_fetch():
    """Pull the feed (Open-Meteo, MET Norway fallback). Network only - never touches Streamlit state."""
    data = None
    try:
        data = dc.live_weather()
        data["source"] = "Open-Meteo"
    except Exception:
        data = None
    if data is None:
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=16.0432&lon=120.3342",
                headers={"User-Agent": "ClimateShieldDagupan/1.0 community disaster-awareness project"})
            with _urlopen_tls(req) as r:
                d = json.loads(r.read().decode("utf-8"))
            series = d["properties"]["timeseries"]
            inst = series[0]["data"]["instant"]["details"]
            t = inst.get("air_temperature")
            if t is None:
                raise ValueError("no temperature")
            times, rains = [], []
            for s_ in series:
                times.append(s_["time"])
                rr = s_.get("data", {}).get("next_1_hours", {}).get("details", {}).get("precipitation_amount", 0.0)
                rains.append(rr or 0.0)
            data = {
                "current": {"temperature_2m": t,
                             "relative_humidity_2m": inst.get("relative_humidity") or 70.0,
                             "precipitation": rains[0] if rains else 0.0,
                             "apparent_temperature": t, "time": series[0]["time"]},
                # MET compact gives no hourly probability — leave the series empty rather than fake zeros
                "hourly": {"time": times, "precipitation": rains, "precipitation_probability": []},
                "source": "MET Norway",
            }
        except Exception:
            data = None

    return data


def _stamp_live(d, fetched_iso, live):
    """Age / observed / source stamps the freshness badge reads."""
    cur = d.setdefault("current", {})
    cur["source"] = d.get("source", "—")
    try:
        ft = datetime.fromisoformat(fetched_iso)
    except Exception:
        ft = datetime.now()
    cur["fetched_at"] = ft.strftime("%b %d %H:%M")
    cur["age_min"] = max(0, int((datetime.now() - ft).total_seconds() // 60))
    cur["observed_at"] = (cur.get("time") or "")[-5:] or "—"
    cur["live"] = live
    d["fetched_at"] = cur["fetched_at"]
    return d


def _live_store(data, ts_iso):
    state = _live_state()
    with state["lock"]:
        state["data"], state["ts"] = data, ts_iso
    try:
        with open(ROOT / "data" / "app_layers" / "live_cache.json", "w") as f:
            json.dump({"ok": True, "ts": ts_iso, "data": data}, f)
    except Exception:
        pass


def _live_refresh_async():
    """Kick a background refresh so a page run never waits on the weather API."""
    state = _live_state()
    with state["lock"]:
        if state["busy"]:
            return
        state["busy"] = True

    def _run():
        try:
            fresh = _live_fetch()
            if fresh is not None:
                _live_store(fresh, datetime.now().isoformat())
        finally:
            with state["lock"]:
                state["busy"] = False

    threading.Thread(target=_run, daemon=True).start()


def get_live():
    """(stamped data, ok) - memory or live_cache.json first; the network is only touched by a
    background refresh (one blocking fetch on a truly cold start, then never again)."""
    state = _live_state()
    with state["lock"]:
        data, ts = state["data"], state["ts"]
    if data is None:
        try:
            with open(ROOT / "data" / "app_layers" / "live_cache.json") as f:
                pkg = json.load(f)
            data, ts = pkg["data"], pkg.get("ts") or ""
        except Exception:
            data = None
        if data is not None:
            with state["lock"]:
                state["data"], state["ts"] = data, ts
    if data is None:
        data = _live_fetch()
        if data is None:
            return None, False
        ts = datetime.now().isoformat()
        _live_store(data, ts)
    try:
        age_s = (datetime.now() - datetime.fromisoformat(ts)).total_seconds()
    except Exception:
        age_s = 1e9
    if age_s > _LIVE_TTL:
        _live_refresh_async()
    ok = 0.0 <= age_s <= _LIVE_OK
    return _stamp_live(dict(data), ts, ok), ok


@st.cache_data(show_spinner=False, max_entries=8)
def depth_overlay_png(w_m, vmax=None):
    """Flood-depth overlay raster, cached per water level — the Response maps re-emit the same
    PNG on every rerun (and identical bytes never reach the browser twice)."""
    png, v = kit.depth_png(L.depth_grid(round(float(w_m), 3))[0], vmax=vmax, L=L)
    return png, v


def freshness_badge(cur, ok):
    """Inline badge: green pulsing LIVE with observation time, or grey STALE with age."""
    if not cur:
        return '<span class="cs-badge" style="background:#9ca3af">NO FEED</span>'
    age = cur.get("age_min", 0)
    if ok and age < 20:
        return (f'<span class="cs-live"></span><b>LIVE</b> · observed {cur.get("observed_at", "—")} · '
                f'fetched {cur.get("fetched_at", "—")} via {cur.get("source", "—")}')
    return (f'<span class="cs-live cs-stale"></span><b>STALE</b> · last fetched {cur.get("fetched_at", "—")} '
            f'({age // 60} h {age % 60} min ago) via {cur.get("source", "—")}')


def plotly_beige(fig, height=None, y_title=None, title=None):
    fig.update_layout(template=PLOT_TEMPLATE, paper_bgcolor=BEIGE_PANEL, plot_bgcolor=BEIGE_PANEL,
                      font=dict(color=BEIGE_TEXT, size=12),
                      margin=dict(l=10, r=10, t=34 if title else 18, b=10),
                      height=height, yaxis_title=y_title, title=title,
                      xaxis=dict(gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID),
                      yaxis=dict(gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID))
    return fig


def _render_storm(frames, story, height, sub):
    m = mapfilm.storm_map(L, frames, story["title"], sub, height=height)
    html = m.get_root().render()
    peak = max(frames, key=lambda f: f["W"])
    worst = max(frames, key=lambda f: f["stranded"])
    span = float(story["hours"][-1]) if story.get("replay") else 40.0
    summary = dict(title=story["title"], peak_W=peak["W"], peak_hour=peak["hour"],
                   peak_label=peak.get("label", ""), pop_in=peak["pop_in"],
                   bldg=peak["bldg"], roads_km=peak["roads_km"], stranded=worst["stranded"],
                   evacuated=max(f["evacuated"] for f in frames), tide=story.get("tide", 0.0),
                   clog=story.get("clog", 0.0), pumps=story.get("pumps", False),
                   warning_h=story.get("warning_h", 0.0),
                   flooded_share=L.flooded_share(peak["W"]),
                   hours_wet=sum(1 for f in frames if f["W"] > 0.15) * (span / len(frames)))
    return html, summary


@st.cache_data(show_spinner=False, max_entries=24)
def storm_html(key, params, height):
    """Map time-lapse HTML for a story (or a custom params dict) + summary; cached per inputs."""
    story = cinema.FLOOD_STORIES[key] if key in cinema.FLOOD_STORIES else cinema.custom_story(**params)
    sub = (f"tide +{story['tide']:.2f} m · drains {story['clog'] * 100:.0f}% blocked · pumps "
           f"{'on' if story['pumps'] else 'off'} · warning {story['warning_h']} h · proxy physics on GLO-30 terrain")
    return _render_storm(mapfilm.storm_frames(L, story), story, height, sub)


@st.cache_data(show_spinner=False, max_entries=12)
def replay_storm_html(ev_key, readiness, height):
    """Time-lapse for a real historical event, driven by the recorded daily rainfall (replay.py)."""
    story = replay.build_story(L, ev_key, readiness)
    sub = (f"real daily rainfall (NASA POWER 1981–2026) → water storage → proxy flood share "
           f"· readiness: {replay.READINESS[readiness]['label'].lower()}")
    return _render_storm(mapfilm.storm_frames(L, story), story, height, sub)


@st.cache_data(show_spinner=False, max_entries=4)
def _debrief_png(state_json):
    """Run debrief chart PNG, cached per finished run - the exercise panel redraws it on every rerun."""
    fig, png = exercise.debrief_figure(L, json.loads(state_json))
    plt.close(fig)
    return png


def factor_tile(label, value, sub=""):
    return (f'<div class="cs-factor"><span>{label}</span><b>{value}</b>'
            f'<small>{sub}</small></div>')


STORM_STRIP_PX = 186  # caption + stat tiles + timeline strip under the map


def _set_flag(k):
    st.session_state[k] = True


def _gate(gate_key, note):
    """Play gate for heavy storm films. True → render; False → button shown instead.

    The film frame-set is a 2–5 MB download — on phones we ship it only after an explicit tap
    (state tiles and text stay available either way)."""
    if not gate_key or st.session_state.get(gate_key):
        return True
    st.button("▶ Play the storm film", type="primary", use_container_width=True,
              key=f"g_{gate_key}", on_click=_set_flag, args=(gate_key,),
              help="The film loads ~2–5 MB of animation, so it stays off until you ask for it.")
    st.caption(note)
    return False


def show_storm(key, height=500, params=None, gate=None):
    """height = map height in px; the stats strip is drawn below it, never over the map."""
    html, s = storm_html(key, params, height)
    if _gate(gate, "Tiles above are live; the animated film loads on your tap (≈2–5 MB)."):
        components.html(html, height=height + STORM_STRIP_PX, scrolling=False)
    return s


@st.cache_data(show_spinner=False, max_entries=40)
def _route_cached(brgy_name, anchor_lon, anchor_lat):
    return kit.route_for(L, {"lon": anchor_lon, "lat": anchor_lat})


def route_card(brgy_name, W, key_prefix="rc"):
    """Evacuation route card: map with depth-coloured route, elevation profile, person-vs-water gauge."""
    anchor = next((b["anchor"] for b in L.brgy_anchors if b["barangay"] == brgy_name), None)
    if anchor is None:
        st.info("No map anchor for this barangay yet.")
        return
    prof = _route_cached(brgy_name, anchor["lon"], anchor["lat"])
    if prof is None or prof["total_m"] < 15:
        st.info("No connected shelter route found within the mapped street network.")
        return
    sh = prof["shelter"]
    sh_name = sh.get("name") or sh.get("category", "evacuation site")
    total = float(prof["total_m"])
    st.markdown(f"**{brgy_name} → {sh_name}** · {total:.0f} m on foot via **{prof['main_road']}** · "
                f"water +{W:.2f} m")
    pos = st.slider("Where are you on the route? (m from start)", 0.0, total, min(total * 0.3, total), 5.0,
                    key=f"{key_prefix}_pos")
    lon, lat, elev, s_, _ = kit.along_route(prof, pos)
    d_here = max(W - elev, 0.0)
    worst_i = int(np.argmax(np.maximum(W - prof["elev"], 0.0)))
    d_worst = float(max(W - prof["elev"][worst_i], 0.0))
    mc, gc = st.columns([2.3, 1])
    with mc:
        try:
            from streamlit_folium import st_folium
            st_folium(mapfilm.route_map(L, prof, W, pos_m=pos), height=430, use_container_width=True,
                      key=f"{key_prefix}_map", returned_objects=[])
        except Exception as e:
            st.info(f"Map unavailable ({type(e).__name__}).")
        st.caption("Route colour = water depth on that stretch: green dry · amber knee · red waist · dark red chest+. "
                   "Hover a segment for ground height and depth.")
    with gc:
        st.markdown(mapfilm.depth_gauge_html(d_here, kit.depth_label(d_here)), unsafe_allow_html=True)
        st.metric("Deepest point on route", f"{d_worst:.2f} m", f"at {prof['cum'][worst_i]:.0f} m · {kit.depth_label(d_worst)}",
                  delta_color="inverse")
        st.metric("Still to walk", f"{total - pos:.0f} m", sh_name)
    fg = go.Figure()
    fg.add_trace(go.Scatter(x=prof["cum"], y=prof["elev"], mode="lines", name="street level",
                            line=dict(color="#6b7280", width=2.5), fill="tozeroy", fillcolor="rgba(107,114,128,.12)"))
    fg.add_hrect(y0=-5, y1=W, fillcolor="rgba(37,99,235,.16)", line_width=0)
    fg.add_hline(y=W, line_color="#2563eb", line_dash="dash", annotation_text=f"water +{W:.2f} m")
    fg.add_trace(go.Scatter(x=[pos], y=[elev], mode="markers+text", text=["you"], textposition="top center",
                            marker=dict(size=13, color="#2563eb", line=dict(width=2, color="white")), name="you"))
    fg.update_yaxes(range=[min(float(prof["elev"].min()) - 0.3, W - 0.3), max(float(prof["elev"].max()) + 0.5, W + 0.5)])
    st.plotly_chart(plotly_beige(fg, height=220, y_title="m above sea", title="Street profile vs water line"),
                    use_container_width=True, config={"displayModeBar": False})


L = get_layers()
ANCHORS = kit.anchors_map(L.brgy_anchors)
kit.set_anchor_lookup(L.brgy_anchors)


def tt(key):
    return kit.T_TITLES.get(key, {}).get(PREFS.get("lang", "English"), key)
PAG_CLASSES = {
    "PAGASA Advisory-level (localized flooding)": "Flood Advisory - awareness",
    "PAGASA Alert-level (widespread threat)": "Flood Alert - preparedness",
    "Calamity-class (Aug 2026-type event)": "Flood Warning - immediate action",
    "Extreme (Oct 2009-type: 469 mm in 3 days)": "Severe Flooding - forced evacuation",
}


def extent_from_mask(margin_m=900):
    rows, cols = np.where(L.land_mask)
    return (L.transform.c + cols.min() * 30 - margin_m, L.transform.c + cols.max() * 30 + margin_m,
            L.transform.f - rows.max() * 30 - margin_m, L.transform.f - rows.min() * 30 + margin_m)


EXT = extent_from_mask()


def draw_map(depth=None, fac=True, labels=True, figsize=(11.5, 9.2), title=None, crowd=True):
    x0, x1, y0, y1 = EXT
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor(BEIGE_BG)
    ax.imshow(L.basemap,
              extent=(L.transform.c, L.transform.c + L.w * 30, L.transform.f - L.h * 30, L.transform.f),
              origin="upper", zorder=1)
    if depth is not None:
        show = np.ma.masked_invalid(np.where(depth > 0.02, depth, np.nan))
        cmap = mpl.colormaps["YlGnBu"].copy()
        cmap.set_bad(alpha=0)
        im = ax.imshow(show, cmap=cmap, vmin=0, vmax=max(0.8, float(np.nanmax(depth))),
                       alpha=0.8, extent=(L.transform.c, L.transform.c + L.w * 30,
                                          L.transform.f - L.h * 30, L.transform.f), zorder=3)
        plt.colorbar(im, ax=ax, shrink=0.55, pad=0.01, label="flood depth (m)")
    for r in L.rivers:
        xs, ys = L.to_utm(*np.array(r["ll"]).T)
        ax.plot(xs, ys, color=WATER, lw=1.7 if r["class"] == "river" else 0.8, alpha=0.8, zorder=4)
    for r in L.coast:
        xs, ys = L.to_utm(*np.array(r["ll"]).T)
        ax.plot(xs, ys, color="#1abc9c", lw=2.6, alpha=0.9, zorder=4)
    if depth is not None:
        for r, (ris, cis) in zip(L.roads, L.road_cells):
            vd = depth[ris, cis]
            vd = vd[np.isfinite(vd)]
            cut = float((vd > 0.30).mean()) if len(vd) else 0.0
            xs, ys = L.to_utm(*np.array(r["ll"]).T)
            col = "#c0392b" if cut >= 0.5 else ("#e67e22" if cut > 0.1 else "#6b5d4f")
            ax.plot(xs, ys, color=col, lw=1.5, alpha=0.95, zorder=5)
    if fac:
        pts = [(L.to_utm(f["lon"], f["lat"]), f["category"]) for f in L.facilities]
        for cat, col in dc.FAC_COLORS.items():
            xs = [p[0][0] for p in pts if p[1] == cat]
            ys = [p[0][1] for p in pts if p[1] == cat]
            ax.scatter(xs, ys, s=16, c=col, edgecolors="white", linewidths=0.3, alpha=0.9, label=cat, zorder=6)
    if labels:
        for p in L.places:
            x, y = L.to_utm(p["lon"], p["lat"])
            if x0 < x < x1 and y0 < y < y1:
                ax.text(x, y, p["name"], fontsize=6.5, color=BEIGE_TEXT, ha="center",
                        path_effects=[mpl.patheffects.withStroke(linewidth=2.5, foreground="#fffcf5")], zorder=7)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_title(title or "", color=BEIGE_TEXT, fontsize=13)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(BEIGE_BORDER)
    if crowd:
        for p in kit.crowd_pins(ANCHORS):
            px, py = L.to_utm(p["lon"], p["lat"])
            ax.scatter([px], [py], s=70 + p["sev"] * 55, c=kit.SEV_COLORS[p["sev"]],
                       edgecolors="white", linewidths=1.4, zorder=9, alpha=0.95)
            ax.text(px, py, str(p["n"]), fontsize=7.5, color="#1f2937", ha="center", va="center",
                    zorder=10, path_effects=[mpl.patheffects.withStroke(linewidth=2, foreground="white")])
    if fac:
        ax.legend(loc="lower right", fontsize=7, framealpha=0.9, facecolor=BEIGE_PANEL,
                  edgecolor=BEIGE_BORDER, labelcolor=BEIGE_TEXT, title="facilities", title_fontsize=7)
    fig.patch.set_facecolor(BEIGE_BG)
    fig.tight_layout()
    return fig


EXIT_CHIP = """<div style="position: fixed; bottom: 10px; right: 12px; z-index: 9999; opacity: .85; font-family: sans-serif;">
<span style="background:#ffffff;color:#6b7280;padding:6px 10px;border-radius:8px;font-size:11px;
border:1px solid #e5e7eb;margin-right:6px;">WALL DISPLAY · scenario auto-advances</span>
<a href="?kiosk=0" style="background:#2563eb;color:#fff;padding:6px 12px;border-radius:8px;
text-decoration:none;font-size:12px;">⚙ Exit wall display</a></div>"""


def make_local_fig(anchor, label):
    x, y = L.to_utm(anchor["lon"], anchor["lat"])
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_facecolor(BEIGE_BG)
    ax.imshow(L.basemap,
              extent=(L.transform.c, L.transform.c + L.w * 30, L.transform.f - L.h * 30, L.transform.f))
    showz = np.ma.masked_invalid(np.where(np.isfinite(L.susc) & (L.susc > np.nanpercentile(L.susc, 70)),
                                          L.susc, np.nan))
    ax.imshow(showz, cmap="YlOrRd", vmin=0, vmax=100, alpha=0.5,
              extent=(L.transform.c, L.transform.c + L.w * 30, L.transform.f - L.h * 30, L.transform.f))
    for r in L.rivers:
        xs, ys = L.to_utm(*np.array(r["ll"]).T)
        ax.plot(xs, ys, color=WATER, lw=1.6 if r["class"] == "river" else 0.7, alpha=0.8)
    ax.scatter([x], [y], marker="*", s=420, c=ACCENT, edgecolors="white", zorder=10)
    ax.annotate(label, (x, y), xytext=(18, -14), textcoords="offset points", color=BEIGE_TEXT, fontsize=12,
                path_effects=[mpl.patheffects.withStroke(linewidth=3, foreground="#ffffff")])
    ax.set_xlim(x - 1800, x + 1800)
    ax.set_ylim(y - 1800, y + 1800)
    ax.set_title(f"{label} — terrain & high-susceptibility pockets (star = barangay core)", color=BEIGE_TEXT)
    ax.set_xticks([]); ax.set_yticks([])
    fig.patch.set_facecolor(BEIGE_BG)
    fig.tight_layout()
    return fig


def render_wall():
    interval = int(PREFS.get("wall_seconds", 15))
    components.html(
        f"<script>window.setTimeout(function() {{ window.parent.location.reload(); }}, {interval * 1000});</script>",
        height=0)
    if time.time() - float(PREFS.get("last_cycle_ts", 0)) >= interval:
        PREFS["cycle_idx"] = int(PREFS.get("cycle_idx", 0)) + 1
        PREFS["last_cycle_ts"] = time.time()
        save_prefs(PREFS)

    scen_names = list(dc.SCENARIOS.keys())
    scen = scen_names[int(PREFS.get("cycle_idx", 0)) % len(scen_names)]
    W = L.water_level_for_share(dc.SCENARIOS[scen]) + 0.20
    depth = L.depth_grid(W)[0]
    exp = L.exposure(depth, W)
    live, ok = get_live()
    cur = (live or {}).get("current", {})
    HI, cat = 0.0, "feed offline"
    if cur:
        HI = dc.hi_c(cur["temperature_2m"], cur["relative_humidity_2m"])
        cat = dc.hi_category(HI)[0]

    if cur and HI >= 42:
        catcolor = "#9e2a2b" if HI >= 52 else "#e06666"
        st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                background:linear-gradient(90deg,{catcolor},#7a1f1f);color:#fff;padding:10px 18px;
                border-radius:12px;margin-bottom:6px;">
      <div style="font-size:22px;font-weight:800;">🔥 HEAT EMERGENCY WALL — HEAT INDEX {HI:.0f}°C ({cat.upper()})</div>
      <div style="font-size:14px;">updated {cur.get('fetched_at', '—')} · water respite points opening</div>
    </div>""", unsafe_allow_html=True)
        left, right = st.columns([1.15, 1])
        with left:
            hg = go.Figure(go.Indicator(
                mode="gauge+number", value=HI, number={"suffix": "°C"},
                title={"text": f"Live heat index · {cat}"},
                gauge={"axis": {"range": [20, 60]}, "bar": {"color": catcolor}, "bgcolor": BEIGE_PANEL,
                       "steps": [{"range": [20, 27], "color": "#e8dfc8"},
                                 {"range": [27, 33], "color": "#ffe699"},
                                 {"range": [33, 42], "color": "#f6b26b"},
                                 {"range": [42, 52], "color": "#e06666"},
                                 {"range": [52, 60], "color": "#9e2a2a"}]},
            ))
            hg.update_layout(template=PLOT_TEMPLATE, height=430, margin=dict(l=10, r=10, t=60, b=10),
                             paper_bgcolor=BEIGE_PANEL)
            st.plotly_chart(hg, use_container_width=True, config={"displayModeBar": False})
        with right:
            top_pop = L.brgy.sort_values("popn", ascending=False).head(10).iloc[::-1]
            fph = px.bar(top_pop, x="popn", y="barangay", orientation="h",
                         color="popn", color_continuous_scale="OrRd")
            fph.update_coloraxes(showscale=False)
            plotly_beige(fph, height=280, title="Open respite points FIRST in these barangays (census-weighted)")
            st.plotly_chart(fph, use_container_width=True, config={"displayModeBar": False})
            month_now = datetime.now().month
            hi_m = L.daily[L.daily["HI"] >= 42].groupby("MONTH").size().reindex(range(1, 13), fill_value=0) / 45.7
            st.markdown(f"""
<div class="cs-banner" style="font-size:13px;">
<b>Coverage playbook:</b> {hi_m.reindex([month_now], fill_value=0).iloc[0]:.0f} danger-level days historically in month {month_now} ·
reschedule outdoor crews · buddy-check elderly/buntis lists hourly · sari-sari water points + shaded rest stations ·
schools follow DepEd suspension guidance.
</div>""", unsafe_allow_html=True)
        st.markdown(EXIT_CHIP, unsafe_allow_html=True)
        return
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                background:linear-gradient(90deg,#b5813e,#8d5b1e);color:#fff;padding:10px 18px;
                border-radius:12px;margin-bottom:6px;">
      <div style="font-size:22px;font-weight:800;">CLIMATESHIELD · DAGUPAN — {scen.upper()}</div>
      <div style="font-size:15px;">water +{W:.2f} m · <b style="font-size:18px;">{exp['pop_affected']:,.0f}</b>
      residents affected · heat index {HI:.0f}°C ({cat}) · updated {cur.get('fetched_at', '—')}</div>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("RESIDENTS IN FLOOD ZONES", f"{exp['pop_affected']:,.0f}",
              f"{exp['pop_affected'] / exp['pop_total'] * 100:.0f}% of census", delta_color="inverse")
    c2.metric("LAND FLOODED", f"{exp['area_flooded_km2']:.1f} km²", "of 33.8 km² active land", delta_color="inverse")
    c3.metric("ROADS CUT", f"{exp['road_km_cut']:.0f} km", f"of {exp['road_km_total']:.0f} km mapped", delta_color="inverse")

    left, right = st.columns([1.72, 1])
    with left:
        st.markdown(f'<div class="cs-kicker">{scen} — water +{W:.2f} m (tide +0.20 m) · scenario advances every {interval}s</div>',
                    unsafe_allow_html=True)
        try:
            from streamlit_folium import st_folium
            st_folium(kit.make_city_map(L, depth=depth, W_cut=W, zoom=13, crowd=True), height=640,
                      use_container_width=True, returned_objects=[], key=f"wall_map_{int(PREFS.get('cycle_idx', 0))}")
        except Exception:
            fig = draw_map(depth=depth, fac=True, figsize=(10.8, 6.05),
                           title=f"{scen} — water +{W:.2f} m (tide +0.20 m)")
            st.pyplot(fig)
            plt.close(fig)
    with right:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=HI, number={"suffix": "°C"},
            title={"text": f"Heat index NOW · {cat}"},
            gauge={"axis": {"range": [20, 60]}, "bar": {"color": "#b5813e"}, "bgcolor": BEIGE_PANEL,
                   "steps": [
                       {"range": [20, 27], "color": "#e8dfc8"},
                       {"range": [27, 33], "color": "#ffe699"},
                       {"range": [33, 42], "color": "#f6b26b"},
                       {"range": [42, 52], "color": "#e06666"},
                       {"range": [52, 60], "color": "#9e2a2a"}]},
        ))
        gauge.update_layout(template=PLOT_TEMPLATE, height=215, margin=dict(l=10, r=10, t=60, b=10),
                            paper_bgcolor=BEIGE_PANEL)
        st.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})

        wl = L.brgy.dropna(subset=["CSRI"]).sort_values("CSRI", ascending=False).head(5).iloc[::-1]
        figb = px.bar(wl, x="CSRI", y="barangay", orientation="h",
                      color="CSRI", color_continuous_scale="Agsunset")
        figb.update_traces(marker_line_width=0)
        plotly_beige(figb, height=205, y_title=None, title="Top-5 risk watchlist")
        figb.update_yaxes(tickfont=dict(size=12))
        figb.update_coloraxes(showscale=False)
        st.plotly_chart(figb, use_container_width=True, config={"displayModeBar": False})

        month_now = datetime.now().month
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        rain_m = L.daily[L.daily["RAIN"] >= 50].groupby("MONTH").size().reindex(range(1, 13), fill_value=0) / 45.7
        hi_m = L.daily[L.daily["HI"] >= 42].groupby("MONTH").size().reindex(range(1, 13), fill_value=0) / 45.7
        figc = go.Figure()
        figc.add_bar(x=month_names, y=rain_m.values, name="heavy rain", marker_color="#4aa3d8")
        figc.add_bar(x=month_names, y=hi_m.values, name="heat danger", marker_color="#d97a3d")
        figc.add_vrect(x0=month_names[month_now - 1], x1=month_names[month_now - 1], line_color="#b5813e", line_width=3)
        figc.update_layout(barmode="group", showlegend=False)
        plotly_beige(figc, height=175, y_title="days/yr", title="Readiness calendar — this month highlighted")
        st.plotly_chart(figc, use_container_width=True, config={"displayModeBar": False})

    st.markdown(EXIT_CHIP, unsafe_allow_html=True)


def _nav_to(v):
    st.session_state["nav_page"] = v


def _go_brgy(qv):
    st.session_state["wt_sel"] = qv
    st.session_state["nav_page"] = NAV[5]


def _go_walk():
    st.session_state["street_brgy"] = "Pantal"
    st.session_state["sim_view"] = "🚶 Evacuation route"
    st.session_state["nav_page"] = NAV[1]


def _go_walk_brgy(brgy):
    st.session_state["street_brgy"] = brgy
    st.session_state["sim_view"] = "🚶 Evacuation route"
    st.session_state["nav_page"] = NAV[1]


def _go_heat_brgy(brgy):
    st.session_state["heat_b_sel"] = brgy
    st.session_state["nav_page"] = NAV[2]


def display_options_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.markdown("⚙️ **Display options** *(saved)*")
    PREFS["kiosk"] = st.sidebar.toggle("📺 Wall display mode", value=PREFS["kiosk"],
                                       help="Full-screen one-page command center: auto-rotating flood scenarios, "
                                            "live header, no page buttons. Press F11 in the browser for true fullscreen.")
    if PREFS["kiosk"]:
        st.sidebar.caption("Wall display runs when you reload. The ⚙ Exit link sits bottom-right on screen.")
    with st.sidebar.expander("Wall display settings"):
        PREFS["wall_seconds"] = st.slider("Seconds per scenario", 8, 45, int(PREFS.get("wall_seconds", 15)))
    _keys = list(kit.THEME_LABELS.keys())
    _cur = PREFS.get("theme2", "day")
    _th = st.sidebar.radio("Theme", [kit.THEME_LABELS[k] for k in _keys],
                           index=_keys.index(_cur) if _cur in _keys else 0,
                           help="Day ops = bright room · Night ops = dark slate for low-light command rooms.")
    PREFS["theme2"] = _keys[[kit.THEME_LABELS[k] for k in _keys].index(_th)]
    PREFS["lang"] = st.sidebar.radio("Language 🌏", kit.LANGS,
                                     index=kit.LANGS.index(PREFS.get("lang", "English")),
                                     help="Action cards & section titles translate. Tagalog lines are solid; "
                                          "Pangasinan lines are best-effort — native-speaker review welcome.")
    with st.sidebar.expander("Command Deck panels"):
        for key, label in [("kpis", "KPI tiles"), ("cinema", "Scenario Cinema"),
                           ("calendar", "Readiness calendar"), ("watchlist", "Barangay watchlist")]:
            PREFS["deck_panels"][key] = st.checkbox(label, PREFS["deck_panels"].get(key, True))
    save_prefs(PREFS)

apply_theme_and_kiosk()

if st.query_params.get("kiosk", "") in ("0", "false", "off"):
    PREFS["kiosk"] = False
    save_prefs(PREFS)
    try:
        del st.query_params["kiosk"]
    except Exception:
        pass
    st.rerun()

field.maybe_ingest(L)   # offline pack sync (?fq= batch) must work from any landing page

if PREFS.get("kiosk"):
    render_wall()
    st.stop()

# ----------------------------------------------------------------- facilitator second screen (?facilitator=1)
@st.fragment(run_every=5)
def _fragment_facilitator():
    """Projector view for drills — storm clock, event feed, live score. Second screen: the operator
    works the queue on the Response page while this runs on the room's display."""
    st.markdown("""<style>
    [data-testid="stSidebar"] { display:none !important; }
    [data-testid="stHeader"] { display:none !important; }
    .block-container { padding-top:1.1rem !important; max-width:1700px !important; }
    .cs-fhuge { font-size:4.4rem; font-weight:800; line-height:1; letter-spacing:-0.02em; }
    .cs-fbig  { font-size:2.4rem; font-weight:700; line-height:1.1; }
    .cs-fmed  { font-size:1.25rem; font-weight:600; }
    .cs-fhdr  { font-size:1.05rem; color:#6b7280; }
    .cs-fgrid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }
    .cs-fcard { border:1px solid #e5e7eb; border-radius:14px; padding:10px 16px; background:#fff;
                box-shadow:0 2px 8px rgba(16,24,40,.07); text-align:left; }
    .cs-fcard span { display:block; font-size:.8rem; text-transform:uppercase; letter-spacing:.08em; color:#6b7280; font-weight:700; }
    </style>""", unsafe_allow_html=True)
    state = exercise.load()
    reqs = rsp.load_requests()
    shel = ops.load_shelters(L)
    rs = ops.load_resources()
    shel_hc = int(pd.to_numeric(shel["headcount"], errors="coerce").fillna(0).sum())
    miss = list((state.get("missions") or {}).values())
    aboard = sum(m.get("load") or 0 for m in miss if m["phase"] == "back")
    waiting = exercise.people_remaining(state, reqs)
    open_n = int((reqs["status"] != "resolved").sum()) if len(reqs) else 0
    units_moving = len(miss)

    h1, h2 = st.columns([3.4, 1])
    h1.markdown("<span class='cs-fhdr'>CLIMATESHIELD · FACILITATOR SCREEN · simulator only — "
                "shares this exercise with the operator console</span>", unsafe_allow_html=True)
    h2.markdown("<a href='?' style='font-size:1rem;'>→ operator console</a>", unsafe_allow_html=True)

    if not state.get("running"):
        st.markdown("<div class='cs-fhuge'>NO EXERCISE RUNNING</div>", unsafe_allow_html=True)
        st.markdown("<div class='cs-fmed'>Start one from the Response & Dispatch page "
                    "(🎯 Timed exercise → ▶ Start).</div>", unsafe_allow_html=True)
        sc = state.get("final_score")
        if sc:
            st.markdown(f"<div class='cs-fbig'>Last run — {state.get('team')}: "
                        f"{sc['total']:.0f}/100 (grade {sc['grade']})</div>", unsafe_allow_html=True)
        return

    story = state["story"]
    h = exercise.sim_hour(state)
    max_h = float(state.get("max_h", 40.0))
    W = exercise.water_at(L, story, h)
    sc = exercise.score(L, state)
    grade_col = {"A": "#15803d", "B": "#4d7c0f", "C": "#b45309", "D": "#b91c1c", "E": "#7f1d1d"}.get(sc["grade"], "#6b7280")

    c1, c2, c3 = st.columns([1.35, 1, 1.9])
    c1.markdown(f"<div class='cs-fhuge'>{h:,.0f} <span class='cs-fmed'>/ {max_h:,.0f} h</span></div>",
                unsafe_allow_html=True)
    c1.markdown(f"<div class='cs-fmed'>×{state['speed']:g} speed</div>", unsafe_allow_html=True)
    c2.markdown("<div class='cs-fhdr'>WATER LEVEL</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='cs-fhuge' style='color:#2563eb;'>"
                + ("dry" if W <= 0 else f"+{W:.2f} m") + "</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='cs-fmed'>land flooded {L.flooded_share(W):.0f}%</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='cs-fbig'>{state['team']} · {story['title']}</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='cs-fmed'>{exercise.caption_at(story, h)}</div>", unsafe_allow_html=True)
    st.progress(min(h / max_h, 1.0))

    st.markdown(f"""
    <div class="cs-fgrid">
      <div class="cs-fcard"><span>Live score</span><div class="cs-fbig" style="color:{grade_col};"
        >{sc['total']:.0f}<span class="cs-fmed">/100 · {sc['grade']}</span></div></div>
      <div class="cs-fcard"><span>People waiting for pickup</span><div class="cs-fbig">{waiting:,}</div></div>
      <div class="cs-fcard"><span>Open requests</span><div class="cs-fbig">{open_n}</div></div>
      <div class="cs-fcard"><span>Units moving</span><div class="cs-fbig">{units_moving}</div>
        <div style="font-size:.95rem;color:#6b7280">{aboard} aboard boats now</div></div>
      <div class="cs-fcard"><span>Evacuees sheltered</span><div class="cs-fbig">{shel_hc:,}</div></div>
    </div>""", unsafe_allow_html=True)

    fired = [e for e in state.get("events", []) if e.get("fired_at")]
    st.markdown("<div class='cs-fhdr'>EVENT FEED</div>", unsafe_allow_html=True)
    for e in reversed(fired[-5:]):
        if e.get("acked_at"):
            st.markdown(f"<div class='cs-fmed' style='color:#15803d;'>✔ h{e['h']:,.0f} · {e['title']}</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='cs-fbig' style='color:#b91c1c;'>🔴 h{e['h']:,.0f} · {e['title']} — "
                        f"<i>awaiting acknowledgment</i></div>", unsafe_allow_html=True)
    nxt = next((e for e in state.get("events", []) if not e.get("fired_at")), None)
    if nxt:
        st.markdown(f"<div class='cs-fmed' style='color:#9ca3af;'>next complication ~h{nxt['h']:,.0f} · {nxt['title']}</div>",
                    unsafe_allow_html=True)


if st.query_params.get("facilitator") == "1" or st.session_state.get("facilitator"):
    _fragment_facilitator()
    st.stop()

page = st.sidebar.radio("ClimateShield · Dagupan", NAV, label_visibility="collapsed", key="nav_page")
st.sidebar.caption(f"{APP_VERSION} · community planning proxy · official warnings: PAGASA / CDRRMO")
st.sidebar.markdown(f"""
    **City card** · Dagupan City, Pangasinan
    PSA 2020 pop **{L.meta['psa_pop_2020']:,}** · 31 barangays
    Active land **{L.meta['active_land_km2']:.1f} km²** (of 44.47 official)
    Facilities **{L.meta['n_facilities']}** · buildings **{L.meta['n_buildings']:,}** · roads **{L.road_len_km:.0f} km**
    """)
display_options_sidebar()

# ================================================================= HOME
if page == NAV[0]:
    st.markdown('<div class="cs-kicker">Dagupan City · Pangasinan · community disaster intelligence</div>',
                unsafe_allow_html=True)
    st.markdown('<h1 style="margin-top:0">🌊 ClimateShield <span class="cs-grad">Command Center</span></h1>',
                unsafe_allow_html=True)
    st.caption("Floods, heat, and the plans that beat them — watch a scenario unfold, then change the factors that decide it.")

    live, ok = get_live()
    cur = (live or {}).get("current", {})
    if cur:
        HI = dc.hi_c(cur["temperature_2m"], cur["relative_humidity_2m"])
        cat, col, _ = dc.hi_category(HI)
        catcolor = "#38bdf8" if cat in ("No Caution", "Caution") else "#fb923c"
        banner(
            f"{freshness_badge(cur, ok)}<br>{cur['temperature_2m']:.1f}°C · RH {cur['relative_humidity_2m']:.0f}% · "
            f"rain now {cur.get('precipitation', 0):.1f} mm → "
            f"<span style='font-weight:700;color:{catcolor};'>heat index ≈ {HI:.0f}°C ({cat})</span>",
            "info" if cat in ("No Caution", "Caution") else "warn",
        )

    g_last = kit.gauge_history()
    if len(g_last):
        g_state, g_col = kit.gauge_class(float(g_last.iloc[-1]["level_m"]))
        g_lab = f"{g_state} · last {float(g_last.iloc[-1]['level_m']):.2f} m"
    else:
        g_state, g_col, g_lab = "no river log yet", "#6b7280", "no river log yet"
    try:
        n_crowd = len(pd.read_csv(ROOT / "data" / "app_layers" / "crowd_reports.csv"))
    except Exception:
        n_crowd = 0
    src = (cur or {}).get("source", "—")
    st.markdown(f"""
    <div class="cs-warn" style="font-size:12.5px;padding:8px 14px;">
      <b>ACTIVE NOW</b> · river Pantal: <span style="background:{g_col};color:#fff;padding:2px 8px;
      border-radius:5px;font-size:11.5px;">{g_lab}</span> · crowd reports logged: <b>{n_crowd}</b>
      · live feed: <b>{src}</b> @ {(cur or {}).get('fetched_at', '—')}
    </div>""", unsafe_allow_html=True)


    panels = PREFS.get("deck_panels", DEFAULT_PREFS["deck_panels"])
    month_now = datetime.now().month
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rain_m = L.daily[L.daily["RAIN"] >= 50].groupby("MONTH").size().reindex(range(1, 13), fill_value=0) / 45.7
    hi_m = L.daily[L.daily["HI"] >= 42].groupby("MONTH").size().reindex(range(1, 13), fill_value=0) / 45.7

    # ----------------------------------------------------------------- STORM THEATRE (map time-lapse)
    if panels.get("cinema", True):
        st.markdown('<div class="cs-kicker" style="margin-top:6px">Scenario time-lapse · on the satellite map</div>',
                    unsafe_allow_html=True)
        st.markdown("### 🎬 What happens when… and what decides it")
        tab_f, tab_h, tab_c, tab_r = st.tabs(["🌊 Flood scenarios", "🔥 Heat scenarios", "🎛️ Build your own storm",
                                              "🌩 Real storm replays"])

        with tab_f:
            fkeys = list(cinema.FLOOD_STORIES.keys())
            flabels = {k: cinema.FLOOD_STORIES[k]["title"] for k in fkeys}
            fsel = st.radio("Scenario", fkeys, format_func=lambda k: flabels[k], horizontal=True,
                            label_visibility="collapsed", key="film_flood")
            s = show_storm(fsel, height=500, gate="play_flood")
            other = "prepared" if fsel == "unprepared" else ("unprepared" if fsel == "prepared" else None)
            f1, f2, f3, f4, f5 = st.columns(5)
            f1.markdown(factor_tile("Peak water", f"+{s['peak_W']:.2f} m", f"hour {s['peak_hour']:.0f}"), unsafe_allow_html=True)
            f2.markdown(factor_tile("Tide / surge", f"+{s['tide']:.2f} m", "sea pushes rivers back"), unsafe_allow_html=True)
            f3.markdown(factor_tile("Drains blocked", f"{s['clog'] * 100:.0f}%", "raises & prolongs the peak"), unsafe_allow_html=True)
            f4.markdown(factor_tile("Pumps · warning", f"{'on' if s['pumps'] else 'off'} · {s['warning_h']} h",
                                    "what the city controls"), unsafe_allow_html=True)
            f5.markdown(factor_tile("Stranded at worst", f"{s['stranded']:,.0f}",
                                    f"{s['hours_wet']:.0f} h of streets under water"), unsafe_allow_html=True)
            if other:
                _, so = storm_html(other, None, 500)
                diff = so["stranded"] - s["stranded"]
                verb = "fewer" if diff < 0 else "more"
                st.markdown(
                    f'<div class="cs-banner" style="margin-top:8px"><b>Same storm, different city.</b> '
                    f'Switching to <i>{so["title"]}</i> leaves <b>{abs(diff):,.0f} {verb} people stranded</b> '
                    f'and the peak {"rises" if so["peak_W"] > s["peak_W"] else "drops"} to +{so["peak_W"]:.2f} m. '
                    f'The difference is drains, pumps and a {so["warning_h"]}-hour head start — not the rain.</div>',
                    unsafe_allow_html=True)
            st.caption("Proxy physics on Copernicus GLO-30 terrain: water = scenario base + tide + blocked-drain surcharge − pumps; "
                       "evacuation follows the warning lead-time. Note: GLO-30 flattens Dagupan's fishpond/wetland belt to 0 m, "
                       "so most low barangays flood together once water passes +0.15 m. Not a hydraulic model.")

        with tab_h:
            hs1, hs2, hs3, hs4 = st.tabs(["📋 Protocol board", "🌡️ Scenario films", "🎛️ Build your own heat day",
                                          "❄️ Cooling register"])
            with hs1:
                st.caption("What the next 48 hours demand, by official band — compiled from PAGASA categories, "
                           "DepEd class rules and DOLE labor guidance (sources listed under each block).")
                hourly = (live or {}).get("hourly") or {}
                if "temperature_2m" in hourly and len(hourly.get("temperature_2m") or []):
                    now_h = pd.Timestamp.now().floor("h")
                    htimes = pd.to_datetime(hourly["time"])
                    fmask = np.asarray(htimes >= now_h) & np.asarray(htimes <= now_h + pd.Timedelta(hours=48))
                    fx, ft, fr = htimes[fmask], np.array(hourly["temperature_2m"])[fmask], np.array(
                        hourly["relative_humidity_2m"])[fmask]
                    fhi = [float(dc.hi_c(t, r)) for t, r in zip(ft, fr)]
                    fhr = [(x - x.floor("D")).total_seconds() / 3600 for x in fx]
                    st.markdown(f"**Next 48 h at the city centre** — peak **{max(fhi):.0f}°C "
                                f"({dc.hi_category(max(fhi))[0]})** · computed from the live forecast grid.")
                    for blk in heat.day_blocks(fhr, fhi):
                        with st.container(border=True):
                            st.markdown(f"**{blk['block']}** ({blk['hours']}) · peak **{blk['peak_hi']:.0f}°C** "
                                        f"<span class='cs-badge' style='background:{blk['color']};color:#fff;'>"
                                        f"{blk['band']}</span> — {blk['headline']}", unsafe_allow_html=True)
                            rows = []
                            for p in heat.protocol_for(blk["peak_hi"]):
                                for owner, text in p["actions"]:
                                    rows.append(dict(step=owner, action=text))
                            st.dataframe(pd.DataFrame(rows).drop_duplicates(), hide_index=True,
                                         use_container_width=True)
                            st.caption("Sources: " + " · ".join(
                                s for p in heat.protocol_for(blk["peak_hi"]) for s in p["sources"])[:220])
                    rank = heat.hi_hours_by_barangay(L, fhr, fhi)
                    st.markdown("**Open respite points in these barangays first** (people × DANGER hours, "
                                "dense cores feel +1–3°C hotter)")
                    st.dataframe(rank.head(8)[["name", "pop", "danger_h", "people_hours"]]
                                 .rename(columns={"name": "barangay", "pop": "census",
                                                  "danger_h": "danger hours (next 48 h)",
                                                  "people_hours": "people-hours"}),
                                 hide_index=True, use_container_width=True)
                else:
                    st.info("Forecast temperature/humidity not in the current feed — reload after a live fetch.")
            with hs2:
                hkeys = list(cinema.HEAT_STORIES.keys())
                hlabels = {k: cinema.HEAT_STORIES[k]["title"] for k in hkeys}
                hsel = st.radio("Heat scenario", hkeys, format_func=lambda k: hlabels[k], horizontal=True,
                                label_visibility="collapsed", key="film_heat")
                hstory = cinema.HEAT_STORIES[hsel]
                hc, hm = st.columns([1.25, 1])
                with hc:
                    fig_h, hplan = cinema.heat_chart(L, hstory, theme_text=BEIGE_TEXT, grid=PLOT_GRID, height=420)
                    st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
                    st.caption("Hover a point for the hour's protocol line. Bands = PAGASA heat-index categories.")
                pk = max(hplan, key=lambda f: f["hi"])
                with hm:
                    hh = st.select_slider("Hour", options=[f["hour"] for f in hplan], value=pk["hour"], key="heat_hour",
                                          format_func=lambda h: f"{h:02d}:00")
                    fh = next(f for f in hplan if f["hour"] == hh)
                    pts = cinema.heat_barangay_points(L, fh["hi"])
                    try:
                        import folium
                        from streamlit_folium import st_folium
                        hmap = folium.Map(location=(16.055, 120.335), zoom_start=12, tiles=None)
                        folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1]).add_to(hmap)
                        for pt in pts:
                            folium.CircleMarker([pt["lat"], pt["lon"]], radius=6 + 10 * (pt["pop"] / 15000), color="white",
                                                weight=1, fill=True, fill_color=pt["color"], fill_opacity=0.9,
                                                tooltip=f"{pt['name']} · feels like {pt['hi']:.0f}°C · pop {pt['pop']:,}").add_to(hmap)
                        st_folium(hmap, height=360, use_container_width=True, returned_objects=[], key="heat_map")
                    except Exception as e:
                        st.info(f"Map unavailable ({type(e).__name__}).")
                    st.caption(f"{hh:02d}:00 · city heat index {fh['hi']:.0f}°C · circles = barangays (size = population, "
                               "colour = felt heat with urban-heat offset)")
                h1, h2, h3, h4 = st.columns(4)
                h1.markdown(factor_tile("Peak heat index", f"{pk['hi']:.0f}°C", f"{dc.hi_category(pk['hi'])[0]} · {pk['hour']:02d}:00"), unsafe_allow_html=True)
                h2.markdown(factor_tile("Hours in DANGER", f"{sum(1 for f in hplan if f['hi'] >= 41)}", "HI ≥ 41°C citywide"), unsafe_allow_html=True)
                h3.markdown(factor_tile("Indoors feels like", f"{max(f['hi_indoor'] for f in hplan):.0f}°C",
                                        "brownout: no fans" if hstory["brownout"] else "with fans running"), unsafe_allow_html=True)
                h4.markdown(factor_tile("Outdoor-worker stress", f"{hplan[-1]['stress']:.1f} h", "cumulative exposure load"), unsafe_allow_html=True)

            with hs3:
                st.caption("Familiar dials, new enemy: set a worst day, then read off what the protocols would demand.")
                d1, d2, d3, d4 = st.columns(4)
                with d1:
                    h_tmax = st.slider("Afternoon peak air (°C)", 31, 40, 36, 1, key="hx_tmax")
                with d2:
                    h_rh = st.slider("Midday humidity (%RH)", 40, 95, 62, 1, key="hx_rh")
                with d3:
                    h_br = st.toggle("Brownout 10:00–16:00", value=True, key="hx_br",
                                     help="No fans, no cold water — indoor line runs ~3°C hotter than shade.")
                with d4:
                    hnight = st.toggle("Tropical night after (min 27°C)", value=True, key="hx_night",
                                       help="No overnight relief — tomorrow starts hot.")
                hstory_x = dict(title="Your worst day", tmax=float(h_tmax), tmin=27.0 if hnight else 25.5,
                                rh_day=float(h_rh), rh_night=80.0, brownout=bool(h_br))
                figx, planx = cinema.heat_chart(L, hstory_x, theme_text=BEIGE_TEXT, grid=PLOT_GRID, height=360)
                st.plotly_chart(figx, use_container_width=True, config={"displayModeBar": False})
                pkx = max(planx, key=lambda f: f["hi"])
                st.markdown(f"**Peak {pkx['hi']:.0f}°C ({dc.hi_category(pkx['hi'])[0]}) at {pkx['hour']:02d}:00** — "
                            f"indoors feels {max(f['hi_indoor'] for f in planx):.0f}°C, "
                            f"outdoor-worker load {planx[-1]['stress']:.1f} h.")
                for p in heat.protocol_for(pkx["hi"]):
                    with st.expander(f"{p['band']} — {p['headline']}", expanded=(p['lo'] >= 42)):
                        for owner, text in p["actions"]:
                            st.markdown(f"**{owner}:** {text}")
                        st.caption("Sources: " + " · ".join(p["sources"]))

            with hs4:
                st.caption("Shaded, ventilated, generator-backed points where people can cool down — registered like "
                           "shelters, matched by distance. Nothing is pre-filled: the first thing a drill does is "
                           "register what actually exists.")
                stt = heat.cooling_stats()
                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("Centers open", stt["open"],
                           f"{heat.practice_count()} practice candidates" if heat.practice_count() else
                           "none registered")
                cc2.metric("Full", stt["full"])
                cc3.metric("Capacity known", f"{stt['capacity_known']}")
                if st.button("➕ Register OPEN shelters as cooling points", key="cool_seed",
                             help="Copies every open shelter into this board once. Cooling status is then managed here."):
                    n = heat.seed_cooling_from_shelters(L)
                    st.toast(f"Added {n} cooling point(s)" if n else
                             "Nothing new to register — the roster has no OPEN shelter yet (use the practice set below)")
                    st.rerun()
                if not heat.cooling_stats()["open"]:
                    st.caption("The roster ships every shelter **closed**, so there is nothing to copy. Register the "
                               "practice set instead: roster shelters become **practice candidates** (labelled as "
                               "such on every map) so rings, reach and gap maps have something to draw.")
                    if st.button("❄ Register practice cooling points", key="cool_seed_practice",
                                 use_container_width=True):
                        n = heat.seed_practice_cooling(L)
                        st.toast(f"Added {n} practice cooling point(s)" if n else "Nothing new to register")
                        st.rerun()
                ced = st.data_editor(heat.load_cooling(), num_rows="dynamic", hide_index=True,
                                     use_container_width=True, key="cool_ed",
                                     column_config={"kind": st.column_config.SelectboxColumn("kind", options=heat.COOL_KINDS),
                                                    "status": st.column_config.SelectboxColumn("status", options=heat.COOL_STATUS),
                                                    "center_id": st.column_config.TextColumn(disabled=True),
                                                    "source": st.column_config.TextColumn(disabled=True),
                                                    "lat": st.column_config.NumberColumn("latitude", format="%.5f"),
                                                    "lon": st.column_config.NumberColumn("longitude", format="%.5f"),
                                                    "updated_at": None})
                if st.button("💾 Save cooling board", key="save_cool"):
                    cx = ced.copy()
                    nums = [int(x[1:]) for x in cx["center_id"].astype(str) if x[:1] == "C" and x[1:].isdigit()]
                    nx = max(nums, default=0) + 1
                    for i in cx.index:
                        if not str(cx.at[i, "center_id"]).strip():
                            cx.at[i, "center_id"] = f"C{nx:03d}"
                            nx += 1
                    empty_rows = cx[cx["name"].astype(str).str.strip() == ""].index
                    heat.save_cooling(cx.drop(index=empty_rows))
                    st.toast("Cooling board saved")
                    st.rerun()


        with tab_c:
            st.markdown("Set the dials, then watch your own storm play out on the map. Each dial is a real lever or hazard.")
            c1, c2, c3 = st.columns(3)
            with c1:
                c_scen = st.selectbox("Storm class", list(dc.SCENARIOS.keys()), index=2, key="cin_scen")
                c_tide = st.slider("Tide / storm surge (+m)", 0.0, 1.2, 0.45, 0.05, key="cin_tide")
            with c2:
                c_clog = st.slider("Drains blocked (%)", 0, 100, 60, 5, key="cin_clog")
                c_pumps = st.toggle("Pumps staged at outfalls", value=False, key="cin_pumps")
            with c3:
                c_warn = st.slider("Evacuation head start (hours before peak)", 0, 16, 2, 1, key="cin_warn")
                c_surge = st.slider("Upstream surge pulse (+m)", 0.0, 0.6, 0.0, 0.05, key="cin_surge")
            params = dict(share=dc.SCENARIOS[c_scen], tide=float(c_tide), clog=c_clog / 100.0,
                          pumps=bool(c_pumps), warning_h=int(c_warn), surge=float(c_surge))
            sc = show_storm("custom", height=480, params=params, gate="play_custom")
            g1, g2, g3, g4 = st.columns(4)
            g1.markdown(factor_tile("Peak water", f"+{sc['peak_W']:.2f} m", f"hour {sc['peak_hour']:.0f}"), unsafe_allow_html=True)
            g2.markdown(factor_tile("People in water", f"{sc['pop_in']:,.0f}", "at the peak"), unsafe_allow_html=True)
            g3.markdown(factor_tile("Moved to shelters", f"{sc['evacuated']:,.0f}", f"{c_warn} h head start"), unsafe_allow_html=True)
            g4.markdown(factor_tile("Stranded", f"{sc['stranded']:,.0f}", "the number to drive to zero"), unsafe_allow_html=True)

        with tab_r:
            st.caption("Real events from the 45-year record (1981–2026), replayed on today's city. A rainfall-storage "
                       "curve (6-day memory) links each day's recorded rain to the proxy flood share, anchored so the "
                       "Aug 2026 habagat matches the CDRRMO 23/31-barangay report and Pepeng 2009 hits the Extreme class.")
            r1, r2 = st.columns([1, 1.5])
            with r1:
                r_ev = st.selectbox("Historical event", list(replay.EVENTS.keys()),
                                    format_func=lambda k: replay.EVENTS[k]["label"], key="rp_ev")
                r_rd = st.radio("City readiness", list(replay.READINESS.keys()),
                                format_func=lambda k: replay.READINESS[k]["label"], key="rp_rd",
                                help=replay.READINESS["prepared"]["note"])
                st.caption(replay.EVENTS[r_ev]["note"])
                story_r = replay.build_story(L, r_ev, r_rd)
                figh = go.Figure()
                figh.add_bar(x=[d for d, _ in story_r["daily_rain"]], y=[r for _, r in story_r["daily_rain"]],
                             name="rain/day (mm)", marker_color="#38bdf8")
                figh.add_trace(go.Scatter(x=[d for d, _ in story_r["daily_rain"]],
                                          y=[replay.water_at(story_r, i * 24 + 12) for i in range(len(story_r["daily_rain"]))],
                                          name="water level (m)", yaxis="y2",
                                          line=dict(color="#dc2626", width=2.5)))
                figh.update_layout(height=230, margin=dict(l=8, r=8, t=24, b=8), barmode="overlay",
                                   legend=dict(orientation="h", y=1.15, x=0, font=dict(size=10)),
                                   yaxis=dict(title="mm/day", gridcolor=PLOT_GRID),
                                   yaxis2=dict(title="m", overlaying="y", side="right", range=[-0.4, 1.2], gridcolor=PLOT_GRID))
                st.plotly_chart(plotly_beige(figh, height=230), use_container_width=True, config={"displayModeBar": False})
            with r2:
                r_html, rs = replay_storm_html(r_ev, r_rd, 500)
                if _gate("play_replay", "Tiles above describe the event; the animated film loads on your tap (≈2–5 MB)."):
                    components.html(r_html, height=500 + STORM_STRIP_PX, scrolling=False)
                q1, q2, q3, q4 = st.columns(4)
                q1.markdown(factor_tile("Peak water", f"+{rs['peak_W']:.2f} m", rs['peak_label'] or f"hour {rs['peak_hour']:.0f}"), unsafe_allow_html=True)
                q2.markdown(factor_tile("Land flooded", f"{rs['flooded_share']:.0f}%", f"{rs['pop_in']:,.0f} people in water"), unsafe_allow_html=True)
                q3.markdown(factor_tile("Stranded at worst", f"{rs['stranded']:,.0f}", f"{rs['hours_wet']:.0f} h of flooded streets"), unsafe_allow_html=True)
                q4.markdown(factor_tile("Roads cut", f"{rs['roads_km']:.0f} km", f"{rs['bldg']:,} buildings in water"), unsafe_allow_html=True)

    st.markdown("#### Where do you want to go?")
    na, nb, nc, nd, ne = st.columns(5)
    na.button("🌊 Simulate a flood", type="primary", use_container_width=True,
              help="Storm + tide sliders → impact map, storm time-lapse, evacuation route",
              on_click=_nav_to, args=(NAV[1],))
    nb.button("🛡️ Plan countermeasures", use_container_width=True,
              help="Dredging / drainage / relocation — watch exposure drop", on_click=_nav_to, args=(NAV[3],))
    nc.button("📡 Live telemetry", use_container_width=True,
              help="Rain radar, river log, crowd reports, heat gauge", on_click=_nav_to, args=(NAV[4],))
    nd.button("🗺️ My barangay", use_container_width=True,
              help="5-step guided walkthrough ending in an action card + PDF briefing", on_click=_nav_to, args=(NAV[5],))
    if ne.button("📺 Wall display", use_container_width=True,
                 help="Full-screen auto-rotating command center for an ops room TV"):
        PREFS["kiosk"] = True
        save_prefs(PREFS)
        st.rerun()
    q1, q2 = st.columns([3.2, 1])
    with q1:
        st.selectbox("🔍 Quick-search a barangay — jumps straight to its walkthrough",
                     sorted(L.brgy["barangay"].tolist()), key="quick_brgy")
    with q2:
        st.write("")
        st.button("Go →", type="primary", use_container_width=True,
                  on_click=_go_brgy, args=(st.session_state["quick_brgy"],))
    if st.button("🚶 Check my evacuation route", use_container_width=True,
                 help="Real streets to the nearest shelter on the satellite map, coloured by how deep the water gets.",
                 on_click=_go_walk):
        pass
    _rq = rsp.load_requests()
    _open = _rq[_rq["status"] != "resolved"] if len(_rq) else _rq
    st.button(f"🚑 Response & Dispatch — {len(_open)} open request(s)", use_container_width=True,
              type="primary" if len(_open) else "secondary", on_click=_nav_to, args=(NAV[6],),
              help="Log stranded-community requests, see nearest hospitals / fire / police / shelters, dispatch.")

    if panels.get("kpis"):
        st.markdown('<div class="cs-kicker" style="margin-top:10px">City at a glance</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Residents (PSA 2020)", f"{L.meta['psa_pop_2020']:,}", "~80% on ≤2 m land")
        with c2:
            top = L.brgy.sort_values("CSRI", ascending=False).iloc[0]
            st.metric("Top-risk barangay", str(top["barangay"]), f"CSRI {top['CSRI']:.0f}/100")
        with c3:
            st.metric("Heat danger-days this month (avg)", f"{hi_m.reindex([month_now], fill_value=0).iloc[0]:.0f}",
                      "PAGASA Danger band (HI ≥ 42°C)", delta_color="inverse")
        with c4:
            st.metric("Heavy-rain days this month (avg)", f"{rain_m.reindex([month_now], fill_value=0).iloc[0]:.1f}",
                      "≥ 50 mm/day", delta_color="inverse")

    if panels.get("calendar", True):
        st.subheader("Readiness calendar (45-year averages)")
        fdf = pd.DataFrame({"month": month_names, "heavy rain": rain_m.values.round(2),
                            "heat danger": hi_m.values.round(2)})
        figp = go.Figure()
        figp.add_bar(x=fdf["month"], y=fdf["heavy rain"], name="heavy-rain days", marker_color="#38bdf8")
        figp.add_bar(x=fdf["month"], y=fdf["heat danger"], name="heat danger days", marker_color="#fb923c")
        figp.add_vrect(x0=month_names[month_now - 1], x1=month_names[month_now - 1],
                       line_color=ACCENT2, line_width=3)
        figp.update_layout(barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(plotly_beige(figp, height=260, y_title="days/yr"), use_container_width=True)

    if panels.get("watchlist"):
        st.subheader("Barangay watchlist — click a row for details")
        wl = L.brgy.dropna(subset=["CSRI"]).sort_values("CSRI", ascending=False).head(12)
        show = wl[["barangay", "popn", "urban", "mean_susc_300m", "CSRI"]].reset_index(drop=True)
        sel = st.dataframe(show, hide_index=True, use_container_width=True, on_select="rerun",
                           selection_mode="single-row")
        rows = sel.selection.rows
        if rows:
            r = show.iloc[rows[0]]
            brow = L.brgy[L.brgy["barangay"] == r["barangay"]].iloc[0]
            W_c = L.water_level_for_share(45)
            d_c = L.depth_grid(W_c)[0]
            e_c = L.exposure(d_c, W_c)
            est = None
            if r["barangay"] in e_c["barangay_impact"]["barangay"].values:
                est = e_c["barangay_impact"].set_index("barangay").loc[r["barangay"], "affected_est"]
            with st.container(border=True):
                st.markdown(f"#### 📋 {r['barangay']}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Census 2020", f"{int(brow['popn']):,}")
                m2.metric("CSRI", f"{brow['CSRI']:.0f}", "of 100")
                m3.metric("Mean susceptibility (300 m)", f"{brow['mean_susc_300m']:.0f}")
                m4.metric("Est. affected · calamity event", f"{est if est is not None else '—'}")
                st.caption(f"Anchor: {brow.get('anchor', 'none')} · buildings within 600 m: "
                           f"{int(brow.get('bldg_600m', 0) or 0)} · guided drill-down lives in 🗺️ Barangay Walkthrough.")
        else:
            st.caption("CSRI = flood-susceptibility × population × density × urban percentile blend. Click a barangay to open its card.")

# ================================================================= SIMULATOR
@st.fragment
def _fragment_sim():
    st.button("Back to Command Deck", on_click=_nav_to, args=(NAV[0],))
    st.title(f"🌊 {tt('Flood Scenario Simulator')}")
    st.caption("Event-scale water levels calibrated to Dagupan terrain percentiles and the Aug 2026 CDRRMO sitrep share.")

    view = st.radio("Map view", ["🗺️ Impact map", "🎬 Storm time-lapse", "🚶 Evacuation route"], horizontal=True,
              label_visibility="collapsed", key="sim_view")

    ctl, mapcol = st.columns([1, 3.1])
    with ctl:
        st.markdown("#### Scenario")
        scen = st.selectbox("Storm event class", list(dc.SCENARIOS.keys()), index=2, label_visibility="collapsed")
        share = dc.SCENARIOS[scen]
        tide = st.slider("High-tide / surge add-on (m)", 0.0, 1.5, 0.20, 0.05,
                         help="Pantal is tidal — Aug 2026 floods lasted 7+ days.")
        tl_on = st.checkbox("⏱ Time-lapse: scrub the event hour", value=False,
                            help="Hour 0 = storm onset · ~10 h = peak · then slow drainage decay (Dagupan water sits for days).")
        anim = bool(st.session_state.get("anim", False))
        if tl_on and not anim:
            if st.button("▶ Play the 48-hour event", use_container_width=True):
                st.session_state["anim"] = True
                st.query_params["h"] = "0"
                st.rerun()
        if tl_on and anim:
            if st.button("⏸ Pause", use_container_width=True):
                st.session_state["anim"] = False
                try:
                    del st.query_params["h"]
                except Exception:
                    pass
                st.rerun()
        if tl_on and anim:
            try:
                hour = int(np.clip(int(float(st.query_params.get("h", "0"))), 0, 48))
            except Exception:
                hour = 0
            st.progress(min(hour / 48.0, 1.0), text=f"Playing — event hour {hour}/48")
            if hour < 48:
                components.html(
                    f"<script>window.setTimeout(function(){{var u=new URL(window.parent.location.href);"
                    f"u.searchParams.set('h',{hour + 2});window.parent.location.href=u.toString();}},1100);</script>",
                    height=0)
            else:
                st.session_state["anim"] = False
                st.success("Event complete — water has drained back toward tide. Move the slider to replay any hour.")
        elif tl_on:
            hour = st.slider("Event hour", 0, 48, 24, 1)
        else:
            hour = 24
        W_peak = L.water_level_for_share(share) + tide
        W = kit.curve_W(W_peak, tide, float(hour)) if tl_on else W_peak
        depth, _ = L.depth_grid(W)
        exp = L.exposure(depth, W)
        st.markdown("#### Output")
        st.metric("Effective water level", f"+{W:.2f} m", f"event hour {hour}" if tl_on else "above sea datum")
        st.metric("Trigger class", PAG_CLASSES[scen].split(" - ")[0])
        st.metric("Land flooded", f"{exp['area_flooded_km2']:.1f} km²",
                  f"{exp['area_flooded_km2'] / L.meta['active_land_km2'] * 100:.0f}% of active land")
        with st.expander("How this is modeled"):
            st.markdown(
                """
                        - Event class → land-flood share (Advisory 12% · Alert 30% · Calamity 45% —
                          *23/31 barangays ≈ 74% by count, ~45% by area, per the Aug 2026 SitRep* · Extreme 65%)
                        - Water level = elevation percentile of the active-land DEM (Copernicus GLO-30)
                        - Depth = water level − terrain, inside the active-land mask. **Not a hydraulic model**;
                        dredging/drainage/relocation economics live in the Countermeasure Lab.
                        """
            )

    with mapcol:
        if view.startswith("🚶"):
            preset = st.session_state.pop("street_brgy", None)
            brgy_list = sorted(L.brgy["barangay"].tolist())
            sw_brgy = st.selectbox("Start from barangay", brgy_list,
                                   index=brgy_list.index(preset) if preset in brgy_list else brgy_list.index("Pantal"))
            w_here = st.slider("Water level on the streets (+m)", 0.0, max(1.5, W + 0.3), float(W), 0.05,
                               help="Defaults to the scenario's water level — drag to test higher water.")
            route_card(sw_brgy, w_here, key_prefix="sim_rc")
        elif view.startswith("🎬"):
            st.markdown("**This storm, hour by hour, on the satellite map.** Same event class and tide as the controls; "
                        "set the city's readiness and watch 40 hours play out. Caption, counters and flood overlay "
                        "share one clock.")
            fc1, fc2, fc3 = st.columns(3)
            s_clog = fc1.slider("Drains blocked (%)", 0, 100, 60, 5, key="sim_film_clog")
            s_pumps = fc2.toggle("Pumps staged at outfalls", value=False, key="sim_film_pumps")
            s_warn = fc3.slider("Evacuation head start (h)", 0, 16, 2, 1, key="sim_film_warn")
            sp = dict(share=share, tide=float(tide), clog=s_clog / 100.0, pumps=bool(s_pumps),
                      warning_h=int(s_warn), surge=0.0)
            sf = show_storm("custom", height=500, params=sp, gate="play_sim")
            j1, j2, j3, j4 = st.columns(4)
            j1.markdown(factor_tile("Peak water", f"+{sf['peak_W']:.2f} m", f"hour {sf['peak_hour']:.0f}"), unsafe_allow_html=True)
            j2.markdown(factor_tile("People in water", f"{sf['pop_in']:,.0f}", "at the peak"), unsafe_allow_html=True)
            j3.markdown(factor_tile("Moved to shelters", f"{sf['evacuated']:,.0f}", f"{s_warn} h head start"), unsafe_allow_html=True)
            j4.markdown(factor_tile("Stranded", f"{sf['stranded']:,.0f}", "drive this to zero"), unsafe_allow_html=True)
        else:
            choro = {}
            if exp.get("barangay_impact") is not None:
                for _, r in exp["barangay_impact"].iterrows():
                    frac = None
                    if L.brgy_cells is not None and r.get("basis") in ("polygon", "anchor window"):
                        est = r["affected_est"]
                        if est is not None and r["census"]:
                            frac = min(1.0, float(est) / float(r["census"]))
                    if frac is not None:
                        choro[r["barangay"]] = dict(
                            frac=frac,
                            note=f"{100 * frac:.0f}% of residents estimated in flood zones "
                                 f"({int(r['affected_est']):,} of {int(r['census']):,}) · basis: {r['basis']}")
            try:
                from streamlit_folium import st_folium
                fm = kit.make_city_map(L, depth=depth, W_cut=W, zoom=13, choro=choro, crowd=True)
                st_folium(fm, height=640, use_container_width=True, returned_objects=[])
                st.caption("Drag to pan · scroll to zoom · shaded barangays = share of residents estimated in "
                           f"flood zones ({L.boundary_source.split('(')[0].strip()}) · hover roads (% cut), "
                           "facilities (flood state), crowd pins and barangays · layer control top-right")
            except Exception:
                fig = draw_map(depth=depth, title=f"{scen} + tide {tide:.2f} m → water +{W:.2f} m")
                st.pyplot(fig)
                plt.close(fig)
            sbuf = __import__("io").BytesIO()
            sfig = draw_map(depth=depth, labels=False, title=f"{scen} + tide {tide:.2f} m → water +{W:.2f} m")
            sfig.savefig(sbuf, format="png", dpi=160, bbox_inches="tight")
            plt.close(sfig)
            st.download_button("⬇ Download this scenario map (PNG)", data=sbuf.getvalue(),
                               file_name=f"dagupan_{scen.split()[0].lower()}_tide{tide:.2f}.png",
                               mime="image/png", use_container_width=True)

    if tl_on:
        hs = list(range(0, 49, 4))
        pops = []
        for hh in hs:
            Wh = kit.curve_W(W_peak, tide, float(hh))
            pops.append(L.exposure(L.depth_grid(Wh)[0], Wh)["pop_affected"])
        figt = go.Figure()
        figt.add_trace(go.Scatter(x=hs, y=pops, mode="lines", name="residents affected",
                                  line=dict(color=ACCENT, width=3), fill="tozeroy",
                                  fillcolor="rgba(37,99,235,.10)"))
        figt.add_trace(go.Scatter(x=[hour], y=[exp["pop_affected"]], mode="markers",
                                  marker=dict(size=14, color="#c0392b", line=dict(width=2, color="white")),
                                  name="your hour"))
        st.plotly_chart(plotly_beige(figt, height=250, y_title="residents",
                                      title="Event time-line — rise ~10 h, slow decay after"),
                        use_container_width=True)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Residents affected", f"{exp['pop_affected']:,.0f}",
              f"{exp['pop_affected'] / exp['pop_total'] * 100:.0f}% of city", delta_color="inverse")
    k2.metric("Buildings flooded", f"{exp['bldg_flooded']:,}", f"of {exp['bldg_total']:,} mapped", delta_color="inverse")
    k3.metric("Schools flooded", f"{exp['fac_counts'].get('school', 0)}", "OSM-mapped schools", delta_color="inverse")
    k4.metric("Health sites flooded", f"{exp['fac_counts'].get('health', 0)}", "hospitals/clinics/pharmacies", delta_color="inverse")
    k5.metric("Roads impaired", f"{exp['road_km_cut']:.0f} km", f"of {exp['road_km_total']:.0f} km (depth ≥ 0.3 m)", delta_color="inverse")

    cuttab, imp = st.columns([1, 1.3])
    with cuttab:
        st.subheader("Worst road segments — click for profile")
        rc = pd.DataFrame(exp["roads_cut_worst"])
        if len(rc):
            rc_show = rc.rename(columns={"name": "road", "km": "length km", "frac": "fraction cut"}).round(3).reset_index(drop=True)
            road_sel = st.dataframe(rc_show, hide_index=True, use_container_width=True, height=240,
                                    on_select="rerun", selection_mode="single-row")
            rrows = road_sel.selection.rows
            if rrows:
                rr = rc_show.iloc[rrows[0]]
                cand = [r for r in L.roads if (r["name"] or r["class"]) == rr["road"]]
                if cand:
                    ef = cand[0]["elevs"]
                    ef = ef[np.isfinite(ef)]
                    with st.container(border=True):
                        st.markdown(f"#### 🛣 {rr['road']}")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Length", f"{cand[0]['length_m'] / 1000:.2f} km")
                        m2.metric("Segment elevation", f"{ef.min():.2f}–{ef.max():.2f} m")
                        m3.metric("Fraction cut now", f"{rr['fraction cut'] * 100:.0f}%")
                        st.caption("Cut criterion: flood depth ≥ 0.30 m — mirrors the Aug 2026 sitrep language "
                                   "'impassable to light vehicles'.")
        else:
            st.info("No mapped road segments cut at this water level.")
    with imp:
        st.subheader("Barangay impact — click for the action card")
        top10 = exp["barangay_impact"].head(10).reset_index(drop=True)
        top10 = top10.rename(columns={"census": "census 2020", "affected_est": "affected (est)"})
        bsel = st.dataframe(top10, hide_index=True, use_container_width=True, height=240,
                            on_select="rerun", selection_mode="single-row")
        brows = bsel.selection.rows
        if brows:
            br = top10.iloc[brows[0]]
            bname = br["barangay"]
            brow = L.brgy[L.brgy["barangay"] == bname].iloc[0]
            with st.container(border=True):
                st.markdown(f"#### 📋 {bname} — {int(br['affected (est)']):,} residents estimated in flood zones "
                            f"of {int(br['census 2020']):,} census")
                card = kit.action_card_flood(brow, W, int(br["affected (est)"]), PAG_CLASSES[scen],
                                             lang=PREFS.get("lang", "English"))
                st.code(card, language=None)
                brief, bext = kit.build_briefing(brow, None, W, int(br["affected (est)"]), PAG_CLASSES[scen],
                                                 PREFS.get("lang", "English"), map_fig_fn=None,
                                                 city_meta=L.meta, susc=float(brow.get("mean_susc_300m", 0) or 0))
                st.download_button(f"⬇ One-page barangay briefing ({bext.upper()})", data=brief,
                                   file_name=f"climateshield_briefing_{bname}.{bext}",
                                   mime="application/pdf" if bext == "pdf" else "image/png")
                if bext == "png":
                    st.caption("PDF export is unavailable on this machine (a Windows security policy blocks the PDF "
                               "library) — the briefing downloads as a printable image instead.")
                st.caption("Copy-ready for SMS/Viber/Facebook. Full guided flow in 🗺️ Barangay Walkthrough.")


    # ================================================================= HEAT SIMULATOR
@st.fragment
def _fragment_heat():
    st.button("Back to Command Deck", on_click=_nav_to, args=(NAV[0],), key="heat_back")
    if "_heat_hour_next" in st.session_state:          # hour-step buttons fire after the slider was drawn
        st.session_state["heat_hour"] = st.session_state.pop("_heat_hour_next")
    if "_heat_b_next" in st.session_state:             # map/chart clicks below run after the selectbox was drawn
        st.session_state["heat_b_sel"] = st.session_state.pop("_heat_b_next")
    st.title("☀️ Heat Scenario Simulator")
    st.caption("A whole heat day, hour by hour — what it feels like in every barangay, which relief and health "
               "services are reachable, and the survival actions behind PAGASA bands, DepEd class rules and "
               "DOLE labor guidance. Simulator only — official warnings come from PAGASA and the CDRRMO.")

    ctl, mapcol = st.columns([1, 3.1])
    with ctl:
        st.markdown("#### Heat day")
        mode = st.radio("Day source", ["📌 Recorded heat days", "🎛️ Build your own day", "📡 Live forecast (today)"],
                        horizontal=True, label_visibility="collapsed", key="heat_mode")
        if mode.startswith("📌"):
            hkeys = list(cinema.HEAT_STORIES.keys())
            hsel = st.selectbox("Recorded day", hkeys, format_func=lambda k: cinema.HEAT_STORIES[k]["title"], key="heat_story")
            hstory = cinema.HEAT_STORIES[hsel]
        elif mode.startswith("🎛️"):
            d1, d2 = st.columns(2)
            hx_tmax = d1.slider("Peak air (°C)", 31, 40, 37, key="hx_tmax")
            hx_rh = d2.slider("Humidity (%RH)", 40, 95, 60, key="hx_rh")
            hx_br = st.toggle("Brownout 10:00–16:00", value=True, key="hx_br",
                              help="No fans or cold water — indoors runs ~3°C above shade.")
            hx_night = st.toggle("Tropical night (min 26.5°C)", value=True, key="hx_night",
                                 help="No overnight relief — tomorrow starts hot.")
            hstory = dict(title="Your own heat day", tmax=float(hx_tmax), tmin=26.5 if hx_night else 25.5,
                          rh_day=float(hx_rh), rh_night=80.0, brownout=bool(hx_br))
        else:
            live, ok_ = get_live()
            hourly = (live or {}).get("hourly") or {}
            now_h = pd.Timestamp.now().floor("h")
            if "temperature_2m" in hourly and len(hourly["temperature_2m"]):
                tday = pd.Series(hourly["temperature_2m"], index=pd.to_datetime(hourly["time"]))
                rhday = pd.Series(hourly["relative_humidity_2m"], index=tday.index)
                win = tday[(tday.index >= now_h.floor("D")) & (tday.index < now_h.floor("D") + pd.Timedelta(days=1))]
                rhwin = rhday.reindex(win.index)
                hstory = dict(title="Today's live forecast (min/max are live; hour shape modelled)",
                               tmax=float(win.max()), tmin=float(win.min()),
                               rh_day=float(rhwin.iloc[len(rhwin) // 2]), rh_night=float(rhwin.iloc[0]),
                               brownout=False)
            else:
                st.caption("Live hourly temperature unavailable — falling back to the April typical day.")
                hstory = cinema.HEAT_STORIES["april_typical"]
        plan = cinema.heat_plan(L, hstory)
        pkh = max(plan, key=lambda f: f["hi"])
        hour = st.select_slider("Hour of the day", options=[f["hour"] for f in plan], value=pkh["hour"],
                                key="heat_hour", format_func=lambda h: f"{h:02d}:00")
        fh = next(f for f in plan if f["hour"] == hour)
        cat, catcolor = dc.hi_category(fh["hi"])[0], dc.hi_category(fh["hi"])[1]
        i_hi = fh["hi_indoor"]
        st.markdown(f"<div class='cs-factor'><span>City feels like at {hour:02d}:00</span>"
                    f"<b style='color:{catcolor};'>{fh['hi']:.0f}°C · {cat}</b>"
                    f"<small>indoors ≈ {i_hi:.0f}°C ({'brownout' if i_hi > fh['hi'] else 'fans ok'})</small></div>",
                    unsafe_allow_html=True)
        hp = heat.protocol_for(fh["hi"])
        with st.expander("📋 Protocol at this hour", expanded=True):
            if hp:
                top = hp[-1]
                st.markdown(f"**{top['band']}** — {top['headline']}")
                for owner, text in top["actions"]:
                    st.markdown(f"- **{owner}:** {text}")
                st.caption("Sources: " + " · ".join(sorted({s for p in hp for s in p["sources"]}, key=lambda x: list(
                    heat.SOURCES).index(x)))[:200])
            else:
                st.caption("Below 27°C — no protocol band in force.")

    # one selected community + one hour drive every tab below (reach, cards and map agree)
    reach_all = heat.cooling_reach(L)
    pts = {p["name"]: p for p in cinema.heat_barangay_points(L, fh["hi"])}
    b_list = sorted(L.brgy["barangay"].tolist())
    if st.session_state.get("heat_b_sel") not in pts:
        st.session_state["heat_b_sel"] = "Pantal" if "Pantal" in pts else b_list[0]
    b_sel = st.session_state["heat_b_sel"]
    pop_max = max([p["pop"] for p in pts.values()], default=1) or 1
    cst_now = heat.cooling_stats()
    cool_open = heat.load_cooling()
    cool_open = cool_open[cool_open["status"] == "open"]
    danger_now = {nm: p for nm, p in pts.items() if p["hi"] >= 42}
    reached_now = {nm for nm in pts if reach_all.get(nm) and reach_all[nm][0] is not None
                   and reach_all[nm][0] <= 2500}
    cov_pop = sum(pts[nm]["pop"] for nm in reached_now)
    tot_pop = sum(p["pop"] for p in pts.values()) or 1

    def _reach_line(nm):
        r = reach_all.get(nm)
        if r is None or r[0] is None:
            return "no open cooling point registered"
        return f"{r[0] / 1000:.1f} km to {r[1]} ({r[2]})"

    # ------------------------------------- right-hand pane is filled by the felt-heat map (see below)

    t1, t2, t3, t4 = st.tabs(["🗺️ Felt-heat map", "🎬 Day time-lapse", "🚶 Relief reach & survival", "📄 Cards & community copy"])

    # ------------------------------------------------------------ map (pinned beside the Heat day controls)
    with mapcol:
        hs = [f["hour"] for f in plan]
        hc1, hc2, hc3, hc4 = st.columns([1.1, 1.1, 1.1, 4])
        if hc1.button("⏮ sunrise", key="heat_h_first", use_container_width=True):
            st.session_state["_heat_hour_next"] = hs[0]; st.rerun()
        if hc2.button("◀ −1 h", key="heat_h_prev", use_container_width=True):
            st.session_state["_heat_hour_next"] = hs[max(0, hs.index(hour) - 1)]; st.rerun()
        if hc3.button("+1 h ▶", key="heat_h_next", use_container_width=True):
            st.session_state["_heat_hour_next"] = hs[min(len(hs) - 1, hs.index(hour) + 1)]; st.rerun()
        hc4.markdown(f"**{hour:02d}:00** · {fh['hi']:.0f}°C feels-like · {dc.hi_category(fh['hi'])[0]} — "
                     "or drag *Hour of the day* on the left; map, bars, reach and cards all follow that one clock.")
        cooling_empty_state("heat_practice_seed", where="the Heat Scenario Simulator")
        try:
            import folium
            from streamlit_folium import st_folium
            fm = folium.Map(location=(16.04, 120.34), zoom_start=12, tiles=None, control_scale=True)
            folium.TileLayer(tiles=mapfilm.ESRI_SAT[0], attr=mapfilm.ESRI_SAT[1], name="satellite").add_to(fm)
            folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(fm)
            choro = {nm: dict(frac=min(1.0, p["hi"] / 55.0),
                              note=f"feels like {p['hi']:.0f}°C ({dc.hi_category(p['hi'])[0]}) · pop {p['pop']:,}"
                                   + ("" if nm in reached_now else " · ⚠ no cooling point within 2.5 km"))
                     for nm, p in pts.items()}
            kit.brgy_layer(L, fm, choro=choro, highlight=b_sel)
            heat.shade_layer(fm)
            heat.water_layer(fm, L)
            popups = folium.FeatureGroup(name="hot cores (dot size = population)", show=True)
            for nm, p in sorted(pts.items(), key=lambda kv: -kv[1]["hi"]):
                col = cinema._hi_color(p["hi"])
                cat = dc.hi_category(p["hi"])[0]
                indoor = fh["hi_indoor"] + (p["hi"] - fh["hi"])
                gap = nm not in reached_now
                folium.CircleMarker(
                    [p["lat"], p["lon"]], radius=4 + 9 * (p["pop"] / pop_max) ** 0.5,
                    color="#ffffff", weight=1.4, fill=True, fill_color=col, fill_opacity=0.9,
                    tooltip=f"{nm} · {p['hi']:.0f}°C",
                    popup=folium.Popup(f"<div style='font:12px/1.4 sans-serif;min-width:170px'>"
                                       f"<b>{nm}</b><br>"
                                       f"feels like <b style='color:{col}'>{p['hi']:.0f}°C</b> · {cat}<br>"
                                       f"indoors ≈ {indoor:.0f}°C ({'brownout' if indoor > p['hi'] else 'fans ok'})<br>"
                                       f"residents {p['pop']:,}<br>"
                                       f"<span style='color:{'#b91c1c' if gap else '#0f766e'}'>"
                                       f"cooling: {_reach_line(nm)}</span></div>", max_width=260)
                ).add_to(popups)
            popups.add_to(fm)
            fg_cool = folium.FeatureGroup(name="❄ cooling points + 2.5 km reach", show=True)
            for _, c in cool_open.iterrows():
                try:
                    la, lo = float(c["lat"]), float(c["lon"])
                except Exception:
                    continue
                heat.cool_ring([la, lo]).add_to(fg_cool)
                heat.cool_marker(
                    [la, lo],
                    tooltip=f"❄ {c['name']} · open · {c['kind']}"
                            + heat.cool_note(c)
                            + (f" · space {c['capacity']}" if c["capacity"] else "")
                            + " · faint dotted ring = 2.5 km walk radius").add_to(fg_cool)
            fg_cool.add_to(fm)
            fg_health = folium.FeatureGroup(name="🏥 health sites", show=True)
            for fct in L.facilities:
                if fct["category"] == "health":
                    heat.health_marker(
                        [fct["lat"], fct["lon"]],
                        tooltip=f"health site: {fct['name'] or '?'} ({fct['class']})").add_to(fg_health)
            fg_health.add_to(fm)
            folium.LayerControl(collapsed=False).add_to(fm)
            ramp = [(27, "#94a3b8", "<27"), (33, "#fde047", "27–32"), (42, "#fb923c", "33–41"),
                    (52, "#ef4444", "42–51"), (99, "#be123c", "52+")]
            fm.get_root().html.add_child(folium.Element(
                '<div style="position:absolute;bottom:14px;left:14px;z-index:1200;background:rgba(255,255,255,.95);'
                "border:1px solid #e5e7eb;border-radius:10px;padding:7px 11px;"
                "font:600 11px 'Segoe UI',sans-serif;color:#1f2937;box-shadow:0 3px 10px rgba(0,0,0,.15);\">"
                'felt heat — PAGASA bands (°C)<div style="display:flex;gap:7px;margin-top:6px">'
                + "".join(f"<span style='text-align:center'><span style='display:block;width:30px;height:9px;"
                          f"border-radius:3px;background:{c};'></span>"
                          f"<span style='font-size:9px;color:#6b7280'>{t}</span></span>" for _, c, t in ramp)
                + "</div></div>"))
            st_folium(fm, height=560, use_container_width=True, returned_objects=[], key="heat_city_map")
            st.caption("Every barangay shaded by **felt** heat (city curve + urban-heat offset; districts "
                       f"clipped to **{L.boundary_source.split('(')[0].strip()}** boundaries). Hover a dot for the "
                       "bulletin. Layers: ❄ snowflake = open cooling point (faint dotted ring = its 2.5 km walk), "
                       "green pin = health site, 💧 water sources (refill stations, wells, ponds, rivers & canals), "
                       "🌳 shade (parks, grass, mangrove, trees) — all toggleable top right. "
                       "The boundary file swaps in when the LGU releases it.")
        except Exception as e:
            st.info(f"Map unavailable ({type(e).__name__}).")

    # ------------------------------------------------------------ barangay breakdown (under the map)
    with t1:
        st.caption("The map stays pinned above; this panel ranks the same hour by barangay — click a bar to load "
                   "that community in the reach and card tabs.")
        order = sorted(pts.items(), key=lambda kv: -kv[1]["hi"])
        names = [k for k, _ in order]
        figb = go.Figure(go.Bar(
            x=names, y=[v["hi"] for _, v in order],
            marker_color=[cinema._hi_color(v["hi"]) for _, v in order],
            customdata=[[k, v["pop"], ("cooling in reach" if k in reached_now else "no cooling in reach")]
                         for k, v in order],
            hovertemplate="%{x} · %{y:.0f}°C<br>residents %{customdata[1]:,}"
                          "<br>%{customdata[2]}<extra></extra>"))
        figb.add_hrect(y0=42, y1=60, fillcolor="#fecaca", opacity=0.5, line_width=0,
                       annotation_text="DANGER ≥42°C", annotation_position="left", annotation_font_size=10)
        figb.add_hrect(y0=33, y1=42, fillcolor="#fed7aa", opacity=0.45, line_width=0,
                       annotation_text="Extreme caution", annotation_position="left", annotation_font_size=10)
        if b_sel in names:
            figb.add_vline(x=names.index(b_sel), line_color="#1e3a8a", line_width=2, line_dash="dot")
        figb.update_layout(height=300, showlegend=False, margin=dict(l=10, r=10, t=12, b=10),
                           xaxis=dict(title="", tickangle=-45, gridcolor=PLOT_GRID),
                           yaxis=dict(title="feels like °C", range=[24, 56], gridcolor=PLOT_GRID))
        figb = plotly_beige(figb, height=300)
        ev = st.plotly_chart(figb, use_container_width=True, config={"displayModeBar": False},
                             on_select="rerun", selection_mode="points", key="heat_bar_sel")
        try:
            hit = (ev.selection or {}).get("points") or []
        except Exception:
            hit = []
        if hit and isinstance(hit[0].get("point_index"), int):
            nm_hit = names[hit[0]["point_index"]]
            if nm_hit != b_sel and st.session_state.get("_heat_bar_applied") != nm_hit:
                st.session_state["_heat_b_next"] = nm_hit
                st.session_state["_heat_bar_applied"] = nm_hit
                st.rerun()
        st.caption("Bar colour = PAGASA band · dot height = felt heat at **"
                   f"{hour:02d}:00**. Click any bar to open that barangay in the reach and card tabs.")

    # ------------------------------------------------------------ film
    with t2:
        if _gate("play_heatsim", "The film loads ~150 KB of hourly overlay frames — tiles stats above are live."):
            frames = heat.film_frames(L, plan, hstory, heat.cooling_reach(L))
            film_html = mapfilm.storm_map(L, frames, hstory["title"],
                                          "bands clipped per barangay · cooling reach = 2.5 km radius around each "
                                          "barangay core point (anchors)",
                                          height=604, autoplay=True, interval_ms=1000, hud=heat.HUD).get_root().render()
            components.html(film_html, height=604 + STORM_STRIP_PX, scrolling=False)
        st.caption("Reading: the red line on the strip = DANGER-zone "
                   "residents **beyond 2.5 km of any open cooling point** — the survival gap a drill should close. "
                   "Stats: residents in DANGER-band barangays per hour (PAGASA band ≥42°C at that barangay's felt "
                   "heat).")

    # ------------------------------------------------------------ relief + survival
    with t3:
        t3c1, t3c2 = st.columns([1.1, 3])
        b_sel = t3c1.selectbox("Community", b_list, key="heat_b_sel")
        hb = pts.get(b_sel)
        reach_row = reach_all.get(b_sel)
        in_reach = bool(reach_row and reach_row[0] is not None and reach_row[0] <= 2500)
        hi_maps = {f["hour"]: {p["name"]: p for p in cinema.heat_barangay_points(L, f["hi"])} for f in plan}
        dang_hours = sum(1 for m in hi_maps.values() if m.get(b_sel) and m[b_sel]["hi"] >= 42)
        with t3c2:
            st.caption(f"Every figure below is for **{b_sel}** at **{hour:02d}:00** ({fh['hi']:.0f}°C city curve). "
                       "Change the community here, click a bar on the felt-heat tab, or click a row in the card "
                       "table — they all drive this panel.")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Feels like here", f"{hb['hi']:.0f}°C" if hb else "—",
                  dc.hi_category(hb["hi"])[0] if hb else "no anchor", delta_color="off")
        s2.metric("Hours in DANGER today", f"{dang_hours} h", "felt ≥42°C at this core", delta_color="inverse")
        s3.metric("Nearest OPEN cooling",
                  f"{reach_row[1][:26]}" if reach_row and reach_row[0] is not None else "none registered",
                  (f"{reach_row[0] / 1000:.1f} km · " + ("IN reach" if in_reach else "beyond 2.5 km"))
                  if reach_row and reach_row[0] is not None else "register one in the Deck's ❄️ register",
                  delta_color="off")
        s4.metric("Residents beyond cooling reach", f"{hb['pop']:,}" if (hb and not in_reach) else "0",
                  "gap the drill should close" if (hb and not in_reach) else "covered by a 2.5 km radius",
                  delta_color="inverse")

        g1, g2 = st.columns([1.45, 1])
        with g1:
            st.markdown("#### 🗺️ Where the gaps are (whole city)")
            try:
                import folium
                from streamlit_folium import st_folium
                fmg = folium.Map(location=(16.04, 120.34), zoom_start=12, tiles=None, control_scale=True)
                folium.TileLayer(tiles=mapfilm.ESRI_SAT[0], attr=mapfilm.ESRI_SAT[1], name="satellite").add_to(fmg)
                folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(fmg)
                kit.brgy_layer(L, fmg, highlight=b_sel)
                centers = []
                for _, c in cool_open.iterrows():
                    try:
                        centers.append((float(c["lat"]), float(c["lon"]), str(c["name"])))
                    except Exception:
                        continue
                for la, lo, nm_ in centers:
                    heat.cool_ring([la, lo]).add_to(fmg)
                    heat.cool_marker([la, lo], tooltip=f"❄ {nm_} · open cooling · faint dotted ring = 2.5 km").add_to(fmg)
                for nm, p in pts.items():
                    covered = nm in reached_now
                    r = reach_all.get(nm)
                    col = "#0f766e" if covered else "#be123c"
                    folium.CircleMarker(
                        [p["lat"], p["lon"]], radius=4 + 8 * (p["pop"] / pop_max) ** 0.5,
                        color="#ffffff", weight=1.3, fill=True, fill_color=col, fill_opacity=0.92,
                        tooltip=f"{nm} · {'covered' if covered else 'GAP'} · {_reach_line(nm)} · pop {p['pop']:,}"
                    ).add_to(fmg)
                    if not covered and centers:
                        best = min(centers, key=lambda t: rsp.haversine_m(p["lat"], p["lon"], t[0], t[1]))
                        dd = rsp.haversine_m(p["lat"], p["lon"], best[0], best[1])
                        folium.PolyLine([[p["lat"], p["lon"]], [best[0], best[1]]], color="#be123c",
                                        weight=1.6, dash_array="4 7", opacity=0.75,
                                        tooltip=f"{nm} → {best[2]} · {dd / 1000:.1f} km").add_to(fmg)
                folium.LayerControl(collapsed=False).add_to(fmg)
                fmg.get_root().html.add_child(folium.Element(
                    '<div style="position:absolute;bottom:14px;left:14px;z-index:1200;background:rgba(255,255,255,.95);'
                    "border:1px solid #e5e7eb;border-radius:10px;padding:7px 11px;"
                    "font:600 11px 'Segoe UI',sans-serif;color:#1f2937;box-shadow:0 3px 10px rgba(0,0,0,.15);\">"
                    'cooling reach<div style="display:flex;gap:10px;margin-top:6px;align-items:center">'
                    "<span><span style='display:inline-block;width:11px;height:11px;border-radius:50%;"
                    "background:#0f766e;margin-right:4px'></span>covered</span>"
                    "<span><span style='display:inline-block;width:11px;height:11px;border-radius:50%;"
                    "background:#be123c;margin-right:4px'></span>gap</span>"
                    "<span><span style='display:inline-block;width:16px;border-top:2px dashed #0e7490;"
                    "margin-right:4px'></span>2.5 km</span></div></div>"))
                st_folium(fmg, height=500, use_container_width=True, returned_objects=[], key="heat_gap_map")
                st.caption("Teal dots sit inside an open cooling point's 2.5 km ring; crimson dots do not — the dashed "
                           "crimson line is how far the people there would have to go today."
                           if centers else "No cooling points registered yet — register one and this map fills in.")
            except Exception as e:
                st.info(f"Map unavailable ({type(e).__name__}).")
        with g2:
            st.markdown(f"#### 🔎 {b_sel} up close")
            a = _anchor(b_sel)
            if a is None:
                st.info("No map anchor for this barangay yet — set one under 📍 Anchor tools (LGU).")
            else:
                try:
                    import folium
                    from streamlit_folium import st_folium
                    fm2 = folium.Map(location=(a["lat"], a["lon"]), zoom_start=14, tiles=None)
                    folium.TileLayer(tiles=mapfilm.ESRI_SAT[0], attr=mapfilm.ESRI_SAT[1], name="satellite").add_to(fm2)
                    folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(fm2)
                    kit.brgy_layer(L, fm2, highlight=b_sel)
                    folium.Circle([a["lat"], a["lon"]], radius=2500, color="#f59e0b", weight=1.5,
                                  opacity=0.5, fill=False, dash_array="4 8").add_to(fm2)
                    folium.Marker([a["lat"], a["lon"], ], tooltip=f"{b_sel} core",
                                  icon=folium.Icon(color="orange", icon="home", prefix="fa")).add_to(fm2)
                    n_mark = 0
                    for _, c in heat.load_cooling().iterrows():
                        try:
                            la, lo = float(c["lat"]), float(c["lon"])
                        except Exception:
                            continue
                        d = rsp.haversine_m(a["lat"], a["lon"], la, lo)
                        col = ("#0e96b8" if (c["status"] == "open" and d <= 2500)
                               else ("#f59e0b" if c["status"] == "open" else "#9ca3af"))
                        heat.cool_marker(
                            [la, lo], color=col, size=16,
                            tooltip=(f"❄ {c['name']} · {c['status']} · {d/1000:.1f} km"
                                     + heat.cool_note(c)
                                     + (f" · space {c['capacity']}" if c["capacity"] else ""))).add_to(fm2)
                        if c["status"] == "open" and d <= 2500:
                            folium.PolyLine([[a["lat"], a["lon"]], [la, lo]], color="#22d3ee", weight=2.5,
                                            dash_array="5 7", opacity=0.85).add_to(fm2)
                        n_mark += 1
                    near_h = rsp.nearest_services(L, a["lat"], a["lon"], fh["hi"], per_type=1)
                    for _, r in near_h.iterrows():
                        tip = (f"nearest {r['service']}: {r['name']} · {r['distance_m']/1000:.1f} km · "
                               f"site {r['state']}")
                        if str(r["service"]).startswith(("🏥", "🩺")):
                            heat.health_marker([r["lat"], r["lon"]], tip).add_to(fm2)
                        else:
                            folium.CircleMarker([r["lat"], r["lon"]], radius=6, color="white", weight=1.4,
                                                fill=True, fill_color=rsp.SERVICE_COLORS.get(str(r["service"]), "#6b7280"),
                                                fill_opacity=1, tooltip=tip).add_to(fm2)
                    folium.LayerControl().add_to(fm2)
                    st_folium(fm2, height=500, use_container_width=True, returned_objects=[], key="heat_reach_map")
                    st.caption("Amber ring = the 2.5 km walk radius from your core · teal ❄ = open and inside it · "
                               "amber ❄ = open but beyond · grey ❄ = closed · green pin = nearest health site · "
                               f"coloured dot = other responder ({n_mark} cooling rows checked).")
                except Exception as e:
                    st.info(f"Map unavailable ({type(e).__name__}).")

        st.markdown("#### 📏 Distance to an open cooling point, all barangays")
        centers_n = len(cool_open)
        if not centers_n:
            cooling_empty_state("heat_practice_seed_reach", where="Relief reach & survival",
                                style="info")
            st.caption("Or register sites by hand in the Deck's ❄️ Cooling register (or the Response page's "
                       "❄️ Cooling tab) — this ranking, the rings and the survival gap all appear once "
                       "at least one point is open.")
        else:
            rows_r = []
            for nm, p in pts.items():
                r = reach_all.get(nm)
                d = float(r[0]) if (r and r[0] is not None) else float("nan")
                rows_r.append(dict(barangay=nm, km=d / 1000.0 if d == d else float("nan"), pop=p["pop"]))
            dfr = pd.DataFrame(rows_r).sort_values("km", na_position="last").reset_index(drop=True)
            dfr["status"] = np.where(dfr["km"].fillna(99) <= 2.5, "in reach", "GAP")
            figr = go.Figure(go.Bar(
                x=dfr["km"], y=dfr["barangay"], orientation="h",
                marker_color=["#0f766e" if s == "in reach" else "#be123c" for s in dfr["status"]],
                customdata=dfr[["pop"]].values,
                hovertemplate="%{y} · %{x:.1f} km<br>residents %{customdata[0]:,}<extra></extra>"))
            figr.add_vline(x=2.5, line_dash="dash", line_color="#b91c1c", line_width=2,
                           annotation_text="2.5 km", annotation_position="bottom")
            if b_sel in set(dfr["barangay"]):
                figr.add_hline(y=b_sel, line_color="#1e3a8a", line_width=2, line_dash="dot")
            figr.update_layout(height=max(300, 22 * len(dfr)), showlegend=False,
                               margin=dict(l=10, r=10, t=14, b=10),
                               xaxis=dict(title="km to the nearest OPEN cooling point", gridcolor=PLOT_GRID,
                                          range=[0, max(3.0, float(np.nanmax(dfr["km"])) * 1.15)]),
                               yaxis=dict(title="", gridcolor=PLOT_GRID, autorange="reversed"))
            figr = plotly_beige(figr, height=max(300, 22 * len(dfr)))
            ev2 = st.plotly_chart(figr, use_container_width=True, config={"displayModeBar": False},
                                  on_select="rerun", selection_mode="points", key="heat_reach_sel")
            try:
                hit2 = (ev2.selection or {}).get("points") or []
            except Exception:
                hit2 = []
            if hit2 and isinstance(hit2[0].get("point_index"), int):
                nm2 = dfr.iloc[hit2[0]["point_index"]]["barangay"]
                if nm2 != b_sel and st.session_state.get("_heat_reach_applied") != nm2:
                    st.session_state["_heat_b_next"] = nm2
                    st.session_state["_heat_reach_applied"] = nm2
                    st.rerun()
            gap_pop = sum(int(r["pop"]) for _, r in dfr.iterrows() if r["status"] == "GAP")
            st.caption(f"**{int((dfr['status'] == 'GAP').sum())} barangay gaps · {gap_pop:,} residents live beyond a "
                       "2.5 km walk to an open cooling point** (straight-line radius, not a routing network). "
                       "Click a bar to open that barangay.")

        st.markdown("#### Stay-alive today")
        for nm, tip_ in heat.tips(PREFS.get("lang", "Tagalog" if PREFS.get("lang") == "Tagalog" else "English")):
            st.markdown(f"- **{nm}:** {tip_}")
        d911 = rsp.load_directory()
        natl = d911[(d911["confirmed_by_call"].astype(str) == "True")
                    & ((d911["mobile"].str.len() > 0) | (d911["landline_075"].str.len() > 0))]
        chips = " · ".join(f"{r['organisation']}: **{r['mobile'] or r['landline_075']}**"
                           for _, r in natl.iterrows())
        st.markdown(f"**Emergencies (national, verified lines):** {chips}", unsafe_allow_html=True)

    # ------------------------------------------------------------ cards & copy
    with t4:
        b_row4 = L.brgy[L.brgy["barangay"] == b_sel].iloc[0]
        lang4 = PREFS.get("lang", "English")
        hb4 = pts.get(b_sel)
        hi4 = hb4["hi"] if hb4 else fh["hi"]
        cat4 = dc.hi_category(hi4)[0]
        reach4 = reach_all.get(b_sel)
        card4 = kit.action_card_heat(b_row4, hi4, cat4, lang=lang4)
        a4 = _anchor(b_sel)
        p1, p2 = st.columns([1.3, 1])
        with p1:
            st.markdown(f"#### 📍 Where this card lands — {b_sel}")
            if a4 is None:
                st.info("No map anchor for this barangay — the card still prints, the map needs a core point.")
            else:
                try:
                    import folium
                    from streamlit_folium import st_folium
                    fm4 = folium.Map(location=(a4["lat"], a4["lon"]), zoom_start=14, tiles=None)
                    folium.TileLayer(tiles=mapfilm.ESRI_SAT[0], attr=mapfilm.ESRI_SAT[1], name="satellite").add_to(fm4)
                    folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(fm4)
                    kit.brgy_layer(L, fm4, highlight=b_sel)
                    folium.Circle([a4["lat"], a4["lon"]], radius=2500, color="#f59e0b", weight=1.5,
                                  opacity=0.5, fill=False, dash_array="4 8").add_to(fm4)
                    folium.Marker([a4["lat"], a4["lon"]], tooltip=f"{b_sel} core",
                                  icon=folium.Icon(color="orange", icon="home", prefix="fa")).add_to(fm4)
                    if reach4 and reach4[0] is not None:
                        for _, c in heat.load_cooling().iterrows():
                            if str(c["name"]) != str(reach4[1]):
                                continue
                            try:
                                la, lo = float(c["lat"]), float(c["lon"])
                            except Exception:
                                break
                            folium.PolyLine([[a4["lat"], a4["lon"]], [la, lo]], color="#0e7490", weight=2,
                                            dash_array="5 8", opacity=0.7,
                                            tooltip=f"{reach4[0]/1000:.1f} km to {reach4[1]}").add_to(fm4)
                            heat.cool_marker([la, lo], size=17,
                                             tooltip=f"❄ {reach4[1]} · {reach4[2]}").add_to(fm4)
                    for fct in L.facilities:
                        if fct["category"] == "health":
                            heat.health_marker(
                                [fct["lat"], fct["lon"]],
                                tooltip=f"health site: {fct['name'] or '?'} ({fct['class']})").add_to(fm4)
                    folium.LayerControl().add_to(fm4)
                    st_folium(fm4, height=430, use_container_width=True, returned_objects=[], key="heat_card_map")
                    st.caption("Amber ring = 2.5 km from your core · dashed navy line = walk to the cooling point "
                               "named on the card · green pin = health sites.")
                except Exception as e:
                    st.info(f"Map unavailable ({type(e).__name__}).")
        with p2:
            st.markdown(f"#### 📄 {b_sel} — {cat4}")
            st.code(card4, language=None)
            png4 = heat.briefing_png(L, b_row4, a4, hi4, cat4, hstory["title"], reach4, lang4)
            st.download_button("⬇ One-page heat survival card (PNG)", data=png4,
                               file_name=f"climateshield_heat_{b_sel}.png", mime="image/png",
                               use_container_width=True)
            st.caption("Felt heat uses {} at the {}:00 hour; services use straight-line distance, and the DERIVED "
                       "boundary labels reflow to official names as soon as the LGU file loads.".format(
                           hstory["title"], hour))

        st.markdown("#### ✉ Copy-paste kit")
        tips4 = heat.tips(lang4)
        proto4 = heat.protocol_for(hi4)
        head4 = proto4[-1]["headline"] if proto4 else "Below 27°C — no protocol band in force."
        cool4 = _reach_line(b_sel)
        sms4 = (f"HEAT {cat4.upper()} {b_sel}: feels like {hi4:.0f}C at {hour:02d}:00. {tips4[0][1][:70]}. "
                f"Cooling: {cool4}. Emergencies 911.")
        fb4 = (f"☀️ HEAT BULLETIN — {b_sel.upper()} ({cat4})\n"
               f"Feels like {hi4:.0f}°C at {hour:02d}:00 · {head4}\n"
               + "".join(f"{i}. {n}: {t}\n" for i, (n, t) in enumerate(tips4[:4], 1))
               + f"Cooling point: {cool4}\n"
               "Emergency: 911 · PAGASA issues the official heat index advisory.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**SMS / Viber text** — {len(sms4)} chars "
                        f"({'1 segment' if len(sms4) <= 160 else str((len(sms4) + 152) // 153) + ' segments'})")
            st.code(sms4, language=None)
        with c2:
            st.markdown(f"**Facebook / Viber group post** — {len(fb4)} chars")
            st.code(fb4, language=None)

        st.markdown("#### 🃏 All barangay cards")
        rows4 = []
        for nm, p in sorted(pts.items(), key=lambda kv: -kv[1]["hi"]):
            r4 = reach_all.get(nm)
            rows4.append({"barangay": nm, "feels like": f"{p['hi']:.0f}°C",
                          "band": dc.hi_category(p["hi"])[0],
                          "cooling": (f"{r4[0]/1000:.1f} km" if r4 and r4[0] is not None else "—"),
                          "residents": p["pop"]})
        tdf = pd.DataFrame(rows4)
        sel4 = st.dataframe(tdf, hide_index=True, use_container_width=True, height=280,
                            on_select="rerun", selection_mode="single-row", key="heat_card_tbl")
        pick4 = list(sel4.selection.rows)
        if pick4:
            nm4 = tdf.iloc[pick4[0]]["barangay"]
            if nm4 != b_sel and st.session_state.get("_heat_tbl_applied") != nm4:
                st.session_state["_heat_b_next"] = nm4
                st.session_state["_heat_tbl_applied"] = nm4
                st.rerun()
        st.caption("Click a row to load that barangay's card, map and copy blocks above.")

    # ------------------------------------------------------------ day dashboard (page bottom)
    st.markdown("#### 📊 Day dashboard")
    k1, k2, k3, k4 = st.columns(4)
    hottest = max(pts.items(), key=lambda kv: kv[1]["hi"]) if pts else ("—", {"hi": 0.0, "pop": 0})
    k1.metric("Hottest barangay now", f"{hottest[0][:22]}", f"{hottest[1]['hi']:.0f}°C feels-like",
              delta_color="off")
    k2.metric("Residents in DANGER-band areas", f"{sum(p['pop'] for p in danger_now.values()):,}",
              f"{len(danger_now)} of {len(pts)} barangays at ≥42°C", delta_color="inverse")
    k3.metric("Population within 2.5 km of cooling", f"{100 * cov_pop / tot_pop:.0f}%",
              f"{len(reached_now)} of {len(pts)} barangays covered", delta_color="inverse")
    k4.metric("Cooling points open", f"{cst_now['open']}",
              f"{heat.practice_count()} practice · {cst_now['full']} full · {cst_now['closed']} closed",
              delta_color="off")
    try:
        fday, _ = cinema.heat_chart(L, hstory, theme_text=BEIGE_TEXT, grid=PLOT_GRID, height=340)
        fday.add_vline(x=hour, line_color="#1e3a8a", line_width=2, line_dash="dot")
        st.plotly_chart(fday, use_container_width=True, config={"displayModeBar": False}, key="heat_day_curve")
    except Exception as e:
        st.info(f"Day curve unavailable ({type(e).__name__}).")
    st.caption(f"**{hstory['title']}** — purple dotted line = indoors, red = heat index in shade, vertical "
               "line = the hour selected up top. Bands are PAGASA categories; the map, bars, reach and cards "
               "all follow this one clock.")

    # ------------------------------------------------------------ tabletop inject pack
    with st.expander("🎲 Heat tabletop injects (facilitator)"):
        st.caption("Read one inject at a time during a team drill — same format as the flood exercise. What breaks "
                   "first is the lesson.")
        for inj in [
            ("05:00 · Brownout notice", "Cooperative says load-shedding 10:00–16:00. No fans, no cold chain, no pumps "
                                        "at cooling points. Which do you fix first? (DOLE rest breaks become critical)"),
            ("09:00 · Water outage", "Main pressure drops in the network; refilling stations close early. Where do "
                                     "trucked water points go? (Deck ranking: people × DANGER-hours)"),
            ("11:30 · School call", "Felt heat crosses 42°C in dense cores. Do you recommend ADM? Whose call — "
                                    "school head or barangay or CDRRMO? (DepEd-2024 discretion)"),
            ("13:00 · Casualty", "Outdoor worker collapses: hot dry skin, confused. Your first three actions — "
                                 "cool, call 911, family notify. Who on your roster does each?"),
            ("14:30 · Single elderly", "Buddy checker can't reach three elderly living alone. Who has keys + who "
                                       "drives in this heat?"),
            ("16:00 · Cooling point full", "Your one open center hits capacity. Nearest other is 4 km — do you "
                                           "re-open a school hall or open shaded churches?"),
            ("18:30 · Lines down", "Cell sites on generator, texts delayed four hours. Which fallback do you trust — "
                                   "radio, siren, or chains of neighbours?"),
            ("Tomorrow's core", "Today never dropped below 26.5°C. What changes tomorrow's schedule before sunrise?")]:
            st.markdown(f"**{inj[0]}** — {inj[1]}")


    # ================================================================= COUNTERMEASURE LAB

@st.fragment
def _fragment_lab():
    st.button("Back to Command Deck", on_click=_nav_to, args=(NAV[0],))
    st.title(f"🛡️ {tt('Countermeasure Lab')}")
    st.caption("Transparent proxy modeling: pick measures, watch exposure drop. Engineering claims need DPWH studies — this ranks *where* benefits land.")

    scen = st.selectbox("Baseline event", list(dc.SCENARIOS.keys()), index=2)
    tide = st.slider("Tide add-on", 0.0, 1.5, 0.20, 0.05)
    W_base = L.water_level_for_share(dc.SCENARIOS[scen]) + tide
    depth0, _ = L.depth_grid(W_base)
    exp0 = L.exposure(depth0, W_base)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("#### 🚤 1 · Channel dredging")
        cov = st.selectbox("Coverage", ["None", "Pantal–Calmay rivers only", "All rivers & canals"], index=1)
        dredge = st.slider("Modeled drawdown in river buffer", 0.0, 0.4, 0.20, 0.05)
        if cov == "None":
            dredge = 0.0
        elif cov == "All rivers & canals":
            dredge = dredge * 1.25
    with m2:
        st.markdown("#### 🌳 2 · Urban drainage + green storage")
        drainage = st.slider("Modeled event drawdown (uniform)", 0.0, 0.4, 0.10, 0.05)
        st.caption("Drainage capacity / rain gardens / retention ponds program intensity.")
    with m3:
        st.markdown("#### 🏠 3 · Managed relocation")
        fam = st.slider("Families moved off ≤1 m land", 0, 2000, 250, 50)
        st.caption(f"≈ {fam * L.meta['avg_hh_size']:.0f} residents at avg household size {L.meta['avg_hh_size']}")

    depth1, W1 = L.depth_grid(W_base, dredge_m=dredge, drainage_m=drainage)
    exp1 = L.exposure(depth1, W_base)
    low_mask = (L.dem <= W1) & (L.land_mask)
    reloc_pop = min(fam * L.meta["avg_hh_size"], float(L.pop_psa[low_mask].sum()))
    pop_final = max(0.0, exp1["pop_affected"] - reloc_pop)

    wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["Baseline exposure", "Dredging + drainage", " ", "Relocation", "Net exposure"],
        y=[exp0["pop_affected"], exp1["pop_affected"] - exp0["pop_affected"], 0, -reloc_pop, pop_final],
        text=[f"{exp0['pop_affected']:,.0f}", f"{exp1['pop_affected'] - exp0['pop_affected']:+,.0f}",
              "combined", f"{-reloc_pop:+,.0f}", f"{pop_final:,.0f}"],
        connector={"line": {"color": "#b9a97e"}},
        increasing_marker_color="#5d8a3c", decreasing_marker_color="#c0392b",
        totals_marker_color="#b5813e",
    ))
    st.plotly_chart(plotly_beige(wf, height=400, y_title="residents",
                                 title="Residents out of flood zones (PSA-calibrated)"), use_container_width=True)
    st.warning("Dredging + drainage are recomputed jointly; the waterfall attributes their combined rain-driven "
               "effect to the first bar, then relocation's arithmetic.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Residents protected", f"{exp0['pop_affected'] - exp1['pop_affected']:,.0f}", "by dredging + drainage")
    c2.metric("Buildings spared", f"{max(0, exp0['bldg_flooded'] - exp1['bldg_flooded']):,}",
              f"of {exp0['bldg_flooded']:,} flooded at baseline")
    c3.metric("Schools spared", f"{max(0, exp0['fac_counts'].get('school', 0) - exp1['fac_counts'].get('school', 0))}",
              "school sites out of flood depth")

    mc, mc2 = st.columns([1.2, 1])
    with mc:
        fig = draw_map(depth=depth1, fac=False,
                       title=f"After countermeasures — flooded land {(depth1 > 0.15).sum() * 0.0009:.1f} km² "
                             f"(baseline {exp0['area_flooded_km2']:.1f} km²)")
        st.pyplot(fig)
        plt.close(fig)
    with mc2:
        st.subheader("Benefit ranking (this storm)")
        rank = pd.DataFrame({
            "measure": ["Channel dredging + drainage", "Managed relocation"],
            "residents protected": [f"{int(round(exp0['pop_affected'] - exp1['pop_affected'])):,}",
                                    f"{int(round(reloc_pop)):,}"],
            "buildings spared": [f"{int(round(max(0, exp0['bldg_flooded'] - exp1['bldg_flooded']))):,}", "0"],
            "schools spared": [f"{int(max(0, exp0['fac_counts'].get('school', 0) - exp1['fac_counts'].get('school', 0))):,}", "0"],
        })
        st.dataframe(rank, hide_index=True, use_container_width=True)
        st.caption("Relocation protects people but abandons structures — dredging/drainage protect both. "
                   "Context: DPWH's own Dagupan flood-mitigation project was contracted Jun 2024 and re-targeted "
                   "to Jun 2026 (PIA) — while the Aug 2026 habagat flooded 23/31 barangays.")
        with st.expander("Model honesty notes"):
            st.markdown(
                """
                        - Dredging proxy = water-level drawdown decaying over 600 m from channels (all channels → +25% reach).
                        - Drainage proxy = uniform event-water drawdown.
                        - These model **direction and scale of benefit**, not engineering guarantees: channel hydraulics,
                          pump stations and siltation rates need DPWH studies.
                        - Relocation arithmetic = families × average household size, capped by residents actually living
                          below the modeled water line.
                        """
            )

    # ------------------------------------------------------------- heat countermeasures
    st.markdown("## ☀️ Heat countermeasures")
    st.caption("Same lab, second hazard: cool the day. Proxy arithmetic only — a cooling point covers a "
               "straight-line radius around its door, shade lowers *felt* heat one-for-one, and class/work rules "
               "take people out of the DANGER window rather than out of the band.")
    cooling_empty_state("lab_heat_practice_seed", where="the Countermeasure Lab", style="info")
    hstory_lab = cinema.HEAT_STORIES["heatwave_brownout"]
    plan_lab = cinema.heat_plan(L, hstory_lab)
    peak_lab = max(plan_lab, key=lambda f: f["hi"])
    hc1, hc2, hc3 = st.columns(3)
    with hc1:
        st.markdown("#### ❄ 1 · Cooling network")
        n_new = st.slider("New cooling points to open", 0, 12, 3, 1, key="lab_cool_n",
                          help="Dropped greedily on the largest uncovered barangay cores (population first).")
        rad_km = st.slider("Reach radius (straight-line)", 2.0, 4.0, 2.5, 0.5, key="lab_cool_r")
    with hc2:
        st.markdown("#### 🌳 2 · Shade, canopy & reflective roofs")
        shade = st.slider("Felt-heat reduction (°C)", 0.0, 3.0, 0.8, 0.1, key="lab_shade",
                          help="Trees, awnings, cool roofs and painted alleys — applied city-wide at the peak hour.")
    with hc3:
        st.markdown("#### 🏫 3 · Class & work rules")
        adm = st.toggle("Suspend outdoor classes at DANGER (DepEd-2024 discretion)", value=True, key="lab_adm")
        rest = st.toggle("DOLE rest cycle (15 min / 2 h outdoors)", value=True, key="lab_rest")

    rad_m = rad_km * 1000.0
    pts_lab = {p["name"]: p for p in cinema.heat_barangay_points(L, peak_lab["hi"])}
    base_centers, base_names = [], []
    for _, c in heat.load_cooling().iterrows():
        if str(c.get("status")) != "open":
            continue
        try:
            base_centers.append((float(c["lat"]), float(c["lon"])))
            base_names.append(str(c["name"]))
        except Exception:
            continue

    def _within(centers):
        s = set()
        for nm, p in pts_lab.items():
            d = min((rsp.haversine_m(p["lat"], p["lon"], clat, clon) for clat, clon in centers), default=1e18)
            if d <= rad_m:
                s.add(nm)
        return s

    cov0 = _within(base_centers)
    unc = sorted((nm for nm in pts_lab if nm not in cov0),
                 key=lambda nm: -pts_lab[nm]["pop"])[:int(n_new)]
    new_centers = [(pts_lab[nm]["lat"], pts_lab[nm]["lon"]) for nm in unc]
    cov1 = _within(base_centers + new_centers)
    pop_cov0 = sum(pts_lab[nm]["pop"] for nm in cov0)
    pop_cov1 = sum(pts_lab[nm]["pop"] for nm in cov1)
    danger0 = sum(p["pop"] for p in pts_lab.values() if p["hi"] >= 42)
    danger1 = sum(p["pop"] for p in pts_lab.values() if p["hi"] - shade >= 42)
    dang_hours = sum(1 for f in plan_lab if f["hi"] >= 42)
    out_share = (0.18 if adm else 0.0) + (0.12 if rest else 0.0)
    ph_out = danger0 * out_share * dang_hours

    q1, q2, q3 = st.columns(3)
    q1.metric("Residents within reach", f"{pop_cov1:,}",
              f"+{pop_cov1 - pop_cov0:,} vs {pop_cov0:,} today · {rad_km:g} km radius", delta_color="inverse")
    q2.metric("Residents in the DANGER band", f"{danger1:,}",
              f"−{danger0 - danger1:,} with {shade:g}°C of shade", delta_color="inverse")
    q3.metric("Person-hours out of the DANGER window", f"{ph_out:,.0f}",
              f"{dang_hours} DANGER hours · {100 * out_share:.0f}% of residents moved", delta_color="inverse")

    ch1, ch2 = st.columns(2)
    with ch1:
        f1 = go.Figure(go.Bar(x=["today", f"+{int(n_new)} points"], y=[pop_cov0, pop_cov1],
                              marker_color=["#be123c" if pop_cov0 < pop_cov1 else "#94a3b8", "#0f766e"],
                              text=[f"{pop_cov0:,}", f"{pop_cov1:,}"], textposition="outside"))
        f1.update_layout(height=270, showlegend=False, margin=dict(l=10, r=10, t=30, b=10),
                         title=f"Residents within {rad_km:g} km of open cooling",
                         yaxis=dict(title="residents", gridcolor=PLOT_GRID), xaxis=dict(gridcolor=PLOT_GRID))
        st.plotly_chart(plotly_beige(f1, height=270), use_container_width=True, config={"displayModeBar": False})
    with ch2:
        f2 = go.Figure(go.Bar(x=["today", f"−{shade:g}°C shade"], y=[danger0, danger1],
                              marker_color=["#ef4444", "#f59e0b"],
                              text=[f"{danger0:,}", f"{danger1:,}"], textposition="outside"))
        f2.update_layout(height=270, showlegend=False, margin=dict(l=10, r=10, t=30, b=10),
                         title=f"Residents in a barangay feeling ≥42°C at {peak_lab['hour']:02d}:00",
                         yaxis=dict(title="residents", gridcolor=PLOT_GRID), xaxis=dict(gridcolor=PLOT_GRID))
        st.plotly_chart(plotly_beige(f2, height=270), use_container_width=True, config={"displayModeBar": False})

    try:
        import folium
        from streamlit_folium import st_folium
        fml = folium.Map(location=(16.04, 120.34), zoom_start=12, tiles=None, control_scale=True)
        folium.TileLayer(tiles=mapfilm.ESRI_SAT[0], attr=mapfilm.ESRI_SAT[1], name="satellite").add_to(fml)
        folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(fml)
        kit.brgy_layer(L, fml)
        heat.shade_layer(fml)
        for clat, clon in base_centers:
            heat.cool_ring([clat, clon], radius_m=rad_m).add_to(fml)
            heat.cool_marker([clat, clon], tooltip="existing open cooling").add_to(fml)
        for nm, (clat, clon) in zip(unc, new_centers):
            folium.Circle([clat, clon], radius=rad_m, color="#15803d", weight=1.5, opacity=0.55,
                          fill=False, dash_array="4 8").add_to(fml)
            heat.cool_marker([clat, clon], color="#15803d",
                             tooltip=f"proposed cooling point · {nm}").add_to(fml)
        pop_max_lab = max([q["pop"] for q in pts_lab.values()], default=1) or 1
        for nm, p in pts_lab.items():
            if nm in cov1:
                continue
            folium.CircleMarker([p["lat"], p["lon"]], radius=4 + 8 * (p["pop"] / pop_max_lab) ** 0.5,
                                color="#ffffff", weight=1.2, fill=True, fill_color="#be123c", fill_opacity=0.92,
                                tooltip=f"{nm} still beyond reach · pop {p['pop']:,}").add_to(fml)
        folium.LayerControl(collapsed=False).add_to(fml)
        st_folium(fml, height=460, use_container_width=True, returned_objects=[], key="lab_heat_map")
        st.caption(f"Teal ❄ + faint ring = the {int(len(base_centers))} registered open cooling points · "
                   f"green ❄ = the {len(new_centers)} proposed by this slider set · crimson dots = barangays that "
                   "would still sit outside the radius · green shading = existing shade (parks, grass, mangrove). "
                   "Straight-line radius, not a routing network.")
    except Exception as e:
        st.info(f"Map unavailable ({type(e).__name__}).")

    st.subheader("Heat benefit ranking (this heat day)")
    hrank = pd.DataFrame({
        "measure": ["Cooling network", "Shade / canopy", "Class & work rules"],
        "residents brought within reach": [f"+{pop_cov1 - pop_cov0:,}", "0", "0"],
        "residents out of the DANGER band": ["0", f"{danger0 - danger1:,}", "0"],
        "person-hours out of DANGER": ["0", "0", f"{ph_out:,.0f}"],
    })
    st.dataframe(hrank, hide_index=True, use_container_width=True)
    st.caption("Heat rows are ranked the same way as the flood rows above: people first. Cooling points move people "
               "into reach, shade moves them out of the band, and class/work rules move hours — none of them change "
               "the weather.")
    with st.expander("Heat model honesty notes"):
        st.markdown(
            f"""
                    - Felt heat = city curve ({hstory_lab['title']}, peak {peak_lab['hi']:.0f}°C at
                      {peak_lab['hour']:02d}:00) + urban-heat offset per barangay (dense/urban cores run hotter).
                    - Coverage = straight-line radius from each open cooling point, measured barangay-core to door —
                      real walking routes, stairs, crossings and gate hours are not modelled.
                    - New points are placed greedily on the largest uncovered core; that is a planning heuristic,
                      not a site survey (a school needs a head, a generator and water before it is a cooling point).
                    - Shade is applied as a flat subtraction at the peak hour; canopy grows slowly and cools unevenly.
                    - Class/work percentages (18% students+staff, 12% outdoor workers) are stated assumptions used to
                      count *person-hours*, never a claim about who is actually outdoors.
                    - PAGASA issues the official heat-index advisory; DepEd and DOLE own the class and labor rules.
                    """
        )


    # ================================================================= TELEMETRY

@st.fragment(run_every=90)
def _fragment_tel():
    st.button("Back to Command Deck", on_click=_nav_to, args=(NAV[0],))
    st.title(f"📡 {tt('Live Telemetry')}")
    st.caption("Real conditions, official thresholds. This page refreshes itself every ~90 seconds; "
               "the feed renews at most every 2 minutes. Crowd reports keep the map human between gauges.")

    live, ok = get_live()
    cur = (live or {}).get("current", {})
    if not cur:
        st.error("Live feed unreachable and no cache available — historical context only. "
                 "Check the internet connection or press Refresh; the badge below shows the last successful fetch.")
    else:
        rcol, _ = st.columns([1, 2])
        with rcol:
            if st.button("🔄 Refresh live data now"):
                st.cache_data.clear()
                st.rerun()
        st.markdown(f'<div class="cs-banner">{freshness_badge(cur, ok)}</div>', unsafe_allow_html=True)
        HI = dc.hi_c(cur["temperature_2m"], cur["relative_humidity_2m"])
        cat, col, _ = dc.hi_category(HI)
        catcolor = "#2e6da4" if cat in ("No Caution", "Caution") else "#b34700"
        g1, g2 = st.columns([1, 2.1])
        with g1:
            gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=HI, number={"suffix": "°C"},
                title={"text": f"Heat index NOW<br><span style='font-size:14px;color:{catcolor};'>{cat}</span>"},
                gauge={"axis": {"range": [20, 60]},
                       "bar": {"color": "#b5813e"},
                       "bgcolor": BEIGE_PANEL,
                       "steps": [
                           {"range": [20, 27], "color": "#e8dfc8"},
                           {"range": [27, 33], "color": "#ffe699"},
                           {"range": [33, 42], "color": "#f6b26b"},
                           {"range": [42, 52], "color": "#e06666"},
                           {"range": [52, 60], "color": "#9e2a2a"}]},
            ))
            gauge.update_layout(template=PLOT_TEMPLATE, height=300, margin=dict(l=10, r=10, t=60, b=10),
                                paper_bgcolor=BEIGE_BG)
            st.plotly_chart(gauge, use_container_width=True)
            st.caption(f"Observed at 16.04°N 120.33°E via {cur.get('source', '—')} "
                       f"({cur['temperature_2m']:.1f}°C, RH {cur['relative_humidity_2m']:.0f}%, "
                       f"obs {cur.get('observed_at', '—')}). "
                       "Station-observed PAGASA heat index may read higher.")
        with g2:
            hourly = live.get("hourly") or {}
            if hourly:
                hf = pd.DataFrame({"time": pd.to_datetime(hourly["time"]), "rain": hourly["precipitation"]})
                now = pd.Timestamp.now().floor("h")
                hf["kind"] = np.where(hf["time"] <= now, "observed / analysed", "forecast")
                figp = go.Figure()
                for kind, colr in [("observed / analysed", "#2563eb"), ("forecast", "#93c5fd")]:
                    sub = hf[hf["kind"] == kind]
                    figp.add_bar(x=sub["time"], y=sub["rain"], name=kind, marker_color=colr)
                figp.add_vline(x=now, line_color="#ef4444", line_dash="dash",
                               annotation_text="now", annotation_position="top")
                figp.add_hline(y=7.5, line_color="#f59e0b", line_dash="dot", annotation_text="7.5 mm/h heavy")
                figp.add_hline(y=15, line_color="#dc2626", line_dash="dot", annotation_text="15 mm/h intense")
                figp.update_layout(barmode="overlay", legend=dict(orientation="h", y=1.1))
                st.plotly_chart(plotly_beige(figp, height=285, y_title="mm per hour"), use_container_width=True,
                                config={"displayModeBar": False})
                last24 = float(hf[(hf["time"] > now - pd.Timedelta(hours=24)) & (hf["time"] <= now)]["rain"].sum())
                next24 = float(hf[(hf["time"] > now) & (hf["time"] <= now + pd.Timedelta(hours=24))]["rain"].sum())
                peak = float(hf[hf["kind"] == "forecast"]["rain"].max() or 0)
                m1, m2, m3 = st.columns(3)
                m1.metric("Rain · last 24 h", f"{last24:.1f} mm", "model-analysed")
                m2.metric("Rain · next 24 h", f"{next24:.1f} mm", "forecast", delta_color="inverse")
                m3.metric("Peak rate ahead", f"{peak:.1f} mm/h", "PAGASA heavy ≥ 7.5 · intense ≥ 15",
                          delta_color="inverse")
                if next24 >= 50:
                    banner(f"<b>Rain trigger watch:</b> {next24:.0f} mm expected in the next 24 h — crosses the "
                           "50 mm heavy-advisory line. Playbook: pre-position banca rosters, clear drains tonight.", "warn")
                elif peak >= 7.5:
                    banner(f"<b>Rain trigger watch:</b> peak hourly rate {peak:.1f} mm/h reaches heavy-advisory "
                           "intensity — watch PAGASA advisories tonight.", "warn")
                else:
                    banner("<b>Rain trigger watch:</b> no heavy-advisory-level rain forecast in the next 24 h — "
                           "good window for drainage maintenance and drills.", "info")
                st.caption("Hourly totals from Open-Meteo (ECMWF/GFS blend), observed + 7-day forecast. Not a radar: "
                            "for live radar use PAGASA's official site. Official rainfall warnings: PAGASA Heavy "
                            "Rainfall Warning System.")

        st.markdown("#### Heat index through the day")
        hourly = (live or {}).get("hourly") or {}
        if "temperature_2m" in hourly and len(hourly.get("temperature_2m") or []):
            hh = pd.DataFrame({"time": pd.to_datetime(hourly["time"]),
                               "t": hourly["temperature_2m"], "rh": hourly["relative_humidity_2m"]})
            hh["HI"] = [dc.hi_c(t, r) for t, r in zip(hh["t"], hh["rh"])]
            now_h = pd.Timestamp.now().floor("h")
            hh = hh[(hh["time"] >= now_h.floor("D")) & (hh["time"] <= now_h.floor("D") + pd.Timedelta(hours=36))]
            figh = go.Figure()
            for y0, y1, colr, lab in [(20, 27, "#f1f5f9", "No caution"), (27, 33, "#fef9c3", "Caution"),
                                       (33, 42, "#fed7aa", "Extreme caution"), (42, 52, "#fecaca", "DANGER"),
                                       (52, 60, "#fda4af", "Extreme danger")]:
                figh.add_hrect(y0=y0, y1=y1, fillcolor=colr, opacity=0.55, line_width=0,
                               annotation_text=lab, annotation_position="left", annotation_font_size=9)
            figh.add_trace(go.Scatter(x=hh["time"], y=hh["HI"], mode="lines", name="heat index",
                                      line=dict(color="#dc2626", width=3),
                                      customdata=hh["rh"], hovertemplate="%{x|%H:%M} · HI %{y:.0f}°C · RH %{customdata:.0f}%<extra></extra>"))
            figh.add_trace(go.Scatter(x=[now_h], y=[HI], mode="markers", name="now",
                                      marker=dict(size=13, color="#dc2626", line=dict(width=2, color="white")),
                                      hovertemplate="now · %{y:.0f}°C<extra></extra>"))
            figh.update_layout(height=280, margin=dict(l=8, r=8, t=8, b=8), showlegend=False,
                               yaxis=dict(title="heat index °C", range=[22, 58], gridcolor=PLOT_GRID),
                               xaxis=dict(gridcolor=PLOT_GRID))
            st.plotly_chart(plotly_beige(figh, height=280), use_container_width=True, config={"displayModeBar": False})
            mid = hh.iloc[(hh["time"] - now_h).abs().argsort()[:1]].iloc[0]
            peak_hi = float(hh["HI"].max())
            st.caption(f"Today's modelled curve for the city centre: currently {mid['HI']:.0f}°C, peaking near "
                       f"**{peak_hi:.0f}°C**. Bands are PAGASA heat-index categories.")
        else:
            st.caption("Hourly temperature/humidity not available from the current feed (MET Norway fallback "
                       "provides rain only).")

        with st.expander("❓ What is this number, on what grounds — and what is it for?"):
            st.markdown(
                f"""
                **What you are looking at:** an automated *estimate* of conditions at one grid point (16.04°N, 120.33°E —
                the city centre), refreshed continuously from the Open-Meteo service, which blends European/global
                weather models at roughly 11 km resolution. It is **not** a thermometer in Dagupan.

                **Why it can differ from radio/TV/PAGASA:** PAGASA's Dagupan station measures real air at its
                enclosure; models smooth over the whole grid cell. Heat index computed from model temperature and
                humidity typically lands within a few °C of the station value but can diverge on humid, still nights
                or during passing showers. The current source: **{(live or {}).get('source', '—')}**
                (fetched {(cur or {}).get('fetched_at', '—')}).

                **So what is it for?** Triage, not pronouncement. A live-on-24/7 estimate lets the city:
                1. **Time the day** — the curve above shows *when* heat index crosses PAGASA's caution/danger bands,
                   so class suspensions, outdoor-work windows and respite-point openings can be planned hours ahead;
                2. **Trigger sims & drills** — heat scenarios and the Walkthrough action card switch on live readings;
                3. **Hold the question** — 'is it dangerously hot right now?' deserves an answer at 3 a.m. too, which
                   no manual feed gives.

                **What it is not:** an official warning. Heat-index warnings come from PAGASA Dagupan; river flooding
                comes from the CDRRMO/PDRRMO gauge network — and as the PhilSensors panel below shows, the nearest
                public river stations are not reporting. When a live station or gauge feed is integrated, this page
                switches to showing both, side by side, with each labeled.
                """)

        # -------------------------------------------------- heat situation & cooling reach (live)
        st.markdown("#### ☀️ Heat situation & cooling reach — live")
        cooling_empty_state("tel_heat_practice_seed", where="the live heat board", style="info")
        cat_t, col_t = dc.hi_category(HI)[0], dc.hi_category(HI)[1]
        hp_t = heat.protocol_for(HI)
        if HI >= 42:
            banner(f"<b>DANGER band right now ({HI:.0f}°C feels-like).</b> "
                   + (hp_t[-1]["headline"] if hp_t else "Cool, hydrate, check the elderly list.") +
                   " Cooling points and the class/work rules below are the levers a barangay still has today.", "warn")
        elif HI >= 33:
            banner(f"<b>Extreme caution ({HI:.0f}°C feels-like)</b> — outdoor work windows and respite points "
                   "are worth setting up before the DANGER hours arrive.", "info")
        pts_t = {p["name"]: p for p in cinema.heat_barangay_points(L, HI)}
        reach_t = heat.cooling_reach(L)
        cool_t = heat.load_cooling()
        cool_t = cool_t[cool_t["status"] == "open"]
        reached_t = {nm for nm in pts_t if reach_t.get(nm) and reach_t[nm][0] is not None and reach_t[nm][0] <= 2500}
        danger_t = {nm: p for nm, p in pts_t.items() if p["hi"] >= 42}
        pop_t = sum(p["pop"] for p in pts_t.values()) or 1
        try:
            hht = pd.DataFrame({"time": pd.to_datetime((live.get("hourly") or {}).get("time") or []),
                                "t": (live.get("hourly") or {}).get("temperature_2m") or [],
                                "rh": (live.get("hourly") or {}).get("relative_humidity_2m") or []})
            hht["HI"] = [dc.hi_c(t_, r_) for t_, r_ in zip(hht["t"], hht["rh"])]
            d0 = pd.Timestamp.now().floor("D")
            hhd = hht[(hht["time"] >= d0) & (hht["time"] < d0 + pd.Timedelta(days=1))]
            dang_left = int((hhd["HI"] >= 42).sum())
        except Exception:
            dang_left = None
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Residents in DANGER-band barangays", f"{sum(p['pop'] for p in danger_t.values()):,}",
                  f"{len(danger_t)} of {len(pts_t)} barangays at ≥42°C", delta_color="inverse")
        h2.metric("Population within 2.5 km of cooling", f"{100 * sum(pts_t[n]['pop'] for n in reached_t) / pop_t:.0f}%",
                  f"{len(reached_t)} of {len(pts_t)} barangays covered", delta_color="inverse")
        h3.metric("Cooling points open", f"{len(cool_t)}",
                  f"{heat.practice_count()} practice candidates · {heat.cooling_stats()['full']} full · "
                  f"{heat.cooling_stats()['closed']} closed", delta_color="off")
        h4.metric("DANGER hours left today", f"{dang_left} h" if dang_left is not None else "—",
                  "modelled city curve ≥42°C", delta_color="inverse")
        try:
            import folium
            from streamlit_folium import st_folium
            fmt = folium.Map(location=(16.04, 120.34), zoom_start=12, tiles=None, control_scale=True)
            folium.TileLayer(tiles=mapfilm.ESRI_SAT[0], attr=mapfilm.ESRI_SAT[1], name="satellite").add_to(fmt)
            folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(fmt)
            kit.brgy_layer(L, fmt, choro={nm: dict(frac=min(1.0, p["hi"] / 55.0),
                                                   note=f"feels like {p['hi']:.0f}°C · "
                                                        f"{dc.hi_category(p['hi'])[0]}"
                                                        + ("" if nm in reached_t else " · ⚠ beyond 2.5 km"))
                                          for nm, p in pts_t.items()})
            heat.shade_layer(fmt)
            heat.water_layer(fmt, L)
            pop_max_t = max([p["pop"] for p in pts_t.values()], default=1) or 1
            for _, c in cool_t.iterrows():
                try:
                    la, lo = float(c["lat"]), float(c["lon"])
                except Exception:
                    continue
                heat.cool_ring([la, lo]).add_to(fmt)
                heat.cool_marker([la, lo],
                                 tooltip=f"❄ {c['name']} · open · faint dotted ring = 2.5 km"
                                         + heat.cool_note(c)).add_to(fmt)
            for nm, p in pts_t.items():
                folium.CircleMarker([p["lat"], p["lon"]],
                                    radius=4 + 8 * (p["pop"] / pop_max_t) ** 0.5, color="#ffffff", weight=1.3,
                                    fill=True, fill_color=cinema._hi_color(p["hi"]), fill_opacity=0.92,
                                    tooltip=f"{nm} · {p['hi']:.0f}°C "
                                            + ("· covered" if nm in reached_t else "· ⚠ beyond 2.5 km")).add_to(fmt)
            folium.LayerControl(collapsed=False).add_to(fmt)
            st_folium(fmt, height=460, use_container_width=True, returned_objects=[], key="tel_heat_map")
            st.caption(f"Shading and dots follow the live reading above ({HI:.0f}°C feels-like at the city "
                       "centre + the urban-heat offset per barangay); faint dotted rings are the 2.5 km walk radius "
                       "of every open cooling point, and the 💧 water / 🌳 shade layers show where relief water and "
                       "cover actually are. Official heat-index advisories come from PAGASA.")
        except Exception as e:
            st.info(f"Heat map unavailable ({type(e).__name__}).")
        if st.button("☀️ Open the Heat Scenario Simulator →", key="tel_to_heat", use_container_width=True):
            _nav_to(NAV[2])

    st.subheader("🛰 Nearest station observations — aviation METAR (live, free)")
    met = gauges.fetch_metar()
    if (met.get("stations") or [{}])[0].get("temp_c") is None:
        st.info("aviationweather.gov unreachable right now (" + (met.get("error") or "network") +
                ") — the model feed above still runs.")
    else:
        from zoneinfo import ZoneInfo
        mcols = st.columns(len(met["stations"]))
        for mc, s in zip(mcols, met["stations"]):
            with mc:
                try:
                    obs = datetime.fromtimestamp(int(s["obs_time"]), tz=ZoneInfo("Asia/Manila")).strftime("%H:%M PHT")
                except Exception:
                    obs = s.get("obs_time", "—")
                rh = s.get("rh_pct")
                hi = dc.hi_c(s["temp_c"], rh) if (s.get("temp_c") is not None and rh) else None
                dmod = None
                if cur and hi is not None:
                    dmod = hi - dc.hi_c(cur["temperature_2m"], cur["relative_humidity_2m"])
                st.markdown(f"**{s['station']}** · {s.get('km_from_dagupan')} km away · obs {obs}")
                k1, k2, k3 = st.columns(3)
                k1.metric("Air", f"{s['temp_c']:.0f}°C", f"dew {s.get('dewpoint_c', '—'):.0f}°C" if s.get("dewpoint_c") is not None else None)
                k2.metric("Feels like", f"{hi:.0f}°C" if hi is not None else "—",
                          f"{dmod:+.0f}°C vs the model" if dmod is not None else "RH " + (f"{rh:.0f}%" if rh else "—"))
                k3.metric("Wind", f"{s.get('wind_kt', '—')} kt")
        st.caption("Real thermometers, wrong addresses: Laoag Intl (≈239 km) and Clark Intl (≈98 km) report every "
                   "30–60 min with no API key needed — Dagupan itself has no METAR station (Baguio RPUB publishes "
                   "none either). These sanity-check the model: a 1–3°C gap is normal weather noise, a 6°C+ gap "
                   "means distrust the model grid until the next fetch.")

    st.subheader("🌊 Upstream dams — Agno system (PAGASA dam table, live)")
    dams = gauges.fetch_dams()
    if not dams.get("dams"):
        st.info("PAGASA flood page unreachable (" + (dams.get("error") or "network") + ") — dam status unknown. "
                "The table at pagasa.dost.gov.ph/flood is updated around 08:00 daily.")
    else:
        st.caption(f"Observed **{dams.get('obs_label') or '—'}** · fetched {dams.get('fetched_at', '—')} · "
                   "parsed from the public PAGASA flood page; every row cross-checked (RWL − normal-high-water "
                   "matches the table's own deviation — bad rows are dropped, never shown).")
        dcols = st.columns(3)
        for dcol, d in zip(dcols, [x for x in dams["dams"] if x["name"] in gauges.AGNO_DAMS]):
            over = d["over_nhwl_m"]
            with dcol:
                st.metric(f"{d['name']} reservoir", f"{d['rwl_m']:.2f} m",
                          f"{over:+.2f} m vs normal high water ({d['nhwl_m']:.1f})",
                          delta_color="inverse" if over > 0 else "normal")
                st.caption(f"Gates: **{d['gates'] or 'closed / none reported'}**")
        sr = next((x for x in dams["dams"] if x["name"] == "San Roque"), None)
        if sr and sr["over_nhwl_m"] > 0 and not sr["gates"]:
            banner("<b>San Roque is holding a full pool</b> (+%.2f m over normal high water, gates closed). "
                   "Heavy rain over the Agno basin from here would force releases that become downstream flow "
                   "toward Dagupan — this is the signal to watch on the Pantal gauge and in PDRRMO bulletins."
                   % sr["over_nhwl_m"], "warn")
        b = dams.get("basin") or {}
        if b.get("status"):
            col = "#15803d" if b.get("level") == "non-flood" else "#b91c1c"
            st.markdown(f"<span style='background:{col};color:#fff;padding:4px 12px;border-radius:8px;"
                        f"font-weight:700;font-size:13px;'>Agno basin: {b['status']}</span> "
                        f"<span style='color:#6b7280;font-size:12px;'>PAGASA flood status — "
                        f"[open the basin PDF]({b.get('link')}) for the full bulletin</span>",
                        unsafe_allow_html=True)

    st.subheader("📟 Station catalogue — DOST-ASTI PhilSensors (archival)")
    ps = gauges.read_cache()
    if ps is None:
        st.info("No station check stored yet. Press **Check the stations now** — the station list is large and the "
                "public page is slow, so the first check can take a couple of minutes with progress shown.")
        if st.button("Check the stations now (~1–2 min, with progress)", key="ps_first"):
            with st.status("Checking PhilSensors…", expanded=True) as stt:
                ps = gauges.fetch_pangasinan(force=True, nearest=8,
                                             progress=lambda i, n, label: stt.update(
                                                 label=f"Checking PhilSensors… {label} ({i + 1}/{n + 1})"))
            st.toast("Station check done")
            st.rerun()
    else:
        c1, c2 = st.columns([3, 1])
        c1.caption(f"Last check: **{ps.get('fetched_at') or 'unknown'}** · live readings pulled for the "
                   f"{ps.get('nearest', 8)} nearest water/rain stations (the public station list is ~3,000 rows, "
                   "so we re-download it at most weekly).")
        if c2.button("⟳ Refresh readings", key="ps_refresh"):
            with st.status("Checking PhilSensors…", expanded=True) as stt:
                try:
                    ps = gauges.fetch_pangasinan(force=True, nearest=8,
                                                 progress=lambda i, n, label: stt.update(
                                                     label=f"Checking PhilSensors… {label} ({i + 1}/{n + 1})"))
                except Exception as e:
                    st.error(f"Refresh failed ({type(e).__name__}) — showing the stored check below.")
            st.rerun()
    if ps is not None:
        if ps.get("error"):
            st.warning(ps["error"])
        psum = gauges.summary(ps)
        sts, errs, tbl = psum["sts"], psum["errs"], psum["rows"]
    else:
        sts, errs, tbl = [], [], None
    if sts:
        g1, g2, g3 = st.columns(3)
        g1.metric("Stations reporting now (<3 h)", f"{psum['live_n']} / {len(sts)}")
        g2.metric("Water-level stations", f"{psum['water_n']}", "none inside Dagupan")
        g3.metric("Newest public reading", psum["newest"][:16])
        if psum["live_n"] == 0:
            st.markdown('<div class="cs-warn"><b>No live official river data for Dagupan.</b> Every Pangasinan '
                        'PhilSensors station\'s latest public reading is old (see table). Until a live feed is '
                        'arranged with PDRRMO / DOST-ASTI, use the manual Pantal log below.</div>', unsafe_allow_html=True)
        with st.expander(f"{len(tbl)} nearest stations with readings · checked {ps.get('fetched_at')}"):
            st.dataframe(tbl, hide_index=True, use_container_width=True)
            st.caption("This is an archive, not a live feed — newest public reading across it is from 2024. "
                       "Refresh only re-checks whether anything new was published. "
                       "For operational use, request official access: philsensors.asti.dost.gov.ph/datarequest/terms")
        if errs:
            st.caption(f"{len(errs)} station(s) skipped this check "
                       f"({', '.join(str(x.get('location') or x.get('station_id')) for x in errs[:4])}"
                       f"{'…' if len(errs) > 4 else ''}) — shown again next refresh.")

    st.subheader("🌊 Pantal River gauge — manual log, sheet bridge, PAGASA hook")
    prov = st.radio("Reading source", kit.GAUGE_PROVIDERS, horizontal=True, label_visibility="collapsed")
    g_last = kit.gauge_history()
    sheet_df, sheet_msg, feed_thresh = None, "", None
    if prov == "shared sheet (CSV URL)":
        surl = st.text_input("Shared sheet CSV export URL",
                             value=PREFS.get("gauge_sheet_url", ""),
                             help="Publish a shared sheet (PDRRMO/Log sheet) → File → Share → Publish to web → CSV, "
                                  "paste the link. Columns: logged_at, level_m (, note); optional alert_m/alarm_m/"
                                  "critical_m switch the tags to your official thresholds. "
                                  "Format spec: docs/future_real_operations/GAUGE_FEED_SPEC.md")
        if surl.strip():
            sheet_df, sheet_msg = kit.read_sheet_csv(surl.strip())
            if sheet_df is not None and len(sheet_df):
                feed_thresh = sheet_df.attrs.get("thresholds")
                PREFS["gauge_sheet_url"] = surl.strip()
                save_prefs(PREFS)
                st.success(f"Sheet bridge live — {len(sheet_df)} rows, latest "
                           f"{sheet_df.iloc[-1]['level_m']:.2f} m @ "
                           f"{pd.Timestamp(sheet_df.iloc[-1]['logged_at']):%b %d %H:%M}")
            else:
                st.warning(sheet_msg or "Sheet unreadable — check the published CSV link.")
        st.caption("**No hosting? Paste rows instead** — columns logged_at, level_m (, note); "
                   "di kalat ang format basta may petsa at lebel. Any stale rows are dropped.")
        ptxt = st.text_area("Paste agency CSV here (rows emailed/texted to you)", key="gauge_paste",
                            height=84)
        if st.button("📥 Load pasted rows"):
            pdf_, pth, pmsg = kit.parse_gauge_text(ptxt)
            if pdf_ is not None:
                st.session_state["gauge_paste_df"] = pdf_
                st.session_state["gauge_paste_note"] = pth
                st.toast(f"Loaded {len(pdf_)} pasted rows")
            else:
                st.toast(pmsg or "Pasted rows unreadable")
    elif prov == "PAGASA hook (experimental)":
        if st.button("Probe PAGASA flood pages"):
            _, msg = kit.pagasa_hook_probe()
            st.info(msg)
    paste_df = st.session_state.get("gauge_paste_df")
    if paste_df is not None:
        sheet_df = paste_df
        feed_thresh = st.session_state.get("gauge_paste_note") or feed_thresh
    if prov == "shared sheet (CSV URL)" and sheet_df is not None and len(sheet_df):
        use_df = sheet_df
        src_lab = "pasted feed" if paste_df is not None else "shared sheet"
    else:
        use_df = g_last
        src_lab = "manual log"
    gl1, gl2, gl3 = st.columns([1, 2, 1])
    lvl = gl1.number_input("Stage above normal (m)", 0.0, 6.0, 0.50, 0.05,
                           help="Read from PDRRMO bulletins/photos; proxy datum — the official PDRRMO stage map remains authoritative.")
    gnote = gl2.text_input("Source note (PDRRMO post, sitrep, banca operator…)")
    if gl3.button("Log stage", use_container_width=True):
        kit.gauge_save(lvl, gnote)
        st.toast("River stage logged")
        st.rerun()
    use_df = kit.gauge_history() if src_lab == "manual log" else use_df
    if len(use_df):
        last = use_df.iloc[-1]
        th = feed_thresh or dict(alert=0.8, alarm=1.2, critical=1.5)
        th_note = " · thresholds provided by the feed" if feed_thresh else " · ⚠ thresholds are proxies (0.8/1.2/1.5 m)"
        state, colr = kit.gauge_class(float(last["level_m"]), alert=th["alert"], alarm=th["alarm"],
                                      critical=th["critical"])
        fresh = kit.gauge_freshness()
        age = ""
        if fresh and src_lab == "manual log":
            age = f" · {fresh['age_h']:.1f} h old" + (" — STALE (>24 h), re-log" if fresh["stale"] else "")
        st.markdown(
            f"<span style='background:{colr};color:#fff;padding:5px 14px;border-radius:8px;"
            f"font-weight:700;font-size:14px;'>{state}</span> "
            f"<span style='color:#6b7280;font-size:12px;'>last: {float(last['level_m']):.2f} m · "
            f"{pd.Timestamp(last['logged_at']):%b %d %H:%M}{age} · source: {src_lab}{th_note}</span>",
            unsafe_allow_html=True)
        figg = go.Figure(go.Scatter(x=use_df["logged_at"], y=use_df["level_m"],
                                    mode="lines+markers", line=dict(color=ACCENT, width=2)))
        st.plotly_chart(plotly_beige(figg, height=210, y_title="m above normal"),
                        use_container_width=True)
    st.caption("Proxy thresholds — Alert 0.8 m · Alarm 1.2 m · Critical 1.5 m — to be re-anchored to the official "
               "PDRRMO stage datum when the gauge feed partnership (roadmap P3) lands.")

    st.subheader("Crowd reports (community telemetry)")
    cr_path = ROOT / "data" / "app_layers" / "crowd_reports.csv"
    with st.form("crowd", clear_on_submit=True):
        r1, r2, r3 = st.columns([1, 1, 1])
        when = r1.date_input("Date", date.today())
        who = r2.selectbox("Barangay", sorted(L.brgy["barangay"].tolist()))
        kind = r3.selectbox("Observation type", ["flood depth", "road state", "banca/rescue request", "water respite point"])
        detail = st.selectbox("Detail", ["gutter-deep", "ankle-deep", "knee-deep (light vehicles risky)",
                                         "waist-deep (impassable)", "chest-deep+ (life-safety)",
                                         "passable", "light vehicles only", "fully impassable"])
        note = st.text_input("Optional note (sitio/street, boats needed…)")
        if st.form_submit_button("Log report"):
            new = pd.DataFrame([[datetime.now().isoformat(timespec="minutes"), str(when), who, kind, detail, note]],
                               columns=["logged_at", "date", "barangay", "type", "detail", "note"])
            if cr_path.exists():
                old = pd.read_csv(cr_path)
                pd.concat([new, old]).to_csv(cr_path, index=False)
            else:
                new.to_csv(cr_path, index=False)
            st.toast("Report logged — salamat, kapitid!")
    if cr_path.exists():
        st.dataframe(pd.read_csv(cr_path).head(12), hide_index=True, use_container_width=True)

    st.subheader("On this week in history (1981–2026)")
    hist = L.daily.copy()
    hist["md"] = hist.index.strftime("%m-%d")

    def _md_obj(s):
        m, d = map(int, s.split("-"))
        return datetime(2000, m, d)

    today_md = datetime.now().strftime("%m-%d")
    window = hist[hist["md"].apply(
        lambda s: min(abs((_md_obj(s) - _md_obj(today_md)).days),
                      366 - abs((_md_obj(s) - _md_obj(today_md)).days)) <= 3)]
    wettest = window.nlargest(5, "RAIN")[["RAIN", "T2M_MAX", "HI"]]
    if len(wettest):
        wettest.index = wettest.index.strftime("%b %d, %Y")
        st.dataframe(wettest.round(1), use_container_width=True)
    st.caption("Context: this same calendar week once delivered 253 mm in one day (Oct 8, 2009).")

    # ================================================================= WALKTHROUGH

@st.fragment
def _fragment_wlk():
    st.button("Back to Command Deck", on_click=_nav_to, args=(NAV[0],))
    st.title(f"🗺️ {tt('Barangay Walkthrough')}")
    st.caption("Guided, barangay-specific: terrain → exposure → countermeasures → action card. Nothing generic.")

    sel_list = sorted(L.brgy["barangay"].tolist())
    top_name = str(L.brgy.dropna(subset=["CSRI"]).sort_values("CSRI", ascending=False).iloc[0]["barangay"])
    sel = st.selectbox("Choose your barangay (31)", sel_list, key="wt_sel",
                       index=sel_list.index(top_name) if top_name in sel_list else 0)
    row = L.brgy[L.brgy["barangay"] == sel].iloc[0]
    anchor_info = next((b for b in L.brgy_anchors if b["barangay"] == sel), None)
    anchor = anchor_info["anchor"] if anchor_info else None

    if "step" not in st.session_state:
        st.session_state["step"] = 0
    steps = ["Profile", "Terrain", "Flood exposure", "Countermeasures", "Evacuation route",
             "☀️ Heat & relief", "Action card"]
    sc = st.columns(len(steps))
    for i, name in enumerate(steps):
        if sc[i].button("➡ " + name if i == st.session_state["step"] else name,
                        use_container_width=True, type="primary" if i == st.session_state["step"] else "secondary"):
            st.session_state["step"] = i
            st.rerun()
    st.progress((st.session_state["step"] + 1) / len(steps))
    step = st.session_state["step"]

    # anchor tools — powered by the LGU when OSM has nothing useful for this barangay
    with st.expander("📍 Anchor tools (LGU / drill settings)"):
        tip = anchor if isinstance(anchor, dict) else None
        hint = ("Tip: no in-city OSM place node matches this barangay. Enter the core coordinates once "
                "(from a GPS reading of the barangay hall or an LGU map) and every map/valuation in this "
                "walkthrough works immediately and survives restarts."
                if anchor is None else
                f"Current anchor: {tip['lon']:.5f}, {tip['lat']:.5f} (OSM place node). If it's misplaced, "
                "override it with exact core coordinates below.")
        try:
            import shapely.geometry as _sg
            import brgypoly as _bp_shim
            city = _bp_shim._city_polygon_utm()
            X, Y = L.to_utm(tip["lon"], tip["lat"]) if tip else (None, None)
            hint += "" if (tip and city.contains(_sg.Point(X, Y))) else (" ⚠ anchor appears OUTSIDE the city — override below."
                                                                        if tip else "")
        except Exception:
            pass
        st.caption(hint)
        ma_path = PREFS_PATH.parent / "manual_anchors.json"
        st.caption("Coordinates stored locally in `data/app_layers/manual_anchors.json` — they survive app "
                   "restarts. Clear and save empty values to return to the OSM anchor.")
        man = json.loads(ma_path.read_text(encoding="utf-8")) if ma_path.exists() else {}
        cur = (man or {}).get(sel) or (tip or {})
        f1, f2, f3 = st.columns([1, 1, 1])
        mv_lon = f1.number_input("Core longitude", value=float(cur.get("lon", 120.3343)), format="%.6f",
                                 step=0.0001, key="ma_lon")
        mv_lat = f2.number_input("Core latitude", value=float(cur.get("lat", 16.0425)), format="%.6f",
                                 step=0.0001, key="ma_lat")
        if f3.button("💾 Save anchor override", use_container_width=True,
                      help="Writes the manual anchor and re-runs the walkthrough with it applied."):
            mm = man or {}
            if mv_lon and mv_lat and 120.0 < mv_lon < 120.6 and 15.8 < mv_lat < 16.3:
                mm[sel] = {"lon": mv_lon, "lat": mv_lat}
            else:
                mm.pop(sel, None)
            ma_path.write_text(json.dumps(mm, indent=1), encoding="utf-8")
            st.toast("Anchor override saved — layers reload on next page view")
            st.rerun()

    if step == 0:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Census 2020", f"{int(row['popn']):,}", "people")
        m2.metric("Urban / rural", "🏙 urban" if str(row["urban"]).strip().upper() == "U" else "🌾 rural")
        csri = row["CSRI"] if pd.notna(row.get("CSRI", np.nan)) else None
        m3.metric("CSRI watchlist score", f"{csri:.0f}/100" if csri else "—",
                  f"rank {int((L.brgy['CSRI'] > csri).sum()) + 1}/28" if csri else "no spatial anchor")
        m4.metric("Buildings within 600 m", f"{int(row.get('bldg_600m', 0) or 0)}")
        st.markdown(
            f"""
                    **{sel}** sits {(f"at ~{row['elev_m']:.1f} m elevation, {row['dist_river_m']:.0f} m from the nearest river/canal")
                    if anchor else "(no OSM spatial anchor — census-only for now; the LGU boundary file unlocks the rest)"}.
                    Mean flood-susceptibility in its 300 m core: **{row['mean_susc_300m']:.0f}/100** {("(city median 51)" if anchor else "")}.
                    """
        )
    elif step == 1:
        if anchor is None:
            st.info("This barangay has no OSM place anchor yet, so we can't center a local map. "
                    "Try Pantal, Carael, Calmay, Bonuan Gueset, Bolosan, Lucao — or ask the LGU for barangay polygons.")
        else:
            W_c = L.water_level_for_share(45)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Elevation at core", f"{row['elev_m']:.1f} m", "city median is 0.0 m")
            c2.metric("Nearest river/canal", f"{row['dist_river_m']:.0f} m")
            c3.metric("Susceptibility (300 m)", f"{row['mean_susc_300m']:.0f}/100",
                      "high" if row['mean_susc_300m'] >= 65 else "mid")
            d_core = max(W_c - float(row["elev_m"]), 0.0)
            c4.metric("Water at the core · calamity",
                      "dry" if d_core <= 0 else f"{d_core:.2f} m", kit.depth_label(d_core), delta_color="inverse")
            plain = ("Most ground here sits at or below ~2 m — in calamity-type events expect knee-to-waist water "
                     "even before high tide."
                     if row['elev_m'] <= 2 else
                     "Ground here is higher than most of this low city — flooding usually arrives through rivers "
                     "and backed-up drainage instead of direct ponding.")
            st.markdown(f'<div class="cs-banner" style="font-size:13.5px;"><b>Plain reading:</b> {plain}</div>',
                        unsafe_allow_html=True)
            t1, t2 = st.columns([1.45, 1])
            with t1:
                d_c = L.depth_grid(W_c)[0]
                try:
                    from streamlit_folium import st_folium
                    fm = kit.make_city_map(L, depth=d_c, W_cut=W_c, legend=False, highlight=sel,
                                           focus={"lat": anchor["lat"], "lon": anchor["lon"], "name": sel},
                                           center=(anchor["lat"], anchor["lon"]), zoom=14)
                    st_folium(fm, height=520, use_container_width=True)
                except Exception:
                    fig = make_local_fig(anchor, sel)
                    st.pyplot(fig)
                    plt.close(fig)
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:10px;font-size:12px;color:#1f2937;">'
                    '<b>How to read this map:</b> star = barangay core · blue shading = flood water at '
                    'calamity level — darker means deeper · green line = coastline · blue lines = rivers/canals · '
                    'dots = schools (blue) & health sites (red). Hover anything.</div>'
                    '<div style="margin-top:4px;font-size:11px;color:#6b7280;">Flood depth: '
                    '<span style="display:inline-block;width:120px;height:8px;border-radius:4px;'
                    'background:linear-gradient(90deg,#ffffd9,#c7e9b4,#41b6c4,#081d58);"></span> shallow → deep</div>',
                    unsafe_allow_html=True)
            with t2:
                st.markdown("#### Your ground, east to west")
                dists, z = kit.terrain_profile(L, anchor["lon"], anchor["lat"])
                fprof = go.Figure()
                fprof.add_scatter(x=dists, y=z, fill="tozeroy", name="ground",
                                  line=dict(color="#8a7a5c", width=2), hovertemplate="%{x:.0f} m · ground %{y:.2f} m<extra></extra>")
                fprof.add_scatter(x=dists, y=np.maximum(z, W_c), fill="tonexty", name="flood water (calamity)",
                                  line=dict(color="#2563eb", width=1.5), fillcolor="rgba(37,99,235,.35)",
                                  hovertemplate="water %{y:.2f} m<extra></extra>")
                fprof.add_scatter(x=[0], y=[float(row["elev_m"])],
                                  mode="markers", name="core", marker=dict(size=12, color="#f59e0b", symbol="star"),
                                  hovertemplate="your core<extra></extra>")
                fprof.update_layout(height=320,
                                    xaxis=dict(title="metres east (−) of the core (+)", gridcolor=PLOT_GRID),
                                    yaxis=dict(title="m above sea", gridcolor=PLOT_GRID))
                fprof = plotly_beige(fprof, height=320, title="Ground profile · 2.6 km through the core")
                fprof.update_layout(margin=dict(l=8, r=8, t=34, b=66),
                                    legend=dict(orientation="h", y=-0.44, x=0, font=dict(size=10),
                                                bgcolor="rgba(0,0,0,0)"))
                st.plotly_chart(fprof, use_container_width=True, config={"displayModeBar": False})
                st.markdown(mapfilm.depth_gauge_html(d_core, kit.depth_label(d_core) + " at the core"),
                            unsafe_allow_html=True)
                st.caption("The blue wedge between the ground line and the water line is how deep a calamity flood "
                           "sits on each street — the wider the wedge over the star, the more of the barangay goes "
                           "under. Tide is not included here; it adds on top.")
    elif step == 2:
        res = []
        for name, share_e in dc.SCENARIOS.items():
            We = L.water_level_for_share(share_e)
            de = L.depth_grid(We)[0]
            e = L.exposure(de, We)
            est = None
            if sel in e["barangay_impact"]["barangay"].values:
                est = e["barangay_impact"].set_index("barangay").loc[sel, "affected_est"]
            res.append({"scenario": name.replace(" (", " · ("), "water level": f"+{We:.2f} m",
                        "residents in flood zones (est)": est})
        st.dataframe(pd.DataFrame(res), hide_index=True, use_container_width=True)
        st.caption("Estimates scale the barangay census by the flooded share of its area — polygon basis where boundary masks exist, 600 m anchor window as fallback (see basis column). "
                   "Multi-day events (Aug 2026 pattern) stress evacuation beyond day-one numbers.")
    elif step == 3:
        W_c = L.water_level_for_share(45) + 0.20
        d0 = L.depth_grid(W_c)[0]
        e0 = L.exposure(d0, W_c)
        d1 = L.depth_grid(W_c, dredge_m=0.25, drainage_m=0.10)[0]
        e1 = L.exposure(d1, W_c)
        est0 = None
        if sel in e0["barangay_impact"]["barangay"].values:
            est0 = e0["barangay_impact"].set_index("barangay").loc[sel, "affected_est"]
        est1 = None
        if sel in e1["barangay_impact"]["barangay"].values:
            est1 = e1["barangay_impact"].set_index("barangay").loc[sel, "affected_est"]
        c1, c2 = st.columns(2)
        c1.metric("Residents affected — status quo", f"{est0 if est0 is not None else '—'}",
                  "calamity event, tide +0.20 m", delta_color="inverse")
        c2.metric("…after dredging + drainage program", f"{est1 if est1 is not None else '—'}",
                  "proxy drawdown 0.25 m / 0.10 m", delta_color="inverse")
        st.info("Standard package shown: channel dredging (0.25 m buffer drawdown) + urban drainage (0.10 m event "
                "storage). Tune the full program in the 🛡️ Countermeasure Lab.")
    elif step == 4:
        if anchor is None:
            st.info("No spatial anchor — the route card needs a barangay core point.")
        else:
            W_s = L.water_level_for_share(45) + 0.20
            st.caption(kit.wt(PREFS.get("lang", "English"), "intro"))
            w_s = st.slider("Water level on the streets (+m)", 0.0, max(1.5, W_s + 0.3), W_s, 0.05, key="wt_w")
            route_card(sel, w_s, key_prefix="wt_rc")
            st.button("Open this route in the Simulator →", on_click=_go_walk_brgy, args=(sel,))
    elif step == 5:
        live_h, _ = get_live()
        cur_h = (live_h or {}).get("current", {})
        plan_h = cinema.heat_plan(L, cinema.HEAT_STORIES["heatwave_brownout"])
        if cur_h and "temperature_2m" in cur_h:
            HIh = dc.hi_c(cur_h["temperature_2m"], cur_h["relative_humidity_2m"])
            src_h = "live estimate (Open-Meteo → PAGASA bands)"
        else:
            HIh = float(max(f["hi"] for f in plan_h))
            src_h = "modelled heat-day curve (no live reading)"
        me = next((p for p in cinema.heat_barangay_points(L, HIh) if p["name"] == sel), None)
        reach_h = heat.cooling_reach(L)
        d_h = reach_h.get(sel)
        near_h = heat.nearest_cooling(L, anchor["lat"], anchor["lon"]) if anchor else None
        dgh = sum(1 for f in plan_h
                  if any(p["name"] == sel and p["hi"] >= 42
                         for p in cinema.heat_barangay_points(L, f["hi"])))
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Feels like here", f"{me['hi']:.0f}°C" if me else "—",
                  dc.hi_category(HIh)[0], delta_color="inverse")
        b2.metric("DANGER hours (heat day)", f"{dgh} h",
                  "≥42°C feels-like at this core", delta_color="inverse")
        b3.metric("Distance to open cooling",
                  f"{d_h[0] / 1000:.1f} km" if d_h and d_h[0] is not None else "—",
                  (d_h[1] if d_h else "none registered"), delta_color="inverse")
        b4.metric("Cooling reached?", "✅ yes" if d_h and d_h[0] is not None and d_h[0] <= 2500 else "⚠ beyond 2.5 km",
                  "straight-line radius", delta_color="off")
        t1, t2 = st.columns([1.45, 1])
        with t1:
            try:
                from streamlit_folium import st_folium
                ch = {p["name"]: dict(frac=min(1.0, p["hi"] / 55.0),
                                      note=f"feels like {p['hi']:.0f}°C · {dc.hi_category(p['hi'])[0]}")
                      for p in cinema.heat_barangay_points(L, HIh)}
                center_h = (anchor["lat"], anchor["lon"]) if anchor else (16.04, 120.34)
                fmh = kit.make_city_map(L, choro=ch, highlight=sel,
                                        focus={"lat": center_h[0], "lon": center_h[1], "name": sel},
                                        center=center_h, zoom=14 if anchor else 12, legend=False,
                                        extras=lambda mm: (heat.shade_layer(mm),
                                                           heat.water_layer(mm, L, rivers=False)))
                for _, c in heat.load_cooling().iterrows():
                    if str(c.get("status")) != "open":
                        continue
                    try:
                        la, lo = float(c["lat"]), float(c["lon"])
                    except Exception:
                        continue
                    heat.cool_ring([la, lo]).add_to(fmh)
                    heat.cool_marker([la, lo],
                                     tooltip=f"❄ {c['name']} · open · faint dotted ring = 2.5 km").add_to(fmh)
                st_folium(fmh, height=520, use_container_width=True)
            except Exception:
                fig = make_local_fig(anchor, sel) if anchor else None
                if fig is not None:
                    st.pyplot(fig)
                    plt.close(fig)
            st.markdown(
                '<div style="font-size:12px;color:#1f2937;"><b>How to read this map:</b> shading = felt heat at '
                f'{HIh:.0f}°C city conditions (deeper = hotter) · ❄ = open cooling point · faint dotted ring = '
                '2.5 km straight-line reach · 💧 blue = ponds & refilling stations · 🌳 green = shade · '
                'star = this barangay core.</div>', unsafe_allow_html=True)
        with t2:
            st.markdown("#### Relief reach here")
            st.markdown(
                f"Nearest open cooling point: **{near_h['name'] if near_h else 'none registered'}**"
                + (f" — {near_h['distance_m'] / 1000:.1f} km, {near_h.get('status', 'open')}"
                   if near_h else
                   " — register one from the 🏠 Command Deck cooling board.")
            )
            hp_h = heat.protocol_for(HIh)
            if hp_h:
                top_h = hp_h[-1]
                st.markdown(f"**{top_h['band']}** — {top_h['headline']}")
                for o, t in top_h["actions"][:3]:
                    st.markdown(f"· **{o}:** {t}")
            st.markdown(
                f"{dgh} DANGER hours on a heat-day + brownout (11:00–17:00 pattern) is when this barangay "
                "needs shade, water and a place to sit — not just a fan."
            )
            st.button("☀️ Open the Heat Scenario Simulator →", on_click=_go_heat_brgy,
                      args=(sel,), key="wt_to_heat")
    else:
        W_c = L.water_level_for_share(45) + 0.20
        depth = L.depth_grid(W_c)[0]
        e = L.exposure(depth, W_c)
        est = None
        if sel in e["barangay_impact"]["barangay"].values:
            est = e["barangay_impact"].set_index("barangay").loc[sel, "affected_est"]
        live, ok = get_live()
        cur = (live or {}).get("current", {})
        heat_now = bool(cur and dc.hi_c(cur["temperature_2m"], cur["relative_humidity_2m"]) >= 42)
        if heat_now:
            HI = dc.hi_c(cur["temperature_2m"], cur["relative_humidity_2m"])
            card = kit.action_card_heat(row, HI, dc.hi_category(HI)[0], lang=PREFS.get("lang", "English"))
            st.subheader("🔥 Heat action card (live trigger)")
        else:
            card = kit.action_card_flood(row, W_c, est, "Calamity-class preparedness",
                                          lang=PREFS.get("lang", "English"))
            st.subheader("🌊 Flood action card (Calamity-class preparedness)")
        gcol, mcol = st.columns([1, 2])
        with gcol:
            d_core = 0.0 if heat_now else max(W_c - float(row["elev_m"]), 0.0)
            st.markdown(mapfilm.depth_gauge_html(d_core, kit.depth_label(d_core) + " at the core"),
                        unsafe_allow_html=True)
        with mcol:
            m1, m2 = st.columns(2)
            m1.metric("Est. residents in flood zones", f"{est:,}" if est is not None else "—",
                      f"of {int(row['popn']):,} census (calamity + tide)")
            if heat_now:
                m2.metric("Heat index NOW", f"{dc.hi_c(cur['temperature_2m'], cur['relative_humidity_2m']):.0f}°C",
                          dc.hi_category(HI)[0], delta_color="inverse")
                hp = heat.protocol_for(HI)[-1]
                st.markdown(f"**Today's call ({hp['band']}):** {hp['headline']}  \n"
                            + "  \n".join(f"· **{o}:** {t}" for o, t in hp["actions"][:2]),
                            unsafe_allow_html=True)
                if anchor:
                    nc = heat.nearest_cooling(L, anchor["lat"], anchor["lon"])
                    st.caption("Nearest open relief: **%s**%s" % (
                        nc["name"][:40] if nc else "none registered",
                        f" · {nc['distance_m'] / 1000:.1f} km" if nc else
                        " — register one in the Deck's ❄️ Cooling register"))
            elif anchor:
                sp = ops.shelter_with_space(L, anchor["lat"], anchor["lon"], W_c, people=int(row["popn"]) // 100 or 1)
                m2.metric("Nearest shelter with space", (sp["name"][:34] if sp else "none OPEN with space"),
                          f"{sp['free']} free · {sp['distance_m'] / 1000:.1f} km" if sp else
                          "open one on the 🏠 Shelters board")
            else:
                m2.metric("Nearest shelter with space", "—", "no spatial anchor")
        st.code(card, language=None)
        brief, bext = kit.build_briefing(row, anchor, W_c, est, "Calamity-class (Aug 2026-type event)",
                                         PREFS.get("lang", "English"),
                                         map_fig_fn=(lambda: make_local_fig(anchor, sel)) if anchor else None,
                                         city_meta=L.meta, susc=float(row.get("mean_susc_300m", 0) or 0))
        st.download_button(f"⬇ One-page barangay briefing ({bext.upper()})", data=brief,
                           file_name=f"climateshield_briefing_{sel}.{bext}",
                           mime="application/pdf" if bext == "pdf" else "image/png",
                           use_container_width=True)
        if bext == "png":
            st.caption("PDF export is unavailable on this machine (a Windows security policy blocks the PDF library) — "
                       "the briefing downloads as a printable image instead.")
        st.caption("Copy-paste ready for the barangay Facebook page, Viber group, or SMS blast.")
        with st.expander("💬 Was this action card useful? (drill feedback)"):
            st.caption("Takes 10 seconds: tells the project what actually helps in the field. Optional author = "
                       "role only (e.g. 'kagawad', 'trainer').")
            wf1, wf2 = st.columns([1, 1.4])
            wf_rate = wf1.select_slider("Usefulness", options=[1, 2, 3, 4, 5], value=4, key="wt_fb_rate")
            wf_who = wf1.text_input("Your role (optional)", key="wt_fb_who")
            wf_change = wf2.text_input("One thing to change or add to this card", key="wt_fb_change")
            if st.button("💾 Log card feedback", use_container_width=True):
                feedback.log(context=f"walkthrough-card:{sel}", barangay=sel, rating=wf_rate,
                             worked="card shown", change=wf_change, author=wf_who)
                st.toast("Salamat — logged for the next card revision")
            notes = feedback.list_notes(context=f"walkthrough-card:{sel}", limit=5)
            if len(notes):
                nd = notes.iloc[0]
                st.caption(f"Last note ({nd['at'][:10]}): ⭐{nd['rating']} · "
                           + (nd["change"] or "no suggested changes"))


    
# ================================================================= RESPONSE & DISPATCH
def _anchor(brgy):
    return next((b["anchor"] for b in L.brgy_anchors if b["barangay"] == brgy), None)


def _inbox_to_request(msg_id, sender, body, drill):
    parsed = sms.parse_request(body, L.brgy["barangay"].tolist())
    if parsed and parsed["barangay"]:
        a = _anchor(parsed["barangay"])
        W_r = st.session_state.get("_resp_W", 0.5)
        inbox = sms.load_log(sms.INBOX)
        rec = inbox[inbox["msg_id"] == msg_id]["at"].iloc[0] if len(inbox) and (inbox["msg_id"] == msg_id).any() else ""
        sug = rsp.suggest_responder(L, a["lat"], a["lon"], parsed["need"], W_r, parsed["urgency"]) if a else None
        rid = rsp.add_request(parsed["barangay"], parsed["people"], parsed["need"], parsed["urgency"], sender,
                              parsed["note"], sug["name"] if sug else "", source="sms", drill=drill, received_at=rec)
        st.session_state["_resp_toast"] = f"Text → request {rid} ({parsed['barangay']}, {parsed['people']} people)"
    else:
        st.session_state["_resp_toast"] = "Could not find a barangay name in that text — log it manually."
    sms.mark_handled(msg_id)


# ----------------------------------------------------------------- timed exercise (clock + events + score)
def _score_card(sc):
    k = sc["kpis"]
    fmt = lambda x: f"{x:.1f} min" if x == x else "—"  # noqa: E731
    c = st.columns(6)
    c[0].metric("Score", f"{sc['total']:.0f} / 100", f"grade {sc['grade']}")
    c[1].metric("Text → request", fmt(k["intake_min"]), "target ≤ 2 min", delta_color="off")
    c[2].metric("Request → unit", fmt(k["assign_min"]), "target ≤ 3 min", delta_color="off")
    c[3].metric("Resolved", f"{100 * k['resolved_pct']:.0f}%", f"critical {100 * k['critical_resolved_pct']:.0f}%",
                delta_color="off")
    c[4].metric("Events acknowledged", f"{100 * k['events_acked_pct']:.0f}%", fmt(k["ack_min"]) + " avg", delta_color="off")
    c[5].metric("People still waiting", f"{k['people_waiting']:,}", f"{k['texts_ignored']} texts unanswered",
                delta_color="off")
    pts = sc["points"]
    st.caption(" · ".join(f"{n} {v:.0f}" for n, v in pts.items())
               + (f" · penalties −{sc['penalty']} ({k['shelters_overfilled']} overfilled shelter(s), "
                  f"{k['unsafe_shelters_occupied']} unsafe shelter(s) still occupied)" if sc["penalty"] else "")
               + " — points: intake 15 · assignment 20 · resolved 25 · critical 15 · events 15 · text coverage 10")


@st.fragment(run_every=5)
def _fragment_exercise():
    state, fired = exercise.tick(L)
    for e in fired:
        st.toast(f"⚠ Storm hour {e['h']:.0f}: {e['title']}")
    for note in (state.get("phys_notes") or []):
        st.toast(note)
    if state.get("phys_notes"):
        state["phys_notes"] = []
        exercise.save(state)
    with st.container(border=True):
        if not state.get("running"):
            st.markdown("#### 🎯 Timed exercise")
            st.caption("Run the response against a storm clock. Flood conditions on this page follow the storm hour; "
                       "complications are injected as it unfolds; you get a score at the end. Starting resets the "
                       "simulation (requests, messages, unit assignments, shelter headcounts) — practice capacities and "
                       "units you registered are kept.")
            r1a, r1b, r1c = st.columns([1.3, 1.7, 3.0])
            team = r1a.text_input("Team name", PREFS.get("ex_team", "Team A"), key="ex_team")
            mode = r1b.radio("Storm source", ["📖 Story storms", "🌩 Real storm replays"], horizontal=True,
                             label_visibility="collapsed", key="ex_mode")
            PREFS["pilot"] = r1c.multiselect("Practice barangay(s)", sorted(L.brgy["barangay"].tolist()),
                                             default=PREFS.get("pilot", ["Pantal"]) or ["Pantal"], key="pilot_sel")
            if mode.startswith("📖"):
                r2a, r2b, r2c = st.columns([3.2, 1.6, 1.0])
                keys = list(cinema.FLOOD_STORIES.keys())
                sk = r2a.selectbox("Story storm", keys, format_func=lambda k: cinema.FLOOD_STORIES[k]["title"], key="ex_story")
                story = cinema.FLOOD_STORIES[sk]
                speed_opts, sdef = [1, 2, 4, 8], 4
                shelp = "4 → the 40-hour story storm takes 10 minutes"
                speed_w, start_w = r2b, r2c
            else:
                r2a, r2b, r2c, r2d = st.columns([1.9, 1.4, 1.2, 1.0])
                ev_keys = list(replay.EVENTS.keys())
                evk = r2a.selectbox("Historical event", ev_keys, format_func=lambda k: replay.EVENTS[k]["label"], key="ex_event")
                rkeys = list(replay.READINESS.keys())
                rk = r2b.selectbox("City readiness", rkeys, format_func=lambda k: replay.READINESS[k]["label"],
                                   key="ex_readiness", help=replay.READINESS["as_happened"]["note"])
                story = replay.build_story(L, evk, rk)
                speed_opts, sdef = [12, 24, 48, 96], 48
                shelp = "48 → a month-long replay runs in ~18 minutes. Replay = real 1981–2026 daily rainfall driving the proxy model."
                speed_w, start_w = r2c, r2d
            speed = speed_w.select_slider(
                "Storm-hours per real minute", speed_opts, value=sdef, key="ex_speed", help=shelp)
            if start_w.button("▶ Start", type="primary", use_container_width=True, key="ex_start"):
                PREFS["ex_team"] = team
                save_prefs(PREFS)
                exercise.start(L, story, speed, PREFS.get("pilot") or ["Pantal"], team)
                st.rerun(scope="app")
            save_prefs(PREFS)
            if mode.startswith("🌩"):
                st.caption(f"**{story['title']}** — {story['note']}")
                dr = story["daily_rain"]
                st.caption("Daily rain in the event window: " + " ".join(
                    f"{d} {r:.0f}" for d, r in dr if r >= 50) or "no heavy-rain day (≥50 mm) in this window")
            if state.get("final_score"):
                st.markdown(f"**Last run — {state.get('team')}** · {state['story']['title']} "
                            f"· stopped at storm hour {state.get('final_hour', 0):.0f}")
                _score_card(state["final_score"])
                try:
                    png = _debrief_png(json.dumps(state, sort_keys=True, default=str))
                    st.image(png, use_column_width=True)
                    st.download_button("⬇ Download this debrief (PNG)", data=png,
                                        file_name=f"debrief_{state.get('team', 'team').replace(' ', '_')}.png",
                                        mime="image/png", use_container_width=True)
                    st.caption("Debrief reading: the blue curve is the storm water level over the run; "
                               "each ▽ marks a help text turned into a request, each ● a unit assignment, each ★ "
                               "everyone in that request delivered; red dotted lines are the complications as they "
                               "hit, labeled E1–E9 with the storm hour — the distance between a line and the next ● "
                               "is your reaction time.")
                except Exception as e:
                    st.info(f"Debrief chart unavailable ({type(e).__name__}).")
            hist = exercise.history_summary()
            if hist:
                with st.expander(f"📊 Run history ({hist['n']} runs) — compare teams"):
                    b = hist["best"]
                    st.markdown(f"**Best run so far:** {b['team']} · {b['scenario']} · "
                                f"**{b['score']:.0f}/100 (grade {b['grade']})** — "
                                f"{b.get('resolved_pct', '')}% resolved · {b.get('people_waiting', '')} still waiting at stop")
                    h = hist["hist"]
                    colors = px.colors.qualitative.Set1
                    figc = go.Figure()
                    for j, tm in enumerate(sorted(set(h["team"]))):
                        hs = h[h["team"] == tm]
                        figc.add_trace(go.Scatter(
                            x=list(hs["finished"].dt.strftime("%b %d %H:%M")),
                            y=hs["score"], mode="lines+markers", name=str(tm),
                            line=dict(color=colors[j % len(colors)]),
                            customdata=hs[["grade", "scenario", "resolved_pct"]],
                            hovertemplate="%{y:.0f}/100 · %{customdata[0]} · %{customdata[1]}<br>"
                                          "resolved %{customdata[2]}%<extra>%{fullData.name}</extra>"))
                    figc.add_hline(y=float(b["score"]), line_dash="dot",
                                   annotation_text=f"best {b['score']:.0f} ({b['team']})")
                    figc.update_layout(yaxis=dict(title="score / 100", range=[0, 105], gridcolor=PLOT_GRID),
                                       xaxis=dict(gridcolor=PLOT_GRID), height=260,
                                       margin=dict(l=10, r=10, t=8, b=10),
                                       legend=dict(orientation="h", y=-0.35, font=dict(size=10)),
                                       hovermode="closest")
                    st.plotly_chart(plotly_beige(figc, height=260), use_container_width=True,
                                    config={"displayModeBar": False})
                    pt = hist["per_team"]
                    st.dataframe(pt.rename(columns={"team": "Team", "best": "Best score", "runs": "Runs"})
                                 .sort_values("Best score", ascending=False),
                                 hide_index=True, use_container_width=True)
                    with st.expander("All runs (table)"):
                        st.dataframe(h.drop(columns=["finished"], errors="ignore"), hide_index=True,
                                     use_container_width=True)
                    st.caption("Runs are comparable when the storm, readiness factors and unit registration match — "
                               "favorable storm draws inflate scores, judge runs by storm first.")
            sfn = feedback.summary()
            _fb_num = f" · avg {sfn['avg']:.1f}★ over {sfn['n']}" if sfn else ""
            with st.expander(f"📋 Team debrief notes{_fb_num} — close the loop"):
                fb1, fb2 = st.columns([1, 1.6])
                with fb1:
                    st.caption("What worked, what didn't — captured here so the next drill starts smarter. "
                               "No names needed; role or team is enough.")
                    fb_rate = st.select_slider("How ready did the team feel? (1 = scrambling, 5 = ready)",
                                               options=[1, 2, 3, 4, 5], value=3, key="fb_rate")
                    fb_team = st.text_input("Role / team (optional)", key="fb_team")
                    fb_worked = st.text_input("What worked", key="fb_worked")
                    fb_change = st.text_input("What to change next time", key="fb_change")
                    if st.button("💾 Log debrief note", use_container_width=True):
                        fb_context = f"exercise: {state.get('team', '—')} · {state['story']['title'][:40]}" \
                            if state.get("running") or state.get("final_score") else "exercise"
                        feedback.log(context=fb_context, barangay=PREFS["pilot"][0] if PREFS.get("pilot") else "",
                                     rating=fb_rate, worked=fb_worked, change=fb_change, author=fb_team)
                        st.toast("Debrief note logged — salamat!")
                        st.rerun()
                with fb2:
                    notes = feedback.list_notes(limit=6)
                    if len(notes):
                        for _, nd in notes.iterrows():
                            st.markdown(f"**⭐{nd['rating']} · {nd['context']}** {nd['at'][:10]} · {nd['author']}" +
                                        (f"  \n✅ _{nd['worked']}_" if nd["worked"] else "") +
                                        (f"  \n🔧 _{nd['change']}_" if nd["change"] else ""))
                    else:
                        st.caption("No notes yet — the first debrief after a drill goes here.")
            return

        story = state["story"]
        max_h = float(state.get("max_h", 40.0))
        h = exercise.sim_hour(state)
        W = exercise.water_at(L, story, h)
        hour_lbl = (f"h {h:,.0f} / {max_h:,.0f}" if story.get("replay") else f"{h:04.1f} / 40")
        t1, t2, t3, t4 = st.columns([1.1, 1, 3, 1])
        t1.metric("Storm clock", hour_lbl, f"×{state['speed']:g} speed", delta_color="off")
        t2.metric("Water", "streets dry" if W <= 0 else f"+{W:.2f} m", delta_color="off")
        with t3:
            st.markdown(f"**{state['team']} · {story['title']}**  \n{exercise.caption_at(story, h)}")
            st.progress(min(h / max_h, 1.0))
        if t4.button("↻ Update tables", use_container_width=True, key="ex_refresh",
                     help="Events update this panel live; the tabs below refresh when you act or press this."):
            st.rerun(scope="app")
        if t4.button("⏹ Stop & score", type="primary", use_container_width=True, key="ex_stop"):
            exercise.stop(L)
            st.rerun(scope="app")
        fired_evs = [e for e in state["events"] if e.get("fired_at")]
        nxt = next((e for e in state["events"] if not e.get("fired_at")), None)
        if fired_evs:
            for e in reversed(fired_evs[-4:]):
                c1, c2 = st.columns([5, 1])
                if e.get("acked_at"):
                    secs = (pd.to_datetime(e["acked_at"]) - pd.to_datetime(e["fired_at"])).total_seconds()
                    c1.markdown(f"✅ **h{e['h']:,.0f} · {e['title']}** — {e['detail']} *(acknowledged in {secs:.0f}s)*")
                else:
                    c1.markdown(f"🔴 **h{e['h']:,.0f} · {e['title']}** — {e['detail']}  \n→ {e['hint']}")
                    c2.button("Acknowledge", key=f"ack_{e['id']}", on_click=exercise.acknowledge, args=(e["id"],),
                              use_container_width=True)
        st.caption((f"Next complication around storm hour {nxt['h']:,.0f}. " if nxt else "All complications fired. ")
                   + "Live score so far: " + f"{exercise.score(L, state)['total']:.0f}/100")
        if h >= max_h:
            exercise.stop(L)
            st.rerun(scope="app")


def _merge_edits(key, base, fresh, id_col):
    """Save only the cells the user changed (see ops.merge_edits) — never overwrite event changes."""
    return ops.merge_edits(st.session_state.get(key) or {}, base, fresh, id_col)


@st.fragment
def _fragment_response():
    if st.session_state.get("_resp_toast"):
        st.toast(st.session_state.pop("_resp_toast"))

    # ---------------------------------------------------------------- simulator banner
    drill = True
    st.markdown('<div class="cs-warn"><b>SIMULATOR</b> — practice environment only. No messages are sent and no '
                'agency is contacted; every "text" here is simulated and logged on this computer.</div>',
                unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([1.4, 1, 1])
    if sc1.button("🎲 Simulate 6 incoming help texts", use_container_width=True):
        for snd, body in ops.drill_messages(PREFS["pilot"] or ["Pantal"], 6):
            sms.simulate_inbound(snd, body)
        st.toast("6 simulated texts are in the 📱 Messages inbox")
    if sc3.button("☀️ Simulate 6 heat help texts", use_container_width=True,
                  help="Heat cramps, brownout and thirst instead of rising water — parsed by the same inbox."):
        for snd, body in ops.heat_drill_messages(PREFS["pilot"] or ["Pantal"], 6):
            sms.simulate_inbound(snd, body)
        st.toast("6 heat texts are in the 📱 Messages inbox")
    if sc2.button("🧹 Reset simulation", use_container_width=True,
                  help="Clears requests, messages, unit assignments and shelter headcounts. Practice barangays are set "
                       "in the exercise panel above."):
        ops.reset_simulation(L)
        st.toast("Simulation reset")
        st.rerun()

    # ---------------------------------------------------------------- heat situation strip
    HIr, cat_r, hp_r = None, "", []
    try:
        # a running exercise keeps this page on the clock — modelled heat, no live weather fetch
        ex_r = exercise.load()
        live_r, _ = (None, None) if ex_r.get("running") else get_live()
        cur_r = (live_r or {}).get("current", {})
        if cur_r and "temperature_2m" in cur_r and "relative_humidity_2m" in cur_r:
            HIr = dc.hi_c(cur_r["temperature_2m"], cur_r["relative_humidity_2m"])
            src_r = "live estimate"
        else:
            plan_r = cinema.heat_plan(L, cinema.HEAT_STORIES["heatwave_brownout"])
            HIr = float(max(f["hi"] for f in plan_r))
            src_r = "modelled heat day (drill)" if ex_r.get("running") else "modelled heat day (no live reading)"
        cat_r = dc.hi_category(HIr)[0]
        hp_r = heat.protocol_for(HIr)
        stats_r = heat.cooling_stats()
        reach_r = heat.cooling_reach(L)
        gap_r = [nm for nm, d in reach_r.items() if not d or d[0] is None or d[0] > 2500]
        st.markdown(
            f'<div class="{"cs-warn" if HIr >= 42 else "cs-banner"}" style="font-size:13.5px;">'
            f'<b>☀️ Heat now ({src_r}):</b> {HIr:.0f}°C feels-like — {cat_r}. '
            f'{stats_r["open"]} cooling point(s) open · {len(gap_r)} of {len(reach_r)} barangays sit beyond a '
            f'2.5 km walk of one.'
            + (f' <b>{hp_r[-1]["headline"]}</b>' if HIr >= 42 and hp_r else "")
            + '</div>', unsafe_allow_html=True)
    except Exception:
        HIr = None
    cooling_empty_state("resp_heat_practice_seed", where="this heat strip, the dispatch map and the "
                                                         "cooling rings", style="info")

    ex_state = exercise.load()
    if ex_state.get("running"):
        _story = ex_state["story"]
        _h = exercise.sim_hour(ex_state)
        W_r = exercise.water_at(L, _story, _h)
        st.caption(f"🎯 Exercise running — flood conditions follow storm hour {_h:,.1f}: "
                   + ("streets dry" if W_r <= 0 else f"water +{W_r:.2f} m") + ". Facility flood states update as it rises.")
        if st.button("🖥 Facilitator screen — open on the room's projector",
                     help="Opens a second tab with a large clock, event feed and live score. This tab stays interactive."):
            components.html(
                "<script>window.open(location.origin + location.pathname + '?facilitator=1', '_blank');</script>",
                height=0)
        st.caption("If a popup blocker stopped it, type this URL on the projector device: "
                   "`http://<this-computer>:8501/?facilitator=1`")
    else:
        scen_r = st.selectbox("Assume flood conditions", list(dc.SCENARIOS.keys()), index=2, key="resp_scen")
        W_r = L.water_level_for_share(dc.SCENARIOS[scen_r]) + 0.20
    st.session_state["_resp_W"] = W_r
    reqs = rsp.load_requests()
    open_r = reqs[reqs["status"] != "resolved"] if len(reqs) else reqs
    shel = ops.load_shelters(L)
    res = ops.load_resources()
    inbox = sms.load_log(sms.INBOX)
    unhandled = inbox[inbox["handled"].astype(str) != "True"] if len(inbox) else inbox
    k = st.columns(6)
    k[0].metric("Open requests", f"{len(open_r)}")
    if ex_state.get("running"):
        k[1].metric("People waiting", f"{exercise.people_remaining(ex_state, open_r):,}"
                    + (f" of {int(pd.to_numeric(open_r['people'], errors='coerce').fillna(0).sum()):,}" if len(open_r) else ""),
                    "pickup still owed")
    else:
        k[1].metric("People waiting", f"{int(pd.to_numeric(open_r['people'], errors='coerce').fillna(0).sum()) if len(open_r) else 0:,}")
    k[2].metric("Critical open", f"{int((open_r['urgency'] == 'critical').sum()) if len(open_r) else 0}")
    k[3].metric("Unread texts (sim)", f"{len(unhandled)}")
    cap = pd.to_numeric(shel["capacity"], errors="coerce")
    hc = pd.to_numeric(shel["headcount"], errors="coerce").fillna(0)
    k[4].metric("Shelter space free", f"{int((cap - hc).clip(lower=0).sum()):,}" if cap.notna().any() else "—",
                f"{int((shel['status'] == 'open').sum())} open · {int(cap.isna().sum())} unknown cap.")
    k[5].metric("Units available", f"{int((res['status'] == 'available').sum()) if len(res) else 0}",
                f"of {len(res)} registered")

    tabs = st.tabs(["🚨 Requests & dispatch", "📱 Messages (simulated)", "🏠 Shelters", "🚤 Resources",
                    "❄️ Cooling", "📍 Nearest services", "📒 Directory"])

    # ================================================================ requests
    with tabs[0]:
        with st.form("rescue_req", clear_on_submit=True):
            st.markdown("**Log a request** (call, SMS, Facebook post, barangay radio…)")
            a1, a2, a3 = st.columns(3)
            r_b = a1.selectbox("Barangay", sorted(L.brgy["barangay"].tolist()))
            r_n = a2.number_input("People needing help", 1, 500, 4)
            r_u = a3.selectbox("Urgency", ["critical", "high", "normal"], index=1,
                               help="critical = life at risk now (rooftop, rising water, medical emergency)")
            b1, b2 = st.columns(2)
            r_need = b1.selectbox("Need", list(rsp.NEEDS.keys()))
            r_c = b2.text_input("Contact number / name (optional)")
            r_note = st.text_input("Where exactly (sitio, street, landmark)")
            if st.form_submit_button("Log request", type="primary"):
                a = _anchor(r_b)
                sug = rsp.suggest_responder(L, a["lat"], a["lon"], r_need, W_r, r_u) if a else None
                rid = rsp.add_request(r_b, r_n, r_need, r_u, r_c, r_note, sug["name"] if sug else "", drill=drill)
                st.session_state["_resp_toast"] = f"Request {rid} logged" + (f" · suggested: {sug['name']}" if sug else "")
                st.rerun()

        reqs = rsp.load_requests()
        if len(reqs):
            st.markdown("**Queue** — work the top row down: set status, then save. Times and sources stay in "
                        "the CSV for the debrief.")
            ed = st.data_editor(
                reqs, hide_index=True, use_container_width=True, key="req_editor",
                column_config={"barangay": st.column_config.TextColumn("Barangay", disabled=True),
                               "people": st.column_config.NumberColumn("People", min_value=1, max_value=500),
                               "need": st.column_config.TextColumn("Need", disabled=True),
                               "urgency": st.column_config.SelectboxColumn("Urgency", options=["critical", "high", "normal"]),
                               "contact": st.column_config.TextColumn("Contact"),
                               "location_note": st.column_config.TextColumn("Where exactly"),
                               "status": st.column_config.SelectboxColumn("Status", options=rsp.STATUSES),
                               "assigned_to": st.column_config.TextColumn("Assigned unit"),
                               # bookkeeping stays in the CSV (debrief + scoring read these)
                               "id": None, "logged_at": None, "source": None, "drill": None, "received_at": None,
                               "assigned_at": None, "resolved_at": None, "updated_at": None})
            if st.button("💾 Save queue changes", key="save_q"):
                latest = rsp.load_requests()
                before = latest.set_index("id")["status"]
                ed = rsp.stamp_status_changes(_merge_edits("req_editor", reqs, latest, "id"), latest)
                rsp.save_requests(ed)
                for _, r in ed.iterrows():
                    if r["status"] == "resolved" and before.get(r["id"]) != "resolved":
                        ops.release_resources_for(r["id"])
                st.toast("Queue saved")
                st.rerun()

            st.markdown("---")
            d1, d2 = st.columns([1.2, 1])
            with d1:
                st.markdown("**Dispatch**")
                _open = reqs[reqs["status"] != "resolved"].copy()
                # unassigned (new) first, then by urgency; already-serving requests last so the queue
                # keeps visible context without ever putting a resolved job back in the picker
                _urg = _open["urgency"].map({"critical": 0, "high": 1, "normal": 2}).fillna(3)
                _open["_o"] = (_open["status"] != "new").astype(int) * 10 + _urg
                open_ids = _open.sort_values(["_o", "logged_at"])["id"].tolist()
            if not open_ids:
                open_ids = reqs[reqs["status"] != "resolved"]["id"].tolist() or [
                    r["id"] for _, r in reqs.iterrows() if not (r.get("assigned_at") or r.get("resolved_at"))]
            if open_ids:
                pick = st.selectbox("Request to dispatch (unassigned · critical first)", open_ids, key="disp_pick",
                                    format_func=lambda r: f"{r} · " + " · ".join(
                                        reqs[reqs["id"] == r][["status", "urgency", "barangay"]].iloc[0].astype(str)))
                rq = reqs[reqs["id"] == pick].iloc[0].to_dict()
                a = _anchor(rq["barangay"])
                sug = rsp.suggest_responder(L, a["lat"], a["lon"], rq["need"], W_r, rq["urgency"]) if a else None
                if sug:
                    st.markdown(f"Suggested facility: **{sug['name']}** ({sug['service']}) · "
                                f"{sug['distance_m'] / 1000:.1f} km · site is **{sug['state']}**.")
                if rq["need"] == "🏠 Shelter space" and a:
                    sp = ops.shelter_with_space(L, a["lat"], a["lon"], W_r, int(rq["people"] or 1))
                    st.markdown(f"Shelter with space: **{sp['name']}** · {sp['free']} free · {sp['distance_m'] / 1000:.1f} km"
                                if sp else "No OPEN shelter with known free space — update the 🏠 Shelters board.")
                if (HIr or 0) >= 42 and rq["need"] in ("🩹 Medical", "🍚 Food / water") and a:
                    nc = heat.nearest_cooling(L, a["lat"], a["lon"], need=int(rq["people"] or 1))
                    st.markdown(
                        f"☀️ **Heat on scene ({cat_r}):** pair this run with water and a shaded rest stop — "
                        + (f"nearest open cooling point **{nc['name']}** ({nc['distance_m'] / 1000:.1f} km, "
                           f"{int(nc['free']) if nc.get('free') is not None else 'room unknown'} free)"
                           if nc else "no cooling point is registered yet — open one on the 🏠 Cooling board."))
                msg = rsp.dispatch_message(rq, sug, PREFS.get("lang", "English"))
                st.code(msg, language=None)
            with d2:
                if not open_ids:
                    st.caption("Nothing to dispatch: the queue is empty or fully resolved. "
                               "Log a request above, or 🎲 simulate incoming help texts.")
                else:
                    avail = res[res["status"] == "available"] if len(res) else res
                    st.markdown("**Assign a unit**")
                    if len(avail):
                        feasible, blocked = avail, []
                        if ex_state.get("running"):
                            _h = exercise.sim_hour(ex_state)
                            _W = exercise.water_at(L, ex_state["story"], _h)
                            ok_rows = []
                            for _, _u in avail.iterrows():
                                ok, reason = exercise.can_serve(L, _u["type"], rq["barangay"], _W)
                                (ok_rows if ok else blocked).append(_u if ok else (_u, reason))
                            if ok_rows:
                                feasible = pd.DataFrame(ok_rows)
                            if blocked:
                                st.caption("Ineligible at this water level "
                                           + (f"(+{_W:.2f} m): " if _W > 0 else "(dry streets): ")
                                           + "; ".join(f"{u['unit_id']} ({u['type']}) — {why.split(' — ')[-1]}"
                                                       for u, why in blocked))
                        if len(feasible):
                            unit = st.selectbox("Available unit", feasible["unit_id"].tolist(), key="assign_unit",
                                                format_func=lambda u: f"{u} · " + " · ".join(
                                                    feasible[feasible["unit_id"] == u][["type", "name", "location"]].iloc[0].astype(str)))
                            if st.button("Assign to " + pick, key="assign_btn", use_container_width=True):
                                if ex_state.get("running"):
                                    ok, det = exercise.assign(L, ex_state, unit, pick)
                                else:
                                    ops.assign_resource(unit, pick)
                                    df = rsp.load_requests()
                                    new = df.copy()
                                    new.loc[new["id"] == pick, ["status", "assigned_to"]] = ["assigned", unit]
                                    rsp.save_requests(rsp.stamp_status_changes(new, df))
                                    ok, det = True, f"{unit} assigned to {pick}"
                                if ok:
                                    st.session_state.pop("disp_pick", None)   # move on to the next waiting request
                                st.toast(det)
                                st.rerun()
                        else:
                            st.caption("No eligible unit at this water level — send a boat, or wait for the water to drop.")
                    else:
                        st.caption("No units marked available — register boats/trucks in 🚤 Resources.")
                    st.markdown("**Simulate dispatch message**")
                    orgs = rsp.load_directory()["organisation"].tolist()
                    to = st.selectbox("To (simulated)", orgs, key="disp_to")
                    if st.button("📤 Simulate send", key="disp_send", use_container_width=True):
                        sms.simulate_send(to, msg, purpose=f"dispatch:{pick}")
                        st.toast("Logged as simulated — nothing was sent")

            miss = (ex_state.get("missions") or {})
            if miss:
                with st.expander(f"🚤 {len(miss)} unit(s) on mission", expanded=True):
                    rows = []
                    for uid, m in miss.items():
                        eta = {"out": m["eta_out"], "back": m.get("eta_back"), "home": m.get("eta_home")}.get(m["phase"], 0)
                        doing = {"out": "en route to scene", "back": "carrying to safety",
                                 "home": "returning to base"}[m["phase"]]
                        deliv = f" · {m['delivered']}/{m['people']} delivered" if m.get("cap") else ""
                        rows.append(f"**{m['unit_name']}** → {m['req']} · {doing} · ETA h{eta:.1f}"
                                    f" · {m['km']} km{deliv}")
                    st.markdown("  \n".join(rows))
                    st.caption("Units travel on the storm clock; each trip carries the unit's capacity. "
                               "Requests auto-resolve when everyone is delivered.")

            try:
                import folium
                from streamlit_folium import st_folium
                fm = folium.Map(location=(16.05, 120.34), zoom_start=13, tiles=None)
                folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(fm)
                folium.TileLayer(tiles=mapfilm.ESRI_SAT[0], attr=mapfilm.ESRI_SAT[1], name="satellite").add_to(fm)
                if W_r > 0:
                    import base64 as _b64r
                    _png, _ = depth_overlay_png(W_r, 1.5)
                    _bb = kit.grid_bounds_4326(L)
                    folium.raster_layers.ImageOverlay(image="data:image/png;base64," + _b64r.b64encode(_png).decode(),
                                                      bounds=[[_bb[1], _bb[0]], [_bb[3], _bb[2]]], opacity=0.5,
                                                      name=f"flood now (+{W_r:.2f} m)").add_to(fm)
                scol = {"new": "#dc2626", "acknowledged": "#f97316", "assigned": "#eab308", "en route": "#2563eb",
                        "resolved": "#16a34a"}
                for _, r in reqs.iterrows():
                    a = _anchor(r["barangay"])
                    if a is None:
                        continue
                    folium.CircleMarker([a["lat"], a["lon"]], radius=7 + min(int(r["people"] or 1), 40) / 3,
                                        color="white", weight=2, fill=True, fill_color=scol.get(r["status"], "#666"),
                                        fill_opacity=0.95,
                                        tooltip=f"{r['id']} · {r['status']} · {r['barangay']} · {r['people']} people · "
                                                f"{r['need']} · {r['urgency']} · unit: {r['assigned_to'] or '—'}").add_to(fm)
                for _, sh_ in shel[shel["status"] == "open"].iterrows():
                    folium.Marker([float(sh_["lat"]), float(sh_["lon"])], tooltip=f"OPEN shelter: {sh_['name']}",
                                  icon=folium.Icon(color="green", icon="home", prefix="fa")).add_to(fm)
                for sv in rsp.services(L):
                    if sv["service"] == "🏥 Hospital":
                        heat.health_marker([sv["lat"], sv["lon"]],
                                           tooltip=f"{sv['service']}: {sv['name']}").add_to(fm)
                    elif sv["service"] in ("🚒 Fire station (BFP)", "🚓 Police (PNP)"):
                        folium.CircleMarker([sv["lat"], sv["lon"]], radius=4, color=rsp.SERVICE_COLORS[sv["service"]],
                                            fill=True, fill_opacity=0.9, tooltip=f"{sv['service']}: {sv['name']}").add_to(fm)
                for _, c_ in heat.load_cooling().iterrows():
                    if str(c_.get("status")) != "open":
                        continue
                    try:
                        cla, clo = float(c_["lat"]), float(c_["lon"])
                    except Exception:
                        continue
                    heat.cool_ring([cla, clo]).add_to(fm)
                    heat.cool_marker([cla, clo],
                                     tooltip=f"❄ cooling point: {c_['name']} · open · faint dotted ring = 2.5 km"
                                             + heat.cool_note(c_)).add_to(fm)
                folium.LayerControl().add_to(fm)
                st_folium(fm, height=440, use_container_width=True, returned_objects=[], key="req_map")
                st.caption("Big circles = requests (red new · orange acknowledged · yellow assigned · blue en route · "
                           "green resolved). Green houses = open shelters · green pin = hospital · red/blue dots = "
                           "fire, police · ❄ + faint ring = open cooling point and its 2.5 km walk.")
            except Exception as e:
                st.info(f"Map unavailable ({type(e).__name__}).")
        else:
            st.info("No requests yet. Log one above, or press 🎲 Simulate 6 incoming help texts.")

    # ================================================================ SMS
    with tabs[1]:
        i1, i2 = st.columns([1.3, 1])
        with i1:
            st.markdown("**Simulated inbox** — texts like `HELP PANTAL 6 BOAT` or `SAKLOLO Carael 3 gamot` become requests")
            inbox = sms.load_log(sms.INBOX)
            pending = inbox[inbox["handled"].astype(str) != "True"] if len(inbox) else inbox
            for _, m in pending.head(12).iterrows():
                parsed = sms.parse_request(m["body"], L.brgy["barangay"].tolist())
                with st.container(border=True):
                    st.markdown(f"**{m['sender']}** · {m['at']}  \n> {m['body']}")
                    if parsed and parsed["barangay"]:
                        st.caption(f"Reads as: {parsed['barangay']} · {parsed['people']} people · {parsed['need']} · {parsed['urgency']}")
                    cc1, cc2 = st.columns(2)
                    cc1.button("➕ Create request", key=f"mk_{m['msg_id']}", on_click=_inbox_to_request,
                               args=(m["msg_id"], m["sender"], m["body"], True), disabled=not (parsed and parsed["barangay"]))
                    cc2.button("✓ Dismiss", key=f"hd_{m['msg_id']}", on_click=sms.mark_handled, args=(m["msg_id"],))
            if len(pending) > 12:
                st.caption(f"Showing the 12 oldest of {len(pending)} pending — handle or dismiss the rest as you go.")
            if not len(pending):
                st.caption("Inbox empty — use 🎲 above, or the 'Write your own simulated text' box below.")
            with st.expander("Write your own simulated text"):
                t_from = st.text_input("From", "Simulated resident", key="sim_from")
                t_body = st.text_input("Message", "HELP PANTAL 6 BOAT nasa bubong", key="sim_body")
                if st.button("Drop into inbox", key="sim_btn"):
                    sms.simulate_inbound(t_from, t_body)
                    st.rerun()
        with i2:
            st.markdown("**Simulated alert broadcast**")
            tpl = {
                "Evacuate now (TL)": "BABALA: Lumikas na sa pinakamalapit na evacuation center. Dalhin ang gamot at ID.",
                "Evacuate now (EN)": "WARNING: Evacuate now to the nearest evacuation center. Bring medicines and IDs.",
                "Pre-emptive (TL)": "PAALALA: Inaasahang tataas ang baha sa susunod na 12 oras. Ihanda ang go-bag.",
                "All clear (TL)": "BALITA: Humupa na ang baha. Mag-ingat sa putik at kuryente.",
            }
            t_pick = st.selectbox("Template", list(tpl.keys()), key="bc_tpl")
            body = st.text_area("Message", tpl[t_pick], key=f"bc_body_{t_pick}", height=100)
            st.caption(f"{len(body)} characters · {1 if len(body) <= 160 else (len(body) + 152) // 153} SMS segment(s)")
            bc_b = st.multiselect("Barangays", ["ALL"] + sorted(L.brgy["barangay"].tolist()),
                                  default=PREFS.get("pilot") or ["Pantal"], key="bc_brgy")
            if st.button("📣 Simulate broadcast", key="bc_send", use_container_width=True):
                n = sms.simulate_broadcast(bc_b, body)
                sms.simulate_send(", ".join(bc_b), body, purpose="alert (area)")
                st.toast(f"Logged as simulated for {', '.join(bc_b)} ({n} practice contacts) — nothing sent")
        with st.expander("📜 Simulated message log"):
            ob = sms.load_log(sms.OUTBOX)
            if len(ob):
                st.dataframe(ob.head(50), hide_index=True, use_container_width=True)
            else:
                st.caption("Nothing logged yet.")

    with tabs[2]:
        st.markdown("**Evacuation centre board.** Every centre starts **CLOSED** on purpose — a school being a school "
                    "is not a shelter until the city opens it. Keeping one open is a status you set and the board "
                    "keeps:")
        with st.expander("📖 How this board works — opening, filling, closing", expanded=False):
            st.markdown(
                """
                1. **To open a centre:** click its **Status** cell in the table and choose `open`
                   (or use the quick-opener below for a whole practice set in one click).
                2. **Capacity:** type the CDRRMO's official figure into *capacity* (blank = unknown — the board will
                   never mark an unknown-capacity centre full).
                3. **In a timed exercise:** every successful boat delivery lands its passengers automatically at the
                   nearest OPEN centre with space — *headcount* rises by itself and you watch the board fill.
                4. **Full:** a centre auto-marks `full` the moment headcount reaches capacity; the next delivery is
                   routed to the next centre. You can also set it by hand.
                5. **Unsafe:** the *evacuation centre loses power* complication will mark an open centre `unsafe` —
                   deliveries stop going there until you reopen it.
                6. **Closed again:** after the exercise, reset with 🧹 Reset simulation at the top of the page
                   (all headcounts clear; statuses stay as you left them).
                """)
        sh = ops.load_shelters(L)
        occ = ops.occupancy(sh)
        hauling = sum(m.get("load") or 0 for m in (ex_state.get("missions") or {}).values() if m["phase"] == "back")
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Open", int((sh["status"] == "open").sum()))
        s2.metric("Full", int((sh["status"] == "full").sum()))
        s3.metric("Evacuees sheltered", f"{int(pd.to_numeric(sh['headcount'], errors='coerce').fillna(0).sum()):,}")
        s4.metric("Capacity known", f"{int(pd.to_numeric(sh['capacity'], errors='coerce').notna().sum())} / {len(sh)}")
        s5.metric("Aboard boats now", f"{hauling}" if hauling else "0", "en route to shelters" if hauling else "no boats en route")
        show_only = st.checkbox("Show open / full only", value=False, key="sh_only")
        view = sh[sh["status"].isin(["open", "full"])] if show_only else sh
        with st.expander("⚡ Quick practice opener"):
            cc0, cc1, cc2, cc3 = st.columns([1.3, 0.7, 0.8, 1.1])
            qp_b = cc0.selectbox("Near barangay", sorted(L.brgy["barangay"].tolist()), index=0, key="sh_qp_b")
            n_op = cc1.number_input("Open nearest", 1, 20, 3, key="sh_qp_n")
            cap_q = cc2.number_input("capacity", 0, 5000, 120, key="sh_qp_cap")
            if cc3.button("🏫 Open them (practice only)", use_container_width=True,
                          help="Sets status=open with a round practice capacity for the centres nearest the chosen "
                               "barangay. Real capacities come from the CDRRMO list — blank them before any "
                               "real-world use."):
                full = ops.load_shelters(L)
                a = _anchor(qp_b)
                if a:
                    d = (full["lat"].astype(float) - a["lat"]) ** 2 + ((full["lon"].astype(float) - a["lon"]) * 0.96) ** 2
                    full.loc[d.nsmallest(int(n_op)).index, "status"] = "open"
                    full.loc[d.nsmallest(int(n_op)).index, "capacity"] = str(int(cap_q))
                    ops.save_shelters(full)
                    st.toast(f"{int(n_op)} centres opened near {qp_b} (practice capacity {int(cap_q)})")
                    st.rerun()
                else:
                    st.caption(f"No anchor for {qp_b} — open centres by hand in the table.")
        sh_cap_max = int(max(120, pd.to_numeric(sh["capacity"], errors="coerce").max() or 120))
        sed = st.data_editor(view, hide_index=True, use_container_width=True, key="sh_ed", height=360,
                             column_config={"status": st.column_config.SelectboxColumn("status", options=ops.SHELTER_STATUS),
                                            "shelter_id": st.column_config.TextColumn(disabled=True),
                                            "lat": None, "lon": None, "updated_at": None,
                                            "elev_m": st.column_config.NumberColumn("ground m", disabled=True, format="%.1f"),
                                            "headcount": st.column_config.ProgressColumn("headcount", min_value=0,
                                                                                          max_value=sh_cap_max,
                                                                                          format="%d evac."),
                                            "capacity": st.column_config.NumberColumn("capacity", min_value=0, step=10)})
        if st.button("💾 Save shelter board", key="save_sh"):
            full = _merge_edits("sh_ed", view, ops.load_shelters(L), "shelter_id").set_index("shelter_id")
            capn = pd.to_numeric(full["capacity"], errors="coerce")
            hcn = pd.to_numeric(full["headcount"], errors="coerce").fillna(0)
            full.loc[(capn > 0) & (hcn >= capn) & (full["status"] == "open"), "status"] = "full"
            ops.save_shelters(full.reset_index())
            st.toast("Shelter board saved (auto-marked full where headcount ≥ capacity)")
            st.rerun()
        try:
            import folium
            from streamlit_folium import st_folium
            fm = folium.Map(location=(16.05, 120.34), zoom_start=13, tiles=None)
            folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1]).add_to(fm)
            for i, r in sh.iterrows():
                o = occ.iloc[i]
                col = {"open": "#16a34a" if (pd.isna(o) or o < 0.8) else "#f59e0b", "full": "#dc2626",
                       "unsafe": "#7f1d1d"}.get(r["status"], "#9ca3af")
                flooded = float(r["elev_m"] or 0) < W_r - 0.15
                folium.CircleMarker([float(r["lat"]), float(r["lon"])], radius=6, color="#1f2937" if flooded else "white",
                                    weight=2, fill=True, fill_color=col, fill_opacity=0.95,
                                    tooltip=f"{r['name']} · {r['status']} · {r['headcount']}/{r['capacity'] or '?'}"
                                            + (" · ⚠ site floods at this water level" if flooded else "")).add_to(fm)
            st_folium(fm, height=420, use_container_width=True, returned_objects=[], key="sh_map")
            st.caption("Green open · amber ≥80% full · red full · dark red unsafe · grey closed. "
                       "Dark outline = the site itself floods at the assumed water level.")
        except Exception as e:
            st.info(f"Map unavailable ({type(e).__name__}).")

    # ================================================================ resources
    with tabs[3]:
        st.markdown("**Response resources** — boats, trucks, ambulances, teams. Add rows for each unit. During a "
                    "timed exercise these units travel at the speeds below and carry the listed capacity per trip.")
        rs = ops.load_resources()
        phy = pd.DataFrame([dict(unit_type=t, **{"speed km/h": p["speed_kmh"], "carries/trip": p["capacity"],
                                                 "max water at request (m)": (p["max_water_m"]
                                                                              if p.get("max_water_m") is not None
                                                                              else float("nan"))})
                            for t, p in ops.UNIT_PHYSICS.items()])
        with st.expander("📐 Unit physics used by the simulator"):
            st.dataframe(phy, hide_index=True, use_container_width=True)
            st.caption("Practice values, clearly not engineering data: straight-line distance ÷ speed gives the ETA; "
                       "vehicles refuse requests deeper than their max water (blank = boats, any water); "
                       "support units (carries 0) make one delivery round trip. Real speeds depend on debris, "
                       "current and road state.")
        ustat = ex_state.get("unit_stats") or {}
        if ustat:
            stat_df = pd.DataFrame([dict(unit=u, trips=s.get("trips", 0), people=s.get("people", 0))
                                    for u, s in ustat.items()])
            with st.expander(f"📊 This exercise so far — {int(stat_df['people'].sum())} people moved in "
                             f"{int(stat_df['trips'].sum())} trips"):
                st.dataframe(stat_df, hide_index=True, use_container_width=True)
        if len(rs):
            cnt = rs.groupby(["type", "status"]).size().unstack(fill_value=0)
            st.dataframe(cnt, use_container_width=True)
        red = st.data_editor(rs, num_rows="dynamic", hide_index=True, use_container_width=True, key="res_ed",
                             column_config={"type": st.column_config.SelectboxColumn("type", options=ops.RESOURCE_TYPES),
                                            "status": st.column_config.SelectboxColumn("status", options=ops.RESOURCE_STATUS),
                                            "location": st.column_config.SelectboxColumn("location", options=sorted(L.brgy["barangay"].tolist())),
                                            "assigned_request": st.column_config.TextColumn("On job", disabled=True),
                                            "updated_at": None})
        if st.button("💾 Save resources", key="save_res"):
            red = _merge_edits("res_ed", rs, ops.load_resources(), "unit_id").fillna("")
            nums = [int(x[1:]) for x in red["unit_id"].astype(str) if x[:1] == "U" and x[1:].isdigit()]
            nxt = max(nums, default=0) + 1
            for i in red.index:
                if not str(red.at[i, "unit_id"]).strip():
                    red.at[i, "unit_id"] = f"U{nxt:03d}"
                    nxt += 1
                if not str(red.at[i, "status"]).strip():
                    red.at[i, "status"] = "available"
            red["updated_at"] = datetime.now().isoformat(timespec="minutes")
            ops.save_resources(red)
            st.toast("Resources saved")
            st.rerun()

    # ================================================================ cooling (heat relief points)
    with tabs[4]:
        st.markdown("**Cooling centers** — where the hot go when shade is not enough. Managed like the "
                    "shelter board; the Deck's cooling register edits the same list.")
        cst = heat.cooling_stats()
        q1, q2, q3 = st.columns(3)
        q1.metric("Open", cst["open"])
        q2.metric("Full", cst["full"])
        q3.metric("Capacity known", cst["capacity_known"])
        cooling_empty_state("resp_cool_tab_seed", where="this cooling board", style="info")
        cl1, cl2 = st.columns([1.5, 1])
        with cl1:
            nb2 = st.selectbox("Find relief for", sorted(L.brgy["barangay"].tolist()),
                               index=sorted(L.brgy["barangay"].tolist()).index("Pantal"), key="cool_near_b")
            a2 = _anchor(nb2)
            if a2 is None:
                st.info("No anchor for this barangay.")
            else:
                nc = heat.nearest_cooling(L, a2["lat"], a2["lon"])
                if nc is None:
                    st.warning("No cooling center registered — register one in the Deck's ❄️ Cooling register "
                               "or add a row below (status = open).")
                else:
                    full2 = nc["free"] is not None and nc["free"] <= 0
                    st.metric("Nearest open relief", nc["name"][:40],
                              f"{'FULL — next closest?' if full2 else str(nc['free']) + ' free' if nc['free'] is not None else 'space unknown'} · {nc['distance_m'] / 1000:.1f} km")
        with cl2:
            st.caption(f"Board: {cst['open']} open ({heat.practice_count()} practice candidates) · "
                       f"{cst['full']} full · {cst['closed']} closed "
                       "(same list as the Deck). Edit rows here or there — it is one table.")
        ced2 = st.data_editor(heat.load_cooling(), num_rows="dynamic", hide_index=True, use_container_width=True,
                              key="cool_ed2",
                              column_config={"kind": st.column_config.SelectboxColumn("kind", options=heat.COOL_KINDS),
                                             "status": st.column_config.SelectboxColumn("status", options=heat.COOL_STATUS),
                                             "center_id": st.column_config.TextColumn(disabled=True),
                                             "source": st.column_config.TextColumn(disabled=True),
                                             "lat": st.column_config.NumberColumn("latitude", format="%.5f"),
                                             "lon": st.column_config.NumberColumn("longitude", format="%.5f"),
                                             "updated_at": None})
        if st.button("💾 Save cooling centers", key="save_cool2"):
            cx = ced2.copy()
            cx = cx[cx["name"].astype(str).str.strip() != ""]
            nums = [int(x[1:]) for x in cx["center_id"].astype(str) if x[:1] == "C" and x[1:].isdigit()]
            nx = max(nums, default=0) + 1
            for i in cx.index:
                if not str(cx.at[i, "center_id"]).strip():
                    cx.at[i, "center_id"] = f"C{nx:03d}"
                    nx += 1
                if not str(cx.at[i, "status"]).strip():
                    cx.at[i, "status"] = "closed"
            heat.save_cooling(cx)
            st.toast("Cooling board saved")
            st.rerun()

    # ================================================================ nearest services
    with tabs[5]:
        nb_list = sorted(L.brgy["barangay"].tolist())
        nb = st.selectbox("Community", nb_list, index=nb_list.index("Pantal"), key="near_b")
        a = _anchor(nb)
        if a is None:
            st.info("No map anchor for this barangay.")
        else:
            near = rsp.nearest_services(L, a["lat"], a["lon"], W_r, per_type=3)
            nc1, nc2 = st.columns([1.4, 1])
            with nc1:
                try:
                    import base64 as _b
                    import folium
                    from streamlit_folium import st_folium
                    fm = folium.Map(location=(a["lat"], a["lon"]), zoom_start=14, tiles=None)
                    folium.TileLayer(tiles=mapfilm.ESRI_SAT[0], attr=mapfilm.ESRI_SAT[1], name="satellite").add_to(fm)
                    folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(fm)
                    if W_r > 0:
                        png, _ = depth_overlay_png(W_r)
                        bb = kit.grid_bounds_4326(L)
                        folium.raster_layers.ImageOverlay(
                            image="data:image/png;base64," + _b.b64encode(png).decode(),
                            bounds=[[bb[1], bb[0]], [bb[3], bb[2]]], opacity=0.55,
                            name=f"flood depth (+{W_r:.2f} m)").add_to(fm)
                    folium.Marker([a["lat"], a["lon"]], tooltip=f"{nb} (community)",
                                  icon=folium.Icon(color="orange", icon="home", prefix="fa")).add_to(fm)
                    for _, r in near.iterrows():
                        col = rsp.SERVICE_COLORS.get(r["service"], "#444")
                        folium.PolyLine([[a["lat"], a["lon"]], [r["lat"], r["lon"]]], color=col, weight=1.5,
                                        dash_array="4 6", opacity=0.7).add_to(fm)
                        folium.CircleMarker([r["lat"], r["lon"]], radius=8, color="white", weight=2, fill=True,
                                            fill_color=col, fill_opacity=1,
                                            tooltip=f"{r['service']}: {r['name']} · {r['distance_m'] / 1000:.1f} km · {r['state']}").add_to(fm)
                    folium.LayerControl().add_to(fm)
                    st_folium(fm, height=500, use_container_width=True, returned_objects=[], key="near_map")
                except Exception as e:
                    st.info(f"Map unavailable ({type(e).__name__}).")
            with nc2:
                show = near[["service", "name", "distance_m", "state"]].copy()
                show["distance"] = (show["distance_m"] / 1000).round(2).astype(str) + " km"
                st.dataframe(show[["service", "name", "distance", "state"]], hide_index=True, use_container_width=True, height=500)
            st.caption("Straight-line distances; 'state' = flood depth at the facility at this water level.")

    # ================================================================ directory
    with tabs[6]:
        st.markdown('<div class="cs-banner"><b>Reference only.</b> Public emergency numbers as published on the official '
                    'City Government of Dagupan website (source column). The simulator never calls or texts them — in a '
                    'real emergency, call these offices directly or <b>911</b>. Landlines use area code (075).</div>',
                    unsafe_allow_html=True)
        dirdf = rsp.load_directory()
        ded = st.data_editor(dirdf, hide_index=True, use_container_width=True, num_rows="dynamic", key="dir_editor",
                             column_config={"confirmed_by_call": None, "sms_dispatch_ok": None,
                                            "source": st.column_config.TextColumn("source", width="medium")})
        if st.button("💾 Save directory", key="save_dir"):
            rsp.save_directory(ded)
            st.toast("Directory saved")
            st.rerun()
        quick = dirdf[(dirdf["mobile"].str.len() > 0) | (dirdf["landline_075"].str.len() > 0)]
        if len(quick):
            st.markdown("**Published emergency numbers** " + " · ".join(
                f"{r['organisation']}: **{r['mobile'] or r['landline_075']}**"
                for _, r in quick.head(12).iterrows()))


# ================================================================= METHODS

@st.fragment
def _fragment_methods():
        st.title("ℹ️ Methods, Sources & Roadmap")
        with st.expander("Data provenance (retrieved Oct 3, 2026)"):
            st.markdown(
                """
                    | Layer | Source | License |
                    |---|---|---|
                    | Elevation, flood depths | Copernicus GLO-30 (ESA/EEA) | free & open |
                    | Flood-susceptibility index | ClimateShield weighted proxy (elev 45% · river 25% · coast 15% · flatness 15%) | MIT (this repo) |
                    | Population grid | WorldPop 2020 (100 m), PSA-calibrated | CC-BY 4.0 |
                    | Barangay census | PSA 2020 CPH via OCHA HDX | open |
                    | Roads, rivers, coast, facilities, buildings | OpenStreetMap | ODbL |
                    | 45-year climate & heat index | NASA POWER (MERRA-2) + ECMWF ERA5 cross-check | open / CC-BY 4.0 |
                    | Live conditions | Open-Meteo real-time API (fallback: MET Norway) | CC-BY 4.0 |
                    | Hourly rain (past 24 h + 7-day) | Open-Meteo | CC-BY 4.0 |
                    | Nearest station observations | aviationweather.gov METAR, Laoag RPLI + Clark RPLC (no Dagupan METAR station exists) | US public domain |
                    | Agno dam levels + basin status | PAGASA public flood page (parsed table, row arithmetic cross-checked) | PH public domain |
                    | Heat protocol rules | PAGASA bands; DepEd Order No. 37, s. 2022; DepEd 4 Apr 2024 ADM statement; DRAFT 2026 ≥40°C auto-suspension proposal (not policy); DOLE Labor Advisory No. 08, s. 2023 | PH public domain |
                    """
            )
        with st.expander("Model validation — Aug 2026 habagat vs CDRRMO SitRep No. 15", expanded=False):
            st.caption(f"Observed facts from one official source: {validation.OBSERVED['source']}. The model is not "
                       "re-tuned here — matches and misses are both reported. Read the 'reading' column before "
                       "quoting a number from this app.")
            vtable, vsum = validation.checks(L)
            st.dataframe(vtable, use_container_width=True, hide_index=True,
                         column_config={"check": st.column_config.TextColumn(width="medium"),
                                        "model": st.column_config.TextColumn(width="small"),
                                        "observed": st.column_config.TextColumn(width="medium"),
                                        "reading": st.column_config.TextColumn(width="large")})
            st.markdown(f"**Bottom line:** at the sitrep date the model now shows "
                         f"**{vsum['poly_late']}/31** barangays with water vs **23** reported still flooded — "
                         f"the closest like-for-like comparison so far (the old anchor-window method gave 4–8). "
                         f"At the peak it over-counts barangays ({vsum['poly_peak']}/31 — expected, the sitrep "
                         f"is a recession snapshot) and matches people well: "
                         f"**{vsum['pop_peak']:,.0f}** residents in flood zones vs 90,015 reported "
                         f"({100 * vsum['ratio']:.0f}%). Keep reading 'drainage timing' with care: core "
                         "points still drain before outlying houses do, and better elevation + a real "
                         "gauge feed remain the two upgrades that would tighten this further.")
        with st.expander("Calibration & honesty"):
            st.markdown(
                f"""
                    - Scenario water levels are **elevation percentiles** of active land
                      (Advisory→12% · Alert→30% · Calamity→45% · Extreme→65% of land flooded deeper than 15 cm), with the
                      Calamity class calibrated against the **Aug 2026 event** (23/31 barangays flooded per CDRRMO SitRep No. 15).
                    - **0 m plateau assumption:** GLO-30 records {100 * L.plateau_share:.0f}% of active land at exactly 0 m
                      (fishponds, wetlands). Within that plateau, cells are ordered by the flood-susceptibility index
                      (most susceptible floods first) and spread over 0–0.5 m, so scenario classes stay distinct.
                      A LiDAR elevation model (Methods → upgrade) replaces this assumption where it has coverage.
                    - *Correction (Oct 2026):* earlier versions inverted the percentile, so Advisory flooded more land than
                      Calamity. Fixed; all scenario numbers now rise with severity.
                    - **Real storm replays** (Command Deck → 🌩 tab) drive the same proxy model with *recorded* daily
                      rainfall (NASA POWER 1981–2026): a 6-day storage tank accumulates rain, and the stored water is
                      mapped to a flooded share of land through calibration anchors — Aug 2026 habagat ≈ the 45% Calamity
                      report, Pepeng 2009 ≈ the 65% Extreme class. "If the city had prepared" subtracts illustrative
                      drain/pump/evacuation benefits. Replays show real dates, not forecasts.
                    - Active-land footprint ({L.meta['active_land_km2']:.1f} km² of the official 44.47 km²) avoids counting
                      Lingayen Gulf municipal waters inside the OSM city polygon.
                    - WorldPop grid rescaled so city totals match PSA census; barangay impact = census × flooded
                      share of the barangay area. Boundaries: **{L.boundary_source}** — no public barangay polygons
                      exist for Dagupan (OSM admin check 2026-10-07), so the app ships interim anchor-Voronoi
                      neighborhoods, clearly labeled DERIVED on every map and swap-in ready: drop an official
                      `data/app_layers/brgy_boundaries.geojson` and run `python app/brgypoly.py`. Barangays with
                      too little area coverage fall back to the old 600 m anchor window (basis column in the
                      impact tables). Same-named place nodes outside the city are no longer used as anchors
                      ({len(L.re_anchored) if hasattr(L, 're_anchored') else 0} re-anchored/cleared at load).
                    - **Not a hydraulic model.** Countermeasure effects are clearly-labeled proxies for community
                      conversation, prioritization and drills.
                    - Official warnings: **PAGASA** (flood advisories, rainfall & TC signals, heat index categories) and the
                      **Dagupan CDRRMO**. When they speak, ClimateShield follows.
                    - Scenario time-lapses are **proxy physics** on the real terrain: water = scenario base + tide
                      + blocked-drain surcharge − pumps (+ optional upstream pulse), rising ~10 h then receding;
                      evacuation share follows the warning lead-time. Heat scenarios add an urban-heat offset per barangay
                      from urban flag + building density. All are labeled visualizations, not forecasts.
                    - **Terrain caveat:** Copernicus GLO-30 flattens Dagupan's fishpond/wetland belt and the gulf to
                      exactly 0 m (71% of the raw tile). Low barangays therefore flood together once water exceeds
                      +0.15 m; a LiDAR/IfSAR DEM from NAMRIA or DOST would sharpen every number here.
                    """
            )
        with st.expander("🗺️ Upgrade the elevation model (LiDAR / IfSAR DTM)"):
            st.markdown(f"**Current terrain:** {L.dem_source}")
            st.markdown("Copernicus GLO-30 flattens 62% of Dagupan's land to exactly 0 m. A bare-earth LiDAR DTM "
                        "(Phil-LiDAR / UP DREAM via the LiPAD portal, or NAMRIA IfSAR) would sharpen every flood number. "
                        "Upload a GeoTIFF in **EPSG:32651** (UTM 51N) or **EPSG:4326**; covered cells replace GLO-30.")
            up = st.file_uploader("Elevation GeoTIFF", type=["tif", "tiff"], key="dem_up")
            lab = st.text_input("Label / source", "Phil-LiDAR DTM", key="dem_lab")
            if up is not None and st.button("Import and merge", key="dem_go"):
                try:
                    rep = demimport.import_dem(L, up.getvalue(), lab)
                    st.success(f"Merged: {rep['coverage_pct']}% of land covered · zero-elevation cells "
                               f"{rep['old_zero_pct']}% → {rep['new_zero_pct']}% · median {rep['old_median']} → "
                               f"{rep['new_median']} m. Restart the app to apply. {rep['note']}")
                except Exception as e:
                    st.error(f"Import failed: {e}")
            if demimport.OVERRIDE.exists() and st.button("Remove imported elevation (back to GLO-30)", key="dem_rm"):
                demimport.remove_override()
                st.info("Removed — restart the app to apply.")
        with st.expander("📱 Take this to the field (phones & tablets)"):
            st.markdown(
                """
                    1. Connect your phone to the **same Wi-Fi** as this computer.
                    2. Scan the QR below (or type the address). The app opens in the browser.
                    3. Phone browser → ⋮ menu (Android) or Share (iPhone) → **Add to Home screen** —
                       ClimateShield then lives beside your other apps.
                    """
            )
            try:
                import socket as _sock
                import qrcode as _qr
                lan = _sock.gethostbyname(_sock.gethostname())
                url = f"http://{lan}:8501"
                _img = _qr.make(url)
                buf = __import__("io").BytesIO()
                _img.save(buf, format="PNG")
                cqr, ctxt = st.columns([1, 2.2])
                with cqr:
                    st.image(buf.getvalue(), width=190)
                with ctxt:
                    st.code(url, language=None)
                    st.caption("Same-Wi-Fi only. For barangay-hall access over the internet, follow DEPLOYING.md "
                               "to publish this on a URL with an access code. True offline operation inside a "
                               "no-signal evacuation center still needs a local server copy — see docs/PHONE_GUIDE.md.")
            except Exception as e:
                st.info(f"QR unavailable here ({type(e).__name__}). Type the address from the browser bar instead.")
        with st.expander("From notebook to platform — roadmap"):
            st.markdown(
                """
                    - **P1 done** — analysis notebook, watchlists, susceptibility rasters, command center v0.2
                      (kiosk/wall mode, clickable drill-downs) → v1.0 map time-lapse, route cards, heat scenarios.
                    - **P2 (crowd telemetry)** — logged reports → heatmap layer; validation against CDRRMO sitreps.
                    - **P3 (partnerships)** — LGU barangay boundaries; DPWH/PDRRMO Pantal river-gauge feed; CBMS
                      household vulnerability. Gauges convert the scenario simulator into a genuine now-cast.
                    - **P4 (anticipatory action)** — auto-triggers tied to PAGASA bulletins: banca pre-positioning,
                      water-respite stations, harvest-lift advisories for the fishpond belt.
                    """
            )
        st.markdown("Full registry: `docs/SOURCES.md` · analysis: `ClimateShield_Dagupan_Analysis.ipynb`")
        st.caption("ClimateShield-Dagupan is a community tool. It does not represent PAGASA, the City Government of "
                   "Dagupan, or any agency; treat all modeled numbers as planning estimates.")

if page == NAV[1]:
    _fragment_sim()

if page == NAV[2]:
    _fragment_heat()

if page == NAV[3]:
    _fragment_lab()

if page == NAV[4]:
    _fragment_tel()

if page == NAV[5]:
    _fragment_wlk()

if page == NAV[6]:
    st.button("Back to Command Deck", on_click=_nav_to, args=(NAV[0],), key="resp_back")
    st.title("🚑 Response & Dispatch")
    _fragment_exercise()
    _fragment_response()

if page == NAV[7]:
    _fragment_methods()

if page == NAV[8]:
    field.render(L)


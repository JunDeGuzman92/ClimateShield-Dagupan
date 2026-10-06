import io
import json
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
LAY = ROOT / "data" / "app_layers"
CR_CROWD = LAY / "crowd_reports.csv"
GAUGE = LAY / "pantal_gauge_log.csv"

SEVERITY = {
    "gutter-deep": 1, "ankle-deep": 2, "knee-deep (light vehicles risky)": 3,
    "waist-deep (impassable)": 4, "chest-deep+ (life-safety)": 5,
}
SEV_COLORS = {1: "#b5c94e", 2: "#ffd166", 3: "#f4a259", 4: "#e76f51", 5: "#9e2a2b"}
PHTZ = timezone(timedelta(hours=8))


def anchors_map(brgy_anchors):
    return {b["barangay"]: b["anchor"] for b in brgy_anchors if b.get("anchor")}


def crowd_pins(anchor_lookup, max_age_days=14, path=CR_CROWD):
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path, parse_dates=["logged_at"])
    except Exception:
        return []
    df = df[df["type"] == "flood depth"].sort_values("logged_at")
    now = pd.Timestamp.now(tz=PHTZ).tz_localize(None)
    df = df[(now - df["logged_at"]).dt.days <= max_age_days]
    out = []
    for brg, g in df.groupby("barangay"):
        last = g.iloc[-1]
        sev = SEVERITY.get(str(last.get("detail", "")), 2)
        a = anchor_lookup.get(brg)
        if not a:
            continue
        out.append({"lon": a["lon"], "lat": a["lat"], "barangay": brg, "sev": sev,
                    "when": pd.Timestamp(last["logged_at"]).strftime("%m-%d %H:%M"),
                    "detail": last.get("detail", ""), "n": len(g)})
    return out


def gauge_history(path=GAUGE):
    if not path.exists():
        return pd.DataFrame(columns=["logged_at", "level_m", "note"])
    return pd.read_csv(path, parse_dates=["logged_at"]).sort_values("logged_at")


def gauge_save(level_m, note, path=GAUGE):
    new = pd.DataFrame([[pd.Timestamp.now(tz=PHTZ).tz_localize(None).isoformat(timespec="minutes"),
                         float(level_m), note]],
                       columns=["logged_at", "level_m", "note"])
    if path.exists():
        pd.concat([new, gauge_history(path)]).to_csv(path, index=False)
    else:
        new.to_csv(path, index=False)


def gauge_class(level_m, alert=0.8, alarm=1.2, critical=1.5):
    if level_m is None:
        return ("no data yet", "#6b7280")
    if level_m >= critical:
        return ("CRITICAL — forced-evacuation protocol", "#9e2a2b")
    if level_m >= alarm:
        return ("ALARM — activate preemptive evacuation list", "#e76f51")
    if level_m >= alert:
        return ("ALERT — banca rosters prepare", "#f4a259")
    return ("MONITORING", "#5d8a3c")


def radar_map():
    import folium
    import urllib.request
    try:
        with urllib.request.urlopen("https://api.rainviewer.com/public/weather-maps.json", timeout=12) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    rinfo = d.get("radar", {})
    past = [(p["time"], "past") for p in rinfo.get("past", [])]
    nowcast = [(n["time"], "nowcast") for n in rinfo.get("nowcast", [])]
    if not past:
        return None
    host = d.get("host", "https://tilecache.rainviewer.com")
    m = folium.Map(location=[16.0432, 120.3342], zoom_start=8, tiles=None, max_bounds=True)
    folium.TileLayer(tiles=ESRI_GRAY[0], attr=ESRI_GRAY[1], name="map (Esri light)").add_to(m)
    frames = (past[-4:] + nowcast[-2:]) if nowcast else past[-6:]
    for i, (ts, kind) in enumerate(frames):
        when = datetime.fromtimestamp(ts, tz=PHTZ).strftime("%H:%M")
        folium.raster_layers.TileLayer(
            tiles=f"{host}/v2/radar/{ts}/256/{{z}}/{{x}}/{{y}}/2/1_1.png",
            attr="RainViewer", name=f"{kind} {when}",
            opacity=0.55, show=(i == len(frames) - 1 if nowcast else i == len(frames) - 1),
        ).add_to(m)
    latest_when = datetime.fromtimestamp(past[-1][0], tz=PHTZ).strftime("%H:%M")
    folium.Marker([16.0432, 120.3342], tooltip="Dagupan City",
                  icon=folium.Icon(color="darkblue", icon="anchor", prefix="fa")).add_to(m)
    return m, latest_when


LANGS = ["English", "Tagalog", "Pangasinan"]

T_TITLES = {
    "Command Deck": {"Tagalog": "Command Deck", "Pangasinan": "Command Deck"},
    "Flood Scenario Simulator": {"Tagalog": "Simulator ng Baha", "Pangasinan": "Simulator na Lames"},
    "Countermeasure Lab": {"Tagalog": "Laboratoryo ng Solusyon", "Pangasinan": "Laboratoryo na Solusyon"},
    "Live Telemetry": {"Tagalog": "Live na Telemetrya", "Pangasinan": "Live na Telemetrya"},
    "Barangay Walkthrough": {"Tagalog": "Paglalakbay sa Barangay", "Pangasinan": "Sankaliblibot na Barangay"},
    "Methods & Sources": {"Tagalog": "Pamamaraan at Pinagmulan", "Pangasinan": "Pamaraan tan Pinagmulan"},
}

TL = {
    "English": {"community": "KAPIT-BAHAYAN ACTIONS (work even before LGU aid arrives):",
                "desk": "BARANGAY RESPONSE DESK:",
                "people": "Estimated residents in flood zones right now:",
                "water": "Scenario water level:",
                "steps": ["Move vehicles, bangus harvest, feed sacks to above +1 m ground NOW",
                          "Charge phones/power banks; fill containers with clean water",
                          "Check on households on your elderly/PWD/buntis list - assign a buddy",
                          "Ready banca or pickups for the sick, elderly, small children",
                          "Clear drainage inlets along your street before the peak"],
                "desklines": ["Activate evacuation center roster (nearest school/townhall/church)",
                              "Monitor Pantal River bulletins; Alert/Alarm/Critical protocol",
                              "Post crowd depth reports to ClimateShield"],
                "heat1": "Reschedule outdoor work/sports before 10am or after 4pm",
                "heat2": "Open sari-sari water stations and shaded rest points (tarp + benches)",
                "heat3": "Buddy-check elderly, PWD, buntis, and bangus-pond workers hourly",
                "heat5": "Schools: suspend or shift to early-morning classes per DepEd guidance"},
    "Tagalog": {"community": "AKSIYON NG KAPITBAHAYAN (gumagawa kahit walang tulong pa ng LGU):",
                "desk": "RESPONSE DESK NG BARANGAY:",
                "people": "Tinatayang residenteng nasa baha ngayon:",
                "water": "Antas ng tubig sa sitwasyon:",
                "steps": ["Ilipat ang sasakyan, ani ng bangus, at mga sako ng pakain sa laging mas mataas pa sa +1 m NGAYON",
                          "I-charge ang mga cellphone at power bank; punuin ang lalagyan ng malinis na tubig",
                          "Bantayan ang mga pamilyang may matatanda, PWD, at buntis sa listahan - mag-assign ng kaibigan",
                          "Ihanda ang bangka o pickup para sa maysakit, matatanda, at maliliit na bata",
                          "Linisin ang mga drainage sa inyong kalsada bago dumating ang rurok ng ulan"],
                "desklines": ["I-activate ang talaan ng evacuation center (pinakamalapit na paaralan, munisipyo, o simbahan)",
                              "Bantayan ang bulletin ng Ilog Pantal; Alert/Alarm/Critical protocol",
                              "Mag-post ng crowd depth report sa ClimateShield"],
                "heat1": "I-schedule muli ang gawaang-oras o paligsahan bago mag-10am o pagkatapos ng 4pm",
                "heat2": "Buksan ang water station ng sari-sari store at may punong may lamong pahingahan (tarp at bangkito)",
                "heat3": "Bantayan bawat oras ang matatanda, PWD, buntis, at manggagawa sa bangus-pond - sistema ng kakampi",
                "heat5": "Mga paaralan: i-suspend o gawing umaga lang ang klase ayon sa gabay ng DepEd"},
    "Pangasinan": {"community": "SALIIR TAN MGA SANKABALEY (agawa ra ed angob na tulong na LGU):",
                   "desk": "RESPONSE DESK NA BARANGAY:",
                   "people": "Tali na mamayaran ed lanang na baha sikan:",
                   "water": "Duktaw na layum ed satwa:",
                   "steps": ["Isimsim so manbansilog, ani na bangus, tan sako na pakain ed nengnengneng so +1 m ANTON",
                            "I-charge so cellphone tan power bank; puno so lalagan na onliling danum",
                            "Bantayen so pamilya na ogogaw, balbaleg, tan buntis - abay so kwentwan",
                            "Iparaan so bangka odino pickup konla so maailangan, ogogaw, tan biek",
                            "Purawen so drainage ed dalan niyo antis so poran na urem"],
                   "desklines": ["I-activate so lista na evacuation center (kaiba so eskwelahan, munisipyo, odino simbaan)",
                               "Bantayen so bulletin na Ilog Pantal; Alert/Alarm/Critical protocol",
                               "Man-post so crowd depth report ed ClimateShield"],
                   "heat1": "Baloan isibi so trabaho odino laro antis 10am odino ingappo 4pm",
                   "heat2": "Iy-open so water station na pananabangan tan pangasusuyenan (tarp tan bankito)",
                   "heat3": "Kada oras bantayen so ogogaw, balbaleg, buntis, tan mangngapis ed bangus-pond",
                   "heat5": "Mga eskwelahan: suspendeen odino agmo-umran so klase kanyan DepEd"},
}


def action_card_flood(brgy_row, water_level, affected_est, trigger_class, lang="English"):
    t = TL.get(lang, TL["English"])
    lines = [
        f"CLIMATESHIELD ADVISORY - {str(brgy_row['barangay']).upper()} (flood trigger: {trigger_class})",
        "",
        f"{t['people']} {affected_est if affected_est is not None else 'n/a (no spatial anchor)'} / {int(brgy_row['popn']):,} (census 2020)",
        f"{t['water']} +{water_level:.2f} m above sea datum",
        "",
        t["community"],
    ]
    lines += [f"{i}. {s}" for i, s in enumerate(t["steps"], 1)]
    lines += ["", t["desk"]]
    lines += [f"- {s}" for s in t["desklines"]]
    return "\n".join(lines)


def action_card_heat(brgy_row, hi_value, category, lang="English"):
    t = TL.get(lang, TL["English"])
    lines = [
        f"CLIMATESHIELD HEAT BULLETIN - {str(brgy_row['barangay']).upper()} ({category})",
        "",
        f"Heat index: {hi_value:.0f} C | {t['people']} {int(brgy_row['popn']):,} (census 2020)",
        "",
        t["community"],
    ]
    lines += [f"1. {t['heat1']}", f"2. {t['heat2']}", f"3. {t['heat3']}",
              "4. Watch heat cramps/exhaustion: shade, elevate legs, sip water, cool packs on "
              "armpits/wrists/ankles; hospital if confusion/vomiting.",
              f"5. {t['heat5']}"]
    return "\n".join(lines)


def curve_W(peak_W, tide, hour, rise_h=10.0, tau=24.0):
    if hour <= rise_h:
        f = (hour / rise_h) ** 1.5
    else:
        f = np.exp(-(hour - rise_h) / tau)
    return tide + (peak_W - tide) * f


def depth_png(depth, vmax=None, L=None):
    import PIL.Image
    if L is None:
        raise ValueError("L (Layers) required")
    d = np.nan_to_num(depth, nan=0.0)
    vmax = vmax or max(0.8, float(np.percentile(d[d > 0.02], 99)) if (d > 0.02).any() else 0.8)
    import matplotlib.cm as cm_mpl
    cmap = matplotlib.colormaps["YlGnBu"]
    rgba = cmap(np.clip(d / vmax, 0, 1))
    out = (rgba * 255).astype("uint8")
    out[..., 3] = np.where(d > 0.03, 190, 0)
    img = PIL.Image.fromarray(out, "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), vmax


def grid_bounds_4326(L):
    from geo import Transformer
    tr = Transformer.from_crs(L.crs, "EPSG:4326", always_xy=True)
    x0, y0 = L.transform.c, L.transform.f - L.h * 30
    x1, y1 = L.transform.c + L.w * 30, L.transform.f
    xs, ys = tr.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
    return min(xs), min(ys), max(xs), max(ys)


ESRI_GRAY = ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
             "Esri, HERE, Garmin, (c) OpenStreetMap contributors, GIS User Community")


def brgy_layer(L, m, choro=None, highlight=None):
    """Barangay boundary outlines (+ optional choropleth fill + one highlighted barangay).

    choro: {barangay: dict(frac=float 0..1, note=str)} — polygons with a `frac` entry are shaded
    YlOrRd and gain a tooltip with the note. highlight: barangay name to outline boldly.
    Source of geometry: see brgypoly.py (official file when provided, else derived interim).
    """
    import folium
    try:
        import brgypoly as _bp
        gj, path = _bp.map_layer()
        if gj is None:
            return
        src = (gj.get("properties") or {}).get("source", "boundaries")
        interim = "derived" in str(src)

        def color_for(frac):
            import math
            if frac is None:
                return "#6b7280"
            f = max(0.0, min(1.0, float(frac)))
            ramp = [(0.0, (255, 247, 237)), (0.25, (254, 204, 138)), (0.5, (253, 141, 60)),
                    (0.75, (217, 72, 1)), (1.0, (128, 0, 38))]
            for (a, ca), (b, cb) in zip(ramp, ramp[1:]):
                if f <= b:
                    t = (f - a) / (b - a) if b > a else 0
                    rgb = tuple(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3))
                    return f"rgb{rgb}"
            return "rgb(128,0,38)"

        def style_fn(f):
            nm = f["properties"]["name"]
            frac = (choro or {}).get(nm, {}).get("frac")
            hl = highlight == nm
            return dict(fillColor=color_for(frac), fill=(choro is not None or hl),
                        fillOpacity=0.45 if hl else (0.38 if choro is not None else 0.0),
                        weight=3 if hl else 1.2, color="#1e3a8a" if hl else "#ffffff", opacity=0.9)

        def tt_fn(f):
            nm = f["properties"]["name"]
            ent = (choro or {}).get(nm)
            base = f"<b>{nm}</b>" + (" · DERIVED boundary (interim)" if interim else "")
            if ent:
                base += "<br>" + ent.get("note", "")
            return base

        layer = folium.GeoJson(gj, name=f"({'DERIVED interim ' if interim else ''}barangay boundaries)",
                               style_function=style_fn,
                               tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Barangay:"])
                               if choro is None else folium.GeoJsonTooltip(
                                   fields=["name"], aliases=["Barangay:"],
                                   labels=False, sticky=False, style="font-size:11px;"))
        layer.add_to(m)
    except Exception:
        pass


def make_city_map(L, depth=None, focus=None, crowd=True, fac=True,
                  center=(16.0432, 120.3342), zoom=13, W_cut=None, vmax=None, legend=True,
                  boundaries=True, choro=None, highlight=None):
    import folium
    m = folium.Map(location=center, zoom_start=zoom, tiles=None)
    folium.TileLayer(tiles=ESRI_GRAY[0], attr=ESRI_GRAY[1], name="map (Esri light)").add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                     attr="Esri, Maxar, Earthstar", name="satellite (Esri)").add_to(m)

    if boundaries:
        brgy_layer(L, m, choro=choro, highlight=highlight)

    if depth is not None:
        png, v = depth_png(depth, vmax=vmax, L=L)
        bounds = grid_bounds_4326(L)
        import base64 as _b64
        b64 = _b64.b64encode(png).decode()
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{b64}",
            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
            opacity=0.78, name="flood depth",
        ).add_to(m)

    for r in L.coast:
        pts = [(la, lo) for lo, la in r["ll"]]
        folium.PolyLine(pts, color="#117864", weight=4, opacity=0.9,
                        tooltip="Lingayen Gulf coastline").add_to(m)
    main_rivers = [r for r in L.rivers if r["class"] in ("river", "canal")]
    for r in main_rivers:
        pts = [(la, lo) for lo, la in r["ll"]]
        folium.PolyLine(pts, color="#2f7fb8", weight=4 if r["class"] == "river" else 2,
                        opacity=0.85, tooltip=f"Pantal/Calmay ({r['class']})").add_to(m)

    if W_cut is not None:
        for r, (ris, cis) in zip(L.roads, L.road_cells):
            vd = depth[ris, cis] if depth is not None else None
            if vd is None:
                continue
            vd = vd[np.isfinite(vd)]
            cut = float((vd > 0.30).mean()) if len(vd) else 0.0
            if cut > 0.05:
                pts = [(la, lo) for lo, la in r["ll"]]
                col = "#c0392b" if cut >= 0.5 else ("#e67e22" if cut > 0.25 else "#f0b37e")
                folium.PolyLine(pts, color=col, weight=3, opacity=0.95,
                                tooltip=f"{r['name'] or r['class']} — {cut*100:.0f}% cut"
                                        + (f" · {r['length_m']/1000:.1f} km" if r.get("length_m") else "")).add_to(m)

    if fac:
        cat_colors = {"school": "#2563eb", "health": "#c0392b", "civic_protective": "#b5813e", "worship": "#6d28d9"}
        icons = {"school": "graduation-cap", "health": "plus", "civic_protective": "home", "worship": "place-of-worship"}
        for f in L.facilities:
            folium.CircleMarker([f["lat"], f["lon"]], radius=4,
                                color="white", weight=0.8,
                                fill=True, fill_color=cat_colors.get(f["category"], "#666"),
                                fill_opacity=0.95,
                                tooltip=f"{f['category']}: {f['name'] or '?'} · elev {f['elev_m']:.1f} m"
                                        + (f" · UNDER +{W_cut:.2f} m WATER" if (W_cut and f["elev_m"] < W_cut) else ""),
                                ).add_to(m)

    if crowd:
        for p in crowd_pins(ANCHORS_GLOBAL) if ANCHORS_GLOBAL is not None else []:
            folium.CircleMarker([p["lat"], p["lon"]], radius=6 + p["sev"] * 2.5,
                                color="white", weight=1.5, fill=True,
                                fill_color=SEV_COLORS[p["sev"]], fill_opacity=0.95,
                                tooltip=f"crowd report · {p['barangay']} · {p['detail']} · {p['when']} ({p['n']} logs)"
                                ).add_to(m)

    if focus:
        folium.Marker([focus["lat"], focus["lon"]],
                      tooltip=f"<b>{focus['name']}</b> — barangay core",
                      icon=folium.Icon(color="orange", icon="star", prefix="fa")).add_to(m)
        folium.map.Marker([focus["lat"], focus["lon"]]).add_child(
            folium.ToolTip(focus["name"], permanent=True)).add_to(m)

    if depth is not None and legend:
        m.get_root().html.add_child(folium.Element(
            '<div class="cs-maplegend" style="position:absolute;bottom:12px;left:12px;z-index:1000;'
            'background:rgba(255,255,255,.92);border:1px solid #e5e7eb;border-radius:10px;padding:6px 10px;'
            'font:600 11px \'Segoe UI\',sans-serif;color:#1f2937;box-shadow:0 3px 10px rgba(0,0,0,.12);">'
            'flood depth<div style="width:110px;height:8px;border-radius:4px;margin-top:4px;'
            'background:linear-gradient(90deg,#ffffd9,#c7e9b4,#41b6c4,#081d58);"></div>'
            '<div style="display:flex;justify-content:space-between;font-size:9px;color:#6b7280;">'
            '<span>shallow</span><span>deep</span></div></div>'))
    folium.LayerControl(collapsed=False).add_to(m)
    return m


ANCHORS_GLOBAL = None


def set_anchor_lookup(brgy_anchors):
    global ANCHORS_GLOBAL
    ANCHORS_GLOBAL = anchors_map(brgy_anchors)


def build_briefing(row, anchor, W, affected_est, scen_label, lang, map_fig_fn=None,
                   city_meta=None, susc=None):
    t = TL.get(lang, TL["English"])
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("#ffffff")

    header = fig.add_axes([0, 0.90, 1, 0.10])
    header.axis("off")
    header.add_patch(plt.Rectangle((0, 0), 1, 1, transform=header.transAxes, color="#2563eb"))
    header.text(0.03, 0.62, f"CLIMATESHIELD — DAGUPAN CITY", color="white", fontsize=20, fontweight="bold")
    header.text(0.03, 0.22, f"{str(row['barangay']).upper()}  ·  {scen_label}  ·  "
                + datetime.now().strftime("%b %d, %Y"), color="#dbeafe", fontsize=11)

    kpi = fig.add_axes([0.04, 0.62, 0.28, 0.25])
    kpi.axis("off")
    kpi.text(0, 1.00, "Scenario KPIs", fontsize=13, fontweight="bold", color="#1f2937")
    kpi.text(0, 0.78, f"Census 2020:  {int(row['popn']):,}", fontsize=11)
    kpi.text(0, 0.60, f"Water level:  +{W:.2f} m", fontsize=11)
    kpi.text(0, 0.42, f"Est. affected:  {affected_est if affected_est is not None else '—'}", fontsize=11)
    if susc is not None:
        kpi.text(0, 0.24, f"Mean susceptibility (300 m):  {susc:.0f}/100", fontsize=11)
    if city_meta:
        kpi.text(0, 0.06, f"City census: {city_meta['psa_pop_2020']:,} · 31 barangays", fontsize=9, color="#6b7280")

    mapax = fig.add_axes([0.36, 0.52, 0.60, 0.36])
    mapax.axis("off")
    if map_fig_fn is not None:
        try:
            mfig = map_fig_fn()
            mfig.axes[0].figure.canvas.draw() if False else None
            buf = io.BytesIO()
            mfig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
            plt.close(mfig)
            img = plt.imread(buf)
            mapax.imshow(img)
            mapax.set_title("Barangay core — terrain & susceptibility", fontsize=10, color="#374151")
        except Exception as e:
            mapax.text(0.5, 0.5, f"map unavailable ({type(e).__name__})", ha="center")
    else:
        mapax.text(0.5, 0.5, "no spatial anchor", ha="center")

    act = fig.add_axes([0.04, 0.05, 0.92, 0.42])
    act.axis("off")
    act.add_patch(plt.Rectangle((0.0, 0.0), 1.0, 1.0, transform=act.transAxes,
                                facecolor="#f8fafc", edgecolor="#e5e7eb"))
    act.text(0.02, 0.93, t["community"], fontsize=11.5, fontweight="bold", color="#1f2937")
    y = 0.80
    for i, s in enumerate(list(t["steps"]), 1):
        for j, wl in enumerate(textwrap.wrap(f"{i}) {s}", 110)):
            act.text(0.02, y, wl, fontsize=10, va="top")
            y -= 0.055
            if y < 0.06:
                break
    act.text(0.02, y - 0.02, t["desk"], fontsize=11, fontweight="bold", color="#1f2937")

    foot = fig.add_axes([0, 0, 1, 0.045])
    foot.axis("off")
    foot.text(0.03, 0.45, "ClimateShield-Dagupan community briefing · proxy planning estimates — official "
             "warnings: PAGASA / CDRRMO", fontsize=7.5, color="#6b7280")
    foot.text(0.97, 0.45, f"lang: {lang} · v0.5", fontsize=7.5, color="#6b7280", ha="right")

    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="pdf")
        ext = "pdf"
    except Exception:
        # Some machines block a DLL the PDF backend needs (Windows Application Control vs fontTools).
        # The Agg/PNG backend is unaffected — deliver the one-page briefing as an image instead.
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200)
        ext = "png"
    plt.close(fig)
    return buf.getvalue(), ext


_graph = None


def load_graph():
    global _graph
    if _graph is None:
        import pickle
        with open(LAY / "street_graph.pkl", "rb") as f:
            _graph = pickle.load(f)
    return _graph


def nearest_node(graph, lon, lat):
    best, bd = None, 1e18
    for nid, n in graph["nodes"].items():
        d = (n["lon"] - lon) ** 2 + (n["lat"] - lat) ** 2
        if d < bd:
            bd, best = d, nid
    return best


def nearest_shelter(brgy_anchor, facilities):
    cands = [f for f in facilities if f["category"] in ("school", "civic_protective", "worship")]
    a = brgy_anchor
    return min(cands, key=lambda f: (f["lon"] - a["lon"]) ** 2 + (f["lat"] - a["lat"]) ** 2)


def shortest_path(graph, start, goal):
    import heapq
    dist = {start: 0.0}
    prev = {}
    seen = set()
    pq = [(0.0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        if u == goal:
            break
        for v, seg, cls, name in graph["edges"].get(u, []):
            nd = d + seg
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = (u, seg, cls, name)
                heapq.heappush(pq, (nd, v))
    if goal not in dist and goal != start:
        return None
    path, cur = [goal], goal
    while cur != start:
        u, seg, cls, name = prev[cur]
        path.append(u)
        cur = u
    path.reverse()
    return path, dist.get(goal, 0.0)


def route_for(L, brgy_anchor):
    graph = load_graph()
    s0 = nearest_node(graph, brgy_anchor["lon"], brgy_anchor["lat"])
    shelter = nearest_shelter(brgy_anchor, L.facilities)
    g0 = nearest_node(graph, shelter["lon"], shelter["lat"])
    found = shortest_path(graph, s0, g0)
    if found is None:
        return None
    path, total = found
    nodes = graph["nodes"]
    cum, elevs, lons, lats, bylen = [0.0], [], [], [], {}
    for i, nid in enumerate(path):
        n = nodes[nid]
        lons.append(n["lon"])
        lats.append(n["lat"])
        elevs.append(n["elev"])
        if i > 0:
            for v, seg, cls, name in graph["edges"].get(path[i - 1], []):
                if v == nid:
                    cum.append(cum[-1] + seg)
                    if name:
                        bylen[name] = bylen.get(name, 0) + seg
                    break
    roadname = max(bylen, key=bylen.get) if bylen else "local streets"
    return {"cum": np.array(cum), "elev": np.array(elevs), "lon": np.array(lons), "lat": np.array(lats),
            "main_road": roadname, "total_m": float(cum[-1]),
            "shelter": shelter}


def along_route(profile, dist_m):
    c = profile["cum"]
    total = float(c[-1])
    s = float(np.clip(dist_m, 0, total))
    i = int(np.searchsorted(c, s, side="right")) - 1
    i = min(max(i, 0), len(c) - 2)
    span = max(c[i + 1] - c[i], 1e-6)
    frac = (s - c[i]) / span
    lon = float(profile["lon"][i] + frac * (profile["lon"][i + 1] - profile["lon"][i]))
    lat = float(profile["lat"][i] + frac * (profile["lat"][i + 1] - profile["lat"][i]))
    elev = float(profile["elev"][i] + frac * (profile["elev"][i + 1] - profile["elev"][i]))
    return lon, lat, elev, s, total


def depth_label(d):
    if d <= 0:
        return "dry ground"
    if d < 0.15:
        return "wet pavement"
    if d < 0.5:
        return "knee-deep"
    if d < 1.0:
        return "waist-deep"
    return "chest-deep or more"


GAUGE_PROVIDERS = ["manual log", "shared sheet (CSV URL)", "PAGASA hook (experimental)"]


def gauge_freshness(path=GAUGE, stale_after_h=24):
    hist = gauge_history(path)
    if not len(hist):
        return None
    last = pd.Timestamp(hist.iloc[-1]["logged_at"])
    now = pd.Timestamp.now(tz=PHTZ).tz_localize(None)
    age_h = max(0.0, (now - last).total_seconds() / 3600.0)
    return {"age_h": age_h, "stale": age_h > stale_after_h,
            "label": hist.iloc[-1]["logged_at"].strftime("%b %d %H:%M") if hasattr(hist.iloc[-1]["logged_at"], "strftime") else str(hist.iloc[-1]["logged_at"])}


def parse_gauge_text(text):
    """Tolerant parser for agency gauge CSV (see docs/future_real_operations/GAUGE_FEED_SPEC.md).

    Accepts logged_at|timestamp|time and level_m|level|stage_m (+ note, station), plus optional
    official thresholds alert_m/alarm_m/critical_m carried on any row. Returns
    (DataFrame[logged_at, level_m, note], thresholds|None, error_message|None).
    """
    import io as _io
    df = pd.read_csv(_io.StringIO(str(text)))
    cols = {str(c).lower().strip(): c for c in df.columns}
    tcol = cols.get("logged_at") or cols.get("timestamp") or cols.get("time") or cols.get("date")
    lcol = cols.get("level_m") or cols.get("level") or cols.get("stage_m")
    ncol = cols.get("note") or cols.get("source") or cols.get("remark")
    if not (tcol and lcol):
        return None, None, "feed needs columns logged_at, level_m (, note) — see GAUGE_FEED_SPEC.md"
    out = pd.DataFrame({"logged_at": pd.to_datetime(df[tcol], errors="coerce"),
                        "level_m": pd.to_numeric(df[lcol], errors="coerce"),
                        "note": (df[ncol].astype(str) if ncol else "feed")})
    out = out.dropna(subset=["logged_at", "level_m"]).sort_values("logged_at")
    thresholds = None
    tac = cols.get("alert_m"), cols.get("alarm_m"), cols.get("critical_m")
    if all(tac):
        vals = [pd.to_numeric(df[c], errors="coerce").dropna() for c in tac]
        if all(len(v) for v in vals) and all(bool((v > 0).all()) for v in vals):
            thresholds = dict(alert=float(vals[0].iloc[-1]), alarm=float(vals[1].iloc[-1]),
                              critical=float(vals[2].iloc[-1]))
    if not len(out):
        return None, thresholds, "no parseable rows (need a date column and numeric levels)"
    return out, thresholds, None


def read_sheet_csv(url, timeout=15):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "ClimateShieldDagupan/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = r.read().decode("utf-8-sig")
    df, thresholds, msg = parse_gauge_text(text)
    if df is not None and thresholds:
        df.attrs["thresholds"] = thresholds
    return df, msg


def pagasa_hook_probe(timeout=12):
    import urllib.request
    urls = [
        "https://www.pagasa.dost.gov.ph/flood",
        "https://www.pagasa.dost.gov.ph/learnings/legend",
    ]
    reached = []
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "ClimateShieldDagupan/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status == 200:
                    reached.append(u)
        except Exception:
            pass
    if reached:
        return None, "PAGASA site reachable but publishes no keyless machine-readable river-stage feed — manual log and sheet bridge remain the live sources."
    return None, "PAGASA site unreachable from here — keeping manual log + sheet bridge."


WT_TL_STRINGS = {
    "English": {
        "intro": "Story of one barangay: ground → water → shelter.",
        "step_profile": "Profile", "step_terrain": "Terrain", "step_flood": "Flood exposure",
        "step_counter": "Countermeasures", "step_street": "Street walk",
        "step_card": "Action card",
        "street_hint": "Drag the flood slider and walk the route — shelters marked on the horizon.",
    },
    "Tagalog": {
        "intro": "Kuwento ng isang barangay: lupa → tubig → kanlungan.",
        "step_profile": "Profile", "step_terrain": "Lupa at Anyo", "step_flood": "Banta ng Baha",
        "step_counter": "Mga Solusyon", "step_street": "Lakad sa Kalye",
        "step_card": "Action Card",
        "street_hint": "Galawin ang flood slider at lakarin ang ruta — may marka ang evacuation center.",
    },
    "Pangasinan": {
        "intro": "Istorya na sakey barangay: dalin → danum → pankalakan.",
        "step_profile": "Profile", "step_terrain": "Dalin", "step_flood": "Banta na Layus",
        "step_counter": "Solusyon", "step_street": "Lakar ed Dalan",
        "step_card": "Action Card",
        "street_hint": "Galawen so flood slider tan lakar so ruta — marka so evacuation center.",
    },
}


def wt(lang, key):
    table = WT_TL_STRINGS.get(lang, WT_TL_STRINGS["English"])
    return table.get(key, WT_TL_STRINGS["English"].get(key, key))


THEMES = {
    "day": {
        "BG": "#f7f8fa", "PANEL": "#ffffff", "BORDER": "#e5e7eb", "TEXT": "#1f2937",
        "MUTED": "#6b7280", "ACCENT": "#2563eb", "ACCENT2": "#4f46e5", "PLOT_TEMPLATE": "plotly_white",
        "GRID": "#e5e7eb", "CARD_SHADOW": "0 1px 3px rgba(16,24,40,.08)",
    },
    "night": {
        "BG": "#0f172a", "PANEL": "#1e293b", "BORDER": "#334155", "TEXT": "#e2e8f0",
        "MUTED": "#94a3b8", "ACCENT": "#38bdf8", "ACCENT2": "#a78bfa", "PLOT_TEMPLATE": "plotly_dark",
        "GRID": "#334155", "CARD_SHADOW": "0 1px 6px rgba(0,0,0,.45)",
    },
}
THEME_LABELS = {"day": "☀️ Day ops", "night": "🌙 Night ops"}


def terrain_profile(L, lon, lat, half_deg=0.012, n=101):
    """Ground elevation along an east–west line through (lon, lat).

    Returns (metres from the core west→east, elevation m). 0.012° ≈ ±1.3 km — enough to show the bowl a
    barangay sits in without leaving the grid. Used by the Walkthrough Terrain tab.
    """
    lons = np.linspace(lon - half_deg, lon + half_deg, n)
    lats = np.full(n, float(lat))
    xs, ys = L.to_utm(lons, lats)
    cis = np.clip(np.round((xs - L.transform.c) / 30 - 0.5), 0, L.w - 1).astype(int)
    ris = np.clip(np.round((L.transform.f - ys) / 30 - 0.5), 0, L.h - 1).astype(int)
    z = np.nan_to_num(L.dem[ris, cis], nan=0.0)
    dists = np.linspace(-half_deg * 111000 * np.cos(np.radians(lat)), half_deg * 111000 * np.cos(np.radians(lat)), n)
    return dists, z


def resolve_bg_photo():
    from pathlib import Path as _P
    p = _P(__file__).resolve().parents[1] / "assets" / "hero" / "slide_real.jpg"
    return p if p.exists() else None

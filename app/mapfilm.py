"""Map-based storm time-lapse and route card — everything drawn on the real Dagupan basemap.

storm_map(): one Leaflet map, N flood-depth overlays (one per hour), and a HUD with a scrubber/play
button. Overlay, caption and counters all read from the same frame index, so nothing drifts.
route_map(): highlighted evacuation route to the nearest shelter, with a depth gauge readout.
"""
import base64
import json

import folium
import numpy as np

import kit

ESRI_SAT = ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "Esri, Maxar, Earthstar Geographics")
ESRI_LABELS = ("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
               "Esri")


def _base(center, zoom, satellite=True, height=None):
    kw = dict(height=f"{height}px", width="100%") if height else {}
    m = folium.Map(location=center, zoom_start=zoom, tiles=None, control_scale=True, **kw)
    if satellite:
        folium.TileLayer(tiles=ESRI_SAT[0], attr=ESRI_SAT[1], name="satellite").add_to(m)
        folium.TileLayer(tiles=ESRI_LABELS[0], attr=ESRI_LABELS[1], name="labels", overlay=True, control=False).add_to(m)
    else:
        folium.TileLayer(tiles=kit.ESRI_GRAY[0], attr=kit.ESRI_GRAY[1], name="map").add_to(m)
    return m


def _rivers_coast(m, L):
    for r in L.coast:
        folium.PolyLine([(la, lo) for lo, la in r["ll"]], color="#5eead4", weight=3, opacity=0.9).add_to(m)
    for r in L.rivers:
        if r["class"] in ("river", "canal"):
            folium.PolyLine([(la, lo) for lo, la in r["ll"]], color="#60a5fa",
                            weight=3 if r["class"] == "river" else 1.5, opacity=0.85).add_to(m)


def frame_stats(L, W, evac_frac):
    depth, _ = L.depth_grid(W)
    inwater = (depth > 0.15) & L.land_mask
    pop_in = float(L.pop_psa[inwater].sum())
    bldg = int((L.bldg_elev < W - 0.15).sum())
    cut_km = 0.0
    for r, (ris, cis) in zip(L.roads, L.road_cells):
        vd = depth[ris, cis]
        frac = float((vd > 0.30).mean()) if len(vd) else 0.0
        if frac > 0:
            cut_km += r["length_m"] / 1000.0 * frac
    evac = pop_in * evac_frac
    return depth, dict(pop_in=pop_in, bldg=bldg, roads_km=cut_km, evacuated=evac, stranded=pop_in - evac)


def storm_frames(L, story, hours=40, n=16):
    """Hourly frames for a story: water level, stats, caption and a depth PNG (base64).

    Scripted stories use the proxy rise/recession curve; replay stories (story["replay"]) carry their own
    water series from the historical rainfall record (see replay.py).
    """
    if story.get("replay"):
        return _replay_frames(L, story)
    DRY = -0.35
    base_W = L.water_level_for_share(story["share"])
    peak = base_W + story["tide"] + 0.45 * story["clog"] - (0.22 if story["pumps"] else 0.0)
    tau = 16.0 + 32.0 * story["clog"]
    rise_h = 10.0
    frames = []
    vmax = max(0.8, peak + story.get("surge", 0.0) + 0.3)
    for h in np.linspace(0, hours, n):
        W = kit.curve_W(peak, DRY, h, rise_h=rise_h, tau=tau)
        if story.get("surge", 0) > 0 and h >= 10:
            W += story["surge"] * np.exp(-((h - 13.0) ** 2) / 18.0)
        if story["warning_h"] > 0:
            ef = float(np.clip((h - (rise_h - story["warning_h"])) / max(story["warning_h"], 1), 0, 1)) * 0.88
        else:
            ef = float(np.clip((h - 7.0) / 10.0, 0, 1)) * 0.35
        depth, st = frame_stats(L, W, ef)
        png, _ = kit.depth_png(depth, vmax=vmax, L=L)
        text = story["beats"][0][1]
        for bh, t in story["beats"]:
            if h >= bh:
                text = t
        frames.append(dict(hour=float(h), W=float(W), caption=text,
                           png=base64.b64encode(png).decode(), **st))
    return frames


def _replay_frames(L, story, max_frames=48):
    hours = np.array(story["hours"], dtype=float)
    Ws = np.array(story["W_series"], dtype=float)
    idx = np.unique(np.linspace(0, len(hours) - 1, min(max_frames, len(hours))).round().astype(int))
    vmax = max(0.8, float(Ws.max()) + 0.3)
    peak_h, warn = story["peak_h"], story["warning_h"]
    frames = []
    for i in idx:
        h, W = float(hours[i]), float(Ws[i])
        if warn > 0:
            ef = float(np.clip((h - (peak_h - warn - 6)) / max(warn, 1), 0, 1)) * 0.88
        else:
            ef = float(np.clip((h - (peak_h - 6)) / 18.0, 0, 1)) * 0.35
        depth, st = frame_stats(L, W, ef)
        png, _ = kit.depth_png(depth, vmax=vmax, L=L)
        text = story["beats"][0][1]
        for bh, t in story["beats"]:
            if h >= bh:
                text = t
        frames.append(dict(hour=h, W=W, caption=text, label=story["labels"][i],
                           png=base64.b64encode(png).decode(), **st))
    return frames


FLOOD_HUD = {"w_line": "people stranded over the", "p": "🧍 people in water", "e": "🏫 in shelters",
             "s": "⚠ stranded", "b": "🏠 buildings in water", "r": "🛣 roads cut", "r_suffix": " km",
             "legend": "flood depth: shallow → deep",
             "legend_gradient": "linear-gradient(90deg,#ffffd9,#7fcdbb,#1d91c0,#081d58)"}


def storm_map(L, frames, title, subtitle, center=(16.055, 120.335), zoom=13, height=600,
              autoplay=True, interval_ms=1100, hud=None):
    """Film player HUD. `hud` overrides stat labels/units/legend (see heat.HUD); flood defaults kept.
    NOTE: the HTML block variable is `hud_html` — never name it `hud`, it shadows this parameter
    (that bug shipped once; the heat tests catch it now)."""
    HUDL = {**FLOOD_HUD, **(hud or {})}
    m = _base(center, zoom, satellite=True, height=height)
    bounds = kit.grid_bounds_4326(L)
    bb = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]
    names = []
    for k, f in enumerate(frames):
        ov = folium.raster_layers.ImageOverlay(image=f"data:image/png;base64,{f['png']}", bounds=bb,
                                               opacity=0.82 if k == 0 else 0.0, interactive=False,
                                               cross_origin=False, zindex=400 + k)
        ov.add_to(m)
        names.append(ov.get_name())
    _rivers_coast(m, L)
    for fct in L.facilities:
        if fct["category"] in ("school", "health"):
            folium.CircleMarker([fct["lat"], fct["lon"]], radius=3.5, color="white", weight=0.8, fill=True,
                                fill_color="#2563eb" if fct["category"] == "school" else "#ef4444", fill_opacity=0.95,
                                tooltip=f"{fct['category']}: {fct['name'] or '?'} · ground {fct['elev_m']:.1f} m").add_to(m)

    meta = [dict(hour=f["hour"], W=f["W"], caption=f["caption"], pop_in=f["pop_in"], bldg=f["bldg"],
                 roads_km=f["roads_km"], evacuated=f["evacuated"], stranded=f["stranded"],
                 label=f.get("label", "")) for f in frames]
    mid = m.get_name()
    hmax = int(frames[-1]["hour"])
    smax = max(1.0, max(f["stranded"] for f in frames))
    pts = " ".join(f"{(f['hour'] / max(hmax, 1)) * 1000:.1f},{44 - (f['stranded'] / smax) * 40:.1f}" for f in frames)
    hud_html = f"""
    <style>
    html, body {{ margin:0; padding:0; font-family:'Source Sans Pro','Segoe UI',sans-serif; background:#fff; }}
    .cs-chip {{ position:absolute; z-index:1000; background:rgba(255,255,255,.95); border:1px solid #e5e7eb;
      border-radius:10px; padding:5px 11px; font:600 13px 'Segoe UI',sans-serif; color:#1f2937; box-shadow:0 3px 10px rgba(0,0,0,.15); }}
    .cs-tag {{ top:10px; left:50px; }}
    .cs-now {{ top:10px; right:10px; font-size:14px; }}
    .cs-now b {{ color:#1e3a8a; }}
    .cs-legend {{ bottom:22px; right:10px; font-size:11px; font-weight:600; }}
    .cs-legend .bar {{ width:120px; height:8px; border-radius:4px; margin-top:3px;
      background:linear-gradient(90deg,#ffffd9,#7fcdbb,#1d91c0,#081d58); }}
    .cs-strip {{ border-top:1px solid #e5e7eb; padding:8px 12px 6px 12px; color:#1f2937; }}
    .cs-cap {{ font-size:14px; min-height:19px; margin-bottom:6px; }}
    .cs-cap b {{ color:#1e3a8a; margin-right:6px; }}
    .cs-stats {{ display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:8px; }}
    .cs-stat {{ border:1px solid #e5e7eb; border-radius:9px; padding:4px 8px; }}
    .cs-stat span {{ display:block; font-size:10.5px; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; }}
    .cs-stat b {{ font-size:17px; font-variant-numeric:tabular-nums; }}
    .cs-stat.bad b {{ color:#b91c1c; }}
    .cs-ctl {{ display:flex; align-items:center; gap:10px; margin-top:6px; }}
    .cs-ctl button {{ border:1px solid #cbd5e1; background:#fff; border-radius:8px; padding:3px 12px; cursor:pointer; font-weight:600; }}
    .cs-track {{ flex:1; position:relative; height:46px; }}
    .cs-track svg {{ position:absolute; inset:0; width:100%; height:46px; }}
    .cs-track input {{ position:absolute; left:0; right:0; bottom:0; width:100%; margin:0; accent-color:#2563eb; }}
    .cs-sub {{ font-size:11px; color:#6b7280; margin-top:2px; }}
    @media (max-width: 700px) {{ .cs-stats {{ grid-template-columns:repeat(3, minmax(0,1fr)); }} }}
    </style>
    <div class="cs-chip cs-tag" id="tag_{mid}">{title}</div>
    <div class="cs-chip cs-now" id="now_{mid}"><b id="hour_{mid}">HOUR 00</b> · <span id="w_{mid}"></span></div>
    <div class="cs-chip cs-legend" id="leg_{mid}">{HUDL['legend']}<div class="bar" style="background:{HUDL['legend_gradient']};"></div></div>
    <div class="cs-strip" id="hud_{mid}">
      <div class="cs-cap" id="cap_{mid}"></div>
      <div class="cs-stats">
        <div class="cs-stat"><span>{HUDL['p']}</span><b id="p_{mid}"></b></div>
        <div class="cs-stat"><span>{HUDL['e']}</span><b id="e_{mid}"></b></div>
        <div class="cs-stat bad"><span>{HUDL['s']}</span><b id="s_{mid}"></b></div>
        <div class="cs-stat"><span>{HUDL['b']}</span><b id="b_{mid}"></b></div>
        <div class="cs-stat"><span>{HUDL['r']}</span><b id="r_{mid}"></b></div>
        <div class="cs-stat"><span>⏱ hour</span><b id="hh_{mid}"></b></div>
      </div>
      <div class="cs-ctl">
        <button id="play_{mid}">❚❚ Pause</button>
        <div class="cs-track">
          <svg viewBox="0 0 1000 46" preserveAspectRatio="none">
            <polyline points="{pts}" fill="none" stroke="#fca5a5" stroke-width="2.5" vector-effect="non-scaling-stroke"/>
            <line id="cur_{mid}" x1="0" x2="0" y1="0" y2="46" stroke="#1e3a8a" stroke-width="2" vector-effect="non-scaling-stroke"/>
          </svg>
          <input type="range" id="rng_{mid}" min="0" max="{len(frames) - 1}" value="0" step="1">
        </div>
      </div>
      <div class="cs-sub">red line = {HUDL['w_line']} {hmax} hours · {subtitle}</div>
    </div>
    """
    js = f"""
    function csInit_{mid}() {{
      if (typeof window['{mid}'] === 'undefined' || typeof window['{names[-1]}'] === 'undefined') {{
        return setTimeout(csInit_{mid}, 60);
      }}
      var ovs = [{", ".join(names)}];
      var meta = {json.dumps(meta)};
      var map = {mid};
      var i = 0, timer = null, playing = {str(autoplay).lower()};
      var $ = function(id){{ return document.getElementById(id + '_{mid}'); }};
      var fmt = function(x){{ return Math.round(x).toLocaleString(); }};
      function show(k) {{
        i = k; var f = meta[k];
        ovs.forEach(function(o, j){{ o.setOpacity(j === k ? 0.82 : 0); }});
        $('hour').textContent = f.label ? f.label : 'HOUR ' + String(Math.round(f.hour)).padStart(2, '0') + (f.hour >= 24 ? ' · day ' + (Math.floor(f.hour / 24) + 1) : '');
        $('w').textContent = (typeof f.W === 'string') ? f.W
            : (f.W <= 0 ? 'streets dry' : 'water +' + f.W.toFixed(2) + ' m');
        $('cap').innerHTML = '<b>' + $('hour').textContent + '</b>' + f.caption;
        $('p').textContent = fmt(f.pop_in); $('e').textContent = fmt(f.evacuated);
        $('s').textContent = fmt(f.stranded); $('b').textContent = fmt(f.bldg);
        $('r').textContent = f.roads_km.toFixed(0) + '{HUDL["r_suffix"]}';
        $('hh').textContent = Math.round(f.hour) + ' / {hmax}';
        $('rng').value = k;
        var x = (f.hour / {max(hmax, 1)}) * 1000; $('cur').setAttribute('x1', x); $('cur').setAttribute('x2', x);
      }}
      function tick() {{ show((i + 1) % meta.length); if (i === 0) {{ pause(); setTimeout(play, 2200); }} }}
      function play() {{ if (timer) return; playing = true; $('play').textContent = '❚❚ Pause'; timer = setInterval(tick, {interval_ms}); }}
      function pause() {{ playing = false; $('play').textContent = '▶ Play'; if (timer) {{ clearInterval(timer); timer = null; }} }}
      $('play').onclick = function(){{ timer ? pause() : play(); }};
      $('rng').oninput = function(e){{ pause(); show(parseInt(e.target.value)); }};
      var c = map.getContainer();
      ['tag', 'now', 'leg'].forEach(function(n){{ var el = $(n); c.appendChild(el); L.DomEvent.disableClickPropagation(el); }});
      c.insertAdjacentElement('afterend', $('hud'));
      show(0); if (playing) play();
      document.body.setAttribute('data-cs-ready', '1');
    }}
    if (document.readyState === 'loading') {{ document.addEventListener('DOMContentLoaded', csInit_{mid}); }}
    else {{ csInit_{mid}(); }}
    """
    m.get_root().html.add_child(folium.Element(hud_html))
    m.get_root().script.add_child(folium.Element(js))
    return m


def route_map(L, profile, W, pos_m=None, height=520):
    """Evacuation route on the satellite map, coloured by water depth along the street."""
    lat_c = float(np.mean(profile["lat"]))
    lon_c = float(np.mean(profile["lon"]))
    m = _base((lat_c, lon_c), 16, satellite=True)
    depth = np.maximum(W - profile["elev"], 0.0)
    pts = list(zip(profile["lat"], profile["lon"]))
    for i in range(len(pts) - 1):
        d = float(max(depth[i], depth[i + 1]))
        col = "#22c55e" if d < 0.15 else ("#f59e0b" if d < 0.5 else ("#ef4444" if d < 1.0 else "#7f1d1d"))
        folium.PolyLine([pts[i], pts[i + 1]], color="white", weight=9, opacity=0.9).add_to(m)
        folium.PolyLine([pts[i], pts[i + 1]], color=col, weight=6, opacity=1.0,
                        tooltip=f"{profile['cum'][i]:.0f} m · ground {profile['elev'][i]:.2f} m · "
                                f"{kit.depth_label(d)} ({d:.2f} m)").add_to(m)
    folium.Marker(pts[0], tooltip="Start — barangay core",
                  icon=folium.Icon(color="orange", icon="home", prefix="fa")).add_to(m)
    sh = profile["shelter"]
    folium.Marker([sh["lat"], sh["lon"]], tooltip=f"Shelter: {sh.get('name') or sh.get('category')}",
                  icon=folium.Icon(color="green", icon="flag", prefix="fa")).add_to(m)
    if pos_m is not None:
        lon, lat, elev, s, total = kit.along_route(profile, pos_m)
        d = max(W - elev, 0.0)
        folium.CircleMarker([lat, lon], radius=9, color="white", weight=2, fill=True, fill_color="#2563eb",
                            fill_opacity=1, tooltip=f"You · {kit.depth_label(d)} ({d:.2f} m)").add_to(m)
    m.fit_bounds([[min(profile["lat"]), min(profile["lon"])], [max(profile["lat"]), max(profile["lon"])]], padding=(30, 30))
    return m


def depth_gauge_html(depth_m, label):
    """A simple person-vs-water graphic. Person = 1.70 m."""
    person_h = 170
    water_px = int(min(depth_m, 2.2) / 2.2 * person_h * 1.3)
    col = "#22c55e" if depth_m < 0.15 else ("#f59e0b" if depth_m < 0.5 else ("#ef4444" if depth_m < 1.0 else "#7f1d1d"))
    return f"""
    <div style="display:flex;align-items:flex-end;gap:16px;padding:10px 12px;border:1px solid #e5e7eb;border-radius:12px;background:#fff;">
      <div style="position:relative;width:70px;height:{int(person_h * 1.3)}px;background:linear-gradient(#f8fafc,#eef2f7);border-radius:8px;overflow:hidden;border:1px solid #e5e7eb">
        <div style="position:absolute;left:0;right:0;bottom:0;height:{water_px}px;background:rgba(37,99,235,.45);border-top:2px solid #2563eb"></div>
        <div style="position:absolute;left:50%;bottom:0;transform:translateX(-50%);width:34px;height:{person_h}px;">
          <div style="width:16px;height:16px;border-radius:50%;background:#374151;margin:0 auto"></div>
          <div style="width:22px;height:60px;background:#374151;margin:2px auto 0;border-radius:6px"></div>
          <div style="display:flex;justify-content:center;gap:6px"><div style="width:7px;height:88px;background:#374151;border-radius:3px"></div><div style="width:7px;height:88px;background:#374151;border-radius:3px"></div></div>
        </div>
        <div style="position:absolute;right:3px;top:3px;font:600 10px sans-serif;color:#64748b">1.7 m</div>
      </div>
      <div><div style="font:600 11px sans-serif;color:#6b7280;text-transform:uppercase;letter-spacing:.08em">Water here</div>
        <div style="font:800 28px sans-serif;color:{col}">{depth_m:.2f} m</div>
        <div style="font:600 14px sans-serif;color:#1f2937">{label}</div></div>
    </div>"""

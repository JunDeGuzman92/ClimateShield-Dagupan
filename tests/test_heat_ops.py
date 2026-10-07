"""Live providers (METAR obs, PAGASA dam table) and the heat-operations engine."""
import json
from pathlib import Path


def test_protocol_bands_match_official_cuts():
    import heat
    assert heat.protocol_for(26.9) == []
    assert [p["band"] for p in heat.protocol_for(30)] == ["Caution · 27–32°C"]
    assert [p["band"] for p in heat.protocol_for(38)] == ["Caution · 27–32°C", "Extreme Caution · 33–41°C"]
    d = heat.protocol_for(44)
    assert d[-1]["band"].startswith("DANGER")
    assert any("ADM" in t for _, t in d[-1]["actions"]), "DANGER must carry the class-suspension call"
    assert any("DepEd-2024" in s for p in d for s in p["sources"])
    x = heat.protocol_for(55)
    assert x[-1]["band"].startswith("EXTREME DANGER")
    assert "DOLE-08-23" in [s for p in heat.protocol_for(34) for s in p["sources"]]


def test_day_blocks_cover_the_day():
    import heat
    hours = list(range(0, 24))
    his = [30 + 12 * max(0, (h - 6) / 9) if h < 15 else 42 - (h - 15) for h in hours]
    rows = heat.day_blocks(hours, his)
    assert [r["block"] for r in rows] == ["Overnight", "Morning", "Late morning", "Midday", "Afternoon", "Evening"]
    mid = next(r for r in rows if r["block"] == "Midday")
    assert "Extreme Caution" in mid["band"]
    aft = next(r for r in rows if r["block"] == "Afternoon")
    assert aft["peak_hi"] >= 41 and "DANGER" in aft["band"]


def test_danger_ranking_is_population_weighted_and_complete(layers):
    import heat
    rank = heat.hi_hours_by_barangay(layers, list(range(5, 21)), [45.0] * 16)
    anchored = sum(1 for b in layers.brgy_anchors if b["anchor"])
    assert len(rank) == anchored, "every anchored barangay ranked; Barangay II has no anchor (yet)"
    assert (rank["danger_h"] == 16).all()
    top = rank.iloc[0]
    assert top["people_hours"] == rank["people_hours"].max()
    assert top["pop"] >= rank["pop"].median(), "top row must be populous, not just hot"


DAM_FIXTURE = """<html><body><table>
<tr><th>Dam Name</th><th>Observation Time &amp; Date</th><th>Reservoir Water Level (RWL) (m)</th>
<th>Water Level Deviation</th><th>Normal High Water Level (NHWL) (m)</th>
<th>Deviation from NHWL (m)</th><th>Rule Curve Elevation (m)</th><th>Deviation from Rule Curve (m)</th></tr>
<tr><td>Ambuklao</td><td>08:00 AM</td><td>751.56</td><td>24</td><td>0.03</td><td>752.00</td>
<td>-0.44</td><td>745.00</td><td>6.56</td></tr>
<tr><td>San Roque</td><td>08:00 AM</td><td>283.15</td><td>24</td><td>0.19</td><td>280.00</td>
<td>3.15</td><td>271.21</td><td>11.94</td></tr>
<tr><td>Binga</td><td>08:00 AM</td><td>574.04</td><td>24</td><td>0.24</td><td>575.00</td>
<td>9.99</td><td>565.00</td><td>9.04</td></tr>
<tr><td>Ipo</td><td>08:00 AM</td><td>100.33</td><td>24</td><td>0.35</td><td>101.10</td>
<td>-0.77</td><td>0.00</td><td>0.00</td></tr>
</table>
<a href='https://pubfiles.pagasa.dost.gov.ph/pagasaweb/files/hmd/riverbasin/agno.pdf' class='non-flood'>Non-Flood Watch</a>
</body></html>"""


def test_dam_parse_accepts_checked_rows_drops_bad_ones():
    import gauges
    out = gauges.parse_dams(DAM_FIXTURE, "2026-10-07 09:00")
    names = [d["name"] for d in out["dams"]]
    assert "San Roque" in names and "Ambuklao" in names
    assert "Binga" not in names, "Binga row claims NHWL deviation 9.99 vs real -0.96 — must drop"
    assert "Ipo" not in names, "non-Agno dams must not leak into the Agno panel"
    sr = next(d for d in out["dams"] if d["name"] == "San Roque")
    assert sr["over_nhwl_m"] == 3.15 and sr["gates"] is None
    assert out["basin"]["level"] == "non-flood" and "agno.pdf" in out["basin"]["link"]
    assert out["obs_label"] is not None


def test_cooling_register_match_roundtrip(layers):
    import heat
    import ops
    sh = ops.load_shelters(layers)
    sh.loc[sh.index[:2], "status"] = "open"
    sh.loc[sh.index[:2], "capacity"] = "120"
    ops.save_shelters(sh)
    assert heat.seed_cooling_from_shelters(layers) == 2
    assert heat.seed_cooling_from_shelters(layers) == 0, "seeding must be idempotent"
    a = next(b["anchor"] for b in layers.brgy_anchors if b["barangay"] == "Pantal")
    nc = heat.nearest_cooling(layers, a["lat"], a["lon"])
    assert nc is not None and nc["free"] is not None and nc["distance_m"] >= 0
    st = heat.cooling_stats()
    assert st["open"] == 2


def test_film_gate_releases_on_tap():
    from conftest import APP
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=1200)
    at.run()
    assert not at.exception
    play = next(b for b in at.button if b.label == "▶ Play the storm film")
    assert not at.session_state.get("play_flood"), "film must be gated off on first paint"
    play.click()
    at.run()
    assert at.session_state.get("play_flood") is True


def test_response_cooling_tab_exists():
    from conftest import APP
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=1200)
    at.run()
    at.sidebar.radio[0].set_value("🚑 Response & Dispatch")
    at.run()
    assert not at.exception
    assert any(getattr(t, "label", "") == "❄️ Cooling" for t in at.tabs)
    md = " ".join(m.value for m in at.markdown)
    assert "Nearest open relief" in md or "Cooling centers" in md


def test_deck_protocol_board_renders():
    """The 48-hour protocol board and danger ranking render on the heat tab boot."""
    from conftest import APP
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=1200)
    at.run()
    assert not at.exception
    assert any(getattr(t, "label", "") == "📋 Protocol board" for t in at.tabs)
    caps = " ".join(c.value for c in at.caption)
    md = " ".join(m.value for m in at.markdown)
    assert "What the next 48 hours demand" in caps
    assert "Open respite points in these barangays first" in md
    assert "Next 48 h at the city centre" in md

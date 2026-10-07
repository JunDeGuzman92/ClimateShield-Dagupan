"""Heat Scenario Simulator: frames, HUD labels, survival board, briefing card, navigation."""
import base64

from conftest import APP


def test_heat_film_frames_shape_and_labels(layers):
    import cinema
    import heat
    story = cinema.HEAT_STORIES["heatwave_brownout"]
    plan = cinema.heat_plan(layers, story)
    frames = heat.film_frames(layers, plan, story, heat.cooling_reach(layers))
    assert len(frames) == len(plan)
    assert frames[0]["label"] == "05:00" and frames[-1]["label"] == "20:00"
    assert isinstance(frames[0]["W"], str) and "°C" in frames[0]["W"], "HUD w passes a string for heat"
    png = base64.b64decode(frames[0]["png"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 3000
    # no cooling registered in this sandbox → the survival gap equals exposure
    f_pk = max(frames, key=lambda f: f["pop_in"])
    assert f_pk["evacuated"] == 0 and f_pk["stranded"] == f_pk["pop_in"]


def test_heat_map_player_uses_heat_hud(layers):
    import cinema
    import heat
    import mapfilm
    story = cinema.HEAT_STORIES["heatwave_brownout"]
    plan = cinema.heat_plan(layers, story)
    frames = heat.film_frames(layers, plan, story, heat.cooling_reach(layers))
    html = mapfilm.storm_map(layers, frames, "t", "s", hud=heat.HUD).get_root().render()
    assert "cooling point" in html and "DANGER" in html, "heat labels must appear in the HUD"
    assert "people in water" not in html, "flood defaults must not leak into the heat HUD"
    flat = mapfilm.storm_map(layers, frames, "t", "s").get_root().render()
    assert "people in water" in flat and "roads cut" in flat, "flood defaults must survive untouched"


def test_cooling_reach_respects_2_5km_radius(layers):
    import heat
    # register one practice centre right on Pantal's core
    a = next(b["anchor"] for b in layers.brgy_anchors if b["barangay"] == "Pantal")
    heat.save_cooling(__import__("pandas").DataFrame([dict(
        center_id="C001", name="Pantal Hall", kind="hall", capacity="200", headcount=0, status="open",
        barangay_hint="Pantal", lat=a["lat"], lon=a["lon"], contact="", updated_at="")]))
    reach = heat.cooling_reach(layers)
    r = reach.get("Pantal")
    assert r is not None and r[0] < 200 and r[2] == "open"
    far = reach.get("Bonuan Gueset")
    assert far is None or far[0] > 2500, "far barangays must not count as covered"


def test_briefing_png_renders_and_carries_protocols(layers):
    import heat
    row = layers.brgy.iloc[0]
    a = next(b["anchor"] for b in layers.brgy_anchors if b["barangay"] == row["barangay"])
    png = heat.briefing_png(layers, row, a, 46.0, "DANGER", "test story", None)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 20000


HEAT_NAV_LABEL = "☀️ Heat Scenario Simulator"


def test_heat_simulator_page_renders_end_to_end():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=1500)
    at.run()
    assert HEAT_NAV_LABEL in [str(o) for o in at.sidebar.radio[0].options]
    at.sidebar.radio[0].set_value(HEAT_NAV_LABEL)
    at.run()
    assert not at.exception, " | ".join(e.value[:200] for e in at.exception)
    labels = [getattr(t, "label", "") for t in at.tabs]
    for want in ("🗺️ Felt-heat map", "🎬 Day time-lapse", "🚶 Relief reach & survival", "📄 Cards & community copy"):
        assert any(want in l for l in labels), f"missing tab {want}"
    md = " ".join(m.value for m in at.markdown)
    caps = " ".join(c.value for c in at.caption)
    assert "Stay-alive today" in md or "Protocol at this hour" in md
    assert "911" in md, "verified national emergency lines must appear"
    # header layout: controls left, dashboard + day curve fill the right pane (it used to be blank)
    assert "Day dashboard" in md, "right-hand dashboard pane missing"
    assert "Day curve unavailable" not in md, "day curve failed to render"
    want = {"Hottest barangay now", "Residents in DANGER-band areas",
            "Population within 2.5 km of cooling", "Cooling points open"}
    assert want <= set(m.label for m in at.metric), "dashboard metrics moved out of the header"
    # recorded-day picker → heat-specific scenario
    st = next(s for s in at.selectbox if s.key == "heat_story")
    st.set_value("heatwave_brownout"); at.run()
    assert not at.exception
    slat = next((s for s in at.slider if s.key == "hx_tmax"), None)  # own-day controls appear in that mode
    # switching to live forecast mode is guarded (no network in tests) — recorded is the smoke path


def test_heat_day_time_lapse_film_renders_after_gate():
    """Regression: the Day time-lapse crashed with 'module mapfilm has no attribute STORM_STRIP_PX'."""
    from conftest import boot, button, goto, nav_labels, no_exc
    at = goto(boot(), nav_labels()[2])
    no_exc(at)
    button(at, startswith="▶ Play").click()
    at.run()
    no_exc(at)   # before the fix this raised AttributeError on the film strip height


def test_walkthrough_and_telemetry_indices_after_nav_insert():
    """NAV grew by one: exercises old index sites (walkthrough NAV[5], telemetry NAV[4])."""
    from conftest import nav_labels
    nav = nav_labels()
    assert nav[1].startswith("🌊") and nav[2].startswith("☀️") and nav[5].startswith("🗺️")

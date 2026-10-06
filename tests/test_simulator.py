"""Command Deck scenarios, Simulator views, Walkthrough route card, Telemetry badges."""
from conftest import boot, button, goto, nav_labels, no_exc

NAV = nav_labels()


def _md(at):
    return " ".join(m.value for m in at.markdown)


def test_deck_scenario_tabs_and_controls():
    at = boot()
    no_exc(at)
    assert len(at.tabs) >= 3
    assert _md(at).count("cs-factor") >= 5, "factor tiles missing under the time-lapse"
    next(r for r in at.radio if r.key == "film_flood").set_value("king_tide"); at.run(); no_exc(at)
    next(r for r in at.radio if r.key == "film_heat").set_value("heatwave_brownout"); at.run(); no_exc(at)
    next(s for s in at.select_slider if s.key == "heat_hour").set_value(9); at.run(); no_exc(at)
    next(s for s in at.slider if s.key == "cin_clog").set_value(95); at.run(); no_exc(at)
    next(r for r in at.radio if r.key == "film_flood").set_value("prepared"); at.run(); no_exc(at)
    assert "Same storm, different city" in _md(at)


def test_deck_replay_tab():
    at = boot()
    no_exc(at)
    assert len(at.tabs) == 4
    ev = next(s for s in at.selectbox if s.key == "rp_ev")
    ev.set_value("pepeng_2009"); at.run(); no_exc(at)
    rd = next(s for s in at.radio if s.key == "rp_rd")
    rd.set_value("prepared"); at.run(); no_exc(at)
    assert any("469 mm" in c.value for c in at.caption), "selected event's note not shown"
    assert any("Land flooded" in m.value for m in at.markdown), "replay summary tiles missing"
    assert any("Peak water" in m.value for m in at.markdown)


def test_simulator_views():
    at = goto(boot(), NAV[1])
    view = lambda: next(r for r in at.radio if r.key == "sim_view")  # noqa: E731 — re-fetch after every rerun
    for opt in view().options:
        view().set_value(opt); at.run()
        assert not at.exception, f"{opt}: {at.exception[0].value[:300]}"
    view().set_value(next(o for o in view().options if "Evacuation" in o)); at.run()
    pos = next(s for s in at.slider if s.key == "sim_rc_pos")
    pos.set_value(60.0); at.run(); no_exc(at)
    assert next(s for s in at.slider if s.key == "sim_rc_pos").value == 60.0


def test_walkthrough_route_and_action_card():
    at = goto(boot(), NAV[4])
    button(at, startswith="Evacuation route").click(); at.run(); no_exc(at)
    assert "Water here" in _md(at), "person-vs-water gauge missing"
    button(at, startswith="Action card").click(); at.run(); no_exc(at)
    assert len(at.code) >= 1, "action card text missing"


def test_walkthrough_terrain_tab_explains_itself():
    at = goto(boot(), NAV[4])
    button(at, label="Terrain").click(); at.run(); no_exc(at)
    md = _md(at)
    assert "How to read this map" in md, "map reading guide missing"
    assert "Your ground, east to west" in md, "terrain profile heading missing"
    assert "Water here" in md, "person-vs-water gauge missing"
    assert "Plain reading" in md
    assert any(m.label and m.label.startswith("Water at the core") for m in at.metric), \
        "core water-depth metric missing"


def test_telemetry_has_freshness_and_sensor_panel():
    at = goto(boot(), NAV[3])
    no_exc(at)
    md = _md(at)
    assert ("LIVE" in md) or ("STALE" in md) or ("NO FEED" in md)
    assert any("PhilSensors" in str(s.value) for s in at.subheader)

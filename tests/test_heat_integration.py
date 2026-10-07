"""Heat carried into the other pages: Lab measures, Telemetry board, Walkthrough step, Response drill."""
from conftest import boot, button, goto, nav_labels, no_exc

NAV = nav_labels()


def _md(at):
    return " ".join(m.value for m in at.markdown)


def _txt(at):
    """Markdown plus the st.info / st.warning blocks (AppTest exposes those separately)."""
    parts = [m.value for m in at.markdown]
    parts += [w.value for w in getattr(at, "warning", [])]
    parts += [i.value for i in getattr(at, "info", [])]
    return " ".join(str(p) for p in parts)


def test_lab_heat_countermeasure_section():
    at = goto(boot(), NAV[3])
    no_exc(at)
    assert "Heat countermeasures" in _md(at)
    assert "Residents within reach" in [m.label for m in at.metric]
    assert any(str(s).startswith("Heat benefit ranking") for s in [s.value for s in at.subheader])
    next(s for s in at.slider if s.key == "lab_cool_n").set_value(8)
    at.run()
    no_exc(at)
    rows = []
    for d in at.dataframe:
        try:
            v = d.value
            if hasattr(v, "to_string"):
                rows.append(v.to_string())
        except Exception:
            continue
    assert any("Cooling network" in r and "Shade / canopy" in r for r in rows), "heat ranking table missing"


def test_walkthrough_heat_relief_step():
    at = goto(boot(), NAV[5])
    button(at, label="☀️ Heat & relief").click()
    at.run()
    no_exc(at)
    labels = [m.label for m in at.metric]
    assert "Feels like here" in labels, labels
    assert "DANGER hours (heat day)" in labels
    assert "Relief reach here" in _md(at)
    assert "cooling point" in _md(at)
    button(at, startswith="Action card").click()
    at.run()
    no_exc(at)
    assert len(at.code) >= 1, "action card step must still render after the inserted step"


def test_telemetry_heat_situation_board():
    at = goto(boot(), NAV[4])
    no_exc(at)
    md = _md(at)
    if "NO FEED" in md:
        return                      # board is live-only; the page still has to render cleanly
    assert "Heat situation & cooling reach" in md
    labels = [m.label for m in at.metric]
    for want in ("Residents in DANGER-band barangays", "Population within 2.5 km of cooling", "Cooling points open"):
        assert want in labels, labels


def test_response_heat_strip_and_heat_texts():
    at = goto(boot(), NAV[6])
    no_exc(at)
    assert "Heat now" in _md(at), "heat status strip missing under the simulator banner"
    button(at, label="☀️ Simulate 6 heat help texts").click()
    at.run()
    no_exc(at)
    import sms
    inbox = sms.load_log(sms.INBOX)
    assert len(inbox) == 6, f"expected 6 heat texts, got {len(inbox)}"
    assert inbox["body"].str.upper().str.contains("SAKLOLO|TULONG|HELP").all()
    # the requests map (with the cooling network) only draws once there is a queue
    button(at, label="Log request").click()
    at.run()
    no_exc(at)
    assert "❄ + faint ring = open cooling point" in " ".join(c.value for c in at.caption)
    assert "green pin = hospital" in " ".join(c.value for c in at.caption)


def test_heat_relief_layers_and_map_symbology():
    """OSM-derived water/shade layers exist and the heat symbology helpers render."""
    import heat
    assert len(heat.water_points()) > 0, "no water refilling stations / wells extracted"
    assert len(heat.water_areas()) > 0, "no ponds / open water extracted"
    assert len(heat.shade_areas()) > 0, "no shade polygons extracted"
    import folium
    m = folium.Map(location=(16.04, 120.34), zoom_start=12)
    heat.shade_layer(m)
    heat.water_layer(m)
    heat.cool_marker([16.04, 120.34], "open cooling").add_to(m)
    heat.cool_ring([16.04, 120.34]).add_to(m)
    heat.health_marker([16.04, 120.34], "health site").add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    html = m.get_root().render()
    assert "2744" in html, "cooling marker must be a snowflake glyph, not a circle"
    assert "cs-cool-icon" in html
    assert '"opacity": 0.3' in html or '"opacity":0.3' in html, "reach ring must stay faint"
    assert "medkit" in html, "health site must be a medical icon, not a red dot"
    assert "tint" in html, "water sources must use the droplet icon"
    assert "green areas" in html, "shade layer missing from the layer control"
    assert "water sources" in html, "water layer missing from the layer control"

    at = goto(boot(), NAV[2])
    no_exc(at)
    caps = " ".join(c.value for c in at.caption)
    assert "water sources" in caps and "shade" in caps, "heat map caption must name the new layers"


def test_heat_drill_texts_parse_to_heat_needs():
    import ops
    import sms
    brgs = ["Pantal", "Bolosan", "Carael"]
    bodies = ops.heat_drill_messages(brgs, 6, seed=2)
    parsed = [sms.parse_request(b, brgs) for _, b in bodies]
    assert all(p and p["barangay"] in brgs for p in parsed), bodies
    assert all(2 <= p["people"] <= 10 for p in parsed)
    assert all(p["need"] in ("🩹 Medical", "🍚 Food / water", "🏠 Shelter space") for p in parsed)
    assert len({b for _, b in bodies}) > 1, "drill should vary the wording"


def test_empty_cooling_register_warns_and_seeds_practice_points():
    import heat
    at = goto(boot(), NAV[2])
    no_exc(at)
    assert heat.cooling_stats()["open"] == 0, "sandbox must start with an empty register"
    assert "No cooling points registered" in _txt(at), "empty state missing on the heat map"
    button(at, label="❄ Register practice cooling points").click()
    at.run()
    no_exc(at)
    st = heat.cooling_stats()
    assert st["open"] > 10, st
    assert heat.practice_count() == st["open"], "every seeded row must be marked practice"
    df = heat.load_cooling()
    assert df["lat"].astype(str).str.len().min() > 0, "practice points need coordinates to draw rings"
    assert "No cooling points registered" not in _txt(at), "warning must clear once seeded"
    # practice candidates are labelled on the map, not passed off as verified
    assert heat.cool_note(df.iloc[0]) == " · practice candidate"

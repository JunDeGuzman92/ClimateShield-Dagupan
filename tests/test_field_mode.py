"""Field Mode: three-tap flood reports from the water line (NAV[8])."""
from datetime import date

import pandas as pd

from conftest import LAY, boot, button, goto, nav_labels, no_exc

FIELD = next(l for l in nav_labels() if "Field Report" in l)


def _on_field():
    return goto(boot(), FIELD)


def _sel(at, prefix):
    return next(s for s in at.selectbox if s.label.startswith(prefix))


def _kinds(at):
    return next(r for r in at.radio if "Flood depth" in list(getattr(r, "options", []) or []))


def test_field_page_renders_with_rescue_notice(layers):
    at = _on_field()
    no_exc(at)
    assert any("NOT a rescue channel" in w.value for w in at.warning), "the boundary must be on screen"
    assert any("no stored coordinates" in c.value for c in at.caption), "anonymity promise must be on screen"
    kinds = _kinds(at)
    assert kinds.value == "Flood depth", "default kind should be flood depth"


def test_report_reaches_pin_schema_and_map(layers):
    at = _on_field()
    _sel(at, "Barangay").set_value("Pantal")
    _sel(at, "How deep").set_value("waist-deep (impassable)")
    next(t for t in at.text_input if "sitio" in t.label).set_value("near the bridge")
    button(at, label="Send report").click()
    at.run()
    no_exc(at)

    df = pd.read_csv(LAY / "crowd_reports.csv")
    assert list(df.columns) == ["logged_at", "date", "barangay", "type", "detail", "note"], \
        "field reports must keep the crowd_reports schema (no location columns)"
    row = df.iloc[0]
    assert row["barangay"] == "Pantal" and row["type"] == "flood depth"
    assert row["detail"] == "waist-deep (impassable)"
    assert row["note"] == "near the bridge"
    assert row["date"] == str(date.today())

    # the same row must come out through the map pin pipeline, at waist-deep severity
    import kit
    pins = kit.crowd_pins(kit.anchors_map(layers.brgy_anchors))
    pin = next(p for p in pins if p["barangay"] == "Pantal")
    assert pin["detail"] == "waist-deep (impassable)" and pin["sev"] == 4


def test_kind_switch_swaps_the_detail_list(layers):
    at = _on_field()
    _kinds(at).set_value("Road state")
    at.run()
    no_exc(at)
    assert list(_sel(at, "How deep").options) == ["passable", "light vehicles only", "fully impassable"]
    _kinds(at).set_value("Banca needed")
    at.run()
    no_exc(at)
    assert list(_sel(at, "How deep").options)[0] == "gutter-deep", "banca requests keep the depth scale"

    _kinds(at).set_value("Road state")
    at.run()
    _sel(at, "Barangay").set_value("Pogo Chico")
    _sel(at, "How deep").set_value("fully impassable")
    button(at, label="Send report").click()
    at.run()
    no_exc(at)
    row = pd.read_csv(LAY / "crowd_reports.csv").iloc[0]
    assert row["type"] == "road state" and row["detail"] == "fully impassable"


def test_gps_prefill_snaps_to_the_nearest_barangay(layers):
    target = next(b for b in layers.brgy_anchors if b["anchor"] is not None)
    at = boot()
    at.query_params["flat"] = str(target["anchor"]["lat"])
    at.query_params["flon"] = str(target["anchor"]["lon"])
    at = goto(at, FIELD)
    no_exc(at)
    assert _sel(at, "Barangay").value == target["barangay"], "GPS suggestion should preselect its barangay"
    assert "flat" not in at.query_params, "coordinates must be discarded after the snap"


def test_gps_from_outside_dagupan_is_ignored(layers):
    at = boot()
    at.query_params["flat"] = "14.6000"     # Manila, not Dagupan
    at.query_params["flon"] = "121.0000"
    at = goto(at, FIELD)
    no_exc(at)
    assert any("outside Dagupan" in i.value for i in at.info)
    brgys = sorted(layers.brgy["barangay"].tolist())
    assert _sel(at, "Barangay").value == brgys[0], "far taps must not pin a Dagupan barangay"

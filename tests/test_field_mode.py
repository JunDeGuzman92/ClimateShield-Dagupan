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


def _payload(rows):
    import base64
    import json
    return base64.urlsafe_b64encode(json.dumps(rows).encode()).decode().rstrip("=")


def _good_row(brgy="Pantal", **kw):
    r = {"i": kw.pop("i", "r1"), "b": brgy, "t": "flood depth",
         "d": kw.pop("d", "knee-deep (light vehicles risky)"),
         "n": kw.pop("n", "near the bridge"), "ts": kw.pop("ts", "2026-10-08T09:05")}
    r.update(kw)
    return r


def test_ingest_queue_validates_the_form_vocabulary(layers):
    import field
    out = field.ingest_queue(layers, _payload([
        _good_row(),                                                     # accepted
        _good_row(i="r2", b="Makati"),                                   # unknown barangay
        _good_row(i="r3", t="road state"),                               # road type with a depth detail
        {"i": "r4", "b": "Pantal", "t": "road state",
         "d": "fully impassable", "n": "x<y & z", "ts": "not a date"},   # accepted, note escaped, ts now
    ]))
    assert len(out) == 2
    first = out[0]
    assert first["logged_at"] == "2026-10-08T09:05" and first["date"] == "2026-10-08"
    second = out[1]
    assert second["note"] == "x&lt;y &amp; z" and second["logged_at"] != "not a date"
    assert field.ingest_queue(layers, "!!not-base64!!") == []
    many = field.ingest_queue(layers, _payload([_good_row(i=f"r{j}", ts="2026-10-08T09:05")
                                                for j in range(20)]))
    assert len(many) == field.MAX_QUEUE_SYNC, "the batch cap must hold"


def test_offline_batch_syncs_from_any_landing_page(layers):
    at = boot()
    at.query_params["fq"] = _payload([
        _good_row(i="q1", brgy="Pantal"),
        _good_row(i="q2", brgy="Pogo Chico", t="road state", d="fully impassable", ts="2026-10-08T10:00"),
        _good_row(i="q3", b="Makati"),
    ])
    at.run()
    no_exc(at)
    df = pd.read_csv(LAY / "crowd_reports.csv")
    assert len(df) == 2, "only the two valid rows may land"
    assert df.iloc[0]["barangay"] == "Pantal" and df.iloc[1]["barangay"] == "Pogo Chico"
    assert df.iloc[1]["logged_at"] == "2026-10-08T10:00"
    assert "fq" not in at.query_params, "the batch param must be consumed"
    assert any("Synced 2" in s.value for s in at.success)
    at.run()          # a plain rerun (or refresh) must not double-log the same batch
    assert len(pd.read_csv(LAY / "crowd_reports.csv")) == 2


def test_offline_pack_matches_the_form_vocabulary(layers):
    import json
    from pathlib import Path
    import field
    root = Path(__file__).resolve().parents[1]
    html = (root / "field" / "index.html").read_text(encoding="utf-8")
    for d in field.DEPTH_DETAILS + field.ROAD_DETAILS:
        assert d in html, f"offline pack must offer the same detail: {d}"
    for k in field.FIELD_KINDS:
        assert k[1] in html, f"offline pack must offer the same type: {k[1]}"
    assert "climateshield-dagupan-jundeguzman.streamlit.app" in html, "pack must sync to the deployed app"
    anchors = (root / "field" / "anchors.js").read_text(encoding="utf-8")
    data = json.loads(anchors.split("=", 1)[1].strip().rstrip(";"))
    assert [r["b"] for r in data] == sorted(layers.brgy["barangay"].tolist()), \
        "anchors.js must be regenerated (python app\\build_field_pwa.py)"


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

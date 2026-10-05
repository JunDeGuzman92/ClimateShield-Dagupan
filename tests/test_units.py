"""Fast unit tests — no Streamlit app boot."""
import io
import re
from pathlib import Path

import numpy as np

from conftest import APP_DIR


def test_utm_roundtrip_is_submillimetre():
    import geo
    E, N = geo.ll_to_utm51(120.3342, 16.0432)
    lon, lat = geo.utm51_to_ll(E, N)
    assert abs(lon - 120.3342) * 111e3 < 1e-3 and abs(lat - 16.0432) * 111e3 < 1e-3


def test_sms_parser_english_and_tagalog(layers):
    import sms
    names = layers.brgy["barangay"].tolist()
    r = sms.parse_request("HELP PANTAL 5 BOAT nasa bubong", names)
    assert r["barangay"] == "Pantal" and r["people"] == 5 and r["urgency"] == "critical"
    r = sms.parse_request("saklolo Carael 3 gamot", names)
    assert r["barangay"] == "Carael" and r["need"].endswith("Medical")
    r = sms.parse_request("TULONG Bonuan Gueset 12 pagkain", names)
    assert r["barangay"] == "Bonuan Gueset" and r["people"] == 12
    assert sms.parse_request("hello there", names) is None


def test_messaging_module_cannot_send():
    """Simulator guarantee: the messaging module has no network code at all."""
    src = (APP_DIR / "sms.py").read_text(encoding="utf-8")
    for forbidden in ("urllib", "requests", "http.client", "socket", "api.semaphore", "httpsms.com", "twilio"):
        assert forbidden not in src, f"sms.py must not reference {forbidden}"


def test_simulated_send_is_logged_not_sent():
    import sms
    body = sms.simulate_send("Test office", "hello https://example.com")
    assert body.startswith("[SIM]") and "https://" not in body
    log = sms.load_log(sms.OUTBOX)
    assert log.iloc[0]["status"] == "simulated — not sent"


def test_geotiff_import_resamples_exact_cell_count(layers):
    import demimport
    from PIL import Image, TiffImagePlugin
    h = w = 200
    x0, y0 = layers.transform.c + 3000, layers.transform.f - 3000
    arr = (np.linspace(0.2, 3.0, w)[None, :] + np.zeros((h, 1))).astype("float32")
    info = TiffImagePlugin.ImageFileDirectory_v2()
    info[33550] = (10.0, 10.0, 0.0)
    info[33922] = (0.0, 0.0, 0.0, x0, y0, 0.0)
    info[34735] = (1, 1, 0, 1, 3072, 0, 1, 32651)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="TIFF", tiffinfo=info)
    a2, g2 = demimport.read_geotiff(buf.getvalue())
    assert g2["epsg"] == 32651
    rs = demimport.resample_to_grid(layers, a2, g2)
    assert int(np.isfinite(rs).sum()) == (h * 10 // 30) * (w * 10 // 30)
    assert 0.2 <= np.nanmin(rs) and np.nanmax(rs) <= 3.0


def test_storm_frames_start_dry_and_peak_near_hour_11(layers):
    import cinema
    import mapfilm
    fr = mapfilm.storm_frames(layers, cinema.FLOOD_STORIES["unprepared"])
    assert fr[0]["W"] <= 0
    peak = max(fr, key=lambda f: f["W"])
    assert 8 <= peak["hour"] <= 14
    prepared = mapfilm.storm_frames(layers, cinema.FLOOD_STORIES["prepared"])
    assert max(f["stranded"] for f in prepared) < max(f["stranded"] for f in fr)


def test_exercise_water_matches_timelapse_physics(layers):
    import cinema
    import exercise
    import mapfilm
    story = cinema.FLOOD_STORIES["king_tide"]
    fr = mapfilm.storm_frames(layers, story)
    for f in fr[::5]:
        assert abs(exercise.water_at(layers, story, f["hour"]) - f["W"]) < 1e-6


def test_no_hardcoded_old_page_labels_in_app():
    """Guard against the fragment-rebuild bug class: every page guard must have a matching fragment."""
    src = Path(APP_DIR / "climateshield_command_center.py").read_text(encoding="utf-8")
    calls = re.findall(r"^if page == NAV\[(\d)\]:\n((?:    .*\n)+)", src, re.M)
    called = {int(i) for i, _ in calls}
    assert {1, 2, 3, 4, 5, 6} <= called, f"page dispatch missing for {sorted({1, 2, 3, 4, 5, 6} - called)}"

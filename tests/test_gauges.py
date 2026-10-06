"""PhilSensors panel logic: reads the stored check instantly, shows readings without blocking."""


def _fake_ps():
    return dict(fetched_at="2026-10-26 20:00", stations=[
        dict(station_id="9", location="POBLACION-CALASIAO,CALASIO", type="Rain2", lat=16.0, lon=120.35,
             km_from_dagupan=4.5, last_reading="2022-05-24 13:10:05", age_hours=20000.0, live=False,
             values={"rain": "0.0 mm"}, water_level_m=None, status="TELCO"),
        dict(station_id="12", location="MACALONG BRIDGE,URDANETA CITY", type="Waterlevel & Rain 2",
             lat=15.97, lon=120.57, km_from_dagupan=25.3, last_reading="2026-10-26 18:00", age_hours=2.0,
             live=True, values={"water level": "0.56 m"}, water_level_m=0.56, status="OK"),
        dict(station_id="13", location="DEAD STATION", type="Rain2", error="TimeoutError"),
    ])


def test_summary_splits_counts_and_sorts():
    import gauges
    s = gauges.summary(_fake_ps())
    assert s["live_n"] == 1 and s["water_n"] == 1
    assert len(s["errs"]) == 1 and len(s["sts"]) == 2
    assert list(s["rows"]["station"]) == ["POBLACION-CALASIAO,CALASIO", "MACALONG BRIDGE,URDANETA CITY"]
    assert s["rows"].iloc[0]["age"].endswith("yr"), "old readings must read in years, not thousands of days"
    assert s["newest"].startswith("2026-10-26")


def test_summary_handles_empty_or_missing():
    import gauges
    s = gauges.summary(None)
    assert s["live_n"] == 0 and s["newest"] == "—" and len(s["rows"]) == 0
    s = gauges.summary(dict(fetched_at="x", stations=[]))
    assert s["live_n"] == 0


def test_read_cache_roundtrip(tmp_path, monkeypatch):
    import json

    import gauges
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"ts": 1, "stations": []}), encoding="utf-8")
    monkeypatch.setattr(gauges, "CACHE", p)
    assert gauges.read_cache()["ts"] == 1
    monkeypatch.setattr(gauges, "CACHE", tmp_path / "missing.json")
    assert gauges.read_cache() is None

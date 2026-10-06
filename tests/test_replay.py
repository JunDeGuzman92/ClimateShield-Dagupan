"""Historical storm replay: model calibration and frames."""
def test_calibration_anchors(layers):
    import mapfilm
    import replay
    s_cal = replay.build_story(layers, "habagat_2026", "as_happened")
    fr = mapfilm.storm_frames(layers, s_cal)
    pk = max(fr, key=lambda f: f["W"])
    assert 42 <= layers.flooded_share(pk["W"]) <= 48, "Aug 2026 must land near the 45% Calamity anchor"
    s_ext = replay.build_story(layers, "pepeng_2009", "as_happened")
    fr = mapfilm.storm_frames(layers, s_ext)
    pk = max(fr, key=lambda f: f["W"])
    assert 62 <= layers.flooded_share(pk["W"]) <= 68, "Pepeng 2009 must land near the 65% Extreme anchor"


def test_replay_frames_use_calendar_labels_and_start_sensibly(layers):
    import mapfilm
    import replay
    st_ = replay.build_story(layers, "egay_2023", "as_happened")
    fr = mapfilm.storm_frames(layers, st_)
    assert len(fr) <= 48
    assert fr[0]["W"] <= 0.35, "first frame should be near-dry (replays start at the event window)"
    assert all(":" in f.get("label", "") for f in fr), "replay frames must carry calendar labels"
    assert any(f["W"] > 0 for f in fr)


def test_replay_water_never_dips_below_the_dry_stage(layers):
    """Regression: early-window storage barely above onset once mapped tiny shares onto the raw DEM's
    negative sliver (down to −2 m), showing 'water at −1.8 m'. The floor is the dry stage."""
    import replay
    for key in replay.EVENTS:
        st_ = replay.build_story(layers, key, "as_happened")
        assert min(st_["W_series"]) >= -0.36, f"{key}: water dips to {min(st_['W_series']):.2f}"
    assert exercise_water_matches_frames(layers, "habagat_2026")


def exercise_water_matches_frames(layers, key):
    import exercise
    import numpy as np
    import replay
    st_ = replay.build_story(layers, key, "as_happened")
    return all(exercise.water_at(layers, st_, h) >= -0.36 for h in np.arange(0, 100, 2.0))


def test_prepared_city_floods_less(layers):
    import mapfilm
    import replay
    peaks = {}
    for rd in ("as_happened", "prepared"):
        st_ = replay.build_story(layers, "pepeng_2009", rd)
        peaks[rd] = layers.flooded_share(max(fr["W"] for fr in mapfilm.storm_frames(layers, st_)))
    assert peaks["prepared"] < peaks["as_happened"] - 15


def test_exercise_runs_on_replay_story(layers):
    from datetime import datetime, timedelta
    import exercise
    import json
    import replay
    st_ = replay.build_story(layers, "habagat_2026", "as_happened")
    assert exercise.water_at(layers, st_, st_["peak_h"]) > 0
    exercise.start(layers, st_, 96, ["Pantal"], "replay team")
    p = exercise.STATE
    s = json.loads(p.read_text(encoding="utf-8"))
    s["started_at"] = (datetime.fromisoformat(s["started_at"]) - timedelta(minutes=1.2)).isoformat(timespec="seconds")
    p.write_text(json.dumps(s), encoding="utf-8")
    s, fired = exercise.tick(layers)
    assert fired and fired[0]["id"] == "E1"
    hh = exercise.sim_hour(s)
    assert exercise.water_at(layers, st_, hh) > 0, "flood conditions should follow the replay series"
    e6 = next(e for e in s["events"] if e["id"] == "E6")
    assert abs(e6["h"] - st_["peak_h"]) < 6, "peak event must sit on the replay's peak"
    exercise.stop(layers)

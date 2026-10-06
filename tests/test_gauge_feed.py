"""Gauge feed intake: parse_gauge_text (spec format) incl. official thresholds."""
GOOD = """logged_at,level_m,note,alert_m,alarm_m,critical_m
2026-08-10 06:00,0.72,normal,0.9,1.3,1.7
2026-08-10 09:00,1.05,sitrep
2026-08-10 12:00,1.44,impassable
garbage-row-not-a-date,NaN,dropped
"""


def test_parses_rows_and_official_thresholds():
    import kit
    df, th, msg = kit.parse_gauge_text(GOOD)
    assert df is not None and msg is None
    assert len(df) == 3, "the garbage row must drop, keep valid 3"
    assert df.iloc[-1]["level_m"] == 1.44
    assert th == dict(alert=0.9, alarm=1.3, critical=1.7), "feed thresholds must be picked up"


def test_alternative_column_names_and_no_thresholds():
    import kit
    df, th, msg = kit.parse_gauge_text("time,stage_m\n2026-10-01 10:00,1.2\n2026-10-01 11:00,0.4\n")
    assert df is not None and th is None and len(df) == 2
    assert df["level_m"].tolist() == [1.2, 0.4]


def test_garbage_is_rejected_with_a_helpful_message():
    import kit
    df, th, msg = kit.parse_gauge_text("a,b\n1,2\n")
    assert df is None and msg and "GAUGE_FEED_SPEC" in msg


def test_provided_thresholds_drive_classification():
    import kit
    _, th, _ = kit.parse_gauge_text(GOOD)
    s140, _ = kit.gauge_class(1.40, alert=th["alert"], alarm=th["alarm"], critical=th["critical"])
    s100, _ = kit.gauge_class(1.00, alert=th["alert"], alarm=th["alarm"], critical=th["critical"])
    s185, _ = kit.gauge_class(1.85, alert=th["alert"], alarm=th["alarm"], critical=th["critical"])
    s050, _ = kit.gauge_class(0.50, alert=th["alert"], alarm=th["alarm"], critical=th["critical"])
    assert s140.upper().startswith("ALARM"), "1.40 m sits between feed alarm 1.3 and critical 1.7"
    assert s100.upper().startswith("ALERT"), "1.00 m sits between feed alert 0.9 and alarm 1.3"
    assert s185.upper().startswith("CRITICAL"), "1.85 m is past the feed critical 1.7"
    assert s050.upper().startswith("MONITOR"), "0.50 m is below the feed alert"

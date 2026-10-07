"""Resident escalation (ignored texts nag) and the run debrief figure."""
from datetime import datetime, timedelta

from conftest import LAY
from test_missions import _start, _tick_all, _units


def _age_inbox(minutes):
    """Backdate every message's receipt by `minutes` of REAL time (escalation needs receipt age)."""
    import pandas as pd
    import sms
    df = sms.load_log(sms.INBOX)
    if len(df):
        df["at"] = [(datetime.fromisoformat(a) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
                    for a in df["at"]]
        df.to_csv(sms.INBOX, index=False)


def test_ignored_texts_escalate_up_to_twice(layers):
    import sms
    _units([dict(type="🚤 Rubber boat", name="Boat 1", location="Pantal")])
    _start(layers, speed=4)
    sms.simulate_inbound("Simulated resident #1", "HELP PANTAL 4 BOAT nasa bubong")
    _age_inbox(6.5 / 4)          # 6.5 storm-hours of being ignored at ×4
    _tick_all(layers, n=1, mins=0.02)
    inbox = sms.load_log(sms.INBOX)
    msgs = inbox[inbox["sender"] == "Simulated resident #1"]
    assert len(msgs) == 2, "first follow-up missing"
    assert "TUMATAAS" in msgs.iloc[0]["body"].upper()
    _age_inbox(12.5 / 4)         # 12.5 storm-hours ignored
    _tick_all(layers, n=1, mins=0.02)
    msgs = sms.load_log(sms.INBOX)
    msgs = msgs[msgs["sender"] == "Simulated resident #1"]
    assert len(msgs) == 3, "second follow-up missing"
    assert "BATA" in msgs.iloc[0]["body"].upper()
    _age_inbox(20 / 4)
    _tick_all(layers, n=1, mins=0.02)
    msgs = sms.load_log(sms.INBOX)[lambda d: d["sender"] == "Simulated resident #1"]
    assert len(msgs) == 3, "escalation must stop after two follow-ups"


def test_handled_texts_do_not_escalate(layers):
    import sms
    _start(layers, speed=4)
    sms.simulate_inbound("Simulated resident #2", "HELP PANTAL 4 BOAT nasa bubong")
    sms.mark_handled(sms.load_log(sms.INBOX).iloc[0]["msg_id"])
    _age_inbox(7 / 4)
    _tick_all(layers, n=1, mins=0.02)
    msgs = sms.load_log(sms.INBOX)[lambda d: d["sender"] == "Simulated resident #2"]
    assert len(msgs) == 1, "handled texts must not nag"


def test_debrief_figure_renders_the_run(layers):
    import exercise
    import response as rsp
    _units([dict(type="🚤 Rubber boat", name="Boat 1", location="Pantal")])
    _start(layers)
    rid = rsp.add_request("Pantal", 4, "🚤 Rescue boat / evacuation", "critical", "sim", "")
    exercise.assign(layers, exercise.load(), "U001", rid)
    _tick_all(layers, n=6, mins=0.09)
    st_, sc = exercise.stop(layers)
    fig, png = exercise.debrief_figure(layers, st_)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 20000
    assert st_["final_score"]["kpis"]["requests"] == 1
    ax = fig.axes[0]
    labs = [t.get_text() for t in ax.texts if t.get_text().startswith("E")]
    assert labs, "event labels missing from the debrief chart"
    ys = {round(t.get_position()[1], 3) for t in ax.texts if t.get_text().startswith("E")}
    assert len(ys) >= 2, "event labels must stagger at two heights"
    tables = [c for c in fig.axes[1].get_children() if type(c).__name__ == "Table"]
    assert tables, "score rows must use an auto-layout Table (hand-stacked text overlapped the footer)"
    leg = ax.get_legend()
    fig.canvas.draw()
    leg_bb, title_bb = leg.get_window_extent(), ax.title.get_window_extent()
    assert not leg_bb.overlaps(title_bb), "legend must not cover the chart title"
    assert not leg_bb.overlaps(ax.get_window_extent()), "legend must not cover the plot area"

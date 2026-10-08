"""Telegram field bot: the whole conversation, driven without touching the network."""
import pandas as pd

import field_bot
from conftest import LAY


def _bot(layers):
    sent = []

    def api(method, **kw):
        sent.append((method, kw))
        return {"ok": True}

    return field_bot.FieldBot(layers, api=api), sent


def _texts(sent):
    return [kw.get("text", "") for m, kw in sent if m == "sendMessage"]


def _msg(text=None, loc=None, chat=1):
    return {"message": {"chat": {"id": chat}, **({"text": text} if text else {}),
                       **({"location": loc} if loc else {})}}


def _cb(data, chat=1):
    return {"callback_query": {"id": "c1", "data": data, "message": {"chat": {"id": chat}}}}


def test_start_announces_the_rescue_boundary(layers):
    bot, sent = _bot(layers)
    bot.handle_update(_msg(text="/start"))
    assert any("NOT a rescue channel" in t for t in _texts(sent)), "boundary first, always"


def test_full_conversation_from_location_to_csv(layers):
    target = next(b for b in layers.brgy_anchors if b["anchor"] is not None)
    bot, sent = _bot(layers)
    bot.handle_update(_msg(text="/start"))
    bot.handle_update(_msg(loc={"latitude": target["anchor"]["lat"],
                                "longitude": target["anchor"]["lon"]}))
    assert any(f"Barangay {target['barangay']} noted" in t for t in _texts(sent))
    bot.handle_update(_cb("k:fd"))
    bot.handle_update(_cb("d:3"))                       # waist-deep
    assert any("waist-deep (impassable)" not in t and "Any note" in t for t in _texts(sent))
    bot.handle_update(_cb("skip"))
    assert any("Ready to log" in t for t in _texts(sent))
    bot.handle_update(_cb("done"))

    df = pd.read_csv(LAY / "crowd_reports.csv")
    assert len(df) == 1
    row = df.iloc[0]
    assert row["barangay"] == target["barangay"]
    assert row["type"] == "flood depth" and row["detail"] == "waist-deep (impassable)"
    assert str(row["note"]) in ("nan", "")
    assert any("salamat, kapitid" in t for t in _texts(sent))


def test_road_state_conversation_keeps_the_vocabulary(layers):
    bot, sent = _bot(layers)
    bot.handle_update(_msg(text="/start"))
    bot.handle_update(_msg(text="pantal"))              # lowercase, real users type this
    bot.handle_update(_cb("k:rd"))
    assert any("What state is the road?" in t for t in _texts(sent))
    bot.handle_update(_cb("d:1"))                       # light vehicles only
    bot.handle_update(_msg(text="at the crossing <b>"))
    bot.handle_update(_cb("done"))
    row = pd.read_csv(LAY / "crowd_reports.csv").iloc[0]
    assert row["barangay"] == "Pantal" and row["type"] == "road state"
    assert row["detail"] == "light vehicles only" and row["note"] == "at the crossing &lt;b&gt;"


def test_barangay_aliases_resolve_like_the_app(layers):
    bot, sent = _bot(layers)
    bot.handle_update(_msg(text="/start"))
    bot.handle_update(_msg(text="bugallon"))           # notebook-era alias for Barangay I
    assert any("Barangay I noted" in t for t in _texts(sent))


def test_unknown_barangay_gets_a_retry_not_a_row(layers):
    bot, sent = _bot(layers)
    bot.handle_update(_msg(text="/start"))
    bot.handle_update(_msg(text="Makati"))
    assert any("Did not catch that barangay" in t for t in _texts(sent))
    bot.handle_update(_msg(text="Makati City"))
    assert not (LAY / "crowd_reports.csv").exists(), "nothing may be logged without a resolved barangay"


def test_typed_detail_is_refused_so_pins_stay_readable(layers):
    bot, sent = _bot(layers)
    bot.handle_update(_msg(text="/start"))
    bot.handle_update(_msg(text="Pantal"))
    bot.handle_update(_cb("k:fd"))
    n = len(sent)
    bot.handle_update(_msg(text="about neck-deep"))
    assert any("pick from the buttons" in t for t in _texts(sent)), "free-text depth must not enter the CSV"
    assert not (LAY / "crowd_reports.csv").exists()

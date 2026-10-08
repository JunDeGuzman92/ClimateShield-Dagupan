"""Telegram channel for field reports: a chat where a crew member reports with no app at all.

Runs beside the command center on the ops-room laptop (`run_bot.bat`) and writes to that
machine's crowd_reports.csv - the same file the maps read - so bot reports pin like any
other. Long-polling only: no public webhook, no server account, no new dependencies.

Anonymous by design: chat state lives in memory for the conversation only, no names or chat
ids are ever written, and the report row stores the barangay, type, detail and note alone.
Like every reporting channel here, the first message says this is NOT a rescue channel.

Setup (once): in Telegram, talk to @BotFather -> /newbot -> copy the token -> either set the
CS_TG_TOKEN environment variable or paste the token as the single line in
data/app_layers/bot_token.txt (gitignored). Then `python app\\field_bot.py` (or run_bot.bat).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

import data_core as dc
import field

TG_API = "https://api.telegram.org/bot{token}/{method}"

KIND_BTNS = [("Flood depth", "fd"), ("Road state", "rd"), ("Banca needed", "bk")]
KMAP = {"fd": "flood depth", "rd": "road state", "bk": "banca/rescue request"}

WELCOME = ("ClimateShield field reporting for Dagupan.\n"
           "This bot feeds the community flood map. It is NOT a rescue channel - if lives are "
           "at risk, call the CDRRMO or emergency lines directly.\n"
           "Which barangay? Type the name (e.g., Pantal) or send your \U0001F4CD location.")
TOKEN_HELP = ("No bot token found. In Telegram, talk to @BotFather -> /newbot -> copy the token, "
              "then set the CS_TG_TOKEN environment variable, or paste the token as the only "
              "line into data/app_layers/bot_token.txt (gitignored), and run this again.")


def bot_token():
    """Env var first, then the gitignored one-line file."""
    tok = os.environ.get("CS_TG_TOKEN", "").strip()
    if tok:
        return tok
    try:
        return (dc.LAYERS / "bot_token.txt").read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _tg(token, method, payload, timeout=35):
    """One Telegram API call. Returns the parsed reply, never assumes success."""
    url = TG_API.format(token=token, method=method)
    req = urllib.request.Request(url, data=json.dumps(payload or {}).encode(),
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def match_barangay(L, text):
    """Barangay names the way the table stores them, plus the app's alias list. Typed 'pantal'
    and 'bugallon' both resolve; 'Makati' must never land a barangay, so nothing here does
    loose substring matching (a normalized 'Barangay I' is just 'i' - inside half of Manila)."""
    t = dc._norm(text)
    if not t:
        return None
    names = sorted(L.brgy["barangay"].tolist())

    def alias_keys(n):
        low = str(n).lower()
        keys = set(dc._alias.get(low, []))
        keys.update(dc._alias.get(dc._norm(low), []))
        # the alias table was written for the notebook-era names, e.g. 'barangay i (t. bugallon)'
        for k, vals in dc._alias.items():
            if k == low or k.startswith(low + " ") or k.startswith(low + "("):
                keys.update(vals)
        return keys

    for n in names:                                   # exact after normalization
        if dc._norm(n) == t:
            return n
    for n in names:                                   # exact alias hits
        if t in alias_keys(n):
            return n
    if len(t) >= 3:                                    # word-boundary prefixes, both ways
        for n in names:
            nm = dc._norm(n)
            if len(nm) >= 3 and (nm.startswith(t) or t.startswith(nm)):
                return n
    return None


class FieldBot:
    """Conversation state machine; every Telegram detail is behind the injected api callable,
    so tests drive whole conversations without touching the network."""

    def __init__(self, L, api=None):
        self.L, self.api, self.sessions = L, api, {}
        self.token = ""
        if self.api is None:
            self.token = bot_token()
            if not self.token:
                raise SystemExit(TOKEN_HELP)
            self.api = lambda m, **kw: _tg(self.token, m, kw)

    # ---- telegram glue -------------------------------------------------------
    def _send(self, chat, text, markup=None):
        self.api("sendMessage", chat_id=chat, text=text,
                 **({"reply_markup": markup} if markup else {}))

    def _answer(self, cb_id):
        if cb_id:
            self.api("answerCallbackQuery", callback_query_id=cb_id)

    @staticmethod
    def _kb(rows):
        return {"inline_keyboard": rows}

    # ---- steps ---------------------------------------------------------------
    def _ask_kind(self, chat):
        self._send(chat, "What do you see?",
                   self._kb([[(b, f"k:{c}") for b, c in KIND_BTNS]]))

    def _set_brgy(self, chat, brgy):
        self.sessions[chat].update({"step": "kind", "brgy": brgy})
        self._send(chat, f"Barangay {brgy} noted. What do you see?",
                   self._kb([[(b, f"k:{c}") for b, c in KIND_BTNS]]))

    def handle_update(self, u):
        msg, cb = u.get("message") or {}, u.get("callback_query") or {}
        chat = (msg.get("chat") or {}).get("id") or ((cb.get("message") or {}).get("chat") or {}).get("id")
        if chat is None:
            return
        text = (msg.get("text") or "").strip()
        loc = msg.get("location") or {}
        if cb:
            self._answer(cb.get("id"))
        code = cb.get("data") or ""
        s = self.sessions.setdefault(chat, {"step": "brgy"})

        if text in ("/start", "/cancel"):
            self.sessions[chat] = {"step": "brgy"}
            self._send(chat, WELCOME)
            return
        if loc:
            brgy, _km = field.nearest_barangay(self.L, loc.get("latitude", 0),
                                                loc.get("longitude", 0))
            if brgy:
                self._set_brgy(chat, brgy)
            else:
                self._send(chat, "That location looks outside Dagupan - type the barangay instead.")
            return

        if s["step"] == "brgy" and text:
            brgy = match_barangay(self.L, text)
            if brgy:
                self._set_brgy(chat, brgy)
            else:
                self._send(chat, "Did not catch that barangay. Type it like 'Pantal', or send your location.")
            return
        if s["step"] == "kind" and code.startswith("k:"):
            rtype = KMAP.get(code[2:])
            if not rtype:
                return
            details = field.ROAD_DETAILS if rtype == "road state" else field.DEPTH_DETAILS
            s.update({"step": "detail", "type": rtype})
            self._send(chat, "What state is the road?" if rtype == "road state" else "How deep?",
                       self._kb([[(d, f"d:{i}")] for i, d in enumerate(details)]))
            return
        if s["step"] == "detail":
            if code.startswith("d:"):
                details = field.ROAD_DETAILS if s["type"] == "road state" else field.DEPTH_DETAILS
                try:
                    d = details[int(code[2:])]
                except (IndexError, ValueError):
                    return
                s.update({"step": "note", "detail": d})
                self._send(chat, "Any note (sitio, landmark, banca count)? Tap Skip, or type it in one message.",
                           self._kb([[("Skip", "skip")]]))
            elif text:      # typed instead of tapping: re-offer the buttons, vocabulary stays exact
                self._send(chat, "Please pick from the buttons so the map reads it correctly.")
            return
        if s["step"] == "note":
            if code == "skip":
                s["note"] = ""
            elif text:
                s["note"] = field._clean_note(text)
            else:
                return
            s["step"] = "confirm"
            self._send(chat, f"Ready to log:\n{s['brgy']} · {s['type']} · {s['detail']}"
                             + (f"\nnote: {s['note']}" if s["note"] else "\nnote: none"),
                       self._kb([[("Send", "done")], [("Cancel", "cancel")]]))
            return
        if s["step"] == "confirm" and code in ("done", "cancel"):
            if code == "cancel":
                self.sessions.pop(chat, None)
                self._send(chat, "Cancelled. /start to try again.")
                return
            field.append_report(s["brgy"], s["type"], s["detail"], s.get("note", ""))
            self.sessions.pop(chat, None)
            self._send(chat, "Report logged - salamat, kapitid! The map at the barangay hall "
                            "picks it up on the next refresh. /start to log another one.")


def _loop(L, token, timeout=25):
    api = lambda m, **kw: _tg(token, m, kw)
    fb = FieldBot(L, api=api)
    print("Field bot listening (Ctrl+C to stop). Reports land in this machine's crowd_reports.csv.")
    offset = 0
    while True:
        try:
            res = api("getUpdates", offset=offset, timeout=timeout)
            for u in (res or {}).get("result", []):
                offset = max(offset, u.get("update_id", 0) + 1)
                fb.handle_update(u)
        except KeyboardInterrupt:
            print("Field bot stopped. Salamat!")
            return
        except urllib.error.HTTPError as e:
            if e.code in (401, 404):      # Telegram rejecting the token: retrying cannot fix this
                print("Telegram rejected this token (HTTP " + str(e.code) + "). Check the token in "
                      "data/app_layers/bot_token.txt (one line, no spaces or quotes) and run this again.")
                return
            print(f"Telegram hiccup ({type(e).__name__} {e.code}) - retrying in 5s")
            time.sleep(5)
        except Exception as e:
            print(f"Telegram hiccup ({type(e).__name__}) - retrying in 5s")
            time.sleep(5)


def main():
    token = bot_token()
    if not token:
        print(TOKEN_HELP)
        sys.exit(1)
    _loop(dc.Layers(), token)


if __name__ == "__main__":
    main()

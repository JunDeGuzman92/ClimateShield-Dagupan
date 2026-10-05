"""SIMULATED messaging — no network calls, nothing ever leaves this computer.

This module only parses and logs messages for the response simulator:
  * inbound "texts" are created by the simulator (drill injector / test box), never received from a network
  * outbound "texts" (dispatch, alerts) are written to a local log marked SIMULATED — never sent
There is intentionally no gateway/API code here. If real messaging is ever wanted, it must be a separate,
reviewed change with agency agreement.
"""
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
OUTBOX = LAY / "sim_outbox.csv"
INBOX = LAY / "sim_inbox.csv"
CONTACTS = LAY / "sim_contacts.csv"

NEEDS_KEYWORDS = {
    "BOAT": "🚤 Rescue boat / evacuation", "BANCA": "🚤 Rescue boat / evacuation", "BANGKA": "🚤 Rescue boat / evacuation",
    "RESCUE": "🚤 Rescue boat / evacuation", "MED": "🩹 Medical", "MEDICAL": "🩹 Medical", "GAMOT": "🩹 Medical",
    "FIRE": "🔥 Fire", "SUNOG": "🔥 Fire", "FOOD": "🍚 Food / water", "WATER": "🍚 Food / water",
    "PAGKAIN": "🍚 Food / water", "TUBIG": "🍚 Food / water", "SHELTER": "🏠 Shelter space",
}
TRIGGER_WORDS = ("HELP", "SAKLOLO", "TULONG", "RESCUE")
TAG = "[SIM]"


def clean_body(text):
    t = re.sub(r"https?://\S+|www\.\S+", "[link removed]", str(text)).strip()
    return t if t.startswith(TAG) else f"{TAG} {t}"


def _log(path, row):
    df = pd.read_csv(path, dtype=str).fillna("") if path.exists() else pd.DataFrame()
    pd.concat([pd.DataFrame([row]), df], ignore_index=True).to_csv(path, index=False)


def load_log(path):
    return pd.read_csv(path, dtype=str).fillna("") if path.exists() else pd.DataFrame()


def simulate_send(to_label, text, purpose=""):
    """Record a simulated outgoing message. Never transmits anything."""
    body = clean_body(text)
    _log(OUTBOX, dict(at=datetime.now().isoformat(timespec="seconds"), to=str(to_label), body=body,
                      status="simulated — not sent", purpose=purpose))
    return body


def simulate_broadcast(barangays, text):
    c = load_contacts()
    sel = c[c["barangay"].isin(barangays) | ("ALL" in barangays)] if len(c) else c
    for _, r in sel.iterrows():
        simulate_send(f"{r['name']} ({r['barangay']})", text, purpose="alert")
    return len(sel)


def load_contacts():
    if CONTACTS.exists():
        return pd.read_csv(CONTACTS, dtype=str).fillna("")
    df = pd.DataFrame(columns=["name", "barangay", "role"])
    df.to_csv(CONTACTS, index=False)
    return df


def save_contacts(df):
    df.to_csv(CONTACTS, index=False)


def parse_request(text, barangays):
    """'HELP PANTAL 5 BOAT near bridge' / 'SAKLOLO Carael 3 gamot' → dict or None."""
    t = str(text or "").strip()
    words = t.upper().split()
    if not words or words[0] not in TRIGGER_WORDS:
        return None
    rest = t.split(None, 1)[1] if len(t.split(None, 1)) > 1 else ""
    brgy = None
    for b in sorted(barangays, key=len, reverse=True):
        if re.search(r"\b" + re.escape(b.upper()) + r"\b", rest.upper()):
            brgy = b
            break
    m = re.search(r"\b(\d{1,3})\b", rest)
    people = int(m.group(1)) if m else 1
    need = "🚤 Rescue boat / evacuation"
    for k, v in NEEDS_KEYWORDS.items():
        if re.search(r"\b" + k + r"\b", rest.upper()):
            need = v
            break
    urgency = "critical" if any(w in rest.upper() for w in ("BUBONG", "ROOF", "LUNOD", "DROWN", "BUNTIS", "PREGNANT", "BATA", "CHILD", "DIBDIB")) else "high"
    return dict(barangay=brgy, people=people, need=need, urgency=urgency, note=rest[:120])


def simulate_inbound(sender, body):
    row = dict(msg_id=f"SIM-{datetime.now().strftime('%H%M%S%f')}", at=datetime.now().isoformat(timespec="seconds"),
               sender=sender, body=body, handled="False")
    _log(INBOX, row)
    return row


def mark_handled(msg_id):
    df = load_log(INBOX)
    if len(df):
        df.loc[df["msg_id"] == msg_id, "handled"] = "True"
        df.to_csv(INBOX, index=False)

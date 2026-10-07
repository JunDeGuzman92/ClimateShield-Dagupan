"""Community/team feedback loop for drills + walkthrough cards.

Notes are stored locally (data/app_layers/feedback_notes.csv) with no personal-data requirement —
the author field is optional and meant for role/team, never required names. Used to close the
loop between simulated exercises and real barangay experience.
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

LAY = Path(__file__).resolve().parents[1] / "data" / "app_layers"
NOTES = LAY / "feedback_notes.csv"
COLS = ["at", "context", "barangay", "rating", "worked", "change", "author"]


def log(context, barangay="", rating=3, worked="", change="", author=""):
    df = list_notes()
    row = dict(at=datetime.now().isoformat(timespec="minutes"), context=str(context),
               barangay=str(barangay), rating=int(rating), worked=str(worked),
               change=str(change), author=str(author or "—"))
    out = pd.concat([pd.DataFrame([row]), df], ignore_index=True)
    out.to_csv(NOTES, index=False)
    return len(out)


def list_notes(context=None, limit=50):
    if NOTES.exists():
        try:
            df = pd.read_csv(NOTES, dtype=str).fillna("")
        except Exception:
            df = pd.DataFrame(columns=COLS)
    else:
        df = pd.DataFrame(columns=COLS)
    if context:
        df = df[df["context"].str.startswith(str(context))]
    return df.head(limit).reset_index(drop=True)


def summary():
    """(avg_rating, n) over all notes — None when empty."""
    df = list_notes(limit=10_000)
    if not len(df):
        return None
    return dict(avg=float(pd.to_numeric(df["rating"], errors="coerce").mean()),
                n=int(len(df)))

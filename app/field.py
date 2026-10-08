"""Field Mode: a three-tap flood report for tanods and banca crews on their phones.

Two capture paths share one file:
- The Streamlit page below, when the phone has data.
- The offline field pack (a small PWA served from GitHub Pages, see field/ in the repo): it
  queues reports in the phone's own storage with no signal, then syncs them here through an
  ?fq= batch (base64 JSON, capped at MAX_QUEUE_SYNC) whenever connectivity returns.

Both write the same crowd_reports.csv the command-center maps already read, so a report filed
at the water line shows up as a pin in the barangay hall within minutes.

Anonymous by design: no login, no name, no stored coordinates - the optional GPS tap only
picks the nearest barangay from its OSM anchor and is then discarded.
This page is community telemetry, never a rescue channel, and says so on screen.
"""
import base64
import json
from datetime import date, datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import kit

CR = kit.CR_CROWD
FIELD_PWA_URL = "https://jundeguzman92.github.io/ClimateShield-Dagupan/"   # offline pack (GitHub Pages)
MAX_QUEUE_SYNC = 12          # reports per offline batch; the PWA syncs newest first

DEPTH_DETAILS = [
    "gutter-deep",
    "ankle-deep",
    "knee-deep (light vehicles risky)",
    "waist-deep (impassable)",
    "chest-deep+ (life-safety)",
]
ROAD_DETAILS = ["passable", "light vehicles only", "fully impassable"]

# (radio label, the type string already used in crowd_reports.csv, detail options)
FIELD_KINDS = [
    ("Flood depth", "flood depth", DEPTH_DETAILS),
    ("Road state", "road state", ROAD_DETAILS),
    ("Banca needed", "banca/rescue request", DEPTH_DETAILS),
]

GPS_MAX_KM = 6.0    # a tap farther than this from any barangay anchor is not ours to guess

_GPS_BUTTON = """
<script>
function csFieldGps() {
  if (!navigator.geolocation) { return; }
  navigator.geolocation.getCurrentPosition(function (p) {
    try {
      var u = new URL(parent.location.href);
      u.searchParams.set("flat", p.coords.latitude.toFixed(5));
      u.searchParams.set("flon", p.coords.longitude.toFixed(5));
      parent.location.href = u.href;
    } catch (e) { /* embedded elsewhere: no GPS prefill, form still works */ }
  });
}
</script>
<button onclick="csFieldGps()"
 style="width:100%;padding:14px 18px;font-size:17px;font-weight:700;color:#fff;
 background:#16a34a;border:0;border-radius:10px;cursor:pointer;">
&#128205; Use my location (sets the barangay only)</button>
"""


def nearest_barangay(L, lat, lon, max_km=GPS_MAX_KM):
    """(barangay, km) of the closest anchored barangay centre, or (None, None) beyond max_km."""
    best, best_m = None, 1e12
    try:
        x, y = L.to_utm(float(lon), float(lat))
    except Exception:
        return None, None
    for b in L.brgy_anchors:
        a = b["anchor"]
        if a is None:
            continue
        ax, ay = L.to_utm(a["lon"], a["lat"])
        d = (x - ax) ** 2 + (y - ay) ** 2
        if d < best_m:
            best_m, best = d, b["barangay"]
    if best is None or (best_m ** 0.5) / 1000.0 > max_km:
        return None, None
    return best, (best_m ** 0.5) / 1000.0


def append_report(barangay, rtype, detail, note="", path=CR):
    """One row in the exact schema the Telemetry board and the map pins already read."""
    new = pd.DataFrame(
        [[datetime.now().isoformat(timespec="minutes"), str(date.today()),
          barangay, rtype, detail, note]],
        columns=["logged_at", "date", "barangay", "type", "detail", "note"])
    if path.exists():
        pd.concat([new, pd.read_csv(path)]).to_csv(path, index=False)
    else:
        new.to_csv(path, index=False)
    return new


def _clean_note(s, limit=120):
    """Notes end up inside map tooltips, so angle brackets never survive the trip."""
    s = str(s or "").strip()[:limit]
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _sane_ts(ts):
    try:
        datetime.fromisoformat(str(ts))
        return True
    except Exception:
        return False


def ingest_queue(L, fq):
    """Validate an offline batch (?fq= base64url JSON list) into crowd-report rows.

    Everything the form could have sent is checked against the same vocabulary the app uses,
    notes are escaped, the batch is capped, and timestamps fall back to now when a phone's
    clock is missing or wrong. Returns the accepted rows (possibly empty), never raises.
    """
    try:
        fq = str(fq).strip()
        rows = json.loads(base64.urlsafe_b64decode(fq + "=" * (-len(fq) % 4)))
        if not isinstance(rows, list):
            return []
    except Exception:
        return []
    brgys = set(L.brgy["barangay"].tolist())
    types = {k[1] for k in FIELD_KINDS}
    out = []
    for r in rows[:MAX_QUEUE_SYNC]:
        if not isinstance(r, dict):
            continue
        b, t, d = str(r.get("b", "")), str(r.get("t", "")), str(r.get("d", ""))
        if b not in brgys or t not in types:
            continue
        valid = ROAD_DETAILS if t == "road state" else DEPTH_DETAILS
        if d not in valid:
            continue
        ts = str(r.get("ts", "") or "")
        ok_ts = _sane_ts(ts)
        out.append({
            "id": str(r.get("i", ""))[:36],
            "logged_at": ts[:16] if ok_ts else datetime.now().isoformat(timespec="minutes"),
            "date": ts[:10] if ok_ts else str(date.today()),
            "barangay": b, "type": t, "detail": d, "note": _clean_note(r.get("n", "")),
        })
    return out


def maybe_ingest(L):
    """Module-level hook: the offline pack lands on any page with ?fq=<batch>, so ingestion
    cannot wait for this page to be open. Writes the batch, confirms back to the pack
    (?synced=ids, which clears them on the phone), and stops the run there - a sync visit
    is a quick round trip, not a browsing session."""
    fq = st.query_params.get("fq", "")
    if "fq" in st.query_params:
        del st.query_params["fq"]
    if not fq:
        return
    if fq in st.session_state.setdefault("cs_fq_seen", []):
        return          # same batch reloaded - already ingested, do not double-log
    st.session_state["cs_fq_seen"].append(fq)
    rows = ingest_queue(L, fq)
    if not rows:
        st.error("That offline sync did not contain usable reports. Nothing was written.")
        st.stop()
    new = pd.DataFrame(rows)[["logged_at", "date", "barangay", "type", "detail", "note"]]
    if CR.exists():
        pd.concat([new, pd.read_csv(CR)]).to_csv(CR, index=False)
    else:
        new.to_csv(CR, index=False)
    ids = ",".join(r["id"] for r in rows if r["id"])
    back = FIELD_PWA_URL + "?synced=" + ids
    st.success(f"Synced {len(rows)} report(s) from the offline queue. Heading back to the field app...")
    components.html(f"""
        <script>setTimeout(function() {{ window.location.href = {json.dumps(back)}; }}, 900);</script>
        <a href="{back}">If the field app does not reopen by itself, tap here.</a>""", height=52)
    st.stop()


def _gps_suggestion(L):
    """Read flat/flon from the URL (set by the GPS button), snap to a barangay, clean up."""
    lat_s, lon_s = st.query_params.get("flat", ""), st.query_params.get("flon", "")
    for k in ("flat", "flon"):
        if k in st.query_params:
            del st.query_params[k]
    if not lat_s or not lon_s:
        return None
    try:
        lat, lon = float(lat_s), float(lon_s)
    except ValueError:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    brgy, km = nearest_barangay(L, lat, lon)
    if brgy is None:
        st.info("You seem to be outside Dagupan, so pick the barangay yourself. Salamat!")
        return None
    st.toast(f"Location set near {brgy}" + (f" (~{km:.1f} km from the centre)" if km > 0.5 else ""))
    return brgy


def render(L):
    st.caption("Field report for tanods, banca crews and neighbours at the water line. "
               "Three taps: barangay, what you see, how deep.")
    st.warning("This page feeds the community map. It is NOT a rescue channel - "
               "if lives are at risk, call the CDRRMO or emergency lines directly.")

    suggested = _gps_suggestion(L) or st.session_state.get("cs_field_brgy")
    if suggested:
        st.session_state["cs_field_brgy"] = suggested
    components.html(_GPS_BUTTON, height=56)

    picked = st.radio("What do you see?", [k[0] for k in FIELD_KINDS], label_visibility="collapsed")
    kind_label, rtype, details = next(k for k in FIELD_KINDS if k[0] == picked)

    brgys = sorted(L.brgy["barangay"].tolist())
    with st.form("field", clear_on_submit=True):
        brgy = st.selectbox("Barangay", brgys,
                            index=brgys.index(suggested) if suggested in brgys else 0)
        detail = st.selectbox("How deep / What state", details)
        note = st.text_input("Optional note (sitio, street landmark, banca count)")
        if st.form_submit_button("Send report", use_container_width=True, type="primary"):
            append_report(brgy, rtype, detail, note or "")
            st.toast("Report logged - salamat, kapitid!")

    if CR.exists():
        st.caption("Latest reports (newest first, all anonymous)")
        st.dataframe(pd.read_csv(CR).head(6), hide_index=True, use_container_width=True)

    with st.expander("Offline field pack (install once on each tanod phone)"):
        st.markdown(f"`{FIELD_PWA_URL}` opens the pack. After one online visit, the phone keeps it "
                    "and queues reports with no signal; the queued batch syncs to this app "
                    "automatically the moment the phone finds data again.")
        try:
            import io
            import qrcode as _qr
            buf = io.BytesIO()
            _qr.make(FIELD_PWA_URL).save(buf, format="PNG")
            st.image(buf.getvalue(), width=190)
        except Exception as e:
            st.caption(f"QR unavailable here ({type(e).__name__}). Type the address instead.")
        st.caption("Anonymous by design, like everything here - the pack stores reports on the "
                   "phone itself until they sync, then keeps nothing.")

    st.caption("No name, no login, no stored coordinates - a report keeps your barangay only. "
               "On the flood map, the latest flood-depth report per barangay shows as a pin, "
               "colour-coded from gutter-deep (yellow-green) to chest-deep (dark red).")

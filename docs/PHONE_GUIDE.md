# ClimateShield on phones and tablets: field guide

The command center runs in any modern phone browser. No app-store install, no new software.

## 30-second install

1. Join the same Wi-Fi network as the computer running the app.
2. Scan the QR in *Methods & Sources → 📱 Take this to the field* (or type the `http://192.168.x.x:8501` address).
3. Pin it:
   - Android (Chrome): ⋮ menu → Add to Home screen → Add.
   - iPhone (Safari): Share → Add to Home Screen → Add.
4. The icon now opens ClimateShield full-screen like a normal app.

## What works well on phones

- Field Report (crowd reports). The dedicated page for tanods and banca crews: three taps (barangay, what you see, how deep), optional one-tap GPS that fills the barangay only, and no login. It writes the same crowd reports the maps pin.
- Offline field pack. Open `https://jundeguzman92.github.io/ClimateShield-Dagupan/` once while online and add it to the home screen; after that it opens and takes reports with no signal at all, queuing them on the phone until data returns. One tap syncs the batch into the map.
- Telegram bot, optional. Crew members with nothing but Telegram can send reports through a chat (`run_bot.bat` on the ops laptop, one-time @BotFather token; details in `app/field_bot.py`). Buttons only, so every word the map reads stays exact.
- Barangay walkthrough + action card: the copy button feeds straight into SMS / Viber / Facebook.
- PDF briefings, downloaded from the phone and shared onward.

## Honest limits

- Maps are data-heavy; on slow connections wait for them to finish drawing.
- If you open the app from the internet (not the same Wi-Fi), use the published URL and access code from `DEPLOYING.md`.
- Streamlit itself always needs the network. For no-signal duty that is exactly what the offline field pack covers: the pack queues reports on the phone and syncs them the moment any connection appears, so the full command center never has to load inside the flood.
- For a whole no-signal evacuation center, keep a copy of the app running on a laptop on site (a pocket Wi-Fi router is enough; no internet needed) and have phones connect to it.

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

- Crowd reports (flood depth, road state, banca requests). This is the feature built for tanods and banca crews.
- Barangay walkthrough + action card: the copy button feeds straight into SMS / Viber / Facebook.
- PDF briefings, downloaded from the phone and shared onward.

## Honest limits

- Maps are data-heavy; on slow connections wait for them to finish drawing.
- If you open the app from the internet (not the same Wi-Fi), use the published URL and access code from `DEPLOYING.md`.
- For true offline use inside a no-signal evacuation center, keep a copy of the app running on a laptop on site (a pocket Wi-Fi router is enough; no internet needed) and have phones connect to it. Full offline packaging (service workers, cached bundles) is not supported by Streamlit, so this local-server pattern is the workaround.

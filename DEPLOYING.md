# Deploying ClimateShield-Dagupan to the cloud (free tier)

The app is a normal Streamlit app — the steps below take it from your laptop to a URL barangay halls can reach.

## 1. Push the project to GitHub

This folder is **already a git repository** with full history — create an empty repo on GitHub
(new → Repository, no README/license needed), then:

```bash
cd "C:\Users\junbu\Documents\ClimateShieldProject for Dagupan"
git remote add origin https://github.com/<you>/<your-new-repo>.git
git push -u origin main
```

Runtime CSVs (requests, shelters, ui_prefs), raw downloads and all `*.tif` are already excluded by
`.gitignore` — personal information from exercises never leaves the laptop.

What ships and why: the running app needs **only** `app/`, `data/app_layers/` (~25 MB),
`assets/` (<1 MB), the dashboard chart in `outputs/charts/`, plus docs. Everything under
`data/raw/` and `data/processed/` (including all `*.tif`) is excluded by `.gitignore` —
the notebook (`ClimateShield_Dagupan_Analysis.ipynb` + `nbcells_part*.py`) can rebuild
any of it locally from the sources in `docs/SOURCES.md`. First cloud boot takes ~60–90 s
(layer load + dependency install), then pages respond in ~1–3 s each.

## 2. Create the free Streamlit Cloud app

1. Go to https://share.streamlit.io → sign in with GitHub.
2. **New app** → pick the repo, branch `main`, main file path: `app/climateshield_command_center.py`.
3. Python version: default (3.12) is fine; `requirements.txt` at repo root is picked up automatically
   (includes streamlit-folium).
4. **Advanced → Secrets** — paste:

   ```toml
   app_password = "choose-a-strong-code-for-your-community"
   ```

   With this secret present, the app shows an **access-code screen** before anything else (feature G).
   Without a secret — e.g., on your laptop — the app stays open as before.

## 3. Verify the deployment

- The app must reach `data/app_layers/*` — confirm those paths landed in the repo.
- Live features that need internet on the server: Open-Meteo (live weather), RainViewer (radar). All have
  graceful offline fallbacks baked in — the app never crashes when a feed is down.
- Wall display mode + F11 works in any browser; share the URL with barangay halls.

## 4. Security notes

- The password gate is a simple **community-privacy screen**, not bank-grade auth. Streamlit Cloud already
  serves HTTPS; for anything handling person-identifiable data later (P2 crowd reports with names),
  upgrade to a proper auth layer before collecting.
- Never commit `secrets.toml`; it lives only in the Streamlit Cloud dashboard (or `.streamlit/secrets.toml`
  locally, which .gitignore should exclude).
- If your LGU wants a fixed, LAN-only install instead: run `run_app.bat` on an ops-room PC and use
  `--server.address 127.0.0.1` (or LAN IP) so the app is not exposed to the public internet.

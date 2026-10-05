# ClimateShield — Dagupan City Edition

**Community disaster intelligence for Dagupan City, Pangasinan, Philippines.**

This project refocuses the original [ClimateShield pipeline](https://github.com/JunDeGuzman92/climateshield-analysis) (Brilliant Catalyst Smart Communities Challenge, March 2026 — Durham Region, Ontario) on the city of Dagupan: a low-lying, tide-locked delta city that is simultaneously **the Philippines' hottest heat-index station** (51°C station readings, PAGASA — Apr 2024 and May 2021) and a chronic **habagat flood zone** (Aug 2026 habagat → state of calamity, 90,015 residents affected across all 31 barangays, CDRRMO SitRep No. 15).

The analytical engine is a single fully-executed notebook, `ClimateShield_Dagupan_Analysis.ipynb`, accompanied by app-ready map/raster products. Every number traces to a cited official, scientific, or News source (see `docs/SOURCES.md`).

## What the analysis establishes (headline findings)

| # | Finding | Basis |
|---|---|---|
| 1 | **The terrain is the hazard**: ~80% of Dagupan's active land lies at or below ~2 m above sea level; median elevation 0.0 m (post-1990-earthquake subsidence, Ishihara et al. 1993) | Copernicus GLO-30 DEM + active-land footprint |
| 2 | **~174k residents (≈80%) live on land at or below ~2 m** | WorldPop 2020 × DEM bands; PSA 2020 Census: 174,302 |
| 3 | **Heavy & intense rain days are significantly increasing** (D50: +0.15 d/yr, p=0.001; D100: +0.04 d/yr, p=0.027; Kendall tau) | NASA POWER 1981–2026, cross-checked vs ERA5 (r≈0.69–0.77) |
| 4 | **Danger-level heat-index days rising**: ~107/yr (1981–1990) → ~135/yr (2017–2026), tau p<0.02; station records crest at **51°C** | Rothfusz HI on NASA POWER; PAGASA station anchors; ERA5 apparent-T cross-check |
| 5 | Ready-made early-warning triggers aligned to **official PAGASA categories** (flood Monitoring/Alert/Warning/Severe; heat-index Caution→Extreme Danger) with community playbooks that work with or without government aid | PAGASA official classifications |
| 6 | **Barangay risk watchlist** (Pantal, Pogo Chico, Mayombo, Bolosan, Lucao, …) with transparent CSRI scoring; 28/31 barangays spatially anchored | PSA census × OSM anchors × susceptibility rasters |
| 7 | **Shed-light finding**: *every* active-land cell is within 1.5 km of a shelter-worthy site — Dagupan's problem is shelter **suitability** (20% of facilities stand in top-20% susceptibility ground), not shelter distance | OSM facilities × accessibility surface |
| 8 | Honest small-sample ML: trend models are labeled *planning heuristics* with reported (sometimes weak) R² — no model theater | §9 of the notebook |

## Repository layout

```
ClimateShieldProject for Dagupan/
├── ClimateShield_Dagupan_Analysis.ipynb   <- fully executed analysis (charts, maps, models embedded)
├── nbcells_part[1-6].py                    <- notebook cell sources (single source of truth)
├── build_notebook.py                       <- assembles + syntax-checks the .ipynb from the parts
├── docs/SOURCES.md                         <- full registry of datasets, news, agencies, licenses
├── data/raw/                               <- downloaded, cited datasets (see docs/SOURCES.md)
│   ├── nasa_power_dagupan_daily_1981_2026.json      (NASA POWER, MERRA-2)
│   ├── openmeteo_era5_dagupan_daily_1981_2026.json  (ECMWF ERA5 via Open-Meteo)
│   ├── dem_glo30_dagupan_raw.tif                     (clipped at build; source: Copernicus GLO-30)
│   ├── worldpop100m_dagupan_2020.tif                 (WorldPop 2020, 100 m)
│   ├── psa_2020_census_population_by_barangay.xlsx   (official PSA table via OCHA HDX)
│   ├── dagupan_city_boundary.geojson                 (OSM relation 13001749)
│   └── osm_dagupan_features_raw.json                 (OSM API 0.6 extract: rivers, coast, buildings, facilities)
├── data/processed/                         <- engineered products (recomputed by the notebook)
└── outputs/
    ├── charts/    (17 publication-quality PNGs, 01…17)
    ├── maps/      (climateshield_dagupan_interactive.html — folium app map + susceptibility overlay)
    └── reports/
```

## Quick start

```bash
# 1) environment
pip install -r requirements.txt

# 2) re-run the full analysis
jupyter nbconvert --to notebook --execute --inplace ClimateShield_Dagupan_Analysis.ipynb

# or rebuild the notebook from its source modules (recommended when editing)
python build_notebook.py && jupyter nbconvert --to notebook --execute --inplace ClimateShield_Dagupan_Analysis.ipynb
```

## The Command Center app (v0.2)

A reactive, **beige field-ops themed** Streamlit command center on top of the analysis artifacts:

```
run_app.bat          <- double-click: launches http://localhost:8501
app/
├── climateshield_command_center.py   6 sections, smoke-tested headlessly
├── data_core.py                      cached layers + flood/countermeasure models + action cards
└── prep_layers.py                    one-time artifact builder (re-run after notebook changes)
assets/
├── photos/    licensed Dagupan flood photo (Wikimedia Commons, CC BY-SA 4.0) + credits.json
└── hero/      web-optimized gallery slides (real photo + labeled model renders)
data/app_layers/                      fast app artifacts (DEM grids, road/building elevations, daily climate, ui_prefs.json)
```

| Section | What it does |
|---|---|
| 🏠 Command Deck | Live heat-index banner, **auto-crossfading incident gallery** (real CC-licensed Dagupan flood photo + labeled model renders), KPI cards, readiness calendar, clickable watchlist drill-down |
| 🌊 Flood Scenario Simulator | Storm + tide sliders; **2D map or rotatable 3D terrain model** (water plane + buildings + facility pins); roads flip passable→cut; barangay impact tables open copy-ready action cards; worst-road click → elevation profile |
| 🛡️ Countermeasure Lab | Dredging / drainage / relocation sliders → exposure waterfall + 'after' map + benefit ranking |
| 📡 Live Telemetry | Live gauge, 7-day rain triggers, crowd-report form, this-week-in-history events |
| 🗺️ Barangay Walkthrough | 5-step guided flow per barangay ending in a copy-ready action card |
| ℹ️ Methods & Sources | Provenance (incl. photo credit), calibration, roadmap |

**Wall display mode (⚙️ Display options → "📺 Wall display mode"):** a true **single-screen command center** — no page buttons, no scrolling. The screen shows the live header (scenario, water level, residents affected, live heat index, update stamp), three flood KPIs, the flood map on an **Esri Light Gray Canvas basemap** (pre-rendered offline into the app so it loads instantly), a heat-index gauge, the top-5 watchlist, and the readiness calendar — while the **flood scenario auto-rotates** (Advisory → Alert → Calamity → Extreme) every N seconds and the page silently re-polls live weather. Paired with browser F11 it is an LGU ops-room TV feed; the **⚙ Exit wall display** link always floats bottom-right. Regular mode keeps all six interactive pages. Panel visibility on the Command Deck remains toggleable; all preferences persist in `data/app_layers/ui_prefs.json`.

**v0.8 (current build): interactive pages & live-data resilience.** Command Deck cards navigate pages via callbacks (no more widget-state crashes), all maps use Esri tiles (no access-blocked layers), live weather falls back Open-Meteo → MET Norway with visible source chips, stale cache files can't blank the timestamps anymore, radar renders on the supported zoom, 3D scenes sit on a labeled map table with km axes + north mark, and a version chip (sidebar) identifies the running build. Countermeasure numbers round to whole persons.
- **A · Crowd-report map pins** — logged depth reports appear as severity-colored markers (with report counts) on every 2D map & the wall
- **B · Event time-lapse scrubber** — Simulator checkbox for dragging hour 0→48 of a storm (rise ~10 h, slow tidal decay), with a residents-affected timeline chart
- **C · Live rain radar** — RainViewer public-API frames (past + nowcast) as toggled radar layers over the region (Telemetry)
- **D · One-page PDF briefings** — per-barangay, per-scenario, in English/Tagalog/Pangasinan, with mini-map and action list (Simulator + Walkthrough)
- **E · Heat-season wall variant** — when live heat index crosses PAGASA Danger (42°C), the wall display auto-switches to a heat emergency layout (big gauge, respite-first barangay list, coverage playbook)
- **F · Language toggle** — English / Tagalog / Pangasinan for section titles, action cards and PDFs (Tagalog solid; Pangasinan best-effort, native review welcome)
- **G · Cloud deployment + access code** — password gate (Streamlit secret `app_password`) and step-by-step free deployment guide in `DEPLOYING.md`
- **H · Pantal River gauge log** — manual stage entries with instant Alert/Alarm/Critical classification + history chart; official PDRRMO feed hooks wait on roadmap P3 partnership

Run the headless smoke test any time you change the app:

```bash
python - <<'PY'
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app/climateshield_command_center.py", default_timeout=600); at.run()
print(at.exception or "OK")
PY
```

Countermeasure & scenario models are **planning proxies** (weights and caveats printed in-app); official warnings remain PAGASA/CDRRMO's.

## How this notebook is maintained

The notebook is **generated** from `nbcells_part1..6.py` by `build_notebook.py` (which also compile-checks every code cell before writing). Edit the part modules, then rebuild — this keeps large diffs reviewable and prevents broken-cell regressions.

## From notebook to community platform (next phase)

The notebook ends with the **command-center blueprint** (§10-13): data layer (PAGASA official feeds + CDRRMO sitreps + crowd reports + this repo's static rasters), intelligence layer (triggers → actions mapping, watchlists, typology segments), community layer (offline-first alerts, barangay dashboards, playbooks). The app picks up the four product phases P1–P4 defined there.

## Licenses & attribution

- **Interactive map basemaps** (keyless, chosen because tile.openstreetmap.org serves "Access blocked" to locally-opened `file://` maps and Carto now requires an API key): default **Esri Light Gray Canvas** (the closest key-free twin of Carto Positron) + optional **Esri World Imagery** satellite toggle + a "Place labels" overlay. To restore the *true* Carto Positron style, register a free key at https://carto.com/basemaps/apikey and paste it into `CARTO_API_KEY` in the map cell of `nbcells_part6.py`, then rebuild.
- PSA census data: Philippine Statistics Authority (via OCHA HDX, open license)
- WorldPop: CC-BY 4.0 · ERA5/Open-Meteo: CC-BY 4.0 · OpenStreetMap: ODbL
- Copernicus GLO-30: free & open (ESA/EEA)
- News citations: INQUIRER.net, PIA, GMA, ABS-CBN (attribution, quoted sparsely)
- Code: MIT (same as the original ClimateShield repo)

## Response simulator

ClimateShield's 🚑 Response & Dispatch page is a **simulator / training tool**. It contains no SMS or messaging
gateway code and never contacts any agency — all "texts", dispatches and alerts are simulated and logged locally.
Agency numbers shown are the public numbers from the official City Government of Dagupan website, for reference.

- Tabletop exercise script: `docs/PILOT_PLAYBOOK.md`
- Parked material for a possible future real-operations phase (not in use): `docs/future_real_operations/`



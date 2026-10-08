# ClimateShield: Dagupan City Edition

**Community disaster intelligence for Dagupan City, Pangasinan, Philippines.**

This project takes the original [ClimateShield pipeline](https://github.com/JunDeGuzman92/climateshield-analysis) (Brilliant Catalyst Smart Communities Challenge, March 2026, Durham Region, Ontario) and refocuses it on Dagupan: a low-lying, tide-locked delta city that holds the country's hottest heat-index readings (51°C station records, PAGASA, Apr 2024 and May 2021) and floods chronically in the habagat. In August 2026, monsoon flooding put the city under a state of calamity, with 90,015 residents affected across all 31 barangays (CDRRMO SitRep No. 15).

The analysis lives in one fully executed notebook, `ClimateShield_Dagupan_Analysis.ipynb`, with app-ready map and raster products beside it. Every number traces to a cited official, scientific, or news source (see `docs/SOURCES.md`).

## What the analysis establishes (headline findings)

| # | Finding | Basis |
|---|---|---|
| 1 | The terrain is the hazard: about 80% of Dagupan's active land lies at or below ~2 m above sea level; median elevation 0.0 m (post-1990-earthquake subsidence, Ishihara et al. 1993) | Copernicus GLO-30 DEM + active-land footprint |
| 2 | ~174k residents (~80%) live on land at or below ~2 m | WorldPop 2020 x DEM bands; PSA 2020 Census: 174,302 |
| 3 | Heavy and intense rain days are rising significantly (D50: +0.15 d/yr, p=0.001; D100: +0.04 d/yr, p=0.027; Kendall tau) | NASA POWER 1981-2026, cross-checked vs ERA5 (r~0.69-0.77) |
| 4 | Danger-level heat-index days rising: ~107/yr (1981-1990) to ~135/yr (2017-2026), tau p<0.02; station records crest at 51°C | Rothfusz HI on NASA POWER; PAGASA station anchors; ERA5 apparent-T cross-check |
| 5 | Ready-made early-warning triggers aligned to official PAGASA categories (flood Monitoring/Alert/Warning/Severe; heat-index Caution to Extreme Danger) with community playbooks that work with or without government aid | PAGASA official classifications |
| 6 | Barangay risk watchlist (Pantal, Pogo Chico, Mayombo, Bolosan, Lucao, ...) with transparent CSRI scoring; 30/31 barangays spatially anchored (Barangay II has no in-city OSM node yet) and interim barangay boundaries (anchor-Voronoi, labeled DERIVED) pending the LGU/PSA request | PSA census x OSM anchors x susceptibility rasters |
| 7 | Every active-land cell is within 1.5 km of a shelter-worthy site. Dagupan's problem is shelter suitability (20% of facilities stand in top-20% susceptibility ground), not shelter distance | OSM facilities x accessibility surface |
| 8 | Small-sample ML reported honestly: trend models are labeled planning heuristics with their (sometimes weak) R², no model theater | Notebook §9 |

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
│   ├── worldpop100m_dagupan_2020.tif                  (WorldPop 2020, 100 m)
│   ├── psa_2020_census_population_by_barangay.xlsx   (official PSA table via OCHA HDX)
│   ├── dagupan_city_boundary.geojson                 (OSM relation 13001749)
│   └── osm_dagupan_features_raw.json                  (OSM API 0.6 extract: rivers, coast, buildings, facilities)
├── data/processed/                         <- engineered products (recomputed by the notebook)
├── data/app_layers/                        <- fast app artifacts (DEM grids, daily climate, street graph, runtime CSVs)
├── tests/                                  <- pytest suite (86 tests) + run_tests.bat
└── outputs/                                <- charts, interactive map, reports
```

## Quick start

```bash
# 1) environment
pip install -r requirements.txt

# 2) re-run the full analysis
jupyter nbconvert --to notebook --execute --inplace ClimateShield_Dagupan_Analysis.ipynb

# or rebuild the notebook from its source modules (recommended when editing)
python build_notebook.py && jupyter nbconvert --to notebook --execute --inplace ClimateShield_Dagupan_Analysis.ipynb

# 3) launch the command center
run_app.bat            # or: python -m streamlit run app/climateshield_command_center.py
```

## The Command Center app (v1.0)

A Streamlit command center built on the analysis artifacts: clean light theme, satellite maps, no 3D. Nine pages:

| Page | What it does |
|---|---|
| 🏠 Command Deck | Live heat-index badge (Open-Meteo, with source and timestamp), storm time-lapses on the satellite map (4 scripted stories + 5 recorded real storms, optionally "if the city had prepared"), heat-scenario curves, KPI tiles, readiness calendar, clickable watchlist |
| 🌊 Flood Scenario Simulator | Storm-class + tide sliders give an interactive impact map (hover roads, facilities, crowd pins), storm time-lapse, and an evacuation route view (person-vs-water gauge, elevation profile) |
| ☀️ Heat Scenario Simulator | Recorded, custom, or live-forecast heat day; felt-heat raster and day film; relief reach and survival board (cooling points 2.5 km, health sites, hydration TL/EN); survival card PNG; tabletop inject pack |
| 🛡️ Countermeasure Lab | Dredging, drainage, relocation sliders: exposure waterfall, "after" map, benefit ranking |
| 📡 Live Telemetry | Live heat gauge + rain timeline, hourly heat-index curve with PAGASA bands, PhilSensors official-station status (instant from cache, explicit refresh), Pantal river manual log, crowd reports |
| 🗺️ Barangay Walkthrough | 6-step guided flow per barangay: profile, terrain (ground profile, person-vs-water gauge, plain reading), flood exposure, countermeasures, evacuation route, action card + PNG/PDF briefing |
| 🚑 Response & Dispatch | Simulator/training tool: timed team exercises on the storm clock, help texts to requests to unit travel and capacity to shelter fill-up, score and debrief PNG. Shelter/resources boards, nearest services, official directory (reference only) |
| 📱 Field Report | Three-tap flood report for tanods and banca crews on their phones: barangay (optional one-tap GPS prefill), what you see, how deep. Anonymous by design, no stored coordinates, writes the same crowd reports the maps pin |
| ℹ️ Methods & Sources | Provenance, calibration and honesty notes, model validation vs CDRRMO SitRep No. 15, elevation upgrade importer |

Wall display (kiosk) mode: a single-screen auto-rotating scenario feed for an ops-room TV (F11 for fullscreen; exit link bottom-right).

**Data-quality caveat, stated in-app:** Copernicus GLO-30 records ~62% of Dagupan's active land at exactly 0 m (fishpond and wetland flattening). Scenario classes stay distinct by ordering that plateau with the susceptibility index; a LiDAR/IfSAR DEM upload (Methods page) replaces it where available.

## Response simulator, important

ClimateShield's response and dispatch page is a simulator and training tool. It contains no SMS or messaging gateway code and never contacts any agency: all "texts", dispatches and alerts are simulated and logged locally. Agency numbers shown are the public numbers from the official City Government of Dagupan website, for reference only.

- Tabletop exercise script: `docs/PILOT_PLAYBOOK.md`
- Parked material for a possible future real-operations phase (not in use): `docs/future_real_operations/`

## Tests

The repo carries a sandboxed pytest suite (about 10 minutes; runtime data is backed up and restored by the tests):

```bash
run_tests.bat        # or: python -m pytest
```

It covers: all 9 pages render, wall mode, heat simulator and relief layers, field reports to map pins, the flood ladder's monotonicity, replay calibration anchors (Aug 2026 habagat ~45% land flooded; Pepeng 2009 ~65%), mission travel and capacity physics, shelter fill-up, escalation, debrief rendering, a real-browser check that the time-lapse plays and the HUD doesn't cover the map, and an import-safety test that fails if network code ever appears in the messaging module.

## How the notebook is maintained

The notebook is generated from `nbcells_part1..6.py` by `build_notebook.py` (which also compile-checks every code cell before writing). Edit the part modules, then rebuild.

## Licenses & attribution

- Interactive map basemaps, keyless ones (tile.openstreetmap.org serves "Access blocked" to `file://` maps and Carto requires an API key): Esri Light Gray Canvas, Esri World Imagery satellite, place-labels overlay.
- PSA census data: Philippine Statistics Authority (via OCHA HDX, open license)
- WorldPop: CC-BY 4.0 · ERA5/Open-Meteo: CC-BY 4.0 · OpenStreetMap: ODbL
- Copernicus GLO-30: free & open (ESA/EEA)
- News citations: INQUIRER.net, PIA, GMA, ABS-CBN (attribution, quoted sparsely)
- Code: MIT (see `LICENSE`, same as the original ClimateShield repo). The data layers keep their upstream licenses (OSM-derived files are ODbL; WorldPop/ERA5 CC-BY 4.0; Copernicus free & open): scope is mapped in `docs/SOURCES.md` §9.

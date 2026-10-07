# ClimateShield Dagupan: Source & Credibility Registry

All datasets, agency products, news reports, and scientific papers used or cited in
`ClimateShield_Dagupan_Analysis.ipynb`. Retrieval date for all online sources: **October 3, 2026**.

## 1. Primary datasets

| Dataset | Provider | Version/date | License | Access URL |
|---|---|---|---|---|
| Daily climate 1981–2026 (T2M, T2M_MAX, T2M_MIN, RH2M, PRECTOTCORR) @ 16.0432°N 120.3342°E | NASA POWER (MERRA-2 reanalysis) | retrieved 2026-10-03 | NASA open data | https://power.larc.nasa.gov/ |
| Daily climate 1981–2026 (ERA5: temperature_2m_max/min, relative_humidity_2m_mean, apparent_temperature_max, precipitation_sum) | ECMWF ERA5 via Open-Meteo archive API | retrieved 2026-10-03 | CC-BY 4.0 | https://archive-api.open-meteo.com/ |
| Copernicus DEM GLO-30 (30 m DSM), tile N16 E120 | ESA Copernicus / EEA | 2021 release, retrieved 2026-10-03 | Free & open | https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N16_00_E120_00_DEM/Copernicus_DSM_COG_10_N16_00_E120_00_DEM.tif |
| WorldPop population count 2020, 100 m (PHL) | WorldPop, University of Southampton | 2020, phl_ppp_2020.tif | CC-BY 4.0 | https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/PHL/ |
| 2020 Census of Population and Housing, total population by barangay (41,984 barangays, official PSA table) | Philippine Statistics Authority via OCHA HDX | 2020 CPH | Open (HDX) | https://data.humdata.org/dataset/2020-census-total-population-by-barangay-admin4 (resource: 2020-census-total-popn-brgy_adm4_new-pcode.xlsx) |
| Dagupan City polygon | OpenStreetMap relation 13001749 | retrieved 2026-10-03 via Nominatim | ODbL | https://www.openstreetmap.org/relation/13001749 |
| OSM feature extract (rivers/canals, coastline, major roads, 6,532 building footprints, amenities, place labels); API 0.6 map calls, 3×3 tiles | OpenStreetMap contributors | retrieved 2026-10-03 | ODbL | https://www.openstreetmap.org |

**City reference figures:** population 174,302 (PSA 2020 CPH barangay sum, computed in-notebook); 174,777 (PSA 2024 census, as published in the city profile); land area 4,447.10 ha; 31 barangays (17 urban-classified, 14 rural; note: in-notebook computation gives 21 urban / 10 rural per 2020 CPH flags).

## 2. Official Philippine government sources

| Source | Product used | URL |
|---|---|---|
| DOST-PAGASA | Heat Index portal & iHeatMAP (official national heat-index platform); heat-index categories (Caution 27–32 / Extreme Caution 33–41 / Danger 42–51 / Extreme Danger ≥52 °C) | https://www.pagasa.dost.gov.ph/weather/heat-index |
| DOST-PAGASA | Rainfall & Thunderstorm Warning System legend (flood categories: Flood Monitoring/Advisory, Flood Alert, Flood Warning/Emergency, Severe Flooding; telemetered-basin Alert/Alarm/Critical = 40/60/100% channel capacity) | https://www.pagasa.dost.gov.ph/learnings/legend |
| DOST-PAGASA | 1991–2020 climatological normals for Dagupan station (rainfall, temperatures, humidity), official reference series | published PAGASA normals (as compiled on the Dagupan city profile) |
| Dagupan City CDRRMO | Situational Report No. 15, August 2026 habagat event (22,047 families / 90,015 individuals affected; 23 barangays flooded; 6 evacuation centers; 65 families preemptively evacuated) | via INQUIRER.net and PIA reporting (below) |
| Philippine Information Agency (PIA) | Official news of the state of calamity and DPWH flood-mitigation project timeline | https://pia.gov.ph |
| DPWH | Dagupan flood-mitigation project, contract effective Jun 24, 2024, originally due Nov 28, 2024, re-targeted June 2026 | PIA, Jun 18, 2026 |

## 3. News & agency reporting (event anchors)

| Date | Outlet | Headline (key figures) | URL |
|---|---|---|---|
| 2026-08-10 | INQUIRER.net | “Dagupan City declares state of calamity due to widespread flooding”; CDRRMO SitRep 15 details | https://newsinfo.inquirer.net/2281468/ |
| 2026-08-10 | PIA | “Dagupan City declares state of calamity due to flooding” | https://pia.gov.ph/disaster-information-service/dagupan-city-declares-state-of-calamity-due-to-flooding/ |
| 2026-08-25 | GMA News | “Pangasinan braces for habagat peak”; Pantal River above normal | https://www.gmanetwork.com/news/topstories/regions/999702/ |
| 2026-06-18 | PIA | “DPWH fast-tracks flood mitigation project in Dagupan” | https://pia.gov.ph/news/dpwh-fast-tracks-flood-mitigation-project-in-dagupan/ |
| 2025-07-28 | GMA Regional TV | “Floods persist in two Pangasinan cities, 13 towns” | https://www.gmanetwork.com/regionaltv/news/109376/ |
| 2025-03-14 | GMA Regional TV | “Dagupan City heat index may reach 50°C, PAGASA says” (45°C highest in PH to that date in 2025) | https://www.gmanetwork.com/regionaltv/news/107098/ |
| 2025-03-26 | INQUIRER.net | “‘Dangerous’ level heat index seen in Dagupan City” (forecast 47°C) | https://newsinfo.inquirer.net/2046925/ |
| 2024-04-29 | INQUIRER.net | “51ºC heat index recorded in Dagupan City, over 42ºC in 32 other areas”; PAGASA; national record day Apr 28, 2024 | https://newsinfo.inquirer.net/1935013/ |
| 2024-07 | AGHAM (scientists' group) | “On the 2024 Habagat- and Typhoon Carina-induced flood disaster: a preliminary analysis” (Luzon-wide; Pangasinan among affected) | https://www.agham.org/wp-content/uploads/2024/07/ |
| 2021-05-09 | ABS-CBN News | “Dagupan City scorches at 51 degrees Celsius heat index” (2 PM, PAGASA) | https://www.abs-cbn.com/news/05/09/21/ |

## 4. Scientific literature

- Ishihara, K., Acacio, A. A., & Towhata, I. (1993). *Liquefaction-Induced Ground Damage in Dagupan in the July 16, 1990 Luzon Earthquake.* Soils and Foundations 33(1), 33–45. doi:10.3208/sandf1972.33.133 (primary documentation of the 1990 liquefaction and subsidence event).
- Rodolfo, K. S., & Siringan, F. P.: studies of delta subsidence and flood aggravation on the western Luzon coastal plain (Pantal/Agno context). Recommended reading for the app phase.
- AGHAM (2024), above; flood-disaster analysis of the July 2024 habagat + Typhoon Carina/Gaemi event.

## 5. Landscape / analogous projects (not used as data, cited as context)

- ProjectLigtas, live Philippine flood monitoring (water levels, alerts, barangay flood map): https://projectligtas.com/flood_monitoring
- PAGASA iHeatMAP, real-time national heat-index dashboard (official): https://www.pagasa.dost.gov.ph/weather/heat-index
- Kontur Boundaries PH (admin divisions w/ aggregated population; used diagnostically during data prospecting to confirm barangay geometry is not openly published for Dagupan): https://data.humdata.org/dataset/kontur-boundaries-philippines

## 6. Methodological standards applied

- Heat index: Rothfusz (NWS) regression, computed from daily maximum temperature × daily mean relative humidity; results framed as *worst-case daily basis*, anchored to PAGASA station observations (Apr 28, 2024: 51°C station vs 59°C reanalysis worst-case; same PAGASA 'Danger' category).
- Rainfall extremes: ≥50 mm/day (heavy) and ≥100 mm/day (intense) analytical thresholds consistent with PAGASA rainfall-intensity descriptors; 3-day/7-day storm maxima.
- Trends: Kendall's tau (two-sided) + OLS slope; significance reported as-found.
- Flood susceptibility: transparent weighted proxy (elevation 45% + Euclidean river proximity 25% + coastal proximity 15% + flatness 15%) over a 30 m UTM 51N grid; not a hydraulic model. Official DOST-PAGASA / DPWH flood-hazard maps remain authoritative for engineering.
- Active-land footprint: OSM land-use polygons ∪ building footprints ∪ WorldPop occupancy, within the OSM city polygon (which extends into gulf municipal waters); validated at 33.8 km² = 76% of the official 44.47 km² land area.
- Exposure arithmetic: zonal sums on the WorldPop native 100 m grid (nearest-resampled zone ids); PSA census totals are the authoritative population counts.


## 7. Known limitations (summary; full discussion in notebook §13)

- Reanalysis grids (~9–60 km) smooth station-point extremes; the operational app must ingest PAGASA synoptic-station feeds.
- GLO-30 is a surface model (rooftop/canopy bias documented); band shares are planning-grade.
- Barangay polygons are not published openly for Dagupan (checked: OSM subareas, OCHA COD-AB, geoBoundaries ADM4 → 404, GADM L4 → 404); barangay analysis uses PSA census + 30/31 OSM anchors and interim anchor-Voronoi neighborhoods labeled DERIVED until the LGU boundary file arrives.
- Annual-scale ML models have weak held-out skill (reported honestly in-notebook); used as labeled planning heuristics only.

## 8. Operational sources (app runtime, checked 7 Oct 2026)

| Source | Product used | Access |
|---|---|---|
| Open-Meteo forecast API | Current + hourly temperature/humidity/rain at 16.0432°N 120.3342°E (model grid, primary live feed) | CC-BY 4.0 · https://api.open-meteo.com/ |
| MET Norway Locationforecast | Rain fallback when Open-Meteo is unreachable (rain only, no temperature/RH) | open data · https://api.met.no/ |
| aviationweather.gov METAR | Nearest real station observations: Laoag Intl RPLI (~239 km), Clark Intl RPLC (~98 km); Dagupan and Baguio publish no METAR | US public domain · https://aviationweather.gov/api/data/metar |
| PAGASA dam table (`/flood` page) | Ambuklao/Binga/San Roque reservoir vs normal-high-water readings + Agno basin watch status (parsed, row arithmetic cross-checked) | PH public domain · https://www.pagasa.dost.gov.ph/flood |
| DOST-ASTI PhilSensors public page | Station catalogue only; archival (newest Pangasinan public reading Feb 2024, none inside Dagupan) | https://philsensors.asti.dost.gov.ph/ |
| DepEd Order No. 37, s. 2022 | Class/work suspension rules for disasters and calamities (authority behind school actions) | Public issuance |
| DepEd statement, 4 Apr 2024 | School heads may suspend face-to-face classes and shift to ADM in extreme heat | https://www.deped.gov.ph/2024/04/04/on-class-suspensions-and-shifting-to-adm-due-to-high-heat-index-other-calamities |
| Draft 2026 automatic-suspension proposal (≥40°C) | Reported Jul 2026, not policy; shown in the app flagged as draft | Reported by GMA News, 29 Jul 2026 |
| DOLE Labor Advisory No. 08, s. 2023 | Heat-stress prevention: risk/comorbidity assessment, rest breaks, uniforms/PPE, ≥2–3 L water, info campaigns, emergency procedures, flexible hours | https://bwc.dole.gov.ph/wp-content/uploads/2024/06/LA-08-23-Safety-and-Health-Measures-to-Prevent-and-Control-Heat-Stress-at-the-Workplace.pdf |

## 9. How licensing applies to this repository

The code and the data carry different licenses; this section says which is which.

- **Code: MIT** (`LICENSE`). The app, the notebook cell sources and the build scripts are free to use, modify and redistribute with attribution.
- **OpenStreetMap-derived files are ODbL.** `data/app_layers/rivers.pkl`, `roads.pkl`, `coast.pkl`, `places.pkl`, `buildings.pkl`, `facilities.pkl`, `street_graph.pkl`, `brgy_boundaries_derived.geojson`, the `heat_*` layer files, and the raw extract `data/raw/osm_dagupan_features_raw.json` derive from OpenStreetMap, © OpenStreetMap contributors, licensed under the Open Database License (ODbL) v1.0. Distributed derivatives stay under ODbL; the attribution line stays with them.
- **Copernicus-derived rasters**: `dem_utm.npy`, `hillshade.npy`, `land_mask.npy`, `city_mask.npy`, `susc.npy`, `dist_river.npy`, `dist_coast.npy`, `elev_calibration.npz` (contains modified Copernicus data, ESA/EEA; free and open).
- **WorldPop-derived**: `pop_utm.npy` (CC-BY 4.0, WorldPop 2020).
- **NASA POWER-derived**: `daily.csv` (NASA open data; attribute NASA POWER / Langley Research Center).
- **PSA census table and PAGASA/DepEd/DOLE texts**: Philippine government works carry no copyright (RA 8293 §176); cited anyway.
- **Chart backgrounds are synthesized, not stored Esri tiles.** `basemap_utm.npy` (once a reprojected copy of Esri Light Gray Canvas) no longer ships: it is gitignored, `prep_layers.py` builds the canvas from the Copernicus hillshade and land/water masks, and `data_core.synth_basemap` renders it at runtime when the file is absent. Esri imagery stays in the live Leaflet maps only, with attribution, as their terms require.
- **Personal data never ships**: runtime CSVs that could hold names or numbers (requests, contacts, exercise state) are gitignored and stay on the operator's machine; nothing person-identifiable is distributed under any license.


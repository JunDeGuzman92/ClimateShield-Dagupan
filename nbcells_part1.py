CELLS_P1 = []

CELLS_P1.append(("md", """# ClimateShield: Community Disaster Intelligence for Dagupan City, Pangasinan

A reproducible, fully executed analysis notebook behind the ClimateShield-Dagupan command center.

This notebook extends the original ClimateShield pipeline (Brilliant Catalyst Smart Communities Challenge, March 2026, Durham Region, Ontario) and re-focuses it on Dagupan City, Pangasinan: a coastal city that lives a double hazard life:

| Hazard | Reality on the ground |
|---|---|
| Flash flooding | Enhanced southwest monsoon (*habagat*), typhoon rains and a tidal river system (Pantal/Calmay) routinely flood large parts of the city. In August 2026, habagat flooding put 23 barangays underwater, affected 90,015 people (22,047 families) and forced a state of calamity (CDRRMO SitRep, via INQUIRER.net / PIA, Aug 10, 2026). |
| Extreme heat | Dagupan repeatedly posts the highest heat index in the Philippines: 51°C on Apr 28, 2024 (PAGASA, via INQUIRER.net), 51°C on May 9, 2021 (ABS-CBN), and danger-level readings again in March 2025 (GMA). |
| The compounding problem | Parts of the city subsided below sea level after the July 16, 1990 M7.7 Luzon earthquake (liquefaction documented by Ishihara et al., 1993, *Soils and Foundations*), so floodwaters drain slower, streets stay submerged for days, and government flood-control projects have slipped (the DPWH Dagupan flood-mitigation project was re-targeted from Nov 2024 to June 2026; PIA, June 2026). |

What this notebook delivers:

1. A 45-year climate analysis (1981–2026) of rainfall and heat-index extremes over Dagupan (NASA POWER + ERA5 cross-validation)
2. A satellite-terrain flood-susceptibility analysis of the city (Copernicus GLO-30 DEM + OSM river/coast networks)
3. Population and critical-infrastructure exposure mapping (PSA 2020 Census, WorldPop 2020, OpenStreetMap)
4. Barangay-level watchlists, early-warning triggers aligned to official PAGASA categories, and community response playbooks that work with or without government aid
5. Compact machine-learning models in the spirit of the original ClimateShield pipeline
6. A blueprint for the ClimateShield app / community command center

> *Analysis date: October 3, 2026. Author: Jun De Guzman (ClimateShield-Dagupan edition). All figures trace to cited datasets; every headline number is computed in this notebook.*"""))

CELLS_P1.append(("md", """## 0. City profile and hazard timeline

**Dagupan City**, the "Bangus (Milkfish) Capital of the Philippines" and the commercial/financial hub of Pangasinan:

| Attribute | Value | Source |
|---|---|---|
| Population (2020 census) | 174,302 | PSA 2020 Census of Population and Housing (barangay table, via OCHA HDX) |
| Population (2024 census) | 174,777 | PSA via city profile |
| Land area | 4,447.10 ha (44.47 km²) | City profile / PSA |
| Barangays | 31 (17 urban, 14 rural per 2020 CPH classification) | PSA PSGC |
| Coastline | Lingayen Gulf (north) | - |
| Rivers | Pantal, Calmay, Bued + extensive tidal river/canal network | OSM |
| Climate | Tropical monsoon (*Am*), Type I: pronounced dry season Nov–Apr, wet May–Oct | PAGASA Modified Coronas classification |

**Documented hazard events (all cited):**

| Date | Event | Reported impact | Source |
|---|---|---|---|
| Jul 16, 1990 | M7.7 Luzon earthquake → liquefaction & subsidence in Dagupan | Buildings tilted/sank; parts of city dropped to/below sea level; Pantal bridge collapse | Ishihara, Acacio & Towhata (1993), *Soils and Foundations* 33(1), doi:10.3208/sandf1972.33.133 |
| May 9, 2021 | Highest heat index in PH: 51°C (2pm, PAGASA station) | National record day | ABS-CBN News |
| Jul 24–28, 2024 | Habagat + Typhoon Carina (Gaemi) disaster, Luzon-wide | Regional flooding (Pangasinan among affected) | AGHAM preliminary analysis (2024) |
| Apr 28, 2024 | 51°C peak heat index, the highest of 33 danger-level stations nationwide | Health warnings, El Niño spring | INQUIRER.net, Apr 29, 2024 (PAGASA data) |
| Jul 2025 | Habagat floods persist in 2 Pangasinan cities + 13 towns | Multi-day floods in Dagupan & Urdaneta | GMA Regional TV, Jul 28, 2025 |
| Mar 2025 | Heat index 45°C (country's highest) with forecast up to 50°C | Dry-season onset | GMA Regional TV, Mar 14, 2025; INQUIRER.net Mar 26, 2025 |
| Aug 10, 2026 | Habagat floods; STATE OF CALAMITY declared (CDRRMO SitRep No. 15) | 90,015 individuals (22,047 families) affected across all 31 barangays; 23 barangays flooded; 6 evacuation centers; 65 families preemptively evacuated; classes suspended 7 straight days; roads impassable to light vehicles | INQUIRER.net Aug 10, 2026; PIA Aug 10, 2026 |
| Aug 25, 2026 | Pantal River above normal level ahead of habagat peak | Province-wide monitoring | GMA News, Aug 25, 2026 |
| Jun 2026 | DPWH flood-mitigation project reported fast-tracked | Contract effective Jun 24, 2024, originally due Nov 28, 2024, re-targeted Jun 2026 | PIA, Jun 18, 2026 |

The August 2026 flood alone touched 52% of the city's population in a single event. That is the baseline scenario ClimateShield must prepare communities for."""))

CELLS_P1.append(("md", """## 0.1 Data sources & credibility registry

Every dataset used here is from an official government agency, a scientific institution, or a peer-reviewed publication. News items come from major national outlets or the official Philippine Information Agency.

### Primary datasets

| # | Dataset | Provider | Used for | Access |
|---|---|---|---|---|
| 1 | Daily climate 1981–2026 (T2M, T2M_MAX, T2M_MIN, RH2M, PRECTOTCORR) @ 16.043N, 120.334E | NASA POWER (MERRA-2 reanalysis) | Rainfall & heat trends, extremes | power.larc.nasa.gov, retrieved Oct 3, 2026 |
| 2 | Daily climate 1981–2026 (ERA5: Tmax, Tmin, RH, apparent temperature max, precip) | Open-Meteo archive (ECMWF ERA5) | Independent cross-validation | archive-api.open-meteo.com, retrieved Oct 3, 2026, CC-BY 4.0 |
| 3 | Elevation (DSM) 30m, Copernicus GLO-30 | ESA Copernicus / EEA | Terrain, flood-susceptibility proxies | copernicus-dem-30m S3 bucket (free, no auth) |
| 4 | Population raster 2020, 100m | WorldPop (Univ. of Southampton) | Population exposure mapping | data.worldpop.org, CC-BY 4.0 |
| 5 | 2020 Census total population by barangay (official PSA table, 41,984 barangays) | PSA via OCHA Humanitarian Data Exchange (HDX) | Barangay watchlist, ground-truth population | data.humdata.org (`2020-census-total-population-by-barangay_admin4`) |
| 6 | Administrative division (city polygon) | OpenStreetMap (relation 13001749) | City boundary | nominatim / OSM, ODbL |
| 7 | Rivers, canals, coastline, buildings, schools, hospitals, clinics, police, town halls, places of worship | OpenStreetMap (API 0.6 extract, ~100k nodes) | Flood network distance, infrastructure exposure | openstreetmap.org, ODbL |
| 8 | PAGASA 1991–2020 climatological normals for Dagupan + official warning classifications (heat index categories; Flood Monitoring/Alert/Warning/Severe; rainfall Advisory/Alert/Emergency; TC wind signals w/ 12–36h lead times) | DOST-PAGASA (official) | Climatology validation, trigger thresholds | pagasa.dost.gov.ph |

### Key news / agency reports (with access date Oct 3, 2026)

- INQUIRER.net, *"Dagupan City declares state of calamity due to widespread flooding"* (Aug 10, 2026): full CDRRMO SitRep No. 15 figures used in this notebook.
- INQUIRER.net, *"51ºC heat index recorded in Dagupan City, over 42ºC in 32 other areas"* (Apr 29, 2024, PAGASA data): the April 28, 2024 national-record heat event.
- PIA (*Philippine Information Agency*), *"Dagupan City declares state of calamity…"* (Aug 10, 2026) and *"DPWH fast-tracks flood mitigation project in Dagupan"* (Jun 18, 2026).
- GMA Regional TV / GMA News, heat index warnings (Mar 14, 2025; Mar 26, 2025) and *"Pangasinan braces for habagat peak"* (Aug 25, 2026).
- ABS-CBN News, *"Dagupan City scorches at 51 degrees Celsius heat index"* (May 9, 2021).
- AGHAM, *"On the 2024 Habagat- and Typhoon Carina-induced flood disaster: a preliminary analysis"* (Jul 2024).
- Ishihara, K., Acacio, A.A., Towhata, I. (1993). *Liquefaction-Induced Ground Damage in Dagupan in the July 16, 1990 Luzon Earthquake.* Soils and Foundations 33(1) 33–45, doi:10.3208/sandf1972.33.133.
- Landscape reference: ProjectLigtas live flood-monitoring platform (projectligtas.com), an existing civic flood app that shows the demand for this kind of tool in the Philippines.
- PAGASA iHeatMAP (official), the real-time national heat-index platform (pagasa.dost.gov.ph/weather/heat-index): the official feed ClimateShield's app will ingest for Dagupan.

### Honest limitations preview

- NASA POWER / ERA5 are reanalysis grid datasets (~9–60 km cells). They capture regional climate and extremes, but they can smooth single-station records (e.g., PAGASA's 51°C station heat index). We cross-validate both and treat official PAGASA station reports as the ground truth anchors.
- Copernicus GLO-30 is a digital surface model (it includes building and canopy tops), so built-up pixels read a few meters higher than bare ground. Flood susceptibility here is a transparent weighted proxy built for community planning, not a hydraulic flood model, and official hydrology remains with the DOST-PAGASA / DPWH flood-hazard maps.
- Barangay polygons are not openly published for Dagupan (OSM/geoBoundaries/GADM all stop at municipality level), so barangay-level analysis uses official PSA census tables plus OSM neighborhood anchors, documented cell-by-cell."""))

CELLS_P1.append(("code", """import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patheffects
from scipy import stats
from scipy import ndimage

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 40)

ROOT = Path.cwd()
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"
REPORTS = ROOT / "outputs" / "reports"
CHARTS.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

CITY = "Dagupan City, Pangasinan"
LON, LAT = 120.3342, 16.0432

PAGASA_HI_CATEGORIES = [
    (27, 32, "Caution", "#ffe699"),
    (33, 41, "Extreme Caution", "#f6b26b"),
    (42, 51, "Danger", "#e06666"),
    (52, 100, "Extreme Danger", "#741b47"),
]

def save_chart(fig, name):
    dest = CHARTS / name
    fig.savefig(dest, dpi=150, bbox_inches="tight")
    print(f"saved: {dest}")
    plt.show()

def hi_category(hi):
    if hi < 27:
        return "No Caution"
    if hi <= 32:
        return "Caution"
    if hi <= 41:
        return "Extreme Caution"
    if hi <= 51:
        return "Danger"
    return "Extreme Danger"

def rothfusz_hi_c(t2m_max_c, rh_mean):
    tf = t2m_max_c * 9 / 5 + 32
    hi_f = (
        -42.379 + 2.04901523 * tf + 10.14333127 * rh_mean
        - 0.22475541 * tf * rh_mean - 0.00683783 * tf**2 - 0.05481717 * rh_mean**2
        + 0.00122874 * tf**2 * rh_mean + 0.00085282 * tf * rh_mean**2
        - 0.00000199 * tf**2 * rh_mean**2
    )
    return (hi_f - 32) * 5 / 9

def kendall_trend(years, values):
    tau, p = stats.kendalltau(years, values)
    slope = np.polyfit(years, values, 1)[0]
    return tau, p, slope

print("Environment ready:", CITY, " @", LAT, LON)"""))

CELLS_P1.append(("md", """## 1. Load 45 years of daily climate data (1981–2026)

Two independent reanalysis products:

- NASA POWER (MERRA-2 based), the primary product
- ERA5 (ECMWF, via the Open-Meteo archive) for independent cross-validation; it includes *apparent temperature*, a heat-index analogue

QC checks: expected ~16,600 daily records since Jan 1, 1981; missing-value rates; physical bounds (0.5 ≤ T ≤ 45°C, 0 ≤ RH ≤ 100, 0 ≤ rain)."""))

CELLS_P1.append(("code", """with open(RAW / "nasa_power_dagupan_daily_1981_2026.json") as f:
    power = json.load(f)

par = power["properties"]["parameter"]
df = pd.DataFrame(
    {
        "date": pd.to_datetime(list(par["T2M"].keys()), format="%Y%m%d"),
        "T2M": list(par["T2M"].values()),
        "T2M_MAX": list(par["T2M_MAX"].values()),
        "T2M_MIN": list(par["T2M_MIN"].values()),
        "RH2M": list(par["RH2M"].values()),
        "RAIN": list(par["PRECTOTCORR"].values()),
    }
).set_index("date").sort_index()
df = df[(df > -900).all(axis=1)]

df["YEAR"] = df.index.year
df["MONTH"] = df.index.month

print(f"POWER daily records: {len(df):,}  ({df.index.min().date()} -> {df.index.max().date()})")
print(f"missing/day-since-1981: {(len(pd.date_range(df.index.min(), df.index.max())) - len(df))} days")
print(df[["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "RAIN"]].describe().round(2).to_string())

with open(RAW / "openmeteo_era5_dagupan_daily_1981_2026.json") as f:
    era5 = json.load(f)["daily"]
df_e = pd.DataFrame(
    {
        "date": pd.to_datetime(era5["time"]),
        "TMAX": era5["temperature_2m_max"],
        "TMIN": era5["temperature_2m_min"],
        "RH": era5["relative_humidity_2m_mean"],
        "APP_TMAX": era5["apparent_temperature_max"],
        "RAIN": era5["precipitation_sum"],
    }
).set_index("date").sort_index()
df_e = df_e.dropna(how="all")

print(f"\\nERA5 daily records: {len(df_e):,}  ({df_e.index.min().date()} -> {df_e.index.max().date()})")"""))

CELLS_P1.append(("md", """### 1.1 Climatology vs. official PAGASA normals (1991–2020)

PAGASA's Dagupan synoptic-station normals (published 1991–2020 series) are the national official reference, a well-mapped ground-truth benchmark. Below, the reanalysis-derived monthly climatology (1991–2020 to match the normal's window) is plotted **against** the official station normal. Good agreement validates 45 years of reanalysis for trend work; systematic offsets are documented, not hidden."""))

CELLS_P1.append(("code", """PAG_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PAG_RAIN = [5.7, 9.5, 23.0, 69.5, 218.2, 335.5, 532.7, 619.5, 401.6, 226.6, 54.9, 20.0]
PAG_TMAX = [30.7, 31.5, 32.9, 34.4, 34.0, 33.3, 31.9, 31.1, 31.5, 31.9, 31.8, 31.0]
PAG_RH = [81, 81, 79, 79, 81, 84, 87, 88, 87, 85, 83, 82]

win = df.loc["1991":"2020"]
power_rain = win.groupby("MONTH")["RAIN"].sum() / 30
power_tmax = win.groupby("MONTH")["T2M_MAX"].mean()
power_rh = win.groupby("MONTH")["RH2M"].mean()

power_rain_avg = float((win.groupby("YEAR")["RAIN"].sum()).mean())
print(f"POWER 1991-2020 mean annual rainfall: {power_rain_avg:,.0f} mm  (PAGASA station normal: 2,516.7 mm)")
print(f"POWER annual Tmax mean: {power_tmax.mean():.1f} C vs station normal {np.mean(PAG_TMAX):.1f} C")

fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
x = np.arange(12)
axes[0].bar(x - 0.2, PAG_RAIN, width=0.4, label="PAGASA station normal", color="#255c7a")
axes[0].bar(x + 0.2, power_rain.values, width=0.4, label="NASA POWER (1991-2020)", color="#7db7d9")
axes[0].set_xticks(x); axes[0].set_xticklabels(PAG_MONTHS, rotation=45)
axes[0].set_ylabel("Monthly rainfall (mm)"); axes[0].set_title("Rainfall climatology")
axes[0].legend(fontsize=8)
axes[1].plot(x, PAG_TMAX, "o-", label="PAGASA station normal", color="#255c7a")
axes[1].plot(x, power_tmax.values, "s--", label="NASA POWER (1991-2020)", color="#c0392b")
axes[1].set_xticks(x); axes[1].set_xticklabels(PAG_MONTHS, rotation=45)
axes[1].set_ylabel("Mean daily max temp (C)"); axes[1].set_title("Temperature climatology"); axes[1].legend(fontsize=8)
axes[2].plot(x, PAG_RH, "o-", label="PAGASA station normal", color="#255c7a")
axes[2].plot(x, power_rh.values, "s--", label="NASA POWER (1991-2020)", color="#27ae60")
axes[2].set_xticks(x); axes[2].set_xticklabels(PAG_MONTHS, rotation=45)
axes[2].set_ylabel("Relative humidity (%)"); axes[2].set_title("Humidity climatology"); axes[2].legend(fontsize=8)
fig.suptitle("Dagupan climatology: reanalysis vs. official PAGASA normals (1991-2020)", y=1.02)
save_chart(fig, "01_climatology_vs_pagasa.png")
plt.close(fig)"""))

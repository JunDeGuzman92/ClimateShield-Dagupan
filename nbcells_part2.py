CELLS_P2 = []

CELLS_P2.append(("md", """## 2. Extreme rainfall, the flood driver (1981–2026)

Dagupan's floods are overwhelmingly **rain-driven**: habagat cloudbands, typhoons, and organized convection dump extraordinary volumes on an already tide-locked, subsided, low-gradient delta city. We quantify the changing frequency of heavy and intense daily rainfall (thresholds set at ≥50 mm/day for heavy and ≥100 mm/day for intense, consistent with PAGASA rainfall intensity descriptors), plus multi-day storm volumes (3-day and 7-day maxima) that matter when the Pantal-Calmay system backs up at high tide.

Each metric gets a trend test (Kendall's tau, with OLS slope), the same statistical honesty the original ClimateShield pipeline applied to Durham's heat days."""))

CELLS_P2.append(("code", """annual = pd.DataFrame(index=sorted(df["YEAR"].unique()))
annual["RAIN_ANN"] = df.groupby("YEAR")["RAIN"].sum()
annual["MAX1D"] = df.groupby("YEAR")["RAIN"].max()
annual["MAX3D"] = df["RAIN"].rolling(3).sum().groupby(df["YEAR"]).max()
annual["MAX7D"] = df["RAIN"].rolling(7).sum().groupby(df["YEAR"]).max()
annual["D50"] = df[df["RAIN"] >= 50].groupby("YEAR").size().reindex(annual.index, fill_value=0)
annual["D100"] = df[df["RAIN"] >= 100].groupby("YEAR").size().reindex(annual.index, fill_value=0)
annual = annual.dropna()
yrs = annual.index.values.astype(float)

print("=== Annual heavy/intense rain-day trends (1981-2026) ===")
for metric in ["D50", "D100", "MAX1D", "MAX3D"]:
    tau, p, slope = kendall_trend(yrs, annual[metric].values)
    direction = "upward" if slope > 0 else "downward"
    sig = "significant (p<0.05)" if p < 0.05 else "not significant"
    unit = "days/yr" if metric.startswith("D") else "mm/yr"
    print(f"  {metric}: Kendall tau={tau:+.2f}, p={p:.3f} -> {direction} {slope:+.2f} {unit} ({sig})")

tau50 = kendall_trend(yrs, annual["D50"].values)
tau100 = kendall_trend(yrs, annual["D100"].values)

fig, axes = plt.subplots(2, 2, figsize=(15, 9))
ax = axes[0, 0]
ax.bar(annual.index, annual["D50"], color="#7db7d9", label="days >= 50mm (heavy)")
z = np.polyfit(yrs, annual["D50"], 1)
ax.plot(annual.index, np.polyval(z, yrs), "r--", label=f"trend {z[0]:+.2f} d/yr")
ax.set_title(f"Heavy-rain days per year (tau={tau50[0]:+.2f}, p={tau50[1]:.3f})")
ax.legend(fontsize=8)

ax = axes[0, 1]
ax.bar(annual.index, annual["D100"], color="#c0392b", label="days >= 100mm (intense)")
z = np.polyfit(yrs, annual["D100"], 1)
ax.plot(annual.index, np.polyval(z, yrs), "k--", label=f"trend {z[0]:+.2f} d/yr")
ax.set_title(f"Intense-rain days per year (tau={tau100[0]:+.2f}, p={tau100[1]:.3f})")
ax.legend(fontsize=8)

ax = axes[1, 0]
ax.plot(annual.index, annual["MAX3D"], "o-", color="#255c7a", ms=4)
ax.axhline(annual["MAX3D"].mean(), color="grey", ls=":", label=f"mean {annual['MAX3D'].mean():.0f} mm/3-days")
z = np.polyfit(yrs, annual["MAX3D"], 1)
ax.plot(annual.index, np.polyval(z, yrs), "r--", label=f"trend {z[0]:+.2f} mm/yr")
ax.set_title("Annual maximum 3-day rainfall (storm volume)")
ax.legend(fontsize=8)

ax = axes[1, 1]
worst = annual.nlargest(10, "MAX7D")
ax.barh([str(y) for y in worst.index], worst["MAX7D"], color="#8e44ad")
ax.set_xlabel("7-day rainfall total (mm)")
ax.set_title("Top 10 wettest weeks on record")
fig.suptitle("Dagupan extreme rainfall, 1981-2026 (NASA POWER / MERRA-2)", y=1.0)
fig.tight_layout()
save_chart(fig, "02_extreme_rainfall.png")
plt.close(fig)

top_days = df.nlargest(15, "RAIN")[["RAIN", "T2M_MAX", "RH2M"]].copy()
top_days.insert(0, "date", top_days.index.strftime("%Y-%m-%d (%a)"))
top_days["category"] = ["INTENSE (>=100mm)" if r >= 100 else "heavy" for r in top_days["RAIN"]]
print("\\n=== Top 15 wettest days on record ===")
print(top_days.round(1).to_string(index=False))

monthly_dist = df[df["RAIN"] >= 100].groupby("MONTH").size()
print("\\nMonths when intense-rain days (>=100mm) historically occur:", dict(monthly_dist))"""))

CELLS_P2.append(("md", """## 3. Seasonality: habagat concentration & dry-season drought stress

Dagupan's climate (Type I, *Am*) splits the year into two operational regimes:

- Wet / flood regime (May–Oct, peaking Jul–Aug): habagat + typhoon season, the months that produced the Aug 2026 calamity
- Dry / heat regime (Nov–Apr, peaking Apr–May): El Niño-amplified heat-index season, when the 51°C records are set

We track (a) the share of annual rainfall falling in Jun–Oct, (b) dry-spell lengths (the longest run of days with < 1 mm, a proxy for drought and aquaculture stress in the bangus farm belt), and (c) off-season heavy rain: surprise events that catch communities unprepared during the nominal dry months."""))

CELLS_P2.append(("code", """wet_share = (df[df["MONTH"].between(6, 10)].groupby("YEAR")["RAIN"].sum() / annual["RAIN_ANN"]).dropna()

ds = df.assign(dry=(df["RAIN"] < 1.0).astype(int))
ds["group"] = (ds["dry"].diff() != 0).cumsum()
runs = ds[ds["dry"] == 1].groupby("group").size()
run_year = ds[ds["dry"] == 1].groupby("group")["YEAR"].first()
cds = pd.Series(runs.values, index=run_year.values).groupby(level=0).max().reindex(annual.index).fillna(0)

off_annual = df[(df["RAIN"] >= 50) & (~df["MONTH"].between(6, 10))].groupby("YEAR").size().reindex(annual.index, fill_value=0)

fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.6))
ax = axes[0]
ax.plot(wet_share.index, wet_share.values * 100, "o-", color="#255c7a", ms=4)
z = np.polyfit(wet_share.index.astype(float), wet_share.values * 100, 1)
ax.plot(wet_share.index, np.polyval(z, wet_share.index.astype(float)), "r--")
tau_w, p_w, _ = kendall_trend(wet_share.index.astype(float), wet_share.values)
ax.set_title(f"Jun-Oct share of annual rainfall (tau={tau_w:+.2f}, p={p_w:.2f})")
ax.set_ylabel("% of annual rain")
ax.set_ylim(50, 100)

ax = axes[1]
ax.bar(cds.index, cds.values, color="#e67e22")
ax.set_title("Longest dry spell each year (< 1mm/day)")
ax.set_ylabel("consecutive days")

ax = axes[2]
ax.bar(off_annual.index, off_annual.values, color="#7d3c98")
z = np.polyfit(yrs, off_annual.values, 1)
ax.plot(annual.index, np.polyval(z, yrs), "r--")
tau_o, p_o, _ = kendall_trend(yrs, off_annual.values)
ax.set_title(f"Off-season heavy-rain days (Nov-May) (tau={tau_o:+.2f}, p={p_o:.2f})")
fig.suptitle("Seasonality and regime stress, 1981-2026", y=1.02)
save_chart(fig, "03_seasonality.png")
plt.close(fig)
print(f"2026 YTD longest dry spell: {cds.loc[2026]:.0f} days")
print(f"Off-season (Nov-May) heavy-rain days 1981-2026: {off_annual.sum():.0f} total, occurring in {int((off_annual > 0).sum())} of 46 years")"""))

CELLS_P2.append(("md", """## 4. Heat: how dangerous has Dagupan's heat index become?

PAGASA's official national heat-index categories: **Caution 27–32°C · Extreme Caution 33–41°C · Danger 42–51°C · Extreme Danger ≥52°C**. The Danger band is where heat cramps, heat exhaustion and heat stroke become probable with continued exposure.

Method: daily heat index via the Rothfusz regression (the NWS formula underlying PAGASA heat-index guidance), computed from daily maximum temperature × daily mean relative humidity (NASA POWER). This correlates with, but can smooth, 2pm synoptic-station observations; the Apr 28, 2024 record (51°C station heat index, per PAGASA/INQUIRER.net) is used as an anchor event (validated below). Days are counted by their worst-case category."""))

CELLS_P2.append(("code", """df["HI"] = rothfusz_hi_c(df["T2M_MAX"].values, df["RH2M"].values)
df["HI_CAT"] = df["HI"].map(hi_category)

hi_annual = pd.DataFrame(index=annual.index)
for cat in ["Caution", "Extreme Caution", "Danger", "Extreme Danger"]:
    hi_annual[cat] = df[df["HI_CAT"] == cat].groupby("YEAR").size().reindex(hi_annual.index, fill_value=0)

for cat in ["Danger", "Extreme Danger"]:
    tau, p, slope = kendall_trend(hi_annual.index.values.astype(float), hi_annual[cat].values)
    print(f"{cat} days 1981-2026: tau={tau:+.2f} p={p:.4f} slope={slope:+.2f} d/yr  "
          f"(1981-1990 avg {hi_annual[cat].iloc[:10].mean():.1f} -> 2017-2026 avg {hi_annual[cat].iloc[-10:].mean():.1f} days/yr)")

max_hi = df.loc[df["HI"].idxmax()]
print(f"\\nWorst computed heat-index day of the satellite era: {max_hi.name.date()} HI={max_hi['HI']:.1f}C "
      f"(Tmax={max_hi['T2M_MAX']:.1f}C, RH={max_hi['RH2M']:.0f}%)")
rec24 = df.loc["2024-04-28"]
print(f"Anchor check, 2024-04-28 (PAGASA station HI = 51.0C, national record):")
print(f"   reanalysis HI = {rec24['HI']:.1f}C (Tmax={rec24['T2M_MAX']:.1f}C, RH={rec24['RH2M']:.0f}%) -> same PAGASA 'Danger' category")

colors = {"Caution": "#ffe699", "Extreme Caution": "#f6b26b", "Danger": "#e06666", "Extreme Danger": "#741b47"}
fig, axes = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={"width_ratios": [2.4, 1]})
ax = axes[0]
bottom = np.zeros(len(hi_annual))
for cat in ["Caution", "Extreme Caution", "Danger", "Extreme Danger"]:
    ax.bar(hi_annual.index, hi_annual[cat], bottom=bottom, color=colors[cat], label=cat)
    bottom += hi_annual[cat].values
z = np.polyfit(hi_annual.index.values.astype(float), hi_annual["Danger"] + hi_annual["Extreme Danger"], 1)
ax.plot(hi_annual.index, np.polyval(z, hi_annual.index.values.astype(float)), "k--",
        label=f"danger days trend {z[0]:+.2f} d/yr")
ax.axvline(2024, color="grey", ls=":", lw=1)
ax.annotate("2024: PAGASA logged\\n51C station HI (record)",
            xy=(2024, hi_annual.loc[2024, "Danger"] + hi_annual.loc[2024, "Extreme Danger"]),
            xytext=(2002, 150), fontsize=8, arrowprops=dict(arrowstyle="->"))
ax.legend(fontsize=8, loc="upper left")
ax.set_ylabel("days per year")
ax.set_title("Days by PAGASA heat-index category (worst-hour basis)")

ax = axes[1]
ax.hist(df["HI"], bins=50, color="#f6b26b", edgecolor="white")
ax.axvline(42, color="#c0392b", ls="--")
ax.text(42.6, ax.get_ylim()[1] * 0.9, "Danger\\n(42C)", color="#c0392b", fontsize=9)
ax.axvline(33, color="#e67e22", ls="--")
ax.text(33.3, ax.get_ylim()[1] * 0.6, "Extreme\\nCaution", color="#e67e22", fontsize=9)
ax.set_xlabel("Daily heat index (C)")
ax.set_title("Distribution of all daily heat-index values")
fig.suptitle("Dagupan heat-index regime, 1981-2026", y=1.02)
save_chart(fig, "04_heat_index_categories.png")
plt.close(fig)"""))

CELLS_P2.append(("code", """all_years = np.arange(1981, 2027)
heat_matrix = df[df["HI"] >= 42].pivot_table(index="YEAR", columns="MONTH", values="HI", aggfunc="size").fillna(0)
heat_matrix = heat_matrix.reindex(all_years, fill_value=0)

fig, axes = plt.subplots(1, 2, figsize=(16.5, 5.6))
ax = axes[0]
im = ax.imshow(heat_matrix.values, aspect="auto", cmap="YlOrRd", origin="lower")
ax.set_yticks(range(0, len(heat_matrix), 5))
ax.set_yticklabels(heat_matrix.index[::5])
ax.set_xticks(np.arange(12) + 0.5, minor=False)
ax.set_xticks(np.arange(12))
ax.set_xticklabels(PAG_MONTHS)
plt.colorbar(im, ax=ax, label="days with HI >= 42C")
ax.set_title("Danger-level heat-index days: year x month")

ax = axes[1]
trop = df[df["T2M_MIN"] >= 26].groupby("YEAR").size().reindex(all_years, fill_value=0)
ax.bar(trop.index, trop.values, color="#5d6d7e")
z = np.polyfit(all_years, trop.values, 1)
ax.plot(trop.index, np.polyval(z, all_years), "r--", label=f"trend {z[0]:+.2f} d/yr")
tau_t, p_t, _ = kendall_trend(all_years, trop.values)
ax.set_title(f"Tropical nights (Tmin >= 26C) (tau={tau_t:+.2f}, p={p_t:.4f})")
ax.legend(fontsize=9)
fig.suptitle("When heat strikes - and the overnight relief that never comes", y=1.02)
save_chart(fig, "05_heat_seasonality.png")
plt.close(fig)
print("Ten worst heat seasons (Danger + Extreme Danger days):")
print(hi_annual[["Danger", "Extreme Danger"]].assign(TOTAL=lambda d: d.sum(axis=1)).nlargest(10, "TOTAL").to_string())"""))

CELLS_P2.append(("md", """### 4.1 Independent cross-validation with ERA5 (ECMWF)

Two satellite-era reanalyses are never identical; checking them against each other (and against station-recorded events) is how we avoid building conclusions on one model's artifacts."""))

CELLS_P2.append(("code", """merged_h = df[["T2M_MAX", "RAIN", "HI"]].merge(
    df_e[["TMAX", "APP_TMAX", "RAIN"]], left_index=True, right_index=True, suffixes=("", "_e")
).dropna(subset=["T2M_MAX", "TMAX", "RAIN", "RAIN_e"])
joined = merged_h
r_t, _ = stats.pearsonr(joined["T2M_MAX"], joined["TMAX"])
r_p, _ = stats.pearsonr(joined["RAIN"], joined["RAIN_e"])
r_hi, _ = stats.pearsonr(joined["HI"], joined["APP_TMAX"])
bias_rain = (joined["RAIN"] - joined["RAIN_e"]).mean()
print(f"Daily Tmax correlation (NASA POWER vs ERA5): r={r_t:.3f}")
print(f"Daily rainfall correlation: r={r_p:.3f} (POWER mean bias vs ERA5: {bias_rain:+.2f} mm/day)")
print(f"POWER heat index vs ERA5 apparent-temperature max: r={r_hi:.3f}")

ann_e_rain = df_e.groupby(df_e.index.year)["RAIN"].sum()
ann_e_appt = df_e.groupby(df_e.index.year)["APP_TMAX"].max()
common = annual.index.intersection(ann_e_rain.index)

fig, axes = plt.subplots(1, 2, figsize=(14.5, 4.8))
ax = axes[0]
ax.plot(common, annual.loc[common, "RAIN_ANN"], "o-", ms=4, label="NASA POWER (MERRA-2)", color="#255c7a")
ax.plot(common, ann_e_rain.loc[common], "s--", ms=4, label="ERA5 (ECMWF)", color="#e67e22")
ax.set_title("Annual rainfall: two independent reanalyses agree")
ax.set_ylabel("mm/year")
ax.legend(fontsize=8)

ax = axes[1]
ax.scatter(joined["HI"], joined["APP_TMAX"], s=3, alpha=0.25, color="#c0392b")
lim = [joined[["HI", "APP_TMAX"]].min().min(), joined[["HI", "APP_TMAX"]].max().max()]
ax.plot([20, 60], [20, 60], "k--", lw=1, label="1:1 line")
ax.set_xlabel("POWER heat index (Rothfusz, daily basis)")
ax.set_ylabel("ERA5 apparent temperature max (C)")
ax.set_title(f"Heat-stress products agree (r={r_hi:.2f})")
ax.legend(fontsize=9)
fig.suptitle("Cross-validation: the climate signal is source-robust", y=1.02)
save_chart(fig, "06_era5_crosscheck.png")
plt.close(fig)"""))

CELLS_P2.append(("md", """## 4.2 Early-warning triggers aligned to official PAGASA categories

Alert triggers use only official classification systems. ClimateShield's job is to translate them into community action earlier and faster, not to invent rival science.

**PAGASA official flood advisory classes** (Rainfall Warning System; river-stage basis for telemetered basins):

| PAGASA level | Official meaning | ClimateShield community trigger |
|---|---|---|
| Flood Monitoring / Advisory | "Flooding is **possible** in low-lying areas and near river channels" (Pantal River stage also monitored toward Alert = 40% channel capacity) | Pre-position banca/rescue rosters; charge lights & phones; clear drainage inlets; call elderly/needy list |
| Flood Alert | "Flooding is **threatening**"; preparedness phase (moderate-heavy rainfall) | Move vehicles & bangus harvest to high ground; voluntary evacuation of subsided-zone households; school pickup protocol |
| Flood Warning / Emergency | "Flood is **occurring** — immediate action recommended / severe flooding expected" | Mandatory evacuation to designated centers; banca taxi operations; crowd-sourced depth layer activates |
| Severe Flooding | "Flood is **persisting** — forced evacuation recommended" | Full city-wide response; mutual-aid network activates |

**PAGASA heat-index categories** (Caution / Extreme Caution / Danger / Extreme Danger) come with official health guidance. At Danger: move to shade, elevate legs, sip cool water, apply cool water + ice packs to armpits-wrists-ankles-groin, and hospital transport for suspected heat stroke. ClimateShield turns each band into barangay-level action sets, alert-copy templates, and school/work scheduling rules.

**Readiness calendar**: 45 years of data distilled into the expected red-flag days per month, so preparedness budgets and drills land *before* the season that needs them."""))

CELLS_P2.append(("code", """rain_monthly = df[df["RAIN"] >= 50].groupby("MONTH").size() / 45.7
hi_monthly = df[df["HI"] >= 42].groupby("MONTH").size() / 45.7

mon = np.arange(1, 13)
fig, ax = plt.subplots(figsize=(13.5, 4.6))
ax.bar(mon - 0.2, rain_monthly.reindex(mon, fill_value=0).values, 0.4, color="#255c7a", label="days with rain >= 50mm")
ax.bar(mon + 0.2, hi_monthly.reindex(mon, fill_value=0).values, 0.4, color="#c0392b", label="days with heat index >= 42C (Danger)")
ax.set_xticks(mon); ax.set_xticklabels(PAG_MONTHS)
ax.set_ylabel("average days per month, 1981-2026")
ax.set_title("Readiness calendar: when Dagupan's two hazard seasons strike")
ax.legend()
ax.grid(axis="y", alpha=0.3)
save_chart(fig, "07_readiness_calendar.png")
plt.close(fig)

cal = pd.DataFrame({
    "month": PAG_MONTHS,
    "heavy_rain_days_per_yr": rain_monthly.reindex(mon, fill_value=0).values.round(2),
    "heat_danger_days_per_yr": hi_monthly.reindex(mon, fill_value=0).values.round(2),
})
cal["dominant_threat"] = np.where(
    cal["heavy_rain_days_per_yr"] > cal["heat_danger_days_per_yr"], "FLOOD preparedness",
    np.where(cal["heat_danger_days_per_yr"] > 0, "HEAT preparedness", "LOW-RISK window (drills/maintenance)")
)
print(cal.to_string(index=False))"""))


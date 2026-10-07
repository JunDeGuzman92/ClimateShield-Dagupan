CELLS_P4 = []

CELLS_P4.append(("md", """## 6. Who is in harm's way? Exposure analysis

Three official and spatial layers triangulate exposure:

1. PSA 2020 Census of Population & Housing: the authoritative count of Dagupan's 31 barangays (downloaded from the official PSA file mirrored on OCHA HDX)
2. WorldPop 2020 (100 m, CC-BY 4.0): the spatial distribution of those ~174k residents (used for maps and zone arithmetic; totals cross-checked against the census)
3. OpenStreetMap critical infrastructure: schools, health facilities, civic/protective amenities, places of worship (historically the first evacuation shelters), and ~6.5k building footprints"""))

CELLS_P4.append(("code", """psa = pd.read_excel(RAW / "psa_2020_census_population_by_barangay.xlsx", sheet_name="2020 CPH")
dag = psa[psa["Mun_City"] == "City of Dagupan"].copy()
dag["popn"] = dag["2020 Census Popn"].astype(int)
dag["Barangay"] = dag["Barangay"].str.strip()
dag["urban"] = dag["Urban / Rural\\n(based on 2020 CPH)"].str.strip()
dag = dag[["New 10 digit PSGC", "Barangay", "urban", "popn"]].rename(columns={"New 10 digit PSGC": "psgc"})
dag = dag.sort_values("popn", ascending=False).reset_index(drop=True)
dag.to_csv(PROC / "psa_2020_dagupan_barangay_population.csv", index=False)
print(f"PSA 2020 CPH - City of Dagupan: {len(dag)} barangays, total population {dag['popn'].sum():,}")
print(f"  urban barangays: {(dag['urban'] == 'U').sum()} | rural: {(dag['urban'] == 'R').sum()} | urban population share: {dag.loc[dag['urban'] == 'U', 'popn'].sum() / dag['popn'].sum() * 100:.0f}%")
print(f"  vs. PSA 2024 census city total: 174,777 -> {174777 - dag['popn'].sum():+,} change since 2020")

fig, ax = plt.subplots(figsize=(11.5, 7.2))
top = dag.head(15).iloc[::-1]
colors_ur = {"U": "#c0392b", "R": "#27ae60"}
ax.barh(top["Barangay"], top["popn"], color=[colors_ur[u] for u in top["urban"]])
for y, (brg, p) in enumerate(zip(top["Barangay"], top["popn"])):
    ax.text(p + 250, y, f"{p:,}", va="center", fontsize=8)
ax.set_xlabel("Population (PSA 2020 census)")
ax.set_title("Dagupan's 15 most populated barangays (red = urban per 2020 CPH classification)")
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, label=l) for l, c in
                   [("urban", colors_ur["U"]), ("rural", colors_ur["R"])]], fontsize=9)
ax.grid(axis="x", alpha=0.3)
save_chart(fig, "11_barangay_census.png")
plt.close(fig)"""))

CELLS_P4.append(("code", """worldpop_path = PROC / "worldpop100m_dagupan_2020.tif"

if worldpop_path.exists():
    with rasterio.open(worldpop_path) as psrc:
        pop = psrc.read(1).astype("float32")
        pop_tr, pop_crs, pop_shape = psrc.transform, psrc.crs, pop.shape
    pop[pop < 0] = 0
    pop_city_mask = geometry_mask(city_gdf.geometry.values, out_shape=pop.shape,
                                  transform=pop_tr, invert=True)
    wp_city = pop[pop_city_mask].sum()
    print(f"WorldPop 2020 raster: {pop_shape[1]}x{pop_shape[0]} cells @ ~100 m")
    print(f"WorldPop population in city boundary: {wp_city:,.0f}")
    print(f"PSA 2020 census: {dag['popn'].sum():,} -> WorldPop estimate within {abs(wp_city / dag['popn'].sum() - 1) * 100:.0f}%")
else:
    pop = None
    print("WorldPop raster not found - population-zone arithmetic falls back to uniform-density approximation")

if pop is not None:
    def zone_raster_on_pop_grid(utm_zone_float):
        z = np.zeros(pop.shape, dtype="float32")
        reproject(utm_zone_float, z,
                  src_transform=utm_transform, src_crs=dst_crs,
                  dst_transform=pop_tr, dst_crs=pop_crs,
                  resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=0)
        return z

    band_ids = np.full((utm_h, utm_w), np.nan, dtype="float32")
    for i, (lo, hi, label) in enumerate(BANDS):
        sel = land_mask & (dem_utm >= lo) & (dem_utm < hi)
        band_ids[sel] = i
    zones_band = zone_raster_on_pop_grid(band_ids)

    nq = 5
    qs = np.nanpercentile(susc, np.linspace(0, 100, nq + 1))
    quint_ids = np.full((utm_h, utm_w), np.nan, dtype="float32")
    for qi in range(nq):
        lo = qs[qi]
        hi = qs[qi + 1] if qi < nq - 1 else np.inf
        sel = land_mask & (susc >= lo) & (susc <= hi) if qi < nq - 1 else land_mask & (susc >= lo)
        quint_ids[sel] = qi
    zones_quint = zone_raster_on_pop_grid(quint_ids)

    pop_by_band = np.array([pop[(zones_band == i) & (pop_city_mask)].sum() for i in range(len(BANDS))])
    tot = pop[pop_city_mask].sum()
    pop_by_quint = np.array([pop[(zones_quint == qi) & (pop_city_mask)].sum() for qi in range(nq)])

    print(f"\\n=== POPULATION x ELEVATION ===  residents at or below ~2 m: {pop_by_band[:3].sum():,.0f} ({pop_by_band[:3].sum() / tot * 100:.0f}%)")
    for i, (lo, hi, label) in enumerate(BANDS):
        print(f"  {label:>26}: {pop_by_band[i]:>9,.0f}  ({pop_by_band[i] / tot * 100:4.1f}%)")
    print(f"=== POPULATION x SUSCEPTIBILITY QUINTILE ===")
    for qi in range(nq):
        tag = ["lowest", "low", "middle", "high", "HIGHEST"][qi]
        print(f"  {tag:>7} 20% of city area: {pop_by_quint[qi]:>9,.0f} residents ({pop_by_quint[qi] / tot * 100:4.1f}%)")

    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8))
    ax = axes[0]
    cols = ["#1a5276", "#2874a6", "#5499c7", "#85c1e9", "#d6eaf8", "#fef9e7"]
    ax.bar([b[2] for b in BANDS], pop_by_band, color=cols)
    ax.set_ylabel("residents (WorldPop 2020)")
    ax.set_title(f"Residents by elevation band - {pop_by_band[:3].sum() / tot * 100:.0f}% live at or below ~2 m")
    ax.tick_params(axis="x", rotation=20, labelsize=8)
    ax = axes[1]
    ax.bar([f"Q{q + 1}" for q in range(nq)], pop_by_quint,
           color=["#eafaf1", "#f9e79f", "#f5b041", "#e67e22", "#c0392b"])
    ax.set_title("Residents by flood-susceptibility quintile")
    fig.suptitle("Population exposure - the demographic center of gravity of the hazard", y=1.04)
    save_chart(fig, "12_population_exposure.png")
    plt.close(fig)
else:
    pop_by_band = pd.Series(np.nan, index=[b[2] for b in BANDS])
    band_area_share = pd.Series(band_pct, index=[b[2] for b in BANDS])
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8))
    band_area_share.plot.bar(ax=axes[0], color="#5499c7")
    axes[0].set_title("Area share by elevation band (uniform population approximation)")
    axes[1].text(0.5, 0.5, "WorldPop raster unavailable -\\nsee published chart version for full exposure run", ha="center")
    axes[1].axis("off")
    save_chart(fig, "12_population_exposure.png")
    plt.close(fig)"""))

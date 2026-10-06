"""Barangay boundary masks: coverage, exposure basis, choropleth layer."""


def test_masks_cover_the_land_and_split_by_barangay(layers):
    import numpy as np
    assert layers.brgy_cells is not None, "boundary masks not built — run `python app/brgypoly.py`"
    assert layers.brgy_cells.shape == layers.dem.shape
    land_assigned = int(((layers.brgy_cells >= 0) & layers.land_mask).sum())
    assert land_assigned / layers.land_mask.sum() > 0.985, "masks must cover ≥98.5% of land"
    counts = [(nm, int(((layers.brgy_cells == i) & layers.land_mask).sum()))
              for i, nm in enumerate([b["barangay"] for b in layers.brgy_anchors])]
    have = [nm for nm, c in counts if c >= 25]
    assert len(have) >= 27, f"only {len(have)} barangays have polygon area; expected ≥27"


def test_exposure_uses_polygon_basis(labels=None):
    import data_core as dc

    L = dc.Layers()
    W = L.water_level_for_share(45) + 0.20
    bi = L.exposure(L.depth_grid(W)[0], W)["barangay_impact"]
    bases = bi["basis"].value_counts().to_dict()
    assert bases.get("polygon", 0) >= 27, "polygon basis must carry the vast majority of barangays"
    assert bi[bi["basis"] == "polygon"]["affected_est"].notna().all()
    # Barangay II (no in-city place node) shows honestly as no estimate
    b2 = bi[bi["barangay"] == "Barangay II"]
    assert len(b2) == 1 and pd.isna(b2.iloc[0]["affected_est"])


def test_anchors_stay_inside_the_city():
    import data_core as dc

    L = dc.Layers()
    import brgypoly as bp
    from shapely.geometry import Point
    outline = bp._city_polygon_utm()
    bad = []
    for b in L.brgy_anchors:
        if b["anchor"] is None:
            continue
        X, Y = L.to_utm(b["anchor"]["lon"], b["anchor"]["lat"])
        if not outline.contains(Point(float(X), float(Y))):
            bad.append(b["barangay"])
    assert not bad, f"anchors held outside the city outline: {bad}"


def test_map_carries_boundaries_and_choropleth():
    import data_core as dc
    import kit

    L = dc.Layers()
    W = L.water_level_for_share(45) + 0.20
    exp = L.exposure(L.depth_grid(W)[0], W)
    choro = {r["barangay"]: dict(frac=0.5, note="n") for _, r in exp["barangay_impact"].iterrows()}
    html = kit.make_city_map(L, depth=L.depth_grid(W)[0], W_cut=W, choro=choro, highlight="Pantal").get_root().render()
    assert "barangay boundaries" in html
    assert "DERIVED" in html, "interim source must be labeled on the map layer"
    assert "#1e3a8a" in html, "highlight stroke missing"


import pandas as pd  # noqa: E402

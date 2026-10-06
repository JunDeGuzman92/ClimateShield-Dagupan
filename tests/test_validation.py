"""Model validation against CDRRMO SitRep No. 15 (Aug 2026 habagat)."""
def test_observed_facts_are_the_official_sitreps():
    import validation
    assert validation.OBSERVED["barangays_still_flooded"] == 23
    assert validation.OBSERVED["families"] == 22047
    assert validation.OBSERVED["individuals"] == 90015


def test_peak_matches_families_and_barangay_counts_within_bands(layers):
    import validation
    _, s = validation.checks(layers)
    assert 0.4 <= s["W_peak"] <= 0.65, "peak water level in the expected range"
    assert 0.70 <= s["ratio"] <= 1.10, f"model affected {s['ratio']:.2f} of the reported 90,015 — outside the comparable band"
    assert 20 <= s["poly_peak"] <= 31, "barangays with water at peak (polygon share) should be ≥ the sitrep's 23"
    assert 4 <= s["anchors_peak"] <= 20, "anchor-point count is the stricter criterion (OSM cores are dry)"


def test_sitrep_date_polygon_count_lands_near_the_reported_23(layers):
    """The like-for-like comparison: barangays with water at sitrep time ≈ the reported 23/31."""
    import validation
    _, s = validation.checks(layers)
    assert abs(s["poly_late"] - validation.OBSERVED["barangays_still_flooded"]) <= 5, \
        (f"polygon count at sitrep time is {s['poly_late']}; the reported count is "
         f"{validation.OBSERVED['barangays_still_flooded']} — if this drifts, re-check the storage curve "
         "before shipping, and update the Methods wording")
    assert s["poly_late"] < s["poly_peak"], "water must recede between peak and sitrep time"


def test_anchor_point_measure_still_underestimates(layers):
    """The stricter point measure keeps showing the cores drain first — documented as a limitation."""
    import validation
    _, s = validation.checks(layers)
    assert s["anchors_late"] <= s["anchors_peak"], "anchor points should drain between peak and sitrep date"
    assert s["anchors_late"] < 10, "if cores stop draining, the persistence narrative needs a rewrite"

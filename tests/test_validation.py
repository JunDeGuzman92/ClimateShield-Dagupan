"""Model validation against CDRRMO SitRep No. 15 (Aug 2026 habagat)."""
def test_observed_facts_are_the_official_sitreps():
    import validation
    assert validation.OBSERVED["barangays_still_flooded"] == 23
    assert validation.OBSERVED["families"] == 22047
    assert validation.OBSERVED["individuals"] == 90015


def test_peak_matches_families_and_barangay_counts_within_bands(layers):
    import validation
    _, s = validation.checks(layers)
    assert 40 <= s["W_peak"] * 100 <= 60 or 0.4 <= s["W_peak"] <= 0.65, "peak water level in the expected range"
    assert 0.70 <= s["ratio"] <= 1.10, f"model affected {s['ratio']:.2f} of the reported 90,015 — outside the comparable band"
    assert 15 <= s["windows_peak"] <= 26, "barangay windows flooded at peak should land near the 23 reported"
    assert 6 <= s["anchors_peak"] <= 20, "anchor-cell count is the stricter criterion (OSM cores are dry)"


def test_persistence_gap_is_reported_not_hidden(layers):
    """The model drains faster than Dagupan did — validation must report the shortfall."""
    import validation
    _, s = validation.checks(layers)
    assert s["windows_late"] < s["windows_peak"] or s["anchors_late"] < s["anchors_peak"], \
        "expected the model to recede by sitrep time"
    assert s["windows_late"] < validation.OBSERVED["barangays_still_flooded"], \
        "under-estimating persistence is the documented limitation; update the Methods text if this ever passes"

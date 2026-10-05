"""Regression: flood scenario severity must be monotonic (an inverted percentile once made Advisory > Calamity)."""


def test_scenario_ladder_is_monotonic_and_hits_targets(layers):
    import data_core as dc
    prev_W, prev_pop = -9.0, -1.0
    for name, share in dc.SCENARIOS.items():
        W = layers.water_level_for_share(share)
        assert abs(layers.flooded_share(W) - share) < 1.0, f"{name}: floods {layers.flooded_share(W):.1f}% not {share}%"
        pop = layers.exposure(layers.depth_grid(W)[0], W)["pop_affected"]
        assert W > prev_W and pop > prev_pop, f"{name} is not more severe than the class before it"
        prev_W, prev_pop = W, pop


def test_plateau_is_broken_up(layers):
    import numpy as np
    land = layers.dem[layers.land_mask]
    assert float((np.abs(land) < 1e-6).mean()) < 0.01, "0 m plateau still present — tie-break not applied"
    assert layers.plateau_share > 0.5   # the raw GLO-30 plateau we documented

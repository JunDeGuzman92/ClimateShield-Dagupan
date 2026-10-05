"""Every page renders without an exception, plus the wall display."""
import pytest

from conftest import boot, goto, nav_labels, no_exc

PAGES = nav_labels()


def test_every_page_renders():
    at = boot()
    no_exc(at)
    for label in PAGES:
        goto(at, label)
        assert not at.exception, f"{label}: " + " | ".join(e.value[:400] for e in at.exception)


@pytest.mark.parametrize("cycle", [1, 2])
def test_wall_display(prefs, cycle):
    prefs(kiosk=True, cycle_idx=cycle)
    at = boot()
    no_exc(at)
    assert len(at.metric) >= 3
    assert len(at.sidebar) == 0, "sidebar should be hidden in wall mode"

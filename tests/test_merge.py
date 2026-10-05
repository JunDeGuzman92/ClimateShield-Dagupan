"""Regression: saving a table must not overwrite changes made meanwhile by exercise events."""
import pandas as pd


def _shelters():
    return pd.DataFrame(dict(shelter_id=["S001", "S002", "S003"], name=["A", "B", "C"],
                             status=["open", "open", "closed"], capacity=["", "", ""], headcount=[0, 0, 0]))


def test_stale_table_does_not_revert_event_change():
    import ops
    shown = _shelters()                              # what the user had on screen
    on_disk = _shelters()
    on_disk.loc[1, "status"] = "unsafe"              # an event fired meanwhile: S002 lost power
    user = {"edited_rows": {0: {"capacity": "150"}}}  # user only typed a capacity for S001
    out = ops.merge_edits(user, shown, on_disk, "shelter_id").set_index("shelter_id")
    assert out.loc["S001", "capacity"] == "150"
    assert out.loc["S002", "status"] == "unsafe", "stale table reverted the event"


def test_merge_uses_ids_not_positions_when_view_is_filtered():
    import ops
    full = _shelters()
    view = full[full["status"] == "open"].iloc[[1]]   # filtered view shows only S002 at position 0
    out = ops.merge_edits({"edited_rows": {0: {"headcount": 40}}}, view, full, "shelter_id").set_index("shelter_id")
    assert out.loc["S002", "headcount"] == 40 and out.loc["S001", "headcount"] == 0


def test_merge_handles_added_and_deleted_rows():
    import ops
    base = pd.DataFrame(dict(unit_id=["U001", "U002"], type=["boat", "truck"], status=["available"] * 2))
    st_ = {"deleted_rows": [1], "added_rows": [{"unit_id": "", "type": "ambulance", "status": ""}, {}]}
    out = ops.merge_edits(st_, base, base, "unit_id")
    assert list(out["type"]) == ["boat", "ambulance"]

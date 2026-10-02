import numpy as np
import pandas as pd
import pytest

from pcb_inspection.trace_diagnostics import trace_table, summarize_offsets, join_anomaly_diagnostics


def fixture():
    predictions = pd.DataFrame({"image_id": ["a", "b"], "run_id": ["one", "one"], "label": [1, 0],
        "primary_score": [2., 3.], "primary_reference_id": ["fit", "fit"],
        "query_patch_row": [1, 2], "query_patch_column": [2, 2],
        "reference_patch_row": [4, 2], "reference_patch_column": [6, 2]})
    references = [{"image_id": "fit", "row": 4, "column": 6}, {"image_id": "fit", "row": 2, "column": 2}]
    return predictions, references


def test_offsets_and_strict_threshold():
    pred, refs = fixture()
    traces = trace_table(pred, 2, refs)
    assert traces.outcome.tolist() == ["FN", "FP"]
    assert traces.offset_euclidean_cells.tolist() == [5, 0]
    assert traces.offset_chebyshev_cells.tolist() == [4, 0]
    assert traces.outside_radius_4.tolist() == [False, False]
    summary = summarize_offsets(traces)
    assert summary.set_index("outcome").loc["FN", "outside_radius_2_count"] == 1


@pytest.mark.parametrize("column,value", [("query_patch_row", 32), ("query_patch_column", -.1),
    ("reference_patch_column", 1.5), ("primary_score", np.inf), ("label", 2), ("run_id", "two")])
def test_invalid_traces(column, value):
    pred, refs = fixture()
    if isinstance(value, float): pred[column] = pred[column].astype(float)
    pred.loc[0, column] = value
    with pytest.raises(ValueError): trace_table(pred, 2, refs)


def test_reference_and_join_identity():
    pred, refs = fixture()
    with pytest.raises(ValueError): trace_table(pred, 2, refs[:1])
    traces = trace_table(pred, 2, refs)
    joined = join_anomaly_diagnostics(traces, pd.DataFrame({"image_id": ["a"], "defect_types": ['["scratch","missing"]']}))
    assert joined.defect_types.iloc[0] == '["scratch","missing"]'
    with pytest.raises(ValueError): join_anomaly_diagnostics(traces, pd.DataFrame({"image_id": ["wrong"]}))
    with pytest.raises(ValueError): join_anomaly_diagnostics(traces, pd.DataFrame({"image_id": ["a"], "run_id": ["other"]}))

"""Retrospective analysis of saved maximum-score patch traces, without inference.

These traces describe the winning query patch, not necessarily a defect patch.
Offsets are in the unregistered Run 1 feature grid, not canonical board coordinates.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


COORDINATES = ["query_patch_row", "query_patch_column", "reference_patch_row", "reference_patch_column"]


def trace_table(predictions, image_threshold, references, grid_shape=(32, 32)):
    required = {"image_id", "run_id", "label", "primary_score", "primary_reference_id", *COORDINATES}
    if not required.issubset(predictions.columns):
        raise ValueError("Missing saved trace columns")
    if predictions.image_id.duplicated().any() or len(predictions.run_id.unique()) != 1:
        raise ValueError("Duplicate IDs or mixed runs")
    if not np.isfinite(image_threshold) or not np.isfinite(predictions.primary_score).all():
        raise ValueError("Nonfinite score/threshold")
    if not predictions.label.isin([0, 1]).all():
        raise ValueError("Invalid labels")
    frame = predictions[["image_id", "run_id", "label", "primary_score", "primary_reference_id", *COORDINATES]].copy()
    reference_tuples = {(r["image_id"], int(r["row"]), int(r["column"])) for r in references}
    for column in COORDINATES:
        values = frame[column].to_numpy()
        bound = grid_shape[0] if column.endswith("row") else grid_shape[1]
        if not np.isfinite(values).all() or not ((values >= 0) & (values < bound) & (values == np.floor(values))).all():
            raise ValueError("Invalid feature-grid coordinate")
        frame[column] = values.astype(int)
    for row in frame.itertuples():
        if (row.primary_reference_id, row.reference_patch_row, row.reference_patch_column) not in reference_tuples:
            raise ValueError("Saved reference missing from frozen memory metadata")
    frame["frozen_image_threshold"] = image_threshold
    frame["detected_at_frozen_threshold"] = frame.primary_score > image_threshold
    frame["outcome"] = np.select([frame.label.eq(1) & frame.detected_at_frozen_threshold,
                                  frame.label.eq(1), frame.detected_at_frozen_threshold], ["TP", "FN", "FP"], default="TN")
    frame["offset_rows"] = frame.reference_patch_row - frame.query_patch_row
    frame["offset_columns"] = frame.reference_patch_column - frame.query_patch_column
    frame["offset_chebyshev_cells"] = frame[["offset_rows", "offset_columns"]].abs().max(axis=1)
    frame["offset_euclidean_cells"] = np.hypot(frame.offset_rows, frame.offset_columns)
    for radius in [0, 1, 2, 4, 8]:
        frame[f"outside_radius_{radius}"] = frame.offset_chebyshev_cells > radius
    frame["trace_scope"] = "maximum_score_query_patch_only"
    return frame.sort_values("image_id").reset_index(drop=True)


def summarize_offsets(frame, group_column="outcome"):
    result = []
    group_columns = [group_column] if isinstance(group_column, str) else list(group_column)
    for group, rows in frame.groupby(group_column, dropna=False):
        group_values = [group] if isinstance(group_column, str) else list(group)
        record = {**dict(zip(group_columns, group_values)), "n_traces": len(rows),
                  "median_offset_cells": float(rows.offset_chebyshev_cells.median()),
                  "p90_offset_cells": float(rows.offset_chebyshev_cells.quantile(.9))}
        for radius in [0, 1, 2, 4, 8]:
            record[f"outside_radius_{radius}_count"] = int(rows[f"outside_radius_{radius}"].sum())
            record[f"outside_radius_{radius}_rate"] = float(rows[f"outside_radius_{radius}"].mean())
        result.append(record)
    return pd.DataFrame(result)


def join_anomaly_diagnostics(traces, diagnostics):
    if diagnostics.image_id.duplicated().any():
        raise ValueError("Anomaly diagnostics must have unique image IDs")
    if set(diagnostics.image_id) != set(traces.loc[traces.label == 1, "image_id"]):
        raise ValueError("Diagnostic anomaly IDs do not match prediction anomalies")
    if "run_id" in diagnostics and set(diagnostics.run_id) != set(traces.run_id):
        raise ValueError("Diagnostic and trace runs differ")
    paired = diagnostics.set_index("image_id").reindex(traces.loc[traces.label == 1, "image_id"])
    anomaly_traces = traces.loc[traces.label == 1]
    if "image_anomaly_score" in paired and not np.array_equal(paired.image_anomaly_score.to_numpy(), anomaly_traces.primary_score.to_numpy()):
        # CSV round-tripping may differ by the last float64 digit.
        if not np.allclose(paired.image_anomaly_score.to_numpy(), anomaly_traces.primary_score.to_numpy(), rtol=0, atol=1e-12):
            raise ValueError("Diagnostic and trace scores differ")
    if "detected_at_frozen_threshold" in paired and not np.array_equal(paired.detected_at_frozen_threshold.to_numpy(), anomaly_traces.detected_at_frozen_threshold.to_numpy()):
        raise ValueError("Diagnostic and trace threshold decisions differ")
    new_columns = [c for c in diagnostics.columns if c not in traces.columns or c == "image_id"]
    return traces.merge(diagnostics[new_columns], on="image_id", how="left", validate="one_to_one")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=Path("artifacts/runs/31e0704ff1da6906"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/pcb1_a2"))
    args = parser.parse_args()
    if not args.output.is_dir():
        raise ValueError("A2 output directory must already exist")
    names = ["trace_offsets.csv", "trace_offsets.parquet", "trace_by_outcome.csv", "trace_summary.md"]
    if any((args.output/n).exists() for n in names + ["trace_by_defect_type.csv", "trace_by_defect_type_outcome.csv", "trace_manifest.json"]):
        raise FileExistsError("Refusing to overwrite A2 trace artifacts")
    predictions = pd.read_parquet(args.run/"predictions.parquet")
    threshold = json.loads((args.run/"calibration.json").read_text())["primary"]["image_threshold"]
    references = json.loads((args.run/"memory_bank_metadata.json").read_text())["references"]
    traces = trace_table(predictions, threshold, references)
    diagnostics_path = args.output/"per_anomaly_diagnostics.csv"
    if not diagnostics_path.exists():
        raise ValueError("Anomaly diagnostics required before trace publication")
    traces = join_anomaly_diagnostics(traces, pd.read_csv(diagnostics_path))
    traces.to_csv(args.output/names[0], index=False)
    traces.to_parquet(args.output/names[1], index=False)
    by_outcome = summarize_offsets(traces)
    by_outcome.to_csv(args.output/names[2], index=False)
    label_column = "defect_types" if "defect_types" in traces.columns else "defect_type"
    if label_column in traces:
        def labels(value):
            if pd.isna(value): return []
            if str(value).startswith("["): return json.loads(value)
            return str(value).split(";")
        typed = traces[traces.label == 1].copy()
        typed["defect_type"] = typed[label_column].map(labels)
        typed = typed.explode("defect_type")
        summarize_offsets(typed, "defect_type").to_csv(args.output/"trace_by_defect_type.csv", index=False)
        summarize_offsets(typed, ["defect_type", "outcome"]).to_csv(args.output/"trace_by_defect_type_outcome.csv", index=False)
    lines = ["# Run 1 maximum-score nearest-reference trace diagnostics", "",
             f"Analyzed {len(traces)} saved traces; no inference or fitting was repeated.", "",
             "Offsets use the original unregistered 32×32 feature grid. A large offset is descriptive and can reflect repeated structures, acquisition displacement, 180-degree orientation differences or implausible matching; it is not itself evidence of a defect.", ""]
    for row in by_outcome.itertuples():
        lines.append(f"- {row.outcome}: {row.n_traces} traces; median Chebyshev offset {row.median_offset_cells:.1f} cells; {row.outside_radius_2_count}/{row.n_traces} outside radius 2.")
    lines += ["", "The winning maximum-score patch may lie outside the annotation. These traces cannot establish which normal patches matched the underlying false-negative defect region, or show that cross-location matching caused a miss.", "",
              "Next useful diagnostic: before any new model, predeclare a deterministic sample spanning false-negative defect types and size quartiles, extract only those existing Run 1 query features, and inspect nearest references at annotation-intersecting grid cells. Use annotation masks solely to select retrospective diagnostic queries. Record this as new diagnostic inference, preserve Run 1 outputs, and compare matched/nonmatched controls; do not select a spatial radius from these traces alone.", "",
              "Defect-type summaries count multi-label images once in each listed type; row totals can exceed the anomaly count."]
    (args.output/names[3]).write_text("\n".join(lines)+"\n")
    inputs = [args.run/"predictions.parquet", args.run/"calibration.json",
              args.run/"memory_bank_metadata.json", diagnostics_path, Path(__file__)]
    manifest = {"run_id": str(traces.run_id.iloc[0]), "n_traces": len(traces),
                "new_inference": False, "coordinate_scope": "unregistered_32x32_Run1",
                "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                "output_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(args.output.glob("trace_*")) if p.is_file()}}
    (args.output/"trace_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")


if __name__ == "__main__":
    main()

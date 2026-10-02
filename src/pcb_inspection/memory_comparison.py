"""Artifact-backed five-recipe journey and matched memory-selection figures.

Reads existing predictions only. Run after both D recipes and independent reviews
finish; never fits, scores images, recalibrates, or accesses PCB2.
"""
import argparse
import json
from pathlib import Path
import textwrap

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

from .guard import digest, now, write_new

RECIPES = [("Run1 direct256", "artifacts/runs/31e0704ff1da6906", 256, "original"),
           ("C1 uniform256", "artifacts/runs/geometry_256_v1", 256, "uniform"),
           ("C2 uniform512", "artifacts/runs/geometry_512_v1", 512, "uniform"),
           ("D1 coreset256", "artifacts/runs/coreset_256_v1", 256, "coreset"),
           ("D2 coreset512", "artifacts/runs/coreset_512_v1", 512, "coreset")]
COLORS = {"Run1 direct256": "#888888", "C1 uniform256": "#4e79a7",
          "C2 uniform512": "#f28e2b", "D1 coreset256": "#59a14f", "D2 coreset512": "#b07aa1"}
METRICS = [("recall", "Anomaly recall ↑", 1), ("fpr", "Normal false-alarm rate ↓", 1),
           ("image_ap", "Image AP ↑", 1), ("auroc", "Image AUROC ↑", 1),
           ("median_pixel_ap", "Median per-anomaly pixel AP ↑", 1),
           ("peak_inside_count", "Map peak inside annotation / 100 ↑", 100)]


def display_name(name):
    """Keep CSV recipe identities stable while spacing labels for human readers."""
    return name.replace("direct256", "direct 256").replace("uniform256", "uniform 256").replace("uniform512", "uniform 512").replace("coreset256", "coreset 256").replace("coreset512", "coreset 512")


def read_json(path, sources):
    sources.add(Path(path))
    return json.loads(Path(path).read_text())


def read_csv(path, sources):
    sources.add(Path(path))
    return pd.read_csv(path)


def original_summary(metrics, anomalies, runtime):
    primary = metrics["primary"]
    return {"image_ap": primary["average_precision"], "auroc": primary["auroc"],
            "recall": primary["recall"], "fpr": primary["normal_false_alarm_rate"],
            "tp": primary["tp"], "fp": primary["fp"], "fn": primary["fn"], "tn": primary["tn"],
            "median_pixel_ap": float(anomalies.per_image_pixel_ap.median()),
            "pooled_pixel_ap": metrics["localization"]["pixel_average_precision"],
            "iou": metrics["localization"]["pixel_iou"],
            "peak_inside_count": int(anomalies.peak_inside_mask.sum()),
            "overlap_count": int(anomalies.any_overlap_with_mask.sum()),
            "source_median_pixel_ap": None,
            "inference_median_seconds": runtime["primary_including_features"]["median_seconds"],
            "inference_p95_seconds": runtime["primary_including_features"]["p95_seconds"]}


def revised_summary(metrics):
    image, local = metrics["image"], metrics["anomaly_localization"]["common256_"]
    return {"image_ap": image["average_precision"], "auroc": image["auroc"],
            "recall": image["recall"], "fpr": image["normal_false_alarm_rate"],
            "tp": image["tp"], "fp": image["fp"], "fn": image["fn"], "tn": image["tn"],
            "median_pixel_ap": local["median_per_image_pixel_ap"],
            "pooled_pixel_ap": metrics["localization_common256"]["pixel_average_precision"],
            "iou": metrics["localization_common256"]["pixel_iou"],
            "peak_inside_count": local["peak_inside_count"], "overlap_count": local["overlap_count"],
            "source_median_pixel_ap": metrics["anomaly_localization"]["source_"]["median_per_image_pixel_ap"],
            "inference_median_seconds": metrics["runtime"]["median_inference_seconds"],
            "inference_p95_seconds": metrics["runtime"]["p95_inference_seconds"]}


def score_rows(recipe, table, score_column, group, threshold):
    return pd.DataFrame({"recipe": recipe, "image_id": table.image_id,
                         "group": group, "score": table[score_column],
                         "image_threshold": threshold,
                         "above_threshold": table[score_column] > threshold})


def metric_bars(plt, table, output, title):
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))
    names = table.recipe.tolist()
    for ax, (metric, label, upper) in zip(axes.flat, METRICS):
        bars = ax.bar(np.arange(len(names)), table[metric], color=[COLORS[n] for n in names])
        ax.set_xticks(np.arange(len(names)), [display_name(n).replace(" ", "\n", 1) for n in names], fontsize=9)
        ax.set_ylim(0, upper * 1.13)
        ax.set_title(label)
        for bar, value in zip(bars, table[metric]):
            ax.text(bar.get_x() + bar.get_width() / 2, value + upper * .02,
                    f"{int(value)}" if upper == 100 else f"{value:.3f}", ha="center", fontsize=9)
    fig.suptitle(title + "\nC/D outcomes are PCB1 development; AP and scores are not probabilities", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, .93))
    fig.savefig(output, dpi=145)
    plt.close(fig)


def grouped_plot(plt, table, group, value, labels, output, title, ylabel):
    fig, ax = plt.subplots(figsize=(13, 5))
    names = [name for name, *_ in RECIPES]
    x, width = np.arange(len(labels)), .15
    for index, name in enumerate(names):
        part = table[table.recipe == name].set_index(group)
        ax.bar(x + (index - 2) * width, [part.loc[label, value] for label in labels],
               width, label=display_name(name), color=COLORS[name])
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(ncol=3, fontsize=9, loc="upper center", bbox_to_anchor=(.5, -.15), frameon=False)
    fig.tight_layout(rect=(0, .12, 1, 1))
    fig.savefig(output, dpi=150)
    plt.close(fig)


def build(root):
    root = Path(root).resolve()
    out = root / "artifacts/pcb1_memory_selection_comparison"
    if (out / "comparison_complete.json").exists():
        raise FileExistsError("Completed comparison is immutable")
    sources = {Path(__file__)}
    # Verify required completion/review receipts before creating any draft output.
    for _, relative, _, method in RECIPES[1:]:
        path = root / relative
        complete = read_json(path / "complete.json", sources)
        review = read_json(path / "independent_review.json", sources)
        if not review["passed"] or review["complete_sha256"] != digest(path / "complete.json"):
            raise ValueError(f"Missing or stale independent review: {relative}")
        if not complete["development_only"] or complete["pcb2_exposed"]:
            raise ValueError("Development-only comparison required")
        # Every saved outcome file is bound to its completion receipt.
        for name in ["metrics.json", "predictions.csv", "calibration.json", "normal_runtime.json",
                     "by_defect_type.csv", "by_size_quartile.csv"]:
            if digest(path / name) != complete["outputs"][name]:
                raise ValueError(f"Saved outcome changed: {relative}/{name}")
    for size in [256, 512]:
        diagnostic = read_json(root / f"artifacts/stage3_memory_diagnostics/{size}/memory_diagnostics.json", sources)
        if not diagnostic["no_anomaly_access"] or not diagnostic["no_pcb2_access"]:
            raise ValueError("Normal-only memory diagnostics required")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out.mkdir(parents=True, exist_ok=True)
    old = root / RECIPES[0][1]
    anomalies = read_csv(root / "artifacts/pcb1_a2/per_anomaly_diagnostics.csv", sources)
    rows, runtimes, phases, types, sizes, scores = [], [], [], [], [], []
    paths, thresholds, predictions = {}, {}, {}
    for name, relative, size, method in RECIPES:
        path = root / relative
        paths[name] = path
        metrics = read_json(path / "metrics.json", sources)
        calibration = read_json(path / "calibration.json", sources)
        if method == "original":
            runtime = read_json(path / "runtime.json", sources)
            row = original_summary(metrics, anomalies, runtime)
            image_threshold = calibration["primary"]["image_threshold"]
            thresholds[name] = calibration["primary"]["pixel_threshold"]
            sources.update([path / "predictions.parquet", path / "calibration_predictions.parquet"])
            test = pd.read_parquet(path / "predictions.parquet")
            cal = pd.read_parquet(path / "calibration_predictions.parquet")
            scores += [score_rows(name, cal, "primary_score", "calibration_normal", image_threshold),
                       score_rows(name, test[test.label == 0], "primary_score", "development_normal", image_threshold),
                       score_rows(name, test[test.label == 1], "primary_score", "development_anomaly", image_threshold)]
            types.append(read_csv(root / "artifacts/pcb1_a2/recall_by_defect_type.csv", sources)
                         .rename(columns={"median_per_image_pixel_ap": "median_pixel_ap"}).assign(recipe=name))
            sizes.append(read_csv(root / "artifacts/pcb1_a2/recall_by_defect_size_quartile.csv", sources)
                         .rename(columns={"median_per_image_pixel_ap": "median_pixel_ap"}).assign(recipe=name))
            prep = read_json(path / "pretest_runtime.json", sources)
            prep_seconds = prep["normal_preparation_seconds"]
            peak = runtime["process_peak_rss_bytes"]
        else:
            row = revised_summary(metrics)
            thresholds[name] = calibration["pixel_threshold"]
            image_threshold = calibration["image_threshold"]
            test = read_csv(path / "predictions.csv", sources)
            cal = read_csv(path / "calibration_predictions.csv", sources)
            predictions[name] = test.set_index("image_id")
            scores += [score_rows(name, cal, "score", "calibration_normal", image_threshold),
                       score_rows(name, test[test.label == "normal"], "score", "development_normal", image_threshold),
                       score_rows(name, test[test.label == "anomaly"], "score", "development_anomaly", image_threshold)]
            types.append(read_csv(path / "by_defect_type.csv", sources).assign(recipe=name))
            sizes.append(read_csv(path / "by_size_quartile.csv", sources).assign(recipe=name))
            prep = read_json(path / "normal_runtime.json", sources)
            prep_seconds, peak = prep["preparation_seconds"], max(prep["peak_rss_bytes"], metrics["runtime"]["peak_rss_bytes"])
            for phase, values in prep.get("phases", {}).items():
                phases.append({"recipe": name, "phase": phase, **values})
        rows.append({"recipe": name, "size": size, "selector": method,
                     "image_threshold": image_threshold, "pixel_threshold": thresholds[name], **row})
        runtimes.append({"recipe": name, "preparation_seconds": prep_seconds,
                         "physical_current_preparation_seconds": prep.get("physical_current_preparation_seconds", prep_seconds),
                         "charged_cached_extraction_seconds": prep.get("charged_cached_extraction_seconds", 0),
                         "peak_rss_bytes": peak, "median_inference_seconds": row["inference_median_seconds"],
                         "p95_inference_seconds": row["inference_p95_seconds"]})
    journey = pd.DataFrame(rows)
    journey.to_csv(out / "comparison.csv", index=False, float_format="%.17g")
    pd.DataFrame(runtimes).to_csv(out / "runtime_comparison.csv", index=False)
    pd.DataFrame(phases).to_csv(out / "runtime_phases.csv", index=False)
    type_table, size_table = pd.concat(types, ignore_index=True), pd.concat(sizes, ignore_index=True)
    type_table.to_csv(out / "type_recall_comparison.csv", index=False)
    size_table.to_csv(out / "size_localization_comparison.csv", index=False)
    score_table = pd.concat(scores, ignore_index=True)
    score_table.to_csv(out / "score_distributions.csv", index=False, float_format="%.17g")
    score_summary = score_table.groupby(["recipe", "group"]).agg(
        count=("score", "size"), mean=("score", "mean"), median=("score", "median"),
        std=("score", "std"), p90=("score", lambda v: v.quantile(.9)),
        p95=("score", lambda v: v.quantile(.95)), p99=("score", lambda v: v.quantile(.99)),
        fraction_above_threshold=("above_threshold", "mean"))
    score_summary.to_csv(out / "score_distribution_summary.csv")
    pairs = []
    for control, revised in [("C1 uniform256", "D1 coreset256"), ("C2 uniform512", "D2 coreset512")]:
        before, after = journey.set_index("recipe").loc[[control, revised]].iloc[0], journey.set_index("recipe").loc[[control, revised]].iloc[1]
        for metric, _, _ in METRICS:
            pairs.append({"control": control, "revised": revised, "metric": metric,
                          "control_value": before[metric], "revised_value": after[metric],
                          "difference_revised_minus_control": after[metric] - before[metric],
                          "preferred_direction": "lower" if metric == "fpr" else "higher"})
    pd.DataFrame(pairs).to_csv(out / "matched_pair_changes.csv", index=False)
    metric_bars(plt, journey, out / "journey.png", "Preserved original pilot and all four declared development recipes")
    matched = journey.set_index("recipe").loc[["C1 uniform256", "D1 coreset256", "C2 uniform512", "D2 coreset512"]].reset_index()
    metric_bars(plt, matched, out / "matched_pairs.png", "Matched pairs: uniform → coreset at each resolution")
    grouped_plot(plt, type_table, "defect_type", "recall", ["bent", "melt", "missing", "scratch"],
        out / "type_recall.png", "Recall by source defect type; multi-label images count in each listed type",
        "Recall at each recipe's normal-only threshold")
    grouped_plot(plt, size_table, "size_quartile", "median_pixel_ap", ["Q1", "Q2", "Q3", "Q4"],
        out / "size_quartile_localization.png", "Fixed A2 area quartiles: Q1 smallest, Q4 largest; common full-source 256 masks",
        "Median per-anomaly common256 pixel AP")
    coverage_rows, composition_rows, region_rows, image_rows, diagnostic_tables = [], [], [], [], {}
    for size in [256, 512]:
        folder = root / f"artifacts/stage3_memory_diagnostics/{size}"
        diagnostics = read_json(folder / "memory_diagnostics.json", sources)
        for method in ["uniform", "coreset"]:
            name = f"{'C' if method == 'uniform' else 'D'}{1 if size == 256 else 2} {method}{size}"
            coverage_rows.append({"recipe": name, "size": size, **{k: v for k, v in diagnostics["coverage"][method].items() if not isinstance(v, dict)}})
            comp = diagnostics["composition"][method]
            composition_rows.append({"recipe": name, "size": size,
                **{k: v for k, v in comp.items() if not isinstance(v, dict)},
                **{f"per_image_{k}": v for k, v in comp["references_per_fitting_image"].items()}})
            region_rows.append(read_csv(folder / f"{method}_normalized_crop_regions.csv", sources).assign(recipe=name))
            image_rows.append(read_csv(folder / f"{method}_references_per_image.csv", sources).assign(recipe=name))
        diagnostic_tables[size] = read_csv(folder / "coverage_distances.csv", sources)
    coverage_table, composition_table = pd.DataFrame(coverage_rows), pd.DataFrame(composition_rows)
    coverage_table.to_csv(out / "coverage_comparison.csv", index=False)
    composition_table.to_csv(out / "memory_composition.csv", index=False)
    pd.concat(region_rows, ignore_index=True).to_csv(out / "memory_regions.csv", index=False)
    pd.concat(image_rows, ignore_index=True).to_csv(out / "references_per_image.csv", index=False)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    order = ["C1 uniform256", "D1 coreset256", "C2 uniform512", "D2 coreset512"]
    coverage_index = coverage_table.set_index("recipe")
    for index, name in enumerate(order):
        axes[0, 0].bar(np.arange(3) + (index - 1.5) * .18,
            coverage_index.loc[name, ["mean", "p95", "maximum"]].to_numpy(dtype=float),
            .18, label=display_name(name), color=COLORS[name])
    axes[0, 0].set_xticks(np.arange(3), ["Mean", "95th percentile", "Maximum"])
    axes[0, 0].set_title("Fixed 2,048 queries; typical and tail distances separately")
    axes[0, 0].set_ylabel("Original 384-dimensional Euclidean distance (lower is tighter coverage)")
    axes[0, 0].legend(fontsize=9)
    composition_table = composition_table.set_index("recipe").loc[order]
    for ax, column, title, limit in [(axes[0, 1], "unique_source_images", "Fitting images represented / 723", 723),
        (axes[1, 0], "padding_center_proxy_fraction", "Reference centers outside letterbox content (proxy)", 1)]:
        ax.bar(np.arange(4), composition_table[column], color=[COLORS[n] for n in order])
        ax.set_xticks(np.arange(4), [display_name(n).replace(" ", "\n", 1) for n in order], fontsize=9)
        ax.set_ylim(0, limit * 1.08); ax.set_title(title)
    for name, table in pd.concat(image_rows).groupby("recipe"):
        axes[1, 1].step(np.sort(table.references), np.arange(1, len(table) + 1) / len(table),
                         label=display_name(name), color=COLORS[name])
    axes[1, 1].set_title("References per fitting image; zero-reference images included")
    axes[1, 1].set_xlabel("References in an image"); axes[1, 1].set_ylabel("Cumulative image fraction")
    axes[1, 1].legend(fontsize=9)
    fig.suptitle("Memory diagnostics describe a fitting-normal sample; they do not prove detection improvement")
    fig.tight_layout(rect=(0, 0, 1, .95)); fig.savefig(out / "memory_composition.png", dpi=145); plt.close(fig)
    selection = read_csv(root / "artifacts/pcb1_a2/qualitative/selection.csv", sources)
    if len(selection) != 11 or selection.image_id.duplicated().any():
        raise ValueError("The original eleven fixed A2 examples are required")
    selection.to_csv(out / "qualitative_selection.csv", index=False)
    manifest = read_csv(root / "data/manifests/pcb1_manifest.csv", sources).fillna("").set_index("image_id")
    fig, axes = plt.subplots(11, 6, figsize=(18, 30.8), squeeze=False)
    qualitative_rows = []
    for i, item in enumerate(selection.itertuples()):
        record = manifest.loc[item.image_id]
        raw = root / "data/raw" / record.image_path
        if digest(raw) != record.sha256:
            raise ValueError("Source image identity changed")
        sources.add(raw)
        with Image.open(raw) as image:
            rgb = np.asarray(ImageOps.exif_transpose(image).convert("RGB").resize((256, 256), Image.Resampling.BILINEAR))
        mask = np.zeros((256, 256), bool)
        if record.label == "anomaly":
            mask_path = root / "data/raw" / record.mask_path
            if digest(mask_path) != record.mask_sha256:
                raise ValueError("Source mask identity changed")
            sources.add(mask_path)
            with Image.open(mask_path) as image:
                mask = np.asarray(ImageOps.exif_transpose(image).convert("L").resize((256, 256), Image.Resampling.NEAREST)) > 0
        axes[i, 0].imshow(rgb)
        axes[i, 0].set_title(f"{item.image_id[:8]} · {record.label}\n" + textwrap.fill(json.loads(item.reasons)[0], 28), fontsize=8)
        axes[i, 1].imshow(mask, cmap="gray", vmin=0, vmax=1)
        axes[i, 1].set_title(f"Whole-source GT; {int(mask.sum())} pixels\nnearest resize to common 256", fontsize=8)
        for j, name in enumerate(order):
            path = paths[name] / "anomaly_maps" / f"{item.image_id}.npy"
            sources.add(path)
            values = np.load(path)
            if values.shape != (256, 256) or not np.isfinite(values).all() or thresholds[name] <= 0:
                raise ValueError("Finite common256 maps and positive pixel thresholds required")
            plot = axes[i, j + 2].imshow(values / thresholds[name], cmap="magma", vmin=0, vmax=2)
            if mask.any():
                axes[i, j + 2].contour(mask, levels=[.5], colors=["cyan"], linewidths=.7)
            prediction = predictions[name].loc[item.image_id]
            axes[i, j + 2].set_title(f"{display_name(name)} · detected={bool(prediction.detected)}\nimage score={prediction.score:.3f}", fontsize=8)
            qualitative_rows.append({"recipe": name, "image_id": item.image_id, "label": record.label,
                "score": prediction.score, "detected": prediction.detected,
                "common_mask_pixels": int(mask.sum()), "pixel_ap": prediction.pixel_ap,
                "peak_inside": prediction.peak_inside, "reasons": item.reasons})
        for ax in axes[i]:
            ax.axis("off")
    fig.suptitle("Same eleven A2 examples · full-source 256 view · cyan annotation\nDisplay map / recipe pixel threshold, clipped 0–2; not probability", fontsize=14)
    fig.tight_layout(rect=(0, 0, .965, .98))
    cax = fig.add_axes([.974, .10, .008, .75]); fig.colorbar(plot, cax=cax, label="Map / pixel threshold")
    fig.savefig(out / "fixed_a2_qualitative.png", dpi=115); plt.close(fig)
    pd.DataFrame(qualitative_rows).to_csv(out / "qualitative_metrics.csv", index=False)
    metadata = {"created_at_utc": now(), "development_only": True, "pcb2_exposed": False,
        "new_model_inference": False, "role": "Preserved pilot + PCB1 development matched-memory comparison",
        "definitions": {"fpr": "lower is better; each recipe recalibrated from the same 181 normals",
            "qualitative": "same 11 fixed A2 IDs; source GT unchanged; direct full-source common256 view",
            "heatmap_display": "map / recipe pixel threshold, display clipped 0–2; metrics use raw maps",
            "pixel_metrics": "all 200 images pooled, all 100 anomalies per-image; source medians are a separate denominator",
            "coverage": "same 2,048 fitting-normal query positions per resolution; queries may be selected references",
            "timing": "D2 (512) preparation charges original cached extraction; original pilot latency excludes raw hashing, development includes it"},
        "inputs": {str(path.relative_to(root)): digest(path) for path in sorted(sources)},
        "outputs": {path.name: digest(path) for path in sorted(out.iterdir()) if path.suffix in [".csv", ".png"]}}
    destination = out / "comparison_metadata.json"
    destination.unlink(missing_ok=True)
    write_new(destination, metadata)
    print("Built draft memory comparison; root interpretation/QA still required", out, flush=True)
    return journey


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(args.root)

"""Guarded category-adapted PCB2 confirmation; no changes to earlier stages.

Normal preparation never imports the confirmation loader or opens normal_test
images. Anomaly materialization is possible only after the shared final freeze.
"""
import argparse
import importlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import torch

from .baseline import nearest
from .calibration import calibrate
from .coreset import gaussian_projection, project_features, select_coreset
from .environment import report
from .evaluation import image_metrics, localization_metrics
from .geometry import inverse_map
from .geometry_experiment import DynamicExtractor, WEIGHT, pixel_row, score_feature, setup
from .guard import digest, now, write_new
from .memory_experiment import check_resources, padding_center, projection_digest, reference_metadata, rss_bytes, validate_selected
from .preprocessing import preprocess_mask

ROLES = {"primary": ("pcb2_d1_primary", 256), "secondary": ("pcb2_d2_secondary", 512)}
NORMAL_MANIFEST = "artifacts/stage4/pcb2_normals/normal_manifest.csv"
FROZEN_MODULES = ["acquisition", "baseline", "calibration", "coreset", "data", "diagnostics", "environment",
                  "evaluation", "geometry", "geometry_experiment", "guard", "memory_experiment",
                  "preprocessing", "provenance", "stage4_geometry", "stage4_data", "stage4_transfer",
                  "stage4_review", "pcb2_confirmation_data"]


def module_path(root, name):
    if not name.startswith("pcb_inspection.") or ".." in name:
        raise ValueError("Project-owned module required")
    return root / "src" / Path(*name.split(".")).with_suffix(".py")


def validate_config(config):
    selector = config["selector"]
    expected = {"memory_count": 4096, "all_fitting_candidates": True,
                "projection_dimensions": 64, "scoring_dimensions": 384,
                "projection_seed": 43, "selection_seed": 42, "initial_anchor_count": 10}
    if any(selector.get(k) != value for k, value in expected.items()):
        raise ValueError("Frozen Stage 3 selector controls must remain unchanged")
    calibration = config["calibration"]
    if any(calibration.get(k) != value for k, value in {
        "image_quantile": .95, "pixel_quantile": .99, "method": "higher", "comparison": ">"}.items()):
        raise ValueError("Original normal-only calibration policy required")
    if not isinstance(config["geometry"], dict):
        raise ValueError("Reviewed geometry parameters must be concrete before freezing")
    if config.get("retuning_after_unseal") is not False or config.get("anomaly_access_before_finalfreeze") is not False:
        raise ValueError("Sealed no-retuning confirmation required")
    return config


def normal_frame(root, config):
    frame = pd.read_csv(root / config.get("normal_manifest", NORMAL_MANIFEST), keep_default_na=False)
    required = {"image_id", "image_path", "sha256", "label", "split"}
    if not required.issubset(frame) or frame.empty or frame.image_id.duplicated().any():
        raise ValueError("Unique nonempty normal manifest required")
    if not frame.label.eq("normal").all() or not frame.split.isin(["fit", "calibration", "normal_test"]).all():
        raise ValueError("Only declared normal partitions permitted before final freeze")
    for column in ["mask_path", "mask_sha256", "defect_types"]:
        if column in frame and frame[column].astype(str).str.len().gt(0).any():
            raise ValueError("Normal-only manifest cannot contain anomaly annotations")
    if not {"fit", "calibration", "normal_test"}.issubset(set(frame.split)):
        raise ValueError("Fitting, calibration and final held-out normals required")
    if frame.groupby("sha256").split.nunique().gt(1).any():
        raise ValueError("Exact-duplicate leakage across normal partitions")
    return frame


def verify_inputs(root, receipt):
    for name, expected in receipt["frozen_files"].items():
        if digest(root / name) != expected:
            raise ValueError(f"Frozen identity changed: {name}")


def normal_protocol(root):
    path = root / "artifacts/stage4/normal_protocol.json"
    protocol = json.loads(path.read_text())
    verify_inputs(root, protocol)
    validate_config(protocol["config"])
    return protocol


def tensor_and_transform(root, row, size, config):
    if getattr(row, "split", None) == "normal_test" and not (root / "artifacts/stage4/freeze_receipt.json").exists():
        raise ValueError("Held-out normals remain sealed until the final freeze")
    if row.label != "normal" and not (root / "artifacts/stage4/anomaly_access.json").exists():
        raise ValueError("Anomaly access remains sealed")
    raw = root / row.image_path
    if digest(raw) != row.sha256:
        raise ValueError("Image identity changed")
    module = importlib.import_module(config.get("geometry_module", "pcb_inspection.stage4_geometry"))
    return module.tensor_and_transform(root, row, size, config)


def freeze_normal(root, config_path):
    root = Path(root).resolve()
    config_path = Path(config_path)
    config = validate_config(json.loads((root / config_path).read_text()))
    frame = normal_frame(root, config)
    review_path = config.get("geometry_review", "artifacts/stage4/geometry_preflight/normal_geometry_review.json")
    geometry = json.loads((root / review_path).read_text())
    if not geometry["passed"] or geometry["geometry"] != config["geometry"]:
        raise ValueError("Passing normal-only geometry review for exact chosen parameters required")
    if (root / "artifacts/stage4/anomaly_access.json").exists():
        raise ValueError("Fresh confirmation already unsealed")
    files = [str(config_path), config.get("normal_manifest", NORMAL_MANIFEST), review_path, WEIGHT,
             "requirements.lock"] + config.get("provenance_inputs", [])
    files += [f"src/pcb_inspection/{name}.py" for name in FROZEN_MODULES]
    patterns = ["test_models.py", "test_coreset.py", "test_geometry*.py", "test_memory_experiment.py",
                "test_data.py", "test_guard.py", "test_stage4*.py", "test_pcb2_confirmation*.py"]
    files += [str(path.relative_to(root)) for pattern in patterns for path in sorted((root / "tests").glob(pattern))]
    # The loader source is pinned, but deliberately not imported or called here.
    files += [str(module_path(root, config.get("geometry_module", "pcb_inspection.stage4_geometry")).relative_to(root)),
              str(module_path(root, config.get("test_loader_module", "pcb_inspection.pcb2_confirmation_data")).relative_to(root))]
    write_new(root / "artifacts/stage4/normal_protocol.json", {
        "frozen_at_utc": now(), "config": config, "normal_split_counts": frame.groupby("split").size().to_dict(),
        "primary": {"role": "primary", "input_size": 256}, "secondary": {"role": "secondary", "input_size": 512},
        "anomalies_exposed": False, "held_out_normals_decoded": False,
        "frozen_files": {name: digest(root / name) for name in sorted(set(files))}})


def project_normals(root, fit, size, out, config, extractor, started):
    grid = size // 8
    projection = gaussian_projection(384, 64, 43)
    destination = out / "projected_features.npy"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("Projected candidates already exist")
    projected = np.lib.format.open_memmap(destination, mode="w+", dtype="float32", shape=(len(fit) * grid * grid, 64))
    for start in range(0, len(fit), 4):
        rows = list(fit.iloc[start:start + 4].itertuples())
        if any(row.split != "fit" or row.label != "normal" for row in rows):
            raise ValueError("Fitting normals only")
        pairs = [tensor_and_transform(root, row, size, config) for row in rows]
        features = extractor(torch.stack([pair[0] for pair in pairs]))
        if tuple(features.shape[1:]) != (384, grid, grid):
            raise ValueError("Frozen feature geometry differs")
        flattened = features.permute(0, 2, 3, 1).reshape(-1, 384).numpy()
        begin = start * grid * grid
        projected[begin:begin + len(flattened)] = project_features(flattened, projection).numpy()
        check_resources(started, config)
        if start % 80 == 0:
            print("PCB2 fitting-normal projection", size, start, "/", len(fit), flush=True)
    projected.flush()
    return projected, projection


def reextract_normals(root, fit, selected, size, config, extractor, started):
    grid = size // 8
    selected = validate_selected(selected, len(fit) * grid * grid, 4096)
    images = selected // (grid * grid)
    bank = torch.empty((4096, 384), dtype=torch.float32)
    transforms = {}
    unique = np.unique(images)
    for start in range(0, len(unique), 4):
        source_indices = unique[start:start + 4]
        rows = [next(fit.iloc[[int(index)]].itertuples()) for index in source_indices]
        pairs = [tensor_and_transform(root, row, size, config) for row in rows]
        features = extractor(torch.stack([pair[0] for pair in pairs]))
        for local, index in enumerate(source_indices):
            positions = np.flatnonzero(images == index)
            cells = selected[positions] % (grid * grid)
            bank[positions] = features[local, :, cells // grid, cells % grid].T
            transforms[rows[local].image_id] = pairs[local][1]
        check_resources(started, config)
    if not torch.isfinite(bank).all():
        raise ValueError("Nonfinite normal reference features")
    return bank, transforms


def prepare(root, size):
    root = Path(root).resolve()
    if size not in [256, 512]:
        raise ValueError("Primary256/secondary512 only")
    shared = normal_protocol(root)
    config = shared["config"]
    setup(root)
    name = "pcb2_d1_primary" if size == 256 else "pcb2_d2_secondary"
    out = root / "artifacts/stage4" / name
    out.mkdir(parents=True, exist_ok=False)
    cache = root / "data/cache/stage4" / name
    cache.mkdir(parents=True, exist_ok=False)
    paths = {key: str((cache / filename).relative_to(root)) for key, filename in {
        "memory": "memory.npy", "projected": "projected_features.npy", "calibration_maps": "calibration_maps.npy",
        "calibration_model_maps": "calibration_model_maps", "model_maps": "model_maps", "anomaly_maps": "anomaly_maps"}.items()}
    write_new(out / "array_paths.json", paths)
    write_new(out / "protocol.json", {"input_size": size, "role": "primary" if size == 256 else "secondary",
              "normal_protocol_sha256": digest(root / "artifacts/stage4/normal_protocol.json"), "config": config})
    write_new(out / "prepare_started.json", {"started_at_utc": now(), "normal_only": True,
              "normal_protocol_sha256": digest(root / "artifacts/stage4/normal_protocol.json")})
    started = time.perf_counter()
    frame = normal_frame(root, config)
    fit = frame[frame.split == "fit"].reset_index(drop=True)
    calibration = frame[frame.split == "calibration"]
    phases = {}
    tick = time.perf_counter(); extractor = DynamicExtractor()
    phases["backbone_load"] = {"seconds": time.perf_counter() - tick, "peak_rss_bytes": rss_bytes()}
    tick = time.perf_counter()
    projected, projection = project_normals(root, fit, size, cache, config, extractor, started)
    phases["projection"] = {"seconds": time.perf_counter() - tick, "peak_rss_bytes": rss_bytes()}
    tick = time.perf_counter()
    selected = select_coreset(torch.from_numpy(projected), count=4096, seed=42, initial_count=10,
        deadline_seconds=config["caps"]["preparation_seconds"] - (time.perf_counter() - started),
        progress=lambda *args: print("PCB2 normal coreset", size, *args, flush=True))
    selected = validate_selected(selected, len(projected), 4096)
    phases["selection"] = {"seconds": time.perf_counter() - tick, "peak_rss_bytes": rss_bytes()}
    candidate_count = len(projected); del projected
    np.save(out / "selected_indices.npy", selected)
    tick = time.perf_counter()
    bank, transforms = reextract_normals(root, fit, selected, size, config, extractor, started)
    phases["reextraction"] = {"seconds": time.perf_counter() - tick, "peak_rss_bytes": rss_bytes()}
    np.save(cache / "memory.npy", bank.numpy())
    references = reference_metadata(selected, fit, transforms, size)
    write_new(out / "memory_metadata.json", {"references": references, "fit_image_ids": fit.image_id.tolist(),
        "count": 4096, "candidate_count": candidate_count, "fraction": 4096 / candidate_count,
        "grid_shape": [size // 8] * 2, "bytes": bank.numel() * 4, "scoring_dimensions": 384,
        "projection_sha256": projection_digest(projection), "selection_projection_only": True,
        "represented_fit_images": len(set(r["image_id"] for r in references)),
        "padding_center_fraction": float(np.mean([r["is_padding_center"] for r in references]))})
    write_new(out / "fit_reference_transforms.json", transforms)
    maps = np.lib.format.open_memmap(cache / "calibration_maps.npy", mode="w+", dtype="float32", shape=(len(calibration), 256, 256))
    calibration_model_maps = cache / "calibration_model_maps"; calibration_model_maps.mkdir(exist_ok=False)
    records, timings, calibration_transforms = [], [], {}; tick = time.perf_counter()
    for index, row in enumerate(calibration.itertuples()):
        if row.label != "normal" or row.split != "calibration":
            raise ValueError("Calibration normals only")
        begin = time.perf_counter()
        tensor, transform = tensor_and_transform(root, row, size, config)
        score, model_map, common = score_feature(extractor(tensor[None]), bank, size, transform)
        seconds = time.perf_counter() - begin; timings.append(seconds); maps[index] = common
        np.save(calibration_model_maps / f"{row.image_id}.npy", model_map)
        calibration_transforms[row.image_id] = transform
        records.append({"image_id": row.image_id, "score": score, "seconds": seconds, "fallback": transform["fallback"]})
        if index == 4:
            check_resources(started, config, float(np.median(timings)))
            write_new(out / "normal_smoke.json", {"count": 5, "median_inference_seconds": float(np.median(timings)), "peak_rss_bytes": rss_bytes()})
        check_resources(started, config)
    maps.flush(); table = pd.DataFrame(records); table.to_csv(out / "calibration_predictions.csv", index=False)
    write_new(out / "calibration_transforms.json", calibration_transforms)
    write_new(out / "calibration.json", calibrate(table.score.to_numpy(), maps)); del maps
    phases["calibration"] = {"seconds": time.perf_counter() - tick, "peak_rss_bytes": rss_bytes()}
    runtime = {"preparation_seconds": time.perf_counter() - started, "peak_rss_bytes": rss_bytes(),
               "median_inference_seconds": float(np.median(timings)), "p95_inference_seconds": float(np.quantile(timings, .95)), "phases": phases}
    check_resources(started, config, runtime["median_inference_seconds"])
    write_new(out / "normal_runtime.json", runtime)
    required = [out / name for name in ["protocol.json", "array_paths.json", "prepare_started.json", "memory_metadata.json", "selected_indices.npy",
                "fit_reference_transforms.json", "calibration_transforms.json", "calibration_predictions.csv", "calibration.json", "normal_runtime.json"]]
    required += [cache / name for name in ["memory.npy", "calibration_maps.npy", "projected_features.npy"]]
    required += sorted(calibration_model_maps.glob("*.npy"))
    write_new(out / "prepared.json", {"completed_at_utc": now(), "resource_gate_passed": True, "normal_only": True,
        "normal_test_decoded": False, "normal_protocol_sha256": digest(root / "artifacts/stage4/normal_protocol.json"),
        "array_paths": paths, "prerequisites": {str(path.relative_to(root)): digest(path) for path in required}})
    print("Prepared PCB2 normals only", name, runtime, flush=True)


def verify_prepared(root, out):
    protocol = normal_protocol(root)
    prepared = json.loads((out / "prepared.json").read_text())
    if not prepared["resource_gate_passed"] or not prepared["normal_only"] or prepared["normal_test_decoded"]:
        raise ValueError("Passing sealed normal-only preparation required")
    if prepared["normal_protocol_sha256"] != digest(root / "artifacts/stage4/normal_protocol.json"):
        raise ValueError("Normal protocol identity changed")
    for name, expected in prepared["prerequisites"].items():
        if digest(root / name) != expected:
            raise ValueError(f"Prepared artifact changed: {name}")
    return protocol


def freeze_confirmation(root):
    root = Path(root).resolve()
    protocol = normal_protocol(root)
    if (root / "artifacts/stage4/anomaly_access.json").exists():
        raise ValueError("Confirmation already unsealed")
    files = dict(protocol["frozen_files"])
    files["artifacts/stage4/normal_protocol.json"] = digest(root / "artifacts/stage4/normal_protocol.json")
    for name, _ in ROLES.values():
        out = root / "artifacts/stage4" / name
        verify_prepared(root, out)
        review = json.loads((out / "independent_normal_review.json").read_text())
        if not review["passed"] or review["prepared_sha256"] != digest(out / "prepared.json"):
            raise ValueError("Passing independent normal preparation review required")
        for path in [out / "prepared.json", out / "independent_normal_review.json"]:
            files[str(path.relative_to(root))] = digest(path)
    environment = root / "artifacts/stage4/environment.json"
    write_new(environment, report())
    files[str(environment.relative_to(root))] = digest(environment)
    write_new(root / "artifacts/stage4/freeze_receipt.json", {
        "frozen_at_utc": now(), "config": protocol["config"], "normal_split_counts": protocol["normal_split_counts"],
        "primary": {"run": "pcb2_d1_primary", "input_size": 256},
        "secondary": {"run": "pcb2_d2_secondary", "input_size": 512},
        "anomaly_access_status": "sealed", "held_out_normals_status": "not decoded or scored",
        "frozen_files": files})


def claim_confirmation(root, role):
    if role not in ROLES:
        raise ValueError("Predeclared primary/secondary roles only")
    stage = root / "artifacts/stage4"
    receipt = json.loads((stage / "freeze_receipt.json").read_text())
    verify_inputs(root, receipt)
    name, _ = ROLES[role]
    out = stage / name
    verify_prepared(root, out)
    if role == "secondary" and not (stage / "pcb2_d1_primary/complete.json").is_file():
        raise ValueError("Primary confirmation must complete before secondary analysis")
    if role == "primary":
        write_new(stage / "anomaly_access.json", {"first_anomaly_access_utc": now(),
            "freeze_receipt_sha256": digest(stage / "freeze_receipt.json"), "primary": name,
            "secondary_predeclared": "pcb2_d2_secondary", "access_scope": "Shared dataset unseal; each recipe once"})
    else:
        access = json.loads((stage / "anomaly_access.json").read_text())
        if access["freeze_receipt_sha256"] != digest(stage / "freeze_receipt.json"):
            raise ValueError("Shared unseal identity changed")
    write_new(out / "confirmation_access.json", {"started_at_utc": now(), "role": role,
              "freeze_receipt_sha256": digest(stage / "freeze_receipt.json"), "evaluation_count": 1})
    return receipt


def validate_test_frame(frame, normals):
    required = {"image_id", "image_path", "sha256", "label", "mask_path", "mask_sha256"}
    if not required.issubset(frame) or frame.empty or frame.image_id.duplicated().any():
        raise ValueError("Unique complete confirmation manifest required")
    if not frame.label.isin(["normal", "anomaly"]).all() or not frame.label.eq("anomaly").any():
        raise ValueError("Both normal and anomalous confirmation images required")
    held = normals[normals.split == "normal_test"].set_index("image_id")
    observed = frame[frame.label == "normal"].set_index("image_id")
    if set(held.index) != set(observed.index) or not held.sha256.sort_index().equals(observed.sha256.sort_index()):
        raise ValueError("Declared held-out normal identities changed")
    construction = normals[normals.split.isin(["fit", "calibration"])]
    if set(frame.image_id) & set(construction.image_id) or set(frame.sha256) & set(construction.sha256):
        raise ValueError("Confirmation leakage into fitting/calibration")
    if frame.groupby("sha256").size().gt(1).any():
        raise ValueError("Duplicate confirmation observations require explicit invalidation")


def evaluate(root, role):
    root = Path(root).resolve()
    receipt = claim_confirmation(root, role)
    config = receipt["config"]
    name, size = ROLES[role]
    out = root / "artifacts/stage4" / name
    # Importing/calling the data loader occurs only after the shared unseal receipt.
    loader = importlib.import_module(config.get("test_loader_module", "pcb_inspection.pcb2_confirmation_data"))
    frame = getattr(loader, config.get("test_loader_function", "load_test_manifest"))(root, config)
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("Confirmation loader must return a DataFrame")
    validate_test_frame(frame, normal_frame(root, config))
    frame = frame.reset_index(drop=True)
    frame.to_csv(out / "confirmation_manifest.csv", index=False)
    arrays = json.loads((out / "array_paths.json").read_text())
    bank = torch.from_numpy(np.load(root / arrays["memory"]))
    metadata = json.loads((out / "memory_metadata.json").read_text())
    fit_ids = set(normal_frame(root, config).query("split == 'fit'").image_id)
    if bank.shape != (4096, 384) or not torch.isfinite(bank).all() or any(r["image_id"] not in fit_ids for r in metadata["references"]):
        raise ValueError("Invalid fitting-only reference bank")
    setup(root); extractor = DynamicExtractor()
    thresholds = json.loads((out / "calibration.json").read_text())
    mapdir, modeldir = root / arrays["anomaly_maps"], root / arrays["model_maps"]
    mapdir.mkdir(exist_ok=False); modeldir.mkdir(exist_ok=False)
    records, transforms, all_maps, masks, timings = [], {}, [], [], []
    started = time.perf_counter()
    for index, row in enumerate(frame.itertuples()):
        tick = time.perf_counter()
        tensor, transform = tensor_and_transform(root, row, size, config)
        score, model_map, common = score_feature(extractor(tensor[None]), bank, size, transform)
        seconds = time.perf_counter() - tick; timings.append(seconds)
        if row.label == "anomaly":
            mask_path = root / row.mask_path
            if not row.mask_path or digest(mask_path) != row.mask_sha256:
                raise ValueError("Abnormal mask identity missing or changed")
            mask = preprocess_mask(mask_path)
        else:
            mask = np.zeros((256, 256), bool)
        all_maps.append(common); masks.append(mask); transforms[row.image_id] = transform
        np.save(mapdir / f"{row.image_id}.npy", common); np.save(modeldir / f"{row.image_id}.npy", model_map)
        record = {"image_id": row.image_id, "image_path": row.image_path, "label": row.label,
                  "score": score, "detected": score > thresholds["image_threshold"], "seconds": seconds,
                  "fallback": transform["fallback"], "crop_area_fraction": transform["crop_area_fraction"],
                  **pixel_row(mask, common, thresholds["pixel_threshold"])}
        if row.label == "anomaly":
            record["defect_types"] = getattr(row, "defect_types", "[]")
            labels = json.loads(record["defect_types"])
            if not isinstance(labels, list) or any(not isinstance(value, str) for value in labels):
                raise ValueError("Source defect labels must preserve a JSON list")
            with Image.open(mask_path) as opened:
                source_mask = np.asarray(ImageOps.exif_transpose(opened).convert("L")) > 0
            source_map = inverse_map(model_map, transform)
            if source_mask.shape != source_map.shape or not source_mask.any():
                raise ValueError("Abnormal source mask geometry/positive region invalid")
            record.update({f"source_{key}": value for key, value in pixel_row(source_mask, source_map, thresholds["pixel_threshold"]).items()})
            x0, y0, x1, y1 = transform["crop_box"]
            record["source_annotation_outside_crop_fraction"] = 1 - float(source_mask[y0:y1, x0:x1].sum() / source_mask.sum())
            record["reference_area_band"] = f"R{1 + int(np.searchsorted(config['size_slices']['edges'], record['mask_area_fraction'], side='left'))}"
        records.append(record)
        if index % 25 == 0:
            print("PCB2 frozen confirmation", role, index, "/", len(frame), flush=True)
    table = pd.DataFrame(records)
    anomalous = table[table.label == "anomaly"].copy()
    # Supplementary size grouping uses area alone after unseal, never model outcomes.
    edges = np.quantile(anomalous.mask_area_fraction, [.25, .5, .75], method="higher")
    table.loc[table.label == "anomaly", "pcb2_size_quartile"] = [f"Q{1 + int(np.searchsorted(edges, value, side='left'))}" for value in anomalous.mask_area_fraction]
    table.to_csv(out / "predictions.csv", index=False)
    table.to_csv(out / "per_image_scores.csv", index=False)
    anomalous = table[table.label == "anomaly"].copy()
    anomalous.to_csv(out / "per_anomaly_localization.csv", index=False)
    write_new(out / "test_transforms.json", transforms)
    metrics = {"role": role, "input_size": size,
        "image": image_metrics(table.label.eq("anomaly"), table.score.to_numpy(), thresholds["image_threshold"]),
        "localization_common256": localization_metrics(np.asarray(masks), np.asarray(all_maps), thresholds["pixel_threshold"]),
        "anomaly_localization": {},
        "runtime": {"total_evaluation_seconds": time.perf_counter() - started,
                    "median_inference_seconds": float(np.median(timings)), "p95_inference_seconds": float(np.quantile(timings, .95)), "peak_rss_bytes": rss_bytes()},
        "geometry": {"fallback_count": int(table.fallback.sum()),
                     "anomaly_with_annotation_outside_crop_count": int(anomalous.source_annotation_outside_crop_fraction.gt(0).sum()),
                     "maximum_annotation_outside_fraction": float(anomalous.source_annotation_outside_crop_fraction.max())},
        "memory": {key: metadata[key] for key in ["count", "candidate_count", "fraction", "represented_fit_images", "padding_center_fraction"]}}
    for prefix in ["", "source_"]:
        metrics["anomaly_localization"][prefix or "common256_"] = {
            "anomaly_count": len(anomalous), "median_per_image_pixel_ap": float(anomalous[prefix + "pixel_ap"].median()),
            "q25": float(anomalous[prefix + "pixel_ap"].quantile(.25)), "q75": float(anomalous[prefix + "pixel_ap"].quantile(.75)),
            "peak_inside_count": int(anomalous[prefix + "peak_inside"].sum()), "overlap_count": int(anomalous[prefix + "overlap"].sum())}
    write_new(out / "metrics.json", metrics)
    write_new(out / "size_group_definitions.json", {"reference_edges": config["size_slices"]["edges"],
              "pcb2_supplement_edges": edges.tolist(), "ties": "lower band; searchsorted left", "empty_groups_retained": True})
    typed = []
    for row in anomalous.itertuples():
        for label in json.loads(row.defect_types):
            typed.append({"defect_type": label, "detected": row.detected, "pixel_ap": row.pixel_ap, "source_pixel_ap": row.source_pixel_ap})
    if typed:
        pd.DataFrame(typed).groupby("defect_type").agg(sample_count=("detected", "size"), detected_count=("detected", "sum"),
            recall=("detected", "mean"), median_pixel_ap=("pixel_ap", "median"), median_source_pixel_ap=("source_pixel_ap", "median")).to_csv(out / "by_defect_type.csv")
    else:
        pd.DataFrame(columns=["defect_type", "sample_count", "detected_count", "recall", "median_pixel_ap", "median_source_pixel_ap"]).to_csv(out / "by_defect_type.csv", index=False)
    for group, labels in [("reference_area_band", ["R1", "R2", "R3", "R4"]), ("pcb2_size_quartile", ["Q1", "Q2", "Q3", "Q4"])]:
        sliced = anomalous.groupby(group).agg(sample_count=("detected", "size"), detected_count=("detected", "sum"), recall=("detected", "mean"),
            median_pixel_ap=("pixel_ap", "median"), median_source_pixel_ap=("source_pixel_ap", "median")).reindex(labels)
        sliced[["sample_count", "detected_count"]] = sliced[["sample_count", "detected_count"]].fillna(0).astype(int)
        sliced.to_csv(out / f"by_{group}.csv")
    outputs = {str(path.relative_to(root)): digest(path) for path in sorted(out.rglob("*")) if path.is_file()}
    outputs.update({str(path.relative_to(root)): digest(path) for folder in [mapdir, modeldir] for path in sorted(folder.glob("*.npy"))})
    for path in sorted((root / "artifacts/stage4/confirmation_data").glob("*")):
        if path.is_file():
            outputs[str(path.relative_to(root))] = digest(path)
    write_new(out / "complete.json", {"completed_at_utc": now(), "role": role, "confirmatory": True,
        "freeze_receipt_sha256": digest(root / "artifacts/stage4/freeze_receipt.json"), "outputs": outputs})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze-normal", "prepare", "freeze-confirmation", "evaluate"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--config", default="configs/stage4_protocol.json")
    parser.add_argument("--size", type=int, choices=[256, 512])
    parser.add_argument("--role", choices=["primary", "secondary"])
    args = parser.parse_args()
    if args.action == "freeze-normal": freeze_normal(args.root, args.config)
    elif args.action == "prepare": prepare(args.root, args.size)
    elif args.action == "freeze-confirmation": freeze_confirmation(args.root)
    else: evaluate(args.root, args.role)

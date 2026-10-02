"""Bounded full-population projected-coreset PCB1 development experiments.

Projection is for selection only. Scoring retains all 384 frozen channels and
the geometry experiment's padding, mapping, calibration and evaluation policies.
"""
import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import torch

from .calibration import calibrate
from .coreset import gaussian_projection, project_features, select_coreset
from .evaluation import image_metrics, localization_metrics
from .geometry import inverse_map
from .geometry_experiment import (
    DynamicExtractor, MANIFEST, WEIGHT, pixel_row, score_feature, setup,
    tensor_and_transform, verify_recipe as verify_geometry_recipe,
)
from .guard import digest, now, write_new
from .preprocessing import preprocess_mask
from .baseline import nearest

SOURCE_FILES = [MANIFEST, WEIGHT, "src/pcb_inspection/geometry.py",
                "src/pcb_inspection/geometry_experiment.py",
                "src/pcb_inspection/preprocessing.py", "src/pcb_inspection/coreset.py"]


def projection_digest(projection):
    return hashlib.sha256(projection.cpu().numpy().tobytes()).hexdigest()


def rss_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def check_resources(started, config, median_seconds=None):
    caps = config["caps"]
    if time.perf_counter() - started > caps["preparation_seconds"]:
        raise RuntimeError("Preparation deadline exceeded; no anomaly access permitted")
    if rss_bytes() > caps["peak_rss_bytes"]:
        raise RuntimeError("Peak RSS cap exceeded; no anomaly access permitted")
    if median_seconds is not None and median_seconds > caps["median_inference_seconds"]:
        raise RuntimeError("Normal median latency cap exceeded; no anomaly access permitted")


def validate_selected(selected, candidate_count, count):
    selected = np.asarray(selected)
    if selected.ndim != 1 or len(selected) != count or not np.issubdtype(selected.dtype, np.integer):
        raise ValueError("Coreset must supply the declared count of integer indices")
    if len(np.unique(selected)) != count or (selected < 0).any() or (selected >= candidate_count).any():
        raise ValueError("Invalid, repeated, or out-of-population coreset indices")
    return selected.astype(np.int64)


def padding_center(row, column, transform):
    # This is a feature-cell bin-center proxy, not receptive-field support.
    x, y = (column + .5) * 8, (row + .5) * 8
    return not (transform["pad_x"] <= x < transform["pad_x"] + transform["content_width"]
                and transform["pad_y"] <= y < transform["pad_y"] + transform["content_height"])


def reference_metadata(selected, fit, transforms, size):
    grid = size // 8
    records = []
    for order, flat_index in enumerate(selected):
        image_index, cell = divmod(int(flat_index), grid * grid)
        row, column = divmod(cell, grid)
        image_id = fit.iloc[image_index].image_id
        records.append({"memory_index": order, "selection_order": order,
                        "flat_index": int(flat_index), "image_id": image_id,
                        "row": row, "column": column,
                        "is_padding_center": padding_center(row, column, transforms[image_id])})
    return records


def coverage_diagnostics(queries, bank, query_indices, bank_indices):
    distances, indices = nearest(queries, bank, 256)
    values = distances.numpy()
    summary = {"sample_count": len(values), "dimensions": 384, "units": "Euclidean",
            "mean": float(values.mean()), "median": float(np.median(values)),
            "p95": float(np.quantile(values, .95)), "maximum": float(values.max()),
            "query_index_in_bank_count": int(len(np.intersect1d(query_indices, bank_indices))),
            "zero_distance_count": int((values == 0).sum()),
            "query_rule": "sorted 2048 candidate indices sampled without replacement, default_rng seed44"}
    return summary, values, indices.numpy()


def project_candidates(root, size, destination, started, config, *, extractor=None):
    """Stream every fitting patch to a 64D disk bank; never retain full 384D bank."""
    root, destination = Path(root), Path(destination)
    frame = pd.read_csv(root / MANIFEST).fillna("")
    fit = frame[frame.split == "fit"].reset_index(drop=True)
    if not (fit.label == "normal").all():
        raise ValueError("Only fitting normals can construct a candidate bank")
    grid = size // 8
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("Refusing to overwrite projected candidate features")
    projection = gaussian_projection(384, 64, 43)
    projected = np.lib.format.open_memmap(destination, mode="w+", dtype="float32",
                                         shape=(len(fit) * grid * grid, 64))
    extractor = extractor or DynamicExtractor()
    transforms = {}
    for start in range(0, len(fit), 4):
        rows = list(fit.iloc[start:start + 4].itertuples())
        pairs = [tensor_and_transform(root, row, size) for row in rows]
        features = extractor(torch.stack([pair[0] for pair in pairs]))
        if tuple(features.shape[1:]) != (384, grid, grid):
            raise ValueError("Unexpected extractor feature geometry")
        flat = features.permute(0, 2, 3, 1).reshape(-1, 384).numpy()
        reduced = project_features(flat, projection)
        begin = start * grid * grid
        projected[begin:begin + len(flat)] = reduced.numpy()
        for row, pair in zip(rows, pairs):
            transforms[row.image_id] = pair[1]
        if start % 80 == 0:
            print("Projected fitting normals", size, start, "/", len(fit), flush=True)
        check_resources(started, config)
    projected.flush()
    return projected, fit, transforms, projection


def reextract_selected(root, size, selected, fit, extractor, started, config):
    """Recover 384D scoring vectors in selection order using bounded image batches."""
    grid = size // 8
    candidate_count = len(fit) * grid * grid
    selected = validate_selected(selected, candidate_count, config["memory_count"])
    images = selected // (grid * grid)
    memory = torch.empty((len(selected), 384), dtype=torch.float32)
    transforms = {}
    unique_images = np.unique(images)
    for begin in range(0, len(unique_images), 4):
        image_indices = unique_images[begin:begin + 4]
        rows = [next(fit.iloc[[int(i)]].itertuples()) for i in image_indices]
        pairs = [tensor_and_transform(root, row, size) for row in rows]
        features = extractor(torch.stack([pair[0] for pair in pairs]))
        for local_index, image_index in enumerate(image_indices):
            positions = np.flatnonzero(images == image_index)
            cell = selected[positions] % (grid * grid)
            memory[positions] = features[local_index, :, cell // grid, cell % grid].T
            transforms[rows[local_index].image_id] = pairs[local_index][1]
        check_resources(started, config)
    if not torch.isfinite(memory).all():
        raise ValueError("Nonfinite recovered reference features")
    return memory, transforms


def validate_engineering_cache(root, config):
    root = Path(root)
    descriptor = root / config["projected_cache_descriptor"]
    evidence = json.loads(descriptor.read_text())
    if not evidence["normal_only"] or not evidence["resource_gate_passed"]:
        raise ValueError("Normal-only engineering gate required for cached candidates")
    if evidence["projection_sha256"] != projection_digest(gaussian_projection(384, 64, 43)):
        raise ValueError("Projection matrix identity mismatch")
    if set(evidence["source_sha256"]) != set(SOURCE_FILES):
        raise ValueError("Incomplete engineering cache input identities")
    for source, expected in evidence["source_sha256"].items():
        if digest(root / source) != expected:
            raise ValueError(f"Engineering cache source changed: {source}")
    cache = root / evidence["cache_path"]
    if digest(cache) != evidence["cache_sha256"]:
        raise ValueError("Engineering candidate cache changed")
    features = np.load(cache, mmap_mode="r")
    fit_count = int((pd.read_csv(root / MANIFEST).split == "fit").sum())
    if features.dtype != np.float32 or features.shape != (fit_count * (config["input_size"] // 8) ** 2, 64):
        raise ValueError("Engineering cache geometry mismatch")
    return features, cache


def verify_recipe(root, out):
    protocol = json.loads((out / "protocol.json").read_text())
    for source, expected in protocol["frozen_files"].items():
        if digest(root / source) != expected:
            raise ValueError(f"Frozen Stage 3 identity changed: {source}")
    verify_geometry_recipe(root, root / protocol["preserved_control"])
    if protocol["config"]["development_only"] is not True or protocol["config"]["pcb2_exposed"] is not False:
        raise ValueError("PCB1 development-only recipe required")
    return protocol


def freeze(root, size):
    root = Path(root).resolve()
    if size not in (256, 512):
        raise ValueError("Declared resolutions only")
    control = root / f"artifacts/runs/geometry_{size}_v1"
    old = verify_geometry_recipe(root, control)
    if not (control / "complete.json").is_file():
        raise ValueError("Preserved completed Stage 2 control required")
    config = dict(old["config"])
    config.update({"memory_selector": "full-population approximate greedy projected coreset",
                   "projection_dimensions": 64, "projection_seed": 43,
                   "projection_distribution": "Gaussian 384x64; defined by frozen coreset.py",
                   "selection_seed": 42, "initial_point_count": 10,
                   "selection_initialization": "mean Euclidean distance to 10 seeded random candidate points",
                   "selection_update": "minimum Euclidean distance to each selected center; farthest remaining candidate",
                   "selection_tie": "first candidate flat index",
                   "memory_order": "selection order; NN distance ties take first memory index",
                   "candidate_order": "manifest fitting-image order, row-major layer2 feature grid",
                   "padding_eligibility": "all patches, unchanged from geometry control",
                   "padding_center_proxy": "cell bin center ((column+.5)*8,(row+.5)*8), not receptive-field extent",
                   "coverage_query_count": 2048, "coverage_query_seed": 44,
                   "coverage_query_rule": "all fitting positions; sorted default_rng without replacement, same queries for both banks",
                   "coverage_units": "original 384-dimensional Euclidean scoring space",
                   "projected_cache_descriptor": "artifacts/stage3_engineering/engineering.json" if size == 512 else None})
    files = list(old["frozen_files"])
    files += [str(p.relative_to(root)) for p in sorted((root / "src/pcb_inspection").glob("*.py"))]
    files += [str(p.relative_to(root)) for p in sorted((root / "tests").glob("test_*.py"))]
    files += [str((control / name).relative_to(root)) for name in ["protocol.json", "complete.json", "memory.npy", "memory_metadata.json"]]
    if size == 512:
        _, cache = validate_engineering_cache(root, config)
        files += [config["projected_cache_descriptor"], str(cache.relative_to(root))]
    scope = root / "docs/development/stage3_scope.json"
    if scope.exists():
        files.append(str(scope.relative_to(root)))
    files += [name for name in ["docs/development/stage3_method_notes.md", "configs/stage3_protocol.json"] if (root / name).exists()]
    out = root / f"artifacts/runs/coreset_{size}_v1"
    out.mkdir(parents=True, exist_ok=False)
    write_new(out / "protocol.json", {"frozen_at_utc": now(), "config": config,
              "preserved_control": str(control.relative_to(root)),
              "frozen_files": {name: digest(root / name) for name in sorted(set(files))}})
    print("Frozen Stage 3 before candidate selection", out, flush=True)


def prepare(root, size):
    root = Path(root).resolve()
    out = root / f"artifacts/runs/coreset_{size}_v1"
    protocol = verify_recipe(root, out)
    config = protocol["config"]
    setup(root)
    write_new(out / "prepare_started.json", {"started_at_utc": now(),
              "protocol_sha256": digest(out / "protocol.json"), "normal_only": True})
    physical_started = time.perf_counter()
    charged_extraction_seconds = 0.0
    if config["projected_cache_descriptor"]:
        engineering = json.loads((root / config["projected_cache_descriptor"]).read_text())
        charged_extraction_seconds = float(engineering["feature_extraction_seconds"])
    # Charge the cached extraction to the gate as if this recipe built it itself.
    started = physical_started - charged_extraction_seconds
    phases = {}
    backbone_tick = time.perf_counter()
    extractor = DynamicExtractor()
    phases["backbone_load"] = {"seconds": time.perf_counter() - backbone_tick, "peak_rss_bytes": rss_bytes()}
    frame = pd.read_csv(root / MANIFEST).fillna("")
    fit = frame[frame.split == "fit"].reset_index(drop=True)
    cal = frame[frame.split == "calibration"]
    if not (fit.label == "normal").all() or not (cal.label == "normal").all():
        raise ValueError("Fitting and calibration normals only")
    phase = time.perf_counter()
    if config["projected_cache_descriptor"]:
        projected, cache = validate_engineering_cache(root, config)
        projection = gaussian_projection(384, 64, 43)
        write_new(out / "candidate_cache.json", {"cache_path": str(cache.relative_to(root)),
                  "sha256": digest(cache), "reused_normal_only_engineering_cache": True})
    else:
        projected, fit, _, projection = project_candidates(root, size,
            out / "cache/projected_features.npy", started, config, extractor=extractor)
    phases["projection"] = {"seconds": time.perf_counter() - phase, "peak_rss_bytes": rss_bytes(),
                             "projection_sha256": projection_digest(projection),
                             "charged_cached_extraction_seconds": charged_extraction_seconds}
    check_resources(started, config)
    phase = time.perf_counter()
    projected_tensor = torch.from_numpy(projected)
    selected = select_coreset(projected_tensor, count=4096, seed=42, initial_count=10,
                              deadline_seconds=config["caps"]["preparation_seconds"] - (time.perf_counter() - started),
                              progress=lambda *args: print("Coreset", size, *args, flush=True))
    selected = validate_selected(selected, len(projected), 4096)
    phases["selection"] = {"seconds": time.perf_counter() - phase, "peak_rss_bytes": rss_bytes()}
    np.save(out / "selected_indices.npy", selected)
    candidate_count = len(projected)
    del projected_tensor, projected
    check_resources(started, config)
    phase = time.perf_counter()
    queries = np.sort(np.random.default_rng(44).choice(candidate_count, size=2048, replace=False))
    np.save(out / "coverage_query_indices.npy", queries)
    union_indices = np.unique(np.concatenate([selected, queries]))
    recovered, transforms = reextract_selected(root, size, union_indices, fit, extractor,
                                               started, {**config, "memory_count": len(union_indices)})
    memory = recovered[np.searchsorted(union_indices, selected)].clone()
    query_vectors = recovered[np.searchsorted(union_indices, queries)].clone()
    del recovered
    (out / "cache").mkdir(exist_ok=True)
    np.save(out / "cache/coverage_queries.npy", query_vectors.numpy())
    np.save(out / "cache/query_flat_indices.npy", queries)
    phases["reextraction"] = {"seconds": time.perf_counter() - phase, "peak_rss_bytes": rss_bytes()}
    np.save(out / "memory.npy", memory.numpy())
    write_new(out / "fit_reference_transforms.json", transforms)
    write_new(out / "memory_metadata.json", {"references": reference_metadata(selected, fit, transforms, size),
        "fit_image_ids": fit.image_id.tolist(), "count": len(memory), "candidate_count": candidate_count,
        "fraction": len(memory) / candidate_count, "grid_shape": [size // 8] * 2, "bytes": memory.numel() * 4,
        "selection_projection_only": True, "scoring_dimensions": 384})
    phase = time.perf_counter()
    control = root / protocol["preserved_control"]
    uniform = torch.from_numpy(np.load(control / "memory.npy"))
    control_metadata = json.loads((control / "memory_metadata.json").read_text())
    uniform_indices = np.array([r["flat_index"] for r in control_metadata["references"]], dtype=np.int64)
    uniform_summary, uniform_distances, uniform_nearest = coverage_diagnostics(query_vectors, uniform, queries, uniform_indices)
    coreset_summary, coreset_distances, coreset_nearest = coverage_diagnostics(query_vectors, memory, queries, selected)
    distance_table = pd.DataFrame({"query_index": np.arange(len(queries)), "flat_index": queries,
        "uniform_nearest_distance": uniform_distances, "coreset_nearest_distance": coreset_distances,
        "uniform_nearest_memory_index": uniform_nearest, "coreset_nearest_memory_index": coreset_nearest,
        "uniform_query_is_selected_reference": np.isin(queries, uniform_indices),
        "coreset_query_is_selected_reference": np.isin(queries, selected)})
    distance_table.to_csv(out / "coverage_distances.csv", index=False, float_format="%.17g")
    coverage = {"uniform_control": uniform_summary, "coreset": coreset_summary,
                "query_indices_sha256": digest(out / "coverage_query_indices.npy"),
                "queries_may_coincide_with_selected_references": True}
    write_new(out / "coverage.json", coverage)
    counts = np.bincount(selected // (size // 8) ** 2, minlength=len(fit))
    references = reference_metadata(selected, fit, transforms, size)
    write_new(out / "memory_composition.json", {"represented_fit_images": int((counts > 0).sum()),
              "selected_duplicate_indices": 0,
              "duplicate_feature_vector_count": int(len(memory) - len(np.unique(memory.numpy(), axis=0))),
              "total_fit_images": len(fit), "references_per_fit_image_minimum": int(counts.min()),
              "references_per_fit_image_median": float(np.median(counts)),
              "references_per_fit_image_p95": float(np.quantile(counts, .95)),
              "references_per_fit_image_maximum": int(counts.max()),
              "padding_center_count": sum(r["is_padding_center"] for r in references),
              "padding_center_fraction": float(np.mean([r["is_padding_center"] for r in references])),
              "padding_proxy": config["padding_center_proxy"]})
    phases["preparation_diagnostics"] = {"seconds": time.perf_counter() - phase, "peak_rss_bytes": rss_bytes()}
    del query_vectors, uniform
    check_resources(started, config)
    maps = np.lib.format.open_memmap(out / "calibration_maps.npy", mode="w+", dtype="float32",
                                     shape=(len(cal), 256, 256))
    records, timings = [], []
    phase = time.perf_counter()
    for i, row in enumerate(cal.itertuples()):
        tick = time.perf_counter()
        tensor, transform = tensor_and_transform(root, row, size)
        score, _, common = score_feature(extractor(tensor[None]), memory, size, transform)
        timings.append(time.perf_counter() - tick)
        maps[i] = common
        records.append({"image_id": row.image_id, "score": score, "seconds": timings[-1], "fallback": transform["fallback"]})
        if i == 4:
            smoke = {"normal_images": 5, "median_inference_seconds": float(np.median(timings)),
                     "peak_rss_bytes": rss_bytes(), "new_test_evidence": False}
            write_new(out / "normal_smoke.json", smoke)
            check_resources(started, config, smoke["median_inference_seconds"])
        if i % 40 == 0:
            print("Calibration normals", size, i, "/", len(cal), flush=True)
        check_resources(started, config)
    maps.flush()
    table = pd.DataFrame(records)
    table.to_csv(out / "calibration_predictions.csv", index=False)
    thresholds = calibrate(table.score.to_numpy(), maps)
    write_new(out / "calibration.json", thresholds)
    del maps
    phases["calibration"] = {"seconds": time.perf_counter() - phase, "peak_rss_bytes": rss_bytes()}
    runtime = {"preparation_seconds": time.perf_counter() - started, "peak_rss_bytes": rss_bytes(),
               "physical_current_preparation_seconds": time.perf_counter() - physical_started,
               "charged_cached_extraction_seconds": charged_extraction_seconds,
               "median_inference_seconds": float(np.median(timings)),
               "p95_inference_seconds": float(np.quantile(timings, .95)), "phases": phases}
    check_resources(started, config, runtime["median_inference_seconds"])
    write_new(out / "normal_runtime.json", runtime)
    required = ["selected_indices.npy", "memory.npy", "memory_metadata.json", "fit_reference_transforms.json",
                "calibration_predictions.csv", "calibration_maps.npy", "calibration.json", "normal_runtime.json",
                "coverage_query_indices.npy", "coverage.json", "memory_composition.json",
                "coverage_distances.csv", "cache/coverage_queries.npy", "cache/query_flat_indices.npy"]
    write_new(out / "prepared.json", {"completed_at_utc": now(), "resource_gate_passed": True,
        "protocol_sha256": digest(out / "protocol.json"), "prerequisites": {name: digest(out / name) for name in required}})
    print("Prepared normals only", size, runtime, flush=True)


# Evaluation body intentionally preserves the Stage 2 metric definitions.
def evaluate(root,size):
 root=Path(root).resolve();out=root/f'artifacts/runs/coreset_{size}_v1';protocol=verify_recipe(root,out);setup(root)
 prep=json.loads((out/'prepared.json').read_text());assert prep['resource_gate_passed'] and prep['protocol_sha256']==digest(out/'protocol.json')
 for p,h in prep['prerequisites'].items():
  if digest(out/p)!=h:raise ValueError('Prepared prerequisite mismatch')
 metadata=json.loads((out/'memory_metadata.json').read_text())
 members=pd.read_csv(root/MANIFEST).fillna('')
 fit_ids=set(members.loc[members.split=='fit','image_id']);test_ids=set(members.loc[members.split=='test','image_id'])
 if set(metadata['fit_image_ids'])!=fit_ids or any(r['image_id'] not in fit_ids for r in metadata['references']) or not fit_ids.isdisjoint(test_ids):raise ValueError('Reference leakage/membership failure')
 if metadata['count']!=4096 or metadata['scoring_dimensions']!=384:raise ValueError('Reference recipe mismatch')
 write_new(out/'development_access.json',{'started_at_utc':now(),'role':'PCB1 development, already exposed in A2','protocol_sha256':digest(out/'protocol.json'),'prepared_sha256':digest(out/'prepared.json'),'evaluation_count':1})
 bank=torch.from_numpy(np.load(out/'memory.npy'));ext=DynamicExtractor();f=pd.read_csv(root/MANIFEST).fillna('');test=f[f.split=='test'];assert set(test.image_id).isdisjoint(set(f[f.split=='fit'].image_id))
 thresh=json.loads((out/'calibration.json').read_text());annotations=pd.read_csv(root/'artifacts/pcb1_a2/per_anomaly_diagnostics.csv').set_index('image_id');records=[];transforms={};maps=[];masks=[];timings=[]
 mapdir=out/'anomaly_maps';mapdir.mkdir(exist_ok=False);modeldir=out/'model_maps';modeldir.mkdir(exist_ok=False)
 for i,row in enumerate(test.itertuples()):
  tick=time.perf_counter();x,t=tensor_and_transform(root,row,size);score,model_map,common=score_feature(ext(x[None]),bank,size,t);seconds=time.perf_counter()-tick;timings.append(seconds)
  mask=preprocess_mask(root/'data/raw'/row.mask_path) if row.label=='anomaly' else np.zeros((256,256),bool)
  maps.append(common);masks.append(mask);transforms[row.image_id]=t;np.save(mapdir/f'{row.image_id}.npy',common);np.save(modeldir/f'{row.image_id}.npy',model_map)
  record={'image_id':row.image_id,'image_path':row.image_path,'label':row.label,'score':score,'detected':score>thresh['image_threshold'],'seconds':seconds,'fallback':t['fallback'],'crop_area_fraction':t['crop_area_fraction'],**pixel_row(mask,common,thresh['pixel_threshold'])}
  if row.label=='anomaly':
   a=annotations.loc[row.image_id];record.update({'defect_types':a.defect_types,'size_quartile':a.size_quartile})
   source=inverse_map(model_map,t)
   if digest(root/'data/raw'/row.mask_path)!=row.mask_sha256:raise ValueError('Source mask hash changed')
   with Image.open(root/'data/raw'/row.mask_path) as m:sm=np.asarray(ImageOps.exif_transpose(m).convert('L'))>0
   sr=pixel_row(sm,source,thresh['pixel_threshold']);record.update({f'source_{k}':v for k,v in sr.items()})
   x0,y0,x1,y1=t['crop_box'];record['source_annotation_outside_crop_fraction']=1-float(sm[y0:y1,x0:x1].sum()/sm.sum())
  records.append(record)
  if i%25==0:print('development',size,i,'/',len(test),flush=True)
 pd.DataFrame(records).to_csv(out/'predictions.csv',index=False);write_new(out/'test_transforms.json',transforms)
 maps=np.asarray(maps);masks=np.asarray(masks);labels=(test.label=='anomaly').to_numpy();metrics={'image':image_metrics(labels,np.array([r['score'] for r in records]),thresh['image_threshold']),'localization_common256':localization_metrics(masks,maps,thresh['pixel_threshold']),'anomaly_localization':{}}
 anomaly=pd.DataFrame(records)[labels]
 for prefix in ['','source_']:
  metrics['anomaly_localization'][prefix or 'common256_']={'median_per_image_pixel_ap':float(anomaly[prefix+'pixel_ap'].median()),'q25':float(anomaly[prefix+'pixel_ap'].quantile(.25)),'q75':float(anomaly[prefix+'pixel_ap'].quantile(.75)),'peak_inside_count':int(anomaly[prefix+'peak_inside'].sum()),'overlap_count':int(anomaly[prefix+'overlap'].sum())}
 metrics['memory']={'count':metadata['count'],'candidate_count':metadata['candidate_count'],'fraction':metadata['fraction'],'selector':'projected approximate greedy coreset','scoring_dimensions':384}
 metrics['runtime']={'median_inference_seconds':float(np.median(timings)),'p95_inference_seconds':float(np.quantile(timings,.95)),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};metrics['geometry']={'fallback_count':int(pd.DataFrame(records).fallback.sum()),'anomaly_with_annotation_outside_crop_count':int((anomaly.source_annotation_outside_crop_fraction>0).sum()),'maximum_annotation_outside_fraction':float(anomaly.source_annotation_outside_crop_fraction.max())}
 write_new(out/'metrics.json',metrics)
 types=[]
 for r in anomaly.itertuples():
  for typ in json.loads(r.defect_types):types.append({'defect_type':typ,'detected':r.detected,'pixel_ap':r.pixel_ap,'source_pixel_ap':r.source_pixel_ap})
 for key,table in [('defect_type',pd.DataFrame(types)),('size_quartile',anomaly)]:
  table.groupby(key).agg(sample_count=('detected','size'),detected_count=('detected','sum'),recall=('detected','mean'),median_pixel_ap=('pixel_ap','median'),median_source_pixel_ap=('source_pixel_ap','median')).to_csv(out/f'by_{key}.csv')
 write_new(out/'complete.json',{'completed_at_utc':now(),'development_only':True,'pcb2_exposed':False,'protocol_sha256':digest(out/'protocol.json'),'outputs':{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()}})
 print('Complete',size,json.dumps(metrics),flush=True)


if __name__ == '__main__':
 parser=argparse.ArgumentParser()
 parser.add_argument('action',choices=['freeze','prepare','evaluate'])
 parser.add_argument('--root',default='.')
 parser.add_argument('--size',type=int,choices=[256,512],required=True)
 args=parser.parse_args()
 globals()[args.action](args.root,args.size)

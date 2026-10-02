# Phase A findings: PCB1 visual inspection

Completed 2026-10-01 America/Vancouver. Recommendation: **stop/revise methodology**.
The repository and tested reproducible pilot are complete; this frozen recipe does
not yet support sufficiently consistent small-region inspection to advance the app.
No threshold or recipe was changed after final benchmark scoring.

## Measured evidence

Run `31e0704ff1da6906`. Official test:100 anomalies/100 normals, benchmark prevalence 50%.
Both methods share the frozen pretrained backbone and fitting/calibration membership.

| Frozen method | Image AP | AUROC | TP | FP | FN | TN | Precision | Recall | Normal false alarms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Global embedding nearest normal |0.8276|0.7872|43|2|57|98|95.56%|43%|2/100 (2%)|
| PatchCore-inspired |0.8516|0.8654|43|9|57|91|82.69%|43%|9/100 (9%)|

Thresholds were calibrated from 181 normals, using95th percentile `higher` and strict
`>`: baseline 0.0661174655; primary 2.4000701904. The illustrative5% calibration policy
does not guarantee5% future false alarms. Primary ranking improves AUROC by 0.0782
and AP by 0.0240; it catches no additional anomalies at the declared threshold and
adds seven false alarms. No statistical significance or factory transfer is asserted.

Primary localization at 256x256, all 200 test images including implicit-zero normals:
pooled **pixel AP 0.79198**; global pixel IoU **0.12182** at the frozen normal-only
99th-percentile map threshold1.8157923222. Intersected positive pixels54,333;
union446,022; annotated positive pixels61,045 of 13,107,200 total pixels.

The pooled metric conceals major variation. A **post-final descriptive check** across
all 100 anomalous images gives median per-image pixel AP **0.03934** (mean 0.2112).
The raw map's peak lies inside the annotation for **26/100** images; **79/100** have
any positive mask overlap at the frozen pixel threshold. These supplemental metrics
were added to investigate localization consistency, not to retune or replace the
predeclared primary metric. They exclude normals; pooled pixel AP above includes them.
Large annotated areas contribute more pixels to pooled AP. Neither pooled AP alone
nor any overlap alone proves consistently useful small-defect localization.

The fixed retrospective panel includes the lowest-scoring anomaly, highest-scoring
normal, median-scoring anomaly and highest-scoring anomaly. The strongest example
highlights a large annotated region. Small annotated regions receive broad/diffuse
maps, and the high-scoring normal highlights an unannotated background feature.
These views support the limitation rather than a reliable small-region detector claim.

## Runtime and resource evidence

M2 Pro/16GB RAM; CPU, four PyTorch threads. MPS was unavailable in this execution
context, although the installed PyTorch build contains MPS support.

| Measurement | Observed |
| --- | ---: |
| Normal fitting+calibration preparation |72.49s|
| Baseline warm median / p95, including features |0.0241s /0.0280s|
| Primary warm median / p95, including features |0.3069s /0.3355s|
| First primary image, excluding model loads |0.3205s|
| Cold backbone / reference-memory loads |1.0260s /0.00564s|
| Final evaluation, excluding integrity hashing/reference load |65.96s|
| Preparation peak process RSS |1.61GiB|
| Final evaluation peak process RSS |1.32GiB|
| Primary 4096x384 float32 memory |6MiB|

Warm latency excludes the first image (199 observations); the two methods share one
feature extraction in the final loop. Process peak RSS uses macOS `getrusage`, not
system-wide memory. These measurements do not include an LLM or review application.

Setup observation spans 961.20s from clone timestamp to protocol freeze, including
research, implementation and waits. Dependency environment-to-lock span 486.55s.
Successful selective data acquisition 211.27s; this excludes interrupted attempts.
These filesystem/timer measurements are documented in`artifacts/setup_runtime.json`;
they are not clean installation benchmarks or promised reproduction times.

## Data fitness and limitations

Owner-hosted VisA PCB1, CC BY4.0. Audit: 1104 RGB images 1404x1070, no exclusions,
no exact duplicate groups, consistent owner annotations and official split.
Fit 723/calibration181/test200. Training-only perceptual-hash screening 1261 pairs;
20-pair numeric inspection found different thumbnails, without proving physical
board independence. Source provides no board IDs, groups or factory timestamps.

Direct256-square resizing reduces resolution and changes aspect ratio. No full
anomaly mask disappears, but resized annotation-area fractions range 0.9201–1.1938
relative to source. This says nothing about preservation of small visible defects.
Uniform memory sampling may undersample normal modes. Neither limitation is proven
to be the sole cause of weak performance. No fine tuning or test-guided selection
occurred. Original PatchCore uses a coreset and different scoring options; this is
explicitly **PatchCore-inspired**, not a published-method reproduction.

Controlled defects, one category, unknown object independence and50% benchmark
anomaly prevalence prevent factory performance or savings claims. ImageNet checkpoint
commercial/redistribution rights remain unverified; weights are local and ignored.

## Validation and decision

All **30 automated tests pass**. Protocol/source/config/manifest/weight hashes were
frozen before fitting and final scoring. The exclusive final gate checked passing
tests, calibration identities, fitting membership and resource budget. There was
one hardware smoke, one normal preparation and one final evaluation per method.
No invalidation, final rerun, anomalous development tuning or Phase B/C work occurred.
Structural dataset audit read test labels/masks for integrity before freeze; model
scoring and held-out result inspection occurred only after the guarded access receipt.

Independent verifier recomputed image AP/AUROC/confusion, pooled pixel AP/IoU from
saved maps and independently decoded masks. All200 evidence reference memberships
and grid coordinates were checked; three score-independent image IDs had winning
patch scores/nearest references independently recomputed in float64. This is sampled
numerical trace verification, not all 200 feature recomputations. The executed notebook
reads saved artifacts; all four localization examples and quantitative figures were
visually inspected. An arithmetic disagreement would invalidate the recommendation;
none was found.

**Stop/revise methodology** follows from 57% missed anomalies, worse false alarms than
the baseline at equal recall, and uneven small-region localization. Fast runtime and
correct provenance are useful engineering results, but do not overcome these limits.

If continuing, propose a separately frozen bounded study of higher-resolution/tiled
features and a coreset reference memory, with an honest plan for fresh evaluation.
The already viewed PCB1 test cannot become untouched evidence again. A new category
can supply separately frozen evidence but does not erase the PCB1 result. Do not
build the review workflow or claim inspection reliability from this run alone.

## Inspect and reproduce

- `notebooks/pcb1_pilot.ipynb`: executed companion with tables, comparisons and examples.
- `artifacts/runs/31e0704ff1da6906/`: predictions, metrics, calibration, runtime, maps,
  provenance, memory reference metadata, completion hashes and independent verification.
- `notebooks/review_localization.py`: repeat the post-final supplemental check.
- `docs/protocol.json`, `docs/exposure_ledger.md`: frozen decisions and actual exposure.
- `docs/source_research.md`, `docs/data_card.md`, `docs/model_card.md`: source/use limits.

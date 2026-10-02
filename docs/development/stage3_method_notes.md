# Stage3 method controls: projected approximate greedy selection

Written October2,2026 before D1/D2 outcomes. Stage3 is explicitly authorized PCB1
development work. This note documents the intended method and checks; actual frozen
protocols and measured resource receipts remain the execution authority. No PCB2
data is accessed here.

## Verified author algorithm and our declared departure

Primary source: [Amazon Science sampler.py at fcaa92f124fb1ad74a7acf56726decd4b27cbcad](https://github.com/amazon-science/patchcore-inspection/blob/fcaa92f124fb1ad74a7acf56726decd4b27cbcad/src/patchcore/sampler.py).
`ApproximateGreedyCoresetSampler` defaults to128 projected dimensions and10 random
starting points. Projection is an untrained `torch.nn.Linear` with no bias. The
initial anchor score for each candidate is the **mean Euclidean distance** to
the starting points, which NumPy samples without replacement. At each iteration,
select the maximum anchor score, compute Euclidean distance to that selected
candidate, and update anchor scores by elementwise minimum. The requested count is
`int(N * percentage)`. Selection operates on projected features; returned reference
vectors are from the original feature bank. This avoids a full N×N distance matrix
but requires repeated candidate scans.

Our proposed selection-only Gaussian projection to64 dimensions is a documented
departure from the author default128/untrained-linear projection. It is a single
bounded **projected approximate greedy** recipe, not an exact PatchCore reproduction.
Freeze distribution/scaling, random generator, seed, projection matrix hash, float
dtype, candidate ordering, initialization, distance implementation and tie policy.
Final anomaly scoring retains the384-dimensional ResNet18 features. Our seeded
NumPy `default_rng` anchor sampling also differs from the author's legacy global
`np.random.choice` stream; reproducibility requires its explicit generator identity.

If squared anchor distances are used to avoid later square roots, preserve the
initializer mathematically: compute mean Euclidean first, **then square it**.
Mean squared distance is a different initializer and can choose another first
reference. After correctly initialized squaring, min/argmax order is equivalent
because square is monotonic on nonnegative distances. Numerical cancellation,
float precision and ties still need tests. A direct synthetic oracle should verify
initialization, the first selections and later updates independently. An initial
independent check of the new selector matched a NumPy float64 direct-distance
oracle for20 selections across four synthetic80×11 matrices/seeds. This checks
ordinary non-tied initialization/update arithmetic; it does not validate full-bank
runtime or guarantee identical floating-point behavior for all near ties.

Ten initial points seed distances; they are not automatically the first ten output
references. Explicitly exclude already-selected indices after each selection.
All-identical features otherwise make repeated `argmax` choose the same index.
Exactly4096 unique **indices** are required, but different indices may have identical
feature vectors. Report vector duplicates separately if measured; do not equate
index uniqueness with feature diversity or silently remove candidates.

## Full population and resource gate

Candidate population remains all fitting-normal feature positions, including gray
padding centers, in the same source-image/grid ordering as C1/C2. At256 this is
723×32×32=740,352 positions; at512 it is723×64×64=2,961,408. Every selected reference
must resolve to one of those fitting image IDs and its actual grid coordinate.
Neither calibration normals nor development anomalies enter selection.

Projection may be streamed into a disk-backed candidate array. Preserve global
candidate indices across extraction batches; a batch-local index is insufficient.
No candidate pre-sampling or silent fallback belongs in the matched comparison.
Re-extract the selected384-dimensional features with frozen geometry/weights and
verify a deterministic sample independently. Memory count remains4096 for all
compared banks, not5–10%.

One normal-only engineering pilot may run the first64 greedy iterations against
the full projected512 bank before freezing D1/D2. Record feature/projection time,
initialization time,64-step selection time, peak RSS, estimated4096-step time and
the estimate's assumptions. Linear extrapolation estimates feasibility; it does not
certify a gate pass. Do not use its bank for detector outcomes or inspect anomalies.

Actual total normal preparation must satisfy a strict **1800seconds** deadline,
including extraction, projection, all4096 selections, full-dimensional reference
re-extraction, calibration and required preparation diagnostics. Resource checks
must run within greedy loops/batches and fail before anomaly evaluation. Peak
process RSS is bounded at8GiB; the normal smoke and final calibration median
inference must remain≤10seconds. If construction cannot pass, preserve the stop
receipt and propose a changed bounded study. A64-dimensional projection or any
resource revision must be frozen before new outcome access, never tuned to recall.

## Matched calibration, maps and evidence

D1 compares only to C1; D2 only to C2. Keep input/crop/margin/letterbox/fallback,
feature aggregation, Euclidean score, maximum image rule, interpolation and all-patch
eligibility exactly matched. Padding exclusion now would add a second intervention.
Thresholds recalibrate on the same181 normals with image95th/common-map99th
quantiles, `higher` and strict `>`; do not reuse numeric C1/C2 thresholds or an A2
oracle operating point.

Strip letterboxing, inverse-map into the full source image with outside-crop scores
zero, and preserve the full source ground truth. Compare common full-image256
maps to masks nearest-resized directly from source. Source per-image summaries are
supporting views at a different denominator. Do not compare newly cropped masks
with old full-image masks, or quietly remove unobserved positives. Keep all200
images in pooled common AP and all100 anomalies in per-image summaries. Preserve
fixed A2 size groups, multi-label membership conventions and qualitative IDs.

Each selected-reference record needs global candidate index, selection order,
fitting image ID and grid row/column. Map grid-center coordinates through that
image's transform when displaying source references. Crop/padding offsets differ
by image; equal feature-grid coordinates do not imply equal physical PCB components.
Save transform/source hashes and projection identity with the selection table.

## Coverage measurements and interpretation

Use one predetermined fitting-normal diagnostic query set per resolution, identical
for uniform/representative banks. Freeze IDs/global indices and diagnostic seed
before any new anomaly result. State whether query positions can coincide with
selected references; their zero distances can affect summaries. Do not choose a
query subset because its distances favor one selector.

Report nearest-reference distance mean/median/p95/max in **original384-dimensional
scoring space**. Projected64-space distances are useful selector diagnostics but
have another scale and are not interchangeable. Keep units Euclidean throughout
coverage arithmetic; squared distances need explicit naming. Add sample count,
represented fitting-image count, references-per-image distribution and broad
normalized-region/padding-center composition. A padding-center proxy describes
center position only, not the whole receptive field.

Coverage may improve on the query subset without improving anomaly ranking,
normal FPR or defect localization. Report that mixed outcome. A positive matched
result supports this selector under this projection/count/geometry on PCB1
development; it does not prove memory was the unique causal bottleneck. A negative
result rejects neither all coreset methods nor all memory-capacity hypotheses.
Farthest-first can retain unusual healthy modes or emphasize noise/outliers; neither
mechanism is established from composition counts alone.

Do not publish D1/D2 comparisons until independent identity, selected-count and
membership checks, sampled vector re-extraction, quantile ranks, all200 decisions,
independent image AP/AUROC and all100 common per-anomaly localization checks pass.
Track source-metric independent-recalculation limits explicitly. Preserve C1/C2,
Run1 and A2 snapshots and record any invalidation as a new run identity.

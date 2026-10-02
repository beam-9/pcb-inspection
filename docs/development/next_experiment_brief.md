# Next experiment: improve detail with an explainable comparison

Prepared 2026-10-02 after A2. **Proposed, not executed or frozen for confirmation.**

The initial target is source-labeled scratch/melt and small annotated regions.
A2 establishes association and where to look; it does not establish a root cause.
The intervention asks whether putting more pixels on the board improves localization
without changing the pretrained representation or reference-memory count.

| Step | Change | What it can tell us | What it cannot tell us |
| --- | --- | --- | --- |
| G0 normal-only geometry feasibility | Detect board, preserve aspect, assess pose/alignment, retain source transforms | Whether a deterministic crop/pose procedure works and reverses correctly | Detector accuracy or a universal PCB detector |
| C1 geometry block | Verified crop/pose/aspect procedure at 256; existing ResNet18/scoring/4096 reference policy | Effect of the documented geometry block relative to preserved Run 1 | Separate causal effects of crop, pose and padding inside that block |
| C2 resolution | Same C1 geometry at 512; same backbone, memory count, aggregation and scoring | Incremental effect of resolution under a fixed memory budget | A pure benefit independent of memory coverage: fixed count samples a smaller fraction |

Start with these two detector configurations, not the entire handoff's grid. G0 is
an engineering prerequisite, not an anomaly-performance experiment. Choose content/
landmarks/templates using fitting normals. Test deterministic transforms, inverse
mapping, margins around edge components and known 180-degree ambiguity. Do not assume
a homography is required or beneficial; measure normal residuals and failures before
choosing a more complex registration. Record fallback behavior or reject failed crops.

Before each detector run, save config/code/input identities, deterministic fitting/
calibration membership, coordinate/valid-region rules, random seeds, memory counts
and interpolation. Calibrate from the same normal-only partition under the original
95th/99th percentile higher/strict-greater policy for comparability. The A2 ROC oracle
threshold is not a substitute. Evaluate each declared recipe once on PCB1 development
and report all outcomes, including regressions. All future PCB1 results are development.

Report image AP/AUROC, normal FPR and recall at the recalibrated fixed policy; per-image
localization median/IQR, type and size slices, peak/overlap counts, IoU; transform
failures; memory count/fraction; preparation time, peak RSS and median/p95 inference.
Map predictions back to source coordinates, then score against a declared common
geometry so changing resolution does not silently change the evaluation denominator.
Retain a matched 256 reference view plus source-resolution localization where feasible;
record mask interpolation and avoid comparing AP at different pixel grids as if equal.

Proposed initial engineering caps: peak RSS 8 GiB, median inference 10 seconds,
preparation 30 minutes per recipe. Stop before anomaly evaluation if the normal-only
smoke exceeds a cap; revise and record configuration while still in development.
These are resource limits, not quality acceptance targets or expected measurements.

Only after these comparisons: test uniform versus approximate greedy memory selection
at matched actual bank counts. Report projection, candidate-pool reduction and effective
fraction; a capped 4096/16384 bank is not a 5–10% coreset at 512. A WideResNet candidate
requires a separate smoke and explicit paper-versus-author-code choice. Co-occurring
changes in embedding reduction, squared/Euclidean distance, neighbor aggregation,
image-score weighting and Gaussian smoothing must be tracked, not hidden behind
“faithful PatchCore.” Spatial restrictions wait for reliable registered coordinates.

The final choice must weigh localization consistency, review burden and resources.
No numeric quality pass target is invented after viewing results. Freeze the entire
selected algorithm and category-adaptation procedure before acquiring/inspecting PCB2
anomaly evidence. Fit PCB2's own allowed normals and calibrate its own normal threshold
under that frozen procedure; explain this as fresh-category recipe confirmation,
not zero-shot transfer of the PCB1 memory. Keep factory claims outside this benchmark.

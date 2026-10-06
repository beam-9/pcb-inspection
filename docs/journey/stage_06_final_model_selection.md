# Stage 6 — Final model selection

## Stage 6A completed; final freeze remains pending

Stage6A analyzed the remaining PCB2 development failures without changing the detector. The strongest observable pattern is **limited defect-score separation at the frozen operating threshold**, with generally strong GT patch ranks. The evidence does not establish one dominant, remediable backbone, resolution or aggregation mechanism. The decision gate takes the supplied proposal's **Branch D: recommend freezing the current D2+orientation candidate and documenting unresolved limitations, rather than forcing Stage6B**. This is a technical recommendation, not a formal Modelv1.0 freeze or authorization to build the UI. No final-model receipt has been created.

The human request was to review and implement Stage6A. The supplied Stage6 document also describes Stage6B, model publication and UI; those sections supplied context, not additional requested work. Historical Stage4 D1 remains the portfolio primary; Stage5C D2+orientation remains the current high-sensitivity development candidate.

## Why Stage 6A exists

Stage5C removed much of the reversed-pose response while preserving D2's91/100 anomaly detections and4/100 normal flags. Canonical missing/small defects still failed. Stage6A asks whether the model fails to represent their union-GT regions, misranks them, or has insufficient decision margin. These are exposed PCB2 development results, not fresh confirmation, causal resolution evidence or factory validation.

See the [proposal review](../development/stage6a_plan_review.md), [frozen protocol](../../artifacts/stage6a/protocol.json), [target manifest](../../artifacts/stage6a/target_manifest.csv) and [decision gate](../../artifacts/stage6a/decision_gate.json).

## Population and preserved recipe

The fixed union contains36 anomalies: all12 canonical source-missing-label cases, all29 fixed R1/R2 cases and the reversed Stage5C rescue `bfebbd19caf4dad38fd66eab`. Cohorts overlap. Six canonical missing cases are missed; eight R1/R2 cases are missed; their union is nine distinct misses, all canonical. All source labels are retained. Source annotations are union masks and cannot isolate a missing component when other defect labels coexist. R1/R2 and common mask areas use the historical common256 definitions, not a new size cutoff.

Main results use exact Stage5C orientation-normalized D2 at512. Supporting D1 uses exact Stage5B orientation at256; canonical outputs are exact historical no-ops. Both historical banks remain4096×384, with unchanged frozen ResNet18 layer2/layer3 features, crop/letterbox, Euclidean distance and recipe-specific thresholds. No bank fitting, calibration, alternative detection decisions or detector changes occurred.

Frozen re-extraction reproduces saved model maps and scores within the declared1e-5 tolerance. Canonical saved maps and scores exactly equal historical D1/D2. Native maxima retain padding patches. Patch ranks use stable row-major tie ordering. Original source union masks are rotated within the crop only for projection into an oriented query grid; source GT stays untouched. Any positive in an8×8 model cell defines overlap. This footprint is not the backbone receptive field. Common256 interpolation can alter maxima; native scores and common map maxima are separate fields.

## Remaining failures

| Image ID | Labels / band | D2 image / threshold | D2 GT / threshold | First GT rank | Diagnostic flags |
|---|---|---:|---:|---:|---|
|156203b86fd0a31b58234f24|melt / R1|0.9361|0.9361|1|F5|
|19c7eaaf7a7c2b71d5da1dc8|melt / R2|0.9785|0.9785|1|F4|
|733208e2c25e1af5454d93f2|missing / R2|0.9174|0.8805|12|F5|
|86317f47cc684a4a33717793|missing / R1|0.9314|0.9314|1|F5|
|989748a316d5781c15aa24a6|melt / R1|0.9715|0.9715|1|F4|
|a7e7261362d3ab9b5fa975d0|missing / R1|0.9326|0.9304|2|F5|
|d086b78f683af0d19bb68594|missing / R1|0.9937|0.9937|1|F2,F4|
|e68d2653f5376170791a8674|missing / R2|0.9751|0.9751|1|F4|
|ead24842cb7981c9674e9d4e|missing / R3|0.9677|0.9677|1|F4|

The [case table](../../artifacts/stage6a/case_diagnosis.csv) retains all36 cases and both recipes. [Per-recipe diagnostics](../../artifacts/stage6a/per_recipe_diagnostics.csv) include all requested score decomposition, common localization counts, source coordinates, GT patch counts and margins. Seven of nine misses have native rank1 GT peaks; the others have ranks2 and12. No miss needs rank20+ to reach GT. Image margins are0.63–8.26% below threshold. Canonical missing-miss median GT/threshold is0.9495 versus1.1791 for canonical missing hits; their median common AP is0.1823 versus0.5799.

## Aggregation and competing regions

[Aggregation diagnostics](../../artifacts/stage6a/aggregation_diagnostics.csv) retain top1, top3/5/10 means,90th/95th/99th percentiles, top1%-mean, GT-only max and outside-GT max. [Patch ranks](../../artifacts/stage6a/patch_rank_diagnostics.csv) include first-GT rank and top5/10/20 overlap fractions.

An outside-GT maximum cannot cause a miss under the current max rule: raising an outside patch only raises the image score. It can mislead localization or produce normal false positives. The F3 descriptive flag therefore applies to competing response on hits only; three cohort hits meet it. It must not be interpreted as explaining the nine misses.

For the same threshold, any top-k mean is at most the maximum, so replacing max with a mean cannot rescue these false negatives. Separately calibrated aggregation could change discrimination and FPR, but Stage6A does not measure a new normal calibration distribution or demonstrate that isolated normal peaks differ from these defect peaks. Selecting top-k merely because margins are narrow would exceed the evidence.

## Feature distances and D1/D2 context

[Feature distances](../../artifacts/stage6a/feature_distance.csv) save every GT-overlap query's nearest distance, median of its top5 distances, and nearest frozen bank index. Every query searches the entire historical4096-reference bank. Group summaries below first take the median across GT queries per image, then the median across images; patches are not independent observations.

| D2 group | Images | Median nearest distance | Median query top5 distance | Median first-GT rank |
|---|---:|---:|---:|---:|
|Canonical missing miss|6|1.7637|1.9009|1|
|Canonical missing hit|6|2.0193|2.1483|1|
|Small miss|8|1.7921|1.9301|1|
|Small hit|21|2.0561|2.1647|1|
|Reversed rescue|1|1.9194|2.0303|1|

Missed GT patches are closer to the frozen normal bank on these summaries. Canonical missing controls overlap: per-image nearest medians span1.5123–1.8473 for misses and1.4736–2.2785 for hits. Small-case medians separate within this selected cohort: misses1.5123–1.8473, hits1.8631–2.6934. This supports weaker feature-distance separation on small misses, but does not identify whether a stronger backbone, more resolution, or a different operating policy would improve the tradeoff. No component-specific normal-neighbor semantics are inferred.

D1/D2 within-recipe ratios, distances, common AP and ranks are saved for every target. All six canonical missing misses improve D2 common AP relative to D1; D2 often moves GT toward rank1. Only one distinct miss meets the declared large joint GT-ratio/AP improvement flag F2. This supports sensitivity to recipe choice, without isolating resolution: banks, candidate populations, fractions and independently calibrated thresholds differ. Sparse and mixed labels further limit causal claims.

The reversed rescue remains a useful contrast: normalized D1 image/threshold0.9712 becomes D2 1.0156, with a rank1 native GT patch and D2 common AP0.3141. The native GT maximum exceeds image threshold, while the interpolated common GT maximum is slightly below that image threshold; they are different grids and image threshold is not a pixel decision rule. The rescue is marginal and does not establish robust separation.

## Failure flags and decision gate

Operational flags were specified before extracting new diagnostics. F1 requires both recipes' GT/image-threshold ratios below0.8 on a D2 miss. F2 requires a small case with D2-D1 GT ratio improvement at least0.2 and common AP improvement at least0.1. F3 is competing-response context on detected cases. F4 requires a missed image ratio at least0.95 and GT ratio at least0.9. Otherwise F5 preserves ambiguity. On the nine misses: F1=0, F2=1, F3=0, F4=5, F5=4; one image has both F2 and F4. Flags are overlapping descriptions, not validated causal diagnoses. F5 on hit controls denotes no applicable flag, not a failed detection.

The exact0.8/0.95 conventions do not establish natural boundaries. Relaxing “near threshold” to0.90 would include all nine misses; that is an interpretive sensitivity observation, not tuning or a changed detection decision. Absent F1 flags does not prove the representation is adequate. It means the strict low-score pattern in the reviewed proposal is not demonstrated. Strong ranks and limited margins coexist with lower distances and poor localization on some misses.

**Decision: Branch D. Recommend freezing the existing D2+orientation candidate with documented limitations; do not force a Stage6B experiment.** No single proposed intervention is clearly justified by this evidence. Representation weakness is plausible but not uniquely supported; resolution causality is unresolved; max misranking is not the common miss mechanism; calibrated top-k improvement is untested. The remaining issue is limited separation at the chosen operating point, with unresolved causes. This is sufficient understanding to stop the requested diagnostic stage while retaining honest uncertainty.

## Figures and artifact reader

Ten exported figures cover all eight requested figure types; contact sheets have two pages each so no miss is omitted. Maps use shared0–2 scales after division by each recipe's own pixel threshold. GT is outlined in cyan. Ratio comparisons provide within-recipe context, not a shared raw-score calibration.

- [Failure flags](../../artifacts/stage6a/figures/failure_category_summary.png)
- [GT versus outside-GT](../../artifacts/stage6a/figures/gt_vs_outside_gt.png)
- [Patch ranks](../../artifacts/stage6a/figures/patch_rank_distribution.png)
- [Reference distance](../../artifacts/stage6a/figures/nearest_reference_distance.png)
- [D1/D2 evidence](../../artifacts/stage6a/figures/d1_vs_d2_evidence.png)
- Canonical missing-miss sheets: [page1](../../artifacts/stage6a/figures/canonical_missing_miss_contact_sheet_1.png), [page2](../../artifacts/stage6a/figures/canonical_missing_miss_contact_sheet_2.png)
- Small-miss sheets: [page1](../../artifacts/stage6a/figures/small_defect_miss_contact_sheet_1.png), [page2](../../artifacts/stage6a/figures/small_defect_miss_contact_sheet_2.png)
- [Marginal rescue](../../artifacts/stage6a/figures/marginal_rescue_comparison.png)

The [notebook](../../notebooks/pcb2_stage6a_diagnosis.ipynb) reads saved evidence only. The [figure metadata](../../artifacts/stage6a/figure_metadata.json) retains source tables, case IDs and hashes.

## Verification and reproducibility

The Stage5C no-write computational audit passed before Stage6A extraction:195 no-op maps/scores/flags,200 inverse maps, all1101 pose labels and five independent float64 reversed checks. The new [computational review](../../artifacts/stage6a/independent_review.json) independently reconstructs oriented GT footprints, rankings, aggregation summaries, common AP/counts and bounded systematic SciPy float64 top5 distances, including each native peak. It verifies all839 prior tracked files through exact preserved navigation snapshots. It is a separate computational implementation by the same author, not an external human/agent review.

All142 tests pass, including meaningful odd-padding reverse-mask, stable-rank and max-miss category controls. Extraction is frozen and overwrite-guarded; no historical evaluation, fitting, bank selection or calibration was rerun. Ignored cache arrays under`data/cache/stage6a/` retain native scores, GT grids, all top5 distances/indices and systematic query vectors; public tables and receipts bind their hashes. Git content alone does not include raw data, weights or these local arrays.

A first audit failed because basename-only navigation snapshots collided for root and journey README files. The original files were unchanged. The [repair record](../../artifacts/stage6a/audit_repair.json) preserves original code, pins corrected code and documents the restoration of full relative paths. No numerical extraction rerun occurred. The frozen original protocol remains intact; its original code hashes resolve to preserved snapshots through the repair record. The first figure set is preserved under`figure_revision_v1/`: visual inspection corrected title overlap and missing-hit outcome markers, with no data changes.

To inspect completed evidence, open the notebook or CSVs. To reproduce on a separate restored baseline, use the preserved protocol/input identities and supplied proposal; the current commands refuse to reuse an existing namespace. Do not refreeze over completed work. The exact Stage5C detector recipe remains authoritative in its protocol, historical D2 calibration/bank identity and unchanged shared orientation code.

## Stage 6B, final model decision and UI boundary

Stage6B was not executed. A formal Modelv1.0 freeze is pending; this chapter does not claim the whole Stage6 definition of done or manufacture a final-model receipt. The recommended candidate remains D2+orientation, and the model's91/100 recall,4/100 normal flags and localization evidence remain the historical Stage5C baseline. Stage6A's selected case cohort does not estimate a new full-population metric.

Before a formal freeze, identify and bind the final recipe, bank, weights, thresholds, source identities, runtime boundary and limitations in the model receipt. The current recommendation defers further model research, with missed small/canonical defects, marginal rescue, broad sparse maps, limited pose coverage, union-mask ambiguity and exposed PCB2 development data stated explicitly. Future research belongs to a new version. No UI or productization changes were made.

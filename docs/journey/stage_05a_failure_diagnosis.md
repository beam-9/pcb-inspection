# Stage 5A — Why does the detector still fail?

Completed October 3, 2026. This is **post-confirmation PCB2 development diagnosis**. Stage 4 was committed and pushed as [2ec21c4](https://github.com/beam-9/pcb-inspection/commit/2ec21c4686c7dad7d60c177cb35fed2cd62d9280). Its detector, banks, thresholds, predictions, metrics and evidence remain unchanged. D1 remains the historical primary and D2 secondary. No Stage 5B intervention was executed.

The strongest observed candidate for a first controlled intervention is **canonical orientation normalization**. Five reversed boards contribute about 29–30% of false-positive pixels in both recipes. This is an association with broad maps, not proof of causation or an explanation for all remaining errors. Missing-component misses occur on canonical boards and generally retrieve local normal references. The proposed distant-match explanation is not supported as the distinctive mechanism of these misses.

## Where Stage 4 left us

The normal-reference procedure detected 80/100 anomalies with 5/100 normal flags for D1, and 91/100 with 4/100 for D2. Median per-anomaly pixel AP was 0.325/0.496, but pooled AP was only 0.153/0.277 and fixed-threshold IoU 0.047/0.070. Image discrimination and tight defect localization are different tasks. High any-overlap counts do not establish precise maps.

Stage 5A uses saved maps and outputs, and re-extracts the same frozen features solely to trace neighbors. It neither rotates inputs for detector inference nor fits or evaluates a modified detector. The [design review](../development/stage5a_plan_review.md) records the supplied handoff's useful hypotheses and limits; the [diagnostic protocol](../../artifacts/stage5a/diagnostic_protocol.json) snapshots history and diagnostic definitions.

## Does pose matter?

### Method and label validation

An image-only classifier counts approximately neutral, bright, elongated pin ridges in exterior bands around the saved blue-board box. At analysis width 512 it examines the central 40% of board width, with bands extending 45% of board height above and below. At least two elongated pin components and a threefold cue dominance are required. Pin-top is `canonical`, pin-bottom `reversed_180`, and an inconclusive cue is `uncertain`. No angle precision is invented. Scores, maps, detection outcomes and GT masks are not classifier inputs.

All 1,101 images were labeled: 720 fitting normals, 181 calibration normals, 100 evaluation normals and 100 anomalies. Labels were finalized before outcome joins. Two agents visually checked grouped image-only sheets; the labeling agent reviewed 32 systematic canonical examples plus every reversed/uncertain example, 42 total. The labels use no manual override or method refinement. Prior Stage 4 visual knowledge is acknowledged: this is outcome-independent computation, not a retrospectively double-blind study.

All 1,001 normals are classified canonical. Among anomalies, 90 are canonical, five reversed and five uncertain. Every reversed example visibly has inverted layout/pins at the bottom. All five uncertain examples visually retain canonical layout but have damaged, missing or folded connector cues. **Uncertain is a cue-failure group, not a verified unusual-pose group**, and is not pooled with reversed cases. Representative heatmaps use deterministic full-ID selection by pose and normal/anomaly status; a reversed normal panel is explicitly unavailable.

See [labels](../../artifacts/stage5a/pose/pose_labels.csv), [labeling criteria](../../artifacts/stage5a/pose/pose_labeling_notes.md), [final label receipt](../../artifacts/stage5a/pose/labels_final.json), [contact sheet](../../artifacts/stage5a/pose/pose_contact_sheet.png) and [representative heatmaps](../../artifacts/stage5a/pose/pose_representative_heatmaps.png).

### Results: reversed boards have broad responses

Use anomaly-only comparisons: pooling 100 canonical normals with 90 canonical anomalies would exaggerate some differences. The [stratified table](../../artifacts/stage5a/pose/pose_binary_stratified_summary.csv) and [anomaly-only FP plot](../../artifacts/stage5a/pose/pose_fp_pixels_anomalies.png) retain matched denominators.

| Quantity | D1 canonical anomalies (90) | D1 reversed (5) | D2 canonical anomalies (90) | D2 reversed (5) |
| --- | ---: | ---: | ---: | ---: |
| Median false-positive pixels | 2,639.5 | 29,180 | 1,577.5 | 19,367 |
| Median anomaly pixel AP | 0.333 | 0.0757 | 0.515 | 0.274 |
| Median crop fraction above threshold | 0.0699 | 0.7465 | 0.0436 | 0.5020 |
| Detected | 70/90 | 5/5 | 81/90 | 5/5 |

The five reversed boards contribute 146,977 of 510,336 D1 FP pixels (28.80%) and 97,150 of 325,593 D2 FP pixels (29.84%). They are the five largest FP contributors in both recipes. Their anomaly-only median burden is 11.1×/12.3× canonical anomalies, and the same broad-map direction appears at both resolutions. Yet all five were detected: pose does **not** explain image-level misses here. There are no reversed normals, so reversed-normal FPR or normal-score effects cannot be estimated. Five images, overlapping defect types and unknown physical identities cannot establish cause, population prevalence or statistical equivalence.

## Why are missing components difficult?

### Frozen nearest-neighbor tracing

All 19 images carrying the source `missing` label were traced at both resolutions. Six were missed by both, one missed by D1 and detected by D2, and twelve detected by both; there are no D1-only detections. All seven D1 missing-label misses are canonical. Four reversed and three uncertain cases are among the twelve both-detected images.

The source GT union mask is mapped through each saved crop/letterbox with nearest-neighbor resizing. Every feature-grid cell whose 8×8 input footprint overlaps the mask is traced, plus an eight-connected one-cell context ring. These footprints are **not** the full ResNet receptive fields. Two missing-labeled images have multi-type union masks, so traced regions cannot always be attributed uniquely to a missing component.

There are 3,698 query cells and 18,490 query/reference pairs. Top five neighbors come from every vector in the unchanged 4,096-reference, 384-dimensional bank with unrestricted Euclidean matching. Exact ties use ascending bank index. Source, feature and normalized crop-content coordinates and padding indicators are retained. Displacement is Euclidean normalized crop-coordinate distance divided by √2. Diagnostic radii 0.05/0.10/0.20 were fixed before outcome association and are not optimized. Coordinates are unregistered; spatial distance is not anatomical correspondence.

### Results: misses do not retrieve more distant references

The table below gives image-weighted medians of defect-overlap/top-five summaries, excluding context-ring queries from these values.

| Canonical paired group | Images | D1 displacement | D1 fraction beyond 0.10 | D2 displacement | D2 fraction beyond 0.10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Both missed | 6 | 0.0090 | 0.000 | 0.0253 | 0.092 |
| D2 rescue | 1 | 0.0026 | 0.000 | 0.0175 | 0.105 |
| Both detected | 5 | 0.0228 | 0.003 | 0.0311 | 0.260 |

Misses retrieve **more local** references in this sample. Their median embedding distances are also lower: 1.472 vs 1.819 for D1 and 1.903 vs 2.268 for D2 when comparing canonical both-missed with both-detected groups. This weakens distant matching as the distinctive explanation for canonical misses; it does not prove that local references encode the correct expected component. The one missing-label D2 rescue cannot establish a general resolution mechanism.

Every case has a trace sheet at each resolution. The displayed query is the overlap cell closest to the source union-mask centroid, with feature-ID tie breaks, rather than a visually favorable peak. For bounded semantic inspection, the lowest full image ID in each observed paired group was reviewed at both sizes, all five displayed neighbors: 30 pair views. Full-source context and enlarged center views were used. Five were labeled component, three clear empty substrate, and 22 uncertain. Clear substrate centers occurred in the selected both-detected 512 case, not the selected miss/rescue. These are center-view labels, not whole-receptive-field or prevalence claims. Unreviewed references remain explicitly uncertain.

See [tracing findings](../../artifacts/stage5a/missing_component/findings.md), [all pairs](../../artifacts/stage5a/missing_component/nn_trace.csv), [paired cases](../../artifacts/stage5a/missing_component/missing_cases.csv), [context review](../../artifacts/stage5a/missing_component/selected_reference_context_review.csv) and [displacement plot](../../artifacts/stage5a/missing_component/missing_hit_vs_miss.png).

## Why are maps broad?

A 4×4 grid partitions normalized crop content, excluding letterbox padding. The crop includes conservative surrounding background, so grid cells are not automatically anatomical board regions. Native-content score/spread metrics and source-inverted common-256 count metrics use separate explicit denominators. Common-256 grid FP counts sum to the full frozen totals; FP pixels outside the crop are zero for both recipes. Mean raw score, threshold-exceedance frequency and FP frequency are aggregated separately for normals/anomalies, each pose, and missing/nonmissing anomalies. Colors use fixed numeric scales within each recipe and column, not per-panel contrast stretching.

Reversed boards light up across most crop content. Canonical anomalies also have FP responses, especially central/right crop cells, so orientation will not explain the entire map problem. All-anomaly highest FP frequencies are D1 row1/column2 0.1787 and row2/column2 0.1763; D2 row2/column2 0.1452 and row1/column2 0.1291 (zero-based). Those are crop-relative observations without pose registration, not diagnoses of a named physical connector or component.

See [regional summary](../../artifacts/stage5a/broad_maps/summary.md), [grid table](../../artifacts/stage5a/broad_maps/grid_summary.csv), [D1 aggregate maps](../../artifacts/stage5a/broad_maps/D1_aggregate_maps.png), [D2 maps](../../artifacts/stage5a/broad_maps/D2_aggregate_maps.png) and [per-image spread](../../artifacts/stage5a/broad_maps/map_spread.csv).

## How do small defects fail?

All 29 anomalies in fixed PCB1 reference area bands R1/R2 are retained, 58 recipe-specific rows. Operational categories compare the frozen common map's GT maximum with its pixel threshold and outside-GT maximum, and record image flags separately. They are overlapping descriptions: a smoothed map maximum is not identical to the frozen native patch-maximum image score.

D1 has three low-GT-map-response cases, 23 with higher response outside GT, and eleven with pixel evidence but no image flag. D2 has zero, eleven and eight respectively. Seven small defects missed by D1 are detected by D2. Twenty cases meet the declared resolution-contrast description (a D2 rescue or pixel-AP gain at least 0.10); this does not isolate resolution causally because D1/D2 have different normal-calibrated thresholds and candidate populations.

These patterns distinguish weak local response, competing responses and frozen aggregation/threshold effects, without claiming to prove a representation failure. Mixed/unclear cases remain possible. See [all case descriptions](../../artifacts/stage5a/small_defects/failure_decomposition.csv) and [paired figure](../../artifacts/stage5a/small_defects/small_case_decomposition.png).

## Combined confounders

The [200-row combined dataset](../../artifacts/stage5a/combined/per_image_diagnostics.csv) preserves one row per evaluation image, null anomaly/NN fields where not applicable, and separate D1/D2 quantities.

- **Pose × missing:** all seven D1 missing-label misses are canonical. Reversed missing-label cases are detected but have broad maps. This prevents attributing the missing misses to reversal.
- **Pose × spread:** reversed anomalies have much greater spread in both recipes, but no reversed-normal control exists. Uncertain cue failures must stay separate.
- **Size × missing:** among six R1/R2 missing-labeled images, each recipe detects only one; among 23 nonmissing images in those same coarse bands, D1 detects 14 and D2 20. Small regions and missing labels overlap, but coarse size alone does not explain away the observed weakness. Counts are tiny, exact area/context/type remain confounded, and unions complicate attribution. Larger R4 missing cases include reversed images, so their good detection is not evidence of precise missing-component localization.

The [pose × missing](../../artifacts/stage5a/combined/pose_x_missing.csv), [pose × spread](../../artifacts/stage5a/combined/pose_x_map_spread.csv) and [size × missing](../../artifacts/stage5a/combined/size_x_missing.csv) tables retain empty groups rather than inventing estimates.

## Decision gate: one future intervention

Recommend **canonical orientation normalization before the existing D1 feature extraction** as the primary Stage 5B experiment. It targets a clearly observed, repeated broad-map concentration. It should compare the current D1 procedure with D1 plus orientation normalization, keeping feature layers, bank budget/selection, scoring and calibration policy stable, with a predeclared image-only orientation rule and uncertain-case handling. Preserve the historical primary; any new result is PCB2 development evidence. Check both matched canonical/reversed localization and overall recall/FPR/runtime. No simultaneous backbone, memory, crop or spatial-restriction change is justified.

This proposal does not promise to solve the six canonical both-missed missing cases, and should not erase that separate question. Spatial constraints are not the first recommendation because missed cases already match locally; one missing-label D2 rescue is insufficient to prioritize a new high-resolution experiment. A controlled orientation experiment is needed to determine whether the observed association is actionable. It has **not been implemented or evaluated**.

## Validation and unresolved issues

The independent diagnostic review verified 1,514 Stage 4 source/artifact/local-cache identities unchanged, all 200 diagnostic IDs/flags/scores/pixel APs, independent saved-map counts for both recipes, all 18,490 reference identities and 36,980 query/reference coordinate conversions, and crop-grid count reconciliation. Frozen feature re-extraction reproduced all 38 missing-case native maps exactly. There are 190 fixed-subset NumPy float64 distance checks, maximum error 1.55e-6; this is not a second independent extraction of every trace. See [review receipt](../../artifacts/stage5a/independent_review.json).

All 121 tests pass. Figure/source identity checks and an executed artifact-only notebook accompany the final diagnostic receipt. Two artifact-generation failures (a nullable numeric dtype and a chart-column typo) were corrected; failed output directories and failure notes remain under Stage 5A. These changed neither inference nor Stage 4.

Remaining uncertainties include pin-cue damage, no reversed normals, only five reversed anomalies, multi-label union GT, physical-board identity, unregistered coordinates, receptive-field context and local-reference semantic ambiguity. PCB2 is exposed; subsequent tuning cannot be described as another fresh confirmation. The original timing-clock and historical transport limitations remain in Stage 4. No detector logic, threshold, memory, registration or UI changed in this stage.

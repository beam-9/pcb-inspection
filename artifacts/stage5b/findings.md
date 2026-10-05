# Stage 5B — Orientation tightens reversed maps but loses one detection

Completed and independently audited October 4, 2026 (America/Vancouver). **Post-confirmation PCB2 development evidence.** Historical Stage 4 D1 remains the primary result. Orientation normalization is **not adopted unconditionally**: the unchanged image threshold detects only four of the five previously detected reversed anomalies.

## Why this experiment

The supplied handoff was reviewed against Stage 5A in [the plan review](../../docs/development/stage5b_plan_review.md). Five reversed anomalies generated 146,977 common-256 false-positive pixels, 28.80% of D1's 510,336 total. All five were detected already. Canonical missing-label misses retrieve local normal references, so this experiment tests pose mismatch as a contributor to broad maps; it does not test spatially restricted matching.

## Frozen intervention and controls

Reuse the exact Stage 4 D1 4,096×384 bank, ResNet18 layer2/layer3 features and local aggregation, 256 input, Euclidean distance, maximum-patch image score, crop, letterbox and interpolation. No fitting, augmentation, recalibration or tuning occurred. Image threshold is **1.6270664930343628**, pixel threshold **1.348502516746521**, strict `>`.

The unchanged Stage 5A pin classifier receives full original source RGB and original board box. Canonical and uncertain crops are unchanged; only the five `reversed_180` crops receive exact vertical/horizontal array reversal before resizing and letterboxing. The map is unpadded, bilinearly resized to crop dimensions, inverse-reversed, pasted at the original crop location and finally resized to common 256. Original GT masks remain untouched. Odd-padding/asymmetric-crop tests guard this order. See [protocol](orientation_protocol.json), [freeze](freeze_receipt.json) and [geometry figure](figures/orientation_geometry.png).

The freeze uses Stage 4 commit `2ec21c4686c7dad7d60c177cb35fed2cd62d9280` and the actual uncommitted Stage 5A receipt identity rather than inventing a Stage 5A commit. Every one of the 1,101 original pose labels reproduced. All 195 non-reversed evaluation images were rerun through D1: tensors, scores, flags, native/common arrays, applicable AP and FP counts match **exactly**, with no numerical tolerance. The 100 normal flags remain 5/100. These are implementation controls, not a reversed-normal robustness test.

## All five paired cases

Common-256 maps cover the original source image. Pixel AP/FP/intersection counts below use that space; native crop spread excludes padding and has a different denominator.

| Image ID | Source label | FP pixels: historical → normalized | Pixel AP: historical → normalized | Image score: historical → normalized | Detection | GT intersection: historical → normalized |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| `2bea857039ef9c03907fb299` | missing | 31,238 → 5,877 | 0.4918 → 0.8484 | 2.928387 → 2.529640 | Retained | 1152 → 1152 |
| `735d89d870bbb25b3bc3dfce` | melt | 29,697 → 2,645 | 0.0048 → 0.2144 | 2.861748 → 1.650754 | Retained | 168 → 165 |
| `76964f3ab9f7c03b08de6900` | missing | 28,422 → 5,980 | 0.4121 → 0.8314 | 2.827421 → 2.804057 | Retained | 2012 → 2012 |
| `9bd08200d5d939f4a498aae7` | missing | 28,440 → 2,544 | 0.0757 → 0.8350 | 2.865720 → 2.619817 | Retained | 1104 → 1104 |
| `bfebbd19caf4dad38fd66eab` | missing | 29,180 → 1,111 | 0.0017 → 0.0258 | 2.725965 → 1.580128 | Lost | 50 → 31 |

All five FP counts decline and all five pixel APs improve. Total reversed FP pixels fall **146,977 → 18,157 (87.65%)**; median **29,180 → 2,645**. Median reversed AP rises **0.0757 → 0.8314**. Median native crop fraction above the frozen pixel threshold falls **0.7465 → 0.0927**. The positive bounding-box fraction and eight-connected component counts remain available separately in [per-image results](results/per_image_results.csv); a crop-wide bounding box can persist even when exceedances become sparse.

The detection guardrail fails: **5/5 → 4/5**. Missing-labeled image `bfebbd19caf4dad38fd66eab` falls from image score **2.725965 → 1.580128**, below the unchanged 1.627066 threshold. Its GT intersection declines **50 → 31** common pixels while outside-GT FP falls **29,180 → 1,111**. Its AP improves only **0.0017 → 0.0258**, remaining poor. Removing broad mismatch has not preserved enough image-level anomaly signal in this case. The melt case retains detection narrowly at **1.650754**; no statistical robustness margin is inferred.

![All five paired source-space maps](figures/reversed_before_after.png)

![Removed and new threshold exceedances](figures/reversed_map_differences.png)

All five cases are shown on a shared clipped score/pixel-threshold scale (0–3), not probability. Signed differences use −3–3. The [difference statistics](results/map_difference_statistics.csv) separate removed response inside versus outside GT and newly added exceedances. The [fixed 4×4 grid](regional/reversed_grid_comparison.csv) preserves both native-content and common-256 original-crop coordinate views; crop cells are not anatomical segmentation. The paired FP totals reconcile with common-256 grids.

## Full 200-image impact

| Quantity | Historical Stage 4 D1 | Stage 5B orientation D1 |
| --- | ---: | ---: |
| TP / FN | 80 / 20 | 79 / 21 |
| FP / TN | 5 / 95 | 5 / 95 |
| Image AP | 0.9604 | 0.9587 |
| AUROC | 0.9499 | 0.9484 |
| Median anomaly pixel AP | 0.3245 | 0.3329 |
| Pooled pixel AP, including normals | 0.1534 | 0.3142 |
| Pixel IoU, including normals | 0.04744 | 0.06234 |
| Peak inside /100 | 44 | 45 |
| Any overlap /100 | 97 | 97 |
| All-image FP pixels | 510,336 | 381,516 |
| Missing-label detection /19 | 12 | 11 |
| Fixed small R1/R2 detection /29 | 15 | 14 |

All seven historical canonical missing-label misses remain unchanged. The new miss is one of four reversed missing-labeled examples; total missing recall was not assumed invariant. Small-defect detection loses the same image, rather than improving through resolution. Canonical map weaknesses remain untouched by this experiment. Pooled AP improves alongside a much larger reduction in thresholded outside-GT burden, despite a slight intersection decline. AP measures ranking and does not follow directly from thresholded FP counts; this does not imply every defect is better detected.

## Engineering cost and timing limits

Measured median end-to-end inference is **0.3636 s**, p95 **0.4049 s**. Reversed median is **0.3664 s**, no-op median **0.3634 s**. Pose classification median is **45.44 ms**; actual crop-array rotation median over five reversed cases is **3.958 ms**. Process peak RSS is **1.417 GiB**, below the inherited 8 GiB cap.

The per-image timer includes source decoding, geometry, pose and tensor construction, frozen `score_feature` (which includes its historical common inverse), and additional source/common orientation inverses. It excludes GT metrics, artifact saving, the no-op tensor check, model loading and the separate 1,101-image label audit; first image is retained. Timers are nested and must not be added. The runtime figure summarizes all 200 images, so its rotation median/p95 are zero because only five images rotate; the 3.958 ms rotation median above uses the five reversed cases only. Retaining frozen scoring introduces redundant inverse work in this research implementation; it is disclosed rather than attributed entirely to pose overhead. Historical **0.2918 s** includes preprocessing and historical inverse mapping, so it is contextual, not a matched isolated-model comparison. [Per-image timers](results/runtime.csv) preserve boundaries and [runtime figure](figures/runtime.png) shows median/p95.

## Interpretation and decision

**Mixed support.** Exact controls and the across-case reduction support orientation mismatch as an actionable contributor to broad responses on these five observed reversed boards. The paired localization benefit is large, but the predeclared 5/5 detection guardrail fails. Keep the historical D1 pipeline as the primary; retain this orientation implementation as an experimental candidate, not an unconditional replacement. Do not lower thresholds, augment the bank, modify uncertain handling or tune this completed experiment.

A separate next study should ask: **How can orientation normalization preserve true defect signal while reducing broad pose-induced response?** Investigate the newly missed small missing-component case and the narrow-margin melt case alongside unresolved canonical missing/small-defect mechanisms before selecting a Stage 5C intervention. A representation/resolution or operating-policy proposal needs its own evidence and freeze; spatial constraints remain unsupported as the automatic next step. No Stage 5C experiment or UI was started.

## Verification and preserved failure

The first attempt stopped on the first canonical image because blank normal AP cells made the historical CSV column a string. Tensor, score, flags, native/common maps and FP counts were already identical; converting AP to a number reproduced its exact float value. The repair is reader typing, not detector logic or tolerance. No reversed result had been examined. [Failed attempt notes](../stage5b_failed_v1/failure_notes.json), original frozen runner/tests and partial maps are preserved in separate failed namespaces. The final freeze followed the regression test.

The independent review audits original masks and raw saved maps, all200 inverse mappings, all195 controls, all1101 RGB labels, paired/grid/difference counts and full metrics. It also independently reconstructs the five reversed inputs and scores their frozen features using float64 SciPy distances; this is bounded independent re-extraction, not a second full-population run or model fitting. [The authoritative review](independent_review.json) passed: maximum independently reconstructed native-map error was 1.43×10⁻⁶ and image-score error 9.25×10⁻⁷ against float64 distances (predeclared 1e-5 limit). All 200 saved inverse maps and 195 no-op maps match exactly; the independent float64 tolerance applies only to the separately implemented numerical distance audit. All 130 tests pass. The [completion manifest](complete.json) binds final evidence, documentation, figures, tests and the executed notebook.

Only five reversed anomalies and no reversed normals exist. PCB2 is exposed development data; overlapping source labels, union GT masks and unknown physical-board identities limit causation and generalization. This result neither resolves all canonical failures nor establishes factory readiness. Stage 4 timing-clock and historical archive-transport caveats remain. Stage4 and Stage5A code, banks, thresholds and measured outputs are preserved; evolving navigation is saved before changes under `history_navigation/` so earlier receipt identities remain verifiable without rewriting historical receipts.

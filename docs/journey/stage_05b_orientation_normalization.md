# Stage 5B — Can canonical orientation reduce broad maps?

Completed October 4, 2026 (America/Vancouver). **Post-confirmation PCB2 development evidence.** Stage 4 D1 remains the historical primary.

**Answer: yes for the observed broad-map burden, with a detection trade-off.** Exact 180° crop normalization reduced false-positive pixels on all five reversed anomalies, but one previously detected small missing-component case became a miss. Orientation normalization is retained as an experimental candidate and is not adopted unconditionally.

## Why the experiment was chosen

Stage 5A found five reversed anomalies responsible for 28.80% of D1 false-positive pixels, with an anomaly-only median burden 11.1× canonical anomalies. All five were already detected. Canonical missing-label misses retrieved local normal references, weakening distant matching as the first intervention. The [proposal review](../development/stage5b_plan_review.md) evaluates the supplied handoff and resolves crop, pose, coordinate, denominator and timing ambiguities.

## Hypothesis and exactly one change

Query orientation may mismatch a normal memory consisting entirely of canonical boards. The unchanged Stage 5A rule consumes full original RGB and original board boxes. Actions were frozen before inference: `canonical → no-op`, `reversed_180 → exact 180° crop reversal`, `uncertain → no-op`. Uncertain cues are not verified reversed poses.

Keep the original crop/margins, 256 letterbox, ResNet18 layer2/layer3 features, aggregation, Euclidean reference scoring, maximum-patch image score, exact 4,096×384 bank and thresholds. Image threshold is 1.6270664930343628; pixel threshold 1.348502516746521, strict `>`. No fitting, bank augmentation, recalibration, D2 arm or tuning occurred.

Rotation happens after crop determination and before resize/letterbox. The native map is unpadded, bilinearly resized to crop size, inverse-reversed and pasted at the original crop location before common-256 resizing. GT stays in original coordinates. The [frozen protocol](../../artifacts/stage5b/orientation_protocol.json) binds the recipe and actual uncommitted Stage 5A identity; the [freeze receipt](../../artifacts/stage5b/freeze_receipt.json) predates final inference.

## Matched results on every reversed image

| Image ID | FP pixels: historical → orientation | Pixel AP: historical → orientation | Detection |
| --- | ---: | ---: | --- |
| `2bea857039ef9c03907fb299` | 31,238 → 5,877 | 0.4918 → 0.8484 | retained |
| `735d89d870bbb25b3bc3dfce` | 29,697 → 2,645 | 0.0048 → 0.2144 | retained narrowly |
| `76964f3ab9f7c03b08de6900` | 28,422 → 5,980 | 0.4121 → 0.8314 | retained |
| `9bd08200d5d939f4a498aae7` | 28,440 → 2,544 | 0.0757 → 0.8350 | retained |
| `bfebbd19caf4dad38fd66eab` | 29,180 → 1,111 | 0.0017 → 0.0258 | **lost** |

Common-256 FP total falls **146,977 → 18,157 (87.65%)**, median **29,180 → 2,645**. Reversed median AP rises **0.0757 → 0.8314**. Native unpadded crop fraction above threshold falls **0.7465 → 0.0927**; its denominator differs from common-source pixel counts. All five FP counts decline and all five AP values improve, but AP remains poor on the newly missed case.

The predeclared detection guardrail fails: **5/5 → 4/5**. `bfebbd19caf4dad38fd66eab` falls from image score 2.725965 to 1.580128, below 1.627066. Its GT intersection falls 50 → 31 common pixels, while FP falls 29,180 → 1,111. The melt example retains detection at 1.650754, narrowly above threshold. Do not lower a threshold to make this completed experiment look successful.

![All five original-coordinate comparisons](../../artifacts/stage5b/figures/reversed_before_after.png)

See the [complete paired table](../../artifacts/stage5b/results/reversed_paired_results.csv), [geometry sheet](../../artifacts/stage5b/figures/orientation_geometry.png), [differences](../../artifacts/stage5b/results/map_difference_statistics.csv) and [native/common fixed crop grids](../../artifacts/stage5b/regional/reversed_grid_comparison.csv). Shared threshold-relative heatmaps are not probability. All cases are shown; grid cells are crop-relative, not anatomical segmentation.

## No-op validation and overall impact

Every one of the 1,101 original pose labels reproduced. Fresh inference on all 195 unrotated evaluation images reproduced tensors, scores, flags, native/common arrays, applicable AP and FP counts exactly. All 100 normal outputs remain unchanged. [Control table](../../artifacts/stage5b/results/no_op_invariance.csv).

| Quantity | Historical D1 | Orientation D1 |
| --- | ---: | ---: |
| Anomalies detected /100 | 80 | 79 |
| Normal flags /100 | 5 | 5 |
| Image AP / AUROC | 0.9604 / 0.9499 | 0.9587 / 0.9484 |
| Median anomaly pixel AP | 0.3245 | 0.3329 |
| Pooled pixel AP | 0.1534 | 0.3142 |
| IoU | 0.04744 | 0.06234 |
| Peak inside /100 | 44 | 45 |
| Any overlap /100 | 97 | 97 |
| All-image FP pixels | 510,336 | 381,516 |
| Missing-label detection /19 | 12 | 11 |
| Small R1/R2 detection /29 | 15 | 14 |

All seven historical canonical missing-label misses remain unchanged. The one new reversed missing-label miss accounts for both subgroup losses; resolution and canonical behavior were unchanged. Pooled ranking improves alongside thresholded burden reduction, but does not erase the detection trade-off.

## Engineering cost and validation

Median end-to-end inference is 0.3636 s, p95 0.4049 s; reversed/no-op medians are 0.3664/0.3634 s. Median pose classification is 45.44 ms; reversed-only exact array rotation is 3.958 ms. Process peak RSS is 1.417 GiB under the inherited 8 GiB cap.

These timers include decoding, geometry, pose, tensor construction, frozen scoring including its historical inverse, and extra source/common orientation inverses. They exclude metrics, saving, control-tensor recomputation, model load and separate population pose audit. Redundant inverse work is disclosed. Historical 0.2918 s is contextual, not isolated model time or a perfectly matched latency comparison. [Timers](../../artifacts/stage5b/results/runtime.csv) and [full findings](../../artifacts/stage5b/findings.md) retain details.

All **130 tests** pass. [Independent validation](../../artifacts/stage5b/independent_review.json) reproduced 1,101 labels; checked all 200 inverse maps, 195 exact controls, 160 native/common grid rows, all paired/difference arithmetic, full AP/AUROC/IoU/counts and runtime summaries. Five separately reconstructed reversed inputs were extracted with frozen features and independently scored against the bank using float64 SciPy distances: maximum native-map error 1.43e-6, score error 9.25e-7, both below the declared 1e-5 independent-numerics bound. This is not a second independent full-population extractor.

The first attempt stopped on a canonical image because blank normal AP cells made historical AP a string. All other controls and the numeric AP value were exact. The reader fix and regression test changed no scientific recipe or tolerance. The [failed attempt](../../artifacts/stage5b_failed_v1/failure_notes.json), original frozen code/tests and partial maps are retained; no reversed outcomes were examined before the new freeze.

## Decision and next question

**Mixed support:** orientation mismatch contributes actionable broad response on these five examples, but the detection guardrail blocks unconditional adoption. Historical D1 remains primary; keep the wrapper as a documented candidate rather than replacing it. No threshold tuning, post-result overrides or simultaneous detector changes are justified.

The next question is **how to preserve true defect signal while reducing pose-induced broad response**. Diagnose the newly missed tiny missing-component case and narrow-margin melt case alongside unresolved canonical missing/small failures before choosing a separately frozen Stage 5C representation, resolution or operating-policy experiment. Do not automatically pivot to spatial restriction. Stage 5C and UI were not started.

There are only five reversed anomalies, no reversed normals, overlapping labels, union GT masks and unknown physical-board identities. This cannot estimate reversed-normal FPR, factory robustness or fresh generalization. Canonical broad-map and small/missing mechanisms remain. Stage 4 timing-clock and transport caveats are retained. Historical model/evidence identities are unchanged; the three evolving navigation documents were preserved in Stage 5B `history_navigation/` before updates, keeping Stage 5A receipts truthful and verifiable. The [executed artifact-only notebook](../../notebooks/pcb2_stage5b_orientation.ipynb) and [completion receipt](../../artifacts/stage5b/complete.json) bind the final state.

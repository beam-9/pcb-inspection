# Stage4: useful PCB2 detection, mixed localization

Completed October 2, 2026 locally (October 3 in UTC). Both frozen evaluations and
independent reviews passed. D1 remains the predeclared primary; D2 remains secondary.
The primary meets every preregistered numerical project criterion, but sharply lower
pooled pixel AP and IoU prevent a claim that localization quality transferred intact.
This is fresh analytical category confirmation of a category-specific fitting and
calibration procedure, not zero-shot reuse of PCB1 memory or factory validation.

## What was frozen and why

PCB1 development established a sequence: direct256 feasibility detected 43/100
anomalies; geometry/resolution reached 61–70; representative selection reached
89–95. D1 was chosen before PCB2 outcomes for its lower normal burden and CPU cost.
Stage4 tests this procedure on another category rather than optimizing PCB2 scores.

Both recipes retain ResNet18 layer2/layer3 local features, the Stage3 aggregation,
384-dimensional Euclidean scoring, maximum patch image score, full candidate
projected approximate greedy selection of 4096 unique references, projection seed 43
and selection seed 42, and unchanged image/map calibration quantile semantics.
Gaussian 64 projection is selection-only. All fitting patches, including padding,
remain eligible. Geometry remains the inherited blue-component crop/margins and gray
aspect-preserving letterbox; no pose registration or new backbone was introduced.
D1 uses 256 and D2 uses 512. This is PatchCore-inspired, with the departures documented
in the [Stage3 method notes](../../../docs/development/stage3_method_notes.md).

The normal-only suitability stage decoded 901 training normals, split deterministically
into 720 fitting and 181 calibration; 100 official test normals were acquired/hashed but
not decoded or used for geometry optimization before final freeze. All 901 inherited
crops had zero fallbacks/source-boundary contacts. Two reviewers viewed 17 predetermined
extreme/systematic examples; board edges and pins were retained. No category-specific
geometry change was needed. The [geometry chapter](../../../docs/journey/stage_04a_pcb2_normal_adaptation.md)
records that normal-only decision. It could not guarantee unseen defect retention.

Both normal banks/thresholds passed independent review before the final freeze at
2026-10-03 01:01:20.600342 UTC. Logical unseal was 01:01:58.729924. The primary finished
01:04:54.839360, secondary 01:10:56.998181, each exactly once without retuning. See the
[exposure ledger](../../../docs/development/stage4_exposure_ledger.md) for identities.

## Primary criteria and reviewed results

The practical criterion requires all four point estimates plus resource/integrity
gates. It is not a statistical equivalence test, factory requirement or guarantee
of future recall/FPR. Recall sits exactly at its declared boundary.

| Primary D1 criterion | Declared | PCB2 observed | Outcome |
| --- | ---: | ---: | --- |
| Recall | >=80% | 80/100 | Pass at boundary |
| Normal FPR | <=10% | 5/100 | Pass |
| Median anomaly common pixel AP | >=0.25 | 0.3245 | Pass |
| Peak inside annotation fraction | >=40% | 44/100 | Pass |

| Reviewed endpoint | D1 primary256 | D2 secondary512 |
| --- | ---: | ---: |
| TP / FN | 80 / 20 | 91 / 9 |
| FP / TN | 5 / 95 | 4 / 96 |
| Image AP | 0.9604 | 0.9770 |
| AUROC | 0.9499 | 0.9697 |
| Median per-anomaly common pixel AP | 0.3245 | 0.4957 |
| Per-anomaly pixel AP Q25 / Q75 | 0.1171 / 0.5136 | 0.2967 / 0.6723 |
| Pooled common pixel AP | 0.1534 | 0.2766 |
| Thresholded common pixel IoU | 0.04744 | 0.07044 |
| Peak inside annotation | 44/100 | 71/100 |
| Any thresholded overlap | 97/100 | 100/100 |
| Source-resolution median pixel AP | 0.3293 | 0.4869 |
| Source peak inside | 44/100 | 66/100 |
| Median / p95 inference, seconds | 0.2918 / 0.3064 | 1.0757 / 1.1169 |

Detection uses 100 anomalies and100 held-out normals. Common pooled localization
includes every pixel of all 200 full-source-relative 256 views: 13,107,200 pixels,
27,079 positive annotation pixels. Outside-crop source regions remain scored zero;
annotations are never cropped out of the denominator. No observed annotated pixels
fell outside either crop, and no anomaly mask vanished on nearest resize. Medians/
quartiles and peak/overlap summaries use 100 anomalous images. Source-resolution
metrics use original full images and are supplemental, with a different denominator.
Scores and AP are not probabilities. The inherited 95th normal-score calibration
policy is an operating rule, not a promise of 5% FPR on a new sample.

See [detection](figures/detection.png), [localization](figures/localization.png),
[score distributions](figures/score_distributions.png) and [raw comparison](d1_vs_d2.csv).

## What retained usefulness, and what weakened

Compared descriptively with PCB1 D1, recall changed 89%→80%, FPR 4%→5%, image
AP 0.9680→0.9604 and median common pixel AP 0.3529→0.3245. But pooled pixel AP fell
0.8452→0.1534 and IoU 0.1153→0.04744. For D2, recall 95%→91%, FPR 11%→4%, median
AP 0.5348→0.4957; pooled AP 0.8300→0.2766 and IoU 0.1411→0.07044. Thus image ranking
and typical per-anomaly localization retain useful signal, while globally comparable
pixel ranking and thresholded region precision transfer poorly.

Median per-image AP ranks pixels within each anomaly; pooled AP also compares score
levels across images and includes normal pixels. IoU penalizes false-positive regions
under the fixed normal-calibrated pixel threshold. High any-overlap counts do not
mean the highlighted area is tight. These metrics describe different failures and
must not be substituted for one another. PCB2 has fewer positive common pixels than
PCB1 (27,079 versus 61,045), so prevalence/difficulty also affect pooled AP comparisons;
the decline alone is not proof of a calibration defect or a single map mechanism.

No PCB2 uniform-memory or direct-resize control was run. Absolute confirmation cannot
isolate a causal benefit of coreset/geometry on PCB2. D1/D2 resolution comparisons
also change the candidate sampling fraction at fixed memory count. Categories are
not established as statistically interchangeable; 100 anomalies/normals provide
finite-sample observations, not precise factory guarantees.

## Remaining error concentrations and fixed qualitative review

Missing-component labeled images remain difficult: D1 detects 12/19 (63.2%), with
median AP 0.0757; D2 detects 13/19 (68.4%), median AP 0.2087. Six of D2's nine missed
images have that source label. Defect types overlap (nine multi-label images); counts
must not be added as disjoint populations, and these associations do not prove why
an image was missed. D2 detects 15/15 bent, 52/55 melt and 20/20 scratch labeled images.
See [type slices](defect_type.csv) and [type figure](figures/defect_type_recall.png).

Fixed PCB1 common-mask area bands show weaker detection for small defects. In the
smallest band D1 detects 7/14 and D2 detects 9/14; in the next band 8/15 and 12/15. The
largest band reaches 36/37 and 37/37. These are fixed reference bands, not PCB2
quartiles. Supplementary PCB2 quartiles use the preregistered higher/left-tie rule.
Small-bin results are descriptive and size/type may be confounded. See
[size slices](defect_size.csv) and [size figure](figures/defect_size.png).

The frozen qualitative rules selected 18 distinct examples on 3 sheets: marginal TPs,
near-threshold FNs, high-score FPs, small/large masks, median-area type representatives,
recipe disagreements and peak/overlap cases. No new inference or selection by visual
appeal occurred. Maps use their own frozen pixel threshold as denominator, clipped
0–2, with unchanged cyan annotations; this display does not show probabilities.
[Sheet1](figures/qualitative_contact_sheet_01.png), [sheet2](figures/qualitative_contact_sheet_02.png)
and [sheet3](figures/qualitative_contact_sheet_03.png) include broad diffuse responses
and disagreement cases, not only clean successes. Some shown boards have pins at the
bottom and physically reversed orientation relative to reviewed training examples.
Pose sensitivity is a post-confirmation candidate explanation, not a proven cause;
no registration was added or tested in Stage4. A broad map can detect an anomaly while
ranking unrelated board regions highly. [Selection metadata](qualitative_metadata.json)
records the rules and saved-output-only scope.

Saved-count pixel analysis reinforces that thresholded responses are broad: D1 has
510,336 false-positive pixels (81,281 on normals, 429,055 on anomalies); D2 has
325,593 (65,668 on normals, 259,925 on anomalies). The ten largest contributors account
for 36.35% and 35.50% respectively. Both reversed-pose examples visible on sheet2 (`bfebbd19caf4dad38fd66eab` and
`76964f3ab9f7c03b08de6900`) are among each recipe's top five contributors. This is a post-confirmation descriptive
association, not a causal pose effect or an estimate of reversed-pose frequency.
See [pixel error contributions](pixel_error_contributions.csv) and
[summary](pixel_error_contributions.json). No orientation intervention was executed.

## Engineering, clocks and validation limits

| Normal preparation | D1 | D2 |
| --- | ---: | ---: |
| Measured preparation timer, seconds | 207.135 | 652.335 |
| UTC start-to-completion span, seconds | 2457.094 | 2942.653 |
| Normal preparation peak RSS, bytes | 1,153,318,912 | 2,935,586,816 |
| Candidate count | 737,280 | 2,949,120 |
| Reference fraction | 0.5556% | 0.1389% |
| Represented fitting images /720 | 676 | 696 |
| Padding-centered reference fraction | 1.074% | 0.464% |

The frozen implementation gates `perf_counter` preparation duration <=1800 seconds,
RSS <=8 GiB and median inference <=10 seconds. Both passed those measured gates. UTC
spans exceeded 30 minutes; no under 30 minute calendar completion guarantee is supported,
and the discrepancy's cause is not established. Do not reinterpret the gate after
unseal. Machine state differs across observations; timings do not isolate a causal
cross-category compute effect. D2 confirmation inference is about 3.69 times D1.
[Runtime table](runtime.csv), [phase costs](runtime_phases.csv) and
[runtime/review burden](figures/runtime_review_burden.png) preserve both clocks.

All 109 tests passed. Normal reviews checked exact group splits/identities, all
calibration inverse maps/quantiles, 4096 unique fitting coordinates, five re-extracted
selected vectors/projection values and first 16 independent selector steps. Full
reviews checked all 200 flags/image AP/AUROC/confusions, all 200 inverse maps, all 100
anomaly common APs, pooled AP/IoU and all completion/freeze identities. Source metrics
were independently recomputed on 3 fixed anomalies, not all 100; the full 4096-step
selector was not independently rerun. Original saved artifacts and code remain
unchanged. Reviews: [D1](../pcb2_d1_primary/independent_review.json),
[D2](../pcb2_d2_secondary/independent_review.json).

Historical PCB1 range prefetch/probes could have transiently transported incidental
PCB2 payload bytes. No earlier PCB2 image persistence, decoding, viewing or scoring
was discovered, but zero historical bytes cannot be guaranteed. This disclosed
transport uncertainty limits a literal transport-sealed claim while preserving the
fresh analytical category story. New normal acquisition used exact allowlisted
ranges with no prefetch. Acquisition labels/header routing were structural metadata
access. Dataset physical board identities and factory timestamps remain unknown.
Pretrained commercial/redistribution rights remain unverified; scope is educational.

## Decision and next question

D1 passes the declared practical criterion, with mixed map quality. Preserve D1 as
primary and the cheaper baseline, and D2 as a stronger observed secondary alternative;
do not rewrite the primary after seeing results. Defer UI. The next recommended work
is saved-map/reference diagnosis of missing/small defects, broad maps and possible
pose sensitivity, before selecting one controlled spatial-matching test or a backbone
question. No Stage5 experiment, new model or UI was executed here. Any later tuning
on PCB2 must be labeled post-confirmation development, with new identities.

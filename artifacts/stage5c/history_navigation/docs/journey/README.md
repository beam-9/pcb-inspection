# PCB inspection: an investigation in stages

Updated October 4, 2026. Public VisA PCB benchmark; local educational/research project.
The project asks whether a person could use anomaly scores, highlighted regions and
traceable normal references to review suspicious boards. It does not measure a
Seagate production process or establish automatic rejection reliability.

| Stage | Question | Intervention | Evidence and decision |
| --- | --- | --- | --- |
| 1: frozen feasibility | Does a small normal-reference detector provide useful signal? | Direct256 ResNet18, uniform4096 patch memory, normal-only calibration; global embedding comparator | Ranking signal exists, but57/100 anomalies missed and median localization weak. **Stop/revise methodology**; investigate before building the app. |
| A2: retrospective diagnosis | Where does that frozen detector struggle? | Reuse saved PCB1 scores/maps; type/size, operating-point and localization analysis | Hypotheses about detail, reference matching and operating points; no independently validated replacement threshold and no established single cause. |
| 2: geometry/resolution | Does using more input pixels for the board help? | Content crop/margin, aspect preservation, gray padding at256 (C1), then512 (C2); same4096 uniform policy | C1 lowers normal review burden and improves recall. C2 improves typical localization but raises FPR and cost. Keep both matched references for the next question. |
| 3: memory selection | At the same4096 budget, does representative selection improve either geometry branch? | D1/D2 replace only uniform selection with declared projected approximate greedy selection | Both independently reviewed. Carry D1 forward as the lower-FPR, faster default; preserve D2 for higher recall/localization. Decision led to the later Stage4 confirmation. |
| 4: PCB2 confirmation | Does the frozen procedure retain useful signal on a fresh analytical category? | Unchanged normal-reviewed geometry, category-specific fitting/calibration; D1 primary, D2 secondary | D1 80% recall/5% FPR passes practical point criteria; D2 91%/4%. Pooled AP/IoU degrade. Diagnose saved evidence before UI. |
| 5A: failure diagnosis | Why broad maps and missing/small failures? | Saved-map, pose and nearest-reference diagnosis | Five reversed anomalies dominate FP burden; missing misses canonical/local. Test orientation alone. |
| 5B: orientation experiment | Does canonical orientation reduce broad responses? | Exact 180° crop query normalization; historical D1 bank/thresholds unchanged | FP falls87.65% on five reversed images, detection5→4.195 exact controls. **Mixed support; no unconditional adoption.** |

Stage1 was **frozen before original final scoring**. Structural dataset integrity
checks read labels/masks before the scoring gate, as disclosed in its exposure
ledger. PCB1 became development data after the original results and examples were
viewed. Later PCB1 comparisons are development findings; they do not retroactively
change Stage1's status or make its test untouched again.

## Measured results so far

The table keeps detection, normal review burden and localization together. All rows
use100 anomalous and100 normal PCB1 images. Common localization uses the full-image
256 view with source masks nearest-resized; cropped-out source areas remain in the
denominator. Per-image AP summaries below use the100 anomalous images.

| Recipe | Recall | Normal FPR | Image AP | AUROC | Median anomaly pixel AP | Pooled pixel AP | Peak inside mask | Median inference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Run1 direct256 | 43% | 9% | 0.852 | 0.865 | 0.039 | 0.792 | 26/100 | 0.307s |
| C1 crop256 | 61% | 4% | 0.906 | 0.908 | 0.097 | 0.813 | 30/100 | 0.292s |
| C2 crop512 | 70% | 12% | 0.903 | 0.913 | 0.354 | 0.686 | 50/100 | 1.081s |
| D1 crop256 representative4096 | 89% | 4% | 0.968 | 0.973 | 0.353 | 0.845 | 49/100 | 0.291s |
| D2 crop512 representative4096 | 95% | 11% | 0.976 | 0.978 | 0.535 | 0.830 | 71/100 | 1.081s |

Each recipe recalibrates under the same normal-only95th image/99th common-map
quantile policy, `higher` and strict `>`. Threshold values differ; scores are anomaly
scores, not probabilities. Geometry timing includes hashing/cropping while Run1
timing excludes raw hashing, so original-versus-new cost is not a perfectly matched
latency benchmark. Fullsource per-image localization is supplemental and has a
different denominator from common256. Overlapping defect-type counts must not be
added as independent examples.

C1's improved detection did not improve IoU:0.118 versus Run1's0.122. C2's typical
localization improved while pooled AP fell and12 normal boards were flagged. These
tradeoffs prevent a single “best accuracy” storyline. C1→C2 changes effective
resolution **under a fixed reference count**, which also reduces the sampled
fraction; it does not isolate every possible mechanism of resolution improvement.

## Stage3: representative selection improves the matched recipes

The memory hypothesis is that uniform selection retains redundant patches and
misses rare healthy structures. Farthest-first selection may improve coverage, but
can also emphasize outliers. A smaller sampled fraction at512 is an arithmetic
fact, not proof that memory caused its12% false alarms.

```text
C1/C2: all fitting-normal patch positions → uniform sampling → 4096 references
D1/D2: same positions → projected approximate greedy selection → 4096 references
```

The matched experiment preserved geometry, weights,384-dimensional
scoring features, image maximum, Euclidean nearest distances, map interpolation,
all-patches padding eligibility, splits and calibration policy. Projection is for
selection only. No rotation/registration, spatial restriction, larger memory,
backbone change or padding exclusion belongs in Stage3.

Both full-population preparations passed the normal-only 8 GiB RSS/30-minute
budget and 10-second median inference gate. Charged preparation took 117.955 seconds
for D1 and 361.741 seconds for D2, including 44.616 seconds of reused pilot extraction.
The complete candidate populations were retained; no candidate pre-sampling was
needed. Phase costs and the separate engineering-pilot RSS peak are disclosed in
the [Stage3 exposure ledger](../development/stage3_exposure_ledger.md).

Coverage must be measured on the same predetermined fitting-normal query indices
for both banks, in original scoring space as well as projected space. Report query
sample size, mean/median/p95/max nearest distance, represented images, selected-index
uniqueness and padding-center composition. Reference percentage alone is not feature
coverage. A patch-center padding proxy says nothing definitive about the whole
receptive field.

Matched C1→D1 recall rose from 61 to 89 of 100 anomalies at the same 4 of 100
normal flags. Median common pixel AP rose from 0.097 to 0.353, while thresholded
pixel IoU fell slightly from 0.118 to 0.115. Matched C2→D2 recall rose from 70 to 95,
normal flags changed from 12 to 11, and median pixel AP rose from 0.354 to 0.535.
D2's IoU rose from 0.127 to 0.141. Thus improved ranking and typical localization do
not guarantee tighter thresholded regions for every branch.

Both completed runs passed independent checks of frozen/output identities,
normal-only quantiles, all 200 image flags/AP/AUROC/confusions, all 100 anomaly
common-map APs, pooled AP, and all 200 inverse geometry mappings. The review also
checked all 4096 unique fitting coordinates and re-extracted five selected vectors.
Source-resolution arithmetic was independently sampled on three fixed anomalies;
the complete 4096-step selection was not independently rerun. These limits are
recorded in the review receipts rather than described as complete reimplementation.

This one declared selection recipe supports representative memory as a useful
intervention on exposed PCB1. Coverage and composition diagnostics help describe
the change; they do not establish memory redundancy as the sole original cause or
validate a Seagate production process.

**Decision:** carry D1 forward as the default development recipe: 89% recall,
4% normal FPR and 0.291-second median inference. Preserve D2 as the higher-recall,
stronger-localization alternative at 11% FPR and about 3.7 times the inference cost.
The decision at Stage3 completion was to freeze category adaptation and normal-only
geometry/resource gates before PCB2 confirmation. That work was not executed in Stage3; the later authorized Stage4 is reported below.
No app was built.

## Stage4: fresh analytical category confirmation

[Stage4](stage_04_pcb2_confirmation.md) refit/calibrated PCB2 normals under the frozen
procedure, with D1 primary throughout. Inherited geometry passed normal-only review
unchanged. D1 reached 80/100 recall and 5/100 normal flags, median anomaly AP 0.3245 and
peak-inside 44/100: all preregistered practical point criteria passed. D2 reached 91/100,
4/100 normal flags, median AP 0.4957 and peak-inside 71/100, at about 3.69 times inference.

Pooled pixel AP fell to 0.1534/0.2766 and IoU to 0.04744/0.07044, much lower than PCB1.
Detection and typical localization retain useful signal; broad pixel responses,
missing-component and small-defect failures limit the result. Missing-labeled images
were detected 12/19 by D1 and 13/19 by D2; six of nine D2 misses carry that overlapping
source label. The smallest fixed area band reached 7/14 and 9/14 recall. Both full reviews passed;
no retuning or primary reassignment occurred. There was no PCB2 uniform control, so
causal geometry/coreset transfer is not established. Future diagnosis should reuse
saved maps/reference traces before one controlled intervention; defer UI. Stage5 was
not executed.

The [ledger](../development/stage4_exposure_ledger.md) discloses historical uncertain
incidental archive bytes without discovered prior analytical exposure. Measured
preparation-clock gates passed, while UTC calendar spans exceeded 30 minutes; no calendar
guarantee is claimed. Some fixed qualitative examples have reversed physical pose;
that post-confirmation observation is a hypothesis, not a proven failure cause.

## Read the evidence

- [Stage1 findings](../pilot_findings.md), [original protocol](../protocol.json), [original exposure ledger](../exposure_ledger.md), [executed pilot notebook](../../notebooks/pcb1_pilot.ipynb).
- [A2 diagnostics](../../artifacts/pcb1_a2/diagnostic_summary.md), [A2 exposure ledger](../development/a2_exposure_ledger.md).
- [Stage2 findings](../../artifacts/pcb1_geometry_comparison/findings.md), [coordinate/metric protocol](../development/geometry_resolution_protocol_review.md), [execution ledger](../development/geometry_execution_ledger.md), [executed geometry notebook](../../notebooks/pcb1_geometry_resolution.ipynb).
- [Stage4 findings](../../artifacts/stage4/comparison/findings.md), [normal geometry chapter](stage_04a_pcb2_normal_adaptation.md), [confirmation chapter](stage_04_pcb2_confirmation.md).
- [Stage3 proposal review](../development/stage3_plan_review.md), [method notes](../development/stage3_method_notes.md), [exposure ledger](../development/stage3_exposure_ledger.md), [D1 independent review](../../artifacts/runs/coreset_256_v1/independent_review.json), [D2 independent review](../../artifacts/runs/coreset_512_v1/independent_review.json), [decision log](decision_log.md). Earlier proposal text remains historical.

Pretrained weight commercial/redistribution rights remain unverified. Benchmark
acquisition identity is unknown; no factory timestamps or unseen-factory claims are
made. PCB2 category-specific memory and normal calibration tested a frozen adaptation
procedure; zero-shot transfer of the PCB1 memory was not tested.

## Stage 5A — Diagnose before changing the detector

[Completed failure diagnosis](stage_05a_failure_diagnosis.md) quantifies pose, traces
all 19 missing-label cases at both resolutions, maps crop-relative FP burden and
decomposes 29 small defects. This uses exposed PCB2 development data; Stage 4 remains
published history at 2ec21c4. Five reversed images contribute about 29–30% of FP pixels
but no image misses. Canonical missing-label misses retrieve more local references
than hits, weakening distant matching as the next intervention. One proposed next
step is canonical orientation normalization; no Stage 5B detector was fitted/scored.
See the [combined decision](../../artifacts/stage5a/combined/decision_summary.md),
[diagnostic dataset](../../artifacts/stage5a/combined/per_image_diagnostics.csv),
[validation receipt](../../artifacts/stage5a/independent_review.json) and
[artifact-only notebook](../../notebooks/pcb2_stage5a_diagnostics.ipynb).

## Stage 5B — Controlled orientation, with a detection trade-off

[Completed Stage 5B](stage_05b_orientation_normalization.md) changed only confidently
reversed crops. Reversed FP falls146,977→18,157 and median pixelAP0.0757→0.8314,
but detection5/5→4/5. All195 non-reversed outputs remain exact; all100 normal flags
unchanged. Full recall79/100, FPR5/100, pooled pixelAP0.3142, IoU0.06234. All130 tests
and independent checks passed. Keep Stage4 D1 primary; this is mixed development
support, not unconditional adoption. The next question is preserving true defect
signal while removing broad pose mismatch, alongside unresolved canonical failures.
See [full findings](../../artifacts/stage5b/findings.md),
[all-five paired evidence](../../artifacts/stage5b/results/reversed_paired_results.csv),
[independent review](../../artifacts/stage5b/independent_review.json) and
[artifact-only notebook](../../notebooks/pcb2_stage5b_orientation.ipynb).
Stage5A's earlier recommendation above is its historical completion snapshot.
Pre-update navigation copies under Stage5B history_navigation preserve its receipt
hashes; model/evidence history remains unchanged. Stage5C and UI remain deferred.

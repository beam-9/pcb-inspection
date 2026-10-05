# PCB visual inspection feasibility pilot

A local educational project using public **VisA PCB1 and PCB2**, exploring whether visible
anomaly scores and suspicious-region maps can support a human inspection workflow.
It uses no Seagate data and establishes no factory performance or root causes.

The initial **Phase A** scope compared a frozen global-embedding nearest-normal baseline
versus a clearly labeled **PatchCore-inspired** normal patch-memory detector.
Both use frozen ResNet18 features. Normal-only calibration and an exclusive guarded
final evaluation preserve the official benchmark and prohibit test-driven tuning.
The review application and Ollama integration follow a separate decision.

## Measured Phase A outcome

**Recommendation: stop/revise methodology.** All 30 tests pass, and the final
metrics/reference traces were independently checked. The executed pilot is complete.

| Method | Image AP | AUROC | Recall | Normal false alarms |
| --- | ---: | ---: | ---: | ---: |
| Global embedding baseline |0.8276|0.7872|43/100|2/100|
| PatchCore-inspired |0.8516|0.8654|43/100|9/100|

Pooled pixel AP is 0.7920, but median per-anomaly AP is only 0.0393; heatmap peaks
fall inside annotations for 26/100 anomalies. CPU inference takes 0.307 s median
(0.335 s p95). This is useful experimental evidence, but insufficient to support a
reliable small-region inspection workflow. [Full findings](docs/pilot_findings.md)
include failures, protocol, runtime, provenance and proposed next study.

## A2 development diagnostics — 2 October 2026

The proposed improvement plan was critically reviewed, then the saved Run 1 outputs
were analyzed without refitting. PCB1 is now development data; PCB2 remains sealed.

- Source-labeled scratch recall is **3/21 (14.3%)**; melt recall is **19/54 (35.2%)**.
- The largest mask-area quartile has **70.8% recall**, versus **29–40%** for the smaller groups.
- A retrospective threshold can detect **53/100** anomalies with the same **9/100**
  observed false alarms. This is a diagnostic oracle point, not a calibrated operating policy.
- Poor localization remains concentrated in misses; the saved location traces do not
  establish cross-location matching as their cause.

Start with the [A2 diagnostic summary](artifacts/pcb1_a2/diagnostic_summary.md) and
[executed A2 notebook](notebooks/pcb1_a2_diagnostics.ipynb). The
[plan review](docs/improvement_plan_review.md) corrects method/source assumptions;
[feasibility note](docs/improvement_feasibility.md) bounds memory and search costs.

The next proposed comparison isolates verified board geometry and then 512 resolution
with ResNet18 and a fixed memory budget. Coreset/backbone changes follow separate tests.
No revised-model improvement or fresh PCB2 confirmation has been claimed.

## Geometry and resolution experiments — 2 October 2026

The completed comparison retained ResNet18 and the same 4,096-reference budget,
then tested a conservative content-derived board crop with aspect preservation at
256 and 512 pixels. Thresholds were recalibrated only from the same normal partition.

| Recipe | Detected defects /100 | Normal false alarms /100 | Median anomaly pixel AP |
| --- | ---: | ---: | ---: |
| Original direct 256 | 43 | 9 | 0.039 |
| Crop 256 | **61** | **4** | 0.097 |
| Crop 512 | 70 | 12 | **0.354** |

Crop 256 offers the better current balance of detection, normal review burden and
cost. Crop 512 improves typical localization but takes about 3.7 times longer than
crop 256, raises false alarms, and lowers pooled pixel AP. Neither result establishes
factory readiness or fresh-category generalization. These are PCB1 development results.

Read the [complete comparison](artifacts/pcb1_geometry_comparison/findings.md),
[executed notebook](notebooks/pcb1_geometry_resolution.ipynb),
[coordinate and experiment controls](docs/development/geometry_resolution_protocol_review.md),
and [experiment registry](artifacts/experiment_registry.csv).
All 50 tests pass and both independent run reviews passed. PCB2 remains sealed.
Large reference arrays, calibration maps and individual heatmaps remain local;
tables, figures, protocols and artifact-reading notebooks are published.

The A2 section above records the earlier diagnostic snapshot; its proposed geometry
comparison has now been completed. Historical README hashes can be verified against
the A2 commit documented in the [publication notes](docs/development/publication_notes.md)
rather than this evolving README.

## Representative memory selection — Stage 3 completed

At the same 4,096-reference budget, selecting representative normal patches improves
both preserved geometry branches. Each new recipe was frozen before evaluation;
thresholds still use normal-only calibration. These are PCB1 development results.

| Recipe | Detected /100 | Normal false alarms /100 | Median anomaly pixel AP | Median CPU inference |
| --- | ---: | ---: | ---: | ---: |
| Uniform 256 → representative 256 | 61 → **89** | **4 → 4** | 0.097 → 0.353 | 0.291 s |
| Uniform 512 → representative 512 | 70 → **95** | 12 → **11** | 0.354 → **0.535** | 1.081 s |

Carry representative 256 (D1) forward as the default balance of detection, review
burden and speed. D2 offers higher recall/localization with more normal flags and
processing cost. D1 pixel IoU slightly regresses; measured fitting-memory coverage
improves in the tail but worsens on average. All outcomes and limits are retained.

Read the [Stage 3 findings](artifacts/pcb1_memory_selection_comparison/findings.md),
[executed artifact-only notebook](notebooks/pcb1_memory_selection.ipynb),
[project journey](docs/journey/README.md) and [decision log](docs/journey/decision_log.md).
All 81 tests, both independent reviews and resource gates passed. PCB2 remains sealed; category
adaptation and normal-geometry checks must be frozen before fresh confirmation.
The completed Stage 3 snapshot and follow-up publication notes were pushed through
`91aa697`. See [commit provenance](docs/development/stage3_publication_notes.md).

## Fresh PCB2 confirmation — Stage 4

The frozen procedure fitted new references from **720 PCB2 construction normals**,
calibrated on **181 normals**, and evaluated once on **100 held-out normals and
100 anomalies**. Normal-only geometry review preceded unsealing; D1 at 256 was
declared primary and D2 at 512 secondary. Both independent confirmation reviews passed.

| Recipe | Detected /100 | Normal false alarms /100 | Median anomaly pixel AP | Peak inside /100 | Median CPU inference |
| --- | ---: | ---: | ---: | ---: | ---: |
| D1 primary 256 | **80** | **5** | **0.325** | **44** | **0.292 s** |
| D2 secondary 512 | 91 | 4 | 0.496 | 71 | 1.076 s |

D1 meets all four declared project criteria: recall ≥80%, normal FPR ≤10%, median
common 256 pixel AP ≥0.25 and peak-inside fraction ≥40%. D2 has stronger observed
detection and localization at about 3.7 times the inference cost; it remains secondary.
These are category-adapted benchmark results, with normal references fitted for PCB2.
They do not establish factory readiness or isolate the cause of category differences.

Localization remains limited: pooled pixel AP fell from 0.845/0.830 on PCB1 to
0.153/0.277 on PCB2, and fixed-threshold IoU is only 0.047/0.070. Missing-component
images were detected in 12/19 and 13/19 cases. These weaknesses motivate diagnosis
before building the application. See the [full findings](artifacts/stage4/comparison/findings.md)
and [executed evidence notebook](notebooks/pcb2_stage4_confirmation.ipynb).

Preparation timing has a material limit: the frozen measured timer reports 207/652 s
for D1/D2, while recorded start-to-finish UTC spans are 2,457/2,943 s, above the
1,800-second preparation target. The saved runtime table preserves both measures;
an end-to-end preparation-cap claim remains unsupported.

Read the [Stage 4 journey and interpretation](docs/journey/stage_04_pcb2_confirmation.md),
[normal-only adaptation record](docs/journey/stage_04a_pcb2_normal_adaptation.md),
[comparison table](artifacts/stage4/comparison/d1_vs_d2.csv),
[runtime evidence](artifacts/stage4/comparison/runtime.csv) and
[predeclared qualitative examples](artifacts/stage4/comparison/qualitative_selection.csv).
The [frozen protocol](configs/stage4_protocol.json) records the criteria and sequence.
Earlier sections preserve the historical snapshots when PCB2 was still sealed.
This paragraph records Stage 4 completion; subsequent Stage 5 work is below. Application/UI and Ollama remain deferred.

## Failure diagnosis — Stage 5A

Stage 4 is [committed and pushed as 2ec21c4](https://github.com/beam-9/pcb-inspection/commit/2ec21c4686c7dad7d60c177cb35fed2cd62d9280).
Subsequent PCB2 analysis is post-confirmation development diagnosis. Detector code,
banks, thresholds and Stage 4 predictions remain unchanged.

Five reversed anomalies contribute about **29–30% of false-positive pixels** in both
recipes. Their anomaly-only median burden is 11–12 times canonical anomalies, but all
five are detected and no reversed normals exist. Missing-component misses occur on
canonical boards; their frozen nearest neighbors are generally **more local** than
those of detected canonical cases. Distant matching is not the distinctive failure
pattern proposed by the handoff.

The one recommended next experiment is **canonical orientation normalization**,
with existing D1 features/scoring/memory/calibration policy controlled. It has not
been implemented. Canonical missing-component failures remain a separate unresolved
question. All **121 tests** and diagnostic metric/identity checks pass.

Read the [Stage 5A diagnosis](docs/journey/stage_05a_failure_diagnosis.md),
[combined decision](artifacts/stage5a/combined/decision_summary.md),
[200-image diagnostic table](artifacts/stage5a/combined/per_image_diagnostics.csv),
[nearest-neighbor findings](artifacts/stage5a/missing_component/findings.md) and
[executed evidence notebook](notebooks/pcb2_stage5a_diagnostics.ipynb).

## Controlled orientation normalization — Stage 5B

Only confidently reversed crops received exact 180° normalization, with the same
D1 bank, thresholds, features and scoring. All 195 unrotated evaluation images
reproduced tensors/maps/scores/flags/AP/FP counts exactly; all 1,101 pose labels matched.

Reversed FP pixels fell **146,977 → 18,157 (87.65%)**, and median reversed pixel AP
rose **0.0757 → 0.8314**. But detection fell **5/5 → 4/5**: one small missing-component
case lost enough image signal to become a miss. Full recall is **79/100**, with the
same **5/100** normal flags. Pooled pixel AP rose **0.1534 → 0.3142**; IoU is **0.06234**.

**Mixed support; no unconditional adoption.** Historical Stage 4 D1 remains primary.
The next question is how to preserve true defect signal while reducing pose-induced
broad response; canonical missing/small failures remain unresolved. Median total
inference is 0.3636 s (p95 0.4049 s), with timing boundaries disclosed in the findings.
All **130 tests** and the independent numerical/coordinate/control audit pass.

Read the [Stage 5B journey](docs/journey/stage_05b_orientation_normalization.md),
[full findings](artifacts/stage5b/findings.md), [all-five paired table](artifacts/stage5b/results/reversed_paired_results.csv),
[before/after maps](artifacts/stage5b/figures/reversed_before_after.png),
[independent review](artifacts/stage5b/independent_review.json) and
[executed artifact-only notebook](notebooks/pcb2_stage5b_orientation.ipynb).
Stage 4 and Stage 5A evidence remain preserved. These are exposed PCB2 development
results based on five reversed anomalies; there are no reversed normal controls.

## Inspect the first findings

![Score distributions for both frozen methods](artifacts/runs/31e0704ff1da6906/score_distributions.png)

![Per-anomaly localization varies substantially](artifacts/runs/31e0704ff1da6906/per_anomaly_localization.png)

The [localization examples](artifacts/runs/31e0704ff1da6906/localization_examples.png)
include a missed anomaly and a false alarm alongside stronger examples. Source masks
are shown only as retrospective benchmark annotations. Predictions, thresholds,
metrics, runtime and verification receipts are saved under
[`artifacts/runs/31e0704ff1da6906`](artifacts/runs/31e0704ff1da6906).

## Setup

Python 3.11 on macOS ARM64 was used. Create an isolated environment, then install
exact successful dependency versions:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-build-isolation -e .
source .venv/bin/activate
```

Raw data, feature arrays and checkpoints are Git-ignored. Owner-hosted VisA is
CC BY 4.0; attribution and weight-use limitations are in
[the source record](docs/source_research.md) and [data card](docs/data_card.md).
The acquisition command selectively retrieves PCB1 via validated byte ranges;
it never silently downloads the full 1.80 GiB archive:

```bash
python -m pcb_inspection.acquisition --destination data/raw
python -c "from pcb_inspection.data import build_manifest; print(build_manifest('data/raw','data/raw/1cls.csv','data/manifests'))"
```

## Reproduce the saved pilot

Start with [the executed notebook](notebooks/pcb1_pilot.ipynb),
[measured findings](docs/pilot_findings.md), [protocol](docs/protocol.md),
and [exposure ledger](docs/exposure_ledger.md). The notebook reads saved evidence;
rerunning it does not fit or unseal the benchmark again.

This GitHub snapshot includes the notebook's executed outputs, predictions, manifests,
metrics, provenance and rendered figures. Raw images, pretrained weights, fitted
reference models, feature arrays and full anomaly-map arrays are excluded. You can
inspect the published evidence directly on GitHub. Executing the artifact-reading
notebook requires the corresponding local data/cache and anomaly maps; a fresh clone
alone does not contain those large local artifacts.

For a **separate reproduction workspace without the saved final run or access receipts**,
after acquiring/auditing
raw data and caching the exact official checkpoint under
`data/cache/hub/checkpoints/resnet18-f37072fd.pth`, run the normal preparation and
then the guarded final command:

```bash
python -m pcb_inspection.checks
python -m pcb_inspection.pilot prepare
python -m pcb_inspection.evaluate_test --config configs/pilot.yaml --protocol docs/protocol.json --confirm-frozen-protocol
python -m pcb_inspection.verify_results --run artifacts/runs/RUN_ID --raw-root data/raw
```

These commands document the original execution sequence. Preserve the published run
and receipts as historical evidence; a new experiment needs a separate workspace and
its own frozen protocol. The original final test has already been viewed, so rerunning
it is replication rather than fresh validation.

The exact frozen protocol expects the recorded source/config/code/manifest/weight
identities, successful tests, calibration and leakage/resource gates. It refuses
changed content or an existing final-access receipt. A new machine or changed recipe
requires its own explicitly documented protocol, rather than quietly modifying this
run. See `artifacts/tests_passed.json` for the measured verification receipt.

No anomaly model was fine-tuned; uniform memory sampling is a departure from the
PatchCore coreset method. Direct 256-square resizing can discard small defects;
benchmark prevalence and acquisition conditions cannot establish factory precision.
Local pretrained-weight use is educational; commercial rights remain unverified.

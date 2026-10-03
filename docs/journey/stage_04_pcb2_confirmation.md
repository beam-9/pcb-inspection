# Stage4: useful detection on PCB2, localization remains mixed

Completed October 2, 2026 locally. The frozen primary D1 detects 80/100 anomalies with
5/100 normal flags and passes every preregistered numerical project criterion.
Secondary D2 detects 91/100 with 4/100 normal flags. Both independent reviews passed.
However, pooled pixel AP and thresholded IoU fell substantially from PCB1 development;
passing the practical criterion does not mean localization transferred intact.

## Where we came from and what was tested

The original frozen PCB1 feasibility detector reached 43% recall. Geometry/resolution
development reached 61–70%; representative normal-memory selection reached 89–95%.
D1 was selected before PCB2 outcomes for its lower review burden and faster inference.
Stage4 asks whether the frozen category-adaptation procedure retains useful signal
on fresh analytical PCB2, rather than optimizing another PCB1 configuration.

Both recipes retain ResNet18 local features, 4096 projected approximate-greedy selected
references, full-dimensional scoring, maximum patch image score and normal-only
higher 95th/99th quantile calibration with strict `>`. D1 is 256, D2 is 512. PCB2 normal
memory and thresholds are fitted anew; this is category-specific adaptation, not
zero-shot transfer of the PCB1 bank. No PCB2 uniform/direct-resize control was run,
so this confirmation cannot isolate causal coreset/geometry benefits on PCB2.

The [normal geometry chapter](stage_04a_pcb2_normal_adaptation.md) records 901 training
normals, 720 fitting/181 calibration, with 100 held-out normals excluded from geometry development
and fitting. Both reviewers found inherited geometry suitable on 17 fixed examples;
no category-specific geometry change or pose registration was needed. Both normal
preparations and independent reviews passed before final freeze 01:01:20 UTC October 3;
logical unseal followed 01:01:58. One primary evaluation then one predeclared secondary
was completed without retuning.

## Confirmation results and interpretation

| Endpoint | D1 primary | D2 secondary |
| --- | ---: | ---: |
| TP / FN | 80 / 20 | 91 / 9 |
| FP / TN | 5 / 95 | 4 / 96 |
| Image AP / AUROC | 0.9604 / 0.9499 | 0.9770 / 0.9697 |
| Median anomalous common pixel AP | 0.3245 | 0.4957 |
| Pooled common pixel AP | 0.1534 | 0.2766 |
| Thresholded common pixel IoU | 0.04744 | 0.07044 |
| Peak inside annotation | 44/100 | 71/100 |
| Any thresholded overlap | 97/100 | 100/100 |
| Median inference | 0.292s | 1.076s |

D1's criterion required recall>=80%, FPR<=10%, median common anomaly AP>=0.25,
peak-inside>=40%, plus gates. Every point criterion passed; recall is exactly at its
minimum. These are project criteria, not statistical equivalence or factory targets.
D2 remains secondary even though its PCB2 detection/localization point estimates are
stronger. Its inference costs about 3.69 times D1.

Image ranking and typical per-anomaly localization retain useful signal. But D1 pooled
AP drops 0.8452→0.1534 and IoU 0.1153→0.04744; D2 drops 0.8300→0.2766 and 0.1411→0.07044.
Per-image AP ranks within an anomaly, whereas pooled AP compares scores across all
images and IoU penalizes excessive highlighted regions. Broad responses and normal
pixels matter even when the map overlaps a defect. Different positive-pixel prevalence
also affects pooled AP comparisons. Common metrics retain all 200 full-source-relative
256 views, 13,107,200 pixels including outside-crop regions. No observed GT was clipped.
Source-resolution supporting metrics use different denominators.

## Remaining failures and next question

Missing-component source labels remain difficult: D1 detects 12/19, D2 detects 13/19;
median common AP 0.0757/0.2087. Six of nine D2 misses carry that label. Small fixed PCB1
area bands also perform worse than the largest band. Type memberships overlap;
these associations are descriptive. The 18 fixed-rule qualitative examples include
reversed physical board poses and broad maps. Those poses were observed only after
confirmation and are candidate explanations, not proven causes or a reason to retune.
Saved-count analysis finds 510,336/325,593 false-positive pixels for D1/D2; two reversed
examples are among the five largest contributors for both recipes. No pose-frequency
or causal claim follows from this selected sample.

Defer UI. Recommend saved-map/reference diagnosis of missing/small defects, diffuse
maps and possible pose sensitivity before choosing one controlled spatial-matching
experiment or a backbone question. No Stage5 experiment was executed. Future PCB2
tuning must be labeled post-confirmation development with a new identity.

## Evidence and limits

The frozen `perf_counter` preparation gates passed at 207/652 seconds, with peak RSS
about 1.15/2.94 GB. UTC spans 2457/2943 seconds exceeded 30 minutes; cause is unestablished
and no calendar completion guarantee is claimed. Full reviews checked all image and
common-map results/inversions; independent source-resolution arithmetic covers three
fixed anomalies, and full 4096-step selection was not independently rerun.

Historical archive prefetch/probes may have transported incidental PCB2 bytes before
Stage4, though no earlier PCB2 persistence/decoding/viewing/scoring was discovered.
Fresh analytical confirmation is retained with that limitation; zero incidental
transport cannot be guaranteed. Dataset physical identities are unknown and
commercial pretrained-weight rights unverified. No factory readiness is established.

Read the [complete findings](../../artifacts/stage4/comparison/findings.md),
[comparison figures](../../artifacts/stage4/comparison/figures/journey.png),
[plan review](../development/stage4_plan_review.md),
[exposure ledger](../development/stage4_exposure_ledger.md),
[primary review](../../artifacts/stage4/pcb2_d1_primary/independent_review.json) and
[secondary review](../../artifacts/stage4/pcb2_d2_secondary/independent_review.json).

# Stage3 development exposure ledger

Written October 2, 2026 while the primary agent is executing D1 then D2 serially.
This new ledger is a narrative index; run JSON receipts contain exact event times,
content hashes and immutable execution records. Later completion/review entries
must be appended. No Stage3 performance conclusion is made in this initial entry.

## Scope and preserved chronology

The user explicitly authorized Stage3: replace uniform normal reference selection
with projected approximate greedy selection at the same 4096 reference budget,
matched to C1/C2. PCB1 is already exposed development data. Run1 retains its initial
frozen feasibility status before original scoring; A2 and C1/C2 remain preserved.
PCB2 remains unacquired and sealed. No Stage4, UI or Ollama work is included.

Normal fitting uses the original 723 IDs and calibration the original 181 IDs.
All 740,352/2,961,408 fitting patch positions remain eligible at 256/512, including
padding. No candidate pre-sampling or anomaly-derived selection was used. Gaussian
384→64 projection, seed 43, serves selection only; original 384-dimensional scoring
features remain in the 4096 reference bank. Selection seed 42, mean 10-anchor
Euclidean initialization and farthest-point minimum-distance updates are recorded
in the frozen recipe. Original geometry/scoring/padding/calibration policies stay
matched. Normal-only coverage diagnostics do not select detector settings.

## Events before development anomaly evaluation

Times below are UTC from the saved receipts; October 2 local time in Vancouver is
seven hours earlier. JSON receipts, rather than rounded prose durations, govern.

| Event | UTC timestamp | Evidence |
| --- | --- | --- |
| Full 512 normal-only feasibility declared | 20:00:34.302385 | [Engineering scope](../../artifacts/stage3_engineering/scope.json) |
| Full 512 feasibility completed | 20:01:21.283182 | [Engineering receipt](../../artifacts/stage3_engineering/engineering.json) |
| D1 crop 256 protocol frozen | 20:07:33.488892 | [D1 protocol](../../artifacts/runs/coreset_256_v1/protocol.json) |
| D2 crop 512 protocol frozen | 20:07:35.457649 | [D2 protocol](../../artifacts/runs/coreset_512_v1/protocol.json) |
| D1 normal preparation started | 20:08:13.939611 | [D1 preparation-start receipt](../../artifacts/runs/coreset_256_v1/prepare_started.json) |
| D1 normal preparation completed | 20:10:11.896541 | [D1 prepared receipt](../../artifacts/runs/coreset_256_v1/prepared.json) |
| D2 normal preparation started | 20:11:05.023881 | [D2 preparation-start receipt](../../artifacts/runs/coreset_512_v1/prepare_started.json) |
| D2 normal preparation completed | 20:16:22.155969 | [D2 prepared receipt](../../artifacts/runs/coreset_512_v1/prepared.json) |
| D1 development evaluation claimed | 20:19:53.725754 | [D1 development access receipt](../../artifacts/runs/coreset_256_v1/development_access.json) |

The feasibility pilot extracted/projected the complete 512 fitting-normal population
and selected only 64 references as an engineering timing test. No anomaly-performance
evaluation was done with that pilot bank. It measured 44.616 seconds extraction and
1.599 seconds selection, peak 2,908,520,448 bytes. The 496.964 second full-preparation
estimate included a 350 second allowance and was explicitly an estimate, not a
completed detector run. The resulting full-population projected cache is hash-bound
to source inputs, geometry, weight and projection identities and reused by D2.

All 81 tests passed before both recipe freezes. Independent synthetic selector
checks preceded outcomes; D1's first 16 actual selections matched an independent
NumPy oracle before anomaly evaluation. This prefix check does not constitute a
complete independent 4096-step selector rerun.

## Actual normal resource gates

Both prepared receipts report passing normal-only gates: 8 GiB peak process RSS,
1800 seconds charged total preparation, 10 seconds median inference. Full calibration
uses only 181 normals. Phase measurements are recorded separately.

| Measurement | D1 crop 256 | D2 crop 512 |
| --- | ---: | ---: |
| Charged total normal preparation | 117.955 s | 361.741 s |
| Current-process preparation | 117.955 s | 317.126 s |
| Charged cached extraction | 0 s | 44.616 s |
| Full 4096 selection | 18.363 s | 72.511 s |
| Reference-vector re-extraction | 21.856 s | 43.172 s |
| Normal calibration | 53.034 s | 198.345 s |
| Process peak RSS | 1,046,478,848 bytes | 2,334,834,688 bytes |
| Median normal inference | 0.292 s | 1.083 s |

See [D1 runtime](../../artifacts/runs/coreset_256_v1/normal_runtime.json) and
[D2 runtime](../../artifacts/runs/coreset_512_v1/normal_runtime.json). D2 is not described
as “free extraction” merely because its candidate cache was created during the pilot.
RSS is a per-process high-water measurement; the earlier pilot peak is disclosed
separately. Normal coverage/composition exports are saved before anomaly evaluation
under [256 diagnostics](../../artifacts/stage3_memory_diagnostics/256/memory_diagnostics.json)
and [512 diagnostics](../../artifacts/stage3_memory_diagnostics/512/memory_diagnostics.json).

## Evaluation/review status at this entry

D1 has claimed its one PCB1 development evaluation; D2 is authorized for one
evaluation after D1. Root is executing them serially to preserve timing interpretation.
Other agents are not running CPU
reviews concurrently with inference. This entry did not inspect anomaly outcomes.
Completion JSON, independent-review receipts and matched comparison findings are
required before publication; references to future D2 access/completion remain pending.

Append the D1/D2 completion times, independent-review results, publication identities
and one evidence-backed decision after they exist. If a legitimate implementation
defect is found, preserve its failed artifacts and record invalidation/new identity.
No rerun or anomaly-driven retuning is authorized merely by a disappointing result.

## Completion and independent review appended October 2, 2026

The earlier pending-status entry is preserved as written. Both evaluations are now
complete, each with evaluation count 1 and PCB2 exposure false. No recipe was retuned
or repeated after these development outcomes.

| Event | UTC timestamp | Evidence |
| --- | --- | --- |
| D1 development evaluation completed | 20:21:07.302959 | [D1 completion](../../artifacts/runs/coreset_256_v1/complete.json) |
| D1 independent review passed | 20:21:19.069122 | [D1 review](../../artifacts/runs/coreset_256_v1/independent_review.json) |
| D2 development evaluation claimed | 20:21:29.411162 | [D2 access](../../artifacts/runs/coreset_512_v1/development_access.json) |
| D2 development evaluation completed | 20:25:23.499140 | [D2 completion](../../artifacts/runs/coreset_512_v1/complete.json) |
| D2 independent review passed | 20:25:40.104462 | [D2 review](../../artifacts/runs/coreset_512_v1/independent_review.json) |

Both reviews bind the same reviewer code SHA256
`1ad95d2afc2d9f06c167973799e2727803ef76af9d924e6264d7a6d0daecc23a`.
They bind completion SHA256 identities
`752622b4da50535136e89af448beb34cf23bcf711de1c8d7cdc8a8d97db58490`
(D1) and `94a5a09adaf5994d770c2c2ecf5ce308a6b6a975b9a42f61258537160dd9f2f2`
(D2), check source/output/prerequisite hashes and preserve the matched C1/C2 config.
All 200 image flags, AP/AUROC/confusions and inverse common geometry mappings, all
100 anomalous per-image common pixel APs, pooled common AP and normal calibration
quantile ranks were independently checked. All 4096 fitting-index coordinates were
checked; five selected vectors and their projected cache values were re-extracted.
D1 used the independent first-16 NumPy selection oracle; D2 matched the engineering
first-64 prefix. Full 4096-step selection was not rerun. Source-resolution arithmetic
was independently checked on three fixed anomalies, rather than on the entire set.

| Outcome | D1 | D2 |
| --- | ---: | ---: |
| TP / FN on 100 anomalies | 89 / 11 | 95 / 5 |
| FP / TN on 100 normals | 4 / 96 | 11 / 89 |
| Image AP / AUROC | 0.968 / 0.973 | 0.976 / 0.978 |
| Median anomalous common pixel AP | 0.353 | 0.535 |
| Pooled common pixel AP, all 200 images | 0.845 | 0.830 |
| Thresholded common pixel IoU | 0.115 | 0.141 |
| Peak inside annotation, 100 anomalies | 49 | 71 |
| Median development inference | 0.291s | 1.081s |

Common localization preserves all 13,107,200 pixels across all 200 source-relative
256 views, including areas outside the crop. Per-image AP summaries use the 100
anomalous images. Neither run clipped annotated anomaly pixels in this observed
set. This does not guarantee future crops retain defects.

**Decision after review:** carry D1 forward as the faster, lower-FPR default;
preserve D2 as the higher-recall/localization alternative. One declared approximate
selection recipe improved the matched PCB1 controls; this is development evidence,
not proof of a sole causal bottleneck or fresh-category confirmation. The next work
is to freeze category adaptation and a normal-only geometry/resource gate before
fresh PCB2 confirmation. That work and PCB2 access were not executed in Stage3.
The [journey index](../journey/README.md) records the measured comparison; the
[decision log](../journey/decision_log.md) preserves prior decisions.

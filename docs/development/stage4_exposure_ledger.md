# Stage4 exposure ledger

## Initial entry — October 2, 2026

The user authorized critical review and beginning Stage4 after Stage3. This entry
records reviewer access; acquisition/preflight agents must append their own exact
allowlists, timestamps and receipts. Run JSON identities govern chronological checks.
The prior Stage1–3 artifacts and bound narrative documents remain immutable.

Reviewer accessed the supplied Stage4 handoff and existing PCB1 protocol/Stage3
method, execution and exposure notes. No PCB2 images, masks, anomaly filenames,
defect-type labels or scores were accessed by this reviewer. No PCB2 detector work
or model experiments were performed. The [plan review](stage4_plan_review.md) records
methodological corrections and pre-unseal decisions still required.

PCB2 normal-only acquisition, geometry suitability and bounded adaptation are the
next authorized operations. Anomaly acquisition/access is not permitted until the
final freeze gate binds normal preparation, immutable primary/secondary recipes
and passing independent normal-preflight review. Official held-out normals should
remain untouched by geometry optimization and fitting; any earlier access must be
recorded and its consequence for FPR interpretation disclosed.

Required later entries: normal file allowlist and source identities; acquisition
receipt; normal partition and duplicate-audit identities; inherited geometry review;
any adaptation and its normal evidence; recipe freeze; full normal preparation and
independent review; final freeze receipt; first anomaly/mask/type access; exclusive
primary/secondary evaluation receipts; completions and independent reviews; all
post-unseal diagnosis/publication actions. Do not erase pending entries or earlier
exposures after results. Record accidental exposure immediately.

PCB2 confirmation tests category-specific fitting/calibration under a frozen
adaptation procedure. It is not zero-shot transfer of PCB1 memory, and without a
PCB2 uniform control it cannot isolate geometry/coreset causal transfer.

## Historical transport audit finding — October 2, 2026

During preparation of stricter Stage4 acquisition, the data agent found that the
historical PCB1 `RangeReader` prefetched 8 MB and that bounded 2 MB header probes
could include bytes beyond the requested PCB1 entries, potentially including PCB2
payload. Therefore a blanket claim that no PCB2 bytes were ever transported cannot
be verified. This is an uncertainty about incidental historical transport, distinct
from analytic exposure. The audit found no PCB2 images persisted, decoded, viewed
or scored and no PCB2 masks or defect annotations used in previous modeling work.
The relevant prior records are preserved rather than silently rewritten.

PCB2 remains a fresh analytical category with this transport limitation disclosed;
we do not guarantee zero incidental PCB2 bytes historically reached a transient
reader buffer. New Stage4 acquisition uses exact 512-byte header reads and exact
allowlisted normal payload ranges without prefetch. Acquisition receipts must state
those boundaries and file identities. No anomaly decoding, viewing or scoring is
permitted before the final freeze gate. Any stronger evidence or accidental analytic
exposure must receive a new chronological entry.

## Independent normal geometry visual review — October 2, 2026

This reviewer viewed `normal_contact_sheet_01.png` through `_03.png` under
`artifacts/stage4/geometry_preflight`: 17 selected fitting/calibration normal
examples showing inherited crop extremes and systematic samples. The cyan board
bounds followed the blue board body. Orange margins retained the four protruding
upper connector pins and visible board corners/edges in every shown example.
Letterboxing retained aspect ratio, with gray top/bottom bands and some textured
background. Small pose tilt remains without orientation normalization. No visible
background component error or clipped board/pins appeared in this selected sample.

The normal evidence supports retaining inherited geometry unchanged; it does not
guarantee unseen annotated defects will stay inside future crops. Held-out normals,
anomaly images, masks and defect types were not viewed. Quantitative all-training
normal preflight and exact file identities remain in its machine-readable receipt.

## Normal acquisition, audit and protocol freeze — October 2, 2026

| Event | UTC timestamp | Receipt |
| --- | --- | --- |
| Stage4 protocol draft declared | 22:33:00.450222 | [Concrete config](../../configs/stage4_protocol.json), retaining declaration time |
| Allowed normal acquisition completed | 22:39:38 | [Acquisition](../../artifacts/stage4/pcb2_normals/normal_acquisition.json) |
| Inherited geometry preflight completed | 22:42:35.998312 | [Geometry preflight](../../artifacts/stage4/geometry_preflight/geometry_preflight.json) |
| Unchanged geometry approved | 22:43:54.352414 | [Normal geometry review](../../artifacts/stage4/geometry_preflight/normal_geometry_review.json) |
| Normal detector protocol frozen | 23:10:28.355272 | [Normal protocol](../../artifacts/stage4/normal_protocol.json) |
| All 109 tests passed | 23:18:25.893434 | [Test receipt](../../artifacts/stage4/tests_preflight.json) |

Acquisition fetched 1,001 official PCB2 normal image bodies only (901 official
training and 100 official test normals), totaling 247,481,451 selected payload
bytes. Its 1,210 exact 512-byte routing headers were read without prefetch/cache;
201 other regular member bodies were skipped. The receipt reports zero unallowed
payload bytes acquired in this new operation. This does not erase the historical
transport uncertainty recorded above. Header routing/official split filtering is
metadata access; anomaly body, mask and defect-annotation access remain deferred.

The [normal audit](../../artifacts/stage4/pcb2_normals/normal_audit.json) records
720 fitting and 181 calibration normals under seed 42 exact-SHA group allocation,
plus 100 official held-out normals. All 901 training normals decoded successfully
at 1,404×1,070. The held-out normal bytes were acquired/hashed, with decoding and
geometry/scoring deferred to final confirmation. No exact duplicate groups or
cross-category PCB1 image SHA matches were found among these normals. Normal
manifest SHA256 is `618cc7a6885c5622dc531542adc9bf1c128da2bb8a904aebce9c6a3c075709ed`.

Inherited geometry was run on fitting/calibration normals for suitability and quality
assessment, without category-specific tuning. All 901 had zero fallback and zero
board/crop source-boundary contacts. Both reviewers inspected the 17 fixed examples
on three sheets and retained the inherited parameters unchanged. This is normal-only
suitability evidence, not a claim that every unseen defect lies inside a future crop.

The normal protocol freezes code, environment dependency lock, weights, normal
inputs and geometry/config identities before bank selection and calibration. D1
is primary and D2 secondary. This is the preparation freeze, **not the final anomaly
access gate**: both banks/thresholds and independent normal reviews must still be
bound by a later final receipt before any confirmation unseal. The model agent/root
runs D1 then D2 normal preparation serially. This reviewer performs no CPU review
concurrently with latency measurements. No PCB2 anomaly result is available here.

## Normal preparation reviews, final freeze and logical unseal

All times in this table include UTC date. These events occur October 2 locally in
Vancouver even where the UTC date is October 3.

| Event | UTC timestamp | Receipt |
| --- | --- | --- |
| D1 normal preparation started | 2026-10-02 23:10:29.845312 | [D1 start](../../artifacts/stage4/pcb2_d1_primary/prepare_started.json) |
| D1 normal preparation completed | 2026-10-02 23:51:26.939009 | [D1 prepared](../../artifacts/stage4/pcb2_d1_primary/prepared.json) |
| D1 independent normal review passed | 2026-10-03 00:08:51.492926 | [D1 normal review](../../artifacts/stage4/pcb2_d1_primary/independent_normal_review.json) |
| D2 normal preparation started | 2026-10-03 00:09:10.533829 | [D2 start](../../artifacts/stage4/pcb2_d2_secondary/prepare_started.json) |
| D2 normal preparation completed | 2026-10-03 00:58:13.186577 | [D2 prepared](../../artifacts/stage4/pcb2_d2_secondary/prepared.json) |
| D2 independent normal review passed | 2026-10-03 01:00:54.706316 | [D2 normal review](../../artifacts/stage4/pcb2_d2_secondary/independent_normal_review.json) |
| Final confirmation freeze | 2026-10-03 01:01:20.600342 | [Final freeze](../../artifacts/stage4/freeze_receipt.json) |
| Final gate review passed | 2026-10-03 01:01:20.823258 | [Final gate review](../../artifacts/stage4/final_gate_review.json) |
| Shared logical anomaly-access claim | 2026-10-03 01:01:58.729924 | [Shared access](../../artifacts/stage4/anomaly_access.json) |

| Measured normal resource cost | D1 primary256 | D2 secondary512 |
| --- | ---: | ---: |
| Preparation timer, seconds | 207.135 | 652.335 |
| Projection, seconds | 38.938 | 84.868 |
| Selection, seconds | 30.083 | 140.286 |
| Reference re-extraction, seconds | 40.640 | 81.818 |
| Calibration, seconds | 96.591 | 344.121 |
| Peak process RSS, bytes | 1,153,318,912 | 2,935,586,816 |
| Median normal inference, seconds | 0.619 | 2.275 |
| p95 normal inference, seconds | 0.799 | 3.031 |

Costs come from [D1 runtime](../../artifacts/stage4/pcb2_d1_primary/normal_runtime.json)
and [D2 runtime](../../artifacts/stage4/pcb2_d2_secondary/normal_runtime.json). They
passed the implemented preparation timer <=1,800 seconds, RSS <=8 GiB and median
inference <=10 seconds gates. The UTC start-to-completion spans are about 2,457 and
2,943 seconds respectively, longer than the recorded preparation timer durations.
Do not describe these as under 30 minutes of calendar wall time. The receipts do
not establish why these spans differ; phase/timer measurements and event chronology
are both preserved. Cross-stage timings are observational and may reflect machine
state as well as recipe/data differences.

Both independent normal reviews checked all frozen/input/prerequisite identities,
exact-SHA group splits, normal calibration quantile ranks, every calibration map's
inverse coordinates, all 4096 unique fitting coordinates, five fixed re-extracted
vectors/projection values and an independent first-16 selection oracle. Full
4096-step selection was not independently rerun. Both reviews recorded held-out
normals not decoded and anomaly images/masks/types not accessed. Their reviewer
code SHA256 is `112920b1058963197292f18da037b06f1eb44658e4e5838f159f05b9e2ad4068`.

The final receipt binds both prepared banks/thresholds and normal reviews together
with configuration, normal splits, geometry, code/weights/dependency and environment
identities. Its SHA256 is
`a574ab907b9c871dbd55778fa5374b61c4c0d1bd988272e65819ddc4243a8d4d`.
The separate final gate checked tested/frozen code identity, passing normal reviews
and the absent access receipt before approving one primary then one secondary run.

The shared access claim is the conservative **logical unseal timestamp** before
network anomaly acquisition, decoding or scoring. Acquisition and first decode
receipts will refine actual analytic-access timing later; this entry does not read
raw test data. D1 remains primary and D2 secondary. No CPU reviews run concurrently
with confirmation latency measurements, and no recipes were changed after freeze.

## Shared materialization and reviewed primary result

After the logical unseal, the primary claimed its one evaluation at
2026-10-03 01:01:58.730162 UTC. The shared loader's
[materialization-start receipt](../../artifacts/stage4/confirmation_data/materialization_started.json)
records 01:01:58 UTC (second precision) and binds the same final freeze/access
identities. No finer first-byte/decode timestamp is recorded, so do not invent one.
The [test acquisition receipt](../../artifacts/stage4/confirmation_data/test_acquisition.json)
records 26,363,939 selected bytes, exact header routing without cache and no other
category payload acquisition. Test image/mask/annotation acquisition and decoding
were authorized only after that access claim.

The [test audit](../../artifacts/stage4/confirmation_data/test_audit.json) records
100 official held-out normals and 100 anomalies, all decoded; all anomalous masks
were positive and none disappeared entirely in the common256 view. No cross-PCB1
or fit/calibration exact-SHA duplicate matches and no exclusions were found.
Held-out normal decoding occurred only after final freeze/unseal. Scalar mask class
IDs were reduced to positive foreground under the frozen semantics; original class
and multi-label annotations remain available for descriptive slices. Normal geometry
was not readapted after access.

D1 primary completed at 2026-10-03 01:04:54.839360 UTC and its
[independent full review](../../artifacts/stage4/pcb2_d1_primary/independent_review.json)
passed at 01:06:23.063755 UTC. Completion SHA256 is
`7302c119c1771520d3b190a2ee891c3a02ae4a112e973bb365dae3285fcc62eb`.
Review checked all image flags/AP/AUROC/confusions, all 200 inverse maps, all 100
anomaly common APs, pooled full-denominator AP/IoU, hashes/timestamps and all 4096
fitting coordinates. Source-resolution arithmetic was checked on three fixed
anomalies, not independently recomputed for all 100.

Root reported D1 TP80/FN20 and FP5/TN95, image AP 0.96044/AUROC 0.9499, median
common anomaly pixel AP 0.32451, peak inside 44/100 and overlap 97/100. Median inference
was about 0.292 seconds. All four preregistered numerical project criteria passed,
including recall exactly at the 0.80 minimum. **Pooled pixel AP fell to 0.15339 and
thresholded IoU to 0.04744**, substantially below PCB1 D1 development results. These
supporting limitations remain part of the confirmation conclusion despite the
practical criterion pass. No annotated source pixels lay outside the observed crops;
that fact alone cannot explain or remedy weak pooled localization.

Root started predeclared D2 secondary after D1 completion/review. During secondary
inference this reviewer only read small receipts/audit metadata and updated this
ledger; no raw test image/mask inspection or CPU review was performed. D1 remains
primary. No threshold, geometry, selector, seed or memory changes were made.

## Reviewed secondary completion and final scope

D2 claimed its single predeclared secondary evaluation at 2026-10-03
01:07:03.296809 UTC, completed at 01:10:56.998181 UTC, and passed independent
full review at 01:11:42.939206 UTC. See [secondary access](../../artifacts/stage4/pcb2_d2_secondary/confirmation_access.json),
[completion](../../artifacts/stage4/pcb2_d2_secondary/complete.json) and
[review](../../artifacts/stage4/pcb2_d2_secondary/independent_review.json).
Completion SHA256 is
`e18a3b7caa50bad87d35df57b9aadadb5ed05ed4e1013466b936b3e67e9e96ac`.
The same frozen reviewer code checked full image/common metrics and inverse
coordinates, with the same disclosed three-anomaly source-resolution arithmetic
sample limitation. There was no new data unseal, primary reassignment or retuning.

Root reported these reviewed secondary outcomes:

| Endpoint | D2 PCB2 secondary |
| --- | ---: |
| TP / FN, 100 anomalies | 91 / 9 |
| FP / TN, 100 normals | 4 / 96 |
| Image AP / AUROC | 0.9770 / 0.9697 |
| Median anomalous common pixel AP | 0.4957 |
| Pooled common pixel AP | 0.2766 |
| Thresholded common pixel IoU | 0.07044 |
| Common peak-inside / overlap, 100 anomalies | 71 / 100 |
| Source median anomalous pixel AP | 0.4869 |
| Source peak inside, 100 anomalies | 66 |
| Median inference, seconds | 1.0757 |

The pooled denominator is all 200 images and all 13,107,200 common-view pixels;
per-anomaly medians and peak/overlap counts use 100 anomalies. Source maps use the
full original image, a distinct coordinate/denominator. D2 improved detection and
typical localization relative to the primary PCB2 result, while both pooled AP and
thresholded IoU remain markedly lower than their respective PCB1 development
recipes. This mixed result must remain visible beside passing D1 practical criteria.
The primary designation and criterion conclusions remain D1's.

Root's post-confirmation source-type analysis found D2 detected 13 of 19 images
with a source missing-component label; six of D2's nine missed images carried that
label. Median common pixel AP within that labeled group was about 0.2087, versus
0.0757 for D1. Source-type memberships may overlap and are descriptive, not mutually
exclusive root-cause categories. These observations motivate diagnosis; they do
not establish spatial matching, backbone choice or crop error as the cause.

Post-unseal work is confined to independently checking saved outputs, fixed-rule
qualitative review, source-type/size analysis, comparison figures and publication.
No detector threshold, crop, seed, projection, feature layers, backbone, memory size
or reference-matching rule changed. The project now has one primary confirmation
and one predeclared secondary confirmation, both reviewed, with historical transport
uncertainty and clock semantics explicitly disclosed. Fresh analytical category
confirmation of an adapted procedure is supported; zero-shot transfer, a causal
PCB2 coreset benefit and factory readiness are not established by this design.

**Next-stage recommendation only:** inspect saved maps and reference traces around
missing-component, small-defect and diffuse-localization failures before choosing
one controlled spatial-matching experiment or a backbone question. No Stage5
experiment or UI work was executed or authorized through this ledger entry. The
root agent owns final findings/journey/report publication and any subsequent
publication identities; no prior-stage frozen record is rewritten here.

## Post-confirmation publication review

After both complete reviews, this reviewer viewed all three fixed qualitative sheets
in `artifacts/stage4/comparison/figures` (18 selected examples), rather than raw images
or new model inference. The sheets include broad diffuse maps, normal false flags,
recipe disagreements and visibly reversed board poses. These observations inform
post-confirmation diagnosis only; no geometry, threshold or detector was changed.
The saved-count false-positive-pixel contribution analysis and pose association are
descriptive, not causal or frequency estimates.

The comparison findings, completed Stage4 journey chapter, journey index and one new
decision-log entry were written from reviewed artifacts. Earlier decision entries
remain verbatim; prior frozen snapshot artifacts and modules were not edited.
The final conclusion retains D1's practical point-criterion pass alongside severe
pooled localization limitations, clock discrepancy and historical transport caveat.
No Stage5 experiment, UI or additional detector fit/inference was run for publication.
Root owns final publication receipt/output hashes and notebook execution records.

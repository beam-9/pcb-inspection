# Stage4 plan review: fresh PCB2 category confirmation

Reviewed October 2, 2026 before any PCB2 anomaly access by this reviewer. The supplied
handoff is design input; the user's Stage4 authorization defines the work scope.
Prior frozen source, artifacts and journey documents remain unchanged.

## What the proposed experiment can establish

D1 is primary and D2 secondary before results. Both refit normal memory and calibrate
thresholds on PCB2 normals. This tests a frozen category-adaptation procedure on a
fresh category, not zero-shot use of PCB1 memory/thresholds and not factory transfer.
Normal-only geometry adaptation changes the procedure from literally unchanged
PCB1 preprocessing; report inherited behavior and the exact normal-driven change.

No PCB2 uniform-memory or direct-resize control is planned. Therefore a strong
absolute PCB2 result supports this complete procedure's usefulness on another VisA
category. It cannot isolate a transferable causal benefit of geometry or coreset
selection. D1 versus D2 remains a matched resolution comparison under fixed memory
count, which also changes sampling fraction. The handoff's historical statements
that detail was lost and geometry was a major bottleneck are plausible
interpretations; prior experiments measured improvements without establishing a
single original mechanism. Poor confirmation can identify an observed failure mode,
but alone cannot prove a backbone or spatial-memory cause.

## Decisions that must be explicit before unseal

1. Persist official fitting/calibration/held-out normal membership. Mirror the
   deterministic PCB1 80/20 split within official training normals if desired, and
   reserve official test normals for final FPR. Exact counts follow the official
   normal inventory; never derive partitions from anomalous performance. Use a
   fixed seed and stable ordering, and keep exact SHA256 duplicate groups together.
   Screen normal perceptual similarity as a heuristic only; aligned PCB photographs
   may look similar without representing the same physical board. Do not merge or
   exclude them without identity evidence.
2. Geometry development and resource selection should use training normals only.
   The handoff allows all normals, but using final held-out normals to optimize
   geometry makes final FPR partly development evidence. If this occurs, disclose
   it and do not call those normals untouched. Calibration normals should calibrate
   thresholds rather than tune alternative recipes repeatedly.
3. Audit cross-category exact SHA256 duplicates with exposed PCB1 and normal PCB2
   data before freeze. Fresh-category independence is not guaranteed by a category
   name. Normal perceptual similarity screening is descriptive, not an automatic
   physical-identity test. Anomaly identity audit waits until the declared access
   gate. A post-unseal cross-category exact match stops confirmatory status: preserve
   outputs, record incomplete/invalid fresh confirmation and disclose any later
   sensitivity analysis. Never discard duplicates silently to rescue confirmation.
4. Predeclare what constitutes acceptable geometry: conservative edge/connector
   retention, quantitative fallback/crop/padding diagnostics, deterministic extreme
   examples and fixed normal contact-sheet review. A content crop cannot prove
   unseen defects will be retained. When normal geometry is unsuitable, make one
   bounded documented adaptation; stop rather than expand into unbounded search.
5. Preserve all Stage3 detector settings, including padding eligibility, selection
   seeds and Gaussian 64-dimensional selection projection, 384-dimensional scoring,
   mean ten-anchor Euclidean initialization and tie/uniqueness semantics. Do not call
   this the exact author PatchCore recipe; see the frozen Stage3 method notes.
6. Bind geometry, final splits, code/environment/weights, selected banks, thresholds,
   inverse-map rules and independent normal-preflight review in the final freeze
   receipt. Distinguish a draft protocol freeze before preparation from the final
   anomaly-access gate after normal preparation. The latter must verify all required
   outputs and hashes and record anomalies/masks/types not accessed.
7. Declare each recipe's exclusive evaluation receipt before opening anomalies.
   Primary completes first, then secondary with its already frozen bank/thresholds.
   A crash may resume from the same immutable identity; any legitimate defect fix
   needs invalidation and a new identity, never overwrite or retuning.

## Endpoints and interpretation must precede outcome access

The primary project criterion, declared before outcomes, requires D1 recall >=0.80,
held-out normal FPR <=0.10, median anomalous common pixel AP >=0.25 and peak inside
annotation on >=0.40 of anomalous images, plus all resource/integrity gates. These
are practical project criteria, not a statistical hypothesis test, non-inferiority
margin, factory target or claim of category equivalence. Report each component
separately; a failed component must remain visible even if another improves.
D1 detection and normal review burden lead; image AP/AUROC are supporting outcomes.
D2 remains secondary regardless of performance. Record exact criteria in the final
protocol and do not revise them after access.

The 95th-quantile normal calibration policy is not a guarantee of <=5% held-out FPR.
Report numerator/denominator and uncertainty; do not claim statistically interchangeable
categories. D1 versus D2 and PCB1 versus PCB2 comparisons are descriptive rather than
post-outcome primary selection or proof of equivalence.

Retain full source-relative common256 views, including cropped-out areas scored
zero, and whole-image nearest-resized masks. Per-anomaly AP quartiles use anomalous
images only; pooled pixel AP/IoU include all images and pixels. Report the actual
positive-pixel denominator per category, source clipping fraction and empty-mask
handling. Cross-category AP depends on prevalence/difficulty; direct differences
are descriptive. Source-resolution metrics have a different denominator and must
be labeled supplemental. Never omit outside-crop annotation pixels to improve AP.

The primary size slices use the fixed PCB1 A2 common256 mask area-fraction edges;
call them fixed size bands, not PCB2 quartiles. Freeze exact values and edge/tie
semantics in the protocol. Supplementary PCB2 quartiles use a predeclared `higher`
quantile algorithm, inclusive/exclusive edge rules and empty/tied-bin reporting.
Common-view area means positive nearest-resized mask pixels divided by all
256×256 pixels. Source-original area fractions are supplemental and must not be
compared to common-view edges. Sizes and types remain sealed until final access. Defect types may overlap; report per-type
membership rather than adding overlapping counts. All slices are descriptive.

The agreed qualitative rules are fixed before interpretive viewing: up to two D1
TPs with lowest score margin, two FNs with highest margin, two FPs with highest score,
two smallest masks, two largest masks, one example per available source type closest
to that type's median area, two D1/D2 disagreements with lowest stable ID, one
annotation-overlap/peak-outside example and one peak-inside example. Break ties by
full image ID lexicographically; suppress duplicates in declared selection-reason
priority order; cap the union at 24 and report empty strata. Freeze the precise
reason priority, margins and median/area tie convention in the machine-readable
protocol. Compute selection only after frozen evaluation, before detailed viewing.
The sheet is a fixed diagnostic sample, not an unbiased estimate of failure prevalence.
Map display scale must be fixed (for example shared calibration-derived scale) or
independently normalized panels explicitly labeled.

## Independent review scope

Normal preflight must require fitting-only 4096 unique indices, valid coordinates,
finite banks/maps/thresholds, raw identity and split disjointness, deterministic
selection prefix/projection checks, five fixed re-extracted selected vectors,
independent calibration quantile ranks, map-coordinate synthetic fixtures, resource
gates and exclusive output paths. Do not score held-out normals before final access
unless this was deliberately frozen as an earlier diagnostic exposure.

After completion, independently recompute all image flags, confusion/AP/AUROC,
all anomalous common per-image APs, pooled full-denominator AP/IoU and inverse
mapping for every evaluated image. Preserve reviewer-code and completed-output hashes.
Use the same clearly disclosed source-resolution subset limitation as Stage3, or
expand checks prospectively; do not quietly weaken them. An exposure ledger is
an auditable record of authorized operations, not technical proof that arbitrary
filesystem access was impossible. Enforce gates in entry points and acquisition
allowlists, and report any accidental exposure immediately.

## Recommended execution decision

Proceed with normal-only acquisition/inventory and inherited-geometry suitability,
then bounded documented adaptation if required. Freeze the complete adapted procedure
and independent normal-preflight gate before confirmation. Do not add a PCB2 control
or alter primary designation opportunistically; any extra control requires a new
predeclared scope before unseal. Stage5 recommendation follows reviewed evidence;
strong Stage4 scores do not establish factory readiness or automatically authorize
UI/model upgrades.

## Sources reviewed

- [User-supplied Stage4 handoff](/Users/beam.t/Downloads/pcb_inspection_stage4_handoff.md).
- [Stage3 method notes](stage3_method_notes.md): exact inherited selector and departures.
- [Stage3 execution notes](stage3_execution_notes.md): normal gates and review limits.
- [Stage3 exposure ledger](stage3_exposure_ledger.md): prior chronology.
- [Original protocol](../protocol.json): calibration policy and decision scope.

No PCB2 anomaly images, masks, filenames or defect-type annotations were accessed
for this review. No detector experiments were run by this reviewer.

Handoff SHA256: `ac03c05e9f8fe2c19d2e16a5dfd8a9ed4b0b788ff886cf920f369b3ae24fe998`.

# Project decision log

This is an append-only narrative index of decisions. Entries for completed stages
are retrospective summaries linked to contemporaneous protocols and evidence;
they are not substitute preregistrations. New findings receive a new entry rather
than rewriting the rationale of an earlier decision.

## October1,2026 — Stage1: stop before the review application

**Decision:** stop/revise methodology after the frozen feasibility evaluation.

**Evidence:** Run1 `31e0704ff1da6906`: primary recall43/100, false alarms9/100;
image AP0.852/AUROC0.865; median anomaly pixel AP0.039; peak inside annotation26/100.
The original test was frozen before scoring, and the post-final supplemental
localization analysis is labeled retrospective. See [original findings](../pilot_findings.md)
and [exposure ledger](../exposure_ledger.md).

**Alternatives:** build a polished review UI immediately; lower a threshold using
test outcomes; switch models immediately.

**Reason:** valid provenance, useful ranking and fast inference did not compensate
for inconsistent localization and57 missed anomalies. Diagnose with saved evidence
before adding a workflow or promising inspection reliability.

**Uncertainty:** which combination of effective resolution, normal representation,
matching, normal variation and operating point limits this recipe. The result did
not establish that all57 misses were invisible to the representation.

## October2,2026 — A2: reuse saved PCB1 results for diagnosis

**Decision:** explicitly treat PCB1 as development after original result exposure;
reuse scores/maps with original thresholds and preserve Run1 artifacts.

**Evidence:** [A2 diagnostic summary](../../artifacts/pcb1_a2/diagnostic_summary.md)
and [A2 ledger](../development/a2_exposure_ledger.md) describe type/size variation,
per-image localization and retrospective operating-point tradeoffs.

**Alternatives:** rerun expensive inference without a changed question; describe an
A2 oracle threshold as independently selected; call a size association proof of
resize causality.

**Reason:** saved-output analysis identifies testable hypotheses while preserving
the distinction between original frozen evidence and retrospective development.

**Uncertainty:**9/100 test-normal flags alone do not establish a calibration defect
or distribution shift; reduced RGB detail and cross-location matching remain
hypotheses requiring controlled interventions.

## October2,2026 — Stage2: test geometry then effective resolution

**Decision:** implement a content-derived blue-board crop with conservative margins
and gray letterboxing, without introducing pose registration. Execute C1 at256,
then C2 at512 with the same4096 uniform bank policy and normal-only calibration.

**Evidence:** [geometry review](../../artifacts/pcb1_geometry/geometry_review.json)
preceded fitting; [execution ledger](../development/geometry_execution_ledger.md)
and [comparison findings](../../artifacts/pcb1_geometry_comparison/findings.md)
record resource gates and one development evaluation per recipe. C1 reached61%
recall/4% FPR; C2 reached70%/12%; median pixel AP0.097/0.354 respectively.

**Alternatives:** replace backbone/memory/scoring simultaneously; fit registration
without proving need; implement tiles and several image sizes at once.

**Reason:** the bounded geometry block made a useful comparison on the actual CPU
machine. Retain C1 as the less expensive lower-FPR reference and C2 as a localization
candidate for a matched memory-selection question.

**Uncertainty:** crop/aspect/padding and extra interpolation jointly define C1's
intervention. Fixed reference count samples a smaller fraction at512. C2's higher
median AP and lower pooled AP show uneven effects, not uniform improvement. This
does not establish factory generalization or the cause of the higher normal FPR.

## October2,2026 — Stage3: test representative memory before adding capacity

**Decision:** the user explicitly authorized Stage3. Prepare projected approximate
greedy selection of exactly4096 unique references from the complete fitting-normal
patch population, then run matched D1/D2 only if normal-only resource gates pass.
No PCB2 access or Stage4 intervention is authorized by this entry.

**Evidence available at decision:** [Stage3 proposal review](../development/stage3_plan_review.md)
and preserved C1/C2 show a plausible redundancy/coverage question. Reference fractions
0.5533% and0.1383% are sampling fractions, not measured feature-space coverage.
**New detector outcomes remain pending** at the time this entry is written.

**Alternatives:** increase memory count; replace ResNet18; add spatial restrictions;
exclude padding; tune a threshold against anomalies.

**Reason:** change reference selection while holding those alternatives fixed.
Record candidate ordering, projection/seed, initialization, tie semantics, selected
indices/order and full-dimensional reference identity before anomaly evaluation.
Measure normal-space nearest-reference coverage on fixed queries for both banks.

**Uncertainty:** farthest-first emphasis may help rare healthy modes or overemphasize
outliers; projected coverage need not imply original-feature coverage. Full-population
selection may exceed8GiB/30minutes. If reduced candidates become necessary, preserve
the failed feasibility evidence and declare a changed comparison before proceeding.
Do not silently fall back to uniform or claim a selection-only test after changing
the candidate population.

**Next entry condition:** append measured matched outcomes and one justified decision
after D1/D2 completion and independent review, or append a resource-stop decision if
the engineering gate prevents execution. Keep pending results out of earlier entries.

## October 2, 2026 — Stage 3 completed: carry D1 forward

**Decision:** retain representative 256 (D1) as the default development recipe.
Prepare a frozen category-adaptation and normal-geometry gate before any fresh PCB2
confirmation. PCB2 remains sealed; this entry does not execute the next stage.

**Evidence:** both independent reviews passed. C1→D1 improves recall 61%→89% at
unchanged 4% normal FPR; median anomaly pixel AP improves 0.097→0.353 at approximately
0.291 seconds median inference. C2→D2 improves recall 70%→95%, FPR 12%→11%, median
pixel AP 0.354→0.535. See [Stage 3 findings](../../artifacts/pcb1_memory_selection_comparison/findings.md).

**Alternatives:** D2 offers higher recall/localization but eleven normal flags and
roughly 3.7 times the processing cost. Uniform controls are preserved. More memory,
a new backbone, spatial matching, seed search and anomaly-tuned thresholds were
not tested or silently introduced.

**Reason:** D1 provides the better default balance of observed detection, review
burden and CPU cost. The comparison supports this selector on exposed PCB1; it does
not identify a single bottleneck or establish factory readiness. Normal coverage
mean/median worsened despite better tails, and D1 pixel IoU slightly regressed.

**Uncertainty:** D1 still misses eleven anomalies. Coverage/composition are descriptive;
physical board identities are unknown. Generalization and crop suitability require
fresh evidence under a frozen procedure. Preserve D2 as an alternative rather than
claiming that one recipe dominates every metric.

## October 2, 2026 — Stage4 completed: useful detection, diagnose localization

**Decision:** retain D1 as the predeclared primary and passing practical feasibility
result, while reporting mixed localization. Preserve D2's stronger secondary result.
Defer UI; recommend saved-map/reference diagnosis before selecting one controlled
spatial-matching intervention or a backbone question. No Stage5 experiment executed.

**Why confirmation now:** Stage3 supplied useful PCB1 development improvements, but
another PCB1 optimization would not answer fresh-category usefulness. D1 was primary
for lower burden/cost before PCB2 outcomes; D2 was secondary, never a fallback.

**Geometry and freeze:** 901 training normals passed inherited crop diagnostics;
17 fixed normal examples retained board/pins. No adaptation was needed. Both banks
and thresholds passed normal-only independent review. Final freeze was 2026-10-03
01:01:20.600342 UTC; logical unseal 01:01:58.729924. Primary then secondary evaluated
once, without changing thresholds, geometry, model or memory.

**Evidence:** D1 recall 80%, FPR 5%, median common anomaly AP 0.3245, peak-inside 44%
meet all four predeclared point criteria. D2 recall 91%, FPR 4%, median AP 0.4957,
peak-inside 71%. But pooled AP 0.1534/0.2766 and IoU 0.04744/0.07044 are markedly below
PCB1; missing/small defects remain difficult. Both reviews passed. See
[confirmation findings](../../artifacts/stage4/comparison/findings.md) and
[exposure ledger](../development/stage4_exposure_ledger.md).

**Reason:** useful image discrimination does not establish precise heatmaps. Diagnose
broad maps and source missing-component labels using saved evidence before committing
to spatial matching or a new representation. Some selected boards are physically
reversed; pose is a post-confirmation candidate explanation, not a tested cause.

**Uncertainty:** no PCB2 uniform/direct-resize control isolates causal transfer;
category-specific fitting/calibration is not zero-shot transfer. Historical incidental
archive transport cannot be ruled out, despite no discovered earlier analytical
PCB2 exposure. Preparation timer gates passed, but UTC calendar spans exceeded 30 minutes
and their discrepancy is unexplained. Source arithmetic was independently sampled
on three anomalies, and full 4096 selection was not rerun. Practical criteria are
point-estimate project criteria, not equivalence or factory guarantees. Any later
PCB2 tuning becomes post-confirmation development, with new identities.

## October 3, 2026 — Stage 5A recommends one orientation experiment

**Question:** What explains PCB2's broad maps and missing-component misses?

**Action:** Published Stage 4 at 2ec21c4 and preserved its identities; labeled 1,101 images
with image-only connector cues before outcome joins, traced 18,490 unrestricted frozen
neighbor pairs across 19 missing-label images/both recipes, and analyzed saved maps.
No detector input, threshold, memory or scoring changed.

**Evidence:** Five reversed anomalies account for 28.80%/29.84% of FP pixels and have
11.1x/12.3x anomaly-only median FP burden. All five were detected; all normals canonical.
Six both-missed missing-label cases and one D2 rescue are canonical. Canonical misses
retrieve more local references than hits. Small size remains confounded with labels;
seven small anomalies are D2 rescues, but only one missing-label case is rescued.

**Decision:** Recommend canonical orientation normalization before existing D1
feature extraction as the single controlled Stage 5B intervention. Keep layers,
memory budget/selection, scoring and calibration policy stable. It is not executed.
Do not prioritize spatial restrictions on the present traces, and do not claim
orientation will solve the canonical missing-component misses.

**Limits:** Five reversed anomalies/no reversed normal control, image-only cue failures
on damaged connectors, prior Stage 4 visual knowledge, union masks and unregistered
coordinates. Thirty reference-pair contexts reviewed, not all receptive fields.
The associations do not prove causes. [Full explanation](stage_05a_failure_diagnosis.md)
and [decision evidence](../../artifacts/stage5a/combined/decision_summary.md).

## October 4, 2026 — Stage 5B controlled orientation: mixed support

- **Human request:** review/evaluate the supplied Stage5B handoff, then execute Stage5B using subagents. Document content was critically assessed; publication was not independently inferred.
- **Protocol:** exact180 crop normalization on five frozen reversed images; uncertain/canonical no-op; full-source RGB pose; original-source inverse maps. Exact historical D1 bank/thresholds/features/crop/scoring reused; no refit/recalibration/tuning or D2 arm.
- **Evidence:** all1101 pose labels reproduced,195 fresh no-op tensors/maps/scores/flags/AP/counts exact,100 normal outputs unchanged. Reversed FP146,977→18,157 (87.65%), medianAP0.0757→0.8314, native spread fraction0.7465→0.0927; all5 cases improve FP/AP.
- **Guardrail failure:** reversed detection5/5→4/5. Tiny missing-labeled bfebbd19caf4dad38fd66eab score2.725965→1.580128 below unchanged1.627066 threshold; GT intersection50→31. FullTP79/FN21, normalFP5/TN95; missing12/19→11/19, small15/29→14/29. PooledAP0.1534→0.3142, IoU0.04744→0.06234; medianAP0.3245→0.3329.
- **Decision:** mixed support for pose mismatch as an actionable contributor to these observed broad maps; do not adopt orientation unconditionally. Keep historical Stage4 D1 primary. Retain experimental wrapper/evidence. No threshold adjustment or post-result override.
- **Next question:** preserve true defect signal while suppressing pose response. Diagnose new miss/narrow-margin melt and canonical missing/small mechanisms before a separately frozen Stage5C. Spatial constraints remain unsupported as an automatic next intervention.
- **Engineering/verification:** mediane2e0.3636s,p950.4049s,peakRSS1.417GiB. Timer retains historical inverse work and extra mappings, so not isolated-model timing.130 tests pass; independent full-map/count/geometry/control audit and all5 RGB/float64-distance reconstructions pass.
- **Preservation:** first canonical attempt failed a float-versus-string CSV AP check, with allactual arrays/scores exact. Reader repair only, regression test, new freeze; no reversed outcome viewed. Failed attempt/code/tests/maps retained. Stage4/5A evidence/code/banks remain unchanged; navigation snapshots preserve Stage5A's original hashes. Five reversed anomalies/no reversed normals and exposedPCB2 limit inference. Stage5C/UI/publication not executed.

[Chapter](stage_05b_orientation_normalization.md), [complete findings](../../artifacts/stage5b/findings.md), [review](../../artifacts/stage5b/independent_review.json), [completion](../../artifacts/stage5b/complete.json).

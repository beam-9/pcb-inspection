# PCB Inspection Project — Stage 6 Handoff
## Final Technical Phase Before Model v1.0 Freeze

**Stage type:** Final post-confirmation development stage  
**Purpose:** Diagnose the remaining canonical missing/small-defect failures, execute exactly one final controlled intervention, and decide whether the detector is ready to be frozen as **Model v1.0** for UI/productization.

---

# 1. Why Stage 6 exists

The project has already answered most of its major technical questions.

## Stage 1 — Feasibility
A direct 256 PatchCore-inspired pilot established that one-class anomaly detection could work at all.

## Stage 2 — Preserve PCB information
Cropping, aspect preservation and higher input resolution improved detection and localization.

## Stage 3 — Representative memory
Projected approximate-greedy reference selection substantially improved detection and localization at the same 4,096-reference budget.

## Stage 4 — Fresh PCB2 confirmation
The method transferred to a fresh PCB category:
- D1: 80/100 anomalies detected, 5/100 normal flags
- D2: 91/100 anomalies detected, 4/100 normal flags

Image-level discrimination transferred well, but localization became broader and less precise.

## Stage 5A — Failure diagnosis
The project identified:
- reversed pose as a strong contributor to broad anomaly maps
- missing-component failures as mostly canonical
- no strong evidence that distant normal-reference matching was the distinctive cause of canonical missing misses
- D2 as stronger on several small-defect cases

## Stage 5B — 256 orientation normalization
Exact 180° normalization dramatically reduced broad false-positive response on reversed boards, but one small missing-component case became a miss.

## Stage 5C — 512 orientation normalization
Applying the same orientation wrapper to historical D2:
- preserved **5/5 reversed detections**
- reduced reversed FP pixels **97,150 → 10,730**
- improved median reversed pixel AP **0.2739 → 0.8491**
- recovered the Stage 5B lost case
- preserved full D2 recall at **91/100**
- preserved normal FPR at **4/100**
- improved pooled pixel AP **0.2766 → 0.4449**
- improved IoU **0.07044 → 0.09328**

This is strong evidence that D2 + orientation is a viable high-sensitivity development candidate.

However, canonical missing/small defects remain unresolved.

Stage 6 is therefore the **final technical stage**.

Its job is not to chase perfect accuracy.

Its job is to answer:

> **What is the dominant remaining failure mechanism on canonical missing/small defects, and can one final controlled intervention improve it enough to justify freezing Model v1.0?**

---

# 2. Stage 6 structure

Stage 6 has two internal parts:

```text
Stage 6A — Final diagnosis
↓
Identify dominant remaining failure mechanism
↓
Decision gate
↓
Stage 6B — One final controlled intervention
↓
Final evaluation
↓
MODEL v1.0 FREEZE / NO-FREEZE DECISION
```

Do not start the UI before the Stage 6 freeze decision.

---

# 3. Stage 6A research question

## Primary question

> **Why do canonical missing-component and small-defect cases remain difficult even after pose mismatch has been controlled?**

The goal is to distinguish among:

1. weak local feature representation
2. insufficient spatial resolution
3. image-level aggregation weakness
4. threshold / operating-policy margin
5. competing high-score regions outside GT
6. mixed or unresolved mechanisms

Stage 6A is diagnostic only.

Do not modify the detector during 6A.

---

# 4. Stage 6A target cases

Use PCB2 post-confirmation development data.

Focus on:

## A. Canonical D2 missing-label misses

Identify the exact canonical D2 missing-label misses from frozen Stage 4/5 artifacts.

At minimum separate:

```text
canonical missing miss
canonical missing hit
```

Retain multi-label information.

Do not assume every `missing` source label corresponds to an isolated missing-component mask.

## B. Fixed R1/R2 small-defect failures

Use the existing fixed small-defect reference bands from prior stages.

Separate:

```text
small detected
small missed
```

and retain overlap with missing labels.

## C. Marginal Stage 5C rescued reversed case

Include:

`bfebbd19caf4dad38fd66eab`

as a comparison example.

Do not treat it as canonical.

Use it to ask:

> What does a marginal but recoverable defect signal look like compared with canonical misses?

---

# 5. Stage 6A must remain detector-neutral

Allowed:
- saved-map analysis
- frozen feature re-extraction
- nearest-neighbor tracing
- score decomposition
- patch ranking
- GT vs non-GT comparisons
- D1/D2 historical comparisons
- Stage 5B/5C supporting comparisons
- diagnostic tables/figures
- saved threshold-margin analysis

Not allowed:
- new backbone
- new bank
- threshold tuning
- aggregation changes
- new crop
- new resolution
- spatial restriction
- learned classifier
- retraining
- UI

---

# 6. Stage 6A analysis framework

For each target anomaly, calculate and save:

```text
image_id
source_labels
pose_label
mask_area
size_band

image_score
image_threshold
score_minus_threshold
score_divided_by_threshold
detected

max_native_patch_score
max_GT_patch_score
max_outside_GT_patch_score

GT_to_image_max_ratio
outside_to_image_max_ratio

common_pixel_ap
peak_inside
any_overlap
GT_max_common
outside_GT_max_common

FP_pixels
predicted_positive_pixels
GT_intersection_pixels
IoU

top_score_patch_location
top_score_patch_inside_GT
```

Use D2 as the main representation.

Use D1 only as historical/supporting comparison where useful.

---

# 7. Failure categories

Classify each target case into one or more evidence-based categories.

## F1 — Weak representation

Evidence pattern:
- GT-region patch scores are low
- GT max is far below image threshold
- outside-GT response is not the main reason for the miss
- D1 and D2 both weak in GT region

Interpretation:
> current ResNet18 feature representation may not encode the defect strongly enough

## F2 — Resolution-sensitive

Evidence pattern:
- D2 GT-region evidence is materially stronger than D1
- D2 may detect where D1 misses
- localization improves substantially at 512
- defect is spatially small

Interpretation:
> finer spatial representation is likely important

## F3 — Competing-response / aggregation failure

Evidence pattern:
- GT has meaningful anomaly evidence
- but highest patch/image score comes from outside GT
- top outside-GT responses dominate image scoring or map interpretation

Interpretation:
> max-patch aggregation may be over-sensitive to unrelated regions

## F4 — Threshold-margin failure

Evidence pattern:
- meaningful GT evidence exists
- image score is only slightly below threshold
- defect-region evidence is not obviously poor

Interpretation:
> operating policy / aggregation may be more important than feature representation

Do not change threshold in Stage 6A.

## F5 — Mixed / unresolved

Use this when evidence is genuinely ambiguous.

Do not force a clean explanation.

---

# 8. Case-level comparison table

Create:

`artifacts/stage6a/case_diagnosis.csv`

Columns:

```text
image_id
source_labels
pose_label
mask_area
size_band

d1_detected
d2_detected
d1_score_ratio
d2_score_ratio

d1_gt_max_ratio
d2_gt_max_ratio

d1_outside_gt_ratio
d2_outside_gt_ratio

d1_pixel_ap
d2_pixel_ap

d1_top_patch_inside_gt
d2_top_patch_inside_gt

failure_category
diagnostic_notes
```

If Stage 5C orientation-normalized D2 is applicable, use the normalized result as the current candidate representation.

Canonical images should reproduce historical D2 exactly.

---

# 9. Aggregation diagnosis

The current detector uses maximum patch anomaly score as image score.

Stage 6A should determine whether this rule is part of the remaining problem.

For each target image, inspect:

```text
top 1 patch score
top 3 mean
top 5 mean
top 10 mean
top percentile summary
GT-only max
outside-GT max
```

This is diagnostic only.

Do not use alternative aggregation to generate new detection decisions yet.

The purpose is to ask:

> Is the max-patch score selecting a meaningful defect patch or unrelated noise?

---

# 10. Patch-rank analysis

For each anomaly:

1. rank all native patch scores descending
2. identify which ranked patches overlap GT
3. save:
   - rank of first GT-overlap patch
   - fraction of top-5 overlapping GT
   - fraction of top-10 overlapping GT
   - fraction of top-20 overlapping GT

Create:

`artifacts/stage6a/patch_rank_diagnostics.csv`

Useful interpretation:

```text
GT patch rank = 1–3
→ detector sees defect strongly

GT patch rank = 20+
→ stronger unrelated responses dominate
```

---

# 11. Feature-distance diagnosis

For defect-overlap query patches calculate:

```text
nearest reference distance
median top-k reference distance
```

Compare:

```text
canonical missing misses
canonical missing hits
small misses
small hits
marginal Stage5C rescue
```

The goal is not to repeat Stage 5A's spatial displacement analysis.

The goal here is:

> Are failed defect patches genuinely close to normal in feature space?

If yes, that supports a representation problem.

---

# 12. D1 vs D2 representation comparison

For the same defect-overlap regions compare D1 vs D2:

```text
GT max / threshold
nearest-reference distance
pixel AP
GT patch rank
```

Interpret carefully.

D1 vs D2 is not pure resolution causality because their:
- thresholds differ
- candidate populations differ
- reference fractions differ

Use it as diagnostic context only.

---

# 13. Required Stage 6A figures

Generate at least:

1. **Failure-category summary**
2. **GT vs outside-GT score plot**
3. **Patch-rank distribution**
4. **Nearest-reference distance by outcome**
5. **D1 vs D2 defect-region evidence**
6. **Canonical missing miss contact sheet**
7. **Small-defect miss contact sheet**
8. **Marginal Stage 5C rescue comparison**

All qualitative figures must include failures, not only successes.

---

# 14. Stage 6A decision gate

At the end of diagnosis, recommend exactly **one** Stage 6B intervention.

Use this logic.

## Branch A — Representation weakness dominates

If most important misses show:
- low GT-region anomaly score
- low nearest-reference distance
- poor D1 and D2 GT evidence
- weak GT patch rank

Then Stage 6B should test:

> **stronger / more faithful PatchCore feature representation**

Recommended intervention:

```text
WideResNet50-style PatchCore backbone / feature extraction
```

Keep:
- crop
- orientation wrapper
- memory budget
- one-class setup
- evaluation framework

as stable as practical.

## Branch B — Aggregation weakness dominates

If:
- GT patches score meaningfully high
- GT patch ranks are reasonably strong
- image max is dominated by unrelated regions
- misses/marginal cases are mainly decision-level failures

Then Stage 6B should test:

> **one alternative image-level aggregation rule**

Example candidate:

```text
top-k patch aggregation
```

Do not simultaneously change backbone.

## Branch C — Resolution-sensitive behavior dominates

If:
- D2 repeatedly has much stronger GT evidence than D1
- canonical small failures still show resolution dependence
- D2 remains close to detecting missed cases

Then Stage 6B may test:

> **targeted higher-resolution / tiled representation**

Do not combine with new backbone.

## Branch D — No dominant mechanism

If evidence is mixed and no intervention is clearly supported:

> **Do not force Stage 6B.**

Instead freeze the current best candidate and document unresolved limitations.

A project can be complete without solving every failure.

---

# 15. Stage 6A definition of done

Stage 6A is complete when:

- [ ] all target canonical missing misses are identified
- [ ] small R1/R2 misses are included
- [ ] marginal Stage 5C rescued case included
- [ ] GT vs outside-GT evidence computed
- [ ] patch-rank analysis complete
- [ ] aggregation diagnostics complete
- [ ] feature-distance diagnostics complete
- [ ] D1/D2 context complete
- [ ] failure categories assigned
- [ ] ambiguity preserved where necessary
- [ ] exactly one Stage 6B intervention recommended, OR explicit freeze-now decision made
- [ ] no detector changes executed yet

---

# 16. Stage 6B purpose

Stage 6B is the **last allowed model experiment before v1.0 freeze**.

It must answer one question only:

> **Does the intervention selected by Stage 6A materially improve the dominant remaining failure mode without unacceptable regression?**

Do not run multiple candidate interventions.

---

# 17. Stage 6B experimental rules

Whatever intervention 6A selects:

Keep frozen as much as possible:
- PCB crop
- margins
- orientation normalization
- evaluation population
- GT masks
- one-class training protocol
- normal fitting/calibration split
- reporting metrics
- no post-result retuning

Predeclare:
- intervention
- baseline
- success metrics
- guardrails
- failure interpretation

before new result inspection.

---

# 18. Stage 6B baseline

The recommended current development candidate entering Stage 6 is:

> **D2 + orientation normalization**

Historical Stage 5C metrics:

```text
TP / FN                  91 / 9
FP / TN                   4 / 96
Image AP                  0.9766
AUROC                     0.9693
Median anomaly pixel AP   0.5101
Pooled pixel AP           0.4449
IoU                       0.09328
Peak inside               73 / 100
Any overlap               100 / 100
Total FP pixels           239,173
Missing-label detection   13 / 19
Fixed R1/R2 detection     21 / 29
```

This is the Stage 6B comparison baseline.

Do not overwrite it.

---

# 19. Stage 6B success criteria

Do not require every metric to improve.

The intervention should be judged primarily on the failure mechanism identified in 6A.

But require guardrails:

## Detection guardrails
- overall recall should not materially collapse
- normal FPR should not materially worsen
- image AP/AUROC should remain strong

## Localization guardrails
- pooled pixel AP should not regress materially
- IoU should not collapse
- broad-map FP burden should not reappear

## Targeted failure outcome
The specific target group from 6A should show:
- more detections and/or
- stronger GT-region evidence and/or
- better pixel AP / patch rank

depending on intervention.

---

# 20. Stage 6B must not chase one case

Do not optimize solely for:

`bfebbd19caf4dad38fd66eab`

or one canonical missing image.

The final intervention should target a **pattern**, not a single example.

---

# 21. Stage 6 artifact structure

Suggested:

```text
artifacts/
  stage6/
    diagnosis/
      case_diagnosis.csv
      patch_rank_diagnostics.csv
      feature_distance.csv
      aggregation_diagnostics.csv
      figures/

    experiment/
      protocol.json
      freeze_receipt.json
      baseline_identity.json
      results/
        full_metrics.json
        per_image_results.csv
        targeted_group.csv
        runtime.csv
      figures/
      independent_review.json
      complete.json
```

---

# 22. Stage 6 documentation chapter

Create:

`docs/journey/stage_06_final_model_selection.md`

Suggested structure:

# Stage 6 — Final model selection

## Why Stage 6 exists

## Stage 6A — Remaining failure diagnosis

### Canonical missing failures
### Small-defect failures
### GT vs outside-GT evidence
### Aggregation diagnosis
### Feature-distance diagnosis
### Failure categories

## Decision gate

State:
> We selected intervention X because evidence Y was strongest.

## Stage 6B — Final controlled intervention

### What changed
### What stayed frozen
### Baseline
### Results
### Regressions
### Engineering cost

## Final model decision

One of:

```text
FREEZE v1.0
```

or

```text
DO NOT FREEZE — blocking issue remains
```

## Final limitations

## Why further research is deferred

## Handoff to UI/productization

---

# 23. Final Model v1.0 freeze criteria

Model v1.0 can be frozen when:

- [ ] detector works on PCB1 development history
- [ ] detector has been confirmed on PCB2
- [ ] major pose failure was diagnosed
- [ ] pose intervention was validated
- [ ] high-resolution orientation candidate preserves detection
- [ ] remaining canonical failures are diagnosed
- [ ] one final evidence-driven intervention has been tested OR no justified intervention remains
- [ ] no severe regression is introduced
- [ ] exact final recipe is identified
- [ ] code/config/bank/thresholds are versioned
- [ ] limitations are documented
- [ ] no obvious high-value technical experiment remains before productization

The model does **not** need:
- 100% recall
- perfect segmentation
- zero false positives
- factory validation
- arbitrary-rotation guarantees
- every PCB category
- every backbone comparison

---

# 24. Formal freeze artifact

If Stage 6 ends successfully, create:

`artifacts/model_v1/final_model_receipt.json`

Record:

```text
model_name
version
freeze_timestamp
git_commit

preprocessing_identity
crop_identity
orientation_identity
input_resolution

backbone_identity
feature_layers
aggregation

memory_bank_identity
memory_size
selection_identity

image_threshold
pixel_threshold
threshold_semantics

evaluation_summary
runtime_summary
known_limitations

pcb1_status
pcb2_status

stage_history_links
```

Also save:

```text
artifacts/model_v1/
  final_model_receipt.json
  final_config.json
  final_bank_hash.txt
  final_metrics.json
  limitations.md
  reproducibility.md
```

---

# 25. Recommended naming

Example:

```text
PCB-AD-v1.0
```

or:

```text
pcb-inspection-v1.0
```

Do not call it:
- production-ready
- factory-ready
- validated industrial detector

unless future evidence supports those claims.

---

# 26. What "frozen" means after Stage 6

Once frozen:

Do not change for the v1.0 UI:
- crop
- pose handling
- resolution
- backbone
- bank
- thresholds
- scoring
- aggregation

The UI should call the frozen inference pipeline.

Future research becomes:

```text
v1.1
v2.0
experimental branch
```

not silent changes to v1.0.

---

# 27. After freeze: UI phase

Only after Stage 6 model freeze, begin the main UI/productization phase.

The UI should present two things:

## A. Usable inspection workflow

Example:

```text
upload PCB image
↓
preprocess
↓
orientation normalization
↓
anomaly inference
↓
image-level result
↓
heatmap
↓
review
```

## B. Engineering journey

Show:

```text
Stage 1
43% recall
↓
Stage 2
geometry/resolution
↓
Stage 3
representative memory
↓
Stage 4
fresh PCB2 confirmation
↓
Stage 5
failure diagnosis + pose correction
↓
Stage 6
final failure analysis + final model selection
↓
v1.0
```

This journey is a major portfolio asset.

---

# 28. Stage 6 execution order

## Phase 1 — Protect prior work
1. Verify Stage 5C outputs.
2. Snapshot current repository state.
3. Preserve historical D1/D2/Stage5 artifacts.
4. Create Stage 6 directories.

## Phase 2 — Stage 6A diagnosis
5. Identify canonical missing D2 misses.
6. Identify R1/R2 small misses.
7. Include marginal Stage5C rescue.
8. Compute GT/outside-GT evidence.
9. Compute patch ranks.
10. Compute aggregation diagnostics.
11. Compute feature-distance diagnostics.
12. Compare D1/D2 context.
13. Assign failure categories.
14. Generate figures.

## Phase 3 — Decision gate
15. Review evidence.
16. Select exactly one intervention.
17. Or explicitly decide current model is sufficient to freeze.

## Phase 4 — Freeze Stage 6B experiment
18. Define baseline.
19. Define intervention.
20. Define guardrails.
21. Create protocol.
22. Create freeze receipt.

## Phase 5 — Execute final experiment
23. Run exactly once under frozen recipe.
24. Save raw outputs.
25. Do not tune post-result.

## Phase 6 — Evaluate
26. Compute targeted metrics.
27. Compute full metrics.
28. Check regressions.
29. Measure runtime/resources.
30. Generate matched figures.

## Phase 7 — Independent validation
31. Recompute key metrics.
32. Validate identities.
33. Run full tests.
34. Verify prior artifacts unchanged.

## Phase 8 — Final freeze decision
35. Compare Stage 6B against Stage 5C baseline.
36. Decide freeze/no-freeze.
37. If freeze: create Model v1.0 receipt.
38. If no-freeze: document blocking issue.

## Phase 9 — Documentation
39. Write Stage 6 journey chapter.
40. Update project README/journey.
41. Append decision log.
42. Document final limitations.
43. Hand off frozen model to UI phase.

---

# 29. Stage 6 definition of done

Stage 6 is complete only when:

- [ ] Stage 5C history is preserved
- [ ] canonical missing misses analyzed
- [ ] small-defect misses analyzed
- [ ] GT vs outside-GT evidence computed
- [ ] patch-rank analysis complete
- [ ] feature-distance analysis complete
- [ ] aggregation diagnosis complete
- [ ] dominant failure mechanism identified or ambiguity documented
- [ ] exactly one final intervention selected OR freeze-now decision justified
- [ ] final experiment frozen before execution
- [ ] no post-result tuning occurred
- [ ] targeted metrics computed
- [ ] full metrics computed
- [ ] regressions documented
- [ ] independent review passes
- [ ] exact final recipe identified
- [ ] final limitations documented
- [ ] Model v1.0 freeze decision made
- [ ] final receipt created if frozen
- [ ] UI work has not yet changed the model
- [ ] project is ready to move into productization

---

# 30. Core principle

Stage 6 is not:

> "How much more performance can we squeeze out?"

It is:

> **"Do we understand the remaining failures well enough to make one final justified improvement, then stop?"**

The project should end technical development with a clear line:

```text
research
↓
evidence
↓
one final intervention
↓
final evaluation
↓
MODEL v1.0 FROZEN
↓
UI / demo / portfolio journey
```

The objective is not perfection.

The objective is a technically credible, reproducible, well-documented model that is good enough to productize and whose limitations are understood.

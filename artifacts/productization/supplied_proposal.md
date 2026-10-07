# PCB Inspection Project — Model v1.0 Freeze + UI/Journey Handoff

**Phase:** Productization and storytelling  
**Research status:** Stop current PCB2 tuning loop after Stage 6A  
**Model candidate to freeze:** D2 + canonical orientation normalization  
**Goal:** Build a portfolio-ready inspection demo that also explains the complete engineering journey and the reasoning behind stopping further refinement.

---

## 1. What happens now

The next sequence is:

```text
Formalize Model v1.0
↓
Freeze exact recipe
↓
Wrap frozen inference
↓
Build inspection UI
↓
Build interactive project journey
↓
Package for portfolio + interviews
```

This is **not another model-development stage**.

Stage 6A recommended Branch D: do not force a Stage 6B experiment because the remaining errors did not identify one clearly justified intervention.

---

## 2. Why development stops here

Stage 6A examined 36 target anomalies, including all canonical missing-label cases, all fixed R1/R2 small cases, and the marginal Stage 5C reversed rescue.

There were **9 distinct important misses**, all canonical.

Key evidence:

- 7/9 misses had their first GT-overlap patch ranked **#1**
- the other two GT ranks were **2** and **12**
- image scores were only about **0.63–8.26% below** the frozen D2 image threshold
- no miss required rank 20+ before the model reached the GT region
- missed GT patches were generally closer to the frozen normal bank than detected controls
- max-patch misranking did not explain the common false-negative pattern
- replacing max with a top-k mean at the same threshold cannot rescue a false negative because the mean cannot exceed the max
- D1→D2 improvement was useful but did not isolate resolution as the causal mechanism
- the evidence did not uniquely support a backbone, resolution, aggregation, or threshold-policy intervention

The most defensible interpretation is:

> **The remaining problem is limited anomaly-score separation near the operating threshold, but its root cause is not uniquely identified.**

Continuing to tune repeatedly on already-exposed PCB2 cases would increasingly risk optimizing to those specific misses rather than demonstrating better generalization.

Therefore:

> Freeze the current evidence-backed detector as v1.0 and move future model research into v1.1/v2.0.

---

## 3. Interview talking point — why I stopped

Short version:

> "I stopped refinement deliberately rather than chasing the last few errors. By the final diagnostic stage, most remaining misses were already ranking the annotated defect region correctly, but their anomaly scores were close to the frozen decision threshold. The diagnostics did not isolate whether the right next change was the backbone, resolution, aggregation, or operating policy. Since PCB2 had already become development data, continuing to tune against those same failures would increasingly risk overfitting. I froze the best evidence-backed model as v1.0, documented the limitations, and would evaluate the next major representation change on another untouched PCB category."

If asked why not immediately try a stronger backbone:

> "A stronger backbone is a plausible v1.1 experiment, but Stage 6A did not prove the backbone was the unique bottleneck. I wanted a defensible stopping rule rather than the highest number I could extract from an exposed benchmark."

If asked what comes next technically:

> "I would test a stronger, more faithful PatchCore-style representation as a new version, ideally on another untouched PCB category so I could distinguish real generalization from optimization to PCB2."

---

## 4. Freeze the final model before UI work

Recommended model name:

```text
PCB-AD-v1.0
```

Create:

```text
artifacts/model_v1/
  final_model_receipt.json
  final_config.json
  final_metrics.json
  final_bank_hash.txt
  limitations.md
  reproducibility.md
```

The UI must read model metadata from these frozen artifacts rather than duplicating values manually.

---

## 5. Exact Model v1.0 recipe

Freeze the Stage 5C D2 + orientation candidate.

### Preprocessing
- existing blue-board crop logic
- existing crop margins
- gray aspect-preserving letterbox
- input size: **512 × 512**

### Orientation
Use the exact frozen image-only rule:

```text
canonical     → no rotation
reversed_180  → exact 180° crop reversal
uncertain     → no rotation
```

No arbitrary-angle registration.

### Representation
- ResNet18
- aggregated `layer2` + `layer3`
- 384-dimensional local scoring representation

### Memory
- exact historical D2 normal memory bank
- 4,096 references
- preserve exact order and hash
- projected approximate-greedy selection history

### Scoring
- Euclidean nearest-reference distance
- image score = maximum patch anomaly score

### Frozen thresholds

```text
Image threshold = 2.060171127319336
Pixel threshold = 1.6943607330322266
Comparison semantics = strict >
```

Do not round these values inside inference code.

---

## 6. Final v1.0 reference metrics

Use Stage 5C as the final development-candidate result.

### Detection

```text
TP / FN        91 / 9
FP / TN         4 / 96
Recall          91%
Normal FPR       4%
Image AP       0.9766
AUROC          0.9693
```

### Localization

```text
Median anomaly pixel AP    0.5101
Pixel AP Q25 / Q75         0.3128 / 0.6779
Pooled pixel AP            0.4449
IoU                        0.09328
Peak inside                73 / 100
Any overlap                100 / 100
Total FP pixels            239,173
```

### Relevant subgroups

```text
Missing-label detection    13 / 19
Fixed R1/R2 detection      21 / 29
Reversed detection          5 / 5
```

Do not describe these as production guarantees.

---

## 7. Known limitations that must remain visible

Create a permanent v1.0 limitations section.

Include:

- PCB2 became exposed development data after Stage 4
- final candidate is not another fresh confirmation
- only five reversed anomalies were available
- no reversed PCB2 normal controls exist
- arbitrary rotations are unsupported
- canonical missing/small defects remain the primary known weakness
- annotations can be union masks across multiple defect types
- localization heatmaps are not precise segmentation
- heatmap intensity is not calibrated probability
- physical board identity is not fully controlled
- no factory robustness study was performed
- not certified for manufacturing decisions

---

# UI PRODUCT

## 8. Product goals

Build two equally important experiences.

### A. Inspection demo

```text
Upload PCB
↓
Run frozen v1.0
↓
Show anomaly decision
↓
Show score vs threshold
↓
Show orientation action
↓
Show anomaly heatmap
```

### B. Engineering journey

```text
Stage 1
↓
Question
↓
Experiment
↓
Evidence
↓
Decision
↓
Next question
...
↓
Model v1.0
```

The journey is a major part of the portfolio value.

---

## 9. Recommended routes

```text
/
├── /inspect
├── /journey
├── /journey/:stage
├── /model
└── /about
```

---

## 10. Landing page

The landing page should explain the project in ~20 seconds.

Suggested hero concept:

> **PCB Anomaly Detection**  
> A one-class visual inspection system developed through controlled experiments on geometry, memory selection, fresh-category transfer, pose sensitivity, and final failure analysis.

Primary CTAs:

```text
Run inspection
Explore the journey
```

### Summary metrics

Display:

```text
PCB2 recall              91%
Normal FPR                4%
Image AUROC             0.969
Pooled pixel AP         0.445
Input                   512×512
Reference memory        4,096 patches
```

Label clearly:

> Final PCB2 development-candidate evaluation

Do not say "production accuracy."

---

## 11. Landing visual

Prefer a real project example showing:

```text
Original PCB
→
Orientation normalization
→
Anomaly response
→
Review result
```

Use saved project assets, not a generic stock PCB if avoidable.

---

# INSPECTION PAGE

## 12. Upload experience

Support:

- drag/drop
- file picker
- image preview
- optional benchmark example selector

GT masks should only appear for benchmark examples that actually have annotations.

---

## 13. Result language

Use:

```text
Anomalous
No anomaly flagged
```

Avoid:

```text
Defective
Safe
Factory pass
```

because v1.0 is a research detector.

---

## 14. Score display

Show:

```text
Anomaly score
Frozen image threshold
```

Example:

```text
Score      2.31
Threshold  2.06
```

Never convert the score into fake confidence.

Do not display:

```text
94% confidence
```

---

## 15. Orientation result

Show:

```text
Pose:
Canonical / Reversed 180° / Uncertain

Normalization:
Applied / Not applied
```

For reversed inputs explain:

> The board was rotated into the detector's canonical reference orientation before feature extraction.

For uncertain inputs:

> Orientation cue was inconclusive; no rotation was applied.

---

## 16. Heatmap

Offer:

```text
Original
Overlay
Heatmap
```

Optional opacity control.

Label:

> **Anomaly response**

Tooltip:

> Brighter regions are less similar to the detector's normal reference memory. Response is not a calibrated defect probability.

Optional toggle:

```text
Show pixels above localization threshold
```

Add:

> Thresholded regions are diagnostic highlights, not precise segmentation.

---

## 17. Advanced model details

Collapsed by default.

Show:

```text
Model                 PCB-AD-v1.0
Input                 512
Backbone              ResNet18
Features              layer2 + layer3
Memory                4,096 references
Image threshold       2.06017
Pixel threshold       1.69436
Runtime               ...
Pose action           ...
```

---

## 18. Stable backend contract

Expose one stable inference function/API.

Conceptually:

```text
inspect(image)
→
{
  model_version,
  pose_label,
  normalization_applied,
  anomaly_score,
  image_threshold,
  is_anomalous,
  heatmap,
  thresholded_map,
  runtime
}
```

Frontend must not know internal inference implementation.

---

## 19. Model metadata source

Provide a model metadata endpoint or static loader:

```text
/model-info
```

Source from the v1.0 receipt/config.

Return:

```text
version
input_size
backbone
feature_layers
memory_size
thresholds
metrics
limitations
```

Do not duplicate frozen constants in frontend source files.

---

# JOURNEY PAGE

## 20. Journey design

This should be the signature portfolio page.

Each stage should use the same structure:

```text
Question
↓
What changed
↓
Evidence
↓
What we learned
↓
Next question
```

The page must feel causal, not like a list of random experiments.

---

## 21. Critical dataset boundary

Do **not** show one simple line chart implying:

```text
43% → 61% → 89% → 91%
```

came from one unchanged test set.

Visually separate:

```text
PCB1 DEVELOPMENT
Stages 1–3
```

from:

```text
PCB2 FRESH CONFIRMATION
Stage 4
```

and:

```text
PCB2 POST-CONFIRMATION DEVELOPMENT
Stages 5–6
```

Insert a clear divider before Stage 4:

> **New untouched PCB category introduced**

This is essential for credibility.

---

## 22. Stage 1 — Feasibility

### Question
Can normal-reference anomaly detection detect PCB defects at all?

### Setup
- direct resize 256
- ResNet18 layer2/layer3
- 4,096 uniform references
- PatchCore-inspired local nearest-neighbor scoring

### Result

```text
Recall                   43%
Normal FPR                9%
Image AP                0.852
AUROC                   0.865
Median pixel AP         0.039
```

### Learning
The detector had useful signal, but direct resize lost local detail and localization was extremely weak.

### Next
Can preserving board geometry and resolution help?

---

## 23. Stage 2 — Geometry and resolution

Compare:

```text
Direct 256
Crop 256
Crop 512
```

### Crop 256

```text
Recall                   61%
FPR                       4%
Median pixel AP          0.097
```

### Crop 512

```text
Recall                   70%
FPR                      12%
Median pixel AP          0.354
```

### Learning
Geometry preservation mattered. Higher resolution greatly improved localization, but cost more compute and increased FPR.

### Next
Is the normal reference memory now the bottleneck?

---

## 24. Stage 3 — Representative memory

Compare uniform selection vs approximate-greedy representative selection at the same 4,096-reference budget.

### D1 — 256

```text
Recall                   89%
FPR                       4%
Image AP                0.968
Median pixel AP         0.353
```

### D2 — 512

```text
Recall                   95%
FPR                      11%
Image AP                0.976
Median pixel AP         0.535
```

### Learning
Reference selection was a major bottleneck.

### Next
Does the frozen recipe transfer to another PCB category?

---

## 25. Stage 4 — Fresh PCB2 confirmation

Make the fresh-data boundary prominent.

### D1

```text
Recall                   80%
FPR                       5%
Image AP                0.960
Median pixel AP         0.325
Pooled pixel AP         0.153
IoU                     0.047
```

### D2

```text
Recall                   91%
FPR                       4%
Image AP                0.977
Median pixel AP         0.496
Pooled pixel AP         0.277
IoU                     0.070
```

### Learning
Image-level detection transferred strongly, but localization became much broader and less precise.

### Next
Why are maps broad, and why are missing/small defects difficult?

---

## 26. Stage 5A — Failure diagnosis

This was diagnosis, not optimization.

Show three findings.

### Pose
Five reversed anomalies contributed roughly:

```text
29–30%
```

of all FP pixels in both D1 and D2.

### Missing components
Misses did not retrieve more distant normal references than hits. This weakened the proposed cross-location-matching hypothesis.

### Small defects
D2 showed stronger evidence than D1 on multiple small cases.

### Decision
Test canonical orientation normalization first.

---

## 27. Stage 5B — Orientation normalization at 256

Feature a before/after map.

### Result

```text
Reversed FP pixels
146,977 → 18,157
```

```text
Reduction
87.65%
```

```text
Median reversed pixel AP
0.0757 → 0.8314
```

But:

```text
Reversed detections
5/5 → 4/5
```

### Learning
Pose mismatch was an actionable broad-map problem, but removing it exposed weak real defect signal in one small missing-component case.

### Next
Can 512 retain the cleanup without losing that defect?

---

## 28. Stage 5C — Orientation normalization at 512

This is one of the strongest journey visuals.

### Result

```text
Reversed FP pixels
97,150 → 10,730
```

```text
Reduction
88.96%
```

```text
Median reversed pixel AP
0.2739 → 0.8491
```

```text
Reversed detections
5/5 → 5/5
```

Overall:

```text
Recall                   91%
Normal FPR                4%
Pooled pixel AP          0.445
IoU                      0.093
```

### Learning
The 512 recipe preserved defect signal while canonical orientation normalization removed most of the pose-induced broad response.

### Next
Why do canonical missing/small defects remain difficult?

---

## 29. Stage 6A — Final diagnosis and stopping rule

This stage is about engineering judgment, not another metric increase.

### Findings

```text
9 distinct important misses
all canonical
```

```text
7/9 first GT-overlap patch rank = 1
remaining ranks = 2 and 12
```

```text
Image-score margin below threshold:
approximately 0.63–8.26%
```

Missed defect patches were generally closer to normal references than detected controls.

However:

- no dominant backbone failure was isolated
- no dominant resolution mechanism was isolated
- max-patch misranking did not explain the false negatives
- no calibrated aggregation alternative was justified by the evidence

### Decision

> **Stop tuning PCB2. Freeze D2 + orientation as v1.0.**

---

## 30. Final v1.0 timeline card

Display:

```text
PCB-AD-v1.0

512 input
ResNet18
layer2 + layer3
4,096 reference patches
canonical orientation normalization

PCB2 recall              91%
Normal FPR                4%
AUROC                   0.969
Pooled pixel AP         0.445
```

CTA:

```text
Try the model
View model card
```

---

## 31. Stage detail pages

Each `/journey/:stage` page should contain:

1. Question
2. Why this followed from prior evidence
3. Experimental setup
4. What was held constant
5. Metrics
6. Figures
7. Interpretation
8. What the evidence does **not** prove
9. Decision
10. Next question

This makes the entire project easy to discuss in interviews.

---

# MODEL CARD

## 32. `/model` page

Show architecture:

```text
Input image
↓
Board crop
↓
Pose classification
↓
Optional exact 180° normalization
↓
512 letterbox
↓
ResNet18 layer2/layer3
↓
Local embeddings
↓
Distance to normal reference memory
↓
Image anomaly score + localization map
```

Sections:

- frozen recipe
- thresholds
- final evaluation
- intended use
- known limitations
- future work
- reproducibility/version

---

## 33. Intended use

Use wording like:

> Research and portfolio demonstration of one-class visual anomaly detection for PCB inspection.

Not intended for:

> Certified manufacturing pass/fail decisions.

---

# METHODOLOGY / ABOUT

## 34. Explain one-class anomaly detection simply

Suggested explanation:

> Instead of training a classifier on every possible defect, the system builds a memory of normal PCB features. A new PCB is compared against that normal memory. Regions whose features differ strongly from known normal examples receive a higher anomaly response.

Diagram:

```text
Normal PCBs
↓
feature extraction
↓
normal reference memory

New PCB
↓
feature extraction
↓
distance to reference memory
↓
anomaly score + heatmap
```

---

# STORYTELLING RULES

## 35. Always explain why the next stage happened

Bad:

```text
Then I tried 512.
Then I tried coreset selection.
Then I rotated images.
```

Good:

```text
Direct resize destroyed localization.
↓
Test geometry preservation.

Geometry helped.
↓
Reference memory became the suspected bottleneck.

Representative memory improved PCB1.
↓
Freeze and test a fresh PCB category.

Detection transferred but maps broadened.
↓
Diagnose pose and missing failures.

Pose dominated false-positive maps.
↓
Test orientation normalization.
```

This causal chain is the core portfolio story.

---

## 36. Heatmap language

Always call it:

```text
Anomaly response
```

Do not call it:

```text
Defect probability
```

For normalized displays explain the scale.

Do not auto-stretch each comparison independently if that would make weak and strong maps visually equivalent.

---

## 37. Journey metric rules

Allowed:

```text
Stage 2 vs Stage 3 on PCB1
```

because they are development comparisons.

Allowed:

```text
Historical D2 vs orientation D2 on fixed PCB2
```

because this is a matched intervention.

Be careful with:

```text
Stage 3 95% vs Stage 4 91%
```

because Stage 4 is a new PCB category.

Label the dataset boundary.

---

# README / PORTFOLIO

## 38. README structure

Recommended:

```text
Problem
Final system
Key result
Demo
Engineering journey
Method
Evaluation
Limitations
Reproducibility
Future work
```

Do not begin with a long chronological log.

---

## 39. Suggested README opening

Concept:

> PCB-AD is a one-class visual anomaly detection project for PCB inspection. The final v1.0 system combines representative normal-patch memory, 512-resolution local features, and deterministic orientation normalization. The project was developed through staged experiments that isolated geometry, memory quality, fresh-category transfer, pose sensitivity, and remaining failure mechanisms rather than changing multiple variables at once.

---

# STRUCTURED CONTENT

## 40. Journey data

Create something like:

```text
content/journey.json
```

Each stage should contain:

```json
{
  "id": "stage-5c",
  "title": "Orientation normalization at 512",
  "datasetPhase": "PCB2 post-confirmation development",
  "question": "...",
  "change": "...",
  "result": "...",
  "learning": "...",
  "nextQuestion": "...",
  "metrics": {},
  "figures": [],
  "sources": []
}
```

Prefer data-driven rendering over copying metrics into multiple components.

---

## 41. Preserve source references

For every major claim keep internal fields such as:

```text
source_report
source_table
source_figure
```

This prevents UI copy drifting away from the original research.

---

# DEMO EXAMPLES

## 42. Example gallery

Include:

- canonical normal
- obvious anomaly
- missing-component example
- small subtle anomaly
- reversed-orientation anomaly
- at least one difficult/known limitation case

Do not curate only easy successes.

---

# ACCESSIBILITY / UX

## 43. Handle these states

```text
idle
uploading
processing
result
error
unsupported image
pose uncertain
```

Processing copy can say:

```text
Preparing image
Checking orientation
Extracting features
Comparing with normal memory
Building anomaly map
```

---

## 44. Accessibility

Ensure:

- keyboard-accessible controls
- readable contrast
- status not communicated by color alone
- alt text for research figures
- responsive timeline
- mobile-friendly image/heatmap tabs

---

# VALIDATION

## 45. Productization tests

Add tests for:

```text
final model receipt loads
final config matches receipt
bank hash matches
frozen thresholds match

inspection API returns required fields
score/threshold decision is consistent
reversed pose applies exact 180°
uncertain pose remains no-op

model-info matches receipt
journey schema validates
journey stage metrics match source data
every stage has dataset-phase label
```

---

## 46. Smoke-test manifest

Create:

```text
tests/model_v1_smoke_manifest.json
```

Include representative:

```text
canonical normal
canonical anomaly
reversed anomaly
uncertain-pose case
subtle missing/small case
```

Use this to ensure future UI/backend work does not silently change the frozen detector.

---

# EXECUTION ORDER

## Phase 0 — Formal freeze

1. Identify exact Stage 5C D2+orientation artifacts.
2. Bind exact code commit.
3. Hash the memory bank.
4. Save exact thresholds/config.
5. Save final metrics.
6. Write limitations.
7. Create final model receipt.
8. Create smoke-test manifest.
9. Tag/commit v1.0.

## Phase 1 — Content layer

10. Build journey data file.
11. Populate all stage metrics from source artifacts.
12. Add PCB1/PCB2 phase labels.
13. Select figures.
14. Write model card.
15. Write "Why stop here?" section.

## Phase 2 — Backend

16. Wrap frozen `inspect()` pipeline.
17. Create model-info metadata.
18. Ensure frontend contains no duplicated model constants.
19. Add smoke tests.

## Phase 3 — Inspection UI

20. Upload flow.
21. Preview.
22. Processing state.
23. Result/status.
24. Score vs threshold.
25. Pose action.
26. Heatmap/overlay.
27. Advanced details.
28. Error/uncertain states.

## Phase 4 — Journey UI

29. Build timeline.
30. Add explicit fresh-PCB2 boundary.
31. Add stage cards.
32. Add stage detail pages.
33. Add before/after comparisons.
34. Add Stage 6 stopping-rule presentation.
35. Add final v1.0 node.

## Phase 5 — Model/About

36. Model card.
37. Methodology diagram.
38. Limitations.
39. Future work.
40. Interview-friendly summary.

## Phase 6 — Polish

41. Responsive design.
42. Accessibility.
43. Visual scale review.
44. Copy review.
45. Overclaim audit.

## Phase 7 — Final validation

46. Run v1.0 smoke tests.
47. Verify all journey metrics.
48. Verify historical artifacts unchanged.
49. Verify final UI uses frozen model receipt.
50. Capture portfolio screenshots/demo video.

---

# DEFINITION OF DONE

## Frozen model

- [ ] Model v1.0 receipt created
- [ ] final config created
- [ ] bank hash recorded
- [ ] thresholds frozen
- [ ] limitations documented
- [ ] smoke tests pass

## Inspection demo

- [ ] upload works
- [ ] frozen inference works
- [ ] pose state shown
- [ ] image result shown
- [ ] anomaly score shown
- [ ] threshold shown
- [ ] heatmap/overlay shown
- [ ] runtime shown
- [ ] error/uncertain states work

## Journey

- [ ] Stage 1 through Stage 6A represented
- [ ] PCB1/PCB2 boundary explicit
- [ ] each stage has question/change/result/learning/next
- [ ] Stage 5 pose story visualized
- [ ] Stage 6 stopping rationale explained
- [ ] final v1.0 node shown
- [ ] all claims source-backed

## Portfolio credibility

- [ ] known limitations visible
- [ ] heatmaps not called probabilities
- [ ] no factory-ready language
- [ ] no fake confidence percentages
- [ ] stopping rationale interview-ready
- [ ] future research separated from v1.0

---

# Final message the project should communicate

The strongest project story is **not**:

> "I built a model with 91% recall."

It is:

> "I started with a weak anomaly detector, isolated its failure modes through controlled experiments, validated transfer to a new PCB category, diagnosed an unexpected pose failure, corrected it without hiding the trade-offs, and deliberately stopped tuning when the remaining exposed-data errors no longer supported one clearly justified intervention."

That is what the UI and portfolio should make obvious.

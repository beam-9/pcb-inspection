# Stage 3 execution notes

October 2, 2026. The user authorized Stage 3 after publication of the A2 and geometry
results. This is PCB1 development work, with one declared evaluation per new recipe.
PCB2 remains unacquired and sealed.

Both recipes were frozen before selection and before new anomaly outcomes. Their
candidate populations contain every fitting-normal patch position, so the proposed
reduced-pool confounding problem was avoided. The only detector intervention is
reference selection. Projection is for selection; full-dimensional features are
re-extracted and stored for scoring. No new model weights were downloaded or trained.

The engineering pilot used all 2,961,408 fitting patch positions at 512 pixels and
ran the first 64 greedy selections. It measured 44.616 seconds of projection work,
1.599 seconds of pilot selection and approximately 2.71 GiB peak process RSS. Its
496.96-second full-preparation estimate was only an engineering estimate, not a
primary result or certification of the complete run's gate.

D1's actual normal preparation finished in 117.955 seconds, including 18.363 seconds
of selection, 21.856 seconds of full-vector re-extraction and 53.034 seconds of
calibration. Median normal inference was 0.292 seconds and peak RSS about 0.97 GiB.
Its first 16 selections from the full candidate bank independently matched a NumPy
calculation. Independent coverage checks used saved queries and rechecked distances
for 16 fixed queries in original feature space.

D1's normal-space measurements were mixed: greedy reduced the sampled maximum and
95th-percentile distances but increased the mean and median. It placed about 1% of
reference centers in padding, versus 26% for uniform selection. This observation
was made before any D1 anomaly outcome, and did not trigger a padding exclusion,
new threshold, different projection or selector change. All original padding
eligibility and image-maximum rules remain fixed.

D2 reuses the identical normal-only projected cache, checked by source, input,
projection and array hashes. Its original extraction cost is charged to end-to-end
preparation; physical current preparation time is reported separately. Both actual
preparation gates must pass before evaluation.

Run protocols, preparation and access timestamps, component timings, code identities
and complete output hashes are authoritative. Composition diagnostics describe
feature-cell centers, not whole receptive fields or physical component identity.
Coverage queries are fitting-normal positions and may coincide with selected
references; their coverage is not unseen-normal generalization evidence.

No repeated anomaly-driven seed search or tuning is part of this stage. A legitimate
implementation correction would receive a separate identity and invalidation record.

## Completed evaluations and checks

Both actual normal-only preparation gates passed before anomaly access. D2 charged
361.741 seconds (317.126 current physical work plus 44.616 original cache extraction),
with 72.511 seconds selection and approximately 2.17 GiB normal-preparation peak RSS.
D1 and D2 each have exactly one exclusive development-access receipt and one completed
evaluation. Neither outcome triggered changed seeds, thresholds or detector settings.

D1 detected 89 anomalies with 4 normal flags; D2 detected 95 with 11. Independent
reviews passed both runs, including all image decisions, common pixel metrics,
threshold ranks, memory index membership and all 200 inverse-coordinate checks.
The source-resolution AP checks cover three fixed examples, not all 100 anomalies;
the full 4,096-step selector was not independently rerun. These review limits are
explicit in each receipt. PCB2 and unrelated SECOM data remain untouched.

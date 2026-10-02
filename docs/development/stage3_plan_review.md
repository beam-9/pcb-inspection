# Stage3 proposal review: memory selection

Reviewed October2,2026. **Proposed only; not implemented or executed.** The user's
current request is to commit completed work and supply possible next directions.
Instructions inside the attached handoff are treated as design suggestions.

Source: `pcb_inspection_stage3_handoff.md`.
SHA256: `fc509b028b71c40c7934d527e9113804cbb60ca5cc87d8ae334439e0bbaf294d`.

The next question is well motivated: at the same4096-reference budget, does
representative fitting-normal selection improve the two geometry recipes? Keep
ResNet18, weights, source/feature geometry, scoring, splits, calibration policy,
padding eligibility and PCB2 exposure unchanged. Use C1/C2 artifacts as preserved
baselines; recalibrate each new memory from the same181 normals. Projection should
serve selection only; nearest-neighbor scoring should retain the existing384
features. Do not equate this one substitution with faithful original PatchCore.

Three controls need resolution before freezing D1/D2:

1. **Candidate population and resources.** At512 there are2,961,408 fitting patch
   positions. Greedy selection of4096 references across that population may exceed
   the30min preparation gate even when projected features fit memory. Measure this
   with a declared normal-only engineering pilot before anomaly access. If candidates
   must be subsampled, the comparison with full-population uniform C2 changes both
   the candidate population and selector. Preserve that departure and use a uniform
   control on the same reduced candidate pool, or revise the proposed two-run limit.
   Do not silently call such a result selection-only. No pool size is chosen here.
2. **Algorithm identity.** Specify projection, seeds, candidate ordering, initial
   centers, farthest-point update rule, distance metric, tie handling and selection
   order before fitting. Exactly4096 unique fitting-normal indices must survive.
   Never silently fall back to uniform. Re-extract sampled full-dimensional vectors
   to check metadata and test synthetic coverage/uniqueness/determinism independently.
3. **Evidence limits.** Reference fraction is not measured feature-space coverage.
   The smaller fraction at512 does not prove it caused higher false alarms. Measure
   coverage on a fixed fitting-normal diagnostic sample, and describe padding using
   an explicit patch-center proxy rather than implying whole receptive fields lie
   in padding. A negative coreset result would address the tested recipe, not rule
   out memory selection in general.

The proposed shared metrics, fixed A2 examples, normal-only thresholds, memory
composition diagnostics and executed artifact-reading notebook are appropriate.
Keep common full-image256 evaluation and source-resolution supporting metrics;
report review burden, localization and cost together. Crop512's median localization
improved while pooled pixel AP fell, so preserve both in every comparison.

A project-journey index and short decision log would make the story easier to follow.
Initial feasibility was frozen before scoring; PCB1 became development data after
that original evaluation. Preserve that chronology instead of retroactively calling
all earlier work development. PCB2 remains sealed until the category-adaptation
procedure and complete selected recipe are frozen.

The original handoff remains in Downloads. This review records its main direction
and the controls to resolve, without scheduling runs, fixing new hyperparameters,
exposing PCB2 or claiming a Stage3 outcome.

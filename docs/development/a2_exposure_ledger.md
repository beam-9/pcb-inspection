# A2 development exposure ledger

Recorded 2026-10-02. The original pilot was already unsealed before this review.
PCB1 is development data for all further work; these diagnostics cannot provide a
fresh estimate of a revised method's generalization.

A2 inspected the existing scores of 100 anomalous and 100 normal test images,
181 calibration normals, all 100 saved anomaly maps and resized source masks,
owner defect labels (110 memberships across 100 anomalous images), and the 200
saved maximum-score patch traces. 11 systematically selected examples were
rendered from existing images and maps; exact IDs and selection reasons are in
`artifacts/pcb1_a2/qualitative/selection.csv`.

No detector inference, refitting, new memory, operational threshold selection or
PCB2 acquisition/exposure occurred. ROC thresholds are retrospective diagnostic
oracles and must not become the next experiment's calibration policy. The original
protocol, scores, final-access gate and completion record were preserved.

The attached next-steps document was reviewed as a proposal. Scope was recorded
before A2 processing in `a2_scope.json`; analysis inputs and outputs are hashed in
A2 metadata, trace manifest and completion record. Changes are a local development
snapshot based on published commit 75e4758; the original protocol remains the
identity for the original model code.

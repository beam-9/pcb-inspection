# Development and exposure ledger

2026-10-01 America/Vancouver. Scope: one PCB1 Phase A pilot.

- Source CSV metadata counts were read for source/protocol decisions.
- Hardware smoke: `artifacts/smoke.json` records three official training normals,
  backbone/cache identity, two repeat scoring calls and actual runtime. It is one
  hardware smoke, not an anomaly development experiment. Membership may later fall
  into fitting or calibration; no learned transformation from this smoke is retained.
- Acquisition/audit structurally reads image headers, decoded pixel arrays, exact
  hashes, similarity hashes on training normals, masks and geometry. This includes
  test metadata and mask integrity/counts. No test image views, detector scores or
  failure inspections occur during development. `first_model_test_access_utc`
  consequently means first final model-scoring access, not first structural decode.
- Synthetic unit tests use random features/untrained weights, not held-out examples.
- `docs/protocol.json` is created once after source/data/weight checks and smoke,
  before normal fitting. It binds source, manifest, model/code/tests and preprocessing.
- Normal preparation runs create an exclusive protocol-identified directory.
  The initial implementation uses one preparation run unless an invalidation is
  explicitly recorded here; no hyperparameter search is performed.
- `artifacts/test_access.json` is the exclusive final-access receipt for both frozen
  methods. It is saved before model scoring/mask metric evaluation and cannot be
  overwritten silently. `final_complete.json` and independent `verification.json`
  record completed artifacts and recomputation; retrospective charts come afterward.

No final-test-driven recipe changes or threshold tuning are permitted. Any correction
requires identifying the demonstrated bug, affected artifacts and reason for rerun.

## Completed execution receipts

- Frozen 2026-10-02T05:33:38UTC (2026-10-01 Vancouver), protocol SHA256
  `31e0704ff1da6906cc45fb420b21ade4bf473fcb6388ea05bb1cf9eda9e3bd2d`.
- One normal preparation run`31e0704ff1da6906`;72.49s, no debug reruns.
- One final evaluation each for baseline and primary, completed without invalidation.
  Metrics and completion hashes are immutable in the run directory.
- Independent verification recomputed arithmetic for all saved test outputs and
  independently feature-scored three lexicographically selected test IDs solely to
  validate trace correspondence, without fitting or changing any setting.
- Post-final localization consistency check inspected all 100 anomaly masks/maps;
  it added descriptive per-image AP and peak/overlap counts after the pooled metric
  exposed the need to assess consistency. It did not replace predeclared metrics,
  choose thresholds or trigger another model recipe. Code/data saved under notebooks
  and artifacts/review. Retrospective visual inspection followed completed scoring.
- Notebook initially could not start because sandbox blocked local Jupyter sockets;
  it was executed with approved local-kernel access. No benchmark evaluation rerun.

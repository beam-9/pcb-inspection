# Stage 6A proposal review

The human request authorizes Stage6A review and implementation. The supplied final-model proposal also describes Stage6B, model receipts and UI; those are context and are outside this implementation.

Accept the detector-neutral diagnosis with these clarifications, declared before new outputs:

- Main representation is frozen D2+Stage5C orientation. Supporting D1 uses its frozen Stage5B wrapper for aligned pose context. Canonical images must exactly match historical maps and scores. Include every canonical missing-label case and every fixed R1/R2 case, with hit controls; additionally include the fixed reversed rescue.
- Source annotations are union masks; no component-specific semantics inferred for multi-label cases. Common256 mask area defines historical size bands. Native patch overlap is any positive in the nearest-resized union-mask 8x8 footprint, not a receptive field. Rotate source crop before projecting a reversed mask; leave GT source files untouched.
- Image score is native maximum across all patches, including padding. Interpolated map maxima cannot substitute for native patch scores. Source coordinates, ranks, overlap counts and common metrics have explicit separate denominators.
- F3 cannot explain a false negative under max scoring: outside response can only increase the score. It describes localization competition on hits. A top-k mean is bounded above by max; rescuing misses would require independently calibrated operating policy in a future experiment. No alternative decisions or tuned thresholds here.
- Operational F1–F4 flags are declared in protocol; residual cases use F5. These thresholds are descriptive conventions, not validated mechanisms. Low normal-neighbor distances alone do not prove feature inadequacy; hits and misses provide image-weighted context. D1/D2 banks, thresholds and populations differ, so F2 is sensitivity context, not resolution causality.
- Use all4096 frozen references and top5 distance summaries. Save every GT-overlap query and per-image distributions; do not treat patches as independent images. A systematic bounded float64 computation checks distances separately.
- Preserve original namespaces, receipts and caches. Snapshot navigation before edits. Freeze Stage6A inputs/code before extraction; refuse overwrites. Review all required figure types and run meaningful geometry/rank/category tests plus full suite.

Deliver Stage6A artifacts under `artifacts/stage6a/`, an artifact-reading notebook, research figures and a Stage6 journey chapter with a pending Stage6B/freeze boundary. Recommend one future intervention only if supported; do not execute it.

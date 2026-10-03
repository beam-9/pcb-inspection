# Stage 4 preservation verification

The preservation audit passed without unresolved mismatches. It performed hash-only reads; it did not infer, refit, recalibrate, or decode images. No prior receipt, artifact, frozen source, test, or configuration was edited by this audit, and no Git commit was created.

The reference Stage3 snapshot is `120b2bf997426c37e2a3505c3dba514b0b2aa399`. All **275 tracked pre-Stage4 files** under `artifacts/`, `src/`, `tests/`, `configs/`, and `data/manifests/` match that Git snapshot byte for byte. The new Stage4 files are separate additions.

Receipt verification passed **1,968 working-tree hash comparisons across 1,695 distinct paths**, plus two historical snapshot resolutions. Repeated paths occur because several receipts bind the same prerequisite. Coverage includes the original protocol, Run1 model/calibration prerequisites and all 200 final maps; A2 outputs/code; both geometry recipes' frozen protocols, preparation prerequisites and completed outputs; both coreset recipes' equivalent evidence; and both comparison completion receipts.

| Receipt scope | Working-tree hash checks |
| --- | ---: |
| Original Run1 completion | 3 |
| Original Run1 maps | 200 |
| Original Run1 prerequisites | 6 |
| Original frozen protocol | 33 |
| geometry_256_v1 frozen protocol | 40 |
| geometry_256_v1 prepared prerequisites | 6 |
| geometry_256_v1 completed outputs | 216 |
| geometry_512_v1 frozen protocol | 40 |
| geometry_512_v1 prepared prerequisites | 6 |
| geometry_512_v1 completed outputs | 216 |
| coreset_256_v1 frozen protocol | 56 |
| coreset_256_v1 prepared prerequisites | 14 |
| coreset_256_v1 completed outputs | 425 |
| coreset_512_v1 frozen protocol | 58 |
| coreset_512_v1 prepared prerequisites | 14 |
| coreset_512_v1 completed outputs | 425 |
| A2 completion | 54 |
| Geometry comparison | 32 |
| Stage3 comparison | 122 |
| Geometry run receipt identity | 2 |

Historical documentation is verified against the snapshot that its receipt actually binds. An evolving project README or journey index does not invalidate an unchanged historical experiment. The A2 README's bound hash resolves at `f08ab0874d77ab493d0793662c27c0d215df644d`; its current content has evolved. The Stage3 documentation identities below all resolve at `120b2bf997426c37e2a3505c3dba514b0b2aa399`. Later Stage4 navigation edits should be interpreted against this historical snapshot, rather than silently rewriting the old receipt.

| Evolving documentation | Historical SHA256 | Verification |
| --- | --- | --- |
| `README.md` | `3827d8eb623985a85e74e87bf92bc2e28769605504fbdf1c613b1a288ed7463e` | Historical Stage3 receipt matches; current file has evolved at verification. |
| `docs/journey/README.md` | `d9432b8d0cde8d7c251f3e908e86bdd5bbd843e971fed341e7d0dfee6dd254c3` | Historical Stage3 receipt matches; current file matches at verification. |
| `docs/journey/decision_log.md` | `065ee20a377ba362198c474b6e6084232a409ad078e8d8660b76bdd7fbb2189c` | Historical Stage3 receipt matches; current file matches at verification. |

The old registry `artifacts/stage3_experiment_registry.csv` and old `artifacts/experiment_registry.csv` remain unchanged. Stage4 has a separate `artifacts/stage4/experiment_registry.csv`, with two rows derived from the saved D1 primary and predeclared D2 secondary metrics, preparation metadata, final freeze/shared unseal receipts, and independent reviews. It records the normal-only gates, 720 fitting and 181 calibration normals, 200 heldout test images, full candidate populations, selection-only projection, strict thresholds, results, resource measurements, and exact evidence hashes. D2 is not promoted to primary after its outcome.

The working tree contains local raw images, checkpoint, reference arrays, calibration arrays and individual maps that are intentionally ignored by Git. Their preservation was checked where completion/provenance receipts bind them; this audit does not claim that Git alone contains those payloads, or that every unbound raw/cache file was exhaustively inventoried. The exact-size selective acquisition and earlier incidental transport exposure caveat are documented separately in `docs/development/stage4_exposure_ledger.md`. No historical zero-byte transport claim is inferred from preservation.

Preparation timing is qualified in the new registry. D1 measured `perf_counter` preparation is 207.134684 seconds but its saved UTC start-to-completion span is 2,457.093697 seconds; D2 measured preparation is recorded from its runtime receipt while its UTC span is 2,942.652748 seconds. The normal-only resource gate passed the frozen measured-clock rule. Both UTC spans exceed the 1,800-second cap, so the registry does not present that gate as proof of ordinary end-to-end preparation within 30 minutes. The source of the clock discrepancy remains unresolved.

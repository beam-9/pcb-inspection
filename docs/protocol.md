# Frozen PCB1 Phase A protocol

See `protocol.json` for timestamp and immutable content identities. All fitting is on official training normals after seed-42 normal-only calibration separation. The official final test is preserved. Both recipes and thresholds are fixed before final scoring.

CPU ResNet18 layer2/layer3 frozen ImageNet features; direct 256-square resize, no crop. Primary: 4096 seeded uniform normal patches, exact Euclidean nearest neighbor, maximum patch score, bilinear raw maps without smoothing or normalization. This departs from PatchCore coreset and weighting. Baseline: global pooling of the same aggregated features, L2 normalization, nearest normal.

Image threshold: normal calibration 95th percentile, NumPy higher; flag strictly greater. Pixel overlap threshold: normal calibration map 99th percentile, higher and strictly greater. Pixel AP pools all 200 test images at 256-square geometry; this may discard small source defects. No confidence interval claims or factory operating requirements.

At most three normal implementation runs; one final evaluation each. Bug-correction reruns require explicit invalidation and ledger record. Final outputs refuse silent overwrite.

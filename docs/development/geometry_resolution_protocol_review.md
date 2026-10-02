# Controlled board-detail experiment

Started 2026-10-02. This is a PCB1 development comparison following A2, not fresh
confirmation. PCB2 remains unacquired and sealed. Subagents were dispatched but hit
an account usage limit before saving work; the primary agent completed implementation.

The intervention is deliberately small: find the largest connected blue region,
add conservative margins around the board, and preserve crop aspect ratio with gray
letterbox padding. Test this block at 256 pixels (C1), then at 512 pixels (C2).
The normal-only audit and visual review are saved under `artifacts/pcb1_geometry`.
The exact color thresholds and margin rules are frozen in each run protocol.

This is a category-specific crop for VisA PCB1, not a universal board detector.
The rule uses image content without masks or source defect labels. It was designed
from fitting normals and audited on fitting/calibration normals. The blue component
can change when a defect changes board color; fallbacks and annotation exclusion
are therefore reported. Any invalid blue component falls back to the entire image;
no examples are excluded. Pose and 180-degree orientation remain unchanged.
Normal sample review supports connector containment only in the inspected images.
No landmark residual, registration accuracy or universal containment is claimed.

## What stays fixed

ResNet18 ImageNet V1 weights; layer2/layer3 with 3x3 average aggregation; no training;
723 fitting and 181 calibration normals; 4096 global uniform patches without
replacement, seed42; exact Euclidean nearest neighbors; maximum patch image score;
no Gaussian smoothing. A numerical test establishes that the dynamic extractor at
256 is exactly equal to the original extractor with identical weights and inputs.
At 512, its feature grid is64x64 rather than32x32.

Sample global indices before extracting features, then gather only those features
while streaming four images at a time. This is the original uniform sampling
policy, not approximate greedy selection. A fixed4096 bank covers about0.553% of
256 fitting patches and0.138% at512. The changed coverage limits a pure resolution
interpretation. No full raw fitting feature bank is materialized.

## Coordinate and threshold rules

Crop bounds use exclusive right/bottom edges. Resized content dimensions are rounded
once and centered in the square; all bounds and padding are recorded per image.
Input-grid maps are bilinear-interpolated, stripped of letterbox padding, resized
back to the source crop, and pasted into the original source extent. Outside-crop
scores are zero. That convention preserves the full-image denominator and penalizes
missed cropped-out annotations; it is not evidence those regions are normal.
All image patches, including letterbox boundaries, contribute to the image maximum.

For comparison with Run1, inverse source maps are resized to a common256-square view.
Ground-truth masks are independently nearest-resized from the original source to
that same view. The map path has two interpolation stages whereas Run1 has one;
record this as part of the geometry block. Do not call C1 a crop-only causal estimate.
Masks are never cropped to discard unobserved ground truth. Report excluded source
annotation fractions, source-resolution per-image localization and common256 metrics.
Fullsource pooled pixel AP is omitted to bound memory; pooled common256 AP includes
all100 normal and100 anomalous images. Source metrics are supporting views, not
identical to the original256 metrics.

Calibrate image95th and common-map99th normal quantiles using NumPy higher and strict
`>` exactly as before. A2's retrospective oracle is never used. The pixel policy
includes all full-image common pixels, including inverse-mapped zeros, so it can
shift with crop size. Compare thresholds in the context of this denominator.

## Gates and provenance

Freeze code, tests, inputs, weights, geometry audit and review before fitting. Hash
check every raw input image against its manifest; check masks before source metrics.
Save exclusive preparation and evaluation-start records. Each recipe has one declared
PCB1 development evaluation and refuses reuse of an existing access record.
The first five calibration normals serve as a smoke with the actual4096 bank.
Continue only below8GiB peak RSS and10s median inference. Preparation must stay below
30min and peak memory is checked throughout. Full calibration rechecks resource gates
before opening development images. Report measured times instead of analytical claims.
Peak RSS is the macOS process high-water value in bytes, not total device memory.

Independent review checks identities, exact normal quantile ranks, every image
flag/confusion count, independent image AP/AUROC, common256 per-image localization,
sampled memory indices/membership and three re-extracted bank vectors. Source metrics
are explicitly not independently recomputed in that receipt. Original frozen Run1
identities are checked throughout; new modules leave the original implementation intact.

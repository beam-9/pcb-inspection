# A2-first improvement feasibility

Prepared 2026-10-02. This is a proposed bounded development sequence, not a tested
replacement model. Run 1 remains unchanged. No PCB2 images, new weights, or new
detector inference were used for this note.

## What saved traces can establish

Run 1 saved the maximum-score query patch and its nearest normal reference for
every test image. `trace_offsets.csv` reports their row/column offsets and
Chebyshev-window membership; `trace_by_outcome.csv` separates TP/FN/FP/TN. These
coordinates are in each original unregistered feature grid. Large offsets can
arise from repeated board structure, 180-degree orientation differences or shifts,
not only inappropriate matches. They therefore cannot establish that global
matching caused a miss.

The maximum-score patch is not necessarily an annotated defect patch. To evaluate
the actual defect-matching hypothesis, additional diagnostic queries are warranted
if A2 supports structural or small-defect weakness: preregister a deterministic
sample across FN type/size strata, include matched TP/normal controls, extract
the original frozen features only for those samples, and retain nearest references
for annotation-intersecting grid cells. Use masks solely for retrospective query
selection. Inspect full reference/context images as well as patches. Keep this
diagnostic inference separate from Run 1 and do not infer a correct spatial radius
before registration. This extra diagnostic has not been executed.

## Feature geometry and analytical resource budget

The existing hardware record is 16 GiB unified RAM, CPU inference; Run 1 imposed
8 GiB peak RSS and 10 seconds median inference as its engineering budget. New
development caps must be logged before running, rather than inherited implicitly.

The official torchvision definitions give layer2/layer3 outputs of 128/256
channels for ResNet18 and 512/1024 for WideResNet50_2. WideResNet widens internal
bottleneck channels; its output feature channels follow bottleneck expansion.
Layer2 stride is 8 and layer3 stride is 16. After layer3 upsampling, a 512-square
input has a 64×64 patch grid. The following arithmetic assumes raw concatenated
float32 channels and all 723 fitting normals, without dimensional pooling.
These are derived storage/search counts, not measured memory or runtime.
[Official torchvision source](https://docs.pytorch.org/vision/stable/_modules/torchvision/models/resnet.html).

Total candidate patches = 723×64×64 = 2,961,408. A crop letterboxed to 512-square
keeps this grid count; excluding padding changes eligible counts and must be
declared. Rectangular inputs or tiles require new arithmetic.

| Candidate at 512 | Channels | Full feature bank GiB | 5% bank patches / GiB | 10% bank patches / GiB |
|---|---:|---:|---:|---:|
| ResNet18 raw layer2+3 | 384 | 4.236 | 148,070 / 0.212 | 296,140 / 0.424 |
| WideResNet50_2 raw layer2+3 | 1,536 | 16.945 | 148,070 / 0.847 | 296,140 / 1.695 |

Formula: feature bytes = patches×channels×4; bank sizes use floor(fraction×patches).
These exclude weights, activations, allocator/cache overhead, temporary copies,
distance arrays and coreset workspaces. A complete WideResNet raw feature bank
exceeds physical RAM even before overhead, so eager in-memory construction is
not viable here. A disk memmap alone does not make a sampler safe if it converts,
projects or copies the full bank into RAM.

Exact search for one 64×64 query image performs 606,494,720 query/reference
comparisons at 5%, or 1,212,989,440 at 10%. Multiplying by channels gives
232.9/465.8 billion channel comparisons for ResNet18 and 931.6/1,863.2 billion for
WideResNet raw features. These are work estimates, not CPU latency predictions.
At query chunks of 256, the distance matrix alone is 144.6/289.2 MiB. Chunking
both query and memory can bound workspace while preserving exact minima.

Approximate greedy coreset avoids a full candidate-by-candidate distance matrix,
but still updates distances from every candidate per selected center. At these
fractions that is approximately 438.5/877.0 billion candidate-center updates,
before projected-dimension cost. Projection to 128 channels alone occupies
about 1.41 GiB. This selection workload is the stronger feasibility concern,
even when the final memory fits.
[Author sampler implementation](https://github.com/amazon-science/patchcore-inspection/blob/main/src/patchcore/sampler.py).

The author recipe also includes dimension pooling, so raw 1,536-dimensional
concatenation is not automatically its final embedding. Before any faithful
candidate, pin a source revision and declare pooling dimensions, patchification,
distance units, neighbor count, image aggregation and Gaussian smoothing. The
paper specification and author code must be distinguished: author FAISS outputs
squared L2 distances and its mean-neighbor image scoring is not the pilot's
direct Euclidean max-only path. Recalibrate new scores from normals; numerical
thresholds are not transferable across definitions.
[Author common implementation](https://github.com/amazon-science/patchcore-inspection/blob/main/src/patchcore/common.py).

## Crop and registration prerequisites

First inspect a deterministic normal-only sample spanning pose/background variation.
Start with color/contour board segmentation plus an explicit margin only if the
sample supports it. White components, shadows, edge connectors and threshold
instability can confuse segmentation. Save source bounding boxes and rejection
reasons, and retain source-to-crop transforms. A failed crop must fail loudly or
use a documented fallback; it must not silently trim a suspicious edge.

Preserve aspect ratio using declared padding and interpolation, including valid
board/padding regions. Registration must resolve 180-degree ambiguity from normal
landmarks and report reprojection/residual errors. Repeated components can produce
plausible but incorrect correspondences; a homography may distort detail or be
underconstrained. Fixed landmark templates must come from fitting normals only.
Validate inverse map transforms with synthetic landmarks and visually inspect a
normal contact sheet before testing spatial restrictions.

After freezing the content-based crop rule, PCB1 development masks may be used
retrospectively to measure retained defect area, especially edge defects. They
must never choose a per-image crop, alignment, input pixels or confirmation
threshold. Record source-resolution and resized mask area to test detail loss;
the A2 small-defect correlation alone does not prove resize causality.

## Bounded candidate sequence

1. Geometry-only prerequisite: persist and validate normal-derived crop/registration
   transforms without changing the detector. Accept/reject geometry using declared
   normal alignment checks and retrospective PCB1 retention checks; log all failures.
2. C1 geometry isolation: fixed ResNet18, 256 input, original aggregation, uniform
   4,096 memory and scoring, but apply verified crop/registration/aspect preservation.
   This tests geometry as one explicitly logged change group. Calibrate new normals.
3. C2 resolution isolation: same C1 preprocessing/ResNet/scoring/memory policy at
   512. Keep memory capped at 4,096 so the resolution comparison does not secretly
   introduce a 36-fold bank expansion. This remains PatchCore-inspired. Measure
   setup, peak RSS, p50/p95 and normal score behavior before anomaly evaluation.
4. Only then compare a pinned approximate greedy sampler with a predeclared cap;
   capped 4,096 at 512 is 0.1383%, and 16,384 is 0.5532%, not a 5–10% coreset.
   A cap must be reported as the actual fraction and justified by measured resources.
   A subsampled candidate pool followed by greedy selection is a further departure.
5. A WideResNet candidate follows a separate normal-only resource smoke and an
   explicit feature-streaming/projected-coreset implementation. Do not combine
   backbone, pooling, neighbor weighting and smoothing into an untracked change.

For proposed next experiments, retain the 8 GiB/10-second engineering caps unless
explicitly revised before results; impose a declared setup-time cap as well. Keep
two candidate configurations initially (C1/C2), save immutable IDs and calibrate
normal-only. This sequence is proposed and has not been executed. PCB2 stays sealed
until the selected complete recipe and confirmation protocol are frozen.

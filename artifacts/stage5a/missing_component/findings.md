# Missing-label frozen-reference tracing — post-confirmation diagnosis

All 19 PCB2 images carrying the source `missing` label were traced against both
unchanged Stage4 banks. There are six both-missed images, one D2 rescue and twelve
both-hit images; no D1-only hit. All seven D1 misses are canonical. Four reversed
and three uncertain cases occur among the both-hit group. Uncertain is retained
separately: those labels describe an ambiguous connector cue, not a reversed pose.

## What was measured

The original source union mask is cropped using the saved crop box, nearest-resized
into its exact letterboxed content dimensions, and placed at the saved padding
origin. Every feature-grid cell containing a positive mask pixel is queried, along
with an eight-connected one-cell context ring excluding those overlap cells.
An 8×8 input-space cell is a geometric footprint, **not** the ResNet receptive field.
Two images have multi-type union annotations; their traced positive pixels cannot
be attributed solely to the missing component.

For all 3,698 overlap/ring cells, the top five references are taken from the entire
frozen 4,096-vector bank in the original 384-dimensional Euclidean feature space:
18,490 query/reference pairs. Exact float32 ties use ascending frozen bank index;
nearest tie counts are retained. No spatial restriction, orientation correction,
threshold adjustment, refitting or scoring change was applied.

Both query and reference feature, model and source coordinates are saved. Spatial
displacement uses normalized **crop-content** coordinates, divided by the crop
coordinate diagonal √2. The declared local radii are 0.05, 0.10 and 0.20; 0.10 is
shown as the descriptive cross-location fraction. Padding centers remain labeled,
and their crop-normalized coordinates can fall outside [0,1]. Coordinates are
unregistered: distance alone does not determine anatomical correspondence.

## Result: distant matching does not distinguish the canonical misses

Image-weighted medians of per-image defect-overlap/top-five summaries:

| Canonical group | Images | D1 median displacement | D1 fraction beyond 0.10 | D2 median displacement | D2 fraction beyond 0.10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Both miss | 6 | 0.0090 | 0.000 | 0.0253 | 0.092 |
| D2 rescue | 1 | 0.0026 | 0.000 | 0.0175 | 0.105 |
| Both hit | 5 | 0.0228 | 0.003 | 0.0311 | 0.260 |

Canonical misses have **more local**, rather than more distant, retrieved normal
references in this sample. Canonical both-miss median embedding distances are also
lower than canonical both-hit distances: D1 1.472 versus 1.819; D2 1.903 versus 2.268.
The single rescue cannot establish a resolution mechanism by itself.

Reversed both-hit cases have substantially larger displacement/cross-location
fractions: D1 0.0907/0.444; D2 0.1673/0.617. Uncertain both-hit cases also show larger
fractions, but must not be pooled with reversed cases. These patterns limit an
unqualified cross-location interpretation. This trace analysis does not prove that
pose caused any error, nor does it test a spatially constrained detector.

## Conservative visual reference-context check

All 19 images have a trace sheet at each resolution. The displayed query is the
mask-overlap cell center nearest the original union-mask centroid, with feature ID
tie breaks. This is a geometric selection, not the highest anomaly response.
Each sheet shows the source image, union annotation, frozen map, query context,
and five full-source normal contexts with exact reference-center markers.

For an explicit bounded semantic review, the lowest full image ID in each actual
outcome group was selected at each resolution: three cases × two resolutions ×
five neighbors = **30 pair views**. Separate sheets show each full normal source
and a three-cell-wide local context. A visible package body centered at the marker
is labeled `component`; visible unpopulated blue substrate is `empty_board`;
package boundaries, intercomponent gaps and unclear/mixed content remain `uncertain`.
These labels classify the center view, not the entire receptive field.

The review assigned **5 component, 3 empty_board and 22 uncertain** pair labels.
The three clear substrate centers occur in the selected **both-hit 512 case**;
none of the selected both-miss/rescue reference views supports a clear empty-board
center label. The latter often show populated component strips and ambiguous
intercomponent/package-boundary centers. This is a limited visual check, not a
prevalence estimate across all patch pairs. Unreviewed reference contexts remain
explicitly uncertain. The pair-specific reviewed table includes query ID, rank,
reference identity, reviewer, criteria and timestamp.

## Verification and limits

Every re-extracted native model map matched its saved Stage4 map exactly (maximum
absolute error 0). All saved image scores matched. Five systematic query positions
per image/resolution were independently checked with float64 NumPy direct-distance
calculations; the maximum recorded distance difference was 1.55e-6. References were
checked against fitting IDs and frozen bank index metadata. The five synthetic
geometry, mask-ring, out-of-crop, tie-order and nonfinite-distance tests passed.

No source annotation or Stage4 detector artifact was changed. The CSVs retain
per-query and per-image denominators; outcome/pose summaries give each image equal
weight. Nearest-neighbor distance is not a defect probability, and local-looking
references are not proof of correct expected-component matching. These observations
weaken the proposed distant-match explanation for the canonical misses; representation,
small regions, receptive-field context and aggregation remain unresolved alternatives.
Stage5B was not executed.

## Publication and manual-label authority

`selected_reference_context_review.csv` is the authoritative pair-specific manual
context review; `reference_context_labels.csv` carries its reviewed bank-index labels.
Before publication, rerunning `summarize` regenerates the reference table with
unreviewed uncertain labels, so the manual review must be reapplied explicitly.
After `artifacts/stage5a/diagnostics.json` exists, all four write entry points
(`extract`, `summarize`, `sheets`, `review-sheets`) refuse to run. Existing extraction
completion is also exclusive. The publication guard was verified with a temporary
sentinel without touching diagnostic outputs or frozen detector artifacts.

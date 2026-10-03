# Stage 4A: is PCB1 geometry suitable for PCB2?

Started October 2, 2026. Results are pending; no PCB2 anomaly content has informed
this work. Historical transport uncertainty is disclosed in the Stage 4 exposure ledger.

The inherited crop identifies the largest blue/cyan component at a 512-pixel
working width, applies conservative board-relative margins and preserves aspect
ratio with gray letterboxing. It does not normalize pose. A crop tuned to PCB1
might identify the wrong region or omit PCB2 edges and connectors.

PCB2 official training normals alone will be used to examine inherited geometry.
Exact SHA groups are split deterministically using the same PCB1 algorithm:
sorted groups, NumPy default_rng seed 42, 20% rounded up for calibration. Official
held-out normal images are excluded from geometry development and fitting.

Before any adaptation, quantitative crop, component, aspect, boundary and padding
statistics and deterministic extreme/systematic contact sheets will be retained.
Visual review must consider edges, connectors, obvious background, pose and any
wrong component. Crop boundary contact is a warning to inspect, not proof of
clipping. Source defect masks cannot be used to decide the crop.

The detector remains the Stage 3 feature/scoring/selection recipe. If geometry is
acceptable it will be retained unchanged. If normal evidence shows a failure,
a documented normal-only geometry change must precede the final freeze. No
orientation registration or other detector change is assumed in advance.

The exact suitability decision and supporting examples will be appended after
normal preflight. Primary D1 is fixed at 256; secondary D2 at 512. PCB2 anomalies,
masks and defect annotations remain withheld until both preparations and
independent preflight checks are bound by the final freeze receipt.

## Normal-only result and geometry decision

All 901 official training normals decoded as 1404×1070 RGB images, with no exact
duplicates or exact PCB1 matches. Splits are 720 fitting, 181 calibration and 100
held-out normals; held-out decode is deferred. Applying the inherited geometry
yielded zero fallbacks and zero crop/board source-boundary contacts. Crop-area
fractions span 0.5945–0.6822; padding spans 20.3–29.3%.

Seventeen deterministic extreme/systematic normals were reviewed on three contact
sheets. Board edges and connector pins were retained; the component detector
selected the full PCB, with mild tilt but no reviewed orientation reversal. The
conservative vertical margin retains background. This is acceptable normal evidence
for keeping the inherited recipe, not proof that every future defect is retained.

**Decision: retain the inherited blue crop and margins unchanged.** No category
adaptation or pose normalization was introduced. Anomaly masks remain excluded
from this decision; source annotations will remain in the confirmation denominator.

See [preflight statistics](../../artifacts/stage4/geometry_preflight/geometry_preflight.json),
[review receipt](../../artifacts/stage4/geometry_preflight/normal_geometry_review.json),
and the [first normal sheet](../../artifacts/stage4/geometry_preflight/normal_contact_sheet_01.png).

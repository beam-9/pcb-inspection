# Run 1 maximum-score nearest-reference trace diagnostics

Analyzed 200 saved traces; no inference or fitting was repeated.

Offsets use the original unregistered 32×32 feature grid. A large offset is descriptive and can reflect repeated structures, acquisition displacement, 180-degree orientation differences or implausible matching; it is not itself evidence of a defect.

- FN: 57 traces; median Chebyshev offset 1.0 cells; 15/57 outside radius 2.
- FP: 9 traces; median Chebyshev offset 5.0 cells; 5/9 outside radius 2.
- TN: 91 traces; median Chebyshev offset 1.0 cells; 22/91 outside radius 2.
- TP: 43 traces; median Chebyshev offset 2.0 cells; 19/43 outside radius 2.

The winning maximum-score patch may lie outside the annotation. These traces cannot establish which normal patches matched the underlying false-negative defect region, or show that cross-location matching caused a miss.

Next useful diagnostic: before any new model, predeclare a deterministic sample spanning false-negative defect types and size quartiles, extract only those existing Run 1 query features, and inspect nearest references at annotation-intersecting grid cells. Use annotation masks solely to select retrospective diagnostic queries. Record this as new diagnostic inference, preserve Run 1 outputs, and compare matched/nonmatched controls; do not select a spatial radius from these traces alone.

Defect-type summaries count multi-label images once in each listed type; row totals can exceed the anomaly count.

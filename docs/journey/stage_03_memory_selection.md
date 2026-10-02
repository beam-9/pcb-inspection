# Stage 3: does a better normal memory help?

Completed October 2, 2026. PCB1 development only; PCB2 remains sealed.

Stage 2 made the board occupy more useful pixels, but uniform sampling still spent
roughly a quarter of its limited reference budget on padding centers. That was a
plausible inefficiency, not proof of the cause of errors. Stage 3 tested whether a
representative normal memory helped while preserving everything else.

Each resolution used all fitting-normal patch positions and exactly 4,096 references.
A seeded 384-to-64 Gaussian projection made approximate greedy selection practical;
scoring still uses the original 384-dimensional features. Geometry, weights,
Euclidean matching, maximum image score, padding eligibility, map coordinates and
normal-only calibration policy stayed fixed. This is PatchCore-inspired, not a
faithful reproduction of the complete original algorithm.

| Matched comparison | Detected /100 | Normal false alarms /100 | Median anomaly pixel AP | Median inference |
| --- | ---: | ---: | ---: | ---: |
| C1 uniform 256 | 61 | 4 | 0.097 | 0.292 s |
| D1 representative 256 | **89** | **4** | **0.353** | 0.291 s |
| C2 uniform 512 | 70 | 12 | 0.354 | 1.081 s |
| D2 representative 512 | **95** | **11** | **0.535** | 1.081 s |

The research question has a useful answer: **this selection recipe improves both
branches on PCB1 development data at the same reference count.** D1 gains 28 detections
without increasing the observed false alarms. D2 gains 25, improves localization,
and reduces false alarms by one. Ranking metrics also improve. D1's thresholded
pixel IoU decreases slightly; maps can rank defects better while highlighting an
excessively broad region. D2 still misses five anomalies and flags eleven normals.

Normal-space coverage is mixed: both new banks reduce sampled upper-tail nearest
reference distances while increasing mean and median distances. Padding-center
references drop to about 1.0% at 256 and 0.56% at 512, but fewer fitting images are
represented. These composition changes do not establish a causal explanation.

Normal preparation took 118 seconds at 256 and 362 seconds at 512, including the
charged original extraction cost of the verified 512 cache. Both passed the 8 GiB,
30-minute preparation and 10-second median inference gates. Independent reviews
passed both runs; all image decisions and common-resolution localization metrics
were checked. Source-resolution AP was independently checked on three examples,
and selection prefix/vector checks do not constitute a second complete selector run.

**Next decision:** carry D1 forward as the default development recipe because it
balances detection, four normal flags and 0.291-second processing. Preserve D2 as
the higher-recall/localization alternative. Before fresh PCB2 confirmation, freeze
a category-adaptation procedure and check geometry using allowed normals; the blue
PCB1 crop must not be assumed to work on another category. That work is deferred.
No UI, LLM integration or Stage 4 intervention was performed.

Read the [complete findings](../../artifacts/pcb1_memory_selection_comparison/findings.md),
[executed notebook](../../notebooks/pcb1_memory_selection.ipynb),
[method notes](../development/stage3_method_notes.md),
[execution notes](../development/stage3_execution_notes.md) and
[exposure ledger](../development/stage3_exposure_ledger.md). Fixed A2 examples,
defect type and size slices, preparation costs and all regressions are retained.

# Stage 5A decision: test orientation normalization first

**One proposed Stage 5B intervention:** image-only canonical orientation normalization before existing D1 feature extraction. Not executed.

Five reversed anomalies account for 28.80%/29.84% of all false-positive pixels; anomaly-only median burden is 11.1×/12.3× canonical anomalies and crop spread is 0.7465/0.5020 vs 0.0699/0.0436. Both recipes show the direction. All reversed cases are detected; no reversed normals exists, so pose is a candidate mechanism for broad maps, not an explanation for image misses or causal proof.

Missing-label misses occur on canonical boards and retrieve more local references than matched canonical hits. This weakens spatial restrictions as the first intervention. Six both-missed cases remain unresolved, and only one missing-label case is rescued by D2. Size and source labels remain confounded.

Control the future experiment: current D1 vs D1 plus orientation normalization, image-only pose rule/uncertain handling declared before results; unchanged layers, memory budget/selection, scoring and calibration policy; measure canonical/reversed localization and overall detection/resources. Do not combine with another intervention. New PCB2 results are post-confirmation development.

See the complete method/evidence/limits in `docs/journey/stage_05a_failure_diagnosis.md` and combined tables here. No Stage 5B detector was fitted or scored.

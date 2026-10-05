# Small-defect saved-map decomposition

All29 fixed R1/R2 anomalies appear for both recipes:58 rows. Predicates are declared
in broad_maps/diagnostic_policy.json, can overlap and describe saved maps only.
D1 has23 cases with a larger outside-GT maximum,11 with GT map evidence above the
pixel threshold despite an unflagged image, and3 with GT map maximum at/below the
pixel threshold. D2 has11 competing outside maxima,8 evidence/unflagged cases and
zero low-GT-map-response cases. Two D1 and15 D2 rows meet none of these predicates;
`unclear_or_mixed` means unclassified by these rules, not proven failure.

Seven small anomalies are D1miss/D2hit. Twenty show that rescue or a common pixel
AP gain>=0.10, under the fixed diagnostic contrast rule. The contrast does not prove
resolution caused improvement: reference fraction/bank/calibration also differ.
Image scores are patch maxima, whereas bilinear map maxima may be lower; comparing
GT map maxima with the image threshold does not reconstruct patch-level evidence.
No rule proves representation failure or justifies changing a frozen threshold.
Missing labels/pose must be analyzed jointly before choosing an intervention.

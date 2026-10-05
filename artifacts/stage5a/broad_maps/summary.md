# Saved-map spatial diagnosis

Post-confirmation PCB2 development only; no detector or threshold changed.
All 400 per-recipe image rows and 12,800 grid rows preserve Stage4 identities.
Full common256 FP totals reproduce D1 510,336 and D2 325,593 exactly. No thresholded
FP pixels fall outside the source-relative crop-center membership in this dataset.

Native score grids exclude letterbox padding. Common256 grids map pixel centers
through full source extent into crop coordinates; these are different pixel
resolutions/denominators. Neither grid is a segmented anatomical board mask: retained
crop background remains included. Normalized 64×64 aggregates use bilinear native
scores and nearest source GT; frequency is per selected image, not a new inference
map. Eight-connectivity and positive bounding-box fractions use native content.

Among anomalies, median crop exceedance fractions are D1 canonical90 0.0699,
reversed5 0.7465, uncertain5 0.1422; D2 0.0436, 0.5020 and 0.0772. Reversed cases
account for 146,977/97,150 FP pixels (~28.8%/29.8% of all image FP). All normals are
canonical; there is no reversed-normal comparison. Uncertain is not pooled with
reversed. Pose associations are descriptive, based on five reversed anomalies,
and cannot establish a causal orientation effect or explain all localization error.

The largest all-anomaly common-crop cell FP frequencies are D1(row1,col2)0.1787,
(row2,col2)0.1763,(row0,col2)0.1678; D2(row2,col2)0.1452,(row1,col2)0.1291,
(row2,col1)0.1244, with zero-based indices. Responses occupy interior/right crop
regions rather than only padding. Without anatomical registration and interventions,
do not label these grid cells as a specific faulty component or causal structure.

Numeric plot colorbars are shared across groups per recipe: mean raw scores span
0–2.6901 D1 and 0–2.6920 D2; threshold/FP frequencies span0–1. CSV/NPY values govern.

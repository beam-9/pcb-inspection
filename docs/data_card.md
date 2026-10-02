# VisA PCB1 data card

VisA is a public visual anomaly benchmark released by Amazon Science, attributed to Yang Zou, Jongheon Jeong, Latha Pemula, Dongqing Zhang and Onkar Dabeer. This is public PCB imagery, not Seagate data. Dataset reuse is CC BY 4.0; attribution and indications of modifications are required. Repository code and model weights have separate terms.

Primary sources: [owner repository](https://github.com/amazon-science/spot-diff), [AWS Open Data registry](https://registry.opendata.aws/visa/), [authors' paper](https://arxiv.org/abs/2207.14315). Source revision is `2a692ab575001cbde74d402d897a7286086c6199`; official one-class split is `split_csv/1cls.csv` from that revision.

The source category has 1,004 normal and 100 anomalous images. Official one-class membership is 904 normal training, 100 normal test and 100 anomalous test. Calibration is seed-42 20% of exact-duplicate official normal training groups, with the remainder fitting; the official test remains unchanged. The manifest stores source membership, masks, hashes and IDs. Identifiers, paths and labels never enter feature extraction or detector scoring.

Acquisition uses only PCB1 member ranges from the uncompressed 1,929,840,640-byte owner archive, with bounded header probes and category-local 8 MB range caching. Each request verifies HTTP 206, exact Content-Range and unchanged multipart ETag. A 400 MB selected-member limit prevents silent full-collection acquisition. The downloader checks coverage against the official CSV. Raw data is gitignored and not republished. Member SHA-256 records and full retrieval details are under `data/raw/acquisition.json`; the whole-archive hash is unavailable because the full archive was not acquired.

Audit policy: load images to validate decoding, RGB mode, orientation, geometry and image/mask pairing. Missing abnormal masks or corrupt inputs are excluded only with recorded reasons before evaluation. Normal masks are implicit zeros. Original multiclass scalar masks become binary anomaly masks with `>0`; masks are resized with nearest-neighbor interpolation. A fixed 256x256 structural mask audit quantifies complete loss of annotated regions and changes in annotated area without tuning to test masks. Test images are not viewed or scored during this audit.

SHA-256 groups isolate exact duplicate files. Training-only dHash Hamming-distance candidates are reviewed numerically for coarse-image differences. Similar aligned normal boards are not removed merely for looking alike. Public acquisition metadata does not identify physical boards or related observations, so grouping beyond confirmed exact duplicates remains unavailable. This is an image-benchmark holdout, not a verified unseen-object, chronological or unseen-factory assessment. No factory timestamps are assumed.

The authors describe manually generated defects and high-resolution RGB sensor acquisition. Controlled anomalies, the selected board type and benchmark prevalence limit transfer to production images and production defect rates. Localization indicates suspicious visual regions and does not establish a defect cause, component diagnosis, repair action or future HDD reliability.

Measured audit results are recorded in `data/manifests/pcb1_audit.json` and summarized below. Structural validation does not establish model performance.

## Executed structural audit (2026-10-01 Vancouver)

All 1,104 RGB images decoded successfully, each 1,404x1,070 pixels with supported orientation. There were no exclusions, missing abnormal masks or SHA-256 exact duplicates. Owner `image_anno.csv` agrees with all 1,104 image/mask rows and binary labels in the pinned official split after collapsing named anomaly classes to anomaly. Final membership is 723 fitting normals, 181 calibration normals, 100 normal test images and 100 anomalous test images. Manifest SHA-256 is `3b6c9c04f2342ca1e5d31923612b3fb39769a3db7b7bbcd846415f50cd87ec08`.

Training-only dHash screening found 1,261 candidate pairs. A numeric investigation of 20 lowest-distance pairs found normalized 64x64 RGB mean absolute differences ranging from 0.025391 to 0.057976. Public source metadata still cannot establish physical board identities; none were removed or grouped on similarity alone. Exact hashes remain the only confirmed groups. Candidate evidence is saved in `pcb1_near_duplicates.json` and `pcb1_near_duplicate_review.json`.

All 100 anomaly masks had positive pixels. At the predeclared 256x256 nearest-neighbor resize, none lost all annotated pixels; positive-area fraction relative to the original ranged from 0.9201 to 1.1938. This measures annotation sampling loss only, not preservation of visible defect information in resized RGB images. The 1,404x1,070 to 256x256 image transformation substantially reduces resolution and changes aspect ratio. Audit results do not demonstrate detector quality.

Successful selective acquisition retained 1,205 PCB1 members (1,204 required images/masks and the owner annotation CSV), totaling 296,989,825 bytes. The successful acquisition attempt transferred 322,051,072 bytes including bounded probes/cache overhead. Earlier interrupted feasibility attempts transferred additional discarded bytes; this value is not total-session network consumption. The complete 1,929,840,640-byte collection was never downloaded.

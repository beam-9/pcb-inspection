# VisA PCB1 data

Source: Amazon Science's [SPot-the-Difference / VisA](https://github.com/amazon-science/spot-diff), revision `2a692ab575001cbde74d402d897a7286086c6199`. Dataset **CC BY 4.0**; code licensing is separate. Attribute Yang Zou, Jongheon Jeong, Latha Pemula, Dongqing Zhang and Onkar Dabeer, *SPot-the-Difference Self-Supervised Pre-training for Anomaly Detection and Segmentation*, ECCV 2022, [paper](https://arxiv.org/abs/2207.14315).

The owner archive is 1,929,840,640 bytes, uncompressed TAR. The downloader locates PCB1 with bounded header probes, acquires only its members using HTTP ranges, verifies the S3 ETag for each request, rejects full responses, imposes a 400 MB selected-member cap, and checks all required official split images/masks exist. Probe payload bytes are discarded. No full archive is retained. Raw files are gitignored.

```bash
curl -L https://raw.githubusercontent.com/amazon-science/spot-diff/2a692ab575001cbde74d402d897a7286086c6199/split_csv/1cls.csv -o data/raw/1cls.csv
python -m pcb_inspection.acquisition --destination data/raw
python -c "from pcb_inspection.data import build_manifest; print(build_manifest('data/raw','data/raw/1cls.csv','data/manifests'))"
```

`data/raw/acquisition.json` records URL, source revision, ETag, bytes and per-member SHA-256 hashes. S3 multipart ETag is not a whole-archive SHA-256. `data/manifests/pcb1_manifest.csv` stores relative raw image/mask paths, immutable image IDs, labels, source splits, fitting/calibration/test membership, image and mask hashes and structural geometry. The manifest's SHA-256 identifies the split. Repeated audit against identical inputs is accepted; altered membership refuses overwrite.

Official PCB1 membership: 904 normal training images, 100 normal test images, 100 anomalous test images. Seed 42 allocates 20% of exact-duplicate training groups to normal calibration; the remainder fit. All official test membership is preserved. Exact duplicate hashes across source train/test stop the audit. Original scalar mask class IDs become anomaly with `>0`; normal masks are implicit zeros.

Acquisition identity cannot be established from public filenames. Training-only dHash candidates are screening evidence, not proof of identical physical boards; no automatic removal or inferred timestamps. Structural audit decodes held-out files and checks mask geometry/content; no held-out views or model scoring are emitted before the frozen evaluation gate.

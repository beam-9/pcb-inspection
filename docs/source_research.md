# Phase A source and acquisition decisions

Research/access date: 2026-10-01 America/Vancouver (network responses dated 2026-10-02 UTC). This note resolves source questions for a local educational/research PCB1 pilot. It records source facts separately from engineering decisions. It does not establish factory performance or commercial deployment rights.

## Dataset and official protocol

The [dataset owner's repository](https://github.com/amazon-science/spot-diff) lists PCB1 as 1,004 normal images and 100 anomalous images. The [AWS registry](https://registry.opendata.aws/visa/) identifies the current archive and CC BY 4.0 dataset license. Registry attribution: VisA, Zou, Yang; Jeong, Jongheon; Pemula, Latha; Zhang, Dongqing; Dabeer, Onkar, *SPot-the-Difference Self-Supervised Pre-training for Anomaly Detection and Segmentation* (2022), accessed on the date above.

Owner source revision verified using GitHub's commits API: `2a692ab575001cbde74d402d897a7286086c6199`.

- [Pinned official one-class split CSV](https://raw.githubusercontent.com/amazon-science/spot-diff/2a692ab575001cbde74d402d897a7286086c6199/split_csv/1cls.csv): programmatic CSV counts are **904 training normals, 100 test normals, 100 test anomalies** for PCB1. These are membership facts, not model results.
- [Pinned dataset license](https://github.com/amazon-science/spot-diff/blob/2a692ab575001cbde74d402d897a7286086c6199/LICENSE-DATASET): CC BY 4.0. [Creative Commons terms](https://creativecommons.org/licenses/by/4.0/) permit sharing/adaptation, including commercial use, with attribution, license link and indication of changes; do not imply endorsement.
- [Pinned code license](https://github.com/amazon-science/spot-diff/blob/2a692ab575001cbde74d402d897a7286086c6199/LICENSE): Apache-2.0, separate from data.
- [Preparation code](https://raw.githubusercontent.com/amazon-science/spot-diff/2a692ab575001cbde74d402d897a7286086c6199/utils/prepare_data.py) converts every nonzero original mask label to 255. Adopt `mask > 0` binary anomalies. Normal masks are implicit zeros, as stated in the owner's README; a missing anomaly mask is an error. Normal test images belong in localization metrics.

Decision: preserve all 200 official test images. Divide the official normal training membership into fitting/calibration without accessing test results. Exact duplicates and acquisition identity limitations require the separate audit; the source split alone does not prove object independence. The [authors' paper](https://arxiv.org/html/2207.14315) describes manually introduced defects and high-resolution RGB acquisition; this is a benchmark holdout, not a temporal factory trial.

## Bounded selective acquisition

Official object: [VisA_20220922.tar](https://amazon-visual-anomaly.s3.us-west-2.amazonaws.com/VisA_20220922.tar). This is an **uncompressed TAR**, not a compressed per-category download.

Observed HEAD response:

| Field | Value |
| --- | --- |
| HTTP status | 200 |
| Content-Length | 1,929,840,640 bytes (1.80 GiB) |
| Content-Type | application/x-tar |
| Accept-Ranges | bytes |
| Last-Modified | Thu, 22 Sep 2022 19:23:39 GMT |
| ETag | `05c830591a1172938cb714895c9e0cfb-113` |

The [public bucket listing](https://amazon-visual-anomaly.s3.us-west-2.amazonaws.com/?list-type=2) returned only `VisA.tar` (older, 1,930,393,600 bytes) and `VisA_20220922.tar`; no PCB1 object was listed. Actual probe `Range: bytes=0-1023` returned **206**, `Content-Range: bytes 0-1023/1929840640`, exactly 1,024 bytes, and TAR header name `candle/`. Thus selective range retrieval is technically available; this conclusion is supported by an executed probe, not just advertised headers.

Decision: scan TAR headers through HTTP byte ranges, seek past unrelated file bodies, fetch only safe regular PCB1 members and relevant annotations. Validate response 206, Content-Range, length, source ETag and TAR paths/types/checksums. Do not fall back silently to an HTTP 200 full download. Coalesce nearby ranges only with a bounded transfer budget. Record transferred bytes, per-file SHA-256 and source metadata. The multipart ETag is a source identity indicator, **not a full-file SHA-256**. Archive checksum cannot be honestly claimed from selective bytes. Raw data/checkpoint files remain Git-ignored. Actual PCB1 selected byte total and acquired counts must come from acquisition, not estimation in this note.

## Primary method and library decision

The [authors' PatchCore implementation](https://github.com/amazon-science/patchcore-inspection) extracts pretrained, locally aggregated patch features and constructs a subsampled normal memory. Its README's example uses WideResNet50, layer2/layer3, a 3×3 patch neighborhood, approximate greedy coreset and FAISS. It reports the original environment as Python 3.8. [Pinned requirements](https://github.com/amazon-science/patchcore-inspection/blob/fcaa92f124fb1ad74a7acf56726decd4b27cbcad/requirements.txt) include faiss-cpu and lower bounds for torch/torchvision. Source revision verified: `fcaa92f124fb1ad74a7acf56726decd4b27cbcad`; code is [Apache-2.0](https://github.com/amazon-science/patchcore-inspection/blob/fcaa92f124fb1ad74a7acf56726decd4b27cbcad/LICENSE).

[Maintained Anomalib documentation](https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/models/image/patchcore.html) documents ResNet18 layer2/layer3 features, normal-only memory, average pooling, feature-map concatenation after alignment, coreset reduction and chunked Euclidean nearest neighbors. With one scoring neighbor it returns the maximum patch distance; more neighbors enable weighted image scoring. Anomalib uses timm/Lightning wrappers and configurable processing/evaluation.

Decision: a small project-owned CPU-compatible implementation is reasonable for the pilot's frozen protocol and exact patch/image reference tracing. Call it **PatchCore-inspired**, documenting any smaller backbone, coreset/subsampling, feature aggregation, preprocessing, map smoothing or score differences. Do not present official published performance as our expected result. Avoid library postprocessing that learns thresholds from labeled test/validation anomalies; calibration is exclusively held-out normals. Hardware smoke testing, not documentation, decides practical feasibility.

## Backbone, checkpoint and use terms

Proposed frozen backbone is torchvision ResNet18 with explicit `ResNet18_Weights.IMAGENET1K_V1`, not mutable `DEFAULT`. [Official model documentation](https://docs.pytorch.org/vision/0.21/models/generated/torchvision.models.resnet18.html) records approximately 44.7 MB and the reference transform: shorter side 256, center crop 224, RGB values in [0,1], mean `[0.485, 0.456, 0.406]`, standard deviation `[0.229, 0.224, 0.225]`. If the pilot resizes the complete image to retain PCB borders, disclose its geometry/defect-resolution departure rather than claiming identical reference preprocessing.

[Official torchvision source](https://github.com/pytorch/vision/blob/6da25ff876100d36f23472f5762d5f306c47d735/torchvision/models/resnet.py) identifies the exact download as [resnet18-f37072fd.pth](https://download.pytorch.org/models/resnet18-f37072fd.pth). Record downloaded checkpoint SHA-256 in the run provenance; the filename prefix is not a substitute for the full locally computed hash. Pin the installed torch/torchvision versions after successful smoke testing.

The [torchvision code license](https://github.com/pytorch/vision/blob/6da25ff876100d36f23472f5762d5f306c47d735/LICENSE) is BSD-3-Clause. This does **not** establish unrestricted rights to pretrained weights. The [owner's pretrained model statement](https://github.com/pytorch/vision/blob/6da25ff876100d36f23472f5762d5f306c47d735/README.md#pre-trained-model-license) says model terms may derive from their training datasets and users must determine permitted use. [ImageNet's access terms](https://www.image-net.org/download.php) restrict use of the Database to noncommercial research and education. [ImageNet's image access page](https://www.image-net.org/download-images.php) also states that ImageNet does not own image copyrights.

Decision and limitation: this Phase A is a **local noncommercial educational/research evaluation**. No ImageNet database download is needed. Use the owner-published checkpoint locally, record its provenance and the above terms, and do not commit or redistribute it. We found no ResNet18-specific commercial license grant and do not conclude that database terms definitively transfer to checkpoint weights. **Commercial deployment/redistribution rights remain unverified** and must be reconsidered before expanding the use case. Dataset attribution-only terms and torchvision BSD code terms must not be conflated with model-weight rights.

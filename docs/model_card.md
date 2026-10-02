# Frozen pilot model card

Scope: local educational visual anomaly benchmark on VisA PCB1, not Seagate data.
No physical defect/root-cause diagnosis, rejection decision or factory validation.

Backbone: torchvision ResNet18 IMAGENET1K_V1, frozen evaluation mode.
Input: EXIF-corrected RGB, direct 256x256 bilinear full-image resize, ImageNet
normalization. Official weight reference preprocessing uses 224 center crop;
our full-board geometry is a deliberate departure. Layer2 and layer3 features each
receive 3x3 average aggregation; layer3 is bilinear aligned to layer2, yielding
384 channels over a 32x32 grid. Receptive fields overlap; patch grid coordinates
are evidence coordinates, not component boundaries.

Baseline: mean-pool the same aggregated features, L2 normalize, nearest fitting-normal
Euclidean distance. No fine tuning, centroids or test-dependent choices.

Primary: **PatchCore-inspired**, not a reproduction: ResNet18, 4096 seed42 uniform
patches without replacement, CPU exact nearest neighbor, unweighted maximum patch
score, bilinear anomaly maps without smoothing. Original PatchCore uses a coreset
and can apply image-score weighting. Uniform sampling may miss normal modes.

All reference vectors derive exclusively from fitting normals. Sampling metadata
records actual fitting image ID, row and column. Calibration normals set image 95th
and pixel 99th quantiles with higher convention; values equal to threshold remain
unflagged. These illustrative policies give no future false-alarm guarantee.

Image AP/AUROC and confusion use the official benchmark. Pixel AP includes normal
images at 256-square resolution; localization may lose small source defects. No
per-image map normalization is used. Thresholded global pixel IoU is supplemental.

See source_research.md for separate code, dataset and pretrained-weight terms.
The checkpoint stays local and ignored; commercial rights are unverified.
See pilot_findings.md for measured results once final evaluation completes.

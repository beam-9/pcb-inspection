"""Frozen geometry: direct 256-square RGB resize, ImageNet normalization, no crop."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import torch
from torch import nn
from torch.nn import functional as F

IMAGE_SIZE = 256
PREPROCESSING_ID = "rgb-exif-transpose-direct256-bilinear-imagenet-v1"


def preprocess_image(image: Image.Image | str | Path) -> torch.Tensor:
    if isinstance(image, (str, Path)):
        with Image.open(image) as opened:
            return preprocess_image(opened)
    image = ImageOps.exif_transpose(image).convert("RGB")
    resized = image.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
    array = np.asarray(resized, dtype=np.float32).copy() / 255.0
    tensor = torch.from_numpy(array).permute(2, 0, 1)
    mean = torch.tensor([.485, .456, .406])[:, None, None]
    std = torch.tensor([.229, .224, .225])[:, None, None]
    return (tensor - mean) / std


def preprocess_mask(mask: Image.Image | str | Path) -> np.ndarray:
    if isinstance(mask, (str, Path)):
        with Image.open(mask) as opened:
            return preprocess_mask(opened)
    mask = ImageOps.exif_transpose(mask).convert("L")
    return np.asarray(mask.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.NEAREST)) > 0


class FrozenPatchExtractor(nn.Module):
    """ResNet18 layer2 + layer3, 3x3 neighborhood aggregation; no training."""

    weight_id = "torchvision.ResNet18_Weights.IMAGENET1K_V1"

    def __init__(self, device: str = "cpu", *, weights: bool = True):
        super().__init__()
        from torchvision.models import ResNet18_Weights, resnet18
        backbone = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 if weights else None)
        self.stem = nn.Sequential(backbone.conv1, backbone.bn1, backbone.relu, backbone.maxpool,
                                  backbone.layer1)
        self.layer2 = backbone.layer2
        self.layer3 = backbone.layer3
        self.device = torch.device(device)
        self.requires_grad_(False)
        self.to(self.device)
        self.eval()

    @torch.inference_mode()
    def forward(self, batch: torch.Tensor) -> torch.Tensor:
        if batch.ndim != 4 or tuple(batch.shape[1:]) != (3, IMAGE_SIZE, IMAGE_SIZE):
            raise ValueError("Expected [N,3,256,256] images")
        if not torch.isfinite(batch).all():
            raise ValueError("Images must be finite")
        self.eval()
        layer2 = self.layer2(self.stem(batch.to(self.device)))
        layer3 = self.layer3(layer2)
        layer2 = F.avg_pool2d(layer2, 3, stride=1, padding=1)
        layer3 = F.avg_pool2d(layer3, 3, stride=1, padding=1)
        layer3 = F.interpolate(layer3, size=layer2.shape[-2:], mode="bilinear", align_corners=False)
        return torch.cat([layer2, layer3], dim=1).cpu()

    def extract(self, paths: list[str | Path], batch_size: int = 8) -> torch.Tensor:
        if not paths or batch_size < 1:
            raise ValueError("Nonempty paths and positive batch size required")
        return torch.cat([self(torch.stack([preprocess_image(p) for p in paths[i:i+batch_size]]))
                          for i in range(0, len(paths), batch_size)])

"""PatchCore-inspired uniform memory sampling; not a faithful coreset reproduction.

Departures: ResNet18, seeded uniform sampling, unweighted maximum patch score,
CPU exact nearest neighbors, and bilinear maps without Gaussian smoothing.
"""
import numpy as np
import torch
from torch.nn import functional as F

from .baseline import checked_features, nearest, validate_ids


class PatchCoreInspired:
    def __init__(self, max_memory=4096, seed=42, chunk_size=256):
        if max_memory < 1 or chunk_size < 1:
            raise ValueError("Positive memory and chunk budgets required")
        self.max_memory, self.seed, self.chunk_size = max_memory, seed, chunk_size

    def fit(self, features, image_ids):
        features = checked_features(features)
        validate_ids(image_ids, len(features))
        n, c, h, w = features.shape
        rng = np.random.default_rng(self.seed)
        sampled = np.sort(rng.choice(n*h*w, size=min(self.max_memory, n*h*w), replace=False))
        # Gather selected rows directly: reshaping a permuted fitting bank would
        # otherwise allocate a second full (~1GB for this pilot) feature array.
        image_index = torch.from_numpy(sampled // (h*w))
        row_index = torch.from_numpy((sampled % (h*w)) // w)
        column_index = torch.from_numpy(sampled % w)
        self.memory = features[image_index, :, row_index, column_index].clone()
        self.image_ids = list(image_ids)
        self.grid_shape = (h, w)
        self.metadata = [{"image_id": image_ids[int(i)//(h*w)], "row": (int(i) % (h*w))//w,
                          "column": int(i) % w, "flat_index": int(i)} for i in sampled]
        return self

    def score(self, features):
        if not hasattr(self, "memory"):
            raise RuntimeError("Model has not been fitted")
        features = checked_features(features)
        n, c, h, w = features.shape
        if c != self.memory.shape[1] or (h, w) != self.grid_shape:
            raise ValueError("Features differ from fitted channel/grid geometry")
        query = features.permute(0, 2, 3, 1).reshape(-1, c)
        distances, indices = nearest(query, self.memory, self.chunk_size)
        patch_distances = distances.reshape(n, h, w)
        maps = F.interpolate(patch_distances[:, None], (256, 256), mode="bilinear", align_corners=False)[:, 0]
        return {"scores": patch_distances.flatten(1).max(dim=1).values.numpy(),
                "maps": maps.numpy(), "patch_distances": patch_distances.numpy(),
                "nearest_indices": indices.reshape(n, h, w).numpy()}

    def assert_no_test_ids(self, test_ids):
        overlap = set(self.image_ids) & set(test_ids)
        if overlap:
            raise ValueError(f"Test IDs in reference memory: {sorted(overlap)}")

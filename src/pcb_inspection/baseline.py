"""Frozen global-average embedding nearest-normal baseline."""
import torch
from torch.nn import functional as F


def checked_features(features: torch.Tensor) -> torch.Tensor:
    features = torch.as_tensor(features, dtype=torch.float32, device="cpu").detach()
    if features.ndim != 4 or min(features.shape) < 1:
        raise ValueError("Expected nonempty finite [N,C,H,W] features")
    if any(not torch.isfinite(chunk).all() for chunk in features.split(16)):
        raise ValueError("Expected nonempty finite [N,C,H,W] features")
    return features


def validate_ids(image_ids, n):
    if len(image_ids) != n or len(set(image_ids)) != n or any(not isinstance(i, str) or not i for i in image_ids):
        raise ValueError("A unique nonempty image ID is required per fitting image")


def nearest(query, memory, chunk_size=256):
    if chunk_size < 1:
        raise ValueError("Positive chunk size required")
    distances, indices = [], []
    for chunk in query.split(chunk_size):
        # Direct Euclidean kernel avoids cancellation-induced positive self-distance.
        d = torch.cdist(chunk, memory, p=2, compute_mode="donot_use_mm_for_euclid_dist")
        values, positions = d.min(dim=1)
        if not torch.isfinite(values).all():
            raise ValueError("Nonfinite nearest-neighbor distance; check feature scale")
        distances.append(values)
        indices.append(positions)
    return torch.cat(distances), torch.cat(indices)


class FrozenEmbeddingBaseline:
    def fit(self, features, image_ids):
        features = checked_features(features)
        validate_ids(image_ids, len(features))
        self.memory = F.normalize(features.mean(dim=(-2, -1)), p=2, dim=1).clone()
        self.image_ids = list(image_ids)
        return self

    def score(self, features):
        if not hasattr(self, "memory"):
            raise RuntimeError("Model has not been fitted")
        features = checked_features(features)
        query = F.normalize(features.mean(dim=(-2, -1)), p=2, dim=1)
        if query.shape[1] != self.memory.shape[1]:
            raise ValueError("Feature channel mismatch")
        scores, indices = nearest(query, self.memory)
        return {"scores": scores.numpy(), "reference_ids": [self.image_ids[i] for i in indices.tolist()]}

    def assert_no_test_ids(self, test_ids):
        overlap = set(self.image_ids) & set(test_ids)
        if overlap:
            raise ValueError(f"Test IDs in reference memory: {sorted(overlap)}")

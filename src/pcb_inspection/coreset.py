"""Deterministic projected approximate-greedy selection, preserving scoring features.

The initializer follows mean distance to seeded anchors, followed by a running
minimum with each selected center. This is a heuristic, not optimal k-center.
Projection is used only to select original candidate indices.
"""
import time
import numpy as np
import torch


class ResourceGateError(RuntimeError):
    """Normal-only engineering work exceeded a declared resource deadline."""


def gaussian_projection(input_dim=384, output_dim=64, seed=43):
    if input_dim < 1 or output_dim < 1 or output_dim > input_dim or seed < 0:
        raise ValueError('Positive projection dimensions and nonnegative seed required')
    generator = torch.Generator(device='cpu').manual_seed(seed)
    return torch.randn(input_dim, output_dim, generator=generator) / np.sqrt(output_dim)


def project_features(features, projection):
    features = torch.as_tensor(features, dtype=torch.float32, device='cpu')
    if features.ndim != 2 or projection.ndim != 2 or features.shape[1] != projection.shape[0]:
        raise ValueError('Candidate/projection dimensions do not match')
    if not torch.isfinite(features).all() or not torch.isfinite(projection).all():
        raise ValueError('Finite projection and candidates required')
    return features @ projection


def select_coreset(projected, count=4096, seed=42, initial_count=10,
                   deadline_seconds=None, progress=None):
    """Return unique original indices in selection order; ties use smallest index.

    All rows remain eligible. Duplicate-valued rows may be selected but the same
    candidate index cannot recur. `deadline_seconds` bounds this selector call.
    """
    if not isinstance(projected, torch.Tensor):
        projected = torch.as_tensor(projected, dtype=torch.float32)
    if projected.device.type != 'cpu' or projected.dtype != torch.float32:
        raise ValueError('Selection requires CPU float32 projected candidates')
    if projected.ndim != 2 or not projected.shape[1] or not torch.isfinite(projected).all():
        raise ValueError('Finite nonempty candidate matrix required')
    n = len(projected)
    if count < 1 or count > n or initial_count < 1 or seed < 0:
        raise ValueError('Invalid requested count, anchor count or seed')
    if deadline_seconds is not None and deadline_seconds < 0:
        raise ValueError('Nonnegative deadline required')
    if deadline_seconds == 0:
        raise ResourceGateError('No selector time remains')
    started = time.perf_counter()
    anchors = np.random.default_rng(seed).choice(n, min(initial_count, n), replace=False)
    squared_norms = torch.linalg.vector_norm(projected, dim=1).square_()

    def distance(index):
        v = projected[index]
        return (squared_norms + torch.dot(v, v) - 2 * torch.mv(projected, v)).clamp_min_(0).sqrt_()

    def check_deadline():
        if deadline_seconds is not None and time.perf_counter() - started > deadline_seconds:
            raise ResourceGateError('Approximate-greedy selection exceeded its normal-only deadline')

    minimum = torch.zeros(n, dtype=torch.float32)
    for index in anchors:
        check_deadline()
        minimum.add_(distance(int(index)))
    minimum.div_(len(anchors))
    selected = np.empty(count, dtype=np.int64)
    for step in range(count):
        check_deadline()
        index = int(torch.argmax(minimum))
        selected[step] = index
        torch.minimum(minimum, distance(index), out=minimum)
        # Explicit exclusion prevents repeated argmax on all-identical vectors.
        minimum[index] = -float('inf')
        if progress is not None and (step % 128 == 0 or step == count - 1):
            progress(step + 1, count, time.perf_counter() - started)
    check_deadline()
    if len(np.unique(selected)) != count:
        raise RuntimeError('Selector produced duplicate indices')
    return selected

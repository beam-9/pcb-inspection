import json
import time

import numpy as np
import pandas as pd
import pytest
import torch

from pcb_inspection import memory_experiment as runner


def config(count=8):
    return {"memory_count": count, "caps": {"preparation_seconds": 1800,
             "peak_rss_bytes": 8 * 1024 ** 3, "median_inference_seconds": 10}}


def transform(size=256):
    return {"pad_x": 0, "pad_y": size // 4, "content_width": size,
            "content_height": size // 2, "fallback": False}


class FakeExtractor:
    @staticmethod
    def feature(image_index, size):
        grid = size // 8
        channels = torch.arange(384, dtype=torch.float32)[:, None, None]
        cells = torch.arange(grid * grid, dtype=torch.float32).reshape(1, grid, grid)
        return image_index * 10 + channels / 100 + cells / 1000

    def __call__(self, batch):
        return torch.stack([self.feature(float(x[0, 0, 0]), batch.shape[-1]) for x in batch])


def fake_input(root, row, size):
    assert row.label == "normal"
    return torch.full((3, size, size), float(row.image_id[-1])), transform(size)


def test_stream_reextraction_retains_selection_order_and_original_channels(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "tensor_and_transform", fake_input)
    fit = pd.DataFrame({"image_id": ["fit0", "fit1", "fit2"], "label": ["normal"] * 3})
    selected = np.array([3071, 0, 1025, 31, 2048, 1000, 1024, 2000])
    memory, transforms = runner.reextract_selected(tmp_path, 256, selected, fit,
        FakeExtractor(), time.perf_counter(), config())
    assert memory.shape == (8, 384)
    for i, flat in enumerate(selected):
        image, cell = divmod(int(flat), 1024)
        row, column = divmod(cell, 32)
        assert torch.equal(memory[i], FakeExtractor.feature(image, 256)[:, row, column])
    refs = runner.reference_metadata(selected, fit, transforms, 256)
    assert [r["flat_index"] for r in refs] == selected.tolist()
    assert [r["selection_order"] for r in refs] == list(range(8))
    assert refs[0]["image_id"] == "fit2"
    assert refs[0]["is_padding_center"] is True


def test_projection_streams_only_fitting_normals(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "tensor_and_transform", fake_input)
    manifest = tmp_path / runner.MANIFEST
    manifest.parent.mkdir(parents=True)
    pd.DataFrame({"image_id": ["fit0", "fit1", "anomaly2"],
                  "label": ["normal", "normal", "anomaly"],
                  "split": ["fit", "fit", "test"]}).to_csv(manifest, index=False)
    projected, fit, transforms, projection = runner.project_candidates(tmp_path, 256,
        tmp_path / "candidate.npy", time.perf_counter(), config(), extractor=FakeExtractor())
    assert projected.shape == (2048, 64) and projected.dtype == np.float32
    assert fit.image_id.tolist() == ["fit0", "fit1"]
    assert set(transforms) == {"fit0", "fit1"}
    full = torch.cat([FakeExtractor.feature(i, 256).permute(1, 2, 0).reshape(-1, 384) for i in [0, 1]])
    np.testing.assert_allclose(projected[[0, 125, 2047]], (full @ projection)[[0, 125, 2047]].numpy(), rtol=2e-6, atol=2e-6)
    with pytest.raises(FileExistsError):
        runner.project_candidates(tmp_path, 256, tmp_path / "candidate.npy",
            time.perf_counter(), config(), extractor=FakeExtractor())


@pytest.mark.parametrize("selected", [[0, 0], [-1, 1], [0, 3], [0., 1.], [0]])
def test_invalid_selection_rejected(selected):
    with pytest.raises(ValueError):
        runner.validate_selected(np.asarray(selected), candidate_count=3, count=2)


def test_padding_center_and_resource_gate():
    assert runner.padding_center(0, 3, transform())
    assert not runner.padding_center(8, 3, transform())
    assert runner.padding_center(24, 3, transform())
    with pytest.raises(RuntimeError, match="latency"):
        runner.check_resources(time.perf_counter(), config(), 11)
    with pytest.raises(RuntimeError, match="deadline"):
        runner.check_resources(time.perf_counter() - 2000, config())


def test_coverage_distances_original_feature_space_and_overlap():
    queries = torch.zeros(3, 384)
    queries[:, 0] = torch.tensor([0., 1., 5.])
    bank = torch.zeros(2, 384)
    bank[1, 0] = 3
    summary, distances, indices = runner.coverage_diagnostics(queries, bank,
        np.array([1, 2, 4]), np.array([1, 3]))
    np.testing.assert_array_equal(distances, [0, 1, 2])
    np.testing.assert_array_equal(indices, [0, 0, 1])
    assert summary["dimensions"] == 384 and summary["units"] == "Euclidean"
    assert summary["mean"] == summary["median"] == 1
    assert summary["query_index_in_bank_count"] == summary["zero_distance_count"] == 1


def test_evaluate_rejects_failed_prepare_before_access(monkeypatch, tmp_path):
    out = tmp_path / "artifacts/runs/coreset_256_v1"
    out.mkdir(parents=True)
    (out / "prepared.json").write_text(json.dumps({"resource_gate_passed": False}))
    monkeypatch.setattr(runner, "verify_recipe", lambda root, out: {})
    monkeypatch.setattr(runner, "setup", lambda root: None)
    with pytest.raises(AssertionError):
        runner.evaluate(tmp_path, 256)
    assert not (out / "development_access.json").exists()

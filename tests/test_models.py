import numpy as np
from PIL import Image
import pytest
import torch

from pcb_inspection.preprocessing import preprocess_image, preprocess_mask, FrozenPatchExtractor
from pcb_inspection.baseline import FrozenEmbeddingBaseline
from pcb_inspection.patchcore import PatchCoreInspired
from pcb_inspection.calibration import calibrate, flag
from pcb_inspection.evaluation import image_metrics, localization_metrics


def test_preprocessing_geometry_determinism_and_mask():
    rgb = np.zeros((17, 39, 3), dtype=np.uint8)
    rgb[:, 20:, 0] = 255
    image = Image.fromarray(rgb)
    assert torch.equal(preprocess_image(image), preprocess_image(image))
    assert preprocess_image(image).shape == (3, 256, 256)
    mask = preprocess_mask(Image.fromarray(rgb[:, :, 0]))
    assert mask.dtype == bool and mask.shape == (256, 256)
    assert not mask[:, :100].any() and mask[:, 150:].all()


def test_frozen_backbone_geometry_without_weight_download():
    torch.manual_seed(42)
    model = FrozenPatchExtractor(weights=False)
    torch.set_num_threads(2)
    result = model(torch.zeros(1, 3, 256, 256))
    assert result.shape == (1, 384, 32, 32)
    assert not any(p.requires_grad for p in model.parameters())
    assert torch.isfinite(result).all()


def test_baseline_is_l2_normalized_nearest_reference():
    fit = torch.tensor([[[[1.]], [[0.]]], [[[0.]], [[1.]]]])
    model = FrozenEmbeddingBaseline().fit(fit, ["fit-a", "fit-b"])
    scored = model.score(fit * 4)
    np.testing.assert_array_equal(scored["scores"], [0, 0])
    assert scored["reference_ids"] == ["fit-a", "fit-b"]
    assert np.isclose(model.score(torch.ones(1, 2, 1, 1))["scores"][0], np.sqrt(2-np.sqrt(2)))
    with pytest.raises(ValueError, match="Test IDs"):
        model.assert_no_test_ids(["fit-a"])


def test_sampling_provenance_leakage_and_reproducibility():
    fit = torch.arange(24, dtype=torch.float32).reshape(2, 3, 2, 2)
    first = PatchCoreInspired(max_memory=5).fit(fit, ["a", "b"])
    second = PatchCoreInspired(max_memory=5).fit(fit, ["a", "b"])
    assert first.metadata == second.metadata
    assert torch.equal(first.memory, second.memory)
    for ref, row in zip(first.metadata, first.memory):
        image = ["a", "b"].index(ref["image_id"])
        assert torch.equal(row, fit[image, :, ref["row"], ref["column"]])
    first.assert_no_test_ids(["test"])
    with pytest.raises(ValueError, match="Test IDs"):
        first.assert_no_test_ids(["b"])


def test_patch_distance_geometry_score_and_nearest_ties():
    fit = torch.zeros(1, 2, 2, 2)
    model = PatchCoreInspired(max_memory=4, chunk_size=1).fit(fit, ["normal"])
    query = fit.clone(); query[0, :, 1, 1] = torch.tensor([3., 4.])
    output = model.score(query)
    assert output["scores"].tolist() == [5.]
    assert output["maps"].shape == (1, 256, 256)
    assert output["maps"][0, 0, 0] == 0 and output["maps"][0, -1, -1] == 5
    assert (output["nearest_indices"] == 0).all()
    np.testing.assert_array_equal(model.score(fit)["scores"], [0])
    with pytest.raises(ValueError, match="geometry"):
        model.score(torch.zeros(1, 2, 1, 1))


def test_threshold_quantile_and_ties():
    calibration = calibrate(np.arange(20), np.arange(80).reshape(20, 2, 2))
    assert calibration["image_threshold"] == 19
    assert calibration["pixel_threshold"] == 79
    assert flag([18, 19, 20], 19).tolist() == [False, False, True]


def test_independent_confusion_arithmetic_and_localization():
    result = image_metrics([0, 0, 1, 1], [0, 4, 2, 5], 3)
    assert [result[k] for k in ("tp", "fp", "fn", "tn")] == [1, 1, 1, 1]
    assert result["precision"] == result["recall"] == result["normal_false_alarm_rate"] == .5
    assert result["auroc"] == .75
    assert np.isclose(result["average_precision"], 5/6)
    masks = np.array([[[0, 1], [0, 1]], [[0, 0], [0, 0]]])
    maps = np.array([[[0, 5], [1, 4]], [[0, 0], [0, 0]]])
    loc = localization_metrics(masks, maps, 3)
    assert loc["pixel_average_precision"] == loc["pixel_iou"] == 1
    assert loc["n_pixels"] == 8 and loc["positive_pixels"] == 2


def test_single_class_and_empty_invalid_cases():
    result = image_metrics([0, 0], [0, 1], 1)
    assert result["auroc"] is None and result["average_precision"] is None
    assert result["precision"] is None and result["recall"] is None
    assert localization_metrics(np.zeros((1, 2, 2)), np.zeros((1, 2, 2)), 1)["pixel_iou"] is None
    for invalid in ([], [np.nan], [np.inf]):
        with pytest.raises(ValueError):
            calibrate(invalid)
    with pytest.raises(ValueError):
        image_metrics([2], [1], 0)
    with pytest.raises(ValueError):
        localization_metrics(np.zeros((1, 2, 2)), np.zeros((1, 3, 3)), 1)


def test_invalid_features_ids_and_unfitted_models():
    for cls in (FrozenEmbeddingBaseline, PatchCoreInspired):
        with pytest.raises(RuntimeError):
            cls().score(torch.zeros(1, 2, 2, 2))
        with pytest.raises(ValueError):
            cls().fit(torch.full((1, 2, 2, 2), float("nan")), ["a"])
        with pytest.raises(ValueError):
            cls().fit(torch.zeros(2, 2, 2, 2), ["a", "a"])


def test_score_overflow_rejected():
    model = PatchCoreInspired().fit(torch.zeros(1, 2, 2, 2), ["normal"])
    with pytest.raises(ValueError, match="Nonfinite"):
        model.score(torch.full((1, 2, 2, 2), 1e38))

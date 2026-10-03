import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from pcb_inspection import stage4_transfer as runner
from pcb_inspection.guard import digest


def config():
    return {"selector": {"memory_count": 4096, "all_fitting_candidates": True, "projection_dimensions": 64,
            "scoring_dimensions": 384, "projection_seed": 43, "selection_seed": 42, "initial_anchor_count": 10},
            "calibration": {"image_quantile": .95, "pixel_quantile": .99, "method": "higher", "comparison": ">"},
            "geometry": {"mode": "inherited_blue"}, "retuning_after_unseal": False,
            "anomaly_access_before_finalfreeze": False}


def normals():
    return pd.DataFrame({"image_id": ["fit", "cal", "held"], "image_path": ["data/raw/normal.jpg"] * 3,
                         "sha256": ["fit-sha", "cal-sha", "held-sha"], "label": ["normal"] * 3,
                         "split": ["fit", "calibration", "normal_test"]})


def write_normals(root, frame):
    path = root / runner.NORMAL_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def test_frozen_selector_and_calibration_controls():
    runner.validate_config(config())
    for key, value in [("memory_count", 8192), ("projection_seed", 44), ("all_fitting_candidates", False)]:
        altered = config(); altered["selector"][key] = value
        with pytest.raises(ValueError): runner.validate_config(altered)
    altered = config(); altered["calibration"]["comparison"] = ">="
    with pytest.raises(ValueError): runner.validate_config(altered)
    altered = config(); altered["geometry"] = "pending"
    with pytest.raises(ValueError): runner.validate_config(altered)


def test_normal_manifest_rejects_annotations_and_cross_split_duplicates(tmp_path):
    frame = normals(); write_normals(tmp_path, frame)
    assert runner.normal_frame(tmp_path, config()).split.tolist() == ["fit", "calibration", "normal_test"]
    frame["defect_types"] = ["", "", '["scratch"]']; write_normals(tmp_path, frame)
    with pytest.raises(ValueError, match="annotations"): runner.normal_frame(tmp_path, config())
    frame = normals(); frame.loc[2, "sha256"] = "fit-sha"; write_normals(tmp_path, frame)
    with pytest.raises(ValueError, match="leakage"): runner.normal_frame(tmp_path, config())


def test_anomaly_and_heldout_guards_precede_any_pixel_access(tmp_path):
    row = SimpleNamespace(label="anomaly", split="test", image_path="does-not-exist", sha256="none")
    with pytest.raises(ValueError, match="sealed"): runner.tensor_and_transform(tmp_path, row, 256, config())
    row = SimpleNamespace(label="normal", split="normal_test", image_path="does-not-exist", sha256="none")
    with pytest.raises(ValueError, match="Held-out"): runner.tensor_and_transform(tmp_path, row, 256, config())
    assert not (tmp_path / "artifacts/stage4/anomaly_access.json").exists()


def test_secondary_cannot_unseal_and_primary_is_exclusive(monkeypatch, tmp_path):
    stage = tmp_path / "artifacts/stage4"; stage.mkdir(parents=True)
    (stage / "freeze_receipt.json").write_text(json.dumps({"config": config(), "frozen_files": {}}))
    (stage / "pcb2_d1_primary").mkdir(); (stage / "pcb2_d2_secondary").mkdir()
    monkeypatch.setattr(runner, "verify_prepared", lambda root, out: {})
    with pytest.raises(ValueError, match="Primary"): runner.claim_confirmation(tmp_path, "secondary")
    assert not (stage / "anomaly_access.json").exists()
    runner.claim_confirmation(tmp_path, "primary")
    assert json.loads((stage / "anomaly_access.json").read_text())["freeze_receipt_sha256"] == digest(stage / "freeze_receipt.json")
    with pytest.raises(FileExistsError): runner.claim_confirmation(tmp_path, "primary")


def test_root_relative_prepared_array_hashes(monkeypatch, tmp_path):
    stage = tmp_path / "artifacts/stage4"; stage.mkdir(parents=True)
    (stage / "normal_protocol.json").write_text("{}")
    out = stage / "pcb2_d1_primary"; out.mkdir()
    cache = tmp_path / "data/cache/stage4/pcb2_d1_primary/memory.npy"
    cache.parent.mkdir(parents=True); cache.write_bytes(b"synthetic-array")
    prepared = {"resource_gate_passed": True, "normal_only": True, "normal_test_decoded": False,
                "normal_protocol_sha256": digest(stage / "normal_protocol.json"),
                "prerequisites": {str(cache.relative_to(tmp_path)): digest(cache)}}
    (out / "prepared.json").write_text(json.dumps(prepared))
    monkeypatch.setattr(runner, "normal_protocol", lambda root: {})
    runner.verify_prepared(tmp_path, out)
    cache.write_bytes(b"changed")
    with pytest.raises(ValueError, match="artifact changed"): runner.verify_prepared(tmp_path, out)


def test_confirmation_manifest_exact_heldout_identity_and_no_leakage():
    frame = pd.DataFrame({"image_id": ["held", "new"], "image_path": ["held.jpg", "new.jpg"],
                          "sha256": ["held-sha", "new-sha"], "label": ["normal", "anomaly"],
                          "mask_path": ["", "mask.png"], "mask_sha256": ["", "mask-sha"]})
    runner.validate_test_frame(frame, normals())
    changed = frame.copy(); changed.loc[0, "sha256"] = "unknown"
    with pytest.raises(ValueError, match="held-out"): runner.validate_test_frame(changed, normals())
    changed = frame.copy(); changed.loc[1, "sha256"] = "fit-sha"
    with pytest.raises(ValueError, match="leakage"): runner.validate_test_frame(changed, normals())


def test_new_transfer_files_do_not_need_report_module():
    assert "stage4_transfer" in runner.FROZEN_MODULES
    assert "stage4_review" in runner.FROZEN_MODULES
    assert "stage4_report" not in runner.FROZEN_MODULES

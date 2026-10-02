"""The actual production config agrees with model and preprocessing constants."""
from pathlib import Path
import yaml
from pcb_inspection.preprocessing import IMAGE_SIZE, PREPROCESSING_ID
from pcb_inspection.calibration import calibrate


def test_config_matches_fixed_implementations():
    root=Path(__file__).resolve().parents[1]
    config=yaml.safe_load((root/'configs/pilot.yaml').read_text())
    assert config['input_size']==IMAGE_SIZE==256
    assert config['backbone']=='resnet18' and config['weights']=='IMAGENET1K_V1'
    assert config['feature_layers']==['layer2','layer3']
    assert config['device']=='cpu' and config['map_normalization']=='none'
    thresholds=calibrate([0,1])
    assert thresholds['image_quantile']==config['image_threshold_quantile']
    assert thresholds['pixel_quantile']==config['pixel_threshold_quantile']
    assert thresholds['quantile_method']==config['quantile_method']
    assert config['threshold_comparison']=='strict_greater' and thresholds['comparison']=='>'

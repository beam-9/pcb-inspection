"""Hash-verified frozen PCB-AD-v1.0 inference. No fitting or calibration."""
import base64
from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
import threading
import time
import warnings

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
import torch

from .guard import digest
from .geometry_experiment import DynamicExtractor, setup, score_feature
from .stage4_geometry import geometry_for
from .stage5a_pose import classify_pose
from .stage5b_orientation import orientation_tensor, orientation_inverse_map

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
FORMATS = {'JPEG', 'PNG', 'WEBP'}


class UnsupportedImage(ValueError):
    pass


def decode_image(data):
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise UnsupportedImage('Choose a JPEG, PNG or WebP image smaller than 12 MiB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in FORMATS or image.width * image.height > MAX_IMAGE_PIXELS or min(image.size) < 32:
                    raise UnsupportedImage('Use a JPEG, PNG or WebP, at least 32 pixels per side and at most 16 megapixels.')
                if getattr(image, 'n_frames', 1) != 1:
                    raise UnsupportedImage('Use a still image; animated images are unsupported.')
                image.load()
                return ImageOps.exif_transpose(image).convert('RGB').copy()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning, SyntaxError) as exc:
        raise UnsupportedImage('This image could not be decoded. Choose a valid JPEG, PNG or WebP.') from exc


def load_metadata(root, verify_runtime=False):
    root = Path(root).resolve(); folder = root/'artifacts/model_v1'
    receipt = json.loads((folder/'final_model_receipt.json').read_text())
    for name, expected in receipt['artifact_identities'].items():
        if digest(root/name) != expected:
            raise ValueError('Frozen model artifact changed: '+name)
    config = json.loads((folder/'final_config.json').read_text())
    if verify_runtime:
        for name, expected in receipt['runtime_identities'].items():
            if digest(root/name) != expected:
                raise ValueError('Frozen inference identity changed: '+name)
        bank = np.load(root/config['memory']['path'], allow_pickle=False, mmap_mode='r')
        if bank.shape != tuple(config['memory']['shape']) or bank.dtype != np.float32:
            raise ValueError('Frozen bank shape/type changed')
    return {
        'name': receipt['model_name'], 'version': receipt['version'], 'recipe_commit': receipt['git_commit'],
        'frozen_at': receipt['freeze_timestamp'], 'input_size': config['input_size'],
        'backbone': config['backbone'], 'feature_layers': config['feature_layers'],
        'memory_size': config['memory']['shape'][0], 'thresholds': config['thresholds'],
        'metrics': json.loads((folder/'final_metrics.json').read_text()),
        'limitations': config['limitations'], 'config': config,
    }


@dataclass
class Inspection:
    metadata: dict
    original: Image.Image
    pose_label: str
    score: float
    model_map: np.ndarray
    common_map: np.ndarray
    source_map: np.ndarray
    transform: dict
    runtime: dict
    pose_details: dict

    @property
    def is_anomalous(self):
        return self.score > self.metadata['thresholds']['image_threshold']

    def payload(self):
        """Display assets use one fixed ratio scale, never per-image min/max."""
        preview = self.original.copy(); preview.thumbnail((1100, 1100))
        scores = np.asarray(Image.fromarray(self.source_map).resize(preview.size, Image.Resampling.BILINEAR))
        pt = self.metadata['thresholds']['pixel_threshold']
        ratio = np.clip(scores/pt/2, 0, 1)
        palette = np.array([[13, 10, 25], [55, 38, 97], [144, 50, 112], [236, 108, 61], [255, 231, 147]], dtype=float)
        step = ratio * (len(palette)-1); lower = np.floor(step).astype(int); upper = np.minimum(lower+1, len(palette)-1)
        rgb = (palette[lower]*(1-(step-lower)[...,None])+palette[upper]*(step-lower)[...,None]).astype(np.uint8)
        thresholded = Image.fromarray((self.source_map>pt).astype(np.uint8)*255).resize(preview.size, Image.Resampling.NEAREST)
        return {
            'model_name': self.metadata['name'], 'model_version': self.metadata['version'],
            'pose_label': self.pose_label, 'normalization_applied': self.pose_label == 'reversed_180',
            'anomaly_score': self.score, 'image_threshold': self.metadata['thresholds']['image_threshold'],
            'pixel_threshold': pt, 'is_anomalous': self.is_anomalous,
            'original': png_url(preview), 'heatmap': png_url(Image.fromarray(rgb)),
            'thresholded_map': png_url(thresholded), 'runtime': self.runtime,
            'crop_fallback': self.transform['fallback'], 'crop_box': self.transform['crop_box'],
            'source_size': list(self.original.size), 'display_size': list(preview.size),
            'heatmap_scale': 'Response / frozen pixel threshold, fixed 0–2; values above 2 clipped for display.',
            'pose_uncertainty_reason': self.pose_details.get('uncertainty_reason', ''),
        }


def png_url(image):
    stream = BytesIO(); image.save(stream, format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode('ascii')


class FrozenInspector:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.metadata = load_metadata(self.root, verify_runtime=True)
        config = self.metadata['config']; setup(self.root)
        # setup points torchvision's cached weights at the hash-verified local file.
        self.extractor = DynamicExtractor()
        self.bank = torch.from_numpy(np.load(self.root/config['memory']['path'], allow_pickle=False))
        self.lock = threading.Lock()

    def inspect(self, image):
        """Accept decoded RGB or bytes; callers never supply masks or pose labels."""
        tick = time.perf_counter()
        image = decode_image(image) if isinstance(image, bytes) else ImageOps.exif_transpose(image).convert('RGB').copy()
        if image.width*image.height>MAX_IMAGE_PIXELS or min(image.size)<32:
            raise UnsupportedImage('Image dimensions exceed the supported limits.')
        with self.lock:
            start = time.perf_counter(); config = self.metadata['config']
            geometry = geometry_for(image, config['geometry'])
            pose = classify_pose(image, geometry['board_box'])
            tensor, transform = orientation_tensor(image, geometry, pose['pose_label'], config['input_size'])
            prepared = time.perf_counter()
            features = self.extractor(tensor[None])
            score, model, _ = score_feature(features, self.bank, config['input_size'], transform)
            scored = time.perf_counter()
            common = orientation_inverse_map(model, transform, pose['pose_label'], 256)
            source = orientation_inverse_map(model, transform, pose['pose_label'])
            end = time.perf_counter()
        return Inspection(self.metadata, image, pose['pose_label'], score, model, common, source, transform,
                          {'preprocessing_seconds': prepared-start, 'feature_scoring_seconds': scored-prepared,
                           'inverse_map_seconds': end-scored, 'end_to_end_seconds': end-tick,
                           'timing_boundary': 'Decode/preprocess/features/scoring including historical common inverse, then orientation-aware common/source inverse; excludes display PNG encoding.'}, pose)

"""Collect useful runtime facts without host/person identifiers."""
import importlib.metadata
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
import psutil
import torch


def report():
    return {
        'measured_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'platform': platform.system(),
        'architecture': platform.machine(),
        'processor': 'Apple M2 Pro (system hardware inspection)',
        'logical_cpus': psutil.cpu_count(),
        'ram_bytes': psutil.virtual_memory().total,
        'disk_free_bytes': shutil.disk_usage('.').free,
        'mps_available': torch.backends.mps.is_available(),
        'mps_built': torch.backends.mps.is_built(),
        'declared_device': 'cpu',
        'packages': {p:importlib.metadata.version(p) for p in [
            'torch','torchvision','numpy','pandas','scikit-learn','Pillow',
            'pytest','pydantic','pyarrow','nbformat','nbclient','psutil']},
    }

"""Content-bound prerequisites and exclusive test access registration."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def verify_frozen(root, protocol):
    root = Path(root)
    for relative, expected in protocol['frozen_files'].items():
        if digest(root / relative) != expected:
            raise ValueError(f'Frozen identity mismatch: {relative}')
    if not protocol.get('source_terms_resolved'):
        raise ValueError('Source/weight terms unresolved')


def claim_test_access(root, protocol, run_id, prerequisite_files):
    verify_frozen(root, protocol)
    for name, expected in prerequisite_files.items():
        if digest(Path(root) / name) != expected:
            raise ValueError(f'Prerequisite changed: {name}')
    write_new(Path(root) / 'artifacts' / 'test_access.json', {
        'first_model_test_access_utc': now(), 'run_id': run_id,
        'protocol_sha256': digest(Path(root) / 'docs/protocol.json'),
        'prerequisite_files': prerequisite_files,
        'scope': 'One final evaluation of both frozen methods; no retuning',
        'prior_access': 'Structural data audit only; no held-out model scoring or visual review',
    })

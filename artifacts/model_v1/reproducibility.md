# Reproduce the frozen detector

Use Python3.11 and `requirements.lock`, plus the original local VisA data, exact ordered D2 bank and cached ResNet18 weights. Ignored files are not present in a Git clone. `FrozenInspector` verifies their SHA256 and the effective scientific code before loading. It never fits a bank or calibrates thresholds.

Run `PYTHONPATH=src .venv/bin/python -m pcb_inspection.demo_server --root . --port 8765` from the repository. Then open `http://127.0.0.1:8765`. Run `PYTHONPATH=src .venv/bin/python scripts/check_model_v1_smoke.py` for matched saved-array checks. Uploads remain in memory and are not saved. The server binds loopback only and is a local demo, not an Internet service.

The recipe commit pins published scientific code. New wrapper/UI source identities are separately bound in the productization completion receipt; no unpublished commit ID is invented. Scientific receipts retain their original creation-state fields.

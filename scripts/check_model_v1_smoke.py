"""Compare the wrapper to representative saved Stage5C outputs; no tuning."""
import json
import argparse
from pathlib import Path
import numpy as np
from pcb_inspection.model_v1 import FrozenInspector
from pcb_inspection.guard import digest, now, write_new

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    manifest=json.loads((ROOT/'tests/model_v1_smoke_manifest.json').read_text())
    assert digest(ROOT/'artifacts/model_v1/final_model_receipt.json')==manifest['model_receipt_sha256']
    inspector=FrozenInspector(ROOT);checks=[]
    for case in manifest['cases']:
        path=ROOT/case['image_path'];assert digest(path)==case['image_sha256']
        result=inspector.inspect(path.read_bytes())
        assert abs(result.score-case['score'])<=manifest['score_map_tolerance']
        assert result.is_anomalous==case['detected'] and result.pose_label==case['pose_label']
        errors={}
        for key,actual in [('model_maps',result.model_map),('anomaly_maps',result.common_map),('source_maps',result.source_map)]:
            source=ROOT/case['maps'][key];assert digest(source)==case['map_hashes'][key]
            error=float(np.abs(actual-np.load(source)).max());assert error<=manifest['score_map_tolerance'],(case['id'],key,error);errors[key]=error
        checks.append({'id':case['id'],'image_id':case['image_id'],'pose':result.pose_label,'score_error':abs(result.score-case['score']),
                       'flag_exact':True,'map_max_errors':errors,'runtime':result.runtime})
        print(case['id'],result.pose_label,result.score,'matched',flush=True)
    if not args.verify_only:
        write_new(ROOT/'artifacts/productization/model_v1_smoke.json',{'passed':True,'created_at_utc':now(),'checks':checks,
           'model_receipt_sha256':manifest['model_receipt_sha256'],'wrapper_code_sha256':digest(ROOT/'src/pcb_inspection/model_v1.py')})

if __name__=='__main__':main()

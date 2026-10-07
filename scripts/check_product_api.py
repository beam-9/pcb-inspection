"""Bounded checks of the running local demo's public contract."""
import json
import argparse
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from pcb_inspection.guard import write_new,now,digest
ROOT=Path(__file__).resolve().parents[1];URL='http://127.0.0.1:8765'

def get(path):
    with urlopen(URL+path,timeout=60) as response:return response.status,response.read()

def post(path,data,content_type):
    try:
        with urlopen(Request(URL+path,data=data,headers={'Content-Type':content_type}),timeout=60) as response:return response.status,json.load(response)
    except HTTPError as exc:return exc.code,json.load(exc)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    status,body=get('/health');assert status==200 and json.loads(body)['status']=='ready'
    metadata=json.loads(get('/model-info')[1]);receipt=json.loads((ROOT/'artifacts/model_v1/final_model_receipt.json').read_text())
    assert metadata['name']==receipt['model_name'] and metadata['thresholds']['image_threshold']==receipt['image_threshold']
    assert len(json.loads(get('/api/journey')[1])['stages'])==9
    status,result=post('/api/inspect-example',b'{"id":"known_small_missing_miss"}','application/json')
    assert status==200 and not result['is_anomalous'] and 'ground_truth' in result
    case=next(c for c in json.loads((ROOT/'tests/model_v1_smoke_manifest.json').read_text())['cases'] if c['id']=='reversed_anomaly')
    status,upload=post('/api/inspect',(ROOT/case['image_path']).read_bytes(),'image/jpeg')
    assert status==200 and upload['normalization_applied'] and upload['pose_label']=='reversed_180' and 'ground_truth' not in upload
    assert upload['is_anomalous']==(upload['anomaly_score']>upload['image_threshold'])
    assert post('/api/inspect',b'invalid','image/jpeg')[0]==400
    assert post('/api/inspect-example',b'{"id":"nonexistent"}','application/json')[0]==400
    assert post('/api/inspect-example',b'[]','application/json')[0]==400
    assert post('/api/inspect',b'','image/jpeg')[0]==413
    try:get('/evidence/../../.git/config');raise AssertionError('Traversal allowed')
    except HTTPError as exc:assert exc.code==404
    if not args.verify_only:
        write_new(ROOT/'artifacts/productization/api_validation.json',{'passed':True,'created_at_utc':now(),'model_metadata_matches_receipt':True,'real_upload_reversed_action':True,'benchmark_known_miss_retained':True,'uploaded_image_no_GT':True,'invalid_image_unknown_example_invalid_json_empty_upload_rejected':True,'path_traversal_rejected':True,'receipt_sha256':digest(ROOT/'artifacts/model_v1/final_model_receipt.json')})
    print('API contract, real upload, known miss, errors and route containment passed')

if __name__=='__main__':main()

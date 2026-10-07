"""Export six verified frozen results for a clearly labelled static portfolio."""
import json
from pathlib import Path
from pcb_inspection.demo_server import DemoApplication
from pcb_inspection.guard import digest, now, write_new

ROOT=Path(__file__).resolve().parents[1]

def main():
    app=DemoApplication(ROOT)
    output=ROOT/'content/benchmark_results';output.mkdir(exist_ok=False)
    checks=[]
    for identity,case in app.cases.items():
        result=app.inspect_example(identity)
        assert abs(result['anomaly_score']-case['score'])<=1e-5
        assert result['is_anomalous']==case['detected'] and result['pose_label']==case['pose_label']
        result['inspection_kind']='saved_preview'
        result['recorded_at_utc']=now()
        result['model_receipt_sha256']=digest(ROOT/'artifacts/model_v1/final_model_receipt.json')
        write_new(output/(identity+'.json'),result)
        checks.append({'id':identity,'sha256':digest(output/(identity+'.json')),'score_matches_saved_stage5c':True})
    write_new(ROOT/'artifacts/productization/public_export.json',{'passed':True,'created_at_utc':now(),
        'scope':'Six recorded frozen inferences; static preview never claims a new inspection.',
        'checks':checks,'model_receipt_sha256':digest(ROOT/'artifacts/model_v1/final_model_receipt.json')})
    print('Exported six verified saved results; no fitting, calibration or detector changes.')

if __name__=='__main__':main()

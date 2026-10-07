"""Formalize the existing scientific recipe, once. No detector inference."""
import json
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from pcb_inspection.guard import digest, write_new, now
from pcb_inspection.stage5a_pose import METHOD

ROOT=Path(__file__).resolve().parents[1]
LIMITATIONS=[
 'PCB2 became exposed development data after Stage 4; this final candidate is not another fresh confirmation.',
 'Only five reversed anomalies were available, with no reversed PCB2 normal controls.',
 'Arbitrary rotations are unsupported; uncertain pose is a no-op.',
 'Canonical missing and small defects remain the primary known weakness; a no-flag result can miss anomalies.',
 'Annotations can be union masks across multiple defect types.',
 'Anomaly response is not a calibrated probability; highlighted regions are not precise segmentation.',
 'Physical board identity is not fully controlled.',
 'No factory robustness study was performed; not certified for manufacturing decisions.',
 'The D2 bank is PCB2-specific; arbitrary board categories and capture conditions are outside demonstrated coverage.',
 'PCB1 evidence describes the staged development history, not a fresh test of this final PCB2 bank/orientation recipe.'
]

def main():
    root=ROOT; out=root/'artifacts/model_v1';out.mkdir(exist_ok=False)
    stage=root/'artifacts/stage5c';historical=root/'artifacts/stage4/pcb2_d2_secondary'
    paths=json.loads((historical/'array_paths.json').read_text());cal=json.loads((historical/'calibration.json').read_text())
    bank=np.load(root/paths['memory'],allow_pickle=False);assert bank.shape==(4096,384) and bank.dtype==np.float32 and np.isfinite(bank).all()
    geometry=json.loads((root/'artifacts/stage4/freeze_receipt.json').read_text())['config']['geometry']
    config={'model_name':'PCB-AD-v1.0','version':'1.0','input_size':512,'geometry':geometry,
            'orientation':{'method':METHOD,'actions':{'canonical':'no_op','reversed_180':'exact_180_crop_reversal','uncertain':'no_op'}},
            'backbone':'ResNet18 IMAGENET1K_V1','weights_path':'data/cache/hub/checkpoints/resnet18-f37072fd.pth',
            'feature_layers':['layer2','layer3'],'feature_dimensions':384,
            'feature_aggregation':'avg_pool2d3 stride1 pad1 per layer; bilinear layer3 to layer2 align_corners=False',
            'memory':{'path':paths['memory'],'shape':[4096,384],'dtype':'float32','selection':'historical D2 projected approximate-greedy selection; preserve order', 'sha256':digest(root/paths['memory'])},
            'distance':'full384 direct Euclidean CPU against all4096 references',
            'image_aggregation':'maximum all native feature-grid scores including padding patches',
            'thresholds':{'image_threshold':cal['image_threshold'],'pixel_threshold':cal['pixel_threshold'],'comparison':'>'},
            'map_semantics':'bilinear native patch distances to512; unpad/crop-resize/inverse180 when reversed/paste source; common256 direct-square for historical metrics',
            'device':'cpu','threads':4,'limitations':LIMITATIONS,'intended_use':'Research and portfolio demonstration of one-class visual anomaly detection for PCB inspection.'}
    write_new(out/'final_config.json',config)
    metrics=json.loads((stage/'results/full_metrics.json').read_text());write_new(out/'final_metrics.json',metrics)
    (out/'final_bank_hash.txt').write_text(config['memory']['sha256']+'\n')
    (out/'limitations.md').write_text('# PCB-AD-v1.0 limitations\n\n'+'\n'.join('- '+s for s in LIMITATIONS)+'\n')
    (out/'reproducibility.md').write_text('# Reproduce the frozen detector\n\nUse Python3.11 and `requirements.lock`, plus the original local VisA data, exact ordered D2 bank and cached ResNet18 weights. Ignored files are not present in a Git clone. `FrozenInspector` verifies their SHA256 and the effective scientific code before loading. It never fits a bank or calibrates thresholds.\n\nRun `PYTHONPATH=src .venv/bin/python -m pcb_inspection.demo_server --root . --port 8765` from the repository. Then open `http://127.0.0.1:8765`. Run `PYTHONPATH=src .venv/bin/python scripts/check_model_v1_smoke.py` for matched saved-array checks. Uploads remain in memory and are not saved. The server binds loopback only and is a local demo, not an Internet service.\n\nThe recipe commit pins published scientific code. New wrapper/UI source identities are separately bound in the productization completion receipt; no unpublished commit ID is invented. Scientific receipts retain their original creation-state fields.\n')
    runtime=['src/pcb_inspection/preprocessing.py','src/pcb_inspection/geometry.py','src/pcb_inspection/geometry_experiment.py','src/pcb_inspection/baseline.py','src/pcb_inspection/stage4_geometry.py','src/pcb_inspection/stage5a_pose.py','src/pcb_inspection/stage5b_orientation.py',config['weights_path'],paths['memory']]
    sources=['artifacts/stage5c/complete.json','artifacts/stage5c/orientation_protocol.json','artifacts/stage5c/results/full_metrics.json','artifacts/stage4/pcb2_d2_secondary/calibration.json','artifacts/stage4/pcb2_d2_secondary/memory_metadata.json','artifacts/stage6a/complete.json','artifacts/stage6a/decision_gate.json']
    receipt={'model_name':config['model_name'],'version':'1.0','freeze_timestamp':now(),
             'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
             'commit_semantics':'published scientific recipe at Stage6A completion; wrapper/UI identities separately recorded',
             'decision':'Formal freeze of existing Stage5C D2+orientation after Stage6A Branch D; no Stage6B experiment',
             'preprocessing_identity':'pcb1-blue-margin-letterbox-v1 at512, unchanged effective Stage4geometry',
             'crop_identity':geometry,'orientation_identity':METHOD,'input_resolution':512,
             'backbone_identity':config['backbone'],'feature_layers':config['feature_layers'],'aggregation':config['image_aggregation'],
             'memory_bank_identity':config['memory'],'memory_size':4096,'selection_identity':'historical D2 projected approximate-greedy memory',
             'image_threshold':cal['image_threshold'],'pixel_threshold':cal['pixel_threshold'],'threshold_semantics':'strict >',
             'evaluation_summary':metrics['image'],'runtime_summary':metrics['runtime'],'known_limitations':LIMITATIONS,
             'pcb1_status':'development history only; final PCB2 bank/pose wrapper not independently confirmed on PCB1',
             'pcb2_status':'Stage4 fresh-category confirmation; Stage5C final candidate is exposed post-confirmation development',
             'stage_history_links':sources,'source_identities':{name:digest(root/name) for name in sources},
             'runtime_identities':{name:digest(root/name) for name in runtime},
             'artifact_identities':{str(p.relative_to(root)):digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    write_new(out/'final_model_receipt.json',receipt)
    frame=pd.read_csv(stage/'predictions.csv');manifest=pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv').set_index('image_id')
    normals=pd.read_csv(root/'artifacts/stage4/pcb2_normals/normal_manifest.csv').set_index('image_id')
    categories=[('canonical_normal',frame[(frame.label=='normal')&(~frame.detected)].iloc[0]),
                ('canonical_anomaly',frame[(frame.label=='anomaly')&(frame.pose_label=='canonical')&frame.detected].iloc[0]),
                ('reversed_anomaly',frame[frame.image_id=='bfebbd19caf4dad38fd66eab'].iloc[0]),
                ('uncertain_pose',frame[(frame.pose_label=='uncertain')].iloc[0]),
                ('known_small_missing_miss',frame[frame.image_id=='d086b78f683af0d19bb68594'].iloc[0]),
                ('missing_detected',frame[(frame.label=='anomaly')&frame.detected&frame.defect_types.fillna('[]').map(lambda s:'missing' in json.loads(s))&(frame.pose_label=='canonical')].iloc[0])]
    array_paths=json.loads((stage/'array_paths.json').read_text());cases=[]
    for label,row in categories:
        source=(manifest if row.label=='anomaly' else normals).loc[row.image_id]
        cases.append({'id':label,'image_id':row.image_id,'image_path':source.image_path,'image_sha256':source.sha256,
                      'mask_path':source.mask_path if row.label=='anomaly' else None,
                      'mask_sha256':source.mask_sha256 if row.label=='anomaly' else None,
                      'score':float(row.score),'detected':bool(row.detected),'pose_label':row.pose_label,
                      'maps':{key:f'{path}/{row.image_id}.npy' for key,path in array_paths.items()},
                      'map_hashes':{key:digest(root/f'{path}/{row.image_id}.npy') for key,path in array_paths.items()}})
    write_new(root/'tests/model_v1_smoke_manifest.json',{'model_receipt_sha256':digest(out/'final_model_receipt.json'),'score_map_tolerance':1e-5,'cases':cases})
    print('Frozen',config['model_name'],'bank',config['memory']['sha256'])

if __name__=='__main__':main()

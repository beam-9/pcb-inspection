import json
from pathlib import Path
import shutil
from io import BytesIO
import numpy as np
import pandas as pd
import pytest
from PIL import Image
from pcb_inspection.guard import digest
from pcb_inspection.model_v1 import decode_image, load_metadata, UnsupportedImage, FrozenInspector

ROOT=Path(__file__).resolve().parents[1]


def test_frozen_metadata_identities_and_exact_thresholds():
    metadata=load_metadata(ROOT,verify_runtime=True)
    calibration=json.loads((ROOT/'artifacts/stage4/pcb2_d2_secondary/calibration.json').read_text())
    assert metadata['thresholds']=={k:calibration[k] for k in ['image_threshold','pixel_threshold']}|{'comparison':'>'}
    assert metadata['config']['memory']['sha256']==(ROOT/'artifacts/model_v1/final_bank_hash.txt').read_text().strip()
    assert metadata['metrics']==json.loads((ROOT/'artifacts/stage5c/results/full_metrics.json').read_text())


def test_metadata_rejects_modified_config(tmp_path):
    target=tmp_path/'artifacts/model_v1';shutil.copytree(ROOT/'artifacts/model_v1',target)
    config=json.loads((target/'final_config.json').read_text());config['thresholds']['image_threshold']=0
    (target/'final_config.json').write_text(json.dumps(config))
    with pytest.raises(ValueError,match='Frozen model artifact changed'):load_metadata(tmp_path)


def test_bad_image_formats_and_dimensions():
    with pytest.raises(UnsupportedImage):decode_image(b'not an image')
    for size,format in [((20,40),'PNG'),((32,32),'GIF')]:
        stream=BytesIO();Image.new('RGB',size).save(stream,format=format)
        with pytest.raises(UnsupportedImage):decode_image(stream.getvalue())
    stream=BytesIO();Image.new('RGB',(64,64)).save(stream,format='PNG');assert decode_image(stream.getvalue()).size==(64,64)


def test_journey_values_match_original_sources_and_boundaries():
    content=json.loads((ROOT/'content/journey.json').read_text());stages=content['stages']
    assert [s['id'] for s in stages]==['stage-1','stage-2','stage-3','stage-4','stage-5a','stage-5b','stage-5c','stage-6a','model-v1']
    assert stages[0]['datasetPhase']=='PCB1 development'
    assert stages[3]['datasetPhase']=='PCB2 fresh confirmation'
    assert all(s['datasetPhase']=='PCB2 post-confirmation development' for s in stages[4:])
    for stage in stages:
        for field in ['question','change','rationale','learning','nextQuestion','heldConstant','limits','sources','figures']:assert stage[field]
        for metric in stage['metrics']:
            source=metric['source'];path=ROOT/source['path'];assert digest(path)==source['sha256']
            if 'computation' in source:
                table=pd.read_csv(path);recipe='d1' if metric['label'].startswith('D1') else 'd2';column=recipe+'_common_fp_pixels'
                expected=table.loc[table.pose_label=='reversed_180',column].sum()/table[column].sum()
            elif source.get('row'):
                row=source['row'];table=pd.read_csv(path,float_precision='round_trip');expected=table.loc[table[row['column']]==row['value'],source['selector']].iloc[0]
            else:
                expected=json.loads(path.read_text())
                for key in source['selector']:expected=expected[key]
            assert metric['value']==pytest.approx(expected,abs=1e-12)
        for figure in stage['figures']:assert digest(ROOT/figure['path'])==figure['sha256']


def test_smoke_manifest_includes_failure_and_pose_controls():
    manifest=json.loads((ROOT/'tests/model_v1_smoke_manifest.json').read_text())
    assert manifest['model_receipt_sha256']==digest(ROOT/'artifacts/model_v1/final_model_receipt.json')
    cases=manifest['cases'];assert {'canonical','reversed_180','uncertain'}<={c['pose_label'] for c in cases}
    assert any(c['id']=='known_small_missing_miss' and not c['detected'] for c in cases)


def test_public_recordings_keep_frozen_results_and_failure():
    manifest=json.loads((ROOT/'tests/model_v1_smoke_manifest.json').read_text())
    export=json.loads((ROOT/'artifacts/productization/public_export.json').read_text())
    hashes={c['id']:c['sha256'] for c in export['checks']}
    for case in manifest['cases']:
        path=ROOT/'content/benchmark_results'/(case['id']+'.json');recording=json.loads(path.read_text())
        assert digest(path)==hashes[case['id']]
        assert recording['inspection_kind']=='saved_preview'
        assert recording['model_receipt_sha256']==manifest['model_receipt_sha256']
        assert recording['anomaly_score']==pytest.approx(case['score'],abs=1e-5)
        assert recording['pose_label']==case['pose_label'] and recording['is_anomalous']==case['detected']
        assert ('ground_truth' in recording)==bool(case['mask_path'])


def test_purpose_sources_and_future_experiments_are_explicit():
    purpose=json.loads((ROOT/'content/purpose.json').read_text())
    assert purpose['inspiration']['source_url'].startswith('https://www.seagate.com/')
    assert '2019' in purpose['inspiration']['text']
    assert 'no Seagate data' in purpose['inspiration']['boundary']
    for source in purpose['sources']:assert digest(ROOT/source['path'])==source['sha256']
    assert len(purpose['future'])==5
    for idea in purpose['future']:
        assert all(idea[key] for key in ['reason','experiment','success','status'])


def test_inspection_contract_preserves_known_miss_and_fixed_scale():
    model=FrozenInspector(ROOT)
    case=next(c for c in json.loads((ROOT/'tests/model_v1_smoke_manifest.json').read_text())['cases'] if c['id']=='known_small_missing_miss')
    result=model.inspect((ROOT/case['image_path']).read_bytes());payload=result.payload()
    assert not payload['is_anomalous'] and payload['anomaly_score']<payload['image_threshold']
    assert not payload['normalization_applied'] and payload['pose_label']=='canonical'
    assert 'ground_truth' not in payload and 'confidence' not in payload
    assert all(payload[k].startswith('data:image/png;base64,') for k in ['original','heatmap','thresholded_map'])
    assert 'fixed 0–2' in payload['heatmap_scale']


def test_reader_index_preserves_source_identity_and_excludes_runtime_caches():
    index=json.loads((ROOT/'content/evidence_index.json').read_text())
    history=json.loads((ROOT/'artifacts/productization/historical_preservation.json').read_text())
    preserved={x['path']:x['preserved_at'] for x in history['checks']}
    sources={x['path']:x for x in index['files']}
    assert {'docs/data_card.md','requirements.lock','artifacts/stage6a/protocol.json','artifacts/stage6a/case_diagnosis.csv'} <= sources.keys()
    for source in index['files']:
        path=source['path']
        assert '..' not in Path(path).parts and not Path(path).is_absolute()
        assert not path.startswith(('data/raw/','data/cache/'))
        assert path in preserved or path.startswith('artifacts/model_v1/')
        assert digest(ROOT/preserved.get(path,path))==source['sha256']

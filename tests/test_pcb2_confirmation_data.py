"""Synthetic-only sealed-data gate tests; never access the real PCB2 source."""
import io
import json
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from PIL import Image
import pytest

from pcb_inspection import pcb2_confirmation_data as loader
from pcb_inspection.provenance import sha256_file


def write_gate(root, config=None):
    config={} if config is None else config
    stage=root/'artifacts/stage4';stage.mkdir(parents=True,exist_ok=True)
    pinned=root/'pinned.txt';pinned.write_text('frozen source')
    receipt={'config':config,'anomaly_access_status':'sealed',
             'primary':{'run':'pcb2_d1_primary'},'secondary':{'run':'pcb2_d2_secondary'},
             'frozen_at_utc':'2026-01-01T00:00:00+00:00',
             'frozen_files':{'pinned.txt':sha256_file(pinned)}}
    (stage/'freeze_receipt.json').write_text(json.dumps(receipt))
    access={'freeze_receipt_sha256':sha256_file(stage/'freeze_receipt.json'),
            'primary':'pcb2_d1_primary','secondary_predeclared':'pcb2_d2_secondary',
            'first_anomaly_access_utc':'2026-01-01T00:01:00+00:00'}
    (stage/'anomaly_access.json').write_text(json.dumps(access))
    return stage,receipt,access


def test_missing_gate_refuses_before_any_network_or_source(tmp_path,monkeypatch):
    monkeypatch.setattr(loader,'RangeReader',lambda *_:pytest.fail('Network reached before gate'))
    monkeypatch.setattr(loader,'_test_routes',lambda *_:pytest.fail('Sealed routes read before gate'))
    with pytest.raises(PermissionError,match='Final freeze'):
        loader.load_test_manifest(tmp_path,{})
    assert not (tmp_path/loader.OUTPUT).exists()


@pytest.mark.parametrize('mutation',['receipt_hash','config','role','timestamp','frozen_source'])
def test_gate_rejects_unbound_or_modified_inputs(tmp_path,mutation):
    stage,receipt,access=write_gate(tmp_path)
    config={}
    if mutation=='receipt_hash':access['freeze_receipt_sha256']='0'*64
    elif mutation=='config':config={'changed':True}
    elif mutation=='role':access['primary']='pcb2_d2_secondary'
    elif mutation=='timestamp':access['first_anomaly_access_utc']='2025-12-31T23:59:59+00:00'
    elif mutation=='frozen_source':(tmp_path/'pinned.txt').write_text('changed')
    (stage/'anomaly_access.json').write_text(json.dumps(access))
    with pytest.raises(PermissionError):loader.validate_confirmation_gate(tmp_path,config)


def image_bytes(color, mode='RGB'):
    image=Image.new(mode,(18,12),color)
    stream=io.BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def synthetic_source(root,monkeypatch,empty_mask=False):
    source=root/'data/raw/1cls.csv';source.parent.mkdir(parents=True)
    normal='pcb2/Data/Images/Normal/heldout.png'
    anomalous='pcb2/Data/Images/Anomaly/abnormal.png'
    mask='pcb2/Data/Masks/Anomaly/abnormal.png'
    pd.DataFrame([{'object':'pcb2','split':'test','label':'normal','image':normal,'mask':''},
                  {'object':'pcb2','split':'test','label':'anomaly','image':anomalous,'mask':mask}]).to_csv(source,index=False)
    monkeypatch.setattr(loader,'OFFICIAL_SPLIT_SHA256',sha256_file(source))
    normal_path=root/'data/raw/stage4'/normal;normal_path.parent.mkdir(parents=True)
    normal_path.write_bytes(image_bytes((1,2,3)))
    output=root/'artifacts/stage4/pcb2_normals';output.mkdir(parents=True)
    pd.DataFrame([{'source_path':normal,'image_path':str(normal_path.relative_to(root)),
                   'sha256':sha256_file(normal_path),'split':'normal_test'},
                  {'source_path':'synthetic/fit','image_path':'unused','sha256':'1'*64,'split':'fit'},
                  {'source_path':'synthetic/cal','image_path':'unused','sha256':'2'*64,'split':'calibration'}]).to_csv(output/'normal_manifest.csv',index=False)
    prior=root/'data/manifests/pcb1_manifest.csv';prior.parent.mkdir(parents=True)
    pd.DataFrame({'sha256':['3'*64]}).to_csv(prior,index=False)
    owner=pd.DataFrame([{'image':normal,'mask':'','label':'normal'},
                        {'image':anomalous,'mask':mask,'label':'missing component, extra component'}]).to_csv(index=False).encode()
    mask_image=Image.new('L',(18,12),0)
    if not empty_mask:mask_image.putpixel((3,4),5)
    stream=io.BytesIO();mask_image.save(stream,format='PNG')
    entries=[('pcb2/Data/Images/Normal/unrequested.png',b'UNALLOWED NORMAL'),
             (anomalous,image_bytes((4,5,6))),(mask,stream.getvalue()),('pcb2/image_anno.csv',owner)]
    archive_bytes=io.BytesIO();allowed_reads={}
    with tarfile.open(fileobj=archive_bytes,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        for name,body in entries:
            offset=archive_bytes.tell();info=tarfile.TarInfo(name);info.size=len(body)
            archive.addfile(info,io.BytesIO(body))
            if name!=entries[0][0]:allowed_reads[offset+512]=len(body)
    payload=archive_bytes.getvalue();instances=[]
    class Reader:
        cache_enabled=False;etag='synthetic';size=len(payload)
        def __init__(self,*args):
            self.transferred=0;self.calls=[];self.conn=SimpleNamespace(close=lambda:None);instances.append(self)
        def get(self,start,length):
            assert length==512 or allowed_reads.get(start)==length
            self.transferred+=length;self.calls.append((start,length));return payload[start:start+length]
    monkeypatch.setattr(loader,'RangeReader',Reader)
    (output/'normal_acquisition.json').write_text(json.dumps({'archive_etag':'synthetic','archive_bytes':len(payload),'start_header_offset':0}))
    return instances


def test_synthetic_shared_unseal_complete_and_verified_reuse(tmp_path,monkeypatch):
    instances=synthetic_source(tmp_path,monkeypatch);write_gate(tmp_path)
    frame=loader.load_test_manifest(tmp_path,{})
    assert len(frame)==2 and set(frame.label)=={'normal','anomaly'}
    anomaly=frame[frame.label=='anomaly'].iloc[0]
    assert json.loads(anomaly.defect_types)==['missing component','extra component']
    assert all(value.startswith('data/raw/stage4/') for value in frame.image_path)
    assert len(instances)==1
    output=tmp_path/loader.OUTPUT;complete=json.loads((output/'complete.json').read_text())
    assert all(path.startswith(loader.OUTPUT+'/') for path in complete['outputs'])
    audit=json.loads((output/'test_audit.json').read_text())
    assert audit['exclusions']==[] and audit['multi_label_images']==1
    assert audit['common256_masks_lost_completely']==0
    repeated=loader.load_test_manifest(tmp_path,{})
    pd.testing.assert_frame_equal(frame,repeated)
    assert len(instances)==1
    (tmp_path/anomaly.mask_path).write_bytes(b'changed')
    with pytest.raises(ValueError,match='raw source changed'):loader.load_test_manifest(tmp_path,{})


def test_empty_abnormal_mask_stops_without_completion_or_exclusion(tmp_path,monkeypatch):
    synthetic_source(tmp_path,monkeypatch,empty_mask=True);write_gate(tmp_path)
    with pytest.raises(ValueError,match='mask empty'):loader.load_test_manifest(tmp_path,{})
    assert not (tmp_path/loader.OUTPUT/'complete.json').exists()
    with pytest.raises(FileExistsError,match='no silent replay'):loader.load_test_manifest(tmp_path,{})


def test_invalid_owner_image_class_refuses_route(tmp_path):
    source=tmp_path/'synthetic.csv'
    pd.DataFrame([{'object':'pcb2','split':'test','label':'normal','image':'pcb2/Data/Images/Anomaly/wrong.png','mask':''}]).to_csv(source,index=False)
    with pytest.raises(ValueError,match='image route'):loader._test_routes(source)

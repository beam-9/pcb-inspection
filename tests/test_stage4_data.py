import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np
import pandas as pd
from PIL import Image
import pytest

from pcb_inspection.stage4_data import normal_routes, is_allowed_normal_path, acquire_normal_ranges, build_normal_manifest


def test_routes_retain_only_normal_paths_and_never_defect_metadata(tmp_path):
    path=tmp_path/'source.csv'
    path.write_text('object,split,label,image,mask\n'
                    'pcb2,train,normal,pcb2/Data/Images/Normal/0001.JPG,\n'
                    'pcb2,test,normal,pcb2/Data/Images/Normal/0002.JPG,\n'
                    'pcb2,test,anomaly,pcb2/Data/Images/Anomaly/sealed.JPG,pcb2/Data/Masks/Anomaly/sealed.png\n')
    routes=normal_routes(path)
    assert len(routes)==2 and all(row['label']=='normal' for row in routes)
    assert all(is_allowed_normal_path(row['image']) for row in routes)
    assert 'sealed' not in json.dumps(routes)
    assert not is_allowed_normal_path('pcb2/Data/Images/Anomaly/0001.JPG')
    assert not is_allowed_normal_path('pcb2/Data/Images/Normal/../../outside.JPG')


def test_transport_fetches_only_headers_and_allowlisted_normal_bodies(tmp_path):
    content=io.BytesIO()
    entries=[('pcb2/Data/Images/Anomaly/sealed.JPG',b'SEALED IMAGE PAYLOAD'),
             ('pcb2/Data/Masks/Anomaly/sealed.png',b'SEALED MASK PAYLOAD'),
             ('pcb2/image_anno.csv',b'SEALED ANNOTATION PAYLOAD'),
             ('pcb2/Data/Images/Normal/0001.JPG',b'NORMAL IMAGE PAYLOAD')]
    with tarfile.open(fileobj=content,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        for name,body in entries:
            info=tarfile.TarInfo(name);info.size=len(body);archive.addfile(info,io.BytesIO(body))
    data=content.getvalue()
    normal_body_offset=3*1024+512
    class Reader:
        cache_enabled=False
        size=len(data)
        calls=[]
        def get(self,start,length):
            self.calls.append((start,length))
            assert length==512 or (start==normal_body_offset and length==len(entries[-1][1]))
            return data[start:start+length]
    reader=Reader()
    report=acquire_normal_ranges(reader,[{'image':entries[-1][0]}],tmp_path,0)
    assert report['unallowed_payload_bytes_acquired']==0 and report['skipped_regular_member_count']==3
    assert len(report['entries'])==1
    saved=tmp_path/'stage4'/entries[-1][0]
    assert saved.read_bytes()==entries[-1][1]
    assert [call for call in reader.calls if call[1]!=512]==[(normal_body_offset,len(entries[-1][1]))]
    reader.cache_enabled=True
    with pytest.raises(ValueError,match='caching is prohibited'):
        acquire_normal_ranges(reader,[{'image':entries[-1][0]}],tmp_path,0)


def make_normals(root):
    source=root/'data/raw/1cls.csv';source.parent.mkdir(parents=True)
    output=root/'artifacts/stage4/pcb2_normals';output.mkdir(parents=True)
    routes=[];entries=[]
    for index in range(7):
        original=f'pcb2/Data/Images/Normal/{index:04}.JPG'
        relative='stage4/'+original;path=root/'data/raw'/relative;path.parent.mkdir(parents=True,exist_ok=True)
        if index<6:Image.new('RGB',(20,12),(index*30,20,30)).save(path)
        else:path.write_bytes(b'heldout bytes intentionally undecodable')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append({'source_path':original,'image_path':relative,'sha256':digest})
        routes.append({'object':'pcb2','split':'train' if index<6 else 'test','label':'normal','image':original,'mask':''})
    pd.DataFrame(routes).to_csv(source,index=False)
    (output/'normal_acquisition.json').write_text(json.dumps({'entries':entries,'source_split_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}))
    pd.DataFrame({'sha256':['0'*64]}).to_csv(root/'data/manifests_dummy.csv',index=False)
    destination=root/'data/manifests/pcb1_manifest.csv';destination.parent.mkdir(parents=True)
    pd.DataFrame({'sha256':['0'*64]}).to_csv(destination,index=False)
    return output


def test_normal_split_deterministic_and_heldout_decode_deferred(tmp_path):
    output=make_normals(tmp_path)
    audit=build_normal_manifest(tmp_path)
    assert audit['split_counts']=={'calibration':2,'fit':4,'normal_test':1}
    frame=pd.read_csv(output/'normal_manifest.csv',keep_default_na=False)
    heldout=frame[frame.split=='normal_test'].iloc[0]
    assert heldout['width']=='' and heldout['structural_decode_status']=='deferred_until_final_freeze'
    assert audit['decode_passed_fit_calibration']==6 and audit['heldout_decode_deferred']==1
    assert build_normal_manifest(tmp_path)==audit
    groups=sorted(frame[frame.official_split=='train'].sha256.unique())
    np.random.default_rng(42).shuffle(groups)
    assert set(frame[frame.split=='calibration'].sha256)==set(groups[:2])


def test_source_image_change_fails_before_publication(tmp_path):
    output=make_normals(tmp_path)
    (tmp_path/'data/raw/stage4/pcb2/Data/Images/Normal/0000.JPG').write_bytes(b'changed')
    with pytest.raises(ValueError,match='source bytes changed'):
        build_normal_manifest(tmp_path)
    assert not (output/'normal_manifest.csv').exists()

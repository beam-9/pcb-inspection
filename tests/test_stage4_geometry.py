from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from PIL import Image
from pcb_inspection.guard import digest
from pcb_inspection.geometry import detect_geometry, image_tensor
from pcb_inspection.stage4_geometry import geometry_for, tensor_and_transform, preflight


def test_inherited_geometry_and_tensor_are_exact(tmp_path):
    a=np.full((200,300,3),90,dtype=np.uint8);a[60:140,80:220]=[20,150,230]
    image=Image.fromarray(a);path=tmp_path/'normal.png';image.save(path)
    config={'mode':'inherited_blue'}
    assert geometry_for(image,config)==detect_geometry(image)
    row=SimpleNamespace(image_path='normal.png',sha256=digest(path))
    x,t=tensor_and_transform(tmp_path,row,256,config)
    expected,et=image_tensor(image,detect_geometry(image),256)
    assert t==et
    np.testing.assert_array_equal(x.numpy(),expected.numpy())
    with pytest.raises(ValueError,match='Only inherited'):geometry_for(image,{'mode':'unknown'})
    row.sha256='invalid'
    with pytest.raises(ValueError,match='changed'):tensor_and_transform(tmp_path,row,256,config)


def test_preflight_never_opens_heldout_or_anomalies_and_rejects_overwrite(tmp_path):
    path=tmp_path/'normal.png';Image.new('RGB',(100,80),(15,140,230)).save(path)
    rows=[{'image_id':'a','image_path':'normal.png','sha256':digest(path),'label':'normal','split':'fit'},
          {'image_id':'b','image_path':'MUST_NOT_BE_OPENED','sha256':'invalid','label':'normal','split':'normal_evaluation'},
          {'image_id':'c','image_path':'MUST_NOT_BE_OPENED','sha256':'invalid','label':'anomaly','split':'test'}]
    pd.DataFrame(rows).to_csv(tmp_path/'manifest.csv',index=False)
    output=tmp_path/'preflight'
    result=preflight(tmp_path,'manifest.csv',output)
    assert result['normal_count']==1 and result['anomaly_access'] is False
    assert list(pd.read_csv(output/'normal_geometry.csv').image_id)==['a']
    with pytest.raises(FileExistsError):preflight(tmp_path,'manifest.csv',output)

import pandas as pd
import pytest
from PIL import Image
from pcb_inspection.data import build_manifest, load_manifest, validate_manifest
from pcb_inspection.provenance import canonical_hash, immutable_json


def make_source(tmp_path):
    rows=[]
    for index in range(6):
        image=f'pcb1/Data/Images/Normal/{index}.png'
        path=tmp_path/image
        path.parent.mkdir(parents=True,exist_ok=True)
        Image.new('RGB',(10,10),(index*30,20,30)).save(path)
        rows.append({'object':'pcb1','split':'train' if index<5 else 'test','label':'normal','image':image,'mask':''})
    image='pcb1/Data/Images/Anomaly/bad.png'
    path=tmp_path/image
    path.parent.mkdir(parents=True,exist_ok=True)
    Image.new('RGB',(10,10),(99,99,99)).save(path)
    mask='pcb1/Data/Masks/Anomaly/bad.png'
    path=tmp_path/mask
    path.parent.mkdir(parents=True,exist_ok=True)
    Image.new('L',(10,10),2).save(path)
    rows.append({'object':'pcb1','split':'test','label':'anomaly','image':image,'mask':mask})
    source=tmp_path/'split.csv'
    pd.DataFrame(rows).to_csv(source,index=False)
    return source


def test_official_test_unchanged_deterministic_split(tmp_path):
    source=make_source(tmp_path)
    first=build_manifest(tmp_path,source,tmp_path/'manifest')
    second=build_manifest(tmp_path,source,tmp_path/'manifest')
    assert first==second
    frame=load_manifest(tmp_path/'manifest'/first['manifest_path'])
    assert frame.loc[frame.official_split=='test','split'].eq('test').all()
    assert first['counts']=={'calibration/normal':1,'fit/normal':4,'test/anomaly':1,'test/normal':1}
    assert validate_manifest(frame)


def test_duplicate_contamination_rejected(tmp_path):
    source=make_source(tmp_path)
    from shutil import copyfile
    copyfile(tmp_path/'pcb1/Data/Images/Normal/0.png',tmp_path/'pcb1/Data/Images/Normal/5.png')
    with pytest.raises(ValueError,match='across official'):
        build_manifest(tmp_path,source,tmp_path/'manifest')


def test_missing_mask_excluded_and_reported(tmp_path):
    source=make_source(tmp_path)
    (tmp_path/'pcb1/Data/Masks/Anomaly/bad.png').unlink()
    report=build_manifest(tmp_path,source,tmp_path/'manifest')
    assert report['included_count']==6
    assert report['exclusions'][0]['reason']=='Missing abnormal mask'


def test_within_train_duplicates_stay_together(tmp_path):
    source=make_source(tmp_path)
    from shutil import copyfile
    copyfile(tmp_path/'pcb1/Data/Images/Normal/0.png',tmp_path/'pcb1/Data/Images/Normal/1.png')
    report=build_manifest(tmp_path,source,tmp_path/'manifest')
    frame=load_manifest(tmp_path/'manifest'/report['manifest_path'])
    duplicate=frame.loc[frame.image_path.str.endswith(('0.png','1.png'))]
    assert duplicate.split.nunique()==1


def test_immutable_json_rejects_change(tmp_path):
    path=tmp_path/'frozen.json'
    immutable_json(path,{'x':1})
    immutable_json(path,{'x':1})
    with pytest.raises(FileExistsError):
        immutable_json(path,{'x':2})
    assert canonical_hash({'a':1,'b':2})==canonical_hash({'b':2,'a':1})


@pytest.mark.parametrize('status,content_range',[(200,'bytes 0-3/100'),(206,'bytes 0-9/100')])
def test_range_reader_refuses_ignored_or_incorrect_ranges(status,content_range):
    from pcb_inspection.acquisition import RangeReader
    class Response:
        def __init__(self):
            self.status=status
        def getheader(self,name):
            return {'Content-Range':content_range,'ETag':'pinned'}.get(name)
        def close(self):
            pass
        def read(self):
            raise AssertionError('A rejected response body must never be downloaded')
    class Connection:
        def request(self,*args,**kwargs):
            pass
        def getresponse(self):
            return Response()
    reader=RangeReader.__new__(RangeReader)
    reader.conn=Connection()
    reader.path='/archive'
    reader.size=100
    reader.etag='pinned'
    reader.transferred=0
    reader.cache_enabled=False
    with pytest.raises(RuntimeError,match='full download refused'):
        reader.get(0,4)
    assert reader.transferred==0

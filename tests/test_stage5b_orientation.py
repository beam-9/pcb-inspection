"""Geometry/control tests use asymmetric crops and odd letterbox padding."""
import numpy as np
import pytest
from PIL import Image
import torch
from pcb_inspection.geometry import image_tensor,inverse_map
from pcb_inspection.stage5b_orientation import ACTIONS,rotate_180,orientation_tensor,orientation_inverse_map,freeze


def geometry():
    return dict(source_width=17,source_height=13,crop_box=[3,2,14,10],board_box=[4,3,13,9],fallback=False,failure_reason=None,component_fraction=.2,crop_area_fraction=88/221)


def test_rotation_twice_shape_identity():
    a=np.arange(7*11*3,dtype=np.uint8).reshape(7,11,3)
    assert rotate_180(a).shape==a.shape
    assert np.array_equal(rotate_180(rotate_180(a)),a)
    assert np.array_equal(rotate_180(a)[0,0],a[-1,-1])


@pytest.mark.parametrize('pose',['canonical','uncertain'])
def test_noop_input_and_map_exact(pose):
    g=geometry();image=Image.fromarray(np.arange(13*17*3,dtype=np.uint8).reshape(13,17,3))
    expected,t=image_tensor(image,g,256);actual,u=orientation_tensor(image,g,pose)
    assert torch.equal(expected,actual) and t==u
    scores=np.arange(256*256,dtype=np.float32).reshape(256,256)
    assert np.array_equal(inverse_map(scores,t,256),orientation_inverse_map(scores,t,pose,256))
    assert ACTIONS[pose]=='no_op'


def test_crop_rotates_before_letterbox_not_padding():
    g=geometry();image=Image.fromarray(np.arange(13*17*3,dtype=np.uint8).reshape(13,17,3))
    expected=image.copy();expected.paste(Image.fromarray(rotate_180(np.asarray(image.crop(g['crop_box'])))),(3,2))
    tensor,t=orientation_tensor(image,g,'reversed_180');reference,u=image_tensor(expected,g,256)
    assert torch.equal(tensor,reference) and t==u


def test_inverse_alignment_asymmetric_crop():
    g=geometry();_,t=image_tensor(Image.new('RGB',(17,13)),g,256)
    scores=np.zeros((256,256),np.float32);py,px=t['pad_y'],t['pad_x']
    content=np.arange(t['content_height']*t['content_width'],dtype=np.float32).reshape(t['content_height'],t['content_width'])
    scores[py:py+t['content_height'],px:px+t['content_width']]=content
    expected_crop=np.asarray(Image.fromarray(content).resize((11,8),Image.Resampling.BILINEAR))[::-1,::-1]
    expected=np.zeros((13,17),np.float32);expected[2:10,3:14]=expected_crop
    actual=orientation_inverse_map(scores,t,'reversed_180')
    assert np.array_equal(actual,expected)
    assert np.array_equal(orientation_inverse_map(scores,t,'reversed_180',256),np.asarray(Image.fromarray(expected).resize((256,256),Image.Resampling.BILINEAR)))


def test_output_refuses_overwrite(tmp_path):
    (tmp_path/'artifacts/stage5b').mkdir(parents=True)
    with pytest.raises(FileExistsError):freeze(tmp_path)


def test_odd_padding_crop_rotation_differs_from_tensor_rotation():
    g=geometry();g['crop_box']=[3,2,14,9]
    image=Image.fromarray(np.arange(13*17*3,dtype=np.uint8).reshape(13,17,3));before=np.asarray(image).copy()
    original,t=image_tensor(image,g,256);rotated,u=orientation_tensor(image,g,'reversed_180')
    assert (256-t['content_height'])%2==1
    assert not torch.equal(rotated,original.flip([1,2]))
    assert np.array_equal(np.asarray(image),before)
    assert t==u


def test_unknown_pose_rejected():
    with pytest.raises(KeyError):orientation_tensor(Image.new('RGB',(17,13)),geometry(),'unknown')


def test_historical_csv_mixed_blank_numeric_fields_preserve_exact_float(tmp_path):
    from pcb_inspection.stage5b_orientation import historical_predictions
    path=tmp_path/'predictions.csv'
    literal='0.10453364602550923'
    path.write_text('image_id,pixel_ap,iou,source_pixel_ap,source_iou,score\na,'+literal+',0.03927148548662493,'+literal+',0.03879352865739371,1.8522746562957764\nn,,,,,1.0\n')
    frame=historical_predictions(path)
    assert frame.loc[0,'pixel_ap']==float(literal)
    assert float(frame.loc[0,'pixel_ap']).hex()==float(literal).hex()
    assert np.isnan(frame.loc[1,'pixel_ap'])
    assert frame.loc[0,'score']==float('1.8522746562957764')

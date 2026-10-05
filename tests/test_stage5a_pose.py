import numpy as np
from PIL import Image
from pcb_inspection.stage5a_pose import classify_pose

def board(top=False,bottom=False):
    array=np.full((300,512,3),50,dtype=np.uint8)
    array[100:200,80:432]=[20,80,180]
    for x in [220,240,260,280]:
        if top:array[65:101,x:x+2]=220
        if bottom:array[199:235,x:x+2]=220
    return Image.fromarray(array)

def test_pin_position_symmetry_and_ambiguous_cues():
    box=[80,100,432,200]
    assert classify_pose(board(top=True),box)['pose_label']=='canonical'
    assert classify_pose(board(bottom=True),box)['pose_label']=='reversed_180'
    assert classify_pose(board(top=True,bottom=True),box)['pose_label']=='uncertain'
    assert classify_pose(board(),box)['pose_label']=='uncertain'

def test_absent_or_nonhorizontal_board_is_uncertain():
    assert classify_pose(board(top=True),None)['pose_label']=='uncertain'
    assert classify_pose(board(top=True),[200,10,300,290])['pose_label']=='uncertain'

def test_180_pin_position_changes_label_without_angle_claim():
    image=board(top=True)
    reversed_image=image.transpose(Image.Transpose.ROTATE_180)
    assert classify_pose(reversed_image,[80,100,432,200])['pose_label']=='reversed_180'
    assert 'estimated_rotation_degrees' not in classify_pose(image,[80,100,432,200])

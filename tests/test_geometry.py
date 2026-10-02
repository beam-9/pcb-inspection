import numpy as np
from PIL import Image
from pcb_inspection.geometry import detect_geometry,letterbox,inverse_map

def test_margin_keeps_board_and_connector_region():
 a=np.full((200,300,3),100,dtype=np.uint8);a[70:130,60:240]=[20,150,190]
 g=detect_geometry(Image.fromarray(a));x0,y0,x1,y1=g['crop_box']
 assert not g['fallback'] and x0<60 and x1>240 and y0<=45 and y1>=155

def test_fallback_retains_all_pixels():
 g=detect_geometry(Image.new('RGB',(300,200),'gray'))
 assert g['fallback'] and g['crop_box']==[0,0,300,200]

def test_inverse_map_excludes_padding_and_has_source_extent():
 im=Image.new('RGB',(300,200),'gray');g=detect_geometry(im)
 _,t=letterbox(im,g,256);a=np.full((256,256),100,dtype=np.float32)
 a[t['pad_y']:t['pad_y']+t['content_height'],t['pad_x']:t['pad_x']+t['content_width']]=2
 m=inverse_map(a,t)
 assert m.shape==(200,300) and np.allclose(m,2)

def test_crop_inverse_preserves_outside_zero_and_common_denominator():
 im=Image.new('RGB',(300,200),'gray');g={'source_width':300,'source_height':200,'crop_box':[60,40,240,160]}
 _,t=letterbox(im,g,512);m=inverse_map(np.ones((512,512)),t)
 assert m.shape==(200,300) and m[0,0]==0 and m[100,100]==1
 assert inverse_map(np.ones((512,512)),t,256).shape==(256,256)

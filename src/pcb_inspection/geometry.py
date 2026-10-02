"""PCB1 blue-board crop; content-only, reversible, no pose registration."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage
import torch

GEOMETRY_CONFIG = {'id':'pcb1-blue-margin-letterbox-v1','detection_width':512,
 'blue_minus_red':0.05,'green_minus_red':0.03,'minimum_saturation':0.12,
 'closing_iterations':3,'minimum_component_fraction':0.02,'maximum_component_fraction':0.65,
 'horizontal_margin_board_width':0.08,'vertical_margin_board_height':0.45,
 'padding_rgb':[128,128,128],'pose':'unchanged; 180-degree ambiguity retained'}

def detect_geometry(image):
    image=ImageOps.exif_transpose(image).convert('RGB'); w,h=image.size
    dw=min(w,512); dh=round(h*dw/w)
    a=np.asarray(image.resize((dw,dh),Image.Resampling.BILINEAR),dtype=np.float32)/255
    hi=a.max(2);lo=a.min(2)
    blue=(a[:,:,2]-a[:,:,0]>.05)&(a[:,:,1]-a[:,:,0]>.03)&((hi-lo)/np.maximum(hi,1e-6)>.12)
    labels,n=ndimage.label(ndimage.binary_closing(blue,iterations=3))
    sizes=np.bincount(labels.ravel());sizes[0]=0
    failure='no_blue_component' if n==0 else None
    if n:
        label=int(sizes.argmax()); fraction=float(sizes[label]/labels.size)
        if not .02<=fraction<=.65: failure='component_fraction_outside_bounds'
    else: fraction=0.
    if failure:
        box=[0,0,w,h]; board=None
    else:
        ys,xs=np.where(labels==label)
        board=[int(np.floor(xs.min()*w/dw)),int(np.floor(ys.min()*h/dh)),
               int(np.ceil((xs.max()+1)*w/dw)),int(np.ceil((ys.max()+1)*h/dh))]
        bw=board[2]-board[0];bh=board[3]-board[1]
        box=[max(0,int(np.floor(board[0]-.08*bw))),max(0,int(np.floor(board[1]-.45*bh))),
             min(w,int(np.ceil(board[2]+.08*bw))),min(h,int(np.ceil(board[3]+.45*bh)))]
    return {'source_width':w,'source_height':h,'crop_box':box,'board_box':board,
            'component_fraction':fraction,'fallback':bool(failure),'failure_reason':failure,
            'crop_area_fraction':(box[2]-box[0])*(box[3]-box[1])/(w*h)}

def letterbox(image,geometry,size):
    if size not in (256,512): raise ValueError('Declared input sizes are256/512')
    im=ImageOps.exif_transpose(image).convert('RGB')
    if im.size!=(geometry['source_width'],geometry['source_height']): raise ValueError('Source geometry mismatch')
    x0,y0,x1,y1=geometry['crop_box'];cw,ch=x1-x0,y1-y0
    scale=min(size/cw,size/ch);rw=max(1,round(cw*scale));rh=max(1,round(ch*scale))
    px=(size-rw)//2;py=(size-rh)//2
    canvas=Image.new('RGB',(size,size),(128,128,128));canvas.paste(im.crop((x0,y0,x1,y1)).resize((rw,rh),Image.Resampling.BILINEAR),(px,py))
    transform={**geometry,'input_size':size,'content_width':rw,'content_height':rh,'pad_x':px,'pad_y':py}
    return canvas,transform

def image_tensor(image,geometry,size):
    canvas,t=letterbox(image,geometry,size)
    a=np.asarray(canvas,dtype=np.float32).copy()/255
    x=torch.from_numpy(a).permute(2,0,1)
    return (x-torch.tensor([.485,.456,.406])[:,None,None])/torch.tensor([.229,.224,.225])[:,None,None],t

def inverse_map(scores,transform,common_size=None):
    a=np.asarray(scores,dtype=np.float32);s=transform['input_size']
    if a.shape!=(s,s):raise ValueError('Map/input shape mismatch')
    x0,y0,x1,y1=transform['crop_box'];px,py=transform['pad_x'],transform['pad_y']
    rw,rh=transform['content_width'],transform['content_height']
    crop=Image.fromarray(a[py:py+rh,px:px+rw]).resize((x1-x0,y1-y0),Image.Resampling.BILINEAR)
    full=Image.new('F',(transform['source_width'],transform['source_height']),0.);full.paste(crop,(x0,y0))
    if common_size: full=full.resize((common_size,common_size),Image.Resampling.BILINEAR)
    return np.asarray(full,dtype=np.float32).copy()

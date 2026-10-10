import argparse,sys,os,hashlib,json,io
sys.path.insert(0,'work/a180_deps')
from psd_tools import PSDImage
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import numpy as np
a=argparse.ArgumentParser(description="q060 PSD clean-layer unapproved trial reproduction")
a.add_argument('--psd',required=True)
a.add_argument('--official-dds',required=True)
a.add_argument('--english-source-png',required=True)
a.add_argument('--font',required=True)
a.add_argument('--output-dir',required=True)
params=a.parse_args()
b=params.output_dir.rstrip('/')+'/'
os.makedirs(b,exist_ok=True)
for path,expected in [(params.psd,'cb03eb03f6515da0453c0e70d316a89955fa6da9690833354b869145c97a8024'),(params.official_dds,'d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01'),(params.english_source_png,'9f4a4c114a306bd039304415dce32d1a6addd9274e5f57b4ed2ee9372f0f3d72'),(params.font,'3cffb10242b4b7e6edd439ebf3bd7e392345525e093ea08149e0a0158a1b5151')]:
 assert hashlib.sha256(open(path,'rb').read()).hexdigest()==expected, 'source SHA mismatch: '+path
font_path=params.font
psd=PSDImage.open(params.psd)
flat=psd[1][0][2][1][0].topil().convert('RGBA')
raw=bytearray(open(params.official_dds,'rb').read())
assert len(raw)==128+4096*2048*4 and raw[:4]==b'DDS '
original=np.frombuffer(raw,dtype=np.uint8,offset=128).reshape((2048,4096,4)).copy()
readable=original[::-1].copy()
prior=readable.copy()
x0,y0,x1,y1=2179,340,3028,474
W,H=x1-x0,y1-y0
flat_crop=np.asarray(flat.crop((x0,y0,x1,y1)),dtype=np.uint8)
# PSD layer furnishes RGB only; native source plate alpha must stay transparent.
readable[y0:y1,x0:x1,:3]=flat_crop[:,:,:3]
readable[y0:y1,x0:x1,3]=0
plate=readable[y0:y1,x0:x1,:].copy()
# Test raster is deliberately not promoted; final appearance requires independent optical review.
msg='최고 주행 시간'
font=ImageFont.truetype(font_path,116,index=1)
for ch in msg.replace(' ',''):
 assert font.getbbox(ch) is not None
canvas=Image.new('L',(1060,170))
d=ImageDraw.Draw(canvas)
bb=d.textbbox((0,0),msg,font=font,spacing=5)
d.text((20-bb[0],5-bb[1]),msg,fill=255,font=font)
mask=canvas.crop(canvas.getbbox())
# Source readable B stem has rightward top-minus-bottom dx ~0.3421 per dy.
sh=0.3421
L=mask.size[0]+75
M=mask.size[1]
mask=mask.transform((L,M),Image.Transform.AFFINE,(1,sh,-sh*M,0,1,0),resample=Image.Resampling.BICUBIC)
mask=mask.crop(mask.getbbox())
# Italic width and height must remain inside the original English effect bbox.
if mask.width+20>W or mask.height+18>H:
 raise ValueError('SOURCE_BBOX_CEILING_FAILED '+str((mask.size,(W,H))))
ox=(W-mask.width)//2
oy=(H-mask.height)//2
base=Image.new('L',(W,H));base.paste(mask,(ox,oy))
# Contour bevel is oriented by source glyph boundaries, not an unrelated rectangle.
outline=base.filter(ImageFilter.MaxFilter(9))
face=np.asarray(base,dtype=np.uint8)
edge=np.asarray(outline,dtype=np.uint8)
upper=np.maximum(face.astype(np.int16)-np.asarray(Image.new('L',(W,H),0),dtype=np.uint8).astype(np.int16),0)
# Gold metallic face with per-x warm modulation and boundary-lit highlights.
y,x=np.indices((H,W));t=np.clip((y-oy)/max(mask.height,1),0,1)
r=np.full((H,W),255,dtype=np.float32)
g=225-105*t+9*np.sin(x/37.0)
bb=121-117*t+7*np.sin(x/24.0)
# Use nearby source English material to condition glint warmth, with bounded range.
src=np.array(Image.open(params.english_source_png).convert('RGBA').crop((x0,y0,x1,y1)))
bright=(src[:,:,0].astype(float)-src[:,:,2].astype(float))/255.0
warm=np.clip(bright,0,1)
g+=np.clip(warm*7,0,7)
fill=np.stack([np.clip(r,0,255),np.clip(g,0,255),np.clip(bb,0,255)],axis=2).astype(np.uint8)
# A minimal navy extruded base, gold edge, and local upper bevel — all masked.
import PIL.ImageChops as Ch
layer=Image.new('RGBA',(W,H),(0,0,0,0))
navy=Image.new('RGBA',(W,H),(3,9,59,255))
extr=Image.new('L',(W,H));extr.paste(outline,(9,5))
layer.paste(navy,(0,0),extr)
gold=Image.new('RGBA',(W,H),(251,164,15,255))
layer.paste(gold,(0,0),outline)
face_rgb=Image.fromarray(fill,'RGB').convert('RGBA')
layer.paste(face_rgb,(0,0),base)
# highlight on the upper-left stroke contour; no opaque backing rectangles.
shift=Ch.offset(base,2,3)
high=Ch.subtract(base,shift)
layer.paste(Image.new('RGBA',(W,H),(255,244,187,255)),(0,0),high)
final=Image.alpha_composite(Image.fromarray(plate,'RGBA'),layer)
fa=np.asarray(final,dtype=np.uint8)
readable[y0:y1,x0:x1,:]=fa
outside=np.any(readable!=prior,axis=2)
outside[y0:y1,x0:x1]=False
changed=int(np.count_nonzero(np.any(readable!=prior,axis=2)))
assert np.count_nonzero(outside)==0
assert changed>0
# Persist same native 128-byte header with mirror-Y raw orientation and single mip.
encoded=readable[::-1].tobytes()
raw[128:]=encoded
out=b+'Q060_PSD_SOURCE_PLATE_TRIAL_UNAPPROVED.dds'
open(out,'wb').write(raw)
check=Image.frombytes('RGBA',(4096,2048),open(out,'rb').read()[128:]).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
assert np.array_equal(np.asarray(check),readable)
plate_img=Image.fromarray(plate,'RGBA');plate_img.save(b+'Q060_PSD_PLATE_ONLY.png')
layer.save(b+'Q060_PSD_KOREAN_LETTERING_ONLY.png')
Image.fromarray(fa,'RGBA').save(b+'Q060_PSD_FINAL_ROI.png')
preview=Image.new('RGB',(W*3,H*3),'#858585')
original_source=Image.open(params.english_source_png).convert('RGBA').crop((x0,y0,x1,y1))
for i,img in enumerate((original_source,Image.fromarray(prior[y0:y1,x0:x1,:],'RGBA'),Image.fromarray(fa,'RGBA'))):
 p=Image.new('RGB',(W,H),'#777777');p.paste(img,mask=img.getchannel('A'))
 for j,scale in enumerate((1.0,.75,.5)):
  tw,th=round(W*scale),round(H*scale)
  preview.paste(p.resize((tw,th),Image.Resampling.LANCZOS),(i*W,j*H))
preview.save(b+'Q060_PSD_3WAY_ORIGINAL_OFFICIAL_TRIAL_100_75_50.jpg',quality=93)
report={'asset':'q060 A064FDFC','candidate_status':'TRIAL_UNAPPROVED_C2_NOT_RUN','runtime_validation':'UNTESTED','source_psd_sha256':hashlib.sha256(open(params.psd,'rb').read()).hexdigest(),'psd_layer':'objects/**Put background art inside this folder**/original-4x-Nearest-Neighbor/BG Flat Colors/Flat Colors 0','english_source_sha256':'6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc','old_official_sha256':hashlib.sha256(open(params.official_dds,'rb').read()).hexdigest(),'new_trial_sha256':hashlib.sha256(open(out,'rb').read()).hexdigest(),'source_bbox':[x0,y0,x1,y1],'localized_text':msg,'glyph_mask_bbox_native':[ox,oy,ox+mask.width,oy+mask.height],'change_pixels':changed,'outside_source_bbox_change_pixels':0,'persisted_decoder_roundtrip_mismatch':0,'original_header_equal':open(out,'rb').read(128)==open(params.official_dds,'rb').read(128),'psd_text_independent':False,'psd_background_rgb_recovered':True,'source_family_optical':'UNQUALIFIED_VISUAL_REVIEW_REQUIRED'}
open(b+'Q060_PSD_PILOT_REPORT.json','w').write(json.dumps(report,indent=2,ensure_ascii=False))
print(json.dumps(report,ensure_ascii=False))
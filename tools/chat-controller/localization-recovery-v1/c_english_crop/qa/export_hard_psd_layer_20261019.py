#!/usr/bin/env python3
"""Export upstream HARD [Rasterized] original PSD layer to separate test-only PNG.
Do not modify source, game DDS, active C OCR queue or 44 earlier candidates.
"""
import sys,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops
import numpy as np
BASE=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
Q=BASE/'qa_review_20261018'
DEP=Q/'upstream_psd_evidence'
sys.path.insert(0,str(DEP/'_qa_psd_deps'))
from psd_tools import PSDImage
psd=PSDImage.open(DEP/'33491F83_512x256.psd')
L=psd[1][1][0][0][3][2][1]
assert L.name=='HARD [Rasterized]' and L.kind=='pixel' and tuple(L.bbox)==(808,287,1068,373)
raw=L.topil()
assert raw is not None
rgba=raw.convert('RGBA')
assert rgba.size==(260,86)
outdir=Q/'next_last2'/'hard_upstream_layer'
outdir.mkdir(parents=True,exist_ok=True)
outfile=outdir/'Q062_HARD_UPSTREAM_PSD_RASTERIZED_LAYER_TEST_ONLY.png'
rgba.save(outfile,'PNG')
with Image.open(outfile) as im:
 assert im.tobytes()==rgba.tobytes()
src=BASE/'hd_original_108_verified/Q062_33491F83_BASE_READABLE_FLIPY.png'
with Image.open(src) as atlas:
 image=atlas.crop((808,287,1068,373)).convert('RGBA')
arr=np.array(rgba)
orig=np.array(image)
alpha=arr[:,:,3]
selected=alpha>0
avg_diff=float(np.abs(arr[:,:,:3].astype('int16')-orig[:,:,:3].astype('int16'))[selected].mean()) if selected.any() else 0.
count_same=int(np.all(arr==orig,axis=2).sum())
same_visible=int((np.all(arr==orig,axis=2)&selected).sum())
all_alpha=int(selected.sum())
alpha_src=np.count_nonzero(orig[:,:,3])
fonts=Image.open(outfile).getchannel('A').getbbox()
fontclip=np.asarray(rgba)[:,:,3]
border={'top':int((fontclip[:3]>0).sum()),'bottom':int((fontclip[-3:]>0).sum()),
        'left':int((fontclip[:,:3]>0).sum()),'right':int((fontclip[:,-3:]>0).sum())}
# Source vs PNG preview separate: checkerboard displays alpha and isolation
board=Image.new('RGB',(1240,390),(226,230,236))
dr=ImageDraw.Draw(board)
for k,(caption,rimg) in enumerate([('Original 4x source ROI incl plate',image),('PSD HARD [Rasterized] layer',rgba)]):
 x=10+k*620
 dr.text((x+8,12),caption,fill=(25,31,38))
 bg=Image.new('RGBA',(600,300),(221,225,230,255));d=ImageDraw.Draw(bg)
 for y in range(0,300,22):
  for xx in range(0,600,22):
   if (xx//22+y//22)%2==0:d.rectangle((xx,y,xx+21,y+21),fill=(244,247,249,255))
 r=rimg.resize((520,172),resample=Image.Resampling.NEAREST)
 bg.alpha_composite(r,(40,64))
 board.paste(bg.convert('RGB'),(x,48))
 dr.text((x+8,352),str((808,287,1068,373)),fill=(40,56,68))
preview=outdir/'Q062_HARD_ORIGINAL_VS_PSD_LAYER.jpg'
board.save(preview,quality=93)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for v in iter(lambda:f.read(1048576),b''):h.update(v)
 return h.hexdigest()
receipt={
 'status':'PSD_RASTERIZED_LAYER_EXPORTED_TEST_ONLY',
 'upstream_psd_git_blob_sha1':'e22ed4d6b9f7d8464fc40d724dd0b1d37e306104',
 'layer_name':L.name,'layer_kind':L.kind,'layer_bbox':list(L.bbox),
 'png_path':str(outfile),'png_sha256':sha(outfile),
 'source_4x_png_sha256':sha(src),'source_region_bbox':[808,287,1068,373],
 'layer_nonzero_alpha_pixels':all_alpha,'source_nonzero_alpha_pixels':int(alpha_src),
 'visible_layer_pixels_exact_source_rgba':same_visible,
 'mean_visible_rgb_abs_diff':round(avg_diff,4),
 'layer_alpha_bbox':fonts,'border_alpha_nonzero':border,
 'layer_only_is_source_pixel_identical':bool(same_visible==all_alpha),
 'source_atlas_untouched':True,
 'rework_candidates_test_only':True,
 'dds':'NOT_WRITTEN','A_B':'UNTOUCHED',
 'game':'UNTESTED',
 'comparison_jpg':str(preview)
}
(outdir/'Q062_HARD_LAYER_EVIDENCE.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
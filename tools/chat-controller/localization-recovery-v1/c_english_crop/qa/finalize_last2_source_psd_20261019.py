#!/usr/bin/env python3
"""Complete isolated QA candidate creation for final two C-slot English phrases.
Q201 uses exact unchanged source RGBA. Q062 uses SHA-pinned upstream
Photoshop raster layer, never mislabelled as source pixel-identical.
No active source/queue/DDS/previous crop modifications.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import hashlib,json,io,csv,zipfile,sys
import numpy as np
BASE=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
Q=BASE/'qa_review_20261018'
S=BASE/'hd_original_108_verified'
PSD=Q/'upstream_psd_evidence'
out=Q/'reworked_final2_test_only_20261019'
out.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(BASE/'hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip') as z:
 spec={i['png_filename']:i for i in csv.DictReader(io.StringIO(z.read('01_DDS_PNG_MANIFEST_108.csv').decode('utf-8-sig')))}
assert len(spec)==108
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

# CONIFEROUS FOREST: target T terminates at atlas x1155; no alpha at all in
# gap x1156..1172 within ROI y1924..2036. Next STAGES glyph starts x1173.
source201=S/'Q201_A9ABD877_BASE_READABLE_FLIPY.png'
assert sha(source201)==spec[source201.name]['png_sha256']
bbox=(89,1924,1167,2036)
with Image.open(source201) as im:
 assert im.mode=='RGBA' and im.format=='PNG'
 native=im.crop(bbox)
 alpha=np.asarray(im.getchannel('A'))
 assert np.count_nonzero(alpha[1924:2036,1157:1173])==0  # last T antialias at x1156 retained
 assert np.count_nonzero(alpha[1924:2036,1173:1186])>0
q201dir=out/'059_Q201_CONIFEROUS_FOREST'
q201dir.mkdir(parents=True,exist_ok=True)
q201png=q201dir/'english_native_c_crop_candidate.png'
if not q201png.exists():native.save(q201png)
with Image.open(q201png) as cmp:
 assert cmp.size==native.size and cmp.mode=='RGBA' and cmp.tobytes()==native.tobytes()
record201={
 'phrase':'CONIFEROUS FOREST','index':59,
 'status':'TEST_ONLY_NATIVE_4X_EXACT_PIXELS_CROP',
 'source_png':source201.name,'source_sha256':sha(source201),
 'source_bbox_xyxy':list(bbox),
 'destination_png':str(q201png),'destination_sha256':sha(q201png),
 'native_rgba_pixel_identical_to_original_source':True,
 'right_side_gap_zero_alpha':True,'adjacent_STAGES_excluded':True,
 'manual_fine_qa':'PENDING','runtime':'UNTESTED',
 'A_B':'UNTOUCHED','dds':'NOT_WRITTEN'}
(q201dir/'manifest.json').write_text(json.dumps(record201,ensure_ascii=False,indent=2)+'\n')

# HARD: verified upstream PSD rasterized text-only layer.
# Is not byte identical to flattened PNG; mark distinct provenance and difference.
sys.path.insert(0,str(PSD/'_qa_psd_deps'))
from psd_tools import PSDImage
source62=S/'Q062_33491F83_BASE_READABLE_FLIPY.png'
assert sha(source62)==spec[source62.name]['png_sha256']
psdf=PSD/'33491F83_512x256.psd'
assert len(psdf.read_bytes())==8669875
with psdf.open('rb') as f:
 h=hashlib.sha1()
 h.update(b'blob 8669875\x00')
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()=='e22ed4d6b9f7d8464fc40d724dd0b1d37e306104'
psd=PSDImage.open(psdf)
layer=psd[1][1][0][0][3][2][1]
assert layer.name=='HARD [Rasterized]' and layer.kind=='pixel' and tuple(layer.bbox)==(808,287,1068,373)
real=layer.topil().convert('RGBA')
assert real.size==(260,86)
pad=8
padded=Image.new('RGBA',(real.width+2*pad,real.height+2*pad),(0,0,0,0))
padded.paste(real,(pad,pad))
q062dir=out/'036_Q062_HARD_PSD_RASTER_LAYER'
q062dir.mkdir(parents=True,exist_ok=True)
q062png=q062dir/'english_psd_layer_test_candidate.png'
if not q062png.exists():padded.save(q062png)
with Image.open(q062png) as check:
 assert check.mode=='RGBA' and check.size==padded.size and check.tobytes()==padded.tobytes()
 assert check.crop((pad,pad,pad+260,pad+86)).tobytes()==real.tobytes()
with Image.open(source62) as orig:
 sourcepart=np.asarray(orig.crop((808,287,1068,373)).convert('RGBA'))
layerpart=np.asarray(real)
visible=layerpart[:,:,3]>0
same_visible=int((np.all(sourcepart==layerpart,axis=2)&visible).sum())
total_visible=int(visible.sum())
assert 0<same_visible<total_visible
record62={
 'phrase':'HARD','index':36,
 'status':'TEST_ONLY_PSD_RASTERIZED_LAYER_ISOLATED',
 'source_png':source62.name,'source_png_sha256':sha(source62),
 'upstream_repository':'Sonic-TV/OR2006Sprites',
 'upstream_git_commit':'3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6',
 'upstream_psd_git_blob_sha1':h.hexdigest(),
 'upstream_psd_layer_path':'/1/1/0/0/3/2/1',
 'layer_name':layer.name,'layer_kind':layer.kind,
 'layer_original_canvas_bbox':[808,287,1068,373],
 'padding_transparent_pixels':pad,
 'source_rgba_pixel_identical':False,
 'pixel_agreement_on_visible_psd_layer':{'identical':same_visible,'total':total_visible},
 'destination_png':str(q062png),'destination_sha256':sha(q062png),
 'plate_and_background_are_removed_by_separate_psd_layer':True,
 'human_visual_final_qa':'PENDING','game_runtime':'UNTESTED','A_B':'UNTOUCHED','dds':'NOT_WRITTEN'}
(q062dir/'manifest.json').write_text(json.dumps(record62,ensure_ascii=False,indent=2)+'\n')
summary={
 'status':'FINAL_2_QA_CANDIDATES_CREATED_WITH_DIFFERENT_PROVENANCE',
 'source_HD_originals_sha_verified':108,
 'prior_native_pixel_exact_crops':44,
 'new_native_pixel_exact_crops':1,
 'new_psd_layer_crops_NOT_source_pixel_identical':1,
 'total_test_only_rework_candidates':46,
 'historical_native_test_only_crops_retained':242,
 'no_composite_or_DDS_or_A_B':True,
 'game_status':'UNTESTED','manual_QA':'PENDING',
 'items':[record201,record62]}
(Q/'FINAL_2_LAYER_EXTRACTION_20261019.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')

board=Image.new('RGB',(1500,620),(227,230,235))
d=ImageDraw.Draw(board)
inputs=[
 ('CONIFEROUS FOREST - old bbox, adjacent STAGES',
  (S/source201.name), (89,1924,1186,2036)),
 ('CONIFEROUS FOREST - new native pixel exact',q201png,None),
 ('HARD - original 4x composite, includes plate',source62,(808,287,1068,373)),
 ('HARD - PSD raster text layer, test-only',q062png,None)]
for i,(label,path,cropbox) in enumerate(inputs):
 x=(i%2)*750;y=(i//2)*305
 d.rounded_rectangle((x+6,y+6,x+742,y+298),radius=10,fill='#ffffff',outline='#9aa4ad',width=2)
 d.text((x+16,y+16),label,fill='#243245')
 with Image.open(path) as im:
  if cropbox:im=im.crop(cropbox)
  im=im.convert('RGBA')
  bg=Image.new('RGBA',(710,245),(222,230,237,255));sq=ImageDraw.Draw(bg)
  for yy in range(0,245,22):
   for xx in range(0,710,22):
    if (xx//22+yy//22)%2==0:sq.rectangle((xx,yy,xx+21,yy+21),fill='#f5f6f8')
  im.thumbnail((695,230),Image.Resampling.LANCZOS)
  bg.alpha_composite(im,((710-im.width)//2,(245-im.height)//2))
  board.paste(bg.convert('RGB'),(x+20,y+45))
comparison=Q/'FINAL2_SOURCE_VS_EXTRACTED_20261019.jpg'
board.save(comparison,quality=94)
summary['comparison']=str(comparison)
(Q/'FINAL_2_LAYER_EXTRACTION_20261019.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({
 'state':summary['status'],'native_source_exact':1,'psd_rasterized_layer':1,
 'source_region_same_visible_psd':same_visible,'source_region_all_visible_psd':total_visible,
 'total_candidates':46,'comparison':str(comparison),
 'DSD_or_game_modified':False},ensure_ascii=False))
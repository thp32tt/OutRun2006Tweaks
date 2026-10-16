#!/usr/bin/env python3
"""Produce TEST_ONLY F2 Q051 five-Hangul DDS with hard-pinned original/F1 and native-glyph guards.

Never mutates original, F0, F1, VR or controller artifacts. Requires transfer ZIP
containing independently verified palette Korean labels derived from user ImageGen.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import io,json,hashlib,zipfile
import numpy as np

ROOT=Path('/home/chatgpt-runner2/work/c_salvage_text_roi')
F1DIR=ROOT/'F0_Q051_NATIVE_DDS_20261016'
OUT=ROOT/'F2_Q051_FIVE_LABELS_20261016'
SOURCE=ROOT/'source_full_20261012/q051_FF2462BB_GITHUB_HD_SOURCE_20261015.dds'
READ=ROOT/'source_full_20261012/q051_FF2462BB_FLIPY_CHECK_ORIENTATION.png'
F1=F1DIR/'Q051_TIME_KO_F1_TEST_ONLY.dds'
BUNDLE=F1DIR/'F2_TRANSFER_4_SPRITES.zip'
SHA={
 'original':'5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67',
 'readable':'2da1b6f01219356ddc6ea925bd8fcd4afd37d9040eb48081a40861cc649da6f0',
 'f1':'4f07654689e93bfb65cdd0ca710490e7ecbc0e40f31f3109f7adceb442f2a956',
 'bundle':'2dd9088f4ab315e2008d334bb905cd5257b2910387cfda5f736f1c2399f3bbd0'}
SPRITE_SHA={
 'TOTAL_TIME':'59b5c05b6d804ecbf347ee673d6e7abe89e08b90a19554049b9670fb3ad54d32',
 'LAP_TIME':'1751cf84c797638365088bb91ea7dddb2e8c2540d53d31b8c1ced5b64a6f9623',
 'HEARTS':'3a8e7a121169df5309af216c3eefbedda6e0b7bef77ccaa8f7ca55d482df7a9e',
 'SCORE':'6b56f6c64ca16d530c3d52061d3785c7bb57efafe803e4984caee978f7b96fd1'}
LABELS=[('TOTAL_TIME','총 시간',(14,628,500,713)),('LAP_TIME','랩 타임',(500,628,1011,711)),('HEARTS','하트',(1011,628,1328,713)),('SCORE','점수',(1328,628,1600,713))]
TIME=(1595,608,1845,727)
W,H=4096,2048
sha=lambda b:hashlib.sha256(b).hexdigest()
def verified(p,name):
 raw=p.read_bytes();assert sha(raw)==SHA[name],f'{name} SHA_MISMATCH';return raw

def write_if_new(p,b):
 if p.exists():
  assert sha(p.read_bytes())==sha(b),'NON_IDENTICAL_EXISTING_NO_OVERWRITE:'+str(p)
 else:
  p.write_bytes(b)

def main():
 src=verified(SOURCE,'original'); f1=verified(F1,'f1'); verified(READ,'readable');verified(BUNDLE,'bundle')
 assert len(src)==len(f1)==128+W*H*4==33554560
 assert src[:128]==f1[:128]
 with Image.open(READ) as image: original=np.array(image.convert('RGBA'))
 with Image.open(F1) as image: f1_read=np.array(image.convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM))
 assert original.shape==(H,W,4) and f1_read.shape==(H,W,4)
 # Previously proven readable orientation is literal DDS top-bottom flip; re-check.
 src_pixels=np.frombuffer(src,dtype=np.uint8,offset=128).reshape(H,W,4)
 assert np.array_equal(original,src_pixels[::-1]), 'SOURCE_READABLE_DDS_DIFFER'
 f1_difference=np.any(original!=f1_read,axis=2)
 permitted=np.zeros((H,W),dtype=bool)
 permitted[TIME[1]:TIME[3],TIME[0]:TIME[2]]=True
 assert not np.any(f1_difference & ~permitted),'F1_CHANGED_OUTSIDE_TIME'
 assert int(f1_difference.sum())==14156,'F1_PIXEL_DIFF_COUNT'
 raw=bytearray(f1)
 dst=np.frombuffer(raw,dtype=np.uint8,offset=128).reshape(H,W,4)
 before=np.frombuffer(f1,dtype=np.uint8,offset=128).reshape(H,W,4)
 meta=[];patch_masks={}
 with zipfile.ZipFile(BUNDLE) as z:
  assert set(z.namelist())==set(n+'.png' for n,_,_ in LABELS)
  for name,korean,(x0,y0,x1,y1) in LABELS:
   b=z.read(name+'.png');assert sha(b)==SPRITE_SHA[name],name+'_SPRITE_SHA'
   with Image.open(io.BytesIO(b)) as im: kr=np.asarray(im.convert('RGBA')).copy()
   # Palette-alpha normalization used in accepted F1 quality-reduced pilot.
   alpha=kr[:,:,3].copy();kr[:,:,3][alpha<=8]=0;kr[:,:,3][alpha>=250]=255
   kr[:,:,:3][kr[:,:,3]==0]=0
   assert np.count_nonzero(kr[:,:,3])>=6000,name+'_EMPTY_KOREAN'
   source=original[y0:y1,x0:x1]
   mask=source[:,:,3]>0
   # At LAP TIME y>=708, a dark blue tip links to red nonletter HUD art at y720.
   # Protect that x610..657 feature; do not erase the stripe or its shadow.
   if name=='LAP_TIME':
    ax0,ax1=610-x0,658-x0
    mask[708-y0:,ax0:ax1]=False
   yy,xx=np.where(mask)
   assert len(xx)>7000,name+'_MISSING_SOURCE'
   rgb=source[:,:,:3]
   red=(rgb[:,:,0]>120)&(rgb[:,:,1]<70)&(rgb[:,:,2]<100)&mask
   white=(rgb[:,:,0]>210)&(rgb[:,:,1]>210)&(rgb[:,:,2]>210)&mask
   assert red.sum()==0 and white.sum()==0,name+'_NONLETTER_ART_DETECTED'
   assert not (mask[:3].any() or mask[-1:].any() or mask[:,:3].any() or mask[:,-3:].any()),name+'_MASK_EDGE'
   tight=(x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1)
   safe=(tight[0]+2,tight[1]+2,tight[2]-2,tight[3]-2)
   kh,kw=kr.shape[:2];sw,sh=safe[2]-safe[0],safe[3]-safe[1]
   assert kw<=sw and kh<=sh,(name,'UNSAFE_KR_SIZE',kw,kh,sw,sh)
   px=safe[0]+(sw-kw)//2;py=safe[1]+(sh-kh)//2
   assert py>=safe[1] and px>=safe[0]
   # Native, flipped DDS pixel mask update. No changes to unrelated pixels.
   raw_x=xx+x0; raw_y=H-1-(yy+y0)
   assert np.array_equal(dst[raw_y,raw_x],src_pixels[raw_y,raw_x]),name+'_SOURCE_ALREADY_CHANGED'
   dst[raw_y,raw_x]=np.array([0,10,57,0],dtype=np.uint8)
   permitted[y0:y1,x0:x1]|=mask
   # Korean layers are generated with RGBA alpha, not composite backgrounds.
   ky,kx=np.where(kr[:,:,3]>0)
   paste_x=kx+px;paste_y=ky+py
   assert min(paste_x)>=safe[0] and max(paste_x)<safe[2],name+'_KR_WIDTH'
   assert min(paste_y)>=safe[1] and max(paste_y)<safe[3],name+'_KR_HEIGHT'
   assert np.all(src_pixels[H-1-paste_y,paste_x,3]>=0)
   dst[H-1-paste_y,paste_x]=kr[ky,kx]
   permitted[py:py+kh,px:px+kw]|=(kr[:,:,3]>0)
   meta.append({'id':name,'ko':korean,'english_glyph_bbox_readable':tight,
        'safe_bbox_readable':safe,'clean_mask_pixels':int(mask.sum()),
        'ko_rgba_size':[kw,kh],'ko_nontransparent_pixels':int(len(ky)),
        'paste_xy_readable':[px,py],'transfer_sprite_sha256':SPRITE_SHA[name],
        'art_exclusion':'HUD_TIP_AT_X610_658_Y708_PLUS' if name=='LAP_TIME' else 'NONE'})
   patch_masks[name]=mask
 # Byte-level F1 TIME preserved exactly.
 for y in range(H-TIME[3],H-TIME[1]):
  lo=128+4*(y*W+TIME[0]);hi=128+4*(y*W+TIME[2]);assert raw[lo:hi]==f1[lo:hi],'F1_TIME_ALTERED'
 final=bytes(raw)
 assert final[:128]==src[:128] and len(final)==len(src)
 with Image.open(io.BytesIO(final)) as im: decoded=np.array(im.convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM))
 changed=np.any(decoded!=original,axis=2)
 assert not np.any(changed & ~permitted),'PROTECTED_PIXEL_CHANGED'
 a,b,c,d=TIME
 assert np.array_equal(decoded[b:d,a:c],f1_read[b:d,a:c]),'F1_PIXEL_CHANGED'
 assert decoded.shape==(H,W,4)
 OUT.mkdir(parents=True,exist_ok=True)
 output=OUT/'Q051_5_LABELS_KO_F2_TEST_ONLY.dds'
 write_if_new(output,final)
 with Image.open(output) as im:
  persisted=np.array(im.convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM))
 assert np.array_equal(decoded,persisted),'PERSISTED_REDECODE_DIFFER'
 # Preserve natural atlas positions in native-readable preview at source resolution.
 orig_im=Image.fromarray(original,'RGBA');final_im=Image.fromarray(decoded,'RGBA')
 canvas=Image.new('RGB',(1040,5*150),(18,24,38));draw=ImageDraw.Draw(canvas)
 for i,(name,korean,bounds) in enumerate(LABELS+[('TIME','시간',TIME)]):
  if name!='TIME':bounds=tuple(meta[i]['english_glyph_bbox_readable'])
  x0,y0,x1,y1=bounds
  box=(max(0,x0-14),max(0,y0-14),min(W,x1+14),min(H,y1+14))
  for j,source_im in enumerate([orig_im,final_im]):
   roi=source_im.crop(box)
   bg=Image.new('RGBA',roi.size,(0,10,57,255));bg.alpha_composite(roi)
   visible=bg.convert('RGB');visible.thumbnail((490,110),Image.Resampling.LANCZOS)
   canvas.paste(visible,(10+j*520,i*150+28))
  draw.text((10,i*150+4),name+' ORIGINAL',fill='white')
  draw.text((530,i*150+4),name+' KOREAN F2',fill='white')
 preview=OUT/'Q051_F2_FIVE_LABELS_COMPARE_TEST_ONLY.png';canvas.save(preview)
 report={'schema':'outrun-q051-f2-five-labels-native-v2','F2_STATIC':'PASS_CANDIDATE',
  'source_dds_sha256':SHA['original'],'f1_dds_sha256':SHA['f1'],
  'source_readable_sha256':SHA['readable'],'sprite_bundle_sha256':SHA['bundle'],
  'dds_format':'DDS_UNCOMPRESSED_RGBA32','dds_size_bytes':len(final),'dimensions':[W,H],'mips':1,
  'labels':meta+[{'id':'TIME','ko':'시간','preserved_exact_from_F1':True}],
  'changed_pixels_vs_original':int(changed.sum()),'protected_changed_pixels':0,
  'f1_time_exact':True,'original_header_exact':True,'output_redecode_rgba_exact':True,
  'runtime_validation':'WAIVED_BY_USER_FOR_THIS_TEST_UNTESTED_NOT_PASS',
  'C1_C3':'NOT_RUN','approval':'TEST_ONLY_NOT_GAME_RELEASE',
  'original_and_F1_modified':False,
  'output_dds_sha256':sha(final),
  'outputs':{output.name:sha(final),preview.name:sha(preview.read_bytes())}}
 report_path=OUT/'Q051_F2_FIVE_LABELS_REPORT.json'
 write_if_new(report_path,(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
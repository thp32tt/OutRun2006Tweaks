#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json,hashlib,struct
base=Path('/home/chatgpt-runner2/work/outrun-c2-1920');g=base/'localization/graphics'
out=g/'role_C/20261010-C2-Q212-B357-INDEPENDENT-P1-MODE-FAMILY'
m=json.loads((out/'C2_Q212_B357_EXACT_BYTES_MACHINE.json').read_text())
src=Path('/home/chatgpt-runner2/tmp/c2_q212_source_en_20261010.dds')
off=g/'hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds'
tri=g/'role_B/20261010-B357-Q212-NATIVE-SOURCE-MODE-FAMILY/B357_Q212_TWO_FAMILY_NATIVE_UNAPPROVED.dds'
def decode(p):
 b=p.read_bytes();return np.frombuffer(b,dtype=np.uint8,offset=128).reshape(2048,2048,4)[:,:,[2,1,0,3]][::-1].copy()
S=decode(src);O=decode(off);T=decode(tri)
result=[]
for rg in m['regions']:
 i=rg['id'];x0,y0,x1,y1=rg['source_full_bbox']; sx0,sy0,sx1,sy1=rg['source_native_alpha32_bbox_measured']
 sr=S[y0:y1,x0:x1];old=O[y0:y1,x0:x1];cur=T[y0:y1,x0:x1]
 Y,X=np.indices((y1-y0,x1-x0))
 outside_core=(X+x0<sx0)|(X+x0>=sx1)|(Y+y0<sy0)|(Y+y0>=sy1)
 visible_cur=cur[:,:,3]>32
 old_alpha=old[:,:,3]>32
 source_alpha=sr[:,:,3]>32
 unexpected=visible_cur & outside_core & ~source_alpha
 inherited=np.all(old==cur,axis=2)&old_alpha&visible_cur
 residual=inherited & outside_core
 yv,xv=np.where(unexpected)
 assert len(xv)>0
 bbox=[int(x0+xv.min()),int(y0+yv.min()),int(x0+xv.max()+1),int(y0+yv.max()+1)]
 # Exact protected-region mask before visualization; rendered magenta for rejected glyph pixels.
 bg=Image.new('RGBA',(x1-x0,y1-y0),(123,123,123,255))
 curim=Image.fromarray(np.ascontiguousarray(cur),'RGBA')
 bg.alpha_composite(curim)
 display=np.asarray(bg.convert('RGB')).copy()
 display[unexpected]=np.array([255,0,190],dtype=np.uint8)
 annotated=Image.fromarray(display)
 draw=ImageDraw.Draw(annotated)
 draw.rectangle((sx0-x0,sy0-y0,sx1-x0-1,sy1-y0-1),outline=(0,255,80),width=1)
 annotated.resize((annotated.width*3,annotated.height*3),Image.Resampling.NEAREST).save(out/f'C2_Q212_B357_{i.upper()}_ALPHA32_SOURCE_CORE_OVERFLOW_3X.png')
 # Side-by-side true English and final at readable native with labeled source core.
 comp=Image.new('RGB',((x1-x0)*2,(y1-y0)+18),(30,30,30));d=ImageDraw.Draw(comp)
 d.text((3,2),'ENGLISH SOURCE',fill=(255,255,255));d.text((x1-x0+3,2),'TRIAL SAVED DDS',fill=(255,255,255))
 for j,x in enumerate([sr,cur]):
  layer=Image.new('RGBA',(x1-x0,y1-y0),(127,127,127,255));layer.alpha_composite(Image.fromarray(np.ascontiguousarray(x),'RGBA'));comp.paste(layer.convert('RGB'),((x1-x0)*j,18))
 comp.save(out/f'C2_Q212_B357_{i.upper()}_SOURCE_VS_PERSISTED_NATIVE.png')
 result.append({'id':i,'source_alpha32_core_bbox':[sx0,sy0,sx1,sy1],'trial_alpha32_full_bbox':rg['candidate_native_alpha32_bbox_full_scope'],
 'candidate_alpha32_outside_source_core_pixels':int(np.count_nonzero(visible_cur & outside_core)),
 'candidate_alpha32_not_supported_by_source_alpha32_pixels':int(np.count_nonzero(unexpected)),
 'candidate_alpha32_source_core_overflow_bbox':bbox,
 'inherited_official_visible_pixels_unchanged_in_trial_inside_cell':int(inherited.sum()),
 'inherited_old_visible_pixels_unchanged_outside_source_core':int(residual.sum()),
 'original_source_alpha32_pixels_in_cell':int(source_alpha.sum()),'trial_alpha32_pixels_in_cell':int(visible_cur.sum())})
m['additional_core_overlap_audit']=result
m['conclusion']='HARD_FAIL_SOURCE_GLYPH_CORE_OVERFLOW_AND_INHERITED_OLD_KOREAN_IN_SAVED_TRIAL'
m['outside_full_source_original_roi_rgba_changed']=0
m['visual_approval_not_inferred']=True
(out/'C2_Q212_B357_EXACT_BYTES_MACHINE.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))

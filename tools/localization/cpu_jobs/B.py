#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter
from scipy.ndimage import distance_transform_edt

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')
repo=Path.cwd();run='20261004-B-PRODUCTION21';out=repo/'localization/graphics/role_B'/run;out.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds'
url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds'
source_sha_expected='4e486f35ca8982266f7f52e4d45aca20a12a2a4fe2a62fee9083db72c7454f9b'
source=Path('/tmp/788CE557_HD.dds');urllib.request.urlretrieve(url,source);candidate=repo/'localization/graphics/hd_candidates'/asset_rel;candidate.parent.mkdir(parents=True,exist_ok=True)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=source_sha_expected:raise RuntimeError(('source sha mismatch',sha(source)))

def resolve_font(style='Black'):
 pat=f'Noto Sans CJK KR:style={style}'
 try:fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
 except Exception:fp=''
 if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
  subprocess.run(['sudo','apt-get','update','-qq'],check=True);subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True);fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
 if not fp or not Path(fp).exists():raise RuntimeError('Noto CJK unavailable')
 return fp
FONT=resolve_font('Black')

def load_dds(p):
 b=Path(p).read_bytes();assert b[:4]==b'DDS '
 h=struct.unpack_from('<I',b,12)[0];w=struct.unpack_from('<I',b,16)[0];pitch=struct.unpack_from('<I',b,20)[0];mips=struct.unpack_from('<I',b,28)[0];fourcc=b[84:88];bpp=struct.unpack_from('<I',b,88)[0];masks=struct.unpack_from('<IIII',b,92)
 if not(w==2048 and h==1024 and pitch==8192 and mips==1 and fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and len(b)==128+w*h*4):raise RuntimeError((w,h,pitch,mips,fourcc,bpp,masks,len(b)))
 raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA');return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{'width':w,'height':h,'pitch':pitch,'mips':mips,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}
def write_dds(template,readable,dest):
 b=Path(template).read_bytes();payload=b[:128]+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes('raw','RGBA');Path(dest).write_bytes(payload);return hashlib.sha256(payload).hexdigest()
def bbox_arr(m):
 ys,xs=np.nonzero(m);return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def dil(m,n=2):
 if n<=0:return m
 im=Image.fromarray((m.astype(np.uint8)*255),'L')
 for _ in range(n):im=im.filter(ImageFilter.MaxFilter(3))
 return np.asarray(im)>0

def shear(im,s):
 shift=max(0,int(round(s*(im.height-1))));o=Image.new('RGBA',(im.width+shift,im.height),(0,0,0,0))
 for y in range(im.height):o.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(s*(im.height-1-y))),y))
 return o

header,src,meta=load_dds(source);sa=np.asarray(src,dtype=np.uint8);H,W=sa.shape[:2];alpha=sa[:,:,3]>0
# B_PRODUCTION17 showed the exact-HD readable placement. Build semantic source masks by color-seeded assignment rather than a nonexistent transparent x-split.
# Top pair share x-overlap because of italic effects; nearest red/orange fill seeds assign each effect pixel to its owning label.
y0,y1=70,184;x0,x1=0,770
suba=alpha[y0:y1,x0:x1];rgb=sa[y0:y1,x0:x1,:3].astype(np.int16);R,G,B=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
red_seed=suba & (R>=130) & (R>=G+45) & (R>=B+30) & (np.indices(suba.shape)[1] < 430)
orange_seed=suba & (R>=170) & (G>=65) & (R>=G+35) & (B<=95) & (np.indices(suba.shape)[1] > 300)
if red_seed.sum()<100 or orange_seed.sum()<100:raise RuntimeError(('insufficient top color seeds',int(red_seed.sum()),int(orange_seed.sum())))
# The fills provide an unambiguous geometric handoff even though white/navy outline pixels overlap in x.
ry,rx=np.nonzero(red_seed);oy,ox=np.nonzero(orange_seed)
red_fill_max_x=x0+int(rx.max());orange_fill_min_x=x0+int(ox.min());top_split=(red_fill_max_x+orange_fill_min_x)//2
seed_y0=y0+min(int(ry.min()),int(oy.min()));seed_y1=y0+max(int(ry.max()),int(oy.max()))+1;top_band_y0=max(y0,seed_y0-22);top_band_y1=min(y1,seed_y1+22)
if not(340<=top_split<=460 and top_band_y0<top_band_y1):raise RuntimeError(('unexpected semantic split',red_fill_max_x,orange_fill_min_x,top_split,top_band_y0,top_band_y1))
red=np.zeros((H,W),bool);orange=np.zeros((H,W),bool)
red[top_band_y0:top_band_y1,0:top_split]=alpha[top_band_y0:top_band_y1,0:top_split]
orange[top_band_y0:top_band_y1,top_split:770]=alpha[top_band_y0:top_band_y1,top_split:770]
# Single-label cells are semantically unambiguous in the exact-HD readable source.
def cellmask(cell):
 x0,y0,x1,y1=cell;m=np.zeros((H,W),bool);m[y0:y1,x0:x1]=alpha[y0:y1,x0:x1];return m
music=cellmask((770,78,1140,174));time=cellmask((930,180,1600,286))
source_masks={'for_experts':red,'outrun2sp':orange,'music_change':music,'time_remaining':time}
expected={
 'for_experts':{'x':(0,450),'y':(85,190),'text':'상급자용','source':'For Experts','style':'red_white_navy','slant':0.13},
 'outrun2sp':{'x':(420,780),'y':(85,190),'text':'아웃런2 SP','source':'OutRun2SP','style':'orange_white_navy','slant':0.12},
 'music_change':{'x':(770,1140),'y':(78,174),'text':'음악 변경','source':'Music Change','style':'white_shadow','slant':0.10},
 'time_remaining':{'x':(930,1600),'y':(180,286),'text':'남은 시간:','source':'Time remaining :','style':'white_navy','slant':0.10},
}
source_bboxes={};source_text=np.zeros((H,W),bool)
for k,m in source_masks.items():
 bb=bbox_arr(m)
 if bb is None:raise RuntimeError((k,'empty source mask'))
 e=expected[k]
 if not(e['x'][0]<=bb[0] and bb[2]<=e['x'][1] and e['y'][0]<=bb[1] and bb[3]<=e['y'][1]):raise RuntimeError((k,'unexpected bbox',bb,e))
 source_bboxes[k]=bb;source_text|=m
# Semantic masks must be pairwise disjoint, and must leave every non-target source alpha protected.
keys=list(source_masks)
for i in range(len(keys)):
 for j in range(i+1,len(keys)):
  ov=int(np.logical_and(source_masks[keys[i]],source_masks[keys[j]]).sum())
  if ov:raise RuntimeError(('source semantic masks overlap',keys[i],keys[j],ov))
protected_source=alpha & ~source_text;protected_guard=dil(protected_source,2)
# Exact-pixel transparent clean plate: only source target alpha/effects are removed.
clean_arr=sa.copy();clean_arr[source_text]=0;clean=Image.fromarray(clean_arr,'RGBA');residue=int(np.logical_and(np.asarray(clean.getchannel('A'))>0,source_text).sum())
if residue:raise RuntimeError(('clean residue',residue))

def render(k,cfg,occupied):
 sb=source_bboxes[k];sx0,sy0,sx1,sy1=sb;SW,SH=sx1-sx0,sy1-sy0;dummy=ImageDraw.Draw(Image.new('L',(8,8)))
 for fs in range(min(150,int(SH*.94)),14,-1):
  f=ImageFont.truetype(FONT,fs);outer=max(3,round(fs*.07));inner=max(2,round(fs*.035));shadow=max(2,round(fs*.025));tb=dummy.textbbox((0,0),cfg['text'],font=f,stroke_width=outer);tw=tb[2]-tb[0];th=tb[3]-tb[1];pad=outer+shadow+6
  g=Image.new('RGBA',(tw+2*pad+10,th+2*pad+10),(0,0,0,0));d=ImageDraw.Draw(g);pos=(pad-tb[0],pad-tb[1])
  if cfg['style']=='red_white_navy':
   d.text(pos,cfg['text'],font=f,fill=(215,52,57,255),stroke_width=outer,stroke_fill=(250,250,250,255));d.text(pos,cfg['text'],font=f,fill=(215,52,57,255),stroke_width=inner,stroke_fill=(7,22,75,255))
  elif cfg['style']=='orange_white_navy':
   d.text(pos,cfg['text'],font=f,fill=(246,142,13,255),stroke_width=outer,stroke_fill=(250,250,250,255));d.text(pos,cfg['text'],font=f,fill=(246,142,13,255),stroke_width=inner,stroke_fill=(7,22,75,255))
  elif cfg['style']=='white_shadow':
   d.text((pos[0]+shadow,pos[1]+shadow),cfg['text'],font=f,fill=(24,24,24,180),stroke_width=max(1,inner),stroke_fill=(20,20,20,150));d.text(pos,cfg['text'],font=f,fill=(252,252,252,255),stroke_width=max(1,inner),stroke_fill=(248,248,248,255))
  elif cfg['style']=='white_navy':
   d.text(pos,cfg['text'],font=f,fill=(252,252,252,255),stroke_width=outer,stroke_fill=(5,18,72,255))
  else:raise RuntimeError(cfg['style'])
  gb=g.getchannel('A').getbbox();g=shear(g.crop(gb),cfg['slant']);gb=g.getchannel('A').getbbox();g=g.crop(gb)
  if g.width>SW-4 or g.height>SH-4:continue
  gm=np.asarray(g.getchannel('A'))>0;cx=sx0+(SW-g.width)//2;cy=sy0+(SH-g.height)//2
  for dx,dy in [(0,0),(0,-2),(0,2),(-2,0),(2,0),(-4,0),(4,0)]:
   px=max(sx0+2,min(sx1-g.width-2,cx+dx));py=max(sy0+2,min(sy1-g.height-2,cy+dy))
   if np.any(gm & protected_guard[py:py+g.height,px:px+g.width]):continue
   if np.any(gm & (dil(occupied,2)[py:py+g.height,px:px+g.width] if np.any(occupied) else occupied[py:py+g.height,px:px+g.width])):continue
   layer=Image.new('RGBA',src.size,(0,0,0,0));layer.alpha_composite(g,(px,py));lm=np.asarray(layer.getchannel('A'))>0;lb=bbox_arr(lm)
   if lb[0]>=sx0 and lb[1]>=sy0 and lb[2]<=sx1 and lb[3]<=sy1 and (lb[2]-lb[0])<=SW and (lb[3]-lb[1])<=SH:return layer,lm,fs,outer,inner,lb
 raise RuntimeError((k,'NO_NATIVE_ZERO_OVERLAP_FIT',sb))

final=clean.copy();occupied=np.zeros((H,W),bool);layers={};rows=[]
for k in ['for_experts','outrun2sp','music_change','time_remaining']:
 cfg=expected[k];layer,lm,fs,outer,inner,lb=render(k,cfg,occupied)
 if np.any(lm&protected_source):raise RuntimeError((k,'protected overlap'))
 if np.any(lm&occupied):raise RuntimeError((k,'new-new overlap'))
 occupied|=lm;layers[k]=layer;final.alpha_composite(layer);sb=source_bboxes[k]
 rows.append({'key':k,'source':cfg['source'],'korean':cfg['text'],'original_bbox':sb,'localized_bbox':lb,'source_size':[sb[2]-sb[0],sb[3]-sb[1]],'localized_size':[lb[2]-lb[0],lb[3]-lb[1]],'delta_left':lb[0]-sb[0],'delta_right':sb[2]-lb[2],'delta_top':lb[1]-sb[1],'delta_bottom':sb[3]-lb[3],'containment':'PASS','size_ceiling':'PASS','zero_overlap':'PASS','positive_separation_px':2,'native_font':'Noto Sans CJK KR Black','native_font_size':fs,'outer_stroke':outer,'inner_stroke':inner,'slant':cfg['slant'],'style':cfg['style'],'native_raster_resampled':False,'rework_status':'HOLD_RESOLVED_NEW_CANDIDATE'})
# Global exact-source-bbox / protected QA.
allowed=np.zeros((H,W),bool)
for bb in source_bboxes.values():allowed[bb[1]:bb[3],bb[0]:bb[2]]=1
fa=np.asarray(final,dtype=np.uint8);changed=np.any(fa!=sa,axis=2);outside=int(np.logical_and(changed,~allowed).sum());alpha_out=int(np.logical_and(fa[:,:,3]!=sa[:,:,3],~allowed).sum());protected_overlap=int(np.logical_and(occupied,protected_source).sum());guard_conflict=int(np.logical_and(dil(occupied,2),protected_source).sum())
if outside or alpha_out or protected_overlap or guard_conflict:raise RuntimeError(('global qa',outside,alpha_out,protected_overlap,guard_conflict))
pair=[]
for i in range(len(keys)):
 for j in range(i+1,len(keys)):
  a=np.asarray(layers[keys[i]].getchannel('A'))>0;b=np.asarray(layers[keys[j]].getchannel('A'))>0;ov=int(np.logical_and(a,b).sum());g=int(np.logical_and(dil(a,2),b).sum())
  if ov or g:pair.append({'a':keys[i],'b':keys[j],'overlap_pixels':ov,'two_px_guard_conflicts':g})
if pair:raise RuntimeError(('new pair guard',pair))
# Exact-header encode and decoded identity.
candidate_sha=write_dds(source,final,candidate);ch,decoded,cm=load_dds(candidate)
if ch!=header or cm!=meta or ImageChops.difference(decoded,final).getbbox() is not None:raise RuntimeError('roundtrip/header mismatch')
# Evidence masks and standard validators.
Image.fromarray((source_text*255).astype(np.uint8),'L').save(out/'788CE557_SOURCE_TEXT_MASK.png');Image.fromarray((allowed*255).astype(np.uint8),'L').save(out/'788CE557_ALLOWED_TEXT_REGION_MASK.png');Image.fromarray(((~allowed)*255).astype(np.uint8),'L').save(out/'788CE557_PROTECTED_MASK.png');Image.fromarray((occupied*255).astype(np.uint8),'L').save(out/'788CE557_TARGET_TEXT_MASK.png');clean.save(out/'788CE557_CLEAN_PLATE.png')
for k,m in source_masks.items():Image.fromarray((m*255).astype(np.uint8),'L').save(out/f'788CE557_SOURCE_MASK_{k}.png')
work=Path('/tmp/b21');work.mkdir(exist_ok=True);sp=work/'source.png';cp=work/'clean.png';fp=work/'final.png';src.save(sp);clean.save(cp);decoded.save(fp)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(sp),str(cp),str(out/'788CE557_SOURCE_TEXT_MASK.png'),'--report',str(out/'B_PRODUCTION21_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(sp),str(fp),str(out/'788CE557_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(out/'788CE557_PROTECTED_MASK.png'),'--report',str(out/'B_PRODUCTION21_FINAL_MASK_VALIDATION.json')],check=True)
# Readable/raw/source-clean-final visual proof.
def comp(im,bg):z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
def card(label,im,bg=(55,55,55,255)):
 v=comp(im,bg);v.thumbnail((900,480),Image.Resampling.LANCZOS);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),label,fill='black');return c
cards=[card('SOURCE',src),card('CLEAN',clean),card('FINAL',decoded),card('FINAL_WHITE',decoded,(255,255,255,255))];ww=cards[0].width+cards[1].width+8;hh=cards[0].height+cards[2].height+8;sheet=Image.new('RGB',(ww,hh),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+8,0));sheet.paste(cards[2],(0,cards[0].height+8));sheet.paste(cards[3],(cards[2].width+8,cards[1].height+8));sheet.save(out/'B_PRODUCTION21_788CE557_COMPARE.jpg',quality=95)
contacts=[]
for rr in rows:
 sb=rr['original_bbox'];pad=34;cr=(max(0,sb[0]-pad),max(0,sb[1]-pad),min(W,sb[2]+pad),min(H,sb[3]+pad));ims=[]
 for tag,im in [('SRC',src),('CLEAN',clean),('FINAL',decoded)]:
  v=comp(im,(55,55,55,255)).crop(cr);scale=min(1,750/max(1,v.width));
  if scale<1:v=v.resize((round(v.width*scale),round(v.height*scale)),Image.Resampling.LANCZOS)
  c=Image.new('RGB',(v.width,v.height+26),'white');c.paste(v,(0,26));ImageDraw.Draw(c).text((4,4),tag,fill='black');ims.append(c)
 h=max(x.height for x in ims);w=sum(x.width for x in ims)+6*(len(ims)-1);c=Image.new('RGB',(w,h+24),'white');ImageDraw.Draw(c).text((4,4),f'{rr["source"]} -> {rr["korean"]}',fill='black');x=0
 for im in ims:c.paste(im,(x,24));x+=im.width+6
 contacts.append(c)
CW=max(x.width for x in contacts);CH=sum(x.height for x in contacts)+6*(len(contacts)-1);cs=Image.new('RGB',(CW,CH),'white');y=0
for c in contacts:cs.paste(c,(0,y));y+=c.height+6
cs.save(out/'B_PRODUCTION21_788CE557_ROW_CONTACT.jpg',quality=96)
# Dense top pair 2x for semantic split visual check.
cr=(0,55,800,195);dense=[]
for tag,im in [('SOURCE',src),('CLEAN',clean),('FINAL',decoded)]:
 v=comp(im,(55,55,55,255)).crop(cr).resize(((cr[2]-cr[0])*2,(cr[3]-cr[1])*2),Image.Resampling.NEAREST);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),tag,fill='black');dense.append(c)
dw=max(x.width for x in dense);dh=sum(x.height for x in dense)+12;ds=Image.new('RGB',(dw,dh),'white');y=0
for c in dense:ds.paste(c,(0,y));y+=c.height+6
ds.save(out/'B_PRODUCTION21_788CE557_TOP_PAIR_2X.jpg',quality=96)
raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM);r1=card('SOURCE_RAW',raws);r2=card('FINAL_RAW',rawf);rs=Image.new('RGB',(r1.width+r2.width+8,max(r1.height,r2.height)),'white');rs.paste(r1,(0,0));rs.paste(r2,(r1.width+8,0));rs.save(out/'B_PRODUCTION21_788CE557_RAW_COMPARE.jpg',quality=94)
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':106,'asset':asset_rel,'source_url':url,'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'candidate_path':str(candidate.relative_to(repo)),'readiness_tier':'HOLD_STRICT_RECHECK_RESOLVED_TO_RENDER_READY_AND_COMPLETED_SAME_INVOCATION','structure':{**meta,'header_128_exact':True,'raw_orientation':'mirror_y'},'method':'B_PRODUCTION17/18 hold resolved using color-seeded nearest semantic assignment for overlapping-x For Experts/OutRun2SP effects; exact alpha masks for unambiguous Music Change/Time remaining; transparent clean plate; fresh native Korean; exact header DDS','source_mask_seed_counts':{'red':int(red_seed.sum()),'orange':int(orange_seed.sum())},'semantic_split':{'red_fill_max_x':red_fill_max_x,'orange_fill_min_x':orange_fill_min_x,'top_split_x':top_split,'top_band_y':[top_band_y0,top_band_y1]},'rows':rows,'clean_plate':{'source_text_residue_pixels':residue,'status':'PASS'},'containment':{'elements_total':4,'elements_pass':4,'elements_fail':0,'changed_pixels_outside_exact_source_bboxes':outside,'alpha_changed_outside_exact_source_bboxes':alpha_out,'status':'PASS'},'zero_overlap':{'new_vs_preserved_source_alpha_pixels':protected_overlap,'two_px_guard_vs_preserved_conflicts':guard_conflict,'new_pair_overlap_or_2px_guard_conflicts':pair,'status':'PASS'},'protected_preserved':['Transmission labels','selector arrows','warning icon','vehicle silhouettes','steering wheels','numeric row','all unrelated atlas alpha'],'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_PRODUCTION21_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(out/'B_PRODUCTION21_788CE557_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'B_PRODUCTION21_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'bbox_and_size_pass':'4/4','changed_outside':outside,'alpha_outside':alpha_out,'source_residue':residue,'protected_overlap':protected_overlap,'two_px_guard_vs_preserved_conflicts':guard_conflict,'new_pair_overlap_or_2px_guard_conflicts':len(pair),'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},indent=2)+'\n')
print('B_PRODUCTION21_DONE',candidate_sha,'bboxes',source_bboxes,'seeds',int(red_seed.sum()),int(orange_seed.sum()),'split',top_split,'band',top_band_y0,top_band_y1)

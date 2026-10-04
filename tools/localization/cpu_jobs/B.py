#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')
repo=Path.cwd(); run='20261004-B-RECOVERY09'; out=repo/'localization/graphics/role_B'/run; out.mkdir(parents=True,exist_ok=True)
source=repo/'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds'
candidate=repo/'localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds'
old_report=repo/'localization/graphics/role_B/20261004-B-RECOVERY02/B_RECOVERY02_A064FDFC_REPORT.json'
old_target=repo/'localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_TARGET_TEXT_MASK.png'
old_source_text=repo/'localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_SOURCE_TEXT_MASK.png'
source_sha_expected='6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc'
input_sha_expected='15b5970daf2e85818e99efbe37e980564188ebeaaf48a40592b3e561765dfa3f'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=source_sha_expected: raise RuntimeError(('source sha',sha(source)))
if sha(candidate)!=input_sha_expected: raise RuntimeError(('candidate sha',sha(candidate)))

def load_rgba(p):
 b=Path(p).read_bytes(); assert b[:4]==b'DDS '
 h=struct.unpack_from('<I',b,12)[0];w=struct.unpack_from('<I',b,16)[0];pitch=struct.unpack_from('<I',b,20)[0];mips=struct.unpack_from('<I',b,28)[0];fourcc=b[84:88];bpp=struct.unpack_from('<I',b,88)[0];masks=struct.unpack_from('<IIII',b,92)
 if not(fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and pitch==w*4 and mips==1 and len(b)==128+w*h*4):raise RuntimeError((h,w,pitch,mips,fourcc,bpp,masks,len(b)))
 raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA');return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{'width':w,'height':h,'pitch':pitch,'mips':mips,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}
def write_rgba(template,readable,dest):
 b=Path(template).read_bytes();raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM);payload=b[:128]+raw.tobytes('raw','RGBA');Path(dest).write_bytes(payload);return hashlib.sha256(payload).hexdigest()
def bbox(mask):
 a=np.asarray(mask)>0;ys,xs=np.nonzero(a);return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def count(mask):return int(np.count_nonzero(np.asarray(mask)>0))
def dilate(mask,n=2):
 im=Image.fromarray((mask.astype(np.uint8)*255),'L')
 for _ in range(n):im=im.filter(__import__('PIL').ImageFilter.MaxFilter(3))
 return np.asarray(im)>0

def font(style='Black'):
 pat=f'Noto Sans CJK KR:style={style}'
 try:fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
 except Exception:fp=''
 if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
  subprocess.run(['sudo','apt-get','update','-qq'],check=True);subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True);fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
 return fp
FONT=font('Black')
header,src,meta=load_rgba(source);chead,before,cmeta=load_rgba(candidate)
if header!=chead or meta!=cmeta:raise RuntimeError('source/candidate structure mismatch')
W,H=src.size
rep=json.loads(old_report.read_text(encoding='utf-8')); rows={r['key']:r for r in rep['rows']}
selected={
 'ranking':{'text':'순위','source_bbox':[120,245,455,350],'style':'gold_white_navy','safe':[140,253,435,342],'slant':0.12},
 'stage':{'text':'스테이지','source_bbox':[455,245,690,350],'style':'gold_white_navy','safe':[463,253,682,342],'slant':0.12},
 'rank':{'text':'랭크','source_bbox':[690,245,875,350],'style':'white_navy','safe':[700,253,865,342],'slant':0.04},
 'dumped_white':{'text':'차였어요!','source_bbox':[3169,270,3605,390],'style':'white_shadow','safe':[3180,276,3592,360],'slant':0.10},
}
for k,v in selected.items():
 if list(map(int,rows[k]['original_bbox']))!=v['source_bbox']:raise RuntimeError((k,'bbox drift',rows[k]['original_bbox']))
source_mask_all=np.asarray(Image.open(old_source_text).convert('L'))>0
target_old=np.asarray(Image.open(old_target).convert('L'))>0
# Exact selected source text masks are clipped by their authoritative source bboxes.
sel_source=np.zeros((H,W),bool);sel_regions=np.zeros((H,W),bool)
for v in selected.values():
 x0,y0,x1,y1=v['source_bbox'];sel_regions[y0:y1,x0:x1]=1;sel_source[y0:y1,x0:x1]|=source_mask_all[y0:y1,x0:x1]
# Fail closed if persisted source mask is unexpectedly empty in a target bbox.
for k,v in selected.items():
 x0,y0,x1,y1=v['source_bbox'];
 if not np.any(sel_source[y0:y1,x0:x1]):raise RuntimeError((k,'empty source mask'))
# Scoped exact-source clean plate: source with only selected English effects removed.
clean_src_arr=np.asarray(src).copy();clean_src_arr[sel_source]=0;clean_src=Image.fromarray(clean_src_arr,'RGBA')
# Final starts from coherent pre-C fallback; reset selected regions to the exact-source clean plate.
final_arr=np.asarray(before).copy();clean_arr=np.asarray(clean_src)
for v in selected.values():
 x0,y0,x1,y1=v['source_bbox'];final_arr[y0:y1,x0:x1]=clean_arr[y0:y1,x0:x1]
final=Image.fromarray(final_arr,'RGBA')
# Occupied mask = all existing localized target pixels outside the four selected source boxes. Require 2px separation.
occupied=target_old & ~sel_regions
occ_guard=dilate(occupied,2)
# Also preserve any canonical source alpha foreground outside the selected source-text footprint.
src_alpha=np.asarray(src.getchannel('A'))>1
protected_foreground=src_alpha & ~source_mask_all
protected_guard=dilate(protected_foreground & ~sel_regions,1)

def shear(im,s):
 if not s:return im
 shift=max(0,int(round(s*(im.height-1))));o=Image.new('RGBA',(im.width+shift,im.height),(0,0,0,0))
 for y in range(im.height):o.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(s*(im.height-1-y))),y))
 return o

def render_native(k,cfg):
 x0,y0,x1,y1=cfg['safe'];maxw=x1-x0;maxh=y1-y0;dummy=ImageDraw.Draw(Image.new('L',(8,8)))
 for fs in range(min(110,int(maxh*.92)),22,-1):
  f=ImageFont.truetype(FONT,fs)
  if cfg['style']=='white_shadow':
   sw=max(1,round(fs*.018));tb=dummy.textbbox((0,0),cfg['text'],font=f,stroke_width=sw);tw=tb[2]-tb[0];th=tb[3]-tb[1];pad=8
   g=Image.new('RGBA',(tw+2*pad+8,th+2*pad+8),(0,0,0,0));d=ImageDraw.Draw(g)
   # source family: soft gray drop shadow then solid white italic face.
   pos=(pad-tb[0],pad-tb[1]);d.text((pos[0]+3,pos[1]+5),cfg['text'],font=f,fill=(166,166,166,180),stroke_width=2,stroke_fill=(95,95,95,140));d.text(pos,cfg['text'],font=f,fill=(255,255,255,255),stroke_width=sw,stroke_fill=(238,238,238,255))
  else:
   outer=max(3,round(fs*.075));inner=max(2,round(fs*.040));tb=dummy.textbbox((0,0),cfg['text'],font=f,stroke_width=outer);tw=tb[2]-tb[0];th=tb[3]-tb[1];pad=outer+4
   g=Image.new('RGBA',(tw+2*pad,th+2*pad),(0,0,0,0));d=ImageDraw.Draw(g);pos=(pad-tb[0],pad-tb[1])
   if cfg['style']=='gold_white_navy':
    d.text(pos,cfg['text'],font=f,fill=(248,202,14,255),stroke_width=outer,stroke_fill=(255,255,255,255));d.text(pos,cfg['text'],font=f,fill=(248,202,14,255),stroke_width=inner,stroke_fill=(7,24,85,255))
   elif cfg['style']=='white_navy':
    d.text(pos,cfg['text'],font=f,fill=(255,255,255,255),stroke_width=outer,stroke_fill=(255,255,255,255));d.text(pos,cfg['text'],font=f,fill=(255,255,255,255),stroke_width=inner,stroke_fill=(7,24,85,255))
   else:raise RuntimeError(cfg['style'])
  gb=g.getchannel('A').getbbox();g=shear(g.crop(gb),cfg['slant']);gb=g.getchannel('A').getbbox();g=g.crop(gb)
  if g.width>maxw or g.height>maxh:continue
  # place centered in safe box then search small offsets for 0-overlap + 2px separation.
  cx=x0+(maxw-g.width)//2;cy=y0+(maxh-g.height)//2
  candidates=[(0,0)]
  for q in range(2,34,2):candidates += [(0,-q),(0,q),(-q,0),(q,0),(-q,-q),(q,-q),(-q,q),(q,q)]
  gm=np.asarray(g.getchannel('A'))>0
  for dx,dy in candidates:
   px=max(x0,min(x1-g.width,cx+dx));py=max(y0,min(y1-g.height,cy+dy))
   if np.any(gm & occ_guard[py:py+g.height,px:px+g.width]):continue
   if np.any(gm & protected_guard[py:py+g.height,px:px+g.width]):continue
   layer=Image.new('RGBA',src.size,(0,0,0,0));layer.alpha_composite(g,(px,py));lb=bbox(layer.getchannel('A'))
   sb=cfg['source_bbox'];
   if lb[0]<sb[0] or lb[1]<sb[1] or lb[2]>sb[2] or lb[3]>sb[3]:continue
   if (lb[2]-lb[0])>(sb[2]-sb[0]) or (lb[3]-lb[1])>(sb[3]-sb[1]):continue
   return layer,fs,lb
 raise RuntimeError((k,'NO_FRESH_NATIVE_ZERO_OVERLAP_PLACEMENT'))

new_layers={};new_mask=np.zeros((H,W),bool);rowrep=[]
# render the touching ranking-stage-rank group left-to-right, then dumped_white with existing stage_clear guard.
for k in ['ranking','stage','rank','dumped_white']:
 layer,fs,lb=render_native(k,selected[k]);lm=np.asarray(layer.getchannel('A'))>0
 # pairwise strict zero overlap + 2px positive separation among new labels
 guard=dilate(new_mask,2) if np.any(new_mask) else new_mask
 if np.any(lm & guard):raise RuntimeError((k,'new-new overlap/separation fail'))
 new_mask|=lm; occ_guard |= dilate(lm,2); new_layers[k]=layer;final.alpha_composite(layer)
 sb=selected[k]['source_bbox'];rowrep.append({'key':k,'source':rows[k]['source'],'korean':selected[k]['text'],'original_bbox':sb,'localized_bbox':lb,'source_size':[sb[2]-sb[0],sb[3]-sb[1]],'localized_size':[lb[2]-lb[0],lb[3]-lb[1]],'delta_left':lb[0]-sb[0],'delta_right':sb[2]-lb[2],'delta_top':lb[1]-sb[1],'delta_bottom':sb[3]-lb[3],'containment':'PASS','size_ceiling':'PASS','localized_pair_overlap_pixels':0,'protected_overlap_pixels':0,'positive_separation_px':2,'native_font_size':fs,'native_raster_resampled':False,'style':selected[k]['style'],'rework_status':'B_RECOVERY09_FRESH_NATIVE_ZERO_OVERLAP'})
# hard overlap checks against existing target and source/protected foreground.
existing_overlap=int(np.logical_and(new_mask,occupied).sum());protected_overlap=int(np.logical_and(new_mask,protected_foreground & ~sel_regions).sum())
if existing_overlap or protected_overlap:raise RuntimeError(('final overlap',existing_overlap,protected_overlap))
# compare changes against input candidate: only selected source bboxes may change.
fa=np.asarray(final);ba=np.asarray(before);changed=np.any(fa!=ba,axis=2);outside_selected=int(np.logical_and(changed,~sel_regions).sum())
if outside_selected:raise RuntimeError(('candidate collateral',outside_selected))
# compare selected clean plate to source: only selected source text mask may change.
ca=np.asarray(clean_src);sa=np.asarray(src);clean_changed=np.any(ca!=sa,axis=2);clean_out=int(np.logical_and(clean_changed,~sel_source).sum())
if clean_out:raise RuntimeError(('clean outside source text',clean_out))
# Ensure source-script alpha is gone on selected clean plate before Korean is applied.
clean_residue=int(np.logical_and(np.asarray(clean_src.getchannel('A'))>0,sel_source).sum())
if clean_residue:raise RuntimeError(('clean residue',clean_residue))
# exact header encode/decode.
out_sha=write_rgba(source,final,candidate);oh,decoded,om=load_rgba(candidate)
if oh!=header or om!=meta or ImageChops.difference(final,decoded).getbbox() is not None:raise RuntimeError('roundtrip/header fail')
# validate new label masks after roundtrip remain exact and no bbox growth.
for rr in rowrep:
 k=rr['key'];sb=rr['original_bbox'];m=np.asarray(new_layers[k].getchannel('A'))>0;lb=rr['localized_bbox'];
 if not (lb[0]>=sb[0] and lb[1]>=sb[1] and lb[2]<=sb[2] and lb[3]<=sb[3]):raise RuntimeError((k,'bbox'))
# evidence masks
Image.fromarray((sel_source*255).astype(np.uint8),'L').save(out/'A064FDFC_SELECTED_SOURCE_TEXT_MASK.png')
Image.fromarray((sel_regions*255).astype(np.uint8),'L').save(out/'A064FDFC_SELECTED_ALLOWED_REGION_MASK.png')
Image.fromarray((new_mask*255).astype(np.uint8),'L').save(out/'A064FDFC_NEW_TARGET_MASK.png')
clean_src.save(out/'A064FDFC_SELECTED_CLEAN_PLATE.png')
# Full + row contact visual evidence.
def comp(im,bg=(55,55,55,255)):
 z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
def card(label,im):
 v=comp(im);v.thumbnail((900,460),Image.Resampling.LANCZOS);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),label,fill='black');return c
cards=[card('SOURCE',src),card('BEFORE',before),card('FINAL',decoded),card('FINAL_WHITE',Image.alpha_composite(Image.new('RGBA',decoded.size,(255,255,255,255)),decoded))]
ww=cards[0].width+cards[1].width+8;hh=cards[0].height+cards[2].height+8;sheet=Image.new('RGB',(ww,hh),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+8,0));sheet.paste(cards[2],(0,cards[0].height+8));sheet.paste(cards[3],(cards[2].width+8,cards[1].height+8));sheet.save(out/'B_RECOVERY09_A064FDFC_FULL_COMPARE.jpg',quality=94)
contacts=[]
for rr in rowrep:
 sb=rr['original_bbox'];pad=60;cr=(max(0,sb[0]-pad),max(0,sb[1]-pad),min(W,sb[2]+pad),min(H,sb[3]+pad));imgs=[]
 for tag,im in [('SRC',src),('BEFORE',before),('CLEAN',clean_src),('FINAL',decoded)]:
  v=comp(im).crop(cr);scale=min(1,900/max(1,v.width));
  if scale<1:v=v.resize((round(v.width*scale),round(v.height*scale)),Image.Resampling.LANCZOS)
  c=Image.new('RGB',(v.width,v.height+28),'white');c.paste(v,(0,28));ImageDraw.Draw(c).text((4,4),tag,fill='black');imgs.append(c)
 h=max(x.height for x in imgs);w=sum(x.width for x in imgs)+6*(len(imgs)-1);strip=Image.new('RGB',(w,h+26),'white');ImageDraw.Draw(strip).text((4,4),f'{rr["key"]}: {rr["source"]} -> {rr["korean"]}',fill='black');x=0
 for c in imgs:strip.paste(c,(x,26));x+=c.width+6
 contacts.append(strip)
CW=max(x.width for x in contacts);CH=sum(x.height for x in contacts)+6*(len(contacts)-1);cs=Image.new('RGB',(CW,CH),'white');y=0
for c in contacts:cs.paste(c,(0,y));y+=c.height+6
cs.save(out/'B_RECOVERY09_A064FDFC_ROW_CONTACT.jpg',quality=96)
# dense group high zoom: ranking/stage/rank source/before/clean/final.
gcr=(80,205,930,385);gs=[]
for tag,im in [('SOURCE',src),('BEFORE',before),('CLEAN',clean_src),('FINAL',decoded)]:
 v=comp(im).crop(gcr);v=v.resize((v.width*2,v.height*2),Image.Resampling.NEAREST);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),tag,fill='black');gs.append(c)
gw=max(x.width for x in gs);gh=sum(x.height for x in gs)+6*3;g=Image.new('RGB',(gw,gh),'white');y=0
for c in gs:g.paste(c,(0,y));y+=c.height+6
g.save(out/'B_RECOVERY09_A064FDFC_DENSE_GROUP_2X.jpg',quality=96)
# raw orientation compare.
raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM);r1=card('SOURCE_RAW',raws);r2=card('FINAL_RAW',rawf);rs=Image.new('RGB',(r1.width+r2.width+8,max(r1.height,r2.height)),'white');rs.paste(r1,(0,0));rs.paste(r2,(r1.width+8,0));rs.save(out/'B_RECOVERY09_A064FDFC_RAW_COMPARE.jpg',quality=94)
report={'schema_version':1,'role':'B','run':run,'queue_index':60,'asset':'textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds','base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_sha256':source_sha_expected,'input_candidate_sha256':input_sha_expected,'candidate_sha256':out_sha,'structure':{**meta,'header_128_exact':True,'raw_orientation':'mirror_y'},'method':'C_OVERLAP05 producer return: exact-source scoped clean reconstruction for dumped_white + ranking/stage/rank; fresh native Hangul rerender; explicit independent per-row target masks; 2px positive-separation guards; no localized raster scaling; preserve all unrelated candidate pixels byte/pixel-exact','rows':rowrep,'zero_overlap':{'new_vs_existing_localized_pixels':existing_overlap,'new_vs_protected_source_foreground_pixels':protected_overlap,'new_pair_overlap_pixels':0,'positive_separation_px':2,'status':'PASS'},'clean_plate':{'changed_pixels_outside_selected_source_text_mask':clean_out,'source_text_residue_pixels':clean_residue,'status':'PASS'},'collateral':{'changed_pixels_vs_input_candidate_outside_selected_source_bboxes':outside_selected,'status':'PASS'},'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY09_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(out/'B_RECOVERY09_A064FDFC_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_RECOVERY09_DONE',out_sha,'rows',len(rowrep),'overlap',existing_overlap,protected_overlap,'outside',outside_selected)

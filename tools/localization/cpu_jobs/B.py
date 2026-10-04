#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')
repo=Path.cwd(); run='20261004-B-RECOVERY09'; out=repo/'localization/graphics/role_B'/run; out.mkdir(parents=True,exist_ok=True)
rel='localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds'
source=repo/'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds'
candidate=repo/rel
old_report=repo/'localization/graphics/role_B/20261004-B-RECOVERY02/B_RECOVERY02_A064FDFC_REPORT.json'
old_target=repo/'localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_TARGET_TEXT_MASK.png'
source_sha_expected='6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc'
prior_sha_expected='15b5970daf2e85818e99efbe37e980564188ebeaaf48a40592b3e561765dfa3f'
rejected_sha_expected='f78d11bfbef569bebee078aeccd9adbd8e35d89f39e99454174c8c22de7945bb'
prior_commit='d32f0385e7ddd297b993a35ffecdb65298eabde7'

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_bytes(b):
 if b[:4]!=b'DDS ':raise RuntimeError('not dds')
 h=struct.unpack_from('<I',b,12)[0];w=struct.unpack_from('<I',b,16)[0];pitch=struct.unpack_from('<I',b,20)[0];mips=struct.unpack_from('<I',b,28)[0];fourcc=b[84:88];bpp=struct.unpack_from('<I',b,88)[0];masks=struct.unpack_from('<IIII',b,92)
 if not(fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and pitch==w*4 and mips==1 and len(b)==128+w*h*4):raise RuntimeError((h,w,pitch,mips,fourcc,bpp,masks,len(b)))
 raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA');return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{'width':w,'height':h,'pitch':pitch,'mips':mips,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}
def write_rgba(template_bytes,readable,dest):
 raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM);payload=template_bytes[:128]+raw.tobytes('raw','RGBA');Path(dest).write_bytes(payload);return sha_bytes(payload)
def bb(mask):
 a=np.asarray(mask)>0;ys,xs=np.nonzero(a);return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def rectmask(shape,box):
 H,W=shape;m=np.zeros((H,W),bool);x0,y0,x1,y1=map(int,box);m[y0:y1,x0:x1]=1;return m
def dil(a,n=2):
 im=Image.fromarray((a.astype(np.uint8)*255),'L')
 for _ in range(n):im=im.filter(ImageFilter.MaxFilter(3))
 return np.asarray(im)>0

def getfont():
 pat='Noto Sans CJK KR:style=Black'
 try:fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
 except Exception:fp=''
 if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
  subprocess.run(['sudo','apt-get','update','-qq'],check=True);subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True);fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
 return fp
FONT=getfont()
# Recover the coherent pre-overlap B_RECOVERY02 candidate exactly from Git history; do not build on the rejected f78 worker visual.
current_bytes=candidate.read_bytes();current_sha=sha_bytes(current_bytes)
if current_sha!=rejected_sha_expected:raise RuntimeError(('unexpected current candidate',current_sha))
prior_bytes=subprocess.check_output(['git','show',f'{prior_commit}:{rel}'])
if sha_bytes(prior_bytes)!=prior_sha_expected:raise RuntimeError(('prior sha mismatch',sha_bytes(prior_bytes)))
sb,src,meta=load_bytes(source.read_bytes());pb,prior,pmeta=load_bytes(prior_bytes);cb,rejected,cmeta=load_bytes(current_bytes)
if sha(source)!=source_sha_expected or sb!=pb or sb!=cb or meta!=pmeta or meta!=cmeta:raise RuntimeError('source/prior/current structure mismatch')
W,H=src.size;rep=json.loads(old_report.read_text(encoding='utf-8'));rows={r['key']:r for r in rep['rows']};target=np.asarray(Image.open(old_target).convert('L'))>0
cfg={
 'ranking':{'bbox':[120,245,455,350],'text':'순위'},
 'stage':{'bbox':[455,245,690,350],'text':'스테이지'},
 'rank':{'bbox':[690,245,875,350],'text':'랭크'},
 'dumped_white':{'bbox':[3169,270,3605,390],'text':'차였어요!'},
}
for k,c in cfg.items():
 if list(map(int,rows[k]['original_bbox']))!=c['bbox']:raise RuntimeError((k,'source bbox drift'))
# Split the persisted target mask into explicit per-row masks using each row's accepted localized bbox.
row_masks={};selected_old=np.zeros((H,W),bool);selected_regions=np.zeros((H,W),bool)
for k,c in cfg.items():
 r=rows[k];lb=list(map(int,r.get('new_localized_bbox') or r.get('localized_bbox')));rm=target & rectmask((H,W),lb);b=bb(Image.fromarray((rm*255).astype(np.uint8),'L'))
 if b is None:raise RuntimeError((k,'empty persisted target row mask'))
 row_masks[k]=rm;selected_old|=rm;selected_regions|=rectmask((H,W),c['bbox'])
# Existing localized labels excluding the four selected rows. This preserves Stage Clear where its atlas pixels cross dumped_white's rectangle.
occupied=target & ~selected_old
# Build exact-source clean plate for selected rectangles. These are authoritative text-effect bboxes; clear every source alpha pixel inside them to eliminate all English/fringe residue.
src_arr=np.asarray(src).copy();source_alpha=np.asarray(src.getchannel('A'))>0;clean_mask=source_alpha & selected_regions
clean_arr=src_arr.copy();clean_arr[clean_mask]=0;clean_src=Image.fromarray(clean_arr,'RGBA')
# Reconstruct candidate from coherent prior result: exact clean pixels in selected regions, then restore unrelated localized target pixels that geometrically cross those regions.
final_arr=np.asarray(prior).copy();ca=np.asarray(clean_src)
final_arr[selected_regions]=ca[selected_regions]
unselected_inside=occupied & selected_regions
final_arr[unselected_inside]=np.asarray(prior)[unselected_inside]
final=Image.fromarray(final_arr,'RGBA')
# Exact preserved styles for Ranking/Stage/Rank: reapply their already accepted Korean target pixels with no resampling/recoloring.
new_masks={};new_layers={};row_reports=[];guard=dil(occupied,2)
for k in ['ranking','stage','rank']:
 rm=row_masks[k];rgba=np.asarray(prior).copy();rgba[~rm]=0;layer=Image.fromarray(rgba,'RGBA');lb=bb(layer.getchannel('A'));sbx=cfg[k]['bbox']
 if np.any(rm & guard):raise RuntimeError((k,'persisted exact target violates 2px separation'))
 if not(lb[0]>=sbx[0] and lb[1]>=sbx[1] and lb[2]<=sbx[2] and lb[3]<=sbx[3]):raise RuntimeError((k,'bbox fail',lb,sbx))
 final.alpha_composite(layer);new_masks[k]=rm;new_layers[k]=layer;guard|=dil(rm,2)
 row_reports.append({'key':k,'source':rows[k]['source'],'korean':cfg[k]['text'],'original_bbox':sbx,'localized_bbox':lb,'source_size':[sbx[2]-sbx[0],sbx[3]-sbx[1]],'localized_size':[lb[2]-lb[0],lb[3]-lb[1]],'delta_left':lb[0]-sbx[0],'delta_right':sbx[2]-lb[2],'delta_top':lb[1]-sbx[1],'delta_bottom':sbx[3]-lb[3],'containment':'PASS','size_ceiling':'PASS','zero_overlap':'PASS','positive_separation_px':2,'native_raster_resampled':False,'style':'pixel-exact B_RECOVERY02 accepted Korean style','rework_status':'B_RECOVERY09_EXPLICIT_ROW_MASK_REAPPLY_AFTER_FULL_SOURCE_CLEAN'})
# dumped_white: first try exact prior target. If it is too close to Stage Clear/other target pixels, use a fresh native smaller white+gray-shadow render.
def layer_from_mask(rm):
 rgba=np.asarray(prior).copy();rgba[~rm]=0;return Image.fromarray(rgba,'RGBA')
def shear(im,s=.10):
 shift=max(0,int(round(s*(im.height-1))));o=Image.new('RGBA',(im.width+shift,im.height),(0,0,0,0))
 for y in range(im.height):o.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(s*(im.height-1-y))),y))
 return o
k='dumped_white';sbx=cfg[k]['bbox'];rm=row_masks[k];use_exact=not np.any(rm & guard)
if use_exact:
 layer=layer_from_mask(rm);lb=bb(layer.getchannel('A'));fs=None;mode='PIXEL_EXACT_REAPPLY';newrm=rm
else:
 safe=[3182,276,3590,358];x0,y0,x1,y1=safe;dummy=ImageDraw.Draw(Image.new('L',(8,8)));layer=None
 for fs0 in range(82,42,-1):
  f=ImageFont.truetype(FONT,fs0);tb=dummy.textbbox((0,0),cfg[k]['text'],font=f,stroke_width=1);tw=tb[2]-tb[0];th=tb[3]-tb[1];pad=8;g=Image.new('RGBA',(tw+2*pad+10,th+2*pad+10),(0,0,0,0));d=ImageDraw.Draw(g);pos=(pad-tb[0],pad-tb[1]);d.text((pos[0]+3,pos[1]+5),cfg[k]['text'],font=f,fill=(145,145,145,185),stroke_width=2,stroke_fill=(88,88,88,150));d.text(pos,cfg[k]['text'],font=f,fill=(255,255,255,255),stroke_width=1,stroke_fill=(242,242,242,255));gb=g.getchannel('A').getbbox();g=shear(g.crop(gb));gb=g.getchannel('A').getbbox();g=g.crop(gb)
  if g.width>x1-x0 or g.height>y1-y0:continue
  cx=x0+(x1-x0-g.width)//2;cy=y0+(y1-y0-g.height)//2;gm=np.asarray(g.getchannel('A'))>0
  placed=False
  for dy in [0,-2,-4,2,4,-6,6]:
   py=max(y0,min(y1-g.height,cy+dy));px=cx
   if np.any(gm & guard[py:py+g.height,px:px+g.width]):continue
   ll=Image.new('RGBA',src.size,(0,0,0,0));ll.alpha_composite(g,(px,py));lb=bb(ll.getchannel('A'))
   if lb[0]>=sbx[0] and lb[1]>=sbx[1] and lb[2]<=sbx[2] and lb[3]<=sbx[3]:layer=ll;newrm=np.asarray(ll.getchannel('A'))>0;fs=fs0;placed=True;break
  if placed:break
 if layer is None:raise RuntimeError((k,'NO_NATIVE_ZERO_OVERLAP_PLACEMENT_AFTER_EXPLICIT_GROUP_CLEAN'))
 mode='FRESH_NATIVE_WHITE_SHADOW'
final.alpha_composite(layer);new_masks[k]=newrm;new_layers[k]=layer;guard|=dil(newrm,2)
lb=bb(layer.getchannel('A'))
row_reports.append({'key':k,'source':rows[k]['source'],'korean':cfg[k]['text'],'original_bbox':sbx,'localized_bbox':lb,'source_size':[sbx[2]-sbx[0],sbx[3]-sbx[1]],'localized_size':[lb[2]-lb[0],lb[3]-lb[1]],'delta_left':lb[0]-sbx[0],'delta_right':sbx[2]-lb[2],'delta_top':lb[1]-sbx[1],'delta_bottom':sbx[3]-lb[3],'containment':'PASS','size_ceiling':'PASS','zero_overlap':'PASS','positive_separation_px':2,'native_font_size':fs,'native_raster_resampled':False,'style':'source white italic face + gray shadow family','rework_status':'B_RECOVERY09_'+mode})
# Machine gates.
new_union=np.zeros((H,W),bool)
for m in new_masks.values():new_union|=m
# pairwise 0 exact and positive separation >0.
keys=list(new_masks);pair=[];pair_guard=[]
for i in range(len(keys)):
 for j in range(i+1,len(keys)):
  ov=int(np.logical_and(new_masks[keys[i]],new_masks[keys[j]]).sum());near=int(np.logical_and(dil(new_masks[keys[i]],2),new_masks[keys[j]]).sum())
  if ov or near:pair_guard.append([keys[i],keys[j],ov,near])
if pair_guard:raise RuntimeError(('new pair spacing',pair_guard))
existing_overlap=int(np.logical_and(new_union,occupied).sum());near_existing=int(np.logical_and(dil(new_union,2),occupied).sum())
if existing_overlap or near_existing:raise RuntimeError(('new-existing overlap/spacing',existing_overlap,near_existing))
# Source residue: after resetting selected rectangles, no canonical source-alpha pixel may survive there unless it belongs to an explicitly preserved unrelated localized target crossing the rectangle.
fa=np.asarray(final);final_alpha=fa[:,:,3]>0;residue=int(np.logical_and(clean_mask & ~unselected_inside, final_alpha & ~new_union).sum())
if residue:raise RuntimeError(('source residue',residue))
# Outside selected rectangles must remain exactly prior candidate, proving no collateral.
pa=np.asarray(prior);changed=np.any(fa!=pa,axis=2);outside=int(np.logical_and(changed,~selected_regions).sum())
if outside:raise RuntimeError(('collateral outside selected',outside))
# Clean plate changes only source alpha in selected rectangles.
cla=np.asarray(clean_src);sa=np.asarray(src);clean_changed=np.any(cla!=sa,axis=2);clean_out=int(np.logical_and(clean_changed,~clean_mask).sum());clean_residue=int(np.logical_and((cla[:,:,3]>0),clean_mask).sum())
if clean_out or clean_residue:raise RuntimeError(('clean gate',clean_out,clean_residue))
# DDS exact roundtrip.
out_sha=write_rgba(source.read_bytes(),final,candidate);oh,decoded,om=load_bytes(candidate.read_bytes())
if oh!=sb or om!=meta or ImageChops.difference(final,decoded).getbbox() is not None:raise RuntimeError('roundtrip/header fail')
# Evidence masks/images.
Image.fromarray((clean_mask*255).astype(np.uint8),'L').save(out/'A064FDFC_SELECTED_SOURCE_TEXT_MASK.png');Image.fromarray((selected_regions*255).astype(np.uint8),'L').save(out/'A064FDFC_SELECTED_ALLOWED_REGION_MASK.png');Image.fromarray((new_union*255).astype(np.uint8),'L').save(out/'A064FDFC_NEW_TARGET_MASK.png');Image.fromarray((occupied*255).astype(np.uint8),'L').save(out/'A064FDFC_EXISTING_TARGET_MASK.png');clean_src.save(out/'A064FDFC_SELECTED_CLEAN_PLATE.png')
def comp(im,bg=(55,55,55,255)):
 z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
def card(label,im,maxw=920,maxh=480):
 v=comp(im);v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),label,fill='black');return c
cards=[card('SOURCE',src),card('PRIOR_COHERENT',prior),card('REJECTED_F78',rejected),card('FINAL',decoded)];ww=cards[0].width+cards[1].width+8;hh=cards[0].height+cards[2].height+8;s=Image.new('RGB',(ww,hh),'white');s.paste(cards[0],(0,0));s.paste(cards[1],(cards[0].width+8,0));s.paste(cards[2],(0,cards[0].height+8));s.paste(cards[3],(cards[2].width+8,cards[1].height+8));s.save(out/'B_RECOVERY09_A064FDFC_FULL_COMPARE.jpg',quality=94)
contacts=[]
for rr in row_reports:
 box=rr['original_bbox'];pad=70;cr=(max(0,box[0]-pad),max(0,box[1]-pad),min(W,box[2]+pad),min(H,box[3]+pad));ims=[]
 for tag,im in [('SRC',src),('PRIOR',prior),('CLEAN',clean_src),('FINAL',decoded)]:
  v=comp(im).crop(cr);scale=min(1.0,800/max(1,v.width));
  if scale<1:v=v.resize((round(v.width*scale),round(v.height*scale)),Image.Resampling.LANCZOS)
  c=Image.new('RGB',(v.width,v.height+26),'white');c.paste(v,(0,26));ImageDraw.Draw(c).text((4,4),tag,fill='black');ims.append(c)
 h=max(x.height for x in ims);w=sum(x.width for x in ims)+6*3;strip=Image.new('RGB',(w,h+24),'white');ImageDraw.Draw(strip).text((4,4),f'{rr["key"]}: {rr["source"]} -> {rr["korean"]}',fill='black');x=0
 for c in ims:strip.paste(c,(x,24));x+=c.width+6
 contacts.append(strip)
CW=max(x.width for x in contacts);CH=sum(x.height for x in contacts)+6*(len(contacts)-1);cs=Image.new('RGB',(CW,CH),'white');y=0
for c in contacts:cs.paste(c,(0,y));y+=c.height+6
cs.save(out/'B_RECOVERY09_A064FDFC_ROW_CONTACT.jpg',quality=96)
# dense 2x group + dumped overlap neighborhood.
for name,cr in [('DENSE_GROUP',(80,205,930,385)),('DUMPED_STAGECLEAR',(3070,230,4050,500))]:
 panels=[]
 for tag,im in [('SOURCE',src),('PRIOR',prior),('CLEAN',clean_src),('FINAL',decoded)]:
  v=comp(im).crop(cr);v=v.resize((v.width*2,v.height*2),Image.Resampling.NEAREST);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),tag,fill='black');panels.append(c)
 pw=max(x.width for x in panels);ph=sum(x.height for x in panels)+6*3;pp=Image.new('RGB',(pw,ph),'white');y=0
 for c in panels:pp.paste(c,(0,y));y+=c.height+6
 pp.save(out/f'B_RECOVERY09_A064FDFC_{name}_2X.jpg',quality=96)
r1=card('SOURCE_RAW',src.transpose(Image.Transpose.FLIP_TOP_BOTTOM));r2=card('FINAL_RAW',decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM));rs=Image.new('RGB',(r1.width+r2.width+8,max(r1.height,r2.height)),'white');rs.paste(r1,(0,0));rs.paste(r2,(r1.width+8,0));rs.save(out/'B_RECOVERY09_A064FDFC_RAW_COMPARE.jpg',quality=94)
report={'schema_version':2,'role':'B','run':run,'queue_index':60,'asset':rel.replace('localization/graphics/hd_candidates/',''),'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_sha256':source_sha_expected,'coherent_prior_candidate_sha256':prior_sha_expected,'rejected_intermediate_candidate_sha256':rejected_sha_expected,'candidate_sha256':out_sha,'structure':{**meta,'header_128_exact':True,'raw_orientation':'mirror_y'},'method':'C_OVERLAP05 producer return: full exact-source alpha cleanup inside four authoritative source text bboxes; restore unrelated crossing localized target pixels; reapply Ranking/Stage/Rank pixel-exact via explicit per-row masks without resampling; dumped_white exact reapply if safely separated else fresh native smaller render; hard 0px overlap + 2px spacing; no collateral outside four source bboxes','rows':row_reports,'zero_overlap':{'new_vs_existing_localized_pixels':existing_overlap,'new_vs_existing_with_2px_guard':near_existing,'new_pair_overlap_or_guard_conflicts':pair_guard,'positive_separation_px':2,'status':'PASS'},'clean_plate':{'changed_pixels_outside_selected_source_alpha_mask':clean_out,'source_alpha_residue_pixels':clean_residue,'status':'PASS'},'source_residue_gate':{'unexplained_source_alpha_pixels_in_selected_regions_after_final':residue,'status':'PASS'},'collateral':{'changed_pixels_vs_coherent_prior_outside_selected_source_bboxes':outside,'status':'PASS'},'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY09_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(out/'B_RECOVERY09_A064FDFC_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_RECOVERY09_FIXED',out_sha,'dumped_mode',mode,'overlap',existing_overlap,near_existing,'residue',residue,'outside',outside)

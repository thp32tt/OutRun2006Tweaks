#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter,ImageOps

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')
repo=Path.cwd();run='20261004-B-PRODUCTION18';out=repo/'localization/graphics/role_B'/run;out.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds'
source_url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds'
source_sha_expected='4e486f35ca8982266f7f52e4d45aca20a12a2a4fe2a62fee9083db72c7454f9b'
source=Path('/tmp/788CE557_HD.dds');urllib.request.urlretrieve(source_url,source)
candidate=repo/'localization/graphics/hd_candidates'/asset_rel;candidate.parent.mkdir(parents=True,exist_ok=True)
# Readable-orientation cells confirmed from B_PRODUCTION17 exact-HD diagnostic.
spec=[
 ('for_experts','For Experts','상급자용',(0,68,376,170),'red_white_navy',0.15),
 ('outrun2sp','OutRun2SP','아웃런2 SP',(372,68,750,170),'orange_white_navy',0.14),
 ('music_change','Music Change','음악 변경',(780,88,1115,174),'white_shadow',0.12),
 ('time_remaining','Time remaining :','남은 시간:',(940,174,1570,276),'white_navy',0.12),
]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=source_sha_expected:raise RuntimeError(('source_sha',sha(source),source_sha_expected))

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
def count(m):return int(np.count_nonzero(m))
def dil(m,n=2):
 if n<=0:return m
 im=Image.fromarray((m.astype(np.uint8)*255),'L')
 for _ in range(n):im=im.filter(ImageFilter.MaxFilter(3))
 return np.asarray(im)>0

def shear(im,s):
 shift=max(0,int(round(s*(im.height-1))));o=Image.new('RGBA',(im.width+shift,im.height),(0,0,0,0))
 for y in range(im.height):o.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(s*(im.height-1-y))),y))
 return o

header,src,meta=load_dds(source);sa=np.asarray(src,dtype=np.uint8);H,W=sa.shape[:2];source_alpha=sa[:,:,3]>0
source_masks={};source_bboxes={};source_text=np.zeros((H,W),bool)
for key,en,ko,cell,style,slant in spec:
 x0,y0,x1,y1=cell;sub=source_alpha[y0:y1,x0:x1]
 bb=bbox_arr(sub)
 if bb is None:raise RuntimeError((key,'empty cell'))
 bb=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
 # exact target effect must not touch manual isolation cell edge.
 margins=[bb[0]-x0,bb[1]-y0,x1-bb[2],y1-bb[3]]
 if min(margins)<=0:raise RuntimeError((key,'source effect touches isolation cell',cell,bb,margins))
 m=np.zeros((H,W),bool);m[y0:y1,x0:x1]=sub
 source_masks[key]=m;source_bboxes[key]=bb;source_text|=m
# Explicit protected art/text = all source alpha outside target masks. 2px guard for zero-overlap placement.
protected_source=source_alpha & ~source_text;protected_guard=dil(protected_source,2)
# clean plate is transparent source with exact target effect pixels removed only.
clean_arr=sa.copy();clean_arr[source_text]=0;clean=Image.fromarray(clean_arr,'RGBA')
if count((clean_arr[:,:,3]>0)&source_text):raise RuntimeError('source alpha residue in clean target mask')

# Hard allowed regions are the exact source effect bboxes, not cells.
allowed=np.zeros((H,W),bool)
for bb in source_bboxes.values():x0,y0,x1,y1=bb;allowed[y0:y1,x0:x1]=1
protected_rect=~allowed

def render(key,text,bb,style,slant,occupied_guard):
 sx0,sy0,sx1,sy1=bb;SW,SH=sx1-sx0,sy1-sy0;dummy=ImageDraw.Draw(Image.new('L',(8,8)))
 # leave positive internal margin where possible; exact source bbox still remains the hard ceiling.
 safe=[sx0+2,sy0+2,sx1-2,sy1-2];MW=safe[2]-safe[0];MH=safe[3]-safe[1]
 for fs in range(min(150,int(MH*.94)),9,-1):
  f=ImageFont.truetype(FONT,fs)
  outer=max(2,round(fs*.065));inner=max(1,round(fs*.032));shadow=max(1,round(fs*.025));tb=dummy.textbbox((0,0),text,font=f,stroke_width=outer);tw=tb[2]-tb[0];th=tb[3]-tb[1];pad=outer+shadow+5
  g=Image.new('RGBA',(tw+2*pad+8,th+2*pad+8),(0,0,0,0));d=ImageDraw.Draw(g);pos=(pad-tb[0],pad-tb[1])
  if style=='red_white_navy':
   # white outer keyline -> navy separator -> red source-family face.
   d.text(pos,text,font=f,fill=(220,58,60,255),stroke_width=outer,stroke_fill=(250,250,250,255));d.text(pos,text,font=f,fill=(218,55,58,255),stroke_width=inner,stroke_fill=(6,22,78,255))
  elif style=='orange_white_navy':
   d.text(pos,text,font=f,fill=(247,146,15,255),stroke_width=outer,stroke_fill=(250,250,250,255));d.text(pos,text,font=f,fill=(247,146,15,255),stroke_width=inner,stroke_fill=(6,22,78,255))
  elif style=='white_shadow':
   d.text((pos[0]+shadow,pos[1]+shadow),text,font=f,fill=(40,40,40,190),stroke_width=max(1,inner),stroke_fill=(20,20,20,160));d.text(pos,text,font=f,fill=(252,252,252,255),stroke_width=max(1,inner),stroke_fill=(245,245,245,255))
  elif style=='white_navy':
   d.text((pos[0]+shadow,pos[1]+shadow),text,font=f,fill=(8,20,60,180),stroke_width=outer,stroke_fill=(8,20,60,180));d.text(pos,text,font=f,fill=(252,252,252,255),stroke_width=outer,stroke_fill=(5,18,73,255))
  else:raise RuntimeError(style)
  gb=g.getchannel('A').getbbox();g=shear(g.crop(gb),slant);gb=g.getchannel('A').getbbox();g=g.crop(gb)
  if g.width>MW or g.height>MH:continue
  gm=np.asarray(g.getchannel('A'))>0;cx=safe[0]+(MW-g.width)//2;cy=safe[1]+(MH-g.height)//2
  for q in [0,2,-2,4,-4,6,-6,8,-8]:
   px=max(safe[0],min(safe[2]-g.width,cx+q));py=cy
   if np.any(gm & protected_guard[py:py+g.height,px:px+g.width]):continue
   if np.any(gm & occupied_guard[py:py+g.height,px:px+g.width]):continue
   layer=Image.new('RGBA',src.size,(0,0,0,0));layer.alpha_composite(g,(px,py));la=np.asarray(layer.getchannel('A'))>0;lb=bbox_arr(la)
   if lb[0]<sx0 or lb[1]<sy0 or lb[2]>sx1 or lb[3]>sy1:continue
   if (lb[2]-lb[0])>SW or (lb[3]-lb[1])>SH:continue
   return layer,fs,outer,inner,lb
 raise RuntimeError((key,'NO_ZERO_OVERLAP_NATIVE_FIT',bb))

final=clean.copy();layers={};occupied=np.zeros((H,W),bool);rows=[]
for key,en,ko,cell,style,slant in spec:
 layer,fs,outer,inner,lb=render(key,ko,source_bboxes[key],style,slant,dil(occupied,2) if np.any(occupied) else occupied);lm=np.asarray(layer.getchannel('A'))>0
 if np.any(lm & protected_source):raise RuntimeError((key,'protected source overlap'))
 if np.any(lm & occupied):raise RuntimeError((key,'new-new overlap'))
 occupied|=lm;layers[key]=layer;final.alpha_composite(layer);sb=source_bboxes[key]
 rows.append({'key':key,'source':en,'korean':ko,'source_cell':list(cell),'original_bbox':sb,'localized_bbox':lb,'source_size':[sb[2]-sb[0],sb[3]-sb[1]],'localized_size':[lb[2]-lb[0],lb[3]-lb[1]],'delta_left':lb[0]-sb[0],'delta_right':sb[2]-lb[2],'delta_top':lb[1]-sb[1],'delta_bottom':sb[3]-lb[3],'containment':'PASS','size_ceiling':'PASS','native_font_size':fs,'outer_stroke':outer,'inner_stroke':inner,'slant':slant,'style':style,'native_raster_resampled':False,'rework_status':'NEW_CANDIDATE'})
# Static gates before encode.
fa=np.asarray(final,dtype=np.uint8);changed=np.any(fa!=sa,axis=2);outside=int(np.logical_and(changed,~allowed).sum());alpha_diff=fa[:,:,3]!=sa[:,:,3];alpha_out=int(np.logical_and(alpha_diff,~allowed).sum());protchg=int(np.logical_and(changed,protected_rect).sum())
new_overlap_protected=int(np.logical_and(occupied,protected_source).sum())
# source-script residue is clean-alpha at target mask; must be zero.
residue=int(np.logical_and(np.asarray(clean.getchannel('A'))>0,source_text).sum())
if any((outside,alpha_out,protchg,new_overlap_protected,residue)):raise RuntimeError(('static',outside,alpha_out,protchg,new_overlap_protected,residue))
# Pairwise new-label overlap and positive 2px guard.
pair=[];ks=list(layers)
for i in range(len(ks)):
 for j in range(i+1,len(ks)):
  a=np.asarray(layers[ks[i]].getchannel('A'))>0;b=np.asarray(layers[ks[j]].getchannel('A'))>0
  ov=int(np.logical_and(a,b).sum());guard=int(np.logical_and(dil(a,2),b).sum())
  if ov or guard:pair.append({'a':ks[i],'b':ks[j],'overlap_pixels':ov,'two_px_guard_conflicts':guard})
if pair:raise RuntimeError(('pair overlap',pair))
# Exact-header DDS encode / roundtrip.
candidate_sha=write_dds(source,final,candidate);ch,decoded,cm=load_dds(candidate)
if ch!=header or cm!=meta or ImageChops.difference(decoded,final).getbbox() is not None:raise RuntimeError('roundtrip/header mismatch')
# Evidence masks and validators.
Image.fromarray((source_text*255).astype(np.uint8),'L').save(out/'788CE557_SOURCE_TEXT_MASK.png');Image.fromarray((allowed*255).astype(np.uint8),'L').save(out/'788CE557_ALLOWED_TEXT_REGION_MASK.png');Image.fromarray((protected_rect*255).astype(np.uint8),'L').save(out/'788CE557_PROTECTED_MASK.png');Image.fromarray((occupied*255).astype(np.uint8),'L').save(out/'788CE557_TARGET_TEXT_MASK.png');clean.save(out/'788CE557_CLEAN_PLATE.png')
work=Path('/tmp/b18');work.mkdir(exist_ok=True);sp=work/'source.png';cp=work/'clean.png';fp=work/'final.png';src.save(sp);clean.save(cp);decoded.save(fp)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(sp),str(cp),str(out/'788CE557_SOURCE_TEXT_MASK.png'),'--report',str(out/'B_PRODUCTION18_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(sp),str(fp),str(out/'788CE557_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(out/'788CE557_PROTECTED_MASK.png'),'--report',str(out/'B_PRODUCTION18_FINAL_MASK_VALIDATION.json')],check=True)
# Human visual evidence.
def comp(im,bg):z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
def card(label,im,bg=(55,55,55,255)):
 v=comp(im,bg);v.thumbnail((900,480),Image.Resampling.LANCZOS);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),label,fill='black');return c
cards=[card('SOURCE',src),card('CLEAN',clean),card('FINAL',decoded),card('FINAL_WHITE',decoded,(255,255,255,255))];ww=cards[0].width+cards[1].width+8;hh=cards[0].height+cards[2].height+8;sheet=Image.new('RGB',(ww,hh),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+8,0));sheet.paste(cards[2],(0,cards[0].height+8));sheet.paste(cards[3],(cards[2].width+8,cards[1].height+8));sheet.save(out/'B_PRODUCTION18_788CE557_COMPARE.jpg',quality=95)
contacts=[]
for rr in rows:
 sb=rr['original_bbox'];pad=30;cr=(max(0,sb[0]-pad),max(0,sb[1]-pad),min(W,sb[2]+pad),min(H,sb[3]+pad));ims=[]
 for tag,im in [('SRC',src),('CLEAN',clean),('FINAL',decoded)]:
  v=comp(im,(55,55,55,255)).crop(cr);scale=min(1,800/max(1,v.width));
  if scale<1:v=v.resize((round(v.width*scale),round(v.height*scale)),Image.Resampling.LANCZOS)
  c=Image.new('RGB',(v.width,v.height+26),'white');c.paste(v,(0,26));ImageDraw.Draw(c).text((4,4),tag,fill='black');ims.append(c)
 h=max(x.height for x in ims);w=sum(x.width for x in ims)+6*(len(ims)-1);c=Image.new('RGB',(w,h+24),'white');ImageDraw.Draw(c).text((4,4),f'{rr["source"]} -> {rr["korean"]}',fill='black');x=0
 for im in ims:c.paste(im,(x,24));x+=im.width+6
 contacts.append(c)
CW=max(x.width for x in contacts);CH=sum(x.height for x in contacts)+6*(len(contacts)-1);cs=Image.new('RGB',(CW,CH),'white');y=0
for c in contacts:cs.paste(c,(0,y));y+=c.height+6
cs.save(out/'B_PRODUCTION18_788CE557_ROW_CONTACT.jpg',quality=96)
raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM);r1=card('SOURCE_RAW',raws);r2=card('FINAL_RAW',rawf);rs=Image.new('RGB',(r1.width+r2.width+8,max(r1.height,r2.height)),'white');rs.paste(r1,(0,0));rs.paste(r2,(r1.width+8,0));rs.save(out/'B_PRODUCTION18_788CE557_RAW_COMPARE.jpg',quality=94)
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':106,'asset':asset_rel,'source_url':source_url,'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'candidate_path':str(candidate.relative_to(repo)),'readiness_tier':'ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION','structure':{**meta,'header_128_exact':True,'raw_orientation':'mirror_y'},'method':'exact HD source alpha-isolated target effects -> transparent clean plate -> native Hangul -> exact header DDS; Transmission labels/icons/numbers and all non-target alpha protected','rows':rows,'clean_plate':{'changed_pixels_outside_source_text_mask':0,'source_text_residue_pixels':residue,'status':'PASS'},'containment':{'elements_total':4,'elements_pass':4,'elements_fail':0,'changed_pixels_outside_exact_source_bboxes':outside,'alpha_changed_outside_exact_source_bboxes':alpha_out,'protected_changes':protchg,'status':'PASS'},'zero_overlap':{'new_vs_preserved_source_alpha_pixels':new_overlap_protected,'new_pair_overlap_or_2px_guard_conflicts':pair,'status':'PASS'},'preserved_original':['Transmission labels','selector arrows','warning icon','vehicle silhouettes','steering wheels','numeric row'],'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_PRODUCTION18_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(out/'B_PRODUCTION18_788CE557_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'B_PRODUCTION18_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'bbox_and_size_pass':'4/4','changed_outside':outside,'alpha_outside':alpha_out,'protected_changes':protchg,'source_residue':residue,'overlap_preserved':new_overlap_protected,'pair_overlap_or_2px_guard_conflicts':len(pair),'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},indent=2)+'\n')
print('B_PRODUCTION18_DONE',candidate_sha,'4/4','outside',outside,'protected',protchg,'residue',residue,'overlap',new_overlap_protected)

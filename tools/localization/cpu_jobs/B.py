#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter
if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':raise SystemExit('B hosted worker only')
repo=Path.cwd();run='20261004-B-PRODUCTION20';out=repo/'localization/graphics/role_B'/run;out.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_sumo_fe_cvt_Exst/5B65E08C_512x256.dds';url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_sumo_fe_cvt_Exst/5B65E08C_512x256.dds';source_sha_expected='5ca485fc5bcad59ba4d23225a951660a5009c436cac23b590946cb1a64e4634e'
source=Path('/tmp/5B65E08C_HD.dds');urllib.request.urlretrieve(url,source);candidate=repo/'localization/graphics/hd_candidates'/asset_rel;candidate.parent.mkdir(parents=True,exist_ok=True)
# B_PRODUCTION19 exact-HD/historical diff established the semantic SELECT LICENSE target region.
semantic_region=(590,565,1493,659);text='라이선스 선택'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=source_sha_expected:raise RuntimeError(('source sha',sha(source)))
def resolve_font():
 pat='Noto Sans CJK KR:style=Black'
 try:fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
 except Exception:fp=''
 if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
  subprocess.run(['sudo','apt-get','update','-qq'],check=True);subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True);fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
 if not fp or not Path(fp).exists():raise RuntimeError('Noto CJK unavailable')
 return fp
FONT=resolve_font()
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
 im=Image.fromarray((m.astype(np.uint8)*255),'L')
 for _ in range(n):im=im.filter(ImageFilter.MaxFilter(3))
 return np.asarray(im)>0
header,src,meta=load_dds(source);sa=np.asarray(src,dtype=np.uint8);H,W=sa.shape[:2];alpha=sa[:,:,3]>0
x0,y0,x1,y1=semantic_region;source_text=np.zeros((H,W),bool);source_text[y0:y1,x0:x1]=alpha[y0:y1,x0:x1]
sb=bbox_arr(source_text)
if sb is None:raise RuntimeError('empty target source mask')
# Historical diff region is semantic evidence; actual exact source effect bbox must remain contained within it.
if sb[0]<x0 or sb[1]<y0 or sb[2]>x1 or sb[3]>y1:raise RuntimeError(('source bbox escaped semantic region',sb,semantic_region))
# Ensure all significant alpha in the semantic region belongs to one plain-text band (no unrelated icon/art island).
region_alpha=int(np.count_nonzero(alpha[y0:y1,x0:x1]));bbox_alpha=int(np.count_nonzero(source_text[sb[1]:sb[3],sb[0]:sb[2]]))
if region_alpha!=bbox_alpha:raise RuntimeError(('unexpected target alpha accounting',region_alpha,bbox_alpha))
# Source palette should be plain near-white; fail closed rather than inventing a new style.
p=sa[source_text];opaque=p[p[:,3]>=160];median_rgb=[int(v) for v in np.median(opaque[:,:3],axis=0)] if len(opaque) else [255,255,255]
if min(median_rgb)<210:raise RuntimeError(('source not plain-white family',median_rgb))
protected_source=alpha & ~source_text;protected_guard=dil(protected_source,2)
# Transparent clean plate: remove exact source glyph/effect pixels only.
clean_arr=sa.copy();clean_arr[source_text]=0;clean=Image.fromarray(clean_arr,'RGBA')
residue=int(np.logical_and(np.asarray(clean.getchannel('A'))>0,source_text).sum())
if residue:raise RuntimeError(('clean residue',residue))
# Render native Hangul, source-family heavy plain white, no invented outline/glow/slant.
dummy=ImageDraw.Draw(Image.new('L',(8,8)));SW,SH=sb[2]-sb[0],sb[3]-sb[1];layer=None;render_meta=None
for fs in range(min(150,int(SH*.98)),10,-1):
 f=ImageFont.truetype(FONT,fs);sw=max(4,round(fs*.06));tb=dummy.textbbox((0,0),text,font=f,stroke_width=sw);tw=tb[2]-tb[0];th=tb[3]-tb[1]
 if tw>SW-4 or th>SH-4:continue
 g=Image.new('RGBA',(tw+4,th+4),(0,0,0,0));ImageDraw.Draw(g).text((2-tb[0],2-tb[1]),text,font=f,fill=tuple(median_rgb)+(255,),stroke_width=sw,stroke_fill=tuple(median_rgb)+(255,));gb=g.getchannel('A').getbbox();g=g.crop(gb);gm=np.asarray(g.getchannel('A'))>0
 if g.width>SW-4 or g.height>SH-4:continue
 cx=sb[0]+(SW-g.width)//2;cy=sb[1]+(SH-g.height)//2
 for dy in [0,-2,2,-4,4]:
  px=cx;py=max(sb[1]+2,min(sb[3]-g.height-2,cy+dy))
  if np.any(gm & protected_guard[py:py+g.height,px:px+g.width]):continue
  l=Image.new('RGBA',src.size,(0,0,0,0));l.alpha_composite(g,(px,py));lm=np.asarray(l.getchannel('A'))>0;lb=bbox_arr(lm)
  if lb[0]>=sb[0] and lb[1]>=sb[1] and lb[2]<=sb[2] and lb[3]<=sb[3] and (lb[2]-lb[0])<=SW and (lb[3]-lb[1])<=SH:
   layer=l;render_meta=(fs,lb,lm);break
 if layer:break
if layer is None:raise RuntimeError('NO_NATIVE_ZERO_OVERLAP_FIT')
fs,lb,newmask=render_meta
new_protected_overlap=int(np.logical_and(newmask,protected_source).sum())
if new_protected_overlap:raise RuntimeError(('protected overlap',new_protected_overlap))
final=clean.copy();final.alpha_composite(layer);fa=np.asarray(final,dtype=np.uint8)
# Exact source bbox is the only allowed final-edit region.
allowed=np.zeros((H,W),bool);allowed[sb[1]:sb[3],sb[0]:sb[2]]=1;changed=np.any(fa!=sa,axis=2);outside=int(np.logical_and(changed,~allowed).sum());alpha_out=int(np.logical_and(fa[:,:,3]!=sa[:,:,3],~allowed).sum())
if outside or alpha_out:raise RuntimeError(('outside source bbox',outside,alpha_out))
# 2px positive separation from all preserved source alpha.
guard_conflict=int(np.logical_and(dil(newmask,2),protected_source).sum())
if guard_conflict:raise RuntimeError(('2px protected guard conflict',guard_conflict))
# encode / decoded equality.
candidate_sha=write_dds(source,final,candidate);ch,decoded,cm=load_dds(candidate)
if ch!=header or cm!=meta or ImageChops.difference(decoded,final).getbbox() is not None:raise RuntimeError('DDS roundtrip/header mismatch')
# evidence masks.
Image.fromarray((source_text*255).astype(np.uint8),'L').save(out/'5B65E08C_SOURCE_TEXT_MASK.png');Image.fromarray((allowed*255).astype(np.uint8),'L').save(out/'5B65E08C_ALLOWED_TEXT_REGION_MASK.png');Image.fromarray(((~allowed)*255).astype(np.uint8),'L').save(out/'5B65E08C_PROTECTED_MASK.png');Image.fromarray((newmask*255).astype(np.uint8),'L').save(out/'5B65E08C_TARGET_TEXT_MASK.png');clean.save(out/'5B65E08C_CLEAN_PLATE.png')
work=Path('/tmp/b20');work.mkdir(exist_ok=True);sp=work/'source.png';cp=work/'clean.png';fp=work/'final.png';src.save(sp);clean.save(cp);decoded.save(fp)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(sp),str(cp),str(out/'5B65E08C_SOURCE_TEXT_MASK.png'),'--report',str(out/'B_PRODUCTION20_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(sp),str(fp),str(out/'5B65E08C_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(out/'5B65E08C_PROTECTED_MASK.png'),'--report',str(out/'B_PRODUCTION20_FINAL_MASK_VALIDATION.json')],check=True)
# visual evidence.
def comp(im,bg):z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
def card(label,im,bg=(55,55,55,255)):
 v=comp(im,bg);v.thumbnail((900,500),Image.Resampling.LANCZOS);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),label,fill='black');return c
cards=[card('SOURCE',src),card('CLEAN',clean),card('FINAL',decoded),card('FINAL_WHITE',decoded,(255,255,255,255))];ww=cards[0].width+cards[1].width+8;hh=cards[0].height+cards[2].height+8;sheet=Image.new('RGB',(ww,hh),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+8,0));sheet.paste(cards[2],(0,cards[0].height+8));sheet.paste(cards[3],(cards[2].width+8,cards[1].height+8));sheet.save(out/'B_PRODUCTION20_5B65E08C_COMPARE.jpg',quality=95)
pad=50;cr=(max(0,sb[0]-pad),max(0,sb[1]-pad),min(W,sb[2]+pad),min(H,sb[3]+pad));ims=[]
for tag,im in [('SOURCE',src),('CLEAN',clean),('FINAL',decoded)]:
 v=comp(im,(55,55,55,255)).crop(cr);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),tag,fill='black');ims.append(c)
row=Image.new('RGB',(sum(x.width for x in ims)+12,max(x.height for x in ims)+28),'white');ImageDraw.Draw(row).text((5,5),'SELECT LICENSE -> 라이선스 선택',fill='black');xx=0
for c in ims:row.paste(c,(xx,28));xx+=c.width+6
row.save(out/'B_PRODUCTION20_5B65E08C_ROW_CONTACT.jpg',quality=96)
raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM);r1=card('SOURCE_RAW',raws);r2=card('FINAL_RAW',rawf);rs=Image.new('RGB',(r1.width+r2.width+8,max(r1.height,r2.height)),'white');rs.paste(r1,(0,0));rs.paste(r2,(r1.width+8,0));rs.save(out/'B_PRODUCTION20_5B65E08C_RAW_COMPARE.jpg',quality=94)
rowrec={'key':'select_license','source':'SELECT LICENSE','korean':text,'original_bbox':sb,'localized_bbox':lb,'source_size':[SW,SH],'localized_size':[lb[2]-lb[0],lb[3]-lb[1]],'delta_left':lb[0]-sb[0],'delta_right':sb[2]-lb[2],'delta_top':lb[1]-sb[1],'delta_bottom':sb[3]-lb[3],'containment':'PASS','size_ceiling':'PASS','zero_overlap':'PASS','positive_separation_px':2,'native_font':'Noto Sans CJK KR Black','native_font_size':fs,'same_color_weight_stroke_px':sw,'source_median_rgb':median_rgb,'style':'source-faithful heavy plain white; same-white weight stroke only, no outline/shadow/slant invented','native_raster_resampled':False,'rework_status':'NEW_CANDIDATE'}
report={'schema_version':1,'role':'B','run':run,'queue_index':164,'asset':asset_rel,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_url':url,'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'candidate_path':str(candidate.relative_to(repo)),'readiness_tier':'ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION','structure':{**meta,'header_128_exact':True,'raw_orientation':'mirror_y'},'method':'B_PRODUCTION19 semantic region -> exact source alpha glyph mask -> transparent clean plate -> native source-family plain-white Korean render -> exact header DDS','rows':[rowrec],'clean_plate':{'source_text_residue_pixels':residue,'status':'PASS'},'containment':{'elements_total':1,'elements_pass':1,'elements_fail':0,'changed_pixels_outside_exact_source_bbox':outside,'alpha_changed_outside_exact_source_bbox':alpha_out,'status':'PASS'},'zero_overlap':{'new_vs_preserved_source_alpha_pixels':new_protected_overlap,'two_px_guard_conflicts':guard_conflict,'status':'PASS'},'protected_preserved':'all red panel artwork and all non-target atlas pixels','manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_PRODUCTION20_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(out/'B_PRODUCTION20_5B65E08C_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'B_PRODUCTION20_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'bbox_and_size_pass':'1/1','changed_outside':outside,'alpha_outside':alpha_out,'source_residue':residue,'protected_overlap':new_protected_overlap,'two_px_guard_conflicts':guard_conflict,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},indent=2)+'\n')
print('B_PRODUCTION20_DONE',candidate_sha,'source_bbox',sb,'localized_bbox',lb,'font',fs,'median',median_rgb)

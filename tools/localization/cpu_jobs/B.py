#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')

repo=Path.cwd()
run='20261006-B-INGAME164-B169-SLIPSTREAM'
out=repo/'localization/graphics/role_B'/run
out.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'
candidate=repo/'localization/graphics/hd_candidates'/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
old_candidate_sha='448d4cd751461af26731028daad4835ec0a8dfcbdcdd7fb23c194478fe74df21'
source_url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'
source_sha='3c58bf9587d0454e5bb8733bd35c5b2613b11c7fd52c49a428f0fa5fb4cea12d'
source=Path('/tmp/B1696633_HD.dds')
urllib.request.urlretrieve(source_url,source)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=source_sha: raise RuntimeError(('source sha mismatch',sha(source)))
if not candidate.exists() or sha(candidate)!=old_candidate_sha:
    raise RuntimeError(('current candidate drift',candidate.exists(),sha(candidate) if candidate.exists() else None))

def resolve_font():
    pat='Noto Sans CJK KR:style=Black'
    fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
    if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
        subprocess.run(['sudo','apt-get','update','-qq'],check=True)
        subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True)
        fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
    if not fp or not Path(fp).exists(): raise RuntimeError('Noto CJK unavailable')
    return fp
FONT=resolve_font()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b'DDS ': raise RuntimeError('not DDS')
    h=struct.unpack_from('<I',b,12)[0];w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0];mips=struct.unpack_from('<I',b,28)[0]
    pf_flags=struct.unpack_from('<I',b,80)[0];fourcc=b[84:88];bpp=struct.unpack_from('<I',b,88)[0]
    masks=struct.unpack_from('<IIII',b,92)
    if not(w==2048 and h==2048 and pitch==8192 and mips==1 and pf_flags==65 and fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and len(b)==128+w*h*4):
        raise RuntimeError((w,h,pitch,mips,pf_flags,fourcc,bpp,masks,len(b)))
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),dict(width=w,height=h,pitch=pitch,mips=mips,pf_flags=pf_flags,fourcc='00000000',bpp=bpp,masks=[hex(x) for x in masks])

def write_dds(header,readable,dest):
    payload=header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes('raw','RGBA')
    Path(dest).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

def bbox_mask(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def shear(im,s):
    shift=max(0,int(np.ceil(abs(s)*(im.height-1))))+3
    out=im.transform((im.width+shift,im.height),Image.Transform.AFFINE,
        (1.0,-s,s*(im.height-1),0.0,1.0,0.0),resample=Image.Resampling.BICUBIC)
    bb=out.getchannel('A').getbbox()
    return out.crop(bb) if bb else out

header,src,meta=load_dds(source)
ch,base,cmeta=load_dds(candidate)
if ch!=header or cmeta!=meta: raise RuntimeError('candidate/source DDS structure mismatch')

old_clean=Image.open(repo/'localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_CLEAN_PLATE.png').convert('RGBA')
old_protected=np.asarray(Image.open(repo/'localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_PROTECTED_MASK.png').convert('L'))>0
if old_clean.size!=src.size or old_protected.shape!=(2048,2048): raise RuntimeError('old evidence size mismatch')

# User in-game regression IGR-009: only Slipstream is reopened.
source_bbox=[889,1718,1388,1825]
old_localized_bbox=[892,1719,1385,1823]
x0,y0,x1,y1=source_bbox
final=base.copy()
# Restore the already-C-approved native clean plate under the exact source Slipstream effect bbox.
final.paste(old_clean.crop((x0,y0,x1,y1)),(x0,y0))

dummy=ImageDraw.Draw(Image.new('L',(8,8)))
chosen=None
# Source family: strong right italic, white face, navy inner line, cobalt outer line/glow.
for fs in range(104,58,-1):
    font=ImageFont.truetype(FONT,fs)
    outer=max(5,round(fs*0.085))
    inner=max(2,round(fs*0.035))
    glow=max(2,round(fs*0.04))
    tb=dummy.textbbox((0,0),'슬립스트림',font=font,stroke_width=outer)
    pad=outer+glow+10
    w=tb[2]-tb[0]+2*pad; h=tb[3]-tb[1]+2*pad
    glyph=Image.new('RGBA',(w,h),(0,0,0,0))
    pos=(pad-tb[0],pad-tb[1])

    # soft blue halo from the source effect family
    gm=Image.new('L',(w,h),0);gd=ImageDraw.Draw(gm)
    gd.text(pos,'슬립스트림',font=font,fill=255,stroke_width=outer+2,stroke_fill=255)
    halo=Image.new('RGBA',(w,h),(36,87,255,0));halo.putalpha(gm.filter(ImageFilter.GaussianBlur(radius=glow)))
    glyph.alpha_composite(halo)

    d=ImageDraw.Draw(glyph)
    d.text(pos,'슬립스트림',font=font,fill=(246,252,252,255),stroke_width=outer,stroke_fill=(39,78,219,240))
    d.text(pos,'슬립스트림',font=font,fill=(246,252,252,255),stroke_width=inner,stroke_fill=(4,23,105,255))

    glyph=shear(glyph,0.26)
    bb=glyph.getchannel('A').getbbox()
    glyph=glyph.crop(bb)
    if glyph.width>(x1-x0-8) or glyph.height>(y1-y0-8): continue

    # Source-aligned vertical center; horizontal center without artificial glyph tracking.
    px=x0+((x1-x0)-glyph.width)//2
    py=y0+((y1-y0)-glyph.height)//2
    arr=np.asarray(glyph.getchannel('A'))>0
    prot=old_protected[py:py+glyph.height,px:px+glyph.width]
    if np.any(arr & prot): continue
    chosen=(glyph,px,py,fs,outer,inner,glow)
    break
if chosen is None: raise RuntimeError('no protected-safe source-bbox fit for Slipstream')

glyph,px,py,fs,outer,inner,glow=chosen
layer=Image.new('RGBA',src.size,(0,0,0,0));layer.alpha_composite(glyph,(px,py))
render_mask=np.asarray(layer.getchannel('A'))>0
lb=bbox_mask(render_mask)
if lb is None: raise RuntimeError('empty render')
if not(x0<lb[0] and y0<lb[1] and lb[2]<x1 and lb[3]<y1): raise RuntimeError(('no positive margin',lb,source_bbox))
if np.any(render_mask & old_protected): raise RuntimeError('localized render overlaps protected pixels')
final.alpha_composite(layer)

ba=np.asarray(base,dtype=np.uint8)
fa=np.asarray(final,dtype=np.uint8)
changed=np.any(ba!=fa,axis=2)
allowed=np.zeros((2048,2048),bool);allowed[y0:y1,x0:x1]=1
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(ba[:,:,3]!=fa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,old_protected).sum())
if outside or alpha_out or protected_changed:
    raise RuntimeError(('change scope fail',outside,alpha_out,protected_changed))

# All eight non-Slipstream prior localized regions must remain byte exact.
preserved_rows=[
 [110,770,169,804],[1690,769,1752,804],[1092,849,1212,884],[1334,916,1615,968],
 [1669,919,1822,968],[245,1700,647,1838],[1619,1734,1876,1839],[1040,1901,1570,2040]
]
preserved_row_diffs=[]
for bb in preserved_rows:
    ax0,ay0,ax1,ay1=bb
    n=int(np.count_nonzero(np.any(ba[ay0:ay1,ax0:ax1]!=fa[ay0:ay1,ax0:ax1],axis=2)))
    preserved_row_diffs.append(n)
if any(preserved_row_diffs): raise RuntimeError(('other localized row changed',preserved_row_diffs))

new_sha=write_dds(header,final,candidate)
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox() is not None:
    raise RuntimeError('DDS roundtrip/header mismatch')

# Evidence masks/validator.
Image.fromarray((allowed*255).astype(np.uint8),'L').save(out/'B1696633_SLIPSTREAM_EDIT_MASK.png')
Image.fromarray((old_protected*255).astype(np.uint8),'L').save(out/'B1696633_PROTECTED_MASK.png')
Image.fromarray((render_mask*255).astype(np.uint8),'L').save(out/'B1696633_SLIPSTREAM_RENDER_MASK.png')
work=Path('/tmp/b164');work.mkdir(exist_ok=True)
bp=work/'before.png';fp=work/'final.png';base.save(bp);decoded.save(fp)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(bp),str(fp),str(out/'B1696633_SLIPSTREAM_EDIT_MASK.png'),'--protected-mask',str(out/'B1696633_PROTECTED_MASK.png'),'--report',str(out/'B164_FINAL_MASK_VALIDATION.json')],check=True)

def comp(im,bg=(55,55,55,255)):
    z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
def card(label,im,crop=None,scale=1):
    v=comp(im)
    if crop:v=v.crop(crop)
    if scale!=1:v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),label,fill='black')
    return c

crop=(840,1680,1440,1860)
cards=[card('SOURCE',src,crop),card('OLD_CANDIDATE',base,crop),card('CLEAN',old_clean,crop),card('B164_FINAL',decoded,crop)]
W=max(c.width for c in cards);H=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new('RGB',(W,H),'white');yy=0
for c in cards:sheet.paste(c,(0,yy));yy+=c.height+8
sheet.save(out/'B164_SLIPSTREAM_SOURCE_OLD_CLEAN_FINAL.jpg',quality=97)

zoom=[card('SOURCE_2X',src,crop,2),card('OLD_2X',base,crop,2),card('FINAL_2X',decoded,crop,2)]
W=max(c.width for c in zoom);H=sum(c.height for c in zoom)+8*(len(zoom)-1)
zs=Image.new('RGB',(W,H),'white');yy=0
for c in zoom:zs.paste(c,(0,yy));yy+=c.height+8
zs.save(out/'B164_SLIPSTREAM_2X.jpg',quality=97)

raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
r1=card('SOURCE_RAW',raws);r2=card('FINAL_RAW',rawf)
rs=Image.new('RGB',(r1.width+r2.width+8,max(r1.height,r2.height)),'white');rs.paste(r1,(0,0));rs.paste(r2,(r1.width+8,0))
rs.save(out/'B164_RAW_COMPARE.jpg',quality=94)

report={
 'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'queue_index':48,'asset':asset_rel,'source_url':source_url,'source_sha256':source_sha,
 'superseded_candidate_sha256':old_candidate_sha,'candidate_sha256':new_sha,
 'candidate_path':str(candidate.relative_to(repo)),'readiness_tier':'P1_USER_INGAME_FAIL_REWORK_COMPLETED_SAME_INVOCATION',
 'user_ingame_regression':['IGR-009','스크린샷(152).png'],
 'method':'Reopen only Slipstream on prior C104-approved B169 atlas; restore C104-approved native clean plate under exact source effect bbox; rerender native Noto CJK Black with natural advance, 0.26 right shear, white face + navy/cobalt outline/glow; preserve source streak field and all other localized/non-text pixels exactly; exact-header RGBA32 DDS.',
 'structure':{**meta,'header_128_exact':True,'raw_orientation':'mirror_y'},
 'slipstream':{
   'source':'Slipstream','korean':'슬립스트림','original_bbox':source_bbox,'prior_localized_bbox':old_localized_bbox,'localized_bbox':lb,
   'source_size':[x1-x0,y1-y0],'localized_size':[lb[2]-lb[0],lb[3]-lb[1]],
   'delta_left':lb[0]-x0,'delta_right':x1-lb[2],'delta_top':lb[1]-y0,'delta_bottom':y1-lb[3],
   'containment':'PASS','size_ceiling':'PASS','positive_margin':'PASS',
   'native_font':'Noto Sans CJK KR Black','native_font_size':fs,'outer_stroke':outer,'inner_stroke':inner,'glow_radius':glow,
   'slant':0.26,'artificial_tracking_px':0,'native_raster_resampled':False,
   'effect_preservation':'SOURCE_STREAK_FIELD_FROM_PRIOR_VALIDATED_CLEAN_PLATE'
 },
 'scope_qa':{
   'changed_pixels':int(changed.sum()),'changed_outside_exact_source_bbox':outside,'alpha_changed_outside_exact_source_bbox':alpha_out,
   'protected_changed_pixels':protected_changed,'other_8_localized_row_changed_pixels':preserved_row_diffs,
   'localized_to_protected_overlap_pixels':int(np.logical_and(render_mask,old_protected).sum()),'status':'PASS'
 },
 'visual_qa':'PENDING_CONTROLLER_SELF_QA','runtime_validation':'PENDING_NEW_INGAME_RETEST',
 'status':'B164_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'
}
(out/'B164_B1696633_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'B164_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({
 'source_sha256':source_sha,'superseded_candidate_sha256':old_candidate_sha,'candidate_sha256':new_sha,
 'localized_bbox':lb,'original_bbox':source_bbox,'bbox_size_positive_margin':'1/1 PASS',
 'changed_outside':outside,'alpha_outside':alpha_out,'protected_changed':protected_changed,
 'other_8_localized_row_changed_pixels':preserved_row_diffs,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B164_DONE',new_sha,'bbox',lb,'font',fs,'changed',int(changed.sum()))

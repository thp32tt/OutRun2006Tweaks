#!/usr/bin/env python3
# B218: q228 E7F6E9B7 manual PRE_INGAME false-negative repair.
# Current C144 bytes pass containment but several Korean rows are materially
# undersized and the source-wide silver techno family is rendered too blocky.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA218-E7F6E9B7"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION68/E7F6_CLEAN_PLATE.png"
EXPECTED_BEFORE="6e880cb7614531a95b5dcc8cda311423b8a6cbeaf6b7f6c2d0fc5befcca6d607"
SOURCE_SHA="3f98c940c51d2f054934d4e0b7c7d9745f9f8ad71d68548b0b336c62c1cf5154"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/Release/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
tmp=Path("/tmp/b218"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

rows=[
 ("coast 2 coast","코스트 2 코스트",[5,26,1456,145]),
 ("car select","차량 선택",[5,182,1124,301]),
 ("license select","라이선스 선택",[6,338,1500,457]),
 ("game lobby","게임 로비",[7,494,1132,644]),
 ("main menu","메인 메뉴",[6,644,1107,769]),
 ("multiplayer","멀티플레이",[6,806,1195,956]),
 ("music select","음악 선택",[6,956,1276,1077]),
 ("options","옵션",[6,1114,748,1265]),
 ("network","네트워크",[6,1274,816,1424]),
 ("rankings","랭킹",[6,1424,792,1580]),
 ("game select","게임 선택",[3,1580,1236,1736]),
 ("mode select","모드 선택",[2,1736,1252,1861]),
 ("race select","레이스 선택",[6,1898,1244,2017]),
]

def shab(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rect(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def bbox(m):
    ys,xs=np.nonzero(m); return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,2048) or len(b)!=128+w*h*4: raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mipmaps":mips,"raw_mode":mode,"format":"RGBA32"}

sb=src_dds.read_bytes(); cb=candidate.read_bytes()
if shab(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",shab(sb)))
if shab(cb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",shab(cb)))
src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(cb)
if meta!=ometa or sb[:128]!=cb[:128]: raise RuntimeError("header/meta drift")
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError("clean size drift")

sa=np.asarray(src); oa=np.asarray(old); ca=np.asarray(clean)
H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool)
for _,_,b in rows: allowed|=rect((H,W),b)
clean_diff=np.any(sa!=ca,axis=2)
if np.count_nonzero(clean_diff & ~allowed): raise RuntimeError("clean plate changed outside target bboxes")
# The validated B68 plate must contain no visible source glyphs inside the target boxes.
for en,ko,b in rows:
    x0,y0,x1,y1=b
    if np.count_nonzero(ca[y0:y1,x0:x1,3]):
        raise RuntimeError(("clean target alpha not empty",en))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Medium"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Noto CJK Medium unavailable",font_line))

STRETCH=1.18
SHEAR=0.12
MARGIN=4

def text_alpha(text,fs):
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(4,4),0))
    tb=d.textbbox((0,0),text,font=f,stroke_width=0)
    pad=12
    a=Image.new("L",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),0)
    ImageDraw.Draw(a).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255)
    bb=a.getbbox(); a=a.crop(bb)
    a=a.resize((max(1,round(a.width*STRETCH)),a.height),Image.Resampling.LANCZOS)
    # rightward techno lean
    sw=max(1,int(round(a.height*SHEAR)))
    canvas=Image.new("L",(a.width+sw+4,a.height),0)
    canvas.paste(a,(0,0))
    canvas=canvas.transform(canvas.size,Image.Transform.AFFINE,(1,-SHEAR,sw,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=canvas.getbbox(); return canvas.crop(bb)

def effect(text,fs):
    core=text_alpha(text,fs)
    # Keep the C144 silver vertical family, but use Medium CJK and stronger source-wide geometry.
    outline=np.asarray(core.filter(ImageFilter.MaxFilter(11)),dtype=np.uint8)
    shadow=np.zeros((core.height+6,core.width+6),dtype=np.uint8)
    shadow[5:5+core.height,4:4+core.width]=np.asarray(core)
    h=max(core.height,outline.shape[0],shadow.shape[0]); w=max(core.width,outline.shape[1],shadow.shape[1])
    tile=Image.new("RGBA",(w,h),(0,0,0,0))
    # shadow
    sm=Image.fromarray(shadow,"L")
    s=Image.new("RGBA",(w,h),(2,2,2,200)); s.putalpha(sm); tile.alpha_composite(s)
    # outline centered at origin
    om=Image.fromarray(outline,"L")
    o=Image.new("RGBA",(w,h),(2,2,2,255)); o.putalpha(om); tile.alpha_composite(o)
    # vertical silver gradient
    g=np.zeros((core.height,core.width,4),dtype=np.uint8)
    for y in range(core.height):
        t=y/max(1,core.height-1)
        v=int(round(244*(1-t)+134*t))
        g[y,:,0:3]=v
    g[:,:,3]=np.asarray(core)
    f=Image.fromarray(g,"RGBA"); tile.alpha_composite(f,(0,0))
    bb=tile.getbbox(); return tile.crop(bb)

def fit_effect(text,b):
    aw=b[2]-b[0]; ah=b[3]-b[1]
    maxw,maxh=aw-2*MARGIN,ah-2*MARGIN
    best=None
    for fs in range(170,60,-1):
        t=effect(text,fs)
        if t.width<=maxw and t.height<=maxh:
            best=(fs,t); break
    if best is None: raise RuntimeError(("fit failed",text,b))
    return best

final=clean.copy(); target=np.zeros((H,W),bool); rr=[]
for en,ko,b in rows:
    fs,tile=fit_effect(ko,b)
    x0,y0,x1,y1=b; aw=x1-x0; ah=y1-y0
    px=x0+MARGIN
    py=y0+(ah-tile.height)//2
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    lb=bbox(lm); margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("margin",en,lb,b,margins))
    final.alpha_composite(layer); target|=lm
    oldm=(oa[:,:,3]>0)&rect((H,W),b); ob=bbox(oldm)
    os=None if ob is None else [ob[2]-ob[0],ob[3]-ob[1]]
    ns=[lb[2]-lb[0],lb[3]-lb[1]]
    rr.append({"source":en,"korean":ko,"source_bbox":b,"source_size":[aw,ah],
      "prior_localized_bbox":ob,"prior_localized_size":os,"localized_bbox":lb,"localized_size":ns,
      "margins":margins,"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,
      "font_size":fs,"horizontal_stretch":STRETCH,"shear":SHEAR,
      "width_gain_px":None if os is None else ns[0]-os[0],"height_gain_px":None if os is None else ns[1]-os[1],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["raw_mode"])
candidate.write_bytes(payload)
after=shab(payload)
new_raw,new,nmeta=decode(payload)
if nmeta!=meta or payload[:128]!=sb[:128] or ImageChops.difference(new,final).getbbox() is not None:
    raise RuntimeError("roundtrip/header failure")
na=np.asarray(new)
diff=np.any(sa!=na,axis=2)
outside=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=na[:,:,3]) & ~allowed))
source_residue=0
# Since the clean plate is transparent in all target boxes, any exact source-only color/alpha residue is absent;
# retain a conservative alpha check outside the new target glyphs.
for en,ko,b in rows:
    x0,y0,x1,y1=b
    core=(sa[y0:y1,x0:x1,3]>0)&(na[y0:y1,x0:x1,3]>0)
    # Exact old source RGB surviving in pixels not covered by the new target indicates residue.
    same=np.all(sa[y0:y1,x0:x1]==na[y0:y1,x0:x1],axis=2)
    source_residue+=int(np.count_nonzero(core & same))
# Exact source pixels may naturally equal parts of the new grayscale effect; residue is validated visually below,
# so machine hard-fail uses outside/alpha and clean-plate provenance rather than color coincidence.
if outside or alpha_out: raise RuntimeError(("outside gate",outside,alpha_out))

height_improved=sum(1 for r in rr if (r["height_gain_px"] or 0)>0)
height_material=sum(1 for r in rr if (r["height_gain_px"] or 0)>=12)
if height_improved<7 or height_material<5: raise RuntimeError(("insufficient hierarchy improvement",height_improved,height_material))

def comp(im):
    bg=Image.new("RGBA",im.size,(104,104,104,255)); bg.alpha_composite(im); return bg.convert("RGB")
def labeled(label,im,size=(1024,1024)):
    v=comp(im).resize(size,Image.Resampling.LANCZOS)
    c=Image.new("RGB",(size[0],size[1]+28),(25,25,25)); c.paste(v,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c

cards=[labeled("SOURCE",src),labeled("C144/B68",old),labeled("B68 CLEAN",clean),labeled("B218",new)]
sheet=Image.new("RGB",(2048,2104),(22,22,22))
sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(1024,0));sheet.paste(cards[2],(0,1052));sheet.paste(cards[3],(1024,1052))
sheet.thumbnail((1700,1750),Image.Resampling.LANCZOS); sheet.save(out/"B218_E7F6_SOURCE_OLD_CLEAN_NEW_READABLE.jpg","JPEG",quality=95,subsampling=0)
raw=Image.new("RGB",(2100,728),(22,22,22))
for i,(lab,im) in enumerate([("SOURCE RAW",src_raw),("C144 RAW",old_raw),("B218 RAW",new_raw)]):
    c=labeled(lab,im,(700,700)); raw.paste(c,(700*i,0))
raw.thumbnail((1900,700),Image.Resampling.LANCZOS); raw.save(out/"B218_E7F6_SOURCE_OLD_NEW_RAW.jpg","JPEG",quality=95,subsampling=0)

contacts=[]
scomp,ocomp,ncomp=comp(src),comp(old),comp(new)
for r in rr:
    x0,y0,x1,y1=r["source_bbox"]; p=8; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[]
    for im in (scomp,ocomp,ncomp):
        z=im.crop(cr); sc=min(1.0,900/max(1,z.width)); z=z.resize((max(1,round(z.width*sc)),max(1,round(z.height*sc))),Image.Resampling.LANCZOS); ims.append(z)
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+26
    c=Image.new("RGB",(cw,ch),(25,25,25)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","C144","B218"),ims):
        d.text((xx+3,4),lab,fill="white"); c.paste(z,(xx,24)); xx+=z.width+6
    contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+5*(len(contacts)-1)),(22,22,22))
yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+5
rs.thumbnail((2200,9000),Image.Resampling.LANCZOS); rs.save(out/"B218_E7F6_ROW_CONTACT.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B218","queue_index":228,"asset":asset,
 "trigger":"MANUAL_PRE_INGAME_ENGLISH_ORIGINAL_VISUAL_FALSE_NEGATIVE_AFTER_NEW_8_STEP_GATE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/058_q228_E7F6E9B7.jpg",
 "prior_c_status":"C144_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["UNNECESSARY_UNDERSIZING_ON_TALL_ROWS","SOURCE_TECHNO_PROPORTION_WEIGHT_MISMATCH"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "method":"pinned exact source + C144/B68 validated clean plate; fresh native Noto CJK Medium; per-row maximum safe height with 4px positive margin; 1.18x source-wide geometry; preserved silver gradient/dark outline-shadow/rightward techno lean; exact canonical DDS header/BGRA/raw mirror_y",
 "rows":rr,
 "machine_qa":{"bbox_size_positive_margin":"13/13 PASS","changed_outside_source_bboxes":outside,
   "alpha_changed_outside_source_bboxes":alpha_out,"clean_changed_outside_source_bboxes":int(np.count_nonzero(clean_diff&~allowed)),
   "height_improved_rows":height_improved,"height_material_gain_ge12_rows":height_material,
   "header_128_exact":True,"raw_mode":meta["raw_mode"],"raw_orientation":"mirror_y"},
 "ordered_generation_gate":{
   "1_source_text_removed_and_plate_restored":"PASS_INHERITED_C144_VALIDATED_B68_CLEAN_PLATE",
   "2_source_matching_slant_direction":"PASS_RIGHTWARD_TECHNO_SHEAR",
   "3_no_unnecessary_undersizing":"PASS_MAX_SAFE_PER_ROW_HEIGHT_WITH_4PX_MARGIN",
   "4_source_faithful_weight_outline_shadow":"PASS_MEDIUM_CJK_PLUS_SILVER_GRADIENT_DARK_OUTLINE_SHADOW",
   "5_no_clipped_pixels":"PASS_13_OF_13_POSITIVE_MARGIN",
   "6_protected_art_clearance":"PASS_ZERO_CHANGES_OUTSIDE_EXACT_SOURCE_BBOXES",
   "7_raw_and_flip_y":"PASS_EVIDENCE_WRITTEN",
   "8_immediate_readability_vs_english":"PENDING_CONTROLLER_VISUAL"
 },
 "runtime_validation":"UNTESTED","status":"B218_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B218_E7F6E9B7_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B218_E7F6E9B7.json").write_text(json.dumps({"role":"B","run":"B218","queue_index":228,"asset":asset,"candidate_sha256":after,"report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B218","before":EXPECTED_BEFORE,"after":after,"font":Path(FONT).name,"height_improved_rows":height_improved,"height_material_gain_ge12_rows":height_material,"status":report["status"]},ensure_ascii=False))

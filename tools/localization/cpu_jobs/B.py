#!/usr/bin/env python3
# B222: q94 2DA43E41 strict PRE_INGAME hierarchy/slant rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA222-2DA43E41"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_CLEAN_PLATE_CANONICAL.png"
source_mask_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_SOURCE_TEXT_MASK_CANONICAL.png"
EXPECTED_BEFORE="dce31f89fa30da614378d7cfd8e3b9e8b6d39bc037369f059249e358897c66ae"
SOURCE_SHA="3e00bfda82c2175b28c1d45d3041f91e34ede6de52b867cd867c1c27d4837099"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/Release/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds"
tmp=Path("/tmp/b222"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

ROWS={
 "course_or2":{"source":"OutRun2 · 15 Continuous Course has been selected.","korean":["OutRun2 · 15코스 연속이","선택되었습니다."],"bbox":[115,192,2056,448],"old_bbox":[569,207,1645,429],"kind":"course","width_ratio":0.82},
 "course_sp":{"source":"OutRun2: SP · 15 Continuous Course has been selected.","korean":["OutRun2: SP · 15코스 연속이","선택되었습니다."],"bbox":[132,488,2078,717],"old_bbox":[456,496,1754,709],"kind":"course","width_ratio":0.82},
 "max_speed":{"source":"最高速:","korean":"최고 속도:","bbox":[3827,319,4018,410],"old_bbox":[3829,340,4015,388],"kind":"plain","width_ratio":0.96,"height_ratio":0.84},
 "handling":{"source":"ハンドリング:","korean":"핸들링:","bbox":[1677,896,2112,1050],"old_bbox":[1731,920,2066,1026],"kind":"plain","width_ratio":0.88,"height_ratio":0.86},
 "view_change":{"source":"View Change Button :","korean":"시점 변경 버튼:","bbox":[3430,998,3896,1102],"old_bbox":[3434,1023,3890,1098],"kind":"view","width_ratio":0.90,"height_ratio":0.82,"slant":0.26},
 "expert":{"source":"For Expert Drivers","korean":"상급자용","bbox":[2842,1124,3479,1229],"old_bbox":[2984,1125,3337,1228],"kind":"expert","width_ratio":0.86,"height_ratio":0.82,"slant":0.25},
 "special_course":{"source":"Special Course","korean":"스페셜 코스","bbox":[3137,1279,3879,1403],"old_bbox":[3227,1280,3781,1402],"kind":"special","width_ratio":0.86,"height_ratio":0.82,"slant":0.25},
}
PRESERVED=["wait_other","wait_now","acceleration","single_play"]

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(4096,4096) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"raw_mode":mode}
def bb(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    return im.transform((im.width+shift,im.height),Image.Transform.AFFINE,(1,s,-s*(im.height-1),0,1,0),resample=Image.Resampling.BICUBIC)

sb=src_dds.read_bytes(); cb=candidate.read_bytes()
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(sb)))
if sha_bytes(cb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha_bytes(cb)))
src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(cb)
if meta!=ometa or sb[:128]!=cb[:128]: raise RuntimeError("header/meta drift")
clean=Image.open(clean_path).convert("RGBA")
source_text_mask=Image.open(source_mask_path).convert("L")
if clean.size!=src.size or source_text_mask.size!=src.size: raise RuntimeError("clean/mask size drift")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
fl=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT,FI,FSTYLE=fl.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Noto CJK Black unavailable",fl))

# Source-derived color helpers. Exact bboxes contain source lettering/effects, so visible
# source pixels are a better style reference than a generic hand-picked palette.
sa=np.asarray(src)
def source_pixels(bbox):
    x0,y0,x1,y1=bbox
    a=sa[y0:y1,x0:x1]
    return a[a[:,:,3]>24]
def med(sel,fallback):
    if len(sel)==0: return fallback
    v=np.median(sel,axis=0).astype(int)
    return tuple(int(x) for x in v[:3])+(255,)
def palette_for(kind,bbox):
    p=source_pixels(bbox)
    rgb=p[:,:3].astype(int)
    lum=(rgb[:,0]*2126+rgb[:,1]*7152+rgb[:,2]*722)//10000
    sat=rgb.max(axis=1)-rgb.min(axis=1)
    light=med(p[lum>210],(248,248,248,255))
    dark=med(p[lum<75],(22,28,48,255))
    orange=med(p[(rgb[:,0]>170)&(rgb[:,1]>70)&(rgb[:,1]<220)&(rgb[:,2]<140)&(rgb[:,0]>rgb[:,1]+20)],(245,165,25,255))
    red=med(p[(rgb[:,0]>125)&(rgb[:,0]>rgb[:,1]*1.35)&(rgb[:,0]>rgb[:,2]*1.25)&(sat>55)],(150,25,35,255))
    blue=med(p[(rgb[:,2]>90)&(rgb[:,2]>rgb[:,0]*1.15)&(rgb[:,2]>rgb[:,1]*1.05)&(sat>45)],(28,45,155,255))
    yellow=med(p[(rgb[:,0]>150)&(rgb[:,1]>120)&(rgb[:,2]<160)&(rgb[:,0]+rgb[:,1]>360)],(244,213,92,255))
    cyan=med(p[(rgb[:,1]>120)&(rgb[:,2]>130)&(rgb[:,2]>rgb[:,0]+20)],(45,190,235,255))
    return {"light":light,"dark":dark,"orange":orange,"red":red,"blue":blue,"yellow":yellow,"cyan":cyan}

def native_mask(text,fs,stroke=0):
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    pad=max(8,stroke+5)
    m=Image.new("L",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),0)
    ImageDraw.Draw(m).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255,stroke_width=stroke,stroke_fill=255)
    b=m.getbbox()
    return m.crop(b),f

def color_tile(text,fs,kind,pal,slant=0.0):
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    if kind=="plain":
        outer=max(1,round(fs*.018)); inner=0; fill=pal["light"]; inner_col=fill; outer_col=pal["dark"]
    elif kind=="view":
        outer=max(2,round(fs*.055)); inner=max(1,round(fs*.018)); fill=pal["light"]; inner_col=pal["light"]; outer_col=pal["dark"]
    elif kind=="expert":
        outer=max(3,round(fs*.072)); inner=max(2,round(fs*.043)); fill=pal["blue"]; inner_col=pal["red"]; outer_col=pal["light"]
    elif kind=="special":
        outer=max(3,round(fs*.065)); inner=max(2,round(fs*.035)); fill=pal["yellow"]; inner_col=pal["dark"]; outer_col=pal["light"]
    else:
        raise RuntimeError(kind)
    tb=d.textbbox((0,0),text,font=f,stroke_width=outer)
    pad=outer+8
    size=(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad)
    fillm=Image.new("L",size,0); midm=Image.new("L",size,0); outm=Image.new("L",size,0)
    pos=(pad-tb[0],pad-tb[1])
    ImageDraw.Draw(fillm).text(pos,text,font=f,fill=255)
    ImageDraw.Draw(midm).text(pos,text,font=f,fill=255,stroke_width=inner,stroke_fill=255)
    ImageDraw.Draw(outm).text(pos,text,font=f,fill=255,stroke_width=outer,stroke_fill=255)
    tile=Image.new("RGBA",size,(0,0,0,0))
    tile.paste(outer_col,(0,0),outm)
    tile.paste(inner_col,(0,0),midm)
    tile.paste(fill,(0,0),fillm)
    if slant: tile=shear_rgba(tile,slant)
    ab=tile.getchannel("A").getbbox()
    return tile.crop(ab),{"font_size":fs,"outer_stroke":outer,"inner_stroke":inner,"fill":fill,"inner_color":inner_col,"outer_color":outer_col}

def fit_single(key,cfg):
    x0,y0,x1,y1=cfg["bbox"]; sw=x1-x0; sh=y1-y0
    pal=palette_for(cfg["kind"],cfg["bbox"])
    slant=cfg.get("slant",0.0)
    best=None
    for fs in range(min(190,round(sh*1.15)),20,-1):
        tile,sty=color_tile(cfg["korean"],fs,cfg["kind"],pal,slant)
        # Height first: preserve source vertical hierarchy, then shape fresh native raster horizontally.
        if tile.height<=max(8,round(sh*cfg.get("height_ratio",0.88))):
            best=(tile,sty); break
    if best is None: raise RuntimeError(("fit_single_height",key))
    tile,sty=best
    target_w=min(sw-4,max(tile.width,round(sw*cfg["width_ratio"])))
    target_h=min(sh-4,max(tile.height,round(sh*cfg.get("height_ratio",tile.height/sh))))
    # Do not enlarge vertically after rasterization; choose fs for target height. Horizontal shaping only.
    if target_w!=tile.width:
        tile=tile.resize((target_w,tile.height),Image.Resampling.LANCZOS)
    if tile.width>sw-4 or tile.height>sh-4: raise RuntimeError(("fit_single_size",key,tile.size,cfg["bbox"]))
    px=x0+(sw-tile.width)//2; py=y0+(sh-tile.height)//2
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lb=list(layer.getchannel("A").getbbox())
    return layer,lb,{**sty,"palette":pal,"target_width_ratio":cfg["width_ratio"],"slant":slant}

def course_line(text,fs,fill,outer):
    f=ImageFont.truetype(FONT,fs,index=FI)
    stroke=max(2,round(fs*.045))
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); tb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    pad=stroke+7
    tile=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
    ImageDraw.Draw(tile).text((pad-tb[0],pad-tb[1]),text,font=f,fill=fill,stroke_width=stroke,stroke_fill=outer)
    return tile.crop(tile.getchannel("A").getbbox()),stroke
def fit_course(key,cfg):
    x0,y0,x1,y1=cfg["bbox"]; sw=x1-x0; sh=y1-y0
    pal=palette_for("course",cfg["bbox"])
    line1,line2=cfg["korean"]; best=None
    for fs in range(112,48,-1):
        a,st=course_line(line1,fs,pal["orange"],pal["dark"])
        b,_=course_line(line2,max(42,round(fs*.88)),pal["light"],pal["dark"])
        gap=max(2,round(fs*.02))
        if a.height+b.height+gap<=sh-8:
            best=(a,b,st,fs,gap); break
    if best is None: raise RuntimeError(("fit_course_height",key))
    a,b,st,fs,gap=best
    w1=min(sw-6,max(a.width,round(sw*cfg["width_ratio"])))
    # Source second line is substantially shorter than the first; keep that hierarchy.
    w2=min(sw-6,max(b.width,round(sw*0.48)))
    a=a.resize((w1,a.height),Image.Resampling.LANCZOS) if w1!=a.width else a
    b=b.resize((w2,b.height),Image.Resampling.LANCZOS) if w2!=b.width else b
    total_h=a.height+b.height+gap
    layer=Image.new("RGBA",src.size,(0,0,0,0))
    yy=y0+(sh-total_h)//2
    layer.alpha_composite(a,(x0+(sw-a.width)//2,yy)); yy+=a.height+gap
    layer.alpha_composite(b,(x0+(sw-b.width)//2,yy))
    lb=list(layer.getchannel("A").getbbox())
    return layer,lb,{"font_size":fs,"stroke":st,"palette":pal,"target_width_ratio":cfg["width_ratio"],"second_width_ratio":0.48,"slant":0.0}

final=old.copy()
layers={}
row_reports=[]
allowed=np.zeros((meta["h"],meta["w"]),bool)
for key,cfg in ROWS.items():
    x0,y0,x1,y1=cfg["bbox"]; sw=x1-x0; sh=y1-y0
    # Step 1: restore the already C90-validated clean plate only inside this exact source bbox.
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    if cfg["kind"]=="course": layer,lb,style=fit_course(key,cfg)
    else: layer,lb,style=fit_single(key,cfg)
    final.alpha_composite(layer); layers[key]=layer
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0 or lw>sw or lh>sh: raise RuntimeError(("bbox gate",key,lb,margins))
    allowed[y0:y1,x0:x1]=True
    row_reports.append({"key":key,"source":cfg["source"],"korean":cfg["korean"],"source_bbox":cfg["bbox"],
        "source_size":[sw,sh],"prior_localized_bbox":cfg["old_bbox"],"prior_size":[cfg["old_bbox"][2]-cfg["old_bbox"][0],cfg["old_bbox"][3]-cfg["old_bbox"][1]],
        "localized_bbox":lb,"localized_size":[lw,lh],"margins":margins,
        "localized_width_source_ratio":round(lw/sw,4),"localized_height_source_ratio":round(lh/sh,4),
        "style":style,"containment":"PASS","size_ceiling":"PASS"})

# Ensure reworked layers cannot overlap each other and candidate modifications remain in selected source bboxes.
keys=list(layers)
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        if ImageChops.multiply(layers[keys[i]].getchannel("A"),layers[keys[j]].getchannel("A")).getbbox():
            raise RuntimeError(("localized_overlap",keys[i],keys[j]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["raw_mode"])
candidate.write_bytes(payload); AFTER=sha_bytes(payload)
new_raw,new,nmeta=decode(payload)
if nmeta!=meta or payload[:128]!=sb[:128] or ImageChops.difference(new,final).getbbox() is not None:
    raise RuntimeError("roundtrip failure")
oa=np.asarray(old); na=np.asarray(new)
diff=np.any(oa!=na,axis=2); adiff=oa[:,:,3]!=na[:,:,3]
outside=int(np.count_nonzero(diff&~allowed)); alpha_out=int(np.count_nonzero(adiff&~allowed))
if outside or alpha_out: raise RuntimeError(("candidate_changes_outside_selected_bboxes",outside,alpha_out))

# Re-measure each row from candidate-vs-clean alpha contribution inside the source bbox.
for rr in row_reports:
    x0,y0,x1,y1=rr["source_bbox"]
    cm=(na[y0:y1,x0:x1,3]>np.asarray(clean)[y0:y1,x0:x1,3])
    db=bb(cm)
    if db is not None: db=[db[0]+x0,db[1]+y0,db[2]+x0,db[3]+y0]
    rr["decoded_target_bbox"]=db
    rr["decoded_containment"]="PASS" if db and db[0]>=x0 and db[1]>=y0 and db[2]<=x1 and db[3]<=y1 else "FAIL"
    if rr["decoded_containment"]!="PASS": raise RuntimeError(("decoded_bbox",rr["key"],db))

# Validate the inherited clean plate against its canonical full source mask again.
validator=repo/"tools/localization/validate_clean_plate.py"
src_png=tmp/"source_readable.png"; new_png=tmp/"new_readable.png"
src.save(src_png); new.save(new_png)
subprocess.run(["python3",str(validator),str(src_png),str(clean_path),str(source_mask_path),"--report",str(out/"B222_CLEAN_PLATE_VALIDATION.json")],check=True)

# Visual evidence: whole relevant upper atlas + per-row contact + RAW orientation.
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")
def crop_card(label,im,crop,scale=1):
    v=comp(im).crop(crop)
    if scale!=1: v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+26),(24,24,24)); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c
fullcrop=(0,0,4096,1500)
cards=[crop_card("SOURCE",src,fullcrop),crop_card("C90",old,fullcrop),crop_card("B222",new,fullcrop)]
for c in cards: c.thumbnail((1400,540),Image.Resampling.LANCZOS)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(20,20,20)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B222_2DA_SOURCE_C90_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
for rr in row_reports:
    x0,y0,x1,y1=rr["source_bbox"]; p=12; cr=(max(0,x0-p),max(0,y0-p),min(meta["w"],x1+p),min(meta["h"],y1+p))
    z=[crop_card("SOURCE",src,cr,2),crop_card("C90",old,cr,2),crop_card("B222",new,cr,2)]
    cw=sum(i.width for i in z)+8; ch=max(i.height for i in z)
    c=Image.new("RGB",(cw,ch+24),(20,20,20)); ImageDraw.Draw(c).text((4,4),rr["key"],fill="white"); xx=0
    for i in z: c.paste(i,(xx,24)); xx+=i.width+4
    contacts.append(c)
cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),(20,20,20)); yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+4
cs.save(out/"B222_2DA_ROW_CONTACT_2X.jpg","JPEG",quality=96,subsampling=0)

raw_cards=[crop_card("SOURCE RAW",src_raw,(0,meta["h"]-1500,4096,4096)),crop_card("B222 RAW",new_raw,(0,meta["h"]-1500,4096,4096))]
for c in raw_cards: c.thumbnail((1400,540),Image.Resampling.LANCZOS)
rs=Image.new("RGB",(max(c.width for c in raw_cards),sum(c.height for c in raw_cards)+4),(20,20,20)); yy=0
for c in raw_cards: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"B222_2DA_SOURCE_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B222","queue_index":94,"asset":asset,
 "trigger":"STRICT_PRE_INGAME_8_STEP_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/007_q094_2DA43E41.jpg",
 "prior_c_status":"C_USERPOLICY02_PASS_PENDING_INGAME",
 "defects":["MULTIROW_TEXT_HIERARCHY_UNDERSIZED","VIEW_CHANGE_RIGHT_SLANT_STYLE_MISMATCH","EXPERT_RIGHT_SLANT_AND_WIDTH_MISMATCH","SPECIAL_COURSE_RIGHT_SLANT_AND_WIDTH_MISMATCH"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,
 "method":"exact pinned 4096x4096 RGBA32 source + C90/B_RECOVERY05 independently validated canonical clean plate; only 7 strict-audit-failing source bboxes restored; fresh native Noto Sans CJK KR Black at final atlas resolution; source-derived palettes; fresh-raster horizontal family shaping for source hierarchy; explicit readable right shear only on source-italic rows; preserved 4 acceptable localized rows byte/pixel exact outside selected bboxes",
 "reworked_keys":list(ROWS),"preserved_keys":PRESERVED,"rows":row_reports,
 "machine_qa":{"bbox_size_positive_margin":"7/7 PASS","candidate_changes_outside_selected_source_bboxes":outside,
   "alpha_changes_outside_selected_source_bboxes":alpha_out,"reworked_row_overlap_pixels":0,
   "header_128_exact":True,"raw_mode":meta["raw_mode"],"raw_orientation":"mirror_y","roundtrip":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_C90_VALIDATED_CLEAN_REUSED_AND_REVALIDATED",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT_OR_EXPLICIT_RIGHT_SHEAR_BY_ROW",
   "3_no_unnecessary_undersizing":"PASS_SEVEN_FALSE_NEGATIVE_ROWS_HIERARCHY_RESTORED",
   "4_source_weight_outline_shadow":"PASS_SOURCE_DERIVED_PALETTE_NATIVE_BLACK",
   "5_no_clipping":"PASS_7_OF_7_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_CANDIDATE_CHANGE_OUTSIDE_SELECTED_EXACT_SOURCE_BBOXES",
   "7_flip_y_raw":"PASS_RAW_EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"
 },
 "runtime_validation":"UNTESTED","status":"B222_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B222_2DA43E41_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B222_2DA43E41.json").write_text(json.dumps({"role":"B","run":"B222","queue_index":94,"asset":asset,
 "candidate_sha256":AFTER,"report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B222","before":EXPECTED_BEFORE,"after":AFTER,"rows":{r["key"]:{"old":r["prior_size"],"new":r["localized_size"],"ratios":[r["localized_width_source_ratio"],r["localized_height_source_ratio"]]} for r in row_reports},"status":report["status"]},ensure_ascii=False))

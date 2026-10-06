#!/usr/bin/env python3
# B224: q140 31C58963 strict PRE_INGAME hierarchy rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA224-31C58963"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_C/20261005-C140-31C58963/C140_EXACT_CLEAN_PLATE.png"
source_mask_path=repo/"localization/graphics/role_C/20261005-C140-31C58963/C140_SOURCE_TEXT_MASK.png"
allowed_full_path=repo/"localization/graphics/role_C/20261005-C140-31C58963/C140_ALLOWED_BBOX_MASK.png"
protected_full_path=repo/"localization/graphics/role_C/20261005-C140-31C58963/C140_PROTECTED_VISIBLE_MASK.png"
enter_icon_path=repo/"localization/graphics/role_C/20261005-C140-31C58963/C140_ENTER_ICON_MASK.png"
EXPECTED_BEFORE="ecc7efdde172f410c85207ecdc5bbfd5bac95c753341763ad6afb9a6a7f1b3f2"
SOURCE_SHA="ae048d04fef96108f6ee30c41022aedb78083d76386448df5483ae0ccd083dcd"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds"
tmp=Path("/tmp/b224"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

# Four white headings and the yellow KEY word are materially undersized in C140 PRE_INGAME #017.
ROWS=[
 {"key":"select_stage","source":"SELECT STAGE","korean":"스테이지 선택","bbox":[7,905,840,1003],"prior_bbox":[9,907,548,1001],"kind":"white","target_width":630,"font_size":95},
 {"key":"select_race","source":"SELECT RACE","korean":"레이스 선택","bbox":[13,749,793,847],"prior_bbox":[15,751,463,845],"kind":"white","target_width":560,"font_size":95},
 {"key":"select_mode","source":"SELECT MODE","korean":"모드 선택","bbox":[7,589,815,687],"prior_bbox":[9,591,373,685],"kind":"white","target_width":500,"font_size":95},
 {"key":"showroom","source":"SHOWROOM","korean":"쇼룸","bbox":[7,432,652,527],"prior_bbox":[9,434,181,525],"kind":"white","target_width":280,"font_size":95},
 {"key":"key_word","source":"KEY","korean":"키","bbox":[457,319,583,381],"prior_bbox":[498,321,547,379],"kind":"yellow","target_width":82,"font_size":48},
]
PRESERVED={"press_word":"누르세요","enter_icon":"original Enter-key icon"}

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def decode_rgba32(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,1024) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"raw_mode":mode}
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")

sb=src_dds.read_bytes(); cb=candidate.read_bytes()
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(sb)))
if sha_bytes(cb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha_bytes(cb)))
src_raw,src,meta=decode_rgba32(sb); old_raw,old,ometa=decode_rgba32(cb)
if meta!=ometa or sb[:128]!=cb[:128]: raise RuntimeError("header/meta drift")
clean=Image.open(clean_path).convert("RGBA")
source_mask=Image.open(source_mask_path).convert("L")
allowed_full=Image.open(allowed_full_path).convert("L")
protected_full=Image.open(protected_full_path).convert("L")
enter_icon=Image.open(enter_icon_path).convert("L")
if any(im.size!=src.size for im in [clean,source_mask,allowed_full,protected_full,enter_icon]):
    raise RuntimeError("mask size drift")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
fl=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=fl.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Noto CJK Bold unavailable",fl))

WHITE=(255,255,255,255)
YELLOW=(255,203,57,255)
BLACK=(0,0,0,255)

def native_tile(text,fs,kind):
    stroke=2 if kind=="white" else 6
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    pad=stroke+8
    tile=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
    ImageDraw.Draw(tile).text((pad-tb[0],pad-tb[1]),text,font=f,
                              fill=WHITE if kind=="white" else YELLOW,
                              stroke_width=stroke,
                              stroke_fill=WHITE if kind=="white" else BLACK)
    ab=tile.getchannel("A").getbbox()
    return tile.crop(ab),stroke

final=old.copy()
selected=np.zeros((meta["h"],meta["w"]),bool)
layers={}
rows=[]
for cfg in ROWS:
    x0,y0,x1,y1=cfg["bbox"]; sw=x1-x0; sh=y1-y0
    # First restore the exact C140 clean plate over this source cell.
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    tile,stroke=native_tile(cfg["korean"],cfg["font_size"],cfg["kind"])
    target_w=min(sw-4,cfg["target_width"])
    if target_w<tile.width:  # never shrink height to force fit; use horizontal refit only.
        tile=tile.resize((target_w,tile.height),Image.Resampling.LANCZOS)
    elif target_w>tile.width:
        tile=tile.resize((target_w,tile.height),Image.Resampling.LANCZOS)
    if tile.width>=sw or tile.height>=sh:
        raise RuntimeError(("preplace ceiling",cfg["key"],tile.size,[sw,sh]))
    # Preserve the source-left heading alignment; KEY remains centered in its own exact word bbox.
    if cfg["kind"]=="white":
        px=x0+2
    else:
        px=x0+(sw-tile.width)//2
    py=y0+(sh-tile.height)//2
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lb=list(layer.getchannel("A").getbbox())
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("margin",cfg["key"],lb,margins))
    final.alpha_composite(layer); layers[cfg["key"]]=layer
    selected[y0:y1,x0:x1]=True
    oldw=cfg["prior_bbox"][2]-cfg["prior_bbox"][0]; oldh=cfg["prior_bbox"][3]-cfg["prior_bbox"][1]
    rows.append({
      "key":cfg["key"],"source":cfg["source"],"korean":cfg["korean"],"source_bbox":cfg["bbox"],
      "source_size":[sw,sh],"prior_localized_bbox":cfg["prior_bbox"],"prior_size":[oldw,oldh],
      "localized_bbox":lb,"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"margins":margins,
      "width_source_ratio":round((lb[2]-lb[0])/sw,4),"height_source_ratio":round((lb[3]-lb[1])/sh,4),
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,
      "font_size":cfg["font_size"],"stroke_width":stroke,"kind":cfg["kind"],
      "containment":"PASS","size_ceiling":"PASS"
    })

# No localized layer overlap among reworked rows.
ks=list(layers)
for i in range(len(ks)):
    for j in range(i+1,len(ks)):
        if ImageChops.multiply(layers[ks[i]].getchannel("A"),layers[ks[j]].getchannel("A")).getbbox():
            raise RuntimeError(("localized overlap",ks[i],ks[j]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["raw_mode"])
candidate.write_bytes(payload)
AFTER=sha_bytes(payload)
new_raw,new,nmeta=decode_rgba32(payload)
if nmeta!=meta or payload[:128]!=sb[:128] or ImageChops.difference(new,final).getbbox() is not None:
    raise RuntimeError("roundtrip failure")

oa=np.asarray(old); na=np.asarray(new)
diff=np.any(oa!=na,axis=2)
adiff=oa[:,:,3]!=na[:,:,3]
outside=int(np.count_nonzero(diff & ~selected))
alpha_out=int(np.count_nonzero(adiff & ~selected))
if outside or alpha_out: raise RuntimeError(("outside selected",outside,alpha_out))

# Full-family static protection gates.
prot=np.asarray(protected_full)>0
icon=np.asarray(enter_icon)>0
protected_changed=int(np.count_nonzero(diff & prot))
enter_icon_changed=int(np.count_nonzero(diff & icon))
if protected_changed or enter_icon_changed:
    raise RuntimeError(("protected change",protected_changed,enter_icon_changed))

# Re-measure decoded rows.
for rr in rows:
    x0,y0,x1,y1=rr["source_bbox"]
    # Changed visible target relative to exact clean, within this source cell.
    a=na[y0:y1,x0:x1]
    c=np.asarray(clean)[y0:y1,x0:x1]
    vis=(a[:,:,3]>16) & (np.any(a[:,:,:3]!=c[:,:,:3],axis=2) | (a[:,:,3]!=c[:,:,3]))
    db=bbox(vis)
    if db is None: raise RuntimeError(("decoded empty",rr["key"]))
    db=[db[0]+x0,db[1]+y0,db[2]+x0,db[3]+y0]
    margins=[db[0]-x0,x1-db[2],db[1]-y0,y1-db[3]]
    if min(margins)<=0: raise RuntimeError(("decoded margin",rr["key"],db,margins))
    rr["decoded_localized_bbox"]=db
    rr["decoded_localized_size"]=[db[2]-db[0],db[3]-db[1]]
    rr["decoded_margins"]=margins
    rr["decoded_containment"]="PASS"; rr["decoded_size_ceiling"]="PASS"

# Revalidate exact clean and full final against C140 full masks.
src_png=tmp/"source_readable.png"; new_png=tmp/"new_readable.png"
src.save(src_png); new.save(new_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_path),str(source_mask_path),
                "--protected-mask",str(protected_full_path),"--report",str(out/"B224_CLEAN_PLATE_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(new_png),str(allowed_full_path),
                "--protected-mask",str(protected_full_path),"--report",str(out/"B224_FINAL_MASK_VALIDATION.json")],check=True)

# Evidence: SOURCE / C140 / B224 readable, selected row contacts, RAW.
def card(label,im):
    v=comp(im)
    c=Image.new("RGB",(v.width,v.height+28),(24,24,24)); c.paste(v,(0,28))
    ImageDraw.Draw(c).text((6,6),label,fill="white")
    return c
cards=[card("SOURCE",src),card("C140",old),card("B224",new)]
sheet=Image.new("RGB",(meta["w"],sum(c.height for c in cards)+8),(20,20,20)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B224_31C_SOURCE_C140_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
for rr in rows:
    x0,y0,x1,y1=rr["source_bbox"]; p=10
    cr=(max(0,x0-p),max(0,y0-p),min(meta["w"],x1+p),min(meta["h"],y1+p))
    ims=[comp(z).crop(cr) for z in [src,old,new]]
    ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+28
    c=Image.new("RGB",(cw,ch),(24,24,24)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(["SOURCE","C140","B224"],ims):
        d.text((xx+5,6),lab,fill="white"); c.paste(z,(xx,28)); xx+=z.width+6
    contacts.append(c)
cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),(20,20,20)); yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+4
cs.save(out/"B224_31C_ROW_CONTACT_2X.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE RAW",src_raw),card("B224 RAW",new_raw)]
rs=Image.new("RGB",(meta["w"],sum(c.height for c in rawcards)+4),(20,20,20)); yy=0
for c in rawcards: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"B224_31C_SOURCE_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B224","queue_index":140,"asset":asset,
 "trigger":"STRICT_PRE_INGAME_8_STEP_VISUAL_FALSE_NEGATIVE_HIERARCHY",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/017_q140_31C58963.jpg",
 "prior_c_status":"C140_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,"source_url":url,
 "defects":["FOUR_WHITE_HEADINGS_VISIBLY_UNDERSIZED","KEY_WORD_VISIBLY_UNDERSIZED","SOURCE_RELATIVE_HIERARCHY_TOO_WEAK"],
 "preserved":PRESERVED,
 "method":"exact pinned 2048x1024 RGBA32 source + C140 independent exact clean plate; rerender four white headings with native Noto Sans CJK KR Bold 95px + 2px same-color weight and source-left 2px anchor; moderate source-relative horizontal restoration from fresh native raster (630/560/500/280px) to avoid the prior caption-like hierarchy; rerender KEY from native 48px yellow/black family to 82px width while preserving PRESS and Enter icon exactly; only five exact source bboxes changed",
 "rows":rows,
 "machine_qa":{"bbox_source_size_positive_margin":"5/5 PASS","candidate_changes_outside_selected_source_bboxes":outside,
   "alpha_changes_outside_selected_source_bboxes":alpha_out,"protected_visible_changed":protected_changed,
   "enter_icon_changed":enter_icon_changed,"localized_overlap_pixels":0,"header_128_exact":True,
   "raw_mode":meta["raw_mode"],"raw_orientation":"mirror_y","roundtrip":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_C140_EXACT_CLEAN_REUSED_AND_REVALIDATED",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT_FAMILY",
   "3_no_unnecessary_undersizing":"PASS_MATERIAL_HIERARCHY_RESTORATION",
   "4_source_weight_outline_shadow":"PASS_SHARED_BOLD_WHITE_AND_YELLOW_BLACK_SOURCE_FAMILIES",
   "5_no_clipping":"PASS_5_OF_5_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_OUTSIDE_PROTECTED_AND_ENTER_ICON_CHANGE",
   "7_flip_y_raw":"PASS_RAW_EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"
 },
 "runtime_validation":"UNTESTED","status":"B224_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B224_31C58963_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B224_31C58963.json").write_text(json.dumps({"role":"B","run":"B224","queue_index":140,"asset":asset,
 "candidate_sha256":AFTER,"report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B224","before":EXPECTED_BEFORE,"after":AFTER,"rows":[{"key":r["key"],"old":r["prior_size"],"new":r["decoded_localized_size"],"source":r["source_size"],"margins":r["decoded_margins"]} for r in rows],"outside":outside,"protected":protected_changed,"icon":enter_icon_changed,"status":report["status"]},ensure_ascii=False))

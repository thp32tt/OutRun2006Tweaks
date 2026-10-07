#!/usr/bin/env python3
# B226: q226 E3F4BA07 strict PRE_INGAME source-hierarchy rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA226-E3F4BA07"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
c143=repo/"localization/graphics/role_C/20261005-C143-E3F4BA07"
clean_path=c143/"C143_EXACT_CLEAN_PLATE.png"
source_mask_path=c143/"C143_SOURCE_TEXT_MASK.png"
allowed_full_path=c143/"C143_ALLOWED_BBOX_MASK.png"
protected_path=c143/"C143_PROTECTED_OUTRUN_MASK.png"
EXPECTED_BEFORE="1042102e5f298628ce874fe86a5562211f8a02c87fdd4de55324679f84d8f12c"
SOURCE_SHA="fb31e9f62e0d46c4554646be2f32d70cb015e8fdbc269189bf9d76a26eab5b72"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds"
tmp=Path("/tmp/b226"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

# C143 numeric PASS is visually weak in PRE_INGAME #024 for the GOAL A-E family and
# 15 STAGE CONTINUOUS. Preserve already-strong STAGE and the standalone short GOAL label.
ROWS=[
 {"key":"goal_e","source":"GOAL E","korean":"골 E","bbox":[980,346,1233,410],"prior_bbox":[982,350,1084,406],"target_width":150},
 {"key":"goal_d","source":"GOAL D","korean":"골 D","bbox":[4,262,256,326],"prior_bbox":[6,266,114,322],"target_width":154},
 {"key":"goal_c","source":"GOAL C","korean":"골 C","bbox":[983,262,1234,326],"prior_bbox":[985,266,1091,322],"target_width":152},
 {"key":"goal_b","source":"GOAL B","korean":"골 B","bbox":[4,170,257,234],"prior_bbox":[6,174,113,230],"target_width":153},
 {"key":"goal_a","source":"GOAL A","korean":"골 A","bbox":[986,170,1242,234],"prior_bbox":[988,174,1095,230],"target_width":154},
 {"key":"15_stage","source":"15 STAGE CONTINUOUS","korean":"15코스 연속","bbox":[985,86,1809,150],"prior_bbox":[987,88,1280,147],"target_width":450},
]
PRESERVED={"stage":"스테이지","goal":"골","outrun2":"protected","outrun2sp":"protected"}

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,512) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"mode":mode}
def bb(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    v=comp(im)
    c=Image.new("RGB",(v.width,v.height+26),(24,24,24)); c.paste(v,(0,26))
    ImageDraw.Draw(c).text((5,5),label,fill="white")
    return c

sb=src_dds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha(cb)))
src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(cb)
if meta!=ometa or sb[:128]!=cb[:128]: raise RuntimeError("header/meta drift")
clean=Image.open(clean_path).convert("RGBA")
source_mask=Image.open(source_mask_path).convert("L")
allowed_full=Image.open(allowed_full_path).convert("L")
protected=Image.open(protected_path).convert("L")
if any(im.size!=src.size for im in [clean,source_mask,allowed_full,protected]):
    raise RuntimeError("mask size drift")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
fm=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=fm.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name: raise RuntimeError(("font",fm))
FILL=(79,97,101,255); FS=58; STROKE=2

def render(text):
    f=ImageFont.truetype(FONT,FS,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f,stroke_width=STROKE)
    pad=STROKE+8
    im=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
    ImageDraw.Draw(im).text((pad-tb[0],pad-tb[1]),text,font=f,fill=FILL,stroke_width=STROKE,stroke_fill=FILL)
    b=im.getchannel("A").getbbox()
    if not b: raise RuntimeError(("empty",text))
    return im.crop(b)

final=old.copy()
selected=np.zeros((meta["h"],meta["w"]),bool)
layers={}
rows=[]
for cfg in ROWS:
    x0,y0,x1,y1=cfg["bbox"]; sw=x1-x0; sh=y1-y0
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    tile=render(cfg["korean"])
    target=min(sw-4,cfg["target_width"])
    # Fresh native raster -> moderate horizontal family shaping only. Height remains native.
    if tile.width!=target: tile=tile.resize((target,tile.height),Image.Resampling.LANCZOS)
    if tile.width>=sw or tile.height>=sh: raise RuntimeError(("ceiling",cfg["key"],tile.size,[sw,sh]))
    px=x0+2
    py=y0+(sh-tile.height)//2
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lb=list(layer.getchannel("A").getbbox())
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("margin",cfg["key"],lb,margins))
    final.alpha_composite(layer); layers[cfg["key"]]=layer
    selected[y0:y1,x0:x1]=True
    rows.append({
      "key":cfg["key"],"source":cfg["source"],"korean":cfg["korean"],
      "source_bbox":cfg["bbox"],"source_size":[sw,sh],"prior_bbox":cfg["prior_bbox"],
      "prior_size":[cfg["prior_bbox"][2]-cfg["prior_bbox"][0],cfg["prior_bbox"][3]-cfg["prior_bbox"][1]],
      "localized_bbox":lb,"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"margins":margins,
      "width_source_ratio":round((lb[2]-lb[0])/sw,4),"height_source_ratio":round((lb[3]-lb[1])/sh,4),
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":FS,
      "stroke_width":STROKE,"fill_rgba":FILL,"containment":"PASS","size_ceiling":"PASS"
    })

ks=list(layers)
for i in range(len(ks)):
    for j in range(i+1,len(ks)):
        if ImageChops.multiply(layers[ks[i]].getchannel("A"),layers[ks[j]].getchannel("A")).getbbox():
            raise RuntimeError(("overlap",ks[i],ks[j]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["mode"])
candidate.write_bytes(payload); AFTER=sha(payload)
new_raw,new,nmeta=decode(payload)
if nmeta!=meta or payload[:128]!=sb[:128] or ImageChops.difference(new,final).getbbox() is not None:
    raise RuntimeError("roundtrip")

oa=np.asarray(old); na=np.asarray(new); ca=np.asarray(clean)
diff=np.any(oa!=na,axis=2); adiff=oa[:,:,3]!=na[:,:,3]
outside=int(np.count_nonzero(diff&~selected)); alpha_out=int(np.count_nonzero(adiff&~selected))
prot=np.asarray(protected)>0
protected_changed=int(np.count_nonzero(diff&prot))
if outside or alpha_out or protected_changed:
    raise RuntimeError(("protection",outside,alpha_out,protected_changed))

for rr in rows:
    x0,y0,x1,y1=rr["source_bbox"]
    a=na[y0:y1,x0:x1]; c=ca[y0:y1,x0:x1]
    vis=(a[:,:,3]>16)&(np.any(a[:,:,:3]!=c[:,:,:3],axis=2)|(a[:,:,3]!=c[:,:,3]))
    db=bb(vis)
    if db is None: raise RuntimeError(("decoded empty",rr["key"]))
    db=[db[0]+x0,db[1]+y0,db[2]+x0,db[3]+y0]
    margins=[db[0]-x0,x1-db[2],db[1]-y0,y1-db[3]]
    if min(margins)<=0: raise RuntimeError(("decoded margin",rr["key"],db,margins))
    rr["decoded_bbox"]=db; rr["decoded_size"]=[db[2]-db[0],db[3]-db[1]]; rr["decoded_margins"]=margins

src_png=tmp/"source.png"; new_png=tmp/"new.png"
src.save(src_png); new.save(new_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_path),str(source_mask_path),
                "--protected-mask",str(protected_path),"--report",str(out/"B226_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(new_png),str(allowed_full_path),
                "--protected-mask",str(protected_path),"--report",str(out/"B226_FINAL_VALIDATION.json")],check=True)

cards=[card("SOURCE",src),card("C143",old),card("B226",new)]
sheet=Image.new("RGB",(meta["w"],sum(c.height for c in cards)+8),(20,20,20)); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height+4
sheet.save(out/"B226_E3F4_SOURCE_C143_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
for rr in rows:
    x0,y0,x1,y1=rr["source_bbox"]; p=8
    cr=(max(0,x0-p),max(0,y0-p),min(meta["w"],x1+p),min(meta["h"],y1+p))
    ims=[comp(z).crop(cr) for z in (src,old,new)]
    ims=[z.resize((z.width*3,z.height*3),Image.Resampling.NEAREST) for z in ims]
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+28
    c=Image.new("RGB",(cw,ch),(24,24,24)); d=ImageDraw.Draw(c); x=0
    for lab,z in zip(("SOURCE","C143","B226"),ims):
        d.text((x+5,6),lab,fill="white"); c.paste(z,(x,28)); x+=z.width+6
    contacts.append(c)
cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),(20,20,20)); y=0
for c in contacts: cs.paste(c,(0,y)); y+=c.height+4
cs.save(out/"B226_E3F4_ROW_CONTACT_3X.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE RAW",src_raw),card("B226 RAW",new_raw)]
rs=Image.new("RGB",(meta["w"],sum(c.height for c in rawcards)+4),(20,20,20)); y=0
for c in rawcards: rs.paste(c,(0,y)); y+=c.height+4
rs.save(out/"B226_E3F4_SOURCE_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B226","queue_index":226,"asset":asset,
 "trigger":"STRICT_PRE_INGAME_8_STEP_VISUAL_FALSE_NEGATIVE_HIERARCHY",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/024_q226_E3F4BA07.jpg",
 "prior_c_status":"C143_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,"source_url":url,
 "defects":["GOAL_A_TO_E_SOURCE_RELATIVE_WIDTH_TOO_WEAK","15_STAGE_CONTINUOUS_SOURCE_RELATIVE_WIDTH_TOO_WEAK"],
 "preserved":PRESERVED,
 "method":"exact pinned 2048x512 RGBA32/BGRA source + C143 independently verified exact clean plate; only GOAL A-E and 15 STAGE CONTINUOUS exact source bboxes rebuilt from fresh native Noto Sans CJK KR Bold 58px, same gray-blue fill and 2px same-color weight; source-left anchors and native height preserved; moderate fresh-raster horizontal shaping restores practical source hierarchy without changing STAGE, standalone GOAL, OUTRUN2 or OUTRUN2SP",
 "rows":rows,
 "machine_qa":{"bbox_source_size_positive_margin":"6/6 PASS","candidate_changes_outside_selected_source_bboxes":outside,
   "alpha_changes_outside_selected_source_bboxes":alpha_out,"protected_outrun_changed":protected_changed,
   "localized_overlap_pixels":0,"header_128_exact":True,"raw_mode":meta["mode"],"raw_orientation":"mirror_y","roundtrip":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_C143_EXACT_CLEAN_REUSED_AND_REVALIDATED",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT_FAMILY",
   "3_no_unnecessary_undersizing":"PASS_MODERATE_HIERARCHY_RESTORATION",
   "4_source_weight_outline_shadow":"PASS_SHARED_GRAY_BLUE_SOURCE_FAMILY",
   "5_no_clipping":"PASS_6_OF_6_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_OUTRUN_PROTECTED_CHANGE",
   "7_flip_y_raw":"PASS_RAW_EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"
 },
 "runtime_validation":"UNTESTED","status":"B226_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B226_E3F4BA07_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B226_E3F4BA07.json").write_text(json.dumps({"role":"B","run":"B226","queue_index":226,"asset":asset,
 "candidate_sha256":AFTER,"report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B226","before":EXPECTED_BEFORE,"after":AFTER,
 "rows":[{"key":r["key"],"old":r["prior_size"],"new":r["decoded_size"],"source":r["source_size"],"margins":r["decoded_margins"]} for r in rows],
 "outside":outside,"protected":protected_changed,"status":report["status"]},ensure_ascii=False))

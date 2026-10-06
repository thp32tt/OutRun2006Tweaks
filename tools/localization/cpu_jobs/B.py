#!/usr/bin/env python3
# B219: q232 EBFC709F PRE_INGAME false-negative repair.
# C135 passed containment but centered all four Korean headings inside source
# bboxes while the source family is left-anchored; the Regular treatment also
# weakens the large bold hierarchy. Rebuild all four from native HD source.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA219-EBFC709F"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_C/20261005-C135-EBFC709F/EBFC709F_CLEAN_PLATE.png"
source_mask_path=repo/"localization/graphics/role_C/20261005-C135-EBFC709F/EBFC709F_SOURCE_TEXT_MASK.png"
EXPECTED_BEFORE="7404fa227035e2fa003f4fa13f1bd348a050317757d7761c9d638f5fc1a01da4"
SOURCE_SHA="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/Release/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
tmp=Path("/tmp/b219"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

rows=[
 {"key":"join_small","source":"JOIN GAME","ko":"게임 참가","bbox":[14,287,418,350],"old_bbox":[100,289,331,348],"family":"small"},
 {"key":"create_small","source":"CREATE GAME","ko":"게임 만들기","bbox":[898,291,1420,354],"old_bbox":[1019,293,1298,352],"family":"small"},
 {"key":"create_large","source":"CREATE GAME","ko":"게임 만들기","bbox":[24,695,1245,840],"old_bbox":[315,702,954,833],"family":"large"},
 {"key":"join_large","source":"JOIN GAME","ko":"게임 참가","bbox":[9,874,979,1019],"old_bbox":[230,881,757,1012],"family":"large"},
]

def sha(b): return hashlib.sha256(b).hexdigest()
def rect(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def bbox(m):
    ys,xs=np.nonzero(m); return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,1024) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mips":mips,"raw_mode":mode}

sb=src_dds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha(sb)))
if sha(cb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate sha drift",sha(cb)))
src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(cb)
if meta!=ometa or sb[:128]!=cb[:128]: raise RuntimeError("structure/header drift")
clean=Image.open(clean_path).convert("RGBA")
source_mask_img=Image.open(source_mask_path).convert("L")
if clean.size!=src.size or source_mask_img.size!=src.size: raise RuntimeError(("clean/mask size drift",clean.size,source_mask_img.size,src.size))
sa=np.asarray(src); oa=np.asarray(old); ca=np.asarray(clean)
H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool)
for r in rows: allowed|=rect((H,W),r["bbox"])
source_mask=np.asarray(source_mask_img)>0
# C135 independently validated this clean plate. Hidden RGB under alpha=0 is
# intentionally ignored here; visible/alpha preservation is enforced on the
# final decoded DDS against the exact source bboxes.
clean_diff=np.any(sa!=ca,axis=2)
for r in rows:
    x0,y0,x1,y1=r["bbox"]
    if np.count_nonzero(ca[y0:y1,x0:x1,3]): raise RuntimeError(("clean target alpha remains",r["key"]))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Noto CJK Bold unavailable",font_line))

# Sample visible fill family from the current C135 Korean candidate itself, so
# B219 changes placement/weight hierarchy without inventing a new palette.
def sample_fill(ob):
    x0,y0,x1,y1=ob
    p=oa[y0:y1,x0:x1]
    vis=p[p[:, :, 3] >= 220]
    if len(vis)==0: raise RuntimeError(("empty old fill sample",ob))
    # Ignore neutral background-like pixels by taking the dominant high-alpha
    # text population around channel median.
    med=np.median(vis[:,:3],axis=0)
    dist=np.abs(vis[:,:3].astype(np.int16)-med.astype(np.int16)).sum(axis=1)
    sel=vis[dist<=np.percentile(dist,55)]
    rgb=np.median(sel[:,:3],axis=0).round().astype(np.uint8) if len(sel) else med.round().astype(np.uint8)
    return tuple(int(x) for x in rgb)+(255,)

def render(text,fs,fill):
    font=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(4,4),0))
    tb=d.textbbox((0,0),text,font=font,stroke_width=0)
    pad=12
    mask=Image.new("L",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),0)
    ImageDraw.Draw(mask).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255,stroke_width=0)
    bb=mask.getbbox()
    if not bb: raise RuntimeError(("empty render",text,fs))
    mask=mask.crop(bb)
    tile=Image.new("RGBA",mask.size,fill); tile.putalpha(mask)
    return tile

MARGIN=2
final=src.copy()
# Apply only the C135-validated clean pixels inside the four exact source
# heading bboxes so every unrelated/explanatory source pixel remains exact.
for _r in rows:
    _x0,_y0,_x1,_y1=_r["bbox"]
    final.paste(clean.crop((_x0,_y0,_x1,_y1)),(_x0,_y0))
target=np.zeros((H,W),bool); reports=[]
for r in rows:
    b=r["bbox"]; aw=b[2]-b[0]; ah=b[3]-b[1]; fill=sample_fill(r["old_bbox"])
    best=None
    for fs in range(180,30,-1):
        t=render(r["ko"],fs,fill)
        if t.width<=aw-2*MARGIN and t.height<=ah-2*MARGIN:
            best=(fs,t); break
    if best is None: raise RuntimeError(("fit failed",r["key"]))
    fs,tile=best
    # Source headings are left anchored. This is the material fix versus C135,
    # which centered all four replacements inside the exact source bboxes.
    px=b[0]+MARGIN
    py=b[1]+(ah-tile.height)//2
    if py<=b[1]: py=b[1]+MARGIN
    if py+tile.height>=b[3]: py=b[3]-MARGIN-tile.height
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    lb=bbox(lm); margins=[lb[0]-b[0],b[2]-lb[2],lb[1]-b[1],b[3]-lb[3]]
    if min(margins)<=0: raise RuntimeError(("positive margin fail",r["key"],lb,b,margins))
    final.alpha_composite(layer); target|=lm
    oldsz=[r["old_bbox"][2]-r["old_bbox"][0],r["old_bbox"][3]-r["old_bbox"][1]]
    nsz=[lb[2]-lb[0],lb[3]-lb[1]]
    reports.append({**r,"source_size":[aw,ah],"old_size":oldsz,"localized_bbox":lb,"localized_size":nsz,
      "margins":margins,"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":fs,
      "fill_rgba":list(fill),"alignment":"source_left","height_utilization":round(nsz[1]/ah,4),
      "width_gain_px":nsz[0]-oldsz[0],"height_gain_px":nsz[1]-oldsz[1],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

# Exact non-target protection and no row overlap/touch.
for i in range(len(rows)):
    mi=target & rect((H,W),rows[i]["bbox"])
    for j in range(i+1,len(rows)):
        mj=target & rect((H,W),rows[j]["bbox"])
        if np.count_nonzero(mi & mj): raise RuntimeError(("localized overlap",i,j))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["raw_mode"])
candidate.write_bytes(payload)
after=sha(payload)
new_raw,new,nmeta=decode(payload)
if nmeta!=meta or payload[:128]!=sb[:128] or ImageChops.difference(new,final).getbbox() is not None:
    raise RuntimeError("roundtrip/header failure")
na=np.asarray(new)
diff=np.any(sa!=na,axis=2)
outside=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=na[:,:,3]) & ~allowed))
if outside or alpha_out: raise RuntimeError(("outside gate",outside,alpha_out))

# Evidence.
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    v=comp(im).resize((1024,512),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(1024,540),(25,25,25)); c.paste(v,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
cards=[card("SOURCE",src),card("C135",old),card("C135 CLEAN",clean),card("B219 LEFT-ANCHOR BOLD",new)]
sheet=Image.new("RGB",(2048,1080),(22,22,22))
sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(1024,0));sheet.paste(cards[2],(0,540));sheet.paste(cards[3],(1024,540))
sheet.save(out/"B219_EBFC_SOURCE_C135_CLEAN_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

src_c,old_c,new_c=comp(src),comp(old),comp(new)
contacts=[]
for r in reports:
    x0,y0,x1,y1=r["bbox"]; p=12; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[im.crop(cr) for im in (src_c,old_c,new_c)]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+28),(25,25,25))
    d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","C135","B219"),ims):
        d.text((xx+4,5),lab,fill="white"); c.paste(z,(xx,26)); xx+=z.width+6
    contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+6*(len(contacts)-1)),(22,22,22))
yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+6
rs.thumbnail((2400,5000),Image.Resampling.LANCZOS); rs.save(out/"B219_EBFC_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

rawsheet=Image.new("RGB",(2048,540),(22,22,22))
rawsheet.paste(card("SOURCE RAW",src_raw),(0,0)); rawsheet.paste(card("B219 RAW",new_raw),(1024,0))
rawsheet.save(out/"B219_EBFC_SOURCE_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B219","queue_index":232,"asset":asset,
 "trigger":"MANUAL_PRE_INGAME_8_STEP_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/060_q232_EBFC709F.jpg",
 "prior_c_status":"C135_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["SOURCE_LEFT_ALIGNMENT_MISMATCH","SOURCE_WEIGHT_HIERARCHY_WEAKENED"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "method":"exact pinned source + C135 independently validated clean plate; fresh native Noto Sans CJK KR Bold; maximum safe per-row height; source-left anchor; C135-visible palette retained; no bitmap upscaling",
 "rows":reports,
 "machine_qa":{"bbox_size_positive_margin":"4/4 PASS","changed_outside_exact_source_bboxes":outside,
   "alpha_changed_outside_exact_source_bboxes":alpha_out,"clean_plate_provenance":"C135_INDEPENDENT_VALIDATED",
   "header_128_exact":True,"raw_mode":meta["raw_mode"],"raw_orientation":"mirror_y"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_INHERITED_C135_INDEPENDENT_CLEAN_PLATE",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT",
   "3_no_unnecessary_undersizing":"PASS_MAX_SAFE_HEIGHT_PER_ROW",
   "4_source_weight_effect":"PASS_NATIVE_BOLD_FLAT_SOURCE_FAMILY_PENDING_CONTROLLER",
   "5_no_clipping":"PASS_4_OF_4_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_FINAL_CHANGE_OUTSIDE_EXACT_SOURCE_BBOXES",
   "7_flip_y_raw":"PASS_EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"
 },
 "runtime_validation":"UNTESTED","status":"B219_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B219_EBFC709F_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B219_EBFC709F.json").write_text(json.dumps({"role":"B","run":"B219","queue_index":232,"asset":asset,
 "candidate_sha256":after,"report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B219","before":EXPECTED_BEFORE,"after":after,
 "rows":[{"key":r["key"],"bbox":r["localized_bbox"],"size":r["localized_size"],"height_utilization":r["height_utilization"],"font_size":r["font_size"]} for r in reports],
 "status":report["status"]},ensure_ascii=False))

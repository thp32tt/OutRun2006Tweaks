#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("Run only in GitHub-hosted localization CPU worker as role C.")

repo=Path.cwd()
run="20261004-1820-C93"
outdir=repo/"localization/graphics/role_C"/run
outdir.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_rgba32_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(f"not DDS: {p}")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; depth=struct.unpack_from("<I",b,24)[0]
    mips=struct.unpack_from("<I",b,28)[0]; pf=struct.unpack_from("<I",b,80)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bpp!=32 or pitch!=w*4 or mips!=1 or masks!=(0xff,0xff00,0xff0000,0xff000000):
        raise RuntimeError(("unexpected RGBA32 layout",str(p),w,h,pitch,depth,mips,pf,fourcc,bpp,masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("size mismatch",str(p),len(b),128+w*h*4))
    raw=np.frombuffer(b,dtype=np.uint8,offset=128).reshape(h,w,4).copy()
    read=np.flipud(raw).copy()
    meta={"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"pf_flags":pf,
          "fourcc":"00000000","bpp":bpp,"masks":[hex(x) for x in masks],"bytes":len(b)}
    return b[:128],raw,read,meta

def load_png_rgba(path,size):
    im=Image.open(path).convert("RGBA")
    if im.size!=size: raise RuntimeError(("PNG size mismatch",str(path),im.size,size))
    return np.asarray(im,dtype=np.uint8).copy()

def load_mask(path,size):
    im=Image.open(path).convert("L")
    if im.size!=size: raise RuntimeError(("mask size mismatch",str(path),im.size,size))
    return np.asarray(im,dtype=np.uint8)>0

def bb(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def gate(src,cand,edit,protected):
    diff=np.any(src!=cand,axis=2); adiff=src[:,:,3]!=cand[:,:,3]
    return {
      "changed_pixels":int(diff.sum()),"changed_bbox":bb(diff),
      "changed_pixels_outside_edit_mask":int(np.logical_and(diff,np.logical_not(edit)).sum()),
      "changed_pixels_in_protected_mask":int(np.logical_and(diff,protected).sum()),
      "alpha_changed_outside_edit_mask":int(np.logical_and(adiff,np.logical_not(edit)).sum())
    }

def card(arr,label,maxw=760,maxh=760):
    im=Image.fromarray(arr,"RGBA")
    bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
    v=bg.convert("RGB"); v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+26),"white"); c.paste(v,(0,26))
    ImageDraw.Draw(c).text((5,5),label,fill="black",font=ImageFont.load_default())
    return c

def save_compare(name,arrays):
    cards=[card(arr,label) for label,arr in arrays]
    gap=8; cols=3
    rows=(len(cards)+cols-1)//cols
    widths=[max([cards[i].width for i in range(c,len(cards),cols)] or [1]) for c in range(cols)]
    rowhs=[max(cards[i].height for i in range(r*cols,min((r+1)*cols,len(cards)))) for r in range(rows)]
    sheet=Image.new("RGB",(sum(widths)+gap*(cols-1),sum(rowhs)+gap*(rows-1)),"white")
    y=0
    for r in range(rows):
        x=0
        for c in range(cols):
            i=r*cols+c
            if i<len(cards): sheet.paste(cards[i],(x,y))
            x+=widths[c]+gap
        y+=rowhs[r]+gap
    sheet.save(outdir/name,quality=94)

def save_rows(name,src,clean,final,rows):
    strips=[]; font=ImageFont.load_default()
    for row in rows:
        ob=[int(x) for x in row["original_bbox"]]
        pad=10; cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.shape[1],ob[2]+pad),min(src.shape[0],ob[3]+pad))
        cs=[]
        for label,arr in (("SOURCE",src),("CLEAN",clean),("FINAL",final)):
            im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
            v=bg.convert("RGB").crop(cr); v.thumbnail((500,170),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(520,202),"white"); c.paste(v,((520-v.width)//2,27+(170-v.height)//2))
            ImageDraw.Draw(c).text((4,4),f'{row["key"]} {label}',fill="black",font=font); cs.append(c)
        strip=Image.new("RGB",(1572,202),"white")
        for i,c in enumerate(cs): strip.paste(c,(i*526,0))
        strips.append(strip)
    sheet=Image.new("RGB",(1572,202*len(strips)),"white")
    y=0
    for s in strips: sheet.paste(s,(0,y)); y+=202
    sheet.save(outdir/name,quality=95)

results=[]

# ---- A_RECOVERY08 / FD90AA9 ----
a8=json.loads((repo/"localization/graphics/role_A/20261004-A-RECOVERY08/A_RECOVERY08_FD90AA9_REPORT.json").read_text(encoding="utf-8"))
a7=json.loads((repo/"localization/graphics/role_A/20261004-A-RECOVERY07/A_RECOVERY07_FD90AA9_REPORT.json").read_text(encoding="utf-8"))
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
if sha(source)!="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e": raise RuntimeError("FD90 source SHA mismatch")
if sha(candidate)!="0b7a3138c140617a90207f63eb580c18e953a241951d4832867e8e3ce184338b": raise RuntimeError("FD90 A08 candidate SHA mismatch")
sh,sraw,src,smeta=load_rgba32_dds(source); ch,craw,final,cmeta=load_rgba32_dds(candidate)
if sh!=ch or smeta!=cmeta: raise RuntimeError("FD90 A08 structure/header drift")
size=(smeta["width"],smeta["height"])
clean=load_png_rgba(repo/"localization/graphics/role_A/20261004-A-RECOVERY08/FD90AA9_CLEAN_PLATE_RECOVERY08.png",size)
source_mask=load_mask(repo/"localization/graphics/role_A/20261004-A-RECOVERY08/FD90AA9_SOURCE_TEXT_MASK_RECOVERY08.png",size)
clean_protected=load_mask(repo/"localization/graphics/role_A/20261004-A-RECOVERY08/FD90AA9_CLEAN_PLATE_PROTECTED_MASK_RECOVERY08.png",size)
allowed=load_mask(repo/"localization/graphics/role_A/20261004-A-RECOVERY07/FD90AA9_ALLOWED_TEXT_REGION_MASK.png",size)
final_protected=load_mask(repo/"localization/graphics/role_A/20261004-A-RECOVERY07/FD90AA9_PROTECTED_MASK.png",size)
cg=gate(src,clean,source_mask,clean_protected); fg=gate(src,final,allowed,final_protected)
if any((cg["changed_pixels_outside_edit_mask"],cg["changed_pixels_in_protected_mask"],cg["alpha_changed_outside_edit_mask"],
        fg["changed_pixels_outside_edit_mask"],fg["changed_pixels_in_protected_mask"],fg["alpha_changed_outside_edit_mask"])):
    raise RuntimeError(("FD90 A08 mask gate fail",cg,fg))

# Recover exact A07 input candidate at A08 base to independently verify only four returned bboxes changed.
prior_path=Path("/tmp/C93_FD90_A07_INPUT.dds")
with prior_path.open("wb") as fp:
    subprocess.run(["git","show",f'{a8["base_head"]}:localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds'],stdout=fp,check=True)
if sha(prior_path)!=a8["input_candidate_sha256"]: raise RuntimeError("FD90 prior candidate history SHA mismatch")
ph,praw,prior,pmeta=load_rgba32_dds(prior_path)
if ph!=sh or pmeta!=smeta: raise RuntimeError("FD90 prior structure drift")
four=np.zeros((smeta["height"],smeta["width"]),dtype=bool)
a8_by={r["key"]:r for r in a8["reworked_rows"]}
for r in a8["reworked_rows"]:
    x0,y0,x1,y1=map(int,r["original_bbox"]); four[y0:y1,x0:x1]=True
diff_prior=np.any(prior!=final,axis=2); alpha_prior=prior[:,:,3]!=final[:,:,3]
outside4=int(np.logical_and(diff_prior,np.logical_not(four)).sum())
alpha_out4=int(np.logical_and(alpha_prior,np.logical_not(four)).sum())
if outside4 or alpha_out4: raise RuntimeError(("FD90 changed outside four return bboxes",outside4,alpha_out4))

# Full 29-row bbox gate: A08 rows override A07 rows; independently derive final-vs-clean footprint inside each original bbox.
a7_rows=a7["rows"]
rows=[]; edge=[]
target=np.any(final!=clean,axis=2)
for old in a7_rows:
    base=dict(old); key=old["key"]
    if key in a8_by: base.update(a8_by[key])
    ob=list(map(int,base["original_bbox"])); reported=list(map(int,base["localized_bbox"]))
    if not (reported[0]>=ob[0] and reported[1]>=ob[1] and reported[2]<=ob[2] and reported[3]<=ob[3]):
        raise RuntimeError(("FD90 reported bbox fail",key,ob,reported))
    local=np.zeros_like(target); local[ob[1]:ob[3],ob[0]:ob[2]]=target[ob[1]:ob[3],ob[0]:ob[2]]
    derived=bb(local)
    if derived is None: raise RuntimeError(("FD90 no target diff",key))
    if not (derived[0]>=ob[0] and derived[1]>=ob[1] and derived[2]<=ob[2] and derived[3]<=ob[3]):
        raise RuntimeError(("FD90 derived bbox fail",key,ob,derived))
    d=[reported[0]-ob[0],ob[2]-reported[2],reported[1]-ob[1],ob[3]-reported[3]]
    if min(d)==0: edge.append(key)
    rows.append({"key":key,"original_bbox":ob,"localized_bbox":reported,"derived_final_vs_clean_bbox":derived,
                 "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
                 "containment":"PASS","rework_status":base.get("rework_status")})
save_compare("C93_FD90AA9_FULL_COMPARE.jpg",[("SOURCE_READABLE",src),("CLEAN_READABLE",clean),("PRIOR_A07_READABLE",prior),
                                                   ("FINAL_A08_READABLE",final),("SOURCE_RAW",sraw),("FINAL_A08_RAW",craw)])
save_rows("C93_FD90AA9_REWORK_ROWS.jpg",src,clean,final,[r for r in rows if r["key"] in a8_by])
results.append({
 "asset":"FD90AA9","producer":"A_RECOVERY08","source_sha256":sha(source),"candidate_sha256":sha(candidate),
 "structure":{**smeta,"header_128_exact_to_source":True,"raw_orientation":"mirror_y"},
 "clean_plate_gate":{**cg,"status":"PASS"},"final_gate":{**fg,"status":"PASS"},
 "return_scope_gate":{"changed_pixels_vs_A07_outside_four_return_bboxes":outside4,"alpha_changed_pixels_outside_four_return_bboxes":alpha_out4,"status":"PASS"},
 "bbox_gate":{"elements":len(rows),"pass":len(rows),"fail":0,"edge_touch_keys":edge,"rows":rows,"status":"PASS"},
 "visual_evidence":{"full_compare":f"localization/graphics/role_C/{run}/C93_FD90AA9_FULL_COMPARE.jpg",
                    "rework_rows":f"localization/graphics/role_C/{run}/C93_FD90AA9_REWORK_ROWS.jpg","controller_visual_qa":"PENDING"},
 "runtime_validation":"UNTESTED","status":"C93_STATIC_MACHINE_PASS_PENDING_CONTROLLER_VISUAL_QA"
})

# ---- B_RECOVERY07 / B1696633 ----
b7=json.loads((repo/"localization/graphics/role_B/20261004-B-RECOVERY07/B_RECOVERY07_B1696633_REPORT.json").read_text(encoding="utf-8"))
bsrc=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds"
if not bsrc.exists():
    bsrc=Path("/tmp/C93_B1696633_SOURCE.dds")
    urllib.request.urlretrieve(b7["source_url"],bsrc)
bcand=repo/b7["candidate_path"]
if sha(bsrc)!=b7["source_sha256"]: raise RuntimeError("B169 source SHA mismatch")
if sha(bcand)!=b7["candidate_sha256"]: raise RuntimeError("B169 candidate SHA mismatch")
bh,braw,bsrc_read,bmeta=load_rgba32_dds(bsrc); bch,bcraw,bfinal,bcmeta=load_rgba32_dds(bcand)
if bh!=bch or bmeta!=bcmeta: raise RuntimeError("B169 structure/header drift")
bsize=(bmeta["width"],bmeta["height"])
bclean=load_png_rgba(repo/"localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_CLEAN_PLATE.png",bsize)
bsource_mask=load_mask(repo/"localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_SOURCE_TEXT_MASK.png",bsize)
bprotected=load_mask(repo/"localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_PROTECTED_MASK.png",bsize)
ballowed=load_mask(repo/"localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_ALLOWED_TEXT_REGION_MASK.png",bsize)
bcg=gate(bsrc_read,bclean,bsource_mask,bprotected); bfg=gate(bsrc_read,bfinal,ballowed,bprotected)
if any((bcg["changed_pixels_outside_edit_mask"],bcg["changed_pixels_in_protected_mask"],bcg["alpha_changed_outside_edit_mask"],
        bfg["changed_pixels_outside_edit_mask"],bfg["changed_pixels_in_protected_mask"],bfg["alpha_changed_outside_edit_mask"])):
    raise RuntimeError(("B169 mask gate fail",bcg,bfg))
btarget=np.any(bfinal!=bclean,axis=2)
brows=[]; bedge=[]
for r in b7["rows"]:
    ob=list(map(int,r["original_bbox"])); reported=list(map(int,r["localized_bbox"]))
    if not (reported[0]>=ob[0] and reported[1]>=ob[1] and reported[2]<=ob[2] and reported[3]<=ob[3]):
        raise RuntimeError(("B169 reported bbox fail",r["key"],ob,reported))
    local=np.zeros_like(btarget); local[ob[1]:ob[3],ob[0]:ob[2]]=btarget[ob[1]:ob[3],ob[0]:ob[2]]
    derived=bb(local)
    if derived is None: raise RuntimeError(("B169 no target diff",r["key"]))
    if not (derived[0]>=ob[0] and derived[1]>=ob[1] and derived[2]<=ob[2] and derived[3]<=ob[3]):
        raise RuntimeError(("B169 derived bbox fail",r["key"],ob,derived))
    d=[reported[0]-ob[0],ob[2]-reported[2],reported[1]-ob[1],ob[3]-reported[3]]
    if min(d)==0: bedge.append(r["key"])
    brows.append({"key":r["key"],"source":r["source"],"korean":r["korean"],"original_bbox":ob,"localized_bbox":reported,
                  "derived_final_vs_clean_bbox":derived,"delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
                  "containment":"PASS","rework_status":r.get("rework_status")})
save_compare("C93_B1696633_FULL_COMPARE.jpg",[("SOURCE_READABLE",bsrc_read),("CLEAN_READABLE",bclean),("FINAL_READABLE",bfinal),
                                                     ("SOURCE_RAW",braw),("FINAL_RAW",bcraw)])
save_rows("C93_B1696633_ROW_CONTACT.jpg",bsrc_read,bclean,bfinal,brows)
results.append({
 "asset":"B1696633","producer":"B_RECOVERY07","source_sha256":sha(bsrc),"candidate_sha256":sha(bcand),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"a95efe01d1f136514cef94b0d9e9fd61df021754",
                      "mode":"pinned_upstream_fallback_if_not_repo_committed"},
 "structure":{**bmeta,"header_128_exact_to_source":True,"raw_orientation":"mirror_y"},
 "clean_plate_gate":{**bcg,"status":"PASS"},"final_gate":{**bfg,"status":"PASS"},
 "bbox_gate":{"elements":len(brows),"pass":len(brows),"fail":0,"edge_touch_keys":bedge,"rows":brows,"status":"PASS"},
 "visual_evidence":{"full_compare":f"localization/graphics/role_C/{run}/C93_B1696633_FULL_COMPARE.jpg",
                    "row_contact":f"localization/graphics/role_C/{run}/C93_B1696633_ROW_CONTACT.jpg","controller_visual_qa":"PENDING"},
 "runtime_validation":"UNTESTED","status":"C93_STATIC_MACHINE_PASS_PENDING_CONTROLLER_VISUAL_QA"
})

summary={"schema_version":1,"role":"C","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
         "scope":"new/changed A_RECOVERY08 FD90AA9 and B_RECOVERY07 B1696633 only; completed C90-C92 assets not repeated",
         "assets":results,"summary":{"assets_checked":2,"static_machine_pass":2,"static_machine_fail":0,
                                      "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False}}
(outdir/"C93_CROSS_LANE_STATIC_QA.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C93_STATIC_QA_DONE",[(x["asset"],x["candidate_sha256"]) for x in results])

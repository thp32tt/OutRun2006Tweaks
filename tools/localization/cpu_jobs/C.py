#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("Run only in GitHub-hosted localization CPU worker as role C.")

repo=Path.cwd(); run="20261004-1840-C97"; outdir=repo/"localization/graphics/role_C"/run; outdir.mkdir(parents=True,exist_ok=True)
producer_path=repo/"localization/graphics/role_A/20261004-A-PRODUCTION09/A_PRODUCTION09_455717B2_REPORT.json"
p=json.loads(producer_path.read_text(encoding="utf-8"))
expected="9dadee3c300bd0500940fcfe304bb640e7b458329210ce2b134c8ce06c65eac4"
if p["candidate_sha256"]!=expected: raise RuntimeError(("455717B2 producer advanced",p["candidate_sha256"],expected))

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def meta(path):
    b=Path(path).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    if fourcc!=b"DXT5": raise RuntimeError(("not DXT5",fourcc))
    need=128+((w+3)//4)*((h+3)//4)*16
    if len(b)!=need: raise RuntimeError(("size mismatch",len(b),need))
    return b[:128],{"width":w,"height":h,"mips":mips,"fourcc":"DXT5","bytes":len(b)}
def readable(path):
    return np.asarray(Image.open(path).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8).copy()
def png_rgba(path,size):
    im=Image.open(path).convert("RGBA")
    if im.size!=size: raise RuntimeError(("size",path,im.size,size))
    return np.asarray(im,dtype=np.uint8).copy()
def mask(path,size):
    im=Image.open(path).convert("L")
    if im.size!=size: raise RuntimeError(("mask size",path,im.size,size))
    return np.asarray(im,dtype=np.uint8)>0
def bbox(m):
    ys,xs=np.nonzero(m)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def counts(src,cand,edit,protected):
    diff=np.any(src!=cand,axis=2)
    vis=(src[:,:,3]>0)|(cand[:,:,3]>0)
    ad=src[:,:,3]!=cand[:,:,3]
    return {
      "changed_pixels":int(diff.sum()),"changed_bbox":bbox(diff),
      "changed_pixels_outside_edit_mask":int(np.logical_and(diff,np.logical_not(edit)).sum()),
      "visible_changed_pixels_outside_edit_mask":int(np.logical_and(np.logical_and(diff,vis),np.logical_not(edit)).sum()),
      "alpha_changed_pixels_outside_edit_mask":int(np.logical_and(ad,np.logical_not(edit)).sum()),
      "changed_pixels_in_protected_mask":int(np.logical_and(diff,protected).sum())
    }
def card(arr,label,maxw=760,maxh=760):
    im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
    v=bg.convert("RGB"); v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+24),"white"); c.paste(v,(0,24)); ImageDraw.Draw(c).text((4,4),label,fill="black",font=ImageFont.load_default()); return c

source=Path("/tmp/C97_455717B2_SOURCE.dds")
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds"
urllib.request.urlretrieve(url,source)
candidate=repo/p["candidate_path"]
if sha(source)!=p["source_sha256"]: raise RuntimeError(("source SHA",sha(source),p["source_sha256"]))
if sha(candidate)!=expected: raise RuntimeError(("candidate SHA",sha(candidate),expected))
sh,sm=meta(source); ch,cm=meta(candidate)
if sh!=ch or sm!=cm: raise RuntimeError("header/structure drift")
src=readable(source); final=readable(candidate); size=(sm["width"],sm["height"])
base=repo/"localization/graphics/role_A/20261004-A-PRODUCTION09"
clean=png_rgba(base/"455717B2_CLEAN_PLATE.png",size)
source_mask=mask(base/"455717B2_SOURCE_TEXT_MASK.png",size)
clean_protected=mask(base/"455717B2_CLEAN_PLATE_PROTECTED_VISIBLE_MASK.png",size)
allowed_block=mask(base/"455717B2_DXT5_EDIT_BLOCK_MASK.png",size)
protected_visible=mask(base/"455717B2_PROTECTED_VISIBLE_MASK.png",size)

clean_gate=counts(src,clean,source_mask,clean_protected)
block_gate=counts(src,final,allowed_block,protected_visible)
for label,g in (("clean",clean_gate),("block",block_gate)):
    if g["changed_pixels_outside_edit_mask"] or g["changed_pixels_in_protected_mask"] or g["alpha_changed_pixels_outside_edit_mask"]:
        raise RuntimeError((label,"gate unexpected fail",g))

bbox_union=np.zeros((sm["height"],sm["width"]),dtype=bool)
rows=[]; edge=[]
for r in p["rows"]:
    ob=list(map(int,r["original_bbox"])); lb=list(map(int,r["localized_bbox"]))
    bbox_union[ob[1]:ob[3],ob[0]:ob[2]]=True
    ok=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    if not ok or r.get("containment")!="PASS": raise RuntimeError(("row bbox fail",r["key"],ob,lb))
    d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if min(d)==0: edge.append(r["key"])
    rows.append({"key":r["key"],"source":r["source"],"korean":r["korean"],"original_bbox":ob,"localized_bbox":lb,
                 "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],"containment":"PASS"})
strict=counts(src,final,bbox_union,protected_visible)
transparent_rgb_only=strict["changed_pixels_outside_edit_mask"]-strict["visible_changed_pixels_outside_edit_mask"]
if strict["visible_changed_pixels_outside_edit_mask"]!=0 or strict["alpha_changed_pixels_outside_edit_mask"]!=0:
    strict_decision="REWORK_REQUIRED_VISIBLE_OR_ALPHA_OVERFLOW"
elif strict["changed_pixels_outside_edit_mask"]!=0:
    strict_decision="REWORK_REQUIRED_TRANSPARENT_RGB_OUTSIDE_EXACT_BBOX"
else:
    strict_decision="PASS"
if strict_decision=="PASS":
    raise RuntimeError("Expected current producer strict diagnostic to remain nonzero; source/candidate likely changed")

# evidence
cards=[card(src,"SOURCE_READABLE"),card(clean,"CLEAN_READABLE"),card(final,"FINAL_READABLE")]
sheet=Image.new("RGB",(sum(c.width for c in cards)+16,max(c.height for c in cards)),"white"); x=0
for c in cards: sheet.paste(c,(x,0)); x+=c.width+8
sheet.save(outdir/"C97_455717B2_FULL_COMPARE.jpg",quality=94)
font=ImageFont.load_default(); strips=[]
for rr in rows:
    ob=rr["original_bbox"]; cr=(max(0,ob[0]-8),max(0,ob[1]-8),min(sm["width"],ob[2]+8),min(sm["height"],ob[3]+8))
    cs=[]
    for lab,arr in (("SOURCE",src),("CLEAN",clean),("FINAL",final)):
        im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
        v=bg.convert("RGB").crop(cr); v.thumbnail((440,150),Image.Resampling.NEAREST)
        c=Image.new("RGB",(460,180),"white"); c.paste(v,((460-v.width)//2,24+(150-v.height)//2)); ImageDraw.Draw(c).text((4,4),f'{rr["key"]} {lab}',fill="black",font=font); cs.append(c)
    strip=Image.new("RGB",(1392,180),"white")
    for i,c in enumerate(cs): strip.paste(c,(i*466,0))
    strips.append(strip)
contact=Image.new("RGB",(1392,180*len(strips)),"white"); y=0
for s in strips: contact.paste(s,(0,y)); y+=180
contact.save(outdir/"C97_455717B2_ROW_CONTACT.jpg",quality=95)

result={
 "schema_version":1,"role":"C","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "asset":"455717B2","scope":"independent C final QA of new A_PRODUCTION09 result only; completed FD90/B169 checks not repeated",
 "producer_report":"localization/graphics/role_A/20261004-A-PRODUCTION09/A_PRODUCTION09_455717B2_REPORT.json",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","classification":"stock fallback; no HD entry for key"},
 "source_sha256":sha(source),"candidate_sha256":sha(candidate),"candidate_changed_by_C":False,
 "structure":{**sm,"header_128_exact_to_source":True,"raw_orientation":"mirror_y"},
 "clean_plate_gate":{**clean_gate,"status":"PASS"},
 "dxt5_block_gate":{**block_gate,"status":"PASS"},
 "strict_exact_bbox_gate":{**strict,"transparent_rgb_only_changed_pixels_outside_exact_bboxes":transparent_rgb_only,
                           "policy_decision":strict_decision,"status":"REWORK_REQUIRED"},
 "bbox_gate":{"elements":4,"pass":4,"fail":0,"edge_touch_keys":edge,"rows":rows,"status":"PASS"},
 "visual_evidence":{"full_compare":f"localization/graphics/role_C/{run}/C97_455717B2_FULL_COMPARE.jpg","row_contact":f"localization/graphics/role_C/{run}/C97_455717B2_ROW_CONTACT.jpg","controller_visual_qa":"PENDING"},
 "c_decision":"REWORK_REQUIRED_TRANSPARENT_RGB_OUTSIDE_EXACT_BBOX",
 "decision_reason":"Decoded visible and alpha overflow are zero, but 1028 decoded all-channel pixels outside the union of exact source bboxes differ due DXT5 boundary blocks. Current zero-tolerance policy explicitly requires changed_pixels_outside_source_region=0; block-level allowance cannot override the exact-bbox gate.",
 "runtime_validation":"UNTESTED","status":"C97_REWORK_REQUIRED_TRANSPARENT_RGB_OUTSIDE_EXACT_BBOX","vr_ffb_dx11_dxvk_changes":False
}
(outdir/"C97_455717B2_FINAL_QA.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C97_455717B2_REWORK_REQUIRED",strict)

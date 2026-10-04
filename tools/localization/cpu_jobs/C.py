#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("Run only in GitHub-hosted localization CPU worker as role C.")

repo=Path.cwd(); run="20261004-1828-C94"; outdir=repo/"localization/graphics/role_C"/run; outdir.mkdir(parents=True,exist_ok=True)
report_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY07/B_RECOVERY07_B1696633_REPORT.json"
b=json.loads(report_path.read_text(encoding="utf-8"))
expected="45bf5ee4f7b18bee4a926f6811c4234192fd540b59c22a52ae0f3bf6e10cbae9"
if b["candidate_sha256"]!=expected: raise RuntimeError(("B169 report advanced again",b["candidate_sha256"],expected))

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
    data=Path(p).read_bytes()
    h=struct.unpack_from("<I",data,12)[0]; w=struct.unpack_from("<I",data,16)[0]; pitch=struct.unpack_from("<I",data,20)[0]
    depth=struct.unpack_from("<I",data,24)[0]; mips=struct.unpack_from("<I",data,28)[0]; pf=struct.unpack_from("<I",data,80)[0]
    fourcc=data[84:88]; bpp=struct.unpack_from("<I",data,88)[0]; masks=struct.unpack_from("<IIII",data,92)
    if data[:4]!=b"DDS " or fourcc!=b"\0\0\0\0" or bpp!=32 or pitch!=w*4 or mips!=1 or masks!=(0xff,0xff00,0xff0000,0xff000000):
        raise RuntimeError(("unexpected DDS layout",str(p),w,h,pitch,depth,mips,pf,fourcc,bpp,masks))
    if len(data)!=128+w*h*4: raise RuntimeError(("DDS size",len(data),128+w*h*4))
    raw=np.frombuffer(data,dtype=np.uint8,offset=128).reshape(h,w,4).copy()
    return data[:128],raw,np.flipud(raw).copy(),{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"pf_flags":pf,"fourcc":"00000000","bpp":bpp,"masks":[hex(x) for x in masks],"bytes":len(data)}
def png_rgba(p,size):
    im=Image.open(p).convert("RGBA")
    if im.size!=size: raise RuntimeError(("PNG size",str(p),im.size,size))
    return np.asarray(im,dtype=np.uint8).copy()
def mask(p,size):
    im=Image.open(p).convert("L")
    if im.size!=size: raise RuntimeError(("mask size",str(p),im.size,size))
    return np.asarray(im,dtype=np.uint8)>0
def bbox(m):
    ys,xs=np.nonzero(m)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def gate(src,cand,edit,protected):
    d=np.any(src!=cand,axis=2); a=src[:,:,3]!=cand[:,:,3]
    return {"changed_pixels":int(d.sum()),"changed_bbox":bbox(d),
            "changed_pixels_outside_edit_mask":int(np.logical_and(d,np.logical_not(edit)).sum()),
            "changed_pixels_in_protected_mask":int(np.logical_and(d,protected).sum()),
            "alpha_changed_outside_edit_mask":int(np.logical_and(a,np.logical_not(edit)).sum())}
def card(arr,label,maxw=900,maxh=900):
    im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
    v=bg.convert("RGB"); v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+26),"white"); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="black",font=ImageFont.load_default()); return c

source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds"
if not source.exists():
    source=Path("/tmp/C94_B1696633_SOURCE.dds"); urllib.request.urlretrieve(b["source_url"],source)
candidate=repo/b["candidate_path"]
if sha(source)!=b["source_sha256"]: raise RuntimeError("source SHA mismatch")
if sha(candidate)!=expected: raise RuntimeError(("candidate SHA mismatch",sha(candidate),expected))
sh,sraw,src,smeta=load_dds(source); ch,craw,final,cmeta=load_dds(candidate)
if sh!=ch or smeta!=cmeta: raise RuntimeError("header/structure drift")
size=(smeta["width"],smeta["height"])
base=repo/"localization/graphics/role_B/20261004-B-RECOVERY07"
clean=png_rgba(base/"B1696633_CLEAN_PLATE.png",size)
sm=mask(base/"B1696633_SOURCE_TEXT_MASK.png",size); pm=mask(base/"B1696633_PROTECTED_MASK.png",size); allowed=mask(base/"B1696633_ALLOWED_TEXT_REGION_MASK.png",size)
cg=gate(src,clean,sm,pm); fg=gate(src,final,allowed,pm)
if any((cg["changed_pixels_outside_edit_mask"],cg["changed_pixels_in_protected_mask"],cg["alpha_changed_outside_edit_mask"],
        fg["changed_pixels_outside_edit_mask"],fg["changed_pixels_in_protected_mask"],fg["alpha_changed_outside_edit_mask"])):
    raise RuntimeError(("mask gate fail",cg,fg))
target=np.any(final!=clean,axis=2)
rows=[]; edge=[]
for r in b["rows"]:
    ob=list(map(int,r["original_bbox"])); lb=list(map(int,r["localized_bbox"]))
    if not (lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]): raise RuntimeError(("reported bbox fail",r["key"],ob,lb))
    local=np.zeros_like(target); local[ob[1]:ob[3],ob[0]:ob[2]]=target[ob[1]:ob[3],ob[0]:ob[2]]
    db=bbox(local)
    if db is None or not (db[0]>=ob[0] and db[1]>=ob[1] and db[2]<=ob[2] and db[3]<=ob[3]): raise RuntimeError(("derived bbox fail",r["key"],ob,db))
    d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if min(d)==0: edge.append(r["key"])
    rows.append({"key":r["key"],"source":r["source"],"korean":r["korean"],"original_bbox":ob,"localized_bbox":lb,"derived_final_vs_clean_bbox":db,
                 "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],"containment":"PASS"})
# clean/allowed/protected consistency
if int(np.logical_and(sm,pm).sum()) or int(np.logical_and(allowed,pm).sum()): raise RuntimeError("mask overlap")
# visual evidence
cards=[card(src,"SOURCE_READABLE"),card(clean,"CLEAN_READABLE"),card(final,"FINAL_READABLE"),card(sraw,"SOURCE_RAW"),card(craw,"FINAL_RAW")]
gap=8; top=cards[:3]; bot=cards[3:]; tw=sum(x.width for x in top)+gap*2; bw=sum(x.width for x in bot)+gap
sheet=Image.new("RGB",(max(tw,bw),max(x.height for x in top)+gap+max(x.height for x in bot)),"white")
x=0
for q in top: sheet.paste(q,(x,0)); x+=q.width+gap
y=max(x.height for x in top)+gap; x=0
for q in bot: sheet.paste(q,(x,y)); x+=q.width+gap
sheet.save(outdir/"C94_B1696633_FULL_COMPARE.jpg",quality=94)
font=ImageFont.load_default(); strips=[]
for rr in rows:
    ob=rr["original_bbox"]; cr=(max(0,ob[0]-10),max(0,ob[1]-10),min(smeta["width"],ob[2]+10),min(smeta["height"],ob[3]+10))
    cs=[]
    for lab,arr in (("SOURCE",src),("CLEAN",clean),("FINAL",final)):
        im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im); v=bg.convert("RGB").crop(cr); v.thumbnail((500,170),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(520,202),"white"); c.paste(v,((520-v.width)//2,27+(170-v.height)//2)); ImageDraw.Draw(c).text((4,4),f'{rr["key"]} {lab}',fill="black",font=font); cs.append(c)
    strip=Image.new("RGB",(1572,202),"white")
    for i,q in enumerate(cs): strip.paste(q,(i*526,0))
    strips.append(strip)
contact=Image.new("RGB",(1572,202*len(strips)),"white"); y=0
for q in strips: contact.paste(q,(0,y)); y+=202
contact.save(outdir/"C94_B1696633_ROW_CONTACT.jpg",quality=95)
result={"schema_version":1,"role":"C","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        "asset":"B1696633","scope":"revalidate latest B_RECOVERY07 candidate that advanced after C93 dispatch; FD90AA9 C93 result not repeated",
        "producer_report":"localization/graphics/role_B/20261004-B-RECOVERY07/B_RECOVERY07_B1696633_REPORT.json",
        "source_sha256":sha(source),"candidate_sha256":sha(candidate),"candidate_changed_by_C":False,
        "structure":{**smeta,"header_128_exact_to_source":True,"raw_orientation":"mirror_y"},
        "clean_plate_gate":{**cg,"status":"PASS"},"final_gate":{**fg,"status":"PASS"},
        "bbox_gate":{"elements":9,"pass":9,"fail":0,"edge_touch_keys":edge,"rows":rows,"status":"PASS"},
        "mask_consistency":{"source_text_protected_overlap":0,"allowed_protected_overlap":0,"status":"PASS"},
        "visual_evidence":{"full_compare":f"localization/graphics/role_C/{run}/C94_B1696633_FULL_COMPARE.jpg","row_contact":f"localization/graphics/role_C/{run}/C94_B1696633_ROW_CONTACT.jpg","controller_visual_qa":"PENDING"},
        "runtime_validation":"UNTESTED","status":"C94_STATIC_MACHINE_PASS_PENDING_CONTROLLER_VISUAL_QA","vr_ffb_dx11_dxvk_changes":False}
(outdir/"C94_B1696633_FINAL_QA.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C94_B1696633_STATIC_PASS",sha(candidate),edge)

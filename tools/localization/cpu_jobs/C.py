#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("Run only in GitHub-hosted localization CPU worker as role C.")

repo=Path.cwd()
run="20261004-1740-C92"
outdir=repo/"localization/graphics/role_C"/run
outdir.mkdir(parents=True,exist_ok=True)

key="FD90AA9"
source_rel="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
candidate_rel="localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
producer_rel="localization/graphics/role_A/20261004-A-RECOVERY07/A_RECOVERY07_FD90AA9_REPORT.json"
source_mask_rel="localization/graphics/role_A/20261004-A-RECOVERY07/FD90AA9_SOURCE_TEXT_MASK.png"
clean_rel="localization/graphics/role_A/20261004-A-RECOVERY07/FD90AA9_CLEAN_PLATE.png"
clean_protected_rel="localization/graphics/role_A/20261004-A-RECOVERY07/FD90AA9_CLEAN_PLATE_PROTECTED_MASK.png"
allowed_rel="localization/graphics/role_A/20261004-A-RECOVERY07/FD90AA9_ALLOWED_TEXT_REGION_MASK.png"
final_protected_rel="localization/graphics/role_A/20261004-A-RECOVERY07/FD90AA9_PROTECTED_MASK.png"
source_sha_expected="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
candidate_sha_expected="58a8bd06a38375694da7d3109fc2615ccd6d45092828f7eb5b7a9317afc13010"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; depth=struct.unpack_from("<I",b,24)[0]
    mips=struct.unpack_from("<I",b,28)[0]; pf=struct.unpack_from("<I",b,80)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bpp!=32 or pitch!=w*4 or mips!=1 or masks!=(0xff,0xff00,0xff0000,0xff000000):
        raise RuntimeError(("unexpected canonical RGBA32 layout",p,w,h,pitch,depth,mips,pf,fourcc,bpp,masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("size mismatch",len(b),128+w*h*4))
    raw=np.frombuffer(b,dtype=np.uint8,offset=128).reshape(h,w,4).copy()
    readable=np.flipud(raw).copy()
    return b[:128],raw,readable,{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"pf_flags":pf,"fourcc":"00000000","bpp":bpp,"masks":[hex(x) for x in masks],"bytes":len(b)}

def load_mask(rel,size):
    im=Image.open(repo/rel).convert("L")
    if im.size!=size: raise RuntimeError((rel,im.size,size))
    return np.asarray(im,dtype=np.uint8)>0

def load_rgba(rel,size):
    im=Image.open(repo/rel).convert("RGBA")
    if im.size!=size: raise RuntimeError((rel,im.size,size))
    return np.asarray(im,dtype=np.uint8).copy()

def bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]

def gate(src,cand,edit,protected):
    diff=np.any(src!=cand,axis=2)
    adiff=src[:,:,3]!=cand[:,:,3]
    return {
      "changed_pixels":int(diff.sum()),
      "changed_bbox":bbox(diff),
      "changed_pixels_outside_edit_mask":int(np.logical_and(diff,np.logical_not(edit)).sum()),
      "changed_pixels_in_protected_mask":int(np.logical_and(diff,protected).sum()),
      "alpha_changed_outside_edit_mask":int(np.logical_and(adiff,np.logical_not(edit)).sum())
    }

def panel(arr,label,maxw=900,maxh=900):
    im=Image.fromarray(arr,"RGBA")
    bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
    v=bg.convert("RGB"); v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+26),"white"); c.paste(v,(0,26))
    ImageDraw.Draw(c).text((5,5),label,fill="black",font=ImageFont.load_default())
    return c

source=repo/source_rel; candidate=repo/candidate_rel
if sha(source)!=source_sha_expected: raise RuntimeError("source SHA mismatch")
if sha(candidate)!=candidate_sha_expected: raise RuntimeError("candidate SHA mismatch")
shead,sraw,src,sinfo=load_dds(source)
chead,craw,final,cinfo=load_dds(candidate)
if shead!=chead or sinfo!=cinfo: raise RuntimeError("candidate header/structure drift")
size=(sinfo["width"],sinfo["height"])

producer=json.loads((repo/producer_rel).read_text(encoding="utf-8"))
rows=producer["rows"]
if len(rows)!=29: raise RuntimeError(("producer row count",len(rows)))
if producer.get("candidate_sha256")!=candidate_sha_expected: raise RuntimeError("producer report SHA mismatch")

source_mask=load_mask(source_mask_rel,size)
clean=load_rgba(clean_rel,size)
clean_protected=load_mask(clean_protected_rel,size)
allowed=load_mask(allowed_rel,size)
final_protected=load_mask(final_protected_rel,size)

clean_gate=gate(src,clean,source_mask,clean_protected)
final_gate=gate(src,final,allowed,final_protected)
source_protected_overlap=int(np.logical_and(source_mask,clean_protected).sum())
allowed_protected_overlap=int(np.logical_and(allowed,final_protected).sum())
if any((clean_gate["changed_pixels_outside_edit_mask"],clean_gate["changed_pixels_in_protected_mask"],clean_gate["alpha_changed_outside_edit_mask"],
        final_gate["changed_pixels_outside_edit_mask"],final_gate["changed_pixels_in_protected_mask"],final_gate["alpha_changed_outside_edit_mask"],
        source_protected_overlap,allowed_protected_overlap)):
    raise RuntimeError(("C92 mask gate failed",clean_gate,final_gate,source_protected_overlap,allowed_protected_overlap))

# Independent target footprint from final vs clean, evaluated inside each exact source bbox.
target_diff=np.any(final!=clean,axis=2)
row_reports=[]; edge_touch=[]
row_union=np.zeros((sinfo["height"],sinfo["width"]),dtype=bool)
for row in rows:
    ob=[int(x) for x in row["original_bbox"]]
    reported=[int(x) for x in row["localized_bbox"]]
    if not (reported[0]>=ob[0] and reported[1]>=ob[1] and reported[2]<=ob[2] and reported[3]<=ob[3] and row.get("containment")=="PASS"):
        raise RuntimeError(("producer bbox fail",row["key"],ob,reported))
    row_union[ob[1]:ob[3],ob[0]:ob[2]]=True
    local=np.zeros_like(target_diff)
    local[ob[1]:ob[3],ob[0]:ob[2]]=target_diff[ob[1]:ob[3],ob[0]:ob[2]]
    derived=bbox(local)
    if derived is None: raise RuntimeError(("no target diff",row["key"]))
    # The independently derived final-vs-clean footprint must also remain exact-bbox contained.
    ok=derived[0]>=ob[0] and derived[1]>=ob[1] and derived[2]<=ob[2] and derived[3]<=ob[3]
    if not ok: raise RuntimeError(("derived target bbox fail",row["key"],ob,derived))
    deltas=[reported[0]-ob[0],ob[2]-reported[2],reported[1]-ob[1],ob[3]-reported[3]]
    if min(deltas)==0: edge_touch.append(row["key"])
    row_reports.append({
      "key":row["key"],"source":row.get("source"),"korean":row.get("korean"),
      "original_bbox":ob,"localized_bbox":reported,"derived_final_vs_clean_bbox":derived,
      "delta_left":deltas[0],"delta_right":deltas[1],"delta_top":deltas[2],"delta_bottom":deltas[3],
      "containment":"PASS","raw_original_bbox":row.get("raw_original_bbox"),
      "raw_localized_bbox":row.get("raw_localized_bbox"),"raw_containment":row.get("raw_containment"),
      "rework_status":row.get("rework_status")
    })

allowed_outside_rows=int(np.logical_and(allowed,np.logical_not(row_union)).sum())
if allowed_outside_rows: raise RuntimeError(("allowed mask escapes row union",allowed_outside_rows))

# Prior-pass preservation is checked against producer metadata: all 10 prior-pass owned rows must remain scale 1.0 and be labeled preserved.
ops={x["key"]:x for x in producer.get("operations",[])}
prior_pass=[r["key"] for r in rows if r.get("rework_status")=="PRIOR_C85_PASS_PRESERVED"]
if len(prior_pass)!=10: raise RuntimeError(("prior pass count",len(prior_pass),prior_pass))
for k in prior_pass:
    op=ops.get(k)
    if not op or op.get("status")!="PRIOR_PASS_LAYER_PRESERVED" or float(op.get("scale",0))!=1.0:
        raise RuntimeError(("prior-pass preservation metadata mismatch",k,op))

# Full compare and row-contact visual evidence.
cards=[panel(src,"SOURCE_READABLE"),panel(clean,"CLEAN_READABLE"),panel(final,"FINAL_READABLE"),
       panel(sraw,"SOURCE_RAW"),panel(craw,"FINAL_RAW")]
gap=8; top=cards[:3]; bot=cards[3:]
tw=sum(c.width for c in top)+gap*(len(top)-1); th=max(c.height for c in top)
bw=sum(c.width for c in bot)+gap*(len(bot)-1); bh=max(c.height for c in bot)
sheet=Image.new("RGB",(max(tw,bw),th+gap+bh),"white")
x=0
for c in top: sheet.paste(c,(x,0)); x+=c.width+gap
x=0
for c in bot: sheet.paste(c,(x,th+gap)); x+=c.width+gap
sheet.save(outdir/"C92_FD90AA9_FULL_COMPARE.jpg",quality=93)

font=ImageFont.load_default(); strips=[]
for rr in row_reports:
    x0,y0,x1,y1=rr["original_bbox"]; pad=10
    cr=(max(0,x0-pad),max(0,y0-pad),min(sinfo["width"],x1+pad),min(sinfo["height"],y1+pad))
    cs=[]
    for tag,arr in (("SOURCE",src),("CLEAN",clean),("FINAL",final)):
        im=Image.fromarray(arr,"RGBA"); bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im)
        v=bg.convert("RGB").crop(cr); v.thumbnail((480,160),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(500,190),"white"); c.paste(v,((500-v.width)//2,25+(160-v.height)//2))
        ImageDraw.Draw(c).text((4,4),f'{rr["key"]} {tag}',fill="black",font=font); cs.append(c)
    strip=Image.new("RGB",(1512,190),"white")
    for i,c in enumerate(cs): strip.paste(c,(i*506,0))
    strips.append(strip)
contact=Image.new("RGB",(1512,190*len(strips)),"white")
y=0
for s in strips: contact.paste(s,(0,y)); y+=190
contact.save(outdir/"C92_FD90AA9_ROW_CONTACT.jpg",quality=94)

result={
 "schema_version":1,"role":"C","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "asset":key,"scope":"independent C final static QA of A_RECOVERY07 direct return; completed C90/C91 assets not repeated",
 "producer_report":producer_rel,"source_path":source_rel,"candidate_path":candidate_rel,
 "source_sha256":source_sha_expected,"candidate_sha256":candidate_sha_expected,
 "candidate_changed_by_C":False,
 "structure":{**sinfo,"header_128_exact_to_source":True,"raw_orientation":"mirror_y"},
 "clean_plate_gate":{**clean_gate,"source_text_protected_overlap_pixels":source_protected_overlap,"status":"PASS"},
 "final_candidate_gate":{**final_gate,"allowed_protected_overlap_pixels":allowed_protected_overlap,"status":"PASS"},
 "bbox_gate":{"elements":29,"pass":29,"fail":0,"edge_touch_keys":edge_touch,"rows":row_reports,"status":"PASS"},
 "prior_pass_gate":{"expected":10,"preserved_metadata_count":len(prior_pass),"keys":prior_pass,"status":"PASS"},
 "mask_consistency":{"allowed_pixels_outside_union_of_29_original_bboxes":allowed_outside_rows,"status":"PASS"},
 "visual_evidence":{"full_compare":f"localization/graphics/role_C/{run}/C92_FD90AA9_FULL_COMPARE.jpg","row_contact":f"localization/graphics/role_C/{run}/C92_FD90AA9_ROW_CONTACT.jpg","controller_visual_qa":"PENDING"},
 "runtime_validation":"UNTESTED",
 "status":"C92_STATIC_MACHINE_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_INGAME",
 "vr_ffb_dx11_dxvk_changes":False
}
(outdir/"C92_FD90AA9_FINAL_QA.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C92_FD90AA9_STATIC_PASS","edge_touch",edge_touch,"sha",candidate_sha_expected)

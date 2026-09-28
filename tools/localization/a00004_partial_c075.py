#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image,ImageChops,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
TASK_ID="LOCALIZATION-LOCALIZATION_A-00004"; ASSET="C075FB49"; INDEX=111
SOURCE=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds"
CANDIDATE=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds"
C85=ROOT/"localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
B91=ROOT/"localization/graphics/role_B/20260928-0920-B91/B91_RGBA_REWORK_ACTIONS.json"
R411=ROOT/"localization/graphics/role_A/20260928-A00004/A00004_411827E_REWORK_REPORT.json"
RUN_DIR=ROOT/"localization/graphics/role_A/20260928-A00004"
REPORT=RUN_DIR/"A00004_C075FB49_PARTIAL_REWORK_REPORT.json"
QA=RUN_DIR/"A00004_C075FB49_PARTIAL_REWORK_QA.png"
EXPECTED="9f64a9de61d63c3745fdf45ed7eb36d1514f31a3dfeb880a0e87634263a088b9"
SAFE_KEYS=("long_distance","for_experts","new_course_desc")
sha=lambda b:hashlib.sha256(b).hexdigest()

def parse(b):
    if len(b)<128 or b[:4]!=b"DDS ": raise SystemExit("invalid DDS")
    h,w,pitch,mips=struct.unpack_from("<IIII",b,12); mips=mips or 1
    fourcc=b[84:88]; bits=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bits!=32 or masks!=(0xFF,0xFF00,0xFF0000,0xFF000000):
        raise SystemExit(f"unsupported DDS {fourcc!r} {bits} {masks}")
    if pitch!=w*4 or mips!=1 or len(b)!=128+w*h*4: raise SystemExit("unexpected payload")
    return w,h,mips
def rgba(b,w,h): return Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
def diffmask(a,b):
    d=ImageChops.difference(a,b); r,g,bb,aa=d.split()
    return ImageChops.lighter(ImageChops.lighter(r,g),ImageChops.lighter(bb,aa))
def alpha_bbox(im,cell):
    x0,y0,x1,y1=cell; b=im.crop((x0,y0,x1+1,y1+1)).getchannel("A").getbbox()
    return None if b is None else [x0+b[0],y0+b[1],x0+b[2]-1,y0+b[3]-1]
def inside(b,o): return b is not None and b[0]>=o[0] and b[1]>=o[1] and b[2]<=o[2] and b[3]<=o[3]
def mk_mask(size,boxes):
    m=Image.new("L",size,0); d=ImageDraw.Draw(m)
    for x0,y0,x1,y1 in boxes:d.rectangle((x0,y0,x1,y1),fill=255)
    return m
def nz(m): return sum(v for i,v in enumerate(m.histogram()) if i)

sb=SOURCE.read_bytes(); cb=CANDIDATE.read_bytes()
if sha(cb)!=EXPECTED: raise SystemExit(f"stale C075 candidate {sha(cb)} != {EXPECTED}")
w,h,m=parse(sb); w2,h2,m2=parse(cb)
assert (w,h,m)==(w2,h2,m2)==(2048,2048,1) and sb[:128]==cb[:128]
doc=json.loads(C85.read_text("utf-8")); asset=next(x for x in doc["assets"] if x["asset"]==ASSET); rows=asset["rows"]
actions=json.loads(B91.read_text("utf-8")); amap={x["key"]:x for x in next(a for a in actions["assets"] if a["asset"]==ASSET)["rows"]}
src=rgba(sb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before=rgba(cb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM); after=before.copy()
recs=[]

# These three cells are visually confirmed independent text-only regions in the
# existing B88/C82 readable evidence. Require alpha bbox agreement before editing;
# otherwise abort before any candidate write.
for key in SAFE_KEYS:
    r=next(x for x in rows if x["key"]==key); old=r["localized_bbox"]; orig=r["original_bbox"]
    actual_before=alpha_bbox(before,r["sprite_cell"])
    if actual_before!=old:
        raise SystemExit(f"{key}: text-only alpha precondition mismatch {actual_before} != {old}")
    x0,y0,x1,y1=old; t=amap[key]["new_localized_bbox"]; tx0,ty0,tx1,ty1=t
    patch=before.crop((x0,y0,x1+1,y1+1))
    after.paste((0,0,0,0),(x0,y0,x1+1,y1+1))
    if patch.size!=(tx1-tx0+1,ty1-ty0+1):
        patch=patch.resize((tx1-tx0+1,ty1-ty0+1),Image.Resampling.LANCZOS)
    after.alpha_composite(patch,(tx0,ty0))
    ab=alpha_bbox(after,r["sprite_cell"])
    if not inside(ab,orig):
        raise SystemExit(f"{key}: post alpha bbox {ab} outside {orig}")
    recs.append({"key":key,"method":"isolated_text_patch_fit","before_bbox":old,"target_bbox":t,
                 "post_alpha_bbox":ab,"containment":"PASS",
                 "scale_x":round((tx1-tx0+1)/(x1-x0+1),6),"scale_y":round((ty1-ty0+1)/(y1-y0+1),6)})

touch=mk_mask((w,h),[next(x for x in rows if x["key"]==k)["sprite_cell"] for k in SAFE_KEYS])
changed=diffmask(before,after)
collateral=nz(ImageChops.multiply(changed,ImageChops.invert(touch)))
all_cells=mk_mask((w,h),[r["sprite_cell"] for r in rows])
outside_cells=nz(ImageChops.multiply(changed,ImageChops.invert(all_cells)))
allowed_safe=mk_mask((w,h),[next(x for x in rows if x["key"]==k)["original_bbox"] for k in SAFE_KEYS])
introduced_outside=nz(ImageChops.multiply(ImageChops.subtract(after.getchannel("A"),before.getchannel("A")),ImageChops.invert(allowed_safe)))
if collateral or outside_cells or introduced_outside:
    raise SystemExit(f"guard failed collateral={collateral} outside_cells={outside_cells} introduced_outside={introduced_outside}")

out=cb[:128]+after.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA")
parse(out)
if out[:128]!=cb[:128] or len(out)!=len(cb): raise SystemExit("DDS structure changed")
newsha=sha(out)
if newsha==EXPECTED: raise SystemExit("no change")
remaining=[r["key"] for r in rows if r["containment"]=="FAIL" and r["key"] not in SAFE_KEYS]
if len(remaining)!=6: raise SystemExit(f"unexpected remaining failures {remaining}")

# Focus proof, source/current/after on white.
tiles=[]
for key in SAFE_KEYS:
    r=next(x for x in rows if x["key"]==key); x0,y0,x1,y1=r["sprite_cell"]; pad=8
    x0=max(0,x0-pad);y0=max(0,y0-pad);x1=min(w-1,x1+pad);y1=min(h-1,y1+pad)
    ims=[src.crop((x0,y0,x1+1,y1+1)),before.crop((x0,y0,x1+1,y1+1)),after.crop((x0,y0,x1+1,y1+1))]
    panels=[]
    for im in ims:
        bg=Image.new("RGBA",im.size,(255,255,255,255)); bg.alpha_composite(im)
        panels.append(bg.resize((bg.width*2,bg.height*2),Image.Resampling.NEAREST).convert("RGB"))
    tile=Image.new("RGB",(sum(p.width for p in panels),max(p.height for p in panels)+28),"white")
    ImageDraw.Draw(tile).text((4,4),f"{key} | SOURCE | BEFORE | AFTER",fill="black")
    xx=0
    for p in panels:tile.paste(p,(xx,28));xx+=p.width
    tiles.append(tile)
W=max(t.width for t in tiles);H=sum(t.height for t in tiles);sheet=Image.new("RGB",(W,H),"white");yy=0
for t in tiles:sheet.paste(t,(0,yy));yy+=t.height
RUN_DIR.mkdir(parents=True,exist_ok=True);sheet.save(QA)

CANDIDATE.write_bytes(out)
now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
report={"schema_version":1,"role":"A","run":"A00004","task_id":TASK_ID,"timestamp_kst":now,
 "asset":ASSET,"index":INDEX,"base_head":os.environ.get("GITHUB_SHA"),
 "previous_candidate_sha256":EXPECTED,"candidate_sha256":newsha,
 "structure":{"dimensions":[w,h],"format":"RGBA32","mipmaps":m,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "reworked_elements":recs,"remaining_rework_elements":remaining,
 "qa":{"touched_elements":len(recs),"touched_failed":0,"changed_pixels_outside_touched_cells":collateral,
       "changed_pixels_outside_declared_cells":outside_cells,"introduced_alpha_outside_safe_original_bboxes":introduced_outside,
       "visual_proof":str(QA.relative_to(ROOT))},
 "status":"PARTIAL_REWORK_PASS_3_SAFE_6_REMAIN","automation_validation":"PASS","runtime_validation":"UNTESTED",
 "final_approval":False,"build_performed":False,"vr_ffb_changes":False,"gpt_library_used":False}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")

# Queue remains REWORK_REQUIRED. Preserve all historical malformed rows.
qp=ROOT/"localization/graphics/asset_queue.csv"; qlines=qp.read_text("utf-8").splitlines(); found=False
for i,line in enumerate(qlines):
    if line.startswith("111,"):
        p=line.split(",",5)
        if len(p)<6: raise SystemExit("queue row 111 malformed")
        p[3]="rework_required_zero_pixel_or_artifact"
        p[5]=p[5].rstrip("; ")+"; A00004 partial safe rework: long_distance/for_experts/new_course_desc contained; 6 C85 failures remain"
        qlines[i]=",".join(p);found=True;break
if not found: raise SystemExit("queue row 111 missing")
qp.write_text("\n".join(qlines)+"\n","utf-8")

r411=json.loads(R411.read_text("utf-8"))
pp=ROOT/"localization/progress/progress.json"; p=json.loads(pp.read_text("utf-8"));p["updated_at_kst"]=now
p.setdefault("graphics",{})["latest_a_production"]={"run":"A00004","task_id":TASK_ID,
 "assets":{"411827E":{"candidate_sha256":r411["candidate_sha256"],"status":"A_SELF_QA_PASS_PENDING_C_VISUAL_INGAME","report":str(R411.relative_to(ROOT))},
           "C075FB49":{"candidate_sha256":newsha,"status":"A_PARTIAL_REWORK_3_SAFE_6_REMAIN","report":str(REPORT.relative_to(ROOT))}}}
p["next_checkpoint"]="A00004: 411827E self-QA PASS; C075FB49 partial safe rework 3/9 completed with 6 failures remaining; 568D3696 specialized DXT5 rework remains."
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")

rp=ROOT/"localization/resume_state.json";rs=json.loads(rp.read_text("utf-8"));rs["schema_version"]=int(rs.get("schema_version",0))+1
rs.setdefault("next_actions",[]).insert(0,"A00004: C075FB49 partial safe rework fixed long_distance/for_experts/new_course_desc; 6 failures remain. 411827E pending C visual + DDS_ONLY in-game.")
rs.setdefault("graphics_checkpoint",{})["a00004_c075fb49"]={"timestamp_kst":now,"report":str(REPORT.relative_to(ROOT)),"candidate_sha256":newsha,"status":"PARTIAL_REWORK_3_SAFE_6_REMAIN"}
rp.write_text(json.dumps(rs,ensure_ascii=False,indent=2)+"\n","utf-8")

sp=ROOT/"localization/progress/STATUS.md"
sp.write_text(sp.read_text("utf-8")+f"\n\n### A00004 C075FB49 partial safe rework — {now}\n- Odd index 111: fixed three non-overlapping text-only C85 failures: long_distance, for_experts, new_course_desc. Each post alpha bbox is inside the original permitted bbox.\n- DDS 2048x2048 RGBA32/mip1/header/raw mirror_y preserved; changed pixels outside touched cells=0; introduced alpha outside safe original bboxes=0.\n- Candidate {newsha}; six C85 failures intentionally remain REWORK_REQUIRED because they overlap adjacent cells or artwork/badges. AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED.\n","utf-8")
with (ROOT/"localization/WORKLOG.md").open("a",encoding="utf-8") as f:
    f.write(f"\n\n## {now} - A00004 C075FB49 partial safe rework\n- Continued throughput after 411827E. Modified only three independently isolated text-only regions: long_distance, for_experts, new_course_desc.\n- Actual alpha bbox precondition matched C85 for all three before edit; post alpha bboxes are contained. No changes outside touched cells and no introduced alpha outside their original bboxes. Candidate {newsha}.\n- Six remaining failures are left for dedicated overlap/artwork-safe rework; asset remains REWORK_REQUIRED. RUNTIME_VALIDATION=UNTESTED; no build/N100/GPT Library/VR/FFB work.\n")

tp=ROOT/"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00004.json";tr=json.loads(tp.read_text("utf-8"))
tr["automation_validation"]="PASS";tr["runtime_validation"]="UNTESTED"
tr["summary"]="A00004 produced 411827E full self-QA PASS (7/7) and C075FB49 partial safe rework (3 independent text failures fixed; 6 failures remain). 568D3696 DXT5 specialized rework deferred. C visual/final QA and isolated DDS_ONLY in-game validation remain required."
tr["evidence"].extend([str(REPORT.relative_to(ROOT)),str(QA.relative_to(ROOT))])
tr["c075_candidate_sha256"]=newsha;tr["result_sha"]="PENDING_LATEST_PRODUCTION_COMMIT"
tp.write_text(json.dumps(tr,ensure_ascii=False,indent=2)+"\n","utf-8")

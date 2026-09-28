#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image,ImageChops,ImageDraw,ImageOps

ROOT=Path(__file__).resolve().parents[2]
TASK_ID="LOCALIZATION-LOCALIZATION_A-00004"; ASSET="411827E"; INDEX=97
SOURCE=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"
CANDIDATE=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"
C85=ROOT/"localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
B91=ROOT/"localization/graphics/role_B/20260928-0920-B91/B91_RGBA_REWORK_ACTIONS.json"
RUN_DIR=ROOT/"localization/graphics/role_A/20260928-A00004"
REPORT=RUN_DIR/"A00004_411827E_REWORK_REPORT.json"
QA=RUN_DIR/"A00004_411827E_REWORK_QA.png"
EXPECTED="c3e89fb3875e1aba79a6a3fc744fde6af91bff5906fdb1827573ca0d2c9a2d74"
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
def bbox(src,loc,cell):
    x0,y0,x1,y1=cell
    b=diffmask(src.crop((x0,y0,x1+1,y1+1)),loc.crop((x0,y0,x1+1,y1+1))).getbbox()
    return None if b is None else [x0+b[0],y0+b[1],x0+b[2]-1,y0+b[3]-1]
def inside(b,o): return b is not None and b[0]>=o[0] and b[1]>=o[1] and b[2]<=o[2] and b[3]<=o[3]
def mk_mask(size,boxes):
    m=Image.new("L",size,0); d=ImageDraw.Draw(m)
    for x0,y0,x1,y1 in boxes:d.rectangle((x0,y0,x1,y1),fill=255)
    return m
def nz(m): return sum(v for i,v in enumerate(m.histogram()) if i)

sb=SOURCE.read_bytes(); cb=CANDIDATE.read_bytes()
if sha(cb)!=EXPECTED: raise SystemExit(f"stale candidate {sha(cb)} != {EXPECTED}")
w,h,m=parse(sb); w2,h2,m2=parse(cb)
assert (w,h,m)==(w2,h2,m2)==(2048,2048,1) and sb[:128]==cb[:128]

doc=json.loads(C85.read_text("utf-8")); asset=next(x for x in doc["assets"] if x["asset"]==ASSET); rows=asset["rows"]
fails=[r for r in rows if r["containment"]=="FAIL"]
if {r["key"] for r in fails}!={"seconds","tuned","normal","random"}: raise SystemExit("unexpected C85 failure set")
actions=json.loads(B91.read_text("utf-8")); basset=next(x for x in actions["assets"] if x["asset"]==ASSET)
bmap={r["key"]:r for r in basset["rows"]}

src=rgba(sb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before=rgba(cb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
after=before.copy(); recs=[]

# seconds is a transparent text-only cell. Its Korean raster is genuinely taller than
# the original permitted bbox, so resize only that text patch to B91's proven target.
r=next(x for x in rows if x["key"]=="seconds")
old=r["localized_bbox"]; target=bmap["seconds"]["new_localized_bbox"]
x0,y0,x1,y1=old; tx0,ty0,tx1,ty1=target
patch=before.crop((x0,y0,x1+1,y1+1))
# Safety: no visible candidate pixels may exist in the old rectangle outside the patch itself;
# clear only the old localized rectangle, never the whole sprite cell.
after.paste((0,0,0,0),(x0,y0,x1+1,y1+1))
patch=patch.resize((tx1-tx0+1,ty1-ty0+1),Image.Resampling.LANCZOS)
after.alpha_composite(patch,(tx0,ty0))
recs.append({"key":"seconds","method":"localized_patch_minimal_lanczos","before_bbox":old,"target_bbox":target,
             "scale_x":round((tx1-tx0+1)/(x1-x0+1),6),"scale_y":round((ty1-ty0+1)/(y1-y0+1),6)})

# The three badge labels already look source-faithful. Their 1-3 px overflow is from
# localized/source-diff fringe at the badge/text boundary. Restore canonical source
# only outside each original permitted text bbox; do not resample badge artwork or Hangul.
for key in ("tuned","normal","random"):
    r=next(x for x in rows if x["key"]==key)
    cell=mk_mask((w,h),[r["sprite_cell"]]); allowed=mk_mask((w,h),[r["original_bbox"]])
    repair=ImageChops.multiply(cell,ImageOps.invert(allowed))
    before_key=after.copy()
    after=Image.composite(src,after,repair)
    changed=nz(diffmask(before_key,after))
    recs.append({"key":key,"method":"restore_source_outside_original_bbox_no_resample",
                 "original_bbox":r["original_bbox"],"restored_pixels":changed})

# Strict source-diff containment across all seven declared elements.
qa_rows=[]; failed=[]
for r in rows:
    b=bbox(src,after,r["sprite_cell"]); ok=inside(b,r["original_bbox"])
    q={"key":r["key"],"original_bbox":r["original_bbox"],"localized_diff_bbox":b,
       "delta_left":None if b is None else b[0]-r["original_bbox"][0],
       "delta_right":None if b is None else r["original_bbox"][2]-b[2],
       "delta_top":None if b is None else b[1]-r["original_bbox"][1],
       "delta_bottom":None if b is None else r["original_bbox"][3]-b[3],
       "containment":"PASS" if ok else "FAIL"}
    qa_rows.append(q)
    if not ok: failed.append(q)

touch=mk_mask((w,h),[r["sprite_cell"] for r in fails])
all_cells=mk_mask((w,h),[r["sprite_cell"] for r in rows])
allowed_all=mk_mask((w,h),[r["original_bbox"] for r in rows])
changed=diffmask(before,after)
collateral=nz(ImageChops.multiply(changed,ImageOps.invert(touch)))
source_diff=diffmask(src,after)
outside_cells=nz(ImageChops.multiply(source_diff,ImageOps.invert(all_cells)))
outside_original=nz(ImageChops.multiply(source_diff,ImageOps.invert(allowed_all)))
introduced=nz(ImageChops.multiply(ImageChops.subtract(after.getchannel("A"),src.getchannel("A")),ImageOps.invert(all_cells)))
if failed or collateral or outside_cells or outside_original or introduced:
    print(json.dumps({"failed":failed,"collateral":collateral,"outside_cells":outside_cells,
                      "outside_original":outside_original,"introduced_alpha_outside_cells":introduced},ensure_ascii=False,indent=2))
    raise SystemExit("A00004 strict post-QA failed; candidate not written")

out=cb[:128]+after.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA")
parse(out)
if out[:128]!=cb[:128] or len(out)!=len(cb): raise SystemExit("DDS structure changed")
newsha=sha(out)
if newsha==EXPECTED: raise SystemExit("no change")

# Focused visual proof: SOURCE | BEFORE | AFTER | AFTER-vs-SOURCE diff.
focus=["seconds","tuned","normal","random"]; tiles=[]
for key in focus:
    r=next(x for x in rows if x["key"]==key); x0,y0,x1,y1=r["sprite_cell"]; pad=6
    x0=max(0,x0-pad);y0=max(0,y0-pad);x1=min(w-1,x1+pad);y1=min(h-1,y1+pad)
    ims=[src.crop((x0,y0,x1+1,y1+1)),before.crop((x0,y0,x1+1,y1+1)),after.crop((x0,y0,x1+1,y1+1))]
    ims.append(ImageChops.difference(ims[0],ims[2]))
    panels=[]
    for im in ims:
        bg=Image.new("RGBA",im.size,(255,255,255,255)); bg.alpha_composite(im)
        panels.append(bg.resize((bg.width*2,bg.height*2),Image.Resampling.NEAREST).convert("RGB"))
    tile=Image.new("RGB",(sum(p.width for p in panels),max(p.height for p in panels)+26),"white")
    ImageDraw.Draw(tile).text((3,3),f"{key}: SOURCE | BEFORE | AFTER | DIFF",fill="black")
    xx=0
    for p in panels: tile.paste(p,(xx,26)); xx+=p.width
    tiles.append(tile)
W=max(t.width for t in tiles); H=sum(t.height for t in tiles)
sheet=Image.new("RGB",(W,H),"white"); yy=0
for t in tiles: sheet.paste(t,(0,yy)); yy+=t.height
RUN_DIR.mkdir(parents=True,exist_ok=True); sheet.save(QA)

CANDIDATE.write_bytes(out)
now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
report={"schema_version":1,"role":"A","run":"A00004","task_id":TASK_ID,"timestamp_kst":now,
 "base_head":os.environ.get("GITHUB_SHA"),"asset":ASSET,"index":INDEX,
 "source_path":str(SOURCE.relative_to(ROOT)),"candidate_path":str(CANDIDATE.relative_to(ROOT)),
 "previous_candidate_sha256":EXPECTED,"candidate_sha256":newsha,
 "structure":{"dimensions":[w,h],"format":"RGBA32","mipmaps":m,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rework":recs,"qa":{"elements":len(rows),"failed_elements":0,"rows":qa_rows,
 "changed_pixels_outside_touched_cells":collateral,"source_diff_pixels_outside_declared_cells":outside_cells,
 "source_diff_pixels_outside_original_bboxes":outside_original,"introduced_alpha_outside_declared_cells":introduced,
 "visual_proof":str(QA.relative_to(ROOT))},
 "deferred":{"asset":"568D3696","reason":"DXT5/mip13 failures require shrink beyond proven one-pixel endpoint-preserving remap; no broad recompression attempted"},
 "automation_validation":"PASS","runtime_validation":"UNTESTED","final_approval":False,
 "build_performed":False,"vr_ffb_changes":False,"gpt_library_used":False}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")

# Preserve malformed historical CSV rows byte-for-byte; update only index 97 line.
qp=ROOT/"localization/graphics/asset_queue.csv"; qlines=qp.read_text("utf-8").splitlines()
found=False
for i,line in enumerate(qlines):
    if line.startswith("97,"):
        parts=line.split(",",5)
        if len(parts)<6: raise SystemExit("queue row 97 malformed beyond safe update")
        parts[3]="a00004_self_qa_pass_pending_c_visual_ingame"
        parts[5]=parts[5].rstrip("; ")+"; A00004 411 exact source-bbox PASS 7/7; badge backgrounds not resampled; C visual + DDS_ONLY in-game pending"
        qlines[i]=",".join(parts); found=True; break
if not found: raise SystemExit("queue row 97 missing")
qp.write_text("\n".join(qlines)+"\n","utf-8")

pp=ROOT/"localization/progress/progress.json"; p=json.loads(pp.read_text("utf-8")); p["updated_at_kst"]=now
p.setdefault("graphics",{})["latest_a_production"]={"run":"A00004","task_id":TASK_ID,"report":str(REPORT.relative_to(ROOT)),
 "assets":{ASSET:{"candidate_sha256":newsha,"status":"A_SELF_QA_PASS_PENDING_C_VISUAL_INGAME"}}}
p["next_checkpoint"]="A00004 411827E self-QA PASS; independent C visual/source-style QA and isolated DDS_ONLY in-game validation pending. 568D3696 DXT5 remains specialized rework."
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")

rp=ROOT/"localization/resume_state.json"; rs=json.loads(rp.read_text("utf-8")); rs["schema_version"]=int(rs.get("schema_version",0))+1
rs.setdefault("next_actions",[]).insert(0,"A00004: 411827E self-QA PASS; C visual/source-style + isolated DDS_ONLY in-game pending. 568D3696 remains DXT5 specialized rework.")
rs.setdefault("graphics_checkpoint",{})["a00004_411827e"]={"timestamp_kst":now,"report":str(REPORT.relative_to(ROOT)),
 "candidate_sha256":newsha,"status":"A_SELF_QA_PASS_PENDING_C_VISUAL_INGAME"}
rp.write_text(json.dumps(rs,ensure_ascii=False,indent=2)+"\n","utf-8")

sp=ROOT/"localization/progress/STATUS.md"
sp.write_text(sp.read_text("utf-8")+f"\n\n### A00004 411827E rework — {now}\n- Odd index 97 REWORK: seconds minimally resized/repositioned; TUNED/NORMAL/RANDOM badge backgrounds were not resampled, only source pixels outside original permitted bboxes restored.\n- Automated source-diff containment 7/7 PASS; outside original bboxes/cells 0; collateral outside touched cells 0; introduced alpha outside 0.\n- Candidate {newsha}; AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED; independent C visual/source-style + DDS_ONLY in-game pending.\n- 568D3696 index 53 deferred: DXT5 mip13 shrink cases exceed proven one-pixel remap; broad recompression not attempted.\n","utf-8")
with (ROOT/"localization/WORKLOG.md").open("a",encoding="utf-8") as f:
    f.write(f"\n\n## {now} - A00004 411827E exact-bbox/artifact-safe rework\n- GitHub-only odd index 97 production. 568D3696 index 53 was not force-edited because its DXT5/mip13 shrink cases require a specialized decoded-pixel-safe path.\n- 411827E: seconds resized only within its transparent text cell; tuned/normal/random badge artwork was not scaled. Source pixels were restored only outside each original permitted text bbox.\n- Self-QA: 7/7 exact source-diff containment PASS; source-diff outside original bboxes=0, outside declared cells=0, collateral outside touched cells=0, introduced alpha outside=0. Candidate {newsha}.\n- AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED. Independent C visual/source-style review and isolated DDS_ONLY in-game validation remain required. No build/N100/GPT Library/VR/FFB work.\n")

tp=ROOT/"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00004.json"; tr=json.loads(tp.read_text("utf-8"))
tr["automation_validation"]="PASS"; tr["runtime_validation"]="UNTESTED"
tr["summary"]="A00004 produced 411827E index 97 rework: 7/7 strict source-diff bbox containment PASS; badge backgrounds were not resampled. Independent C visual/source-style QA and isolated DDS_ONLY in-game remain required."
tr["evidence"].extend([str(REPORT.relative_to(ROOT)),str(QA.relative_to(ROOT))])
tr["candidate_sha256"]=newsha; tr["result_sha"]="PENDING_PRODUCTION_COMMIT"
tr["note"]="GitHub-only. 568D3696 index 53 deferred for specialized DXT5-safe shrink handling. No N100/GPT Library/VR/FFB/DX9Ex/DX11/DXVK/build. Runtime validation not performed."
tp.write_text(json.dumps(tr,ensure_ascii=False,indent=2)+"\n","utf-8")

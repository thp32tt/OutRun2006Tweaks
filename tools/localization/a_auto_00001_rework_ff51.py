#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, os, struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT=Path(__file__).resolve().parents[2]
ASSET="FF2462BB"; INDEX=51; TASK_ID="LOCALIZATION-LOCALIZATION_A-00001"
SOURCE=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
CANDIDATE=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
C85=ROOT/"localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
RUN_DIR=ROOT/"localization/graphics/role_A/20260928-AUTO-A00001-FF51"
REPORT=RUN_DIR/"A_AUTO_00001_FF2462BB_TRANSLATION_ONLY_REWORK.json"
EXPECTED="c9ae1b1222ddd1516160912cdd6d28dcd65ac17e4dc806d1c51f05feb10c0b9c"
SAFE_KEYS={"SCREAMING","ENTER_ACCOUNT_NAME","ENTER_ACCOUNT_PASSWORD","LOAD_SAVE","ENTER_XBOX_PASSCODE","LOGIN_TO_ACCOUNT"}
sha=lambda b:hashlib.sha256(b).hexdigest()

def parse(b):
    if len(b)<128 or b[:4]!=b"DDS ": raise SystemExit("invalid DDS")
    h,w,pitch,mips=struct.unpack_from("<IIII",b,12); mips=mips or 1
    fourcc=b[84:88]; bits=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bits!=32 or masks!=(0xFF,0xFF00,0xFF0000,0xFF000000): raise SystemExit("unsupported DDS")
    if pitch!=w*4 or len(b)!=128+w*h*4: raise SystemExit("unexpected payload")
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
def fit_delta(old,orig):
    dx=0; dy=0
    if old[0]<orig[0]: dx=orig[0]-old[0]
    if old[2]+dx>orig[2]: dx+=orig[2]-(old[2]+dx)
    if old[1]<orig[1]: dy=orig[1]-old[1]
    if old[3]+dy>orig[3]: dy+=orig[3]-(old[3]+dy)
    moved=[old[0]+dx,old[1]+dy,old[2]+dx,old[3]+dy]
    return dx,dy,moved

sb=SOURCE.read_bytes(); cb=CANDIDATE.read_bytes()
if sha(cb)!=EXPECTED: raise SystemExit(f"stale FF candidate {sha(cb)} != {EXPECTED}")
w,h,m=parse(sb); w2,h2,m2=parse(cb)
assert (w,h,m)==(w2,h2,m2)==(4096,2048,1) and sb[:128]==cb[:128]
doc=json.loads(C85.read_text("utf-8")); asset=next(x for x in doc["assets"] if x["asset"]==ASSET); rows=asset["rows"]
src=rgba(sb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before=rgba(cb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM); after=before.copy()
recs=[]
for r in rows:
    if r["key"] not in SAFE_KEYS: continue
    old=r["localized_bbox"]; orig=r["original_bbox"]
    ow,oh=orig[2]-orig[0]+1,orig[3]-orig[1]+1
    lw,lh=old[2]-old[0]+1,old[3]-old[1]+1
    if lw>ow or lh>oh: raise SystemExit(f"{r['key']} unexpectedly requires scaling")
    dx,dy,target=fit_delta(old,orig)
    if dx==0 and dy==0: raise SystemExit(f"{r['key']} no move required")
    x0,y0,x1,y1=old
    patch=before.crop((x0,y0,x1+1,y1+1))
    # Restore the old localized rectangle from canonical HD, then move the exact
    # existing Korean raster by integer pixels only. No resampling is permitted.
    after.paste(src.crop((x0,y0,x1+1,y1+1)),(x0,y0))
    after.alpha_composite(patch,(x0+dx,y0+dy))
    recs.append({"key":r["key"],"old_bbox":old,"target_bbox":target,"dx":dx,"dy":dy,"resampled":False})

# Only touched sprite cells may change in this partial A batch.
touch_rows=[r for r in rows if r["key"] in SAFE_KEYS]
touch=mk_mask((w,h),[r["sprite_cell"] for r in touch_rows])
changed=diffmask(before,after)
collateral=nz(ImageChops.multiply(changed,ImageOps.invert(touch)))
if collateral: raise SystemExit(f"collateral pixels outside touched cells: {collateral}")

qa=[]; safe_failed=[]; all_failed=[]
for r in rows:
    b=bbox(src,after,r["sprite_cell"]); ok=inside(b,r["original_bbox"])
    q={"key":r["key"],"original_bbox":r["original_bbox"],"localized_diff_bbox":b,
       "containment":"PASS" if ok else "FAIL","touched":r["key"] in SAFE_KEYS}
    qa.append(q)
    if r["key"] in SAFE_KEYS and not ok:safe_failed.append(q)
    if not ok:all_failed.append(q)
if safe_failed:
    print(json.dumps(safe_failed,ensure_ascii=False,indent=2))
    raise SystemExit("translation-only safe subset failed containment")

out=cb[:128]+after.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"); parse(out)
if out[:128]!=sb[:128] or len(out)!=len(cb): raise SystemExit("structure changed")
oldsha,newsha=sha(cb),sha(out)
if newsha==oldsha: raise SystemExit("no change")
CANDIDATE.write_bytes(out); RUN_DIR.mkdir(parents=True,exist_ok=True)
now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
report={
 "schema_version":1,"role":"A","run":"A_AUTO_00001_FF51","task_id":TASK_ID,"timestamp_kst":now,
 "base_head":os.environ.get("GITHUB_SHA"),"asset":str(CANDIDATE.relative_to(ROOT)),"index":INDEX,
 "previous_candidate_sha256":oldsha,"candidate_sha256":newsha,
 "strategy":"integer_translation_only_no_resampling","structure":{"dimensions":[w,h],"format":"RGBA32","mipmaps":m,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "reworked_elements":recs,"qa":{"touched_elements":len(recs),"touched_failed":0,"all_elements":len(rows),
 "remaining_failures":[x["key"] for x in all_failed],"rows":qa,"changed_pixels_outside_touched_cells":collateral},
 "automation_validation":"PARTIAL_PASS","runtime_validation":"UNTESTED","final_approval":False,
 "build_performed":False,"vr_ffb_changes":False,"gpt_library_used":False
}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")
q=ROOT/"localization/graphics/asset_queue.csv"
with q.open("r",encoding="utf-8",newline="") as f: qr=list(csv.DictReader(f)); fields=list(qr[0])
for row in qr:
    if int(row["index"])==INDEX:
        row["artwork_status"]="rework_required_zero_pixel_or_artifact"
        row["notes"]=(row.get("notes","").rstrip("; ")+"; A AUTO FF51 integer-only partial rework 6 elements, no resampling; remaining strict failures require source-faithful rerender").strip("; ")
with q.open("w",encoding="utf-8",newline="") as f:
    wr=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); wr.writeheader(); wr.writerows(qr)
pp=ROOT/"localization/progress/progress.json"; p=json.loads(pp.read_text("utf-8")); p["updated_at_kst"]=now
p.setdefault("graphics",{})["latest_a_production"]={"run":"A_AUTO_00001_FF51","task_id":TASK_ID,"report":str(REPORT.relative_to(ROOT)),
 "assets":{ASSET:{"candidate_sha256":newsha,"status":"A_PARTIAL_TRANSLATION_ONLY_PASS_REWORK_REMAINS"}}}
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
rp=ROOT/"localization/resume_state.json"; rs=json.loads(rp.read_text("utf-8")); rs["schema_version"]=int(rs.get("schema_version",55))+1
rs.setdefault("next_actions",[]).insert(0,"A AUTO FF51: FF2462BB 6 no-resample bbox fixes committed; remaining strict failures need source-faithful rerender; runtime untested.")
rs.setdefault("graphics_checkpoint",{})["a_auto_00001_ff51"]={"timestamp_kst":now,"report":str(REPORT.relative_to(ROOT)),"candidate_sha256":newsha,"status":"PARTIAL_PASS_REWORK_REMAINS"}
rp.write_text(json.dumps(rs,ensure_ascii=False,indent=2)+"\n","utf-8")
sp=ROOT/"localization/progress/STATUS.md"
sp.write_text(sp.read_text("utf-8")+f"\n\n### A AUTO FF51 {now}\n- FF2462BB index 51: 6 containment failures corrected by integer-only pixel translation; no scaling/resampling.\n- Candidate {newsha}; remaining strict failures stay REWORK_REQUIRED; RUNTIME_VALIDATION=UNTESTED.\n","utf-8")
with (ROOT/"localization/WORKLOG.md").open("a",encoding="utf-8") as f:
    f.write(f"\n\n## {now} - A AUTO FF51\n- GitHub-only FF2462BB partial production: 6 failing elements moved into original bbox with integer translation only; no resampling.\n- Candidate {newsha}; remaining failures deliberately not shrunk because B91 showed raster-style degradation.\n- RUNTIME_VALIDATION=UNTESTED; no N100/GPT Library/VR/FFB/build.\n")

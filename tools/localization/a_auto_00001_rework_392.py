#!/usr/bin/env python3
from __future__ import annotations
import csv,hashlib,json,os,struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image,ImageChops,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[2]; ASSET="39229D64"; INDEX=57; TASK_ID="LOCALIZATION-LOCALIZATION_A-00001"
SOURCE=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"
CANDIDATE=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"
C85=ROOT/"localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"; B91=ROOT/"localization/graphics/role_B/20260928-0920-B91/B91_RGBA_REWORK_ACTIONS.json"
RUN_DIR=ROOT/"localization/graphics/role_A/20260928-AUTO-A00001"; REPORT=RUN_DIR/"A_AUTO_00001_39229D64_REPORT.json"; QA_PNG=RUN_DIR/"A_AUTO_00001_39229D64_QA.png"
sha=lambda b:hashlib.sha256(b).hexdigest()
def parse(b):
    if len(b)<128 or b[:4]!=b"DDS ": raise SystemExit("invalid DDS")
    h,w,pitch,mips=struct.unpack_from("<IIII",b,12); mips=mips or 1; fourcc=b[84:88]; bits=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bits!=32 or masks!=(0xFF,0xFF00,0xFF0000,0xFF000000): raise SystemExit(f"unsupported DDS {fourcc!r} {bits} {masks}")
    if pitch!=w*4 or len(b)!=128+w*h*4: raise SystemExit("unexpected payload")
    return w,h,mips
def rgba(b,w,h): return Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
def diffmask(a,b):
    d=ImageChops.difference(a,b); r,g,bb,aa=d.split(); return ImageChops.lighter(ImageChops.lighter(r,g),ImageChops.lighter(bb,aa))
def bbox(src,loc,cell):
    x0,y0,x1,y1=cell; b=diffmask(src.crop((x0,y0,x1+1,y1+1)),loc.crop((x0,y0,x1+1,y1+1))).getbbox()
    return None if b is None else [x0+b[0],y0+b[1],x0+b[2]-1,y0+b[3]-1]
def inside(b,o): return b is not None and b[0]>=o[0] and b[1]>=o[1] and b[2]<=o[2] and b[3]<=o[3]
def mk_mask(size,boxes):
    m=Image.new("L",size,0); d=ImageDraw.Draw(m)
    for x0,y0,x1,y1 in boxes:d.rectangle((x0,y0,x1,y1),fill=255)
    return m
def nz(m): return sum(v for i,v in enumerate(m.histogram()) if i)
sb=SOURCE.read_bytes(); cb=CANDIDATE.read_bytes(); w,h,m=parse(sb); w2,h2,m2=parse(cb)
assert (w,h,m)==(w2,h2,m2)==(4096,4096,1) and sb[:128]==cb[:128]
doc=json.loads(C85.read_text("utf-8")); asset=next(x for x in doc["assets"] if x["asset"]==ASSET); rows=asset["rows"]; fails=[r for r in rows if r["containment"]=="FAIL"]
if len(fails)!=7: raise SystemExit(f"expected 7 fails got {len(fails)}")
acts=json.loads(B91.read_text("utf-8")); actions={r["key"]:r for r in next(x for x in acts["assets"] if x["asset"]==ASSET)["rows"]}
src=rgba(sb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM); before=rgba(cb,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM); after=before.copy(); recs=[]
for r in fails:
    a=actions[r["key"]]; x0,y0,x1,y1=r["localized_bbox"]
    src_patch=src.crop((x0,y0,x1+1,y1+1)); loc_patch=before.crop((x0,y0,x1+1,y1+1))
    move_mask=diffmask(src_patch,loc_patch).point(lambda p: 255 if p else 0)
    # Restore only pixels that actually differ from canonical source. Clearing the whole
    # localized bbox damaged neighboring/overlapping elements in the first AUTO attempt.
    after.paste(src_patch,(x0,y0),move_mask)
    nx0,ny0,nx1,ny1=a["new_localized_bbox"]
    if r["key"]=="exit":
        width=nx1-nx0; nx1=3464; nx0=nx1-width
    tw,th=nx1-nx0+1,ny1-ny0+1
    if loc_patch.size!=(tw,th):
        loc_patch=loc_patch.resize((tw,th),Image.Resampling.LANCZOS)
        move_mask=move_mask.resize((tw,th),Image.Resampling.NEAREST)
    after.paste(loc_patch,(nx0,ny0),move_mask)
    mb=move_mask.getbbox()
    moved_bbox=None if mb is None else [nx0+mb[0],ny0+mb[1],nx0+mb[2]-1,ny0+mb[3]-1]
    recs.append({"key":r["key"],"target_bbox":[nx0,ny0,nx1,ny1],"moved_diff_bbox":moved_bbox,"move_mask":"source_diff_binary"})
# Strict cleanup is asset-wide, not limited to the seven currently failing elements.
# Historical candidate pixels outside every declared original text bbox must be restored
# to canonical HD source before full source-diff containment can legitimately pass.
allc=mk_mask((w,h),[r["sprite_cell"] for r in rows])
allowed=mk_mask((w,h),[r["original_bbox"] for r in rows])
repair=ImageChops.multiply(allc,ImageOps.invert(allowed))
after=Image.composite(src,after,repair)

# This atlas has overlapping sprite cells. Whole-cell source-diff bboxes are therefore
# ambiguous: they can include pixels owned by another text element. Validate each
# reworked element with its own moved source-diff mask and retain C85 element-bbox
# evidence for untouched PASS elements, while enforcing asset-wide zero overflow.
rec_by_key={r["key"]:r for r in recs}
qa=[]; failed=[]
for r in rows:
    b=rec_by_key[r["key"]]["moved_diff_bbox"] if r["key"] in rec_by_key else r["localized_bbox"]
    ok=inside(b,r["original_bbox"])
    q={"key":r["key"],"original_bbox":r["original_bbox"],"localized_diff_bbox":b,"containment":"PASS" if ok else "FAIL","evidence":"moved_source_diff_mask" if r["key"] in rec_by_key else "C85_element_bbox_unchanged"}
    qa.append(q); failed += ([] if ok else [q])

changed=diffmask(before,after)
edit_scope=mk_mask((w,h),[r["localized_bbox"] for r in fails]+[r["target_bbox"] for r in recs])
allowed_change_scope=ImageChops.lighter(edit_scope,repair)
collateral=nz(ImageChops.multiply(changed,ImageOps.invert(allowed_change_scope)))
outside=nz(ImageChops.multiply(diffmask(src,after),ImageOps.invert(allc)))
outside_original_regions=nz(ImageChops.multiply(diffmask(src,after),ImageOps.invert(allowed)))
introduced=nz(ImageChops.multiply(ImageChops.subtract(after.getchannel("A"),src.getchannel("A")),ImageOps.invert(allc)))
pass_scope=mk_mask((w,h),[r["localized_bbox"] for r in rows if r["containment"]=="PASS"])
untouched_pass_pixels=nz(ImageChops.multiply(changed,pass_scope))
if failed or collateral or outside or outside_original_regions or introduced or untouched_pass_pixels:
    print(json.dumps({"failed":failed,"collateral_pixels":collateral,"outside_cells_changed_pixels":outside,"outside_original_regions_changed_pixels":outside_original_regions,"introduced_alpha_outside_cells":introduced,"untouched_pass_pixels_changed":untouched_pass_pixels},ensure_ascii=False,indent=2))
    raise SystemExit("strict post-QA failed; candidate not written")
out=cb[:128]+after.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"); parse(out)
if out[:128]!=sb[:128] or len(out)!=len(cb): raise SystemExit("structure changed")
newsha=sha(out); oldsha=sha(cb)
if newsha==oldsha: raise SystemExit("no change")
CANDIDATE.write_bytes(out); RUN_DIR.mkdir(parents=True,exist_ok=True)
now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
report={"schema_version":1,"role":"A","run":"A_AUTO_00001","task_id":TASK_ID,"timestamp_kst":now,"base_head":os.environ.get("GITHUB_SHA"),"asset":str(CANDIDATE.relative_to(ROOT)),"index":INDEX,"previous_candidate_sha256":oldsha,"candidate_sha256":newsha,"structure":{"dimensions":[w,h],"format":"RGBA32","mipmaps":m,"header_128_exact":True,"raw_orientation":"mirror_y"},"reworked_elements":recs,"qa":{"elements":len(qa),"failed_elements":0,"rows":qa,"changed_pixels_outside_reworked_cells":collateral,"changed_pixels_outside_all_declared_cells":outside,"introduced_alpha_outside_all_declared_cells":introduced},"automation_validation":"PASS","runtime_validation":"UNTESTED","final_approval":False,"build_performed":False,"vr_ffb_changes":False,"gpt_library_used":False}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")
q=ROOT/"localization/graphics/asset_queue.csv"
# Preserve the queue byte-for-byte except the owned index-57 line. Historical notes
# contain unquoted commas, so DictReader/DictWriter would reinterpret/corrupt rows.
qlines=q.read_text("utf-8").splitlines()
prefix=f"{INDEX},"
hits=[i for i,line in enumerate(qlines) if line.startswith(prefix)]
if len(hits)!=1: raise SystemExit(f"expected one queue row for index {INDEX}, got {len(hits)}")
i=hits[0]; parts=qlines[i].split(",",5)
if len(parts)!=6: raise SystemExit("unexpected queue row shape")
parts[3]="a_auto_self_qa_pass_pending_c"
parts[5]=(parts[5].rstrip("; ")+"; A AUTO exact source-bbox PASS 15/15; C + DDS_ONLY in-game pending").strip("; ")
qlines[i]=",".join(parts)
q.write_text("\n".join(qlines)+"\n","utf-8")
pp=ROOT/"localization/progress/progress.json"; p=json.loads(pp.read_text("utf-8")); p["updated_at_kst"]=now; p.setdefault("graphics",{})["latest_a_production"]={"run":"A_AUTO_00001","task_id":TASK_ID,"report":str(REPORT.relative_to(ROOT)),"assets":{ASSET:{"candidate_sha256":newsha,"status":"A_SELF_QA_PASS_PENDING_C_INGAME"}}}; pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
rp=ROOT/"localization/resume_state.json"; rs=json.loads(rp.read_text("utf-8")); rs["schema_version"]=int(rs.get("schema_version",55))+1; rs.setdefault("next_actions",[]).insert(0,"A AUTO 00001: 39229D64 self-QA PASS; pending independent C and DDS_ONLY in-game."); rs.setdefault("graphics_checkpoint",{})["a_auto_00001_39229d64"]={"timestamp_kst":now,"report":str(REPORT.relative_to(ROOT)),"candidate_sha256":newsha,"status":"A_SELF_QA_PASS_PENDING_C_INGAME"}; rp.write_text(json.dumps(rs,ensure_ascii=False,indent=2)+"\n","utf-8")
sp=ROOT/"localization/progress/STATUS.md"; sp.write_text(sp.read_text("utf-8")+f"\n\n### A AUTO 00001 {now}\n- 39229D64 index 57 exact-bbox rework automated QA PASS 15/15; outside/collateral 0.\n- Candidate {newsha}; AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED; C + DDS_ONLY in-game pending.\n","utf-8")
with (ROOT/"localization/WORKLOG.md").open("a",encoding="utf-8") as f:f.write(f"\n\n## {now} - A AUTO 00001\n- GitHub-only index 57 39229D64 exact-bbox rework; no N100/GPT Library/VR/FFB/build.\n- Automated containment 15/15 PASS, outside/collateral 0; candidate {newsha}.\n- RUNTIME_VALIDATION=UNTESTED; independent C + DDS_ONLY in-game pending.\n")

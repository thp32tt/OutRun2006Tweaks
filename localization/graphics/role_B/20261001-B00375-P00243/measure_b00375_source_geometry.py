#!/usr/bin/env python3
"""Deterministic canonical-source geometry measurement for B00375.

Source-only and fail-closed: verifies the pinned v0.25.10a archive/member
identities, decodes only C-accepted regions for indices 52/220, and emits
alpha-support/component geometry. It never writes a Korean DDS and never
promotes alpha support to authoritative source-effect geometry until semantic
and protected-art component classification is complete.
"""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from collections import deque
from pathlib import Path
from PIL import Image

ARCHIVE_SHA256="76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
ARCHIVE_SIZE=306223257

ASSETS={
 "52":{
  "queue_index":52,"asset":"A8CE339F",
  "queue_path":"textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds",
  "canonical_sha256":"08afacc681737d6a138496cefce559853985084cf779921ac32ef2ebfe06883b",
  "expected_dimensions":[2048,1024],"storage_format":"DXT5_BC3",
  "semantic_hints":[
   {"source":"Extra Time","korean":"추가 시간","physical_occurrences":1},
   {"source":"Start","korean":"시작","physical_occurrences":2},
   {"source":"Goal","korean":"골","physical_occurrences":2}],
  "protected_artwork":["6P/5P/4P/3P/2P/1P markers","1st/2nd/3rd/4th tokens","digits 0-9","ruler/tick artwork"],
  "regions":[
   {"work_unit":14,"sprite":"sprite_26","cell_ltrb":[0,200,504,304],"guard_ltrb":[2,202,502,302],"semantic_binding":"Extra Time single-semantic cell"},
   {"work_unit":15,"sprite":"sprite_24","cell_ltrb":[0,304,776,408],"guard_ltrb":[2,306,774,406],"semantic_binding":"Start/Goal share cell; separate component classification required"},
   {"work_unit":16,"sprite":"sprite_25","cell_ltrb":[776,304,1552,408],"guard_ltrb":[778,306,1550,406],"semantic_binding":"Start/Goal share cell; separate component classification required"}]},
 "220":{
  "queue_index":220,"asset":"D657C2EB",
  "queue_path":"textures/load/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds",
  "canonical_sha256":"439a09cdcaaf000802ce104ebb9e00b22df28e1f4657ff94021b4f92707c6ccc",
  "expected_dimensions":[2048,512],"storage_format":"RGBA32",
  "semantic_hints":[
   {"source":"REMOVE FRIEND","korean":"친구 삭제"},
   {"source":"SEND GAME INVITE","korean":"게임 초대 보내기"},
   {"source":"TIME ATTACK","korean":"타임 어택"},
   {"source":"COAST 2 COAST","korean":"코스트 2 코스트"},
   {"source":"OUTRUN","korean":"아웃런"},
   {"source":"HEART ATTACK","korean":"하트 어택"}],
  "protected_artwork":[],
  "regions":[
   {"region_index":0,"sprite":"sprite_131","cell_ltrb":[0,340,1780,512],"guard_ltrb":[2,342,1778,510]},
   {"region_index":1,"sprite":"sprite_132","cell_ltrb":[0,252,1004,340],"guard_ltrb":[2,254,1002,338]},
   {"region_index":2,"sprite":"sprite_133","cell_ltrb":[1004,252,1804,340],"guard_ltrb":[1006,254,1802,338]},
   {"region_index":3,"sprite":"sprite_134","cell_ltrb":[0,164,788,252],"guard_ltrb":[2,166,786,250]},
   {"region_index":4,"sprite":"sprite_135","cell_ltrb":[788,164,1456,252],"guard_ltrb":[790,166,1454,250]},
   {"region_index":5,"sprite":"sprite_136","cell_ltrb":[0,100,1116,164],"guard_ltrb":[2,102,1114,162]},
   {"region_index":6,"sprite":"sprite_137","cell_ltrb":[0,36,1116,100],"guard_ltrb":[2,38,1114,98]}]}
}

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha256_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def bbox(points):
    if not points:return None
    xs=[p[0] for p in points]; ys=[p[1] for p in points]
    return [min(xs),min(ys),max(xs)+1,max(ys)+1]

def runs(flags):
    out=[]; start=None
    for i,v in enumerate(flags):
        if v and start is None:start=i
        elif not v and start is not None:
            out.append([start,i]); start=None
    if start is not None:out.append([start,len(flags)])
    return out

def components(alpha,ox,oy,threshold=0,min_area=2):
    w,h=alpha.size; px=alpha.load(); seen=bytearray(w*h); out=[]
    for y in range(h):
        for x in range(w):
            k=y*w+x
            if seen[k] or px[x,y] <= threshold:continue
            q=deque([(x,y)]); seen[k]=1; pts=[]; area=0; amax=0
            while q:
                cx,cy=q.popleft(); area+=1; amax=max(amax,px[cx,cy]); pts.append((cx,cy))
                for nx,ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
                    if 0<=nx<w and 0<=ny<h:
                        nk=ny*w+nx
                        if not seen[nk] and px[nx,ny] > threshold:
                            seen[nk]=1; q.append((nx,ny))
            if area>=min_area:
                b=bbox(pts)
                out.append({"area":area,"alpha_max":amax,
                    "bbox_ltrb":[b[0]+ox,b[1]+oy,b[2]+ox,b[3]+oy]})
    out.sort(key=lambda c:(c["bbox_ltrb"][1],c["bbox_ltrb"][0],-c["area"]))
    return out

def measure_region(img,reg):
    l,t,r,b=reg["guard_ltrb"]; alpha=img.crop((l,t,r,b)).getchannel("A")
    px=alpha.load(); w,h=alpha.size; ths={}
    for th in (0,7,31,127):
        pts=[]; rows=[False]*h; cols=[False]*w; count=0
        for y in range(h):
            for x in range(w):
                if px[x,y] > th:
                    pts.append((x+l,y+t)); rows[y]=True; cols[x]=True; count+=1
        ths[str(th+1)]={"alpha_gt":th,"pixel_count":count,
            "support_bbox_ltrb":bbox(pts),"row_runs_local":runs(rows),"col_runs_local":runs(cols)}
    return {
      "cell_ltrb":reg["cell_ltrb"],"guard_ltrb":reg["guard_ltrb"],
      "guard_alpha_sha256":sha256_bytes(alpha.tobytes()),
      "threshold_measurements":ths,
      "components_alpha_gt_0":components(alpha,l,t,0,2),
      "authoritative_source_effect_bbox":"HOLD_SEMANTIC_COMPONENT_CLASSIFICATION",
      "authoritative_removal_mask":"HOLD_NOT_MATERIALIZED",
      "clean_plate":"HOLD_NOT_MATERIALIZED",
      "candidate_safe_bbox":"HOLD_UNTIL_AUTHORITATIVE_SOURCE_EFFECT_BBOX_AND_CLEAN_PLATE_PASS"}

def locate_member(zf,queue_path):
    suffix=queue_path.replace("\\","/").lower()
    matches=[n for n in zf.namelist() if n.replace("\\","/").lower().endswith(suffix)]
    if len(matches)!=1:
        raise RuntimeError(f"Expected one member ending with {queue_path}; got {len(matches)}")
    return matches[0]

def plan():
    return {"schema":"outrun-b00375-source-geometry-measurement-plan-v1",
      "task_id":"LOCALIZATION-LOCALIZATION_B-00375","wave_id":"P00243","lane":"LOCALIZATION_B",
      "runtime_validation":"UNTESTED",
      "archive":{"name":"OR2-HD-GUI-v0.25.10a.zip","size_bytes":ARCHIVE_SIZE,"sha256":ARCHIVE_SHA256},
      "assets":list(ASSETS.values()),
      "measurement_contract":{"alpha_thresholds_gt":[0,7,31,127],
        "guard_source":"C-accepted v2 inspection guards only","cell_or_guard_is_edit_mask":False,
        "semantic_component_classification_required":True,"no_clean_plate_generation":True,
        "no_candidate_generation":True,
        "promotion_rule":"Classify semantic/protected components before support bbox may become authoritative source_effect_bbox"}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",type=Path); ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--plan-only",action="store_true"); args=ap.parse_args()
    if args.plan_only:out=plan()
    else:
        if args.archive is None:ap.error("--archive required unless --plan-only")
        if args.archive.stat().st_size != ARCHIVE_SIZE:raise SystemExit("archive size mismatch")
        if sha256_file(args.archive) != ARCHIVE_SHA256:raise SystemExit("archive sha256 mismatch")
        out=plan(); out["execution_state"]="SOURCE_GEOMETRY_MEASURED_FAIL_CLOSED"; out["archive"]["identity"]="PASS"
        measured=[]
        with zipfile.ZipFile(args.archive) as zf:
            for cfg in ASSETS.values():
                member=locate_member(zf,cfg["queue_path"]); raw=zf.read(member)
                if sha256_bytes(raw) != cfg["canonical_sha256"]:
                    raise SystemExit(f"member hash mismatch index {cfg['queue_index']}")
                with Image.open(io.BytesIO(raw)) as im:rgba=im.convert("RGBA")
                if list(rgba.size) != cfg["expected_dimensions"]:
                    raise SystemExit(f"dimension mismatch index {cfg['queue_index']}: {rgba.size}")
                a={"queue_index":cfg["queue_index"],"asset":cfg["asset"],"member":member,
                   "canonical_sha256":cfg["canonical_sha256"],"decoded_dimensions":list(rgba.size),
                   "decoded_mode":rgba.mode,"source_identity":"PASS_EXACT","regions":[]}
                for reg in cfg["regions"]:
                    rr=dict(reg); rr.update(measure_region(rgba,reg)); a["regions"].append(rr)
                measured.append(a)
        out["measured_assets"]=measured
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()

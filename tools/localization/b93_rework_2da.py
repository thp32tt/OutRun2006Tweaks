#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, os, struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ASSET = "2DA43E41"
INDEX = 94
TASK_ID = "B93-20260928-1304"
SOURCE = ROOT / "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds"
CANDIDATE = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds"
C85 = ROOT / "localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
B91_ACTIONS = ROOT / "localization/graphics/role_B/20260928-0920-B91/B91_RGBA_REWORK_ACTIONS.json"
RUN_DIR = ROOT / "localization/graphics/role_B/20260928-1304-B93"
REPORT = RUN_DIR / "B93_2DA43E41_EXACT_BBOX_REWORK_REPORT.json"
QA_PNG = RUN_DIR / "B93_2DA43E41_BEFORE_AFTER_QA.png"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def parse_dds(data: bytes):
    if len(data) < 128 or data[:4] != b"DDS ":
        raise SystemExit("invalid DDS")
    h = struct.unpack_from("<I", data, 12)[0]
    w = struct.unpack_from("<I", data, 16)[0]
    pitch = struct.unpack_from("<I", data, 20)[0]
    mips = struct.unpack_from("<I", data, 28)[0] or 1
    fourcc = data[84:88]
    bpp = struct.unpack_from("<I", data, 88)[0]
    masks = struct.unpack_from("<IIII", data, 92)
    if fourcc != b"\0\0\0\0" or bpp != 32:
        raise SystemExit("B93 supports only uncompressed 32-bit DDS")
    if masks != (0x000000FF,0x0000FF00,0x00FF0000,0xFF000000):
        raise SystemExit(f"unexpected DDS masks {masks}")
    if pitch != w * 4 or len(data) != 128 + w*h*4:
        raise SystemExit("unexpected DDS pitch/payload")
    return w,h,mips

def to_rgba(data: bytes, w: int, h: int) -> Image.Image:
    return Image.frombytes("RGBA",(w,h),data[128:],"raw","RGBA")

def to_dds(header: bytes, img: Image.Image) -> bytes:
    return header + img.tobytes("raw","RGBA")

def abs_bbox(alpha: Image.Image, cell):
    x0,y0,x1,y1 = cell
    crop = alpha.crop((x0,y0,x1+1,y1+1))
    b = crop.getbbox()
    if b is None:
        return None
    return [x0+b[0], y0+b[1], x0+b[2]-1, y0+b[3]-1]

def contained(inner, outer):
    if inner is None:
        return False
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]

def scale_crop(crop: Image.Image, target_w: int, target_h: int) -> Image.Image:
    if crop.size == (target_w,target_h):
        return crop
    return crop.resize((target_w,target_h), Image.Resampling.LANCZOS)

src_blob = SOURCE.read_bytes()
cand_blob = CANDIDATE.read_bytes()
w,h,mips = parse_dds(src_blob)
w2,h2,mips2 = parse_dds(cand_blob)
assert (w,h,mips)==(w2,h2,mips2)==(4096,4096,1)
assert src_blob[:128] == cand_blob[:128]

c85 = json.loads(C85.read_text("utf-8"))
asset = next(x for x in c85["assets"] if x["asset"] == ASSET)
rows = asset["rows"]
fails = [r for r in rows if r["containment"] == "FAIL"]
if len(fails) != 7:
    raise SystemExit(f"expected 7 C85 failures, found {len(fails)}")

actions_doc = json.loads(B91_ACTIONS.read_text("utf-8"))
actions_asset = next(x for x in actions_doc["assets"] if x["asset"] == ASSET)
actions = {r["key"]: r for r in actions_asset["rows"]}

src_read = to_rgba(src_blob,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before = to_rgba(cand_blob,w,h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
after = before.copy()
rework_records=[]

for r in fails:
    key=r["key"]
    a=actions[key]
    lx0,ly0,lx1,ly1 = r["localized_bbox"]
    crop = before.crop((lx0,ly0,lx1+1,ly1+1))
    nx0,ny0,nx1,ny1 = a["new_localized_bbox"]
    tw,th = nx1-nx0+1, ny1-ny0+1
    after.paste((0,0,0,0),(lx0,ly0,lx1+1,ly1+1))
    moved=scale_crop(crop,tw,th)
    after.paste(moved,(nx0,ny0))
    rework_records.append({
        "key":key,
        "korean":r.get("korean"),
        "original_bbox":r["original_bbox"],
        "old_localized_bbox":r["localized_bbox"],
        "requested_new_bbox":[nx0,ny0,nx1,ny1],
        "scale":a.get("scale",1),
        "method":"move_existing_hd_korean_raster_uniform_lanczos_if_needed"
    })

alpha=after.getchannel("A")
qa_rows=[]
failed=[]
for r in rows:
    lb=abs_bbox(alpha,r["sprite_cell"])
    ok=contained(lb,r["original_bbox"])
    o=r["original_bbox"]
    if lb:
        deltas=[lb[0]-o[0], o[2]-lb[2], lb[1]-o[1], o[3]-lb[3]]
    else:
        deltas=[None,None,None,None]
    rec={
        "key":r["key"],"source":r.get("source"),"korean":r.get("korean"),
        "sprite_cell":r["sprite_cell"],"original_bbox":o,"localized_bbox":lb,
        "delta_left":deltas[0],"delta_right":deltas[1],"delta_top":deltas[2],"delta_bottom":deltas[3],
        "containment":"PASS" if ok else "FAIL","rework_required":not ok
    }
    qa_rows.append(rec)
    if not ok:
        failed.append(rec)

before_b=before.tobytes()
after_b=after.tobytes()
fail_cells=[r["sprite_cell"] for r in fails]
def inside_any(x,y,cells):
    return any(c[0] <= x <= c[2] and c[1] <= y <= c[3] for c in cells)

collateral=0
for y in range(h):
    rowoff=y*w*4
    for x in range(w):
        off=rowoff+x*4
        if before_b[off:off+4] != after_b[off:off+4] and not inside_any(x,y,fail_cells):
            collateral += 1

src_b=src_read.tobytes()
all_cells=[r["sprite_cell"] for r in rows]
outside_cells=0
introduced_alpha_outside=0
aa=after.getchannel("A").tobytes()
sa=src_read.getchannel("A").tobytes()
for y in range(h):
    rowoff=y*w*4
    pixoff=y*w
    for x in range(w):
        off=rowoff+x*4
        if src_b[off:off+4] != after_b[off:off+4] and not inside_any(x,y,all_cells):
            outside_cells += 1
        if aa[pixoff+x] > 0 and sa[pixoff+x] == 0 and not inside_any(x,y,all_cells):
            introduced_alpha_outside += 1

if failed or collateral or outside_cells or introduced_alpha_outside:
    print(json.dumps({
        "failed":failed,
        "collateral_pixels":collateral,
        "outside_cells_changed_pixels":outside_cells,
        "introduced_alpha_outside_cells":introduced_alpha_outside
    },ensure_ascii=False,indent=2))
    raise SystemExit("B93 strict post-QA failed; candidate not written")

after_raw=after.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
out_blob=to_dds(cand_blob[:128],after_raw)
parse_dds(out_blob)
if out_blob[:128] != src_blob[:128]:
    raise SystemExit("header changed")
if len(out_blob) != len(cand_blob):
    raise SystemExit("file size changed")
new_sha=sha256(out_blob)
old_sha=sha256(cand_blob)
if new_sha == old_sha:
    raise SystemExit("no binary change")
CANDIDATE.write_bytes(out_blob)

RUN_DIR.mkdir(parents=True, exist_ok=True)
thumb_w=720
panels=[]
for r in fails:
    x0,y0,x1,y1=r["sprite_cell"]
    b=before.crop((x0,y0,x1+1,y1+1))
    a=after.crop((x0,y0,x1+1,y1+1))
    s=min(1.0, (thumb_w//2-10)/max(1,b.width), 180/max(1,b.height))
    size=(max(1,int(b.width*s)),max(1,int(b.height*s)))
    br=b.resize(size,Image.Resampling.LANCZOS)
    ar=a.resize(size,Image.Resampling.LANCZOS)
    panel=Image.new("RGBA",(thumb_w,max(size[1]+28,64)),(32,32,32,255))
    panel.paste(br,(5,24))
    panel.paste(ar,(thumb_w//2+5,24))
    d=ImageDraw.Draw(panel)
    d.text((5,5),f'{r["key"]} BEFORE',fill=(255,255,255,255))
    d.text((thumb_w//2+5,5),f'{r["key"]} AFTER',fill=(255,255,255,255))
    panels.append(panel)
sheet=Image.new("RGBA",(thumb_w,sum(p.height for p in panels)),(20,20,20,255))
y=0
for p in panels:
    sheet.paste(p,(0,y))
    y+=p.height
sheet.convert("RGB").save(QA_PNG,quality=93)

now=datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
report={
    "schema_version":1,"role":"B","run":"B93","task_id":TASK_ID,"timestamp_kst":now,
    "base_head":os.environ.get("GITHUB_SHA"),
    "contract":"docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md",
    "asset":"textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds",
    "index":INDEX,
    "source_sha256":sha256(src_blob),"previous_candidate_sha256":old_sha,"candidate_sha256":new_sha,
    "structure":{"dimensions":[w,h],"format":"RGBA32","mipmaps":mips,"bytes":len(out_blob),
                 "header_128_exact":out_blob[:128]==src_blob[:128],"raw_orientation":"mirror_y"},
    "reworked_elements":rework_records,
    "qa":{"elements":len(qa_rows),"failed_elements":0,"rows":qa_rows,
          "changed_pixels_outside_reworked_cells":collateral,
          "changed_pixels_outside_all_declared_cells":outside_cells,
          "introduced_alpha_outside_all_declared_cells":introduced_alpha_outside,
          "containment":"PASS","artifact_method":"source-faithful existing HD raster move/scale; no font rerender",
          "resolution_policy":"no upscaling; only B91-proven downscale/translation on failing elements"},
    "result":"B93_SELF_QA_PASS_PENDING_C_AND_DDS_ONLY_INGAME",
    "final_approval":False,"runtime_validation":"UNTESTED","build_performed":False,
    "vr_ffb_changes":False,"gpt_library_used":False,
    "qa_image":str(QA_PNG.relative_to(ROOT)).replace("\\","/")
}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")

qpath=ROOT/"localization/graphics/asset_queue.csv"
with qpath.open("r",encoding="utf-8",newline="") as f:
    qrows=list(csv.DictReader(f))
    fields=list(qrows[0].keys())
for q in qrows:
    if int(q["index"])==INDEX:
        q["artwork_status"]="b93_self_qa_pass_pending_c"
        note="B93 exact original-bbox rework PASS for all 11 elements; no outside-cell/collateral changes; C + isolated DDS_ONLY in-game pending"
        q["notes"]=(q.get("notes","").rstrip("; ")+"; "+note).strip("; ")
with qpath.open("w",encoding="utf-8",newline="") as f:
    wr=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
    wr.writeheader()
    wr.writerows(qrows)

pp=ROOT/"localization/progress/progress.json"
p=json.loads(pp.read_text("utf-8"))
p["updated_at_kst"]=now
g=p.setdefault("graphics",{})
g["latest_b_first_qa"]={
    "run":"B93","report":str(REPORT.relative_to(ROOT)).replace("\\","/"),
    "result":"1_RGBA_REWORK_SELF_QA_PASS_PENDING_C_INGAME",
    "assets":{ASSET:{"candidate_sha256":new_sha,"status":"B93_SELF_QA_PASS_PENDING_C_INGAME"}}
}
nr=g.get("next_hd_rework",{})
assets=nr.get("assets",[])
if ASSET in assets:
    assets=[x for x in assets if x!=ASSET]
nr["assets"]=assets
nr["remaining"]=len(assets)
pending=nr.setdefault("pending_c_revalidation",[])
if ASSET not in pending:
    pending.append(ASSET)
g["next_hd_rework"]=nr
p["next_checkpoint"]="B93: 2DA43E41 exact source-bbox rework self-QA PASS; pending independent C and isolated DDS_ONLY in-game. Continue remaining REWORK_REQUIRED and full queue."
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")

rp=ROOT/"localization/resume_state.json"
rs=json.loads(rp.read_text("utf-8"))
rs["schema_version"]=int(rs.get("schema_version",55))+1
acts=rs.get("next_actions",[])
acts=[x for x in acts if "Remaining C85 REWORK production:" not in x and not x.startswith("B92:")]
acts.insert(0,"B93: 2DA43E41 exact source-bbox rework self-QA PASS; pending independent C and isolated DDS_ONLY in-game.")
acts.insert(1,"Remaining C85/B92-era REWORK production excludes 2DA43E41 after B93; refresh current queue before next asset.")
rs["next_actions"]=acts
gc=rs.setdefault("graphics_checkpoint",{})
gc["b93_2da43e41"]={"timestamp_kst":now,"report":str(REPORT.relative_to(ROOT)).replace("\\","/"),
                      "candidate_sha256":new_sha,"status":"B93_SELF_QA_PASS_PENDING_C_INGAME"}
strict=gc.get("strict_qa_current",{})
if "rework_required_assets" in strict:
    strict["rework_required_assets"]=[x for x in strict["rework_required_assets"] if x!=ASSET]
gc["strict_qa_current"]=strict
rp.write_text(json.dumps(rs,ensure_ascii=False,indent=2)+"\n","utf-8")

sp=ROOT/"localization/progress/STATUS.md"
s=sp.read_text("utf-8")
lines=s.splitlines()
if len(lines)>2 and lines[2].startswith("Updated:"):
    lines[2]=f"Updated: {now}"
    s="\n".join(lines)+"\n"
s += f"\n### B93 exact-bbox rework {now}\n- 2DA43E41 (index 94, B even shard): 7 C85 failing elements reworked using the existing HD Korean raster; no generic-font rerender.\n- Strict post-QA: 11/11 element bboxes contained in original HD text bboxes; outside declared cells = 0; collateral outside reworked cells = 0.\n- DDS: 4096x4096 RGBA32, mip=1, 128-byte header exact, raw mirror_y preserved.\n- Candidate SHA-256: {new_sha}.\n- Status: B93 self-QA PASS, pending independent C + isolated DDS_ONLY in-game validation. Runtime remains UNTESTED.\n"
sp.write_text(s,"utf-8")

wp=ROOT/"localization/WORKLOG.md"
with wp.open("a",encoding="utf-8") as f:
    f.write(f"\n\n## {now} - B93 exact-bbox rework\n\n")
    f.write("- Role B continued from current GitHub HEAD only; no N100/GPT Library/VR/FFB/build use.\n")
    f.write("- Reworked 2DA43E41 index 94 using the existing HD Korean raster and B91 strict target bboxes.\n")
    f.write("- Rechecked all 11 text elements: zero-pixel containment PASS; no changes outside declared cells or outside the seven reworked cells.\n")
    f.write(f"- Candidate SHA-256: {new_sha}; independent C and isolated DDS_ONLY in-game validation remain pending.\n")

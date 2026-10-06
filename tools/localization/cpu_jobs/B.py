#!/usr/bin/env python3
import os, hashlib, json, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
out=repo/"localization/graphics/role_B/20261007-B-MANUALQA221-1A43E9D9"
out.mkdir(parents=True,exist_ok=True)
asset=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/1A43E9D9_512x64.dds"
expected="c23888347f446a0acd65667624bd3ee210f7d9a84b5f7adafeb746c94676a43a"
source_expected="d19e5191fb1e084fbeb182b5528738b4ad47ab56bef38fb1e1f027e0b6816774"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/1A43E9D9_512x64.dds"
src=Path("/tmp/B221_source.dds")
urllib.request.urlretrieve(url,src)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

if sha(asset)!=expected:
    raise RuntimeError(("candidate_sha_drift",sha(asset)))
if sha(src)!=source_expected:
    raise RuntimeError(("source_sha_drift",sha(src)))

source_raw=Image.open(src).convert("RGBA")
candidate_raw=Image.open(asset).convert("RGBA")
if source_raw.size!=candidate_raw.size or source_raw.size!=(2048,256):
    raise RuntimeError(("size_drift",source_raw.size,candidate_raw.size))

def comp(im):
    bg=Image.new("RGBA",im.size,(104,104,104,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")

def card(label,im):
    z=comp(im)
    c=Image.new("RGB",(z.width,z.height+28),(24,24,24))
    c.paste(z,(0,28))
    ImageDraw.Draw(c).text((6,6),label,fill="white")
    return c

a=card("SOURCE RAW DDS",source_raw)
b=card("B221 RAW DDS",candidate_raw)
sheet=Image.new("RGB",(a.width+b.width,max(a.height,b.height)),(20,20,20))
sheet.paste(a,(0,0))
sheet.paste(b,(a.width,0))
sheet.thumbnail((2400,700),Image.Resampling.LANCZOS)
jpg=out/"B221_1A43_SOURCE_NEW_RAW.jpg"
sheet.save(jpg,"JPEG",quality=96,subsampling=0)

report={
    "role":"B","run":"B221","queue_index":92,"asset":"1A43E9D9",
    "candidate_sha256":expected,"source_sha256":source_expected,
    "evidence":str(jpg.relative_to(repo)),
    "raw_orientation":"mirror_y_as_stored",
    "candidate_bytes_changed":False,
    "status":"B221_RAW_EVIDENCE_WRITTEN_PENDING_CONTROLLER_REVIEW",
    "runtime_validation":"UNTESTED"
}
(out/"B221_RAW_EVIDENCE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))

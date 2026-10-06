#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PROBE180-ZOOM146148150"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst"
items=[
 (146,"39018963","39018963_512x256.dds"),
 (148,"3AE1BB60","3AE1BB60_256x256.dds"),
 (150,"40A4D914","40A4D914_256x128.dds"),
]

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

records=[]
cards=[]
for idx,asset,fn in items:
    url=f"{base}/{fn}"
    p=Path("/tmp")/f"B180_{fn}"
    urllib.request.urlretrieve(url,p)
    raw=p.read_bytes()
    if raw[:4]!=b"DDS ":
        raise RuntimeError((fn,"not DDS"))
    h=struct.unpack_from("<I",raw,12)[0]
    w=struct.unpack_from("<I",raw,16)[0]
    mips=struct.unpack_from("<I",raw,28)[0]
    fourcc=raw[84:88]
    bpp=struct.unpack_from("<I",raw,88)[0]
    imraw=Image.open(p).convert("RGBA")
    readable=imraw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    raw_png=out/f"B180_{asset}_RAW.png"
    read_png=out/f"B180_{asset}_READABLE.png"
    imraw.save(raw_png)
    readable.save(read_png)

    # Visual contact with labels, no resampling enlargement beyond 1:1.
    bg=Image.new("RGB",readable.size,"white")
    bg.paste(readable.convert("RGB"))
    draw=ImageDraw.Draw(bg)
    draw.rectangle((0,0,min(bg.width,900),32),fill="white")
    draw.text((6,8),f"idx{idx} {asset} READABLE {w}x{h}",fill="black")
    cards.append((idx,asset,bg))

    records.append({
      "queue_index":idx,
      "asset":asset,
      "queue_filename":fn,
      "source_url":url,
      "source_sha256":sha256(p),
      "dds":{"width":w,"height":h,"mipmaps":mips,"fourcc":fourcc.decode("latin1"),"bpp":bpp},
      "raw_orientation":"mirror_y",
      "readable_evidence":str(read_png.relative_to(repo)),
      "raw_evidence":str(raw_png.relative_to(repo)),
      "controller_classification":"PENDING_CONTROLLER_VISUAL_REVIEW"
    })

maxw=max(c.width for _,_,c in cards)
gap=10
totalh=sum(c.height for _,_,c in cards)+gap*(len(cards)-1)
sheet=Image.new("RGB",(maxw,totalh),"white")
y=0
for _,_,c in cards:
    sheet.paste(c,(0,y))
    y+=c.height+gap
sheet.thumbnail((2200,2200),Image.Resampling.LANCZOS)
sheet_path=out/"B180_READABLE_CONTACT.jpg"
sheet.save(sheet_path,quality=96)

report={
 "schema_version":1,
 "role":"B",
 "run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "purpose":"Next even zoom_review batch after B177/B179 fail-closed index62 and preserve classifications 136/144.",
 "items":records,
 "controller_visual_qa":"PENDING",
 "candidate_written":False,
 "runtime_validation":"UNTESTED",
 "status":"B180_WORKER_PROBE_READY_FOR_CONTROLLER_CLASSIFICATION",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B180_ZOOM146148150_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B180_ZOOM146148150.json").write_text(json.dumps({
 "role":"B","run":run,"indices":[146,148,150],
 "report":str(rp.relative_to(repo)),
 "status":"WORKER_PROBE_READY_FOR_CONTROLLER_CLASSIFICATION"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B180_DONE",[(r["queue_index"],r["asset"],r["source_sha256"],r["dds"]) for r in records])
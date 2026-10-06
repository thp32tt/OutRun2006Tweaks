#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PROBE181-ZOOM166172174178180"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst"
items=[
 (166,"5EBD7FE8","5EBD7FE8_1024x1024.dds"),
 (172,"6C9B3611","6C9B3611_256x256.dds"),
 (174,"73F852A4","73F852A4_512x512.dds"),
 (178,"798A1E","798A1E_1024x256.dds"),
 (180,"7ABD5110","7ABD5110_1024x256.dds"),
]

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def on_white(im):
    bg=Image.new("RGBA",im.size,(255,255,255,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")

records=[]
proofs=[]
for idx,asset,fn in items:
    url=f"{base}/{fn}"
    p=Path("/tmp")/f"B181_{fn}"
    urllib.request.urlretrieve(url,p)
    raw=p.read_bytes()
    if raw[:4]!=b"DDS ":
        raise RuntimeError((fn,"not DDS"))
    h=struct.unpack_from("<I",raw,12)[0]
    w=struct.unpack_from("<I",raw,16)[0]
    mips=struct.unpack_from("<I",raw,28)[0]
    fourcc=raw[84:88]
    bpp=struct.unpack_from("<I",raw,88)[0]
    raw_im=Image.open(p).convert("RGBA")
    readable=raw_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    raw_png=out/f"B181_{asset}_RAW.png"
    read_png=out/f"B181_{asset}_READABLE.png"
    raw_im.save(raw_png)
    readable.save(read_png)

    vis=on_white(readable)
    vis.thumbnail((1600,1200),Image.Resampling.LANCZOS)
    card=Image.new("RGB",(vis.width,vis.height+34),"white")
    card.paste(vis,(0,34))
    ImageDraw.Draw(card).text((8,9),f"idx{idx} {asset} READABLE source={w}x{h}",fill="black")
    proof=out/f"B181_{asset}_READABLE_PROOF.jpg"
    card.save(proof,quality=96)
    proofs.append((idx,asset,card))

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
      "proof_evidence":str(proof.relative_to(repo)),
      "controller_classification":"PENDING_CONTROLLER_VISUAL_REVIEW"
    })

maxw=max(c.width for _,_,c in proofs)
gap=10
totalh=sum(c.height for _,_,c in proofs)+gap*(len(proofs)-1)
sheet=Image.new("RGB",(maxw,totalh),"white")
y=0
for _,_,c in proofs:
    sheet.paste(c,(0,y))
    y+=c.height+gap
sheet.thumbnail((2200,3200),Image.Resampling.LANCZOS)
sheet_path=out/"B181_READABLE_CONTACT.jpg"
sheet.save(sheet_path,quality=95)

report={
 "schema_version":1,
 "role":"B",
 "run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "purpose":"Next even blocked zoom_review batch after B180; classification-only worker evidence.",
 "items":records,
 "controller_visual_qa":"PENDING",
 "candidate_written":False,
 "runtime_validation":"UNTESTED",
 "status":"B181_WORKER_PROBE_READY_FOR_CONTROLLER_CLASSIFICATION",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B181_ZOOM166172174178180_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B181_ZOOM166172174178180.json").write_text(json.dumps({
 "role":"B","run":run,"indices":[166,172,174,178,180],
 "report":str(rp.relative_to(repo)),
 "status":"WORKER_PROBE_READY_FOR_CONTROLLER_CLASSIFICATION"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B181_DONE",[(r["queue_index"],r["asset"],r["source_sha256"],r["dds"]) for r in records])

#!/usr/bin/env python3
import csv, hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PROBE193-ZOOM194196202206210214238"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

items=[
 (194,"textures/load/spr_sprani_sumo_fe_cvt_Exst/9AC75730_512x512.dds"),
 (196,"textures/load/spr_sprani_sumo_fe_cvt_Exst/9EF903AF_512x512.dds"),
 (202,"textures/load/spr_sprani_sumo_fe_cvt_Exst/AB56F682_512x512.dds"),
 (206,"textures/load/spr_sprani_sumo_fe_cvt_Exst/AEA507A4_512x256.dds"),
 (210,"textures/load/spr_sprani_sumo_fe_cvt_Exst/B5BB7AB0_512x512.dds"),
 (214,"textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"),
 (238,"textures/load/spr_sprani_sumo_loading_Exst/132A1B1F_512x512.dds"),
]
source_commit="a95efe01d1f136514cef94b0d9e9fd61df021754"

with (repo/"localization/graphics/inventory.csv").open(encoding="utf-8-sig",newline="") as f:
    inventory={r["path"]:r for r in csv.DictReader(f)}

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def on_white(im):
    bg=Image.new("RGBA",im.size,(255,255,255,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")

def proof(label,im,maxsize=(1600,1200)):
    vis=on_white(im)
    vis.thumbnail(maxsize,Image.Resampling.LANCZOS)
    card=Image.new("RGB",(vis.width,vis.height+34),"white")
    card.paste(vis,(0,34))
    ImageDraw.Draw(card).text((8,9),label,fill="black")
    return card

# Produce compact RAW proof thumbnails for the unresolved B181 items so the
# controller can complete its mandatory raw/orientation visual review without
# re-decoding or re-rendering those sources.
legacy_run=repo/"localization/graphics/role_B/20261006-B-PROBE181-ZOOM166172174178180"
legacy_out=repo/"localization/graphics/role_B/20261006-B-CLASSIFY192-ZOOM166174178180"
legacy_out.mkdir(parents=True,exist_ok=True)
legacy=[(166,"5EBD7FE8"),(174,"73F852A4"),(178,"798A1E"),(180,"7ABD5110")]
legacy_records=[]
for idx,asset in legacy:
    p=legacy_run/f"B181_{asset}_RAW.png"
    if not p.exists():
        raise RuntimeError(("missing B181 raw evidence",str(p)))
    im=Image.open(p).convert("RGBA")
    card=proof(f"idx{idx} {asset} RAW mirror_y (B181 evidence)",im)
    dst=legacy_out/f"B192_{asset}_RAW_PROOF.jpg"
    card.save(dst,quality=95)
    legacy_records.append({"queue_index":idx,"asset":asset,"raw_source":str(p.relative_to(repo)),"raw_proof":str(dst.relative_to(repo))})
(legacy_out/"B192_RAW_PROOF_REPORT.json").write_text(json.dumps({
    "schema_version":1,"role":"B","run":"20261006-B-CLASSIFY192-ZOOM166174178180",
    "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
    "source_worker_report":"localization/graphics/role_B/20261006-B-PROBE181-ZOOM166172174178180/B181_ZOOM166172174178180_REPORT.json",
    "items":legacy_records,
    "purpose":"Compact raw-orientation proofs for pending controller classification only; no candidate/render/state mutation.",
    "status":"RAW_PROOFS_READY_FOR_CONTROLLER_REVIEW",
    "no_vr_ffb_dx11_dxvk_work":True
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

records=[]
read_cards=[]
raw_cards=[]
for idx,rel in items:
    inv=inventory.get(rel)
    if not inv:
        raise RuntimeError(("inventory missing",idx,rel))
    fn=Path(rel).name
    folder=Path(rel).parent.name
    url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{source_commit}/Release/{folder}/{fn}"
    p=Path("/tmp")/f"B193_{fn}"
    urllib.request.urlretrieve(url,p)
    got=sha256(p)
    expected=inv["sha256"]
    if got!=expected:
        raise RuntimeError(("source drift",idx,rel,got,expected))
    raw=p.read_bytes()
    if raw[:4]!=b"DDS ":
        raise RuntimeError((idx,"not DDS"))
    h=struct.unpack_from("<I",raw,12)[0]
    w=struct.unpack_from("<I",raw,16)[0]
    mips=struct.unpack_from("<I",raw,28)[0]
    fourcc=raw[84:88]
    bpp=struct.unpack_from("<I",raw,88)[0]
    raw_im=Image.open(p).convert("RGBA")
    readable=raw_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    asset=Path(fn).stem.split("_")[0]

    raw_png=out/f"B193_{asset}_RAW.png"
    read_png=out/f"B193_{asset}_READABLE.png"
    raw_im.save(raw_png)
    readable.save(read_png)

    rc=proof(f"idx{idx} {asset} READABLE source={w}x{h}",readable)
    qc=proof(f"idx{idx} {asset} RAW mirror_y source={w}x{h}",raw_im)
    read_proof=out/f"B193_{asset}_READABLE_PROOF.jpg"
    raw_proof=out/f"B193_{asset}_RAW_PROOF.jpg"
    rc.save(read_proof,quality=96)
    qc.save(raw_proof,quality=96)
    read_cards.append(rc); raw_cards.append(qc)

    records.append({
      "queue_index":idx,
      "asset":asset,
      "queue_path":rel,
      "queue_filename":fn,
      "source_url":url,
      "inventory_sha256":expected,
      "source_sha256":got,
      "dds":{"width":w,"height":h,"mipmaps":mips,"fourcc":fourcc.decode("latin1"),"bpp":bpp},
      "raw_orientation":"mirror_y",
      "readable_evidence":str(read_png.relative_to(repo)),
      "raw_evidence":str(raw_png.relative_to(repo)),
      "readable_proof":str(read_proof.relative_to(repo)),
      "raw_proof":str(raw_proof.relative_to(repo)),
      "controller_classification":"PENDING_CONTROLLER_VISUAL_REVIEW"
    })

def contact(cards,path):
    maxw=max(c.width for c in cards)
    gap=10
    totalh=sum(c.height for c in cards)+gap*(len(cards)-1)
    sheet=Image.new("RGB",(maxw,totalh),"white")
    y=0
    for c in cards:
        sheet.paste(c,(0,y))
        y+=c.height+gap
    sheet.thumbnail((2200,3600),Image.Resampling.LANCZOS)
    sheet.save(path,quality=95)

contact(read_cards,out/"B193_READABLE_CONTACT.jpg")
contact(raw_cards,out/"B193_RAW_CONTACT.jpg")

report={
 "schema_version":1,
 "role":"B",
 "run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "purpose":"One allowed new preflight batch after consuming existing B181 evidence; exact-HD readable+raw classification evidence for all remaining even blocked zoom_review rows.",
 "items":records,
 "controller_visual_qa":"PENDING",
 "candidate_written":False,
 "runtime_validation":"UNTESTED",
 "status":"B193_WORKER_PROBE_READY_FOR_CONTROLLER_CLASSIFICATION",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B193_ZOOM194196202206210214238_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B193_ZOOM194196202206210214238.json").write_text(json.dumps({
 "role":"B","run":run,"indices":[i for i,_ in items],
 "report":str(rp.relative_to(repo)),
 "status":"WORKER_PROBE_READY_FOR_CONTROLLER_CLASSIFICATION"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B193_DONE",[(r["queue_index"],r["asset"],r["source_sha256"],r["dds"]) for r in records])
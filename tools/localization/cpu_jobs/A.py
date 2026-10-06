#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PROBE111-ZOOM189191217219"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst"
items=[
 (189,"8C9E91F8_512x512.dds"),
 (191,"94BB6271_512x256.dds"),
 (217,"D1039D6F_512x512.dds"),
 (219,"D263B3F1_512x512.dds"),
]
tmp=Path("/tmp/a111"); tmp.mkdir(exist_ok=True)
rows=[]
for idx,name in items:
    p=tmp/name
    urllib.request.urlretrieve(f"{base}/{name}",p)
    raw=p.read_bytes()
    if raw[:4]!=b"DDS ": raise RuntimeError(("not dds",name))
    h=struct.unpack_from("<I",raw,12)[0]
    w=struct.unpack_from("<I",raw,16)[0]
    mips=struct.unpack_from("<I",raw,28)[0]
    fourcc=raw[84:88].decode("latin1")
    bpp=struct.unpack_from("<I",raw,88)[0]
    masks=[hex(x) for x in struct.unpack_from("<IIII",raw,92)]
    imraw=Image.open(p).convert("RGBA")
    if imraw.size!=(w,h): raise RuntimeError(("decode size",name,imraw.size,(w,h)))
    readable=imraw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    stem=name.split("_")[0]
    imraw.save(out/f"A111_{stem}_RAW.png")
    readable.save(out/f"A111_{stem}_READABLE.png")
    for lab,im in (("READABLE",readable),("RAW_MIRROR_Y",imraw)):
        bg=Image.new("RGBA",im.size,(235,235,235,255)); bg.alpha_composite(im)
        proof=bg.convert("RGB")
        proof.thumbnail((1800,1800),Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",(proof.width,proof.height+28),"white")
        ImageDraw.Draw(canvas).text((5,5),f"{stem} {lab}",fill="black")
        canvas.paste(proof,(0,28))
        canvas.save(out/f"A111_{stem}_{lab}_PROOF.jpg",quality=92,optimize=True)
    rows.append({
      "queue_index":idx,
      "asset":name,
      "source_url":f"{base}/{name}",
      "sha256":hashlib.sha256(raw).hexdigest(),
      "bytes":len(raw),
      "width":w,"height":h,"mipmaps":mips,"fourcc":fourcc,"bpp":bpp,"masks":masks
    })
report={
 "schema_version":1,"role":"A","run":run,
 "items":rows,
 "status":"A111_SOURCE_PROBE_BATCH_COMPLETE_CONTROLLER_CLASSIFICATION_REQUIRED"
}
(out/"A111_ZOOM189191217219_PROBE.json").write_text(json.dumps(report,indent=2)+"\n")
(wr/"A111_ZOOM189191217219_PROBE.json").write_text(json.dumps({
 "run":run,
 "indices":[x[0] for x in items],
 "items":[{"queue_index":r["queue_index"],"asset":r["asset"],"sha256":r["sha256"],"width":r["width"],"height":r["height"],"fourcc":r["fourcc"],"mipmaps":r["mipmaps"]} for r in rows],
 "report":f"localization/graphics/role_A/{run}/A111_ZOOM189191217219_PROBE.json",
 "status":report["status"]
},indent=2)+"\n")
print(json.dumps(report),flush=True)

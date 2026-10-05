#!/usr/bin/env python3
import os, json, hashlib, struct, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-MCPTEST01"
out=repo/"localization/graphics/role_A"/run
wr=repo/"localization/graphics/worker_results"
out.mkdir(parents=True,exist_ok=True)
wr.mkdir(parents=True,exist_ok=True)

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
src_url=base+"/Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
atlas_url=base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_0030CF0D_512x256_atlas.json"
expected_src_blob="a17e3caff8610356d70ddc52e89a7533aa99b98c"
expected_atlas_blob="05aef390b13b39d3c9cd74d5c50f8291273fb0d9"

tmp=Path("/tmp/outrun_A_mcptest01")
tmp.mkdir(parents=True,exist_ok=True)
src=tmp/"30CF0D_HD.dds"
atlas=tmp/"30CF0D_atlas.json"
urllib.request.urlretrieve(src_url,src)
urllib.request.urlretrieve(atlas_url,atlas)

def blob_sha1(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

sb=src.read_bytes(); ab=atlas.read_bytes()
if blob_sha1(sb)!=expected_src_blob:
    raise RuntimeError(("source blob drift",blob_sha1(sb),expected_src_blob))
if blob_sha1(ab)!=expected_atlas_blob:
    raise RuntimeError(("atlas blob drift",blob_sha1(ab),expected_atlas_blob))
if sb[:4]!=b"DDS ":
    raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,1024,8192,1) or depth not in (0,1):
    raise RuntimeError(("unexpected DDS structure",W,H,pitch,depth,mips))
if len(sb)!=128+W*H*4:
    raise RuntimeError(("unexpected byte size",len(sb)))
if pf[3]!=32:
    raise RuntimeError(("expected 32-bit source",pf))
masks=(pf[4],pf[5],pf[6])
if masks==(0xff,0xff00,0xff0000):
    rawmode="RGBA"
elif masks==(0xff0000,0xff00,0xff):
    rawmode="BGRA"
else:
    raise RuntimeError(("unsupported masks",masks))

raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",rawmode)
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(atlas.read_text(encoding="utf-8"))
regions={int(r["idx"]):r for r in aj["regions"]}
expected_rects={
  4:[0,136,808,84],
  5:[808,136,808,84],
  6:[0,56,1276,80],
}
for idx,rect in expected_rects.items():
    if idx not in regions or regions[idx]["rect"]!=rect:
        raise RuntimeError(("atlas drift",idx,regions.get(idx),rect))

preview=readable.resize((1024,512),Image.Resampling.LANCZOS).convert("RGB")
d=ImageDraw.Draw(preview)
for idx,rect in expected_rects.items():
    x,y,w,h=rect
    sx,sy=0.5,0.5
    d.rectangle((int(x*sx),int(y*sy),int((x+w)*sx)-1,int((y+h)*sy)-1),outline=(255,255,255),width=2)
    d.text((int(x*sx)+4,int(y*sy)+4),f"region {idx}",fill=(255,255,255))
preview_path=out/"A_MCPTEST01_30CF0D_SOURCE_REGIONS.jpg"
preview.save(preview_path,quality=95)

report={
  "schema_version":1,
  "role":"A",
  "run":run,
  "purpose":"RDS-free A toolchain capability test; no candidate/state mutation",
  "queue_index":137,
  "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds",
  "source_provenance":{
    "repository":"Sonic-TV/OR2006Sprites",
    "commit":commit,
    "path":"Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds",
    "git_blob_sha1":expected_src_blob,
    "sha256":hashlib.sha256(sb).hexdigest()
  },
  "atlas_git_blob_sha1":expected_atlas_blob,
  "structure":{"dimensions":[W,H],"pitch":pitch,"depth":depth,"mipmaps":mips,"pixel_raw_mode":rawmode,"bytes":len(sb),"raw_orientation":"mirror_y"},
  "target_region_preflight":[
    {"region_idx":4,"rect":expected_rects[4],"expected_semantic":"MANUAL -> 수동"},
    {"region_idx":5,"rect":expected_rects[5],"expected_semantic":"AUTOMATIC -> 자동"},
    {"region_idx":6,"rect":expected_rects[6],"expected_semantic":"SELECT TRANSMISSION -> 변속 방식 선택"}
  ],
  "evidence":"localization/graphics/role_A/20261005-A-MCPTEST01/A_MCPTEST01_30CF0D_SOURCE_REGIONS.jpg",
  "candidate_written":False,
  "shared_state_mutated":False,
  "runtime_validation":"UNTESTED",
  "status":"RDS_FREE_TOOLCHAIN_PREFLIGHT_PASS"
}
rp=out/"A_MCPTEST01_30CF0D_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
  "run":run,
  "queue_index":137,
  "asset":"30CF0D",
  "source_sha256":report["source_provenance"]["sha256"],
  "dimensions":[W,H],
  "pixel_raw_mode":rawmode,
  "candidate_written":False,
  "status":report["status"],
  "report":str(rp.relative_to(repo)),
  "runtime_validation":"UNTESTED"
}
(wr/"A_MCPTEST01_30CF0D.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))

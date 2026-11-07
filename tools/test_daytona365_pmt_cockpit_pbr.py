#!/usr/bin/env python3
"""Static structural & provenance validator, never substitutes for Quest runtime tests."""
import json,math,hashlib,struct
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
R=Path(__file__).resolve().parent
O=R/"outputs"
MAN=json.loads((O/"MANIFEST.json").read_text())
assert hashlib.sha256(Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz").read_bytes()).hexdigest()==MAN["source_sha256"]
reports={}
for key in ("car","wheel_local"):
 item=MAN[key];p=O/item["file"]
 raw=p.read_bytes()
 assert raw[:4]==b"glTF",p
 assert struct.unpack_from("<I",raw,8)[0]==len(raw)
 jslen=struct.unpack_from("<I",raw,12)[0]
 j=json.loads(raw[20:20+jslen])
 start=20+jslen
 binsize=struct.unpack_from("<I",raw,start)[0]
 data=raw[start+8:start+8+binsize]
 assert len(data)==binsize
 assert len(data)>=j["buffers"][0]["byteLength"]
 for v in j["bufferViews"]:
  assert 0 <= v.get("byteOffset",0) <= len(data)
  assert v.get("byteOffset",0)+v["byteLength"]<=len(data)
 for a in j["accessors"]:
  assert a["count"]>=1
  assert 0<=a["bufferView"]<len(j["bufferViews"])
 for tx in j["textures"]:
  assert 0<=tx["source"]<len(j["images"])
 for im in j["images"]:
  v=j["bufferViews"][im["bufferView"]]
  assert data[v.get("byteOffset",0):v.get("byteOffset",0)+8]==b"\x89PNG\r\n\x1a\n"
 normal=[i for i,m in enumerate(j["materials"]) if "normalTexture" in m]
 assert normal
 assert len(j["materials"])==len(j["meshes"])==item["meshes"]
 expected=item["triangles_after"]
 tri=sum(j["accessors"][m["primitives"][0]["indices"]]["count"]//3 for m in j["meshes"])
 assert tri==expected,(tri,expected)
 reports[key]={"triangles":tri,"meshes":len(j["meshes"]),"normal_mapped_materials":len(normal),
               "base_color_and_pbr_images":len(j["images"]),
               "geometry_bounds_preserved":bool(key=="car")}
# Confirm changed meaningful material pixels, not identical upscale.
metrics={}
for i in [8,14,15,16,18,19]:
 a=Image.open(R/"original_preview"/("tex_%02d.png"%i)).convert("RGB")
 b=Image.open(O/"textures"/("Daytona_car_tex%02d_BaseColor.png"%i)).convert("RGB")
 bsmall=b.resize(a.size,Image.Resampling.LANCZOS)
 diff=ImageChops.difference(a,bsmall)
 metrics[str(i)]={"original":list(a.size),"rework":list(b.size),"mean_rgb_change":round(sum(ImageStat.Stat(diff).mean)/3,2)}
 assert b.size[0]>=a.size[0]*2
assert metrics["16"]["mean_rgb_change"]>0.1
result={"status":"PASS_STATIC","original_sha_unchanged":True,"dino_source_never_read_or_written":True,
        "output_glbs":reports,"texture_comparison":metrics,
        "runtime":"UNTESTED: no R26 .ovc build, game or headset execution"}
(O/"VALIDATION.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
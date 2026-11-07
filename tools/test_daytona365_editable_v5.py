#!/usr/bin/env python3
"""Validates stand-alone editable Daytona glTF 2.0 and PBR semantics.

Synthetic tests can run on GitHub without any private Ferrari PMT/photo files.
Actual test scans only the user's private generated N100 GLB (optional --actual).
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse,hashlib,io,json,math,struct
from PIL import Image
try:
 import build_daytona_editable_v5 as b
except ImportError:
 import build_daytona365_editable_v5 as b

def validate_glb(path,actual=False):
 raw=Path(path).read_bytes()
 if len(raw)<28:raise ValueError("short GLB")
 magic,version,length=struct.unpack_from("<4sII",raw)
 assert (magic,version,length)==(b"glTF",2,len(raw))
 jlen,jtype=struct.unpack_from("<I4s",raw,12)
 assert jtype==b"JSON" and jlen%4==0
 g=json.loads(raw[20:20+jlen])
 a=20+jlen
 size,typ=struct.unpack_from("<I4s",raw,a)
 assert typ==b"BIN\x00" and size%4==0 and a+8+size==len(raw)
 binary=raw[a+8:a+8+size]
 assert g["asset"]["version"]=="2.0"
 assert g["buffers"][0]["byteLength"]<=len(binary)
 assert len(g["meshes"])==len(g["nodes"])
 image_sizes={}
 for i,v in enumerate(g["bufferViews"]):
  assert v["buffer"]==0
  assert v["byteOffset"]%4==0
  assert v["byteOffset"]>=0 and v["byteLength"]>=0
  assert v["byteOffset"]+v["byteLength"]<=len(binary)
 for i,img in enumerate(g["images"]):
  assert img["mimeType"]=="image/png"
  view=g["bufferViews"][img["bufferView"]]
  im=Image.open(io.BytesIO(binary[view["byteOffset"]:view["byteOffset"]+view["byteLength"]]))
  im.load()
  assert im.size[0]>0 and im.size[1]>0
  assert im.mode in ("RGB","RGBA","L")
  image_sizes[i]=im.size
 for a in g["accessors"]:
  assert a["componentType"] in (5126,5125,5123)
  assert a["count"]>0
  assert a["type"] in ("SCALAR","VEC2","VEC3")
  view=g["bufferViews"][a["bufferView"]]
  components={"SCALAR":1,"VEC2":2,"VEC3":3}[a["type"]]
  width={5126:4,5125:4,5123:2}[a["componentType"]]
  assert a["count"]*components*width<=view["byteLength"]
  if a["componentType"]==5126:
   data=binary[view["byteOffset"]:view["byteOffset"]+a["count"]*components*4]
   assert all(math.isfinite(q) and abs(q)<10000 for (q,) in struct.iter_unpack("<f",data))
 name_set=set()
 total_faces=0
 for mesh in g["meshes"]:
  assert mesh["name"] not in name_set
  name_set.add(mesh["name"])
  assert len(mesh["primitives"])==1
  prim=mesh["primitives"][0]
  assert prim["mode"]==4
  at=prim["attributes"]
  assert all(n in at for n in ("POSITION","NORMAL","TEXCOORD_0"))
  vcount=g["accessors"][at["POSITION"]]["count"]
  assert g["accessors"][at["NORMAL"]]["count"]==vcount
  assert g["accessors"][at["TEXCOORD_0"]]["count"]==vcount
  ind=g["accessors"][prim["indices"]]
  assert ind["count"]%3==0
  assert ind["componentType"] in (5125,5123)
  assert prim["material"]<len(g["materials"])
  view=g["bufferViews"][ind["bufferView"]]
  bi=binary[view["byteOffset"]:view["byteOffset"]+view["byteLength"]]
  fmt="<I" if ind["componentType"]==5125 else "<H"
  assert max(item[0] for item in struct.iter_unpack(fmt,bi))<vcount
  total_faces+=ind["count"]//3
 assert len(g["materials"])>=1
 for m in g["materials"]:
  p=m["pbrMetallicRoughness"]
  for t in (p["baseColorTexture"],p["metallicRoughnessTexture"],m["occlusionTexture"],m["normalTexture"]):
   assert t["index"]<len(g["textures"])
  assert p["metallicRoughnessTexture"]["index"]==m["occlusionTexture"]["index"]
  assert p["roughnessFactor"]==1.0 and p["metallicFactor"]==1.0
  extras=m["extras"]
  assert "HeightMapImageIndex" in extras
  assert extras["HeightMapImageIndex"] in image_sizes
  assert extras["HeightMapUsage"].startswith("OFFLINE")
 assert g["extras"]["notOVC"] is True
 assert g["extras"]["normalORM"]=="glTF native slots applied"
 if actual:
  assert len(g["meshes"])>=80 and total_faces>=50000
  assert len(g["materials"])==9 and len(g["textures"])==36
  assert len([n for n in name_set if "ORIGINAL_THREESPOKE_WHEEL" in n])==3
  for side in ("L","R"):
   assert f"V5_{side}_SEAT_PADDED_CUSHION" in name_set
   assert f"V5_{side}_SEAT_RECLINED_PADDED_BACK" in name_set
  assert g["extras"]["Dino"]=="untouched"
 return {"meshes":len(g["meshes"]),"materials":len(g["materials"]),
         "embeddedImages":len(g["images"]),"faces":total_faces,"bytes":len(raw),
         "sha256":hashlib.sha256(raw).hexdigest()}

def test_scultped_seat_meshes():
 ms=b.sculpted_daytona_seats()
 assert len(ms)>=30
 group={m["name"]:m for m in ms}
 assert all(m["i"] and max(m["i"])<len(m["v"]) for m in ms)
 for side in ("L","R"):
  cu=group[f"V5_{side}_SEAT_PADDED_CUSHION"]
  bk=group[f"V5_{side}_SEAT_RECLINED_PADDED_BACK"]
  assert len(cu["i"])//3==3072 and len(bk["i"])//3==3072
  assert max(x[1] for x in bk["v"])>=.80
  assert min(x[1] for x in bk["v"])>=.42
  assert max(x[2] for x in cu["v"])<.66

def test_photo_normal_and_orm():
 im=Image.new("RGB",(32,32))
 for y in range(32):
  for x in range(32):
   im.putpixel((x,y),(min(255,175+x),min(255,122+y),74+(x//4)))
 n,orm,h=b.make_photo_maps(im,3)
 assert (n.size,orm.size,h.size)==(im.size,)*3
 # Tangent normal must preserve positive Z and lack black artifacts.
 assert min(p[2] for p in n.getdata())>100
 assert all(p[1]==200 and p[2]==0 for p in orm.getdata())
 assert len(set(h.getdata()))>=2

def test_synthetic_gltf_roundtrip():
 with TemporaryDirectory() as tmp:
  path=Path(tmp)/"synthetic.glb"
  g=b.Glb()
  texture=Image.new("RGB",(16,16),(166,117,72))
  normal,orm,height=b.make_photo_maps(texture,3)
  m={"name":"Chrome","base":texture,"normal":normal,"orm":orm,"height":height}
  g.add_material(m)
  mesh=b.make_mesh("UNIT_GLB_PBR_TRIANGLE",0)
  i=b.add_v(mesh,(0.,0.,0.),(0.,1.,0.),(0.,0.))
  j=b.add_v(mesh,(1.,0.,0.),(0.,1.,0.),(1.,0.))
  k=b.add_v(mesh,(0.,0.,1.),(0.,1.,0.),(0.,1.))
  b.face(mesh,i,j,k)
  g.add_mesh(mesh)
  g.save(path)
  result=validate_glb(path)
  assert result["meshes"]==1 and result["faces"]==1
  assert result["embeddedImages"]==4

if __name__=="__main__":
 pa=argparse.ArgumentParser();pa.add_argument("--actual",action="store_true")
 args=pa.parse_args()
 for t in (test_scultped_seat_meshes,test_photo_normal_and_orm,test_synthetic_gltf_roundtrip):
  t();print(t.__name__,"PASS")
 if args.actual:
  path=b.OUT/"Daytona365_Cockpit_EDITABLE_HiDetail_PBR_v5.glb"
  print("ACTUAL",json.dumps(validate_glb(path,True),indent=2))
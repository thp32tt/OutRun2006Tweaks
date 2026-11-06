#!/usr/bin/env python3
"""Dino 246 v4 real mesh detail regression; NO proprietary game assets needed."""
from pathlib import Path
import importlib.util,math,sys,tempfile
from PIL import Image

src=Path(__file__).resolve().parents[1]/"dino_cockpit_concept_detail_v4.py"
spec=importlib.util.spec_from_file_location("v4",src)
v4=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4)
meshes=v4.build_v4()
old=v4.v3.build_v3()
named={m.name:m for m in meshes}
assert len(named)==len(meshes)
assert len(meshes)>len(old)
nv=sum(len(m.vertices) for m in meshes)
nt=sum(len(m.faces)//3 for m in meshes)
assert nv>60000 and 105000<nt<180000
expected=("dashboard_hand_sculpted_v4","driver_arched_instrument_sunhood_v4",
          "aux_gauge00_face","aux_gauge01_face",
          "radio_analog_tuner_dark_glass","upper_vent_0_black_recess",
          "upper_vent_1_black_recess","wheel_center_amber_logo_disc",
          "passenger_fascia_Dino246_signature",
          "pedal_0_15_open_holes","pedal_1_15_open_holes","pedal_2_15_open_holes",
          "central_handbrake_real_metal_rod")
assert all(x in named for x in expected), sorted(set(expected)-set(named))
assert sum("_seat_rib_" in n and n.endswith("_padded") for n in named)==16
assert sum("_back_rib_" in n and n.endswith("_padded") for n in named)==14
assert sum("radio_station_key_" in n and "metal_trim" not in n for n in named)==5
assert sum("_louver_" in n for n in named)==12
assert sum(n.startswith("aux_gauge") and n.endswith("_face") for n in named)==2
assert sum(n=="LHD_steering_rim_remodelled" for n in named)==1
assert sum(n=="LHD_column_outer_padded_shroud" for n in named)==1
for oldname in (
  "dash_top_soft_curve","instrument_hood_curved",
  "dashboard_driver_instrument_recess","LHD_column_real_shafts",
  "pedal_0_plate","pedal_1_plate","pedal_2_plate"):
  assert oldname not in named,oldname

def signed_area(p,a,b,c):
    ab=(b[0]-a[0],b[1]-a[1])
    ac=(c[0]-a[0],c[1]-a[1])
    return ab[0]*ac[1]-ab[1]*ac[0]
def covers(p,verts,faces):
    # restrict to triangles from both front/back surfaces, test 2D x-z only.
    for i in range(0,len(faces),3):
        a,b,c=[(verts[faces[i+j]][0],verts[faces[i+j]][2]) for j in range(3)]
        ab=signed_area(p,a,b,c)
        if abs(ab)<1e-12:continue
        u=signed_area(p,p,b,c)/ab
        v=signed_area(p,a,p,c)/ab
        w=signed_area(p,a,b,p)/ab
        if min(u,v,w)>.000001:
            return True
    return False
# Enforce true physical perforation: no triangle over the center of any
# of the 45 holes across 3 separate real-metal pedal plates.
for i,x in enumerate((-.540,-.410,-.255)):
  mesh=named["pedal_%d_15_open_holes"%i]
  for row in range(5):
      for col in range(3):
          cx=x-.038+(col+.5)*(.076/3)
          cz=-.606+(row+.5)*(.114/5)
          assert not covers((cx,cz),mesh.vertices,mesh.faces),("solid hole",i,col,row)
# All solid meshes have finite geometry and no zero-area triangles.
zero=0
for m in meshes:
    assert m.vertices and len(m.vertices)==len(m.normals)==len(m.uvs)
    assert m.faces and len(m.faces)%3==0
    assert all(0<=i<len(m.vertices) for i in m.faces)
    for ver in m.vertices:
        assert all(math.isfinite(x) and abs(x)<100 for x in ver)
    for j in range(0,len(m.faces),3):
        a,b,c=[m.vertices[m.faces[j+k]] for k in range(3)]
        u=[b[k]-a[k] for k in range(3)]
        v=[c[k]-a[k] for k in range(3)]
        n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        if sum(z*z for z in n)<1e-22:zero+=1
assert zero==0,("zero-area faces",zero)
merged=v4.v2.merge_meshes_for_runtime(meshes)
assert 9<=len(merged)<=14
assert sum(len(m.faces) for m in merged)==sum(len(m.faces) for m in meshes)
assert sum(len(m.vertices) for m in merged)==sum(len(m.vertices) for m in meshes)
assert max(len(m.vertices) for m in merged)<=60000
assert v4.v3.column_clearance()["gauge1"]>.019

textures=v4.new_textures(256)
assert "badge" in textures and "signature" in textures
assert textures["badge"].size==(256,256)
assert textures["signature"].size==(256,64)
assert all(material in textures for material in set(m.material for m in meshes))

print("PASS V4_REF_DETAIL_GEOMETRY",len(meshes),"meshes",nv,"vertices",nt,
      "triangles",len(merged),"R26 batches", "45 real pedal holes",zero,"degenerates")

# Test real GLB normalTexture embedding using a tiny synthetic authoring subset
# (no user game data) and verify all image bufferViews/texture links.
import json,struct
from tempfile import TemporaryDirectory
with TemporaryDirectory() as d:
    root=Path(d)
    glb=root/"synthetic_v4.gltf2.glb"
    v4.v1.write_glb(meshes[:3],textures,glb)
    v4.apply_glb_normal_maps(glb,textures)
    raw=glb.read_bytes()
    assert raw[:4]==b"glTF"
    assert struct.unpack_from("<I",raw,8)[0]==len(raw)
    jl=struct.unpack_from("<I",raw,12)[0]
    obj=json.loads(raw[20:20+jl])
    off=20+jl
    assert raw[off+4:off+8]==b"BIN"+bytes((0,))
    binlen=struct.unpack_from("<I",raw,off)[0]
    assert off+8+binlen==len(raw)
    bound=len(raw)-(off+8)
    assert len(obj["images"])==17 and len(obj["textures"])==17
    assert sum("normalTexture" in mat for mat in obj["materials"])==6
    for idx,item in enumerate(obj["bufferViews"]):
        x=item.get("byteOffset",0)
        n=item["byteLength"]
        assert x%4==0 and x>=0 and n>0 and x+n<=bound,(idx,item)
    for mat in obj["materials"]:
        if mat["name"].split("_PBR")[0] in ("leather","vinyl","plastic","metal","carpet","seat"):
            assert obj["textures"][mat["normalTexture"]["index"]]["source"]>=11
print("PASS V4_PBR_NORMAL_MAP_LINKS",6,"valid normal maps")
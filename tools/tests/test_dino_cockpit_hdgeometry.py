#!/usr/bin/env python3
"""Geometry contract smoke: no original game files needed."""
import importlib.util,math,sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"dino_cockpit_hdgeometry_v1.py"
spec=importlib.util.spec_from_file_location("hd",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
meshes=m.generate_cockpit()
n={x.name:x for x in meshes}
needed=[
 "LHD_steering_rim_remodelled","LHD_column_real_shafts",
 "indicator_stalk","wiper_stalk",
 "driver_seat_pad_sculpted","passenger_seat_pad_sculpted",
 "driver_backrest_sculpted","passenger_backrest_sculpted",
 "gauge_00_face","gauge_01_face","gauge_02_face",
 "center_console_leather","gear_stick_exposed_shaft"
]
assert all(item in n for item in needed),sorted(set(needed)-set(n))
assert len(n)==len(meshes),(len(n),len(meshes))
assert sum(len(x.faces)//3 for x in meshes)>20000
assert sum(len(x.vertices) for x in meshes)>12000
for x in meshes:
 assert x.material in ("leather","seat","vinyl","metal","carpet","plastic","dial0","dial1","dial2")
 assert len(x.vertices)==len(x.normals)==len(x.uvs)
 assert len(x.faces)%3==0
 assert len(x.faces)>=3
 assert all(0<=idx<len(x.vertices) for idx in x.faces)
 assert all(math.isfinite(v) for vertex in x.vertices for v in vertex)
 assert all(.9<math.sqrt(sum(n*n for n in normal))<1.1 for normal in x.normals)
assert sum("steering_rim" in name for name in n)==1,"duplicate steering wheels"
assert sum("column_real_shafts" in name for name in n)==1
assert sum("turn_" in name for name in n)==0
assert len([name for name in n if "gauge_" in name and name.endswith("_face")])==3
assert len([name for name in n if "stitch_rib" in name])==24
for x in meshes:
 for a,b,c in zip(x.vertices,x.vertices[1:],x.vertices[2:]): pass
bounds=[[min(vertex[k] for mesh in meshes for vertex in mesh.vertices),
         max(vertex[k] for mesh in meshes for vertex in mesh.vertices)] for k in range(3)]
assert bounds[0][0] >= -.85 and bounds[0][1] <= .85,bounds
assert bounds[1][0] >= .05 and bounds[1][1] <= 1.2,bounds
assert bounds[2][0] >= -1.2 and bounds[2][1] <= 1.5,bounds
print("PASS HD_GEOMETRY source-aligned bounds",bounds,
      "meshes",len(meshes),"vertices",sum(len(m.vertices) for m in meshes),
      "tris",sum(len(m.faces)//3 for m in meshes))

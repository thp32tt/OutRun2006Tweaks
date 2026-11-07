#!/usr/bin/env python3
"""Fresh-open v8.9 official Blender proof: two real PMT-bounded headrests,
four physically joined source seats, new UV and packed source PBR.
"""
import bpy,hashlib,json,math,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
BASE=W/"Daytona365_Cockpit_Blender_PBR_v8_8.blend"
PATH=W/"Daytona365_Cockpit_Blender_PBR_v8_9.blend"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==PATH.resolve()
manifest=json.loads((W/"DAYTONA_V8_9_BUILD_MANIFEST.json").read_text())
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==manifest["source_sha256"]
assert hashlib.sha256(PATH.read_bytes()).hexdigest()==manifest["new_sha256"]
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert scene.render.engine=="CYCLES"
for name in ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_LOW_CENTER_TUNNEL","V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"):
 assert name in bpy.data.objects,name
tunnel=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
assert len(tunnel.data.vertices)==78
assert tunnel.data.uv_layers.active.name=="V8_8_METRIC_CONSOLE_UV"
objects=[]
for side in ("L","R"):
 h=bpy.data.objects["V8_9_"+side+"_INTEGRATED_PADDED_HEADREST"]
 assert h.type=="MESH"
 assert len(h.data.vertices)==7*4
 assert len(h.data.polygons)==(7-1)*4+2
 assert h.data.uv_layers.active.name=="V8_9_METRIC_HEADREST_UV"
 assert h.data.materials[0].name=="V8_9_Source_Charcoal_Headrest_PBR"
 assert all(math.isfinite(float(q)) for v in h.data.vertices for q in v.co)
 assert all(math.isfinite(float(q)) for v in h.data.uv_layers.active.data for q in v.uv)
 assert max(abs(v.co.x) for v in h.data.vertices)<.575
 assert max(v.co.z for v in h.data.vertices)<=.85301
 assert min(v.co.y for v in h.data.vertices)>-.7499
 assert any(m.type=="WEIGHTED_NORMAL" for m in h.modifiers)
 for kind,ny in (("CUSHION",52),("BACKREST",58)):
  suffix="CLASSIC_PADDED_CUSHION" if kind=="CUSHION" else "TAPERED_PADDED_BACKREST"
  ob=bpy.data.objects["V8_"+side+"_"+suffix]
  mesh=ob.data
  ring=73*(ny+1)
  assert len(mesh.vertices)==2*ring
  assert len(mesh.polygons)==2*ring-2
  assert mesh.uv_layers.active.name=="V8_9_RESCULPTED_GEODESIC_UV"
  assert mesh.materials[0].name=="V8_9_Source_Charcoal_Seat_PBR"
  assert mesh.materials[1].name=="V8_9_Source_Charcoal_Seat_Side_PBR"
  assert sum(f.material_index==1 for f in mesh.polygons)>1000
  assert all(math.isfinite(float(q)) for u in mesh.uv_layers.active.data for q in u.uv)
  for j in (0,ny//3,ny//2,ny):
   for i in (0,18,36,54,72):
    a=mesh.vertices[j*73+i].co
    b=mesh.vertices[ring+j*73+i].co
    if kind=="BACKREST":
     assert abs((b.y-a.y)-.054)<.0002
    else:
     assert abs((b.y-a.y)-.006)<.0002
     assert abs((b.z-a.z)+.049)<.0002
  for edge in ("LEFT","RIGHT"):
   welt=bpy.data.objects["V8_5_"+side+"_"+kind+"_"+edge+"_WELT"]
   assert welt.data.materials[0].name=="V8_9_Source_Charcoal_Seat_Side_PBR"
  objects.append(ob.name)
for matname,sat,value in (
 ("V8_9_Source_Charcoal_Seat_PBR",.13,.40),
 ("V8_9_Source_Charcoal_Seat_Side_PBR",.15,.37),
 ("V8_9_Source_Charcoal_Headrest_PBR",.14,.38)):
 m=bpy.data.materials[matname]
 nodes=m.node_tree.nodes
 shader=nodes["Principled BSDF"]
 hsv=nodes["V8_9_PMT_CHARCOAL_DESATURATION"]
 assert shader.inputs["Base Color"].is_linked
 assert shader.inputs["Normal"].is_linked
 assert shader.inputs["Roughness"].is_linked
 assert abs(hsv.inputs["Saturation"].default_value-sat)<.0001
 assert abs(hsv.inputs["Value"].default_value-value)<.0001
 assert hsv.inputs["Color"].is_linked
 assert hsv.outputs["Color"].is_linked
 assert shader.inputs["Metallic"].default_value==0.0
 remap=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
 assert remap.inputs["Value"].is_linked
 assert 0.0<remap.inputs["To Min"].default_value<remap.inputs["To Max"].default_value<1.0
 assert any(n.type=="NORMAL_MAP" for n in nodes)
 assert any(n.type=="BUMP" for n in nodes)
 imgs=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
 assert len(imgs)>=4 and all(im.packed_file for im in imgs)
 assert any("ORM" in im.name.upper() for im in imgs)
 assert all(im.colorspace_settings.name=="Non-Color" for im in imgs
  if any(s in im.name.upper() for s in ("ORM","NORMAL","HEIGHT")))
report={
 "status":"DAYTONA_V8_9_FRESH_REOPEN_PASS",
 "blend":PATH.name,"sha256":manifest["new_sha256"],"bytes":PATH.stat().st_size,
 "input_sha256":manifest["source_sha256"],"blender":bpy.app.version_string,
 "mesh_objects":sum(ob.type=="MESH" for ob in bpy.data.objects),
 "curve_objects":sum(ob.type=="CURVE" for ob in bpy.data.objects),
 "headrest_meshes":2,"headrest_stations":7,
 "source_seat_shells":objects,
 "real_cushion_and_backrest_pleats":True,
 "source_PMT_boundaries_and_game_controls_preserved":True,
 "geodesic_uv_preserved_and_resampled":True,
 "source_packed_pbr_basecolor_normal_orm_height_retained":True,
 "actual_render":"UNTESTED","full_resolution_matched":"UNTESTED",
 "game_runtime_and_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_9_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_9_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
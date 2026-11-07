#!/usr/bin/env python3
"""Independent fresh-open inspection of genuine v8.10 Blender geometry and packed source PBR."""
import bpy,hashlib,json,math,os
from pathlib import Path
r=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=r/"blender_v8"
model=w/"Daytona365_Cockpit_Blender_PBR_v8_10.blend"
old=w/"Daytona365_Cockpit_Blender_PBR_v8_9.blend"
m=json.loads((w/"DAYTONA_V8_10_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==m["new_sha256"]
assert hashlib.sha256(old.read_bytes()).hexdigest()==m["source_sha256"]
s=bpy.context.scene
assert s.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert s.render.engine=="CYCLES"
assert bpy.data.objects["DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH"]
assert bpy.data.objects["DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4"]
assert bpy.data.objects["DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3"]
names=("V8_10_Source_Charcoal_Door_Leather_PBR",
 "V8_10_Source_Charcoal_Door_Lower_PBR",
 "V8_10_Source_Ebonized_Steering_Rim_PBR",
 "V8_10_Source_Black_Door_Seam_PBR")
for name in names:
 mat=bpy.data.materials[name];n=mat.node_tree.nodes
 bsdf=n["Principled BSDF"]
 assert n.get("V8_10_PMT_DARK_SOURCE_BASECOLOR")
 assert bsdf.inputs["Base Color"].is_linked
 assert bsdf.inputs["Normal"].is_linked and bsdf.inputs["Roughness"].is_linked
 rough=n["V8_5_ORM_ROUGHNESS_RANGE"]
 assert rough.inputs["Value"].is_linked
 assert 0<rough.inputs["To Min"].default_value<rough.inputs["To Max"].default_value<1
 imgs=[x.image for x in n if x.type=="TEX_IMAGE" and x.image]
 assert len(imgs)==4 and all(im.packed_file for im in imgs)
 assert any("NORMAL" in im.name.upper() for im in imgs)
 assert any("ORM" in im.name.upper() for im in imgs)
 assert all(im.colorspace_settings.name=="Non-Color" for im in imgs
   if any(a in im.name.upper() for a in ("NORMAL","ORM","HEIGHT")))
 assert any(x.type=="NORMAL_MAP" for x in n)
 assert any(x.type=="BUMP" for x in n)

for side in ("L","R"):
 ob=bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"]
 me=ob.data
 assert len(me.vertices)==465 and len(me.polygons)==840
 assert me.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
 assert me.materials[0].name==names[0]
 assert all(math.isfinite(float(q)) for v in me.vertices for q in v.co)
 assert all(math.isfinite(float(q)) for p in me.uv_layers.active.data for q in p.uv)
 assert all(math.isfinite(float(v)) for p in me.polygons for v in p.normal)
 assert any(abs(float(v.co.x))>.75 for v in me.vertices)
 for j in (6,8):
  co=bpy.data.objects["V8_10_"+side+"_DOOR_SEAM_"+str(j)]
  assert co.type=="CURVE" and len(co.data.splines[0].points)==27
 assert bpy.data.objects["V8_3_"+side+"_TAN_DOOR_LOWER_PAD"].data.materials[0].name==names[1]
 assert bpy.data.objects["V6_"+side+"_BLENDER_SADDLE_DOOR_POCKET"].data.materials[0].name==names[1]
 assert bpy.data.objects["V6_"+side+"_BLENDER_DOOR_STITCH_BORDER"].data.materials[0].name==names[3]
 assert bpy.data.objects["V8_9_"+side+"_INTEGRATED_PADDED_HEADREST"]
 for suf in ("CLASSIC_PADDED_CUSHION","TAPERED_PADDED_BACKREST"):
  ob=bpy.data.objects["V8_"+side+"_"+suf]
  assert ob.data.uv_layers.active.name=="V8_9_RESCULPTED_GEODESIC_UV"
  assert ob.data.materials[0].name=="V8_9_Source_Charcoal_Seat_PBR"
for name,vcount in (("V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",1536),
 ("V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material002_a0",153)):
 ob=bpy.data.objects[name]
 assert len(ob.data.vertices)==vcount
 assert ob.data.materials[0].name==names[2]
report={"status":"DAYTONA_V8_10_FRESH_REOPEN_PASS",
 "blender":bpy.app.version_string,"sha256":m["new_sha256"],
 "source_sha256":m["source_sha256"],
 "mesh_count":sum(o.type=="MESH" for o in bpy.data.objects),
 "curve_count":sum(o.type=="CURVE" for o in bpy.data.objects),
 "door_original_topology_and_pmt_dark_pbr":True,
 "source_packed_maps":True,"wheel_geometry_preserved":True,
 "original_controls_present":True,"camera":s.camera.name,
 "render_validation":"UNTESTED","full_matched":"UNTESTED","Quest3":"UNTESTED"}
(w/"DAYTONA_V8_10_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_10_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
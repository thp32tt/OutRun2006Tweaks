#!/usr/bin/env python3
"""v8.12 true Blender fresh-open independent source and geometry verification."""
import bpy,hashlib,json,math,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))/"blender_v8"
model=W/"Daytona365_Cockpit_Blender_PBR_v8_12.blend"
source=W/"Daytona365_Cockpit_Blender_PBR_v8_11.blend"
manifest=json.loads((W/"DAYTONA_V8_12_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==manifest["new_sha256"]
assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest["source_sha256"]
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert scene.render.engine=="CYCLES"
assert sum(o.type=="MESH" for o in bpy.data.objects)==106
assert sum(o.type=="CURVE" for o in bpy.data.objects)==92
for obj in ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_LOW_CENTER_TUNNEL"):
 assert bpy.data.objects.get(obj),obj
mat=bpy.data.materials["V8_12_Source_Charcoal_Original_V5_Back_Return_PBR"]
nodes=mat.node_tree.nodes;bsdf=nodes["Principled BSDF"]
assert bsdf.inputs["Base Color"].is_linked
assert bsdf.inputs["Normal"].is_linked and bsdf.inputs["Roughness"].is_linked
assert nodes.get("V8_5_ORM_ROUGHNESS_RANGE")
assert .77<nodes["V8_5_ORM_ROUGHNESS_RANGE"].inputs["To Min"].default_value<.80
assert nodes.get("V8_9_PMT_CHARCOAL_DESATURATION")
assert abs(nodes["V8_9_PMT_CHARCOAL_DESATURATION"].inputs["Value"].default_value-.205)<.001
images=[x.image for x in nodes if x.type=="TEX_IMAGE" and x.image]
assert len(images)==4 and all(i.packed_file for i in images)
assert all(i.colorspace_settings.name=="Non-Color" for i in images if
 any(k in i.name.upper() for k in ("NORMAL","ORM","HEIGHT")))
assert any(n.type=="NORMAL_MAP" for n in nodes)
assert any(n.type=="BUMP" for n in nodes)
for side in "LR":
 ob=bpy.data.objects["V5_"+side+"_SEAT_RECLINED_PADDED_BACK"]
 assert ob.type=="MESH" and not ob.hide_render
 assert len(ob.data.vertices)==1617 and len(ob.data.polygons)==3072
 assert ob.data.materials[0] == mat
 assert ob.data.uv_layers.active.name=="UVMap"
 assert .847<max(v.co.z for v in ob.data.vertices)<=.85149
 assert all(math.isfinite(float(q)) for vert in ob.data.vertices for q in vert.co)
 assert all(math.isfinite(float(q)) for poly in ob.data.polygons for q in poly.normal)
 assert len(bpy.data.objects["V8_9_"+side+"_INTEGRATED_PADDED_HEADREST"].data.vertices)==242
 assert len(bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.vertices)==8614
 assert bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.uv_layers.active.name=="V8_11_CROWN_GEODESIC_UV"
 assert bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"].data.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
 for tag in ("+1","-1"):
  assert bpy.data.objects["V8_3_"+side+"_BACK_OUTER_PIPING_"+tag].data.materials[0].name=="V8_11_Source_Charcoal_Seat_Edge_PBR"
report={"status":"DAYTONA_V8_12_FRESH_REOPEN_PASS","blender":bpy.app.version_string,
 "sha256":manifest["new_sha256"],"source_sha256":manifest["source_sha256"],
 "mesh_count":106,"curve_count":92,
 "original_V5_backrest_meshes_dark_tapered_and_retained":True,
 "source_packed_normal_orm_height":True,"original_controls_preserved":True,
 "camera":scene.camera.name,"render_validation":"UNTESTED",
 "full_matched":"UNTESTED","game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_12_VERIFIED.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_12_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
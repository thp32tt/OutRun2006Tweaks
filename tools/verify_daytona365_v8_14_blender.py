#!/usr/bin/env python3
"""Independent fresh-open v8.14 Blender geometry, UV and shader verification."""
import bpy,hashlib,json,math,os
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR", "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
model=w/"Daytona365_Cockpit_Blender_PBR_v8_14.blend"
m=json.loads((w/"DAYTONA_V8_14_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==m["output_sha256"]
assert hashlib.sha256((w/"Daytona365_Cockpit_Blender_PBR_v8_13.blend").read_bytes()).hexdigest()==m["source_sha256"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==106
assert sum(o.type=="CURVE" for o in bpy.data.objects)==94
o=bpy.data.objects["V8_1_COMPACT_SHIFTER_LEATHER_DECK"]
assert len(o.data.vertices)==100 and len(o.data.polygons)==92
assert o.data.uv_layers.active.name=="V8_14_PMT018_DECK_METRIC_TANGENT_UV"
assert len(o.data.uv_layers.active.data)==len(o.data.loops)
assert all(math.isfinite(float(z)) for p in o.data.vertices for z in p.co)
assert all(math.isfinite(float(z)) for p in o.data.polygons for z in p.normal)
assert all(math.isfinite(float(z)) for p in o.data.uv_layers.active.data for z in p.uv)
assert len(o.modifiers)==2
mat=bpy.data.materials["V8_14_PMT018_Shifter_Deck_Grain_Source_PBR"]
assert o.data.materials[0]==mat
nodes=mat.node_tree.nodes
bsdf=nodes["Principled BSDF"]
for sk in ("Base Color","Roughness","Normal"):
 assert bsdf.inputs[sk].is_linked
assert nodes.get("V8_14_PMT018_SOURCE_DARK_LEATHER")
assert nodes["V8_5_ORM_ROUGHNESS_RANGE"].inputs["Value"].is_linked
imgs=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
assert len(imgs)>=4 and all(i.packed_file for i in imgs)
assert any("Normal" in i.name for i in imgs)
assert any("ORM" in i.name for i in imgs)
for i in imgs:
 if any(s in i.name.upper() for s in ("NORMAL","ORM","HEIGHT")):assert i.colorspace_settings.name=="Non-Color"
gate=bpy.data.objects["DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3"]
knob=bpy.data.objects["V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB"]
assert len(gate.data.vertices)==32 and len(knob.data.vertices)==433
assert gate.data.materials[0].name=="Chrome"
for side in ("L","R"):
 assert bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"].data.uv_layers.active.name=="V8_13_Geodesic_Seat_Leather_UV"
 assert bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.uv_layers.active.name=="V8_11_CROWN_GEODESIC_UV"
 assert bpy.data.objects["V5_"+side+"_SEAT_RECLINED_PADDED_BACK"].data.materials[0].name=="V8_12_Source_Charcoal_Original_V5_Back_Return_PBR"
for name in m["physical_seams"]:
 obj=bpy.data.objects[name]
 assert obj.type=="CURVE" and len(obj.data.splines[0].points)==10
 assert obj.data.materials[0]==mat
rep={"status":"DAYTONA_V8_14_FRESH_REOPEN_PASS",
 "blender":bpy.app.version_string,"model_sha256":m["output_sha256"],
 "mesh_count":106,"curve_count":94,"mesh_vertices":100,
 "mesh_polygons":92,"UV":o.data.uv_layers.active.name,
 "packed_maps":[i.name for i in imgs],"original_chrome_gate_and_knob_preserved":True,
 "v813_channels_preserved":True,"render_validation":"UNTESTED",
 "Quest3_tested":False}
(w/"DAYTONA_V8_14_VERIFIED.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
print("DAYTONA_V8_14_FRESH_REOPEN_PASS",json.dumps(rep),flush=True)
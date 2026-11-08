#!/usr/bin/env python3
"""Blender-fresh-process readback of saved Daytona v8.17 mesh + PBR contract."""
import bpy,json,hashlib,math,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v817_ai2_0917_gpt6"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_17_BUILD_MANIFEST.json").read_text())
s=W/m["output"]
assert Path(bpy.data.filepath).resolve()==s.resolve()
assert hashlib.sha256(s.read_bytes()).hexdigest()==m["output_sha256"]
assert sum(o.type=="MESH" for o in bpy.data.objects)==107
assert sum(o.type=="CURVE" for o in bpy.data.objects)==98
cow=bpy.data.objects[m["cowl_object"]]
me=cow.data
assert len(me.vertices)==650 and len(me.polygons)==648
assert me.uv_layers.active.name=="V8_17_Cowl_Metric_Tangent_UV"
assert "V8_17_Cowl_Tangent_Normal_UV" in me.uv_layers
assert all(math.isfinite(float(z)) for v in me.vertices for z in v.co)
material=bpy.data.materials["V8_17_Source_Packed_Dark_Dashboard_PBR"]
assert cow.data.materials[0]==material
assert bpy.data.objects["V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL"].data.materials[0]==material
assert bpy.data.objects["V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE"].data.materials[0]==material
nodes=material.node_tree.nodes
for name in ("V8_17_Original_Dash_Charcoal_Value","V8_17_Packed_Cowl_Tangent_Normal",
             "V8_17_Source_And_Cowl_Normal_Mix","V8_17_Aligned_Cowl_Tangent_UV_Node",
             "V8_5_ORM_ROUGHNESS_RANGE","Normal Map","Bump"):
 assert name in nodes,name
norm=bpy.data.images["V8_17_Cowl_Packed_Analytical_Tangent_Normal"]
assert norm.packed_file and norm.colorspace_settings.name=="Non-Color"
assert tuple(norm.size)==(256,256)
tex=[a.image for a in nodes if a.type=="TEX_IMAGE" and a.image]
assert len(tex)>=5 and all(a.packed_file for a in tex)
assert len(bpy.data.objects["DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH"].data.vertices)==20
assert len(bpy.data.objects["DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY"].data.vertices)==908
assert len(bpy.data.objects["DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4"].data.vertices)==70
assert len(bpy.data.objects["V8_L_CLASSIC_PADDED_CUSHION"].data.vertices)==7738
assert len(bpy.data.objects["V8_L_TAPERED_PADDED_BACKREST"].data.vertices)==8614
assert len(bpy.data.objects["V8_R_CLASSIC_PADDED_CUSHION"].data.vertices)==7738
assert len(bpy.data.objects["V8_R_TAPERED_PADDED_BACKREST"].data.vertices)==8614
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
result={"status":"DAYTONA_V8_17_FRESH_REOPEN_PASS","model_sha256":m["output_sha256"],
        "mesh_count":107,"curve_count":98,"cowl_vertices":650,
        "cowl_polygons":648,"packed_images":len(tex),"blender":bpy.app.version_string,
        "render_validation":"UNTESTED","full_matched":"UNTESTED","Quest3":"UNTESTED"}
(W/"DAYTONA_V8_17_VERIFIED.json").write_text(json.dumps(result,indent=2))
print("DAYTONA_V8_17_FRESH_REOPEN_PASS",json.dumps(result),flush=True)
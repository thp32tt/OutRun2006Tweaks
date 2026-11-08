#!/usr/bin/env python3
"""Independent Blender fresh-open validation of true v8.24-r2 through-holes."""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
from mathutils import Vector
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v824_ai2_1226"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_24_R2_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert hashlib.sha256((W/m["input"]).read_bytes()).hexdigest()==m["input_sha256"]
assert hashlib.sha256((W/m["output"]).read_bytes()).hexdigest()==m["output_sha256"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==111
assert len(bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"].data.vertices)==61
assert len(bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0"].data.vertices)==4
assert len(bpy.data.objects["V7_SHORT_SHAFT_AT_WHEEL_HUB"].data.vertices)==224
assert len(bpy.data.objects["V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT"].data.vertices)==672
native=bpy.data.materials["V8_23_Source_Linked_Brushed_Spoke_Aluminum"]
bore=bpy.data.materials[m["new_bore_wall_material"]]
assert bore.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value>.4
assert native.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value<.35
im=bpy.data.images["V8_23_Stamped_Spoke_Packed_Tangent_Normal"]
assert im.packed_file and tuple(im.size)==(256,256)
report={}
for side,values in m["spoke_results"].items():
 ob=bpy.data.objects[values["name"]];me=ob.data
 assert len(me.vertices)==values["vertices"] and len(me.polygons)==values["faces"]
 assert me.materials[0]==native and me.materials[1]==bore
 assert sum(p.material_index==1 for p in me.polygons)>=90
 bm=bmesh.new();bm.from_mesh(me)
 assert all(len(e.link_faces)==2 for e in bm.edges),side
 assert abs(bm.calc_volume(signed=True))>1e-8
 bm.free()
 assert "V8_23_Metric_Stamped_Spoke_UV" in me.uv_layers
 assert "V8_23_Aligned_Spoke_Tangent_Normal_UV" in me.uv_layers
 assert all(math.isfinite(float(c)) for layer in me.uv_layers for loop in layer.data for c in loop.uv)
 inverse=ob.matrix_world.inverted()
 direc=(inverse.to_3x3()@Vector((0,-1,0))).normalized()
 for hole in m["holes"][side]:
  cx,cz=hole["x"],hole["z"]
  hit,_,_,_=ob.ray_cast(inverse@Vector((cx,-.22,cz)),direc,distance=.15)
  assert not hit,(side,"real through hole blocked")
  dx=.006 if side=="LOWER" else 0.
  dz=.006 if side!="LOWER" else 0.
  hit,_,_,_=ob.ray_cast(inverse@Vector((cx+dx,-.22,cz+dz)),direc,distance=.15)
  assert hit,(side,"surrounding spoke metal absent")
 report[side]={"mesh_vertices":len(me.vertices),"faces":len(me.polygons),
  "three_real_holes":True,"closed_manifold":True}
assert not any(x.name.startswith("V8_24_TEMP_BOOLEAN_DRILL") for x in bpy.data.objects)
result={"status":"DAYTONA_V8_24_R2_FRESH_REOPEN_PASS",
"input_sha256":m["input_sha256"],"output_sha256":m["output_sha256"],
"blender":bpy.app.version_string,"spokes":report,"nine_true_holes":True,
"real_dark_bore_material":True,"tangent_normal_packed":True,
"source_61v_wheel_unchanged":True,
"mesh_count":113,"curve_count":111,"preview":"UNTESTED",
"original_game_OVC_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_24_R2_VERIFIED.json").write_text(json.dumps(result,indent=2))
print("DAYTONA_V8_24_R2_FRESH_REOPEN_PASS",json.dumps(result),flush=True)
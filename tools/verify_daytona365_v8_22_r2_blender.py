#!/usr/bin/env python3
"""Fresh Blender process: v8.22 exact source, manifold/UV/PBR audit."""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
W=Path(os.environ["DAYTONA365_WORKDIR"])/"blender_v8"
m=json.loads((W/"DAYTONA_V8_22_R2_BUILD_MANIFEST.json").read_text())
for k,fn in (("input_sha256",m["input"]),("output_sha256",m["output"]),("normal_sha256",m["normal"])):
 assert hashlib.sha256((W/fn).read_bytes()).hexdigest()==m[k],k
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==111
boot=bpy.data.objects["V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT"]
mesh=boot.data
assert len(mesh.vertices)==672 and len(mesh.polygons)==672
bm=bmesh.new();bm.from_mesh(mesh)
assert len(bm.verts)==672 and all(len(e.link_faces)==2 for e in bm.edges)
signed_volume=bm.calc_volume(signed=True)
assert abs(signed_volume)>1.e-7
bm.free()
assert "V8_22_Shifter_Metric_Leather_UV" in mesh.uv_layers
assert "V8_22_Shifter_Aligned_Normal_UV" in mesh.uv_layers
for l in mesh.uv_layers:
 assert all(math.isfinite(float(c)) for loop in l.data for c in loop.uv)
mat=bpy.data.materials["V8_22_Source_Packed_Shifter_Boot_Black_Leather_PBR"]
assert mesh.materials[0]==mat
nodes=mat.node_tree.nodes; bsdf=nodes["Principled BSDF"]
assert all(bsdf.inputs[i].is_linked for i in ("Base Color","Normal","Roughness"))
assert bsdf.inputs["Metallic"].default_value==0
assert nodes["V8_22_Shifter_Aligned_Normal_UV_Node"].uv_map=="V8_22_Shifter_Aligned_Normal_UV"
assert nodes["Normal Map"].inputs["Color"].links[0].from_node.name=="V8_22_Source_And_Shifter_Normal_Mix"
im=bpy.data.images["V8_22_Shifter_Boot_Packed_Tangent_Normal"]
assert im.packed_file and tuple(im.size)==(256,256) and im.colorspace_settings.name=="Non-Color"
images=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
assert len(images)>=5 and all(i.packed_file for i in images)
assert all(any(key in i.name for i in images) for key in ("BaseColor","Normal","ORM","Height"))
for name in ("V8_22_LEFT_SHIFTER_BOOT_SEAM","V8_22_RIGHT_SHIFTER_BOOT_SEAM"):
 o=bpy.data.objects[name]
 assert o.type=="CURVE" and len(o.data.splines[0].points)==14
for name in ("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V5_MANUAL_SHIFTER_CHROME_SHAFT","V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
 "V8_1_COMPACT_SHIFTER_LEATHER_DECK","V8_LOW_CENTER_TUNNEL",
 "V7_SHORT_SHAFT_AT_WHEEL_HUB","V8_21_SOURCE_LOWER_GAUGE_SHROUD",
 "V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
 "V6_L_BLENDER_BLACK_FLOOR_MAT","V6_R_BLENDER_BLACK_FLOOR_MAT"):
 assert bpy.data.objects.get(name)
report={"status":"DAYTONA_V8_22_FRESH_REOPEN_PASS",
 "input_sha256":m["input_sha256"],"output_sha256":m["output_sha256"],
 "blender":bpy.app.version_string,"closed_annular_mesh":True,
 "mesh_vertices":672,"mesh_faces":672,"signed_volume":signed_volume,
 "two_true_3d_seams":True,"source_packed_PBR":True,
 "new_tangent_normal_packed":True,"meshes":113,"curves":111,
 "original_game_modified":False,"Quest3_tested":False,"render_validation":"UNTESTED"}
(W/"DAYTONA_V8_22_R2_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_22_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
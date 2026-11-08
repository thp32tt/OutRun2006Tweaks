#!/usr/bin/env python3
"""Independent official Blender 4.5 fresh-open v8.23 geometry/material audit."""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
W=Path(os.environ["DAYTONA365_WORKDIR"])/"blender_v8"
m=json.loads((W/"DAYTONA_V8_23_BUILD_MANIFEST.json").read_text())
for filename,key in ((m["input"],"input_sha256"),(m["output"],"output_sha256"),
                      (m["new_analytical_normal"],"normal_sha256")):
 assert hashlib.sha256((W/filename).read_bytes()).hexdigest()==m[key],key
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==111
native=bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"]
badge=bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0"]
assert len(native.data.vertices)==61 and len(native.data.polygons)==31
assert len(badge.data.vertices)==4
mat=bpy.data.materials["V8_23_Source_Linked_Brushed_Spoke_Aluminum"]
assert mat.use_nodes
nodes=mat.node_tree.nodes
bsdf=nodes["Principled BSDF"]; bump=nodes["V8_BrushedMetalNormal"]
assert bsdf.inputs["Normal"].links[0].from_node==bump
assert .7<float(bsdf.inputs["Metallic"].default_value)<.9
assert .25<float(bsdf.inputs["Roughness"].default_value)<.36
assert bump.inputs["Normal"].links[0].from_node.name=="V8_23_Spoke_Analytical_Normal_Map"
assert nodes["V8_23_Aligned_Stamped_Spoke_UV"].uv_map=="V8_23_Aligned_Spoke_Tangent_Normal_UV"
img=bpy.data.images["V8_23_Stamped_Spoke_Packed_Tangent_Normal"]
assert img.packed_file and img.colorspace_settings.name=="Non-Color"
assert tuple(img.size)==(256,256)
assert nodes["V8_23_Packed_Stamped_Spoke_Tangent_Normal"].image==img
audit={}
for side in ("LEFT","RIGHT","LOWER"):
 obj=bpy.data.objects["V7_3_"+side+"_SHORT_CHROME_SPOKE_BRIDGE"]
 mesh=obj.data
 assert len(mesh.vertices)==224 and len(mesh.polygons)==210
 assert mesh.materials[0]==mat
 assert "V8_23_Metric_Stamped_Spoke_UV" in mesh.uv_layers
 assert "V8_23_Aligned_Spoke_Tangent_Normal_UV" in mesh.uv_layers
 for layer in mesh.uv_layers:
  assert all(math.isfinite(float(c)) for el in layer.data for c in el.uv)
 bm=bmesh.new();bm.from_mesh(mesh)
 assert len(bm.verts)==224 and all(len(e.link_faces)==2 for e in bm.edges)
 vol=bm.calc_volume(signed=True)
 assert abs(vol)>1.e-8
 bm.free()
 w=[obj.matrix_world @v.co for v in mesh.vertices]
 expected=m["spoke_bridges"][side]["world_bounds"]
 for axis in range(3):
  assert abs(min(p[axis] for p in w)-expected[axis][0])<1.e-5
  assert abs(max(p[axis] for p in w)-expected[axis][1])<1.e-5
 audit[side]={"vertices":224,"faces":210,"manifold":True,"signed_volume_m3":vol,
             "original_box_envelope_unchanged":True}
for name in ("V7_SHORT_SHAFT_AT_WHEEL_HUB","V8_21_SOURCE_LOWER_GAUGE_SHROUD",
 "V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT","DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
 "V6_L_BLENDER_BLACK_FLOOR_MAT","V6_R_BLENDER_BLACK_FLOOR_MAT"):
 assert bpy.data.objects.get(name),name
report={"status":"DAYTONA_V8_23_FRESH_REOPEN_PASS","input_sha256":m["input_sha256"],
 "output_sha256":m["output_sha256"],"blender":bpy.app.version_string,
 "three_physically_manifold_reprofiled_helpers":audit,
 "native_source_spoke_badge_rim_and_prior_meshes_preserved":True,
 "packed_256_tangent_normal":True,"machined_metal_source_bump_preserved":True,
 "mesh_count":113,"curve_count":111,
 "render_validation":"UNTESTED","OVC_original_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_23_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_23_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
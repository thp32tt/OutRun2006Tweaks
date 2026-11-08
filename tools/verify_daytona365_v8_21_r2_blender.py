#!/usr/bin/env python3
"""v8.21 real Blender independent fresh-open verification, not source-only CI."""
import bpy,hashlib,json,math,os,bmesh
from pathlib import Path
W=Path(os.environ["DAYTONA365_WORKDIR"])/"blender_v8"
m=json.loads((W/"DAYTONA_V8_21_R2_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
for name,key in ((m["source"],"source_sha256"),(m["output"],"output_sha256"),
                 (m["new_packed_analytical_normal"],"normal_sha256")):
 assert hashlib.sha256((W/name).read_bytes()).hexdigest()==m[key],key
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==109
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
shaft=bpy.data.objects["V7_SHORT_SHAFT_AT_WHEEL_HUB"]
assert len(shaft.data.vertices)==224 and len(shaft.data.polygons)==210
assert shaft.data.materials[0].name=="V7_Machined_Aluminum"
assert "V8_21_Hub_Metric_Tangent_UV" in shaft.data.uv_layers
shroud=bpy.data.objects["V8_21_SOURCE_LOWER_GAUGE_SHROUD"]
me=shroud.data
assert len(me.vertices)==168 and len(me.polygons)==162
assert len(me.materials)==1
assert me.materials[0].name=="V8_21_Source_Packed_Lower_Gauge_Shroud_PBR"
assert "V8_21_Shroud_Metric_Tangent_UV" in me.uv_layers
assert "V8_21_Shroud_Aligned_Tangent_Normal_UV" in me.uv_layers
def manifold(mesh):
 bm=bmesh.new();bm.from_mesh(mesh)
 good=all(len(e.link_faces)==2 for e in bm.edges)
 bm.free()
 return good
assert manifold(shaft.data) and manifold(me)
for obj in (shaft,shroud):
 assert all(math.isfinite(float(c)) for v in obj.data.vertices for c in v.co)
 for uv in obj.data.uv_layers:
  assert all(math.isfinite(float(c)) for d in uv.data for c in d.uv)
atlas=bpy.data.objects["DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH"]
bezel=bpy.data.objects["DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY"]
max_z=max(v.co.z for v in me.vertices)
min_atlas=min((atlas.matrix_world@v.co).z for v in atlas.data.vertices)
min_bezel=min((bezel.matrix_world@v.co).z for v in bezel.data.vertices)
assert max_z<min_atlas and max_z<min_bezel
assert 0<min_bezel-max_z<.004
material=bpy.data.materials["V8_21_Source_Packed_Lower_Gauge_Shroud_PBR"]
nd=material.node_tree.nodes
bsdf=nd["Principled BSDF"]
for key in ("Base Color","Normal","Roughness"):assert bsdf.inputs[key].is_linked
assert bsdf.inputs["Metallic"].default_value==0
assert nd["Normal Map"].inputs["Color"].links[0].from_node.name=="V8_21_Source_And_Shroud_Normal_Mix"
assert nd["V8_21_Shroud_Normal_UV_Node"].uv_map=="V8_21_Shroud_Aligned_Tangent_Normal_UV"
im=bpy.data.images["V8_21_Gauge_Shroud_Packed_Tangent_Normal"]
assert im.packed_file and tuple(im.size)==(256,256) and im.colorspace_settings.name=="Non-Color"
imgs=[n.image for n in nd if n.type=="TEX_IMAGE" and n.image]
assert len(imgs)>=5 and all(i.packed_file for i in imgs)
assert any("ORM" in i.name for i in imgs) and any("Height" in i.name for i in imgs)
welt=bpy.data.objects["V8_21_SOURCE_LOWER_GAUGE_SHROUD_WELT"]
assert welt.type=="CURVE" and len(welt.data.splines[0].points)==21
for n,verts in (
 ("V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",61),
 ("V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0",4),
 ("V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material002_a0",153),
 ("V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",1536),
 ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",20),
 ("DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",908),
 ("V8_17_ORIGINAL_GUIDED_GAUGE_COWL",650),
 ("V8_19_L_DASH_DOOR_FORMED_ENDCAP",128),
 ("V8_19_R_DASH_DOOR_FORMED_ENDCAP",128),
 ("V6_L_BLENDER_BLACK_FLOOR_MAT",494),
 ("V6_R_BLENDER_BLACK_FLOOR_MAT",494)):
 assert len(bpy.data.objects[n].data.vertices)==verts,n
r={"status":"DAYTONA_V8_21_R2_FRESH_REOPEN_PASS",
 "input_sha256":m["source_sha256"],"output_sha256":m["output_sha256"],
 "blender":bpy.app.version_string,"meshes":113,"curves":109,
 "manifold_new_physical_shroud":True,"manifold_reprofiled_hub":True,
 "atlas_bezel_lower_shroud_no_vertical_overlap":True,
 "gauge_clearance_m":float(min_bezel-max_z),
 "packed_source_PBR_detail_normal":True,
 "factory_wheel_spokes_emblem_and_rim_retained":True,
 "game_runtime_validation":"UNTESTED","render_validation":"UNTESTED"}
(W/"DAYTONA_V8_21_R2_VERIFIED.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_21_R2_FRESH_REOPEN_PASS",json.dumps(r),flush=True)
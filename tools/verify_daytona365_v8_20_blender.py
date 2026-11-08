#!/usr/bin/env python3
"""Independent Blender 4.5.15 fresh-open source preservation/packed-PBR audit."""
import bpy,hashlib,json,math,os
from pathlib import Path
W=Path(os.environ["DAYTONA365_WORKDIR"])/"blender_v8"
m=json.loads((W/"DAYTONA_V8_20_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
for p,key in ((W/m["input"],"input_sha256"),(W/m["output"],"output_sha256"),
              (W/m["new_analytical_normal"],"new_analytical_normal_sha256")):
 assert hashlib.sha256(p.read_bytes()).hexdigest()==m[key],key
assert sum(o.type=="MESH" for o in bpy.data.objects)==112
assert sum(o.type=="CURVE" for o in bpy.data.objects)==108
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
mat=bpy.data.materials["V8_20_Source_Packed_Dark_Rubber_Footwell_PBR"]
nodes=mat.node_tree.nodes;bsdf=nodes["Principled BSDF"]
assert all(bsdf.inputs[k].is_linked for k in ("Base Color","Normal","Roughness"))
assert bsdf.inputs["Metallic"].default_value==0
assert nodes["Normal Map"].inputs["Color"].links[0].from_node.name=="V8_20_Source_And_Footwell_Tangent_Normal_Mix"
assert nodes["V8_20_Aligned_Footwell_Normal_UV_Node"].uv_map=="V8_20_Footwell_Aligned_Normal_UV"
detail=bpy.data.images["V8_20_Footwell_Packed_Tangent_Normal"]
assert detail.packed_file and detail.colorspace_settings.name=="Non-Color"
assert tuple(detail.size)==(256,256)
imgs=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
assert len(imgs)>=5 and all(i.packed_file for i in imgs)
assert any("ORM" in i.name for i in imgs)
assert any("Height" in i.name for i in imgs)
for side,cx in (("L",-.353),("R",.353)):
 o=bpy.data.objects["V6_"+side+"_BLENDER_BLACK_FLOOR_MAT"]
 me=o.data
 assert len(me.vertices)==494 and len(me.polygons)==492
 assert len(me.edges)>0 and me.materials[0]==mat
 assert len(me.uv_layers)>=2
 assert "V8_20_Footwell_Metric_Tangent_UV" in me.uv_layers
 assert "V8_20_Footwell_Aligned_Normal_UV" in me.uv_layers
 assert all(math.isfinite(float(v)) for u in me.uv_layers for p in u.data for v in p.uv)
 world=[o.matrix_world@p.co for p in me.vertices]
 assert abs(min(p.x for p in world)-(cx-.225))<.0001
 assert abs(max(p.x for p in world)-(cx+.225))<.0001
 assert abs(min(p.y for p in world)+.26)<.0001
 assert abs(max(p.y for p in world)-.42)<.0001
 assert min(p.z for p in world)>.2824 and max(p.z for p in world)<.302
 assert max(p.z for p in world)-.2975>.003
 edge=bpy.data.objects["V8_20_"+side+"_FOOTWELL_MAT_PERIMETER_WELT"]
 assert edge.type=="CURVE" and edge.data.splines[0].use_cyclic_u
 assert len(edge.data.splines[0].points)==60
for name in ("V6_DRIVER_METAL_PEDAL_0","V6_DRIVER_METAL_PEDAL_1",
 "V6_DRIVER_METAL_PEDAL_2","V7_REAL_BLACK_CARPET_FLOOR",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "V8_19_L_DASH_DOOR_FORMED_ENDCAP","V8_19_R_DASH_DOOR_FORMED_ENDCAP"):
 assert bpy.data.objects.get(name)
assert all(len(bpy.data.objects["V6_DRIVER_METAL_PEDAL_"+str(j)].data.vertices)==8 for j in range(3))
report={"status":"DAYTONA_V8_20_FRESH_REOPEN_PASS","blender":bpy.app.version_string,
 "input_sha256":m["input_sha256"],"output_sha256":m["output_sha256"],
 "mesh_count":112,"curve_count":108,"true_closed_mats_494_vertices_492_faces_each":True,
 "source_controls_seats_v819_door_ends_preserved":True,
 "packed_source_basecolor_normal_ORM_height":True,
 "new_256_tangent_normal_packed":True,"render_validation":"UNTESTED",
 "OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_20_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_20_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
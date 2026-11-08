#!/usr/bin/env python3
"""Official independent Blender fresh-open v8.19 source-to-actual saved scene audit."""
import bpy,hashlib,json,math,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v819_ai2_093x"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_19_R2_BUILD_MANIFEST.json").read_text())
src=W/m["source"];dst=W/m["output"]
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==dst.resolve()
assert hashlib.sha256(src.read_bytes()).hexdigest()==m["source_sha256"]
assert hashlib.sha256(dst.read_bytes()).hexdigest()==m["output_sha256"]
assert hashlib.sha256((W/m["new_packed_tangent_normal"]).read_bytes()).hexdigest()==m["new_tangent_normal_sha256"]
assert sum(o.type=="MESH" for o in bpy.data.objects)==112
assert sum(o.type=="CURVE" for o in bpy.data.objects)==106
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
mat=bpy.data.materials["V8_19_Source_Dash_To_Door_Dark_PBR"]
nd=mat.node_tree.nodes
principled=nd["Principled BSDF"]
assert all(principled.inputs[k].is_linked for k in ("Base Color","Roughness","Normal"))
assert principled.inputs["Metallic"].default_value==0
assert nd["Normal Map"].inputs["Color"].links[0].from_node.name=="V8_19_Source_And_Endcap_Tangent_Normal_Mix"
assert nd["V8_19_Aligned_Endcap_UV_Node"].uv_map=="V8_19_Endcap_Aligned_Tangent_UV"
im=bpy.data.images["V8_19_Endcap_Packed_Tangent_Normal"]
assert im.packed_file and im.colorspace_settings.name=="Non-Color"
assert tuple(im.size)==(256,256)
imgs=[n.image for n in nd if n.type=="TEX_IMAGE" and n.image]
assert len(imgs)>=5 and all(n.packed_file for n in imgs)
assert any("ORM" in n.name for n in imgs) and any("Height" in n.name for n in imgs)
assert any(n.type=="BUMP" for n in nd)
for side in "LR":
 door=bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"].data
 assert len(door.vertices)==465 and len(door.polygons)==840
 assert door.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
 assert door.materials[0].name=="V8_10_Source_Charcoal_Door_Leather_PBR"
 top=bpy.data.objects["V8_3_"+side+"_BLACK_DOOR_TOP_CAP"].data
 assert len(top.vertices)==136 and len(top.polygons)==130
 assert top.materials[0]==mat
 end=bpy.data.objects["V8_19_"+side+"_DASH_DOOR_FORMED_ENDCAP"].data
 assert len(end.vertices)==128 and len(end.polygons)==122 and end.materials[0]==mat
 assert "V8_19_Endcap_Metric_Tangent_UV" in end.uv_layers
 assert "V8_19_Endcap_Aligned_Tangent_UV" in end.uv_layers
 assert all(math.isfinite(float(x)) for v in end.vertices for x in v.co)
 for n in ("V8_19_"+side+"_TOP_ENDCAP_STITCH",
           "V8_19_"+side+"_FORWARD_DOOR_TOP_STITCH"):
  assert bpy.data.objects[n].type=="CURVE"
  assert len(bpy.data.objects[n].data.splines[0].points)==16
 assert len(bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.vertices)==8614
 assert len(bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"].data.vertices)==7738
for n in ("V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
"DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
"V8_18_L_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN",
"V8_18_R_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN"):
 assert bpy.data.objects.get(n)
result={"status":"DAYTONA_V8_19_FRESH_REOPEN_PASS",
        "source_sha256":m["source_sha256"],"model_sha256":m["output_sha256"],
        "blender":bpy.app.version_string,
        "meshes":112,"curves":106,"real_door_reshaping":True,
        "reconstructed_form_topcaps":True,
        "physical_endcap_meshes":True,"packed_original_source_PBR_and_new_normal":True,
        "render_validation":"UNTESTED","OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_19_VERIFIED.json").write_text(json.dumps(result,indent=2))
print("DAYTONA_V8_19_FRESH_REOPEN_PASS",json.dumps(result),flush=True)
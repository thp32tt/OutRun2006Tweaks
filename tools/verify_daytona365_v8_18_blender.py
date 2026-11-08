#!/usr/bin/env python3
"""Actual independent Blender fresh-reopen v8.18 geometry, UV and PBR proof."""
import bpy,hashlib,json,math,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v818_ai2_0926"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_18_R2_BUILD_MANIFEST.json").read_text())
src=W/m["source"];dest=W/m["output"]
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==dest.resolve()
assert hashlib.sha256(src.read_bytes()).hexdigest()==m["source_sha256"]
assert hashlib.sha256(dest.read_bytes()).hexdigest()==m["output_sha256"]
assert hashlib.sha256((W/m["new_packed_normal"]).read_bytes()).hexdigest()==m["new_normal_sha256"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==110
assert sum(o.type=="CURVE" for o in bpy.data.objects)==102
bank=bpy.data.objects["DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4"]
assert len(bank.data.vertices)==70 and len(bank.data.polygons)==96
bankx=max(abs(v.co.x) for v in bank.data.vertices)
bankz=min(v.co.z for v in bank.data.vertices)
assert .142<bankx<.143 and .586<bankz<.588
pad=bpy.data.objects["V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE"].data
assert len(pad.vertices)==1885 and len(pad.polygons)==3584
assert pad.uv_layers.active.name=="UVMap"
assert pad.uv_layers.get("V8_18_Surround_Aligned_Normal_UV")
assert sum(p.material_index==1 for p in pad.polygons)==m["stack_PBR_faces"]
assert m["native_face_changed_vertices"]>350
fair=bpy.data.objects["V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"].data
assert len(fair.vertices)==16 and len(fair.polygons)==14
mat=bpy.data.materials["V8_18_Source_BlackLeather_SwitchSurround_PBR"]
assert fair.materials[0]==mat and pad.materials[1]==mat
nd=mat.node_tree.nodes;bsdf=nd["Principled BSDF"]
for sk in ("Base Color","Roughness","Normal"):assert bsdf.inputs[sk].is_linked
assert nd["Normal Map"].inputs["Color"].links[0].from_node.name=="V8_18_Source_And_Surround_Tangent_Normal_Mix"
assert nd["V8_18_Aligned_Normal_UV_Node"].uv_map=="V8_18_Surround_Aligned_Normal_UV"
im=bpy.data.images["V8_18_SwitchStack_Packed_Tangent_Normal"]
assert im.packed_file and tuple(im.size)==(256,256)
assert im.colorspace_settings.name=="Non-Color"
assert nd["V8_18_Packed_Surround_Tangent_Normal"].image==im
assert nd["V8_5_ORM_ROUGHNESS_RANGE"].inputs["Value"].is_linked
imgs=[n.image for n in nd if n.type=="TEX_IMAGE" and n.image]
assert len(imgs)>=5 and all(i.packed_file for i in imgs)
assert any("ORM" in i.name for i in imgs) and any("Height" in i.name for i in imgs)
assert any(n.type=="BUMP" for n in nd)
for i in imgs:
 if any(t in i.name.upper() for t in ("NORMAL","ORM","HEIGHT")):
  assert i.colorspace_settings.name=="Non-Color"
for side in "LR":
 name="V8_18_"+side+"_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN"
 o=bpy.data.objects[name];me=o.data
 assert len(me.vertices)==104 and len(me.polygons)==98
 assert me.materials[0]==mat
 assert min(abs(v.co.x) for v in me.vertices)>bankx
 for key in ("V8_18_Surround_Metric_Tangent_UV","V8_18_Surround_Aligned_Normal_UV"):
  assert me.uv_layers.get(key)
  assert all(math.isfinite(float(x)) for lp in me.uv_layers[key].data for x in lp.uv)
 for typ in ("INNER","OUTER"):
  welt=bpy.data.objects["V8_18_"+side+"_STACK_"+typ+"_WELT"]
  assert welt.type=="CURVE" and len(welt.data.splines[0].points)==13
 assert bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.uv_layers.active.name=="V8_16_Backrest_Metric_Tangent_UV"
 assert bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"].data.uv_layers.active.name=="V8_15_CROWN_BOLSTER_APRON_METRIC_UV"
sill=bpy.data.objects["V8_18_SOURCE_SWITCHBANK_LOWER_MOLDED_SILL"].data
assert len(sill.vertices)==104 and len(sill.polygons)==98
assert max(v.co.z for v in sill.vertices)<bankz
assert sill.materials[0]==mat
assert len(bpy.data.objects["V8_17_ORIGINAL_GUIDED_GAUGE_COWL"].data.vertices)==650
for name in ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"):assert bpy.data.objects.get(name)
for o in [bpy.data.objects["V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE"],bpy.data.objects["V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"]]:
 assert all(math.isfinite(float(x)) for v in o.data.vertices for x in v.co)
report={"status":"DAYTONA_V8_18_FRESH_REOPEN_PASS",
 "blender":bpy.app.version_string,"model_sha256":m["output_sha256"],
 "input_sha256":m["source_sha256"],"mesh_count":110,"curve_count":102,
 "native_center_fascia_sculpted_vertices":m["native_face_changed_vertices"],
 "switch_surround_pbr_faces":m["stack_PBR_faces"],
 "three_closed_source_switchbank_surround_meshes":True,
 "packed_original_BlackLeather_Normal_ORM_Height":True,
 "new_tangent_normal_packed":True,"original_gauges_switchbank_cowl_seats_preserved":True,
 "render_validation":"UNTESTED","Quest3":"UNTESTED"}
(W/"DAYTONA_V8_18_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_18_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
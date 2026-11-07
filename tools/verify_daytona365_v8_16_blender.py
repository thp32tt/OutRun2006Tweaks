#!/usr/bin/env python3
"""Independent actual Blender fresh-open checks, v8.16 backrest and packed micro normal."""
import bpy,math,hashlib,json,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v816_ai2_0817"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_16_BUILD_MANIFEST.json").read_text())
src=W/m["source"];dest=W/m["output"]
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==dest.resolve()
assert hashlib.sha256(src.read_bytes()).hexdigest()==m["source_sha256"]
assert hashlib.sha256(dest.read_bytes()).hexdigest()==m["output_sha256"]
assert hashlib.sha256((W/m["new_tangent_normal"]).read_bytes()).hexdigest()==m["new_tangent_normal_sha256"]
assert bpy.context.scene.camera.name==m["camera"]
assert sum(o.type=="MESH" for o in bpy.data.objects)==106
assert sum(o.type=="CURVE" for o in bpy.data.objects)==98
normal=bpy.data.images["V8_16_Original_Independent_Wing_Tangent_Normal"]
assert tuple(normal.size)==(256,256) and normal.packed_file
assert normal.colorspace_settings.name=="Non-Color"
mat=bpy.data.materials["V8_16_PMT017_Backrest_Source_Charcoal_PBR"]
nodes=mat.node_tree.nodes;bsdf=nodes["Principled BSDF"]
for s in ("Base Color","Normal","Roughness"):assert bsdf.inputs[s].is_linked
nm=[n for n in nodes if n.type=="NORMAL_MAP"]
assert len(nm)==1
assert nm[0].inputs["Color"].links[0].from_node.name=="V8_16_Original_And_Wing_Normal_Mix"
assert nodes["V8_16_Packed_Wing_Normal"].image==normal
assert nodes["V8_16_Wing_Normal_UV_Node"].uv_map=="V8_16_Aligned_Wing_Tangent_Normal_UV"
assert nodes["V8_5_ORM_ROUGHNESS_RANGE"].inputs["Value"].is_linked
img=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
assert len(img)>=5 and all(x.packed_file for x in img)
assert any("ORM" in x.name.upper() for x in img)
assert any("HEIGHT" in x.name.upper() for x in img)
assert any(n.type=="BUMP" for n in nodes)
for im in img:
 if any(x in im.name.upper() for x in ("NORMAL","ORM","HEIGHT")):
  assert im.colorspace_settings.name=="Non-Color"
for lr in "LR":
 obj=bpy.data.objects["V8_"+lr+"_TAPERED_PADDED_BACKREST"]
 me=obj.data;rep=m["backrests"][lr]
 assert rep["object"]==obj.name
 assert len(me.vertices)==8614 and len(me.polygons)==8612
 assert rep["changed_front_vertices"]>1000
 assert me.uv_layers.active.name=="V8_16_Backrest_Metric_Tangent_UV"
 assert me.uv_layers.get("V8_16_Aligned_Wing_Tangent_Normal_UV")
 assert me.materials[0]==mat
 assert me.materials[1].name=="V8_16_PMT017_Backrest_Return_Source_PBR"
 assert all(math.isfinite(float(x)) for v in me.vertices for x in v.co)
 assert all(math.isfinite(float(x)) for v in me.polygons for x in v.normal)
 for name in ("V8_16_Backrest_Metric_Tangent_UV","V8_16_Aligned_Wing_Tangent_Normal_UV"):
  assert all(math.isfinite(float(x)) for t in me.uv_layers[name].data for x in t.uv)
 for j,i in ((8,11),(23,36),(48,62)):
  k=j*73+i;front=me.vertices[k].co;rear=me.vertices[73*59+k].co
  assert abs((rear.y-front.y)-.054)<.0001
  assert abs((front.z-rear.z)-.004)<.0001
 for name in rep["new_wing_seams"]:
  ob=bpy.data.objects[name]
  assert ob.type=="CURVE" and len(ob.data.splines[0].points)==46
 cushion=bpy.data.objects["V8_"+lr+"_CLASSIC_PADDED_CUSHION"].data
 assert cushion.uv_layers.active.name=="V8_15_CROWN_BOLSTER_APRON_METRIC_UV"
 assert len(cushion.vertices)==7738
 assert cushion.uv_layers.get("V8_13_Seven_Pleat_Aligned_Normal_UV")
 assert len(bpy.data.objects["V8_9_"+lr+"_INTEGRATED_PADDED_HEADREST"].data.vertices)==242
for k in ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"):assert bpy.data.objects.get(k)
report={"status":"DAYTONA_V8_16_FRESH_REOPEN_PASS",
 "model_sha256":m["output_sha256"],"input_sha256":m["source_sha256"],
 "new_normal_sha256":m["new_tangent_normal_sha256"],
 "blender":bpy.app.version_string,"meshes":106,"curves":98,
 "both_backrest_geometry_material_UV":True,
 "packed_tangent_detail_and_source_Normal_ORM_Height":True,
 "v815_cushions_preserved":True,"render_validation":"UNTESTED","Quest3":"UNTESTED"}
(W/"DAYTONA_V8_16_VERIFIED.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_16_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
#!/usr/bin/env python3
"""Independent fresh-open v8.15 Blender seat-bolster and apron source validation."""
import bpy,hashlib,json,math,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))/"blender_v8"
model=W/"Daytona365_Cockpit_Blender_PBR_v8_15.blend"
source=W/"Daytona365_Cockpit_Blender_PBR_v8_14.blend"
m=json.loads((W/"DAYTONA_V8_15_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==m["output_sha256"]
assert hashlib.sha256(source.read_bytes()).hexdigest()==m["input_sha256"]
sc=bpy.context.scene
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sc.render.engine=="CYCLES"
assert sum(o.type=="MESH" for o in bpy.data.objects)==106
assert sum(o.type=="CURVE" for o in bpy.data.objects)==94
mat=bpy.data.materials["V8_15_Source_PMT017_Outer_Bolster_Packed_PBR"]
n=mat.node_tree.nodes;p=n["Principled BSDF"]
assert all(p.inputs[k].is_linked for k in ("Base Color","Roughness","Normal"))
assert n["V8_5_ORM_ROUGHNESS_RANGE"].inputs["Value"].is_linked
images=[q.image for q in n if q.type=="TEX_IMAGE" and q.image]
assert len(images)>=4 and all(q.packed_file for q in images)
assert any("Normal" in q.name for q in images)
assert any("ORM" in q.name for q in images)
assert all(q.colorspace_settings.name=="Non-Color" for q in images if any(t in q.name.upper() for t in ("NORMAL","ORM","HEIGHT")))
report={}
for side in "LR":
 o=bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"]
 me=o.data
 assert len(me.vertices)==7738 and len(me.polygons)==7736
 assert len(me.materials)==3 and me.materials[2]==mat
 assert me.materials[0].name=="V8_13_Source_Sculpted_Charcoal_Cushion_PBR"
 assert me.materials[1].name=="V8_9_Source_Charcoal_Seat_Side_PBR"
 assert me.uv_layers.active.name=="V8_15_CROWN_BOLSTER_APRON_METRIC_UV"
 assert me.uv_layers.get("V8_13_Seven_Pleat_Aligned_Normal_UV")
 assert sum(face.material_index==2 for face in me.polygons)==1456
 assert len(me.uv_layers.active.data)==len(me.loops)
 assert all(math.isfinite(float(q)) for v in me.vertices for q in v.co)
 assert all(math.isfinite(float(q)) for poly in me.polygons for q in poly.normal)
 assert all(math.isfinite(float(q)) for d in me.uv_layers.active.data for q in d.uv)
 assert len(bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.vertices)==8614
 assert bpy.data.objects["V5_"+side+"_SEAT_RECLINED_PADDED_BACK"].data.materials[0].name=="V8_12_Source_Charcoal_Original_V5_Back_Return_PBR"
 assert bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"].data.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
 seams=m["sculpted_source_seat_shells"][side]["seam_curves_reprojected"]
 assert len(seams)==12
 for seam in seams:
  assert bpy.data.objects[seam].type=="CURVE"
 report[side]={"vertices":len(me.vertices),"faces":len(me.polygons),"outer_bolster_faces":1456,"seams":len(seams)}
assert len(bpy.data.objects["DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3"].data.vertices)==32
assert len(bpy.data.objects["V8_1_COMPACT_SHIFTER_LEATHER_DECK"].data.vertices)==100
assert len(bpy.data.objects["V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB"].data.vertices)==433
assert len(bpy.data.objects["V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"].data.vertices)>1000
result={"status":"DAYTONA_V8_15_FRESH_REOPEN_PASS",
 "blender":bpy.app.version_string,"sha256":m["output_sha256"],
 "mesh_count":106,"curve_count":94,"cushions":report,
 "source_packed_pbr_images":[i.name for i in images],
 "source_gate_v813_normal_pmt017_bolster_preserved":True,
 "camera":sc.camera.name,"render_validation":"UNTESTED",
 "full_matched":"UNTESTED","game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_15_VERIFIED.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print("DAYTONA_V8_15_FRESH_REOPEN_PASS",json.dumps(result),flush=True)
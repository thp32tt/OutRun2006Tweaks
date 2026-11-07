#!/usr/bin/env python3
"""Independent fresh-open checks of v8.13 actual dual-cushion topology and packed normal."""
import bpy,hashlib,json,math,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
dest=W/"Daytona365_Cockpit_Blender_PBR_v8_13.blend"
old=W/"Daytona365_Cockpit_Blender_PBR_v8_12.blend"
m=json.loads((W/"DAYTONA_V8_13_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==dest.resolve()
assert hashlib.sha256(dest.read_bytes()).hexdigest()==m["output_sha256"]
assert hashlib.sha256(old.read_bytes()).hexdigest()==m["input_sha256"]
assert hashlib.sha256((W/m["generated_normal"]).read_bytes()).hexdigest()==m["generated_normal_sha256"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert bpy.context.scene.render.engine=="CYCLES"
assert sum(o.type=="MESH" for o in bpy.data.objects)==106
assert sum(o.type=="CURVE" for o in bpy.data.objects)==92
for name in ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_LOW_CENTER_TUNNEL"):
 assert bpy.data.objects.get(name),name
MAT="V8_13_Source_Sculpted_Charcoal_Cushion_PBR"
mat=bpy.data.materials[MAT]
nodes=mat.node_tree.nodes
bsdf=nodes["Principled BSDF"]
assert bsdf.inputs["Base Color"].is_linked and bsdf.inputs["Roughness"].is_linked
assert bsdf.inputs["Normal"].is_linked
assert abs(nodes["V8_9_PMT_CHARCOAL_DESATURATION"].inputs["Value"].default_value-.34)<1e-3
assert abs(nodes["V8_5_ORM_ROUGHNESS_RANGE"].inputs["To Min"].default_value-.72)<1e-3
assert nodes["V8_5_ORM_ROUGHNESS_RANGE"].inputs["Value"].is_linked
mix=nodes["V8_13_SOURCE_PLUS_PLEAT_TANGENT_NORMAL"]
normal=next(n for n in nodes if n.type=="NORMAL_MAP")
assert normal.inputs["Color"].links[0].from_node==mix
assert mix.inputs[1].is_linked and mix.inputs[2].is_linked
assert abs(mix.inputs[0].default_value-.36)<.001
uvmap=nodes["V8_13_PLEAT_DETAIL_UV_SOURCE"]
assert uvmap.uv_map=="V8_13_Seven_Pleat_Aligned_Normal_UV"
tex=nodes["V8_13_PACKED_PLEAT_NORMAL_IMAGE"]
assert tex.inputs["Vector"].links[0].from_node==uvmap
im=tex.image
assert im.name=="V8_13_Seven_Pleat_512_Tangent_Normal"
assert tuple(im.size)==(512,512) and im.packed_file
assert im.colorspace_settings.name=="Non-Color"
# The existing original tangent Normal, ORM and Height remain packed and
# traversable: not just a disconnected label in a copied PBR shader.
original=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image and n!=tex]
assert len(original)==4 and all(q.packed_file for q in original)
assert any("NORMAL" in q.name.upper() for q in original)
assert any("ORM" in q.name.upper() for q in original)
assert any("HEIGHT" in q.name.upper() for q in original)
assert all(q.colorspace_settings.name=="Non-Color" for q in original
 if any(t in q.name.upper() for t in ("NORMAL","ORM","HEIGHT")))
assert any(n.type=="BUMP" for n in nodes)
for side in ("L","R"):
 ob=bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"]
 mesh=ob.data
 assert len(mesh.vertices)==7738 and len(mesh.polygons)==7736
 assert mesh.materials[0]==mat
 assert mesh.materials[1].name=="V8_9_Source_Charcoal_Seat_Side_PBR"
 assert mesh.uv_layers.active.name=="V8_13_Geodesic_Seat_Leather_UV"
 assert mesh.uv_layers.get("V8_13_Seven_Pleat_Aligned_Normal_UV")
 assert all(math.isfinite(float(v)) for p in mesh.vertices for v in p.co)
 assert all(math.isfinite(float(q)) for p in mesh.polygons for q in p.normal)
 for u in ("V8_13_Geodesic_Seat_Leather_UV","V8_13_Seven_Pleat_Aligned_Normal_UV"):
  assert all(math.isfinite(float(q)) for l in mesh.uv_layers[u].data for q in l.uv)
 assert sum(1 for p in mesh.polygons if p.material_index==1)>100
 # Existing 2-skin topology still has 49mm physically-thick return.
 ring=73*53
 for j,i in ((3,7),(13,36),(31,20),(49,60)):
  idx=j*73+i
  a,b=mesh.vertices[idx].co,mesh.vertices[ring+idx].co
  assert abs(float(a.z-b.z)-.049)<.0001
 # Original seat PMT aggregate bound x±.57464, y[-.72863,-.01985].
 assert max(abs(v.co.x) for v in mesh.vertices)<.575
 assert max(v.co.y for v in mesh.vertices)<-.01985
 assert min(v.co.y for v in mesh.vertices)>-.72863
 assert .38<min(v.co.z for v in mesh.vertices[:ring])<.44
 assert max(v.co.z for v in mesh.vertices[:ring])<.49
 assert m["cushions"][side]["physically_changed_top_vertices"]>2000
 for edge in ("LEFT","RIGHT"):
  obc=bpy.data.objects["V8_5_"+side+"_CUSHION_"+edge+"_WELT"]
  assert obc.type=="CURVE" and len(obc.data.splines[0].points)==51
 for frac in ("0.23","0.48","0.72"):
  assert len(bpy.data.objects["V8_5_"+side+"_CUSHION_STITCH_"+frac].data.splines[0].points)==51
 for frac in ("0.16","0.32","0.64","0.80"):
  assert len(bpy.data.objects["V8_7_"+side+"_PLEATED_CUSHION_STITCH_"+frac].data.splines[0].points)==47
 assert len(bpy.data.objects["V8_7_"+side+"_FRONT_CUSHION_APRON_WELT"].data.splines[0].points)==65
 assert bpy.data.objects["V5_"+side+"_SEAT_RECLINED_PADDED_BACK"].data.materials[0].name=="V8_12_Source_Charcoal_Original_V5_Back_Return_PBR"
 assert len(bpy.data.objects["V8_9_"+side+"_INTEGRATED_PADDED_HEADREST"].data.vertices)==242
 assert len(bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.vertices)==8614
 assert bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"].data.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
report={"status":"DAYTONA_V8_13_FRESH_REOPEN_PASS","blender":bpy.app.version_string,
 "source_sha256":m["input_sha256"],"model_sha256":m["output_sha256"],
 "normal_map_sha256":m["generated_normal_sha256"],
 "meshes":106,"curves":92,"source_tangent_normal_retained":True,
 "packed_new_tangent_normal":True,"both_seat_geo_and_uv":True,
 "source_controls_preserved":True,"camera":bpy.context.scene.camera.name,
 "render_validation":"UNTESTED","Quest3":"UNTESTED"}
(W/"DAYTONA_V8_13_VERIFIED.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_13_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
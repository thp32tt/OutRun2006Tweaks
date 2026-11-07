#!/usr/bin/env python3
"""Independent official Blender 4.5.x v8.11 fresh-open source mesh/PBR preservation audit."""
import bpy,json,math,hashlib,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
T=W/"Daytona365_Cockpit_Blender_PBR_v8_11.blend"
P=W/"Daytona365_Cockpit_Blender_PBR_v8_10.blend"
manifest=json.loads((W/"DAYTONA_V8_11_BUILD_MANIFEST.json").read_text())
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==T.resolve()
assert hashlib.sha256(T.read_bytes()).hexdigest()==manifest["new_sha256"]
assert hashlib.sha256(P.read_bytes()).hexdigest()==manifest["source_sha256"]
sc=bpy.context.scene
assert sc.render.engine=="CYCLES"
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
for name in ("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"):
 assert bpy.data.objects.get(name),name
tunnel=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
assert len(tunnel.data.vertices)==78 and tunnel.data.uv_layers.active.name=="V8_8_METRIC_CONSOLE_UV"
for name in ("V8_11_Source_Charcoal_Seat_Edge_PBR",
 "V8_11_Source_Dark_PMT017_Crown_PBR",
 "V8_11_Source_Dark_Headrest_Return_PBR"):
 mat=bpy.data.materials[name]
 nodes=mat.node_tree.nodes;bsdf=nodes["Principled BSDF"]
 assert bsdf.inputs["Base Color"].is_linked and bsdf.inputs["Normal"].is_linked
 assert bsdf.inputs["Roughness"].is_linked
 assert bsdf.inputs["Metallic"].default_value==0
 assert nodes.get("V8_9_PMT_CHARCOAL_DESATURATION")
 assert nodes.get("V8_5_ORM_ROUGHNESS_RANGE")
 assert any(n.type=="NORMAL_MAP" for n in nodes)
 assert any(n.type=="BUMP" for n in nodes)
 imgs=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
 assert len(imgs)>=4 and all(im.packed_file for im in imgs)
 assert all(im.colorspace_settings.name=="Non-Color" for im in imgs
   if any(k in im.name.upper() for k in ("ORM","NORMAL","HEIGHT")))
for side in ("L","R"):
 b=bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"]
 assert len(b.data.vertices)==8614 and len(b.data.polygons)==8612
 assert b.data.uv_layers.active.name=="V8_11_CROWN_GEODESIC_UV"
 assert all(math.isfinite(float(q)) for a in b.data.vertices for q in a.co)
 assert all(math.isfinite(float(q)) for a in b.data.uv_layers.active.data for q in a.uv)
 assert .8495<=max(float(a.co.z) for a in b.data.vertices)<.85149
 # No v8.3 bright material can remain on the four once-cream piping curves.
 for suffix in ("-1","+1"):
  old=bpy.data.objects["V8_3_"+side+"_BACK_OUTER_PIPING_"+suffix]
  assert old.type=="CURVE"
  assert old.data.splines[0].type=="POLY"
  assert len(old.data.splines[0].points)==53
  assert old.data.materials[0].name=="V8_11_Source_Charcoal_Seat_Edge_PBR"
 for frac in ("0.04","0.96"):
  old=bpy.data.objects["V8_"+side+"_BACKREST_PERIMETER_"+frac]
  assert old.data.splines[0].type=="POLY"
  assert len(old.data.splines[0].points)==65
  assert old.data.materials[0].name=="V8_11_Source_Charcoal_Seat_Edge_PBR"
 head=bpy.data.objects["V8_9_"+side+"_INTEGRATED_PADDED_HEADREST"]
 m=head.data
 assert len(m.vertices)==242 and len(m.polygons)==222
 assert m.uv_layers.active.name=="V8_11_HEADREST_SURFACE_GEODESIC_UV"
 assert len(m.materials)==2 and m.materials[0].name=="V8_11_Source_Dark_PMT017_Crown_PBR"
 assert any(p.material_index==1 for p in m.polygons)
 assert abs(max(float(a.co.z) for a in m.vertices)-.8508)<1e-5
 assert min(float(a.co.y) for a in m.vertices)>=-.72863
 assert max(abs(float(a.co.x)) for a in m.vertices)<.55
 assert any(x.type=="WEIGHTED_NORMAL" for x in head.modifiers)
 assert all(math.isfinite(float(q)) for a in m.vertices for q in a.co)
 assert all(math.isfinite(float(q)) for a in m.uv_layers.active.data for q in a.uv)
 for edge in ("LEFT","RIGHT"):
  c=bpy.data.objects["V8_9_"+side+"_HEADREST_"+edge+"_SEAM"]
  assert len(c.data.splines[0].points)==5
  assert c.data.materials[0].name=="V8_11_Source_Charcoal_Seat_Edge_PBR"
 assert len(bpy.data.objects["V8_9_"+side+"_HEADREST_FRONT_HORIZ_WELT"].data.splines[0].points)==33
 assert bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"].data.uv_layers.active.name=="V8_9_RESCULPTED_GEODESIC_UV"
 assert bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"].data.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
assert bpy.data.objects["V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"].data.materials[0].name=="V8_10_Source_Ebonized_Steering_Rim_PBR"
report={"status":"DAYTONA_V8_11_FRESH_REOPEN_PASS","blender":bpy.app.version_string,
 "blend":T.name,"sha256":manifest["new_sha256"],"source_sha256":manifest["source_sha256"],
 "mesh_count":sum(o.type=="MESH" for o in bpy.data.objects),
 "curve_count":sum(o.type=="CURVE" for o in bpy.data.objects),
 "original_piping_reprojected":True,"headrest_original_object_preserved":True,
 "existing_seat_shells_preserved":True,"native_game_controls_preserved":True,
 "source_packed_PBR":True,"camera":sc.camera.name,
 "render_validation":"UNTESTED","original_game/OVC/Quest3":"UNTESTED"}
(W/"DAYTONA_V8_11_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_11_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
#!/usr/bin/env python3
"""Fresh real Blender v8.7 .blend reopen; no render claim implied."""
import bpy,hashlib,json,math,os
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
src=w/"Daytona365_Cockpit_Blender_PBR_v8_7.blend"
prev=w/"Daytona365_Cockpit_Blender_PBR_v8_6.blend"
assert bpy.app.version>=(4,5,0)
assert src.is_file() and prev.is_file()
assert bpy.data.filepath==str(src)
assert hashlib.sha256(prev.read_bytes()).hexdigest()=="cb0eba836a69b3154012bd755fafac92b92b223be0e9394a876c322123e1f2f4"
report=json.loads((w/"DAYTONA_V8_7_BUILD_MANIFEST.json").read_text())
assert hashlib.sha256(src.read_bytes()).hexdigest()==report["new_sha256"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert bpy.context.scene.render.engine=="CYCLES"
for name in ("DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
             "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
             "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
             "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
             "V8_LOW_CENTER_TUNNEL","V8_5_CURVED_COLUMN_COWL"):
 assert name in bpy.data.objects,name
seat=[]
for side in ("L","R"):
 for suffix,ny,kind in (("CLASSIC_PADDED_CUSHION",52,"CUSHION"),
                       ("TAPERED_PADDED_BACKREST",58,"BACKREST")):
  name="V8_"+side+"_"+suffix
  ob=bpy.data.objects[name];m=ob.data
  ring=73*(ny+1)
  assert len(m.vertices)==ring*2
  assert m.uv_layers.active.name=="V8_7_GEODESIC_LEATHER_UV"
  assert len(m.uv_layers.active.data)==len(m.loops)
  assert all(math.isfinite(x) for loop in m.uv_layers.active.data for x in loop.uv)
  side_i=m.materials.find("V8_7_Seat_Side_Return_Leather_PBR")
  assert side_i>=0
  assert sum(p.material_index==side_i for p in m.polygons)>1000
  for j in (0,ny//2,ny):
   for i in (0,12,36,60,72):
    vi=j*73+i
    a,b=m.vertices[vi].co,m.vertices[ring+vi].co
    if kind=="BACKREST":
     assert abs(b.y-a.y-.054)<.0001
     assert abs(b.z-a.z+.004)<.0001
    else:
     assert abs(b.y-a.y-.006)<.0001
     assert abs(b.z-a.z+.049)<.0001
  vertices=[v.co for v in m.vertices[:ring]]
  xs=[x.x for x in vertices];ys=[x.y for x in vertices]
  assert max(abs(min(xs)),abs(max(xs)))<.575
  if kind=="CUSHION":
   assert -.07<max(ys)<-.03
   assert "V8_7_"+side+"_FRONT_CUSHION_APRON_WELT" in bpy.data.objects
  else:
   assert -.735<min(ys)<-.710
  for edge in ("LEFT","RIGHT"):
   assert "V8_5_"+side+"_"+kind+"_"+edge+"_WELT" in bpy.data.objects
   assert "V8_6_"+side+"_"+kind+"_INSET_"+edge+"_BOLSTER_SEAM" in bpy.data.objects
  seat.append(name)
 n="V8_7_"+side+"_SCULPTED_UNDERDASH_KNEE_RETURN"
 ob=bpy.data.objects[n]
 assert len(ob.data.vertices)==30
 assert len(ob.data.polygons)==20
 assert ob.data.uv_layers.active.name=="V8_7_FOOTWELL_METRIC_UV"
 assert any(mod.type=="SOLIDIFY" for mod in ob.modifiers)
 assert "V8_7_"+side+"_KNEE_RETURN_TOP_PIPING" in bpy.data.objects
for mname in ("V8_7_Seat_Side_Return_Leather_PBR","V8_7_Knee_And_Footwell_PBR"):
 m=bpy.data.materials[mname];nodes=m.node_tree.nodes
 bsdf=nodes["Principled BSDF"]
 assert bsdf.inputs["Normal"].is_linked
 assert bsdf.inputs["Roughness"].is_linked
 assert bsdf.inputs["Metallic"].default_value==0
 assert nodes["V8_5_ORM_ROUGHNESS_RANGE"].inputs["Value"].is_linked
 assert any(n.type=="NORMAL_MAP" for n in nodes)
 assert any(n.type=="BUMP" for n in nodes)
 images=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
 assert len(images)>=4 and all(i.packed_file for i in images)
 assert all(i.colorspace_settings.name=="Non-Color" for i in images
  if any(q in i.name.upper() for q in ("ORM","NORMAL","HEIGHT")))
assert max(v.co.z for v in bpy.data.objects["V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"].data.vertices)<.58656
preview=w/"Daytona365_v8_7_ACTUAL_CYCLES_PREVIEW.png"
data={"status":"DAYTONA_V8_7_REAL_BLENDER_FRESH_REOPEN_PASS",
 "blender":bpy.app.version_string,"source":prev.name,"blend":src.name,
 "sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
 "bytes":src.stat().st_size,
 "mesh_count":sum(o.type=="MESH" for o in bpy.data.objects),
 "curve_count":sum(o.type=="CURVE" for o in bpy.data.objects),
 "seat_shells":seat,"connected_side_return_uv_and_pbr":True,
 "source_native_controls_preserved":True,
 "two_footwell_return_panels":True,
 "camera":bpy.context.scene.camera.name,
 "render_validation":"PREVIEW_ONLY" if preview.is_file() else "UNTESTED",
 "full_resolution_render":"UNTESTED","game_runtime":"UNTESTED"}
(w/"DAYTONA_V8_7_VERIFIED.json").write_text(json.dumps(data,indent=2))
print("DAYTONA_V8_7_FRESH_REOPEN_PASS",json.dumps(data),flush=True)

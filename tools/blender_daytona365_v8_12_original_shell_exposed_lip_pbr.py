#!/usr/bin/env python3
"""v8.12: correct exposed original V5 reclining shell over v8.11 dark seats.

Real hide-source diagnostic showed bright near-seat trim disappears only when
the preserved V5 original-backed shell is hidden. Do NOT hide/delete it.
Physically taper its over-height rim against PMT material017 source envelope,
retain original vertex topology and UV, give its visible return source-linked
packed BaseColor/Normal/ORM/Height charcoal PBR, and recalculate normals.
"""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_11.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_12.blend"
EXPECTED="f53ecaf68bea214831dd706baf79e12ab36d9c253febfe8b5bf367c1d13f9cb1"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
assert not DEST.exists(),"No v8.12 checkpoint overwrite"
sc=bpy.context.scene
assert sc.camera and sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
for name in ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_LOW_CENTER_TUNNEL"):
 assert bpy.data.objects.get(name),name

mat=bpy.data.materials["V8_11_Source_Dark_Headrest_Return_PBR"].copy()
mat.name="V8_12_Source_Charcoal_Original_V5_Back_Return_PBR"
nodes=mat.node_tree.nodes;bsdf=nodes["Principled BSDF"]
assert bsdf.inputs["Base Color"].is_linked
assert bsdf.inputs["Roughness"].is_linked and bsdf.inputs["Normal"].is_linked
hsv=nodes["V8_9_PMT_CHARCOAL_DESATURATION"]
hsv.inputs["Saturation"].default_value=.075
hsv.inputs["Value"].default_value=.205
rough=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
assert rough.inputs["Value"].is_linked
rough.inputs["To Min"].default_value=.78
rough.inputs["To Max"].default_value=.93
bsdf.inputs["Metallic"].default_value=0.
images=[]
for n in nodes:
 if n.type=="NORMAL_MAP":n.inputs["Strength"].default_value=.14
 elif n.type=="BUMP":
  n.inputs["Strength"].default_value=.009
  n.inputs["Distance"].default_value=.00013
 elif n.type=="TEX_IMAGE" and n.image:
  assert n.image.packed_file,n.image.name
  if any(k in n.image.name.upper() for k in ("NORMAL","ORM","HEIGHT")):
   assert n.image.colorspace_settings.name=="Non-Color"
  images.append(n.image.name)
assert len(images)>=4
assert any("NORMAL" in n.upper() for n in images)
assert any("ORM" in n.upper() for n in images)
mat["DAYTONA_V8_12"]="source packed BaseColor, Normal tangent, ORM green roughness, Height; only shader tint remap"
mat["DAYTONA_V8_12_PREVIOUS"]="V8_11_Source_Dark_Headrest_Return_PBR"

def smoothstep(a,b,value):
 u=max(0.,min(1.,(value-a)/(b-a)))
 return u*u*(3.-2*u)

report={}
for side,cx in (("L",-.353),("R",.353)):
 name="V5_"+side+"_SEAT_RECLINED_PADDED_BACK"
 ob=bpy.data.objects[name]
 mesh=ob.data
 assert ob.type=="MESH" and len(mesh.vertices)==1617
 assert not ob.hide_render and not ob.hide_viewport
 assert len(mesh.materials)==1 and mesh.materials[0].name=="TanLeather"
 assert mesh.uv_layers.active and len(mesh.uv_layers.active.data)==len(mesh.loops)
 original_uv=mesh.uv_layers.active.name
 before=(len(mesh.vertices),len(mesh.polygons),len(mesh.loops))
 upper_before=max(float(v.co.z) for v in mesh.vertices)
 assert .86<upper_before<.87,upper_before
 # Native V5 original backrest crown extends roughly 14 mm above PMT017
 # height=.85149, poking through our new correct gray upholstery.
 # Preserve silhouette near the lower shoulder; taper only upper 22 cm.
 for p in mesh.vertices:
  z=float(p.co.z)
  k=smoothstep(.69,.864,z)
  p.co.z=z-.0100*k
  p.co.x=cx+(float(p.co.x)-cx)*(1.-.019*k)
 mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(mesh);bm.free()
 for face in mesh.polygons:face.use_smooth=True
 mesh.materials[0]=mat
 ob["DAYTONA_V8_12"]="original V5 seat shell physically tapered below PMT017 upper height, source PBR dark return; not hidden"
 after=(len(mesh.vertices),len(mesh.polygons),len(mesh.loops))
 upper_after=max(float(v.co.z) for v in mesh.vertices)
 assert after==before
 assert .847<upper_after<=.85149,upper_after
 assert all(math.isfinite(float(c)) for v in mesh.vertices for c in v.co)
 assert all(math.isfinite(float(c)) for poly in mesh.polygons for c in poly.normal)
 assert len(mesh.uv_layers[original_uv].data)==len(mesh.loops)
 for uvloop in mesh.uv_layers[original_uv].data:
  assert math.isfinite(float(uvloop.uv.x)) and math.isfinite(float(uvloop.uv.y))
 report[side]={"source_obj":name,"vertices":after[0],"polygons":after[1],
  "native_uv_preserved":original_uv,"z_before":upper_before,
  "z_after":upper_after,"PMT017_z_max":.85149,"source_PBR":mat.name,
  "original_mesh_hidden":False}

# v8.11 correct 2 headrests, 4 seat dark welts, both new seat shells,
# wheel, door and dashboard geometry remain exactly present.
for side in ("L","R"):
 h=bpy.data.objects["V8_9_"+side+"_INTEGRATED_PADDED_HEADREST"]
 assert len(h.data.vertices)==242 and h.data.uv_layers.active.name=="V8_11_HEADREST_SURFACE_GEODESIC_UV"
 back=bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"]
 assert len(back.data.vertices)==8614 and back.data.uv_layers.active.name=="V8_11_CROWN_GEODESIC_UV"
 for sign in ("+1","-1"):
  curve=bpy.data.objects["V8_3_"+side+"_BACK_OUTER_PIPING_"+sign]
  assert curve.data.materials[0].name=="V8_11_Source_Charcoal_Seat_Edge_PBR"
 for name in ("V5_"+side+"_LEATHER_SCULPTED_DOOR",):
  assert bpy.data.objects[name].data.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
sc.render.engine="CYCLES";sc.cycles.samples=10;sc.cycles.use_denoising=True
sc.render.resolution_x=960;sc.render.resolution_y=640
sc.render.resolution_percentage=100;sc.view_settings.exposure=-.52
for img in bpy.data.images:
 if img.source=="FILE" and not img.packed_file:img.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
manifest={"status":"DAYTONA_V8_12_REAL_BLENDER_SAVED",
 "input":SOURCE.name,"source_sha256":EXPECTED,
 "output":DEST.name,"new_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "remaining_exposed_original_shells":report,"source_packed_PBR":images,
 "controls_wheel_doors_v811_seat_shells_preserved":True,
 "camera":sc.camera.name,"render_validation":"UNTESTED",
 "full_matched_render":"UNTESTED","Quest3_tested":False,
 "OVC_created":False,"game_runtime":"UNTESTED",
 "original_game_files_modified":False}
(W/"DAYTONA_V8_12_BUILD_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("DAYTONA_V8_12_MODEL_SAVED",json.dumps(manifest),flush=True)
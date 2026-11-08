#!/usr/bin/env python3
"""Ferrari Daytona v8.24: six-nine physically punched source-aligned helper spoke holes.

Authoritative v8.23 Blender input ONLY. Real boolean geometry of three existing
V7.3/V8.23 forged-helper bridges, never cut the native 61-vertex wheel source,
4-vertex Ferrari badge, source rims, hub, or prior cabin features.
"""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
from mathutils import Vector
W=Path(os.environ.get("DAYTONA365_WORKDIR",
"/home/chatgpt-runner/work_handoff/daytona365_v824_ai2_1226"))/"blender_v8"
SRC=W/"Daytona365_Cockpit_Blender_PBR_v8_23.blend"
DST=W/"Daytona365_Cockpit_Blender_PBR_v8_24_r2.blend"
MANIFEST=W/"DAYTONA_V8_24_R2_BUILD_MANIFEST.json"
SRC_SHA="58c6404ec595392ab73358ec3b61aea3d971629f87d2d633b73918aaffa041bd"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SRC.resolve()
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SRC_SHA
assert not DST.exists() and not MANIFEST.exists()
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==111
def mesh_sha(ob):
 d=ob.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode()).hexdigest()
protected=(
"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0",
"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material002_a0",
"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
"V7_SHORT_SHAFT_AT_WHEEL_HUB","V8_5_STEERING_SHAFT",
"V8_21_SOURCE_LOWER_GAUGE_SHROUD","V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT",
"DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
"V8_LOW_CENTER_TUNNEL",
"V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
"V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST",
"V6_L_BLENDER_BLACK_FLOOR_MAT","V6_R_BLENDER_BLACK_FLOOR_MAT",
"V8_19_L_DASH_DOOR_FORMED_ENDCAP","V8_19_R_DASH_DOOR_FORMED_ENDCAP")
original={n:mesh_sha(bpy.data.objects[n]) for n in protected}
native=bpy.data.objects[protected[0]]
assert len(native.data.vertices)==61 and len(native.data.polygons)==31
source_aluminum=bpy.data.materials["V8_23_Source_Linked_Brushed_Spoke_Aluminum"]
assert source_aluminum.use_nodes
img=bpy.data.images["V8_23_Stamped_Spoke_Packed_Tangent_Normal"]
assert img.packed_file and tuple(img.size)==(256,256)
# Match the existing v8.23 source-linked metal PBR; introduce physically
# distinct slightly darker/rougher exposed circular bore-wall material.
bore_mat=source_aluminum.copy()
bore_mat.name="V8_24_Dark_Anodized_Punched_Spoke_Edge_PBR"
bsdf=bore_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Metallic"].default_value=.77
bsdf.inputs["Roughness"].default_value=.405
col=bsdf.inputs["Base Color"].default_value
col[0]*=.81;col[1]*=.81;col[2]*=.81
assert bore_mat.node_tree.nodes["V8_23_Packed_Stamped_Spoke_Tangent_Normal"].image==img

targets={
"LEFT":"V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
"RIGHT":"V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
"LOWER":"V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE"}
R=.00305
# Each hole is bored along the physical thin depth Y, NOT a black decal.
# Three 6.1mm perforations per arm, separated by 19.25mm in the long axis.
holes={}
results={}
for side,name in targets.items():
 ob=bpy.data.objects[name]
 assert ob.type=="MESH" and len(ob.data.vertices)==224 and len(ob.data.polygons)==210
 assert ob.data.materials[0]==source_aluminum and ob.data.users==1
 old_sha=mesh_sha(ob)
 xyz=[ob.matrix_world@v.co for v in ob.data.vertices]
 old_bounds=[[min(v[k] for v in xyz),max(v[k] for v in xyz)] for k in range(3)]
 if side in ("LEFT","RIGHT"):
  along=0
  fixed=.79
 else:
  along=2
  fixed=-.35
 lo,hi=old_bounds[along]
 centers=[]
 for t in (.25,.5,.75):
  a=lo+(hi-lo)*t
  if along==0:centers.append((a,fixed))
  else:centers.append((fixed,a))
 assert len(centers)==3
 bevels=[mod for mod in ob.modifiers if mod.type=="BEVEL"]
 prev=[m.show_viewport for m in bevels]
 for mod in bevels:mod.show_viewport=False
 for i,(cx,cz) in enumerate(centers):
  bpy.ops.mesh.primitive_cylinder_add(vertices=32,
   radius=R,depth=.075,location=(cx,-.290,cz),
   rotation=(math.pi/2,0.,0.))
  cutter=bpy.context.object
  cutter.name="V8_24_TEMP_BOOLEAN_DRILL_"+side+"_"+str(i)
  bpy.ops.object.select_all(action="DESELECT")
  ob.select_set(True);bpy.context.view_layer.objects.active=ob
  mod=ob.modifiers.new("V8_24_EXACT_PUNCH_"+side+"_"+str(i),"BOOLEAN")
  mod.operation="DIFFERENCE";mod.solver="EXACT";mod.object=cutter
  while ob.modifiers[0].name!=mod.name:
   bpy.ops.object.modifier_move_up(modifier=mod.name)
  bpy.ops.object.modifier_apply(modifier=mod.name)
  bpy.data.objects.remove(cutter,do_unlink=True)
 for mod,old_flag in zip(bevels,prev):
  mod.show_viewport=old_flag
  mod.width=.00050;mod.segments=2
 me=ob.data
 assert len(me.vertices)>224 and len(me.polygons)>210,(side,len(me.vertices),len(me.polygons))
 # Existing tangent normal UV and metallic finish must survive boolean.
 assert "V8_23_Metric_Stamped_Spoke_UV" in me.uv_layers
 assert "V8_23_Aligned_Spoke_Tangent_Normal_UV" in me.uv_layers
 # Reorient cut geometry and prove every edge is incident on exactly two faces.
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 assert all(len(e.link_faces)==2 for e in bm.edges),(side,"nonmanifold")
 signed_volume=bm.calc_volume(signed=True)
 assert abs(signed_volume)>1e-8,(side,signed_volume)
 bm.to_mesh(me);bm.free();me.update()
 # Distinct real material index only on bore side walls; original front/back
 # metal retains source-linked v8.23 packed 256px tangent map.
 me.materials.append(bore_mat)
 marked=0
 for p in me.polygons:
  ctr=ob.matrix_world@p.center
  world_n=(ob.matrix_world.to_3x3()@p.normal).normalized()
  d=min(math.hypot(ctr.x-cx,ctr.z-cz) for cx,cz in centers)
  if abs(d-R)<.00075 and abs(world_n.y)<.76:
   p.material_index=1;marked+=1
 assert marked>=30,(side,"missing physical bore wall",marked)
 for layer in me.uv_layers:
  assert all(math.isfinite(float(v)) for l in layer.data for v in l.uv),side
 # A real ray passes through the hole; surrounding wheel metal still blocks.
 inverse=ob.matrix_world.inverted()
 direction=(inverse.to_3x3()@Vector((0,-1,0))).normalized()
 for cx,cz in centers:
  ray=(inverse@Vector((cx,-.22,cz)))
  hit,_,_,_=ob.ray_cast(ray,direction,distance=.15)
  assert not hit,(side,"hole has material inside",cx,cz)
  adj=(inverse@Vector((cx+(0 if along==0 else .006),-.22,
                       cz+(.006 if along==0 else 0))))
  metal_hit,_,_,_=ob.ray_cast(adj,direction,distance=.15)
  assert metal_hit,(side,"missing surrounding metal",cx,cz)
 after=[ob.matrix_world@v.co for v in me.vertices]
 for k,(mn,mx) in enumerate(old_bounds):
  assert min(v[k] for v in after)>=mn-.000025,(side,k)
  assert max(v[k] for v in after)<=mx+.000025,(side,k)
 assert mesh_sha(ob)!=old_sha
 ob["DAYTONA_V8_24"]="three true 6.1 mm through-punched circular bores; source original wheel untouched"
 holes[side]=[{"x":cx,"z":cz,"radius_m":R} for cx,cz in centers]
 results[side]={"name":name,"old_vertices":224,"old_faces":210,
 "vertices":len(me.vertices),"faces":len(me.polygons),
 "three_true_y_axis_through_holes":True,
 "bore_wall_dark_pbr_faces":marked,
 "closed_manifold":True,"absolute_signed_volume_m3":abs(signed_volume),
 "original_source_envelope_kept":True}

for name,h in original.items():
 assert mesh_sha(bpy.data.objects[name])==h,name
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==111
assert not any(o.name.startswith("V8_24_TEMP_BOOLEAN_DRILL") for o in bpy.data.objects)
for im in bpy.data.images:
 if im.source=="FILE" and not im.packed_file:im.pack()
sc=bpy.context.scene
sc.render.engine="CYCLES";sc.cycles.samples=10
sc.cycles.use_denoising=True
sc.render.resolution_x=960;sc.render.resolution_y=640
sc.render.resolution_percentage=100;sc.view_settings.exposure=-.52
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DST),compress=True)
manifest={"status":"DAYTONA_V8_24_REAL_BLENDER_SAVED",
"input":SRC.name,"input_sha256":SRC_SHA,
"output":DST.name,"output_sha256":hashlib.sha256(DST.read_bytes()).hexdigest(),
"bytes":DST.stat().st_size,"blender":bpy.app.version_string,
"hole_total":9,"holes":holes,"spoke_results":results,
"new_bore_wall_material":bore_mat.name,
"original_source_metal_tangent_normal_packed_preserved":True,
"native_61_vertex_spoke_and_ferrari_emblem_unchanged":True,
"v823_rebuild_v822_boot_v821_hub_and_existing_cabin_preserved":True,
"mesh_count":113,"curve_count":111,
"source_original_PMT_triangle_copy":False,
"render_validation":"UNTESTED","sample_matched_original_PMT":"UNTESTED",
"original_game_modified":False,"OVC_created":False,"Quest3_tested":False}
MANIFEST.write_text(json.dumps(manifest,indent=2))
print("DAYTONA_V8_24_MODEL_SAVED",json.dumps(manifest),flush=True)
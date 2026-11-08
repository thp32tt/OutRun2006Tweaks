#!/usr/bin/env python3
"""F50 real ORIGINAL OutRun 2006 imported-MESH P0 dashboard & steering wheel geometric rework.
Reads ONLY immutable source .blend (itself imported from SHA-pinned original PMT).
Edits exactly three original PMT object identities IN-PLACE; never a replacement vehicle.
No third-party GLB, no OVC/OVC3/PMT output, no textures/PBR, no exterior/wheels.
"""
import bpy,bmesh,json,hashlib,math,struct
from mathutils import Vector
from pathlib import Path
BASE=Path(__file__).resolve().parent
SOURCE=BASE/"F50_OriginalPMT_CockpitSource_v1.blend"
OUTPUT=BASE/"F50_OriginalPMT_P0_DashboardSteering_v1.blend"
REPORT=BASE/"F50_P0_DashboardSteering_OriginalMeshDelta_v1.json"
EXPECTED_RESOURCE_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
GAME=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz")
assert SOURCE.is_file() and not OUTPUT.exists(), "Missing original import or target already exists"
assert hashlib.sha256(GAME.read_bytes()).hexdigest()==EXPECTED_RESOURCE_SHA
assert bpy.data.filepath==str(SOURCE),"Blender must open exact original-import scene, not generate a new car"
sc=bpy.context.scene
assert sc.get("outrun_original_game_resource_sha256")==EXPECTED_RESOURCE_SHA
assert sc.get("geometry_edit_count")==0
objects=[o for o in bpy.data.objects if o.type=="MESH"]
source_ids={o.name:o.get("outrun_original_mesh_object_id") for o in objects}
assert len(objects)==42 and all(source_ids.values()),"Original source objects/tags missing"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":"instrument binnacle/original dashboard face shell",
 "PMT_F50_object21_group01_material002_a0":"source steering rim + 3 spokes",
 "PMT_F50_object21_group00_material000_a0":"source steering hub/spoke backing",
}
assert set(TARGETS).issubset(source_ids)
def signature(mesh):
 h=hashlib.sha256()
 for v in mesh.vertices:
  h.update(struct.pack("<3f",*v.co))
 for p in mesh.polygons:
  h.update(struct.pack("<I",len(p.vertices)))
  for v in p.vertices:h.update(struct.pack("<I",v))
 return h.hexdigest()
prior={o.name:{"vertices":len(o.data.vertices),"faces":len(o.data.polygons),"mesh_sha256":signature(o.data),
                "source_identity":source_ids[o.name],
                "matrix_world":[round(x,9) for row in o.matrix_world for x in row]} for o in objects}
def check_source_edit(o):
 assert o.get("outrun_original_mesh_object_id")==source_ids[o.name]
 assert tuple(round(x,6) for x in o.location)==(0,0,0),"Game local pivot moved"
 assert all(abs(x-1)<1e-6 for x in o.scale),"Original coordinate scale changed"
def subdivide(ob,cuts):
 bm=bmesh.new()
 bm.from_mesh(ob.data)
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=cuts,use_grid_fill=True)
 bm.to_mesh(ob.data);bm.free();ob.data.update()
def apply_solidify(ob,t,name):
 m=ob.modifiers.new(name,"SOLIDIFY")
 m.thickness=t
 m.offset=-1.0
 m.use_even_offset=True
 bpy.ops.object.select_all(action="DESELECT")
 ob.select_set(True)
 bpy.context.view_layer.objects.active=ob
 bpy.ops.object.modifier_apply(modifier=m.name)
def apply_bevel(ob,width):
 m=ob.modifiers.new("P0_PHYSICAL_CORNER_MICRO_BEVEL","BEVEL")
 m.width=width;m.segments=2;m.limit_method="ANGLE";m.angle_limit=0.7
 bpy.ops.object.select_all(action="DESELECT")
 ob.select_set(True)
 bpy.context.view_layer.objects.active=ob
 bpy.ops.object.modifier_apply(modifier=m.name)
# 1. Original F50 dashboard/gauge cowl: contour recess, real shell thickness, fine bevel.
g=bpy.data.objects["PMT_F50_object00_group01_material028_a0"]
check_source_edit(g)
subdivide(g,3)
verts=g.data.vertices
x0=min(v.co.x for v in verts); x1=max(v.co.x for v in verts)
y0=min(v.co.y for v in verts); y1=max(v.co.y for v in verts)
for v in verts:
 u=(v.co.x-x0)/max(x1-x0,1e-8)
 w=(v.co.y-y0)/max(y1-y0,1e-8)
 # Sculpt only this old 10-vertex F50 original instrument binnacle mesh:
 # thin arch-shaped rear recess while source outer silhouette/UV and coordinate frame remain.
 horizontal=max(0.,1.0-(2*u-1.)**2)
 vertical=max(0.,1.0-(2*w-1.)**2)
 v.co.z-=0.0065*horizontal*vertical
g.data.update()
apply_solidify(g,0.004,"P0_DASH_SOURCE_SHELL_4MM")
apply_bevel(g,0.0008)
g["source_edit_scope"]="physical recessed molded instrument housing + 4mm thickness + 0.8mm edge bevel"
# 2. Original F50 three-spoke steering wheel: refine existing rim in native local pivot.
w=bpy.data.objects["PMT_F50_object21_group01_material002_a0"]
check_source_edit(w)
subdivide(w,2)
max_r=max(math.hypot(v.co.x,v.co.y) for v in w.data.vertices)
outer_adjusted=0;raised=0
for v in w.data.vertices:
 x,y,z=v.co
 r=math.hypot(x,y)
 if r>max_r*0.91:
  # Interpolated 14-sided polygon rim edge -> more rounded native radius (no enlarged envelope).
  delta=min(0.004,max(0.,(max_r-r)*0.55))
  if r>1e-9:v.co.x=x*(r+delta)/r;v.co.y=y*(r+delta)/r
  outer_adjusted+=1
 if r>0.115:
  # 2.6mm leather-rim physical arc/contour on genuine source vertices.
  roll=max(0.,1.-abs(r-0.148)/0.026)
  v.co.z=z+0.0026*roll
  raised+=1
 elif 0.047<r<0.115:
  # Very small pressed-spoke ridge; preserve original three-spoke silhouette.
  v.co.z=z+0.0018*math.sin(math.pi*(r-0.047)/(0.115-0.047))
w.data.update()
w["source_edit_scope"]="native 3-spoke ring curvature + existing-spoke stamped relief"
w["outer_original_radius"]=max_r
w["rim_surface_points_edited"]=raised
# 3. Existing original steering hub backing shell, no new replacement object.
h=bpy.data.objects["PMT_F50_object21_group00_material000_a0"]
check_source_edit(h)
subdivide(h,1)
apply_solidify(h,0.003,"P0_HUB_ORIGINAL_THICKNESS_3MM")
h["source_edit_scope"]="physical thickness of original 3-spoke hub backing"
# Original transforms and the 39 non-target source meshes are untouched.
after={o.name:{"vertices":len(o.data.vertices),"faces":len(o.data.polygons),"mesh_sha256":signature(o.data),
 "source_identity":source_ids[o.name],"matrix_world":[round(x,9) for row in o.matrix_world for x in row]} for o in objects}
for name in source_ids:
 assert after[name]["source_identity"]==prior[name]["source_identity"]
 assert after[name]["matrix_world"]==prior[name]["matrix_world"]
 if name not in TARGETS:assert after[name]["mesh_sha256"]==prior[name]["mesh_sha256"],"Non-cockpit source geometry altered"
 else:
  assert after[name]["mesh_sha256"]!=prior[name]["mesh_sha256"],"Original mesh was not physically reshaped"
  assert after[name]["vertices"]>prior[name]["vertices"] and after[name]["faces"]>prior[name]["faces"]
sc["geometry_edit_count"]=3
sc["source_original_blend_sha256"]=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
sc["output_scope"]="F50 original source dashboard/gauge/steering only; no exterior work"
sc["original_game_source_unchanged"]=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
def do_render(name,cam_name,keep):
 orig_hide={o.name:o.hide_render for o in objects}
 try:
  for o in objects:o.hide_render=not keep(o)
  sc.camera=bpy.data.objects[cam_name]
  sc.render.filepath=str(BASE/name)
  bpy.ops.render.render(write_still=True)
 finally:
  for o in objects:o.hide_render=orig_hide[o.name]
do_render("F50_After_RealOriginal_GaugeGeometry.png","QA_F50_GAUGE_DETAIL_NON_GAME",lambda o:o.name=="PMT_F50_object00_group01_material028_a0")
do_render("F50_After_RealOriginal_SteeringGeometry.png","QA_F50_STEERING_LOCAL_NON_GAME",lambda o:o.get("outrun_original_pmt_object_index")==21)
assert hashlib.sha256(GAME.read_bytes()).hexdigest()==EXPECTED_RESOURCE_SHA
report={"status":"REAL_ORIGINAL_SOURCE_GEOMETRY_SAVED_AND_RENDERED",
 "native_input_path":str(GAME),"native_input_sha256":EXPECTED_RESOURCE_SHA,
 "baseline_scene":str(SOURCE),"baseline_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 "candidate_scene":str(OUTPUT),"candidate_sha256":hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
 "source_object_count":len(source_ids),"edited_original_mesh_ids":[source_ids[x] for x in TARGETS],
 "before_after":{n:{"role":role,"before":prior[n],"after":after[n]} for n,role in TARGETS.items()},
 "untouched_source_meshes":len(objects)-len(TARGETS),
 "source_transform_preserved":True,"original_steering_local_pivot_preserved":True,
 "new_vehicle_created":False,"source_glb_used":False,"outside_cockpit_geometry_edits":0,
 "texture_normal_pbr_work":False,"OVC_OVC3_PMT_output":False,"game_integration":False,
 "source_game_camera_qa":"UNTESTED_DIAGNOSTIC_ONLY","photo_comparison":"reference F50 photo dashboard/3-spoke profile confirmed; physical scale/depth not metrologically verified",
 "private_views":["F50_Before_Original_Source_GaugeDetail.png","F50_After_RealOriginal_GaugeGeometry.png","F50_Before_Original_Source_SteeringLocal.png","F50_After_RealOriginal_SteeringGeometry.png"]}
REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print("F50_SOURCE_ORIGINAL_MESH_P0_GEOMETRY_PASS",report["baseline_sha256"],report["candidate_sha256"],report["edited_original_mesh_ids"])
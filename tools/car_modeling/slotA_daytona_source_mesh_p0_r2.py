#!/usr/bin/env python3
"""Slot A Daytona P0: sculpt original-derived dash and original 61v wheel spokes.
No new car, GLB, native/OVC/PMT export, materials, textures, or exterior edits.
"""
import bpy, bmesh, hashlib, json, math, os
from pathlib import Path
from mathutils import Vector

W=Path(os.environ["SLOT_A_WORK"])
SRC=W/"Daytona365_Cockpit_Blender_PBR_v8_22_r2.blend"
OUT=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v1_r2.blend"
REP=W/"SLOT_A_P0_DASH_WHEEL_V1_R2.json"
ORIGINAL=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIGBLEND=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
S_SHA="30ddcbd01ef7e969bb1e4220ff4318c2f75b7fd7ab70bc4d6dafedcdc7954437"
PMT_SHA="f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe"
IMP_SHA="92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SRC.resolve()
assert not OUT.exists() and not REP.exists()
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==S_SHA
assert ORIGINAL.is_file() and hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()==PMT_SHA
assert ORIGBLEND.is_file() and hashlib.sha256(ORIGBLEND.read_bytes()).hexdigest()==IMP_SHA
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"

dash=bpy.data.objects["V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE"]
wheel=bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"]
assert dash.type==wheel.type=="MESH"
assert len(dash.data.vertices)==1885 and len(dash.data.polygons)==3584
assert len(wheel.data.vertices)==61 and len(wheel.data.polygons)==31
assert dash.data.users==wheel.data.users==1
assert wheel.data.materials[0].name=="V7_Machined_Aluminum"
native_ref=bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"]
assert len(native_ref.data.vertices)==13
gauges=bpy.data.objects["DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH"]
assert len(gauges.data.vertices)==20
orig_scene_camera=bpy.context.scene.camera
src_camera_matrix=[[round(float(v),9) for v in row] for row in orig_scene_camera.matrix_world]
original_names=set(o.name for o in bpy.data.objects)
images_before={img.name:(tuple(img.size),bool(img.packed_file)) for img in bpy.data.images}
materials_before=set(m.name for m in bpy.data.materials)
curves_before=set(c.name for c in bpy.data.curves)
def mesh_signature(o):
 d=o.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode("utf8")).hexdigest()
all_protected={o.name:mesh_signature(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in (dash.name,wheel.name)}
before={o.name:{"signature":mesh_signature(o),"vertices":len(o.data.vertices),"faces":len(o.data.polygons),
 "world_matrix":[[round(float(v),9) for v in row] for row in o.matrix_world]} for o in (dash,wheel)}

# Direct edit of existing source-referenced dashboard grid, not a new shell.
# The photograph shows a dished instrument field surrounded by a smoothly
# rolled padded dashboard, avoiding a uniformly planar tablet.
# Only driver instrument envelope is sculpted, with vanishing boundary weights.
def fade(a,b,v):
 t=max(0.,min(1.,(v-a)/(b-a)))
 return t*t*(3-2*t)
world=dash.matrix_world
inv=world.inverted()
dashboard_n=0; maximum_dash_mm=0.
for vert in dash.data.vertices:
 p=world@vert.co
 xf=fade(-.67,-.61,p.x)*(1.-fade(-.14,-.055,p.x))
 zf=fade(.675,.740,p.z)*(1.-fade(.902,.961,p.z))
 if xf<=0 or zf<=0:continue
 w=xf*zf
 # Shallow physical instrument surround: center dished deeper into body
 # 4.4mm, with 1.3mm rolled upper region; source gauge atlas stays untouched.
 recess=.0044*w*(.56+.44*math.cos(min(math.pi,abs(p.x+.349)/.28*math.pi)))
 roll=.0013*w*math.exp(-((p.z-.886)/.036)**2)
 d=Vector((0.,recess,roll))
 if d.length<.00010:continue
 vert.co=inv@(p+d)
 dashboard_n+=1
 maximum_dash_mm=max(maximum_dash_mm,d.length*1000.)
dash.data.update()
assert dashboard_n>=160,(dashboard_n,"no source dashboard geometry edited")
assert 3.0<maximum_dash_mm<6.0
assert len(dash.data.vertices)==1885 and len(dash.data.polygons)==3584
assert len(dash.data.uv_layers)>=1

# Rebuild topology of the SAME original-game object22 stamped steering spoke.
# Subdivide original source facets, then form slight raised presswork in the
# three metal arms without moving pivot or replacing the Ferrari badge/rim.
bm=bmesh.new()
bm.from_mesh(wheel.data)
prior_edges=len(bm.edges)
bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True)
bm.verts.ensure_lookup_table()
winv=wheel.matrix_world.inverted()
wheel_n=0;maximum_wheel_mm=0.
for vert in bm.verts:
 p=wheel.matrix_world@vert.co
 radx=abs(p.x+.35)
 horizontal=fade(.026,.058,radx)*(1.-fade(.104,.133,radx))
 horizontal*=fade(.762,.777,p.z)*(1.-fade(.818,.840,p.z))
 lower=fade(.006,.018,.792-p.z)*(1.-fade(.100,.123,.792-p.z))
 lower*=1.-fade(.018,.033,abs(p.x+.35))
 # Original wheel faces already have different depth; add a shallow
 # physical crown of 2-3 mm along the already curved metal spoke.
 badge_clearance=fade(.059,.084,math.hypot(p.x+.35,p.z-.792))
 dy=-(.00265*horizontal+.00230*lower)*badge_clearance
 if abs(dy)<.00008:continue
 new=Vector((p.x,p.y+dy,p.z))
 vert.co=winv@new
 wheel_n+=1
 maximum_wheel_mm=max(maximum_wheel_mm,abs(dy)*1000.)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
post_verts=len(bm.verts);post_faces=len(bm.faces)
bm.to_mesh(wheel.data);bm.free()
wheel.data.update()
assert post_verts>61 and post_faces>31,(post_verts,post_faces)
assert wheel_n>=20,(wheel_n,"source wheel geometry not touched")
assert 1.0<maximum_wheel_mm<3.1
assert len(wheel.data.uv_layers)>=1
assert wheel.data.materials[0].name=="V7_Machined_Aluminum"

for n,sig in all_protected.items():
 assert mesh_signature(bpy.data.objects[n])==sig,"unrelated original/exterior object modified: "+n
assert set(bpy.data.objects.keys())==original_names,"new car object or unexpected deletion"
assert set(bpy.data.materials.keys())==materials_before,"materials changed"
assert set(bpy.data.curves.keys())==curves_before,"curves changed"
assert images_before=={img.name:(tuple(img.size),bool(img.packed_file)) for img in bpy.data.images},"textures/images changed"
assert [[round(float(v),9) for v in row] for row in orig_scene_camera.matrix_world]==src_camera_matrix
assert [[round(float(v),9) for v in row] for row in wheel.matrix_world]==before[wheel.name]["world_matrix"]
assert [[round(float(v),9) for v in row] for row in dash.matrix_world]==before[dash.name]["world_matrix"]
assert mesh_signature(dash)!=before[dash.name]["signature"]
assert mesh_signature(wheel)!=before[wheel.name]["signature"]
wheel["SLOTA_SOURCE_PMT"]=ORIGINAL.name
wheel["SLOTA_SOURCE_SHA256"]=PMT_SHA
dash["SLOTA_SOURCE_PMT"]=ORIGINAL.name
dash["SLOTA_SOURCE_SHA256"]=PMT_SHA

bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
report={"status":"SLOTA_DAYTONA_P0_REAL_BLENDER_SAVED",
 "original_game_resource":ORIGINAL.name,"original_game_resource_sha256":PMT_SHA,
 "original_import_blend":ORIGBLEND.name,"original_import_blend_sha256":IMP_SHA,
 "input_blend":SRC.name,"input_blend_sha256":S_SHA,
 "output_blend":OUT.name,"output_blend_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
 "output_bytes":OUT.stat().st_size,"blender":bpy.app.version_string,
 "modified_original_derived_objects":{
 dash.name:{"before":before[dash.name],"after_signature":mesh_signature(dash),
 "after_vertices":1885,"after_faces":3584,"moved_existing_vertices":dashboard_n,
 "maximum_displacement_mm":round(maximum_dash_mm,4)},
 wheel.name:{"before":before[wheel.name],"after_signature":mesh_signature(wheel),
 "after_vertices":post_verts,"after_faces":post_faces,
 "modified_subdivided_source_vertices":wheel_n,"maximum_displacement_mm":round(maximum_wheel_mm,4),
 "prior_edges":prior_edges}},
 "factory_61_vertex_source_object_edited_in_place":True,
 "native_original_gauge_uv_and_all_other_mesh_sha_preserved":True,
 "materials_texture_uv_pbr_generation":"NONE","exterior_mesh_changes":0,
 "original_game_asset_modified":False,
 "badge_clearance_zone_m":[.059,.084],"new_car_created":False,
 "GLB_exported":False,"OVC3_OVC_PMT_converted":False,"game_runtime_changed":False,
 "slot":"A","car":"daytona365","QA_status":"P0_PARTIAL_UNTESTED_FULL_24H",
 "next_car_change_allowed":False}
REP.write_text(json.dumps(report,indent=2))
print("SLOTA_DAYTONA_P0_REAL_BLENDER_SAVED",json.dumps({k:report[k] for k in ("output_blend","output_blend_sha256","output_bytes","blender")}),"dash_moved",dashboard_n,"wheel_vertices_faces",post_verts,post_faces,flush=True)
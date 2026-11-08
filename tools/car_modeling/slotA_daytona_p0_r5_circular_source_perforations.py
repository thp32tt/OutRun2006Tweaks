#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona Slot A r5, PMT-derived Blender cockpit geometry only.

Edit the original imported three-spoke metal wheel mesh IN PLACE and the existing
PMT-derived padded dash/cowl. Eight physically open perforations are cut in the
original source-spoke faces; no replacement GLB, primitives, car body, exports,
texture, normal or PBR changes. Original files are SHA-gated and read-only.
"""
import bpy, bmesh, hashlib, json, math, os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

W = Path(os.environ["SLOT_A_WORK"])
SOURCE = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v2_r3.blend"
OUTPUT = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v3_r5.blend"
REPORT = W / "SLOT_A_DAYTONA_P0_R5_SOURCE_HOLES_COWL.json"
PMT = Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT = Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO = Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
SHA = {
 "source": "1f6971bcf8eb1866e0c32a730c87b47967d1044f62317e13f3dd7a58f256abc9",
 "pmt": "f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "import": "92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "photo": "6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
assert bpy.app.version_string.startswith("4.5.15"), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == SOURCE.resolve()
assert not OUTPUT.exists() and not REPORT.exists(), "immutable private output checkpoint"
def digest(p):
 return hashlib.sha256(p.read_bytes()).hexdigest()
for key,p in (("source",SOURCE),("pmt",PMT),("import",IMPORT),("photo",PHOTO)):
 assert p.is_file() and digest(p)==SHA[key], (key,str(p))
assert bpy.context.scene.camera.name == "V7_Camera_Reference_ThreeQuarter"
NAMES={
 "spoke": "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "cowl": "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "dashboard": "V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE"}
OB={k:bpy.data.objects[name] for k,name in NAMES.items()}
for k,o in OB.items():
 assert o.type=="MESH" and o.data.users==1 and o.data.uv_layers
 assert len(o.data.materials)>0
COUNTS={"spoke":(246,279),"cowl":(650,648),"dashboard":(1885,3584)}
assert all((len(o.data.vertices),len(o.data.polygons))==COUNTS[k] for k,o in OB.items())
def signature(o):
 d=o.data
 return hashlib.sha256(repr((
  [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
  [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode("utf8")).hexdigest()
def matrix(o):
 return [[round(float(c),9) for c in row] for row in o.matrix_world]
BEFORE={k:{"object_name":o.name,"vertices":len(o.data.vertices),
 "faces":len(o.data.polygons),"signature":signature(o),"matrix_world":matrix(o)}
 for k,o in OB.items()}
assert BEFORE["spoke"]["signature"]=="ec6690a94d66563c8e3616c85abd5ee5db2584612c108c9916989b2a5106f1a8"
assert BEFORE["cowl"]["signature"]=="8c613ee3317910c311e75d1c1e33b137c0004765efaf3ce9c78123f429e593a9"
assert BEFORE["dashboard"]["signature"]=="9cf59e582a64615fed996616cf0d9c9c23d5bb4a35efbeb8869a20d9e90a96c3"
untouched={o.name:signature(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
all_object_names=set(bpy.data.objects.keys())
all_materials=set(bpy.data.materials.keys())
all_images={i.name:(tuple(i.size),bool(i.packed_file)) for i in bpy.data.images}
all_curves=set(bpy.data.curves.keys())
camera_matrix=matrix(bpy.context.scene.camera)

# Photo comparison: 1971 Daytona Spider original LHD 3 drilled holes in
# each horizontal spoke and a stamped lower arm. Eight validated openings
# fit physically inside the GAME'S existing, 61v factory-origin metal spokes.
# Different trim of coupe photos is not treated as an exact Spider source.
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
       (-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
       (-.350,.745,.0052),(-.350,.716,.0047)]
wheel=OB["spoke"]
original_ray=BVHTree.FromObject(wheel,bpy.context.evaluated_depsgraph_get())
def ray(tree,x,z):
 return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.0)[2] is not None
for x,z,r in HOLES:
 assert ray(original_ray,x,z) and ray(original_ray,x+1.5*r,z),("missing original metal",x,z)
bm=bmesh.new()
bm.from_mesh(wheel.data)
prior_nm=sum(not e.is_manifold for e in bm.edges)
prior_uv=len(wheel.data.uv_layers)
bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=5,use_grid_fill=True)
base_subdivision=(len(bm.verts),len(bm.faces))
# Locally refine only the existing original-game spoke faces around perforations.
# Retain outer original silhouette and all UV/material attributes.
selected_edges=[]
for e in bm.edges:
 q=(wheel.matrix_world@e.verts[0].co+wheel.matrix_world@e.verts[1].co)*.5
 dist=min(math.hypot(q.x-x,q.z-z)/r for x,z,r in HOLES)
 if dist<2.1:selected_edges.append(e)
assert len(selected_edges)>1000
bmesh.ops.subdivide_edges(bm,edges=selected_edges,cuts=2,use_grid_fill=True)
refined_mesh=(len(bm.verts),len(bm.faces))
candidates=[];per_hole=[0]*len(HOLES)
for face in list(bm.faces):
 p=wheel.matrix_world@face.calc_center_median()
 for i,(x,z,r) in enumerate(HOLES):
  if math.hypot(p.x-x,p.z-z)<.90*r:
   per_hole[i]+=1
   candidates.append(face)
   break
assert len(candidates)>=1000 and all(n>=100 for n in per_hole),per_hole
bmesh.ops.delete(bm,geom=candidates,context="FACES")
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
out_verts,out_faces=len(bm.verts),len(bm.faces)
post_nm=sum(not e.is_manifold for e in bm.edges)
bm.to_mesh(wheel.data);bm.free();wheel.data.update()
assert base_subdivision==(5586,10044),base_subdivision
assert refined_mesh==(10314,18836),refined_mesh
assert (out_verts,out_faces)==(9720,17285),(out_verts,out_faces)
assert len(wheel.data.uv_layers)==prior_uv
assert [m.name for m in wheel.data.materials]==["V7_Machined_Aluminum"]
bvh=BVHTree.FromObject(wheel,bpy.context.evaluated_depsgraph_get())
for x,z,r in HOLES:
 assert not ray(bvh,x,z),("NOT_A_THROUGH_HOLE",x,z)
 assert ray(bvh,x+1.5*r,z),("RIM_METAL_REMOVED",x,z)
wheel["SLOTA_SOURCE_PMT"]=PMT.name
wheel["SLOTA_SOURCE_SHA256"]=SHA["pmt"]

# Refine the actual existing source-derived dash and original-guided visor
# without moving gauge atlas, instrument origin, or creating an overlay mesh.
def fade(a,b,v):
 t=max(0.,min(1.,(v-a)/(b-a)))
 return t*t*(3.-2.*t)
contours={}
for key in ("cowl","dashboard"):
 o=OB[key];inv=o.matrix_world.inverted();moved=0;max_mm=0.
 for v in o.data.vertices:
  p=o.matrix_world@v.co
  if key=="cowl":
   wx=fade(-.634,-.589,p.x)*(1.-fade(-.114,-.055,p.x))
   front=math.exp(-((p.y-.156)/.026)**2)
   upper=math.exp(-((p.z-.930)/.018)**2)
   dy=-.0035*wx*front*upper
   dz=.0013*wx*front*math.exp(-((p.z-.937)/.014)**2)
  else:
   wx=fade(-.632,-.573,p.x)*(1.-fade(-.146,-.080,p.x))
   wz=fade(.749,.794,p.z)*(1.-fade(.881,.934,p.z))
   # Supplemental shallow dashboard crown for physical under-gauge transition.
   dy=.0018*wx*wz*math.exp(-((p.x+.35)/.24)**4)
   dz=-.00065*wx*wz*math.exp(-((p.z-.815)/.035)**2)
  displacement=Vector((0.,dy,dz))
  if displacement.length<.00003:continue
  v.co=inv@(p+displacement)
  moved+=1;max_mm=max(max_mm,displacement.length*1000.)
 o.data.update()
 assert moved>({"cowl":60,"dashboard":120}[key]),(key,moved)
 assert max_mm<4.0,(key,max_mm)
 o["SLOTA_SOURCE_PMT"]=PMT.name
 o["SLOTA_SOURCE_SHA256"]=SHA["pmt"]
 contours[key]={"moved_vertices":moved,"maximum_displacement_mm":round(max_mm,4)}
for name,sig in untouched.items():
 assert signature(bpy.data.objects[name])==sig,("unrelated mesh edited",name)
assert set(bpy.data.objects.keys())==all_object_names
assert set(bpy.data.materials.keys())==all_materials
assert set(bpy.data.curves.keys())==all_curves
assert {i.name:(tuple(i.size),bool(i.packed_file)) for i in bpy.data.images}==all_images
assert matrix(bpy.context.scene.camera)==camera_matrix
for k,o in OB.items():
 assert matrix(o)==BEFORE[k]["matrix_world"]
 assert signature(o)!=BEFORE[k]["signature"]

bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
after={k:{"before":BEFORE[k],"after_signature":signature(o),
 "after_vertices":len(o.data.vertices),"after_faces":len(o.data.polygons),
 "source_sha256":o["SLOTA_SOURCE_SHA256"]} for k,o in OB.items()}
report={
 "status":"SLOTA_DAYTONA_P0_R5_CIRCULAR_SOURCE_HOLES_SAVED","slot":"A","car":"daytona365",
 "blender_version":bpy.app.version_string,
 "input_blend":SOURCE.name,"input_sha256":SHA["source"],
 "output_blend":OUTPUT.name,"output_sha256":digest(OUTPUT),"output_bytes":OUTPUT.stat().st_size,
 "original_resource":PMT.name,"original_resource_sha256":SHA["pmt"],
 "original_import_blend":IMPORT.name,"original_import_sha256":SHA["import"],
 "private_exact_spider_LHD_photo":str(PHOTO),"photo_sha256":SHA["photo"],
 "changed_existing_original_derived_objects":after,
 "physical_spoke_through_holes":len(HOLES),
 "hole_centers_xyz_xz_and_radii_m":HOLES,
 "deleted_source_spoke_faces":len(candidates),"faces_removed_per_hole":per_hole,
 "r4_prototype":"SUPSERSEDED_JAGGED_APPEARANCE_NOT_FINAL",
 "adaptive_subdivision_base":base_subdivision,"adaptive_subdivision_selected_edges":len(selected_edges),
 "adaptive_subdivision_refined":refined_mesh,
 "source_spoke_prior_non_manifold_edges":prior_nm,
 "source_spoke_post_non_manifold_edges":post_nm,
 "other_geometry_sculpt":contours,"original_mesh_anchors_unchanged":True,
 "unchanged_other_meshes":len(untouched),"new_scene_objects":0,
 "no_exterior_geometry":True,"no_material_texture_normal_PBR":True,
 "ovc3_ovc_pmt_or_game_export":"NONE","VR_or_Model2_changes":False,
 "camera":"APPROX_LEFT_EYE_NOT_GAME","photo_7view_complete":False,
 "24h_gate":"NOT_COMPLETED","overall_quality":"PARTIAL_NEEDS_QA",
 "source_file_changed":False,"slot_advance":False}
REPORT.write_text(json.dumps(report,indent=2))
print(report["status"],json.dumps({"sha256":report["output_sha256"],
 "punches":len(HOLES),"faces_deleted":len(candidates),"cowl":contours["cowl"],
 "dashboard":contours["dashboard"]}),flush=True)
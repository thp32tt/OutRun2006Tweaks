#!/usr/bin/env python3
"""OutRun 2006 ORIGINAL Ferrari 365 GTS/4 Daytona slot A r13, actual existing cockpit geometry.
STRICT provenance chain: immutable original native PMT -> verified native imported Blender
-> existing source-derived editable R12 scene -> R13 private .blend. Never import/export GLB,
create substitute car, edit exterior, game PMT/OVC/OVC3, textures, PBR or runtime source.
The original source-derived cowl and steering rim gain genuine new interpolated edge loops
via Blender BMesh subdivision; source-based dashboard, three-spoke pressing, gauge bezels
and hub receive direct physical vertex refinements from verified 1971 Spider LHD references.
"""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(os.environ["SLOT_A_WORK"])
SRC=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v10_r12.blend"
DEST=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v11_r13.blend"
PREV=W/"SLOT_A_DAYTONA_P0_R12_NATIVE_SPOKE_EDGE_AND_DASH_GEOMETRY.json"
AUDIT=W/"SLOT_A_DAYTONA_P0_R13_ORIGINAL_VISOR_RIM_EDGELOOPS.json"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
PHOTO_DETAIL=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/REF2_dashboard_original_e91527ff82f3.jpg")
PHOTO_SPYDER=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/REF5_mecum_interior_01_c37db04b5.jpg")
SHA={
"src":"2995c8b21e519d7e7da4de71bf3bd35186ef8f7159506d619c312083cf5fd518",
"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
PARTS={
"dashboard":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
"brow":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
"spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
"rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
"hub":"V7_SHORT_SHAFT_AT_WHEEL_HUB"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]
def hashfile(p):
 h=hashlib.sha256()
 with p.open("rb") as fh:
  for chunk in iter(lambda:fh.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def sig(o):
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],
 [(f.material_index,tuple(f.vertices)) for f in o.data.polygons])).encode()).hexdigest()
def matrix(o):
 return [[round(float(x),9) for x in row] for row in o.matrix_world]
def smooth(a,b,x):
 u=max(0.,min(1.,(x-a)/(b-a)))
 return u*u*(3.-2.*u)
def hole_check(o):
 bpy.context.view_layer.update()
 tree=BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get())
 def hit(x,z):return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]

assert bpy.app.version_string.startswith("4.5.15"),"official Blender 4.5.15 required"
assert Path(bpy.data.filepath).resolve()==SRC.resolve(),"BLOCKED_INPUT: not editable genuine R12"
assert not DEST.exists() and not AUDIT.exists(),"R13 immutable output already exists"
for key,p in (("src",SRC),("pmt",PMT),("import",IMPORT),("photo",PHOTO)):
 assert p.is_file() and hashfile(p)==SHA[key],("BLOCKED_INPUT_SOURCE_SHA",key)
assert PHOTO_DETAIL.is_file() and PHOTO_SPYDER.is_file(),"BLOCKED_INPUT_SPIDER_PHOTOS"
prev=json.loads(PREV.read_text())
assert prev["slot"]=="A" and prev["car_id"]=="daytona365"
assert prev["after_blend_sha256"]==SHA["src"]
assert prev["original_pmt_sha256"]==SHA["pmt"]
assert prev["original_import_sha256"]==SHA["import"]
assert prev["exact_spider_photo_sha256"]==SHA["photo"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
objects={k:bpy.data.objects[n] for k,n in PARTS.items()}
before={}
for k,o in objects.items():
 pr=prev["modified_existing_source_derived_objects"][k]
 assert o.type=="MESH" and pr["name"]==o.name and o.data.users==1
 assert sig(o)==pr["after_signature"],(k,"source mesh signature mismatch")
 assert (len(o.data.vertices),len(o.data.polygons))==(pr["after_vertices"],pr["after_faces"])
 assert o.data.uv_layers and o.data.materials
 before[k]={"name":o.name,"vertices":len(o.data.vertices),
  "faces":len(o.data.polygons),"sig":sig(o),"matrix":matrix(o),
  "uv_layers":[uv.name for uv in o.data.uv_layers],
  "material_names":[mat.name if mat else None for mat in o.data.materials]}
protected={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in PARTS.values()}
assert len(protected)==107
baseline={"objects":set(bpy.data.objects),"materials":set(bpy.data.materials),
"images":{im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images},
"cameras":{o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"},
"curves":set(bpy.data.curves),"camera":(bpy.context.scene.camera.name,matrix(bpy.context.scene.camera))}
assert all(hole_check(objects["spoke"])),"BLOCKED_INPUT: eight original-source through-holes not open"
# Subdivide existing factory-derived cowl and original-derived rim IN PLACE only.
# This adds interpolation loops within original faces, never new disconnected objects.
topology={}
for k in ("brow","rim"):
 ob=objects[k];bm=bmesh.new();bm.from_mesh(ob.data)
 try:
  bef_v,bef_f=len(bm.verts),len(bm.faces)
  bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True,smooth=0.0)
  assert len(bm.verts)>bef_v and len(bm.faces)>bef_f,(k,"subdivide did not create real topology")
  topology[k]={"before":[bef_v,bef_f],"after":[len(bm.verts),len(bm.faces)]}
  bm.to_mesh(ob.data)
 finally:bm.free()
 ob.data.update()
 assert ob.data.uv_layers and [uv.name for uv in ob.data.uv_layers]==before[k]["uv_layers"]
 assert [mat.name if mat else None for mat in ob.data.materials]==before[k]["material_names"]

changed={}
for k,o in objects.items():
 inv=o.matrix_world.inverted()
 modified=0;mx=0.0;acc=0.0
 for vert in o.data.vertices:
  p=o.matrix_world@vert.co
  dx=dy=dz=0.0
  if k=="dashboard":
   # Genuine Spyder's padded shelf curls beneath gauge binnacle;
   # preserve both distant outer dashboard edge profiles.
   mask=smooth(-.654,-.610,p.x)*(1.-smooth(-.103,-.064,p.x))
   front=1.-smooth(.187,.228,p.y)
   band=smooth(.722,.798,p.z)*(1.-smooth(.915,.951,p.z))
   center=math.exp(-((p.x+.35)/.220)**4)
   dz=-.0042*mask*front*band*(.68+.32*center)
   dy=-.0030*mask*front*band*(.46+.54*center)
  elif k=="brow":
   # The reference photograph shows a rounded, curved padded hood arch
   # with shoulders tucked down, not a separate flat floating plate.
   x=p.x+.349
   u=x/.285
   center=math.exp(-(u/.63)**4)
   edge=smooth(-.632,-.609,p.x)*(1.-smooth(-.081,-.053,p.x))
   front=1.-smooth(.178,.227,p.y)
   top=smooth(.927,.958,p.z)
   dz=.0044*edge*front*top*center-.0062*edge*front*top*(1.-center)
   dy=-.0047*edge*front*(.45+.55*center)
  elif k=="bezel":
   # Rolled flange and shallow recession of existing native-derived
   # dial-ring metal; source textures and dial centers stay untouched.
   bright=math.exp(-((p.y-.1537)/.0025)**2)
   recessed=math.exp(-((p.y-.1512)/.0012)**2)
   dy=-.0020*bright+.0005*recessed
   dz=.0008*bright*(p.z-.8252)/.11
  elif k=="spoke":
   # Original source pressing: subtle pressed depression BETWEEN the
   # eight actual source holes and relief at their close metal lips.
   gap=min(math.hypot(p.x-x,p.z-z)/r for x,z,r in HOLES)
   safe=smooth(1.05,2.10,gap)
   ann=0.
   for hx,hz,r in HOLES:
    d=math.hypot(p.x-hx,p.z-hz)/r
    ann=max(ann,math.exp(-((d-1.55)/.32)**2))
   xy=p.x+.350
   arms=math.exp(-((p.z-.802)/.025)**4)*smooth(.032,.100,abs(xy))
   bottom=math.exp(-((p.z-.726)/.055)**4)*math.exp(-(xy/.026)**4)
   depth=math.exp(-((p.y+.286)/.020)**2)
   dy=-.0022*ann*depth+.0018*safe*(arms+.65*bottom)*depth
   dz=.00065*safe*(arms+.40*bottom)*depth*math.tanh(xy/.055)
  elif k=="rim":
   # Actual old rim now has finer native-derived loops to sculpt an
   # oval upper grip profile and keep lower-left/right ring untouched.
   rx=p.x+.35;rz=p.z-.792
   radial=math.hypot(rx,rz)
   angle=math.atan2(rz,rx)
   upper=math.exp(-((angle-.78)/.24)**4)+math.exp(-((angle-2.36)/.24)**4)
   front=math.exp(-((p.y+.279)/.016)**2)
   back=math.exp(-((p.y+.297)/.009)**2)
   if radial>.04:
    d=.0022*upper*front-.0008*upper*back
    dx=d*rx/radial
    dz=d*rz/radial
    dy=.00175*upper*(front-.35*back)
  elif k=="hub":
   # Existing central shaft transition, real shallow collar step.
   radius=math.hypot(p.x+.35,p.z-.767)
   axial=math.exp(-((p.y+.244)/.011)**2)*smooth(.008,.021,radius)
   if radius>1e-7:
    d=.0018*axial
    dx=d*(p.x+.35)/radius
    dz=d*(p.z-.767)/radius
    dy=-.0017*axial
  displacement=Vector((dx,dy,dz))
  if displacement.length<.000030:continue
  vert.co=inv@(p+displacement)
  modified+=1
  mx=max(mx,displacement.length*1000.)
  acc+=displacement.length*1000.
 o.data.update()
 min_moves={"dashboard":90,"brow":250,"bezel":100,"spoke":200,"rim":60,"hub":20}[k]
 assert modified>=min_moves,(k,"insufficient actual source mesh edits",modified)
 assert mx<10.0,(k,"invalid displacement",mx)
 assert sig(o)!=before[k]["sig"]
 assert matrix(o)==before[k]["matrix"]
 assert [uv.name for uv in o.data.uv_layers]==before[k]["uv_layers"]
 assert [mat.name if mat else None for mat in o.data.materials]==before[k]["material_names"]
 changed[k]={"source_derived_original_object":o.name,"before":before[k],
 "after_mesh_signature":sig(o),"after_vertices":len(o.data.vertices),
 "after_faces":len(o.data.polygons),"moved_vertices":modified,
 "maximum_displacement_mm":round(mx,5),"mean_displacement_mm":round(acc/modified,5)}
assert set(bpy.data.objects)==baseline["objects"],"prohibited new object"
assert set(bpy.data.materials)==baseline["materials"]
assert set(bpy.data.curves)==baseline["curves"]
assert {im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}==baseline["images"]
assert {o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"}==baseline["cameras"]
assert (bpy.context.scene.camera.name,matrix(bpy.context.scene.camera))==baseline["camera"]
assert all(sig(bpy.data.objects[n])==h for n,h in protected.items()),"other vehicle mesh changed"
assert all(hole_check(objects["spoke"])),"existing original 8 spoke holes failed physical BVH check"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.is_file() and DEST.stat().st_size>1_000_000
record={
 "result":"SLOTA_DAYTONA_R13_GENUINE_ORIGINAL_GEOMETRY_SAVED",
 "slot":"A","car_id":"daytona365","blender":bpy.app.version_string,
 "original_native_PMT":str(PMT),"original_native_PMT_sha256":SHA["pmt"],
 "verified_original_import":str(IMPORT),"verified_original_import_sha256":SHA["import"],
 "source_blend":SRC.name,"source_blend_sha256":SHA["src"],
 "output_blend":DEST.name,"output_blend_sha256":hashfile(DEST),
 "output_blend_bytes":DEST.stat().st_size,
 "original_native_mesh_object_ids":["object00_group01_material012_a0","object22_group00_material000_a0"],
 "source_derived_original_mesh_changes":changed,
 "refined_original_topology":topology,"other_meshes_preserved":107,
 "other_meshes_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
 "photo_exact_spider_LHD_sha256":SHA["photo"],
 "photo_detail_sha256":hashfile(PHOTO_DETAIL),
 "photo_spyder_1972_sha256":hashfile(PHOTO_SPYDER),
 "source_eight_steering_spoke_holes_open_BVH":True,
 "same_camera_object_matrices_pivots_materials_packed_images":True,
 "no_new_objects_or_materials":True,
 "no_new_textures_normals_PBR_or_exterior":True,
 "no_game_or_native_PMTOVCOVC3_export":True,
 "real_game_driver_eye":"NOT_CALIBRATED","seven_exact_spider_views":"INCOMPLETE",
 "github_hosted_private_source":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "slot_a_active":True,"vehicle_complete":False}
AUDIT.write_text(json.dumps(record,indent=2,ensure_ascii=False))
print(record["result"],json.dumps({
 "scene_sha256":record["output_blend_sha256"],
 "topology":topology,
 "moved":{k:x["moved_vertices"] for k,x in changed.items()},
 "max_mm":{k:x["maximum_displacement_mm"] for k,x in changed.items()}},ensure_ascii=False),flush=True)

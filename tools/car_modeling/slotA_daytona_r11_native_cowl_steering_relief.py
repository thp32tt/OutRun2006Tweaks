#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona slot A r11: source-PMT dashboard / three-spoke geometry continuation.

Visually compared with authenticated 1971 Daytona Spider LHD cockpit photo.
Modify only original source-derived existing dashboard, brow, gauge bezel,
three-spoke metal, rim and hub geometry, compared with archived authentic
Daytona Spider LHD photo (not game camera calibration).
No imported/synthetic replacement, no new objects, no exterior, no textures,
no PMT/OVC/OVC3/GLB exports, no game/VR work. Private source required.
"""
import bpy, hashlib, json, math, os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

W = Path(os.environ["SLOT_A_WORK"])
SRC = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v8_r10.blend"
DEST = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v9_r11.blend"
AUDIT = W / "SLOT_A_DAYTONA_P0_R11_NATIVE_COWL_STEERING_RELIEF_GEOMETRY.json"
PREV = W / "SLOT_A_DAYTONA_P0_R10_ORIGINAL_SPIDER_DASH_WHEEL_GEOMETRY.json"
PMT = Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIGINAL_IMPORT = Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
EXACT_PHOTO = Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECTED = {
 "src": "d18408d82e5de993f96ce882eff80e31eedf4b41468747785890e0942b2f6da9",
 "pmt": "f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "orig": "92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "photo": "6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
NAMES = {
 "dashboard": "V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "brow": "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "bezel": "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "spoke": "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "rim": "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "hub": "V7_SHORT_SHAFT_AT_WHEEL_HUB"}
EXPECTED_COUNTS = {
 "dashboard": (1885,3584),"brow": (650,648),"bezel": (908,1344),
 "spoke": (9720,17285),"rim": (1536,1536),"hub": (224,210)}
HOLES = [
 (-.431,.804,.0068), (-.410,.804,.0068), (-.390,.804,.0068),
 (-.310,.804,.0068), (-.290,.804,.0068), (-.269,.804,.0068),
 (-.350,.745,.0052), (-.350,.716,.0047)]
def sha(p):
 return hashlib.sha256(p.read_bytes()).hexdigest()
def sig(o):
 d = o.data
 return hashlib.sha256(repr((
  [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
  [(f.material_index,tuple(f.vertices)) for f in d.polygons])).encode("utf-8")).hexdigest()
def matrix(o):
 return [[round(float(v),9) for v in row] for row in o.matrix_world]
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)))
 return t*t*(3.-2.*t)
def hole_hit(tree,x,z):
 return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None

assert bpy.app.version_string.startswith("4.5.15"), bpy.app.version_string
assert Path(bpy.data.filepath).resolve()==SRC.resolve()
assert not DEST.exists() and not AUDIT.exists(),"immutable existing r11 private artifact"
for k,p in (("src",SRC),("pmt",PMT),("orig",ORIGINAL_IMPORT),("photo",EXACT_PHOTO)):
 assert p.is_file() and sha(p)==EXPECTED[k],(k,"BLOCKED_INPUT: original source mismatch")
prior=json.loads(PREV.read_text())
assert prior["after_blend_sha256"]==EXPECTED["src"],"source chain disrupted"
assert prior["original_pmt_sha256"]==EXPECTED["pmt"]
assert prior["original_import_sha256"]==EXPECTED["orig"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
objects={k:bpy.data.objects[n] for k,n in NAMES.items()}
before={}
for key,obj in objects.items():
 assert obj.type=="MESH" and obj.data.users==1 and obj.data.uv_layers and obj.data.materials
 assert (len(obj.data.vertices),len(obj.data.polygons))==EXPECTED_COUNTS[key]
 assert sig(obj)==prior["modified_existing_source_derived_objects"][key]["after_signature"],key
 before[key]={"source_mesh_object":obj.name,"vertices":len(obj.data.vertices),
              "faces":len(obj.data.polygons),"geometry_signature":sig(obj),
              "matrix_world":matrix(obj)}
unaltered={obj.name:sig(obj) for obj in bpy.data.objects if obj.type=="MESH"
           and obj.name not in NAMES.values()}
assert len(unaltered)==107
inventory={
 "objects":set(bpy.data.objects),"materials":set(bpy.data.materials),
 "images":{im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images},
 "cameras":{ob.name:matrix(ob) for ob in bpy.data.objects if ob.type=="CAMERA"},
 "curves":set(bpy.data.curves)}
origin_scene=(bpy.context.scene.camera.name,matrix(bpy.context.scene.camera))
test_tree=BVHTree.FromObject(objects["spoke"],bpy.context.evaluated_depsgraph_get())
assert all(not hole_hit(test_tree,x,z) and hole_hit(test_tree,x+1.6*rad,z)
           for x,z,rad in HOLES),"existing source-derived through-holes obstructed"

moved={}
for k,ob in objects.items():
 inv=ob.matrix_world.inverted()
 count=0;max_mm=0.;sum_mm=0.
 for v in ob.data.vertices:
  p=ob.matrix_world@v.co
  dx=dy=dz=0.
  if k=="brow":
   # Existing source-derived closed cowl: round the raised front blade
   # to approximate the real Spider's padded arch and dropped shoulders.
   u=(p.x+.350)/.285
   core=math.exp(-(u/.74)**4)
   shoulders=1-core
   edge=smooth(-.632,-.610,p.x)*(1-smooth(-.077,-.053,p.x))
   front=1-smooth(.195,.228,p.y)
   crown=smooth(.920,.954,p.z)
   dz=edge*front*(.0036*core-.0051*shoulders)*(.44+.56*crown)
   dy=-.0031*edge*front*(.60+.4*core)
  elif k=="dashboard":
   # Profile the ORIGINAL-derived padded dash's gauge recess without
   # editing door, windshield, external surfaces or any source anchors.
   xband=smooth(-.657,-.621,p.x)*(1-smooth(-.077,-.039,p.x))
   floor=smooth(.771,.836,p.z)*(1-smooth(.915,.949,p.z))
   leading=1-smooth(.189,.226,p.y)
   arch=math.exp(-((p.x+.35)/.245)**4)
   dz=.0042*xband*floor*leading*(.45+.55*arch)
   dy=-.0029*xband*floor*leading*(.68+.32*arch)
  elif k=="bezel":
   # Rolled metal relief around three EXISTING gauge rims; original
   # connected components, gauge names, UV and dial art are preserved.
   t=math.exp(-((p.y-.15335)/.00235)**2)
   dy=-.00185*t
   dz=.00055*t*(p.z-.826)/.09
  elif k=="spoke":
   # Three-spoke source pressing: round material far from all eight
   # existing real perforations, retaining steering pivot and hole rims.
   x=p.x+.350
   clearance=min(math.hypot(p.x-hx,p.z-hz)/rad for hx,hz,rad in HOLES)
   safety=smooth(1.22,2.7,clearance)
   horizontal=math.exp(-((p.z-.805)/.023)**4)*smooth(.034,.097,abs(x))
   vertical=math.exp(-((p.z-.716)/.042)**4)*math.exp(-(x/.025)**4)
   shape=safety*min(1.,horizontal+.82*vertical)*math.exp(-((p.y+.287)/.024)**2)
   dy=.0032*shape
   dz=.00085*shape*math.tanh(x/.056)
  elif k=="rim":
   # Slightly sculpt two actual upper grip arcs by adjusting 3D rim
   # cross-section radially, with native wheel spin center unchanged.
   x=p.x+.350;z=p.z-.792
   angle=math.atan2(z,x)
   left_right=math.exp(-((angle-.72)/.18)**4)+math.exp(-((angle-2.42)/.18)**4)
   radial=math.hypot(x,z)
   if radial>.04:
    relief=.00155*left_right*math.exp(-((p.y+.284)/.014)**2)
    dx=relief*x/radial
    dz=relief*z/radial
    dy=-.00125*left_right*math.exp(-((p.y+.278)/.015)**2)
  elif k=="hub":
   # Existing source-derived hub/shaft only, make the concentric hub
   # collar a real physical step without inventing another separate mesh.
   rr=math.hypot(p.x+.350,p.z-.767)
   band=math.exp(-((p.y+.246)/.012)**2)*smooth(.007,.019,rr)
   if rr>.000001:
    dx=.00165*band*(p.x+.350)/rr
    dz=.00165*band*(p.z-.767)/rr
    dy=-.00125*band
  disp=Vector((dx,dy,dz))
  if disp.length<.000025:continue
  v.co=inv@(p+disp)
  count+=1
  max_mm=max(max_mm,disp.length*1000.)
  sum_mm+=disp.length*1000.
 ob.data.update()
 assert count>={"dashboard":90,"brow":120,"bezel":100,"spoke":200,"rim":20,"hub":20}[k],(k,count)
 assert max_mm<12.,(k,max_mm)
 assert sig(ob)!=before[k]["geometry_signature"],"must edit true source-derived geometry"
 assert matrix(ob)==before[k]["matrix_world"],"pivot/object matrix changed"
 ob["SLOTA_SOURCE_PMT"]=PMT.name
 ob["SLOTA_SOURCE_SHA256"]=EXPECTED["pmt"]
 moved[k]={"name":ob.name,"before":before[k],"after_vertices":len(ob.data.vertices),
           "after_faces":len(ob.data.polygons),"after_signature":sig(ob),
           "moved_vertices":count,"max_mm":round(max_mm,5),"average_mm":round(sum_mm/count,5)}
assert all(sig(bpy.data.objects[name])==h for name,h in unaltered.items())
assert set(bpy.data.objects)==inventory["objects"]
assert set(bpy.data.materials)==inventory["materials"]
assert set(bpy.data.curves)==inventory["curves"]
assert {im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}==inventory["images"]
assert {ob.name:matrix(ob) for ob in bpy.data.objects if ob.type=="CAMERA"}==inventory["cameras"]
assert (bpy.context.scene.camera.name,matrix(bpy.context.scene.camera))==origin_scene
final_tree=BVHTree.FromObject(objects["spoke"],bpy.context.evaluated_depsgraph_get())
assert all(not hole_hit(final_tree,x,z) and hole_hit(final_tree,x+1.6*rad,z)
           for x,z,rad in HOLES),"no fabricated/filled spoke openings"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.is_file() and DEST.stat().st_size>1000000
record={
 "status":"SLOT_A_R11_ORIGINAL_SPIDER_NATIVE_COWL_STEERING_SAVED",
 "slot":"A","car_id":"daytona365","original_pmt_resource":str(PMT),
 "original_pmt_sha256":EXPECTED["pmt"],"original_import_blend":str(ORIGINAL_IMPORT),
 "original_import_sha256":EXPECTED["orig"],"exact_spider_photo":str(EXACT_PHOTO),
 "exact_spider_photo_sha256":EXPECTED["photo"],"before_blend":SRC.name,
 "before_blend_sha256":EXPECTED["src"],"after_blend":DEST.name,
 "after_blend_sha256":sha(DEST),"after_blend_bytes":DEST.stat().st_size,
 "blender":bpy.app.version_string,"source_original_mesh_object_ids":[
  "object00_group01_material012_a0","object22_group00_material000_a0"],
 "modified_existing_source_derived_objects":moved,
 "protected_other_meshes":len(unaltered),
 "protected_other_mesh_signatures_sha256":hashlib.sha256(json.dumps(unaltered,sort_keys=True).encode()).hexdigest(),
 "physical_native_steering_spoke_holes_preserved":8,
 "source_matrices_camera_objects_material_images_preserved":True,
 "no_exterior_body_tires_or_texture":True,"no_game_or_mod_export":True,
 "real_driver_eye":"UNVERIFIED","authentic_spider_7_views":"INCOMPLETE",
 "github_hosted_private_blend":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "completion":"PARTIAL_NEEDS_QA","advance_car":False}
AUDIT.write_text(json.dumps(record,indent=2))
print(record["status"],json.dumps({
 "sha256":record["after_blend_sha256"],"bytes":record["after_blend_bytes"],
 "moved":{k:v["moved_vertices"] for k,v in moved.items()},
 "max_mm":{k:v["max_mm"] for k,v in moved.items()}}),flush=True)
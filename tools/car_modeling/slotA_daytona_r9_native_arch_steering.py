#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona slot A r9: native PMT-backed existing mesh only.

Photo-guided geometry continuation: curved instrument brow, recessed dash
surround, gauge rolled faces, original three-spoke metal and hub collar.
No imported/synthetic replacement, no new objects, no exterior, no textures,
no PMT/OVC/OVC3/GLB exports, no game/VR work. Private source required.
"""
import bpy, hashlib, json, math, os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

W = Path(os.environ["SLOT_A_WORK"])
SRC = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v6_r8.blend"
DEST = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v7_r9.blend"
AUDIT = W / "SLOT_A_DAYTONA_P0_R9_ORIGINAL_ARCH_STEERING_GEOMETRY.json"
PREV = W / "SLOT_A_DAYTONA_P0_R8_PHOTO_GUIDED_EXISTING_MESH.json"
PMT = Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIGINAL_IMPORT = Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
EXACT_PHOTO = Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECTED = {
 "src": "39141806a776d14f1283181989608723a00395ed28200fc62c7ecbb87ac5d9dd",
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
assert not DEST.exists() and not AUDIT.exists(),"immutable existing r9 private artifact"
for k,p in (("src",SRC),("pmt",PMT),("orig",ORIGINAL_IMPORT),("photo",EXACT_PHOTO)):
 assert p.is_file() and sha(p)==EXPECTED[k],(k,"BLOCKED_INPUT: original source mismatch")
prior=json.loads(PREV.read_text())
assert prior["output_sha256"]==EXPECTED["src"],"source chain disrupted"
assert prior["original_game_sha256"]==EXPECTED["pmt"]
assert prior["original_import_sha256"]==EXPECTED["orig"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
objects={k:bpy.data.objects[n] for k,n in NAMES.items()}
before={}
for key,obj in objects.items():
 assert obj.type=="MESH" and obj.data.users==1 and obj.data.uv_layers and obj.data.materials
 assert (len(obj.data.vertices),len(obj.data.polygons))==EXPECTED_COUNTS[key]
 if key!="hub":
  r8key = {"brow":"cowl"}.get(key,key)
  assert sig(obj)==prior["changed_existing_meshes"][r8key]["after_signature"],key
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
   # True existing 13-row native-derived cowl shell: shape a smooth,
   # continuous crowned arch (center ~12 mm higher, shoulders ~6 mm
   # lower), with end/perimeter weighting and original thickness.
   x=p.x+.350
   interior=smooth(-.635,-.586,p.x)*(1-smooth(-.114,-.050,p.x))
   arch=math.exp(-(x/.225)**4)
   front=(1-smooth(.190,.228,p.y))
   coverage=(.36+.64*front)
   dz=interior*coverage*(.0120*arch-.0065*(1-arch))
   dy=-.0040*interior*front*(.45+.55*arch)
  elif k=="dashboard":
   # In-place padded dash channel beneath native binnacle; preserve
   # outer dashboard bounds, screen edge and original source anchors.
   cluster=smooth(-.641,-.610,p.x)*(1-smooth(-.089,-.045,p.x))
   zmask=smooth(.854,.895,p.z)*(1-smooth(.933,.955,p.z))
   front=1-smooth(.205,.230,p.y)
   arch=math.exp(-((p.x+.350)/.230)**4)
   dy=-.0070*cluster*zmask*front*(.6+.4*arch)
   dz=.0046*cluster*zmask*front*arch
  elif k=="bezel":
   # Relieve ONLY extant metal-bezel geometry; do not alter instrument
   # art/UV or create new gauges. Shape the existing front ring's axial
   # rolled rim using its physical 3-component y range.
   dy=-.0032*math.exp(-((p.y-.1532)/.00175)**2)
   dz=.0012*(p.z-.8252)/.095*math.exp(-((p.y-.1532)/.0025)**2)
  elif k=="spoke":
   # Factory original three-spoke pressing: tapered material roll around
   # original eight punched holes, without altering their true boundaries.
   x=p.x+.35
   min_hole=min(math.hypot(p.x-hx,p.z-hz)/rad for hx,hz,rad in HOLES)
   safety=smooth(1.20,2.70,min_hole)
   lateral=math.exp(-((p.z-.804)/.022)**4)*smooth(.038,.088,abs(x))
   lower=.78*math.exp(-((p.z-.701)/.036)**4)*math.exp(-(x/.022)**4)
   dy=.0031*safety*min(1.,lateral+lower)*math.exp(-((p.y+.285)/.020)**2)
  elif k=="rim":
   # Genuine retained wheel rim: mirrored thumb contours on upper
   # quadrants; wheel center/steering pivot/transform unaltered.
   x=p.x+.35;z=p.z-.792
   a=math.atan2(z,x)
   grip=math.exp(-((a-.69)/.18)**4)+math.exp(-((a-2.46)/.18)**4)
   dy=-.0026*grip*math.exp(-((p.y+.279)/.017)**2)
  elif k=="hub":
   x,z=p.x+.350,p.z-.767
   rr=math.hypot(x,z)
   if rr>.00001:
    shoulder=math.exp(-((p.y+.249)/.009)**2)
    radial=.0020*shoulder
    dx=radial*x/rr;dz=radial*z/rr
  disp=Vector((dx,dy,dz))
  if disp.length<.000025:continue
  v.co=inv@(p+disp)
  count+=1
  max_mm=max(max_mm,disp.length*1000.)
  sum_mm+=disp.length*1000.
 ob.data.update()
 assert count>={"dashboard":100,"brow":120,"bezel":100,"spoke":100,"rim":30,"hub":20}[k],(k,count)
 assert max_mm<22.,(k,max_mm)
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
 "status":"SLOT_A_R9_NATIVE_PHOTO_GUIDED_EXISTING_DASH_STEERING_SAVED",
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
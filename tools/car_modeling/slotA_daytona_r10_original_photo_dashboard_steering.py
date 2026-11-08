#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona slot A r10: source-PMT cockpit dash/wheel sculpt only.

Visually compared with authenticated 1971 Daytona Spider LHD cockpit photo.
Shape the already-present imported dashboard, visor, gauge-rims, original
three-spoke pressing, rim and steering column without swapping source meshes.
No imported/synthetic replacement, no new objects, no exterior, no textures,
no PMT/OVC/OVC3/GLB exports, no game/VR work. Private source required.
"""
import bpy, hashlib, json, math, os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

W = Path(os.environ["SLOT_A_WORK"])
SRC = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v7_r9.blend"
DEST = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v8_r10.blend"
AUDIT = W / "SLOT_A_DAYTONA_P0_R10_ORIGINAL_SPIDER_DASH_WHEEL_GEOMETRY.json"
PREV = W / "SLOT_A_DAYTONA_P0_R9_ORIGINAL_ARCH_STEERING_GEOMETRY.json"
PMT = Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIGINAL_IMPORT = Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
EXACT_PHOTO = Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECTED = {
 "src": "fd8ec518304d2b048f5652a91f6469cf655ba91f5a40f600e5b5021dcba09e6a",
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
assert not DEST.exists() and not AUDIT.exists(),"immutable existing r10 private artifact"
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
   # Real Spider LHD photograph: hood upper line transitions gently into
   # the long padded dashboard instead of an isolated horizontal blade.
   # Deform the source-derived closed cowl ONLY, preserving edge anchors.
   band=smooth(-.640,-.610,p.x)*(1-smooth(-.106,-.063,p.x))
   center=math.exp(-((p.x+.35)/.205)**4)
   front=1-smooth(.187,.235,p.y)
   crown=smooth(.899,.936,p.z)
   dz=.0065*band*front*(.55+.45*center)*(.68+.32*crown)
   dy=-.0034*band*front*(.55+.45*center)
  elif k=="dashboard":
   # Resculpt the EXISTING original-derived dash to seat the instrument
   # visor and keep the real Spider's slight recess around dial sockets.
   band=smooth(-.640,-.606,p.x)*(1-smooth(-.116,-.074,p.x))
   pocket=smooth(.855,.888,p.z)*(1-smooth(.934,.961,p.z))
   front=1-smooth(.190,.231,p.y)
   center=math.exp(-((p.x+.350)/.200)**4)
   dz=-.0060*band*pocket*front*(.65+.35*center)
   dy=-.0036*band*pocket*front*(.4+.6*center)
  elif k=="bezel":
   # Recess the front of the 3 EXISTING gauge rolled lips without
   # changing dial graphics, ring topology, UV islands or gauge objects.
   face=math.exp(-((p.y-.1530)/.00215)**2)
   dy=.0020*face
   dz=-.0008*face*(p.z-.8252)/.097
  elif k=="spoke":
   # Sculpt the factory perforated 3-spoke alloy stamping; exact
   # eight holes and source animation pivot must remain open/unchanged.
   x=p.x+.350
   clearance=min(math.hypot(p.x-hx,p.z-hz)/rad for hx,hz,rad in HOLES)
   safety=smooth(1.35,2.90,clearance)
   arms=math.exp(-((p.z-.804)/.019)**4)*smooth(.034,.087,abs(x))
   center=math.exp(-((p.z-.708)/.036)**4)*math.exp(-(x/.024)**4)
   envelope=safety*min(1.,arms+.76*center)*math.exp(-((p.y+.286)/.023)**2)
   dy=-.0027*envelope
   dz=.0007*envelope*math.tanh(x/.045)
  elif k=="rim":
   # Compress the cross section of original aligned rim at two authentic
   # thumb-rest arcs; leave its center line, mesh IDs and spin axis fixed.
   a=math.atan2(p.z-.792,p.x+.350)
   thumb=math.exp(-((a-.64)/.20)**4)+math.exp(-((a-2.50)/.20)**4)
   dy=.00185*thumb*math.exp(-((p.y+.279)/.017)**2)
  elif k=="hub":
   # Subtle axial collar step of the existing original wheel hub/column.
   rr=math.hypot(p.x+.350,p.z-.767)
   shoulder=math.exp(-((p.y+.248)/.010)**2)
   dy=-.0016*shoulder*smooth(.006,.028,rr)
  disp=Vector((dx,dy,dz))
  if disp.length<.000025:continue
  v.co=inv@(p+disp)
  count+=1
  max_mm=max(max_mm,disp.length*1000.)
  sum_mm+=disp.length*1000.
 ob.data.update()
 assert count>={"dashboard":60,"brow":120,"bezel":100,"spoke":120,"rim":30,"hub":20}[k],(k,count)
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
 "status":"SLOT_A_R10_ORIGINAL_PHOTO_GUIDED_NATIVE_DASH_STEERING_SAVED",
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
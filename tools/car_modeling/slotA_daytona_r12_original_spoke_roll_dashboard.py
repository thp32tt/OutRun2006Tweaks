#!/usr/bin/env python3
"""Slot A Daytona r12: source-linked P0 geometry of genuine existing cockpit meshes only.
Read-only original OutRun 2006 native PMT + verified original Blender import + immutable r11.
Geometrically roll 8 ORIGINAL spoke perforation lips and reshape EXISTING dashboard/
instrument brow/gauge bezel/rim/hub vertex surfaces. No new cockpit substitute, no
outside body, materials, textures, PBR, exports, game runtime or VR source modifications.
"""
import bpy, hashlib, json, math, os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

W=Path(os.environ["SLOT_A_WORK"])
SRC=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v9_r11.blend"
DEST=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v10_r12.blend"
PREV=W/"SLOT_A_DAYTONA_P0_R11_NATIVE_COWL_STEERING_RELIEF_GEOMETRY.json"
AUDIT=W/"SLOT_A_DAYTONA_P0_R12_NATIVE_SPOKE_EDGE_AND_DASH_GEOMETRY.json"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECT={"src":"2324f2e496d18073d8bd81433512a0a569f13936f0e8930dcb0ee8100723d026",
"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
"orig":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
"photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
NAMES={
 "dashboard":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "brow":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "hub":"V7_SHORT_SHAFT_AT_WHEEL_HUB"}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
(-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
(-.350,.745,.0052),(-.350,.716,.0047)]
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for part in iter(lambda:f.read(1<<20),b""):h.update(part)
 return h.hexdigest()
def sig(o):
 d=o.data
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode()).hexdigest()
def matrix(o):return [[round(float(v),9) for v in row] for row in o.matrix_world]
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)))
 return t*t*(3.-2.*t)
def holes_open(o):
 tree=BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get())
 def hit(x,z):return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
 return [not hit(x,z) and hit(x+1.6*r,z) for x,z,r in HOLES]

assert bpy.app.version_string.startswith("4.5.15"),bpy.app.version_string
assert Path(bpy.data.filepath).resolve()==SRC.resolve(),"BLOCKED_INPUT: expected original-derived r11 scene"
assert not DEST.exists() and not AUDIT.exists(),"immutable R12 already present"
for key,path in (("src",SRC),("pmt",PMT),("orig",ORIG),("photo",PHOTO)):
 assert path.is_file() and sha(path)==EXPECT[key],("BLOCKED_INPUT",key)
prev=json.loads(PREV.read_text())
assert prev["after_blend_sha256"]==EXPECT["src"]
assert prev["original_pmt_sha256"]==EXPECT["pmt"]
assert prev["original_import_sha256"]==EXPECT["orig"]
assert prev["exact_spider_photo_sha256"]==EXPECT["photo"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert "V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0" in bpy.data.objects
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
parts={k:bpy.data.objects[v] for k,v in NAMES.items()}
all_before={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH"}
protected={n:h for n,h in all_before.items() if n not in NAMES.values()}
assert len(protected)==107
scene_inventory={"objects":set(bpy.data.objects),"materials":set(bpy.data.materials),
"images":{im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images},
"cameras":{o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"},
"curves":set(bpy.data.curves),"scene_camera":(bpy.context.scene.camera.name,matrix(bpy.context.scene.camera))}
before={}
for key,o in parts.items():
 pr=prev["modified_existing_source_derived_objects"][key]
 assert pr["name"]==o.name and pr["after_signature"]==sig(o)
 assert (len(o.data.vertices),len(o.data.polygons))==(pr["after_vertices"],pr["after_faces"])
 assert o.type=="MESH" and o.data.users==1 and o.data.uv_layers and o.data.materials
 before[key]={"name":o.name,"vertices":len(o.data.vertices),"faces":len(o.data.polygons),
 "signature":sig(o),"matrix":matrix(o)}
assert all(holes_open(parts["spoke"])),"BLOCKED_INPUT: r11 original real holes not open"

changed={}
for key,o in parts.items():
 inv=o.matrix_world.inverted()
 moves=0;max_mm=0.;sum_mm=0.
 for v in o.data.vertices:
  p=o.matrix_world@v.co
  dx=dy=dz=0.
  if key=="dashboard":
   # The original-derived dash's very front surface rolls down around
   # the actual instrument pod, keeping the horizontal windshield line.
   cluster=smooth(-.645,-.616,p.x)*(1-smooth(-.082,-.054,p.x))
   lower=smooth(.766,.824,p.z)*(1-smooth(.901,.945,p.z))
   front=1-smooth(.186,.229,p.y)
   flank=math.exp(-((p.x+.35)/.22)**4)
   dy=-.0029*cluster*lower*front*(.65+.35*flank)
   dz=-.0038*cluster*lower*front*(.42+.58*flank)
  elif key=="brow":
   # Sculpt the extant source-derived closed gauge shroud, removing an
   # overly sharp straight top ledge and giving the arch padded shoulders.
   u=(p.x+.351)/.28
   center=math.exp(-(u/.72)**4)
   edges=1.-center
   xmask=smooth(-.633,-.607,p.x)*(1.-smooth(-.084,-.052,p.x))
   front=1.-smooth(.182,.228,p.y)
   upper=smooth(.931,.962,p.z)
   dz=xmask*front*upper*(.0032*center-.0039*edges)
   dy=-.0031*xmask*front*(.56+.44*center)
  elif key=="bezel":
   # Give the source-derived gauge surround a true shallow rolled lip,
   # changing geometry only; original art/material slots are untouched.
   outer=math.exp(-((p.y-.1534)/.00175)**2)
   front=math.exp(-((p.y-.15035)/.00092)**2)
   dy=-.00145*outer+.00067*front
   dz=.00036*(p.z-.8252)/.090*outer
  elif key=="spoke":
   # Unlike earlier broad spoke relief, this is an eight-hole local
   # stamped-metal rolled lip: preserve all physical through-holes.
   depth=math.exp(-((p.y+.286)/.017)**2)
   roll=0.
   for hx,hz,r in HOLES:
    dist=math.hypot(p.x-hx,p.z-hz)
    ann=math.exp(-((dist/r-1.33)/.32)**2)
    roll=max(roll,ann)
   edge=(.00275*roll*depth)
   longitudinal=math.exp(-((p.z-.804)/.024)**4)*smooth(.031,.096,abs(p.x+.35))
   safety=min(smooth(1.0,2.2,math.hypot(p.x-hx,p.z-hz)/r) for hx,hz,r in HOLES)
   shell=.0014*longitudinal*depth*safety
   dy=-edge+shell
  elif key=="rim":
   # Source rim sculpt: two physical thumb-rest shoulder arcs, retaining
   # original ring center and spin axis, no invented/replacement wheel.
   ax=p.x+.35;az=p.z-.792
   angle=math.atan2(az,ax)
   thumb=math.exp(-((angle-.79)/.21)**4)+math.exp(-((angle-2.35)/.21)**4)
   radial=math.hypot(ax,az)
   layer=math.exp(-((p.y+.287)/.017)**2)
   if radial>.04:
    expand=.00165*thumb*layer
    dx=expand*ax/radial
    dz=expand*az/radial
    dy=.00098*thumb*layer
  elif key=="hub":
   # A machined axial transition in the existing Ferrari center hub,
   # without changing animation pivot or adding a separate mesh.
   radial=math.hypot(p.x+.35,p.z-.767)
   ring=math.exp(-((p.y+.246)/.009)**2)*smooth(.008,.019,radial)
   if radial>1e-6:
    dx=.00135*ring*(p.x+.35)/radial
    dz=.00135*ring*(p.z-.767)/radial
    dy=-.0012*ring
  displacement=Vector((dx,dy,dz))
  if displacement.length<.000025:continue
  v.co=inv@(p+displacement)
  moves+=1;max_mm=max(max_mm,displacement.length*1000);sum_mm+=displacement.length*1000
 o.data.update()
 minimum={"dashboard":70,"brow":100,"bezel":150,"spoke":60,"rim":15,"hub":15}[key]
 assert moves>=minimum,(key,"too few source-derived vertices moved",moves)
 assert max_mm<=8.,(key,max_mm)
 assert sig(o)!=before[key]["signature"]
 assert matrix(o)==before[key]["matrix"]
 changed[key]={"name":o.name,"before":before[key],
 "after_signature":sig(o),"after_vertices":len(o.data.vertices),
 "after_faces":len(o.data.polygons),"moved_vertices":moves,
 "max_mm":round(max_mm,5),"mean_mm":round(sum_mm/moves,5)}
assert set(bpy.data.objects)==scene_inventory["objects"]
assert set(bpy.data.materials)==scene_inventory["materials"]
assert set(bpy.data.curves)==scene_inventory["curves"]
assert {im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}==scene_inventory["images"]
assert {o.name:matrix(o) for o in bpy.data.objects if o.type=="CAMERA"}==scene_inventory["cameras"]
assert (bpy.context.scene.camera.name,matrix(bpy.context.scene.camera))==scene_inventory["scene_camera"]
assert all(sig(bpy.data.objects[n])==h for n,h in protected.items())
assert all(holes_open(parts["spoke"])),"post-edit BVH found sealed original spoke hole"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.is_file() and DEST.stat().st_size>1_000_000
result={"status":"SLOT_A_DAYTONA_R12_ORIGINAL_SOURCE_NATIVE_GEOMETRY_SAVED",
"slot":"A","car_id":"daytona365",
"original_pmt_resource":str(PMT),"original_pmt_sha256":EXPECT["pmt"],
"original_import_blend":str(ORIG),"original_import_sha256":EXPECT["orig"],
"exact_spider_photo":str(PHOTO),"exact_spider_photo_sha256":EXPECT["photo"],
"before_blend":SRC.name,"before_blend_sha256":EXPECT["src"],
"after_blend":DEST.name,"after_blend_sha256":sha(DEST),
"after_blend_bytes":DEST.stat().st_size,
"original_mesh_ids":["object00_group01_material012_a0","object22_group00_material000_a0"],
"modified_existing_source_derived_objects":changed,
"protected_others_count":len(protected),
"protected_others_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
"preserved_spoke_perforations":8,
"source_camera_object_transforms_materials_images_preserved":True,
"blender":bpy.app.version_string,
"no_new_objects_or_materials":True,"no_exterior_or_export":True,
"game_driver_eye":"NOT_CALIBRATED","seven_spider_views":"INCOMPLETE",
"github_hosted_original_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
"car_complete":False,"slot_a_advance":False}
AUDIT.write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(result["status"],json.dumps({"sha256":result["after_blend_sha256"],
"moved":{k:v["moved_vertices"] for k,v in changed.items()},
"mm":{k:v["max_mm"] for k,v in changed.items()}}),flush=True)

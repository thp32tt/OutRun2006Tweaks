#!/usr/bin/env python3
"""Daytona Slot A r8: refine existing PMT-derived gauge eyebrows, bezel lips,
and factory 3-spoke metal pressing. Actual OutRun2006 original, NEVER a proxy.
No new objects, material/texture work, mesh export, exterior work, or camera edit.
"""
import bpy, bmesh, hashlib, json, math, os
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree

W=Path(os.environ["SLOT_A_WORK"])
SRC=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v5_r7.blend"
OUT=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v6_r8.blend"
AUDIT=W/"SLOT_A_DAYTONA_P0_R8_PHOTO_GUIDED_EXISTING_MESH.json"
PRIOR=W/"SLOT_A_DAYTONA_P0_R7_ORIGINAL_BINNACLE_SPOKE.json"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECTED={
 "src":"a66f156b5f30971263fd1dd623075d275e15c0e73da0e48a94ccf38bbdf645fa",
 "pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"
}
NAMES={
 "dashboard":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
}
COUNTS={"dashboard":(1885,3584),"cowl":(650,648),"bezel":(908,1344),
        "spoke":(9720,17285),"rim":(1536,1536)}
HOLES=[(-.431,.804,.0068),(-.410,.804,.0068),(-.390,.804,.0068),
       (-.310,.804,.0068),(-.290,.804,.0068),(-.269,.804,.0068),
       (-.350,.745,.0052),(-.350,.716,.0047)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sig(o):
 d=o.data
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode()).hexdigest()
def mat(o):return [[round(float(c),9) for c in row] for row in o.matrix_world]
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)))
 return t*t*(3-2*t)
def islands(mesh):
 parents=list(range(len(mesh.vertices)))
 def find(i):
  while parents[i]!=i:
   parents[i]=parents[parents[i]]
   i=parents[i]
  return i
 for e in mesh.edges:
  a,b=map(find,e.vertices)
  parents[a]=b
 groups=defaultdict(list)
 for v in mesh.vertices:groups[find(v.index)].append(v.index)
 return list(groups.values())
def hole_hit(tree,x,z):
 return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None
assert bpy.app.version_string.startswith("4.5.15"),bpy.app.version_string
assert Path(bpy.data.filepath).resolve()==SRC.resolve()
assert not OUT.exists() and not AUDIT.exists(),"immutable private r8 output"
for k,p in [("src",SRC),("pmt",PMT),("import",ORIG),("photo",PHOTO)]:
 assert p.is_file() and sha(p)==EXPECTED[k],("wrong original / photo",k)
r7=json.loads(PRIOR.read_text())
assert r7["output_sha256"]==EXPECTED["src"] and r7["original_game_sha256"]==EXPECTED["pmt"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
changed={k:bpy.data.objects[n] for k,n in NAMES.items()}
old={}
for k,o in changed.items():
 assert o.type=="MESH" and o.data.users==1
 assert (len(o.data.vertices),len(o.data.polygons))==COUNTS[k]
 assert len(o.data.materials)>0 and len(o.data.uv_layers)>0
 if k!="bezel":
  r7key={"dashboard":"dashboard","cowl":"cowl","spoke":"steering_spoke","rim":"steering_rim"}[k]
  assert sig(o)==r7["changed_existing_source_derived_meshes"][r7key]["after_signature"],k
 old[k]={"object":o.name,"counts":COUNTS[k],"signature":sig(o),"matrix":mat(o)}
protected={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
old_objects=set(bpy.data.objects)
old_materials=set(bpy.data.materials)
old_images={im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}
old_cam=(bpy.context.scene.camera.name,mat(bpy.context.scene.camera))
src_tree=BVHTree.FromObject(changed["spoke"],bpy.context.evaluated_depsgraph_get())
assert all(not hole_hit(src_tree,x,z) and hole_hit(src_tree,x+1.6*d,z) for x,z,d in HOLES)
# The existing gauge-bezel object has three connected native-scene components.
# Refine the front lip of each existing component; do not invent any gauge.
bezel_islands=islands(changed["bezel"].data)
bezel_islands.sort(key=lambda ids:-len(ids))
assert sorted(map(len,bezel_islands))==[260,260,388],list(map(len,bezel_islands))
bezel_component={}
island_metrics=[]
for ix,indices in enumerate(bezel_islands):
 ys=[changed["bezel"].data.vertices[i].co.y for i in indices]
 lo,hi=min(ys),max(ys)
 assert hi-lo>.003
 for i in indices:bezel_component[i]=(lo,hi)
 island_metrics.append({"vertices":len(indices),"min_y":round(lo,7),"max_y":round(hi,7)})
result={}
for k,o in changed.items():
 inv=o.matrix_world.inverted()
 moved=0;biggest=0.;distance=0.
 for v in o.data.vertices:
  p=o.matrix_world@v.co
  dx=dy=dz=0.
  if k=="dashboard":
   # Existing original-PMT linked dash upper seam: convex shoulder around
   # the hood transitions into a recessed original cluster, preserving sides.
   ex=smooth(-.655,-.625,p.x)*(1-smooth(-.071,-.037,p.x))
   front=1-smooth(.204,.229,p.y)
   under=smooth(.834,.872,p.z)*(1-smooth(.917,.955,p.z))
   arch=math.exp(-((p.x+.35)/.235)**4)
   dz=-.0040*ex*front*under*(.38+.62*arch)
   dy=-.0021*ex*front*under*(.65+.35*arch)
  elif k=="cowl":
   # Reference Spider shows an arched padded brow rather than a long
   # ruler-straight shelf. Lower the TWO outer crowns more than its middle.
   x=abs((p.x+.35)/.285)
   shoulders=min(1.,x)**1.65
   upper=smooth(.925,.943,p.z)
   leading=1-smooth(.198,.229,p.y)
   dx=0.
   dz=-.0080*upper*leading*(.24+.76*shoulders)
   dy=-.0022*upper*leading*(.65+.35*shoulders)
  elif k=="bezel":
   # Real raised rolled bevel on existing imported-scene gauge rings.
   lo,hi=bezel_component[v.index]
   t=max(0.,min(1.,(p.y-lo)/(hi-lo)))
   lip=math.sin(math.pi*t)**2
   dy=-.0018*lip
   dz=.00052*lip*(p.z-.8252)/.086
  elif k=="spoke":
   # Original factory 3-spoke stamping, with eight genuine cut-through
   # perforations held untouched by a ray-verified safety envelope.
   x=p.x+.35
   hole_dist=min(math.hypot(p.x-hx,p.z-hz)/rad for hx,hz,rad in HOLES)
   guard=smooth(1.12,2.55,hole_dist)
   left_right=math.exp(-((p.z-.804)/.019)**4)*smooth(.043,.089,abs(x))
   lower=math.exp(-((p.z-.686)/.026)**4)*math.exp(-(x/.015)**4)
   envelope=guard*(left_right+.7*lower)
   dy=-.0017*min(1.,envelope)
  elif k=="rim":
   # Leave axis/circumference unchanged; shallow thumb-seat contour in the
   # already source-aligned wheel rim instead of a new torus.
   x=p.x+.35;z=p.z-.792
   ang=math.atan2(z,x)
   grip=math.exp(-((ang-.53)/.16)**4)+math.exp(-((ang-2.61)/.16)**4)
   dy=-.00135*grip*math.exp(-((p.y+.284)/.014)**2)
  d=Vector((dx,dy,dz))
  if d.length<.000020:continue
  v.co=inv@(p+d)
  moved+=1;biggest=max(biggest,d.length*1000);distance+=d.length
 o.data.update()
 assert moved>={"dashboard":80,"cowl":90,"bezel":160,"spoke":90,"rim":20}[k],(k,moved)
 assert biggest<9.,(k,biggest)
 assert sig(o)!=old[k]["signature"],k
 assert mat(o)==old[k]["matrix"],(k,"world transform changed")
 o["SLOTA_SOURCE_PMT"]=PMT.name
 o["SLOTA_SOURCE_SHA256"]=EXPECTED["pmt"]
 result[k]={"source_original_or_derivative_object":o.name,
  "before":old[k],"after_signature":sig(o),
  "after_counts":[len(o.data.vertices),len(o.data.polygons)],
  "vertices_moved":moved,"max_displacement_mm":round(biggest,5),
  "mean_moved_mm":round(1000*distance/moved,5)}
assert all(sig(bpy.data.objects[n])==s for n,s in protected.items())
assert set(bpy.data.objects)==old_objects and set(bpy.data.materials)==old_materials
assert {im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}==old_images
assert (bpy.context.scene.camera.name,mat(bpy.context.scene.camera))==old_cam
tree=BVHTree.FromObject(changed["spoke"],bpy.context.evaluated_depsgraph_get())
assert all(not hole_hit(tree,x,z) and hole_hit(tree,x+1.6*d,z) for x,z,d in HOLES)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
assert OUT.is_file() and OUT.stat().st_size>1000000
audit={"result":"SLOTA_R8_NATIVE_DASH_BEZEL_STEERING_GEOMETRY_SAVED",
 "slot":"A","vehicle":"daytona365","source_photo_model":"365 GTS/4 Daytona Spider LHD",
 "blender":bpy.app.version_string,"original_game_file":str(PMT),
 "original_game_sha256":EXPECTED["pmt"],"original_import_file":str(ORIG),
 "original_import_sha256":EXPECTED["import"],"exact_photo":str(PHOTO),
 "exact_photo_sha256":EXPECTED["photo"],"source_blend":SRC.name,
 "source_sha256":EXPECTED["src"],"output_blend":OUT.name,
 "output_sha256":sha(OUT),"output_bytes":OUT.stat().st_size,
 "changed_existing_meshes":result,"untouched_other_mesh_count":len(protected),
 "untouched_other_geometry_sha256":hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
 "bezel_connected_existing_components":island_metrics,
 "factory_spoke_holes":8,"same_camera_and_object_matrices":True,
 "no_new_objects_or_materials_or_textures":True,"no_external_car_edits":True,
 "no_export_or_game_integration":True,"driver_eye":"APPROX_NOT_GAME_CALIBRATED",
 "seven_exact_photo_views":"INCOMPLETE",
 "hosted_github_original_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
 "vehicle_complete":False,"advance_slot_A":False}
AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(audit["result"],json.dumps({"sha256":audit["output_sha256"],
 "changed":{k:v["vertices_moved"] for k,v in result.items()},"bytes":audit["output_bytes"]}),flush=True)

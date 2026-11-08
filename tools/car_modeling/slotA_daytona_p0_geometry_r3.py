#!/usr/bin/env python3
"""Daytona Slot A P0 r3: in-place geometric refinement of verified PMT-derived cockpit meshes.
No new objects/assets, no material/texture edits, no native/game export.
Only original-mesh-derived dashboard, gauge cowl, spoke, rim and steering shaft.
"""
import bpy, hashlib, json, math, os
from pathlib import Path
from mathutils import Vector

W=Path(os.environ["SLOT_A_WORK"])
SOURCE=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v1_r2.blend"
OUTPUT=W/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v2_r3.blend"
REPORT=W/"SLOT_A_P0_DASH_WHEEL_V2_R3.json"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
IMPORT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
EXPECTED={
 "input":"0d388f558563c2e9a92c483d6e0bfa6260a357b078d3145b87b4d2e7e7433b30",
 "pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3"}
assert bpy.app.version_string.startswith("4.5.15"),bpy.app.version_string
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert not OUTPUT.exists() and not REPORT.exists(), "never overwrite private checkpoints"
for path,key in ((SOURCE,"input"),(PMT,"pmt"),(IMPORT,"import")):
 assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==EXPECTED[key],(path,key)
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
def smooth(a,b,v):
 t=max(0.,min(1.,(v-a)/(b-a)))
 return t*t*(3.-2.*t)
def signature(ob):
 d=ob.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(f.material_index,tuple(f.vertices)) for f in d.polygons])).encode("utf-8")).hexdigest()
def matrix(ob):
 return [[round(float(v),9) for v in row] for row in ob.matrix_world]
names={
 "dashboard":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "bezel":"DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "hub":"V7_SHORT_SHAFT_AT_WHEEL_HUB"}
objects={k:bpy.data.objects[v] for k,v in names.items()}
expected_counts={"dashboard":(1885,3584),"cowl":(650,648),"bezel":(908,1344),
                 "spoke":(246,279),"rim":(1536,1536),"hub":(224,210)}
for k,ob in objects.items():
 assert ob.type=="MESH" and ob.data.users==1,(k,ob.type,ob.data.users)
 assert (len(ob.data.vertices),len(ob.data.polygons))==expected_counts[k]
 assert ob.data.uv_layers and len(ob.data.materials)>0,k
objects_before={k:{"name":ob.name,"vertices":len(ob.data.vertices),"faces":len(ob.data.polygons),
                  "signature":signature(ob),"matrix_world":matrix(ob)} for k,ob in objects.items()}
assert objects_before["dashboard"]["signature"]=="d551ee56afc8db1e5408c5f4b0a430e6bdc34aa22ea511acf8f5232a6a398f84"
assert objects_before["spoke"]["signature"]=="f64cd1f744e5245342eb4fc111eb1a55f5786ddb3d3df7e3b632bc1940dd22de"
protected={ob.name:signature(ob) for ob in bpy.data.objects if ob.type=="MESH" and ob.name not in names.values()}
all_names=set(bpy.data.objects.keys())
materials=set(bpy.data.materials.keys())
image_state={im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}
camera_matrix=matrix(bpy.context.scene.camera)
results={}
for key,ob in objects.items():
 inv=ob.matrix_world.inverted()
 n=0;peak=0.
 for vert in ob.data.vertices:
  p=ob.matrix_world@vert.co
  dx=dy=dz=0.
  if key=="dashboard":
   # Backset the instrument panel within its source-grid limits; preserve outer perimeter.
   wx=smooth(-.648,-.59,p.x)*(1.-smooth(-.145,-.088,p.x))
   wz=smooth(.719,.762,p.z)*(1.-smooth(.905,.950,p.z))
   arch=math.exp(-((p.x+.365)/.225)**4)
   dy=.0027*wx*wz*(.7+.3*arch)
   dz=.0014*wx*wz*math.exp(-((p.z-.886)/.027)**2)
  elif key=="cowl":
   # Shaped upper instrument eyebrow: thin rolled upper lip ahead of gauge plane.
   wx=smooth(-.634,-.590,p.x)*(1.-smooth(-.106,-.055,p.x))
   wz=math.exp(-((p.z-.930)/.014)**2)
   dy=-.0028*wx*wz
   dz=.00065*wx*wz*math.sin(math.pi*smooth(-.635,-.05,p.x))
  elif key=="bezel":
   # Raise the existing metal bezel front edge without altering native gauge atlas UVs.
   dy=-.00115*math.exp(-((p.y-.152)/.0034)**2)
  elif key=="spoke":
   # Small press-formed dish inside the ORIGINAL imported three-arm spoke faces.
   # These are depressions, NOT false claims of through-holes/perforations.
   left_right=(math.exp(-((abs(p.x+.35)-.106)/.020)**2)
               +.70*math.exp(-((abs(p.x+.35)-.077)/.016)**2))
   horiz=math.exp(-((p.z-.799)/.019)**2)
   lower=(math.exp(-((p.z-.708)/.021)**2)
          +.6*math.exp(-((p.z-.737)/.014)**2))
   lower*=math.exp(-((p.x+.35)/.013)**2)
   clear=smooth(.055,.090,math.hypot(p.x+.35,p.z-.792))
   dy=.00110*clear*min(1.,left_right*horiz+lower)
  elif key=="rim":
   # Refine 1970s leather rim cross-section, preserving original centre and axis.
   rx=p.x+.35; rz=p.z-.792; radius=math.hypot(rx,rz)
   if radius>1e-6:
    cross=math.exp(-((p.y+.286)/.0105)**2)
    dr=.00105*cross*math.exp(-((radius-.180)/.010)**2)
    dx=dr*rx/radius; dz=dr*rz/radius
    dy=-.00040*cross*(1.+math.cos(4.*math.atan2(rz,rx)))/2.
  elif key=="hub":
   # Existing hub-to-column neck, subtle shoulder rather than adding a new cylinder.
   w=smooth(-.268,-.253,p.y)*(1.-smooth(-.218,-.200,p.y))
   rz=p.z-.767;rx=p.x+.35
   r=math.hypot(rx,rz)
   if r>1e-6:
    d=.00095*w
    dx=d*rx/r;dz=d*rz/r
  displacement=Vector((dx,dy,dz))
  if displacement.length<.00002:continue
  vert.co=inv@(p+displacement)
  n+=1;peak=max(peak,displacement.length*1000.)
 ob.data.update()
 assert n>=({"dashboard":150,"cowl":20,"bezel":50,"spoke":10,"rim":150,"hub":30}[key]),(key,n)
 assert peak<3.2,(key,peak)
 assert signature(ob)!=objects_before[key]["signature"],"no real geometry change: "+key
 ob["SLOTA_SOURCE_PMT"]=PMT.name
 ob["SLOTA_SOURCE_SHA256"]=EXPECTED["pmt"]
 results[key]={"name":ob.name,"before":objects_before[key],
               "after_signature":signature(ob),"after_vertices":len(ob.data.vertices),
               "after_faces":len(ob.data.polygons),"moved_vertices":n,
               "maximum_displacement_mm":round(peak,4)}
for obj_name,sig in protected.items():
 assert signature(bpy.data.objects[obj_name])==sig,"protected mesh changed: "+obj_name
assert set(bpy.data.objects.keys())==all_names, "object created or removed"
assert set(bpy.data.materials.keys())==materials
assert {im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}==image_state
assert matrix(bpy.context.scene.camera)==camera_matrix
assert all(matrix(objects[k])==objects_before[k]["matrix_world"] for k in objects)
assert bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
report={"status":"SLOTA_DAYTONA_P0_R3_SOURCE_GEOMETRY_SAVED","slot":"A","car":"daytona365",
 "official_blender_version":bpy.app.version_string,"input_blend":SOURCE.name,
 "input_blend_sha256":EXPECTED["input"],"output_blend":OUTPUT.name,
 "output_blend_sha256":hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
 "output_bytes":OUTPUT.stat().st_size,
 "original_game_resource_file":PMT.name,"original_game_resource_sha256":EXPECTED["pmt"],
 "original_import_blend_file":IMPORT.name,"original_import_blend_sha256":EXPECTED["import"],
 "changed_existing_meshes":results,"protected_original_meshes_unchanged":len(protected),
 "original_object_ids_preserved":True,"meshes_external_changed":0,
 "original_read_only":True,"new_objects":0,"materials_or_textures_created":0,
 "pbr_or_normal_work":"NONE","export_ovc3_ovc_pmt":"NONE",
 "game_vr_runtime_changes":False,"photo_review":"PARTIAL_VARIANT_UNVERIFIED",
 "camera_alignment":"APPROXIMATE_NOT_GAME","p0_gate":"NEEDS_VISUAL_QA",
 "completed_24h":False,"advance_slot_a":False}
REPORT.write_text(json.dumps(report,indent=2))
print("SLOTA_DAYTONA_P0_R3_SOURCE_GEOMETRY_SAVED",json.dumps({
 "output_sha256":report["output_blend_sha256"],
 "changed":{k:[v["moved_vertices"],v["maximum_displacement_mm"]] for k,v in results.items()}}),flush=True)
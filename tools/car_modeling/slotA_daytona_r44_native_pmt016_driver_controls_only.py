#!/usr/bin/env python3
"""Daytona SLOT A R44: source-anchored PMT016 driver switch-control plate only.
No pedals/stalk fabrication, no dashboard/steering/editing outside existing 70v control panel.
"""
import array,hashlib,json,math,subprocess,sys
from pathlib import Path
R=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
BL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIGINAL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
BASE=R/"Daytona365_SlotA_OriginalPMT018_CenterConsole_R43.blend"
OUTPUT=R/"Daytona365_SlotA_OriginalPMT016_DriverControls_R44.blend"
AUDIT=R/"SLOTA_R44_DRIVER_CONTROLS_NATIVE_GEOMETRY_AUDIT.json"
REOPEN=R/"SLOTA_R44_DRIVER_CONTROLS_REOPEN_QA.json"
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/REF5_mecum_interior_03_722bdd5e4.jpg")
TARGET="DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4"
NATIVE="object00_group01_material016_a0"
EXPECTED={"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
          "import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
          "input":"27c477d18b3737e08b02276bb50a7c5afb21c97fae14ec7fff9e24f7536ef877"}
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
def gate():
 for k,p in (("pmt",PMT),("import",ORIGINAL),("input",BASE)):
  if not p.is_file() or digest(p)!=EXPECTED[k]:raise RuntimeError("BLOCKED_INPUT_SHA_"+k)
 if not BL.is_file() or not PHOTO.is_file():raise RuntimeError("BLOCKED_REFERENCE_OR_BLENDER")
def sig(o):
 m=o.data;h=hashlib.sha256()
 h.update(o.name.encode())
 for row in o.matrix_world:h.update(",".join(format(float(v),".10g") for v in row).encode())
 h.update(str((o.hide_render,o.hide_viewport)).encode())
 h.update(str(tuple(mat.name if mat else None for mat in m.materials)).encode())
 h.update(str(tuple((md.name,md.type) for md in o.modifiers)).encode())
 co=array.array("f",[0.0])*(3*len(m.vertices));m.vertices.foreach_get("co",co);h.update(co.tobytes())
 loop=array.array("i",[0])*len(m.loops);m.loops.foreach_get("vertex_index",loop);h.update(loop.tobytes())
 for layer in m.uv_layers:
  data=array.array("f",[0.0])*(2*len(layer.data));layer.data.foreach_get("uv",data)
  h.update(layer.name.encode());h.update(data.tobytes())
 return h.hexdigest()
def protected():
 import bpy
 x={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name!=TARGET}
 if len(x)!=112:raise RuntimeError("BLOCKED_OTHER_MESH_COUNT_"+str(len(x)))
 return x
def native():
 import bpy
 with bpy.data.libraries.load(str(ORIGINAL),link=False) as (src,dst):
  if NATIVE not in src.objects:raise RuntimeError("BLOCKED_ORIGINAL_PMT016_MISSING")
  dst.objects=[NATIVE]
 o=dst.objects[0]
 if not o or len(o.data.vertices)!=10 or len(o.data.polygons)!=6:raise RuntimeError("BLOCKED_NATIVE_PMT016_TOPOLOGY")
 pts=[tuple(float((o.matrix_world@v.co)[j]) for j in range(3)) for v in o.data.vertices]
 bpy.data.objects.remove(o,do_unlink=True)
 return pts
def build():
 import bpy
 from mathutils import Vector
 gate()
 if not bpy.app.version_string.startswith("4.5.15") or Path(bpy.data.filepath).resolve()!=BASE.resolve():raise RuntimeError("BLOCKED_BLENDER_INPUT_SCENE")
 if any(x.exists() for x in (OUTPUT,AUDIT,REOPEN)):raise RuntimeError("BLOCKED_OUTPUT_ALREADY_EXISTS")
 names=sorted(o.name for o in bpy.data.objects)
 before=protected()
 o=bpy.data.objects.get(TARGET)
 if not o or o.type!="MESH" or (len(o.data.vertices),len(o.data.polygons))!=(70,96):raise RuntimeError("BLOCKED_SOURCE_DERIVATIVE_MISSING")
 before_target=sig(o);material=tuple(m.name if m else None for m in o.data.materials)
 layer_names=tuple(l.name for l in o.data.uv_layers)
 points=native()
 # First ten SOURCE-DERIVED corner positions preserve the ten genuine PMT016 XY/Z source points.
 # Prior V4 scene has front-face 6 mm ahead of native PMT; restore native anchor plane.
 offsets=[]
 for i,p in enumerate(points):
  world=o.matrix_world@o.data.vertices[i].co
  if abs(world.x-p[0])>0.00016 or abs(world.z-p[2])>0.00016:raise RuntimeError("BLOCKED_PMT016_ANCHOR_XZ_"+str(i))
  offs=p[1]-float(world.y)
  if not .005<offs<.007:raise RuntimeError("BLOCKED_PMT016_ANCHOR_Y_"+str(i))
  offsets.append(offs)
 matrix=o.matrix_world.inverted().to_3x3()
 changed=[];max_d=0.;min_d=1.
 for v in o.data.vertices:
  p=o.matrix_world@v.co
  # Additional recessed curvature ONLY on already existing subdivision vertices.
  # Original ten surface control vertices remain precisely on native PMT016 geometry.
  if v.index<10:delta=offsets[v.index]
  else:
   if float(p.y)<.20:
    zx=min(1.,max(0.,(float(p.z)-.73160)/(.84727-.73160)))
    lateral=max(0.,1.-(float(p.x)/.075)**2)
    recess=.008*math.sin(math.pi*zx)*lateral
   else:
    zx=min(1.,max(0.,(float(p.z)-.58656)/(.73422-.58656)))
    lateral=max(0.,1.-(float(p.x)/.14203)**2)
    recess=.007*math.sin(math.pi*zx)*lateral
   delta=.006+recess
  if delta<=.004:continue
  # World Y-only original-source anchored displacement, zero new vertices/faces.
  v.co+=matrix@Vector((0.,delta,0.))
  changed.append({"vertex":v.index,"world_y_before":round(float(p.y),7),"delta_y_m":round(delta,7)})
  max_d=max(max_d,delta);min_d=min(min_d,delta)
 o.data.update()
 if len(changed)!=70 or max_d<.011 or max_d>.016:raise RuntimeError("BLOCKED_EDIT_MATERIALITY_"+str((len(changed),max_d)))
 if sig(o)==before_target:raise RuntimeError("BLOCKED_NO_CHANGE")
 if tuple(m.name if m else None for m in o.data.materials)!=material or tuple(l.name for l in o.data.uv_layers)!=layer_names:raise RuntimeError("BLOCKED_TARGET_MATERIAL_UV")
 if names!=sorted(o.name for o in bpy.data.objects) or before!=protected():raise RuntimeError("BLOCKED_OTHER_PART_MODIFIED")
 # Validate original source corner coordinates in world space after edit.
 for i,p in enumerate(points):
  q=o.matrix_world@o.data.vertices[i].co
  if max(abs(q[k]-p[k]) for k in range(3))>.00017:raise RuntimeError("BLOCKED_ORIGINAL_PMT016_CORNER_ALIGN")
 after=sig(o)
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
 if not OUTPUT.is_file() or OUTPUT.stat().st_size<1000000:raise RuntimeError("BLOCKED_BLENDER_OUTPUT")
 audit={"task_id":"FERRARI16-SLOTA-DAYTONA-DRIVER-CONTROLS-SWITCHBANK-PMT016-R44-20261109",
 "slot":"A","car_id":"daytona365","component":"driver_controls","covered_subpart":"existing original-PMT016-derived slider/toggle switch housing",
 "blocked_subparts":["original standalone pedal mesh attribution unproven","original stalk mesh attribution unproven"],
 "native_object":NATIVE,"target_existing_original_source_derived_mesh":TARGET,
 "original_native_pmt_sha256":EXPECTED["pmt"],"original_import_blend_sha256":EXPECTED["import"],
 "input_r43_blend_sha256":EXPECTED["input"],"output_r44_blend_sha256":digest(OUTPUT),
 "native_anchor_count":10,"native_face_count":6,"original_derived_target_vertices":70,"faces":96,
 "moved_existing_vertices":len(changed),"max_displacement_m":max_d,"minimum_displacement_m":min_d,
 "target_before_signature":before_target,"target_after_signature":after,"protected_112_signatures":before,
 "photo_switch_controls_sha256":digest(PHOTO),"native_anchor_xyz":points,"changed_vertices":changed,
 "new_objects":0,"new_meshes":0,"new_materials":0,"new_textures":0,"PMT_OVC_OVC3_exports":0,
 "dashboard_steering_meshes_untouched":True,"car_qa_pass":False,"next_region":"inner_door"}
 AUDIT.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf8")
 print("R44_DRIVER_CONTROLS_SAVED",json.dumps({"moved":len(changed),"max_m":max_d,"out_sha":audit["output_r44_blend_sha256"]}),flush=True)
def verify():
 import bpy
 gate()
 if Path(bpy.data.filepath).resolve()!=OUTPUT.resolve() or not AUDIT.is_file():raise RuntimeError("BLOCKED_INDEPENDENT_REOPEN_MISSING")
 a=json.loads(AUDIT.read_text())
 if digest(OUTPUT)!=a["output_r44_blend_sha256"]:raise RuntimeError("BLOCKED_OUTPUT_SHA_MISMATCH")
 if sig(bpy.data.objects[TARGET])!=a["target_after_signature"]:raise RuntimeError("BLOCKED_EDIT_REOPEN_DRIFT")
 if protected()!=a["protected_112_signatures"]:raise RuntimeError("BLOCKED_UNRELATED_112_MESH_DRIFT")
 proof={"result":"PASS_FRESH_OFFICIAL_BLENDER_REOPEN","new_scene_sha256":a["output_r44_blend_sha256"],
  "native_source_object":NATIVE,"edited_existing_original_derived_mesh":TARGET,"protected_112_meshes":True,
  "coverage_state":"COVERED_PARTIAL_QA","car_QA_PASS":False,"next":"inner_door"}
 REOPEN.write_text(json.dumps(proof,indent=2)+"\n",encoding="utf8")
 print("R44_DRIVER_CONTROLS_REOPEN_PASS",json.dumps(proof),flush=True)
def main():
 if "--inside-build" in sys.argv:build();return
 if "--inside-verify" in sys.argv:verify();return
 gate()
 for stage in ("--inside-build","--inside-verify"):
  f=BASE if stage=="--inside-build" else OUTPUT
  p=subprocess.run([str(BL),"--background",str(f),"--threads","1","--python",str(Path(__file__).resolve()),"--",stage],capture_output=True,text=True,timeout=180)
  print((p.stdout+"\n"+p.stderr)[-5000:],flush=True)
  if p.returncode:raise RuntimeError("BLOCKED_BLENDER_"+stage+":"+str(p.returncode))
if __name__=="__main__":main()
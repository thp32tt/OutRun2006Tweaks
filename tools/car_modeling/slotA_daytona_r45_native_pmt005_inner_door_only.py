#!/usr/bin/env python3
"""SLOT A Daytona R45 native-PMT005-guided front-left inner door reshape only.

Use existing original-derived door panel geometry. Do not generate/append faces,
door hardware, steering, dashboard, materials, texture or game exports.
"""
import array,hashlib,json,math,subprocess,sys
from pathlib import Path
R=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
BL=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
INPUT=R/"Daytona365_SlotA_OriginalPMT016_DriverControls_R44.blend"
OUTPUT=R/"Daytona365_SlotA_OriginalPMT005_InnerDoor_R45.blend"
AUDIT=R/"SLOTA_R45_INNER_DOOR_PMT005_GEOMETRY_AUDIT.json"
REOPEN=R/"SLOTA_R45_INNER_DOOR_REOPEN_QA.json"
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/REF5_mecum_interior_04_1f06efa94.jpg")
NATIVE="object00_group01_material005_a0"
TARGET="V5_L_LEATHER_SCULPTED_DOOR"
EXPECTED={"pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
 "import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
 "input":"638f69369f9ff9d074221320f38f4e137675a911d05939470f6cd24bec73040d"}
TASK_ID="FERRARI16-SLOTA-DAYTONA-R45-NATIVE-PMT005-INNER-DOOR-20261109"
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()
def gate():
 for key,p in (("pmt",PMT),("import",ORIG),("input",INPUT)):
  if not p.is_file() or digest(p)!=EXPECTED[key]:raise RuntimeError("BLOCKED_INPUT_SHA:"+key)
 if not PHOTO.is_file() or not BL.is_file():raise RuntimeError("BLOCKED_BLENDER_OR_AUTHENTIC_PHOTO")
def sig(o):
 m=o.data;h=hashlib.sha256()
 h.update(o.name.encode())
 for row in o.matrix_world:
  h.update(",".join(format(float(v),".10g") for v in row).encode())
 h.update(str((o.hide_render,o.hide_viewport)).encode())
 h.update(str(tuple(x.name if x else None for x in m.materials)).encode())
 h.update(str(tuple((x.name,x.type) for x in o.modifiers)).encode())
 a=array.array("f",[0.0])*(len(m.vertices)*3);m.vertices.foreach_get("co",a);h.update(a.tobytes())
 a=array.array("i",[0])*len(m.loops);m.loops.foreach_get("vertex_index",a);h.update(a.tobytes())
 for layer in m.uv_layers:
  a=array.array("f",[0.0])*(len(layer.data)*2);layer.data.foreach_get("uv",a)
  h.update(layer.name.encode());h.update(a.tobytes())
 return h.hexdigest()
def protected():
 import bpy
 p={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name!=TARGET}
 if len(p)!=112:raise RuntimeError("BLOCKED_PROTECTED_COUNT:"+str(len(p)))
 return p
def native_profile():
 import bpy
 with bpy.data.libraries.load(str(ORIG),link=False) as (source,dest):
  if NATIVE not in source.objects:raise RuntimeError("BLOCKED_NATIVE_PMT005_ABSENT")
  dest.objects=[NATIVE]
 o=dest.objects[0]
 if (len(o.data.vertices),len(o.data.polygons))!=(3459,3536):
  raise RuntimeError("BLOCKED_NATIVE_TOPOLOGY")
 pts=[o.matrix_world@v.co for v in o.data.vertices]
 # Front leading door edge, PMT005 actual vertex index -> source coordinate assertions.
 inds=[982,980,979,977,239,240,241]
 truth=[(-.85972,.30208,.64536),(-.85787,.29359,.68692),
        (-.85283,.27800,.72728),(-.84275,.25736,.76594),
        (-.82675,.23607,.79518),(-.80451,.21549,.82407),
        (-.77562,.18531,.84385)]
 profile=[]
 for ix,q in zip(inds,truth):
  p=pts[ix];xyz=tuple(float(p[j]) for j in range(3))
  if max(abs(xyz[j]-q[j]) for j in range(3))>.00020:
   raise RuntimeError("BLOCKED_NATIVE_DOOR_SOURCE_INDEX:"+str((ix,xyz,q)))
  profile.append({"vertex":ix,"xyz":xyz})
 bpy.data.objects.remove(o,do_unlink=True)
 return profile
def src_x(z,profile):
 p=sorted([(r["xyz"][2],r["xyz"][0]) for r in profile])
 for (za,xa),(zb,xb) in zip(p,p[1:]):
  if za<=z<=zb:
   t=(z-za)/(zb-za);return xa+(xb-xa)*t
 return None
def build():
 import bpy
 from mathutils import Vector
 gate()
 if not bpy.app.version_string.startswith("4.5.15") or Path(bpy.data.filepath).resolve()!=INPUT.resolve():
  raise RuntimeError("BLOCKED_NOT_OFFICIAL_BLENDER_OR_INPUT")
 if any(p.exists() for p in (OUTPUT,AUDIT,REOPEN)):raise RuntimeError("BLOCKED_IMMUTABLE_R45_EXISTS")
 allnames=sorted(o.name for o in bpy.data.objects)
 protected_before=protected()
 o=bpy.data.objects.get(TARGET)
 if not o or o.type!="MESH" or (len(o.data.vertices),len(o.data.polygons))!=(465,840):
  raise RuntimeError("BLOCKED_EXISTING_ORIGINAL_DERIVED_DOOR")
 before=sig(o)
 native=native_profile()
 mat=tuple(x.name if x else None for x in o.data.materials)
 uv=tuple(l.name for l in o.data.uv_layers)
 inv=o.matrix_world.inverted().to_3x3()
 changes=[];max_offset=0.
 for v in o.data.vertices:
  world=o.matrix_world@v.co
  x,y,z=tuple(float(world[j]) for j in range(3))
  if not (.64<=z<=.845 and -.02<y<.44):continue
  sx=src_x(z,native)
  if sx is None:continue
  # Keep panel 30mm INSIDE original PMT body edge to prevent replacing outer body.
  # Correct over-straight front upper shoulder only, guided by native edge curvature.
  target_x=sx+.030
  missing=max(0.,x-target_x)
  if missing<.002:continue
  taper_a=min(1.,max(0.,(y+.02)/.18))
  taper_b=min(1.,max(0.,(.44-y)/.12))
  weight=taper_a*taper_b
  delta=max(-.023,min(0.,-.84*missing*weight))
  if abs(delta)<.001:continue
  v.co+=inv@Vector((delta,0,0))
  changes.append({"i":v.index,"old_x":round(x,6),"new_x":round(float((o.matrix_world@v.co).x),6),
                  "source_x":round(sx,6),"y":round(y,5),"z":round(z,5)})
  max_offset=max(max_offset,abs(delta))
 o.data.update()
 if not (12<=len(changes)<=150 and .009<=max_offset<=.0231):
  raise RuntimeError("BLOCKED_NOT_MATERIAL:"+str((len(changes),max_offset)))
 if tuple(x.name if x else None for x in o.data.materials)!=mat or tuple(l.name for l in o.data.uv_layers)!=uv:
  raise RuntimeError("BLOCKED_TARGET_UV_OR_MATERIAL")
 if sorted(x.name for x in bpy.data.objects)!=allnames or protected_before!=protected():
  raise RuntimeError("BLOCKED_OTHER_112_MESH_MUTATED")
 after=sig(o)
 if before==after:raise RuntimeError("BLOCKED_NO_VERTICES_CHANGED")
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
 if not OUTPUT.is_file() or OUTPUT.stat().st_size<1_000_000:raise RuntimeError("BLOCKED_OUTPUT_SAVE")
 audit={"task_id":TASK_ID,"slot":"A","car":"daytona365","component":"inner_door","status":"COVERED_PARTIAL_QA",
 "native_original_object":NATIVE,"original_mesh_vf":[3459,3536],
 "actual_edited_existing_original_derived_mesh":TARGET,"target_vf":[465,840],
 "native_source_front_edge_7_vertices":native,
 "moved_existing_vertices":len(changes),"max_world_x_displacement_m":max_offset,
 "changed_vertices":changes,"target_before_sig":before,"target_after_sig":after,
 "protected_other_112_signatures":protected_before,
 "pmt_sha256":EXPECTED["pmt"],"original_import_sha256":EXPECTED["import"],
 "input_r44_sha256":EXPECTED["input"],"new_r45_sha256":digest(OUTPUT),
 "matched_real_reference_photo":PHOTO.name,"photo_sha256":digest(PHOTO),
 "new_geometry_objects":0,"new_materials":0,"new_textures_or_pbr":0,"PMT_OVC_OVC3_exports":0,
 "car_qa_pass":False,"next_region":"windshield_frame","unresolved":["driver_eye_not_calibrated",
 "same_camera_photo_vs_blender_comparison_not_certified","seven_authenticated_views_not_complete"]}
 AUDIT.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf8")
 print("R45_INNER_DOOR_SOURCE_GEOMETRY_SAVED",json.dumps({"moved":len(changes),"max_displacement_m":max_offset,"sha":audit["new_r45_sha256"]}),flush=True)
def verify():
 import bpy
 gate()
 if Path(bpy.data.filepath).resolve()!=OUTPUT.resolve() or not AUDIT.is_file():
  raise RuntimeError("BLOCKED_INDEPENDENT_REOPEN_INPUT")
 audit=json.loads(AUDIT.read_text())
 if digest(OUTPUT)!=audit["new_r45_sha256"]:raise RuntimeError("BLOCKED_REOPEN_SHA")
 if protected()!=audit["protected_other_112_signatures"]:raise RuntimeError("BLOCKED_REOPEN_OTHER_MESH_DRIFT")
 if sig(bpy.data.objects[TARGET])!=audit["target_after_sig"]:raise RuntimeError("BLOCKED_REOPEN_TARGET_DRIFT")
 if (len(bpy.data.objects[TARGET].data.vertices),len(bpy.data.objects[TARGET].data.polygons))!=(465,840):
  raise RuntimeError("BLOCKED_TOPOLOGY_CHANGED")
 proof={"result":"PASS_INDEPENDENT_BLENDER_4_5_15_SAVE_REOPEN","scene_sha256":audit["new_r45_sha256"],
   "edited_original_derived_mesh":TARGET,"moved_vertices":audit["moved_existing_vertices"],
   "protected_other_112_meshes":"INVARIANT","coverage":"COVERED_PARTIAL_QA",
   "whole_car_qa":"NOT_PASS","next":"windshield_frame"}
 REOPEN.write_text(json.dumps(proof,indent=2)+"\n",encoding="utf8")
 print("R45_SOURCE_DOOR_REOPEN_PASS",json.dumps(proof),flush=True)
def main():
 if "--inside-build" in sys.argv:build();return
 if "--inside-verify" in sys.argv:verify();return
 gate()
 for stage in ("--inside-build","--inside-verify"):
  f=INPUT if stage=="--inside-build" else OUTPUT
  p=subprocess.run([str(BL),"--background",str(f),"--threads","1",
      "--python",str(Path(__file__).resolve()),"--",stage],capture_output=True,text=True,timeout=200)
  print((p.stdout+"\n"+p.stderr)[-6500:],flush=True)
  if p.returncode:raise RuntimeError("BLOCKED_BLENDER_STAGE:"+stage+":"+str(p.returncode))
if __name__=="__main__":main()
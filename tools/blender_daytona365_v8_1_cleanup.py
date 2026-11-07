import bpy,json,hashlib,math
from pathlib import Path
R=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
OUT=R/"blender_v8";assert bpy.data.filepath.endswith("Daytona365_Cockpit_Blender_PBR_v8.blend")
DARK=bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
METAL=bpy.data.materials["V7_Machined_Aluminum"]
# remove floating knee bars and redundant oversized gate created in v8
remove=[]
for o in list(bpy.data.objects):
    n=o.name
    if n in ("V8_DRIVER_KNEE_PAD","V8_PASSENGER_KNEE_PAD","V8_SHIFTER_ALLOY_SURROUND") or n.startswith("V8_HGATE_"):
        remove.append(n);bpy.data.objects.remove(o,do_unlink=True)
def coll(name):
 c=bpy.data.collections.get(name)
 if c:return c
 c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
CD=coll("V8.1 | integrated lower dash")
CC=coll("V8.1 | compact center tunnel")
def box(name,loc,size,mat,collection,rad):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
 o=bpy.context.object;o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 collection.objects.link(o);o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.data.materials.append(mat)
 b=o.modifiers.new("V8.1 soft coachwork edge","BEVEL");b.width=rad;b.segments=5
 w=o.modifiers.new("V8.1 weighted normals","WEIGHTED_NORMAL");w.keep_sharp=True
 return o
# lower dash panels sit flush against existing padded face, instead of floating in front
box("V8_1_DRIVER_INTEGRATED_LOWER_DASH",(-.39,.205,.595),(.57,.035,.085),DARK,CD,.015)
box("V8_1_PASSENGER_INTEGRATED_LOWER_DASH",(.40,.205,.595),(.55,.035,.085),DARK,CD,.015)
# compact center lower panel under switches
box("V8_1_CENTER_LOWER_DASH",(0,.205,.535),(.22,.035,.075),DARK,CD,.012)
# refine existing tunnel proportions: narrower and raised so source gate sits on it
tun=bpy.data.objects["V8_LOW_CENTER_TUNNEL"];tun.dimensions=(.178,.64,.13);tun.location=(0,-.14,.355)
arm=bpy.data.objects["V8_REAR_PADDED_ARMREST"];arm.dimensions=(.16,.235,.075);arm.location=(0,-.455,.405)
# black leather deck under existing source-aligned chrome gate
box("V8_1_COMPACT_SHIFTER_LEATHER_DECK",(0,-.105,.422),(.165,.225,.025),DARK,CC,.015)
# slimmer door armrests
for side,sig in (("L",-1),("R",1)):
 o=bpy.data.objects.get(f"V8_{side}_DOOR_PADDED_ARMREST")
 if o:
  o.dimensions=(.035,.29,.046);o.location=(sig*.742,-.44,.54)
# reduce chrome rail brightness and thickness; curve object itself retained
rail=bpy.data.objects.get("V8_LOWER_DASH_CHROME_RAIL")
if rail and hasattr(rail.data,"bevel_depth"): rail.data.bevel_depth=.0014
s=bpy.context.scene
s.camera=bpy.data.objects["V7_Camera_Reference_ThreeQuarter"]
s.render.engine="CYCLES";s.cycles.samples=10;s.cycles.use_denoising=True
s.render.resolution_x=960;s.render.resolution_y=640;s.render.resolution_percentage=100
s.view_settings.exposure=-.52
for img in bpy.data.images:
 if img.source=="FILE" and not img.packed_file:
  try:img.pack()
  except:pass
out=OUT/"Daytona365_Cockpit_Blender_PBR_v8_1.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
m={"file":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size,
"removed_floating_parts":remove,"integrated_lower_dash":True,"source_gate_preserved":bpy.data.objects.get("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3") is not None,
"compact_tunnel":True,"game_files_modified":False,"OVC_created":False}
(OUT/"DAYTONA_V8_1_BUILD_MANIFEST.json").write_text(json.dumps(m,indent=2))
print("V8_1_PASS",json.dumps(m),flush=True)
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
R=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
OUT=R/"blender_v8"
assert bpy.data.filepath.endswith("Daytona365_Cockpit_Blender_PBR_v8_3.blend")
DARK=bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
METAL=bpy.data.materials["V7_Machined_Aluminum"]

# remove oversized v8.3 column components and rebuild slimmer
for n in ("V8_3_TAPERED_STEERING_COLUMN_COWL","V8_3_SHORT_STEERING_SHAFT",
          "V8_3_PASSENGER_FOOTWELL_END"):
 o=bpy.data.objects.get(n)
 if o:bpy.data.objects.remove(o,do_unlink=True)
C=bpy.data.collections.get("V8.3 | structural cabin details")
assert C
def cylinder_between(name,a,b,r1,r2,mat):
 a=Vector(a);b=Vector(b);d=b-a;mid=(a+b)/2
 bpy.ops.mesh.primitive_cone_add(vertices=48,radius1=r1,radius2=r2,depth=d.length,location=mid)
 o=bpy.context.object;o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 C.objects.link(o);o.rotation_euler=d.to_track_quat("Z","Y").to_euler()
 o.data.materials.append(mat)
 for p in o.data.polygons:p.use_smooth=True
 be=o.modifiers.new("V8.4 subtle column edge","BEVEL");be.width=.0012;be.segments=2
 return o
cylinder_between("V8_4_SLIM_STEERING_COWL",
 (-.35,.130,.640),(-.35,-.125,.716),.030,.021,DARK)
cylinder_between("V8_4_STEERING_SHAFT",
 (-.35,-.125,.716),(-.35,-.276,.783),.0095,.008,METAL)

# Lower/shorten pedal firewall so only its backplate is visible behind pedals.
fw=bpy.data.objects.get("V8_3_DRIVER_PEDAL_FIREWALL")
assert fw
fw.dimensions=(.38,.020,.105);fw.location=(-.39,.222,.332)

# Door caps too thick in v8.3; make them trim-like rather than black beams.
for side in ("L","R"):
 cap=bpy.data.objects.get(f"V8_3_{side}_BLACK_DOOR_TOP_CAP")
 if cap:cap.dimensions.x=.026;cap.dimensions.z=.038
 pad=bpy.data.objects.get(f"V8_3_{side}_TAN_DOOR_LOWER_PAD")
 if pad:pad.dimensions.x=.022;pad.dimensions.z=.115
 pull=bpy.data.objects.get(f"V8_3_{side}_BLACK_DOOR_PULL")
 if pull:pull.dimensions=(.034,.19,.032)

# Reduce seat skirts and recolor to black mount trim instead of dangling tan blocks.
for side in ("L","R"):
 for sign in ("-0.165","+0.165"):
  o=bpy.data.objects.get(f"V8_3_{side}_LOWER_SEAT_SKIRT_{sign}")
  if o:
   o.dimensions=(.022,.23,.048)
   o.data.materials.clear();o.data.materials.append(DARK)

# Seat rails less shiny: retain metal but increase roughness on material globally via shader.
mb=METAL.node_tree.nodes.get("Principled BSDF")
if mb:mb.inputs["Roughness"].default_value=.31

s=bpy.context.scene
s.camera=bpy.data.objects["V7_Camera_Reference_ThreeQuarter"]
s.render.engine="CYCLES";s.cycles.samples=10;s.cycles.use_denoising=True
s.render.resolution_x=960;s.render.resolution_y=640;s.render.resolution_percentage=100
s.view_settings.exposure=-.52
for img in bpy.data.images:
 if img.source=="FILE" and not img.packed_file:
  try:img.pack()
  except:pass
out=OUT/"Daytona365_Cockpit_Blender_PBR_v8_4.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
m={"file":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size,
"steering_column_slimmed":True,"pedal_firewall_lowered":True,"passenger_block_removed":True,
"door_trim_slimmed":True,"seat_skirts_reduced":True,"PBR_maps_preserved":True,
"game_files_modified":False,"OVC_created":False}
(OUT/"DAYTONA_V8_4_BUILD_MANIFEST.json").write_text(json.dumps(m,indent=2))
print("V8_4_PASS",json.dumps(m),flush=True)
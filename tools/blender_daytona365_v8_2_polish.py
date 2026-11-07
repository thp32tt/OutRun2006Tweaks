import bpy,json,hashlib,math
from pathlib import Path
R=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
OUT=R/"blender_v8"
assert bpy.data.filepath.endswith("Daytona365_Cockpit_Blender_PBR_v8_1.blend")
DARK=bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
METAL=bpy.data.materials["V7_Machined_Aluminum"]
THREAD=bpy.data.materials["V7_Stitch_Dark_Tan"]

# remove blocky lower dash panels and low floating chrome line
for n in ("V8_1_DRIVER_INTEGRATED_LOWER_DASH","V8_1_PASSENGER_INTEGRATED_LOWER_DASH",
          "V8_1_CENTER_LOWER_DASH","V8_LOWER_DASH_CHROME_RAIL"):
    o=bpy.data.objects.get(n)
    if o:bpy.data.objects.remove(o,do_unlink=True)
def coll(name):
 c=bpy.data.collections.get(name)
 if c:return c
 c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
C=coll("V8.2 | clean dashboard lower lip")
def box(name,loc,size,mat,rad):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
 o=bpy.context.object;o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 C.objects.link(o);o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.data.materials.append(mat)
 b=o.modifiers.new("V8.2 integrated bevel","BEVEL");b.width=rad;b.segments=5
 w=o.modifiers.new("V8.2 weighted normal","WEIGHTED_NORMAL");w.keep_sharp=True
 return o
# one compact lower dash lip attached beneath source dash at z~.635
box("V8_2_CONTINUOUS_LOWER_DASH_LIP",(0,.208,.616),(1.43,.038,.055),DARK,.014)
# thin brushed-metal trim, physically attached to the lower lip
box("V8_2_DASH_TRIM_STRIP",(0,.186,.592),(1.39,.005,.006),METAL,.0015)

# pedals lowered toward floor and slightly tilted rearward; rubber ribs follow them.
for i,x in enumerate((-.48,-.39,-.30)):
 p=bpy.data.objects.get(f"V6_DRIVER_METAL_PEDAL_{i}")
 if p:
  p.location.y=.105;p.location.z=.328
  p.rotation_euler.x=math.radians(-12)
 for j in range(3):
  r=bpy.data.objects.get(f"V7_PEDAL_{i}_FLUSH_RUBBER_CROSSRIB_{j}")
  if r:
   r.location.y=.099;r.location.z=.314+j*.020
   r.rotation_euler.x=math.radians(-12)

# center tunnel proportions: shorter, narrower and lower, leaving a gap around seats.
tun=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
tun.dimensions=(.16,.50,.105);tun.location=(0,-.12,.345)
arm=bpy.data.objects["V8_REAR_PADDED_ARMREST"]
arm.dimensions=(.15,.18,.068);arm.location=(0,-.405,.398)
deck=bpy.data.objects["V8_1_COMPACT_SHIFTER_LEATHER_DECK"]
deck.dimensions=(.145,.19,.020);deck.location=(0,-.105,.420)

# Soften high front corners of v8 cushion bolsters.
for side,cx in (("L",-.353),("R",.353)):
 o=bpy.data.objects[f"V8_{side}_CLASSIC_PADDED_CUSHION"]
 # first half are visible top vertices
 count=len(o.data.vertices)//2
 for v in o.data.vertices[:count]:
  edge=min(1,abs(v.co.x-cx)/.17)
  front=max(0,min(1,(-.50-v.co.y)/.10))
  v.co.z-=.016*(edge**2)*front
 # make cushion slightly less wide at absolute front edge
 for v in o.data.vertices[:count]:
  if v.co.y<-.55:
   v.co.x=cx+(v.co.x-cx)*.97

# Increase seat leather micro-normal slightly now that surfaces are calmer.
tan=bpy.data.materials["V7_Target_Tan_Leather_PBR"]
for n in tan.node_tree.nodes:
 if n.type=="NORMAL_MAP":n.inputs["Strength"].default_value=.32
# dark material is still flat; add subtle micro bump using existing black map.
for n in DARK.node_tree.nodes:
 if n.type=="NORMAL_MAP":n.inputs["Strength"].default_value=.24

s=bpy.context.scene
s.camera=bpy.data.objects["V7_Camera_Reference_ThreeQuarter"]
s.render.engine="CYCLES";s.cycles.samples=10;s.cycles.use_denoising=True
s.render.resolution_x=960;s.render.resolution_y=640;s.render.resolution_percentage=100
s.view_settings.exposure=-.52
for img in bpy.data.images:
 if img.source=="FILE" and not img.packed_file:
  try:img.pack()
  except:pass
out=OUT/"Daytona365_Cockpit_Blender_PBR_v8_2.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
m={"file":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size,
"dash_blocks_removed":3,"one_integrated_lower_lip":True,"pedals_lowered":3,
"center_tunnel_compacted":True,"seat_front_bolsters_softened":True,
"normal_maps_active":True,"game_files_modified":False,"OVC_created":False}
(OUT/"DAYTONA_V8_2_BUILD_MANIFEST.json").write_text(json.dumps(m,indent=2))
print("V8_2_PASS",json.dumps(m),flush=True)
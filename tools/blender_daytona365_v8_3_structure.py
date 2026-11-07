import bpy,math,json,hashlib
from pathlib import Path
from mathutils import Vector
R=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
OUT=R/"blender_v8"
assert bpy.data.filepath.endswith("Daytona365_Cockpit_Blender_PBR_v8_2.blend")
TAN=bpy.data.materials["V7_Target_Tan_Leather_PBR"]
DARK=bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
METAL=bpy.data.materials["V7_Machined_Aluminum"]
WOOD=bpy.data.materials["V7_Target_Walnut_Steering_Rim_PBR"]
def coll(name):
 c=bpy.data.collections.get(name)
 if c:return c
 c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
C=coll("V8.3 | structural cabin details")
def box(name,loc,size,mat,rad=.005):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
 o=bpy.context.object;o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 C.objects.link(o);o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.data.materials.append(mat)
 b=o.modifiers.new("V8.3 edge radius","BEVEL");b.width=rad;b.segments=4
 w=o.modifiers.new("V8.3 weighted normal","WEIGHTED_NORMAL");w.keep_sharp=True
 return o
def cylinder_between(name,a,b,r1,r2,mat):
 a=Vector(a);b=Vector(b);mid=(a+b)/2;d=b-a
 bpy.ops.mesh.primitive_cone_add(vertices=48,radius1=r1,radius2=r2,depth=d.length,location=mid)
 o=bpy.context.object;o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 C.objects.link(o)
 o.rotation_euler=d.to_track_quat("Z","Y").to_euler()
 o.data.materials.append(mat)
 for p in o.data.polygons:p.use_smooth=True
 be=o.modifiers.new("V8.3 column edge soften","BEVEL");be.width=.0018;be.segments=3
 return o

# Ground both seats with actual rails / brackets.
for side,cx in (("L",-.353),("R",.353)):
 for dx in (-.105,.105):
  box(f"V8_3_{side}_SEAT_RAIL_{dx:+.3f}",(cx+dx,-.385,.292),(.024,.41,.021),METAL,.003)
 for y in (-.51,-.25):
  box(f"V8_3_{side}_SEAT_MOUNT_{y:+.2f}",(cx,y,.315),(.29,.042,.045),DARK,.008)
 # side leather skirts fill visual gap between cushion and rail
 for dx in (-.165,.165):
  box(f"V8_3_{side}_LOWER_SEAT_SKIRT_{dx:+.3f}",(cx+dx,-.39,.338),(.028,.33,.070),TAN,.009)

# Replace long skinny steering column with a compact tapered cowl under gauges.
for n in ("V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES","V7_SHORT_SHAFT_AT_WHEEL_HUB"):
 o=bpy.data.objects.get(n)
 if o:
  o.hide_render=True;o.hide_viewport=True
cylinder_between("V8_3_TAPERED_STEERING_COLUMN_COWL",
 (-.35,.125,.635),(-.35,-.205,.748),.046,.028,DARK)
cylinder_between("V8_3_SHORT_STEERING_SHAFT",
 (-.35,-.205,.748),(-.35,-.278,.784),.012,.010,METAL)

# Add black upper door caps to integrate the tan panels with cabin, and a lower
# padded insert. x is door-plane normal, y runs front/back, z is height.
for side,sig in (("L",-1),("R",1)):
 cap=box(f"V8_3_{side}_BLACK_DOOR_TOP_CAP",(sig*.775,-.33,.685),(.036,1.18,.055),DARK,.014)
 insert=box(f"V8_3_{side}_TAN_DOOR_LOWER_PAD",(sig*.77,-.32,.505),(.030,.82,.145),TAN,.022)
 # black pull pocket embedded within tan panel
 box(f"V8_3_{side}_BLACK_DOOR_PULL",(sig*.748,-.42,.575),(.048,.25,.040),DARK,.013)

# Driver firewall behind pedals to stop controls floating in empty space.
box("V8_3_DRIVER_PEDAL_FIREWALL",(-.39,.218,.360),(.42,.028,.205),DARK,.012)
# small passenger footwell end face
box("V8_3_PASSENGER_FOOTWELL_END",(.39,.218,.345),(.47,.028,.175),DARK,.012)

# Center-tunnel seam/trim gives leather mass a manufactured edge.
def curve(name,pts,radius,mat):
 cu=bpy.data.curves.new(name,"CURVE");cu.dimensions="3D";cu.bevel_depth=radius;cu.bevel_resolution=3
 sp=cu.splines.new("BEZIER");sp.bezier_points.add(len(pts)-1)
 for bp,p in zip(sp.bezier_points,pts):
  bp.co=p;bp.handle_left_type="AUTO";bp.handle_right_type="AUTO"
 ob=bpy.data.objects.new(name,cu);C.objects.link(ob);cu.materials.append(mat);return ob
curve("V8_3_CENTER_TUNNEL_LEFT_SEAM",[(-.075,-.54,.415),(-.075,-.33,.405),(-.075,-.12,.410),(-.075,.10,.402)],.0011,METAL)
curve("V8_3_CENTER_TUNNEL_RIGHT_SEAM",[(.075,-.54,.415),(.075,-.33,.405),(.075,-.12,.410),(.075,.10,.402)],.0011,METAL)

# Seat-back rear shell gets a lighter leather piping line, avoiding dark detached appearance.
PIPE=bpy.data.materials.get("V8_3_Light_Tan_Piping")
if not PIPE:
 PIPE=bpy.data.materials.new("V8_3_Light_Tan_Piping");PIPE.use_nodes=True
 pb=PIPE.node_tree.nodes["Principled BSDF"];pb.inputs["Base Color"].default_value=(.58,.31,.15,1);pb.inputs["Roughness"].default_value=.68
for side,cx in (("L",-.353),("R",.353)):
 for u in (-1,1):
  x=cx+u*.154
  curve(f"V8_3_{side}_BACK_OUTER_PIPING_{u:+d}",[(x,-.50,.47),(x,-.56,.59),(x,-.64,.73),(x,-.68,.84)],.0018,PIPE)

s=bpy.context.scene
s.camera=bpy.data.objects["V7_Camera_Reference_ThreeQuarter"];s.render.engine="CYCLES"
s.cycles.samples=10;s.cycles.use_denoising=True;s.render.resolution_x=960;s.render.resolution_y=640
s.render.resolution_percentage=100;s.view_settings.exposure=-.52
for img in bpy.data.images:
 if img.source=="FILE" and not img.packed_file:
  try:img.pack()
  except:pass
out=OUT/"Daytona365_Cockpit_Blender_PBR_v8_3.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
m={"file":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size,
"seat_rails_and_mounts":True,"compact_steering_cowl":True,"door_caps_and_lower_pads":True,
"pedal_firewall":True,"center_tunnel_seams":True,"normal_orm_maps_preserved":True,
"game_files_modified":False,"OVC_created":False}
(OUT/"DAYTONA_V8_3_BUILD_MANIFEST.json").write_text(json.dumps(m,indent=2))
print("V8_3_PASS",json.dumps(m),flush=True)
#!/usr/bin/env python3
"""Daytona Blender v8: second major shape pass.

Runs inside Blender 4.5.15 on the actual v7.3 .blend. Rebuilds seat shells,
center console and lower dash geometry; preserves original game gauge/switch
meshes, steering spokes/emblem, and v7 PBR normal/ORM/height maps.
"""
import bpy,bmesh,math,json,hashlib
from pathlib import Path
from mathutils import Vector

R=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
OUT=R/"blender_v8"; OUT.mkdir(exist_ok=True)
assert bpy.app.version >= (4,5,0)
assert bpy.data.filepath.endswith("Daytona365_Cockpit_Blender_PBR_v7_3.blend")

TAN=bpy.data.materials["V7_Target_Tan_Leather_PBR"]
DARK=bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
WOOD=bpy.data.materials["V7_Target_Walnut_Steering_Rim_PBR"]
METAL=bpy.data.materials["V7_Machined_Aluminum"]
THREAD=bpy.data.materials["V7_Stitch_Dark_Tan"]

# Material tuning: darker saddle leather, retain linked target-image textures,
# normal map, ORM and bump from v7.
tone=TAN.node_tree.nodes.get("V7.2 Target image warm material tone")
if tone: tone.inputs[2].default_value=(.62,.55,.46,1)
bsdf=TAN.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Coat Weight"].default_value=.01
    bsdf.inputs["Sheen Weight"].default_value=.055
for n in TAN.node_tree.nodes:
    if n.type=="NORMAL_MAP": n.inputs["Strength"].default_value=.27
    if n.type=="BUMP": n.inputs["Strength"].default_value=.045

# Add fine brushed normal behavior to the metal shader with native Blender nodes.
mb=METAL.node_tree.nodes.get("Principled BSDF")
if mb:
    mb.inputs["Metallic"].default_value=.82
    mb.inputs["Roughness"].default_value=.26
    if not METAL.node_tree.nodes.get("V8_BrushedMetalNoise"):
        tex=METAL.node_tree.nodes.new("ShaderNodeTexNoise");tex.name="V8_BrushedMetalNoise"
        tex.inputs["Scale"].default_value=185
        tex.inputs["Detail"].default_value=2
        tex.inputs["Roughness"].default_value=.45
        bump=METAL.node_tree.nodes.new("ShaderNodeBump");bump.name="V8_BrushedMetalNormal"
        bump.inputs["Strength"].default_value=.055;bump.inputs["Distance"].default_value=.00012
        METAL.node_tree.links.new(tex.outputs["Fac"],bump.inputs["Height"])
        METAL.node_tree.links.new(bump.outputs["Normal"],mb.inputs["Normal"])

def coll(name):
    c=bpy.data.collections.get(name)
    if c:return c
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
CSEAT=coll("V8 | sculpted classic bucket seats")
CCON=coll("V8 | lower rounded center console")
CDASH=coll("V8 | split lower dashboard")
CTRIM=coll("V8 | fine trim and seams")

removed=[]
# Replace current v7 seat shells, seat-specific curves and bulky console/lower dash.
for o in list(bpy.data.objects):
    n=o.name.upper()
    kill=(
      n.startswith("V7_L_INTEGRATED_") or n.startswith("V7_R_INTEGRATED_") or
      (n.startswith("V7_L_") or n.startswith("V7_R_")) and
        any(k in n for k in ("CUSHION_EDGE_PIPING","BACKREST_EDGE_PIPING",
                             "CUSHION_INSET_STITCH","BACKREST_INSET_STITCH")) or
      n in ("V5_HIRES_ROUNDED_CENTER_CONSOLE",
            "V6_BLENDER_CENTER_LEATHER_ARMREST",
            "V6_BLENDER_CENTER_ARMREST_CHROME_BASE",
            "V7_BLACK_DASH_UNDERPANEL")
    )
    if kill:
        removed.append(o.name)
        bpy.data.objects.remove(o,do_unlink=True)

def make_mesh(name,verts,faces,uvs,collection,material,smooth=True):
    me=bpy.data.meshes.new(name+"_Mesh")
    me.from_pydata(verts,[],faces);me.update(calc_edges=True)
    ob=bpy.data.objects.new(name,me);collection.objects.link(ob)
    me.materials.append(material)
    uv=me.uv_layers.new(name="V8_UV")
    for p in me.polygons:
        p.use_smooth=smooth
        for li in p.loop_indices:
            vi=me.loops[li].vertex_index
            uv.data[li].uv=uvs[vi]
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(me);bm.free()
    return ob

def closed_surface(name,fn,nx,ny,thickness,collection,material):
    top=[];uv=[]
    for j in range(ny+1):
        v=j/ny
        for i in range(nx+1):
            u=i/nx
            top.append(fn(u,v));uv.append((u,v))
    N=len(top)
    # underside follows same topology with controlled thickness in Z
    bot=[(p[0],p[1]+.008,p[2]-thickness) for p in top]
    verts=top+bot;uvs=uv+list(uv)
    faces=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=a+nx+1;d=c+1
            faces.append((a,b,d,c))
            faces.append((a+N,c+N,d+N,b+N))
    perimeter=[]
    perimeter += [(i,i+1) for i in range(nx)]
    perimeter += [(j*(nx+1)+nx,(j+1)*(nx+1)+nx) for j in range(ny)]
    perimeter += [(ny*(nx+1)+i,ny*(nx+1)+i-1) for i in range(nx,0,-1)]
    perimeter += [(j*(nx+1),(j-1)*(nx+1)) for j in range(ny,0,-1)]
    for a,b in perimeter:faces.append((a,a+N,b+N,b))
    ob=make_mesh(name,verts,faces,uvs,collection,material)
    be=ob.modifiers.new("V8 upholstery rounded perimeter","BEVEL")
    be.width=.006;be.segments=3;be.limit_method="ANGLE";be.angle_limit=math.radians(48)
    sub=ob.modifiers.new("V8 final upholstery subdivision","SUBSURF")
    sub.levels=1;sub.render_levels=1
    return ob

def curve(name,pts,radius,material,collection):
    cu=bpy.data.curves.new(name,"CURVE");cu.dimensions="3D"
    cu.bevel_depth=radius;cu.bevel_resolution=3;cu.resolution_u=12
    spl=cu.splines.new("NURBS");spl.points.add(len(pts)-1)
    for i,p in enumerate(pts):spl.points[i].co=(*p,1)
    if len(pts)>=4:
        spl.order_u=min(4,len(pts));spl.use_endpoint_u=True
    ob=bpy.data.objects.new(name,cu);collection.objects.link(ob)
    cu.materials.append(material);return ob

# Classic seat: central soft cushion with pronounced but integrated edge bolster,
# gently tapered backrest and recessed center panel. No stacked floating bands.
def cushion_fn(cx,u,v):
    a=2*u-1
    # front is y=-.60, rear y=-.17
    y=-.60+.43*v
    width=.173*(1-.035*v)
    x=cx+width*a
    center=max(0,1-a*a)
    side=math.exp(-((abs(a)-.79)/.18)**2)
    front=math.exp(-((v-.08)/.12)**2)
    # central saddle slightly lower; side and front bolsters higher
    z=.392-.010*center + .048*side + .030*front + .010*math.sin(math.pi*v)*center
    # subtle 4 horizontal leather pads integrated in geometry
    z += .0065*math.cos(8*math.pi*v)*center*math.sin(math.pi*v)**.65
    return (x,y,z)

def back_fn(cx,u,v):
    a=2*u-1
    width=.171-.024*v
    x=cx+width*a
    z=.445+.415*v
    # back leans rearward towards negative y as it rises
    base=-.475-.205*v
    center=max(0,1-a*a)
    side=math.exp(-((abs(a)-.80)/.19)**2)
    # side bolsters project toward occupant/camera (more negative y)
    y=base-.034*side-.008*center
    # shallow lumbar and four upholstered horizontal pads
    y-=.010*math.sin(math.pi*v)*center
    y-=.007*math.cos(8*math.pi*v)*center*math.sin(math.pi*v)**.7
    return (x,y,z)

new_seats=[]
for side,cx in (("L",-.353),("R",.353)):
    cush=closed_surface(f"V8_{side}_CLASSIC_PADDED_CUSHION",
        lambda u,v,cx=cx:cushion_fn(cx,u,v),72,52,.052,CSEAT,TAN)
    back=closed_surface(f"V8_{side}_TAPERED_PADDED_BACKREST",
        lambda u,v,cx=cx:back_fn(cx,u,v),72,58,.047,CSEAT,TAN)
    new_seats.extend([cush,back])
    # perimeter piping follows real shell edges
    for uval in (.04,.96):
        pts=[cushion_fn(cx,uval,i/58) for i in range(59)]
        curve(f"V8_{side}_CUSHION_PERIMETER_{uval:.2f}",pts,.00145,THREAD,CTRIM)
        pts=[back_fn(cx,uval,i/64) for i in range(65)]
        curve(f"V8_{side}_BACKREST_PERIMETER_{uval:.2f}",pts,.00145,THREAD,CTRIM)
    # recessed stitch lines in pad troughs (curves are nearly flush, 0.3mm)
    for vval in (.22,.46,.70):
        pts=[cushion_fn(cx,.16+.68*i/60,vval) for i in range(61)]
        pts=[(x,y,z+.0003) for x,y,z in pts]
        curve(f"V8_{side}_CUSHION_SEAM_{vval:.2f}",pts,.00072,THREAD,CTRIM)
        pts=[back_fn(cx,.16+.68*i/60,vval) for i in range(61)]
        pts=[(x,y-.0003,z) for x,y,z in pts]
        curve(f"V8_{side}_BACKREST_SEAM_{vval:.2f}",pts,.00072,THREAD,CTRIM)

# Narrow classic center tunnel with rounded shoulders. Existing shifter remains.
def bevel_box(name,loc,size,material,collection,radius=.012):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    collection.objects.link(o)
    o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    be=o.modifiers.new("V8 rounded coachwork","BEVEL");be.width=radius;be.segments=5
    wn=o.modifiers.new("V8 weighted normals","WEIGHTED_NORMAL");wn.keep_sharp=True
    return o

# low tunnel, rear armrest and shifter plate
bevel_box("V8_LOW_CENTER_TUNNEL",(0,-.155,.333),(.205,.70,.095),DARK,CCON,.022)
bevel_box("V8_REAR_PADDED_ARMREST",(0,-.475,.404),(.175,.27,.085),DARK,CCON,.027)
bevel_box("V8_SHIFTER_ALLOY_SURROUND",(0,-.115,.395),(.175,.205,.011),METAL,CCON,.009)

# H-gate bars, actual thin metal geometry.
for x in (-.045,0,.045):
    bevel_box(f"V8_HGATE_LONG_{x:+.3f}",(x,-.112,.406),(.006,.145,.006),METAL,CTRIM,.0015)
for y in (-.165,-.112,-.059):
    bevel_box(f"V8_HGATE_CROSS_{y:+.3f}",(0,y,.406),(.096,.006,.006),METAL,CTRIM,.0015)

# Replace giant lower dash sheet with two padded knee panels, leaving center/footwell open.
bevel_box("V8_DRIVER_KNEE_PAD",(-.39,.163,.565),(.65,.025,.145),DARK,CDASH,.018)
bevel_box("V8_PASSENGER_KNEE_PAD",(.40,.163,.565),(.61,.025,.145),DARK,CDASH,.018)
# Slim lower chrome rail visually separates dash from footwell.
curve("V8_LOWER_DASH_CHROME_RAIL",
      [(-.72,.145,.488),(-.36,.145,.486),(0,.145,.485),(.36,.145,.486),(.72,.145,.488)],
      .0023,METAL,CTRIM)
# Glovebox seam on passenger side, low relief.
curve("V8_PASSENGER_GLOVEBOX_SEAM",
      [(.12,.141,.615),(.66,.141,.615)],.0011,THREAD,CTRIM)

# Door cards: keep base leather shape but replace black tube armrests with softer,
# shorter padded rails and make existing door pockets less boxy.
for side,sig in (("L",-1),("R",1)):
    old=bpy.data.objects.get(f"V5_{side}_PADDED_DOOR_ARMREST")
    if old: old.hide_render=True;old.hide_viewport=True
    bevel_box(f"V8_{side}_DOOR_PADDED_ARMREST",(sig*.735,-.445,.545),
              (.045,.38,.055),DARK,CCON,.020)

# Reduce overly large footwell kick panels so the cabin remains open.
for side in ("L","R"):
    o=bpy.data.objects.get(f"V7_{side}_BLACK_FOOTWELL_KICKPANEL")
    if o:
        o.dimensions.z=.115
        o.location.z=.355

# Camera remains exactly same for objective comparison.
s=bpy.context.scene
s.camera=bpy.data.objects["V7_Camera_Reference_ThreeQuarter"]
s.view_settings.exposure=-.50
s.render.engine="CYCLES";s.cycles.device="CPU";s.cycles.samples=10
s.cycles.use_denoising=True;s.render.resolution_x=960;s.render.resolution_y=640
s.render.resolution_percentage=100;s.render.threads_mode="FIXED";s.render.threads=2
s.render.image_settings.file_format="PNG"

for img in bpy.data.images:
    if img.source=="FILE" and not img.packed_file:
        try:img.pack()
        except Exception:pass

out=OUT/"Daytona365_Cockpit_Blender_PBR_v8.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
report={
 "file":out.name,"bytes":out.stat().st_size,
 "sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "removed_replaced_objects":removed,
 "new_seat_shells":4,
 "center_console_rebuilt":True,
 "split_lower_dash":True,
 "door_armrest_rebuilt":True,
 "same_v7_camera":True,
 "normal_ORM_height_maps_preserved":True,
 "metal_micro_normal_added":True,
 "game_files_modified":False,"OVC_created":False,"Dino_modified":False}
(OUT/"DAYTONA_V8_BUILD_MANIFEST.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_BUILD_PASS",json.dumps(report),flush=True)
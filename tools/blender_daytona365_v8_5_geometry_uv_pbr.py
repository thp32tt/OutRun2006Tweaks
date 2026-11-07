#!/usr/bin/env python3
"""Daytona 365 GTS/4 v8.5 source-backed upholstery/console/steering/PBR pass.

Run with official Blender in background, loading the *private* verified v8.4
.blend first. Never attempts to open or package original PMT/OVC/game binaries.
This is a modeling pass; it does NOT claim to render, deploy, or test VR.
"""
import bpy
import bmesh
import hashlib
import json
import math
import os
from pathlib import Path
from mathutils import Vector

ROOT = Path(os.environ.get(
    "DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
OUT = ROOT / "blender_v8"
BASE = OUT / "Daytona365_Cockpit_Blender_PBR_v8_4.blend"
DEST = OUT / "Daytona365_Cockpit_Blender_PBR_v8_5.blend"
BASE_SHA256 = "97ff8618a4a16ac837e90e8aa9dd4434f41172c0b54c6894ec680aefa93025d4"

assert bpy.app.version >= (4, 5, 0), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == BASE.resolve(), bpy.data.filepath
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA256
assert not DEST.exists(), "Never overwrite an existing v8.5 deliverable"
CAMERA = bpy.data.objects["V7_Camera_Reference_ThreeQuarter"]
assert bpy.context.scene.camera == CAMERA
TAN = bpy.data.materials["V7_Target_Tan_Leather_PBR"]
DARK = bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
WOOD = bpy.data.materials["V7_Target_Walnut_Steering_Rim_PBR"]
METAL = bpy.data.materials["V7_Machined_Aluminum"]
THREAD = bpy.data.materials["V7_Stitch_Dark_Tan"]

def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c

SEATS = coll("V8.5 | source-contoured upholstery")
TRIM = coll("V8.5 | realistic seams and welts")
CONSOLE = coll("V8.5 | low coachbuilt console")
COLUMN = coll("V8.5 | curved steering column")

def spline(name, points, radius, material, collection, cyclic=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 12
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    sp.points.add(len(points)-1)
    for i,p in enumerate(points):
        sp.points[i].co = (*p,1.0)
    sp.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name,cu)
    collection.objects.link(o)
    cu.materials.append(material)
    o["DAYTONA_SOURCE"] = "v8.4 original geometry alignment; v8.5 modeled trim"
    return o

def fresh_mesh(name, verts, faces, material, collection):
    me = bpy.data.meshes.new(name + "_Mesh")
    me.from_pydata(verts, [], faces)
    me.update(calc_edges=True)
    o = bpy.data.objects.new(name, me)
    collection.objects.link(o)
    me.materials.append(material)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for face in me.polygons:
        face.use_smooth = True
    o["DAYTONA_SOURCE"] = "v8.4 scene alignment; generated physically joined v8.5 geometry"
    return o

# v8.0 built both seats from a parameter grid (72x52/58), but for backrests
# subtracted the thickness in Z rather than moving it behind the front skin.
# This created a vertically duplicated, unnaturally thin seat-back silhouette.
# Correct both surfaces in place so existing original meshes and object IDs
# remain intact. No extra seat shells, and no stretched whole-car transforms.
def refit_shell(side, kind, nx, ny):
    name = f"V8_{side}_{'CLASSIC_PADDED_CUSHION' if kind == 'cushion' else 'TAPERED_PADDED_BACKREST'}"
    o = bpy.data.objects[name]
    me = o.data
    ring = (nx+1)*(ny+1)
    assert len(me.vertices) == 2*ring, (name, len(me.vertices))
    old_poly_count = len(me.polygons)
    for j in range(ny+1):
        v = j/ny
        for i in range(nx+1):
            u = i/nx
            a = abs(2*u-1)
            front = me.vertices[j*(nx+1)+i]
            rear = me.vertices[ring+j*(nx+1)+i]
            if kind == "cushion":
                # Fill the center without recreating the tall front horns.
                center = max(0.0,1.0-a*a)
                toe = max(0.0,1.0-v/.23)
                front.co.z += .0075*center-.009*toe*(a**3)
                # Real constant-depth upholstered return instead of
                # a phantom under-skin at an unrelated Y.
                rear.co = (front.co.x, front.co.y+.006, front.co.z-.049)
            else:
                # Gently rounded lumbar panel in the same front-face direction.
                center = max(0.0,1.0-a*a)
                front.co.y -= .007*center*math.sin(math.pi*v)
                # v8.4 rear skin used Z-47 mm and Y+8 mm. For a mostly
                # upright backrest that is the WRONG thickness direction.
                rear.co = (front.co.x, front.co.y+.054, front.co.z-.004)
    me.update()
    assert len(me.polygons) == old_poly_count

    # New active UV measured along the actual seat surface. All PBR/ORM/
    # normal maps still share this active UV; no source DDS pixel edits.
    # Repeats make micrograin a fabric-scale detail rather than a giant
    # single-image pattern stretched across the whole shell.
    uv = me.uv_layers.get("V8_5_METRIC_UPHOLSTERY_UV")
    if uv is None:
        uv = me.uv_layers.new(name="V8_5_METRIC_UPHOLSTERY_UV")
    for polygon in me.polygons:
        for li in polygon.loop_indices:
            vi = me.loops[li].vertex_index % ring
            u = (vi % (nx+1))/nx
            v = (vi // (nx+1))/ny
            uv.data[li].uv = (u*2.2,v*(2.9 if kind == "cushion" else 2.75))
    me.uv_layers.active = uv
    o["DAYTONA_UV_TEXEL_REPEAT_U"] = 2.2
    o["DAYTONA_UV_TEXEL_REPEAT_V"] = 2.9 if kind == "cushion" else 2.75
    o["DAYTONA_GEOMETRY_PASS"] = "v8.5 thickness axis, padding, and UV"
    return o

def top_vertex(o,nx,j,i):
    return tuple(o.data.vertices[j*(nx+1)+i].co)

shells=[]
for side in ("L","R"):
    cush = refit_shell(side,"cushion",72,52)
    back = refit_shell(side,"backrest",72,58)
    shells.extend((cush,back))

    # Avoid stacking the old inaccurate surface curves on the new fitted
    # surface. Reproduce seam paths directly from the *new* vertex grids.
    for obj in list(bpy.data.objects):
        if obj.name.startswith(f"V8_{side}_") and (
            "_CUSHION_SEAM_" in obj.name or "_BACKREST_SEAM_" in obj.name
            or "_CUSHION_PERIMETER_" in obj.name or "_BACKREST_PERIMETER_" in obj.name
        ):
            obj.hide_render = True
            obj.hide_viewport = True

    for kind,o,nx,ny in (("CUSHION",cush,72,52),("BACKREST",back,72,58)):
        for j_frac in (.23,.48,.72):
            j=round(j_frac*ny)
            pts=[]
            for i in range(11,nx-10):
                x,y,z=top_vertex(o,nx,j,i)
                pts.append((x,y-.0011,z) if kind=="BACKREST" else (x,y,z+.0011))
            spline(f"V8_5_{side}_{kind}_STITCH_{j_frac:.2f}",
                   pts,.00062,THREAD,TRIM)
        for edge,i in (("LEFT",3),("RIGHT",nx-3)):
            pts=[]
            for j in range(1,ny):
                x,y,z=top_vertex(o,nx,j,i)
                pts.append((x,y-.0012,z) if kind=="BACKREST" else (x,y,z+.0012))
            spline(f"V8_5_{side}_{kind}_{edge}_WELT",
                   pts,.00145,TAN,TRIM)

# Replace v8.4 rectangular block tunnel with low, shoulder-shaped connected
# cross-sections. Keep object name and nearby original gearbox and gate intact.
tunnel=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
assert tunnel.type=="MESH"
profile=[
    (-.44,.075,.305,.383),(-.35,.081,.305,.405),
    (-.15,.080,.305,.404),(.030,.070,.305,.395),(.125,.061,.306,.375)
]
verts=[]
for y,width,bottom,top in profile:
    verts.extend([
        (-width,y,bottom),
        (-width,y,top-.023),
        (-width*.70,y,top),
        (width*.70,y,top),
        (width,y,top-.023),
        (width,y,bottom)
    ])
faces=[]
for j in range(len(profile)-1):
    for k in range(6):
        a=j*6+k;b=j*6+(k+1)%6
        faces.append((a,b,b+6,a+6))
faces.extend((tuple(reversed(range(6))),tuple((len(profile)-1)*6+k for k in range(6))))
new_tunnel=fresh_mesh("V8_5_TEMP_TUNNEL",verts,faces,DARK,CONSOLE)
old_data=tunnel.data
tunnel.data=new_tunnel.data.copy()
tunnel.location=(0,0,0)
tunnel.rotation_euler=(0,0,0)
tunnel.scale=(1,1,1)
for mod in list(tunnel.modifiers):tunnel.modifiers.remove(mod)
b=tunnel.modifiers.new("V8.5 soft shoulder edge","BEVEL")
b.width=.009;b.segments=3
w=tunnel.modifiers.new("V8.5 manufactured normal","WEIGHTED_NORMAL")
w.keep_sharp=True
bpy.data.objects.remove(new_tunnel,do_unlink=True)
if old_data.users==0:bpy.data.meshes.remove(old_data)
tunnel["DAYTONA_GEOMETRY_PASS"]="v8.5 5-section low tapered tunnel"

deck=bpy.data.objects["V8_1_COMPACT_SHIFTER_LEATHER_DECK"]
deck.dimensions=(.135,.167,.019)
deck.location=(0,-.111,.414)
arm=bpy.data.objects["V8_REAR_PADDED_ARMREST"]
arm.dimensions=(.135,.153,.064)
arm.location=(0,-.404,.391)
# Replace the v8.3 seams that floated at world Z=.415 above the old block.
for n in ("V8_3_CENTER_TUNNEL_LEFT_SEAM","V8_3_CENTER_TUNNEL_RIGHT_SEAM"):
    if n in bpy.data.objects:
        bpy.data.objects[n].hide_render=True
        bpy.data.objects[n].hide_viewport=True
for sign,name in ((-1,"LEFT"),(1,"RIGHT")):
    pts=[(sign*w*.72,y,top+.0007) for y,w,_bottom,top in profile]
    spline("V8_5_TUNNEL_"+name+"_SEAM",pts,.0008,THREAD,TRIM)

# Replace the v8.4 straight large steering tube with a short, curved,
# lower-radius cowl that exits beneath the real gauge binnacle. Keep the
# original wheel/spokes/emblem and untouched steering pivot.
for n in ("V8_4_SLIM_STEERING_COWL","V8_4_STEERING_SHAFT"):
    assert n in bpy.data.objects,n
    bpy.data.objects.remove(bpy.data.objects[n],do_unlink=True)

def tapered_tube(name,stations,material):
    sections=36
    centers=[Vector(p) for p,r in stations]
    vertices=[];polys=[]
    for j,(center,rad) in enumerate(stations):
        direction=(centers[min(j+1,len(centers)-1)]
                   -centers[max(j-1,0)]).normalized()
        up=Vector((1,0,0))
        if abs(direction.dot(up))>.9:up=Vector((0,0,1))
        axis=direction.cross(up).normalized()
        binormal=direction.cross(axis).normalized()
        for i in range(sections):
            angle=2*math.pi*i/sections
            p=Vector(center)+rad*(axis*math.cos(angle)+binormal*math.sin(angle))
            vertices.append(tuple(p))
    for j in range(len(stations)-1):
        for i in range(sections):
            a=j*sections+i;b=j*sections+(i+1)%sections
            polys.append((a,b,b+sections,a+sections))
    polys.extend((tuple(reversed(range(sections))),
                  tuple((len(stations)-1)*sections+i for i in range(sections))))
    o=fresh_mesh(name,vertices,polys,material,COLUMN)
    uv=o.data.uv_layers.new(name="V8_5_TUBE_UV")
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            idx=o.data.loops[li].vertex_index
            uv.data[li].uv=((idx%sections)/sections,(idx//sections)/(len(stations)-1))
    be=o.modifiers.new("V8.5 edge softener","BEVEL")
    be.width=.0012
    be.segments=2
    return o

tapered_tube("V8_5_CURVED_COLUMN_COWL",[
    ((-.35,.126,.646),.025),
    ((-.35,.065,.660),.028),
    ((-.35,-.022,.687),.025),
    ((-.35,-.103,.714),.017)
],DARK)
tapered_tube("V8_5_STEERING_SHAFT",[
    ((-.35,-.101,.712),.010),
    ((-.35,-.211,.757),.0088),
    ((-.35,-.274,.780),.008)
],METAL)

# Door top cap is a trim insert, not a full-width black beam. Preserve source
# door cards and ensure bevel width fits the smaller section after scaling.
for side in ("L","R"):
    cap=bpy.data.objects[f"V8_3_{side}_BLACK_DOOR_TOP_CAP"]
    cap.dimensions.x=.020
    cap.dimensions.z=.029
    for mod in cap.modifiers:
        if mod.type=="BEVEL":mod.width=min(mod.width,.004)
    pad=bpy.data.objects[f"V8_3_{side}_TAN_DOOR_LOWER_PAD"]
    pad.dimensions.x=.020
    for mod in pad.modifiers:
        if mod.type=="BEVEL":mod.width=min(mod.width,.007)

# PBR: target-derived packed BaseColor/Normal/ORM/HeightOffline stay packed.
# The ORM green channel is roughness. Map it to material-specific physically
# plausible ranges without disconnecting the texture. ORM.B is metallic but
# these leather/wood surfaces are dielectric, so metallic remains 0.
def tune_material(m, rough_min, rough_max, normal_strength, bump_strength, bump_dist):
    assert m.use_nodes
    nt=m.node_tree
    bsdf=nt.nodes["Principled BSDF"]
    orm=next(n for n in nt.nodes if n.type=="TEX_IMAGE" and n.image and
             "ORM" in n.image.name.upper())
    assert orm.image.packed_file
    assert orm.image.colorspace_settings.name=="Non-Color"
    sep=next((n for n in nt.nodes if n.type=="SEPARATE_COLOR"),None)
    assert sep is not None and sep.inputs["Color"].is_linked,m.name
    node=nt.nodes.get("V8_5_ORM_ROUGHNESS_RANGE")
    if node is None:
        node=nt.nodes.new("ShaderNodeMapRange")
        node.name="V8_5_ORM_ROUGHNESS_RANGE"
    node.clamp=True
    node.inputs["From Min"].default_value=0
    node.inputs["From Max"].default_value=1
    node.inputs["To Min"].default_value=rough_min
    node.inputs["To Max"].default_value=rough_max
    nt.links.new(sep.outputs["Green"],node.inputs["Value"])
    nt.links.new(node.outputs["Result"],bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value=0
    nm=[n for n in nt.nodes if n.type=="NORMAL_MAP"]
    bm=[n for n in nt.nodes if n.type=="BUMP"]
    assert nm and bm and bsdf.inputs["Normal"].is_linked,m.name
    for n in nm:n.inputs["Strength"].default_value=normal_strength
    for n in bm:
        n.inputs["Strength"].default_value=bump_strength
        n.inputs["Distance"].default_value=bump_dist
    for n in nt.nodes:
        if n.type=="TEX_IMAGE" and n.image:
            assert n.image.packed_file,(m.name,n.image.name)
            n.extension="REPEAT"
    m["DAYTONA_PBR_ORM_G"]="green: remapped roughness"
    m["DAYTONA_PBR_METALLIC"]="dielectric; physical metallic=0"
    m["DAYTONA_PBR_NORMAL_AND_HEIGHT"]="preserved packed tangent normal + microbump"

tune_material(TAN,.61,.89,.27,.027,.00038)
tune_material(DARK,.67,.93,.20,.018,.00024)
tune_material(WOOD,.23,.45,.17,.019,.00012)
mb=METAL.node_tree.nodes.get("Principled BSDF")
assert mb
mb.inputs["Roughness"].default_value=.36
mb.inputs["Metallic"].default_value=.82
assert METAL.node_tree.nodes.get("V8_BrushedMetalNormal")

scene=bpy.context.scene
assert scene.camera==CAMERA
scene.render.engine="CYCLES"
scene.cycles.samples=10
scene.render.resolution_x=960
scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.view_settings.exposure=-.52
for im in bpy.data.images:
    if im.source=="FILE" and not im.packed_file:
        im.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.is_file()
manifest={
    "status":"V8_5_MODEL_SAVED_RENDER_VALIDATION_UNTESTED",
    "source_blend":BASE.name,
    "source_sha256":BASE_SHA256,
    "blend":DEST.name,
    "sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
    "bytes":DEST.stat().st_size,
    "blender":bpy.app.version_string,
    "seat_shells_refit":len(shells),
    "backrest_thickness_axis_corrected":True,
    "metric_uv_meshes":len(shells),
    "source_gauges_wheel_and_shift_gate_preserved":True,
    "low_section_loft_tunnel":True,
    "curved_steering_column":True,
    "door_caps_trimmed":True,
    "packed_normal_orm_basecolor_height_retained":True,
    "ORM_green_material_roughness_remapped":True,
    "camera":"V7_Camera_Reference_ThreeQuarter",
    "render_engine_preconfigured":"CYCLES",
    "render_validation":"UNTESTED",
    "original_game_files_modified":False,
    "OVC_created":False,
    "Quest3_tested":False
}
(OUT/"DAYTONA_V8_5_BUILD_MANIFEST.json").write_text(
    json.dumps(manifest,indent=2),encoding="utf-8")
print("DAYTONA_V8_5_MODEL_SAVED",json.dumps(manifest),flush=True)

#!/usr/bin/env python3
"""Daytona 365 v8.6: measured original-PMT console fascia, seat supports, UV/PBR.

Load the previously verified *private* v8.5 .blend. Measured source bounds
are reference metadata, not redistributed game geometry. This tool creates
a new checkpoint; it never overwrites the last verified .blend.
Rendering and game integration are explicitly separate validation stages.
"""
import bpy
import bmesh
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(os.environ.get(
    "DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
OUT = ROOT / "blender_v8"
SOURCE = OUT / "Daytona365_Cockpit_Blender_PBR_v8_5.blend"
DEST = OUT / "Daytona365_Cockpit_Blender_PBR_v8_6.blend"
SOURCE_SHA256 = "bac28640d88c745b5f276b1ecb5c2ae730e54660fb9526432aeb8c09be390ef8"

assert bpy.app.version >= (4, 5, 0)
assert Path(bpy.data.filepath).resolve() == SOURCE.resolve()
assert SOURCE.is_file() and hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
assert not DEST.exists(), "Do not overwrite any v8.6 evidence or model"
scene = bpy.context.scene
assert scene.camera.name == "V7_Camera_Reference_ThreeQuarter"
DARK = bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
TAN = bpy.data.materials["V7_Target_Tan_Leather_PBR"]
METAL = bpy.data.materials["V7_Machined_Aluminum"]
THREAD = bpy.data.materials["V7_Stitch_Dark_Tan"]
assert bpy.data.objects.get("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3")
assert bpy.data.objects.get("V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM")

# Private measurement provenance: original imported PMT object00
# material016 (object00_group01_material016_a0 lower center stack) x=[-.14203,+.14203], y=[.16707,.22873],
# z=[.58656,.84731]; original object00_group01_material018_a0 (console) x=[-.10683,+.10683],
# y=[-.23555,+.20228], z=[.33638,.51887].
# The bounds are used only to constrain newly authored topology, never to
# copy/proxy/commit actual original PMT vertices or game texture bytes.
PMT_CENTER_STACK_BOUNDS = ((-.14203, .16707, .58656), (.14203, .22873, .84731))
PMT_CONSOLE_BOUNDS = ((-.10683, -.23555, .33638), (.10683, .20228, .51887))
assert PMT_CENTER_STACK_BOUNDS[0][2] > PMT_CONSOLE_BOUNDS[0][2]

def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
    return c

DETAILS = collection("V8.6 | PMT-bounds measured lower facia and tunnel")
STITCH = collection("V8.6 | geometry-following inset seams")

def mesh_into_existing(obj, verts, faces, mat, uv_kind, profile=None):
    original = obj.data
    mesh = bpy.data.meshes.new(obj.name + "_V8_6_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    mesh.materials.append(mat)
    obj.data = mesh
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.scale = (1, 1, 1)
    if original.users == 0:
        bpy.data.meshes.remove(original)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    uv = mesh.uv_layers.new(name="V8_6_METRIC_TANGENT_UV")
    if uv_kind == "loft":
        # Physical (cross-section arc length, longitudinal Y) unwrap. Avoid
        # the old missing-UV/default-position artifact for tangent normal.
        assert profile is not None
        for poly in mesh.polygons:
            ids = [mesh.loops[li].vertex_index % 6 for li in poly.loop_indices]
            wraps = 0 in ids and 5 in ids and len(poly.loop_indices) == 4
            for li in poly.loop_indices:
                vi = mesh.loops[li].vertex_index
                j, k = divmod(vi, 6)
                y, width, bottom, top = profile[j]
                section = [(-width,bottom),(-width,top-.020),
                           (-width*.68,top),(width*.68,top),
                           (width,top-.020),(width,bottom)]
                cumulative = [0.0]
                for kk in range(1, 6):
                    cumulative.append(cumulative[-1] + math.dist(section[kk-1],section[kk]))
                full = cumulative[-1] + math.dist(section[-1],section[0])
                u = full if wraps and k == 0 else cumulative[k]
                uv.data[li].uv = (u * 5.0, (y - profile[0][0]) * 5.0)
    else:
        # Per-face physical planar mapping for the manufactured dash lip and
        # transition fascia. Poly-island UVs are appropriate for hard corners.
        for poly in mesh.polygons:
            n = poly.normal
            direction = max(range(3), key=lambda i: abs(n[i]))
            for li in poly.loop_indices:
                p = mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv = (
                    (p.y,p.z) if direction == 0 else
                    (p.x,p.z) if direction == 1 else (p.x,p.y))
                uv.data[li].uv *= 5.0
    for p in mesh.polygons:
        p.use_smooth = True
    return mesh

def add_mesh(name, verts, faces, material, uv_kind="planar"):
    ob = bpy.data.objects.new(name, bpy.data.meshes.new(name+"_placeholder"))
    DETAILS.objects.link(ob)
    mesh_into_existing(ob, verts, faces, material, uv_kind)
    ob["DAYTONA_AUTHOR"] = "v8.6, source-bounds constrained, not original PMT"
    return ob

def modifiers(obj, bevel):
    for m in list(obj.modifiers):
        obj.modifiers.remove(m)
    m=obj.modifiers.new("V8.6 body-edge micro radius", "BEVEL")
    m.width=bevel
    m.segments=3
    m.limit_method="ANGLE"
    m.angle_limit=math.radians(38)
    w=obj.modifiers.new("V8.6 curvature-preserving normals","WEIGHTED_NORMAL")
    w.keep_sharp=True

def tuned_copy(source, name, minimum, maximum, normal, bump):
    assert name not in bpy.data.materials
    mat=source.copy()
    mat.name=name
    nodes=mat.node_tree.nodes
    bsdf=nodes["Principled BSDF"]
    orm=nodes.get("V8_5_ORM_ROUGHNESS_RANGE")
    assert orm and bsdf.inputs["Roughness"].is_linked
    orm.inputs["To Min"].default_value=minimum
    orm.inputs["To Max"].default_value=maximum
    for node in nodes:
        if node.type=="NORMAL_MAP":
            node.inputs["Strength"].default_value=normal
        if node.type=="BUMP":
            node.inputs["Strength"].default_value=bump
            node.inputs["Distance"].default_value=.00018
        if node.type=="TEX_IMAGE" and node.image:
            assert node.image.packed_file
            if any(s in node.image.name.upper() for s in ("ORM","NORMAL","HEIGHT")):
                assert node.image.colorspace_settings.name=="Non-Color"
    bsdf.inputs["Metallic"].default_value=0.0
    mat["DAYTONA_PBR_PACKED_ORIGINAL_IMAGES"] = "linked and packed, preserved"
    mat["DAYTONA_ORM_G"] = [minimum,maximum]
    return mat

CONSOLE_MAT=tuned_copy(DARK,"V8_6_Source_Measured_Console_Grain",.67,.85,.15,.013)
DOOR_MAT=tuned_copy(TAN,"V8_6_Soft_Door_Card_Leather",.62,.84,.22,.016)

# The v8.5 tunnel was only .405 m tall and ended at Y=.125, while
# original PMT material018 extends to Y=.202 and Z=.519. Rebuild a continuous
# low rear tunnel rising into an ORIGINAL-BOUNDS-CONSTRAINED front fairing.
# Leave the metal H gate and the source shifter alone at y=-.1 / z=.435+.
stations=[
    (-.440,.069,.305,.379), (-.365,.074,.306,.388),
    (-.275,.080,.307,.394), (-.205,.083,.306,.402),
    (-.095,.089,.308,.407), (-.015,.091,.311,.410),
    (.055,.094,.316,.439), (.125,.101,.326,.475),
    (.185,.105,.336,.503)
]
verts=[]
for y,w,bottom,top in stations:
    verts += [(-w,y,bottom),(-w,y,top-.020),(-w*.68,y,top),
              (w*.68,y,top),(w,y,top-.020),(w,y,bottom)]
faces=[]
for j in range(len(stations)-1):
    for k in range(6):
        a=j*6+k
        b=j*6+(k+1)%6
        faces.append((a,b,b+6,a+6))
faces += [tuple(reversed(range(6))),
          tuple((len(stations)-1)*6+k for k in range(6))]
tunnel=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
assert tunnel.type=="MESH"
mesh_into_existing(tunnel,verts,faces,CONSOLE_MAT,"loft",stations)
modifiers(tunnel,.005)
tunnel["DAYTONA_GEOMETRY_PASS"]="v8.6 source-bounds tapered console"
tunnel["DAYTONA_SOURCE_CONSOLE_BOUNDS"]=str(PMT_CONSOLE_BOUNDS)

for n in ("V8_5_TUNNEL_LEFT_SEAM","V8_5_TUNNEL_RIGHT_SEAM"):
    old=bpy.data.objects.get(n)
    assert old
    bpy.data.objects.remove(old,do_unlink=True)

def curve(name,points,mat=THREAD,radius=.00075):
    cu=bpy.data.curves.new(name,"CURVE")
    cu.dimensions="3D"
    cu.resolution_u=12
    cu.bevel_depth=radius
    cu.bevel_resolution=3
    s=cu.splines.new("POLY")
    s.points.add(len(points)-1)
    for pt,p in zip(s.points,points):
        pt.co=(*p,1)
    o=bpy.data.objects.new(name,cu)
    STITCH.objects.link(o)
    cu.materials.append(mat)
    return o

for sign,label in ((-1,"LEFT"),(1,"RIGHT")):
    curve("V8_6_TUNNEL_"+label+"_CONTINUOUS_SEAM",
        [(sign*w*.68,y,top+.0008) for y,w,_bottom,top in stations],
        THREAD,.00073)

# Sculpt the source-facing underside of the dash instead of a huge sharp
# rectangular v8.2 bar. Preserve its name and source-aligned camera.
lip=bpy.data.objects["V8_2_CONTINUOUS_LOWER_DASH_LIP"]
xs=[-.715,-.60,-.48,-.36,-.245,-.15,-.075,0,.075,.15,.245,.36,.48,.60,.715]
v=[]
for x in xs:
    a=abs(x)/.715
    upper=.644-.003*(1-a*a)
    lower=.575+.029*math.exp(-(x/.20)**2)+.007*math.sin(math.pi*a)
    v.extend([(x,.182,lower),(x,.182,upper),(x,.217,upper),(x,.217,lower)])
f=[]
for j in range(len(xs)-1):
    for k in range(4):
        a=j*4+k;b=j*4+(k+1)%4
        f.append((a,b,b+4,a+4))
f.extend((tuple(reversed(range(4))),tuple((len(xs)-1)*4+k for k in range(4))))
mesh_into_existing(lip,v,f,CONSOLE_MAT,"planar")
modifiers(lip,.005)
lip["DAYTONA_GEOMETRY_PASS"]="v8.6 shallow source-contoured center relief"
trim=bpy.data.objects["V8_2_DASH_TRIM_STRIP"]
trim.location.z += .010
trim.location.y -= .007
trim["DAYTONA_GEOMETRY_PASS"]="v8.6 relaid to sculpted lower lip"

# Bridge the original measured center console lip and the dashboard above
# without covering original game switches/gauge binnacles above Z=.58656.
front_profile=[(-.108,.170,.505),(-.116,.175,.536),
               (-.134,.181,.570),(-.134,.190,.584)]
bridge=[]
for half,y,z in front_profile:
    bridge.extend([(-half,y,z),(half,y,z),
                   (-half,y+.030,z),(half,y+.030,z)])
bridge_faces=[]
for j in range(len(front_profile)-1):
    for k,q in ((0,1),(1,3),(3,2),(2,0)):
        bridge_faces.append((j*4+k,j*4+q,(j+1)*4+q,(j+1)*4+k))
bridge_faces.extend(((0,2,3,1),tuple(reversed(range((len(front_profile)-1)*4,len(front_profile)*4)))))
bridge_obj=add_mesh("V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING",
                    bridge,bridge_faces,CONSOLE_MAT)
modifiers(bridge_obj,.0035)
bridge_obj["DAYTONA_NATIVE_STACK_REFERENCE"]="object00_group01_material016_a0 bounds only"
assert max(p[2] for p in bridge)<PMT_CENTER_STACK_BOUNDS[0][2]
assert max(abs(p[0]) for p in bridge)<PMT_CENTER_STACK_BOUNDS[1][0]

# v8.5 had a smooth outer perimeter but weak *interior* bolster. Alter
# surface vertices in place; retain both original 2*grid topology and the
# physically correct backrest rear-skin Y thickness from v8.5. Sync every
# existing welt/seam curve to the deformed surface, so none floats.
seat_checks=[]
for side in ("L","R"):
    for kind,ny in (("CUSHION",52),("BACKREST",58)):
        suffix=("CLASSIC_PADDED_CUSHION" if kind=="CUSHION" else "TAPERED_PADDED_BACKREST")
        obj=bpy.data.objects["V8_"+side+"_"+suffix]
        me=obj.data
        nx=72
        ring=(nx+1)*(ny+1)
        assert len(me.vertices)==2*ring
        original_faces=len(me.polygons)
        for j in range(ny+1):
            t=j/ny
            taper=max(0, math.sin(math.pi*t)) ** .85
            for i in range(nx+1):
                a=abs(2*i/nx-1)
                bolster=math.exp(-((a-.76)/.17)**2)*taper
                idx=j*73+i
                point=me.vertices[idx]
                back=me.vertices[ring+idx]
                if kind=="CUSHION":
                    point.co.z += .010*bolster
                    back.co=(point.co.x,point.co.y+.006,point.co.z-.049)
                else:
                    point.co.y -= .012*bolster
                    back.co=(point.co.x,point.co.y+.054,point.co.z-.004)
        me.update()
        assert len(me.polygons)==original_faces
        assert me.uv_layers.active.name=="V8_5_METRIC_UPHOLSTERY_UV"
        def top(j,i):
            q=me.vertices[j*73+i].co
            return (float(q.x),float(q.y),float(q.z))
        def set_points(name,points):
            o=bpy.data.objects[name]
            sp=o.data.splines[0]
            assert len(sp.points)==len(points),(name,len(sp.points),len(points))
            for q,p in zip(sp.points,points):
                q.co=(*p,1)
        for edge,i in (("LEFT",3),("RIGHT",nx-3)):
            pts=[top(j,i) for j in range(1,ny)]
            pts=[(x,y-.0012,z) if kind=="BACKREST" else (x,y,z+.0012) for x,y,z in pts]
            set_points("V8_5_"+side+"_"+kind+"_"+edge+"_WELT",pts)
        for frac in (.23,.48,.72):
            j=round(frac*ny)
            pts=[top(j,i) for i in range(11,nx-10)]
            pts=[(x,y-.0011,z) if kind=="BACKREST" else (x,y,z+.0011) for x,y,z in pts]
            set_points("V8_5_"+side+"_"+kind+"_STITCH_"+format(frac,".2f"),pts)
        for edge,i in (("LEFT",14),("RIGHT",nx-14)):
            pts=[top(j,i) for j in range(5,ny-4)]
            pts=[(x,y-.0013,z) if kind=="BACKREST" else (x,y,z+.0013) for x,y,z in pts]
            curve("V8_6_"+side+"_"+kind+"_INSET_"+edge+"_BOLSTER_SEAM",pts)
        obj["DAYTONA_GEOMETRY_PASS"]="v8.6 in-place sculpted side support / synced surface trim"
        seat_checks.append(obj.name)

# Physical repeat UV on long narrow door inserts; the previous cube UV made
# 1 pixel structure cover the entire 820-mm card. Keep each source card/pull
# in its old position and only refine its own mapping/material.
for side in ("L","R"):
    pad=bpy.data.objects["V8_3_"+side+"_TAN_DOOR_LOWER_PAD"]
    mesh=pad.data
    uv=mesh.uv_layers.get("V8_6_DOOR_METRIC_UV") or mesh.uv_layers.new(name="V8_6_DOOR_METRIC_UV")
    for poly in mesh.polygons:
        n=poly.normal
        for li in poly.loop_indices:
            q=pad.matrix_world @ mesh.vertices[mesh.loops[li].vertex_index].co
            coord=(q.y,q.z) if abs(n.x)>.5 else ((q.x,q.z) if abs(n.y)>.5 else (q.x,q.y))
            uv.data[li].uv=(coord[0]*4.5,coord[1]*4.5)
    mesh.uv_layers.active=uv
    mesh.materials.clear()
    mesh.materials.append(DOOR_MAT)
    pad["DAYTONA_UV_PASS"]="v8.6 local metric projection, original card pivot preserved"

deck=bpy.data.objects["V8_1_COMPACT_SHIFTER_LEATHER_DECK"]
arm=bpy.data.objects["V8_REAR_PADDED_ARMREST"]
for o in (deck,arm):
    o.data.materials.clear()
    o.data.materials.append(CONSOLE_MAT)

scene.render.engine="CYCLES"
scene.cycles.samples=10
scene.cycles.use_denoising=True
scene.render.resolution_x=960
scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.view_settings.exposure=-.52
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
for image in bpy.data.images:
    if image.source=="FILE" and not image.packed_file:
        image.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.is_file()
report={
  "status":"V8_6_REAL_BLEND_SAVED_RENDER_VALIDATION_UNTESTED",
  "source_file":SOURCE.name,
  "source_sha256":SOURCE_SHA256,
  "new_file":DEST.name,
  "new_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
  "bytes":DEST.stat().st_size,
  "blender":bpy.app.version_string,
  "camera":scene.camera.name,
  "original_pmt_measured_group16_bounds":PMT_CENTER_STACK_BOUNDS,
  "original_pmt_measured_group18_bounds":PMT_CONSOLE_BOUNDS,
  "replaced_tunnel_station_count":len(stations),
  "tunnel_has_metric_tangent_uv":True,
  "sculpted_dash_lip_and_measured_fairing":True,
  "source_gauges_gear_gate_steering_preserved":True,
  "sculpted_source_seat_shells":seat_checks,
  "old_welts_reprojected":True,
  "door_metric_uv_both_sides":True,
  "packed_normal_basecolor_orm_height_preserved":True,
  "material_roughness_green_orm_remapped":True,
  "render_validation":"UNTESTED",
  "full_resolution_render":"UNTESTED",
  "game_runtime_validation":"UNTESTED",
  "original_game_files_modified":False,
  "OVC_created":False,
  "Quest3_tested":False
}
(OUT/"DAYTONA_V8_6_BUILD_MANIFEST.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_6_MODEL_SAVED",json.dumps(report),flush=True)

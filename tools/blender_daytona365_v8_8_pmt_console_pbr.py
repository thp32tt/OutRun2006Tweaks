#!/usr/bin/env python3
"""Ferrari 365 GTS/4 v8.8: PMT-bounded console, 13-station PMT console and calibrated source PBR.

Private input .blend is verified by hash; never export original PMT/DDS or overwrite v8.7.
Original source group017/018 public aggregate measurements inform bounded handmade topology.
"""
import bpy, bmesh, hashlib, json, math, os
from pathlib import Path
from mathutils import Vector

ROOT=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
OUT=ROOT/"blender_v8"
SOURCE=OUT/"Daytona365_Cockpit_Blender_PBR_v8_7.blend"
DEST=OUT/"Daytona365_Cockpit_Blender_PBR_v8_8.blend"
SOURCE_SHA256="e247abed67d15b5562daa5374163cc4c3a18de7dd059bfc42d94c9227e0e61a3"
assert bpy.app.version >= (4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
assert not DEST.exists(), "Immutable new v8.8 output already exists"
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
for name in ("V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
             "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
             "V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
             "V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"):
    assert bpy.data.objects.get(name), name

# Original material017: seat group, measured x +/-0.57464, y -0.72863..-0.01985,
# z 0.33179..0.85149. Material018: console, x +/-0.10683,
# y -0.23555..0.20228 and z 0.33638..0.51887.
# These are constrained aggregate bounds, NOT copied original game vertices.
PMT_SEAT_BOUNDS=((-0.57464,-0.72863,0.33179),(0.57464,-0.01985,0.85149))
PMT_CONSOLE_BOUNDS=((-0.10683,-0.23555,0.33638),(0.10683,0.20228,0.51887))
def collection(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name)
        scene.collection.children.link(c)
    return c
DETAIL=collection("V8.7 | PMT bounded console and leather side returns")
STITCH=collection("V8.7 | seam and fascia details")

def copy_tuned_mat(original,name,rough_min,rough_max,normal_strength,bump_strength,bump_distance,color_multiplier=None):
    assert name not in bpy.data.materials
    mat=bpy.data.materials[original].copy()
    mat.name=name
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    bsdf=nodes["Principled BSDF"]
    rng=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
    assert bsdf.inputs["Roughness"].is_linked and bsdf.inputs["Normal"].is_linked
    rng.inputs["To Min"].default_value=rough_min
    rng.inputs["To Max"].default_value=rough_max
    bsdf.inputs["Metallic"].default_value=0.0
    for n in nodes:
        if n.type=="NORMAL_MAP":
            n.inputs["Strength"].default_value=normal_strength
        if n.type=="BUMP":
            n.inputs["Strength"].default_value=bump_strength
            n.inputs["Distance"].default_value=bump_distance
        if n.type=="TEX_IMAGE" and n.image:
            assert n.image.packed_file,(mat.name,n.image.name)
            if any(x in n.image.name.upper() for x in ("NORMAL","ORM","HEIGHT")):
                assert n.image.colorspace_settings.name=="Non-Color",n.image.name
    if color_multiplier is not None:
        color_in=bsdf.inputs["Base Color"]
        assert color_in.is_linked,"Do not replace source-derived BaseColor with an invented flat color"
        source_socket=color_in.links[0].from_socket
        mix=nodes.new("ShaderNodeMixRGB")
        mix.name="V8_8_SOURCE_BASECOLOR_ATTENUATION"
        mix.blend_type="MULTIPLY"
        mix.inputs[0].default_value=1.0
        mix.inputs[2].default_value=(*color_multiplier,1.0)
        links.new(source_socket,mix.inputs[1])
        links.new(mix.outputs[0],color_in)
    mat["DAYTONA_V8_8_SOURCE_PBR"]="Packed source BaseColor/tangent Normal/ORM/Height preserved"
    return mat

SEAT_MAT=copy_tuned_mat("V7_Target_Tan_Leather_PBR",
    "V8_8_Source_Seat_Less_Saturated_Leather",.67,.89,.19,.012,.00016,(.78,.73,.68))
SIDE_MAT=copy_tuned_mat("V7_Target_Tan_Leather_PBR",
    "V8_8_Seat_Side_Return_Leather",.71,.90,.15,.010,.00013,(.72,.68,.64))
CONSOLE_MAT=copy_tuned_mat("V8_6_Source_Measured_Console_Grain",
    "V8_8_PMT_Console_Matte_Grain",.72,.89,.13,.011,.00012)
THREAD=bpy.data.materials["V7_Stitch_Dark_Tan"]

def recalc(mesh):
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for face in mesh.polygons:
        face.use_smooth=True

def curve(name,points,material,radius=.0007):
    cu=bpy.data.curves.new(name,"CURVE")
    cu.dimensions="3D"
    cu.bevel_depth=radius
    cu.bevel_resolution=3
    s=cu.splines.new("POLY")
    s.points.add(len(points)-1)
    for point,pos in zip(s.points,points):
        point.co=(*pos,1)
    cu.materials.append(material)
    o=bpy.data.objects.new(name,cu)
    STITCH.objects.link(o)
    return o

def reproject_curve(name,points):
    o=bpy.data.objects[name]
    sp=o.data.splines[0]
    assert len(sp.points)==len(points),(name,len(sp.points),len(points))
    for q,pos in zip(sp.points,points):
        q.co=(*pos,1.0)

# Preserve all v8.7 measured seat topology, geodesic UV, joined side returns and seams.
# Apply only physically restrained source-linked leather shading; no new fake seat shell.
seat_stats={}
for side in ("L","R"):
    for kind in ("CUSHION","BACKREST"):
        suffix="CLASSIC_PADDED_CUSHION" if kind=="CUSHION" else "TAPERED_PADDED_BACKREST"
        ob=bpy.data.objects["V8_"+side+"_"+suffix]
        mesh=ob.data
        assert mesh.uv_layers.active.name=="V8_7_GEODESIC_LEATHER_UV"
        assert len(mesh.materials)>=2,ob.name
        assert mesh.materials[1].name=="V8_7_Seat_Side_Return_Leather_PBR"
        before=(len(mesh.vertices),len(mesh.polygons))
        mesh.materials[0]=SEAT_MAT
        mesh.materials[1]=SIDE_MAT
        assert (len(mesh.vertices),len(mesh.polygons))==before
        assert any(p.material_index==1 for p in mesh.polygons)
        ob["DAYTONA_V8_8_MATERIAL_PASS"]="source BaseColor attenuation, tangent normal and ORM green remap"
        seat_stats[ob.name]={"vertices":before[0],"polygons":before[1],
           "uv":mesh.uv_layers.active.name,"side_returns_preserved":True}

# 13-station hand-modeled PMT-group018 envelope, respecting +/-106.83mm and
# max Z=518.87mm. Tail stays low under the original chrome H-shift mechanism;
# leading shoulder fits the measured 018 fascia instead of rising over controls.
stations=[
(-.44000,.069,.305,.379),(-.350,.074,.306,.388),
(-.275,.079,.307,.394),(-.23555,.080,.307,.409),
(-.205,.082,.306,.410),(-.125,.086,.308,.414),
(-.085,.089,.309,.407),(-.00592,.092,.312,.422),
(.055,.095,.316,.447),(.105,.099,.324,.481),
(.150,.102,.331,.496),(.185,.104,.336,.505),
(.20228,.105,.336,.508)]
assert len(stations)==13
assert max(abs(w) for y,w,bot,top in stations)<=PMT_CONSOLE_BOUNDS[1][0]
assert max(top for y,w,bot,top in stations)<PMT_CONSOLE_BOUNDS[1][2]
verts=[]
for y,w,bottom,top in stations:
    verts.extend([(-w,y,bottom),(-w,y,top-.019),(-w*.68,y,top),
                  (w*.68,y,top),(w,y,top-.019),(w,y,bottom)])
faces=[]
for j in range(len(stations)-1):
    for k in range(6):
        a=j*6+k
        b=j*6+(k+1)%6
        faces.append((a,b,b+6,a+6))
faces.extend((tuple(reversed(range(6))),
              tuple((len(stations)-1)*6+k for k in range(6))))
tunnel=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
old=tunnel.data
mesh=bpy.data.meshes.new("V8_8_PMT_CONSOLE_13_STATION_MESH")
mesh.from_pydata(verts,[],faces)
mesh.update(calc_edges=True)
recalc(mesh)
mesh.materials.append(CONSOLE_MAT)
tunnel.data=mesh
tunnel.location=(0,0,0)
tunnel.rotation_euler=(0,0,0)
tunnel.scale=(1,1,1)
if old.users==0:bpy.data.meshes.remove(old)
uv=mesh.uv_layers.new(name="V8_8_METRIC_CONSOLE_UV")
for poly in mesh.polygons:
    ids=[mesh.loops[li].vertex_index%6 for li in poly.loop_indices]
    wraps=0 in ids and 5 in ids and len(ids)==4
    for li in poly.loop_indices:
        vi=mesh.loops[li].vertex_index
        j,k=divmod(vi,6)
        y,w,bottom,top=stations[j]
        sect=[(-w,bottom),(-w,top-.019),(-w*.68,top),
              (w*.68,top),(w,top-.019),(w,bottom)]
        arc=[0.0]
        for ii in range(1,6):
            arc.append(arc[-1]+math.dist(sect[ii],sect[ii-1]))
        perimeter=arc[-1]+math.dist(sect[-1],sect[0])
        u=perimeter if wraps and k==0 else arc[k]
        uv.data[li].uv=(u*5.0,(y-stations[0][0])*5.0)
for m in list(tunnel.modifiers): tunnel.modifiers.remove(m)
be=tunnel.modifiers.new("V8.7 small console shoulder radius","BEVEL")
be.width=.0045
be.segments=3
be.limit_method="ANGLE"
be.angle_limit=math.radians(39)
wn=tunnel.modifiers.new("V8.7 console weighted normal","WEIGHTED_NORMAL")
wn.keep_sharp=True
tunnel["DAYTONA_GEOMETRY_PASS"]="v8.8 13-station PMT018 envelope with physical tangent UV"
tunnel["DAYTONA_PMT_CONSOLE_REFERENCE"]="group018 measured aggregate, not copied PMT"
for edge in ("LEFT","RIGHT"):
    old=bpy.data.objects["V8_6_TUNNEL_"+edge+"_CONTINUOUS_SEAM"]
    bpy.data.objects.remove(old,do_unlink=True)
for sign,edge in ((-1,"LEFT"),(1,"RIGHT")):
    pts=[(sign*w*.68,y,top+.0007) for y,w,bottom,top in stations]
    curve("V8_8_TUNNEL_"+edge+"_CONTINUOUS_SEAM",pts,THREAD,.00072)

fair=bpy.data.objects["V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"]
assert max(v.co.z for v in fair.data.vertices)<.58656
fair.data.materials.clear()
fair.data.materials.append(CONSOLE_MAT)
fair["DAYTONA_GEOMETRY_PASS"]="v8.8 fairing PBR continuous with measured console"
for n in ("V8_1_COMPACT_SHIFTER_LEATHER_DECK","V8_REAR_PADDED_ARMREST"):
    ob=bpy.data.objects[n]
    ob.data.materials.clear()
    ob.data.materials.append(CONSOLE_MAT)

assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
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
 "status":"V8_8_REAL_BLEND_SAVED_RENDER_VALIDATION_UNTESTED",
 "source_file":SOURCE.name,"source_sha256":SOURCE_SHA256,
 "new_file":DEST.name,
 "new_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "camera":scene.camera.name,
 "seat_existing_geometry_preserved":seat_stats,
 "seat_side_return_meshes":0,
 "seat_backrest_high_band_y_refit_m":0,
 "pmt_seat_aggregate":PMT_SEAT_BOUNDS,
 "pmt_console_aggregate":PMT_CONSOLE_BOUNDS,
 "tunnel_station_count":len(stations),
 "tunnel_uv":"V8_8_METRIC_CONSOLE_UV",
 "seat_uv_preserved":"V8_7_GEODESIC_LEATHER_UV",
 "packed_pbr_original_maps_retained":True,
 "original_gear_gauge_and_wheel_meshes_preserved":True,
 "render_validation":"UNTESTED",
 "original_game_files_modified":False,
 "game_runtime_validation":"UNTESTED",
 "Quest3_tested":False
}
(OUT/"DAYTONA_V8_8_BUILD_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("DAYTONA_V8_8_MODEL_SAVED",json.dumps(manifest),flush=True)
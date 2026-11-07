#!/usr/bin/env python3
"""Daytona 365 GTS/4 cockpit v8.7 actual Blender geometry/UV/PBR rework.

Input is the verified private v8.6 .blend, not a synthetic scene.
Original PMT material017 seat and material018 console coordinate ranges were
aggregated privately, then used as envelopes (never copied as source vertices).
Output is a NEW .blend; render status remains UNTESTED until separately run.
"""
import bpy
import bmesh
import hashlib
import json
import math
import os
from pathlib import Path
from mathutils import Vector

ROOT=Path(os.environ.get(
    "DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
OUT=ROOT/"blender_v8"
SOURCE=OUT/"Daytona365_Cockpit_Blender_PBR_v8_6.blend"
DEST=OUT/"Daytona365_Cockpit_Blender_PBR_v8_7.blend"
SOURCE_SHA256="cb0eba836a69b3154012bd755fafac92b92b223be0e9394a876c322123e1f2f4"

assert bpy.app.version>=(4,5,0),bpy.app.version_string
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve(),bpy.data.filepath
assert SOURCE.is_file() and hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
assert not DEST.exists(),"Do not replace a completed or partial v8.7 model"
scene=bpy.context.scene
assert scene.camera and scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert bpy.data.objects.get("V8_LOW_CENTER_TUNNEL")
assert bpy.data.objects.get("DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4")
assert bpy.data.objects.get("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH")
assert bpy.data.objects.get("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3")
assert bpy.data.objects.get("V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM")

# Original game's actual 184-vertex material017 seat object, aggregation of
# Blender world coordinates only: paired seats approx x=[-.57464,.57464],
# y=[-.72863,-.01985], z=[.33179,.85149]. The v8.6 left cushion ended
# at y=-.16457 and x=-.52518; this is a physical proportion discrepancy,
# not a reason to scale the whole vehicle.
PMT_SEAT_ENVELOPE={"max_abs_x":.57464,"front_y":-.01985,
                   "rear_y":-.72863,"low_z":.33179,"high_z":.85149}
PMT_CONSOLE_ENVELOPE={"max_abs_x":.10683,"min_y":-.23555,
                      "max_y":.20228,"max_z":.51887}
TAN=bpy.data.materials["V7_Target_Tan_Leather_PBR"]
DARK=bpy.data.materials["V8_6_Source_Measured_Console_Grain"]
METAL=bpy.data.materials["V7_Machined_Aluminum"]
THREAD=bpy.data.materials["V7_Stitch_Dark_Tan"]

def coll(name):
    o=bpy.data.collections.get(name)
    if o is None:
        o=bpy.data.collections.new(name)
        scene.collection.children.link(o)
    return o
SEAM=coll("V8.7 | native-contour conformal upholstery")
STRUCT=coll("V8.7 | source-constrained footwell and dash returns")

def clone_packed_pbr(src,name,rmin,rmax,normal,bump):
    assert name not in bpy.data.materials
    m=src.copy();m.name=name
    nt=m.node_tree;nodes=nt.nodes
    shader=nodes["Principled BSDF"]
    remap=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
    assert shader.inputs["Roughness"].is_linked
    assert shader.inputs["Normal"].is_linked
    assert remap.inputs["Value"].is_linked
    remap.inputs["To Min"].default_value=rmin
    remap.inputs["To Max"].default_value=rmax
    shader.inputs["Metallic"].default_value=0
    for n in nodes:
        if n.type=="NORMAL_MAP":
            n.inputs["Strength"].default_value=normal
        elif n.type=="BUMP":
            n.inputs["Strength"].default_value=bump
            n.inputs["Distance"].default_value=.00018
        elif n.type=="TEX_IMAGE" and n.image:
            assert n.image.packed_file,(name,n.image.name)
            n.extension="REPEAT"
            if any(t in n.image.name.upper() for t in ("ORM","NORMAL","HEIGHT")):
                assert n.image.colorspace_settings.name=="Non-Color"
    m["DAYTONA_V8_7_PACKED_PBR"]="source-linked BaseColor/Normal/ORM(G)/Height"
    m["DAYTONA_V8_7_ROUGHNESS_RANGE"]=[rmin,rmax]
    return m

SIDE=clone_packed_pbr(TAN,"V8_7_Seat_Side_Return_Leather_PBR",.67,.86,.21,.019)
KNEE=clone_packed_pbr(DARK,"V8_7_Knee_And_Footwell_PBR",.72,.89,.14,.013)

def curve(name,pts,mat=THREAD,radius=.00060,collection=SEAM):
    assert len(pts)>=3
    c=bpy.data.curves.new(name,"CURVE")
    c.dimensions="3D";c.resolution_u=12
    c.bevel_depth=radius;c.bevel_resolution=3
    s=c.splines.new("POLY");s.points.add(len(pts)-1)
    for p,xyz in zip(s.points,pts):
        p.co=(*xyz,1.0)
    o=bpy.data.objects.new(name,c)
    collection.objects.link(o)
    c.materials.append(mat)
    o["DAYTONA_V8_7"]="curves follow actual modified surface vertices"
    return o

def set_curve(name,coords):
    o=bpy.data.objects[name]
    s=o.data.splines[0]
    assert len(s.points)==len(coords),(name,len(s.points),len(coords))
    for p,v in zip(s.points,coords):
        p.co=(*v,1.0)

def smoothstep(a,b,t):
    v=max(0,min(1,(t-a)/(b-a)))
    return v*v*(3-2*v)

seat_names=[]
seat_dims={}
for side,cx in (("L",-.353),("R",.353)):
    for kind,ny in (("CUSHION",52),("BACKREST",58)):
        name="V8_"+side+("_CLASSIC_PADDED_CUSHION" if kind=="CUSHION" else "_TAPERED_PADDED_BACKREST")
        ob=bpy.data.objects[name]
        mesh=ob.data
        nx=72;ring=(nx+1)*(ny+1)
        assert len(mesh.vertices)==2*ring
        assert mesh.uv_layers.active.name=="V8_5_METRIC_UPHOLSTERY_UV"
        original_polys=len(mesh.polygons)
        for j in range(ny+1):
            t=j/ny
            for i in range(nx+1):
                k=j*(nx+1)+i
                p=mesh.vertices[k]
                rear=mesh.vertices[ring+k]
                a=abs(2*i/nx-1)
                if kind=="CUSHION":
                    # Width grows ~17%, nose grows 118 mm, gently from mid-
                    # cushion rather than translating the original seat pivot.
                    scale=1.17-.03*t
                    p.co.x=cx+(p.co.x-cx)*scale
                    p.co.y+=.118*smoothstep(.25,1,t)
                    p.co.z+=.011*math.exp(-((a-.80)/.15)**2)*math.sin(math.pi*t)**.8
                    # Five restrained transverse stitched leather pleats.
                    for kline in (.16,.32,.48,.64,.80):
                        p.co.z-=.0020*math.exp(-((t-kline)/.024)**2)*max(0,1-a*a)
                    rear.co=(p.co.x,p.co.y+.006,p.co.z-.049)
                else:
                    # Upper shoulders widened close to measured original
                    # material017 extent; recenter stays on original pivot.
                    scale=1.14+.19*smoothstep(.10,.92,t)
                    p.co.x=cx+(p.co.x-cx)*scale
                    p.co.y-=.009*smoothstep(.60,1,t)
                    p.co.y-=.010*math.exp(-((a-.80)/.15)**2)*math.sin(math.pi*t)**.8
                    for kline in (.19,.38,.57,.76):
                        p.co.y+=.0022*math.exp(-((t-kline)/.027)**2)*max(0,1-a*a)
                    rear.co=(p.co.x,p.co.y+.054,p.co.z-.004)
        mesh.update()
        assert len(mesh.polygons)==original_polys

        def top(j,i):
            q=mesh.vertices[j*73+i].co
            return (float(q.x),float(q.y),float(q.z))
        # Physical geodesic length UV: rather than scaling the prior UV
        # coordinates after reshaping, measure the actual updated surface.
        # 5.45 repeat per metre gives approximately 2.2x2.8 leather grain.
        unroll=[[0]*(nx+1) for _ in range(ny+1)]
        vroll=[[0]*(nx+1) for _ in range(ny+1)]
        for j in range(ny+1):
            for i in range(nx+1):
                if i:
                    unroll[j][i]=unroll[j][i-1]+math.dist(top(j,i),top(j,i-1))
                if j:
                    vroll[j][i]=vroll[j-1][i]+math.dist(top(j,i),top(j-1,i))
        new_uv=mesh.uv_layers.get("V8_7_GEODESIC_LEATHER_UV")
        assert new_uv is None
        new_uv=mesh.uv_layers.new(name="V8_7_GEODESIC_LEATHER_UV")
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                vi=mesh.loops[li].vertex_index%ring
                j,i=divmod(vi,nx+1)
                new_uv.data[li].uv=(unroll[j][i]*5.45,vroll[j][i]*5.45)
        mesh.uv_layers.active=new_uv

        # The front edge and actual two-thickness side returns are real
        # connected polygons, not painted-on disconnected floating meshes.
        # Assign a second packed PBR material to the outer 9-column strips.
        idx=mesh.materials.find(SIDE.name)
        if idx<0:
            mesh.materials.append(SIDE)
            idx=len(mesh.materials)-1
        sidefaces=0
        for poly in mesh.polygons:
            cols=[(mesh.loops[li].vertex_index%ring)%(nx+1) for li in poly.loop_indices]
            if max(cols)<=9 or min(cols)>=nx-9:
                poly.material_index=idx
                sidefaces+=1
        assert sidefaces>100

        # Reproject every v8.5 seam/welt, then v8.6 inset strips, without
        # leaving stale curves at previous surface coordinates.
        for edge,i in (("LEFT",3),("RIGHT",nx-3)):
            coords=[top(j,i) for j in range(1,ny)]
            coords=[(x,y-.0012,z) if kind=="BACKREST" else (x,y,z+.0012) for x,y,z in coords]
            set_curve("V8_5_"+side+"_"+kind+"_"+edge+"_WELT",coords)
        for fraction in (.23,.48,.72):
            j=round(fraction*ny)
            pts=[top(j,i) for i in range(11,nx-10)]
            pts=[(x,y-.0011,z) if kind=="BACKREST" else (x,y,z+.0011) for x,y,z in pts]
            set_curve("V8_5_"+side+"_"+kind+"_STITCH_"+format(fraction,".2f"),pts)
        for edge,i in (("LEFT",14),("RIGHT",nx-14)):
            pts=[top(j,i) for j in range(5,ny-4)]
            pts=[(x,y-.0013,z) if kind=="BACKREST" else (x,y,z+.0013) for x,y,z in pts]
            set_curve("V8_6_"+side+"_"+kind+"_INSET_"+edge+"_BOLSTER_SEAM",pts)
        if kind=="CUSHION":
            j=ny
            curve("V8_7_"+side+"_FRONT_CUSHION_APRON_WELT",
                  [(x,y,z+.0014) for x,y,z in (top(j,i) for i in range(4,nx-3))],
                  SIDE,.0011)
            for frac in (.16,.32,.64,.80):
                j=round(frac*ny)
                curve("V8_7_"+side+"_PLEATED_CUSHION_STITCH_"+format(frac,".2f"),
                    [(x,y,z+.0011) for x,y,z in (top(j,i) for i in range(13,nx-12))],
                    THREAD,.00045)
        else:
            for frac in (.19,.38,.57,.76):
                j=round(frac*ny)
                curve("V8_7_"+side+"_PLEATED_BACKREST_STITCH_"+format(frac,".2f"),
                      [(x,y-.0011,z) for x,y,z in (top(j,i) for i in range(13,nx-12))],
                      THREAD,.00046)
        ob["DAYTONA_V8_7_GEOMETRY_PASS"]="source envelope seats: in-place width, forward cushion, pleat, joined returns"
        ob["DAYTONA_V8_7_UV"]="5.45 per-metre geodesic 2D tangential lengths"
        ob["DAYTONA_V8_7_PMT_MEASURE_REFERENCE"]="material017 aggregated bounds; not copied mesh"
        seat_names.append(name)
        xs=[p.co.x for p in mesh.vertices[:ring]]
        ys=[p.co.y for p in mesh.vertices[:ring]]
        zs=[p.co.z for p in mesh.vertices[:ring]]
        seat_dims[name]={"x_range":[round(min(xs),5),round(max(xs),5)],
                         "y_range":[round(min(ys),5),round(max(ys),5)],
                         "z_range":[round(min(zs),5),round(max(zs),5)],
                         "side_return_polygons":sidefaces}
        assert all(math.isfinite(v) for q in mesh.vertices for v in q.co)
        assert max(abs(min(xs)),abs(max(xs)))<.59
        assert max(ys)<0.0 and min(ys)>-.75
        assert max(zs)<.88

# Place the source-backed dash/footwell return behind the actual original
# physical switchbank and clear of the authentic pedal contact surfaces.
# Two slim sculpted panels, not a single full-width obstruction.
def make_mesh(name,verts,faces,material):
    me=bpy.data.meshes.new(name+"_Mesh")
    me.from_pydata(verts,[],faces)
    me.update(calc_edges=True)
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(me);bm.free()
    uv=me.uv_layers.new(name="V8_7_FOOTWELL_METRIC_UV")
    for poly in me.polygons:
        for li in poly.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(p.x*4.2,p.z*4.2)
        poly.use_smooth=True
    me.materials.append(material)
    ob=bpy.data.objects.new(name,me);STRUCT.objects.link(ob)
    s=ob.modifiers.new("V8.7 footwell formed sheet","SOLIDIFY")
    s.thickness=.008;s.offset=-1
    be=ob.modifiers.new("V8.7 rounded sheet lip","BEVEL")
    be.width=.0025;be.segments=3
    wn=ob.modifiers.new("V8.7 normal weighting","WEIGHTED_NORMAL")
    wn.keep_sharp=True
    ob["DAYTONA_V8_7"]="native dashboard y/z envelope, new editable mesh and physical UV"
    return ob

for side,sgn in (("L",-1),("R",1)):
    xs=[.205,.288,.375,.470,.575,.696]
    zs=[.445,.480,.517,.551,.569]
    vs=[]
    for z in zs:
        for x in xs:
            # A slight lateral concavity leaves center console and pedals
            # visible while carrying a dark original-style knee return.
            mid=(x-.205)/(.696-.205)
            y=.173+.015*mid+.046*(.569-z)/(.569-.445)
            y+=.004*math.sin(math.pi*mid)
            vs.append((sgn*x,y,z+.005*math.sin(math.pi*mid)))
    faces=[]
    for j in range(len(zs)-1):
        for i in range(len(xs)-1):
            a=j*len(xs)+i
            faces.append((a,a+1,a+1+len(xs),a+len(xs)))
    o=make_mesh("V8_7_"+side+"_SCULPTED_UNDERDASH_KNEE_RETURN",vs,faces,KNEE)
    assert min(p[2] for p in vs)>.44 and max(p[2] for p in vs)<.58
    assert min(abs(p[0]) for p in vs)>.19
    seam=[vs[(len(zs)-1)*len(xs)+i] for i in range(len(xs))]
    curve("V8_7_"+side+"_KNEE_RETURN_TOP_PIPING",seam,KNEE,.0011,STRUCT)

# Reprofile the previously oversquare steering pedestal-to-floor transition
# only at the LOWER fairing junction; do not change native switchbank or gauges.
fairing=bpy.data.objects["V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"]
assert fairing.type=="MESH" and len(fairing.data.vertices)==16
before=len(fairing.data.polygons)
for v in fairing.data.vertices:
    # Narrow taper toward the console; keep max Z < original physical
    # source switchbank lower bound 0.58656 m.
    a=max(0,min(1,(v.co.z-.505)/(.584-.505)))
    v.co.x*=.92+.06*a
    v.co.y-=.003*(1-a)
fairing.data.update()
assert len(fairing.data.polygons)==before
assert max(v.co.z for v in fairing.data.vertices)<.58656
fairing["DAYTONA_V8_7"]="convergent source-measured lower panel without switch obstruction"

# Narrow chrome footwell transition is kept below native controls, and
# physically placed ahead of the existing padded dashboard.
curve("V8_7_LOWER_CENTER_STACK_JOINT",[
 (-.122,.164,.570),(-.061,.161,.571),(.0,.160,.571),
 (.061,.161,.571),(.122,.164,.570)],METAL,.0008,STRUCT)

scene.render.engine="CYCLES"
scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.view_settings.exposure=-.52
for img in bpy.data.images:
    if img.source=="FILE" and not img.packed_file:
        img.pack()
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.is_file()
report={
 "status":"DAYTONA_V8_7_ACTUAL_BLENDER_SAVED_RENDER_UNTESTED",
 "source":SOURCE.name,"source_sha256":SOURCE_SHA256,
 "new_file":DEST.name,"new_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "native_PMT_material017_aggregate_envelope":PMT_SEAT_ENVELOPE,
 "native_PMT_material018_aggregate_envelope":PMT_CONSOLE_ENVELOPE,
 "seat_shell_count":len(seat_names),"seat_geometry_bounds":seat_dims,
 "seat_geodesic_uv":True,"real_connected_side_returns_pbr":True,
 "cushion_front_extended":True,"existing_curve_seams_synced":True,
 "two_underdash_formed_sheets_with_uv":True,
 "source_controls_unmodified":True,
 "basecolor_normal_orm_height_packed":True,
 "same_reference_camera":scene.camera.name,
 "original_game_files_modified":False,"OVC_created":False,
 "Quest3_tested":False,"render_validation":"UNTESTED",
 "full_resolution_render":"UNTESTED","game_runtime":"UNTESTED"
}
(OUT/"DAYTONA_V8_7_BUILD_MANIFEST.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_7_MODEL_SAVED",json.dumps(report),flush=True)

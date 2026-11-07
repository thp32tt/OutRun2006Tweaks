#!/usr/bin/env python3
"""Ferrari Daytona 365 GTS/4 v8.8 authentic-PMT-silhouette headrest and seat pads.

Input verified private v8.7 Blender scene. The original game material017
upper-seat z/y/x aggregate is a spatial constraint, not source mesh output.
Creates two true 3D headrest upholstery lofts plus sculpted cushion channels
and resamples their physical geodesic tangent-UV/preserved packed normal/ORM.
No game/OVC integration, no unverified render claim.
"""
import bpy, bmesh, math, hashlib, json, os
from pathlib import Path
from mathutils import Vector
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_7.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_8.blend"
EXPECTED="e247abed67d15b5562daa5374163cc4c3a18de7dd059bfc42d94c9227e0e61a3"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
assert not DEST.exists(),"Never overwrite verified/pending v8.8 model"
scene=bpy.context.scene
assert scene.camera and scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert bpy.data.objects.get("DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4")
assert bpy.data.objects.get("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH")
assert bpy.data.objects.get("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3")
assert bpy.data.objects.get("V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM")
TAN=bpy.data.materials["V7_Target_Tan_Leather_PBR"]
SIDE=bpy.data.materials["V8_7_Seat_Side_Return_Leather_PBR"]
THREAD=bpy.data.materials["V7_Stitch_Dark_Tan"]

def collection(name):
 col=bpy.data.collections.get(name)
 if col is None:
  col=bpy.data.collections.new(name)
  scene.collection.children.link(col)
 return col
COL=collection("V8.8 | original PMT headrest silhouette + sculpted cushion")

def headrest_material():
 name="V8_8_Headrest_Leather_PBR"
 assert name not in bpy.data.materials
 m=SIDE.copy();m.name=name
 nodes=m.node_tree.nodes
 bsdf=nodes["Principled BSDF"]
 assert bsdf.inputs["Roughness"].is_linked and bsdf.inputs["Normal"].is_linked
 remap=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
 assert remap.inputs["Value"].is_linked
 remap.inputs["To Min"].default_value=.64
 remap.inputs["To Max"].default_value=.83
 bsdf.inputs["Metallic"].default_value=0
 for n in nodes:
  if n.type=="NORMAL_MAP":n.inputs["Strength"].default_value=.22
  elif n.type=="BUMP":
   n.inputs["Strength"].default_value=.019
   n.inputs["Distance"].default_value=.00018
  elif n.type=="TEX_IMAGE" and n.image:
   assert n.image.packed_file
   n.extension="REPEAT"
   if any(q in n.image.name.upper() for q in ("ORM","NORMAL","HEIGHT")):
    assert n.image.colorspace_settings.name=="Non-Color"
 m["DAYTONA_V8_8"]="retained packed source BaseColor, tangent Normal, ORM green roughness and Height"
 return m
HEADMAT=headrest_material()

def mesh_obj(name,verts,faces,mat):
 mesh=bpy.data.meshes.new(name+"_Mesh")
 mesh.from_pydata(verts,[],faces);mesh.update(calc_edges=True)
 bm=bmesh.new();bm.from_mesh(mesh)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(mesh);bm.free()
 mesh.materials.append(mat)
 ob=bpy.data.objects.new(name,mesh);COL.objects.link(ob)
 for p in mesh.polygons:p.use_smooth=True
 return ob

def stitch(name,coords,mat=THREAD,r=.0009):
 assert len(coords)>=3
 c=bpy.data.curves.new(name,"CURVE")
 c.dimensions="3D";c.bevel_depth=r;c.bevel_resolution=3
 c.resolution_u=12
 spl=c.splines.new("POLY");spl.points.add(len(coords)-1)
 for p,q in zip(spl.points,coords):p.co=(*q,1.0)
 obj=bpy.data.objects.new(name,c);COL.objects.link(obj)
 c.materials.append(mat)
 return obj

def patch_curve(name,coords):
 ob=bpy.data.objects[name]
 spline=ob.data.splines[0]
 assert len(spline.points)==len(coords),(name,len(spline.points),len(coords))
 for p,v in zip(spline.points,coords):p.co=(*v,1)

# The actual original PMT material017 back/head segment at Z=[.75,.851]
# has left X[-.54831,-.13604], Y[-.72863,-.65045]. Construct an
# independently editable, soft-edged 7-section upholstered crown near that
# envelope; do not transfer original PMT verts or user game DDS pixels.
# Smooth wedge loft; rectangular upper shoulder, broad forward cushion
# projecting about 1 cm, not a simple sphere or unrelated AI generated mesh.
headrest_rings=[
 (.713,.132,-.666,-.626),
 (.744,.170,-.717,-.658),
 (.769,.188,-.731,-.651),
 (.794,.195,-.735,-.650),
 (.824,.190,-.733,-.652),
 (.847,.175,-.724,-.657),
 (.865,.124,-.706,-.681)
]
assert len(headrest_rings)==7
headrests=[]
for side,cx in (("L",-.353),("R",.353)):
 verts=[]
 for z,half,front,rear in headrest_rings:
  verts.extend([
   (cx-half,front,z),(cx+half,front,z),
   (cx+half,rear,z),(cx-half,rear,z)])
 faces=[]
 for j in range(len(headrest_rings)-1):
  for k in range(4):
   a=j*4+k;b=j*4+(k+1)%4
   faces.append((a,b,b+4,a+4))
 faces.extend((tuple(reversed(range(4))),
   tuple((len(headrest_rings)-1)*4+k for k in range(4))))
 head=mesh_obj("V8_8_"+side+"_INTEGRATED_PADDED_HEADREST",verts,faces,HEADMAT)
 uv=head.data.uv_layers.new(name="V8_8_METRIC_HEADREST_UV")
 # Physical x/y/z coordinates are naturally metres; preserve ~5.45
 # texture repeats/metre in front and rear bands and along endcaps.
 for poly in head.data.polygons:
  n=poly.normal
  for li in poly.loop_indices:
   p=head.data.vertices[head.data.loops[li].vertex_index].co
   u=p.x if abs(n.y)>.5 else p.y
   uv.data[li].uv=(u*5.45,p.z*5.45)
 head.data.uv_layers.active=uv
 bev=head.modifiers.new("V8.8 soft-sculpted headrest corners","BEVEL")
 bev.width=.008;bev.segments=4
 wn=head.modifiers.new("V8.8 upholstery normals","WEIGHTED_NORMAL")
 wn.keep_sharp=True
 head["DAYTONA_V8_8"]="source-envelope original seat upper silhouette, editable soft upholstery"
 head["DAYTONA_PMT_MATERIAL017_UPPER_Z"]=[.75,.85149]
 assert all(math.isfinite(q) for v in head.data.vertices for q in v.co)
 assert abs(cx)+max(r[1] for r in headrest_rings)<.58
 assert -.75<min(r[2] for r in headrest_rings)<-.72
 assert max(r[0] for r in headrest_rings)<.88
 headrests.append(head.name)
 for edge,k in (("LEFT",-1),("RIGHT",1)):
  points=[(cx+k*half,front-.0010,z) for z,half,front,rear in headrest_rings[1:-1]]
  stitch("V8_8_"+side+"_HEADREST_"+edge+"_SEAM",points,THREAD,.0007)
 # Front center horizontal welt follows the genuine shaped headrest face
 idx=3
 z,h,f,b=headrest_rings[idx]
 stitch("V8_8_"+side+"_HEADREST_FRONT_HORIZ_WELT",
        [(cx-h+2*h*i/32,f-.0012,z+.002*math.sin(math.pi*i/32)) for i in range(33)],
        THREAD,.00048)

# Refine the original v8.7 72x52 source shell, not a floating new cushion:
# five broad leather sections have distinct 4-mm crests, with low-relief
# inter-section crease, tangent-UV recalculated along actual new contour.
seat_names=[]
for side in ("L","R"):
 ob=bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"]
 me=ob.data
 nx,ny=72,52;ring=73*53
 assert len(me.vertices)==2*ring
 assert me.uv_layers.active.name=="V8_7_GEODESIC_LEATHER_UV"
 for j in range(ny+1):
  t=j/ny
  for i in range(nx+1):
   k=j*73+i
   a=abs(2*i/nx-1)
   p=me.vertices[k]
   orig=me.vertices[ring+k]
   center=max(0,1-(a/.80)**2)**1.4
   crest=sum(.0042*math.exp(-((t-x)/.075)**2) for x in (.135,.315,.495,.675,.855))
   p.co.z+=crest*center
   orig.co=(p.co.x,p.co.y+.006,p.co.z-.049)
 me.update()
 assert len(me.vertices)==2*ring
 def vtx(j,i):
  p=me.vertices[j*73+i].co
  return (float(p.x),float(p.y),float(p.z))
 # Recompute physical geodesic length after actual sculpt operation.
 us=[[0.0]*73 for _ in range(53)]
 vs=[[0.0]*73 for _ in range(53)]
 for j in range(53):
  for i in range(73):
   if i:us[j][i]=us[j][i-1]+math.dist(vtx(j,i),vtx(j,i-1))
   if j:vs[j][i]=vs[j-1][i]+math.dist(vtx(j,i),vtx(j-1,i))
 uv=me.uv_layers.new(name="V8_8_RESCULPTED_GEODESIC_UV")
 for poly in me.polygons:
  for li in poly.loop_indices:
   vi=me.loops[li].vertex_index%ring
   j,i=divmod(vi,73)
   uv.data[li].uv=(us[j][i]*5.45,vs[j][i]*5.45)
 me.uv_layers.active=uv
 for edge,i in (("LEFT",3),("RIGHT",69)):
  points=[vtx(j,i) for j in range(1,ny)]
  patch_curve("V8_5_"+side+"_CUSHION_"+edge+"_WELT",
             [(x,y,z+.0012) for x,y,z in points])
 for frac in (.23,.48,.72):
  j=round(frac*ny)
  patch_curve("V8_5_"+side+"_CUSHION_STITCH_"+format(frac,".2f"),
              [(x,y,z+.0011) for x,y,z in (vtx(j,i) for i in range(11,nx-10))])
 for edge,i in (("LEFT",14),("RIGHT",nx-14)):
  patch_curve("V8_6_"+side+"_CUSHION_INSET_"+edge+"_BOLSTER_SEAM",
              [(x,y,z+.0013) for x,y,z in (vtx(j,i) for j in range(5,ny-4))])
 for frac in (.16,.32,.64,.80):
  j=round(frac*ny)
  patch_curve("V8_7_"+side+"_PLEATED_CUSHION_STITCH_"+format(frac,".2f"),
              [(x,y,z+.0011) for x,y,z in (vtx(j,i) for i in range(13,nx-12))])
 j=ny
 patch_curve("V8_7_"+side+"_FRONT_CUSHION_APRON_WELT",
             [(x,y,z+.0014) for x,y,z in (vtx(j,i) for i in range(4,nx-3))])
 ob["DAYTONA_V8_8"]="surface-sculpted broad seat pads, retained source shell, updated physical UV"
 seat_names.append(ob.name)

scene.render.engine="CYCLES"
scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.view_settings.exposure=-.52
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
for img in bpy.data.images:
 if img.source=="FILE" and not img.packed_file:img.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.is_file()
manifest={
 "status":"DAYTONA_V8_8_MODEL_SAVED_RENDER_UNTESTED",
 "source":SOURCE.name,"source_sha256":EXPECTED,
 "new_file":DEST.name,"new_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "headrest_new_true_meshes":headrests,
 "headrest_original_PMT_aggregate_reference":"object00_group01_material017_a0 upper Z .75-.851, X/Y envelope",
 "real_headrest_loft_sections":len(headrest_rings),
 "original_cushion_shells_refined":seat_names,
 "original_cushion_topology_preserved":True,
 "real_cushion_pleat_geometry":True,
 "geodesic_UV_after_resculpt":True,
 "source_packed_pbr_basecolor_normal_orm_height":True,
 "original_gauges_controls_shift_gate_preserved":True,
 "camera":scene.camera.name,
 "render_validation":"UNTESTED","full_resolution_render":"UNTESTED",
 "game_runtime":"UNTESTED","OVC_created":False,
 "original_game_files_modified":False,"Quest3_tested":False}
(W/"DAYTONA_V8_8_BUILD_MANIFEST.json").write_text(json.dumps(manifest,indent=2))
print("DAYTONA_V8_8_MODEL_SAVED",json.dumps(manifest),flush=True)

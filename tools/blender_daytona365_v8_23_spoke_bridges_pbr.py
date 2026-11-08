#!/usr/bin/env python3
"""Daytona365 v8.23: in-place original-reference 3 steering-spoke bridges.

The three existing v7.3 8v/6f rectangular wheel-rim connector helpers are
replaced with physically closed, smoothly tapered, 14x16 forged-metal lofts.
The native original-game 61v stamped spokes, original Ferrari emblem and
factory rim remain BYTE-GEOMETRY IDENTICAL. Measurements from the source
wheel scene bound these newly formed additions, not copied source polygons.
"""
import bpy, bmesh, hashlib, json, math, os, struct, zlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
"/home/chatgpt-runner/work_handoff/daytona365_v823_ai2_20261108"))
W=ROOT/"blender_v8"
SRC=W/"Daytona365_Cockpit_Blender_PBR_v8_22_r2.blend"
DST=W/"Daytona365_Cockpit_Blender_PBR_v8_23.blend"
NORMAL=W/"Daytona365_v8_23_Stamped_Spoke_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_23_BUILD_MANIFEST.json"
SHA="30ddcbd01ef7e969bb1e4220ff4318c2f75b7fd7ab70bc4d6dafedcdc7954437"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SRC.resolve()
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA
for p in (DST,NORMAL,MANIFEST):assert not p.exists(),str(p)
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==111
def mesh_sha(ob):
 me=ob.data
 return hashlib.sha256(repr((
 [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in me.vertices],
 [(p.material_index,tuple(p.vertices)) for p in me.polygons])).encode()).hexdigest()
# The base factory mesh, existing enhanced rim, v8.21-r2 shaft and gauge,
# v8.22-r2 shifter, all original controls and all prior seat and door shapes
# must not be modified by the current incremental geometry operation.
protected=(
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0",
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material002_a0",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V7_SHORT_SHAFT_AT_WHEEL_HUB",
 "V8_21_SOURCE_LOWER_GAUGE_SHROUD",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT",
 "V5_MANUAL_SHIFTER_CHROME_SHAFT",
 "V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
 "V8_LOW_CENTER_TUNNEL",
 "V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
 "V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST",
 "V8_19_L_DASH_DOOR_FORMED_ENDCAP","V8_19_R_DASH_DOOR_FORMED_ENDCAP",
 "V6_L_BLENDER_BLACK_FLOOR_MAT","V6_R_BLENDER_BLACK_FLOOR_MAT")
native=bpy.data.objects[protected[0]]
assert len(native.data.vertices)==61 and len(native.data.polygons)==31
signature={n:mesh_sha(bpy.data.objects[n]) for n in protected}
# Light isotropic brushed-metal micro normal, generated analytically and
# packed alongside the original procedural machined-aluminium material.
def pngchunk(tag,data):
 return (struct.pack(">I",len(data))+tag+data+
 struct.pack(">I",zlib.crc32(tag+data)&0xffffffff))
def cl(x):return min(1.,max(0.,x))
N=256;rows=[]
for j in range(N):
 v=(j+.5)/N;scan=bytearray((0,))
 for i in range(N):
  u=(i+.5)/N
  dx=.009*math.cos(24*math.pi*u)*math.cos(8*math.pi*v)
  dy=.016*math.sin(24*math.pi*u)*math.sin(8*math.pi*v)
  s=math.sqrt(1+dx*dx+dy*dy)
  scan.extend((round(255*cl(.5-.5*dx/s)),
               round(255*cl(.5-.5*dy/s)),
               round(255*cl(.5+.5/s)),255))
 rows.append(bytes(scan))
NORMAL.write_bytes(b"\x89PNG\r\n\x1a\n"+
 pngchunk(b"IHDR",struct.pack(">IIBBBBB",N,N,8,6,0,0,0))+
 pngchunk(b"IDAT",zlib.compress(b"".join(rows),9))+pngchunk(b"IEND",b""))
n_sha=hashlib.sha256(NORMAL.read_bytes()).hexdigest()
img=bpy.data.images.load(str(NORMAL),check_existing=False)
img.name="V8_23_Stamped_Spoke_Packed_Tangent_Normal"
img.colorspace_settings.name="Non-Color";img.pack()
assert img.packed_file and tuple(img.size)==(256,256)
base=bpy.data.materials["V7_Machined_Aluminum"]
assert base.use_nodes
mat=base.copy();mat.name="V8_23_Source_Linked_Brushed_Spoke_Aluminum"
nt=mat.node_tree;n=nt.nodes;l=nt.links
bsdf=n.get("Principled BSDF")
assert bsdf and bsdf.inputs["Normal"].is_linked
bsdf.inputs["Metallic"].default_value=.82
bsdf.inputs["Roughness"].default_value=.31
bsdf.inputs["Anisotropic"].default_value=.095
bump=n.get("V8_BrushedMetalNormal")
assert bump and bump.inputs["Height"].is_linked
assert bump.outputs["Normal"].is_linked
bump.inputs["Strength"].default_value=.029
bump.inputs["Distance"].default_value=.00007
uv=n.new("ShaderNodeUVMap");uv.name="V8_23_Aligned_Stamped_Spoke_UV"
uv.uv_map="V8_23_Aligned_Spoke_Tangent_Normal_UV"
tex=n.new("ShaderNodeTexImage")
tex.name="V8_23_Packed_Stamped_Spoke_Tangent_Normal"
tex.image=img;tex.interpolation="Linear";tex.extension="REPEAT"
nm=n.new("ShaderNodeNormalMap");nm.name="V8_23_Spoke_Analytical_Normal_Map"
nm.space="TANGENT";nm.inputs["Strength"].default_value=.17
l.new(uv.outputs["UV"],tex.inputs["Vector"])
l.new(tex.outputs["Color"],nm.inputs["Color"])
l.new(nm.outputs["Normal"],bump.inputs["Normal"])
assert bump.inputs["Normal"].is_linked
STATIONS=14;AROUND=16
expected={
 "LEFT":((-0.5215,-0.4445),(-.294,-.286),(.7795,.8005)),
 "RIGHT":((-.2555,-.1785),(-.294,-.286),(.7795,.8005)),
 "LOWER":((-.36,-.34),(-.295,-.287),(.6205,.6975))}
results={}
for which in ("LEFT","RIGHT","LOWER"):
 name="V7_3_"+which+"_SHORT_CHROME_SPOKE_BRIDGE"
 ob=bpy.data.objects[name]
 assert ob.type=="MESH" and ob.data.users==1
 assert len(ob.data.vertices)==8 and len(ob.data.polygons)==6
 assert ob.data.materials[0]==base
 world0=[ob.matrix_world@v.co for v in ob.data.vertices]
 extents=[(min(v[i] for v in world0),max(v[i] for v in world0)) for i in range(3)]
 for i in range(3):
  assert abs(extents[i][0]-expected[which][i][0])<.000015
  assert abs(extents[i][1]-expected[which][i][1])<.000015
 axis=2 if which=="LOWER" else 0
 amin,amax=extents[axis]
 length=amax-amin
 assert abs(length-.077)<.00001
 minor=0 if which=="LOWER" else 2
 c_minor=sum(extents[minor])*.5
 half_width=(extents[minor][1]-extents[minor][0])*.5
 c_depth=sum(extents[1])*.5
 half_depth=(extents[1][1]-extents[1][0])*.5
 inv=ob.matrix_world.inverted()
 verts=[];world_verts=[]
 for j in range(STATIONS):
  u=j/(STATIONS-1)
  # The outer rim-facing end becomes slimmer than the native-spoke
  # overlap end; left side runs OUTER->INNER, right INNER->OUTER,
  # bottom OUTER->INNER. Source boxes remain the hard envelope.
  progress=u if which in ("LEFT","LOWER") else (1-u)
  smooth=progress*progress*(3-2*progress)
  width_ratio=.73+.24*smooth
  depth_ratio=.77+.18*smooth
  # shallow shape crown; no new protrusion outside original source
  yshift=-.00018*math.sin(math.pi*u)
  centre_along=amin+length*u
  for k in range(AROUND):
   a=2*math.pi*k/AROUND
   # softly rounded cross section gives physically modeled perimeter
   # not a bevel-only shader fake. Continuity across all 13 segments.
   cross=half_width*width_ratio*math.cos(a)
   depth=half_depth*depth_ratio*math.sin(a)
   if axis==0:
    wp=Vector((centre_along,c_depth+yshift+depth,c_minor+cross))
   else:
    wp=Vector((c_minor+cross,c_depth+yshift+depth,centre_along))
   world_verts.append(wp)
   verts.append(tuple(inv@wp))
 faces=[]
 for j in range(STATIONS-1):
  for k in range(AROUND):
   a=j*AROUND+k;b=j*AROUND+(k+1)%AROUND
   faces.append((a,b,b+AROUND,a+AROUND))
 faces.append(tuple(reversed(range(AROUND))))
 faces.append(tuple((STATIONS-1)*AROUND+k for k in range(AROUND)))
 assert len(verts)==224 and len(faces)==210
 new=bpy.data.meshes.new(name+"_V8_23_Physically_Tapered_Loft")
 new.from_pydata(verts,[],faces);new.update(calc_edges=True)
 bm=bmesh.new();bm.from_mesh(new)
 assert all(len(e.link_faces)==2 for e in bm.edges)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(new);bm.free()
 for p in new.polygons:p.use_smooth=(p.index<len(faces)-2)
 metric=new.uv_layers.new(name="V8_23_Metric_Stamped_Spoke_UV")
 aligned=new.uv_layers.new(name="V8_23_Aligned_Spoke_Tangent_Normal_UV")
 for poly in new.polygons:
  for li in poly.loop_indices:
   vi=new.loops[li].vertex_index
   station=vi//AROUND;k=vi%AROUND
   along=station/(STATIONS-1)
   across=k/AROUND
   if poly.index<(STATIONS-1)*AROUND and poly.index%AROUND==AROUND-1 and k==0:
    across=1.
   # A real metric length with circumferential s-distance; do not
   # reuse screen/pixel coordinates as mapping units.
   metric.data[li].uv=(float(along*length*5.45),
                        float(across*(2*math.pi*half_width)*5.45))
   aligned.data[li].uv=(float(along),float(across))
 new.uv_layers.active=metric
 new.materials.append(mat)
 old=ob.data;ob.data=new
 if old.users==0:bpy.data.meshes.remove(old)
 for mod in ob.modifiers:
  if mod.type=="BEVEL":
   mod.width=.00055;mod.segments=2
   mod.limit_method="ANGLE";mod.angle_limit=math.radians(30)
 ob["DAYTONA_V8_23"]="in-place source-envelope tapered 14-station forged-metal spoke bridge; original factory spokes untouched"
 after=[ob.matrix_world@v.co for v in new.vertices]
 for axis_i,(mn,mx) in enumerate(extents):
  assert min(v[axis_i] for v in after)>=mn-.00002,(name,axis_i)
  assert max(v[axis_i] for v in after)<=mx+.00002,(name,axis_i)
 assert all(math.isfinite(float(x)) for p in new.vertices for x in p.co)
 assert all(math.isfinite(float(x)) for uv_layer in new.uv_layers for elem in uv_layer.data for x in elem.uv)
 results[which]={"object":name,"old_vertices":8,"old_faces":6,
 "new_vertices":len(new.vertices),"new_faces":len(new.polygons),
 "closed_manifold":True,"within_original_source_helper_bounds":True,
 "loft_stations":STATIONS,"cross_section_sides":AROUND,
 "world_bounds":[[round(min(p[i] for p in after),7),round(max(p[i] for p in after),7)] for i in range(3)]}
for n,h in signature.items():assert mesh_sha(bpy.data.objects[n])==h,n
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==111
for image in bpy.data.images:
 if image.source=="FILE" and not image.packed_file:image.pack()
scene=bpy.context.scene
scene.render.engine="CYCLES";scene.cycles.samples=10
scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.view_settings.exposure=-.52
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DST),compress=True)
report={
 "status":"DAYTONA_V8_23_REAL_BLENDER_SAVED",
 "input":SRC.name,"input_sha256":SHA,
 "output":DST.name,"output_sha256":hashlib.sha256(DST.read_bytes()).hexdigest(),
 "bytes":DST.stat().st_size,"blender":bpy.app.version_string,
 "spoke_bridges":results,"mesh_count":113,"curve_count":111,
 "native_factory_61v_spoke_and_4v_emblem_unchanged":True,
 "v822_boot_v821_shroud_hub_v820_mats_and_seats_unchanged":True,
 "new_analytical_normal":NORMAL.name,
 "normal_sha256":n_sha,
 "source_machined_metal_material_retained_procedural_bump":True,
 "new_packed_tangent_normal_in_metal_material":True,
 "original_game_modified":False,"OVC_created":False,
 "Quest3_tested":False,"render_validation":"UNTESTED",
 "original_full_resolution_sample_matched":"UNTESTED"}
MANIFEST.write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_23_MODEL_SAVED",json.dumps(report),flush=True)
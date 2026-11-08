#!/usr/bin/env python3
"""Ferrari 365 GTS/4 v8.21 genuine hub-column relief + lower gauge shroud.

Blender mesh geometry only. Measured original wheel and gauge source envelopes
are guardrails, not copied/recovered PMT vertices. Preserve existing native wheel
spokes/emblem/rim, source gauge geometry, switches, seats and v8.20 floor mats.
"""
import bpy,bmesh,hashlib,json,math,os,struct,zlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v821_ai2_20261108"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_20.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_21_r2.blend"
NORMAL=W/"Daytona365_v8_21_r2_Gauge_Shroud_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_21_R2_BUILD_MANIFEST.json"
SOURCE_SHA="1c0244e4933b343647de2a8ec19e0ef68660cc9f4607f6208399176dd9380d5d"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
for p in (DEST,NORMAL,MANIFEST):assert not p.exists(),p
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==112
assert sum(o.type=="CURVE" for o in bpy.data.objects)==108
def clamp(t):return max(0.,min(1.,t))
def smooth(a,b,x):
 t=clamp((x-a)/(b-a))
 return t*t*(3-2*t)
def mesh_sha(ob):
 me=ob.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in me.vertices],
  [(p.material_index,tuple(p.vertices)) for p in me.polygons])).encode()).hexdigest()
protected=(
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0",
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material002_a0",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES",
 "V8_5_CURVED_COLUMN_COWL","V8_5_STEERING_SHAFT",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
 "V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
 "V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
 "V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST",
 "V8_19_L_DASH_DOOR_FORMED_ENDCAP",
 "V8_19_R_DASH_DOOR_FORMED_ENDCAP",
 "V6_L_BLENDER_BLACK_FLOOR_MAT","V6_R_BLENDER_BLACK_FLOOR_MAT")
unchanged={n:mesh_sha(bpy.data.objects[n]) for n in protected}
gauges=bpy.data.objects["DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH"]
metal=bpy.data.objects["DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY"]
gauge_min_z=min((gauges.matrix_world @ v.co).z for v in gauges.data.vertices)
metal_min_z=min((metal.matrix_world @ v.co).z for v in metal.data.vertices)
assert .740<gauge_min_z<.742 and .739<metal_min_z<.741
# Actual original PMT object22 wheel centre spans X(-.466,-.234),
# Y approximately -.287 and Z(.679,.829); the wheel objects are unchanged.
spoke=bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"]
assert len(spoke.data.vertices)==61 and len(spoke.data.polygons)==31
# Replace only the older helper shaft cylinder in place, not PMT wheel geometry.
shaft=bpy.data.objects["V7_SHORT_SHAFT_AT_WHEEL_HUB"]
assert shaft.type=="MESH" and len(shaft.data.vertices)==40
assert len(shaft.data.polygons)==22 and shaft.data.users==1
assert shaft.data.materials[0].name=="V7_Machined_Aluminum"
old_world=[shaft.matrix_world@v.co for v in shaft.data.vertices]
assert -.288<min(p.y for p in old_world)<-.285
assert -.25<max(p.y for p in old_world)<-.24
nring=14;around=16
inv=shaft.matrix_world.inverted()
vertices=[]
for j in range(nring):
 t=j/(nring-1)
 y=-.274+.075*t
 centre_z=.7835-.0350*t+.002*math.sin(math.pi*t)
 radius=(.0198*(1-t)+.0128*t)*(1+.075*math.sin(math.pi*t))
 # subtly shaped metal collar, smooth rolled shoulder, no original wheel modifications
 for k in range(around):
  theta=2*math.pi*k/around
  x=-.35+radius*math.cos(theta)
  z=centre_z+radius*.77*math.sin(theta)
  vertices.append(tuple(inv@Vector((x,y,z))))
faces=[]
for j in range(nring-1):
 for k in range(around):
  a=j*around+k;b=j*around+(k+1)%around
  faces.append((a,b,b+around,a+around))
faces.extend([tuple(reversed(range(around))),
 tuple((nring-1)*around+k for k in range(around))])
new=bpy.data.meshes.new("V8_21_Source_Wheel_Hub_Tapered_Shaft")
new.from_pydata(vertices,[],faces);new.update(calc_edges=True)
bm=bmesh.new();bm.from_mesh(new)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
bm.to_mesh(new);bm.free()
for p in new.polygons:p.use_smooth=True
new.materials.append(shaft.data.materials[0])
uv=new.uv_layers.new(name="V8_21_Hub_Metric_Tangent_UV")
for face in new.polygons:
 for li in face.loop_indices:
  v=shaft.matrix_world @ new.vertices[new.loops[li].vertex_index].co
  uv.data[li].uv=(5.45*(float(v.y)+.274),5.45*(float(v.z)-.70))
old=shaft.data
shaft.data=new
if old.users==0:bpy.data.meshes.remove(old)
for mod in shaft.modifiers:
 if mod.type=="BEVEL":mod.width=.0012;mod.segments=2
assert len(new.vertices)==224 and len(new.polygons)==210
tip=[shaft.matrix_world@v.co for v in new.vertices[-around:]]
oldshaft=bpy.data.objects["V8_5_STEERING_SHAFT"]
existing=[oldshaft.matrix_world@v.co for v in oldshaft.data.vertices]
tip_gap=min((a-b).length for a in tip for b in existing)
assert tip_gap<.06,tip_gap
# Generate independent analytic 256px tangent micro-normal; source maps preserved.
def pngchunk(tag, data):
 return struct.pack(">I",len(data))+tag+data+struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
N=256;raw=[]
for row in range(N):
 v=(row+.5)/N;line=bytearray((0,))
 for col in range(N):
  u=(col+.5)/N
  dx=.013*math.cos(16*math.pi*u)*math.sin(10*math.pi*v)
  dy=.018*math.sin(16*math.pi*u)*math.cos(10*math.pi*v)
  length=math.sqrt(1+dx*dx+dy*dy)
  line.extend((round(255*clamp(.5-.5*dx/length)),
   round(255*clamp(.5-.5*dy/length)),
   round(255*clamp(.5+.5/length)),255))
 raw.append(bytes(line))
NORMAL.write_bytes(b"\x89PNG\r\n\x1a\n"+
 pngchunk(b"IHDR",struct.pack(">IIBBBBB",N,N,8,6,0,0,0))+
 pngchunk(b"IDAT",zlib.compress(b"".join(raw),9))+
 pngchunk(b"IEND",b""))
normal_sha=hashlib.sha256(NORMAL.read_bytes()).hexdigest()
img=bpy.data.images.load(str(NORMAL),check_existing=False)
img.name="V8_21_Gauge_Shroud_Packed_Tangent_Normal"
img.colorspace_settings.name="Non-Color";img.pack()
assert tuple(img.size)==(256,256) and img.packed_file
base=bpy.data.materials["V8_17_Source_Packed_Dark_Dashboard_PBR"]
mat=base.copy()
mat.name="V8_21_Source_Packed_Lower_Gauge_Shroud_PBR"
nodes=mat.node_tree.nodes
bsdf=nodes["Principled BSDF"]
assert all(bsdf.inputs[k].is_linked for k in ("Base Color","Normal","Roughness"))
nodes["V8_17_Original_Dash_Charcoal_Value"].inputs["Value"].default_value=.245
nodes["V8_17_Original_Dash_Charcoal_Value"].inputs["Saturation"].default_value=.78
rr=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
rr.inputs["To Min"].default_value=.83;rr.inputs["To Max"].default_value=.94
bsdf.inputs["Metallic"].default_value=0
nodes["Normal Map"].inputs["Strength"].default_value=.15
nd=nodes["V8_17_Packed_Cowl_Tangent_Normal"]
nd.name="V8_21_Packed_Shroud_Tangent_Normal";nd.image=img
uvnode=nodes["V8_17_Aligned_Cowl_Tangent_UV_Node"]
uvnode.name="V8_21_Shroud_Normal_UV_Node"
uvnode.uv_map="V8_21_Shroud_Aligned_Tangent_Normal_UV"
mix=nodes["V8_17_Source_And_Cowl_Normal_Mix"]
mix.name="V8_21_Source_And_Shroud_Normal_Mix"
mix.inputs[0].default_value=.12
for node in nodes:
 if node.type=="BUMP":
  node.inputs["Strength"].default_value=.011
  node.inputs["Distance"].default_value=.00012
 if node.type=="TEX_IMAGE" and node.image:
  assert node.image.packed_file
  if any(v in node.image.name.upper() for v in ("NORMAL","ORM","HEIGHT")):
   assert node.image.colorspace_settings.name=="Non-Color"
assert nodes["Normal Map"].inputs["Color"].links[0].from_node==mix
packed=[n.image.name for n in nodes if n.type=="TEX_IMAGE" and n.image]
assert len(packed)>=5 and any("ORM" in p.upper() for p in packed)
# 21 gauge-width stations with a formed closed 8-perimeter cross-section,
# physically separate from already completed v8.17 upper cowl.
shroud_name="V8_21_SOURCE_LOWER_GAUGE_SHROUD"
assert not bpy.data.objects.get(shroud_name)
nx=21;perimeter=8
formed=[]
for i in range(nx):
 t=i/(nx-1);x=-.63+.568*t
 crest=.0022*math.sin(math.pi*t)
 # all upper rim vertices remain below BOTH original gauge atlas and bezel bottoms
 profile=((.169,.716),(.171,.729),(.183,.735),(.191,.731),
          (.201,.724),(.200,.710),(.182,.706),(.169,.710))
 for y,z in profile:
  formed.append((x,y,z+crest))
fs=[]
for i in range(nx-1):
 for j in range(perimeter):
  a=i*perimeter+j
  b=i*perimeter+(j+1)%perimeter
  fs.append((a,b,b+perimeter,a+perimeter))
fs.extend((tuple(reversed(range(perimeter))),
 tuple((nx-1)*perimeter+j for j in range(perimeter))))
me=bpy.data.meshes.new(shroud_name+"_Physical")
me.from_pydata(formed,[],fs);me.update(calc_edges=True)
bm=bmesh.new();bm.from_mesh(me)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
bm.to_mesh(me);bm.free()
for poly in me.polygons:poly.use_smooth=True
metric=me.uv_layers.new(name="V8_21_Shroud_Metric_Tangent_UV")
aligned=me.uv_layers.new(name="V8_21_Shroud_Aligned_Tangent_Normal_UV")
metric=me.uv_layers["V8_21_Shroud_Metric_Tangent_UV"]
aligned=me.uv_layers["V8_21_Shroud_Aligned_Tangent_Normal_UV"]
for poly in me.polygons:
 for li in poly.loop_indices:
  v=me.vertices[me.loops[li].vertex_index].co
  metric.data[li].uv=(float(v.x)*5.45,float(v.y)*5.45)
  aligned.data[li].uv=(clamp((float(v.x)+.63)/.568),
                       clamp((float(v.z)-.700)/.045))
me.uv_layers.active=metric;me.materials.append(mat)
shroud=bpy.data.objects.new(shroud_name,me)
for c in gauges.users_collection:c.objects.link(shroud)
assert len(me.vertices)==168 and len(me.polygons)==162
max_z=max(v.co.z for v in me.vertices)
assert max_z<metal_min_z-.00001 and max_z<gauge_min_z-.00001
assert min(v.co.z for v in me.vertices)>.700
for layer in (metric,aligned):
 assert all(math.isfinite(float(v)) for p in layer.data for v in p.uv)
# Genuine 3D leather welt follows under-gauge front face and curvature.
welt="V8_21_SOURCE_LOWER_GAUGE_SHROUD_WELT"
cu=bpy.data.curves.new(welt+"_PhysicalCurve","CURVE")
cu.dimensions="3D";cu.bevel_depth=.00052;cu.bevel_resolution=3
sp=cu.splines.new("POLY");sp.points.add(nx-1)
for i in range(nx):
 v=me.vertices[i*perimeter+7].co
 sp.points[i].co=(float(v.x),float(v.y)-.0015,float(v.z)+.0004,1.)
cu.materials.append(mat)
curve=bpy.data.objects.new(welt,cu)
for coll in shroud.users_collection:coll.objects.link(curve)
for n,h in unchanged.items():assert mesh_sha(bpy.data.objects[n])==h,n
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==109
for im in bpy.data.images:
 if im.source=="FILE" and not im.packed_file:im.pack()
scene.render.engine="CYCLES";scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.view_settings.exposure=-.52
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
report={
 "status":"DAYTONA_V8_21_REAL_BLENDER_SAVED",
 "source":SOURCE.name,"source_sha256":SOURCE_SHA,
 "output":DEST.name,"output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "reprofiled_existing_hub_shaft":shaft.name,"old_shaft_vertices":40,"old_shaft_faces":22,
 "new_shaft_vertices":224,"new_shaft_faces":210,
 "native_shaft_alignment_gap_m":round(tip_gap,6),
 "original_native_spokes_rim_emblem_unchanged":True,
 "new_lower_gauge_shroud":shroud.name,"shroud_vertices":168,"shroud_faces":162,
 "source_metal_bezel_min_z_m":float(metal_min_z),
 "source_gauge_atlas_min_z_m":float(gauge_min_z),
 "formed_shroud_max_z_m":max_z,
 "new_shroud_welt":welt,"shroud_3d_welt_points":nx,
 "new_packed_analytical_normal":NORMAL.name,
 "normal_sha256":normal_sha,"source_packed_PBR":packed,
 "mesh_count":113,"curve_count":109,
 "all_protected_source_mesh_geometry_preserved":True,
 "original_game_modified":False,"OVC_created":False,"Quest3_tested":False,
 "render_validation":"UNTESTED","matched_PMT_full_resolution":"UNTESTED"}
MANIFEST.write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_21_MODEL_SAVED",json.dumps(report),flush=True)
#!/usr/bin/env python3
"""Daytona365 v8.17: physically formed instrument cowl, shaped dashboard shell and
source-linked packed dark-leather PBR. Reference PMT image is a visual guide only:
no inference of exact original PMT dashboard vertex positions or in-game support."""
import bpy,bmesh,math,os,hashlib,json,struct,zlib
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v817_ai2_0917_gpt6"))/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_16.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_17.blend"
NORMAL=W/"Daytona365_v8_17_Cowl_Analytical_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_17_BUILD_MANIFEST.json"
SOURCE_SHA="d0f3406886262359e9c079ee7eeb122d9a9ac5739d5ffb9148055c9422ee77da"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
for f in (DEST,NORMAL,MANIFEST): assert not f.exists(),f
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==106
assert sum(o.type=="CURVE" for o in bpy.data.objects)==98
assert bpy.data.objects.get("V8_17_ORIGINAL_GUIDED_GAUGE_COWL") is None
def clamp(t):return max(0.,min(1.,t))
def smooth(a,b,x):
 t=clamp((x-a)/(b-a));return t*t*(3-2*t)
def sha_mesh(obj):
 m=obj.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in m.vertices],
 [(p.material_index,tuple(p.vertices)) for p in m.polygons])).encode()).hexdigest()
unchanged={n:sha_mesh(bpy.data.objects[n]) for n in (
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH","DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
 "V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST")}
# Actual analytical fine-grain tangent normal in PNG, not a game-derived texture.
def png_chunk(tag,payload):
 return struct.pack(">I",len(payload))+tag+payload+struct.pack(">I",zlib.crc32(tag+payload)&0xffffffff)
N=256
data=[]
for j in range(N):
 v=(j+.5)/N;row=bytearray([0])
 for i in range(N):
  u=(i+.5)/N
  sx=.014*math.cos(20*math.pi*u)*math.sin(10*math.pi*v)
  sy=.010*math.sin(20*math.pi*u)*math.cos(10*math.pi*v)
  l=math.sqrt(1+sx*sx+sy*sy)
  row.extend([round(255*clamp(.5-.5*sx/l)),round(255*clamp(.5-.5*sy/l)),round(255*clamp(.5+.5/l)),255])
 data.append(bytes(row))
NORMAL.write_bytes(b"\x89PNG\r\n\x1a\n"+
 png_chunk(b"IHDR",struct.pack(">IIBBBBB",N,N,8,6,0,0,0))+
 png_chunk(b"IDAT",zlib.compress(b"".join(data),9))+
 png_chunk(b"IEND",b""))
norm_sha=hashlib.sha256(NORMAL.read_bytes()).hexdigest()
img=bpy.data.images.load(str(NORMAL),check_existing=False)
img.name="V8_17_Cowl_Packed_Analytical_Tangent_Normal"
img.colorspace_settings.name="Non-Color";img.pack()
assert img.packed_file and tuple(img.size)==(N,N)
# Copy instead of changing baseline material datablocks.
mat=bpy.data.materials["V7_Target_Black_Dashboard_PBR"].copy()
mat.name="V8_17_Source_Packed_Dark_Dashboard_PBR"
nodes=mat.node_tree.nodes;links=mat.node_tree.links
bsdf=nodes["Principled BSDF"]
assert bsdf.inputs["Base Color"].is_linked and bsdf.inputs["Roughness"].is_linked and bsdf.inputs["Normal"].is_linked
color_socket=bsdf.inputs["Base Color"].links[0].from_socket
hsv=nodes.new("ShaderNodeHueSaturation");hsv.name="V8_17_Original_Dash_Charcoal_Value"
hsv.inputs["Saturation"].default_value=.92
hsv.inputs["Value"].default_value=.43
links.new(color_socket,hsv.inputs["Color"])
links.new(hsv.outputs["Color"],bsdf.inputs["Base Color"])
rng=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
rng.inputs["To Min"].default_value=.68
rng.inputs["To Max"].default_value=.86
bsdf.inputs["Metallic"].default_value=0
nm=nodes["Normal Map"]
assert nm.inputs["Color"].is_linked
old=nm.inputs["Color"].links[0].from_socket
nm.inputs["Strength"].default_value=.27
detail_uv=nodes.new("ShaderNodeUVMap")
detail_uv.name="V8_17_Aligned_Cowl_Tangent_UV_Node"
detail_uv.uv_map="V8_17_Cowl_Tangent_Normal_UV"
detail=nodes.new("ShaderNodeTexImage");detail.name="V8_17_Packed_Cowl_Tangent_Normal"
detail.image=img;links.new(detail_uv.outputs["UV"],detail.inputs["Vector"])
mix=nodes.new("ShaderNodeMixRGB");mix.name="V8_17_Source_And_Cowl_Normal_Mix"
mix.blend_type="MIX";mix.inputs[0].default_value=.14
links.new(old,mix.inputs[1]);links.new(detail.outputs["Color"],mix.inputs[2])
links.new(mix.outputs["Color"],nm.inputs["Color"])
for n in nodes:
 if n.type=="BUMP":
  n.inputs["Strength"].default_value=.013;n.inputs["Distance"].default_value=.00015
 if n.type=="TEX_IMAGE" and n.image:
  assert n.image.packed_file,(n.name,n.image.name)
  if any(k in n.image.name.upper() for k in ("NORMAL","ORM","HEIGHT")):
   assert n.image.colorspace_settings.name=="Non-Color"
packed=[n.image.name for n in nodes if n.type=="TEX_IMAGE" and n.image]
assert len(packed)>=5 and any("ORM" in p.upper() for p in packed)
# Sculpt the actual incumbent continuous dashboard shell *in place*.
shell=bpy.data.objects["V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL"]
mesh=shell.data
assert len(mesh.vertices)==1495 and len(mesh.polygons)==2816
before=[tuple(v.co) for v in mesh.vertices]
count=0;max_delta=0.
for v in mesh.vertices:
 x,y,z=v.co
 window=smooth(-.68,-.54,x)*(1-smooth(-.14,-.04,x))
 depth=smooth(.187,.235,y)*(1-smooth(.345,.47,y))
 dz=.008*window*depth
 if dz>.0001:
  v.co.z+=dz;count+=1;max_delta=max(max_delta,dz)
assert count>75 and max_delta>.006
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
for p in mesh.polygons:p.use_smooth=True
# Keep every incumbent UV layer; add metric UV for new packed normal inspection.
for name in ("V8_17_Dashboard_Source_Metric_UV","V8_17_Cowl_Tangent_Normal_UV"):
 assert mesh.uv_layers.get(name) is None
metric=mesh.uv_layers.new(name="V8_17_Dashboard_Source_Metric_UV")
align=mesh.uv_layers.new(name="V8_17_Cowl_Tangent_Normal_UV")
for poly in mesh.polygons:
 for li in poly.loop_indices:
  v=mesh.vertices[mesh.loops[li].vertex_index].co
  metric.data[li].uv=(float(v.x)*4.,float(v.y)*4.)
  align.data[li].uv=(clamp((float(v.x)+.635)/.585),clamp((float(v.y)-.185)/.375))
mesh.uv_layers.active=metric
assert len(mesh.materials)==1
mesh.materials[0]=mat
face=bpy.data.objects["V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE"]
assert len(face.data.vertices)==1885 and len(face.data.polygons)==3584
front_before=sha_mesh(face)
face.data.materials[0]=mat
# 65 lateral stations x 5 longitudinal top stations, 4.5mm side and bottom returns.
L=65;R=5;X0=-.635;X1=-.05
yy=[.141,.158,.176,.202,.229]
zz=[.917,.923,.932,.940,.946]
extra=[.008,.011,.014,.011,.003]
points=[]
for bottom in (False,True):
 for j,y in enumerate(yy):
  for i in range(L):
   u=i/(L-1);x=X0+(X1-X0)*u
   crown=max(0.,1-((2*u-1)**2))
   z=zz[j]+extra[j]*crown-(.0045 if bottom else 0.)
   points.append((x,y,z))
K=L*R
faces=[]
for side in range(2):
 off=side*K
 for j in range(R-1):
  for i in range(L-1):
   a=off+j*L+i;b=a+1;c=a+L+1;d=a+L
   faces.append((a,b,c,d) if side==0 else (d,c,b,a))
for j in range(R-1):
 for edge in (0,L-1):
  a=j*L+edge;b=(j+1)*L+edge
  faces.append((a,b,b+K,a+K) if edge==L-1 else (b,a,a+K,b+K))
for i in range(L-1):
 for j in (0,R-1):
  a=j*L+i;b=a+1
  faces.append((b,a,a+K,b+K) if j==0 else (a,b,b+K,a+K))
newmesh=bpy.data.meshes.new("V8_17_Gauge_Cowl_Formed_Solid")
newmesh.from_pydata(points,[],faces);newmesh.update(calc_edges=True)
newobj=bpy.data.objects.new("V8_17_ORIGINAL_GUIDED_GAUGE_COWL",newmesh)
for collection in shell.users_collection:collection.objects.link(newobj)
newmesh.materials.append(mat)
arc=newmesh.uv_layers.new(name="V8_17_Cowl_Metric_Tangent_UV")
normal_uv=newmesh.uv_layers.new(name="V8_17_Cowl_Tangent_Normal_UV")
for p in newmesh.polygons:
 for li in p.loop_indices:
  v=newmesh.vertices[newmesh.loops[li].vertex_index].co
  arc.data[li].uv=(float(v.x)*4.,float(v.y)*4.)
  normal_uv.data[li].uv=(clamp((float(v.x)-X0)/(X1-X0)),clamp((float(v.y)-yy[0])/(yy[-1]-yy[0])))
newmesh.uv_layers.active=arc
bm=bmesh.new();bm.from_mesh(newmesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(newmesh);bm.free()
for p in newmesh.polygons:p.use_smooth=True
# Real edge curve follows new front cowl instead of the inherited flat x-station rim.
rim=bpy.data.objects["V6_BLENDER_INSTRUMENT_COWL_ROUNDED_LEATHER_EDGE"]
assert rim.type=="CURVE" and len(rim.data.splines)==1
s=rim.data.splines[0]
assert s.type=="POLY" and len(s.points)==65
for i,p in enumerate(s.points):
 u=i/64.;x=X0+(X1-X0)*u
 crown=max(0.,1-(2*u-1)**2)
 p.co=(x,.138,.916+extra[0]*crown,1.)
rim.data.materials[0]=mat
newobj["DAYTONA_V8_17"]="Physical solid gauge hood, source-bounded by existing native dash/gauge geometry; not native PMT topology"
bounds=[[min(v.co[k] for v in newmesh.vertices),max(v.co[k] for v in newmesh.vertices)] for k in range(3)]
assert -0.636<=bounds[0][0]<bounds[0][1]<=-.049
assert .140<=bounds[1][0]<bounds[1][1]<=.230
assert .912<=bounds[2][0]<bounds[2][1]<=.958
assert all(math.isfinite(float(d)) for v in newmesh.vertices for d in v.co)
for name,digest in unchanged.items():assert sha_mesh(bpy.data.objects[name])==digest,name
assert sha_mesh(face)==front_before
assert sum(o.type=="MESH" for o in bpy.data.objects)==107
assert sum(o.type=="CURVE" for o in bpy.data.objects)==98
scene.render.engine="CYCLES";scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.view_settings.exposure=-.52
for im in bpy.data.images:
 if im.source=="FILE" and not im.packed_file:im.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
report={"status":"DAYTONA_V8_17_REAL_BLENDER_SAVED","source":SOURCE.name,
 "source_sha256":SOURCE_SHA,"output":DEST.name,
 "output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "cowl_object":newobj.name,"cowl_vertices":len(newmesh.vertices),
 "cowl_polygons":len(newmesh.polygons),"cowl_bounds_m":bounds,
 "sculpted_original_dash_vertices":count,"max_original_dash_lift_m":max_delta,
 "original_gauges_switches_seats_gate_unchanged":True,
 "new_packed_tangent_normal":NORMAL.name,"tangent_normal_sha256":norm_sha,
 "source_packed_material_images":packed,
 "matched_full_resolution":"UNTESTED","OVC_game_Quest3":"UNTESTED",
 "render_validation":"UNTESTED","private_original_pmt_unchanged":True}
MANIFEST.write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_17_MODEL_SAVED",json.dumps(report),flush=True)
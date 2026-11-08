#!/usr/bin/env python3
"""Ferrari Daytona 365 GTS/4 v8.18: actual physical original-switchbank
side surrounds, lower source fairing and in-place recessed center fascia.

The original photo-mapped 70-vertex switchbank, real gauges, v8.17 cowl,
native shifter and already completed v8.13-v8.16 seats remain unchanged.
Source-image PMT measurements are envelope constraints, not original PMT
vertex claims; source-packed PBR/normal/ORM/height stay connected.
"""
import bpy,bmesh,hashlib,json,math,os,struct,zlib
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v818_ai2_0926"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_17.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_18_r2.blend"
NORMAL=W/"Daytona365_v8_18_r2_Switch_Surround_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_18_R2_BUILD_MANIFEST.json"
SOURCE_SHA="fcbe1755599de7a67af43bf7497f8889a756cb5e529efc031ccb1279e3abf1c7"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
for p in (DEST,NORMAL,MANIFEST):assert not p.exists(),p
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==107
assert sum(o.type=="CURVE" for o in bpy.data.objects)==98
def clamp(x):return min(1.,max(0.,x))
def smooth(a,b,x):
 t=clamp((x-a)/(b-a));return t*t*(3-2*t)
def gauss(x,c,w):return math.exp(-((x-c)/w)**2)
def mesh_sha(ob):
 me=ob.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in me.vertices],
 [(p.material_index,tuple(p.vertices)) for p in me.polygons])).encode()).hexdigest()
protected=(
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
 "V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST")
unchanged={name:mesh_sha(bpy.data.objects[name]) for name in protected}
bank=bpy.data.objects["DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4"]
assert len(bank.data.vertices)==70 and len(bank.data.polygons)==96
bank_bnd=[[min(p.co[k] for p in bank.data.vertices),max(p.co[k] for p in bank.data.vertices)] for k in range(3)]
assert .141<bank_bnd[0][1]<.143
assert .586<bank_bnd[2][0]<.588 and .847<bank_bnd[2][1]<.849
# Existing contiguous V5 fascia is a regular 65x29 actual physical mesh.
pad=bpy.data.objects["V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE"]
me=pad.data
assert len(me.vertices)==1885 and len(me.polygons)==3584
assert me.materials[0].name=="V8_17_Source_Packed_Dark_Dashboard_PBR"
assert me.uv_layers.active.name=="UVMap"
before=[tuple(v.co) for v in me.vertices]
for v in me.vertices:
 x,y,z=v.co
 window=1-smooth(.105,.210,abs(float(x)))
 height=smooth(.635,.685,float(z))*(1-smooth(.827,.899,float(z)))
 v.co.y+=.0115*window*height
 v.co.z+=.0018*window*gauss(float(z),.741,.082)
me.update()
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
for p in me.polygons:p.use_smooth=True
sculpted=sum(math.dist(before[i],tuple(v.co))>1e-5 for i,v in enumerate(me.vertices))
assert sculpted>110,sculpted
# Existing lower-stack 16-vertex fairing is returned 3mm behind the new
# 3D sill and source controls, not removed or flattened.
fair=bpy.data.objects["V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"]
assert len(fair.data.vertices)==16 and len(fair.data.polygons)==14
fair_before=mesh_sha(fair)
for v in fair.data.vertices:
 if v.co.z>.560:
  v.co.y+=.003*smooth(.560,.584,float(v.co.z))
fair.data.update()
bm=bmesh.new();bm.from_mesh(fair.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
bm.to_mesh(fair.data);bm.free()
assert mesh_sha(fair)!=fair_before
# New independently generated 256px analytical tangent stitch/roll detail.
# Not exported from any original game texture: base source normal preserved.
def chunk(tag,data):
 return struct.pack(">I",len(data))+tag+data+struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
n=256;scan=[]
def smallheight(u,v):
 return .00034*(gauss(u,.19,.07)+gauss(u,.81,.07))*(
  .6+.4*math.cos(2*math.pi*8*v))
for j in range(n):
 v=(j+.5)/n;row=bytearray([0])
 for i in range(n):
  u=(i+.5)/n;step=1/n
  sx=(smallheight(clamp(u+step),v)-smallheight(clamp(u-step),v))/(2*step*.27)
  sy=(smallheight(u,clamp(v+step))-smallheight(u,clamp(v-step)))/(2*step*.32)
  norm=math.sqrt(1+sx*sx+sy*sy)
  row.extend(tuple(round(clamp((q+1)*.5)*255) for q in (-sx/norm,-sy/norm,1/norm))+(255,))
 scan.append(bytes(row))
png=(b"\x89PNG\r\n\x1a\n"+
 chunk(b"IHDR",struct.pack(">IIBBBBB",n,n,8,6,0,0,0))+
 chunk(b"IDAT",zlib.compress(b"".join(scan),9))+chunk(b"IEND",b""))
NORMAL.write_bytes(png);norm_sha=hashlib.sha256(png).hexdigest()
image=bpy.data.images.load(str(NORMAL),check_existing=False)
image.name="V8_18_SwitchStack_Packed_Tangent_Normal"
image.colorspace_settings.name="Non-Color";image.pack()
assert image.packed_file and tuple(image.size)==(n,n)
# Clone existing packed original dashboard material, do not replace original
# source photos or PBR nodes. Substitute only analytic extra normal.
mat=bpy.data.materials["V8_17_Source_Packed_Dark_Dashboard_PBR"].copy()
mat.name="V8_18_Source_BlackLeather_SwitchSurround_PBR"
nodes=mat.node_tree.nodes;links=mat.node_tree.links
bsdf=nodes["Principled BSDF"]
for k in ("Base Color","Normal","Roughness"):assert bsdf.inputs[k].is_linked,k
hsv=nodes["V8_17_Original_Dash_Charcoal_Value"]
hsv.inputs["Value"].default_value=.38
hsv.inputs["Saturation"].default_value=.86
rough=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
assert rough.inputs["Value"].is_linked
rough.inputs["To Min"].default_value=.77;rough.inputs["To Max"].default_value=.90
bsdf.inputs["Metallic"].default_value=0.
nm=nodes["Normal Map"];nm.inputs["Strength"].default_value=.19
detail=nodes["V8_17_Packed_Cowl_Tangent_Normal"];detail.image=image
detail.name="V8_18_Packed_Surround_Tangent_Normal"
uvnode=nodes["V8_17_Aligned_Cowl_Tangent_UV_Node"]
uvnode.uv_map="V8_18_Surround_Aligned_Normal_UV"
uvnode.name="V8_18_Aligned_Normal_UV_Node"
mix=nodes["V8_17_Source_And_Cowl_Normal_Mix"]
mix.name="V8_18_Source_And_Surround_Tangent_Normal_Mix"
mix.inputs[0].default_value=.20
for x in nodes:
 if x.type=="BUMP":
  x.inputs["Strength"].default_value=.013
  x.inputs["Distance"].default_value=.00014
 if x.type=="TEX_IMAGE" and x.image:
  assert x.image.packed_file,x.image.name
  if any(key in x.image.name.upper() for key in ("NORMAL","ORM","HEIGHT")):
   assert x.image.colorspace_settings.name=="Non-Color"
packed=[x.image.name for x in nodes if x.type=="TEX_IMAGE" and x.image]
assert len(packed)>=5 and any("ORM" in x.upper() for x in packed)
assert any("HEIGHT" in x.upper() for x in packed)
assert nm.inputs["Color"].links[0].from_node==mix
# Explicit detail UV for existing dashboard recessed center.
UV_DETAIL="V8_18_Surround_Aligned_Normal_UV"
UV_METRIC="V8_18_Surround_Metric_Tangent_UV"
paduv=me.uv_layers.new(name=UV_DETAIL)
for polygon in me.polygons:
 for li in polygon.loop_indices:
  p=me.vertices[me.loops[li].vertex_index].co
  paduv.data[li].uv=(clamp((float(p.x)+.20)/.40),clamp((float(p.z)-.585)/.30))
me.uv_layers.active=me.uv_layers["UVMap"]
me.materials.append(mat)
stack_faces=0
for face in me.polygons:
 midx=sum(me.vertices[k].co.x for k in face.vertices)/len(face.vertices)
 midz=sum(me.vertices[k].co.z for k in face.vertices)/len(face.vertices)
 if abs(midx)<.19 and .632<midz<.882:
  face.material_index=1;stack_faces+=1
assert stack_faces>300,stack_faces
fair.data.materials[0]=mat
def make_mesh(name,rings,material):
 assert not bpy.data.objects.get(name),name
 # Ring: 13 sections, each 8 true perimeter vertices; connected quads,
 # closed end caps, recalculated normals, metric tangent UV.
 assert len(rings)==13 and all(len(s)==8 for s in rings)
 verts=[p for ring in rings for p in ring]
 faces=[]
 for j in range(12):
  for k in range(8):
   a=j*8+k;b=j*8+(k+1)%8
   faces.append((a,b,b+8,a+8))
 faces.extend([tuple(reversed(range(8))),tuple(12*8+k for k in range(8))])
 mesh=bpy.data.meshes.new(name+"_FormedMesh")
 mesh.from_pydata(verts,[],faces);mesh.update(calc_edges=True)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(mesh);bm.free()
 for p in mesh.polygons:p.use_smooth=True
 metric=mesh.uv_layers.new(name=UV_METRIC)
 normaluv=mesh.uv_layers.new(name=UV_DETAIL)
 # Avoid Blender 4.5 RNA stale UV layer handles after adding another map:
 metric=mesh.uv_layers[UV_METRIC];normaluv=mesh.uv_layers[UV_DETAIL]
 for poly in mesh.polygons:
  for li in poly.loop_indices:
   v=mesh.vertices[mesh.loops[li].vertex_index].co
   metric.data[li].uv=(float(v.x)*5.45,float(v.z)*5.45)
   normaluv.data[li].uv=(clamp((float(v.x)+.20)/.40),
                              clamp((float(v.z)-.565)/.31))
 mesh.uv_layers.active=metric
 mesh.materials.append(material)
 ob=bpy.data.objects.new(name,mesh)
 for coll in pad.users_collection:coll.objects.link(ob)
 assert len(mesh.vertices)==104 and len(mesh.polygons)==98
 return ob
rails={}
for side,sgn in (("L",-1),("R",1)):
 rings=[]
 for j in range(13):
  t=j/12.;z=.586+.260*t
  front=.179+.0015*math.sin(math.pi*t)
  back=.215+.002*math.sin(math.pi*t)
  xy=[(.146,front+.009),(.148,front+.003),(.154,front),
      (.163,front+.003),(.166,.202),(.164,back),(.149,back),(.146,.199)]
  rings.append([(sgn*a,y,z) for a,y in xy])
 ob=make_mesh("V8_18_"+side+"_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN",rings,mat)
 rails[side]=ob
 # Inner and outer real leather stitch geometry, not painted screen marks.
 def physical_curve(name,k):
  assert not bpy.data.objects.get(name)
  cu=bpy.data.curves.new(name+"_Path","CURVE");cu.dimensions="3D"
  cu.resolution_u=12;cu.bevel_depth=.00040;cu.bevel_resolution=3
  spl=cu.splines.new("POLY");spl.points.add(12)
  for j,p in enumerate(spl.points):
   x,y,z=rings[j][k];p.co=(x,y-.001,z,1.)
  cu.materials.append(mat)
  c=bpy.data.objects.new(name,cu)
  for coll in ob.users_collection:coll.objects.link(c)
  return name
 physical_curve("V8_18_"+side+"_STACK_INNER_WELT",1)
 physical_curve("V8_18_"+side+"_STACK_OUTER_WELT",3)
# The only new cross-connecting source lower sill remains below genuine
# switchbank bottom z=.58656, joined visually to original lower fairing.
sill=[]
for j in range(13):
 t=j/12.;x=-.148+.296*t
 outline=[(.159,.575),(.158,.583),(.166,.585),(.193,.585),
          (.215,.580),(.216,.566),(.192,.564),(.163,.571)]
 sill.append([(x,y,z+.001*math.sin(math.pi*t)) for y,z in outline])
bottom=make_mesh("V8_18_SOURCE_SWITCHBANK_LOWER_MOLDED_SILL",sill,mat)
assert max(v.co.z for v in bottom.data.vertices)<bank_bnd[2][0]
# Side guards clear original switchbank horizontal silhouette by >=~4mm.
assert min(abs(v.co.x) for o in rails.values() for v in o.data.vertices)>.14205
for name,sig in unchanged.items():assert mesh_sha(bpy.data.objects[name])==sig,name
assert sum(o.type=="MESH" for o in bpy.data.objects)==110
assert sum(o.type=="CURVE" for o in bpy.data.objects)==102
assert all(math.isfinite(float(x)) for p in me.vertices for x in p.co)
for ob in [*rails.values(),bottom]:
 assert all(math.isfinite(float(x)) for p in ob.data.vertices for x in p.co)
 for mapname in (UV_METRIC,UV_DETAIL):
  assert all(math.isfinite(float(x)) for t in ob.data.uv_layers[mapname].data for x in t.uv)
pad["DAYTONA_V8_18"]="actual source-back original switchbank recessed fascia plus 3D side rails and lower sill"
scene.render.engine="CYCLES";scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.view_settings.exposure=-.52
for im in bpy.data.images:
 if im.source=="FILE" and not im.packed_file:im.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
report={"status":"DAYTONA_V8_18_R2_REAL_BLENDER_SAVED",
 "source":SOURCE.name,"source_sha256":SOURCE_SHA,
 "output":DEST.name,"output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "native_face_changed_vertices":sculpted,"native_face_vertices":1885,
 "stack_PBR_faces":stack_faces,"original_fairing_16_vertices_retained":True,
 "formed_rails":[rails[s].name for s in "LR"],
 "lower_sill":bottom.name,"each_new_mesh_vertices":104,"each_new_mesh_polygons":98,
 "new_3D_seam_curve_count":4,"mesh_count":110,"curve_count":102,
 "source_switch_bounds_m":bank_bnd,
 "source_controls_v817_cowl_v815_v816_seats_unchanged":True,
 "source_packed_images":packed,"new_packed_normal":NORMAL.name,
 "new_normal_sha256":norm_sha,"new_uv_metric":UV_METRIC,
 "new_uv_normal":UV_DETAIL,
 "original_game_modified":False,"OVC_created":False,"Quest3_tested":False,
 "render_validation":"UNTESTED","matched_full_resolution":"UNTESTED"}
MANIFEST.write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_18_R2_MODEL_SAVED",json.dumps(report),flush=True)
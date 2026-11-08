#!/usr/bin/env python3
"""Daytona 365 GTS/4 v8.20: real original-bounded horizontal footwell mats.

Reshape the SAME two 8-vertex V6 floor-mat objects into closed, physical
494-vertex / 492-face soft channel mats with genuine metric UV and packed
source-linked PBR. Preserve native metal pedal geometry, original floor,
all seats, door endcaps and dashboard. PMT image guides only visible intent.
No runtime assets, OVC or original proprietary geometry are published.
"""
import bpy,bmesh,hashlib,json,math,os,struct,zlib
from mathutils import Vector
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v820_ai2_102x"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_19_r2.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_20.blend"
NORMAL=W/"Daytona365_v8_20_Footwell_Aligned_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_20_BUILD_MANIFEST.json"
SOURCE_SHA="f018aee762f714f84fc3bec12991e217778d1eade598861511729bf901469300"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
for p in (DEST,NORMAL,MANIFEST):assert not p.exists(),p
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==112
assert sum(o.type=="CURVE" for o in bpy.data.objects)==106
def clamp(x):return max(0.,min(1.,x))
def smooth(a,b,x):
 t=clamp((x-a)/(b-a));return t*t*(3-2*t)
def mesh_sha(ob):
 me=ob.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in me.vertices],
 [(p.material_index,tuple(p.vertices)) for p in me.polygons])).encode()).hexdigest()
protected=(
 "V7_REAL_BLACK_CARPET_FLOOR","V8_3_DRIVER_PEDAL_FIREWALL",
 "V6_DRIVER_METAL_PEDAL_0","V6_DRIVER_METAL_PEDAL_1","V6_DRIVER_METAL_PEDAL_2",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "V8_18_L_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN",
 "V8_18_R_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN",
 "V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
 "V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST",
 "V8_19_L_DASH_DOOR_FORMED_ENDCAP","V8_19_R_DASH_DOOR_FORMED_ENDCAP")
signatures={n:mesh_sha(bpy.data.objects[n]) for n in protected}
# Analytical 256px normal detail independent of original game maps.
# Existing packed source normal/ORM/height remain attached to the clone.
def chunk(tag,data):
 return struct.pack(">I",len(data))+tag+data+struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
N=256;rows=[]
for j in range(N):
 v=(j+.5)/N;line=bytearray([0])
 for i in range(N):
  u=(i+.5)/N
  envelope=smooth(.025,.12,u)*(1.-smooth(.88,.975,u))
  dx=.022*math.sin(14*math.pi*u)*math.sin(16*math.pi*v)
  dy=.030*envelope*math.sin(14*math.pi*u)*math.cos(16*math.pi*v)
  norm=math.sqrt(1.+dx*dx+dy*dy)
  line.extend([round(255*clamp(.5-dx/(2*norm))),
               round(255*clamp(.5-dy/(2*norm))),
               round(255*clamp(.5+.5/norm)),255])
 rows.append(bytes(line))
NORMAL.write_bytes(b"\x89PNG\r\n\x1a\n"+
 chunk(b"IHDR",struct.pack(">IIBBBBB",N,N,8,6,0,0,0))+
 chunk(b"IDAT",zlib.compress(b"".join(rows),9))+chunk(b"IEND",b""))
# Handle escaped literal in orchestration strings.
data=NORMAL.read_bytes()
assert data.startswith(b"\x89PNG\r\n\x1a\n")
normal_sha=hashlib.sha256(data).hexdigest()
img=bpy.data.images.load(str(NORMAL),check_existing=False)
img.name="V8_20_Footwell_Packed_Tangent_Normal"
img.colorspace_settings.name="Non-Color";img.pack()
assert img.packed_file and tuple(img.size)==(256,256)
base=bpy.data.materials["V8_19_Source_Dash_To_Door_Dark_PBR"]
mat=base.copy()
mat.name="V8_20_Source_Packed_Dark_Rubber_Footwell_PBR"
nd=mat.node_tree.nodes
bsdf=nd["Principled BSDF"]
for k in ("Base Color","Normal","Roughness"):assert bsdf.inputs[k].is_linked,k
nd["V8_17_Original_Dash_Charcoal_Value"].inputs["Value"].default_value=.28
nd["V8_17_Original_Dash_Charcoal_Value"].inputs["Saturation"].default_value=.78
r=nd["V8_5_ORM_ROUGHNESS_RANGE"]
assert r.inputs["Value"].is_linked
r.inputs["To Min"].default_value=.80;r.inputs["To Max"].default_value=.94
bsdf.inputs["Metallic"].default_value=0.
nd["Normal Map"].inputs["Strength"].default_value=.25
nd["V8_19_Packed_Endcap_Tangent_Normal"].image=img
nd["V8_19_Packed_Endcap_Tangent_Normal"].name="V8_20_Packed_Footwell_Tangent_Normal"
uvnode=nd["V8_19_Aligned_Endcap_UV_Node"]
uvnode.name="V8_20_Aligned_Footwell_Normal_UV_Node"
uvnode.uv_map="V8_20_Footwell_Aligned_Normal_UV"
mix=nd["V8_19_Source_And_Endcap_Tangent_Normal_Mix"]
mix.name="V8_20_Source_And_Footwell_Tangent_Normal_Mix"
mix.inputs[0].default_value=.19
for node in nd:
 if node.type=="BUMP":
  node.inputs["Strength"].default_value=.012
  node.inputs["Distance"].default_value=.00010
 if node.type=="TEX_IMAGE" and node.image:
  assert node.image.packed_file,node.image.name
  if any(t in node.image.name.upper() for t in ("NORMAL","ORM","HEIGHT")):
   assert node.image.colorspace_settings.name=="Non-Color"
assert nd["Normal Map"].inputs["Color"].links[0].from_node==mix
packed_images=[x.image.name for x in nd if x.type=="TEX_IMAGE" and x.image]
assert len(packed_images)>=5 and any("ORM" in x.upper() for x in packed_images)
NX=19;NY=13
top_count=NX*NY
assert top_count==247
def form_mat(side,cx):
 name="V6_"+side+"_BLENDER_BLACK_FLOOR_MAT"
 ob=bpy.data.objects[name]
 assert ob.type=="MESH" and len(ob.data.vertices)==8 and len(ob.data.polygons)==6
 assert ob.data.users==1
 b=[[min((ob.matrix_world@p.co)[axis] for p in ob.data.vertices),
     max((ob.matrix_world@p.co)[axis] for p in ob.data.vertices)] for axis in range(3)]
 assert abs(b[0][0]-(cx-.225))<.0001 and abs(b[0][1]-(cx+.225))<.0001
 assert abs(b[1][0]+.26)<.0001 and abs(b[1][1]-.42)<.0001
 assert abs(b[2][0]-.2825)<.0001 and abs(b[2][1]-.2975)<.0001
 inv=ob.matrix_world.inverted()
 verts=[];outer=[]
 for j in range(NY):
  v=j/(NY-1);y=-.26+.68*v
  for i in range(NX):
   u=i/(NX-1);x=cx-.225+.45*u
   gate=smooth(.045,.15,u)*(1-smooth(.85,.955,u))
   end=smooth(.035,.15,v)*(1-smooth(.85,.97,v))
   # Eight low contrast parallel longitudinal channels physically formed.
   z=.2975+.0036*gate*end*math.sin(8*math.pi*u)**2
   verts.append(tuple(inv@Vector((x,y,z))))
 for j in range(NY):
  v=j/(NY-1);y=-.26+.68*v
  for i in range(NX):
   u=i/(NX-1);x=cx-.225+.45*u
   verts.append(tuple(inv@Vector((x,y,.2825))))
 faces=[]
 for j in range(NY-1):
  for i in range(NX-1):
   a=j*NX+i;b0=a+1;c=b0+NX;d=a+NX
   faces.append((a,b0,c,d)) # top normal +Z
   faces.append((d+top_count,c+top_count,b0+top_count,a+top_count))
 border=([(i,0) for i in range(NX)]
       +[(NX-1,j) for j in range(1,NY)]
       +[(i,NY-1) for i in range(NX-2,-1,-1)]
       +[(0,j) for j in range(NY-2,0,-1)])
 assert len(border)==2*(NX+NY)-4
 for i,(u,v) in enumerate(border):
  j=(i+1)%len(border)
  a=v*NX+u
  u2,v2=border[j];b0=v2*NX+u2
  faces.append((b0,a,a+top_count,b0+top_count))
 old=ob.data
 new=bpy.data.meshes.new(name+"_V8_20_Closed_Contour_Mesh")
 new.from_pydata(verts,[],faces);new.update(calc_edges=True)
 bm=bmesh.new();bm.from_mesh(new)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(new);bm.free()
 for p in new.polygons:p.use_smooth=True
 metric=new.uv_layers.new(name="V8_20_Footwell_Metric_Tangent_UV")
 aligned=new.uv_layers.new(name="V8_20_Footwell_Aligned_Normal_UV")
 metric=new.uv_layers["V8_20_Footwell_Metric_Tangent_UV"]
 aligned=new.uv_layers["V8_20_Footwell_Aligned_Normal_UV"]
 for face in new.polygons:
  for li in face.loop_indices:
   vi=new.loops[li].vertex_index
   p=ob.matrix_world@new.vertices[vi].co
   metric.data[li].uv=(float(p.x)*5.45,float(p.y)*5.45)
   aligned.data[li].uv=(clamp((float(p.x)-(cx-.225))/.45),
                        clamp((float(p.y)+.26)/.68))
 new.uv_layers.active=metric
 new.materials.append(mat)
 ob.data=new
 if old.users==0:bpy.data.meshes.remove(old)
 for mod in ob.modifiers:
  if mod.type=="BEVEL":
   mod.width=.0012;mod.segments=2;mod.limit_method="ANGLE"
   mod.angle_limit=math.radians(35)
 ob["DAYTONA_V8_20"]="in-place original-bounded soft physical rubber mat, 8 channels, source-packed tangent PBR"
 # One closed, actual 3D dark edge welt per mat, no screen-space decal.
 cname="V8_20_"+side+"_FOOTWELL_MAT_PERIMETER_WELT"
 assert cname not in bpy.data.objects
 cu=bpy.data.curves.new(cname+"_Physical","CURVE")
 cu.dimensions="3D";cu.bevel_depth=.00068;cu.bevel_resolution=3
 spl=cu.splines.new("POLY");spl.use_cyclic_u=True
 spl.points.add(len(border)-1)
 for idx,(i,j) in enumerate(border):
  vtx=ob.matrix_world@new.vertices[j*NX+i].co
  spl.points[idx].co=(vtx.x,vtx.y,vtx.z+.0006,1)
 cu.materials.append(mat)
 edge=bpy.data.objects.new(cname,cu)
 for coll in ob.users_collection:coll.objects.link(edge)
 assert len(new.vertices)==494 and len(new.polygons)==492
 assert all(math.isfinite(float(c)) for q in new.vertices for c in q.co)
 for l in (metric,aligned):
  assert all(math.isfinite(float(t)) for q in l.data for t in q.uv)
 # Confirm all corners remain within original horizontal mat footprint.
 xyz=[ob.matrix_world@p.co for p in new.vertices]
 for ax in (0,1):
  assert min(p[ax] for p in xyz)>=b[ax][0]-0.00001
  assert max(p[ax] for p in xyz)<=b[ax][1]+0.00001
 assert max(p.z for p in xyz)<.302 and min(p.z for p in xyz)>.2824
 return {"name":name,"vertices":len(new.vertices),"faces":len(new.polygons),
         "channels":8,"physical_welt_curve":cname,
         "normal_detail_packed":True,"preserved_original_world_xy_footprint":True,
         "new_z_max_m":max(p.z for p in xyz)}
report={s:form_mat(s,cx) for s,cx in (("L",-.353),("R",.353))}
for n,h in signatures.items():assert mesh_sha(bpy.data.objects[n])==h,n
assert sum(o.type=="MESH" for o in bpy.data.objects)==112
assert sum(o.type=="CURVE" for o in bpy.data.objects)==108
for image in bpy.data.images:
 if image.source=="FILE" and not image.packed_file:image.pack()
scene.render.engine="CYCLES"
scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.view_settings.exposure=-.52
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
manifest={"status":"DAYTONA_V8_20_REAL_BLENDER_SAVED",
 "input":SOURCE.name,"input_sha256":SOURCE_SHA,
 "output":DEST.name,"output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "output_bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "physical_floor_mat_rebuild":report,
 "mesh_count":112,"curve_count":108,"new_analytical_normal":NORMAL.name,
 "new_analytical_normal_sha256":normal_sha,"source_packed_textures":packed_images,
 "native_controls_seats_door_endcaps_and_carpet_unchanged":True,
 "original_game_modified":False,"OVC_created":False,"Quest3_tested":False,
 "render_validation":"UNTESTED","matched_full_resolution":"UNTESTED"}
MANIFEST.write_text(json.dumps(manifest,indent=2))
print("DAYTONA_V8_20_MODEL_SAVED",json.dumps(manifest),flush=True)
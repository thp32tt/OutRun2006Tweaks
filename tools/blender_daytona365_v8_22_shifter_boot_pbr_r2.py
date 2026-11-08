#!/usr/bin/env python3
"""Daytona 365 GTS/4 v8.22: physically double-sided shifter leather boot.

Refine only the existing v5 Blender shifter boot, retaining source factory
gear gate, knob, chrome shaft, the three earlier circumferential leather folds,
original world bounds, cockpit controls, v8.21 wheel/shroud, and all seats.
PMT images guide appearance only; NO original PMT mesh reconstruction.
"""
import bpy,bmesh,hashlib,json,math,os,struct,zlib
from pathlib import Path
from mathutils import Vector
W=Path(os.environ["DAYTONA365_WORKDIR"])/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_21_r2.blend"
OUT=W/"Daytona365_Cockpit_Blender_PBR_v8_22_r2.blend"
NORMAL=W/"Daytona365_v8_22_r2_Shifter_Boot_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_22_R2_BUILD_MANIFEST.json"
S_SHA="411cf351d76fcb21413a340c0ff4dbc3994a881c52c56fdc83919d29b4aac110"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==S_SHA
for p in (OUT,NORMAL,MANIFEST):assert not p.exists(),str(p)
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==109
def sha_mesh(obj):
 d=obj.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode()).hexdigest()
guard=("V5_MANUAL_SHIFTER_CHROME_SHAFT","V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
"DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
"V8_1_COMPACT_SHIFTER_LEATHER_DECK","V8_LOW_CENTER_TUNNEL",
"V6_BLENDER_MANUAL_SHIFTER_LEATHER_FOLD_0.026",
"V6_BLENDER_MANUAL_SHIFTER_LEATHER_FOLD_0.036",
"V6_BLENDER_MANUAL_SHIFTER_LEATHER_FOLD_0.043",
"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
"V7_SHORT_SHAFT_AT_WHEEL_HUB","V8_21_SOURCE_LOWER_GAUGE_SHROUD",
"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
"DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
"DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
"V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
"V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST",
"V8_19_L_DASH_DOOR_FORMED_ENDCAP","V8_19_R_DASH_DOOR_FORMED_ENDCAP",
"V6_L_BLENDER_BLACK_FLOOR_MAT","V6_R_BLENDER_BLACK_FLOOR_MAT")
protected={name:sha_mesh(bpy.data.objects[name]) for name in guard}
boot=bpy.data.objects["V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT"]
assert boot.type=="MESH" and len(boot.data.vertices)==60 and len(boot.data.polygons)==84
assert boot.data.users==1
original_world=[boot.matrix_world@v.co for v in boot.data.vertices]
original_bounds=[(min(p[i] for p in original_world),max(p[i] for p in original_world)) for i in range(3)]
assert abs(original_bounds[0][0]+.037)<.001
assert abs(original_bounds[0][1]-.037)<.001
assert original_bounds[1][0]<-.159 and original_bounds[1][1]>-.075
assert original_bounds[2][0]<.433 and original_bounds[2][1]>.512
# New analytic detail is additional to the existing packed original leather
# BaseColor/normal/ORM(G)/offline height. Not a recovered factory texture.
def pngchunk(t,dat):
 return struct.pack(">I",len(dat))+t+dat+struct.pack(">I",zlib.crc32(t+dat)&0xffffffff)
def cl(t):return max(0.,min(1.,t))
n=256; scan=[]
for j in range(n):
 v=(j+.5)/n; line=bytearray([0])
 for i in range(n):
  u=(i+.5)/n
  # very fine leather surface/pleat tangent slope, amplitude < 3%
  dx=.012*math.cos(18*math.pi*u)*math.cos(12*math.pi*v)
  dy=.023*math.sin(18*math.pi*u)*math.sin(12*math.pi*v)
  s=math.sqrt(1.+dx*dx+dy*dy)
  line.extend((round(255*cl(.5-.5*dx/s)),round(255*cl(.5-.5*dy/s)),
               round(255*cl(.5+.5/s)),255))
 scan.append(bytes(line))
NORMAL.write_bytes(b"\x89PNG\r\n\x1a\n"+pngchunk(b"IHDR",struct.pack(">IIBBBBB",n,n,8,6,0,0,0))
 +pngchunk(b"IDAT",zlib.compress(b"".join(scan),9))+pngchunk(b"IEND",b""))
normal_sha=hashlib.sha256(NORMAL.read_bytes()).hexdigest()
img=bpy.data.images.load(str(NORMAL),check_existing=False)
img.name="V8_22_Shifter_Boot_Packed_Tangent_Normal"
img.colorspace_settings.name="Non-Color";img.pack()
assert img.packed_file and tuple(img.size)==(256,256)
mat=bpy.data.materials["V8_21_Source_Packed_Lower_Gauge_Shroud_PBR"].copy()
mat.name="V8_22_Source_Packed_Shifter_Boot_Black_Leather_PBR"
nodes=mat.node_tree.nodes
bsdf=nodes["Principled BSDF"]
assert all(bsdf.inputs[s].is_linked for s in ("Base Color","Roughness","Normal"))
nodes["V8_17_Original_Dash_Charcoal_Value"].inputs["Value"].default_value=.27
nodes["V8_17_Original_Dash_Charcoal_Value"].inputs["Saturation"].default_value=.73
rr=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
rr.inputs["To Min"].default_value=.73
rr.inputs["To Max"].default_value=.91
bsdf.inputs["Metallic"].default_value=0
nodes["Normal Map"].inputs["Strength"].default_value=.25
tex=nodes["V8_21_Packed_Shroud_Tangent_Normal"]
tex.image=img;tex.name="V8_22_Packed_Shifter_Boot_Tangent_Normal"
uvnode=nodes["V8_21_Shroud_Normal_UV_Node"]
uvnode.name="V8_22_Shifter_Aligned_Normal_UV_Node"
uvnode.uv_map="V8_22_Shifter_Aligned_Normal_UV"
mix=nodes["V8_21_Source_And_Shroud_Normal_Mix"]
mix.name="V8_22_Source_And_Shifter_Normal_Mix"
mix.inputs[0].default_value=.16
assert nodes["Normal Map"].inputs["Color"].links[0].from_node==mix
for node in nodes:
 if node.type=="BUMP":
  node.inputs["Strength"].default_value=.014
  node.inputs["Distance"].default_value=.00011
 if node.type=="TEX_IMAGE" and node.image:
  assert node.image.packed_file,node.name
  if any(k in node.image.name.upper() for k in ("NORMAL","ORM","HEIGHT")):
   assert node.image.colorspace_settings.name=="Non-Color"
images=[node.image.name for node in nodes if node.type=="TEX_IMAGE" and node.image]
assert len(images)>=5 and any("ORM" in im.upper() for im in images)
# 14 circular stations x 24 angular facets each: physical outer surface,
# inner dark-leather return, and sewn upper+lower annular lips. The top
# stays open for the original chrome shift shaft, unlike a flat cap.
RINGS=14; SIDES=24; V_PER_SHELL=RINGS*SIDES
assert V_PER_SHELL==336
inverse=boot.matrix_world.inverted()
xyz=[]; shell_world=[]
cx,cy=0.,-.11715
for inner in (False,True):
 for j in range(RINGS):
  t=j/(RINGS-1)
  z=.433+.0795*t
  taper=1-t
  rx=.0148+.0218*(taper**.9)
  ry=.0174+.0248*(taper**.9)
  wave=(.00125*math.sin(6*math.pi*t))*math.sin(math.pi*t)
  # collar at the top retains original shaft clearance; relieved folded base
  rx=max(.013,rx+wave);ry=max(.015,ry+wave)
  if inner:rx-=.0032;ry-=.0032
  for k in range(SIDES):
   a=2*math.pi*k/SIDES
   twist=.035*math.sin(4*math.pi*t)*math.sin(3*a)
   p=Vector((cx+rx*math.cos(a+twist),cy+ry*math.sin(a+twist),z))
   shell_world.append(p);xyz.append(tuple(inverse@p))
faces=[]
# side surfaces
for j in range(RINGS-1):
 for k in range(SIDES):
  a=j*SIDES+k;b=j*SIDES+(k+1)%SIDES
  faces.append((a,b,b+SIDES,a+SIDES))
  a2=a+V_PER_SHELL;b2=b+V_PER_SHELL
  faces.append((a2+SIDES,b2+SIDES,b2,a2))
# closed bottom and top annular thickness, with real central shaft opening
for k in range(SIDES):
 q=(k+1)%SIDES
 faces.append((k,q,q+V_PER_SHELL,k+V_PER_SHELL))
 a=(RINGS-1)*SIDES+k;b=(RINGS-1)*SIDES+q
 faces.append((b,a,a+V_PER_SHELL,b+V_PER_SHELL))
assert len(xyz)==672 and len(faces)==672
mesh=bpy.data.meshes.new("V8_22_Physical_Two_Sided_Folded_Shifter_Boot")
mesh.from_pydata(xyz,[],faces);mesh.update(calc_edges=True)
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
assert all(len(e.link_faces)==2 for e in bm.edges),"non-manifold boot"
bm.to_mesh(mesh);bm.free()
for poly in mesh.polygons:poly.use_smooth=True
metric=mesh.uv_layers.new(name="V8_22_Shifter_Metric_Leather_UV")
aligned=mesh.uv_layers.new(name="V8_22_Shifter_Aligned_Normal_UV")
for polygon in mesh.polygons:
 for li in polygon.loop_indices:
  pos=boot.matrix_world@mesh.vertices[mesh.loops[li].vertex_index].co
  metric.data[li].uv=(float(pos.x)*5.45,float(pos.z)*5.45)
  aligned.data[li].uv=(cl(.5+math.atan2(float(pos.y)-cy,float(pos.x))/(2*math.pi)),
                       cl((float(pos.z)-.433)/.0795))
mesh.uv_layers.active=metric
mesh.materials.append(mat)
old=boot.data;boot.data=mesh
if old.users==0:bpy.data.meshes.remove(old)
boot["DAYTONA_V8_22"]="physically closed annular two-sided leather with real folded conical boot, source PBR and packed tangent normal"
# True 3D stitched seam on both outer sides, not a 2D overlay.
for label,k in (("LEFT",9),("RIGHT",3)):
 name="V8_22_"+label+"_SHIFTER_BOOT_SEAM"
 assert not bpy.data.objects.get(name)
 cu=bpy.data.curves.new(name+"_3D_Seam","CURVE")
 cu.dimensions="3D";cu.bevel_depth=.00038;cu.bevel_resolution=3
 sp=cu.splines.new("POLY");sp.points.add(RINGS-1)
 for j in range(RINGS):
  pos=shell_world[j*SIDES+k]
  # same independent real outer surface, restrained raised thread
  d=Vector((pos.x-cx,pos.y-cy,0.)).normalized()
  sp.points[j].co=(pos.x+d.x*.00035,pos.y+d.y*.00035,pos.z,1)
 cu.materials.append(mat)
 ob=bpy.data.objects.new(name,cu)
 for c in boot.users_collection:c.objects.link(ob)
assert all(sha_mesh(bpy.data.objects[n])==h for n,h in protected.items())
assert sum(o.type=="MESH" for o in bpy.data.objects)==113
assert sum(o.type=="CURVE" for o in bpy.data.objects)==111
world=[boot.matrix_world@v.co for v in mesh.vertices]
assert min(p.x for p in world)>=original_bounds[0][0]-.00005
assert max(p.x for p in world)<=original_bounds[0][1]+.00005
assert min(p.y for p in world)>=original_bounds[1][0]-.00005
assert max(p.y for p in world)<=original_bounds[1][1]+.00005
assert min(p.z for p in world)>=original_bounds[2][0]-.00005
assert max(p.z for p in world)<=original_bounds[2][1]+.00005
for im in bpy.data.images:
 if im.source=="FILE" and not im.packed_file:im.pack()
scene=bpy.context.scene
scene.render.engine="CYCLES";scene.cycles.samples=10
scene.cycles.use_denoising=True;scene.render.resolution_x=960
scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.view_settings.exposure=-.52
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
manifest={"status":"DAYTONA_V8_22_REAL_BLENDER_SAVED",
 "input":SOURCE.name,"input_sha256":S_SHA,"output":OUT.name,
 "output_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
 "output_bytes":OUT.stat().st_size,"blender":bpy.app.version_string,
 "modified_original_boot":boot.name,"old_vertices":60,"old_faces":84,
 "new_vertices":len(mesh.vertices),"new_faces":len(mesh.polygons),
 "closed_annular_boot_manifold":True,"physical_outer_inner_wall":True,
 "external_boot_original_bounds_kept":True,
 "physical_3d_seam_curves":2,"mesh_count":113,"curve_count":111,
 "normal":NORMAL.name,"normal_sha256":normal_sha,
 "source_packed_PBR_images":images,
 "native_factory_chrome_shaft_gate_knob_and_previous_folds_unchanged":True,
 "v821_hub_shroud_v820_mats_and_seats_preserved":True,
 "full_resolution_PMT_matched":"UNTESTED","render_validation":"UNTESTED",
 "original_game_modified":False,"OVC_created":False,"Quest3_tested":False}
MANIFEST.write_text(json.dumps(manifest,indent=2))
print("DAYTONA_V8_22_MODEL_SAVED",json.dumps(manifest),flush=True)
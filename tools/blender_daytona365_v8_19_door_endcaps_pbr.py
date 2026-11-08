#!/usr/bin/env python3
"""v8.19 physical source-envelope dashboard-to-door endcap and formed top rail.
All camera, native steering, gauges, switchbank, gear, v8.18 switch surrounds,
v8.16 seats and reference original PMT remain untouched.
Geometry is manually original-image-guided, NOT extracted original PMT vertices.
"""
import bpy,bmesh,hashlib,json,math,os,struct,zlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v819_ai2_093x"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_18_r2.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_19_r2.blend"
NORMAL=W/"Daytona365_v8_19_r2_Endcap_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_19_R2_BUILD_MANIFEST.json"
SHA="bde686212360eb7450697d3f762351eabe19751af54fa3ea58493063fcf72a4a"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
for f in (DEST,NORMAL,MANIFEST):assert not f.exists(),f
assert sum(o.type=="MESH" for o in bpy.data.objects)==110
assert sum(o.type=="CURVE" for o in bpy.data.objects)==102
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
def clamp(x):return max(0.,min(1.,x))
def smooth(a,b,x):
 t=clamp((x-a)/(b-a));return t*t*(3.-2.*t)
def mesh_sha(ob):
 me=ob.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in me.vertices],
 [(p.material_index,tuple(p.vertices)) for p in me.polygons])).encode()).hexdigest()
protected=("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
 "V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
 "V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST",
 "V8_18_L_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN",
 "V8_18_R_SOURCE_SWITCHBANK_MOLDED_SIDE_RETURN",
 "V8_18_SOURCE_SWITCHBANK_LOWER_MOLDED_SILL",
 "V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",
 "V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE")
unchanged={name:mesh_sha(bpy.data.objects[name]) for name in protected}
# New mathematically generated low-relief tangent detail (NOT an original PMT asset).
def pngchunk(tag,by):
 return struct.pack(">I",len(by))+tag+by+struct.pack(">I",zlib.crc32(tag+by)&0xffffffff)
N=256;lines=[]
for j in range(N):
 v=(j+.5)/N;row=bytearray([0])
 for i in range(N):
  u=(i+.5)/N
  sx=.017*math.cos(12*math.pi*u)*math.sin(18*math.pi*v)
  sy=.012*math.sin(12*math.pi*u)*math.cos(18*math.pi*v)
  l=math.sqrt(1+sx*sx+sy*sy)
  row.extend([round(clamp(.5-.5*sx/l)*255),round(clamp(.5-.5*sy/l)*255),
              round(clamp(.5+.5/l)*255),255])
 lines.append(bytes(row))
NORMAL.write_bytes(b"\x89PNG\r\n\x1a\n"+
 pngchunk(b"IHDR",struct.pack(">IIBBBBB",N,N,8,6,0,0,0))+
 pngchunk(b"IDAT",zlib.compress(b"".join(lines),9))+pngchunk(b"IEND",b""))
normsha=hashlib.sha256(NORMAL.read_bytes()).hexdigest()
img=bpy.data.images.load(str(NORMAL),check_existing=False)
img.name="V8_19_Endcap_Packed_Tangent_Normal"
img.colorspace_settings.name="Non-Color";img.pack()
assert img.packed_file and tuple(img.size)==(N,N)
# Source-linked original BlackLeather color, tangent normal, ORM green roughness
# and Height bump remain intact. Material is cloned, not modifying baseline.
mat=bpy.data.materials["V8_17_Source_Packed_Dark_Dashboard_PBR"].copy()
mat.name="V8_19_Source_Dash_To_Door_Dark_PBR"
nodes=mat.node_tree.nodes
bsdf=nodes["Principled BSDF"]
assert all(bsdf.inputs[k].is_linked for k in ("Base Color","Roughness","Normal"))
hsv=nodes["V8_17_Original_Dash_Charcoal_Value"]
hsv.inputs["Value"].default_value=.405
hsv.inputs["Saturation"].default_value=.88
rough=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
assert rough.inputs["Value"].is_linked
rough.inputs["To Min"].default_value=.70;rough.inputs["To Max"].default_value=.86
bsdf.inputs["Metallic"].default_value=0
nm=nodes["Normal Map"]
nm.inputs["Strength"].default_value=.20
mix=nodes["V8_17_Source_And_Cowl_Normal_Mix"]
mix.name="V8_19_Source_And_Endcap_Tangent_Normal_Mix"
mix.inputs[0].default_value=.16
tex=nodes["V8_17_Packed_Cowl_Tangent_Normal"]
tex.name="V8_19_Packed_Endcap_Tangent_Normal";tex.image=img
uvnode=nodes["V8_17_Aligned_Cowl_Tangent_UV_Node"]
uvnode.name="V8_19_Aligned_Endcap_UV_Node"
uvnode.uv_map="V8_19_Endcap_Aligned_Tangent_UV"
for node in nodes:
 if node.type=="BUMP":
  node.inputs["Strength"].default_value=.012
  node.inputs["Distance"].default_value=.00012
 if node.type=="TEX_IMAGE" and node.image:
  assert node.image.packed_file,node.image.name
  if any(t in node.image.name.upper() for t in ("NORMAL","ORM","HEIGHT")):
   assert node.image.colorspace_settings.name=="Non-Color"
packed=[n.image.name for n in nodes if n.type=="TEX_IMAGE" and n.image]
assert len(packed)>=5 and any("ORM" in i.upper() for i in packed)
assert any("HEIGHT" in i.upper() for i in packed)
assert nodes["Normal Map"].inputs["Color"].links[0].from_node==mix
def form_mesh(name,rings,material,owner):
 assert bpy.data.objects.get(name) is None
 assert len(rings)>=15 and all(len(row)==8 for row in rings)
 vertices=[x for row in rings for x in row];faces=[]
 for j in range(len(rings)-1):
  for k in range(8):
   a=8*j+k;b=8*j+(k+1)%8
   faces.append((a,b,b+8,a+8))
 faces.extend([tuple(reversed(range(8))),
              tuple((len(rings)-1)*8+k for k in range(8))])
 me=bpy.data.meshes.new(name+"_Formed")
 me.from_pydata(vertices,[],faces);me.update(calc_edges=True)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 metric=me.uv_layers.new(name="V8_19_Endcap_Metric_Tangent_UV")
 aligned=me.uv_layers.new(name="V8_19_Endcap_Aligned_Tangent_UV")
 for face in me.polygons:
  for li in face.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co
   metric.data[li].uv=(float(v.y)*5.0,float(v.z)*5.0)
   aligned.data[li].uv=(clamp((float(v.y)+.93)/1.34),
                          clamp((float(v.z)-.66)/.28))
 me.uv_layers.active=metric;me.materials.append(material)
 ob=bpy.data.objects.new(name,me)
 for coll in owner.users_collection:coll.objects.link(ob)
 assert len(me.vertices)==len(rings)*8
 assert len(me.polygons)==(len(rings)-1)*8+2
 return ob
def curve(name,coords,mat,owner):
 assert bpy.data.objects.get(name) is None
 cu=bpy.data.curves.new(name+"_3D","CURVE");cu.dimensions="3D"
 cu.bevel_depth=.00038;cu.bevel_resolution=3
 spl=cu.splines.new("POLY");spl.points.add(len(coords)-1)
 for p,c in zip(spl.points,coords):p.co=(*c,1.)
 cu.materials.append(mat)
 ob=bpy.data.objects.new(name,cu)
 for co in owner.users_collection:co.objects.link(ob)
 return ob
report={}
for side,sign in (("L",-1),("R",1)):
 door=bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"]
 me=door.data
 assert len(me.vertices)==465 and len(me.polygons)==840
 assert me.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
 original=[tuple(v.co) for v in me.vertices]
 # Only source door upper leading shoulder: gently tuck and roll 4mm
 # toward dashboard; keep chrome strip, latch and full rear door geometry.
 moved=0
 for v in me.vertices:
  x,y,z=v.co
  f=smooth(.07,.28,float(y))*smooth(.69,.79,float(z))
  delta=.0042*f
  if delta>1e-5:
   v.co.x-=sign*delta;v.co.z+=.0018*f
   moved+=1
 assert moved>15,moved
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 # Preserve both source UV layers and original PBR; no retint original door.
 assert me.materials[0].name=="V8_10_Source_Charcoal_Door_Leather_PBR"
 assert max(math.dist(original[i],tuple(v.co)) for i,v in enumerate(me.vertices))<.005
 # Replace the same 8-vertex boxy endcap object geometry with 17 real
 # source-envelope graduated ring stations. Keep original object/pivot.
 top=bpy.data.objects["V8_3_"+side+"_BLACK_DOOR_TOP_CAP"]
 assert len(top.data.vertices)==8 and len(top.data.polygons)==6
 assert top.data.users==1
 rings_top=[]
 for j in range(17):
  t=j/16;y=-.92+1.23*t
  nose=smooth(.64,.99,t)
  xc=sign*(.775-.0015*nose)
  zc=.685+.012*nose
  r=.0145*(1-.10*nose)
  rings_top.append([(xc+.018*math.cos(2*math.pi*k/8),
                       y,zc+r*math.sin(2*math.pi*k/8)) for k in range(8)])
 # Original object location preserved, transform world coords to its local mesh space.
 inv=top.matrix_world.inverted()
 mapped=[[tuple(inv@Vector(p)) for p in row] for row in rings_top]
 # Build mesh using exact source object name in temporary storage then rebind.
 newtemp=form_mesh("V8_19_TEMP_"+side+"_TOP_RAIL",mapped,mat,top)
 top.data=newtemp.data.copy()
 bpy.data.objects.remove(newtemp,do_unlink=True)
 assert len(top.data.vertices)==136 and len(top.data.polygons)==130
 top.data.materials.clear();top.data.materials.append(mat)
 top.data.uv_layers.active=top.data.uv_layers["V8_19_Endcap_Metric_Tangent_UV"]
 # Native original door top coords x=.75..81, z<=.92, front y .40.
 # New side cheek fills ONLY narrow side of dash at x ~=.76,
 # rather than covering dashboard itself or source controls.
 bands=[]
 edge_points=[]
 for j in range(16):
  t=j/15
  y=.16+.23*t
  xc=sign*(.756+.011*smooth(.16,.95,t))
  zc=.806-.005*t
  taper=.24+.76*math.sin(math.pi*t)**.7
  rz=.088*taper
  rx=.0095*taper
  pts=[(xc+rx*math.cos(2*math.pi*k/8),
        y,zc+rz*math.sin(2*math.pi*k/8)) for k in range(8)]
  bands.append(pts)
  edge_points.append((xc,y,zc+rz+.001))
 new=form_mesh("V8_19_"+side+"_DASH_DOOR_FORMED_ENDCAP",bands,mat,door)
 curve("V8_19_"+side+"_TOP_ENDCAP_STITCH",edge_points,mat,new)
 # Follow forward tip of new door trim with a second actual physical seam.
 trim=[(sign*(.770-.002*smooth(.65,1.,j/15)),
        -.01+.34*j/15,
        .701+.008*smooth(.6,1.,j/15)) for j in range(16)]
 curve("V8_19_"+side+"_FORWARD_DOOR_TOP_STITCH",trim,mat,top)
 bounds=[[min(v.co[k] for v in new.data.vertices),
          max(v.co[k] for v in new.data.vertices)] for k in range(3)]
 assert max(abs(bounds[0][0]),abs(bounds[0][1]))<.81
 assert .159<bounds[1][0]<bounds[1][1]<.4
 assert .65<bounds[2][0]<bounds[2][1]<.925
 assert all(math.isfinite(float(x)) for v in new.data.vertices for x in v.co)
 assert all(math.isfinite(float(x)) for uv in new.data.uv_layers
            for v in uv.data for x in v.uv)
 report[side]={"sculpted_existing_door_vertices":moved,
 "source_door_vertices":465,"source_door_faces":840,
 "formed_topcap_vertices":len(top.data.vertices),
 "formed_topcap_faces":len(top.data.polygons),
 "new_endcap_vertices":len(new.data.vertices),
 "new_endcap_faces":len(new.data.polygons),
 "new_endcap_bounds_m":bounds,
 "new_seam_curves":2,"original_door_source_material_preserved":True}
for name,h in unchanged.items():
 assert mesh_sha(bpy.data.objects[name])==h,name
assert sum(o.type=="MESH" for o in bpy.data.objects)==112
assert sum(o.type=="CURVE" for o in bpy.data.objects)==106
scene.render.engine="CYCLES"
scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.view_settings.exposure=-.52
for image in bpy.data.images:
 if image.source=="FILE" and not image.packed_file:image.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
manifest={"status":"DAYTONA_V8_19_R2_REAL_BLENDER_SAVED","blender":bpy.app.version_string,
 "source":SOURCE.name,"source_sha256":SHA,
 "output":DEST.name,"output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"door_ends":report,
 "new_packed_tangent_normal":NORMAL.name,
 "new_tangent_normal_sha256":normsha,"source_PBR_images":packed,
 "preserved_gauges_switch_cowl_seats_native_controls":True,
 "original_game_PMT_untouched":True,"OVC_created":False,"Quest3_tested":False,
 "render_validation":"UNTESTED","matched_full_resolution":"UNTESTED"}
MANIFEST.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("DAYTONA_V8_19_R2_MODEL_SAVED",json.dumps(manifest),flush=True)
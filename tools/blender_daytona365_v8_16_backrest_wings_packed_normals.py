#!/usr/bin/env python3
"""v8.16: independent BACKREST wing/shoulder/lumbar geometry and packed tangent normal.
Based on immutable real v8.15, without modifying already-done cushion/apron work.
Original PMT017 material bounds are ONLY aggregate constraints, never copied vertices.
"""
import bpy,bmesh,hashlib,json,math,os,struct,zlib
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v816_ai2_0817"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_15.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_16.blend"
NORMAL=W/"Daytona365_v8_16_Backrest_Wing_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_16_BUILD_MANIFEST.json"
SHA="19728e96bb3b09ea92138cb4201218ac4479cdfaa7b624e375587fc0ef872006"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
for p in (DEST,NORMAL,MANIFEST):assert not p.exists(),p
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert sum(o.type=="MESH" for o in bpy.data.objects)==106
assert sum(o.type=="CURVE" for o in bpy.data.objects)==94
MAX_X=.57464;MIN_Y=-.72863;MAX_Z=.85149
NX=72;NY=58;RING=73*59
def cl(x):return min(1.,max(0.,x))
def sm(a,b,x):
 v=cl((x-a)/(b-a));return v*v*(3-2*v)
def gauss(t,c,w):return math.exp(-((t-c)/w)**2)
def chunk(tag,p):
 return struct.pack(">I",len(p))+tag+p+struct.pack(">I",zlib.crc32(tag+p)&0xffffffff)
# New original-independent 256px micro-wing tangent normal, packed into .blend.
n=256;scan=[]
def height(u,v):
 return .00045*gauss(abs(2*u-1),.70,.16)*sm(.08,.25,v)*(1-sm(.8,.97,v))*math.cos(7*math.pi*v)
for y in range(n):
 v=(y+.5)/n;row=bytearray([0])
 for x in range(n):
  u=(x+.5)/n;eps=1/n
  sx=(height(cl(u+eps),v)-height(cl(u-eps),v))/(2*eps*.402)
  sy=(height(u,cl(v+eps))-height(u,cl(v-eps)))/(2*eps*.405)
  ln=math.sqrt(1+sx*sx+sy*sy)
  row.extend(tuple(round(cl((a+1)*.5)*255) for a in (-sx/ln,-sy/ln,1/ln))+(255,))
 scan.append(bytes(row))
payload=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",n,n,8,6,0,0,0))+chunk(b"IDAT",zlib.compress(b"".join(scan),9))+chunk(b"IEND",b"")
assert len(payload)>500
NORMAL.write_bytes(payload)
nsha=hashlib.sha256(payload).hexdigest()
image=bpy.data.images.load(str(NORMAL),check_existing=False)
image.name="V8_16_Original_Independent_Wing_Tangent_Normal"
image.colorspace_settings.name="Non-Color";image.pack()
assert image.packed_file and tuple(image.size)==(n,n)
# Preserve genuine packed original BaseColor, tangent Normal, ORM(G), Height.
mat=bpy.data.materials["V8_9_Source_Charcoal_Seat_PBR"].copy()
mat.name="V8_16_PMT017_Backrest_Source_Charcoal_PBR"
nodes=mat.node_tree.nodes;links=mat.node_tree.links
shader=nodes["Principled BSDF"]
for k in ("Base Color","Roughness","Normal"):assert shader.inputs[k].is_linked
hsv=nodes["V8_9_PMT_CHARCOAL_DESATURATION"]
hsv.inputs["Value"].default_value=.315;hsv.inputs["Saturation"].default_value=.115
rough=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
assert rough.inputs["Value"].is_linked
rough.inputs["To Min"].default_value=.72;rough.inputs["To Max"].default_value=.89
shader.inputs["Metallic"].default_value=0.
maps=[x for x in nodes if x.type=="NORMAL_MAP"]
assert len(maps)==1 and maps[0].inputs["Color"].is_linked
nm=maps[0];old_socket=nm.inputs["Color"].links[0].from_socket
nm.inputs["Strength"].default_value=.21
uvnode=nodes.new("ShaderNodeUVMap");uvnode.name="V8_16_Wing_Normal_UV_Node"
uvnode.uv_map="V8_16_Aligned_Wing_Tangent_Normal_UV"
tex=nodes.new("ShaderNodeTexImage");tex.name="V8_16_Packed_Wing_Normal"
tex.image=image
links.new(uvnode.outputs["UV"],tex.inputs["Vector"])
mix=nodes.new("ShaderNodeMixRGB");mix.name="V8_16_Original_And_Wing_Normal_Mix"
mix.blend_type="MIX";mix.inputs[0].default_value=.29
links.new(old_socket,mix.inputs[1]);links.new(tex.outputs["Color"],mix.inputs[2])
links.new(mix.outputs["Color"],nm.inputs["Color"])
packed=[]
for x in nodes:
 if x.type=="BUMP":
  x.inputs["Strength"].default_value=.013;x.inputs["Distance"].default_value=.00015
 if x.type=="TEX_IMAGE" and x.image:
  assert x.image.packed_file
  if any(s in x.image.name.upper() for s in ("NORMAL","ORM","HEIGHT")):
   assert x.image.colorspace_settings.name=="Non-Color"
  packed.append(x.image.name)
assert len(packed)>=5 and any("ORM" in x.upper() for x in packed)
assert any("HEIGHT" in x.upper() for x in packed)
side=bpy.data.materials["V8_9_Source_Charcoal_Seat_Side_PBR"].copy()
side.name="V8_16_PMT017_Backrest_Return_Source_PBR"
sn=side.node_tree.nodes
sn["V8_9_PMT_CHARCOAL_DESATURATION"].inputs["Value"].default_value=.31
sn["V8_5_ORM_ROUGHNESS_RANGE"].inputs["To Min"].default_value=.75
sn["V8_5_ORM_ROUGHNESS_RANGE"].inputs["To Max"].default_value=.90
assert all(x.image.packed_file for x in sn if x.type=="TEX_IMAGE" and x.image)
def at(me,j,i):
 c=me.vertices[j*73+i].co
 return (float(c.x),float(c.y),float(c.z))
def reproject(name,pts):
 obj=bpy.data.objects[name];s=obj.data.splines[0]
 assert len(s.points)==len(pts),(name,len(s.points),len(pts))
 for p,v in zip(s.points,pts):p.co=(*v,1.)
def seam(name,pts,ob):
 assert bpy.data.objects.get(name) is None
 curve=bpy.data.curves.new(name+"_Path","CURVE")
 curve.dimensions="3D";curve.bevel_depth=.00047;curve.bevel_resolution=3
 spl=curve.splines.new("POLY");spl.points.add(len(pts)-1)
 for p,v in zip(spl.points,pts):p.co=(*v,1.)
 curve.materials.append(side)
 new=bpy.data.objects.new(name,curve)
 for coll in ob.users_collection:coll.objects.link(new)
 return new.name
result={}
for LR in "LR":
 name="V8_"+LR+"_TAPERED_PADDED_BACKREST"
 obj=bpy.data.objects[name];me=obj.data
 assert len(me.vertices)==8614 and len(me.polygons)==8612
 assert me.uv_layers.active.name=="V8_11_CROWN_GEODESIC_UV"
 assert [a.name for a in me.materials]==["V8_9_Source_Charcoal_Seat_PBR","V8_9_Source_Charcoal_Seat_Side_PBR"]
 cushion=bpy.data.objects["V8_"+LR+"_CLASSIC_PADDED_CUSHION"]
 orig_cush=hashlib.sha256(repr([tuple(v.co) for v in cushion.data.vertices]).encode()).hexdigest()
 orig=[tuple(v.co) for v in me.vertices[:RING]]
 for j in range(NY+1):
  t=j/NY;fade=sm(.06,.24,t)*(1-sm(.76,.98,t))
  for i in range(NX+1):
   edge=abs(2*i/NX-1);idx=j*73+i
   p=me.vertices[idx];q=me.vertices[RING+idx]
   # Side-wing 8.8mm forward, central lumbar 4.5mm forward, and
   # 3.2mm actual upper shoulder outline: all within PMT aggregate.
   p.co.y-=.0088*gauss(edge,.70,.145)*fade+.0045*gauss(t,.32,.19)*gauss(edge,0,.40)
   dx=.0032*gauss(t,.73,.16)*sm(.72,1,edge)
   p.co.x+=dx if i>36 else -dx
   q.co=(p.co.x,p.co.y+.054,p.co.z-.004)
 me.update()
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(me);bm.free()
 for face in me.polygons:face.use_smooth=True
 us=[[0.]*73 for _ in range(59)];vs=[[0.]*73 for _ in range(59)]
 for j in range(59):
  for i in range(73):
   if i:us[j][i]=us[j][i-1]+math.dist(at(me,j,i),at(me,j,i-1))
   if j:vs[j][i]=vs[j-1][i]+math.dist(at(me,j,i),at(me,j-1,i))
 uv=me.uv_layers.new(name="V8_16_Backrest_Metric_Tangent_UV")
 detail=me.uv_layers.new(name="V8_16_Aligned_Wing_Tangent_Normal_UV")
 for face in me.polygons:
  for li in face.loop_indices:
   v=me.loops[li].vertex_index%RING;j,i=divmod(v,73)
   uv.data[li].uv=(us[j][i]*5.45,vs[j][i]*5.45)
   detail.data[li].uv=(i/NX,j/NY)
 me.uv_layers.active=uv
 me.materials[0]=mat;me.materials[1]=side
 paths=[]
 for edge,i in (("LEFT",3),("RIGHT",69)):
  paths.append(("V8_5_"+LR+"_BACKREST_"+edge+"_WELT",
      [(x,y-.0012,z) for x,y,z in (at(me,j,i) for j in range(1,NY))]))
 for t in (.23,.48,.72):
  j=round(t*NY)
  paths.append(("V8_5_"+LR+"_BACKREST_STITCH_"+format(t,".2f"),
      [(x,y-.0011,z) for x,y,z in (at(me,j,i) for i in range(11,NX-10))]))
 for edge,i in (("LEFT",14),("RIGHT",58)):
  paths.append(("V8_6_"+LR+"_BACKREST_INSET_"+edge+"_BOLSTER_SEAM",
      [(x,y-.0013,z) for x,y,z in (at(me,j,i) for j in range(5,NY-4))]))
 for t in (.19,.38,.57,.76):
  j=round(t*NY)
  paths.append(("V8_7_"+LR+"_PLEATED_BACKREST_STITCH_"+format(t,".2f"),
      [(x,y-.0011,z) for x,y,z in (at(me,j,i) for i in range(13,NX-12))]))
 assert len(paths)==11
 for name,pts in paths:reproject(name,pts)
 newseams=[]
 for edge,i in (("LEFT",10),("RIGHT",62)):
  newseams.append(seam("V8_16_"+LR+"_"+edge+"_BACKREST_WING_STITCH",
      [(x,y-.00135,z) for x,y,z in (at(me,j,i) for j in range(6,NY-6))],obj))
 changed=sum(math.dist(orig[k],tuple(me.vertices[k].co))>1e-5 for k in range(RING))
 assert changed>900,changed
 for j in (0,NY):
  assert max(math.dist(orig[j*73+i],tuple(me.vertices[j*73+i].co))
          for i in range(73))<.0006
 assert hashlib.sha256(repr([tuple(v.co) for v in cushion.data.vertices]).encode()).hexdigest()==orig_cush
 bds=[[min(v.co[k] for v in me.vertices),max(v.co[k] for v in me.vertices)] for k in range(3)]
 assert max(abs(bds[0][0]),abs(bds[0][1]))<MAX_X
 assert MIN_Y<bds[1][0]<bds[1][1]<-.01985
 assert .33179<bds[2][0]<bds[2][1]<MAX_Z
 assert all(math.isfinite(float(x)) for v in me.vertices for x in v.co)
 assert all(math.isfinite(float(x)) for v in me.polygons for x in v.normal)
 assert all(math.isfinite(float(x)) for a in (uv,detail) for t in a.data for x in t.uv)
 obj["DAYTONA_V8_16"]="3D wing, lumbar, shoulder; metric UV and source+packed tangent normal"
 result[LR]={"object":obj.name,"vertices":len(me.vertices),"polygons":len(me.polygons),
  "changed_front_vertices":changed,"maximum_forward_wing_m":.0088,
  "maximum_shoulder_width_added_m":.0032,"maximum_lumbar_m":.0045,
  "UV_metric":uv.name,"UV_detail":detail.name,"retouched_existing_seams":len(paths),
  "new_wing_seams":newseams,"bounds_m":bds,"v815_cushion_unchanged":True}
assert sum(x.type=="MESH" for x in bpy.data.objects)==106
assert sum(x.type=="CURVE" for x in bpy.data.objects)==98
for LR in "LR":
 assert bpy.data.objects["V8_"+LR+"_CLASSIC_PADDED_CUSHION"].data.uv_layers.active.name=="V8_15_CROWN_BOLSTER_APRON_METRIC_UV"
 assert len(bpy.data.objects["V8_9_"+LR+"_INTEGRATED_PADDED_HEADREST"].data.vertices)==242
for name in ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB","V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"):
 assert bpy.data.objects.get(name)
scene.render.engine="CYCLES";scene.cycles.samples=10;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.view_settings.exposure=-.52
for img in bpy.data.images:
 if img.source=="FILE" and not img.packed_file:img.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
m={"status":"DAYTONA_V8_16_REAL_BLENDER_SAVED",
 "source":SOURCE.name,"source_sha256":SHA,
 "output":DEST.name,"output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "backrests":result,"new_tangent_normal":NORMAL.name,"new_tangent_normal_sha256":nsha,
 "normal_packed":bool(image.packed_file),"source_packed_PBR_images":packed,
 "v815_cushions_unmodified":True,"native_H_gate_gauges_preserved":True,
 "original_game_files_modified":False,"OVC_created":False,
 "Quest3_tested":False,"camera":scene.camera.name,
 "render_validation":"UNTESTED","matched_full_resolution":"UNTESTED"}
MANIFEST.write_text(json.dumps(m,indent=2),encoding="utf-8")
print("DAYTONA_V8_16_MODEL_SAVED",json.dumps(m),flush=True)
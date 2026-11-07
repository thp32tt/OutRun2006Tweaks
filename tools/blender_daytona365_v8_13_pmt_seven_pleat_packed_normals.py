#!/usr/bin/env python3
"""Daytona365 v8.13: seven physically sculpted original-source cushion pleats,
metric tangent UV, source-packed PBR and a genuinely packed tangent normal map.

Reads immutable real v8.12 Blender; edits only the 2 EXISTING V8 seat cushions,
their fitted original seam curves and source-derived upholstery material.
Original PMT seat material017 bounds supply envelopes, not copied vertices.
"""
import bpy,bmesh,hashlib,json,math,os,struct,zlib
from pathlib import Path

ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_12.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_13.blend"
EXPECTED="03c7e288fad4ecb36952ca2f871e132ee079d9888dea4664d9a97923cd6945c6"
NORMAL_PATH=W/"Daytona365_v8_13_Cushion_Seven_Pleat_Tangent_Normal.png"
MANIFEST=W/"DAYTONA_V8_13_BUILD_MANIFEST.json"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
assert not DEST.exists(),"Never overwrite v8.13 model"
assert not NORMAL_PATH.exists(),"Never overwrite previous generated image"
assert not MANIFEST.exists(),"Preserve previous manifest"
sc=bpy.context.scene
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
required=(
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_LOW_CENTER_TUNNEL",
 "V5_L_SEAT_RECLINED_PADDED_BACK",
 "V5_R_SEAT_RECLINED_PADDED_BACK")
for name in required:assert bpy.data.objects.get(name),name

# Interpret the real original PMT same-camera cushion reference as ~7 transverse
# padded channels, NOT an exact original vertex/face recovery. Keep silhouette
# inside measured PMT group017 x/y/z aggregate envelope.
PMT_SEAT={"max_abs_x":.57464,"front_y":-.01985,"rear_y":-.72863,
          "min_z":.33179,"max_z":.85149}
OLD_CRESTS=(.135,.315,.495,.675,.855)
NEW_CRESTS=(.115,.242,.369,.496,.623,.750,.877)
NEW_GROOVES=tuple((NEW_CRESTS[i]+NEW_CRESTS[i+1])/2 for i in range(6))
NX=72;NY=52;RING=(NX+1)*(NY+1)
SEAT_MAT="V8_13_Source_Sculpted_Charcoal_Cushion_PBR"
NORMAL_NAME="V8_13_Seven_Pleat_512_Tangent_Normal"
UV_NAME="V8_13_Geodesic_Seat_Leather_UV"
DETAIL_UV="V8_13_Seven_Pleat_Aligned_Normal_UV"

def gaussian(t,c,width):
 return math.exp(-((t-c)/width)**2)
def center_envelope(u):
 a=abs(2*u-1)
 return max(0.,1.-(a/.82)**2)**1.4
def old_crest(t,u):
 # Actual v8.9 source script added five broad 4.2mm pillows.
 a=abs(2*u-1)
 center=max(0.,1.-(a/.80)**2)**1.4
 return sum(.0042*gaussian(t,c,.075) for c in OLD_CRESTS)*center
def new_relief(t,u):
 envelope=center_envelope(u)
 endfade=min(1.,max(0.,t/.055),max(0.,(1-t)/.055))
 crowns=sum(.0066*gaussian(t,c,.053) for c in NEW_CRESTS)
 grooves=sum(.0018*gaussian(t,c,.020) for c in NEW_GROOVES)
 return envelope*endfade*(crowns-grooves)

# Create a real PNG tangent-space normal image aligned to the new distinct UV.
# Source normal map remains wired and is MIXed with this topology-aware detail.
# The exact macro pleat displacement is in the mesh; this image adds its
# smaller derivative/micro-crease complement and does not replace source DDS.
def pngchunk(tag,payload):
 return (struct.pack(">I",len(payload))+tag+payload+
         struct.pack(">I",zlib.crc32(tag+payload)&0xffffffff))
size=512
scan=[]
for j in range(size):
 v=(j+.5)/size
 row=bytearray([0])
 for i in range(size):
  u=(i+.5)/size
  # Small 0.8mm high detail wave at the physical V8.13 channels. Pixel
  # tangent slope is dZ/d(y metre), so divide by cushion length ~0.55 m.
  step=1/size
  def h(tt):
   center=center_envelope(u)
   return center*(
    sum(.00085*gaussian(tt,c,.037) for c in NEW_CRESTS)
    -sum(.00055*gaussian(tt,c,.013) for c in NEW_GROOVES))
  slope=(h(min(1,v+step))-h(max(0,v-step)))/(2*step*.554)
  ny=-slope
  inv=1.0/math.sqrt(1+ny*ny)
  g=int(round(max(0.,min(1.,(ny*inv+1)*.5))*255))
  b=int(round(max(0.,min(1.,(inv+1)*.5))*255))
  row.extend((128,g,b,255))
 scan.append(bytes(row))
raw=(b"\x89PNG\r\n\x1a\n"+
 pngchunk(b"IHDR",struct.pack(">IIBBBBB",size,size,8,6,0,0,0))+
 pngchunk(b"IDAT",zlib.compress(b"".join(scan),9))+
 pngchunk(b"IEND",b""))
assert len(raw)>2000
NORMAL_PATH.write_bytes(raw)
generated_sha=hashlib.sha256(raw).hexdigest()
img=bpy.data.images.load(str(NORMAL_PATH),check_existing=False)
img.name=NORMAL_NAME
img.colorspace_settings.name="Non-Color"
img.pack()
assert img.packed_file and img.size[0]==size and img.size[1]==size

source=bpy.data.materials["V8_9_Source_Charcoal_Seat_PBR"]
mat=source.copy()
mat.name=SEAT_MAT
assert mat.use_nodes
nodes=mat.node_tree.nodes;links=mat.node_tree.links
bsdf=nodes["Principled BSDF"]
assert bsdf.inputs["Base Color"].is_linked
assert bsdf.inputs["Roughness"].is_linked
assert bsdf.inputs["Normal"].is_linked
hsv=nodes["V8_9_PMT_CHARCOAL_DESATURATION"]
hsv.inputs["Saturation"].default_value=.115
hsv.inputs["Value"].default_value=.34
rough=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
assert rough.inputs["Value"].is_linked
rough.inputs["To Min"].default_value=.72
rough.inputs["To Max"].default_value=.90
bsdf.inputs["Metallic"].default_value=0.
maps=[n for n in nodes if n.type=="NORMAL_MAP"]
assert len(maps)==1
nm=maps[0]
assert nm.inputs["Color"].is_linked
original_normal=nm.inputs["Color"].links[0].from_socket
nm.inputs["Strength"].default_value=.24
for nd in nodes:
 if nd.type=="BUMP":
  nd.inputs["Strength"].default_value=.016
  nd.inputs["Distance"].default_value=.00015
 if nd.type=="TEX_IMAGE" and nd.image:
  assert nd.image.packed_file,nd.image.name
  if any(k in nd.image.name.upper() for k in ("NORMAL","ORM","HEIGHT")):
   assert nd.image.colorspace_settings.name=="Non-Color"
# Same source tangent space; blend normals in NON-COLOR RGB encoding before
# the source NORMAL_MAP conversion, preserving original packed map RGB.
uvnode=nodes.new("ShaderNodeUVMap")
uvnode.name="V8_13_PLEAT_DETAIL_UV_SOURCE"
uvnode.uv_map=DETAIL_UV
tex=nodes.new("ShaderNodeTexImage")
tex.name="V8_13_PACKED_PLEAT_NORMAL_IMAGE"
tex.image=img
tex.interpolation="Linear"
tex.extension="EXTEND"
links.new(uvnode.outputs["UV"],tex.inputs["Vector"])
mix=nodes.new("ShaderNodeMixRGB")
mix.name="V8_13_SOURCE_PLUS_PLEAT_TANGENT_NORMAL"
mix.blend_type="MIX"
mix.inputs[0].default_value=.36
links.new(original_normal,mix.inputs[1])
links.new(tex.outputs["Color"],mix.inputs[2])
links.new(mix.outputs["Color"],nm.inputs["Color"])
assert nm.inputs["Color"].links[0].from_node==mix
assert bsdf.inputs["Normal"].is_linked
mat["DAYTONA_V8_13"]="original packed BaseColor/tangent Normal/ORM green roughness/Height + 512x512 packed pleat tangent normal"
mat["DAYTONA_V8_13_TEXTURE_SHA256"]=generated_sha
mat["DAYTONA_V8_13_ORIGINAL_NORMAL_PRESERVED"]=True

def curve_update(name,pts):
 ob=bpy.data.objects[name]
 assert ob.type=="CURVE" and len(ob.data.splines)==1
 s=ob.data.splines[0]
 assert s.type=="POLY" and len(s.points)==len(pts),(name,len(s.points),len(pts))
 for p,xyz in zip(s.points,pts):
  p.co=(*xyz,1.)
 return len(pts)

report={}
for side,cx in (("L",-.353),("R",.353)):
 name="V8_"+side+"_CLASSIC_PADDED_CUSHION"
 ob=bpy.data.objects[name];me=ob.data
 assert ob.type=="MESH" and not ob.hide_render
 assert len(me.vertices)==2*RING and len(me.polygons)==7736
 assert me.uv_layers.active.name=="V8_9_RESCULPTED_GEODESIC_UV"
 assert [m.name for m in me.materials]==[
  "V8_9_Source_Charcoal_Seat_PBR","V8_9_Source_Charcoal_Seat_Side_PBR"]
 old_counts=(len(me.vertices),len(me.polygons),len(me.loops))
 oldtop=[me.vertices[i].co.z for i in range(RING)]
 for j in range(NY+1):
  t=j/NY
  for i in range(NX+1):
   u=i/NX;k=j*(NX+1)+i
   top=me.vertices[k]
   below=me.vertices[RING+k]
   dz=new_relief(t,u)-old_crest(t,u)
   top.co.z+=dz
   below.co=(top.co.x,top.co.y+.006,top.co.z-.049)
 me.update()
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 def top(j,i):
  v=me.vertices[j*(NX+1)+i].co
  return (float(v.x),float(v.y),float(v.z))
 # Geodesic lengths along new actual mesh edges, not a screen-space texture.
 us=[[0.]*73 for _ in range(53)]
 vs=[[0.]*73 for _ in range(53)]
 for j in range(53):
  for i in range(73):
   if i:us[j][i]=us[j][i-1]+math.dist(top(j,i),top(j,i-1))
   if j:vs[j][i]=vs[j-1][i]+math.dist(top(j,i),top(j-1,i))
 assert me.uv_layers.get(UV_NAME) is None
 texuv=me.uv_layers.new(name=UV_NAME)
 normuv=me.uv_layers.new(name=DETAIL_UV)
 for poly in me.polygons:
  for li in poly.loop_indices:
   idx=me.loops[li].vertex_index%RING
   j,i=divmod(idx,73)
   texuv.data[li].uv=(us[j][i]*5.45,vs[j][i]*5.45)
   normuv.data[li].uv=(i/NX,j/NY)
 me.uv_layers.active=texuv
 # Preserve inner return source material but darken only the sculpted crown:
 me.materials[0]=mat
 assert me.materials[1].name=="V8_9_Source_Charcoal_Seat_Side_PBR"
 # Reproject EVERY already existing original cushion curve to new mesh
 # (not just visible top stitches). Counts and names are preserved.
 touched=[]
 for edge,i in (("LEFT",3),("RIGHT",69)):
  touched.append(("V8_5_"+side+"_CUSHION_"+edge+"_WELT",
   [(x,y,z+.0012) for x,y,z in (top(j,i) for j in range(1,NY))]))
 for frac in (.23,.48,.72):
  j=round(frac*NY)
  touched.append(("V8_5_"+side+"_CUSHION_STITCH_"+format(frac,".2f"),
   [(x,y,z+.0011) for x,y,z in (top(j,i) for i in range(11,NX-10))]))
 for edge,i in (("LEFT",14),("RIGHT",NX-14)):
  touched.append(("V8_6_"+side+"_CUSHION_INSET_"+edge+"_BOLSTER_SEAM",
   [(x,y,z+.0013) for x,y,z in (top(j,i) for j in range(5,NY-4))]))
 for frac in (.16,.32,.64,.80):
  j=round(frac*NY)
  touched.append(("V8_7_"+side+"_PLEATED_CUSHION_STITCH_"+format(frac,".2f"),
   [(x,y,z+.0011) for x,y,z in (top(j,i) for i in range(13,NX-12))]))
 touched.append(("V8_7_"+side+"_FRONT_CUSHION_APRON_WELT",
  [(x,y,z+.0014) for x,y,z in (top(NY,i) for i in range(4,NX-3))]))
 for name,coords in touched:curve_update(name,coords)
 assert len(touched)==12
 assert (len(me.vertices),len(me.polygons),len(me.loops))==old_counts
 assert all(math.isfinite(float(q)) for v in me.vertices for q in v.co)
 assert all(math.isfinite(float(q)) for p in me.polygons for q in p.normal)
 assert all(math.isfinite(float(q)) for p in texuv.data for q in p.uv)
 assert all(math.isfinite(float(q)) for p in normuv.data for q in p.uv)
 xyz=[top(j,i) for j in range(53) for i in range(73)]
 bnd=[[min(p[k] for p in xyz),max(p[k] for p in xyz)] for k in range(3)]
 assert max(abs(bnd[0][0]),abs(bnd[0][1]))<=PMT_SEAT["max_abs_x"]
 assert bnd[1][0]>PMT_SEAT["rear_y"] and bnd[1][1]<PMT_SEAT["front_y"]
 assert bnd[2][0]>PMT_SEAT["min_z"] and bnd[2][1]<.49
 changed=sum(abs(float(oldtop[k])-float(me.vertices[k].co.z))>1e-5 for k in range(RING))
 assert changed>1500,changed
 # New channel-depth practical geometry in local metres; avoid an alleged
 # "source PMT exact channel count" while measuring new Blender shape.
 report[side]={"mesh":ob.name,"vertices":old_counts[0],
   "polygons":old_counts[1],"physically_changed_top_vertices":changed,
   "top_z_bounds":[round(bnd[2][0],6),round(bnd[2][1],6)],
   "seven_pad_centers":NEW_CRESTS,"six_dividing_channels":NEW_GROOVES,
   "new_metric_UV":texuv.name,"packed_normal_UV":normuv.name,
   "seams_reprojected":len(touched),"material":mat.name}
 ob["DAYTONA_V8_13"]="seven transverse PMT-inferred pleat geometry on existing 2-skin seat + geodesic UV and packed normal"

assert not bpy.data.objects.get("V8_13_DUPLICATE_CUSHION")
for side in "LR":
 assert bpy.data.objects["V5_"+side+"_SEAT_RECLINED_PADDED_BACK"].data.materials[0].name=="V8_12_Source_Charcoal_Original_V5_Back_Return_PBR"
 assert len(bpy.data.objects["V8_9_"+side+"_INTEGRATED_PADDED_HEADREST"].data.vertices)==242
 assert len(bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.vertices)==8614
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
sc.render.engine="CYCLES";sc.cycles.samples=10;sc.cycles.use_denoising=True
sc.render.resolution_x=960;sc.render.resolution_y=640
sc.render.resolution_percentage=100;sc.view_settings.exposure=-.52
for im in bpy.data.images:
 if im.source=="FILE" and not im.packed_file:im.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
manifest={"status":"DAYTONA_V8_13_REAL_BLENDER_SAVED",
 "input":SOURCE.name,"input_sha256":EXPECTED,
 "output":DEST.name,"output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "output_bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "cushions":report,
 "generated_normal":NORMAL_PATH.name,"generated_normal_sha256":generated_sha,
 "packed_normal":img.packed_file is not None,
 "source_normal_orm_height_preserved":True,
 "original_controls_doors_wheel_v812_preserved":True,
 "camera":sc.camera.name,"render_validation":"UNTESTED",
 "full_resolution_matched":"UNTESTED",
 "original_game_modified":False,"OVC_created":False,"Quest3_tested":False}
MANIFEST.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("DAYTONA_V8_13_MODEL_SAVED",json.dumps(manifest),flush=True)
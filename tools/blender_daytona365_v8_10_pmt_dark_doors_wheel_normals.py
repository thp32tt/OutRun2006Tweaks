#!/usr/bin/env python3
"""Daytona 365 GTS/4 v8.10: original-PMT dark door cards and ebony wheel, sculpted door pleats.

Uses private immutable actual Blender v8.9. Changes are material and physical
original-source door card geometry only. Never writes PMT/OVC/EXE or runtime files.
"""
import bpy, bmesh, hashlib, json, math, os
from pathlib import Path

ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_9.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_10.blend"
EXPECTED="bfd91e5e29d796e708918298678305172ec21fff958122d2eed72118303ca9c2"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
assert not DEST.exists(),"Never overwrite v8.10 immutable scene"
s=bpy.context.scene
assert s.camera.name=="V7_Camera_Reference_ThreeQuarter"
protected=("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM")
for name in protected:assert bpy.data.objects.get(name),name

def darken_source(src,name,saturation,value,rmin,rmax,nstrength,bstrength,bdistance):
 assert name not in bpy.data.materials
 m=bpy.data.materials[src].copy();m.name=name
 n=m.node_tree.nodes
 links=m.node_tree.links
 bsdf=n["Principled BSDF"]
 assert bsdf.inputs["Base Color"].is_linked
 assert bsdf.inputs["Roughness"].is_linked
 assert bsdf.inputs["Normal"].is_linked
 orig=bsdf.inputs["Base Color"].links[0].from_socket
 dark=n.new("ShaderNodeHueSaturation")
 dark.name="V8_10_PMT_DARK_SOURCE_BASECOLOR"
 dark.inputs["Hue"].default_value=.5
 dark.inputs["Saturation"].default_value=saturation
 dark.inputs["Value"].default_value=value
 links.new(orig,dark.inputs["Color"])
 links.new(dark.outputs["Color"],bsdf.inputs["Base Color"])
 bsdf.inputs["Metallic"].default_value=0.
 rough=n["V8_5_ORM_ROUGHNESS_RANGE"]
 assert rough.inputs["Value"].is_linked
 rough.inputs["To Min"].default_value=rmin
 rough.inputs["To Max"].default_value=rmax
 for nd in n:
  if nd.type=="NORMAL_MAP":
   nd.inputs["Strength"].default_value=nstrength
  elif nd.type=="BUMP":
   nd.inputs["Strength"].default_value=bstrength
   nd.inputs["Distance"].default_value=bdistance
  elif nd.type=="TEX_IMAGE" and nd.image:
   assert nd.image.packed_file,(name,nd.image.name)
   if any(q in nd.image.name.upper() for q in ("NORMAL","ORM","HEIGHT")):
    assert nd.image.colorspace_settings.name=="Non-Color",nd.image.name
 images=[nd.image.name for nd in n if nd.type=="TEX_IMAGE" and nd.image]
 assert len(images)>=4
 m["V8_10_SOURCE_PBR"]="original packed BaseColor, tangent Normal, ORM-green, Height retained"
 m["V8_10_SOURCE_MATERIAL"]=src
 m["V8_10_COLOR_SETTINGS"]=[saturation,value]
 return m

DOOR=darken_source("V8_6_Soft_Door_Card_Leather",
 "V8_10_Source_Charcoal_Door_Leather_PBR",.085,.16,.74,.91,.21,.014,.00013)
LOWER=darken_source("V8_6_Soft_Door_Card_Leather",
 "V8_10_Source_Charcoal_Door_Lower_PBR",.08,.125,.79,.93,.14,.010,.00011)
WHEEL=darken_source("V7_Target_Walnut_Steering_Rim_PBR",
 "V8_10_Source_Ebonized_Steering_Rim_PBR",.09,.205,.55,.76,.17,.008,.00009)
THREAD=darken_source("V8_6_Soft_Door_Card_Leather",
 "V8_10_Source_Black_Door_Seam_PBR",.06,.11,.78,.94,.12,.008,.00011)

door_report={}
for side,sgn in (("L",1),("R",-1)):
 name="V5_"+side+"_LEATHER_SCULPTED_DOOR"
 ob=bpy.data.objects[name];mesh=ob.data
 assert ob.type=="MESH" and len(mesh.vertices)==15*31
 orig=(len(mesh.vertices),len(mesh.polygons))
 assert mesh.uv_layers.active.name=="UVMap"
 # Original surface grid is [15 height rows] x [31 length columns].
 # The existing original V5 door remains the editable mesh; add 4 subtle
 # upholstered longitudinal bands, outward normal displacement <=3.5 mm.
 for j in range(15):
  z=.430+.035*j
  for i in range(31):
   p=mesh.vertices[j*31+i]
   y=float(p.co.y)
   fade_y=(max(0.,1.-abs((y+.30)/.82)))**.7
   pad=sum(.0033*math.exp(-((z-zt)/.031)**2)
    for zt in (.535,.605,.675,.745))
   stitch_groove=sum(.0010*math.exp(-((z-zt)/.011)**2)
    for zt in (.569,.639,.709))
   p.co.x+=sgn*(pad-stitch_groove)*fade_y
 mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(mesh);bm.free()
 for p in mesh.polygons:p.use_smooth=True
 # Real per-edge geodesic, not UV projection from an arbitrary screen:
 # each flattened direction measures the new topology in metres.
 U=[[0.]*31 for _ in range(15)]
 V=[[0.]*31 for _ in range(15)]
 def coord(j,i):
  return tuple(float(x) for x in mesh.vertices[j*31+i].co)
 for j in range(15):
  for i in range(31):
   if i:U[j][i]=U[j][i-1]+math.dist(coord(j,i),coord(j,i-1))
   if j:V[j][i]=V[j-1][i]+math.dist(coord(j,i),coord(j-1,i))
 assert mesh.uv_layers.get("V8_10_DOOR_GEODESIC_UV") is None
 uv=mesh.uv_layers.new(name="V8_10_DOOR_GEODESIC_UV")
 for poly in mesh.polygons:
  for li in poly.loop_indices:
   vi=mesh.loops[li].vertex_index
   j,i=divmod(vi,31)
   uv.data[li].uv=(U[j][i]*4.9,V[j][i]*4.9)
 mesh.uv_layers.active=uv
 assert len(mesh.materials)==1
 mesh.materials[0]=DOOR
 assert (len(mesh.vertices),len(mesh.polygons))==orig
 assert all(math.isfinite(float(q)) for p in mesh.vertices for q in p.co)
 assert all(math.isfinite(float(q)) for p in uv.data for q in p.uv)

 # Physical true curve seams conform to newly sculpted surface rows, not
 # object-space 2D marks. Keep chrome latch/trim and black pull untouched.
 for j in (6,8):
  positions=[]
  for i in range(2,29):
   x,y,z=coord(j,i)
   positions.append((x+sgn*.0011,y,z))
  cu=bpy.data.curves.new("V8_10_"+side+"_DOOR_SEAM_"+str(j),"CURVE")
  cu.dimensions="3D";cu.bevel_depth=.00042;cu.bevel_resolution=3
  sp=cu.splines.new("POLY");sp.points.add(len(positions)-1)
  for q,xyz in zip(sp.points,positions):q.co=(*xyz,1.)
  cu.materials.append(THREAD)
  co=bpy.data.objects.new(cu.name,cu)
  s.collection.objects.link(co)
  co["DAYTONA_V8_10"]="source-mesh-following sculpted longitudinal door seam"

 # The original V8.6 door lower-panel UV topology already used metric PBR.
 lower=bpy.data.objects["V8_3_"+side+"_TAN_DOOR_LOWER_PAD"]
 assert lower.data.uv_layers.active.name=="V8_6_DOOR_METRIC_UV"
 assert len(lower.data.vertices)==8
 lower.data.materials[0]=LOWER
 pocket=bpy.data.objects["V6_"+side+"_BLENDER_SADDLE_DOOR_POCKET"]
 assert len(pocket.data.vertices)==8
 pocket.data.materials[0]=LOWER
 border=bpy.data.objects["V6_"+side+"_BLENDER_DOOR_STITCH_BORDER"]
 assert border.type=="CURVE"
 border.data.materials[0]=THREAD
 door_report[side]={"source_door":name,"vertices":orig[0],"polygons":orig[1],
    "preserved_uv":"UVMap","new_uv":uv.name,"physical_pleat_bands":4,
    "source_material":DOOR.name,"lower_panel":LOWER.name,
    "conformal_seam_rows":[6,8]}

for obj_name in ("V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material002_a0"):
 ob=bpy.data.objects[obj_name]
 assert ob.type=="MESH" and ob.data.materials[0].name=="V7_Target_Walnut_Steering_Rim_PBR"
 assert len(ob.data.vertices)>100
 ob.data.materials[0]=WHEEL
 ob["DAYTONA_V8_10"]="original intact steering geometry + source walnut normal/ORM, dark PMT ebonized tint"
assert s.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert bpy.data.objects["DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3"]
s.render.engine="CYCLES";s.cycles.samples=10;s.cycles.use_denoising=True
s.render.resolution_x=960;s.render.resolution_y=640
s.render.resolution_percentage=100;s.view_settings.exposure=-.52
for im in bpy.data.images:
 if im.source=="FILE" and not im.packed_file:im.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.is_file()
manifest={"status":"DAYTONA_V8_10_REAL_BLENDER_SAVED",
 "source":SOURCE.name,"source_sha256":EXPECTED,
 "output":DEST.name,"new_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "doors":door_report,"wheel_original_geometry_preserved":True,
 "source_packed_basecolor_normal_orm_height":True,
 "native_h_shifter_gauges_switchbank_emblem_preserved":True,
 "camera":s.camera.name,
 "render_validation":"UNTESTED","full_matched_render":"UNTESTED",
 "game_runtime":"UNTESTED","OVC_created":False,
 "Quest3_tested":False,"original_game_files_modified":False}
(W/"DAYTONA_V8_10_BUILD_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("DAYTONA_V8_10_MODEL_SAVED",json.dumps(manifest),flush=True)
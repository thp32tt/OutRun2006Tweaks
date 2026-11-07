#!/usr/bin/env python3
"""Daytona 365 GTS/4 v8.15: PMT017-bounded real side bolsters and front apron.

On exact immutable private v8.14 source, modify the two EXISTING V8 cushion
meshes and reproject the 24 established seam curves, preserving v8.13 seven
physical pleats and their packed tangent normal, existing source controls,
v8.14 H-gate and original source PMT materials. No runtime/OVC/Quest edits.
"""
import bpy,bmesh,math,hashlib,json,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
SRC=W/"Daytona365_Cockpit_Blender_PBR_v8_14.blend"
DST=W/"Daytona365_Cockpit_Blender_PBR_v8_15.blend"
SHA="6de017b7f62b60a8484eef1b5eb8c851db037bd2ab88b1d09a79259b91702c77"
MANIFEST=W/"DAYTONA_V8_15_BUILD_MANIFEST.json"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SRC.resolve()
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA
assert not DST.exists() and not MANIFEST.exists(),"No immutable output overwrite"
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
for name in ("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_1_COMPACT_SHIFTER_LEATHER_DECK"):
 assert bpy.data.objects.get(name),name
gate=bpy.data.objects["DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3"]
shift=bpy.data.objects["V8_1_COMPACT_SHIFTER_LEATHER_DECK"]
assert len(gate.data.vertices)==32 and len(shift.data.vertices)==100
PMT_SEAT={"max_abs_x":.57464,"rear_y":-.72863,"front_y":-.01985,
 "min_z":.33179,"max_z":.85149}
NX,NY=72,52
RING=(NX+1)*(NY+1)
UV_NAME="V8_15_CROWN_BOLSTER_APRON_METRIC_UV"
PACKED_NORMAL_UV="V8_13_Seven_Pleat_Aligned_Normal_UV"
SEAT_SOURCE="V8_13_Source_Sculpted_Charcoal_Cushion_PBR"
SIDE_SOURCE="V8_9_Source_Charcoal_Seat_Side_PBR"
assert SEAT_SOURCE in bpy.data.materials and SIDE_SOURCE in bpy.data.materials

# New source-linked PBR variant reserved for top-outer sculpted bolsters:
# don't darken/alter the v8.13 central 7-pleat material or source images.
BOLSTER=bpy.data.materials[SIDE_SOURCE].copy()
BOLSTER.name="V8_15_Source_PMT017_Outer_Bolster_Packed_PBR"
node=BOLSTER.node_tree.nodes
pbr=node["Principled BSDF"]
for key in ("Base Color","Normal","Roughness"):
 assert pbr.inputs[key].is_linked,key
hsv=node["V8_9_PMT_CHARCOAL_DESATURATION"]
hsv.inputs["Saturation"].default_value=.125
hsv.inputs["Value"].default_value=.305
rough=node["V8_5_ORM_ROUGHNESS_RANGE"]
assert rough.inputs["Value"].is_linked
rough.inputs["To Min"].default_value=.75
rough.inputs["To Max"].default_value=.91
pbr.inputs["Metallic"].default_value=0.0
packed=[]
for n in node:
 if n.type=="NORMAL_MAP":n.inputs["Strength"].default_value=.21
 if n.type=="BUMP":
  n.inputs["Strength"].default_value=.011
  n.inputs["Distance"].default_value=.00013
 if n.type=="TEX_IMAGE" and n.image:
  assert n.image.packed_file,n.image.name
  if any(k in n.image.name.upper() for k in ("ORM","NORMAL","HEIGHT")):
   assert n.image.colorspace_settings.name=="Non-Color"
  packed.append(n.image.name)
assert len(packed)>=4
assert any("ORM" in v.upper() for v in packed)
assert any("NORMAL" in v.upper() for v in packed)
BOLSTER["DAYTONA_V8_15"]="real source-packed BaseColor/tangent Normal/ORM(G)/Height, outer physical shoulder only"

def clamp(x):return max(0.,min(1.,x))
def smoothstep(lo,hi,x):
 t=clamp((x-lo)/(hi-lo))
 return t*t*(3.-2*t)
def gauss(t,c,width):return math.exp(-((t-c)/width)**2)
def reproject(name,pts):
 ob=bpy.data.objects[name]
 assert ob.type=="CURVE" and len(ob.data.splines)==1
 sp=ob.data.splines[0]
 assert sp.type=="POLY" and len(sp.points)==len(pts),(name,len(sp.points),len(pts))
 for point,coord in zip(sp.points,pts):point.co=(*coord,1.)
 return name

report={}
for side in ("L","R"):
 o=bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"]
 me=o.data
 assert o.type=="MESH" and len(me.vertices)==2*RING and len(me.polygons)==7736
 assert me.uv_layers.active.name=="V8_13_Geodesic_Seat_Leather_UV"
 assert me.uv_layers.get(PACKED_NORMAL_UV)
 assert len(me.materials)==2
 assert me.materials[0].name==SEAT_SOURCE and me.materials[1].name==SIDE_SOURCE
 before=(len(me.vertices),len(me.polygons),len(me.loops))
 old_top=[v.co.copy() for v in me.vertices[:RING]]
 # Sculpt independent physical shoulder volume on the existing top skin:
 # +/- 8 mm narrow outer crowns that fade before the seven central flutes.
 # The leading edge has a rounded 7 mm roll and 5 mm final fall. Connected
 # rear skin remains 49 mm below every source top vertex (not floating mesh).
 for j in range(NY+1):
  t=j/NY
  span=smoothstep(.08,.20,t)*(1.-smoothstep(.80,.98,t))
  for i in range(NX+1):
   u=i/NX
   lateral=abs(2*u-1)
   k=j*(NX+1)+i
   p=me.vertices[k]
   underside=me.vertices[RING+k]
   lift=.0081*gauss(lateral,.76,.145)*span
   lip=.0074*gauss(t,.938,.045)*(1.-.25*lateral)
   edgefall=.0048*smoothstep(.954,1.0,t)*(1.-.22*lateral)
   dx=(.0015*smoothstep(.83,.99,lateral)*span)*(1 if u>.5 else -1)
   p.co.x+=dx
   p.co.z+=lift+lip-edgefall
   # Controlled roll-down at the front: beneath the leading edge the
   # connected return bends 8 mm forward, still inside PMT017 front_y.
   under_y=.006+.0080*smoothstep(.82,1.0,t)
   underside.co=(p.co.x,p.co.y+under_y,p.co.z-.049)
 me.update()
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(me);bm.free()
 me.update()
 for face in me.polygons:face.use_smooth=True
 def vertex(j,i):
  p=me.vertices[j*73+i].co
  return float(p.x),float(p.y),float(p.z)
 # Regenerate source-metric tangent UV on the ACTUAL deformed surface.
 ulen=[[0.]*73 for _ in range(53)]
 vlen=[[0.]*73 for _ in range(53)]
 for j in range(53):
  for i in range(73):
   if i:ulen[j][i]=ulen[j][i-1]+math.dist(vertex(j,i),vertex(j,i-1))
   if j:vlen[j][i]=vlen[j-1][i]+math.dist(vertex(j,i),vertex(j-1,i))
 assert me.uv_layers.get(UV_NAME) is None
 uv=me.uv_layers.new(name=UV_NAME)
 for poly in me.polygons:
  for li in poly.loop_indices:
   idx=me.loops[li].vertex_index%RING;j,i=divmod(idx,73)
   uv.data[li].uv=(ulen[j][i]*5.45,vlen[j][i]*5.45)
 me.uv_layers.active=uv
 # Add a third PBR slot only to center-independent physically outer top
 # polygons. Existing 7-pleat central crown and 49mm backside stay intact.
 me.materials.append(BOLSTER)
 outer_faces=0
 for face in me.polygons:
  ids=[me.loops[k].vertex_index for k in face.loop_indices]
  if ids and all(v<RING for v in ids):
   avg_u=sum((v%73)/72 for v in ids)/len(ids)
   a=abs(2*avg_u-1)
   if a>=.61:
    face.material_index=2
    outer_faces+=1
 assert outer_faces>900,outer_faces
 # Existing original-oriented seam objects (12 per cushion) are moved
 # onto the new nonplanar physical surface. No duplicate floating stitches.
 seams=[]
 for edge,i in (("LEFT",3),("RIGHT",69)):
  seams.append(reproject("V8_5_"+side+"_CUSHION_"+edge+"_WELT",
   [(x,y,z+.0012) for x,y,z in (vertex(j,i) for j in range(1,NY))]))
 for f in (.23,.48,.72):
  j=round(f*NY)
  seams.append(reproject("V8_5_"+side+"_CUSHION_STITCH_"+format(f,".2f"),
   [(x,y,z+.0011) for x,y,z in (vertex(j,i) for i in range(11,NX-10))]))
 for edge,i in (("LEFT",14),("RIGHT",58)):
  seams.append(reproject("V8_6_"+side+"_CUSHION_INSET_"+edge+"_BOLSTER_SEAM",
   [(x,y,z+.0013) for x,y,z in (vertex(j,i) for j in range(5,NY-4))]))
 for f in (.16,.32,.64,.80):
  j=round(f*NY)
  seams.append(reproject("V8_7_"+side+"_PLEATED_CUSHION_STITCH_"+format(f,".2f"),
   [(x,y,z+.0011) for x,y,z in (vertex(j,i) for i in range(13,NX-12))]))
 seams.append(reproject("V8_7_"+side+"_FRONT_CUSHION_APRON_WELT",
  [(x,y,z+.0014) for x,y,z in (vertex(NY,i) for i in range(4,NX-3))]))
 assert len(seams)==12
 assert (len(me.vertices),len(me.polygons),len(me.loops))==before
 assert me.uv_layers.get(PACKED_NORMAL_UV) is not None
 assert all(math.isfinite(float(z)) for v in me.vertices for z in v.co)
 assert all(math.isfinite(float(z)) for p in me.polygons for z in p.normal)
 assert all(math.isfinite(float(z)) for loop in uv.data for z in loop.uv)
 assert all(abs(me.vertices[RING+k].co.z-me.vertices[k].co.z+.049)<1e-6 for k in range(RING))
 top=[vertex(j,i) for j in range(53) for i in range(73)]
 bound=[[min(v[k] for v in top),max(v[k] for v in top)] for k in range(3)]
 assert max(abs(bound[0][0]),abs(bound[0][1]))<PMT_SEAT["max_abs_x"]
 assert bound[1][0]>PMT_SEAT["rear_y"] and bound[1][1]<PMT_SEAT["front_y"]
 assert bound[2][0]>PMT_SEAT["min_z"] and bound[2][1]<.49
 changed=sum((v.co-old_top[i]).length>.001 for i,v in enumerate(me.vertices[:RING]))
 assert changed>900,changed
 # Peak bolster is a real per-vertex difference; film-only coloring isn't a feature.
 peak=max(abs(float(v.co.z-old_top[k].z)) for k,v in enumerate(me.vertices[:RING]))
 assert peak>.006,peak
 front_edge=[vertex(NY,i) for i in range(73)]
 assert math.isfinite(min(q[2] for q in front_edge))
 o["DAYTONA_V8_15"]="physical original-bounded side shoulder and rolled front apron in source seat shell; source-texture bolster PBR"
 report[side]={"object":o.name,"vertices":before[0],"faces":before[1],
  "material_slots":len(me.materials),"outer_bolster_faces":outer_faces,
  "changed_top_vertices_over_1mm":changed,"maximum_z_sculpt_m":round(peak,6),
  "top_bounds_m":bound,"new_metric_uv":UV_NAME,
  "pleat_normal_uv_preserved":PACKED_NORMAL_UV,
  "apron_forward_return_m":.014,
  "physical_rear_depth_m":.049,"seam_curves_reprojected":seams}
for side in ("L","R"):
 assert bpy.data.objects["V5_"+side+"_SEAT_RECLINED_PADDED_BACK"].data.materials[0].name=="V8_12_Source_Charcoal_Original_V5_Back_Return_PBR"
 assert bpy.data.objects["V8_"+side+"_TAPERED_PADDED_BACKREST"].data.uv_layers.active.name=="V8_11_CROWN_GEODESIC_UV"
 assert bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"].data.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
assert sum(o.type=="MESH" for o in bpy.data.objects)==106
assert sum(o.type=="CURVE" for o in bpy.data.objects)==94
assert len(bpy.data.objects["DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3"].data.vertices)==32
assert len(bpy.data.objects["V8_1_COMPACT_SHIFTER_LEATHER_DECK"].data.vertices)==100
scene.render.engine="CYCLES";scene.cycles.samples=10
scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.view_settings.exposure=-.52
for img in bpy.data.images:
 if img.source=="FILE" and not img.packed_file:img.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DST),compress=True)
assert DST.is_file()
result={"status":"DAYTONA_V8_15_REAL_BLENDER_SAVED",
 "input":SRC.name,"input_sha256":SHA,
 "output":DST.name,"output_sha256":hashlib.sha256(DST.read_bytes()).hexdigest(),
 "bytes":DST.stat().st_size,"blender":bpy.app.version_string,
 "preserved_camera":scene.camera.name,
 "PMT017_aggregate_bounds":PMT_SEAT,"source_packed_PBR":packed,
 "sculpted_source_seat_shells":report,
 "v813_pleats_and_normal_v814_gate_preserved":True,
 "render_validation":"UNTESTED","matched_full_res":"UNTESTED",
 "game_runtime":"UNTESTED","OVC_created":False,
 "Quest3_tested":False,"original_game_files_modified":False}
MANIFEST.write_text(json.dumps(result,indent=2),encoding="utf-8")
print("DAYTONA_V8_15_MODEL_SAVED",json.dumps(result),flush=True)
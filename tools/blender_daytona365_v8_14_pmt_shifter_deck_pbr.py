#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona Blender v8.14: true fitted H-gate underdeck.

Read the unmodified independent v8.13 seat-channel scene. Refine only the
preexisting flat 8-vertex shifter leather deck into a 10-section molded
leather underlay below the preserved real source-aligned chrome H gate,
with 3D edge rolls, bevel, recalculated normals, metric tangent UV, two
physical stitching paths, and source-packed PBR maps. No game files touched.
"""
import bpy,bmesh,math,hashlib,json,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_13.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_14.blend"
SHA="130accf3db850df025c836c0364d5a8dfebcf6001a88e61d19135b4331499cc7"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
assert not DEST.exists(),"No overwrite of a v8.14 candidate"
sc=bpy.context.scene
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
controls=("DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM")
for n in controls:assert bpy.data.objects.get(n),n
gate=bpy.data.objects[controls[2]]
assert gate.type=="MESH" and len(gate.data.vertices)==32
gate_before=[tuple(float(c) for c in p.co) for p in gate.data.vertices]
knob=bpy.data.objects[controls[3]]
knob_before=[tuple(float(c) for c in p.co) for p in knob.data.vertices]
o=bpy.data.objects["V8_1_COMPACT_SHIFTER_LEATHER_DECK"]
assert o.type=="MESH" and len(o.data.vertices)==8 and len(o.data.polygons)==6
assert o.data.materials[0].name=="V8_8_PMT_Console_Matte_Grain"
assert o.data.uv_layers.active
oldmesh=o.data
# Genuine original PMT group018 console aggregate X +/-106.83mm,
# Y [-235.55,+202.28]mm, Z [.33638,.51887]m: spatial bounds only.
PMT018={"x":(-.10683,.10683),"y":(-.23555,.20228),
 "z":(.33638,.51887)}
# Source Chrome gate is x [-.077,+.077], y[-.160,-.021],
# Z[.43546,.46598]. New deck fits outside the opening under it.
# Retain steel mechanism and knob intact; no copied game vertices.
stations=[
 (-.2250,.070,.4020,.4205),
 (-.2080,.083,.4040,.4232),
 (-.1840,.088,.4050,.4268),
 (-.1610,.091,.4070,.4292),
 (-.1390,.092,.4090,.4327),
 (-.1160,.092,.4120,.4375),
 (-.0910,.090,.4140,.4425),
 (-.0670,.086,.4160,.4490),
 (-.0390,.081,.4180,.4545),
 (-.0120,.068,.4210,.4608),
]
assert len(stations)==10
assert max(w for y,w,bot,top in stations)<.10683
assert min(y for y,w,b,t in stations)>=PMT018["y"][0]
assert max(z for y,w,b,z in stations)<PMT018["z"][1]
# Ten cross-sectional samples encircle an actually thick padded surface;
# top profile is not a rectangle or a floating plane.
N=10
verts=[]
for y,w,bot,top in stations:
 verts.extend([
  (-w,y,top-.006),
  (-w*.94,y,top-.0014),
  (-w*.79,y,top+.0000),
  (-w*.28,y,top+.0012),
  (w*.28,y,top+.0012),
  (w*.79,y,top+.0000),
  (w*.94,y,top-.0014),
  (w,y,top-.006),
  (w*.96,y,bot),
  (-w*.96,y,bot),
 ])
faces=[]
for j in range(len(stations)-1):
 for k in range(N):
  a=j*N+k;b=j*N+(k+1)%N
  faces.append((a,b,b+N,a+N))
faces.extend((tuple(reversed(range(N))),
              tuple((len(stations)-1)*N+k for k in range(N))))
mesh=bpy.data.meshes.new("V8_14_PMT018_10x10_Shifter_Underdeck_Mesh")
mesh.from_pydata(verts,[],faces);mesh.update(calc_edges=True)
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
bm.to_mesh(mesh);bm.free()
for f in mesh.polygons:f.use_smooth=True
# Genuine source-packed console PBR; darken photographic base color without
# replacing it with a painted flat base.
material=bpy.data.materials["V8_8_PMT_Console_Matte_Grain"].copy()
material.name="V8_14_PMT018_Shifter_Deck_Grain_Source_PBR"
nodes=material.node_tree.nodes;links=material.node_tree.links
shader=nodes["Principled BSDF"]
for socket in ("Base Color","Roughness","Normal"):
 assert shader.inputs[socket].is_linked,socket
orig=shader.inputs["Base Color"].links[0].from_socket
hsv=nodes.new("ShaderNodeHueSaturation")
hsv.name="V8_14_PMT018_SOURCE_DARK_LEATHER"
hsv.inputs["Hue"].default_value=.5
hsv.inputs["Saturation"].default_value=.70
hsv.inputs["Value"].default_value=.53
links.new(orig,hsv.inputs["Color"])
links.new(hsv.outputs["Color"],shader.inputs["Base Color"])
rough=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
assert rough.inputs["Value"].is_linked
rough.inputs["To Min"].default_value=.765
rough.inputs["To Max"].default_value=.907
shader.inputs["Metallic"].default_value=0.
packed=[]
for n in nodes:
 if n.type=="NORMAL_MAP":n.inputs["Strength"].default_value=.19
 if n.type=="BUMP":
  n.inputs["Strength"].default_value=.012
  n.inputs["Distance"].default_value=.00013
 if n.type=="TEX_IMAGE" and n.image:
  assert n.image.packed_file,n.image.name
  if any(k in n.image.name.upper() for k in ("NORMAL","ORM","HEIGHT")):
   assert n.image.colorspace_settings.name=="Non-Color"
  packed.append(n.image.name)
assert len(packed)>=4
material["DAYTONA_V8_14_SOURCE"]="PMT aggregate geometry bounds, original source-packed PBR BaseColor/Normal/ORM/Height"
mesh.materials.append(material)
# Arc-length in cross section / along longitudinal stations for tangent
# frame; no default UVMap that stretches normal microtexture.
arc=[]
for j in range(len(stations)):
 ds=[0.]
 for k in range(1,N):
  ds.append(ds[-1]+math.dist(verts[j*N+k-1],verts[j*N+k]))
 total=ds[-1]+math.dist(verts[j*N+N-1],verts[j*N])
 arc.append((ds,total))
y0=stations[0][0]
uv=mesh.uv_layers.new(name="V8_14_PMT018_DECK_METRIC_TANGENT_UV")
for poly in mesh.polygons:
 if poly.index>=N*(len(stations)-1):
  for li in poly.loop_indices:
   v=mesh.vertices[mesh.loops[li].vertex_index].co
   uv.data[li].uv=(v.x*5.,v.z*5.)
 else:
  idx=[mesh.loops[li].vertex_index%N for li in poly.loop_indices]
  wrap=(0 in idx and N-1 in idx)
  for li in poly.loop_indices:
   index=mesh.loops[li].vertex_index;j,k=divmod(index,N)
   u=arc[j][1] if wrap and k==0 else arc[j][0][k]
   uv.data[li].uv=(u*5.,(stations[j][0]-y0)*5.)
mesh.uv_layers.active=uv
# Existing deck object retains ID and collection links; original source
# chrome gate, switch, lever stay in place.
o.data=mesh
o.location=(0,0,0);o.rotation_euler=(0,0,0);o.scale=(1,1,1)
if oldmesh.users==0:bpy.data.meshes.remove(oldmesh)
for m in list(o.modifiers):o.modifiers.remove(m)
bev=o.modifiers.new("V8_14_PMT018_Molded_Leather_Bevel","BEVEL")
bev.width=.0016;bev.segments=3;bev.limit_method="ANGLE"
bev.angle_limit=math.radians(38)
weighted=o.modifiers.new("V8_14_PMT018_Underdeck_Weighted_Normal","WEIGHTED_NORMAL")
weighted.keep_sharp=True
# Two original-style stitched leather side edges are actual 3D curves,
# distinct from native unmodified chrome H gate.
def seam(name,k):
 assert name not in bpy.data.objects
 data=bpy.data.curves.new(name+"_Path","CURVE")
 data.dimensions="3D";data.resolution_u=8
 data.bevel_depth=.00053;data.bevel_resolution=3
 spline=data.splines.new("POLY");spline.points.add(len(stations)-1)
 for j,p in enumerate(spline.points):
  x,y,z=verts[j*N+k]
  p.co=(x,y,z+.00065,1.)
 data.materials.append(material)
 obj=bpy.data.objects.new(name,data)
 for collection in o.users_collection:collection.objects.link(obj)
 return obj.name
left=seam("V8_14_LEFT_ORIGINAL_PMTCENTER_SHIFTER_DECK_WELT",2)
right=seam("V8_14_RIGHT_ORIGINAL_PMTCENTER_SHIFTER_DECK_WELT",5)
# Validate physical source continuity and avoid penetrating chrome: leather
# edge top follows 6-10mm below original upper chrome at representative y.
assert len(mesh.vertices)==100 and len(mesh.polygons)==92
assert abs(min(v.co.x for v in mesh.vertices)+.092)<.001
assert abs(max(v.co.x for v in mesh.vertices)-.092)<.001
assert abs(max(v.co.z for v in mesh.vertices)-.462)<.003
assert len(mesh.uv_layers.active.data)==len(mesh.loops)
assert all(math.isfinite(float(c)) for v in mesh.vertices for c in v.co)
assert all(math.isfinite(float(c)) for lp in uv.data for c in lp.uv)
assert gate_before==[tuple(float(c) for c in p.co) for p in gate.data.vertices]
assert knob_before==[tuple(float(c) for c in p.co) for p in knob.data.vertices]
for side in ("L","R"):
 cu=bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"]
 assert cu.data.uv_layers.active.name in ("V8_13_Geodesic_Seat_Leather_UV","V8_13_CHANNEL_GEODESIC_LEATHER_UV")
 assert bpy.data.objects["V5_"+side+"_SEAT_RECLINED_PADDED_BACK"].data.materials[0].name=="V8_12_Source_Charcoal_Original_V5_Back_Return_PBR"
assert sum(q.type=="MESH" for q in bpy.data.objects)==106
assert sum(q.type=="CURVE" for q in bpy.data.objects)==94
o["DAYTONA_V8_14"]="original existing deck 10-station fitted padding with 3D seams, metric normal UV and PMT018 bounds"
sc.render.engine="CYCLES";sc.cycles.samples=10
sc.cycles.use_denoising=True
sc.render.resolution_x=960;sc.render.resolution_y=640
sc.render.resolution_percentage=100
sc.view_settings.exposure=-.52
for im in bpy.data.images:
 if im.source=="FILE" and not im.packed_file:im.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
report={"status":"DAYTONA_V8_14_REAL_BLENDER_SAVED",
 "source":SOURCE.name,"source_sha256":SHA,
 "output":DEST.name,"output_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "replaced_object":o.name,"mesh_vertices":len(mesh.vertices),
 "mesh_polygons":len(mesh.polygons),"uv":uv.name,
 "PMT018_aggregate_bounds_m":PMT018,"station_count":len(stations),
 "physical_seams":[left,right],"source_PBR_packed_maps":packed,
 "native_gate_original_32_vertices_preserved":True,
 "native_knob_original_433_vertices_preserved":True,
 "v813_seat_channels_preserved":True,"camera":sc.camera.name,
 "render_validation":"UNTESTED","matched_full_res":"UNTESTED",
 "game_runtime":"UNTESTED","OVC_created":False,
 "Quest3_tested":False,"original_game_files_modified":False}
(W/"DAYTONA_V8_14_BUILD_MANIFEST.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_14_MODEL_SAVED",json.dumps(report),flush=True)
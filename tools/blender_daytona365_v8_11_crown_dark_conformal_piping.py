#!/usr/bin/env python3
"""Daytona 365 GTS/4 v8.11: PMT017-bounded continuous crown and surface-conformal dark upholstery welts.

Actual immutable input v8.10. Rebuild existing 2 headrest mesh datablocks rather
than creating additional overlapping objects. Project stale original v8.3 bright
Bezier seat piping and perimeter seams onto original 4 high-res seat shells.
No original PMT/DDS/OVC/game content exported or changed.
"""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
SOURCE=W/"Daytona365_Cockpit_Blender_PBR_v8_10.blend"
DEST=W/"Daytona365_Cockpit_Blender_PBR_v8_11.blend"
EXPECTED="ab60744f37c93f4db079a9be79b7df09f3d99006fc332e4a9f98e21b92acbb74"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert SOURCE.is_file() and hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
assert not DEST.exists(),"Do not overwrite completed/partial v8.11"
sc=bpy.context.scene
assert sc.camera and sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
for required in ("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
 "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH",
 "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V8_LOW_CENTER_TUNNEL"):
 assert bpy.data.objects.get(required),required
assert len(bpy.data.objects["V8_LOW_CENTER_TUNNEL"].data.vertices)==78
PMT017={"x_extents_m":[-.57464,.57464],"y_extents_m":[-.72863,-.01985],
 "z_extents_m":[.33179,.85149],"upper_left_x_m":[-.54831,-.13604],
 "upper_y_m":[-.72863,-.65045]}

def tune_mat(src,name,value,sat,normal,bump,roughmin,roughmax):
 assert name not in bpy.data.materials
 mat=bpy.data.materials[src].copy()
 mat.name=name
 nodes=mat.node_tree.nodes
 shader=nodes["Principled BSDF"]
 assert shader.inputs["Base Color"].is_linked
 assert shader.inputs["Normal"].is_linked and shader.inputs["Roughness"].is_linked
 hsv=nodes["V8_9_PMT_CHARCOAL_DESATURATION"]
 hsv.inputs["Saturation"].default_value=sat
 hsv.inputs["Value"].default_value=value
 rough=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
 assert rough.inputs["Value"].is_linked
 rough.inputs["To Min"].default_value=roughmin
 rough.inputs["To Max"].default_value=roughmax
 shader.inputs["Metallic"].default_value=0.0
 for n in nodes:
  if n.type=="NORMAL_MAP":n.inputs["Strength"].default_value=normal
  if n.type=="BUMP":
   n.inputs["Strength"].default_value=bump
   n.inputs["Distance"].default_value=.00014
  if n.type=="TEX_IMAGE" and n.image:
   assert n.image.packed_file,(name,n.image.name)
   if any(k in n.image.name.upper() for k in ("NORMAL","ORM","HEIGHT")):
    assert n.image.colorspace_settings.name=="Non-Color",n.image.name
 mat["DAYTONA_V8_11"]="retains packed BaseColor, tangent Normal, ORM(G) roughness and Height"
 return mat
DARK_WELT=tune_mat("V8_9_Source_Charcoal_Seat_Side_PBR",
 "V8_11_Source_Charcoal_Seat_Edge_PBR",.22,.09,.13,.008,.76,.92)
HEAD_FACE=tune_mat("V8_9_Source_Charcoal_Headrest_PBR",
 "V8_11_Source_Dark_PMT017_Crown_PBR",.38,.12,.24,.012,.73,.90)
HEAD_RETURN=tune_mat("V8_9_Source_Charcoal_Seat_Side_PBR",
 "V8_11_Source_Dark_Headrest_Return_PBR",.31,.11,.17,.008,.78,.94)

def lerp(a,b,t):return a*(1.-t)+b*t
def smoothstep(a,b,t):
 x=max(0.,min(1.,(t-a)/(b-a)))
 return x*x*(3.-2*x)
def bounds_world(obj):
 vv=[obj.matrix_world @ v.co for v in obj.data.vertices]
 return [[round(min(float(v[k]) for v in vv),6),round(max(float(v[k]) for v in vv),6)] for k in range(3)]

def rebuild_curve(obj,coords,mat,bevel):
 assert obj.type=="CURVE" and len(coords)>3
 # Replace only this existing curve datablock. Preserve its name, object,
 # collection link and transform, do not create orphan duplicate geometry.
 old=obj.data
 c=bpy.data.curves.new(old.name+"_V8_11_CONFORMAL","CURVE")
 c.dimensions="3D";c.resolution_u=12;c.bevel_resolution=3;c.bevel_depth=bevel
 sp=c.splines.new("POLY")
 sp.points.add(len(coords)-1)
 for q,xyz in zip(sp.points,coords):q.co=(*xyz,1.)
 c.materials.append(mat)
 obj.data=c
 obj["DAYTONA_V8_11"]="reprojected physically from original high-resolution seat surface"
 if old.users==0:bpy.data.curves.remove(old)

def patch_poly(name,coords,mat):
 ob=bpy.data.objects[name]
 assert ob.type=="CURVE"
 c=ob.data
 assert len(c.splines)==1 and c.splines[0].type=="POLY"
 assert len(c.splines[0].points)==len(coords),(name,len(c.splines[0].points),len(coords))
 for p,xyz in zip(c.splines[0].points,coords):p.co=(*xyz,1.)
 c.materials[0]=mat
 return len(coords)

seatreport={}
for side,cx in (("L",-.353),("R",.353)):
 suf="V8_"+side+"_TAPERED_PADDED_BACKREST"
 ob=bpy.data.objects[suf]
 mesh=ob.data
 nx,ny=72,58
 ring=73*(ny+1)
 assert len(mesh.vertices)==2*ring
 assert mesh.uv_layers.active.name=="V8_9_RESCULPTED_GEODESIC_UV"
 old_counts=(len(mesh.vertices),len(mesh.polygons))
 # Reduce over-high 0.860 m backrest lip toward PMT material017 0.85149 m,
 # modestly taper upper shoulder to meet the original paired headrest crown.
 for j in range(ny+1):
  t=j/ny; amt=smoothstep(.78,1.,t)
  for i in range(73):
   q=mesh.vertices[j*73+i]
   rear=mesh.vertices[ring+j*73+i]
   q.co.z-=.0100*amt
   q.co.x=cx+(q.co.x-cx)*(1.-.032*amt)
   q.co.y-=.003*amt*(1.-abs(2*i/72.-1.))
   rear.co=(q.co.x,q.co.y+.054,q.co.z-.004)
 mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(mesh);bm.free()
 for p in mesh.polygons:p.use_smooth=True
 def pt(j,i):
  return tuple(float(v) for v in mesh.vertices[j*73+i].co)
 # Tangent UV lengths after physical deformation; retain material indexes,
 # source maps, original mesh identity and stitched panel topology.
 us=[[0.]*73 for _ in range(ny+1)]
 vs=[[0.]*73 for _ in range(ny+1)]
 for j in range(ny+1):
  for i in range(73):
   if i:us[j][i]=us[j][i-1]+math.dist(pt(j,i),pt(j,i-1))
   if j:vs[j][i]=vs[j-1][i]+math.dist(pt(j,i),pt(j-1,i))
 assert mesh.uv_layers.get("V8_11_CROWN_GEODESIC_UV") is None
 uv=mesh.uv_layers.new(name="V8_11_CROWN_GEODESIC_UV")
 for p in mesh.polygons:
  for li in p.loop_indices:
   vi=mesh.loops[li].vertex_index%ring
   j,i=divmod(vi,73)
   uv.data[li].uv=(us[j][i]*5.45,vs[j][i]*5.45)
 mesh.uv_layers.active=uv
 assert (len(mesh.vertices),len(mesh.polygons))==old_counts
 assert .846<=max(v.co.z for v in mesh.vertices[:ring])<=.8512

 # 4 old v8.3 off-surface bright bezier piping objects become actual dark
 # charcoal source-PBR paths following mesh vertex positions.
 for sign,edge,i in ((-1,"-1",5),(1,"+1",67)):
  # In the preexisting left/right naming, +1 points toward greater X;
  # on the R seat outer +/- order is reversed but use x position explicitly.
  desired_index=i if side=="L" else 72-i
  if side=="L":suf_edge="+1" if desired_index==67 else "-1"
  else:suf_edge="+1" if desired_index==67 else "-1"
  # Existing names use +/- relative to seat-local x; based on actual
  # preexisting coordinates both L +1 and R -1 are the inner edges.
  path=bpy.data.objects["V8_3_"+side+"_BACK_OUTER_PIPING_"+suf_edge]
  pts=[(x,y-.0013,z) for x,y,z in (pt(j,desired_index) for j in range(3,ny-2))]
  rebuild_curve(path,pts,DARK_WELT,.00105)

 # Reposition existing backrest perimeter NURBS curves using exact seat rows.
 for frac,col in ((.04,3),(.96,69)):
  name="V8_"+side+"_BACKREST_PERIMETER_"+format(frac,".2f")
  per=bpy.data.objects[name]
  coords=[]
  for t in range(65):
   jf=ny*t/64.
   j0=min(ny,int(jf));j1=min(ny,j0+1)
   p0,p1=pt(j0,col),pt(j1,col)
   xyz=[lerp(p0[k],p1[k],jf-j0) for k in range(3)]
   coords.append((xyz[0],xyz[1]-.0010,xyz[2]))
  rebuild_curve(per,coords,DARK_WELT,.00095)
 # Update v8.5/6/7 inherited backrest curves so no floating strips survive.
 for edge,i in (("LEFT",3),("RIGHT",69)):
  patch_poly("V8_5_"+side+"_BACKREST_"+edge+"_WELT",
   [(x,y-.0013,z) for x,y,z in (pt(j,i) for j in range(1,ny))],DARK_WELT)
 for frac in (.23,.48,.72):
  j=round(frac*ny)
  patch_poly("V8_5_"+side+"_BACKREST_STITCH_"+format(frac,".2f"),
   [(x,y-.0011,z) for x,y,z in (pt(j,i) for i in range(11,62))],DARK_WELT)
 for edge,i in (("LEFT",14),("RIGHT",58)):
  patch_poly("V8_6_"+side+"_BACKREST_INSET_"+edge+"_BOLSTER_SEAM",
   [(x,y-.0013,z) for x,y,z in (pt(j,i) for j in range(5,ny-4))],DARK_WELT)
 for frac in (.19,.38,.57,.76):
  j=round(frac*ny)
  patch_poly("V8_7_"+side+"_PLEATED_BACKREST_STITCH_"+format(frac,".2f"),
   [(x,y-.0011,z) for x,y,z in (pt(j,i) for i in range(13,60))],DARK_WELT)
 ob["DAYTONA_V8_11"]="source-bounded upper backrest, reprojected piping, preserved double-sided upholstery"
 seatreport[side]={"backrest":suf,"vertices":len(mesh.vertices),"polygons":len(mesh.polygons),
  "uv":uv.name,"bounds":bounds_world(ob),"surface_piping_dark":True}

# Keep the same two original v8.9 headrest object identities; replace mesh
# datablocks in place with richer 11-height x 22-perimeter sculpted crown.
# 0.8508m cap fits authentic PMT017 Zmax 0.85149m. Paired extreme X stays
# within original upper group017 (-.54831,-.13604) and mirror.
rings=[
 (.7060,.121,-.666,-.626),
 (.7290,.150,-.700,-.645),
 (.7445,.173,-.717,-.653),
 (.7600,.190,-.724,-.651),
 (.7760,.199,-.726,-.651),
 (.7950,.206,-.727,-.650),
 (.8130,.204,-.725,-.652),
 (.8280,.194,-.721,-.655),
 (.8395,.180,-.713,-.659),
 (.8470,.159,-.703,-.666),
 (.8508,.122,-.693,-.680)]
N=22
Q=(-1.,-.94,-.8,-.6,-.3,0.,.3,.6,.8,.94,1.)
assert len(Q)==11 and len(rings)==11
headreport={}
for side,cx in (("L",-.342),("R",.342)):
 name="V8_9_"+side+"_INTEGRATED_PADDED_HEADREST"
 ob=bpy.data.objects[name]
 assert ob.type=="MESH" and len(ob.data.vertices)==28
 old=ob.data
 vertices=[]
 for j,(z,w,yf,yb) in enumerate(rings):
  for q in Q:
   y=yf+.010*abs(q)**6-.0012*(1-q*q)*math.sin(math.pi*j/(len(rings)-1))
   vertices.append((cx+w*q,y,z))
  for q in reversed(Q):
   y=yb-.006*abs(q)**4+.0010*(1-q*q)
   vertices.append((cx+w*q,y,z))
 assert len(vertices)==N*len(rings)
 faces=[]
 for j in range(len(rings)-1):
  for k in range(N):
   a=j*N+k;b=j*N+(k+1)%N
   faces.append((a,b,b+N,a+N))
 faces.append(tuple(reversed(range(N))))
 faces.append(tuple((len(rings)-1)*N+k for k in range(N)))
 m=bpy.data.meshes.new("V8_11_"+side+"_PMT017_LOFT_11x22")
 m.from_pydata(vertices,[],faces)
 m.update(calc_edges=True)
 bm=bmesh.new();bm.from_mesh(m)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 bm.to_mesh(m);bm.free()
 for f in m.polygons:f.use_smooth=True
 m.materials.append(HEAD_FACE);m.materials.append(HEAD_RETURN)
 for f in m.polygons:
  if f.index<len(faces)-2 and (f.index%N)>=10:f.material_index=1
 arc=[]
 for j in range(len(rings)):
  path=[m.vertices[j*N+k].co for k in range(N)]
  ds=[0.]
  for k in range(1,N):ds.append(ds[-1]+(path[k]-path[k-1]).length)
  close=ds[-1]+(path[-1]-path[0]).length
  arc.append((ds,close))
 vert_len=[[0.]*N for _ in rings]
 for j in range(1,len(rings)):
  for k in range(N):
   vert_len[j][k]=vert_len[j-1][k]+(m.vertices[j*N+k].co-m.vertices[(j-1)*N+k].co).length
 uv=m.uv_layers.new(name="V8_11_HEADREST_SURFACE_GEODESIC_UV")
 for poly in m.polygons:
  if poly.index>=len(faces)-2:
   for li in poly.loop_indices:
    v=m.vertices[m.loops[li].vertex_index].co
    uv.data[li].uv=(v.x*5.45,v.y*5.45)
  else:
   idxs=[m.loops[li].vertex_index%N for li in poly.loop_indices]
   wraps=(N-1 in idxs and 0 in idxs)
   for li in poly.loop_indices:
    index=m.loops[li].vertex_index
    j,k=divmod(index,N)
    u=arc[j][1] if wraps and k==0 else arc[j][0][k]
    uv.data[li].uv=(u*5.45,vert_len[j][k]*5.45)
 m.uv_layers.active=uv
 ob.data=m
 if old.users==0:bpy.data.meshes.remove(old)
 for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 be=ob.modifiers.new("v8.11 source rounded crown lip","BEVEL")
 be.width=.0033;be.segments=3
 be.limit_method="ANGLE";be.angle_limit=math.radians(42)
 weighted=ob.modifiers.new("v8.11 source topology weighted normals","WEIGHTED_NORMAL")
 weighted.keep_sharp=True

 # Old v8.9 seams now project directly on the revised new front crown.
 for edge,q in (("LEFT",-.94),("RIGHT",.94)):
  pts=[]
  for j in (2,4,5,7,8):
   z,w,yf,yb=rings[j]
   yy=yf+.010*abs(q)**6-.0012*(1-q*q)*math.sin(math.pi*j/10)
   pts.append((cx+w*q,yy-.0009,z))
  patch_poly("V8_9_"+side+"_HEADREST_"+edge+"_SEAM",pts,DARK_WELT)
 j=5;z,w,yf,yb=rings[j]
 coords=[]
 for k in range(33):
  q=-.78+1.56*k/32.
  yy=yf+.010*abs(q)**6-.0012*(1-q*q)*math.sin(math.pi*j/10)
  coords.append((cx+w*q,yy-.0009,z+.0008*math.sin(math.pi*k/32)))
 patch_poly("V8_9_"+side+"_HEADREST_FRONT_HORIZ_WELT",coords,DARK_WELT)

 xs=[v.co.x for v in m.vertices]
 ys=[v.co.y for v in m.vertices]
 zs=[v.co.z for v in m.vertices]
 assert len(m.vertices)==242 and len(m.polygons)==222
 assert abs(max(zs)-.8508)<1e-5 and min(ys)>=-.72863-.00005
 assert max(abs(x) for x in xs)<.55
 assert all(math.isfinite(float(x)) for v in m.vertices for x in v.co)
 assert all(math.isfinite(float(x)) for v in uv.data for x in v.uv)
 ob["DAYTONA_V8_11"]="original existing PMT017 headrest object re-lofted, no duplicate"
 headreport[side]={"existing_object":name,"vertices":len(m.vertices),
 "polygons":len(m.polygons),"uv":uv.name,"bounds":bounds_world(ob)}

# Original control source, seat cushions, door cards, rim mesh and console preserved.
for side in ("L","R"):
 cu=bpy.data.objects["V8_"+side+"_CLASSIC_PADDED_CUSHION"]
 assert cu.data.uv_layers.active.name=="V8_9_RESCULPTED_GEODESIC_UV"
 assert cu.data.materials[0].name=="V8_9_Source_Charcoal_Seat_PBR"
 assert bpy.data.objects["V5_"+side+"_LEATHER_SCULPTED_DOOR"].data.uv_layers.active.name=="V8_10_DOOR_GEODESIC_UV"
assert bpy.data.objects["V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"].data.materials[0].name=="V8_10_Source_Ebonized_Steering_Rim_PBR"
sc.render.engine="CYCLES"
sc.cycles.samples=10;sc.cycles.use_denoising=True
sc.render.resolution_x=960;sc.render.resolution_y=640
sc.render.resolution_percentage=100
sc.view_settings.exposure=-.52
for image in bpy.data.images:
 if image.source=="FILE" and not image.packed_file:image.pack()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
assert DEST.exists()
report={"status":"DAYTONA_V8_11_REAL_BLENDER_SAVED",
 "source_file":SOURCE.name,"source_sha256":EXPECTED,
 "new_file":DEST.name,"new_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "bytes":DEST.stat().st_size,"blender":bpy.app.version_string,
 "source_PMT017_aggregate":PMT017,"backrests":seatreport,"existing_headrests":headreport,
 "native_control_geometry_preserved":True,"prior_door_rim_console_preserved":True,
 "dark_surface_conformal_piping":True,
 "source_packed_basecolor_tangent_normal_orm_height":True,
 "camera":sc.camera.name,"render_validation":"UNTESTED",
 "matched_960x640_10spp":"UNTESTED","game_runtime":"UNTESTED",
 "OVC_created":False,"Quest3_tested":False,"original_game_files_modified":False}
(W/"DAYTONA_V8_11_BUILD_MANIFEST.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_11_MODEL_SAVED",json.dumps(report),flush=True)
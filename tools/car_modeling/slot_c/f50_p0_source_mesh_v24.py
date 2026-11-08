#!/usr/bin/env python3
"""F50 slot C v24: original OutRun 2006 PMT-derived cockpit mesh in-place only.

Never exports PMT, OVC, GLB, textures or game files. The private source .blend and
photos are external, SHA-pinned, read-only inputs. Other slots remain untouched.
Blender 4.5.15 only. Use: blender -b INPUT.blend --python THIS.py -- --mode build ...
And, in a separate Blender process: blender -b OUTPUT.blend --python THIS.py -- --mode audit ...
"""
import argparse, bmesh, bpy, hashlib, json, math, struct, sys
from pathlib import Path
from mathutils import kdtree

PMT="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
V23="92ef962e65686faef64877b3540b4311f103220fad659ab483bbc5c3ba816f0b"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"c9ad46902db240eeefa667fe8f1beb5cb8377e862669ee445f30cceb327e1e64"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"a4e6388ebbed7da582c1f23f3ee860bc27d6b9ba7a2aa84d3563e192137ccd36"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"490dfb71323e1a72d53fa2af6ac75f7912eb8b1f1e06a2c314d8530f205cb896"),
}
VIEWS={
 "GAUGE":("QA_F50_GAUGE_DETAIL_NON_GAME",["PMT_F50_object00_group01_material028_a0"]),
 "STEERING":("QA_F50_STEERING_LOCAL_NON_GAME",[
   "PMT_F50_object21_group00_material000_a0",
   "PMT_F50_object21_group01_material001_a0",
   "PMT_F50_object21_group01_material002_a0"]),
}
def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()
def meshhash(m):
 h=hashlib.sha256()
 for v in m.vertices:h.update(struct.pack("<3f",*v.co))
 for f in m.polygons:
  h.update(struct.pack("<I",len(f.vertices)))
  for i in f.vertices:h.update(struct.pack("<I",i))
 return h.hexdigest()
def snap():
 result={}
 for o in bpy.data.objects:
  if o.type!="MESH":continue
  m=o.data
  bm=bmesh.new();bm.from_mesh(m)
  nonman=sum(not e.is_manifold for e in bm.edges)
  bm.free()
  result[o.name]=dict(original_id=o.get("outrun_original_mesh_object_id"),
   pmt=o.get("outrun_original_game_resource_sha256"),
   sha256=meshhash(m),vertices=len(m.vertices),faces=len(m.polygons),
   nonmanifold=nonman,uv_layers=len(m.uv_layers),materials=len(m.materials),
   matrix=[round(float(v),9) for row in o.matrix_world for v in row])
 return result
def cameras():
 return {o.name:([round(float(v),9) for row in o.matrix_world for v in row],
                   o.data.type,round(float(o.data.lens),9))
         for o in bpy.data.objects if o.type=="CAMERA"}
def smooth(t):
 t=max(0.,min(1.,t));return t*t*(3.-2.*t)
def window(t,lo,hi,f):
 return smooth((t-lo)/f)*smooth((hi-t)/f)
def cowl_photo_fairing(o):
 """Refine EXISTING F50 source binnacle crown using normal-gated local quadratic
 fits: tame wedge-shaped ridges without reshaping the gauge opening or adding parts."""
 import numpy as np
 m=o.data;orig=[v.co.copy() for v in m.vertices]
 coords=[v.co.copy() for v in m.vertices]; norms=[v.normal.copy() for v in m.vertices]
 xs=[v.x for v in coords]; ys=[v.y for v in coords]
 x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);zmax=max(v.z for v in coords)
 kd=kdtree.KDTree(len(coords))
 for i,v in enumerate(coords):kd.insert(v,i)
 kd.balance()
 change={}
 for i,p in enumerate(coords):
  n=norms[i]
  if abs(n.z)<.55:continue
  ux=(p.x-x0)/(x1-x0);uy=(p.y-y0)/(y1-y0)
  mask=window(ux,.075,.925,.14)*window(uy,.11,.89,.16)
  if mask<.045:continue
  X=[];Z=[];W=[]
  for q,j,dist in kd.find_range(p,.064):
   dv=q-p
   if abs(dv.x)>.047 or abs(dv.y)>.048 or abs(dv.z)>.022:continue
   dot=n.dot(norms[j])
   if dot<.76 or n.z*norms[j].z<=0:continue
   xx=dv.x/.029;yy=dv.y/.028
   w=math.exp(-.5*(xx*xx+yy*yy))*dot**4
   if w<.006:continue
   X.append([1.,xx,yy,xx*xx,xx*yy,yy*yy])
   Z.append(float(q.z));W.append(math.sqrt(w))
  if len(X)<18:continue
  weight=np.asarray(W)
  A=np.asarray(X,dtype=np.float64)*weight[:,None]
  try:fit,_,rank,_=np.linalg.lstsq(A,np.asarray(Z)*weight,rcond=None)
  except Exception:continue
  if rank<6:continue
  # Photo: low, smooth instrument eyebrow; protect original lower sill edges.
  center_band=math.exp(-((ux-.50)/.265)**4)
  crest=smooth((float(p.z)-(zmax-.014))/.011)
  dz=(float(fit[0])-float(p.z))*.82*mask-.00078*center_band*crest*mask
  dz=max(-.00170,min(.00170,dz))
  if abs(dz)>1e-7:change[i]=dz
 assert len(change)>500,("F50 ORIGINAL instrument cowl missing",len(change))
 for i,dz in change.items():m.vertices[i].co.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v24 original dashboard binnacle continuous crest/sill fairing; source faces, UV and materials intact"
 return orig

def steering_original_grip(o):
 """Photographed F50 factory three-spoke rim: source-only circular contour relief.
 Neighbor fairing compares matching original outward-facing normals and depth,
 and does not bridge factory rim openings or touch the steering pivot."""
 m=o.data;orig=[v.co.copy() for v in m.vertices]
 pts=[v.co.copy() for v in m.vertices];normal=[v.normal.copy() for v in m.vertices]
 kd=kdtree.KDTree(len(pts))
 for i,c in enumerate(pts):kd.insert(c,i)
 kd.balance()
 changes={}
 for i,p in enumerate(pts):
  x,y,z=p;r=math.hypot(x,y)
  if r<.117 or r>.179:continue
  mask=smooth((r-.117)/.016)*smooth((.179-r)/.014)
  if mask<.015:continue
  theta=math.atan2(y,x)
  # Rim circumference gets local curve fairing, with symmetric side grip relief.
  radw=0.;radial=0.;height=0.
  for q,j,dist in kd.find_range(p,.021):
   if j==i or dist<1e-9:continue
   nj=normal[i].dot(normal[j])
   if nj<.86 or abs(q.z-z)>.009:continue
   rq=math.hypot(q.x,q.y)
   if abs(rq-r)>.013:continue
   da=abs(math.atan2(math.sin(math.atan2(q.y,q.x)-theta),
                         math.cos(math.atan2(q.y,q.x)-theta)))
   if da>.19:continue
   w=math.exp(-.5*(dist/.009)**2)*nj**3
   radw+=w;radial+=w*rq;height+=w*q.z
  if radw<1.5:continue
  side=math.exp(-((abs(theta-math.pi/2)-.68)/.28)**4)
  low=math.exp(-((theta+math.pi/2)/.38)**4)
  fair=max(-.00125,min(.00125,(radial/radw-r)*.58*mask))
  dr=fair+mask*(.00032*side+.00025*low)
  dz=max(-.00105,min(.00105,(height/radw-z)*.43*mask))
  dz+=mask*(.00022*side+.00012*low)
  if abs(dr)>1e-7 or abs(dz)>1e-7:
   changes[i]=(dr,dz)
 assert len(changes)>1200,("F50 source 3-spoke rim not found",len(changes))
 for i,(dr,dz) in changes.items():
  c=m.vertices[i].co;r=math.hypot(c.x,c.y)
  c.x+=dr*c.x/r;c.y+=dr*c.y/r;c.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v24 original three-spoke rim faceting fairing, upper grips and lower rim; unchanged factory topology and pivots"
 return orig

def hub_original_plate_fairing(o):
 """Keep original six-fastener ring and badge untouched; locally flatten ripples
 on the original native hub face to match F50 photographed plate."""
 m=o.data;orig=[v.co.copy() for v in m.vertices]
 pts=[v.co.copy() for v in m.vertices];norm=[v.normal.copy() for v in m.vertices]
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 bolt=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
       for a in (30,90,150,210,270,330)]
 changes={}
 for i,p in enumerate(pts):
  radius=math.hypot(p.x,p.y+.019)
  if radius<.021 or radius>.071 or norm[i].z<.58:continue
  away=min(math.hypot(p.x-x,p.y-y) for x,y in bolt)
  mask=smooth((radius-.021)/.014)*smooth((.071-radius)/.013)
  mask*=smooth((away-.008)/.011)
  if mask<.035:continue
  weight=0.;total=0.
  for q,j,dist in kd.find_range(p,.017):
   if j==i or abs(q.z-p.z)>.007:continue
   n=norm[i].dot(norm[j])
   if n<.79:continue
   dx=q.x-p.x;dy=q.y-p.y
   if dx*dx+dy*dy>.014**2:continue
   w=math.exp(-(dx*dx+dy*dy)/(2*.0068**2))*n**4
   weight+=w;total+=w*q.z
  if weight<.040:continue
  dz=max(-.00135,min(.00135,(total/weight-p.z)*.84*mask))
  if abs(dz)>1e-7:changes[i]=dz
 assert len(changes)>75,("missing F50 original six-bolt hub source",len(changes))
 for i,dz in changes.items():m.vertices[i].co.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v24 original 6-bolt hub plate fairing; badge, screw islands, geometry/UV topology retained"
 return orig

def render(path,cam,visible):
 sc=bpy.context.scene
 old=(sc.camera,sc.render.engine,sc.render.filepath,sc.render.resolution_x,
      sc.render.resolution_y,sc.render.resolution_percentage,sc.render.image_settings.file_format)
 hidden={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 try:
  sc.camera=bpy.data.objects[cam];sc.render.engine="BLENDER_WORKBENCH"
  sc.render.resolution_x=800;sc.render.resolution_y=560;sc.render.resolution_percentage=100
  sc.render.image_settings.file_format="PNG"
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in visible
  sc.render.filepath=str(path)
  bpy.ops.render.render(write_still=True)
  assert path.is_file() and path.stat().st_size>10000,("render absent",path)
 finally:
  (sc.camera,sc.render.engine,sc.render.filepath,sc.render.resolution_x,
   sc.render.resolution_y,sc.render.resolution_percentage,sc.render.image_settings.file_format)=old
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=hidden[o.name]
def source_guard(a):
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 for path,expected in ((a.native,PMT),(a.original_import,IMPORT),(a.before,V23)):
  assert digest(path)==expected,("BLOCKED_INPUT SOURCE SHA",str(path),digest(path),expected)
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
def report_guard(before,after):
 assert len(before)==len(after)==42
 assert set(before)==set(after)
 for name,b in before.items():
  c=after[name]
  assert b["original_id"] and b["pmt"]==c["pmt"]==PMT
  for k in ("original_id","pmt","vertices","faces","nonmanifold",
            "uv_layers","materials","matrix"):
   assert b[k]==c[k],(name,k)
  if name in TARGETS:
   assert b["sha256"]!=c["sha256"],name
  else:
   assert b==c,("SLOT_C_ONLY guard",name)
 assert sum(before[n]["sha256"]==after[n]["sha256"] for n in before)==39
 assert after["PMT_F50_object21_group01_material002_a0"]["nonmanifold"]==624
def build(a):
 source_guard(a)
 assert Path(bpy.data.filepath).resolve()==a.before.resolve()
 assert bpy.context.scene.get("geometry_edit_count")==69
 assert not a.after.exists() and not a.report.exists(),("immutable version would overwrite",str(a.after))
 b=snap();cam=cameras()
 for name,(oid,nv,nf,h) in TARGETS.items():
  s=b[name]
  assert (s["original_id"],s["vertices"],s["faces"],s["sha256"])==(oid,nv,nf,h),(name,s)
  assert s["pmt"]==PMT
 renders={}
 for label,(camera,visible) in VIEWS.items():
  path=Path(str(a.render_root)+"_BEFORE_"+label+".png")
  render(path,camera,visible);renders["before_"+label]={"path":str(path),"sha256":digest(path)}
 funcs=[cowl_photo_fairing,steering_original_grip,hub_original_plate_fairing]
 stats={}
 for name,func in zip(TARGETS,funcs):
  o=bpy.data.objects[name];orig=func(o)
  dd=[(orig[i]-v.co).length for i,v in enumerate(o.data.vertices)]
  count=sum(d>1e-6 for d in dd)
  maximum=max(dd)
  assert count>85 and maximum>.00005,(name,count,maximum)
  stats[name]={"moved_vertices":count,"max_mm":round(maximum*1000,6)}
 c=snap();report_guard(b,c)
 assert cameras()==cam
 bpy.context.scene["geometry_edit_count"]=72
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V24_NATIVE_PHOTO_LOW_COWL_SMOOTH_RIM_SIX_BOLT_HUB"
 bpy.context.scene["slot_c_input_blend_sha256"]=V23
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 for label,(camera,visible) in VIEWS.items():
  path=Path(str(a.render_root)+"_AFTER_"+label+".png")
  render(path,camera,visible);renders["after_"+label]={"path":str(path),"sha256":digest(path)}
 source_guard(a)
 j={"status":"LOCAL_F50_V24_SAVED_INDEPENDENT_REOPEN_PENDING","blender":bpy.app.version_string,
    "native_pmt_sha256":PMT,"original_import_sha256":IMPORT,"input_v23_sha256":V23,
    "output_private_blend":str(a.after),"output_sha256":digest(a.after),
    "original_mesh_count":42,"changed_only_original_meshes":{
     name:{"before":b[name],"after":c[name],**stats[name]} for name in TARGETS},
    "untouched_original_meshes_SHA_identical":39,"original_wheel_nonmanifold_edges":624,
    "renders":renders,"native_game_driver_eye":"UNVERIFIED",
    "seven_photo_view_QA":"INCOMPLETE",
    "github_hosted_original_private_blend":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
    "game_export":False,"texture_pbr_changes":False,"other_slot_changes":False,
    "vehicle_complete":False,"score_delta":0}
 a.report.write_text(json.dumps(j,indent=2),encoding="utf8")
 print("F50_V24_SOURCE_SAVED",j["output_sha256"],stats)
def audit(a):
 source_guard(a)
 j=json.loads(a.report.read_text(encoding="utf8"))
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert digest(a.after)==j["output_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==69
 c=snap();cam=cameras()
 assert len(c)==42
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 b=snap();assert len(b)==42 and cam==cameras()
 report_guard(b,c)
 for n,t in j["changed_only_original_meshes"].items():
  assert b[n]==t["before"] and c[n]==t["after"],n
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert snap()==c and cameras()==cam
 assert not a.audit.exists()
 render(a.render_root.with_name(a.render_root.name+"_INDEPENDENT_STEERING.png"),
        *VIEWS["STEERING"])
 path=a.render_root.with_name(a.render_root.name+"_INDEPENDENT_STEERING.png")
 x={"status":"PASS_F50_V24_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER",
    "original_pmt_sha256":digest(a.native),"original_import_sha256":digest(a.original_import),
    "input_v23_sha256":digest(a.before),"candidate_sha256":digest(a.after),
    "original_mesh_count":42,"modified_original_mesh_count":3,"untouched_source_mesh_count":39,
    "cameras_original_ids_transforms_uv_materials_unchanged":True,
    "original_wheel_nonmanifold_edges":624,"independent_steering_render_sha256":digest(path),
    "seven_photo_view_QA":"INCOMPLETE",
    "native_game_driver_eye":"UNVERIFIED","hosted_private_original_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
    "vehicle_complete":False,"score_delta":0}
 a.audit.write_text(json.dumps(x,indent=2),encoding="utf8")
 print(x["status"],x["candidate_sha256"],x["independent_steering_render_sha256"])
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--mode",required=True,choices=["build","audit"])
 for name in ("native","original-import","before","after","report","audit","render-root"):
  p.add_argument("--"+name,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if a.mode=="build":build(a)
 else:audit(a)
if __name__=="__main__":main()

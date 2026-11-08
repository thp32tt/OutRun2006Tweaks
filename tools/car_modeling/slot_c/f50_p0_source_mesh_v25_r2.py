#!/usr/bin/env python3
"""F50 slot C v25_r2: original OutRun 2006 PMT-derived cockpit mesh in-place only.

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
V24="eda7f5a5ac489b93227b58456e51d02eec993672904f4467a79cb5b0fe2df086"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"e07aaae7f2b8552328ea2384071dc1ca8e290b17715272ffccfcbc3a6f1138ea"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"798fad5bea06c7922992d8e37e5ea70a3c971f17a13de034eee5c431528672e3"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"385dbcbfb715d4caddbdaec44ab5c4e7140e9b49a3e7d00ed987c65c46944d5a"),
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
 """In-place original F50 instrument eyebrow: fair upper visor sheet without
 lifting the gauge-opening rim or building a new shell. Source bmesh only."""
 import numpy as np
 m=o.data
 orig=[v.co.copy() for v in m.vertices]
 coords=[v.co.copy() for v in m.vertices]
 norms=[v.normal.copy() for v in m.vertices]
 xmin=min(p.x for p in coords);xmax=max(p.x for p in coords)
 ymin=min(p.y for p in coords);ymax=max(p.y for p in coords)
 zmax=max(p.z for p in coords)
 kd=kdtree.KDTree(len(coords))
 for i,p in enumerate(coords):kd.insert(p,i)
 kd.balance()
 changes={}
 for i,p in enumerate(coords):
  n=norms[i]
  if abs(n.z)<.59:continue
  ux=(p.x-xmin)/(xmax-xmin);uy=(p.y-ymin)/(ymax-ymin)
  mid=window(ux,.08,.92,.14)*window(uy,.14,.86,.16)
  if mid<.04:continue
  X=[];Z=[];W=[]
  for q,j,dist in kd.find_range(p,.067):
   dv=q-p
   if abs(dv.x)>.05 or abs(dv.y)>.05 or abs(dv.z)>.023:continue
   dot=n.dot(norms[j])
   if dot<.79 or n.z*norms[j].z<=0:continue
   xx=dv.x/.031;yy=dv.y/.028
   w=math.exp(-.5*(xx*xx+yy*yy))*dot**4
   if w<.006:continue
   X.append([1.,xx,yy,xx*xx,xx*yy,yy*yy])
   Z.append(float(q.z));W.append(math.sqrt(w))
  if len(X)<16:continue
  A=np.asarray(X,dtype=np.float64)*np.asarray(W)[:,None]
  try:fit,_,rank,_=np.linalg.lstsq(A,np.asarray(Z)*np.asarray(W),rcond=None)
  except Exception:continue
  if rank<6:continue
  # F50 camera photo: continuous shallow brow, softly curved crown.
  crown=math.exp(-((ux-.50)/.29)**4)
  top=smooth((float(p.z)-(zmax-.015))/.013)
  correction=(float(fit[0])-p.z)*.81*mid-.00045*crown*top*mid
  correction=max(-.00140,min(.00140,correction))
  if abs(correction)>1e-7:changes[i]=correction
 assert len(changes)>600,("original F50 cowl geometry missing",len(changes))
 for i,dz in changes.items():m.vertices[i].co.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v25_r2 original imported instrument cowl upper visor fairing; no extra geometry/texture"
 return orig

def steering_original_grip(o):
 """F50 steering rim P0: original PMT-derived 3-spoke rim and inner return
 roundness fairing; protect spoke roots and original open-edge topology.
 Same source vertex coordinates and array indexing, no added geometry."""
 m=o.data;orig=[v.co.copy() for v in m.vertices]
 coords=[v.co.copy() for v in m.vertices];normal=[v.normal.copy() for v in m.vertices]
 kd=kdtree.KDTree(len(coords))
 for i,p in enumerate(coords):kd.insert(p,i)
 kd.balance()
 changes={}
 for i,p in enumerate(coords):
  r=math.hypot(p.x,p.y)
  if r<.127 or r>.18:continue
  theta=math.atan2(p.y,p.x)
  # Smooth inner rim polygonal transition; gently preserve factory thumb pads.
  ring=smooth((r-.128)/.012)*smooth((.178-r)/.013)
  # The factory three spoke-to-rim unions must not be pulled into a notch.
  near=min(abs(math.atan2(math.sin(theta-a),math.cos(theta-a)))
           for a in (0.0,math.pi,-math.pi/2))
  ring*=smooth((near-.11)/.30)
  if ring<.025:continue
  wsum=0.;rsum=0.;zsum=0.
  for q,j,dist in kd.find_range(p,.024):
   if j==i or dist<1e-9:continue
   dp=normal[i].dot(normal[j])
   if dp<.85 or abs(q.z-p.z)>.008:continue
   rq=math.hypot(q.x,q.y)
   if abs(rq-r)>.012:continue
   da=abs(math.atan2(math.sin(math.atan2(q.y,q.x)-theta),
                         math.cos(math.atan2(q.y,q.x)-theta)))
   if da>.175:continue
   w=math.exp(-.5*(dist/.010)**2)*dp**4
   wsum+=w;rsum+=w*rq;zsum+=w*q.z
  if wsum<1.1:continue
  # Wide factory F50 three-spoke segment relief at 10/2 and 6 o'clock.
  hand=math.exp(-((abs(theta-math.pi/2)-.68)/.33)**4)
  low=math.exp(-((theta+math.pi/2)/.40)**4)
  dr=max(-.00082,min(.00082,(rsum/wsum-r)*.52*ring))
  dr+=ring*(.00019*hand+.00006*low)
  dz=max(-.00063,min(.00063,(zsum/wsum-p.z)*.46*ring))
  dz+=ring*(.00010*hand-.00002*low)
  if abs(dr)>1e-7 or abs(dz)>1e-7:
   changes[i]=(dr,dz)
 assert len(changes)>2400,("F50 original 3-spoke rim insufficient",len(changes))
 for i,(dr,dz) in changes.items():
  v=m.vertices[i].co;r=math.hypot(v.x,v.y)
  v.x+=dr*v.x/r;v.y+=dr*v.y/r;v.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v25_r2 original three-spoke rim contour and grip source vertex refit, no mesh or pivot changes"
 return orig

def hub_original_plate_fairing(o):
 """Retain original six-bolt F50 center cap geometry and photo-based hub face.
 No screw island, recessed badge center, or original outer rim topology edits."""
 m=o.data;orig=[v.co.copy() for v in m.vertices]
 pts=[v.co.copy() for v in m.vertices]
 norms=[v.normal.copy() for v in m.vertices]
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
        for a in (30,90,150,210,270,330)]
 changes={}
 for i,p in enumerate(pts):
  radius=math.hypot(p.x,p.y+.019)
  if radius<.022 or radius>.07 or norms[i].z<.60:continue
  away=min(math.hypot(p.x-x,p.y-y) for x,y in bolts)
  mask=smooth((radius-.022)/.012)*smooth((.07-radius)/.013)
  mask*=smooth((away-.008)/.012)
  if mask<.04:continue
  total=0.;weight=0.
  for q,j,dist in kd.find_range(p,.020):
   if j==i or abs(q.z-p.z)>.007:continue
   dot=norms[i].dot(norms[j])
   if dot<.81:continue
   dx=q.x-p.x;dy=q.y-p.y;dist2=dx*dx+dy*dy
   if dist2>.015**2:continue
   w=math.exp(-dist2/(2*.0075**2))*dot**4
   total+=w*q.z;weight+=w
  if weight<.04:continue
  dz=max(-.0011,min(.0011,(total/weight-p.z)*.77*mask))
  if abs(dz)>1e-7:changes[i]=dz
 assert len(changes)>100,("missing original F50 center-cap data",len(changes))
 for i,dz in changes.items():m.vertices[i].co.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v25_r2 original six-bolt hub cup relief smoothing; preserve face IDs, bolt holes, badge"
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
 for path,expected in ((a.native,PMT),(a.original_import,IMPORT),(a.before,V24)):
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
 assert bpy.context.scene.get("geometry_edit_count")==72
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
 bpy.context.scene["geometry_edit_count"]=75
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V25_R2_ORIGINAL_BROW_ROUNDED_RIM_HUB_PLATE"
 bpy.context.scene["slot_c_input_blend_sha256"]=V24
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 for label,(camera,visible) in VIEWS.items():
  path=Path(str(a.render_root)+"_AFTER_"+label+".png")
  render(path,camera,visible);renders["after_"+label]={"path":str(path),"sha256":digest(path)}
 source_guard(a)
 j={"status":"LOCAL_F50_V25_R2_SAVED_INDEPENDENT_REOPEN_PENDING","blender":bpy.app.version_string,
    "native_pmt_sha256":PMT,"original_import_sha256":IMPORT,"input_v24_sha256":V24,
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
 print("F50_V25_R2_SOURCE_SAVED",j["output_sha256"],stats)
def audit(a):
 source_guard(a)
 j=json.loads(a.report.read_text(encoding="utf8"))
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert digest(a.after)==j["output_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==75
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
 x={"status":"PASS_F50_V25_R2_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER",
    "original_pmt_sha256":digest(a.native),"original_import_sha256":digest(a.original_import),
    "input_v24_sha256":digest(a.before),"candidate_sha256":digest(a.after),
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
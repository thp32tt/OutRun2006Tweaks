#!/usr/bin/env python3
"""F50 slot C v26: original OutRun 2006 PMT-derived cockpit mesh in-place only.

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
V25="bfa8becc5d2bbd0258b135fbc8b3478b2725f8e5f5b8da9c95397cf5908e6da4"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"1bf41eb343e0d2e656230418d91a82b95bc54b32c9b7d8899cd4713a67151be5"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"4643c224d88913fe1af2e2d5042d13f17824768249763169f1b6f57eb8c20fc0"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"32f68dcf0721c0785d3c8ec1398a05579a94ad2181de5d65fc524ea1a379e055"),
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
 """Refine the *existing* native instrument hood with the F50 photo's round
 upper brow and a continuous lower falloff; no detached hood or new topology."""
 import numpy as np
 m=o.data; orig=[v.co.copy() for v in m.vertices]
 coords=[v.co.copy() for v in m.vertices]; normals=[v.normal.copy() for v in m.vertices]
 xmin=min(p.x for p in coords);xmax=max(p.x for p in coords)
 ymin=min(p.y for p in coords);ymax=max(p.y for p in coords)
 zmax=max(p.z for p in coords)
 kd=kdtree.KDTree(len(coords))
 for i,p in enumerate(coords):kd.insert(p,i)
 kd.balance()
 changes={}
 for i,p in enumerate(coords):
  n=normals[i]
  if abs(n.z)<.57:continue
  ux=(p.x-xmin)/(xmax-xmin);uy=(p.y-ymin)/(ymax-ymin)
  mask=window(ux,.06,.94,.13)*window(uy,.11,.89,.15)
  if mask<.045:continue
  X=[];Z=[];W=[]
  for q,j,dist in kd.find_range(p,.063):
   dv=q-p
   if abs(dv.x)>.048 or abs(dv.y)>.048 or abs(dv.z)>.021:continue
   dot=n.dot(normals[j])
   if dot<.80 or n.z*normals[j].z<=0:continue
   xx=dv.x/.030;yy=dv.y/.028
   w=math.exp(-.5*(xx*xx+yy*yy))*dot**4
   if w<.006:continue
   X.append([1.,xx,yy,xx*xx,xx*yy,yy*yy])
   Z.append(float(q.z));W.append(math.sqrt(w))
  if len(X)<16:continue
  A=np.asarray(X,dtype=np.float64)*np.asarray(W)[:,None]
  try:fit,_,rank,_=np.linalg.lstsq(A,np.asarray(Z)*np.asarray(W),rcond=None)
  except Exception:continue
  if rank<6:continue
  # Protected boundary vertices, arch spread from actual old PMT hood topology.
  crown=math.exp(-((ux-.5)/.31)**4)
  upper=smooth((float(p.z)-(zmax-.023))/.016)
  # The driver's instruments sit below the curved, continuous photo hood.
  photo_arch=.0020*crown*upper*mask
  fair=(float(fit[0])-p.z)*.92*mask
  dz=max(-.0023,min(.0028,fair+photo_arch))
  if abs(dz)>1e-7:changes[i]=dz
 assert len(changes)>550,("F50 native hood absent",len(changes))
 for i,dz in changes.items():m.vertices[i].co.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v26 genuine original PMT gauge-hood arch and normal-gated source surface fairing"
 return orig


def steering_original_grip(o):
 """Retain native F50 3-spoke loop and vertex identities; smooth round grip
 and hand/thumb swell without changing the original spoke/hub pivot or seams."""
 m=o.data;orig=[v.co.copy() for v in m.vertices]
 pts=[v.co.copy() for v in m.vertices];normals=[v.normal.copy() for v in m.vertices]
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 changes={}
 for i,p in enumerate(pts):
  r=math.hypot(p.x,p.y)
  if not .125<r<.180:continue
  ang=math.atan2(p.y,p.x)
  ring=smooth((r-.127)/.014)*smooth((.179-r)/.013)
  near=min(abs(math.atan2(math.sin(ang-a),math.cos(ang-a)))
           for a in (0.,math.pi,-math.pi/2))
  ring*=smooth((near-.085)/.30)
  if ring<.025:continue
  rs=zs=ws=0.
  for q,j,dist in kd.find_range(p,.027):
   if i==j or dist<1e-9:continue
   ndot=normals[i].dot(normals[j])
   if ndot<.84 or abs(q.z-p.z)>.010:continue
   rq=math.hypot(q.x,q.y)
   if abs(rq-r)>.014:continue
   da=abs(math.atan2(math.sin(math.atan2(q.y,q.x)-ang),
                         math.cos(math.atan2(q.y,q.x)-ang)))
   if da>.17:continue
   w=math.exp(-.5*(dist/.012)**2)*ndot**4
   rs+=w*rq;zs+=w*q.z;ws+=w
  if ws<.9:continue
  # Photo: broader rim at quarter hand grips, continuous at lower spoke.
  at_10_2=math.exp(-((abs(ang-math.pi/2)-.69)/.31)**4)
  at_bottom=math.exp(-((ang+math.pi/2)/.39)**4)
  dr=max(-.0015,min(.0015,(rs/ws-r)*.81*ring))
  dr+=ring*(.00085*at_10_2+.00020*at_bottom)
  dz=max(-.0011,min(.0011,(zs/ws-p.z)*.65*ring))
  dz+=ring*(.00045*at_10_2-.00008*at_bottom)
  if abs(dr)>1e-7 or abs(dz)>1e-7:changes[i]=(dr,dz)
 assert len(changes)>2000,("native F50 rim missing",len(changes))
 for i,(dr,dz) in changes.items():
  p=m.vertices[i].co;r=math.hypot(p.x,p.y)
  p.x+=dr*p.x/r;p.y+=dr*p.y/r;p.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v26 continuous source original 3-spoke rim local round-grip and spoke-root-exclusion"
 return orig


def hub_original_plate_fairing(o):
 """Fair dented 3-spoke centre-face native vertices while protecting six
 original screw islands, central Ferrari badge area and outer seams."""
 m=o.data;orig=[v.co.copy() for v in m.vertices]
 pts=[v.co.copy() for v in m.vertices];normals=[v.normal.copy() for v in m.vertices]
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
        for a in (30,90,150,210,270,330)]
 changes={}
 for i,p in enumerate(pts):
  r=math.hypot(p.x,p.y+.019)
  if r<.020 or r>.071 or normals[i].z<.62:continue
  dbolt=min(math.hypot(p.x-x,p.y-y) for x,y in bolts)
  mask=smooth((r-.020)/.013)*smooth((.071-r)/.013)
  mask*=smooth((dbolt-.009)/.013)
  if mask<.045:continue
  total=weight=0.
  for q,j,dist in kd.find_range(p,.024):
   if i==j or abs(q.z-p.z)>.009:continue
   dot=normals[i].dot(normals[j])
   if dot<.84:continue
   dxy=(q.x-p.x)**2+(q.y-p.y)**2
   if dxy>.018**2:continue
   w=math.exp(-dxy/(2*.009**2))*dot**4
   total+=w*q.z;weight+=w
  if weight<.05:continue
  dz=max(-.0019,min(.0019,(total/weight-p.z)*.90*mask))
  if abs(dz)>1e-7:changes[i]=dz
 assert len(changes)>100,("native F50 hub face missing",len(changes))
 for i,dz in changes.items():m.vertices[i].co.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v26 native six-bolt hub face smooth fairing, photo-consistent, badges preserved"
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
 for path,expected in ((a.native,PMT),(a.original_import,IMPORT),(a.before,V25)):
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
 assert bpy.context.scene.get("geometry_edit_count")==75
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
 bpy.context.scene["geometry_edit_count"]=78
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V26_ORIGINAL_DASH_ARCH_ROUNDED_GRIP_HUB_FACE"
 bpy.context.scene["slot_c_input_blend_sha256"]=V25
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 for label,(camera,visible) in VIEWS.items():
  path=Path(str(a.render_root)+"_AFTER_"+label+".png")
  render(path,camera,visible);renders["after_"+label]={"path":str(path),"sha256":digest(path)}
 source_guard(a)
 j={"status":"LOCAL_F50_V26_SAVED_INDEPENDENT_REOPEN_PENDING","blender":bpy.app.version_string,
    "native_pmt_sha256":PMT,"original_import_sha256":IMPORT,"input_v25_r2_sha256":V25,
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
 print("F50_V26_SOURCE_SAVED",j["output_sha256"],stats)
def audit(a):
 source_guard(a)
 j=json.loads(a.report.read_text(encoding="utf8"))
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert digest(a.after)==j["output_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==78
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
 x={"status":"PASS_F50_V26_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER",
    "original_pmt_sha256":digest(a.native),"original_import_sha256":digest(a.original_import),
    "input_v25_r2_sha256":digest(a.before),"candidate_sha256":digest(a.after),
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
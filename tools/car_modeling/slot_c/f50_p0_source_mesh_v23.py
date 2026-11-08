#!/usr/bin/env python3
"""F50 slot C v23: original OutRun 2006 PMT-derived cockpit mesh in-place only.

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
V22="cc4090261747c8c013011e68d1781f5aa6f75bca478ec5c2e9fb6fd3f1c5fcc7"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"eafae91ec88b7959dfe87fba29937817a3cb60c035c37fc7dfb98ad833793864"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"47fdc4ec9819f2ff4fb5635f7e9ba396be653830786887838909c439cb5f81c7"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"0c8d859b1076c1b91ef5f08ddd6b3be9b1516918ee91022dff02bef05ec294bb"),
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
 """Only existing upper cluster cowl verts; bounded normal-consistent quadratic
  regression keeps the photographed F50 broad visor silhouette, not fan triangles.
 """
 import numpy as np
 m=o.data
 original=[v.co.copy() for v in m.vertices]
 normals=[v.normal.copy() for v in m.vertices]
 coords=[v.co.copy() for v in m.vertices]
 x0=min(v.x for v in coords);x1=max(v.x for v in coords)
 y0=min(v.y for v in coords);y1=max(v.y for v in coords)
 zmax=max(v.z for v in coords)
 kd=kdtree.KDTree(len(coords))
 for i,c in enumerate(coords):kd.insert(c,i)
 kd.balance()
 changes={}
 for i,c in enumerate(coords):
  n=normals[i]
  if abs(n.z)<.54:continue
  mask=window((c.x-x0)/(x1-x0),.08,.92,.12)
  mask*=window((c.y-y0)/(y1-y0),.12,.88,.15)
  if mask<.040:continue
  X=[];Z=[];W=[]
  for q,j,d in kd.find_range(c,.060):
   dv=q-c
   if abs(dv.x)>.047 or abs(dv.y)>.046 or abs(dv.z)>.022:continue
   dot=n.dot(normals[j])
   if dot<.73 or n.z*normals[j].z<=0:continue
   ax=dv.x/.027;ay=dv.y/.026
   w=math.exp(-.5*(ax*ax+ay*ay))*dot**4
   if w<.006:continue
   X.append([1.,ax,ay,ax*ax,ax*ay,ay*ay]);Z.append(float(q.z));W.append(math.sqrt(w))
  if len(X)<18:continue
  weight=np.asarray(W);A=np.asarray(X,dtype=np.float64)*weight[:,None]
  try:fit,_,rank,_=np.linalg.lstsq(A,np.asarray(Z)*weight,rcond=None)
  except Exception:continue
  if rank<6:continue
  dz=max(-.00105,min(.00105,(float(fit[0])-float(c.z))*.67*mask))
  # Original F50 photos show a broad cowl crown; soften only existing crest
  # vertices, not the visor edge, using original imported local coordinates.
  u=(c.x-x0)/(x1-x0)
  crown=math.exp(-((u-.5)/.22)**4)
  band=smooth((float(c.z)-(zmax-.011))/.008)
  dz-=.00048*crown*band*mask
  if abs(dz)>0.0000001:changes[i]=dz
 assert len(changes)>500,("cowl insufficient target source topology",len(changes))
 for i,d in changes.items():m.vertices[i].co.z+=d
 m.update()
 o["source_edit_scope"]="F50 slot C v23 native original gauge visor controlled curvature/photo lip fairing, no changed source faces"
 return original
def steering_original_grip(o):
 """Subtle left/right symmetric hand-grip profile and lower-spoke transition on the
 genuine original F50 three-spoke wheel. Do not introduce rings or surrogate meshes."""
 m=o.data;original=[v.co.copy() for v in m.vertices]
 for v in m.vertices:
  c=v.co;x,y,z=c;r=math.hypot(x,y)
  if r<.118 or r>.176:continue
  theta=math.atan2(y,x)
  grip=math.exp(-((r-.151)/.016)**4)
  if grip<.002:continue
  side_l=math.exp(-((theta-(math.pi/2+.70))/.245)**4)
  side_r=math.exp(-((theta-(math.pi/2-.70))/.245)**4)
  bottom=math.exp(-((theta+math.pi/2)/.34)**4)
  crown=math.exp(-((theta-math.pi/2)/.65)**4)
  relief=(side_l+side_r)*grip
  dr=.00067*relief+.00037*bottom*grip+.00022*crown*grip
  if r>1e-8:
   c.x+=dr*x/r;c.y+=dr*y/r
  c.z+=.00057*relief+.00032*bottom*grip-.00017*crown*grip
 m.update()
 o["source_edit_scope"]="F50 slot C v23 original 3-spoke upper left/right sculpted grip and lower junction, wheel topology/pivot intact"
 return original
def hub_original_plate_fairing(o):
 """Photo-guided six-bolt front plate smoothing limited to ORIGINAL mesh:
 preserves center badge recess, original screw islands and original open boundaries."""
 m=o.data;orig=[v.co.copy() for v in m.vertices]
 coords=[v.co.copy() for v in m.vertices]
 normals=[v.normal.copy() for v in m.vertices]
 kd=kdtree.KDTree(len(coords))
 for i,c in enumerate(coords):kd.insert(c,i)
 kd.balance()
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
   for a in (30,90,150,210,270,330)]
 changes={}
 for i,c in enumerate(coords):
  radius=math.hypot(c.x,c.y+.019)
  if radius>.068 or normals[i].z<.57:continue
  if radius<.021:continue
  away=min(math.hypot(c.x-bx,c.y-by) for bx,by in bolts)
  mask=smooth((radius-.021)/.013)*smooth((.068-radius)/.012)
  mask*=smooth((away-.007)/.010)
  if mask<.035:continue
  sumw=0.;sumz=0.
  for q,j,d in kd.find_range(c,.016):
   if j==i:continue
   n=normals[i].dot(normals[j])
   if n<.75 or abs(q.z-c.z)>.007:continue
   d2=(q.x-c.x)**2+(q.y-c.y)**2
   if d2>.013**2:continue
   w=math.exp(-d2/(2*.0065**2))*n**4
   sumw+=w;sumz+=w*q.z
  if sumw<.025:continue
  dz=max(-.00090,min(.00090,(sumz/sumw-c.z)*.68*mask))
  if abs(dz)>1e-7:changes[i]=dz
 assert len(changes)>80,("native hub data missing",len(changes))
 for i,dz in changes.items():m.vertices[i].co.z+=dz
 m.update()
 o["source_edit_scope"]="F50 slot C v23 original six-bolt cup/plate local smooth, preserve factory fastener islands and badge"
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
 for path,expected in ((a.native,PMT),(a.original_import,IMPORT),(a.before,V22)):
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
 assert bpy.context.scene.get("geometry_edit_count")==66
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
 bpy.context.scene["geometry_edit_count"]=69
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V23_ORIGINAL_COWL_CROWN_PHOTO_GRIP_HUB"
 bpy.context.scene["slot_c_input_blend_sha256"]=V22
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 for label,(camera,visible) in VIEWS.items():
  path=Path(str(a.render_root)+"_AFTER_"+label+".png")
  render(path,camera,visible);renders["after_"+label]={"path":str(path),"sha256":digest(path)}
 source_guard(a)
 j={"status":"LOCAL_F50_V23_SAVED_INDEPENDENT_REOPEN_PENDING","blender":bpy.app.version_string,
    "native_pmt_sha256":PMT,"original_import_sha256":IMPORT,"input_v22_sha256":V22,
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
 print("F50_V23_SOURCE_SAVED",j["output_sha256"],stats)
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
 x={"status":"PASS_F50_V23_NATIVE_ORIGINAL_BLENDER_4_5_15_FRESH_REOPEN_AND_RENDER",
    "original_pmt_sha256":digest(a.native),"original_import_sha256":digest(a.original_import),
    "input_v22_sha256":digest(a.before),"candidate_sha256":digest(a.after),
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

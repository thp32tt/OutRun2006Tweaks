#!/usr/bin/env python3
"""Slot C F50 v21_r2: edit ONLY three authenticated native PMT-derived cockpit meshes.
Native PMT, original import and v20 input are immutable. Never export game resources.
"""
import bpy,bmesh,math,hashlib,struct,json,argparse,sys
from pathlib import Path
from mathutils import kdtree
PMT="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
V20="e4b82bf586ac8459960b61117d4fb68b8a0e5fa22beae2006fb18b1edc0f47bc"
TARGETS={
"PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"2beef9bfedd70361f8be1d55c58d95959e0eaf185493c6eb2fa6b352f082ee16"),
"PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"ff0d50d358343794daef0183a0e0f4c1456859932e9609df1af2e55beb1d90db"),
"PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"ff4f9ced8d5d6873ebf57922ecf6da3efd1519eaf5f16342f0b32c04895f6a31")}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def meshsha(me):
 h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack("<3f",*v.co))
 for f in me.polygons:
  h.update(struct.pack("<I",len(f.vertices)))
  for idx in f.vertices:h.update(struct.pack("<I",idx))
 return h.hexdigest()
def snap(o):
 bm=bmesh.new();bm.from_mesh(o.data);nm=sum(not e.is_manifold for e in bm.edges);bm.free()
 return {"original_id":o.get("outrun_original_mesh_object_id"),"original_pmt":o.get("outrun_original_game_resource_sha256"),
         "sha256":meshsha(o.data),"verts":len(o.data.vertices),"faces":len(o.data.polygons),"nonmanifold":nm,
         "uv":len(o.data.uv_layers),"materials":len(o.data.materials),
         "matrix":[round(float(v),9) for row in o.matrix_world for v in row]}
def smooth(t):
 t=max(0.,min(1.,t))
 return t*t*(3.-2.*t)
def gate(t,lo,hi,fall):
 return smooth((t-lo)/fall)*smooth((hi-t)/fall)
def sculpt_cowl(o):
 """Repair only original imported F50 gauge visor: repeated normal-side gated local quadratic
 regression over nearby ORIGINAL surface coordinates. No face/edge topology additions.
 Rejected prior topology-fan averaging; smooth across triangulation direction instead.
 """
 import numpy as np
 me=o.data
 original=[tuple(v.co) for v in me.vertices]
 xmin=min(v.co.x for v in me.vertices);xmax=max(v.co.x for v in me.vertices)
 ymin=min(v.co.y for v in me.vertices);ymax=max(v.co.y for v in me.vertices)
 sx=xmax-xmin;sy=ymax-ymin
 normals=[v.normal.copy() for v in me.vertices]
 improved=set()
 for pass_no in range(2):
  coords=[v.co.copy() for v in me.vertices]
  kd=kdtree.KDTree(len(coords))
  for i,c in enumerate(coords):kd.insert(c,i)
  kd.balance()
  changes={}
  for i,c in enumerate(coords):
   n=normals[i]
   if abs(n.z)<.48:continue
   mask=gate((c.x-xmin)/sx,.065,.935,.12)*gate((c.y-ymin)/sy,.12,.90,.14)
   if mask<.025:continue
   X=[];Z=[];W=[]
   for q,j,d in kd.find_range(c,.069):
    delta=q-c
    if abs(delta.x)>.060 or abs(delta.y)>.049 or abs(delta.z)>.025:continue
    dot=n.dot(normals[j])
    if dot<.60 or n.z*normals[j].z<=0:continue
    ax=delta.x/.030;ay=delta.y/.027
    w=math.exp(-.5*(ax*ax+ay*ay)) * dot**3
    if w<.004:continue
    X.append([1.,ax,ay,ax*ax,ax*ay,ay*ay]);Z.append(float(q.z));W.append(math.sqrt(w))
   if len(X)<20:continue
   weights=np.asarray(W);A=np.asarray(X,dtype=np.float64)*weights[:,None]
   values=np.asarray(Z)*weights
   try:coeff,_,rank,_=np.linalg.lstsq(A,values,rcond=None)
   except Exception:continue
   if rank<6:continue
   dz=max(-.0023,min(.0023,(float(coeff[0])-float(c.z))*.88*mask))
   total=float(c.z)-original[i][2]
   dz=max(-.0042-total,min(.0042-total,dz))
   if abs(dz)>1e-7:changes[i]=dz
  assert len(changes)>650,(pass_no,len(changes))
  for i,dz in changes.items():me.vertices[i].co.z+=dz;improved.add(i)
  me.update()
 o["source_edit_scope"]="F50 slot C v21_r2-r2 original PMT gauge visor non-fan bilateral quadratic 2-pass surface curvature fairing, native outline retained"
 o["native_quadratic_fairing_vertices"]=len(improved)
 return original

def sculpt_wheel(o):
 """Genuine F50 source rim and three spokes: photographic upper grip/shaping, original pivot intact."""
 me=o.data;original=[tuple(v.co) for v in me.vertices]
 for v in me.vertices:
  x,y,z=v.co;r=math.hypot(x,y)
  if not .115<r<.179:continue
  theta=math.atan2(y,x)
  arc=math.exp(-((theta-math.pi/2)/1.07)**4)
  shoulder=math.exp(-((abs(theta-math.pi/2)-.79)/.21)**4)
  grip=math.exp(-((r-.151)/.017)**4)
  edge=math.exp(-((r-.166)/.008)**4)
  radial=arc*grip*.00105
  if r>1e-8:v.co.x+=radial*x/r;v.co.y+=radial*y/r
  v.co.z+=arc*(.00092*grip+.00034*edge)+.0010*shoulder*grip
 me.update()
 o["source_edit_scope"]="F50 slot C v21_r2 native three-spoke and upper grip rounded in-place, inherited 624 open boundary edges unchanged"
 return original

def sculpt_hub(o):
 """Genuine original center hub: fair front surface, retain six known photographed bolt-seat locations."""
 me=o.data;original=[tuple(v.co) for v in me.vertices]
 coords=[v.co.copy() for v in me.vertices];normals=[v.normal.copy() for v in me.vertices]
 kd=kdtree.KDTree(len(coords))
 for i,c in enumerate(coords):kd.insert(c,i)
 kd.balance()
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 changes={}
 for i,c in enumerate(coords):
  radius=math.hypot(c.x,c.y+.019)
  if radius>.069 or normals[i].z<.48:continue
  mask=gate(radius,0.,.067,.015)
  mask*=smooth((min(math.hypot(c.x-bx,c.y-by) for bx,by in bolts)-.007)/.012)
  if mask<.04:continue
  total=0.;zsum=0.
  for q,j,d in kd.find_range(c,.018):
   if i==j:continue
   dot=normals[i].dot(normals[j])
   if dot<.60 or abs(q.z-c.z)>.008:continue
   dist2=(q.x-c.x)**2+(q.y-c.y)**2
   if dist2>.014**2:continue
   weight=math.exp(-dist2/(2*.0075**2))*dot**3
   total+=weight;zsum+=weight*q.z
  if total<.03:continue
  dz=max(-.0023,min(.0023,(zsum/total-c.z)*.70*mask))
  if abs(dz)>1e-7:changes[i]=dz
 for i,dz in changes.items():me.vertices[i].co.z+=dz
 me.update()
 assert len(changes)>160,len(changes)
 o["source_edit_scope"]="F50 slot C v21_r2 native center six-bolt plate/hub relief fairing in place, no fabricated hub"
 o["native_hub_fairing_vertices"]=len(changes)
 return original

def render(path,camera,visible):
 sc=bpy.context.scene;prev=(sc.camera,sc.render.engine,sc.render.filepath,sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage)
 hidden={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 try:
  sc.camera=bpy.data.objects[camera];sc.render.engine="BLENDER_WORKBENCH"
  sc.render.resolution_x=800;sc.render.resolution_y=560;sc.render.resolution_percentage=100
  sc.render.image_settings.file_format="PNG"
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in visible
  sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
  assert path.is_file() and path.stat().st_size>10000
 finally:
  sc.camera,sc.render.engine,sc.render.filepath,sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage=prev
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=hidden[o.name]
def main():
 p=argparse.ArgumentParser()
 for n in ["native","original-import","input","output","report","render-root"]:p.add_argument("--"+n,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 assert sha(a.native)==PMT and sha(a.original_import)==IMPORT and sha(a.input)==V20,"BLOCKED_INPUT: exact original source/verified Blender SHA mismatch"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 assert not a.output.exists() and not a.report.exists(),"Refusing to overwrite private checkpoint"
 assert bpy.context.scene.get("geometry_edit_count")==60
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
 objs={o.name:o for o in bpy.data.objects if o.type=="MESH"}
 assert len(objs)==42
 before={n:snap(o) for n,o in objs.items()}
 for n,(oid,v,f,h) in TARGETS.items():
  s=before[n]
  assert (s["original_id"],s["verts"],s["faces"],s["sha256"],s["original_pmt"])==(oid,v,f,h,PMT),(n,s)
 cameras={o.name:[round(float(v),9) for row in o.matrix_world for v in row] for o in bpy.data.objects if o.type=="CAMERA"}
 views={"GAUGE":("QA_F50_GAUGE_DETAIL_NON_GAME",["PMT_F50_object00_group01_material028_a0"]),
        "STEERING":("QA_F50_STEERING_LOCAL_NON_GAME",["PMT_F50_object21_group00_material000_a0","PMT_F50_object21_group01_material001_a0","PMT_F50_object21_group01_material002_a0"])}
 renders={}
 for label,(cam,keep) in views.items():
  path=Path(str(a.render_root)+"_BEFORE_"+label+".png");render(path,cam,keep);renders["before_"+label]={"path":str(path),"sha256":sha(path)}
 moved={}
 for name,fn in zip(TARGETS,[sculpt_cowl,sculpt_wheel,sculpt_hub]):
  start=fn(objs[name]);vs=objs[name].data.vertices
  count=sum(math.dist(start[i],v.co)>1e-6 for i,v in enumerate(vs))
  magnitude=max(math.dist(start[i],v.co) for i,v in enumerate(vs))
  assert count>150 and magnitude>.00020,(name,count,magnitude)
  moved[name]={"count":count,"max_displacement_mm":round(magnitude*1000,6)}
 after={n:snap(o) for n,o in objs.items()}
 for name in before:
  b=before[name];c=after[name]
  assert (b["original_id"],b["original_pmt"],b["verts"],b["faces"],b["nonmanifold"],b["uv"],b["materials"],b["matrix"])==(c["original_id"],c["original_pmt"],c["verts"],c["faces"],c["nonmanifold"],c["uv"],c["materials"],c["matrix"])
  if name in TARGETS:assert b["sha256"]!=c["sha256"]
  else:assert b==c,"SLOT GUARD unexpectedly edited "+name
 assert cameras=={o.name:[round(float(v),9) for row in o.matrix_world for v in row] for o in bpy.data.objects if o.type=="CAMERA"}
 bpy.context.scene["geometry_edit_count"]=63
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V21_R2_ORIGINAL_COWL_QUADRATIC_SURFACE_GRIP_HUB"
 bpy.context.scene["slot_c_input_blend_sha256"]=V20
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,(cam,keep) in views.items():
  path=Path(str(a.render_root)+"_AFTER_"+label+".png");render(path,cam,keep);renders["after_"+label]={"path":str(path),"sha256":sha(path)}
 assert sha(a.native)==PMT and sha(a.original_import)==IMPORT and sha(a.input)==V20
 data={"status":"LOCAL_SAVED_F50_V21_R2_INDEPENDENT_REOPEN_REQUIRED","blender":bpy.app.version_string,
  "original_pmt_sha256":PMT,"original_import_blend_sha256":IMPORT,"input_v20_sha256":V20,
  "output_private_blend":str(a.output),"output_sha256":sha(a.output),"total_original_meshes":42,
  "modified_original_meshes":{n:{"before":before[n],"after":after[n],"moved":moved[n]} for n in TARGETS},
  "other_native_meshes_hash_identical":39,"renders":renders,
  "native_game_driver_eye":"UNVERIFIED","seven_photo_views":"INCOMPLETE",
  "github_hosted_real_private_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "original_wheel_boundary_edges":after["PMT_F50_object21_group01_material002_a0"]["nonmanifold"],
  "game_conversion_or_export":False,"new_texture_or_pbr":False,"other_slot_changes":False,"vehicle_complete":False,"score_delta":0}
 a.report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")
 print("F50_V21_R2_SAVED",data["output_sha256"],moved)
if __name__=="__main__":main()
#!/usr/bin/env python3
"""Slot C F50 v19: edit ONLY three authenticated native PMT-derived cockpit meshes.
Native PMT, original import and v18 input are immutable. Never export game resources.
"""
import bpy,bmesh,math,hashlib,struct,json,argparse,sys
from pathlib import Path
from mathutils import kdtree
PMT="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
V18="c9c2156c21754a3982f8a2f0f602b45834f0f789010717fbc858053638b5f86d"
TARGETS={
"PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"ecb2bf25ce53fbc881a7db9790400786a76b4342f74fcefdc61303445fbd2cce"),
"PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"69f0e5f9f0186e7696e2a329e0bea6fd4f6e63099c32101900dc15c5e950b832"),
"PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"8aea7b7d1f1ea6b44034d7cd50a9b7a9fb7263646aaf17f3689ddad3503a526e")}
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
 """Native F50 dashboard visor: local quadratic 2D source-surface fit removes fan ripples
 without bridging the original double-sided closed shell or replacing its silhouette.
 All regression samples are existing PMT-derived Blender vertices, not a new model.
 """
 import numpy as np
 me=o.data
 original=[tuple(v.co) for v in me.vertices]
 coords=[v.co.copy() for v in me.vertices]
 normals=[v.normal.copy() for v in me.vertices]
 kd=kdtree.KDTree(len(coords))
 for i,co in enumerate(coords):kd.insert(co,i)
 kd.balance()
 xmin=min(c.x for c in coords);xmax=max(c.x for c in coords)
 ymin=min(c.y for c in coords);ymax=max(c.y for c in coords)
 sx=xmax-xmin;sy=ymax-ymin
 deltas={}
 fit_count=0
 for i,co in enumerate(coords):
  u=(co.x-xmin)/sx;t=(co.y-ymin)/sy
  mask=gate(u,.08,.92,.13)*gate(t,.25,.82,.13)
  if mask<.005 or abs(normals[i].z)<.55:continue
  X=[];Z=[];W=[]
  for _,j,d in kd.find_range(co,.070):
   near=coords[j]
   dx=near.x-co.x;dy=near.y-co.y;dz=near.z-co.z
   if abs(dx)>.063 or abs(dy)>.043 or abs(dz)>.028:continue
   agreement=normals[i].dot(normals[j])
   if agreement<.66 or normals[i].z*normals[j].z<=0:continue
   a=dx/.030;b=dy/.024
   w=math.exp(-.5*(a*a+b*b))*agreement**4
   if w<.007:continue
   X.append([1.,a,b,a*a,a*b,b*b])
   Z.append(float(near.z))
   W.append(math.sqrt(w))
  if len(X)<25:continue
  design=np.asarray(X,dtype=np.float64)*np.asarray(W)[:,None]
  target=np.asarray(Z,dtype=np.float64)*np.asarray(W)
  try:
   coeff,_,rank,_=np.linalg.lstsq(design,target,rcond=None)
  except Exception:continue
  if rank<6:continue
  prediction=float(coeff[0])
  dz=max(-.0075,min(.0075,prediction-co.z))
  if abs(dz)<1e-7:continue
  deltas[i]=dz*.88*mask
  fit_count+=1
 for i,dz in deltas.items():me.vertices[i].co.z+=dz
 me.update()
 assert fit_count>700,fit_count
 o["source_edit_scope"]="F50 slot C v19: native double-surface-aware quadratic visor curvature refinement on existing source mesh; original dashboard silhouette preserved"
 o["native_fit_vertices"]=fit_count
 return original

def sculpt_wheel(o):
 """Shape only native F50 wheel grip quadrants and original three spoke shoulder edges."""
 me=o.data
 original=[tuple(v.co) for v in me.vertices]
 for v in me.vertices:
  x,y,z=v.co
  r=math.hypot(x,y)
  if not .065<r<.185:continue
  theta=math.atan2(y,x)
  top=math.exp(-((theta-math.pi/2)/.41)**4)
  q1=math.exp(-((theta-.46)/.27)**4)
  q2=math.exp(-((theta-(math.pi-.46))/.27)**4)
  grip=(q1+q2)*math.exp(-((r-.153)/.024)**4)
  shoulder=math.exp(-((abs(x)-.111)/.032)**4)*math.exp(-((y+.024)/.035)**4)
  lower=math.exp(-(x/.042)**4)*math.exp(-((y+.098)/.049)**4)
  dr=.00108*grip + .00042*top*math.exp(-((r-.153)/.024)**4)
  if r>1e-8:
   v.co.x+=dr*x/r
   v.co.y+=dr*y/r
  v.co.z+=.00066*shoulder+.00067*lower+.00014*top*grip
 me.update()
 o["source_edit_scope"]="F50 slot C v19: source three-spoke steering rim grip contours and physical spoke-root shoulder; no native topology/animation transform changes"
 return original

def sculpt_hub(o):
 """Preserve original F50 boss center and six fastener positions; adjust their seat relief."""
 me=o.data
 original=[tuple(v.co) for v in me.vertices]
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
 for v in me.vertices:
  x,y,z=v.co
  r=math.hypot(x,y+.019)
  if r>.080:continue
  ridge=math.exp(-((r-.038)/.0065)**4)
  dish=math.exp(-(r/.025)**4)
  fillet=math.exp(-((r-.064)/.009)**4)
  dz=.00075*ridge-.00030*dish+.00025*fillet
  for bx,by in bolts:
   d=math.hypot(x-bx,y-by)
   dz+=.00014*math.exp(-((d-.012)/.005)**4)
  v.co.z+=dz
 me.update()
 o["source_edit_scope"]="F50 slot C v19: existing horn cup/bezel + original six fastener seat geometry; no fabricated hub"
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
 assert sha(a.native)==PMT and sha(a.original_import)==IMPORT and sha(a.input)==V18,"BLOCKED_INPUT: exact original source/verified Blender SHA mismatch"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 assert not a.output.exists() and not a.report.exists(),"Refusing to overwrite private checkpoint"
 assert bpy.context.scene.get("geometry_edit_count")==54
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
 bpy.context.scene["geometry_edit_count"]=57
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V19_ORIGINAL_COWL_QUADRATIC_SURFACE_GRIP_HUB"
 bpy.context.scene["slot_c_input_blend_sha256"]=V18
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,(cam,keep) in views.items():
  path=Path(str(a.render_root)+"_AFTER_"+label+".png");render(path,cam,keep);renders["after_"+label]={"path":str(path),"sha256":sha(path)}
 assert sha(a.native)==PMT and sha(a.original_import)==IMPORT and sha(a.input)==V18
 data={"status":"LOCAL_SAVED_F50_V19_INDEPENDENT_REOPEN_REQUIRED","blender":bpy.app.version_string,
  "original_pmt_sha256":PMT,"original_import_blend_sha256":IMPORT,"input_v18_sha256":V18,
  "output_private_blend":str(a.output),"output_sha256":sha(a.output),"total_original_meshes":42,
  "modified_original_meshes":{n:{"before":before[n],"after":after[n],"moved":moved[n]} for n in TARGETS},
  "other_native_meshes_hash_identical":39,"renders":renders,
  "native_game_driver_eye":"UNVERIFIED","seven_photo_views":"INCOMPLETE",
  "github_hosted_real_private_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "original_wheel_boundary_edges":after["PMT_F50_object21_group01_material002_a0"]["nonmanifold"],
  "game_conversion_or_export":False,"new_texture_or_pbr":False,"other_slot_changes":False,"vehicle_complete":False,"score_delta":0}
 a.report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")
 print("F50_V19_SAVED",data["output_sha256"],moved)
if __name__=="__main__":main()
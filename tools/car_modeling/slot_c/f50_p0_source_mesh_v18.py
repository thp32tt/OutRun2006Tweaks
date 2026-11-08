#!/usr/bin/env python3
"""Slot C F50 v18: edit ONLY three authenticated native PMT-derived cockpit meshes.
Native PMT, original import and v17 input are immutable. Never export game resources.
"""
import bpy,bmesh,math,hashlib,struct,json,argparse,sys
from pathlib import Path
from mathutils import kdtree
PMT="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
V17="418574c3d9075495a0695bc8c625c4c0d5fb12b6d106ce2069cdf3b36b2c040d"
TARGETS={
"PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"91a0c1136fda7b0ec79d07f7e0834db12896d829392056d3ca8a4e05d5eb7561"),
"PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"d9662cf9cf72c72c853e36b884bdb3a24d76abb5f0c0c8070cea8fe6bf54fd57"),
"PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"b2f4d4ecac0d7ffc82663d2add358351f13210f83aab343536b4d986282b1e33")}
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
 """Anti-radial-wrinkle screen over the existing connected, normal-compatible dashboard visor.
    Preserve all source triangles, silhouette bounds, two-sided surfaces, and transforms.
 """
 me=o.data
 orig=[tuple(v.co) for v in me.vertices]
 xyz=[v.co.copy() for v in me.vertices]
 normals=[v.normal.copy() for v in me.vertices]
 kd=kdtree.KDTree(len(xyz))
 for i,c in enumerate(xyz):kd.insert(c,i)
 kd.balance()
 xmin=min(c.x for c in xyz);xmax=max(c.x for c in xyz)
 ymin=min(c.y for c in xyz);ymax=max(c.y for c in xyz)
 sx=xmax-xmin;sy=ymax-ymin
 masks=[]
 for c in xyz:
  u=(c.x-xmin)/sx;t=(c.y-ymin)/sy
  masks.append(gate(u,.07,.93,.14)*gate(t,.24,.91,.16))
 # Neighbors come from this exact original imported cowl, not a generated surrogate.
 # Normal agreement prevents smoothing between opposite sides of a thin native shell.
 nei=[]
 for i,c in enumerate(xyz):
  sample=[]
  for _,j,d in kd.find_range(c,.039):
   if i==j or d<1e-6 or normals[i].dot(normals[j])<.83 or abs(xyz[i].z-xyz[j].z)>.012:continue
   w=math.exp(-.5*(d/.021)**2)*max(.05,normals[i].dot(normals[j])**6)
   sample.append((j,w))
  nei.append(sample)
 z=[c.z for c in xyz]
 for step in range(5):
  old=z[:]
  for i,ns in enumerate(nei):
   if masks[i]<.005 or len(ns)<5:continue
   total=sum(w for _,w in ns)
   local=sum(old[j]*w for j,w in ns)/total
   blend=.57*masks[i]
   z[i]=max(xyz[i].z-.006,min(xyz[i].z+.006,old[i]*(1-blend)+blend*local))
 for i,v in enumerate(me.vertices):
  if abs(z[i]-v.co.z)>1e-8:v.co.z=z[i]
 me.update()
 o["source_edit_scope"]="slot C v18 original F50 dashboard visor cowl: source-normal-guided broad surface correction, no added object"
 return orig
def sculpt_wheel(o):
 """Photo-limited native wheel rim grip and three original spoke shoulder rolls."""
 me=o.data;orig=[tuple(v.co) for v in me.vertices]
 for v in me.vertices:
  x,y,z=v.co
  r=math.hypot(x,y)
  if not .045<r<.188:continue
  theta=math.atan2(y,x)
  ring=math.exp(-((r-.151)/.027)**4)
  wrap=math.exp(-((theta-1.57)/.39)**4)
  side=math.exp(-((abs(theta)-.33)/.27)**4)+math.exp(-((abs(theta)-2.81)/.27)**4)
  shoulder=math.exp(-((abs(x)-.102)/.035)**4)*math.exp(-((y+.025)/.032)**4)
  lower=math.exp(-(x/.039)**4)*math.exp(-((y+.094)/.047)**4)
  radial=ring*(.00076*side+.00042*wrap)
  v.co.x+=radial*x/r;v.co.y+=radial*y/r
  v.co.z+=.0009*shoulder+.00068*lower+.00016*ring*wrap
 me.update()
 o["source_edit_scope"]="slot C v18 original F50 3-spoke/rim: native grip/shoulder physical geometry, source open edge loops unchanged"
 return orig
def sculpt_hub(o):
 """Physically round the existing six-fastener original center and spoke-root lip."""
 me=o.data;orig=[tuple(v.co) for v in me.vertices]
 for v in me.vertices:
  x,y,z=v.co
  r=math.hypot(x,y+.019)
  if r>.09:continue
  flange=math.exp(-((r-.048)/.012)**4)
  center=math.exp(-((r-.026)/.008)**4)
  upper=math.exp(-(x/.054)**4)*math.exp(-((y-.019)/.027)**4)
  side=math.exp(-((abs(x)-.056)/.019)**4)*math.exp(-((y+.012)/.029)**4)
  dz=.00092*flange-.00049*center+.00042*side+.00026*upper
  v.co.z+=dz
 me.update()
 o["source_edit_scope"]="slot C v18 F50 original hub/cup/six-fastener lip: source vertices only"
 return orig
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
 assert sha(a.native)==PMT and sha(a.original_import)==IMPORT and sha(a.input)==V17,"BLOCKED_INPUT: exact original source/verified Blender SHA mismatch"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 assert not a.output.exists() and not a.report.exists(),"Refusing to overwrite private checkpoint"
 assert bpy.context.scene.get("geometry_edit_count")==51
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
 bpy.context.scene["geometry_edit_count"]=54
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V18_NATIVE_COWL_WRINKLE_STEERING_SOURCE_EDIT"
 bpy.context.scene["slot_c_input_blend_sha256"]=V17
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,(cam,keep) in views.items():
  path=Path(str(a.render_root)+"_AFTER_"+label+".png");render(path,cam,keep);renders["after_"+label]={"path":str(path),"sha256":sha(path)}
 assert sha(a.native)==PMT and sha(a.original_import)==IMPORT and sha(a.input)==V17
 data={"status":"LOCAL_SAVED_F50_V18_INDEPENDENT_REOPEN_REQUIRED","blender":bpy.app.version_string,
  "original_pmt_sha256":PMT,"original_import_blend_sha256":IMPORT,"input_v17_sha256":V17,
  "output_private_blend":str(a.output),"output_sha256":sha(a.output),"total_original_meshes":42,
  "modified_original_meshes":{n:{"before":before[n],"after":after[n],"moved":moved[n]} for n in TARGETS},
  "other_native_meshes_hash_identical":39,"renders":renders,
  "native_game_driver_eye":"UNVERIFIED","seven_photo_views":"INCOMPLETE",
  "github_hosted_real_private_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "original_wheel_boundary_edges":after["PMT_F50_object21_group01_material002_a0"]["nonmanifold"],
  "game_conversion_or_export":False,"new_texture_or_pbr":False,"other_slot_changes":False,"vehicle_complete":False,"score_delta":0}
 a.report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")
 print("F50_V18_SAVED",data["output_sha256"],moved)
if __name__=="__main__":main()
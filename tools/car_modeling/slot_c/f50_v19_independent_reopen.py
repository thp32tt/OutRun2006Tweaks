#!/usr/bin/env python3
"""Independent separate-process Blender 4.5.15 original F50 source-mesh v19 verification."""
import bpy,bmesh,hashlib,struct,sys,argparse,json
from pathlib import Path
PMT="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
ORIGINAL="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
V18="c9c2156c21754a3982f8a2f0f602b45834f0f789010717fbc858053638b5f86d"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snap():
 result={}
 for o in bpy.data.objects:
  if o.type!="MESH":continue
  m=o.data;h=hashlib.sha256()
  for v in m.vertices:h.update(struct.pack("<3f",*v.co))
  for f in m.polygons:
   h.update(struct.pack("<I",len(f.vertices)))
   for index in f.vertices:h.update(struct.pack("<I",index))
  bm=bmesh.new();bm.from_mesh(m);nonmanifold=sum(not e.is_manifold for e in bm.edges);bm.free()
  result[o.name]={"sha256":h.hexdigest(),"verts":len(m.vertices),"faces":len(m.polygons),
    "original_id":o.get("outrun_original_mesh_object_id"),"pmt":o.get("outrun_original_game_resource_sha256"),
    "nonmanifold":nonmanifold,"uv":len(m.uv_layers),"materials":len(m.materials),
    "matrix":[round(float(v),9) for row in o.matrix_world for v in row]}
 return result
def cams():
 return {o.name:([round(float(v),9) for row in o.matrix_world for v in row],o.data.type,round(float(o.data.lens),9)) for o in bpy.data.objects if o.type=="CAMERA"}
def render_one(path):
 sc=bpy.context.scene
 old=[(o,o.hide_render) for o in bpy.data.objects if o.type=="MESH"]
 cam=sc.camera;engine=sc.render.engine;file=sc.render.filepath
 try:
  sc.camera=bpy.data.objects["QA_F50_STEERING_LOCAL_NON_GAME"]
  sc.render.engine="BLENDER_WORKBENCH";sc.render.resolution_x=800;sc.render.resolution_y=560;sc.render.resolution_percentage=100
  sc.render.image_settings.file_format="PNG"
  visible={"PMT_F50_object21_group00_material000_a0","PMT_F50_object21_group01_material001_a0","PMT_F50_object21_group01_material002_a0"}
  for o,_ in old:o.hide_render=o.name not in visible
  sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
  assert path.is_file() and path.stat().st_size>10000
 finally:
  for o,hidden in old:o.hide_render=hidden
  sc.camera=cam;sc.render.engine=engine;sc.render.filepath=file
def main():
 p=argparse.ArgumentParser()
 for n in ["native","original-import","before","after","report","audit","render"]:p.add_argument("--"+n,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15)
 assert sha(a.native)==PMT and sha(a.original_import)==ORIGINAL and sha(a.before)==V18
 j=json.loads(a.report.read_text(encoding="utf8"))
 assert sha(a.after)==j["output_sha256"] and Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert bpy.context.scene.get("geometry_edit_count")==57
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
 current=snap();after_cams=cams()
 assert len(current)==42
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 before=snap();before_cams=cams()
 assert len(before)==42 and set(before)==set(current) and before_cams==after_cams
 targets=set(j["modified_original_meshes"])
 assert len(targets)==3
 for n,b in before.items():
  c=current[n]
  assert b["original_id"] and b["pmt"]==c["pmt"]==PMT
  for k in ["original_id","pmt","verts","faces","nonmanifold","uv","materials","matrix"]:
   assert b[k]==c[k],(n,k)
  if n in targets:
   assert b["sha256"]!=c["sha256"],n
   assert b["sha256"]==j["modified_original_meshes"][n]["before"]["sha256"]
   assert c["sha256"]==j["modified_original_meshes"][n]["after"]["sha256"]
  else:assert b==c,"Unexpected source edit: "+n
 assert sum(before[n]["sha256"]==current[n]["sha256"] for n in before)==39
 assert current["PMT_F50_object21_group01_material002_a0"]["nonmanifold"]==624
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert snap()==current and cams()==after_cams
 render_one(a.render)
 assert not a.audit.exists()
 audit={"status":"PASS_INDEPENDENT_F50_V19_TRUE_ORIGINAL_BLENDER_4_5_15_REOPEN_RENDER",
 "output_sha256":sha(a.after),"native_pmt_sha256":sha(a.native),"original_import_blend_sha256":sha(a.original_import),
 "input_v18_sha256":V18,"mesh_count":42,"modified_meshes":sorted(targets),
 "identical_other_meshes":39,"original_ids_transforms_uv_materials_unchanged":True,
 "source_wheel_nonmanifold_edges":624,"render_sha256":sha(a.render),
 "native_game_driver_eye":"UNVERIFIED","seven_view_QA":"INCOMPLETE",
 "github_hosted_private_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED","complete":False,"score_delta":0}
 a.audit.write_text(json.dumps(audit,indent=2),encoding="utf8")
 print(audit["status"],audit["output_sha256"],audit["render_sha256"])
if __name__=="__main__":main()
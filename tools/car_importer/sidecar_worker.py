"""Blender-only OutRun VR OVRCABH2 export of user-supplied staged model.
Creates sidecar in separate test folder. Never changes original PMT or game.
Strictly EXPERIMENTAL, not game runtime validated. Requires rights-cleared input.
"""
import bpy,sys,json,hashlib,struct,math,zlib,io
from array import array
from pathlib import Path
from mathutils import Vector
ap=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if len(ap)!=3: raise SystemExit("usage: blender --background --python export_f50_sidecar.py -- STAGED.blend OUTPUT.ovc MANIFEST.json")
source,output,manifest=map(Path,ap)
assert source.is_file() and output.parent.is_dir() and not output.exists() and not manifest.exists()
assert output.suffix.lower()==".ovc"
assert not any(x.lower() in {"cars","outrun2006","outrun2006tweaks"} for x in output.parts[-4:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original_sha=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False)
coll=bpy.data.collections.get("EXTERNAL_MODEL_STAGED_NOT_GAME_ASSET")
assert coll is not None
objs=sorted((o for o in coll.objects if o.type=="MESH"),key=lambda o:o.name)
assert len(objs)>0
mat_to_id={}
mat_triangles={}
skipped=[]
def pick_image(mat):
 if not mat or not mat.use_nodes:return None
 bsdf=next((n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED"),None)
 if bsdf:
  inp=bsdf.inputs.get("Base Color")
  if inp:
   for link in inp.links:
    if link.from_node.type=="TEX_IMAGE" and link.from_node.image:
     return link.from_node.image
 return next((n.image for n in mat.node_tree.nodes if n.type=="TEX_IMAGE" and n.image),None)
for oi,obj in enumerate(objs):
 mesh=obj.data;mesh.calc_loop_triangles()
 normal_transform=obj.matrix_world.to_3x3().inverted_safe().transposed()
 reverse=obj.matrix_world.determinant()<0
 uv_data=mesh.uv_layers.active.data if mesh.uv_layers.active else None
 corner=mesh.corner_normals
 for tri in mesh.loop_triangles:
  midx=tri.material_index
  mat=mesh.materials[midx] if midx<len(mesh.materials) else None
  name=mat.name if mat else "NO_MATERIAL"
  if "window" in name.lower() or "glass" in name.lower():
   skipped.append(name);continue
  if name not in mat_to_id:
   mat_to_id[name]=len(mat_to_id)
  mid=mat_to_id[name]
  buf=mat_triangles.setdefault(mid,bytearray())
  for li in (reversed(tri.loops) if reverse else tri.loops):
   lp=mesh.loops[li]
   v=mesh.vertices[lp.vertex_index]
   pos=obj.matrix_world @ v.co
   nv=normal_transform @ corner[li].vector
   nv.normalize()
   uv=uv_data[li].uv if uv_data else (0.0,0.0)
   vals=(*pos,*nv,float(uv[0]),float(1.0-uv[1]))
   if not all(math.isfinite(z) and abs(z)<10000 for z in vals):
    raise ValueError("nonfinite vertex in "+obj.name)
   buf.extend(struct.pack("<8f",*vals))
if not mat_triangles:raise ValueError("no triangle material groups")
assert len(mat_to_id)<=64
def dds(img,mat):
 maxside=256
 if img:
  local=img.copy()
  try:
   if local.size[0]<=0 or local.size[1]<=0:raise ValueError("bad source image")
   local.scale(maxside,maxside)
   data=array("f",[0.0])*(maxside*maxside*4)
   local.pixels.foreach_get(data)
   rgba=bytearray(maxside*maxside*4)
   # Blender image pixels are bottom-up; DDS is top-down BGRA.
   for y in range(maxside):
    for x in range(maxside):
     p=(y*maxside+x)*4
     q=((maxside-1-y)*maxside+x)*4
     rgba[q+0]=int(max(0,min(255,round(data[p+2]*255))))
     rgba[q+1]=int(max(0,min(255,round(data[p+1]*255))))
     rgba[q+2]=int(max(0,min(255,round(data[p+0]*255))))
     rgba[q+3]=255
  finally:bpy.data.images.remove(local)
 else:
  maxside=16
  if mat and mat.use_nodes:
   bsdf=next((n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED"),None)
   c=bsdf.inputs["Base Color"].default_value if bsdf else mat.diffuse_color
  else:c=mat.diffuse_color if mat else (0.68,0.68,0.68,1.0)
  rgba=bytes((round(max(0,min(1,c[2]))*255),round(max(0,min(1,c[1]))*255),round(max(0,min(1,c[0]))*255),255))*(maxside*maxside)
 h=bytearray(128);h[:4]=b"DDS "
 struct.pack_into("<I",h,4,124);struct.pack_into("<I",h,8,0x0002100F)
 struct.pack_into("<I",h,12,maxside);struct.pack_into("<I",h,16,maxside)
 struct.pack_into("<I",h,20,maxside*4);struct.pack_into("<I",h,28,1)
 struct.pack_into("<I",h,76,32);struct.pack_into("<I",h,80,0x41)
 struct.pack_into("<I",h,88,32)
 struct.pack_into("<4I",h,92,0x00ff0000,0x0000ff00,0x000000ff,0xff000000)
 struct.pack_into("<I",h,108,0x1000)
 return bytes(h)+rgba
payload=bytearray();group_records=[]
total_vertices=0;total_triangles=0
for name,mid in sorted(mat_to_id.items(),key=lambda p:p[1]):
 vb=mat_triangles.get(mid,b"")
 if not vb:continue
 num=len(vb)//32;tri=num//3
 if num>1000000 or tri>2000000:raise ValueError("group budget exceeded")
 name_bytes=("F50_PART_%02d"%mid).encode()
 idx=struct.pack("<%dI"%num,*range(num))
 payload.extend(struct.pack("<HHIII",len(name_bytes),mid,num,num,4))
 payload.extend(name_bytes);payload.extend(vb);payload.extend(idx)
 total_vertices+=num;total_triangles+=tri
 group_records.append({"group":name_bytes.decode(),"material":name,"vertex_count":num,"triangles":tri})
if total_vertices>1000000 or total_triangles>2000000 or len(group_records)>512:raise ValueError("aggregate budget exceeded")
for name,mid in sorted(mat_to_id.items(),key=lambda p:p[1]):
 mat=bpy.data.materials.get(name)
 texture=dds(pick_image(mat),mat)
 payload.extend(struct.pack("<I",len(texture)));payload.extend(texture)
if len(payload)>112*1024*1024:raise ValueError("GPU budget exceeded")
header=b"OVRCABH2"+struct.pack("<7I",2,len(group_records),len(mat_to_id),total_vertices,total_triangles,len(payload),zlib.crc32(payload)&0xffffffff)
assert len(header)==36
out=header+payload
assert len(out)<128*1024*1024
output.write_bytes(out)
assert sha(source)==original_sha
res={"status":"OVRCABH2_STATIC_EXPORT_NOT_GAME_RUNTIME_VALIDATED","source_blend":source.name,"source_blend_sha256":original_sha,"output_ovc":output.name,"output_sha256":sha(output),"bytes":output.stat().st_size,"meshes_orig":len(objs),"groups":len(group_records),"materials":len(mat_to_id),"vertices":total_vertices,"triangles":total_triangles,"skipped_glass_names":sorted(set(skipped)),"game_assets_modified":False,"original_car_animations_preserved":False,"source_rights":"USER_MUST_VERIFY"}
manifest.write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n")
print("F50_OVC2_CONVERT_PASS "+json.dumps(res),flush=True)
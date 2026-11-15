"""Blender-only EXTERNAL GLB stage -> OVRCABH2 experimental mesh sidecar.
Does not install or patch game, and does not claim the VR runtime loads F50 sidecars.
Use only with models for which independent conversion rights have been verified.
"""
import argparse,array,hashlib,json,math,struct,sys,zlib
from pathlib import Path
import bpy
from mathutils import Vector

MAX_GROUPS=512
MAX_MATERIALS=64
MAX_VERTICES=1000000
MAX_TRIANGLES=2000000
MAX_SIZE=128*1024*1024
TEX_SIDE=128
MAX_GROUP_VERTICES=60000
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def color_bytes(material):
 # DDS ARGB32 with exact D3D9 channel masks. Small at 128px for test GPU budget.
 rgba=[.7,.7,.7,1.]
 if material:
  try:rgba=list(material.diffuse_color)
  except Exception:pass
 img=None
 if material and material.use_nodes:
  for node in material.node_tree.nodes:
   if node.type=='TEX_IMAGE' and node.image:
    img=node.image;break
 pix=None
 if img and img.size[0]>0 and img.size[1]>0 and max(img.size)<=8192:
  try:
   clone=img.copy();clone.scale(TEX_SIDE,TEX_SIDE)
   pix=array.array('f',[0.]*(4*TEX_SIDE*TEX_SIDE))
   clone.pixels.foreach_get(pix)
   bpy.data.images.remove(clone)
  except Exception:pix=None
 pixels=bytearray()
 for i in range(TEX_SIDE*TEX_SIDE):
  c=(pix[i*4:i*4+4] if pix is not None else rgba)
  for j in (2,1,0,3):
   f=float(c[j])
   if not math.isfinite(f):f=0.
   pixels.append(max(0,min(255,round(f*255))))
 hdr=bytearray(128)
 hdr[:4]=b'DDS '
 struct.pack_into('<I',hdr,4,124)
 struct.pack_into('<I',hdr,8,0x0002100F)
 struct.pack_into('<I',hdr,12,TEX_SIDE)
 struct.pack_into('<I',hdr,16,TEX_SIDE)
 struct.pack_into('<I',hdr,20,TEX_SIDE*4)
 struct.pack_into('<I',hdr,28,1)
 struct.pack_into('<I',hdr,76,32)
 struct.pack_into('<I',hdr,80,0x41)
 struct.pack_into('<I',hdr,84,0)
 struct.pack_into('<I',hdr,88,32)
 struct.pack_into('<4I',hdr,92,0x00ff0000,0x0000ff00,0x000000ff,0xff000000)
 struct.pack_into('<I',hdr,108,0x1000)
 return bytes(hdr)+pixels

def export(blend,output):
 input_hash=digest(blend)
 bpy.ops.wm.open_mainfile(filepath=str(blend))
 coll=bpy.data.collections.get('EXTERNAL_MODEL_STAGED_NOT_GAME_ASSET')
 if coll is None:raise ValueError('Missing external-model collection')
 objs=[o for o in coll.objects if o.type=='MESH']
 if not objs:raise ValueError('External model is empty')
 mat_names={}
 for o in objs:
  for m in o.data.materials:
   if m is not None:mat_names[m.name]=m
 if len(mat_names)>MAX_MATERIALS-1:raise ValueError('Too many materials (max 63 + fallback)')
 mats=sorted(mat_names)
 matids={n:i for i,n in enumerate(mats)}
 fallback=len(mats)
 palette=[mat_names[n] for n in mats]+[None]
 # group map holds individual batches (some materials will have multiple groups)
 groups=[]
 batches={}  # material-id => {verts,index,keymap}
 def fresh():return {'vertices':[],'indices':[],'map':{}}
 def flush(mid):
  b=batches[mid]
  if b['indices']:
   groups.append((mid,b['vertices'],b['indices']))
   if len(groups)>MAX_GROUPS:raise ValueError('OVC group count >512')
  batches[mid]=fresh()
 for o in objs:
  me=o.data
  me.calc_loop_triangles()
  uvlayer=me.uv_layers.active
  world=o.matrix_world.copy()
  normal_mat=world.to_3x3().inverted_safe().transposed()
  flip=world.to_3x3().determinant()<0
  for triangle in me.loop_triangles:
   mat=me.materials[triangle.material_index] if triangle.material_index<len(me.materials) else None
   mid=matids[mat.name] if mat and mat.name in matids else fallback
   if mid not in batches:batches[mid]=fresh()
   batch=batches[mid]
   loops=list(triangle.loops)
   if flip:loops=[loops[0],loops[2],loops[1]]
   vertices=[]
   for li in loops:
    vi=me.loops[li].vertex_index
    uv=tuple(uvlayer.data[li].uv) if uvlayer else (0.,0.)
    key=(o.name,vi,round(uv[0],6),round(uv[1],6))
    vertices.append((vi,uv,key))
   needed=len({q[2] for q in vertices if q[2] not in batch['map']})
   if len(batch['vertices'])+needed>MAX_GROUP_VERTICES:
    flush(mid);batch=batches[mid]
   for vi,uv,key in vertices:
    ix=batch['map'].get(key)
    if ix is None:
     p=world@me.vertices[vi].co
     normal=(normal_mat@me.vertices[vi].normal).normalized()
     data=tuple(float(v) for v in (p.x,p.y,p.z,normal.x,normal.y,normal.z,uv[0],1.0-uv[1]))
     if not all(math.isfinite(v) and abs(v)<10000 for v in data):raise ValueError('Bad vertex values')
     ix=len(batch['vertices']);batch['vertices'].append(data);batch['map'][key]=ix
    batch['indices'].append(ix)
 for mid in sorted(batches):flush(mid)
 if not groups:raise ValueError('No triangle groups')
 tris=sum(len(g[2])//3 for g in groups)
 verts=sum(len(g[1]) for g in groups)
 if tris>MAX_TRIANGLES or verts>MAX_VERTICES:raise ValueError('Sidecar geometry budget exceeded')
 used=sorted({g[0] for g in groups})
 remap={v:i for i,v in enumerate(used)}
 dds=[color_bytes(palette[i]) for i in used]
 payload=bytearray()
 for n,(mid,positions,indices) in enumerate(groups):
  name=('F50_TEST_M%02d_G%03d'%(mid,n)).encode('ascii')
  if len(positions)>65535:raise ValueError('16 bit index overflow')
  payload+=struct.pack('<HHIII',len(name),remap[mid],len(positions),len(indices),2)
  payload+=name
  for v in positions:payload+=struct.pack('<8f',*v)
  for idx in indices:payload+=struct.pack('<H',idx)
 for tex in dds:
  payload+=struct.pack('<I',len(tex))
  payload+=tex
 if len(payload)+36>MAX_SIZE:raise ValueError('Sidecar file limit exceeded')
 header=b'OVRCABH2'+struct.pack('<7I',2,len(groups),len(dds),verts,tris,len(payload),zlib.crc32(payload)&0xffffffff)
 data=header+payload
 output.write_bytes(data)
 return {'status':'OVRCABH2_STATIC_EXPORT_ONLY_NOT_GAME_LOAD_VERIFIED','file':output.name,
  'sidecar_sha256':digest(output),'source_blend_sha256':input_hash,
  'groups':len(groups),'materials':len(dds),'vertices':verts,'triangles':tris,
  'output_bytes':len(data),'external_meshes':len(objs),'dds_side':TEX_SIDE,
  'game_files_modified':False,'runtime_gameplay_status':'UNTESTED',
  'note':'EXPERIMENTAL OVRCABH2 sidecar: F50 runtime loader not verified; original game PMT untouched'}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--blend',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True)
 args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
 if args.output.exists():raise ValueError('Output already exists')
 args.output.parent.mkdir(parents=True,exist_ok=True)
 result=export(args.blend.resolve(strict=True),args.output.resolve())
 manifest=args.output.with_suffix('.json')
 manifest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print('OUTRUN_OVRCABH2_EXPERIMENTAL_EXPORT_PASS '+json.dumps(result),flush=True)
if __name__=='__main__':main()
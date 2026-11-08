#!/usr/bin/env python3
"""Ferrari F50 slot C v34: edit only original PMT-derived dashboard/3-spoke/hub meshes.
The supplied scene must be the exact accepted private v33-r2 original native derivative.
No new mesh, textures, materials, PBR, game/native exports or runtime changes.
"""
import argparse, bpy, bmesh, hashlib, json, math, struct, sys
from pathlib import Path
from mathutils import kdtree

PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
PARENT_SHA="40a555a8d265b87d6ad7fc109672ceb339629a8311c1f5c0ca96a717916b19df"
D="PMT_F50_object00_group01_material028_a0"
W="PMT_F50_object21_group01_material002_a0"
H="PMT_F50_object21_group00_material000_a0"
TARGETS={D:(5506,7552),W:(13552,26496),H:(2738,4464)}
CAMERAS={"GAUGE":"QA_F50_GAUGE_DETAIL_NON_GAME","STEERING":"QA_F50_STEERING_LOCAL_NON_GAME"}

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
def smooth(t):
 t=max(0.,min(1.,t));return t*t*(3.-2.*t)
def gauss(x,s):
 return math.exp(-.5*(x/s)**2)
def clamp(x,lim):
 return max(-lim,min(lim,x))
def kd_tree(vs):
 kd=kdtree.KDTree(len(vs))
 for i,v in enumerate(vs):kd.insert(v,i)
 kd.balance();return kd
def mesh_hash(o):
 h=hashlib.sha256();m=o.data
 for v in m.vertices:h.update(struct.pack("<3f",*v.co))
 for p in m.polygons:
  h.update(struct.pack("<I",len(p.vertices)))
  for i in p.vertices:h.update(struct.pack("<I",i))
 return h.hexdigest()
def uv_hash(o):
 h=hashlib.sha256()
 for layer in o.data.uv_layers:
  h.update(layer.name.encode("utf-8"))
  for loop in layer.data:h.update(struct.pack("<2f",*loop.uv))
 return h.hexdigest()
def stats(o):
 return {"object":o.name,"source_id":o.get("outrun_original_mesh_object_id"),
         "pmt_sha":o.get("outrun_original_game_resource_sha256"),
         "vertices":len(o.data.vertices),"faces":len(o.data.polygons),
         "mesh_sha256":mesh_hash(o),"uv_sha256":uv_hash(o),
         "matrix":[round(v,9) for row in o.matrix_world for v in row],
         "materials":[x.name if x else None for x in o.data.materials],
         "uv_layers":[x.name for x in o.data.uv_layers]}
def meshes():
 return {o.name:stats(o) for o in bpy.data.objects if o.type=="MESH"}
def cam_state():
 return {o.name:{"matrix":[round(v,9) for row in o.matrix_world for v in row],
       "lens":round(o.data.lens,9),"ortho_scale":round(o.data.ortho_scale,9),
       "type":o.data.type} for o in bpy.data.objects if o.type=="CAMERA"}
def boundary_loop_stats(o):
 b=bmesh.new();b.from_mesh(o.data)
 bad=[e for e in b.edges if not e.is_manifold]
 assert len(bad)==624 and all(len(e.link_faces)==1 for e in bad),("OPEN_EDGE_CONTRACT",len(bad))
 edges={};ids=set()
 for e in bad:
  a,c=e.verts[0].index,e.verts[1].index
  ids.update((a,c));edges.setdefault(a,set()).add(c);edges.setdefault(c,set()).add(a)
 assert len(ids)==624 and all(len(v)==2 for v in edges.values())
 visited=set();sizes=[]
 for a in ids:
  if a in visited:continue
  stack=[a];visited.add(a);n=0
  while stack:
   i=stack.pop();n+=1
   for j in edges[i]:
    if j not in visited:visited.add(j);stack.append(j)
  sizes.append(n)
 b.free()
 assert sorted(sizes)==[48,48,72,72,72,96,96,120],sizes
 return ids,sorted(sizes)

def sculpt_hood(o,pts,normals):
 """F50 native dashboard upper instrument cover: smooth existing hood shoulders.
 Preserve XY and silhouette, preserve low-facing gauge/rear surfaces."""
 kd=kd_tree(pts);out={}
 xmin=min(q.x for q in pts);xmax=max(q.x for q in pts)
 ymin=min(q.y for q in pts);ymax=max(q.y for q in pts)
 for i,p in enumerate(pts):
  ux=(p.x-xmin)/(xmax-xmin)
  shoulder=max(gauss(ux-.20,.21),gauss(ux-.80,.21))
  mask=shoulder*smooth((ux-.045)/.105)*smooth((.955-ux)/.105)
  mask*=smooth((p.y-ymin-.040)/.050)*smooth((ymax-p.y-.009)/.032)
  if mask<.055 or normals[i].z<.61:continue
  target=weight=0.
  for q,j,dd in kd.find_range(p,.024):
   if i==j or abs(q.y-p.y)>.012 or abs(q.z-p.z)>.008:continue
   dot=normals[i].dot(normals[j])
   if dot<.91:continue
   w=gauss(math.hypot(q.x-p.x,q.y-p.y),.008)*dot**7
   target+=w*q.z;weight+=w
  if weight<.10:continue
  dz=clamp((target/weight-p.z)*1.28*mask,.00086)
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>125,("BLOCKED_NO_NATIVE_HOOD",len(out))
 return out

def sculpt_wheel(o,pts,normals):
 """Photo matched F50 three-spoke metal sheet and LOWER leather rim fairing.
 The eight original source openings and upper rim remain untouched.
 No artificial rim rod/primitive, no invented holes, no wheel replacement."""
 protected,loops=boundary_loop_stats(o)
 edge_kd=kd_tree([pts[i] for i in sorted(protected)])
 kd=kd_tree(pts)
 out={}
 for i,p in enumerate(pts):
  if i in protected:continue
  r=math.hypot(p.x,p.y)
  if r<.084:continue
  a=math.atan2(p.y,p.x)
  spoke_gap=min(abs(math.atan2(math.sin(a-t),math.cos(a-t))) for t in (0.,math.pi,-math.pi/2))
  _,_,edge_dist=edge_kd.find(p)
  fence=smooth((edge_dist-.00065)/.0050)
  if fence<.025:continue
  target_z=target_r=weight=0.
  for q,j,dd in kd.find_range(p,.021):
   if i==j or abs(q.z-p.z)>.009:continue
   dot=normals[i].dot(normals[j])
   if dot<.90:continue
   dxy=math.hypot(q.x-p.x,q.y-p.y)
   if dxy>.018:continue
   w=gauss(dxy,.0075)*dot**7
   target_z+=w*q.z;target_r+=w*math.hypot(q.x,q.y);weight+=w
  if weight<.12:continue
  dz=dr=0.
  # Flat, continuous photographed F50 three-spoke sheet.
  if .087<r<.150 and spoke_gap<.49 and normals[i].z>.58:
   mask=fence*smooth((r-.089)/.011)*smooth((.150-r)/.012)
   mask*=smooth((.50-spoke_gap)/.25)
   dz=clamp((target_z/weight-p.z)*1.32*mask,.00140)
  # Correction only on bottom leather grip arc. Prior v33 upper-ring fairing
  # was visually rejected for scar artifacts: deliberately leave upper half.
  if .150<r<.173 and p.y<-.038 and spoke_gap>.19 and normals[i].z>.10:
   arc=smooth((-p.y-.035)/.055)
   mask=fence*arc*smooth((r-.151)/.010)*smooth((.174-r)/.008)
   mask*=smooth((spoke_gap-.17)/.18)
   dr=clamp((target_r/weight-r)*.64*mask,.00055)
   dz+=clamp((target_z/weight-p.z)*.48*mask,.00048)
  if abs(dz)>1e-7 or abs(dr)>1e-7:
   out[i]=(p.x/r*dr,p.y/r*dr,dz)
 assert len(out)>300,("BLOCKED_NO_NATIVE_3SPOKE",len(out))
 return out

def sculpt_hub(o,pts,normals):
 """Genuine F50 6-bolt metal center plate: localized surface fairing.
 Preserve source badge, six bolt islands and original hub outline."""
 kd=kd_tree(pts);out={}
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
        for a in (30,90,150,210,270,330)]
 for i,p in enumerate(pts):
  r=math.hypot(p.x,p.y+.019)
  if not (.027<r<.079) or normals[i].z<.63:continue
  bolt_sep=min(math.hypot(p.x-x,p.y-y) for x,y in bolts)
  mask=smooth((r-.027)/.012)*smooth((.079-r)/.015)*smooth((bolt_sep-.008)/.011)
  if mask<.05:continue
  total=weight=0.
  for q,j,dd in kd.find_range(p,.021):
   if i==j or abs(q.z-p.z)>.009:continue
   dot=normals[i].dot(normals[j])
   if dot<.90:continue
   w=gauss(math.hypot(q.x-p.x,q.y-p.y),.007)*dot**7
   total+=w*q.z;weight+=w
  if weight<.10:continue
  dz=clamp((total/weight-p.z)*1.55*mask,.00125)
  # Tiny convex crown on the original metal plate without touching medallion.
  dz+=.00012*mask
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>80,("BLOCKED_NO_NATIVE_HUB",len(out))
 return out

def verify_input(a,blender_check=True):
 if blender_check:assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 for p,h in ((a.native,PMT_SHA),(a.original_import,IMPORT_SHA),(a.before,PARENT_SHA)):
  assert p.is_file() and sha(p)==h,("BLOCKED_INPUT",str(p))
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert bpy.context.scene.get("geometry_edit_count") in (99,102)
 for o in (D,W,H):
  assert o in bpy.data.objects
  assert bpy.data.objects[o].get("outrun_original_game_resource_sha256")==PMT_SHA
 assert len(meshes())==42
def apply(name,func):
 o=bpy.data.objects[name];m=o.data
 before=[v.co.copy() for v in m.vertices]
 normals=[v.normal.copy() for v in m.vertices]
 protected=None
 if name==W:
  ids,_=boundary_loop_stats(o)
  protected={i:before[i].copy() for i in ids}
 edits=func(o,before,normals)
 for i,(x,y,z) in edits.items():
  v=m.vertices[i];v.co.x+=x;v.co.y+=y;v.co.z+=z
 m.update()
 if protected:assert all((m.vertices[i].co-p).length<1e-10 for i,p in protected.items())
 distances=[(before[i]-v.co).length for i,v in enumerate(m.vertices)]
 moved=sum(x>1e-6 for x in distances);mx=max(distances)
 assert moved>80 and .00002<mx<.002,(name,moved,mx)
 o["source_edit_scope"]="F50 slot C v34 verified original PMT native gauge hood, three-spoke sheet and lower leather rim, six-bolt hub; source holes preserved"
 return {"moved":moved,"max_mm":round(mx*1000,6)}

def compare(base,after,cameras):
 assert set(base)==set(after) and len(base)==42
 for name,b in base.items():
  t=after[name]
  assert b["source_id"]==t["source_id"] and b["pmt_sha"]==t["pmt_sha"]==PMT_SHA
  assert b["source_id"] and b["vertices"]==t["vertices"] and b["faces"]==t["faces"]
  for f in ("matrix","materials","uv_layers","uv_sha256"):assert b[f]==t[f],(name,f)
  if name in TARGETS:
   assert (b["vertices"],b["faces"])==TARGETS[name],name
   assert b["mesh_sha256"]!=t["mesh_sha256"],name
  else:assert b==t,("FORBIDDEN_OTHER_MESH_CHANGED",name)
 assert sum(base[n]["mesh_sha256"]==after[n]["mesh_sha256"] for n in base)==39
 assert cam_state()==cameras
 assert boundary_loop_stats(bpy.data.objects[W])[1]==[48,48,72,72,72,96,96,120]

def render_view(a,stage,label):
 scene=bpy.context.scene
 cam=scene.camera
 engine=scene.render.engine
 oldx,oldy,oldpct=scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage
 oldpath=scene.render.filepath
 oldtransparent=scene.render.film_transparent
 oldformat=scene.render.image_settings.file_format
 vis={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 try:
  scene.camera=bpy.data.objects[CAMERAS[label]]
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in ((D,) if label=="GAUGE" else (W,H))
  scene.render.engine="BLENDER_WORKBENCH"
  scene.render.resolution_x=720;scene.render.resolution_y=480;scene.render.resolution_percentage=100
  scene.render.film_transparent=False
  scene.render.image_settings.file_format="PNG"
  out=Path(str(a.render_root)+"_"+stage+"_"+label+".png")
  scene.render.filepath=str(out)
  bpy.ops.render.render(write_still=True)
  assert out.is_file()
  return sha(out)
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=vis[o.name]
  scene.camera=cam;scene.render.engine=engine
  scene.render.resolution_x=oldx;scene.render.resolution_y=oldy;scene.render.resolution_percentage=oldpct
  scene.render.filepath=oldpath;scene.render.film_transparent=oldtransparent
  scene.render.image_settings.file_format=oldformat

def build(a):
 verify_input(a)
 assert Path(bpy.data.filepath).resolve()==a.before.resolve()
 assert bpy.context.scene["geometry_edit_count"]==99
 assert not any(p.exists() for p in (a.after,a.report,a.audit))
 base=meshes();cameras=cam_state()
 before={label:render_view(a,"BEFORE",label) for label in CAMERAS}
 updates={k:apply(k,f) for k,f in ((D,sculpt_hood),(W,sculpt_wheel),(H,sculpt_hub))}
 after=meshes()
 compare(base,after,cameras)
 bpy.context.scene["geometry_edit_count"]=102
 bpy.context.scene["slot_c_input_blend_sha256"]=PARENT_SHA
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V34_ORIGINAL_NATIVE_P0_SPOKE_HUB_COWL"
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 assert sha(a.before)==PARENT_SHA
 after_r={label:render_view(a,"AFTER",label) for label in CAMERAS}
 doc={"status":"SAVED_REAL_F50_V34_FRESH_PROCESS_PENDING","blender":bpy.app.version_string,
      "original_pmt_sha256":PMT_SHA,"first_native_import_sha256":IMPORT_SHA,
      "immutable_parent_v33_r2_sha256":PARENT_SHA,"private_output_sha256":sha(a.after),
      "private_output_bytes":a.after.stat().st_size,
      "source_object_ids":[base[n]["source_id"] for n in (D,W,H)],
      "modified_source_meshes":{n:{"before":base[n],"after":after[n],**updates[n]} for n in TARGETS},
      "other_original_meshes_unchanged":39,"original_wheel_open_edges":624,
      "original_open_loop_sizes":[48,48,72,72,72,96,96,120],
      "source_cameras_unchanged":True,
      "compare_render_sha256":{"before":before,"after":after_r},
      "game_driver_eye":"UNVERIFIED","seven_exact_photo_views":"INCOMPLETE",
      "hosted_real_private_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
      "car_complete":False,"score_delta":0,"no_PMT_OVC_OVC3_export":True}
 a.report.write_text(json.dumps(doc,indent=2,ensure_ascii=False),encoding="utf-8")
 print("F50_V34_PRIVATE_SOURCE_SAVE "+json.dumps({"output_sha256":doc["private_output_sha256"],"moved":updates},ensure_ascii=False),flush=True)

def audit(a):
 verify_input(a)
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert a.report.is_file()
 doc=json.loads(a.report.read_text(encoding="utf-8"))
 assert sha(a.after)==doc["private_output_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==102
 final=meshes();cameras=cam_state()
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 orig=meshes();assert cam_state()==cameras
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 compare(orig,meshes(),cameras)
 assert meshes()==final
 audit_render=render_view(a,"INDEPENDENT","STEERING")
 out={"status":"PASS_F50_V34_4_5_15_FRESH_PROCESS_SOURCE_REOPEN_RENDER",
      "original_pmt_sha256":sha(a.native),"first_import_sha256":sha(a.original_import),
      "parent_v33_r2_sha256":sha(a.before),"output_v34_sha256":sha(a.after),
      "independent_render_sha256":audit_render,"other_source_meshes_unchanged":39,
      "open_steering_edges":624,"game_driver_eye":"UNVERIFIED","photo_seven_views":"INCOMPLETE",
      "github_hosted_original_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
      "car_complete":False,"score_delta":0}
 assert not a.audit.exists()
 a.audit.write_text(json.dumps(out,indent=2),encoding="utf8")
 print(out["status"]+" "+out["output_v34_sha256"],flush=True)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--mode",choices=("build","audit"),required=True)
 for n in ("native","original-import","before","after","report","audit","render-root"):
  ap.add_argument("--"+n,required=True,type=Path)
 a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
 if a.mode=="build":build(a)
 else:audit(a)
if __name__=="__main__":main()
#!/usr/bin/env python3
"""Ferrari F50 slot C v30: continue exact original game PMT-derived Blender mesh.

Read-only original compressed Ferrari F50 PMT + first verified PMT import +
immutable v29 .blend require exact SHA256 before modifying. Existing P0 dash,
original steering wheel and original hub vertices only; no new mesh, material,
texture, export or other car. Source diagnostics are non-game camera views.
"""
import argparse, bmesh, bpy, hashlib, importlib.util, json, math, sys
from pathlib import Path
from mathutils import kdtree
HELPER=Path(__file__).with_name("f50_p0_source_mesh_v29.py")
spec=importlib.util.spec_from_file_location("f50_v29_source_helpers",str(HELPER))
prev=importlib.util.module_from_spec(spec)
spec.loader.exec_module(prev)
old=prev.old
PMT=prev.PMT; IMPORT=prev.IMPORT
SOURCE="44e33004a37a8a6ef2729e1680cda4f013d56559334987fcdd2978c2423b0c4e"
D=prev.D; W=prev.W; HUB=prev.HUB
TARGETS={
 D:(5506,7552,"0d269c730df489e26bc6d6f6243a912d5daa1ce0f203019528e48f05d87468ec"),
 W:(13552,26496,"cf27f11b8ce8bb7b814a16d894a6922402a6cccdcb142f4360c4079cc9766ffc"),
 HUB:(2738,4464,"bcf5e7567b2e03e06f48dfde9de01fe56ca45e8eed47b422fd4cbe4b3f14d29f")
}
def source_guard(a):
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 for path,sha in ((a.native,PMT),(a.original_import,IMPORT),(a.before,SOURCE)):
  assert path.is_file() and old.digest(path)==sha,("BLOCKED_INPUT_SHA",str(path))
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
def smooth(t):
 t=max(0.,min(1.,t));return t*t*(3-2*t)
def gaussian(x,width):
 return math.exp(-.5*(x/width)**2)
def process(name,fn):
 o=bpy.data.objects[name];m=o.data
 start=[v.co.copy() for v in m.vertices]
 normals=[v.normal.copy() for v in m.vertices]
 changes=fn(o,start,normals)
 for i,(dx,dy,dz) in changes.items():
  v=m.vertices[i];v.co.x+=dx;v.co.y+=dy;v.co.z+=dz
 m.update()
 lengths=[(start[i]-v.co).length for i,v in enumerate(m.vertices)]
 moved=sum(x>1e-6 for x in lengths);mx=max(lengths)
 assert moved>110 and 0.00004<mx<=0.00321,(name,moved,mx)
 o["source_edit_scope"]="F50 slot C v30 native source cowl, spoke, rim and six-bolt hub contour"
 return {"moved_vertices":moved,"max_move_mm":round(mx*1000,6)}
def cowl_rework(o,pts,normals):
 # F50 original instrument cowl, not a recreated/dashboard replacement:
 # attenuate imported surface ridges around the upper asymmetric arch while
 # keeping source lower edge, local normals and shell bounds unchanged.
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts): kd.insert(p,i)
 kd.balance()
 xmin=min(p.x for p in pts);xmax=max(p.x for p in pts)
 ymin=min(p.y for p in pts);ymax=max(p.y for p in pts)
 out={}
 for i,p in enumerate(pts):
  ux=(p.x-xmin)/(xmax-xmin)
  edge=smooth((ux-.042)/.084)*smooth((.958-ux)/.084)
  arch=max(gaussian(ux-.17,.175),gaussian(ux-.83,.175))
  yband=smooth((p.y-ymin-.057)/.040)*smooth((ymax-p.y-.002)/.030)
  n=normals[i]
  mask=edge*arch*yband
  if mask<.025 or n.z<.49:continue
  total=weight=0.
  for q,j,dist in kd.find_range(p,.027):
   if i==j or abs(q.y-p.y)>.018 or abs(q.z-p.z)>.009:continue
   dot=n.dot(normals[j])
   if dot<.86:continue
   dx=q.x-p.x;dy=q.y-p.y
   w=gaussian(math.hypot(dx,dy),.009)*dot**6
   total+=w*q.z;weight+=w
  if weight<.15:continue
  dz=max(-.00145,min(.00145,(total/weight-p.z)*1.12*mask))
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>150,("BLOCKED_INPUT_NATIVE_COWL",len(out))
 return out
def wheel_rework(o,pts,normals):
 # Existing PMT three-spoke rim: smooth the raised upper shoulder and hard
 # spoke-to-grip face transitions. Boundary loops remain stationary to avoid
 # synthetic welded bars/bridges or closing source through-holes.
 b=bmesh.new();b.from_mesh(o.data)
 boundary={v.index for e in b.edges if not e.is_manifold for v in e.verts}
 b.free()
 assert len(boundary)>100
 edges=kdtree.KDTree(len(boundary))
 for j,i in enumerate(sorted(boundary)):edges.insert(pts[i],j)
 edges.balance()
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 out={}
 for i,p in enumerate(pts):
  if i in boundary:continue
  r=math.hypot(p.x,p.y)
  if r<.086:continue
  ang=math.atan2(p.y,p.x)
  _,_,edge_dist=edges.find(p)
  protect=smooth((edge_dist-.001)/.0065)
  if protect<.025:continue
  dr=0.;dz=0.
  if r>.138 and p.y>.010:
   shoulder=max(gaussian(ang-math.radians(44),math.radians(17)),
                gaussian(ang-math.radians(136),math.radians(17)))
   crown=smooth((r-.140)/.015)*smooth((.175-r)/.004)
   dr=-.00115*shoulder*crown*protect
  # Three original pressed spoke junctions on the native source wheel.
  spoke_dirs=(0.,math.pi,-math.pi/2)
  aerr=min(abs(math.atan2(math.sin(ang-a),math.cos(ang-a))) for a in spoke_dirs)
  if .089<r<.153 and aerr<.46 and normals[i].z>.58:
   radial=smooth((r-.091)/.019)*smooth((.155-r)/.020)
   shaped=smooth((.47-aerr)/.26)*radial*protect
   if shaped>.025:
    total=weight=0.
    for q,j,dist in kd.find_range(p,.015):
     if i==j or abs(q.z-p.z)>.007:continue
     dot=normals[i].dot(normals[j])
     if dot<.88:continue
     dx=q.x-p.x;dy=q.y-p.y
     ww=gaussian(math.hypot(dx,dy),.0068)*dot**6
     total+=ww*q.z;weight+=ww
    if weight>.11:
     dz=max(-.00145,min(.00145,(total/weight-p.z)*1.0*shaped))
  if abs(dr)>1e-7 or abs(dz)>1e-7:
   out[i]=(dr*p.x/r,dr*p.y/r,dz)
 assert len(out)>145,("BLOCKED_INPUT_NATIVE_WHEEL",len(out))
 return out
def hub_rework(o,pts,normals):
 # Real F50 centre plate is a smooth pressure-formed panel with six distinct
 # fasteners; preserve their original positions plus original Ferrari medallion.
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 bolt_xy=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
          for a in (30,90,150,210,270,330)]
 out={}
 for i,p in enumerate(pts):
  radius=math.hypot(p.x,p.y+.019)
  if not .028<radius<.068 or normals[i].z<.74:continue
  bolt_gap=min(math.hypot(p.x-x,p.y-y) for x,y in bolt_xy)
  mask=smooth((radius-.029)/.010)*smooth((.069-radius)/.011)
  mask*=smooth((bolt_gap-.009)/.013)
  if mask<.032:continue
  total=weight=0.
  for q,j,dist in kd.find_range(p,.019):
   if i==j or abs(q.z-p.z)>.007:continue
   dot=normals[i].dot(normals[j])
   if dot<.87:continue
   dx=q.x-p.x;dy=q.y-p.y
   ww=gaussian(math.hypot(dx,dy),.0078)*dot**5
   total+=ww*q.z;weight+=ww
  if weight<.115:continue
  dz=max(-.00092,min(.00092,(total/weight-p.z)*1.07*mask))
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>80,("BLOCKED_INPUT_NATIVE_HUB",len(out))
 return out
def compare_guard(b,c):
 assert len(b)==len(c)==42 and set(b)==set(c)
 for name,x in b.items():
  y=c[name]
  for k in ("original_id","pmt","vertices","faces","nonmanifold","uv_layers","materials","matrix"):
   assert x[k]==y[k],(name,k)
  assert x["original_id"] and x["pmt"]==PMT
  if name in TARGETS:assert x["sha256"]!=y["sha256"],name
  else:assert x==y,("NON_F50_P0_CHANGED",name)
 assert c[W]["nonmanifold"]==b[W]["nonmanifold"]==624
 assert sum(b[n]["sha256"]==c[n]["sha256"] for n in b)==39
def renders(a,phase):
 d={}
 for tag,(cam,names) in old.VIEWS.items():
  p=Path(str(a.render_root)+"_"+phase+"_"+tag+".png")
  old.render(p,cam,names);d[tag]=old.digest(p)
 return d
def build(a):
 source_guard(a)
 assert Path(bpy.data.filepath).resolve()==a.before.resolve()
 assert bpy.context.scene.get("geometry_edit_count")==87
 assert not any(p.exists() for p in (a.after,a.report,a.audit))
 b=old.snap();cams=old.cameras()
 for name,(nv,nf,sha) in TARGETS.items():
  x=b[name];assert (x["vertices"],x["faces"],x["sha256"])==(nv,nf,sha),(name,x)
 pre=renders(a,"BEFORE")
 changed={}
 for name,fun in ((D,cowl_rework),(W,wheel_rework),(HUB,hub_rework)):
  changed[name]=process(name,fun)
 c=old.snap();compare_guard(b,c);assert old.cameras()==cams
 bpy.context.scene["geometry_edit_count"]=90
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V30_NATIVE_COWL_ARCH_AND_THREE_SPOKE_JUNCTION_SMOOTHING"
 bpy.context.scene["slot_c_input_blend_sha256"]=SOURCE
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 post=renders(a,"AFTER")
 source_guard(a)
 r=dict(status="F50_V30_PRIVATE_SAVE_INDEPENDENT_REOPEN_PENDING",
   native_source_pmt_sha256=PMT,verified_first_import_sha256=IMPORT,
   source_v29_blend_sha256=SOURCE,new_v30_blend_sha256=old.digest(a.after),
   original_meshes_total=42,other_original_meshes_unchanged=39,
   edited_original_meshes={n:{"before":b[n],"after":c[n],**changed[n]} for n in TARGETS},
   original_wheel_nonmanifold_edges=624,
   render_sha256={"before":pre,"after":post},
   calibrated_game_eye="UNVERIFIED",seven_photo_QA="INCOMPLETE",
   hosted_original_game_scene="BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
   source_game_assets_unchanged=True,other_slots_unchanged=True,no_export=True,
   texture_material_changes=False,vehicle_complete=False,score_delta=0)
 a.report.write_text(json.dumps(r,indent=2),encoding="utf8")
 print("F50_SLOT_C_V30_SAVED",r["new_v30_blend_sha256"],changed,flush=True)
def audit(a):
 source_guard(a)
 r=json.loads(a.report.read_text())
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert old.digest(a.after)==r["new_v30_blend_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==90
 c=old.snap();cams=old.cameras()
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 b=old.snap();compare_guard(b,c);assert old.cameras()==cams
 for n,x in r["edited_original_meshes"].items():
  assert b[n]==x["before"] and c[n]==x["after"]
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert old.snap()==c and old.cameras()==cams
 assert not a.audit.exists()
 path=Path(str(a.render_root)+"_FRESH_REOPEN_WHEEL.png")
 old.render(path,*old.VIEWS["STEERING"])
 q=dict(status="PASS_PRIVATE_F50_V30_ORIGINAL_GAME_BLENDER_4_5_15_FRESH_REOPEN_RENDER",
   native_source_sha256=old.digest(a.native),original_import_sha256=old.digest(a.original_import),
   previous_scene_sha256=old.digest(a.before),new_scene_sha256=old.digest(a.after),
   independently_rendered_wheel_sha256=old.digest(path),
   original_meshes_unchanged=39,edited_meshes=3,nonmanifold_steering_edges=624,
   calibrated_game_eye="UNVERIFIED",seven_photo_QA="INCOMPLETE",
   hosted_real_scene="BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",score_delta=0)
 a.audit.write_text(json.dumps(q,indent=2),encoding="utf8")
 print(q["status"],q["new_scene_sha256"],flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--mode",choices=("build","audit"),required=True)
 for k in ("native","original-import","before","after","report","audit","render-root"):
  p.add_argument("--"+k,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if a.mode=="build":build(a)
 else:audit(a)
if __name__=="__main__":main()
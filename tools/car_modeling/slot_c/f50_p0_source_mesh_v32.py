#!/usr/bin/env python3
"""F50 slot C v32: original OutRun 2006 PMT in-place cockpit contour fairing.
Exact source PMT/import/v31-r2 hash required. Modify existing instrument hood,
three-spoke wheel rim and six-bolt hub vertices only; no new objects, exports,
textures/PBR, outside body, or game/runtime modifications.
"""
import argparse,bpy,bmesh,hashlib,importlib.util,json,math,sys
from pathlib import Path
from mathutils import kdtree
P=Path(__file__).with_name("f50_p0_source_mesh_v31_r2.py")
spec=importlib.util.spec_from_file_location("f50_source_v31_r2",str(P))
v31=importlib.util.module_from_spec(spec);spec.loader.exec_module(v31)
old=v31.old
PMT=v31.PMT;IMPORT=v31.IMPORT
SOURCE="b0d70a7a984098ede5be9494e62a227aa989fe4ccacd6cdd0b9f013cbfa15814"
D=v31.D;W=v31.W;H=v31.HUB
TARGET={
 D:(5506,7552,"0b7fcfb54288fb1e577fc872c6fe1f315fa340cb2d237547c00f177b824c141c"),
 W:(13552,26496,"12145eaf2b444b504047c0b632436ac54b562d2b682e37db128f9269b79d9200"),
 H:(2738,4464,"b15e7e8756a3f9bf174e4945897ed343f9f51ad942a2dcaa839d72b3f0b33b68")
}
def s(x):
 x=max(0.,min(1.,x));return x*x*(3-2*x)
def g(x,sigma):return math.exp(-.5*(x/sigma)**2)
def kd_make(pts):
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance();return kd
def instrument(o,pts,normals):
 """Local real PMT hood shoulder surface smoothing; preserve XY silhouette."""
 kd=kd_make(pts);xmin=min(p.x for p in pts);xmax=max(p.x for p in pts)
 ymin=min(p.y for p in pts);ymax=max(p.y for p in pts)
 out={}
 for i,p in enumerate(pts):
  t=(p.x-xmin)/(xmax-xmin)
  side=s((t-.037)/.09)*s((.963-t)/.09)
  front=s((p.y-ymin-.035)/.042)
  back=s((ymax-p.y-.002)/.025)
  shoulder=max(g(t-.16,.19),g(t-.84,.19))
  mask=side*front*back*shoulder
  if mask<.04 or normals[i].z<.52:continue
  total=weight=0.
  for q,j,dist in kd.find_range(p,.026):
   if i==j or abs(q.y-p.y)>.014 or abs(q.z-p.z)>.009:continue
   nd=normals[i].dot(normals[j])
   if nd<.88:continue
   d=math.hypot(q.x-p.x,q.y-p.y)
   wt=g(d,.009)*nd**5
   total+=wt*q.z;weight+=wt
  if weight<.10:continue
  dz=max(-.00120,min(.00120,(total/weight-p.z)*1.18*mask))
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>130,("BLOCKED_NATIVE_HOOD",len(out))
 return out
def steering(o,pts,normals):
 """Fair source ring circularity and top two handgrip shoulders in place,
 protecting all existing open edges and original three spoke-root segments."""
 kd=kd_make(pts)
 bm=bmesh.new();bm.from_mesh(o.data)
 boundary={v.index for e in bm.edges if not e.is_manifold for v in e.verts}
 bm.free()
 assert len(boundary)>100
 edge_kd=kdtree.KDTree(len(boundary))
 for j,i in enumerate(sorted(boundary)):edge_kd.insert(pts[i],j)
 edge_kd.balance()
 radii=[math.hypot(p.x,p.y) for p in pts]
 out={}
 for i,p in enumerate(pts):
  if i in boundary:continue
  r=radii[i]
  if not (.147<r<.177):continue
  ang=math.atan2(p.y,p.x)
  near_spoke=min(abs(math.atan2(math.sin(ang-a),math.cos(ang-a)))
                 for a in (0,math.pi,-math.pi/2))
  guard=s((near_spoke-.07)/.24)
  _,_,dist=edge_kd.find(p)
  guard*=s((dist-.0008)/.006)
  if guard<.020:continue
  rs=zs=weight=0.
  for q,j,dd in kd.find_range(p,.023):
   if i==j or abs(q.z-p.z)>.008:continue
   nd=normals[i].dot(normals[j])
   if nd<.83:continue
   rq=radii[j]
   if abs(rq-r)>.014:continue
   da=abs(math.atan2(math.sin(math.atan2(q.y,q.x)-ang),math.cos(math.atan2(q.y,q.x)-ang)))
   if da>.22:continue
   w=g(dd,.009)*nd**5
   rs+=w*rq;zs+=w*q.z;weight+=w
  if weight<.4:continue
  dr=max(-.00135,min(.00135,(rs/weight-r)*.92*guard))
  dz=max(-.00065,min(.00065,(zs/weight-p.z)*.5*guard))
  # Thin photo-guided 10/2-o'clock palm-area contour, no new grips.
  hand=max(g(ang-math.radians(58),.25),g(ang-math.radians(122),.25))
  dr+=.00032*hand*guard*s((r-.149)/.014)
  if abs(dr)>1e-7 or abs(dz)>1e-7:
   out[i]=(p.x/r*dr,p.y/r*dr,dz)
 assert len(out)>450,("BLOCKED_NATIVE_WHEEL",len(out))
 return out
def hub(o,pts,normals):
 """Calm original metal spoke plate ridges, keep genuine source bolt islands
 and original center badge untouched. No detached replacement steering hub."""
 kd=kd_make(pts);out={}
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
        for a in (30,90,150,210,270,330)]
 for i,p in enumerate(pts):
  r=math.hypot(p.x,p.y+.019)
  if not (.026<r<.078) or normals[i].z<.55:continue
  mask=s((r-.026)/.011)*s((.078-r)/.013)
  db=min(math.hypot(p.x-x,p.y-y) for x,y in bolts)
  mask*=s((db-.008)/.012)
  if mask<.04:continue
  total=weight=0.
  for q,j,dd in kd.find_range(p,.025):
   if i==j or abs(q.z-p.z)>.011:continue
   nd=normals[i].dot(normals[j])
   if nd<.82:continue
   xy=math.hypot(q.x-p.x,q.y-p.y)
   if xy>.020:continue
   wt=g(xy,.008)*nd**6
   total+=wt*q.z;weight+=wt
  if weight<.08:continue
  dz=max(-.0019,min(.0019,(total/weight-p.z)*1.35*mask))
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>70,("BLOCKED_NATIVE_HUB",len(out))
 return out
def source_guard(a):
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 for f,sha in ((a.native,PMT),(a.original_import,IMPORT),(a.before,SOURCE)):
  assert f.is_file() and old.digest(f)==sha,("BLOCKED_INPUT",str(f))
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
def snapshot_guard(before,after):
 assert len(before)==len(after)==42 and set(before)==set(after)
 for name,b in before.items():
  a=after[name]
  for k in ("original_id","pmt","vertices","faces","nonmanifold","uv_layers","materials","matrix"):
   assert b[k]==a[k],(name,k)
  assert b["pmt"]==a["pmt"]==PMT and b["original_id"]
  if name in TARGET:assert b["sha256"]!=a["sha256"],name
  else:assert a==b,("UNRELATED_SOURCE_MESH_EDIT",name)
 assert sum(before[n]["sha256"]==after[n]["sha256"] for n in before)==39
 assert after[W]["nonmanifold"]==before[W]["nonmanifold"]==624
def process(name,fn):
 o=bpy.data.objects[name];m=o.data
 orig=[v.co.copy() for v in m.vertices]
 normals=[v.normal.copy() for v in m.vertices]
 changes=fn(o,orig,normals)
 for i,(dx,dy,dz) in changes.items():
  v=m.vertices[i];v.co.x+=dx;v.co.y+=dy;v.co.z+=dz
 m.update()
 distances=[(orig[i]-v.co).length for i,v in enumerate(m.vertices)]
 moved=sum(v>1e-6 for v in distances);mx=max(distances)
 assert moved>70 and .00003<mx<=.0021,(name,moved,mx)
 o["source_edit_scope"]="F50 slot C v32: true original wheel circular rim and hub face, original gauge hood surface fairing"
 return {"moved":moved,"maximum_mm":round(mx*1000,6)}
def render_pair(a,phase):
 data={}
 for label,(camera,vis) in old.VIEWS.items():
  path=Path(str(a.render_root)+"_"+phase+"_"+label+".png")
  old.render(path,camera,vis);data[label]=old.digest(path)
 return data
def build(a):
 source_guard(a)
 assert Path(bpy.data.filepath).resolve()==a.before.resolve()
 assert bpy.context.scene.get("geometry_edit_count")==93
 assert not any(p.exists() for p in (a.after,a.report,a.audit))
 b=old.snap();cameras=old.cameras()
 for n,(nv,nf,sha) in TARGET.items():
  r=b[n];assert (r["vertices"],r["faces"],r["sha256"])==(nv,nf,sha),(n,r)
 pre=render_pair(a,"BEFORE")
 changes={n:process(n,fn) for n,fn in ((D,instrument),(W,steering),(H,hub))}
 after=old.snap();snapshot_guard(b,after);assert cameras==old.cameras()
 bpy.context.scene["geometry_edit_count"]=96
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V32_ORIGINAL_PMT_P0_GAUGE_RING_HUB_SURFACE"
 bpy.context.scene["slot_c_input_blend_sha256"]=SOURCE
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 post=render_pair(a,"AFTER")
 source_guard(a)
 record={"state":"PRIVATE_SAVED_REOPEN_PENDING","blender":bpy.app.version_string,
  "original_pmt_sha256":PMT,"original_import_blend_sha256":IMPORT,
  "source_v31_r2_blend_sha256":SOURCE,"output_blend_sha256":old.digest(a.after),
  "edited_original_objects":{n:{"before":b[n],"after":after[n],**changes[n]} for n in TARGET},
  "untouched_original_mesh_count":39,"total_original_mesh_count":42,
  "original_steering_nonmanifold_edges":624,
  "render_sha256":{"before":pre,"after":post},
  "game_driver_eye":"UNVERIFIED","seven_photo_views":"INCOMPLETE",
  "hosted_private_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "no_new_assets_or_exports":True,"complete":False,"score_delta":0}
 a.report.write_text(json.dumps(record,indent=2),encoding="utf8")
 print("F50_V32_PRIVATE_SAVE",record["output_blend_sha256"],changes,flush=True)
def audit(a):
 source_guard(a)
 r=json.loads(a.report.read_text(encoding="utf8"))
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert old.digest(a.after)==r["output_blend_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==96
 c=old.snap();cameras=old.cameras()
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 b=old.snap();assert old.cameras()==cameras;snapshot_guard(b,c)
 for n,v in r["edited_original_objects"].items():
  assert b[n]==v["before"] and c[n]==v["after"]
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert old.snap()==c and old.cameras()==cameras
 independent=Path(str(a.render_root)+"_FRESH_REOPEN_STEERING.png")
 old.render(independent,*old.VIEWS["STEERING"])
 assert not a.audit.exists()
 rec={"state":"PASS_REAL_F50_V32_BLENDER_4_5_15_FRESH_PROCESS_REOPEN_AND_RENDER",
  "original_pmt_sha256":old.digest(a.native),"original_import_sha256":old.digest(a.original_import),
  "source_blend_sha256":old.digest(a.before),"output_blend_sha256":old.digest(a.after),
  "independent_steering_render_sha256":old.digest(independent),
  "untouched_original_meshes":39,"original_wheel_nonmanifold_edges":624,
  "native_game_eye":"UNVERIFIED","seven_photo_QA":"INCOMPLETE",
  "hosted_original_private_blend":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "car_complete":False,"score_delta":0}
 a.audit.write_text(json.dumps(rec,indent=2),encoding="utf8")
 print(rec["state"],rec["output_blend_sha256"],flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument("--mode",choices=("build","audit"),required=True)
 for n in ("native","original-import","before","after","report","audit","render-root"):
  p.add_argument("--"+n,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if a.mode=="build":build(a)
 else:audit(a)
if __name__=="__main__":main()
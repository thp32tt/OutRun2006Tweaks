#!/usr/bin/env python3
"""F50 Slot C v33_r2-r2: guarded in-place shaping of authentic OutRun 2006 PMT cockpit.
Edit existing source three-spoke ring/spoke sheet, native 6-bolt hub and original
gauge hood. Preserve original open boundary loops, object ids, UVs, cameras,
all remaining 39 meshes, textures, and native PMT file. No OVC/PMT conversion.
"""
import argparse,bpy,bmesh,hashlib,importlib.util,json,math,sys
from pathlib import Path
from mathutils import kdtree
SRC=Path(__file__).with_name("f50_p0_source_mesh_v32.py")
sp=importlib.util.spec_from_file_location("f50_v32_source",str(SRC))
prev=importlib.util.module_from_spec(sp);sp.loader.exec_module(prev)
old=prev.old
PMT=prev.PMT;IMPORT=prev.IMPORT
SOURCE="16e2a9e17d83b8e77dd9c2636aeab8bfb60b19b850926f1641b26947382df193"
D=prev.D;W=prev.W;H=prev.H
EXPECTED={
 D:(5506,7552,"133a00c89864613ba299ab39dd39c2d6dff422af07b551389fc393bd75995436"),
 W:(13552,26496,"d3afbebcd59d994418db21ee4a045b7f718333f0ede5bc7538f2714552741444"),
 H:(2738,4464,"618d3ed1f513b1bed124a5dc684e674ea98f5d3c0d13e5352d617a41df0919a8")
}
def smooth(t):
 t=max(0.,min(1.,t));return t*t*(3-2*t)
def gaussian(x,k):return math.exp(-.5*(x/k)**2)
def tree(pts):
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance();return kd
def steering_boundary(o):
 b=bmesh.new();b.from_mesh(o.data);b.verts.ensure_lookup_table()
 loops={};boundary=set()
 for e in b.edges:
  if not e.is_manifold:
   assert len(e.link_faces)==1,("unexpected interior non-manifold")
   for v in e.verts:boundary.add(v.index);loops.setdefault(v.index,set()).add(e.other_vert(v).index)
 assert len(boundary)==624 and len(loops)==624
 assert all(len(v)==2 for v in loops.values())
 seen=set();sizes=[]
 for start in loops:
  if start in seen:continue
  st=[start];seen.add(start);n=0
  while st:
   i=st.pop();n+=1
   for j in loops[i]:
    if j not in seen:seen.add(j);st.append(j)
  sizes.append(n)
 sizes.sort()
 assert sizes==[48,48,72,72,72,96,96,120],sizes
 b.free()
 return boundary,sizes
def hood(o,pts,normals):
 """Local-photo-backed native instrument-hood shoulder fairness.
 No added visor, no moved XY silhouette, no changed hood upper rim."""
 kd=tree(pts)
 xmin=min(p.x for p in pts);xmax=max(p.x for p in pts)
 ymin=min(p.y for p in pts);ymax=max(p.y for p in pts)
 out={}
 for i,p in enumerate(pts):
  ux=(p.x-xmin)/(xmax-xmin)
  zone=max(gaussian(ux-.19,.20),gaussian(ux-.81,.20))
  zone*=smooth((ux-.045)/.11)*smooth((.955-ux)/.11)
  zone*=smooth((p.y-ymin-.036)/.047)*smooth((ymax-p.y-.006)/.029)
  n=normals[i]
  if zone<.042 or n.z<.61:continue
  weighted=weight=0.
  for q,j,dist in kd.find_range(p,.026):
   if i==j or abs(q.y-p.y)>.014 or abs(q.z-p.z)>.009:continue
   dot=n.dot(normals[j])
   if dot<.89:continue
   dx=(q.x-p.x);dy=(q.y-p.y)
   w=gaussian(math.hypot(dx,dy),.009)*dot**6
   weighted+=w*q.z;weight+=w
  if weight<.12:continue
  dz=max(-.00098,min(.00098,(weighted/weight-p.z)*1.26*zone))
  if abs(dz)>1.e-7:out[i]=(0.,0.,dz)
 assert len(out)>170,("BLOCKED_HOOD_NATIVE_REGION",len(out))
 return out
def rim_spokes(o,pts,normals):
 """Three original spoke sheets: smoother source-face tension and flattened
 authentic plate profile, plus gentle original ring corner arc correction.
 All 8 actual original open loops remain in exact original positions."""
 boundary,sizes=steering_boundary(o)
 kd=tree(pts);edge=tree([pts[i] for i in sorted(boundary)])
 out={}
 for i,p in enumerate(pts):
  if i in boundary:continue
  r=math.hypot(p.x,p.y)
  if r<.082:continue
  ang=math.atan2(p.y,p.x)
  spoke_angle=min(abs(math.atan2(math.sin(ang-a),math.cos(ang-a)))
                    for a in (0.,math.pi,-math.pi/2))
  _,_,distance=edge.find(p)
  protected=smooth((distance-.0007)/.006)
  if protected<.025:continue
  n=normals[i];dz=dr=0.
  # From source photo: original straight, near-planar three-spoke steel/metal
  # plate should be smooth across width, without invented centre insert.
  if .086<r<.150 and spoke_angle<.52 and n.z>.51:
   taper=smooth((r-.087)/.014)*smooth((.151-r)/.016)
   cross=smooth((.52-spoke_angle)/.31)
   mask=taper*cross*protected
   if mask>.025:
    total=weight=0.
    for q,j,dist in kd.find_range(p,.022):
     if i==j or abs(q.z-p.z)>.012:continue
     dot=n.dot(normals[j])
     if dot<.83:continue
     dxy=math.hypot(q.x-p.x,q.y-p.y)
     if dxy>.019:continue
     w=gaussian(dxy,.008)*dot**5
     total+=w*q.z;weight+=w
    if weight>.08:
     dz=max(-.00215,min(.00215,(total/weight-p.z)*1.50*mask))
     # Submillimetre authentic plate centre crown, no new topology.
     dz+=.00020*mask*(1-smooth((spoke_angle-.02)/.22))
  # v33-r2 visual acceptance: retain exact v32 native outer rim surface.
  # Rejected preliminary v33 global radial fairing introduced false top-rim scars.
  # Improve only original spoke sheet and independent hood/hub surfaces.
  if abs(dr)>1e-7 or abs(dz)>1e-7:
   out[i]=(p.x/r*dr,p.y/r*dr,dz)
 assert len(out)>600,("BLOCKED_NATIVE_3SPOKE",len(out))
 return out
def hub_face(o,pts,normals):
 """Native photographed six-bolt centre plate smooth from existing mesh.
 Keeps Ferrari medallion core and bolt-hole islands unmodified."""
 kd=tree(pts);out={}
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
        for a in (30,90,150,210,270,330)]
 for i,p in enumerate(pts):
  radius=math.hypot(p.x,p.y+.019)
  if not (.025<radius<.078) or normals[i].z<.60:continue
  bolt_dist=min(math.hypot(p.x-x,p.y-y) for x,y in bolts)
  mask=smooth((radius-.025)/.013)*smooth((.078-radius)/.013)*smooth((bolt_dist-.008)/.013)
  if mask<.045:continue
  total=weight=0.
  for q,j,dist in kd.find_range(p,.024):
   if i==j or abs(q.z-p.z)>.012:continue
   nd=normals[i].dot(normals[j])
   if nd<.84:continue
   dx=math.hypot(q.x-p.x,q.y-p.y)
   if dx>.020:continue
   ww=gaussian(dx,.008)*nd**5
   total+=ww*q.z;weight+=ww
  if weight<.10:continue
  dz=max(-.0019,min(.0019,(total/weight-p.z)*1.45*mask))
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>70,("BLOCKED_NATIVE_6BOLT_HUB",len(out))
 return out
def input_guard(a):
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 for file,hashval in ((a.native,PMT),(a.original_import,IMPORT),(a.before,SOURCE)):
  assert file.is_file() and old.digest(file)==hashval,("BLOCKED_INPUT",str(file))
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
def snapshot_guard(pre,post):
 assert set(pre)==set(post) and len(pre)==len(post)==42
 for n,v in pre.items():
  a=post[n]
  assert v["original_id"] and v["pmt"]==a["pmt"]==PMT
  for k in ("original_id","pmt","vertices","faces","nonmanifold","uv_layers","materials","matrix"):
   assert v[k]==a[k],(n,k)
  if n in EXPECTED:assert v["sha256"]!=a["sha256"],n
  else:assert v==a,("FORBIDDEN_NON_P0_MESH_MODIFICATION",n)
 assert sum(pre[n]["sha256"]==post[n]["sha256"] for n in pre)==39
 assert pre[W]["nonmanifold"]==post[W]["nonmanifold"]==624
def process(n,fn):
 o=bpy.data.objects[n];mesh=o.data
 start=[v.co.copy() for v in mesh.vertices]
 ns=[v.normal.copy() for v in mesh.vertices]
 protected=None
 if n==W:
  ids,_=steering_boundary(o)
  protected={i:start[i].copy() for i in ids}
 moves=fn(o,start,ns)
 for i,(dx,dy,dz) in moves.items():
  p=mesh.vertices[i].co;p.x+=dx;p.y+=dy;p.z+=dz
 mesh.update()
 if protected:
  assert all((mesh.vertices[i].co-p).length<1e-10 for i,p in protected.items())
 ds=[(start[i]-v.co).length for i,v in enumerate(mesh.vertices)]
 moved=sum(x>1e-6 for x in ds);big=max(ds)
 assert moved>70 and 0.00003<big<=0.00260,(n,moved,big)
 o["source_edit_scope"]="F50 original PMT v33_r2-r2: native dash shoulder and 3-spoke metal plate/rim, six-bolt face without source hole filling"
 return {"moved_vertices":moved,"maximum_displacement_mm":round(big*1000,6)}
def pair(a,tag):
 return {label:render_one(a,tag,label,cam,names) for label,(cam,names) in old.VIEWS.items()}
def render_one(a,tag,label,cam,names):
 file=Path(str(a.render_root)+"_"+tag+"_"+label+".png")
 old.render(file,cam,names)
 return old.digest(file)
def build(a):
 input_guard(a)
 assert Path(bpy.data.filepath).resolve()==a.before.resolve()
 assert bpy.context.scene.get("geometry_edit_count")==96
 assert not any(f.exists() for f in (a.after,a.report,a.audit)),"protected output collision"
 original=old.snap();cameras=old.cameras()
 for n,(nv,nf,h) in EXPECTED.items():
  v=original[n]
  assert (v["vertices"],v["faces"],v["sha256"])==(nv,nf,h),(n,v)
 before_render=pair(a,"BEFORE")
 stats={n:process(n,fn) for n,fn in ((D,hood),(W,rim_spokes),(H,hub_face))}
 changed=old.snap();snapshot_guard(original,changed)
 assert cameras==old.cameras()
 bpy.context.scene["geometry_edit_count"]=99
 bpy.context.scene["slot_c_input_blend_sha256"]=SOURCE
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V33_R2_ORIGINAL_PMT_SPOKE_PLATE_RIM_AND_HOOD"
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 after_render=pair(a,"AFTER")
 input_guard(a)
 doc={
  "status":"PRIVATE_F50_V33_R2_SAVED_FRESH_PROCESS_AUDIT_PENDING",
  "blender":bpy.app.version_string,"original_pmt_sha256":PMT,"original_import_blend_sha256":IMPORT,
  "v32_source_sha256":SOURCE,"v33_r2_blend_sha256":old.digest(a.after),
  "original_geometry_source_mesh_count":42,
  "untouched_other_source_meshes":39,
  "source_steering_open_boundary_loops":[48,48,72,72,72,96,96,120],
  "source_steering_open_boundary_edges":624,
  "changed_original_objects":{n:{"before":original[n],"after":changed[n],**stats[n]} for n in EXPECTED},
  "original_camera_unchanged":True,"no_topology_change":True,"no_exterior_or_texture_change":True,
  "no_new_objects":True,"no_PMT_OVC3_OVC_export_or_game_patches":True,
  "renders":{"before":before_render,"after":after_render},
  "seven_actual_car_photo_views":"INCOMPLETE","actual_game_eye":"UNVERIFIED",
  "hosted_real_private_blend":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "car_complete":False,"score_delta":0}
 a.report.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf8")
 print("F50_V33_R2_SAVED",doc["v33_r2_blend_sha256"],stats,flush=True)
def audit(a):
 input_guard(a)
 rec=json.loads(a.report.read_text(encoding="utf8"))
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert old.digest(a.after)==rec["v33_r2_blend_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==99
 now=old.snap();cams=old.cameras()
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 orig=old.snap();assert old.cameras()==cams;snapshot_guard(orig,now)
 for n,v in rec["changed_original_objects"].items():
  assert orig[n]==v["before"] and now[n]==v["after"],n
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert now==old.snap() and cams==old.cameras()
 bound,loops=steering_boundary(bpy.data.objects[W])
 assert len(bound)==624 and loops==[48,48,72,72,72,96,96,120]
 test=Path(str(a.render_root)+"_FRESH_PROCESS_STEERING.png")
 old.render(test,*old.VIEWS["STEERING"])
 assert not a.audit.exists()
 result={"status":"PASS_NATIVE_F50_V33_R2_BLENDER_4_5_15_FRESH_REOPEN_COMPARE_RENDER",
  "native_game_pmt_sha256":old.digest(a.native),"original_import_blend_sha256":old.digest(a.original_import),
  "parent_v32_sha256":old.digest(a.before),"new_v33_r2_blend_sha256":old.digest(a.after),
  "independent_steering_render_sha256":old.digest(test),
  "original_steering_open_edges":624,"original_open_loop_sizes":loops,
  "source_meshes_untouched":39,"seven_photo_views":"INCOMPLETE","game_driver_eye":"UNVERIFIED",
  "hosted_original_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "vehicle_complete":False,"score_delta":0}
 a.audit.write_text(json.dumps(result,indent=2),encoding="utf8")
 print(result["status"],result["new_v33_r2_blend_sha256"],flush=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",choices=("build","audit"),required=True)
 for name in ("native","original-import","before","after","report","audit","render-root"):
  ap.add_argument("--"+name,required=True,type=Path)
 a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
 if a.mode=="build":build(a)
 else:audit(a)
if __name__=="__main__":main()
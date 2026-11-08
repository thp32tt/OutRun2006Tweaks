#!/usr/bin/env python3
"""Ferrari F50 slot C v31_r2: continue exact original game PMT-derived Blender mesh.

Read-only original compressed Ferrari F50 PMT + first verified PMT import +
immutable v30 .blend require exact SHA256 before modifying. Existing P0 dash,
original steering wheel and original hub vertices only; no new mesh, material,
texture, export or other car. Source diagnostics are non-game camera views.
"""
import argparse, bmesh, bpy, hashlib, importlib.util, json, math, sys
from pathlib import Path
from mathutils import kdtree
HELPER=Path(__file__).with_name("f50_p0_source_mesh_v30.py")
spec=importlib.util.spec_from_file_location("f50_v30_source_helpers",str(HELPER))
prev=importlib.util.module_from_spec(spec)
spec.loader.exec_module(prev)
old=prev.old
PMT=prev.PMT; IMPORT=prev.IMPORT
SOURCE="acd9e92e3456ff90cf3837383d56739b35d0cc93a5c9b95f0c522f3b73bb99ec"
D=prev.D; W=prev.W; HUB=prev.HUB
TARGETS={
 D:(5506,7552,"9e1aa3dbffd87c93d9e2a3c3c0e7be2ed7faf927ad103dcd06cea727146044ef"),
 W:(13552,26496,"add2710c720cf6fa805fc91ae1f4f1658950ea6c6dab5f3dc5115516c96989aa"),
 HUB:(2738,4464,"63c6ed1108733286bee22058b8318a4a0c25d8c53699c2b7706656629205a9c3")
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
 o["source_edit_scope"]="F50 slot C v31_r2: preserve true original cowl silhouette, fair spokes and hub wings"
 return {"moved_vertices":moved,"max_move_mm":round(mx*1000,6)}
def cowl_rework(o,pts,normals):
 """True native F50 instrument-hood surface fairing, no invented lip.
 Keep original x/y silhouette exactly: reject v31 test candidate that
 generated a stepped upper contour in the real render."""
 xmin=min(p.x for p in pts);xmax=max(p.x for p in pts)
 ymin=min(p.y for p in pts);ymax=max(p.y for p in pts)
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 out={}
 for i,p in enumerate(pts):
  ux=(p.x-xmin)/(xmax-xmin)
  edge=smooth((ux-.045)/.105)*smooth((.955-ux)/.105)
  # Preserve original PMT top/bottom silhouette and side anchors.
  yband=smooth((p.y-ymin-.058)/.036)*smooth((ymax-p.y-.004)/.027)
  shoulder=max(gaussian(ux-.15,.21),gaussian(ux-.85,.21))
  mask=edge*yband*shoulder
  n=normals[i]
  if mask<.030 or n.z<.52:continue
  total=weight=0.
  for q,j,dist in kd.find_range(p,.031):
   if i==j or abs(q.y-p.y)>.017 or abs(q.z-p.z)>.009:continue
   dot=n.dot(normals[j])
   if dot<.83:continue
   dxy=math.hypot(q.x-p.x,q.y-p.y)
   w=gaussian(dxy,.011)*dot**5
   total+=w*q.z;weight+=w
  if weight<.14:continue
  dz=max(-.00165,min(.00165,(total/weight-p.z)*1.38*mask))
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>170,("BLOCKED_INPUT_SOURCE_COWL",len(out))
 return out

def wheel_rework(o,pts,normals):
 """Original source ring and three spoke surfaces: round shoulders and fair
  the spoke face WITHOUT bridging or moving source open boundary vertices."""
 b=bmesh.new();b.from_mesh(o.data)
 boundary={v.index for e in b.edges if not e.is_manifold for v in e.verts}
 b.free()
 assert len(boundary)>100
 e_tree=kdtree.KDTree(len(boundary))
 for j,i in enumerate(sorted(boundary)):e_tree.insert(pts[i],j)
 e_tree.balance()
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 out={}
 for i,p in enumerate(pts):
  if i in boundary:continue
  r=math.hypot(p.x,p.y)
  if r<.083:continue
  ang=math.atan2(p.y,p.x)
  _,_,d=e_tree.find(p)
  protect=smooth((d-.0008)/.006)
  if protect<.025:continue
  dr=dz=0.
  if r>.134 and p.y>.008:
   shoulder=max(gaussian(ang-math.radians(42),math.radians(21)),
                gaussian(ang-math.radians(138),math.radians(21)))
   crown=smooth((r-.136)/.015)*smooth((.177-r)/.004)
   dr=-.0017*shoulder*crown*protect
  spokes=(0,math.pi,-math.pi/2)
  angular=min(abs(math.atan2(math.sin(ang-a),math.cos(ang-a))) for a in spokes)
  if .084<r<.147 and angular<.54 and normals[i].z>.54:
   radial=smooth((r-.085)/.014)*smooth((.15-r)/.016)
   cross=smooth((.55-angular)/.30)
   mask=radial*cross*protect
   if mask>.024:
    total=weight=0.
    for q,j,dist in kd.find_range(p,.017):
     if i==j or abs(q.z-p.z)>.010:continue
     dot=normals[i].dot(normals[j])
     if dot<.85:continue
     xy=math.hypot(q.x-p.x,q.y-p.y)
     ww=gaussian(xy,.007)*dot**5
     total+=ww*q.z;weight+=ww
    if weight>.08:
     dz=max(-.0024,min(.0024,(total/weight-p.z)*1.38*mask))
  if abs(dr)>1e-7 or abs(dz)>1e-7:out[i]=(dr*p.x/r,dr*p.y/r,dz)
 assert len(out)>250,("BLOCKED_INPUT_SOURCE_WHEEL",len(out))
 return out

def hub_rework(o,pts,normals):
 """Retain real original F50 source six-bolt hub mesh; remove small imported
  3D creases using local filtered fairing, not a replacement central badge.
  Original outer hub tongue vertices advance subtly toward existing spokes."""
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
        for a in (30,90,150,210,270,330)]
 out={}
 for i,p in enumerate(pts):
  r=math.hypot(p.x,p.y+.019)
  if r>.095:continue
  n=normals[i]
  dx=dz=0.
  bolt_dist=min(math.hypot(p.x-x,p.y-y) for x,y in bolts)
  protective=smooth((bolt_dist-.008)/.012)
  # The inherited central medallion is not to be flattened.
  annulus=smooth((r-.024)/.012)*smooth((.075-r)/.012)
  top_smooth=smooth((p.y+.040)/.022)*smooth((.047-p.y)/.018)
  mask=annulus*protective*top_smooth
  if mask>.025 and n.z>.49:
   total=weight=0.
   for q,j,dist in kd.find_range(p,.026):
    if i==j or abs(q.z-p.z)>.013:continue
    dot=n.dot(normals[j])
    if dot<.78:continue
    dd=math.hypot(q.x-p.x,q.y-p.y)
    if dd>.021:continue
    w=gaussian(dd,.009)*dot**5
    total+=w*q.z;weight+=w
   if weight>.10:
    dz=max(-.0028,min(.0028,(total/weight-p.z)*1.75*mask))
  # Source-authentic 3-spoke hub wings extend into the existing source rim
  # tangs; no separate connector geometry or third-party wheel is made.
  edge=smooth((abs(p.x)-.075)/.009)*smooth((.095-abs(p.x))/.005)
  flank=smooth((p.y+.038)/.016)*smooth((.040-p.y)/.017)
  if edge*flank>.045 and n.z>.1:
   dx=math.copysign(.00210*edge*flank,p.x)
  if abs(dx)>1.e-7 or abs(dz)>1.e-7:
   out[i]=(dx,0.,dz)
 assert len(out)>120,("BLOCKED_INPUT_SOURCE_HUB",len(out))
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
 assert bpy.context.scene.get("geometry_edit_count")==90
 assert not any(p.exists() for p in (a.after,a.report,a.audit))
 b=old.snap();cams=old.cameras()
 for name,(nv,nf,sha) in TARGETS.items():
  x=b[name];assert (x["vertices"],x["faces"],x["sha256"])==(nv,nf,sha),(name,x)
 pre=renders(a,"BEFORE")
 changed={}
 for name,fun in ((D,cowl_rework),(W,wheel_rework),(HUB,hub_rework)):
  changed[name]=process(name,fun)
 c=old.snap();compare_guard(b,c);assert old.cameras()==cams
 bpy.context.scene["geometry_edit_count"]=93
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V31_R2_NATIVE_COWL_SURFACE_ONLY_THREESPOKE_HUB_WING"
 bpy.context.scene["slot_c_input_blend_sha256"]=SOURCE
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 post=renders(a,"AFTER")
 source_guard(a)
 r=dict(status="F50_V31_R2_PRIVATE_SAVE_INDEPENDENT_REOPEN_PENDING",
   native_source_pmt_sha256=PMT,verified_first_import_sha256=IMPORT,
   source_v29_blend_sha256=SOURCE,new_v31_r2_blend_sha256=old.digest(a.after),
   original_meshes_total=42,other_original_meshes_unchanged=39,
   edited_original_meshes={n:{"before":b[n],"after":c[n],**changed[n]} for n in TARGETS},
   original_wheel_nonmanifold_edges=624,
   render_sha256={"before":pre,"after":post},
   calibrated_game_eye="UNVERIFIED",seven_photo_QA="INCOMPLETE",
   hosted_original_game_scene="BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
   source_game_assets_unchanged=True,other_slots_unchanged=True,no_export=True,
   texture_material_changes=False,vehicle_complete=False,score_delta=0)
 a.report.write_text(json.dumps(r,indent=2),encoding="utf8")
 print("F50_SLOT_C_V31_R2_SAVED",r["new_v31_r2_blend_sha256"],changed,flush=True)
def audit(a):
 source_guard(a)
 r=json.loads(a.report.read_text())
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert old.digest(a.after)==r["new_v31_r2_blend_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==93
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
 q=dict(status="PASS_PRIVATE_F50_V31_R2_ORIGINAL_GAME_BLENDER_4_5_15_FRESH_REOPEN_RENDER",
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
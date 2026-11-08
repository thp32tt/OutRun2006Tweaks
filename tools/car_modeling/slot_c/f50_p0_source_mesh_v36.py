#!/usr/bin/env python3
"""F50 Slot C v36: source cockpit cowl shoulder and 3-spoke/hub surface fairing.
Real Blender 4.5.15 in-place editing of three existing authentic meshes ONLY:
instrument hood, factory 3-spoke wheel sheet and six-bolt source hub.
Never construct a new vehicle, export game-native files, change any texture or VR.
"""
import argparse,bpy,bmesh,importlib.util,hashlib,json,math,sys
from pathlib import Path
from mathutils import kdtree

BASE=Path(__file__).with_name("f50_p0_source_mesh_v34.py")
spec=importlib.util.spec_from_file_location("f50_v34_source",str(BASE))
prev=importlib.util.module_from_spec(spec);spec.loader.exec_module(prev)
PMT=prev.PMT_SHA;IMPORT=prev.IMPORT_SHA
PARENT="0259f05b9f5b2ae3beeb25644f36de971e269b71000152fdb53d89fc7d6876ff"
D,W,H=prev.D,prev.W,prev.H
EXPECTED={
 D:(5506,7552,"e095c91c9deba43fbc776ff481d40856ef754ee4d78736a3066f0838e7aa8612"),
 W:(13552,26496,"f17c90b11bdf696bf84092df60e480689e9844ceadd7a33d11ed326caa392d9f"),
 H:(2738,4464,"6f637af5c8dddd3e4ec1e0d40c57beca10bc5d42cd798cd75dcb701bf8d5488c")
}
def s(v):return prev.smooth(v)
def g(v,scale):return prev.gauss(v,scale)
def limit(v,m):return prev.clamp(v,m)
def kd(pts):return prev.kd_tree(pts)
def neighbors(p,i,n,pts,tree,maxr,zband,nmin,maxdist):
 total_z=total_r=weight=0.
 for q,j,dist in tree.find_range(p,maxr):
  if j==i or abs(q.z-p.z)>zband:continue
  dot=n.dot(pts[j][1])
  if dot<nmin:continue
  dxy=math.hypot(q.x-p.x,q.y-p.y)
  if dxy>maxdist:continue
  wt=g(dxy,maxdist*.42)*dot**7
  total_z+=wt*q.z
  total_r+=wt*math.hypot(q.x,q.y)
  weight+=wt
 return total_z,total_r,weight
def hood(o,coords,normals):
 """Fair authentic source visor shoulder while protecting all dashboard bounds."""
 tree=kd(coords)
 xmin=min(p.x for p in coords);xmax=max(p.x for p in coords)
 ymin=min(p.y for p in coords);ymax=max(p.y for p in coords)
 out={}
 for i,p in enumerate(coords):
  t=(p.x-xmin)/(xmax-xmin)
  shoulder=max(g(t-.23,.23),g(t-.77,.23))
  mask=shoulder*s((t-.055)/.13)*s((.945-t)/.13)
  mask*=s((p.y-ymin-.038)/.048)*s((ymax-p.y-.012)/.029)
  if mask<.067 or normals[i].z<.66:continue
  dz_sum=w=0.
  for q,j,dist in tree.find_range(p,.027):
   if i==j or abs(q.y-p.y)>.012 or abs(q.z-p.z)>.010:continue
   dot=normals[i].dot(normals[j])
   if dot<.92:continue
   wt=g(math.hypot(q.x-p.x,q.y-p.y),.012)*dot**7
   dz_sum+=wt*q.z;w+=wt
  if w<.13:continue
  dz=limit((dz_sum/w-p.z)*1.18*mask,.00093)
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>170,("BLOCKED_INPUT_NO_ORIGINAL_DASH_PATCH",len(out))
 return out
def wheel(o,coords,normals):
 """Polish factory metal spoke plate and lower grip only.
 Preserve all eight original open hole boundary loops and upper rim unchanged."""
 protected,loops=prev.boundary_loop_stats(o)
 edge_tree=kd([coords[i] for i in sorted(protected)])
 tree=kd(coords)
 out={}
 for i,p in enumerate(coords):
  if i in protected:continue
  r=math.hypot(p.x,p.y)
  if r<.083:continue
  ang=math.atan2(p.y,p.x)
  near_spoke=min(abs(math.atan2(math.sin(ang-t),math.cos(ang-t))) for t in (0.,math.pi,-math.pi/2))
  _,_,edist=edge_tree.find(p)
  freeze=s((edist-.0010)/.008)
  if freeze<.05:continue
  dz=dr=0.
  # Original metal plate, not a replacement or fabricated hole surface.
  if .090<r<.148 and near_spoke<.44 and normals[i].z>.56:
   region=s((r-.092)/.015)*s((.149-r)/.019)*s((.45-near_spoke)/.27)
   mask=region*freeze
   if mask>.055:
    z_total=weight=0.
    for q,j,dist in tree.find_range(p,.024):
     if i==j or abs(q.z-p.z)>.011:continue
     dot=normals[i].dot(normals[j])
     if dot<.90:continue
     dxy=math.hypot(q.x-p.x,q.y-p.y)
     if dxy>.021:continue
     wt=g(dxy,.0115)*dot**7
     z_total+=wt*q.z;weight+=wt
    if weight>.11: dz=limit((z_total/weight-p.z)*1.22*mask,.00118)
  # Fair lower ring arc only - protects v33 rejected upper-rim from scars.
  if .151<r<.174 and p.y<-.056 and near_spoke>.20 and normals[i].z>0:
   region=s((-p.y-.053)/.047)*s((r-.152)/.011)*s((.174-r)/.010)
   region*=s((near_spoke-.20)/.16)*freeze
   if region>.045:
    radial=zz=weight=0.
    for q,j,dist in tree.find_range(p,.019):
     if i==j or abs(q.z-p.z)>.006:continue
     dot=normals[i].dot(normals[j])
     if dot<.91:continue
     wgt=g(dist,.008)*dot**8
     radial+=wgt*math.hypot(q.x,q.y);zz+=wgt*q.z;weight+=wgt
    if weight>.16:
     dr=limit((radial/weight-r)*.45*region,.00043)
     dz+=limit((zz/weight-p.z)*.38*region,.00038)
  if abs(dr)>1e-7 or abs(dz)>1e-7:out[i]=(p.x/r*dr,p.y/r*dr,dz)
 assert len(out)>180,("BLOCKED_INPUT_NO_ORIGINAL_WHEEL_PATCH",len(out))
 return out
def hub(o,coords,normals):
 """Six original PMT bolt-islands and factory medallion remain intact.
 Locally fair original six-bolt spoke-root crown without new cap or bolt mesh."""
 tree=kd(coords);out={}
 bolt_centers=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
              for a in (30,90,150,210,270,330)]
 for i,p in enumerate(coords):
  r=math.hypot(p.x,p.y+.019)
  if not (.026<r<.081) or normals[i].z<.58:continue
  dist_bolt=min(math.hypot(p.x-x,p.y-y) for x,y in bolt_centers)
  mask=s((r-.027)/.014)*s((.081-r)/.016)*s((dist_bolt-.009)/.011)
  if mask<.05:continue
  z_total=weight=0.
  for q,j,d in tree.find_range(p,.025):
   if j==i or abs(q.z-p.z)>.009:continue
   dot=normals[i].dot(normals[j])
   if dot<.90:continue
   distxy=math.hypot(q.x-p.x,q.y-p.y)
   if distxy>.023:continue
   wt=g(distxy,.0115)*dot**7
   z_total+=wt*q.z;weight+=wt
  if weight<.11:continue
  dz=limit((z_total/weight-p.z)*1.35*mask,.00118)
  if abs(dz)>1e-7:out[i]=(0.,0.,dz)
 assert len(out)>90,("BLOCKED_INPUT_NO_ORIGINAL_HUB_PATCH",len(out))
 return out
def verify(a):
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 for p,expected in ((a.native,PMT),(a.original_import,IMPORT),(a.before,PARENT)):
  assert p.is_file() and prev.sha(p)==expected,("BLOCKED_INPUT",str(p))
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
 assert len(prev.meshes())==42
 assert bpy.context.scene.get("geometry_edit_count") in (105,108)
 for n,(nv,nf,ms) in EXPECTED.items():
  o=bpy.data.objects[n]
  assert (len(o.data.vertices),len(o.data.polygons))==(nv,nf)
  if bpy.context.scene.get("geometry_edit_count")==105:
   assert prev.mesh_hash(o)==ms,("BLOCKED_INPUT_UNEXPECTED_PARENT_MESH",n)
  assert o.get("outrun_original_game_resource_sha256")==PMT
  assert o.get("outrun_original_mesh_object_id")==n.replace("PMT_F50_","")
def apply(n,fn):
 o=bpy.data.objects[n]
 before=[v.co.copy() for v in o.data.vertices]
 normals=[v.normal.copy() for v in o.data.vertices]
 protect={}
 if n==W:
  protected,_=prev.boundary_loop_stats(o)
  protect={i:before[i].copy() for i in protected}
 patches=fn(o,before,normals)
 for i,(dx,dy,dz) in patches.items():
  v=o.data.vertices[i]
  v.co.x+=dx;v.co.y+=dy;v.co.z+=dz
 o.data.update()
 assert all((o.data.vertices[i].co-p).length<1e-10 for i,p in protect.items())
 shifts=[(before[i]-v.co).length for i,v in enumerate(o.data.vertices)]
 count=sum(v>1e-6 for v in shifts);maximum=max(shifts)
 assert count>100 and 0.00002<maximum<.0021,(n,count,maximum)
 return {"moved":count,"max_mm":round(maximum*1000,6)}
def compare(x,y,cams):
 assert set(x)==set(y) and len(x)==42
 for n,pre in x.items():
  post=y[n]
  assert pre["source_id"]==post["source_id"] and pre["source_id"]
  assert pre["pmt_sha"]==post["pmt_sha"]==PMT
  for k in ("vertices","faces","matrix","materials","uv_layers","uv_sha256"):
   assert pre[k]==post[k],(n,k)
  if n in EXPECTED:assert pre["mesh_sha256"]!=post["mesh_sha256"],n
  else:assert pre==post,("FORBIDDEN_OTHER_NATIVE_MESH",n)
 assert sum(x[n]["mesh_sha256"]==y[n]["mesh_sha256"] for n in x)==39
 assert prev.cam_state()==cams
 assert prev.boundary_loop_stats(bpy.data.objects[W])[1]==[48,48,72,72,72,96,96,120]
def render(a,step):
 return {label:prev.render_view(a,step,label) for label in prev.CAMERAS}
def build(a):
 verify(a)
 assert bpy.context.scene.get("geometry_edit_count")==105
 assert Path(bpy.data.filepath).resolve()==a.before.resolve()
 assert not any(p.exists() for p in (a.after,a.report,a.audit))
 originals=prev.meshes();cams=prev.cam_state()
 rb=render(a,"BEFORE")
 movement={n:apply(n,fn) for n,fn in ((D,hood),(W,wheel),(H,hub))}
 result=prev.meshes()
 compare(originals,result,cams)
 bpy.context.scene["geometry_edit_count"]=108
 bpy.context.scene["slot_c_input_blend_sha256"]=PARENT
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V36_REAL_NATIVE_COWL_SPOKE_LOWER_RING_AND_6_BOLT_HUB"
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 ra=render(a,"AFTER")
 assert prev.sha(a.before)==PARENT
 document={"status":"PRIVATE_F50_V36_SAVED_FRESH_REOPEN_PENDING","blender":bpy.app.version_string,
   "original_pmt_sha256":PMT,"original_import_sha256":IMPORT,"input_v34_sha256":PARENT,
   "output_private_blend_sha256":prev.sha(a.after),"output_bytes":a.after.stat().st_size,
   "edited_original_objects":{n:{"before":originals[n],"after":result[n],**movement[n]} for n in EXPECTED},
   "untouched_other_original_source_meshes":39,
   "original_source_wheel_open_boundary_edges":624,
   "source_open_loop_sizes":[48,48,72,72,72,96,96,120],
   "original_cameras_unchanged":True,"source_object_identity_uv_materials_transforms_preserved":True,
   "comparison_renders":{"before":rb,"after":ra},
   "native_game_eye":"UNVERIFIED","authentic_photo_seven_views":"INCOMPLETE",
   "hosted_private_blend":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
   "car_complete":False,"advance_slot_c":False,"score_change":0}
 a.report.write_text(json.dumps(document,indent=2,ensure_ascii=False),encoding="utf-8")
 print("F50_V36_SAVED "+json.dumps({"sha":document["output_private_blend_sha256"],"moved":movement},ensure_ascii=False),flush=True)
def audit(a):
 verify(a)
 assert bpy.context.scene.get("geometry_edit_count")==108
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 j=json.loads(a.report.read_text(encoding="utf-8"))
 assert prev.sha(a.after)==j["output_private_blend_sha256"]
 end=prev.meshes();cams=prev.cam_state()
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 before=prev.meshes();assert prev.cam_state()==cams
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 compare(before,prev.meshes(),cams)
 assert prev.meshes()==end
 r=prev.render_view(a,"INDEPENDENT","STEERING")
 result={"status":"PASS_F50_V36_OFFICIAL_4_5_15_FRESH_PROCESS_REOPEN_RENDER",
  "PMT_SHA256":prev.sha(a.native),"native_source_blend_SHA256":prev.sha(a.original_import),
  "parent_v34_SHA256":prev.sha(a.before),"candidate_v36_SHA256":prev.sha(a.after),
  "fresh_steering_render_sha256":r,"unchanged_source_mesh_count":39,
  "source_steering_open_edges":624,"original_game_eye":"UNVERIFIED",
  "seven_authentic_photo_views":"INCOMPLETE",
  "github_actions_real_private_blend":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  "vehicle_complete":False,"score_delta":0}
 assert not a.audit.exists()
 a.audit.write_text(json.dumps(result,indent=2),encoding="utf-8")
 print(result["status"]+" "+result["candidate_v36_SHA256"],flush=True)
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--mode",choices=("build","audit"),required=True)
 for name in ("native","original-import","before","after","report","audit","render-root"):
  parser.add_argument("--"+name,type=Path,required=True)
 a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
 if a.mode=="build":build(a)
 else:audit(a)
if __name__=="__main__":main()
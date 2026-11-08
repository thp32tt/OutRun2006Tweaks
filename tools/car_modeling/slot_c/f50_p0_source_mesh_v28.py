#!/usr/bin/env python3
"""F50 slot C v28: edit genuine PMT-imported existing dashboard/rim/hub meshes only.

Private native PMT, original import and v27-r2 .blend SHA-gated; no exports, no
new vehicle/mesh/texture. Run with Blender 4.5.15 on private input, then fresh
separate-process reopen. Helpers reuse audited public v27_r2 script.
"""
import argparse, bpy, json, math, sys, importlib.util
from pathlib import Path
from mathutils import kdtree
H=Path(__file__).with_name("f50_p0_source_mesh_v27_r2.py")
sp=importlib.util.spec_from_file_location("f50_v27_original_source_helpers",str(H))
old=importlib.util.module_from_spec(sp);sp.loader.exec_module(old)
PMT=old.PMT; IMPORT=old.IMPORT
SOURCE="45393c348358214c4332d449fcdb1c5a47d38b1958e4e1a043efd59eebe92faf"
D="PMT_F50_object00_group01_material028_a0"
W="PMT_F50_object21_group01_material002_a0"
HUB="PMT_F50_object21_group00_material000_a0"
TARGETS={D:(5506,7552,"90ac6661da38cdd20b579ba514a0d2e970e5e8719c35cd130fb980c2a5e9bfa3"),
         W:(13552,26496,"9b338c040d659a1260a975494fe067b083435dfc7b93f56ea42e222931404d6b"),
         HUB:(2738,4464,"977c7c00dc32eb272983e9b9bae0ed3c3f75aa32fd763cd73b996cf0dd52ceab")}
def guard_source(a):
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 for p,sha in [(a.native,PMT),(a.original_import,IMPORT),(a.before,SOURCE)]:
  assert p.is_file() and old.digest(p)==sha,("BLOCKED_INPUT_SHA",str(p))
 assert bpy.context.scene.get("outrun_original_game_resource_sha256")==PMT
def bump(o,fn):
 m=o.data; before=[v.co.copy() for v in m.vertices]
 changes=fn(before,[v.normal.copy() for v in m.vertices])
 for i,delta in changes.items():
  if isinstance(delta,tuple):
   m.vertices[i].co.x+=delta[0];m.vertices[i].co.y+=delta[1]
  else:m.vertices[i].co.z+=delta
 m.update()
 moves=[(v.co-before[i]).length for i,v in enumerate(m.vertices)]
 count=sum(x>1e-6 for x in moves);maximum=max(moves)
 assert count>70 and 0.00003<maximum<=.00121,(o.name,count,maximum)
 o["source_edit_scope"]="F50 slot C v28; source PMT native existing cockpit geometry only"
 return {"moved_vertices":count,"max_displacement_mm":round(1000*maximum,6)}
def cowl(pts,norms):
 xmin=min(p.x for p in pts);xmax=max(p.x for p in pts);ymax=max(p.y for p in pts)
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance();out={}
 for i,p in enumerate(pts):
  ux=(p.x-xmin)/(xmax-xmin);n=norms[i]
  if not .075<ux<.925 or abs(n.z)<.59:continue
  mask=old.smooth((ux-.075)/.16)*old.smooth((.925-ux)/.16)
  mask*=old.smooth((p.y-(ymax-.095))/.04)*old.smooth((ymax-.0045-p.y)/.028)
  if mask<.04:continue
  total=weight=0.
  for q,j,dist in kd.find_range(p,.024):
   dx=q.x-p.x;dy=q.y-p.y
   if i==j or abs(q.z-p.z)>.010 or abs(dy)>.019:continue
   dot=n.dot(norms[j])
   if dot<.86 or dx*dx+dy*dy>.020**2:continue
   w=math.exp(-(dx*dx+dy*dy)/(2*.010**2))*dot**5
   total+=w*q.z;weight+=w
  if weight<.18:continue
  dz=max(-.0009,min(.0009,(total/weight-p.z)*1.08*mask))
  if abs(dz)>2e-7:out[i]=dz
 assert len(out)>120,("BLOCKED_INPUT_SOURCE_COWL",len(out))
 return out
def wheel(pts,norms):
 out={}
 for i,p in enumerate(pts):
  r=math.hypot(p.x,p.y)
  if not .147<r<.174 or p.y<=0:continue
  angle=math.degrees(math.atan2(p.y,p.x))
  peak=max(math.exp(-.5*((angle-40.)/15.)**2),
           math.exp(-.5*((angle-140.)/15.)**2))
  mask=old.smooth((r-.148)/.014)*old.smooth((.174-r)/.004)*peak
  dr=-.00080*mask
  if abs(dr)>2e-7:out[i]=(dr*p.x/r,dr*p.y/r)
 assert len(out)>120,("BLOCKED_INPUT_SOURCE_WHEEL",len(out))
 return out
def hub(pts,norms):
 kd=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):kd.insert(p,i)
 kd.balance()
 bolts=[(.049*math.cos(math.radians(a)),-.019+.049*math.sin(math.radians(a)))
        for a in (30,90,150,210,270,330)]
 out={}
 for i,p in enumerate(pts):
  r=math.hypot(p.x,p.y+.019)
  if not .025<r<.070 or norms[i].z<.77:continue
  bolt_dist=min(math.hypot(p.x-x,p.y-y) for x,y in bolts)
  mask=old.smooth((r-.025)/.012)*old.smooth((.069-r)/.010)
  mask*=old.smooth((bolt_dist-.010)/.013)
  if mask<.035:continue
  total=weight=0.
  for q,j,dist in kd.find_range(p,.021):
   if i==j or abs(q.z-p.z)>.007:continue
   dot=norms[i].dot(norms[j]);dx=q.x-p.x;dy=q.y-p.y
   if dot<.88 or dx*dx+dy*dy>.017**2:continue
   w=math.exp(-(dx*dx+dy*dy)/(2*.008**2))*dot**5
   total+=w*q.z;weight+=w
  if weight<.12:continue
  dz=max(-.0012,min(.0012,(total/weight-p.z)*1.10*mask))
  if abs(dz)>2e-7:out[i]=dz
 assert len(out)>65,("BLOCKED_INPUT_SOURCE_HUB",len(out))
 return out
def guard(before,after):
 assert len(before)==len(after)==42 and set(before)==set(after)
 for name,x in before.items():
  y=after[name]
  assert x["original_id"] and x["pmt"]==y["pmt"]==PMT
  for k in ("original_id","pmt","vertices","faces","nonmanifold","uv_layers","materials","matrix"):
   assert x[k]==y[k],(name,k)
  if name in TARGETS:assert x["sha256"]!=y["sha256"],name
  else:assert x==y,("OTHER_MESH_CHANGED",name)
 assert after[W]["nonmanifold"]==before[W]["nonmanifold"]==624
 assert sum(before[n]["sha256"]==after[n]["sha256"] for n in before)==39
def render(a,stage):
 hashes={}
 for label,(cam,visible) in old.VIEWS.items():
  p=Path(str(a.render_root)+"_"+stage+"_"+label+".png")
  old.render(p,cam,visible);hashes[label]=old.digest(p)
 return hashes
def build(a):
 guard_source(a)
 assert Path(bpy.data.filepath).resolve()==a.before.resolve()
 assert bpy.context.scene.get("geometry_edit_count")==81
 assert not any(p.exists() for p in (a.after,a.report,a.audit))
 before=old.snap();original_cameras=old.cameras()
 for n,(nv,nf,sha) in TARGETS.items():
  s=before[n];assert (s["vertices"],s["faces"],s["sha256"])==(nv,nf,sha),(n,s)
 before_renders=render(a,"BEFORE")
 stats={}
 for name,fn in ((D,cowl),(W,wheel),(HUB,hub)):
  stats[name]=bump(bpy.data.objects[name],fn)
 after=old.snap();guard(before,after);assert original_cameras==old.cameras()
 bpy.context.scene["geometry_edit_count"]=84
 bpy.context.scene["slot_c_last_geometry_stage"]="F50_V28_NATIVE_P0_COWL_WHEEL_RIM_HUB"
 bpy.context.scene["slot_c_input_blend_sha256"]=SOURCE
 bpy.ops.wm.save_as_mainfile(filepath=str(a.after),compress=True)
 after_renders=render(a,"AFTER")
 guard_source(a)
 receipt=dict(status="SAVED_PRIVATE_F50_V28_PENDING_INDEPENDENT_REOPEN",
  native_pmt_sha256=PMT,original_import_sha256=IMPORT,source_v27r2_sha256=SOURCE,
  output_blend_sha256=old.digest(a.after),original_mesh_count=42,
  altered_original_meshes={n:dict(before=before[n],after=after[n],**stats[n]) for n in TARGETS},
  unchanged_source_mesh_count=39,source_wheel_nonmanifold_edges_unfixed=624,
  original_cameras_transforms_unchanged=True,original_UVs_materials_unchanged=True,
  matched_non_game_renders={"before":before_renders,"after":after_renders},
  authentic_game_driver_eye="UNVERIFIED",seven_photo_views="INCOMPLETE",
  github_hosted_original_scene="BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
  vehicle_complete=False,score_delta=0,no_game_exports=True,no_new_textures=True)
 a.report.write_text(json.dumps(receipt,indent=2),encoding="utf8")
 print("F50_V28_SAVED",receipt["output_blend_sha256"],stats,flush=True)
def audit(a):
 guard_source(a)
 r=json.loads(a.report.read_text(encoding="utf8"))
 assert Path(bpy.data.filepath).resolve()==a.after.resolve()
 assert old.digest(a.after)==r["output_blend_sha256"]
 assert bpy.context.scene.get("geometry_edit_count")==84
 after=old.snap();cam=old.cameras()
 bpy.ops.wm.open_mainfile(filepath=str(a.before))
 before=old.snap();guard(before,after);assert cam==old.cameras()
 for n,t in r["altered_original_meshes"].items():
  assert before[n]==t["before"] and after[n]==t["after"],n
 bpy.ops.wm.open_mainfile(filepath=str(a.after))
 assert old.snap()==after and old.cameras()==cam
 assert not a.audit.exists()
 p=Path(str(a.render_root)+"_FRESH_REOPEN_STEERING.png")
 old.render(p,*old.VIEWS["STEERING"])
 audit=dict(status="PASS_PRIVATE_F50_V28_BLENDER_4_5_15_FRESH_REOPEN_RENDER",
  native_sha256=old.digest(a.native),import_sha256=old.digest(a.original_import),
  input_sha256=old.digest(a.before),output_sha256=old.digest(a.after),
  independent_steering_render_sha256=old.digest(p),
  changed_original_meshes=3,unchanged_original_meshes=39,source_wheel_nonmanifold_edges=624,
  original_game_eye="UNVERIFIED",seven_photo_views="INCOMPLETE",
  hosted_private_scene="BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",score_delta=0)
 a.audit.write_text(json.dumps(audit,indent=2),encoding="utf8")
 print(audit["status"],audit["output_sha256"],flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--mode",choices=("build","audit"),required=True)
 for n in ("native","original-import","before","after","report","audit","render-root"):
  p.add_argument("--"+n,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if a.mode=="build":build(a)
 else:audit(a)
if __name__=="__main__":main()
#!/usr/bin/env python3
"""Ferrari F50 slot-C P0 v3r2, ONLY native-derived existing dashboard and 3-spoke wheel geometry.
This script requires the SHA-pinned original PMT source AND existing v2 derived .blend.
It never imports replacement content, constructs another vehicle, or exports game formats.
"""
import bpy, bmesh, hashlib, struct, json, math, sys, argparse
from pathlib import Path

ORIGINAL_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
ORIGINAL_IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
V2_SHA="381326a1b3bfbe598bd744abc19c53aeb6140895fe9e9a095f677ecf49defb53"
TARGETS={
"PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",1378,1888,"6890e11c6af3b0a2b71afbdeb2b65c241e3927b70e53dfdf9c5f5e9a0b9f9469"),
"PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",3460,6624,"c0c6aede3ffdaa74bf1204d4bbecca77a97bf86f975a9bd41822784de014c843"),
"PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",306,496,"df521e8305225847e094c3f177c042bd72845f25dfdd332cf2ab9c0ce53237e0"),
}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mesh_sha(mesh):
 h=hashlib.sha256()
 for v in mesh.vertices:h.update(struct.pack("<3f",*v.co))
 for poly in mesh.polygons:
  h.update(struct.pack("<I",len(poly.vertices)))
  for idx in poly.vertices:h.update(struct.pack("<I",idx))
 return h.hexdigest()
def snapshot(obj):
 bm=bmesh.new();bm.from_mesh(obj.data)
 nm=sum(1 for e in bm.edges if not e.is_manifold);bm.free()
 return {"original_id":obj.get("outrun_original_mesh_object_id"),
         "verts":len(obj.data.vertices),"faces":len(obj.data.polygons),
         "mesh_sha256":mesh_sha(obj.data),"nonmanifold_edges":nm,
         "matrix_world":[round(float(v),9) for row in obj.matrix_world for v in row],
         "materials":len(obj.data.materials),
         "uv_layers":len(obj.data.uv_layers),
         "native_object_index":obj.get("outrun_original_pmt_object_index")}
def bump_cowl(obj):
 """Continue shaping original F50 binnacle shell, without fabricating a second dashboard."""
 verts=obj.data.vertices
 xmin,xmax=min(v.co.x for v in verts),max(v.co.x for v in verts)
 ymin,ymax=min(v.co.y for v in verts),max(v.co.y for v in verts)
 moved=0
 maxabs=0.
 for v in verts:
  u=(v.co.x-xmin)/max(xmax-xmin,1e-8)
  t=(v.co.y-ymin)/max(ymax-ymin,1e-8)
  # Upper padded shroud brow stays in native original physical silhouette.
  x=(u-0.5)*2.
  eyebrow=math.exp(-((t-(0.79-0.16*x*x))/0.125)**2)*max(0.,1.-0.30*x*x)
  # Layered sun-shield slope taper toward the inner gauge face.
  inner=math.exp(-((t-0.49)/0.19)**2)*math.exp(-((x)/0.75)**4)
  # The real F50 cluster has strong left-right curved brow shoulders, not a flat arc.
  shoulders=(math.exp(-((u-0.19)/0.12)**2)+math.exp(-((u-0.81)/0.12)**2))
  endroll=shoulders*math.exp(-((t-0.57)/0.22)**2)
  dz=0.0048*eyebrow-0.0022*inner+0.0016*endroll
  if abs(dz)>1.e-5:
   v.co.z+=dz
   moved+=1
   maxabs=max(maxabs,abs(dz))
 obj.data.update()
 obj["source_edit_scope"]="P0 v3 native F50 cowl: formed padded brow ridge, sunken gauge visor, left/right shoulder roll"
 return moved,maxabs
def bump_spoked_wheel(obj):
 """Refine front grip bulges and press-relief on original 3-spoke steering rim mesh."""
 moved=0;maxabs=0.
 for v in obj.data.vertices:
  x,y,z=v.co
  r=math.hypot(x,y)
  if r<1e-8:continue
  theta=math.atan2(y,x)
  # Photo shows two distinct thumb-rest grips near 10 and 2 o'clock.
  gangle=sum(math.exp(-((math.atan2(math.sin(theta-a),math.cos(theta-a)))/0.21)**2)
             for a in (math.pi*0.82,math.pi*0.18))
  gr=math.exp(-((r-0.146)/0.017)**2)
  front=max(0.12,min(1.,(z+0.014)/0.021))
  # Soft front-contour for both grip bulges.
  dz=0.0034*gr*gangle*front
  dr=0.0011*gr*gangle
  # Original left/right 3-spoke stamped ribs, not a new triangle overlay.
  spoke=(math.exp(-((abs(x)-0.074)/0.033)**2)*
         math.exp(-((y+0.020)/0.023)**2))
  # Original lower stem: subtle center profile rather than flat polygon.
  stem=math.exp(-((x)/0.023)**2)*math.exp(-((y+0.095)/0.036)**2)
  dz+=0.0020*spoke*(1.0 if z>0 else 0.2)
  dz+=0.0017*stem*(1.0 if z>0 else 0.2)
  if abs(dz)>1.e-5 or abs(dr)>1.e-5:
   v.co.x+=dr*x/r
   v.co.y+=dr*y/r
   v.co.z+=dz
   moved+=1;maxabs=max(maxabs,abs(dz),abs(dr))
 obj.data.update()
 obj["source_edit_scope"]="P0 v3 original F50 wheel: thumb grip and three stamped spoke contours"
 return moved,maxabs
def bump_hub(obj):
 """Subtle physical hub/cap rework on its own PMT mesh; avoid fake sharp bolt spikes."""
 bm=bmesh.new()
 bm.from_mesh(obj.data)
 # Additional native-face tessellation retains the original triangular surface linkage.
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True)
 bm.to_mesh(obj.data)
 bm.free()
 moved=0
 maxabs=0.0
 bolt_centers=[(0.048*math.cos(math.radians(d)),
                -0.019+0.048*math.sin(math.radians(d)))
               for d in (30,90,150,210,270,330)]
 # Use broad, low-amplitude source-face stamping to avoid unrealistic spiky creases.
 for v in obj.data.vertices:
  x,y,z=v.co
  rc=math.hypot(x,y+0.019)
  boss=0.00110*math.exp(-((rc/0.028)**4))
  ring=0.00062*math.exp(-((rc-0.032)/0.009)**2)
  bolts=0.
  for bx,by in bolt_centers:
   dist=math.hypot(x-bx,y-by)
   bolts+=-0.00082*math.exp(-(dist/0.0105)**2)
   bolts+=0.00038*math.exp(-((dist-0.014)/0.0075)**2)
  dz=(boss+ring+bolts) * (1.0 if z>=0 else 0.16)
  if abs(dz)>1e-5:
   v.co.z+=dz
   moved+=1
   maxabs=max(maxabs,abs(dz))
 # Smooth front-z continuity only, never rescale or move original native XY/pivot.
 # The original plate boundary and all other source objects remain untouched.
 bm=bmesh.new()
 bm.from_mesh(obj.data)
 for _ in range(3):
  vals={}
  for v in bm.verts:
   x,y,z=v.co
   if math.hypot(x,y+0.019)>0.073 or z<0: continue
   neighbors=[e.other_vert(v).co.z for e in v.link_edges]
   if neighbors:
    vals[v]=z*0.72+(sum(neighbors)/len(neighbors))*0.28
  for v,newz in vals.items():v.co.z=newz
 bm.to_mesh(obj.data)
 bm.free()
 for f in obj.data.polygons:f.use_smooth=True
 obj.data.update()
 obj["source_edit_scope"]="P0 v3r2 original F50 hub: photo-referenced low-profile center boss and six subtle fastener cups, smoothed native source topology"
 return moved,maxabs

def diagnostic(scene,root,tag,camera,kept):
 old={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 engine=scene.render.engine
 fpath=scene.render.filepath
 cam=scene.camera
 res=scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage
 try:
  scene.render.engine="BLENDER_WORKBENCH"
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=800,560,100
  scene.render.image_settings.file_format="PNG"
  scene.camera=bpy.data.objects[camera]
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in kept
  scene.render.filepath=str(root)+"_"+tag+"_NON_GAME.png"
  bpy.ops.render.render(write_still=True)
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=old[o.name]
  scene.camera=cam
  scene.render.engine=engine
  scene.render.filepath=fpath
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=res

def run():
 p=argparse.ArgumentParser()
 for x in ("native","original-import","input","output","report","render-root"):
  p.add_argument("--"+x,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version
 assert a.native.is_file() and sha(a.native)==ORIGINAL_SHA,"Original game F50 PMT input BLOCKED"
 assert a.original_import.is_file() and sha(a.original_import)==ORIGINAL_IMPORT_SHA
 assert a.input.is_file() and sha(a.input)==V2_SHA
 assert not a.output.exists() and not a.report.exists(),"Do not overwrite prior version"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 sc=bpy.context.scene
 assert sc.get("outrun_original_game_resource_sha256")==ORIGINAL_SHA
 assert sc.get("geometry_edit_count")==6
 objects={o.name:o for o in bpy.data.objects if o.type=="MESH"}
 assert len(objects)==42 and all(o.get("outrun_original_mesh_object_id") for o in objects.values())
 before={n:snapshot(o) for n,o in objects.items()}
 for n,(source_id,v,f,sh) in TARGETS.items():
  assert n in objects
  assert before[n]["original_id"]==source_id
  assert (before[n]["verts"],before[n]["faces"],before[n]["mesh_sha256"])==(v,f,sh),n
  assert not before[n]["materials"]
 functions=[bump_cowl,bump_spoked_wheel,bump_hub]
 delta={}
 for name,func in zip(TARGETS,functions):
  count,displacement=func(objects[name])
  assert count>=18 and displacement>0.0005
  delta[name]={"modified_vertices":count,"max_abs_deformation_m":round(displacement,8)}
 after={n:snapshot(o) for n,o in objects.items()}
 for n in before:
  assert before[n]["original_id"]==after[n]["original_id"]
  assert before[n]["matrix_world"]==after[n]["matrix_world"]
  assert before[n]["materials"]==after[n]["materials"]
  assert before[n]["uv_layers"]==after[n]["uv_layers"]
  if n not in TARGETS:assert after[n]==before[n],f"non-cockpit mesh changed {n}"
  else:assert before[n]["mesh_sha256"]!=after[n]["mesh_sha256"]
 sc["geometry_edit_count"]=9
 sc["slot_c_last_geometry_stage"]="F50_P0_V3R2_EXISTING_NATIVE_MESH_ONLY"
 sc["slot_c_input_blend_sha256"]=V2_SHA
 sc["slot_c_native_pmt_sha256"]=ORIGINAL_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 assert sha(a.native)==ORIGINAL_SHA
 result={
  "status":"F50_SLOTC_V3R2_SOURCE_GEOMETRY_SAVED_LOCAL_QA_PENDING",
  "blender":bpy.app.version_string,"native_pmt_sha256":ORIGINAL_SHA,
  "original_import_blend_sha256":ORIGINAL_IMPORT_SHA,"before_blend_sha256":V2_SHA,
  "after_blend_sha256":sha(a.output),"source_imported_mesh_objects":42,
  "source_ids_modified":[TARGETS[n][0] for n in TARGETS],
  "before_after":{n:{"before":before[n],"after":after[n],"edit":delta[n]} for n in TARGETS},
  "untouched_original_source_objects":39,
  "source_object_matrices_preserved":True,"source_game_file_preserved":True,
  "created_new_car":False,"imported_glb":False,"modified_external_geometry":False,
  "created_textures_PBR_normal":False,"created_OVC_PMT_game_output":False,
  "original_game_driver_eye":"UNVERIFIED","photo_seven_views":"NOT_PASSED",
  "local_geometry_saved":True,
  "github_actions_real_scene":"BLOCKED_PRIVATE_SCENE_NOT_SUBMITTED",
  "complete":False
 }
 a.report.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf8")
 diagnostic(sc,a.render_root,"GAUGE_QA","QA_F50_GAUGE_DETAIL_NON_GAME",
            ["PMT_F50_object00_group01_material028_a0"])
 diagnostic(sc,a.render_root,"STEERING_QA","QA_F50_STEERING_LOCAL_NON_GAME",
            ["PMT_F50_object21_group00_material000_a0","PMT_F50_object21_group01_material001_a0","PMT_F50_object21_group01_material002_a0"])
 print("F50_SLOT_C_V3R2_REAL_SOURCE_GEOMETRY_SAVED",result["after_blend_sha256"],
       [(n,after[n]["verts"],after[n]["faces"]) for n in TARGETS])

if __name__=="__main__":run()
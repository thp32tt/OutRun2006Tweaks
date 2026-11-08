#!/usr/bin/env python3
"""F50 Slot C P0 v16_r2: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires the exact read-only original PMT and verified first import, then edits the immutable v15 source-derived .blend.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="d6dd11d872105e94a5f7b5262c7aed8a327098f80c3645e907a2c9ba127d8302"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"715967e7e9a4c9d6eab3b40d8a2776ea69889f3ca3da1160a4d8c97c09a6f6cd"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"b7e76a3f48218a4b5945a7e78a335843a07f52e40d9bdc24936d571d805da722"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"0e72e23cbfb48973c6977e151a4cb1c534ae797ac61f1a9c5f1421792cb94225")}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mesh_sig(me):
 h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack("<3f",*v.co))
 for f in me.polygons:
  h.update(struct.pack("<I",len(f.vertices)))
  for idx in f.vertices:h.update(struct.pack("<I",idx))
 return h.hexdigest()
def snapshot(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 nonmanifold=sum(not e.is_manifold for e in bm.edges);bm.free()
 return {"id":o.get("outrun_original_mesh_object_id"),"pmt":o.get("outrun_original_game_resource_sha256"),
  "mesh_sha256":mesh_sig(o.data),"verts":len(o.data.vertices),"faces":len(o.data.polygons),
  "nonmanifold":nonmanifold,"materials":len(o.data.materials),"uv":len(o.data.uv_layers),
  "matrix":[round(float(a),9) for row in o.matrix_world for a in row]}
def window(value,lo,hi,width):
 return max(0.,min(1.,(value-lo)/width,(hi-value)/width))

def smooth_existing_z(o,weight,rounds=2):
 """Smooth pre-existing source mesh z along authentic edges, never add geometry."""
 me=o.data
 adj=[[] for v in me.vertices]
 for e in me.edges:
  a,b=e.vertices
  adj[a].append(b);adj[b].append(a)
 for _ in range(rounds):
  old=[float(v.co.z) for v in me.vertices]
  new={}
  for i,v in enumerate(me.vertices):
   w=weight(v.co)
   if w>1.e-5 and adj[i]:
    new[i]=old[i]+w*(sum(old[j] for j in adj[i])/len(adj[i])-old[i])
  for i,z in new.items():me.vertices[i].co.z=z
 me.update()


def relax_z_on_source_edges(o, region, passes, strength, cap):
    """Neighbour-constrained real mesh vertex relaxation; keep original face/UV topology."""
    me=o.data
    baseline=[float(v.co.z) for v in me.vertices]
    nbrs=[[] for _ in me.vertices]
    for e in me.edges:
        i,j=e.vertices
        nbrs[i].append(j);nbrs[j].append(i)
    bm=bmesh.new();bm.from_mesh(me)
    bm.verts.ensure_lookup_table();bm.verts.index_update()
    boundary={v.index for e in bm.edges if not e.is_manifold for v in e.verts}
    bm.free()
    for _ in range(passes):
        z=[float(v.co.z) for v in me.vertices]
        moves={}
        for i,v in enumerate(me.vertices):
            if i in boundary or not nbrs[i]: continue
            w=region(v.co)
            if w>1e-6:
                dz=sum(z[j] for j in nbrs[i])/len(nbrs[i])-z[i]
                moves[i]=z[i]+strength*w*dz
        for i,zval in moves.items():me.vertices[i].co.z=zval
    for i,v in enumerate(me.vertices):
        v.co.z=max(baseline[i]-cap,min(baseline[i]+cap,float(v.co.z)))
    me.update()

def sculpt_original_hood(o):
    """Source F50 instrument visor: relax inherited zig-zagged ridge, retain raised original brow."""
    verts=o.data.vertices
    before=[tuple(v.co) for v in verts]
    x0,x1=min(v.co.x for v in verts),max(v.co.x for v in verts)
    y0,y1=min(v.co.y for v in verts),max(v.co.y for v in verts)
    sx=max(1e-9,x1-x0);sy=max(1e-9,y1-y0)
    def region(co):
        u=(co.x-x0)/sx;t=(co.y-y0)/sy
        return window(u,.07,.93,.13)*window(t,.23,.88,.16)
    # High-frequency creasing in the real previous mesh is not present in the F50 photo.
    relax_z_on_source_edges(o,region,passes=3,strength=.28,cap=.0018)
    for v in verts:
        u=(v.co.x-x0)/sx;t=(v.co.y-y0)/sy
        w=region(v.co)
        arc=.730-.059*(2*u-1)**2
        # F50 broad single main dash eyebrow and slim shaded return.
        brow=math.exp(-((t-arc)/.056)**4)*math.exp(-((u-.5)/.42)**6)
        underside=math.exp(-((t-(arc-.075))/.025)**2)*math.exp(-((u-.5)/.40)**6)
        v.co.z+=w*(.00078*brow-.00046*underside)
    o.data.update()
    moved=sum(math.dist(tuple(v.co),p)>1e-6 for v,p in zip(verts,before))
    depth=max(math.dist(tuple(v.co),p) for v,p in zip(verts,before))
    o["source_edit_scope"]="F50 C v16_r2 original game visor dent/zigzag geometric relaxation and F50 photo single eyebrow physical contour"
    return moved,depth

def sculpt_original_wheel(o):
    """Original F50 three-spoke wheel, grip profile and spoke-shoulder smoothing; no hole fill."""
    verts=o.data.vertices
    before=[tuple(v.co) for v in verts]
    def region(co):
        x,y,z=co;r=math.hypot(x,y)
        face=window(z,-.018,.025,.008)
        rim=math.exp(-((r-.154)/.026)**4)
        spoke=math.exp(-((abs(x)-.108)/.039)**4)*math.exp(-((y+.019)/.039)**4)
        lower=math.exp(-(x/.050)**4)*math.exp(-((y+.100)/.060)**4)
        return min(1.,(rim*.62+spoke*.40+lower*.31)*(.28+.72*face))
    relax_z_on_source_edges(o,region,passes=2,strength=.20,cap=.00065)
    for v in verts:
        x,y,z=v.co
        r=math.hypot(x,y)
        if r<1e-8:continue
        a=math.atan2(y,x)
        up=math.exp(-(math.atan2(math.sin(a-math.pi/2),math.cos(a-math.pi/2))/.49)**4)
        side=math.exp(-(math.atan2(math.sin(a-math.pi*.19),math.cos(a-math.pi*.19))/.31)**4)+math.exp(-(math.atan2(math.sin(a-math.pi*.81),math.cos(a-math.pi*.81))/.31)**4)
        rim=math.exp(-((r-.154)/.021)**4)
        # Source positions only; improve rim handhold transition, no new perfect torus.
        dr=(.00067*up+.00056*side)*rim
        v.co.x+=dr*x/r;v.co.y+=dr*y/r
        arms=math.exp(-((abs(x)-.111)/.031)**4)*math.exp(-((y+.018)/.036)**4)
        lower=math.exp(-(x/.043)**4)*math.exp(-((y+.104)/.040)**4)
        v.co.z+=(.00064*arms+.00051*lower)*window(z,-.015,.022,.007)
    o.data.update()
    moved=sum(math.dist(tuple(v.co),p)>1e-6 for v,p in zip(verts,before))
    depth=max(math.dist(tuple(v.co),p) for v,p in zip(verts,before))
    o["source_edit_scope"]="F50 C v16_r2 source three-spoke shoulder transition and upper/lateral rim actual surface contours; source 624 open edges retained"
    return moved,depth

def sculpt_original_hub(o):
    """Existing F50 wheel boss: flatten inherited pinched horn face and define authentic seat."""
    verts=o.data.vertices
    before=[tuple(v.co) for v in verts]
    def region(co):
        x,y,z=co;r=math.hypot(x,y+.019)
        return window(z,-.006,.014,.004)*math.exp(-(r/.076)**6)
    relax_z_on_source_edges(o,region,passes=3,strength=.20,cap=.00075)
    for v in verts:
        x,y,z=v.co
        r=math.hypot(x,y+.019)
        face=region(v.co)
        seat=math.exp(-((r-.030)/.0055)**2)
        center=math.exp(-(r/.019)**6)
        outer=math.exp(-((r-.059)/.008)**2)
        v.co.z+=face*(.00041*seat-.00025*center+.00030*outer)
    o.data.update()
    moved=sum(math.dist(tuple(v.co),p)>1e-6 for v,p in zip(verts,before))
    depth=max(math.dist(tuple(v.co),p) for v,p in zip(verts,before))
    o["source_edit_scope"]="F50 C v16_r2 original 3-spoke metal hub crease reduction and photo-referenced circular boss seat; no emblem or new objects"
    return moved,depth

def render(scene,root,tag,cam,visible):
 old={o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
 prev_camera=scene.camera;eng=scene.render.engine;prev_path=scene.render.filepath
 res=(scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage)
 try:
  scene.render.engine="BLENDER_WORKBENCH"
  scene.render.image_settings.file_format="PNG"
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=800,560,100
  scene.camera=bpy.data.objects[cam]
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=o.name not in visible
  f=Path(str(root)+"_"+tag+".png")
  scene.render.filepath=str(f)
  bpy.ops.render.render(write_still=True)
  assert f.is_file() and f.stat().st_size>10000
  return {"filename":str(f),"sha256":sha(f)}
 finally:
  for o in bpy.data.objects:
   if o.type=="MESH":o.hide_render=old[o.name]
  scene.camera=prev_camera;scene.render.engine=eng;scene.render.filepath=prev_path
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=res
def run():
 p=argparse.ArgumentParser()
 for key in ("native","original-import","input","output","report","render-root"):
  p.add_argument("--"+key,required=True,type=Path)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 assert bpy.app.version[:3]==(4,5,15),bpy.app.version_string
 assert a.native.is_file() and sha(a.native)==PMT_SHA,"BLOCKED_INPUT native PMT provenance mismatch"
 assert a.original_import.is_file() and sha(a.original_import)==IMPORT_SHA,"BLOCKED_INPUT true original import missing"
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT verified immutable v15 original-derived Blender input missing"
 assert not a.output.exists() and not a.report.exists(),"No overwrite of immutable checkpoint"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==45
 originals={o.name:o for o in bpy.data.objects if o.type=="MESH"}
 assert len(originals)==42 and all(o.get("outrun_original_mesh_object_id") for o in originals.values())
 before={name:snapshot(o) for name,o in originals.items()}
 for name,(source,v,f,expected_sha) in TARGETS.items():
  b=before[name]
  assert (b["id"],b["verts"],b["faces"],b["mesh_sha256"])==(source,v,f,expected_sha),name
  assert b["pmt"]==PMT_SHA
 cameras={o.name:(tuple(round(float(v),9) for row in o.matrix_world for v in row),o.data.type,round(float(o.data.lens),9)) for o in bpy.data.objects if o.type=="CAMERA"}
 views=[
 ("GAUGE","QA_F50_GAUGE_DETAIL_NON_GAME",["PMT_F50_object00_group01_material028_a0"]),
 ("STEERING","QA_F50_STEERING_LOCAL_NON_GAME",["PMT_F50_object21_group00_material000_a0","PMT_F50_object21_group01_material001_a0","PMT_F50_object21_group01_material002_a0"])]
 renders={}
 for label,camera,objects in views:
  renders["before_"+label]=render(scene,a.render_root,"BEFORE_"+label,camera,objects)
 changes={}
 for name,func in zip(TARGETS,(sculpt_original_hood,sculpt_original_wheel,sculpt_original_hub)):
  moved,depth=func(originals[name])
  assert moved>150 and depth>(.0002 if 'group00_material000' in name else .0005),(name,moved,depth)
  changes[name]={"moved_vertices":moved,"max_local_deformation_m":round(depth,8)}
 after={name:snapshot(o) for name,o in originals.items()}
 for name in before:
  b,c=before[name],after[name]
  assert b["id"]==c["id"] and b["pmt"]==c["pmt"]==PMT_SHA
  assert (b["verts"],b["faces"],b["matrix"],b["uv"],b["materials"],b["nonmanifold"])==(c["verts"],c["faces"],c["matrix"],c["uv"],c["materials"],c["nonmanifold"])
  if name not in TARGETS:assert b==c,"Outside original cockpit mesh unexpectedly edited: "+name
  else:assert b["mesh_sha256"]!=c["mesh_sha256"],name
 assert all(cameras[o.name]==(tuple(round(float(v),9) for row in o.matrix_world for v in row),o.data.type,round(float(o.data.lens),9)) for o in bpy.data.objects if o.type=="CAMERA")
 scene["geometry_edit_count"]=48
 scene["slot_c_last_geometry_stage"]="F50_P0_V16_R2_SOURCE_DASH_RELAX_WHEEL_SHOULDER_HUB"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V16_R2_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v15_blend_sha256":INPUT_SHA,"new_private_v16_r2_blend_path":str(a.output),
 "new_private_v16_r2_blend_sha256":sha(a.output),
 "original_source_meshes":42,"changed_original_source_meshes":{
  n:{"original_id":before[n]["id"],"before":before[n],"after":after[n],"deformation":changes[n]} for n in TARGETS},
 "untouched_other_original_source_meshes":39,"all_42_original_ids_preserved":True,
 "unchanged_object_camera_transforms":True,"unchanged_UV_materials":True,
 "source_pmt_untouched":True,"source_geometry_nonmanifold_unchanged":True,
 "paired_real_blender_render":renders,
 "photo_reference":["03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg","03_F50/01_interior.jpg","03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg"],
 "photo_use":"qualitative morphology only; no game-calibrated driver-eye",
 "full_7_photo_view_match":"INCOMPLETE","native_driver_eye":"UNVERIFIED",
 "github_hosted_original_scene":"BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED",
 "new_car_objects":0,"external_body_wheels_tires_edit":False,
 "created_textures_PBR_normal_maps":False,"game_export_PMT_OVC_OVC3":False,"VR_Model2_Dino_slotA_change":False,
 "complete":False}
 a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf8")
 print("F50_SLOTC_V16_R2_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v16_r2_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()
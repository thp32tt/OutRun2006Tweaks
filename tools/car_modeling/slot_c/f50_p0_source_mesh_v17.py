#!/usr/bin/env python3
"""F50 Slot C P0 v17: real native PMT-derived existing cockpit-mesh surface refinement.
Does NOT add car objects/GLB, materials, textures, game formats or exterior changes.
Requires the exact read-only original PMT and verified first import, then edits the immutable v16_r2 source-derived .blend.
"""
import bpy,bmesh,math,hashlib,json,struct,sys,argparse
from pathlib import Path
PMT_SHA="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
IMPORT_SHA="d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31"
INPUT_SHA="2522b73c2147866fbf2571a9b29506463f8baa17fe2cb12e8012a1b15668e5b3"
TARGETS={
 "PMT_F50_object00_group01_material028_a0":("object00_group01_material028_a0",5506,7552,"f04fff21e8e442ce88ee8cf7bb4b9ae75fbee1380456abda329eaef15ab33ccb"),
 "PMT_F50_object21_group01_material002_a0":("object21_group01_material002_a0",13552,26496,"09b7c5ed07b81057eaa73b04f48bdce465c066282be4c440eeffe2d684a7f1f3"),
 "PMT_F50_object21_group00_material000_a0":("object21_group00_material000_a0",2738,4464,"faa770ac728485d8a26ec9d3b51ba066b207a1afe35e582e7ed9f8391beb4e6c")}
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



def soft_cap_source_z(o, region, steps, strength, cap):
    """Constrained original topological fan smoothing, no vertex/face/material changes."""
    mesh=o.data
    ref=[float(v.co.z) for v in mesh.vertices]
    adjacency=[[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a,b=edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    boundary={vert.index for edge in bm.edges if not edge.is_manifold for vert in edge.verts}
    bm.free()
    for _ in range(steps):
        old=[tuple(float(v) for v in vert.co) for vert in mesh.vertices]
        change={}
        for i,co in enumerate(old):
            if i in boundary or len(adjacency[i])<3:
                continue
            mask=region(co)
            if mask<=1e-5:
                continue
            z=co[2]
            weighted=0.
            total=0.
            for j in adjacency[i]:
                near=old[j]
                dist=math.hypot(co[0]-near[0],co[1]-near[1])
                dz=abs(z-near[2])
                weight=math.exp(-((dist/.024)**2))*math.exp(-((dz/.009)**2))
                weighted+=weight*near[2]
                total+=weight
            if total>1e-6:
                value=z+strength*mask*((weighted/total)-z)
                change[i]=max(ref[i]-cap,min(ref[i]+cap,value))
        for i,value in change.items():
            mesh.vertices[i].co.z=value
    mesh.update()

def sculpt_original_hood(o):
    """Keep original F50 gauge cowl; recover a broad overhang and tame fan highlights."""
    vs=o.data.vertices
    original=[tuple(float(c) for c in v.co) for v in vs]
    xmin,xmax=min(v.co.x for v in vs),max(v.co.x for v in vs)
    ymin,ymax=min(v.co.y for v in vs),max(v.co.y for v in vs)
    sx=max(1e-8,xmax-xmin);sy=max(1e-8,ymax-ymin)
    def normalized(co):
        return ((co[0]-xmin)/sx,(co[1]-ymin)/sy)
    def region(co):
        u,t=normalized(co)
        return window(u,.075,.925,.115)*window(t,.23,.90,.13)
    # The last checkpoint's spoke-like cowl artifacts follow irregular native edge fans.
    # Smooth only existing connected sheet vertices; bounded displacement retains overhang.
    soft_cap_source_z(o,region,steps=4,strength=.30,cap=.00125)
    for v in vs:
        u,t=normalized(v.co)
        mask=region(v.co)
        # Single broad eyebrow, shallower inner aperture, with a smooth lateral roll-off.
        ridge=.717-.075*(2*u-1)**2
        brow=math.exp(-((t-ridge)/.075)**4)*math.exp(-((u-.5)/.425)**6)
        shadow=math.exp(-((t-(ridge-.087))/.032)**4)*math.exp(-((u-.5)/.365)**6)
        v.co.z+=mask*(.00102*brow-.00078*shadow)
    o.data.update()
    move=sum(math.dist(tuple(v.co),p)>1e-6 for v,p in zip(vs,original))
    maxdelta=max(math.dist(tuple(v.co),p) for v,p in zip(vs,original))
    o["source_edit_scope"]="F50 slot C v17 original imported dashboard visor brow/undercut: photo-guided original-edge physical geometry only"
    return move,maxdelta

def sculpt_original_wheel(o):
    """Existing factory three-spoke wheel and leather rim in place, source holes preserved."""
    vs=o.data.vertices
    original=[tuple(float(c) for c in v.co) for v in vs]
    def region(co):
        x,y,z=co
        r=math.hypot(x,y)
        ring=math.exp(-((r-.153)/.025)**4)
        shoulder=math.exp(-((abs(x)-.108)/.038)**4)*math.exp(-((y+.020)/.039)**4)
        lower=math.exp(-(x/.041)**4)*math.exp(-((y+.102)/.053)**4)
        return min(1.,(ring*.56+shoulder*.38+lower*.26)*window(z,-.017,.024,.007))
    soft_cap_source_z(o,region,steps=3,strength=.21,cap=.00067)
    for v in vs:
        x,y,z=v.co
        r=math.hypot(x,y)
        if r<1e-8:continue
        angle=math.atan2(y,x)
        def lobe(target,width):
            return math.exp(-(math.atan2(math.sin(angle-target),math.cos(angle-target))/width)**4)
        top=lobe(math.pi/2,.50)
        side=lobe(math.pi*.18,.29)+lobe(math.pi*.82,.29)
        ring=math.exp(-((r-.154)/.019)**4)
        # Source rim becomes slightly fuller at 10 and 2, while keeping factory wheel radius.
        dr=(.00087*side+.00052*top)*ring
        v.co.x+=dr*x/r;v.co.y+=dr*y/r
        edge=window(z,-.016,.023,.008)
        spokes=math.exp(-((abs(x)-.107)/.034)**4)*math.exp(-((y+.022)/.037)**4)
        neck=math.exp(-(x/.046)**4)*math.exp(-((y+.103)/.035)**4)
        groove=math.exp(-((abs(x)-.142)/.008)**2)*math.exp(-((y+.017)/.031)**4)
        v.co.z+=edge*(.00104*spokes+.00078*neck-.00030*groove)
    o.data.update()
    moved=sum(math.dist(tuple(v.co),p)>1e-6 for v,p in zip(vs,original))
    peak=max(math.dist(tuple(v.co),p) for v,p in zip(vs,original))
    o["source_edit_scope"]="F50 slot C v17 original rim cross-section and factory left/right/lower spoke-to-rim roll; open steering edge loops untouched"
    return moved,peak

def sculpt_original_hub(o):
    """Original integrated horn cup with 6 source-mesh bolt bosses: no fabricated asset."""
    vs=o.data.vertices
    original=[tuple(float(c) for c in v.co) for v in vs]
    def region(co):
        x,y,z=co
        r=math.hypot(x,y+.019)
        return math.exp(-(r/.075)**6)*window(z,-.005,.012,.0032)
    soft_cap_source_z(o,region,steps=2,strength=.17,cap=.00053)
    locations=[(.049*math.cos(math.radians(a)), -.019+.049*math.sin(math.radians(a))) for a in (30,90,150,210,270,330)]
    for v in vs:
        x,y,z=v.co
        r=math.hypot(x,y+.019)
        gate=region(v.co)
        # Seat the original central horn disc and existing circular hub rim.
        disk=math.exp(-(r/.0185)**6)
        bead=math.exp(-((r-.029)/.0055)**2)
        relief=math.exp(-((r-.043)/.0060)**2)
        dz=-.00031*disk+.00078*bead-.00039*relief
        for cx,cy in locations:
            d=math.hypot(x-cx,y-cy)
            dz+=-.00031*math.exp(-(d/.0065)**2)+.00015*math.exp(-((d-.012)/.0042)**2)
        v.co.z+=dz*gate
    o.data.update()
    moved=sum(math.dist(tuple(v.co),p)>1e-6 for v,p in zip(vs,original))
    peak=max(math.dist(tuple(v.co),p) for v,p in zip(vs,original))
    o["source_edit_scope"]="F50 slot C v17 existing metal hub central circular seat and factory 6 fastener relief; no object addition"
    return moved,peak


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
 assert a.input.is_file() and sha(a.input)==INPUT_SHA,"BLOCKED_INPUT verified immutable v16_r2 original-derived Blender input missing"
 assert not a.output.exists() and not a.report.exists(),"No overwrite of immutable checkpoint"
 assert Path(bpy.data.filepath).resolve()==a.input.resolve()
 scene=bpy.context.scene
 assert scene.get("outrun_original_game_resource_sha256")==PMT_SHA
 assert scene.get("geometry_edit_count")==48
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
 scene["geometry_edit_count"]=51
 scene["slot_c_last_geometry_stage"]="F50_P0_V17_PHOTO_GUIDED_SOURCE_BROW_RIM_SPOKE_HUB"
 scene["slot_c_input_blend_sha256"]=INPUT_SHA
 scene["slot_c_native_pmt_sha256"]=PMT_SHA
 bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
 for label,camera,objects in views:
  renders["after_"+label]=render(scene,a.render_root,"AFTER_"+label,camera,objects)
 assert sha(a.native)==PMT_SHA and sha(a.original_import)==IMPORT_SHA and sha(a.input)==INPUT_SHA
 report={"result":"F50_SLOTC_V17_NATIVE_SOURCE_MESH_SCULPT_SAVED_LOCAL_INDEPENDENT_QA_REQUIRED",
 "blender":bpy.app.version_string,"original_pmt_sha256":PMT_SHA,"original_import_sha256":IMPORT_SHA,
 "previous_v16_r2_blend_sha256":INPUT_SHA,"new_private_v17_blend_path":str(a.output),
 "new_private_v17_blend_sha256":sha(a.output),
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
 print("F50_SLOTC_V17_TRUE_ORIGINAL_GEOMETRY_SAVED",report["new_private_v17_blend_sha256"],[(n,after[n]["verts"],after[n]["faces"],changes[n]["moved_vertices"]) for n in TARGETS])
if __name__=="__main__":run()
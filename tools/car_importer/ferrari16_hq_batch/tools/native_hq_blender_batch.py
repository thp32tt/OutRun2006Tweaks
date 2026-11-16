import bpy, sys, json, math, hashlib, os
from pathlib import Path
args = sys.argv[sys.argv.index("--")+1:]
root = Path(args[0]).resolve()
out_root = Path(args[1]).resolve()
cars = ["250gto","288gto","328gts","360spider","512bb","550barchetta","575superamerica","daytona365","dino246gts","enzo","f355spider","f40","f430","f430spider","f50","testarossa"]
out_root.mkdir(parents=True, exist_ok=True)
summary=[]
def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
for car in cars:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src = root/car/"01_original_mesh_uv"/"original_native.obj"
    if not src.is_file():
        summary.append({"car":car,"status":"SOURCE_MISSING"}); continue
    bpy.ops.wm.obj_import(filepath=str(src), use_split_objects=True, use_split_groups=True)
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    if not meshes:
        summary.append({"car":car,"status":"IMPORT_EMPTY"}); continue
    total_v=sum(len(o.data.vertices) for o in meshes)
    total_p=sum(len(o.data.polygons) for o in meshes)
    mins=[1e30]*3; maxs=[-1e30]*3
    for o in meshes:
        for c in o.bound_box:
            w=o.matrix_world @ __import__('mathutils').Vector(c)
            for i in range(3):
                mins[i]=min(mins[i],w[i]); maxs[i]=max(maxs[i],w[i])
    diag=math.sqrt(sum((maxs[i]-mins[i])**2 for i in range(3)))
    modified=0
    for o in meshes:
        if len(o.data.vertices)<8: continue
        for p in o.data.polygons: p.use_smooth=True
        od=max((o.dimensions.x**2+o.dimensions.y**2+o.dimensions.z**2)**0.5,1e-6)
        width=min(diag*0.00035, od*0.006)
        if width>1e-6:
            bev=o.modifiers.new("OR2_HQ_EDGE_BEVEL","BEVEL")
            bev.width=width
            bev.segments=2
            bev.limit_method='ANGLE'
            bev.angle_limit=math.radians(36)
            bev.affect='EDGES'
            modified+=1
        try:
            wn=o.modifiers.new("OR2_HQ_WEIGHTED_NORMAL","WEIGHTED_NORMAL")
            wn.keep_sharp=True
            wn.weight=50
        except Exception:
            pass
    car_out=out_root/car
    car_out.mkdir(parents=True, exist_ok=True)
    blend=car_out/f"{car}_NativeHQ_v1.blend"
    glb=car_out/f"{car}_NativeHQ_v1.glb"
    try:
        bpy.ops.file.pack_all()
    except Exception:
        pass
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    export_kwargs=dict(filepath=str(glb), export_format='GLB', export_materials='EXPORT',
                       export_texcoords=True, export_normals=True, export_yup=True)
    try:
        bpy.ops.export_scene.gltf(export_apply=True, **export_kwargs)
    except TypeError:
        bpy.ops.export_scene.gltf(**export_kwargs)
    deps=bpy.context.evaluated_depsgraph_get()
    eval_v=eval_p=0
    for o in meshes:
        eo=o.evaluated_get(deps)
        try:
            me=eo.to_mesh()
            eval_v+=len(me.vertices); eval_p+=len(me.polygons)
            eo.to_mesh_clear()
        except Exception:
            pass
    manifest={
      "schema":1,"car":car,"status":"NATIVE_HQ_BLEND_GLB_PASS_NOT_GAME_TESTED",
      "source_obj":str(src.relative_to(root.parent.parent)),
      "source_sha256":sha256(src),"source_vertices":total_v,"source_polygons":total_p,
      "mesh_objects":len(meshes),"model_diagonal":diag,"modified_objects":modified,
      "enhancement":["smooth_shading","angle_limited_2segment_bevel","weighted_normals_when_supported"],
      "uv_material_policy":"preserve imported OBJ UV/materials; no decimation; no topology deletion",
      "evaluated_vertices":eval_v,"evaluated_polygons":eval_p,
      "blend_sha256":sha256(blend),"glb_sha256":sha256(glb),
      "blend_bytes":blend.stat().st_size,"glb_bytes":glb.stat().st_size,
      "dashboard_runtime":"OVRCABH4-ready; per-car needle binding still requires verified needle component calibration",
      "runtime_tested":False
    }
    (car_out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    summary.append(manifest)
(out_root/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("FERRARI16_NATIVE_HQ_DONE",sum(x.get("status","").startswith("NATIVE_HQ") for x in summary),"/",len(cars))
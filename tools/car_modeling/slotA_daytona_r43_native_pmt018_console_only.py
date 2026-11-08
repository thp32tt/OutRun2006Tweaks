#!/usr/bin/env python3
"""SLOT A Daytona: source-PMT018 guided edit of existing center tunnel ONLY.
Loads genuine original OutRun PMT import as read-only geometry reference.
No extra mesh, new materials, PBR, game integration, dashboard or wheel edits.
"""
import array, hashlib, json, subprocess, sys
from pathlib import Path

R = Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
BL = Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender-4.5.15-linux-x64/blender")
NATIVE_PMT = Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
NATIVE_IMPORT = Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
BASE = R / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v40_r42.blend"
OUTPUT = R / "Daytona365_SlotA_OriginalPMT018_CenterConsole_R43.blend"
AUDIT = R / "SLOTA_R43_CENTER_CONSOLE_NATIVE_GEOMETRY_AUDIT.json"
REOPEN = R / "SLOTA_R43_CENTER_CONSOLE_REOPEN_QA.json"
PHOTO1 = Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/REF9_transmission_01_b09482c09.jpg")
PHOTO2 = Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/REF5_mecum_interior_04_1f06efa94.jpg")
TARGET = "V8_LOW_CENTER_TUNNEL"
NATIVE_NAME = "object00_group01_material018_a0"
EXPECTED = {
    "pmt": "f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
    "native_import": "92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
    "input_r42": "55ffc5dd9c26448ffc3a076a3749319f6c1d082fd4d18ad165c6f3bcf22547f2",
}
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()
def gate():
    for key,p in (("pmt",NATIVE_PMT),("native_import",NATIVE_IMPORT),("input_r42",BASE)):
        if not p.is_file() or digest(p)!=EXPECTED[key]:
            raise RuntimeError("BLOCKED_INPUT_SHA:"+key)
    if not BL.is_file() or not PHOTO1.is_file() or not PHOTO2.is_file():
        raise RuntimeError("BLOCKED_BLENDER_OR_REAL_PHOTOS")
def signature(obj):
    """Hash the actual mesh data and UVs of each protected object, not just names."""
    mesh=obj.data;h=hashlib.sha256()
    h.update(obj.name.encode())
    for row in obj.matrix_world:
        h.update(",".join(format(float(v),".10g") for v in row).encode())
    h.update(str((obj.hide_render,obj.hide_viewport)).encode())
    h.update(str(tuple(mat.name if mat else None for mat in mesh.materials)).encode())
    h.update(str(tuple((m.name,m.type) for m in obj.modifiers)).encode())
    verts=array.array("f",[0.0])*(3*len(mesh.vertices))
    mesh.vertices.foreach_get("co",verts);h.update(verts.tobytes())
    loops=array.array("i",[0])*len(mesh.loops)
    mesh.loops.foreach_get("vertex_index",loops);h.update(loops.tobytes())
    for layer in mesh.uv_layers:
        data=array.array("f",[0.0])*(2*len(layer.data))
        layer.data.foreach_get("uv",data)
        h.update(layer.name.encode());h.update(data.tobytes())
    return h.hexdigest()
def protected():
    import bpy
    d={o.name:signature(o) for o in bpy.data.objects if o.type=="MESH" and o.name!=TARGET}
    if len(d)!=112:raise RuntimeError("BLOCKED_UNEXPECTED_PROTECTED_MESH_COUNT:"+str(len(d)))
    return d
def native_profile():
    import bpy
    with bpy.data.libraries.load(str(NATIVE_IMPORT),link=False) as (source,dest):
        if NATIVE_NAME not in source.objects:raise RuntimeError("BLOCKED_NATIVE_PMT018_ABSENT")
        dest.objects=[NATIVE_NAME]
    obj=dest.objects[0]
    if len(obj.data.vertices)!=24 or len(obj.data.polygons)!=12:
        raise RuntimeError("BLOCKED_NATIVE_PMT018_TOPOLOGY")
    # Real original PMT018 surface vertices, not invented proportions.
    coords=[obj.matrix_world@v.co for v in obj.data.vertices]
    pairs=[(float(coords[i].y),float(coords[i].z)) for i in (7,2,0)]
    truth=[(-.198485,.416049),(-.005917,.458297),(.129182,.518870)]
    if not all(abs(p[0]-q[0])<.0001 and abs(p[1]-q[1])<.0001 for p,q in zip(pairs,truth)):
        raise RuntimeError("BLOCKED_ORIGINAL_PROFILE_MISMATCH")
    bpy.data.objects.remove(obj,do_unlink=True)
    return pairs
def interp(y,pairs):
    for (ya,za),(yb,zb) in zip(pairs,pairs[1:]):
        if ya-1e-6<=y<=yb+1e-6:
            t=max(0.,min(1.,(y-ya)/(yb-ya)))
            return za+(zb-za)*t
    return None
def build():
    import bpy
    gate()
    if not bpy.app.version_string.startswith("4.5.15") or Path(bpy.data.filepath).resolve()!=BASE.resolve():
        raise RuntimeError("BLOCKED_WRONG_BLENDER_OR_SCENE")
    if any(p.exists() for p in (OUTPUT,AUDIT,REOPEN)):
        raise RuntimeError("BLOCKED_IMMUTABLE_OUTPUT_EXISTS")
    objects_before=sorted(o.name for o in bpy.data.objects)
    protected_before=protected()
    obj=bpy.data.objects.get(TARGET)
    if not obj or obj.type!="MESH" or len(obj.data.vertices)!=78 or len(obj.data.polygons)!=74:
        raise RuntimeError("BLOCKED_TARGET_BASE_TOPOLOGY")
    # Existing target mesh: material, faces, UV, pivots preserved in place.
    target_before=signature(obj)
    material_before=tuple(x.name if x else None for x in obj.data.materials)
    uv_before=tuple(l.name for l in obj.data.uv_layers)
    native=native_profile()
    moved=0;max_move=0.;mean=0.;records=[]
    verts=obj.data.vertices
    for start in range(0,len(verts),6):
        row=list(verts[start:start+6])
        if len(row)!=6:raise RuntimeError("BLOCKED_TARGET_ROW_LAYOUT")
        y=float(row[2].co.y)
        old_ridge=(float(row[2].co.z)+float(row[3].co.z))*.5
        src=interp(y,native)
        if src is None:continue
        source_shortfall=max(0.,src-old_ridge)
        if source_shortfall<.004:continue
        ridge_delta=min(.040,source_shortfall*.90)
        for j in (1,2,3,4):
            v=row[j]
            weight=1.0 if j in (2,3) else .57
            displacement=ridge_delta*weight
            if displacement<.003:continue
            old=float(v.co.z)
            v.co.z+=displacement
            moved+=1
            max_move=max(max_move,displacement)
            mean+=displacement
            records.append({"index":start+j,"y":round(y,6),"before_z":round(old,6),
                            "after_z":round(float(v.co.z),6),"native_top_z":round(src,6)})
    obj.data.update()
    if moved<15 or not (.017<max_move<=.040):
        raise RuntimeError("BLOCKED_NO_MEANINGFUL_SOURCE_GEOMETRY:"+str((moved,max_move)))
    if tuple(x.name if x else None for x in obj.data.materials)!=material_before:
        raise RuntimeError("BLOCKED_MATERIAL_DRIFT")
    if tuple(l.name for l in obj.data.uv_layers)!=uv_before:
        raise RuntimeError("BLOCKED_UV_LAYER_DRIFT")
    if sorted(o.name for o in bpy.data.objects)!=objects_before:
        raise RuntimeError("BLOCKED_SCENE_OBJECT_ADDITION")
    protected_after=protected()
    if protected_before!=protected_after:raise RuntimeError("BLOCKED_OTHER_112_MESH_MUTATED")
    target_after=signature(obj)
    if target_before==target_after:raise RuntimeError("BLOCKED_NO_EDIT")
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
    if not OUTPUT.is_file() or OUTPUT.stat().st_size<1000000:
        raise RuntimeError("BLOCKED_BLEND_SAVE")
    audit={"task_id":"FERRARI16-SLOTA-DAYTONA-PMT018-CENTER-CONSOLE-R43-20261109",
       "slot":"A","car_id":"daytona365","component":"center_console",
       "source_native_object":NATIVE_NAME,"native_24v_12f_yz_profile":native,
       "original_pmt_sha256":EXPECTED["pmt"],"original_import_sha256":EXPECTED["native_import"],
       "input_r42_sha256":EXPECTED["input_r42"],"output_r43_sha256":digest(OUTPUT),
       "actual_edited_existing_mesh":TARGET,"vertices":len(obj.data.vertices),
       "faces":len(obj.data.polygons),"moved_existing_vertices":moved,
       "max_displacement_m":max_move,"mean_displacement_m":mean/moved,
       "changed_vertices":records,"target_before_sha256":target_before,
       "target_after_sha256":target_after,
       "protected_112_mesh_signatures":protected_before,
       "photo_transmission_sha256":digest(PHOTO1),"photo_cockpit_sha256":digest(PHOTO2),
       "new_geometry_objects":0,"new_materials_or_textures":0,"pmt_ovc_ovc3_exports":0,
       "render_evidence":"NOT_PRODUCED_HEAVY_HOST_LOAD",
       "calibrated_game_eye":"BLOCKED","seven_photos":"INCOMPLETE",
       "whole_car_qa_pass":False}
    AUDIT.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf8")
    print("R43_NATIVE_CENTER_CONSOLE_SAVED",json.dumps({"output_sha256":audit["output_r43_sha256"],"moved":moved,"max_m":max_move}),flush=True)
def verify():
    import bpy
    gate()
    if Path(bpy.data.filepath).resolve()!=OUTPUT.resolve() or not AUDIT.is_file():
        raise RuntimeError("BLOCKED_NEW_BLEND_REOPEN")
    a=json.loads(AUDIT.read_text())
    if a["output_r43_sha256"]!=digest(OUTPUT):raise RuntimeError("BLOCKED_REOPEN_DISK_SHA")
    if a["protected_112_mesh_signatures"]!=protected():raise RuntimeError("BLOCKED_112_MESH_REOPEN_DRIFT")
    obj=bpy.data.objects[TARGET]
    if signature(obj)!=a["target_after_sha256"]:raise RuntimeError("BLOCKED_TARGET_REOPEN_DRIFT")
    if len(obj.data.vertices)!=78 or len(obj.data.polygons)!=74:
        raise RuntimeError("BLOCKED_TARGET_TOPOLOGY_REOPEN")
    proof={"result":"PASS_INDEPENDENT_BLENDER_SAVE_REOPEN",
        "source_native_PMT018":a["source_native_object"],
        "output_sha256":a["output_r43_sha256"],
        "changed_existing_meshes":1,"protected_other_meshes":112,
        "coverage_state":"COVERED_PARTIAL_QA",
        "pending_visual_QA":"MATCHED_CAMERA_AND_SEVEN_AUTHENTIC_PHOTO_VIEWS",
        "vehicle_qa_pass":False,"next_component":"driver_controls"}
    REOPEN.write_text(json.dumps(proof,indent=2)+"\n",encoding="utf8")
    print("R43_SOURCE_CONSOLE_REOPEN_PASS",json.dumps(proof),flush=True)
def main():
    if "--inside-build" in sys.argv:build();return
    if "--inside-verify" in sys.argv:verify();return
    gate()
    for stage in ("--inside-build","--inside-verify"):
        cmd=[str(BL),"--background",str(BASE if stage=="--inside-build" else OUTPUT),
             "--threads","1","--python",str(Path(__file__).resolve()),"--",stage]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=220)
        print((p.stdout+"\n"+p.stderr)[-6000:],flush=True)
        if p.returncode:raise RuntimeError("BLOCKED_BLENDER_SUBPROCESS:"+stage+":"+str(p.returncode))
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Ferrari Daytona slot A R18: original PMT-derived, in-place P0 geometry sculpt.
ONLY input: SHA-pinned original game PMT and imported .blend, plus the verified R17
editable private .blend. ONLY output: immutable new private R18 .blend and audit.
Never exports or converts native assets, GLB, OVC/OVC3/PMT, or touches game/VR.
No new objects, textures, PBR, image or material edits; all other car meshes fixed.
"""
from pathlib import Path
import bpy, bmesh, json, hashlib, math, os, sys
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slotA_daytona_r17_original_spider_p0_sculpt as r17

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
OLD=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v15_r17.blend"
NEW=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v16_r18.blend"
LAST=ROOT/"SLOT_A_DAYTONA_P0_R17_PHOTO_GUIDED_NATIVE_GEOMETRY.json"
AUDIT=ROOT/"SLOT_A_DAYTONA_P0_R18_NATIVE_DASH_SPOKE_RELIEF_GEOMETRY.json"
QA=ROOT/"SLOTA_R18_REAL_SOURCE_REOPEN_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R18_AFTER_REAL_CYCLES_APPROX_EYE.png"
SOURCE_HASH="93b3d1ee0a6c6e0828a2b9103cae52009cd0984893cbe81314684f61a9e4726a"
PHOTO_HASH="6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"
prior=r17.prior
smooth=prior.smooth
sha=prior.sha
state=prior.state

def gate():
    assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT_BLENDER_4_5_15_REQUIRED"
    assert OLD.is_file() and sha(OLD)==SOURCE_HASH,"BLOCKED_INPUT_R17_SHA"
    assert sha(prior.PMT)==prior.EXPECTED["pmt"],"BLOCKED_INPUT_ORIGINAL_PMT_SHA"
    assert sha(prior.IMP)==prior.EXPECTED["import"],"BLOCKED_INPUT_ORIGINAL_IMPORT_SHA"
    assert sha(prior.PHOTO)==PHOTO_HASH,"BLOCKED_INPUT_SPIDER_REFERENCE_SHA"
    assert LAST.is_file(),"BLOCKED_INPUT_R17_PROVENANCE"
    last=json.loads(LAST.read_text(encoding="utf-8"))
    assert last["r17_output_sha256"]==SOURCE_HASH
    assert last["original_object_names"]==["object00_group01_material012_a0","object22_group00_material000_a0"]
    # The original importer is verified by filename/hash. These derived meshes
    # have retained, verifiable lineage but are NOT byte-identical raw PMT faces.
    assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
    assert len(bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0"].data.vertices)==9720
    return last

def sculpt(part,p):
    dx=dy=dz=0.
    if part=="dashboard":
        # Photo: broad padded dash with a softened top front transition.
        span=smooth(-.631,-.565,p.x)*(1-smooth(-.135,-.074,p.x))
        crown=smooth(.768,.808,p.z)*(1-smooth(.917,.957,p.z))
        front=1-smooth(.164,.249,p.y)
        emphasis=.67+.33*math.exp(-((p.x+.352)/.17)**4)
        dz=-.00265*span*crown*front*emphasis
        dy=.00135*span*crown*front
    elif part=="cowl":
        # Ref photo has a thin instrument brow, not a high white centre crest.
        width=smooth(-.624,-.576,p.x)*(1-smooth(-.119,-.069,p.x))
        front=1-smooth(.132,.223,p.y)
        arc=math.exp(-((p.x+.348)/.175)**4)
        high=smooth(.907,.966,p.z)
        dz=-.0038*width*front*arc*(.35+.65*high)
        dy=-.0022*width*front*arc
    elif part=="bezel":
        # Pressed metal: softly taper existing bezel rings' front shoulders.
        band=math.exp(-((p.y-.1504)/.0028)**2)
        shoulder=math.exp(-((p.y-.1544)/.0021)**2)
        dy=-.00088*band+.00043*shoulder
        dz=.00028*band*math.tanh((p.z-.824)/.036)
    elif part=="spoke":
        # Existing factory-derived 3-spoke pressing, 8 physical holes remain
        # untouched at their centres. Bend OUTER metal toward photo while
        # preserving hub and each perforation's zero-metal opening.
        holes=[math.hypot(p.x-x,p.z-z)/r for x,z,r in prior.HOLES]
        clear=smooth(1.045,1.64,min(holes))
        xdist=abs(p.x+.350)
        outer=smooth(.068,.160,xdist)
        upper=math.exp(-((p.z-.797)/.047)**4)
        facing=math.exp(-((p.y+.287)/.030)**2)
        lip=max(math.exp(-((d-1.39)/.26)**2) for d in holes)
        dz=.00255*outer*upper*facing*clear
        dy=-.00165*lip*facing*clear + .00115*outer*upper*facing*clear
        # Lower vertical spoke transitions to the hub without shifting pivot.
        lower=(1-smooth(.763,.809,p.z))*smooth(.690,.716,p.z)
        dx=-.032*(p.x+.350)*lower*clear
    elif part=="rim":
        # Reduce oversized cross section at steering top and lower-left
        # without moving the nominal rim path, diameter or source pivot.
        ux=p.x+.350
        vz=p.z-.792
        radius=math.hypot(ux,vz)
        if radius>.06:
            tube=radius-.1740
            polar=math.atan2(vz,ux)
            mod=1+.13*math.cos(2*polar)
            dr=-.096*tube*mod
            dx=dr*ux/radius
            dz=dr*vz/radius
        dy=-.073*(p.y+.286)
    elif part=="hub":
        # Smooth existing metal shaft flange at the horn-button shoulder.
        radial=math.hypot(p.x+.35,p.z-.767)
        collar=math.exp(-((p.y+.249)/.011)**2)*smooth(.008,.023,radial)
        if radial>1e-6:
            dx=.00085*collar*(p.x+.35)/radial
            dz=.00085*collar*(p.z-.767)/radial
        dy=-.00105*collar
    return Vector((dx,dy,dz))

def build():
    assert Path(bpy.data.filepath).resolve()==OLD.resolve(),"BLOCKED_INPUT_R17_NOT_OPEN"
    assert not NEW.exists() and not AUDIT.exists(),"IMMUTABLE_R18_OUTPUT_COLLISION"
    previous=gate()
    objs,keep,base=prior.snapshot()
    before={part:state(obj) for part,obj in objs.items()}
    for part,entry in previous["source_derived_existing_meshes"].items():
        assert before[part]==entry["after"],("BLOCKED_SOURCE_OBJECT_MISMATCH",part)
    assert all(prior.holes(objs["spoke"])),"BLOCKED_ORIGINAL_EIGHT_HOLES"
    changes={}
    for part,obj in objs.items():
        inv=obj.matrix_world.inverted()
        moved=0;max_mm=0.;sum_mm=0.
        for vertex in obj.data.vertices:
            world=obj.matrix_world@vertex.co
            delta=sculpt(part,world)
            if delta.length<.000012:
                continue
            vertex.co=inv@(world+delta)
            mm=delta.length*1000.
            moved+=1;max_mm=max(max_mm,mm);sum_mm+=mm
        assert moved>={"dashboard":100,"cowl":300,"bezel":200,"spoke":700,"rim":5000,"hub":15}[part],("TOO_FEW_P0_VERTEX_CHANGES",part,moved)
        assert max_mm<5.2,("P0_DISPLACEMENT_OVER_LIMIT",part,max_mm)
        obj.data.update()
        after=state(obj)
        assert after["signature"]!=before[part]["signature"]
        assert (after["vertices"],after["faces"])==(before[part]["vertices"],before[part]["faces"])
        for field in ("name","matrix","uv","materials"):
            assert after[field]==before[part][field],("IDENTITY_CHANGED",part,field)
        changes[part]={"before":before[part],"after":after,"moved":moved,
                       "max_move_mm":round(max_mm,5),"avg_move_mm":round(sum_mm/moved,5)}
    prior.invariants(objs,keep,base)
    assert all(prior.holes(objs["spoke"])),"DAMAGED_STEERING_THROUGH_HOLES"
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(NEW),compress=True)
    assert NEW.stat().st_size>1000000
    result={
        "slot":"A","car":"daytona365","revision":"r18",
        "source_game_pmt":str(prior.PMT),"pmt_sha256":prior.EXPECTED["pmt"],
        "native_import":str(prior.IMP),"import_sha256":prior.EXPECTED["import"],
        "native_object_identity":["object00_group01_material012_a0","object22_group00_material000_a0"],
        "private_input_r17":str(OLD),"r17_sha256":SOURCE_HASH,
        "private_output_r18":str(NEW),"r18_sha256":sha(NEW),
        "reference_Spider_LHD_sha256":PHOTO_HASH,
        "source_derived_existing_objects":changes,
        "protected_other_107_mesh_signatures_sha256":hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest(),
        "native_through_holes_open":8,
        "existing_camera_anchors_pivots_UV_materials_images_unchanged":True,
        "original_game_asset_read_only":True,
        "no_new_car_objects_exterior_textures_PBR":True,
        "native_formats_exported":[],
        "full_seven_authentic_photo_views":"INCOMPLETE",
        "real_game_camera_calibrated":False,
        "hosted_GitHub_private_source_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
        "complete":False,"score_change":0
    }
    AUDIT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("SLOTA_R18_NATIVE_SOURCE_GEOMETRY_SAVED",json.dumps({
        "r18_sha256":result["r18_sha256"],
        "moved":{k:v["moved"] for k,v in changes.items()},
        "before_after_VF":{k:[v["before"]["vertices"],v["before"]["faces"],
                             v["after"]["vertices"],v["after"]["faces"]] for k,v in changes.items()}
    }),flush=True)

def verify():
    assert Path(bpy.data.filepath).resolve()==NEW.resolve(),"BLOCKED_R18_INDEPENDENT_OPEN"
    assert AUDIT.is_file() and not QA.exists() and not PNG.exists(),"IMMUTABLE_R18_QA_COLLISION"
    gate()
    record=json.loads(AUDIT.read_text(encoding="utf-8"))
    assert sha(NEW)==record["r18_sha256"]
    objs,keep,_=prior.snapshot()
    assert hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest()==record["protected_other_107_mesh_signatures_sha256"]
    assert all(prior.holes(objs["spoke"]))
    stats={}
    for part,obj in objs.items():
        assert state(obj)==record["source_derived_existing_objects"][part]["after"]
        bm=bmesh.new();bm.from_mesh(obj.data)
        stats[part]={"vertices":len(bm.verts),"faces":len(bm.faces),
                    "nonmanifold_edges":sum(not e.is_manifold for e in bm.edges)}
        bm.free()
        assert stats[part]["nonmanifold_edges"]=={
            "dashboard":184,"cowl":0,"bezel":932,"spoke":1597,"rim":0,"hub":0}[part]
    scene=bpy.context.scene
    tempdata=bpy.data.cameras.new("SLOTA_R18_APPROX_EYE_TEMP_NOT_SAVED")
    temp=bpy.data.objects.new("SLOTA_R18_APPROX_EYE_TEMP_NOT_SAVED",tempdata)
    scene.collection.objects.link(temp)
    temp.location=(-.35,-.92,1.055)
    target=Vector((-.24,.19,.797))
    temp.rotation_euler=(target-temp.location).to_track_quat("-Z","Y").to_euler()
    tempdata.type="PERSP";tempdata.lens=28;tempdata.clip_start=.01
    scene.camera=temp
    scene.render.engine="CYCLES";scene.cycles.device="CPU"
    scene.render.threads_mode="FIXED";scene.render.threads=2
    scene.cycles.samples=3;scene.cycles.use_denoising=True
    scene.render.resolution_x=720;scene.render.resolution_y=480
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.view_settings.exposure=-.52
    scene.render.filepath=str(PNG)
    bpy.ops.render.render(write_still=True)
    assert PNG.is_file() and PNG.stat().st_size>12000
    assert sha(NEW)==record["r18_sha256"]
    qa={"status":"REAL_PRIVATE_BLENDER_4_5_15_INDEPENDENT_FRESH_REOPEN_CYCLES_PASS",
        "slot":"A","car":"daytona365","r18_blend_sha256":sha(NEW),
        "cycles_sha256":sha(PNG),"resolution":[720,480],"samples":3,
        "geometry":stats,"original_eight_spoke_holes":8,"unmodified_other_meshes":107,
        "original_game_camera":"NOT_CALIBRATED","seven_Spider_photo_views":"INCOMPLETE",
        "GitHub_Actions_private_source_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
        "vehicle_complete":False,"score_change":0}
    QA.write_text(json.dumps(qa,indent=2),encoding="utf-8")
    print("SLOTA_R18_PRIVATE_SOURCE_INDEPENDENT_REOPEN_CYCLES_PASS",json.dumps(qa),flush=True)

if __name__=="__main__":
    mode=os.environ.get("SLOT_A_R18_MODE")
    if mode=="build":build()
    elif mode=="verify":verify()
    else:raise SystemExit("SLOT_A_R18_MODE=build|verify required")

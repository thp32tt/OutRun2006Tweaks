#!/usr/bin/env python3
"""Slot A / original OutRun 2006 Daytona cockpit R17 (geometry only).

Input: immutable, SHA-verified original Daytona PMT + native original-import .blend
       + verified existing PMT-derived R16 .blend.
Output: separate private R17 .blend, audit JSON, independent Cycles PNG.
Never exports PMT/OVC/OVC3/GLB, edits a game asset, or replaces a vehicle.
The R16 helper has the strict 107-other-object, camera/UV/material and 8-hole gates.
"""
from pathlib import Path
import bpy, bmesh, hashlib, json, math, os
from mathutils import Vector
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import slotA_daytona_r16_native_dashboard_steering as prior

ROOT=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
OLD=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v14_r16.blend"
NEW=ROOT/"Daytona365_SlotA_SourceCockpit_P0_DashWheel_v15_r17.blend"
R16_AUDIT=ROOT/"SLOT_A_DAYTONA_P0_R16_STEERING_DASH_SOURCE_GEOMETRY.json"
AUDIT=ROOT/"SLOT_A_DAYTONA_P0_R17_PHOTO_GUIDED_NATIVE_GEOMETRY.json"
QA=ROOT/"SLOTA_R17_SEPARATE_PROCESS_REAL_CYCLES.json"
PNG=ROOT/"SLOTA_DAYTONA_R17_AFTER_REAL_CYCLES_APPROX_EYE.png"
SOURCE_HASH="1af18e11637b4eb4fe8ee61d5d16b34d1ccb93a7a831bbb585e998d81d72ea49"
PHOTO_HASH="6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"
PARTS=prior.PARTS
smooth=prior.smooth
sha=prior.sha
state=prior.state

def native_guard():
    assert bpy.app.version_string.startswith("4.5.15"),"BLOCKED_INPUT_BLENDER_VERSION"
    assert OLD.is_file() and sha(OLD)==SOURCE_HASH,"BLOCKED_INPUT_R16_HASH"
    prior.source_gate()
    assert sha(prior.PMT)==prior.EXPECTED["pmt"]
    assert sha(prior.IMP)==prior.EXPECTED["import"]
    assert sha(prior.PHOTO)==PHOTO_HASH
    assert R16_AUDIT.is_file()
    previous=json.loads(R16_AUDIT.read_text())
    assert previous["output_r16_sha256"]==SOURCE_HASH
    assert previous["original_object_ids"]==["object00_group01_material012_a0","object22_group00_material000_a0"]
    return previous

def displacement(k,p):
    dx=dy=dz=0.
    if k=="dashboard":
        # Native-derived dashboard's existing cushion: continuous seam and
        # shallow centre rise, using verified 1971 LHD Spider dashboard photo.
        span=smooth(-.628,-.576,p.x)*(1-smooth(-.130,-.074,p.x))
        height=smooth(.758,.793,p.z)*(1-smooth(.921,.953,p.z))
        front=1-smooth(.174,.248,p.y)
        sweep=math.exp(-((p.x+.35)/.184)**4)
        dz=.0019*span*height*front*(.62+.38*sweep)
        dy=-.0011*span*height*front
    elif k=="cowl":
        # Subdue over-pronounced central bump on existing hood, preserve
        # original circular instrument openings and cowl closed topology.
        span=smooth(-.620,-.582,p.x)*(1-smooth(-.110,-.080,p.x))
        lip=1-smooth(.139,.212,p.y)
        crown=math.exp(-((p.x+.352)/.157)**4)
        top=smooth(.919,.968,p.z)
        dz=-.0027*span*lip*crown*(.38+.62*top)
        dy=-.0014*span*lip*(.6+.4*crown)
    elif k=="bezel":
        # Press the existing gauge lip 0.7 mm rearward, without inventing
        # gauges, changing face indices, UVs or materials.
        outer=math.exp(-((p.y-.1494)/.0026)**2)
        dy=-.00075*outer
        dz=.00021*outer*math.tanh((p.z-.82)/.032)
    elif k=="spoke":
        # More pronounced three-spoke metal stamping, but no motion within
        # pre-existing eight native perforation voids.
        ds=[math.hypot(p.x-x,p.z-z)/r for x,z,r in prior.HOLES]
        safe=smooth(1.075,1.55,min(ds))
        r=math.hypot(p.x+.35,p.z-.792)
        face=math.exp(-((p.y+.285)/.025)**2)
        wing=smooth(.075,.151,r)
        dy=-.00125*safe*wing*face
        dz=-.00032*safe*wing*face*math.tanh((p.z-.792)/.031)
        # Existing downward spoke is slightly narrowed below centre hub.
        lower=(1-smooth(.775,.804,p.z))*smooth(.681,.716,p.z)
        if p.z<.805:
            dx=-.039*(p.x+.35)*lower*safe
    elif k=="rim":
        # Verified Spider photo's black steering rim is slimmer than R16;
        # compress only tube cross-section about the original wheel path.
        ux=p.x+.350;vz=p.z-.792
        radius=math.hypot(ux,vz)
        if radius>.06:
            shrink=-.145*(radius-.1740)
            dx=shrink*ux/radius
            dz=shrink*vz/radius
        dy=-.11*(p.y+.286)
    elif k=="hub":
        # Existing original wheel's centre-column shoulder: shallow roll.
        radius=math.hypot(p.x+.350,p.z-.767)
        flange=math.exp(-((p.y+.250)/.012)**2)*smooth(.009,.023,radius)
        if radius>.00001:
            dx=.00095*flange*(p.x+.350)/radius
            dz=.00095*flange*(p.z-.767)/radius
        dy=-.00085*flange
    return Vector((dx,dy,dz))

def build():
    assert Path(bpy.data.filepath).resolve()==OLD.resolve(),"BLOCKED_INPUT_NOT_R16_SCENE"
    assert not NEW.exists() and not AUDIT.exists(),"IMMUTABLE_OUTPUT_COLLISION"
    oldaudit=native_guard()
    objs,keep,baseline=prior.snapshot()
    before={k:state(o) for k,o in objs.items()}
    for k,prior_state in oldaudit["source_derived_original_objects"].items():
        assert before[k]==prior_state["after"],("R16_SOURCE_MESH_DRIFT",k)
    assert all(prior.holes(objs["spoke"])),"SOURCE_HOLES_INVALID"
    report={}
    for k,o in objs.items():
        inverse=o.matrix_world.inverted()
        n=0;maxmm=0.;summm=0.
        for v in o.data.vertices:
            p=o.matrix_world@v.co
            delta=displacement(k,p)
            if delta.length<.000012:continue
            v.co=inverse@(p+delta)
            n+=1; mm=delta.length*1000.;summm+=mm;maxmm=max(maxmm,mm)
        minmove={"dashboard":80,"cowl":140,"bezel":200,"spoke":300,"rim":4000,"hub":15}[k]
        assert n>=minmove,("BLOCKED_P0_GEOMETRY_SELECTION",k,n)
        assert maxmm<4.5,("BLOCKED_GEOMETRY_OVERMOVE",k,maxmm)
        o.data.update()
        after=state(o)
        assert (before[k]["vertices"],before[k]["faces"])==(after["vertices"],after["faces"])
        for attr in ("name","matrix","uv","materials"):
            assert before[k][attr]==after[attr],("MESH_IDENTITY_CHANGED",k,attr)
        assert before[k]["signature"]!=after["signature"]
        report[k]={"before":before[k],"after":after,"moved":n,
                   "max_move_mm":round(maxmm,4),"mean_move_mm":round(summm/n,4)}
    prior.invariants(objs,keep,baseline)
    assert all(prior.holes(objs["spoke"]))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(NEW),compress=True)
    assert NEW.stat().st_size>1_000_000
    record={"slot":"A","car":"daytona365","revision":"r17",
            "real_source":"OutRun 2006 obj_plcar_dayts_pmt.sz",
            "original_native_pmt_sha256":prior.EXPECTED["pmt"],
            "original_import_blend_sha256":prior.EXPECTED["import"],
            "original_object_names":["object00_group01_material012_a0",
                                     "object22_group00_material000_a0"],
            "r16_input_sha256":SOURCE_HASH,"r17_output_sha256":sha(NEW),
            "reference_exact_1971_spider_lhd_photo_sha256":PHOTO_HASH,
            "source_derived_existing_meshes":report,
            "other_107_meshes_sha256":hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest(),
            "original_camera_matrices_pivots_uv_materials_images_preserved":True,
            "native_eight_spoke_through_holes":"PASS",
            "original_pmt_never_written":True,
            "no_new_objects_textures_or_exterior":True,"no_game_export":True,
            "driver_eye":"APPROXIMATE_NOT_GAME","all_seven_authentic_spider_views":"INCOMPLETE",
            "github_actions_real_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
            "complete":False,"score_change":0}
    AUDIT.write_text(json.dumps(record,indent=2),encoding="utf-8")
    print("SLOTA_R17_SOURCE_GEOMETRY_SAVED",json.dumps({
        "sha256":record["r17_output_sha256"],
        "moved":{k:v["moved"] for k,v in report.items()},
        "before_after_v_f":{k:[v["before"]["vertices"],v["before"]["faces"],
                             v["after"]["vertices"],v["after"]["faces"]] for k,v in report.items()}}),flush=True)

def verify():
    assert Path(bpy.data.filepath).resolve()==NEW.resolve(),"BLOCKED_INPUT_NO_R17_REOPEN"
    assert AUDIT.is_file() and not QA.exists() and not PNG.exists()
    native_guard()
    audit=json.loads(AUDIT.read_text())
    assert sha(NEW)==audit["r17_output_sha256"]
    objs,keep,base=prior.snapshot()
    assert hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest()==audit["other_107_meshes_sha256"]
    assert all(prior.holes(objs["spoke"]))
    stats={}
    for k,o in objs.items():
        assert state(o)==audit["source_derived_existing_meshes"][k]["after"],k
        bm=bmesh.new();bm.from_mesh(o.data)
        stats[k]={"v":len(bm.verts),"f":len(bm.faces),
                  "nonmanifold_edges":sum(not e.is_manifold for e in bm.edges)}
        bm.free()
    # Vertex-only editing must not increase existing non-manifold topology.
    for k,expected in {"dashboard":184,"cowl":0,"bezel":932,
                       "spoke":1597,"rim":0,"hub":0}.items():
        assert stats[k]["nonmanifold_edges"]==expected,(k,stats[k])
    sc=bpy.context.scene
    camdata=bpy.data.cameras.new("SLOTA_R17_APPROX_EYE_TEMP")
    cam=bpy.data.objects.new("SLOTA_R17_APPROX_EYE_TEMP",camdata)
    sc.collection.objects.link(cam)
    cam.location=(-.35,-.92,1.055)
    look=Vector((-.24,.19,.797))
    cam.rotation_euler=(look-cam.location).to_track_quat("-Z","Y").to_euler()
    camdata.type="PERSP";camdata.lens=28;camdata.clip_start=.01
    sc.camera=cam
    sc.render.engine="CYCLES";sc.cycles.device="CPU"
    sc.render.threads_mode="FIXED";sc.render.threads=2
    sc.cycles.samples=3;sc.cycles.use_denoising=True
    sc.render.resolution_x=720;sc.render.resolution_y=480
    sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
    sc.view_settings.exposure=-.52;sc.render.filepath=str(PNG)
    bpy.ops.render.render(write_still=True)
    assert PNG.is_file() and PNG.stat().st_size>12000
    assert sha(NEW)==audit["r17_output_sha256"]
    qa={"status":"REAL_PRIVATE_BLENDER_4_5_15_INDEPENDENT_REOPEN_CYCLES_PASS",
        "car":"daytona365","slot":"A","blend_sha256":sha(NEW),
        "real_Cycles_SHA256":sha(PNG),"render":PNG.name,"resolution":[720,480],
        "samples":3,"geometry":stats,"native_holes_open":8,"other_meshes_untouched":107,
        "photo_views":"INCOMPLETE","game_camera":"NOT_CALIBRATED",
        "GitHub_hosted_real_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
        "vehicle_complete":False,"score_change":0}
    QA.write_text(json.dumps(qa,indent=2),encoding="utf-8")
    print("SLOTA_R17_FRESH_REOPEN_CYCLES_PASS",json.dumps(qa),flush=True)

if __name__=="__main__":
    mode=os.environ.get("SLOT_A_R17_MODE")
    if mode=="build":build()
    elif mode=="verify":verify()
    else:raise SystemExit("SLOT_A_R17_MODE must be build or verify")

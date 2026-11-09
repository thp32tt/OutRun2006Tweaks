#!/usr/bin/env python3
"""F50 SLOT=C: hosted-only second inner_door candidate, not a QA claim.

Edit only source-native driver-side upper inner door PMT031 from exact v41.
Require real private F50 reference photo; do not synthesize handles, dashboard,
steering, seats, exterior, other objects, materials, faces, or UV.
"""
import hashlib
import math
from pathlib import Path

ROOT = Path("/home/chatgpt-runner")
NAME = "PMT_F50_object00_group01_material031_a0"
PARENT_ID = "object00_group01_material031_a0"
ORIGINAL = "10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab"
SOURCE = "016645f5fea43ef75c8e80479f49baaff2d3aa8d1647a058f732ac69080da08d"
PHOTO = ROOT / "outrun2_vr_refs/20261104_16car_cockpit/03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg"
PHOTO_HASH = "cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2"
OUT = ROOT / "work_handoff/ferrari_hosted_results/slot_C"
VERTICES = (26,27,30,31,32,33,34,36,37,62)

def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for x in iter(lambda:f.read(1024*1024),b""):
            h.update(x)
    return h.hexdigest()

def render(bpy, target, label):
    from mathutils import Vector
    scene = bpy.context.scene
    oldcam = scene.camera
    config = (scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,
              scene.render.resolution_percentage,scene.render.filepath,scene.render.image_settings.file_format)
    oldhidden = {o.name:o.hide_render for o in bpy.data.objects if o.type=="MESH"}
    camera_data = bpy.data.cameras.new("TEMP_NATIVE_INNER_DOOR_"+label)
    camera = bpy.data.objects.new(camera_data.name,camera_data)
    scene.collection.objects.link(camera)
    camera.location=(-1.75,1.04,-.18)
    camera.rotation_euler=(Vector((-.63,.57,-.12))-camera.location).to_track_quat("-Z","Y").to_euler()
    camera_data.type="ORTHO"
    camera_data.ortho_scale=1.8
    output=OUT/("F50_NativeInnerDoor_v42_"+label+".png")
    try:
        scene.camera=camera
        for o in bpy.data.objects:
            if o.type=="MESH":
                o.hide_render=o.name!=target.name
        scene.render.engine="BLENDER_WORKBENCH"
        scene.render.resolution_x=760
        scene.render.resolution_y=600
        scene.render.resolution_percentage=100
        scene.render.filepath=str(output)
        scene.render.image_settings.file_format="PNG"
        bpy.ops.render.render(write_still=True)
        if not output.is_file() or output.stat().st_size<200:
            raise RuntimeError("BLOCKED_HOSTED_RENDER: missing PNG")
        return sha(output)
    finally:
        for o in bpy.data.objects:
            if o.type=="MESH":
                o.hide_render=oldhidden[o.name]
        scene.camera=oldcam
        (scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,
         scene.render.resolution_percentage,scene.render.filepath,
         scene.render.image_settings.file_format)=config
        bpy.data.objects.remove(camera,do_unlink=True)
        bpy.data.cameras.remove(camera_data)

def apply(bpy):
    if bpy.app.version[:3]!=(4,5,15) or sha(Path(bpy.data.filepath))!=SOURCE:
        raise RuntimeError("BLOCKED_HOSTED_INPUT: exact v41 + Blender 4.5.15 required")
    if bpy.context.scene.get("outrun_original_game_resource_sha256")!=ORIGINAL:
        raise RuntimeError("BLOCKED_ORIGINAL_PMT")
    if not PHOTO.is_file() or sha(PHOTO)!=PHOTO_HASH:
        raise RuntimeError("BLOCKED_HOSTED_INPUT: private genuine F50 photo absent")
    native=[o for o in bpy.data.objects if o.type=="MESH"]
    if len(native)!=42 or any(o.get("outrun_original_game_resource_sha256")!=ORIGINAL for o in native):
        raise RuntimeError("BLOCKED_NATIVE_SOURCE: expected 42 PMT meshes")
    ob=bpy.data.objects.get(NAME)
    if ob is None or ob.type!="MESH" or ob.get("outrun_original_mesh_object_id")!=PARENT_ID:
        raise RuntimeError("BLOCKED_SCOPE: PMT031 original identity")
    me=ob.data
    if len(me.vertices)!=66 or len(me.polygons)!=40:
        raise RuntimeError("BLOCKED_SCOPE: original door topology")
    coords={}
    for i in VERTICES:
        x,y,z=map(float,me.vertices[i].co)
        if not (-.80<x<-.54 and .710<y<.92 and .24<z<.49):
            raise RuntimeError("BLOCKED_SOURCE_WINDOW: driver door coordinates changed")
        coords[i]=(x,y,z)
    OUT.mkdir(parents=True,exist_ok=True)
    before=render(bpy,ob,"BEFORE")
    for i in VERTICES:
        x,y,z=coords[i]
        t=min(1.,max(0.,(y-.715)/.185))
        dy=-.003*t
        dz=.006+.009*t
        if math.hypot(dy,dz)>.016:
            raise RuntimeError("BLOCKED_BOUNDED_MOVE")
        me.vertices[i].co=(x,y+dy,z+dz)
    me.update()
    after=render(bpy,ob,"AFTER")
    if before==after:
        raise RuntimeError("BLOCKED_NO_RENDER_DELTA")
    bpy.context.scene["slot_c_inner_door_hosted_candidate"]="NATIVE_UPPER_RAIL_ONLY_PHOTO_QA_PENDING"

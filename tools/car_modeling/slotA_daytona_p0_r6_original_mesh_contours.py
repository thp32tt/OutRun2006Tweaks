#!/usr/bin/env python3
"""Slot A Daytona r6: sculpt the EXISTING verified OutRun 2006 cockpit meshes only.

Requires exact private r5 editable .blend and the original native game PMT/import.
No new mesh, material, texture, export, car or VR/runtime asset is made.
The private source remains immutable. This is not a game-camera or 7-photo PASS.
"""
import bpy
import hashlib
import json
import math
import os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

W = Path(os.environ["SLOT_A_WORK"])
SOURCE = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v3_r5.blend"
OUTPUT = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v4_r6.blend"
REPORT = W / "SLOT_A_DAYTONA_P0_R6_PHYSICAL_LIPS_GRIP_HUB_BEZEL.json"
PMT = Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIGINAL_IMPORT = Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO = Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
SHA = {
    "source": "163e48fe83c4555d45e18ba33b574854bc871fa5794b2c91a71a1d57d568696b",
    "pmt": "f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
    "original_import": "92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
    "photo": "6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb",
}
OBJECTS = {
    "spoke": "V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
    "rim": "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
    "hub": "V7_SHORT_SHAFT_AT_WHEEL_HUB",
    "bezel": "DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",
    "dashboard": "V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
}
EXPECTED = {
    "spoke": (9720, 17285),
    "rim": (1536, 1536),
    "hub": (224, 210),
    "bezel": (908, 1344),
    "dashboard": (1885, 3584),
}
HOLES = [
    (-.431, .804, .0068), (-.410, .804, .0068), (-.390, .804, .0068),
    (-.310, .804, .0068), (-.290, .804, .0068), (-.269, .804, .0068),
    (-.350, .745, .0052), (-.350, .716, .0047),
]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def signature(o):
    d = o.data
    return hashlib.sha256(repr((
        [(round(v.co.x, 7), round(v.co.y, 7), round(v.co.z, 7)) for v in d.vertices],
        [(p.material_index, tuple(p.vertices)) for p in d.polygons],
    )).encode("utf8")).hexdigest()

def matrix(o):
    return [[round(float(c), 9) for c in row] for row in o.matrix_world]

def hit(tree, x, z):
    return tree.ray_cast(Vector((x, -.55, z)), Vector((0., 1., 0.)), 1.)[2] is not None

assert bpy.app.version_string.startswith("4.5.15"), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == SOURCE.resolve()
assert not OUTPUT.exists() and not REPORT.exists(), "r6 private output must be immutable"
for key, path in (("source", SOURCE), ("pmt", PMT), ("original_import", ORIGINAL_IMPORT), ("photo", PHOTO)):
    assert path.is_file() and sha(path) == SHA[key], (key, str(path))
assert bpy.context.scene.camera.name == "V7_Camera_Reference_ThreeQuarter"
assert bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].type == "MESH"
# Factory wheel identity was validated in the separate original imported .blend;
# current edited scene retains its source-derived V5 wheel object identity.
obj = {k: bpy.data.objects[name] for k, name in OBJECTS.items()}
before = {}
for k, o in obj.items():
    assert o.type == "MESH" and o.data.users == 1
    assert (len(o.data.vertices), len(o.data.polygons)) == EXPECTED[k]
    assert o.data.uv_layers and o.data.materials
    before[k] = {
        "object_name": o.name, "vertices": len(o.data.vertices), "faces": len(o.data.polygons),
        "signature": signature(o), "world_matrix": matrix(o),
    }
protected = {o.name: signature(o) for o in bpy.data.objects if o.type == "MESH" and o.name not in OBJECTS.values()}
scene_objects = set(bpy.data.objects)
materials = set(bpy.data.materials)
images = {i.name: (tuple(i.size), bool(i.packed_file)) for i in bpy.data.images}
curves = set(bpy.data.curves)
camera_matrix = matrix(bpy.context.scene.camera)
camera_name = bpy.context.scene.camera.name

# Preserve all EIGHT open original-spoke perforations, visible in the exact Spider photo.
original_tree = BVHTree.FromObject(obj["spoke"], bpy.context.evaluated_depsgraph_get())
assert all(not hit(original_tree, x, z) and hit(original_tree, x + 1.6*r, z)
           for x, z, r in HOLES)

# Only MOVE existing vertices of the original-derived cockpit objects; no new topology asset.
# Pressed bright metal lips soften r5 flat punched apertures without filling the openings.
moved = {}
for key, o in obj.items():
    inv = o.matrix_world.inverted()
    touched = 0
    max_mm = 0.
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        dx = dy = dz = 0.
        if key == "spoke":
            near = min(math.hypot(p.x-x, p.z-z)/r for x,z,r in HOLES)
            if .97 < near < 2.05:
                # 1.25 mm smooth pressed annulus on the ORIGINAL perforated spoke faces.
                dy = -.00125 * math.exp(-((near - 1.34) / .40)**2)
        elif key == "rim":
            xx, zz = p.x + .350, p.z - .792
            radius = math.hypot(xx, zz)
            if radius > 1e-8:
                angle = math.atan2(zz, xx)
                # Small rounded grips at the top-left and top-right; keep
                # the original wheel center, ring path, transform and pivot.
                top_grips = (math.exp(-((angle-math.pi/3)/.32)**4)
                             + math.exp(-((angle-2*math.pi/3)/.32)**4))
                # Change actual cross-section, not just translate the whole ring.
                dr = .00145 * top_grips * max(-1., min(1., (radius-.180)/.011))
                dx, dz = dr * xx / radius, dr * zz / radius
                dy = .00072 * top_grips * max(-1., min(1., (p.y+.286)/.014))
        elif key == "hub":
            xx, zz = p.x + .350, p.z - .767
            radius = math.hypot(xx, zz)
            shoulder = math.exp(-((p.y + .254)/.010)**2)
            if radius > 1e-8:
                dr = .0017 * shoulder
                dx, dz = dr * xx/radius, dr * zz/radius
            dy = -.00055 * shoulder
        elif key == "bezel":
            # Re-profile the existing imported-guided chrome gauge rim
            # in depth, retaining its original ring loops and atlas UV.
            dy = -.00105 * math.exp(-((p.y-.1532)/.0018)**2)
        elif key == "dashboard":
            # A shallow padded roll under the factory instrument binnacle:
            # keep the wide upper dash silhouette and outer edges unchanged.
            cx = math.exp(-((p.x+.348)/.225)**4)
            az = math.exp(-((p.z-.865)/.039)**2)
            lo = 1. if -.592 < p.x < -.085 else 0.
            dy = -.00122*cx*az*lo
            dz = .00048*cx*az*lo
        change = Vector((dx, dy, dz))
        if change.length < .000015:
            continue
        v.co = inv @ (p + change)
        touched += 1
        max_mm = max(max_mm, change.length * 1000.)
    o.data.update()
    assert touched >= {"spoke": 200, "rim": 100, "hub": 20, "bezel": 100, "dashboard": 80}[key], (key,touched)
    assert max_mm < 2.5, (key, max_mm)
    assert signature(o) != before[key]["signature"], key
    o["SLOTA_SOURCE_PMT"] = PMT.name
    o["SLOTA_SOURCE_SHA256"] = SHA["pmt"]
    moved[key] = {"vertices_moved": touched, "max_displacement_mm": round(max_mm,4)}

updated_tree = BVHTree.FromObject(obj["spoke"], bpy.context.evaluated_depsgraph_get())
for x, z, r in HOLES:
    assert not hit(updated_tree, x, z), ("source through-hole blocked",x,z)
    assert hit(updated_tree, x + 1.6*r, z), ("source surrounding spoke lost",x,z)
for name, value in protected.items():
    assert signature(bpy.data.objects[name]) == value, ("unrelated original mesh edited",name)
assert set(bpy.data.objects) == scene_objects
assert set(bpy.data.materials) == materials
assert set(bpy.data.curves) == curves
assert {i.name:(tuple(i.size),bool(i.packed_file)) for i in bpy.data.images} == images
assert bpy.context.scene.camera.name == camera_name
assert matrix(bpy.context.scene.camera) == camera_matrix
assert all(matrix(obj[k]) == before[k]["world_matrix"] for k in obj)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
report = {
    "status":"DAYTONA_SLOT_A_R6_PRIVATE_SOURCE_GEOMETRY_SAVED",
    "car":"daytona365", "slot":"A", "blender_version":bpy.app.version_string,
    "input_blend":SOURCE.name, "input_blend_sha256":SHA["source"],
    "output_blend":OUTPUT.name, "output_blend_sha256":sha(OUTPUT),
    "output_bytes":OUTPUT.stat().st_size,
    "original_game_resource":str(PMT), "original_game_resource_sha256":SHA["pmt"],
    "original_game_import_blend":str(ORIGINAL_IMPORT),
    "original_game_import_sha256":SHA["original_import"],
    "exact_spider_photo":str(PHOTO), "exact_spider_photo_sha256":SHA["photo"],
    "original_derived_edited_meshes": {
        k: {"before":before[k], "after_vertices":len(o.data.vertices),
            "after_faces":len(o.data.polygons), "after_signature":signature(o),
            **moved[k]} for k,o in obj.items()
    },
    "unchanged_other_mesh_count":len(protected),
    "unchanged_other_mesh_sha256_aggregate":
        hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest(),
    "source_spoke_perforation_centers":HOLES,
    "open_eight_perforations_verified":True,
    "original_matrices_and_camera_unchanged":True,
    "no_scene_objects_added":True, "no_materials_textures_normals_PBR_created":True,
    "no_exterior_mesh_edits":True, "no_ovc3_ovc_pmt_or_game_exports":True,
    "game_camera_calibrated":False, "photo_seven_view_complete":False,
    "24h_quality_gate":"INCOMPLETE", "vehicle_complete":False, "slot_a_advance":False,
    "hosted_private_blend_actions_validation":"BLOCKED_INPUT_NO_PRIVATE_SCENE_TRANSFER",
}
REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False))
print(report["status"], json.dumps({"blend_sha":report["output_blend_sha256"],"moved":moved}),flush=True)

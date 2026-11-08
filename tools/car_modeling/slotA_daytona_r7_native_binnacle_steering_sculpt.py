#!/usr/bin/env python3
"""Slot A Daytona r7: original PMT-derived instrument binnacle and steering bowl sculpt.

ONLY an existing editable derivative of the actual OutRun 2006 Daytona PMT is
opened and edited. All unchanged objects, UV/material/packed images, object
matrices, camera and eight physical native-spoke perforations are guarded.
Not game-camera-calibrated. No original PMT writes, game export, OVC, GLB,
external wheel/body, materials, normal-map, PBR or vehicle fabrication.
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
SRC = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v4_r6.blend"
OUT = W / "Daytona365_SlotA_SourceCockpit_P0_DashWheel_v5_r7.blend"
AUDIT = W / "SLOT_A_DAYTONA_P0_R7_ORIGINAL_BINNACLE_SPOKE.json"
PMT = Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
ORIG = Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
PHOTO = Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
EXPECTED_SHA = {
    "src":"cb220cd75eb09c84fe722a14b5d4bc268a8cf1d9af23c77aba56a97c38b19ea9",
    "pmt":"f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe",
    "original_import":"92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3",
    "exact_photo":"6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb"}
NAMES = {
    "dashboard":"V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",
    "cowl":"V8_17_ORIGINAL_GUIDED_GAUGE_COWL",
    "steering_spoke":"V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0",
    "steering_rim":"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
    "steering_hub":"V7_SHORT_SHAFT_AT_WHEEL_HUB",
}
COUNTS = {
    "dashboard":(1885,3584), "cowl":(650,648), "steering_spoke":(9720,17285),
    "steering_rim":(1536,1536), "steering_hub":(224,210)}
EXPECTED_SIG = {
    "dashboard":"8c290e3e9d4f25908988ca72a2997a5924e0e9a86ecc25d77dc5d0b492cebee6",
    "cowl":"45169e04cd053682daffa8fe7f2d6c87f9cd92df242145a3550e7f545ff48429",
    "steering_spoke":"adaa606a84f0ef1a495674b37527c579e839a3fb51520f28762c868a95619c46",
    "steering_rim":"0c310bc4a7d476a1eff01b2f736af2b23a418e73af52116e8bfde18036c4e5b3",
    "steering_hub":"67a9e1c7e88e5d92c4ce8e89f6efd22a2796e52130157bd78691931e5e365bf4",
}
HOLES = [
    (-.431,.804,.0068), (-.410,.804,.0068), (-.390,.804,.0068),
    (-.310,.804,.0068), (-.290,.804,.0068), (-.269,.804,.0068),
    (-.350,.745,.0052), (-.350,.716,.0047)]

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def sig(o):
    d=o.data
    return hashlib.sha256(repr((
        [(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
        [(f.material_index,tuple(f.vertices)) for f in d.polygons],
    )).encode("utf8")).hexdigest()

def matrix(o):
    return [[round(float(x),9) for x in row] for row in o.matrix_world]

def blend(lo,hi,x):
    t=max(0.,min(1.,(x-lo)/(hi-lo)))
    return t*t*(3.-2.*t)

def ray(tree,x,z):
    return tree.ray_cast(Vector((x,-.55,z)),Vector((0.,1.,0.)),1.)[2] is not None

assert bpy.app.version_string.startswith("4.5.15"), bpy.app.version_string
assert Path(bpy.data.filepath).resolve()==SRC.resolve()
assert not OUT.exists() and not AUDIT.exists(), "immutable r7 private checkpoint"
for key,p in (("src",SRC),("pmt",PMT),("original_import",ORIG),("exact_photo",PHOTO)):
    assert p.is_file() and digest(p)==EXPECTED_SHA[key], (key,str(p))
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert len(bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"].data.vertices)==13
ob={k:bpy.data.objects[n] for k,n in NAMES.items()}
prior={}
for k,o in ob.items():
    assert o.type=="MESH" and o.data.users==1 and o.data.uv_layers and o.data.materials
    assert (len(o.data.vertices),len(o.data.polygons))==COUNTS[k]
    assert sig(o)==EXPECTED_SIG[k], (k,"unexpected prior topology/source geometry")
    prior[k]={"object":o.name,"vertices":len(o.data.vertices),
              "faces":len(o.data.polygons),"signature":sig(o),"matrix":matrix(o)}
keep={o.name:sig(o) for o in bpy.data.objects if o.type=="MESH" and o.name not in NAMES.values()}
known_objects=set(bpy.data.objects.keys())
known_materials=set(bpy.data.materials.keys())
known_curves=set(bpy.data.curves.keys())
known_images={im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}
scene_cam_name=bpy.context.scene.camera.name
scene_cam_matrix=matrix(bpy.context.scene.camera)
initial_tree=BVHTree.FromObject(ob["steering_spoke"],bpy.context.evaluated_depsgraph_get())
assert all(not ray(initial_tree,x,z) and ray(initial_tree,x+1.6*r,z) for x,z,r in HOLES)

# 1971 365 GTS/4 LHD exact-Spider photo: a continuously rounded instrument
# hood with a deeper instrument-field recess; avoid the old rectangular overlay
# look. Change EXISTING original-linked dash grid, not generate a new part.
moved={}
for k,o in ob.items():
    inverse=o.matrix_world.inverted()
    count=0; peak=0.; total=0.
    for v in o.data.vertices:
        p=o.matrix_world@v.co
        dx=dy=dz=0.
        if k=="dashboard":
            cluster_x=blend(-.650,-.592,p.x)*(1.-blend(-.118,-.055,p.x))
            field_z=blend(.716,.755,p.z)*(1.-blend(.887,.940,p.z))
            # Real recessed instrument-pad cross section, only under native
            # gauge mask; preserve entire perimeter and original dash anchors.
            front=1.-.85*blend(.193,.229,p.y)
            envelope=cluster_x*field_z*front
            bowl=math.exp(-((p.x+.351)/.205)**4)
            dy=-.0140*envelope*(.80+.20*bowl)
            # Upper padding has subtle lip below upper cowl.
            dz=.00165*envelope*math.exp(-((p.z-.892)/.029)**2)
        elif k=="cowl":
            # Retain native-source arch and reshape its actual existing shell
            # into a visibly deeper visor around the main large instruments.
            xmask=blend(-.625,-.594,p.x)*(1.-blend(-.108,-.065,p.x))
            centre=math.exp(-((p.x+.350)/.220)**4)
            front=1.-blend(.183,.224,p.y)
            top=blend(.916,.935,p.z)
            dy=-.0093*xmask*centre*front*top
            dz=.0052*xmask*centre*front*top
        elif k=="steering_spoke":
            # Three originally imported factory spoke strips, including the
            # real eight punched through-holes. Form a shallow bowl in the
            # surrounding sheet-metal, NOT in the perforation boundaries.
            x=p.x+.350
            radius=math.hypot(x,p.z-.792)
            lower=math.exp(-((p.z-.693)/.033)**2)*math.exp(-(x/.017)**4)
            # stamp only occupied lower original arm, fade away from open holes.
            hole_distance=min(math.hypot(p.x-hx,p.z-hz)/hr for hx,hz,hr in HOLES)
            guard=blend(1.05,2.60,hole_distance)
            dy=.0025*lower*guard*blend(.043,.085,radius)
        elif k=="steering_rim":
            # Existing ring cross-section: slight ergonomic thumb rest in the
            # outer upper arc; centre, rim path, wheel pivot unchanged.
            x,z=p.x+.350,p.z-.792
            rr=math.hypot(x,z)
            if rr>1e-8:
                angle=math.atan2(z,x)
                thumb=(math.exp(-((angle-.74)/.18)**4)+math.exp(-((angle-2.40)/.18)**4))
                dy=-.0017*thumb*math.exp(-((p.y+.281)/.011)**2)
                dr=.00135*thumb*(rr-.180)/.010
                dr=max(-.0014,min(.0014,dr))
                dx=dr*x/rr;dz=dr*z/rr
        elif k=="steering_hub":
            x,z=p.x+.350,p.z-.767
            rr=math.hypot(x,z)
            # Existing connecting collar: clean shoulder between pressed
            # three-spoke centre and existing steering column.
            step=math.exp(-((p.y+.248)/.007)**2)
            if rr>1e-8:
                dr=.00125*step
                dx=dr*x/rr;dz=dr*z/rr
        d=Vector((dx,dy,dz))
        if d.length<=.000020:continue
        v.co=inverse@(p+d)
        count+=1
        peak=max(peak,d.length*1000)
        total+=d.length
    o.data.update()
    assert count>={"dashboard":150,"cowl":80,"steering_spoke":30,"steering_rim":40,"steering_hub":20}[k], (k,count)
    assert peak<16.,(k,peak)
    assert sig(o)!=prior[k]["signature"],(k,"mesh unchanged")
    assert matrix(o)==prior[k]["matrix"],(k,"world transform changed")
    o["SLOTA_SOURCE_PMT"]=PMT.name
    o["SLOTA_SOURCE_SHA256"]=EXPECTED_SHA["pmt"]
    moved[k]={"moved_vertices":count,"maximum_mm":round(peak,5),"mean_moved_mm":round(total/count*1000,5)}
for name,signature in keep.items():
    assert sig(bpy.data.objects[name])==signature,("unrelated mesh changed",name)
assert set(bpy.data.objects.keys())==known_objects
assert set(bpy.data.materials.keys())==known_materials
assert set(bpy.data.curves.keys())==known_curves
assert {im.name:(tuple(im.size),bool(im.packed_file)) for im in bpy.data.images}==known_images
assert bpy.context.scene.camera.name==scene_cam_name
assert matrix(bpy.context.scene.camera)==scene_cam_matrix
final_tree=BVHTree.FromObject(ob["steering_spoke"],bpy.context.evaluated_depsgraph_get())
assert all(not ray(final_tree,x,z) and ray(final_tree,x+1.6*r,z) for x,z,r in HOLES),"source spoke openings changed"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
post={
 k:{"source_original_object":v["object"],"before":v,"after_signature":sig(ob[k]),
    "after_vertices":len(ob[k].data.vertices),"after_faces":len(ob[k].data.polygons),
    **moved[k]} for k,v in prior.items()
}
record={
 "status":"SLOTA_DAYTONA_R7_NATIVE_DASH_COWL_STEERING_SAVE_PASS",
 "slot":"A","car":"daytona365","blender":bpy.app.version_string,
 "original_game_resource":str(PMT),"original_game_sha256":EXPECTED_SHA["pmt"],
 "original_import_blend":str(ORIG),"original_import_sha256":EXPECTED_SHA["original_import"],
 "exact_spider_lhd_photo":str(PHOTO),"photo_sha256":EXPECTED_SHA["exact_photo"],
 "input_blend":SRC.name,"input_sha256":EXPECTED_SHA["src"],
 "output_blend":OUT.name,"output_sha256":digest(OUT),"bytes":OUT.stat().st_size,
 "changed_existing_source_derived_meshes":post,"untouched_other_meshes":len(keep),
 "protected_mesh_geometry_aggregate_sha256":hashlib.sha256(json.dumps(keep,sort_keys=True).encode()).hexdigest(),
 "through_holes_preserved":8,"source_object_matrices_unchanged":True,
 "no_new_scene_objects":True,"no_new_textures_materials_PBR_normals":True,
 "no_exterior_mesh_changes":True,"no_game_export":True,
 "driver_eye":"APPROXIMATE_NOT_GAME","7_exact_spider_photos":"INCOMPLETE",
 "github_hosted_real_original_scene":"BLOCKED_INPUT_PRIVATE_BLEND",
 "24h_gate":"NOT_COMPLETE","vehicle_complete":False,"advance_slot_A":False}
AUDIT.write_text(json.dumps(record,indent=2,ensure_ascii=False))
print(record["status"],json.dumps({"sha256":record["output_sha256"],"moved":moved}),flush=True)

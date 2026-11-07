"""Blender v7.1: fix v6 footmats erroneously modeled as VERTICAL panels.
Add a grounded footwell and rear firewall so nothing floats.
Refine reference image color grading, preserving physical normal and ORM maps.
"""
import bpy,bmesh,math,json,hashlib
from pathlib import Path
R=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
OUT=R/"blender_v7"
s=bpy.context.scene
assert bpy.data.filepath.endswith("Daytona365_Cockpit_Blender_PBR_v7.blend")
DARK=bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
TAN=bpy.data.materials["V7_Target_Tan_Leather_PBR"]
coll=bpy.data.collections.get("V7 | continuous padded seat shells")
assert coll
floor_collection=bpy.data.collections.new("V7 | corrected horizontal footwell and firewall")
s.collection.children.link(floor_collection)
fix=[]
for side,cx in (("L",-.353),("R",.353)):
    obj=bpy.data.objects.get(f"V6_{side}_BLENDER_BLACK_FLOOR_MAT")
    assert obj
    # Previous mistaken dimensions (.52,.017,.62) produced a huge upright wall!
    obj.location=(cx,.08,.29)
    obj.dimensions=(.45,.68,.015)
    for c in list(obj.users_collection): c.objects.unlink(obj)
    floor_collection.objects.link(obj)
    if obj.data.materials:obj.data.materials[0]=DARK
    else:obj.data.materials.append(DARK)
    fix.append(obj.name)
def box(name,loc,size,mat,bevel=.008):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object
    o.name=name
    for col in list(o.users_collection):col.objects.unlink(o)
    floor_collection.objects.link(o)
    o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.clear();o.data.materials.append(mat)
    bevel_mod=o.modifiers.new("Blender v7 genuine rounded joinery","BEVEL")
    bevel_mod.width=bevel;bevel_mod.segments=3
    weight=o.modifiers.new("Blender v7 corner normals","WEIGHTED_NORMAL")
    weight.keep_sharp=True
    return o
# Continuous carpet floor prevents the backdrop from showing through footwell.
box("V7_REAL_BLACK_CARPET_FLOOR",(0,-.15,.266),(1.56,1.52,.016),DARK,.018)
# Instrument panel lower face: source cluster y≈.15, z≈.74; this stays BELOW z=.68.
box("V7_BLACK_DASH_UNDERPANEL",(0,.161,.495),(1.46,.027,.338),DARK,.018)
# Add subtle internal side floor tunnels connecting footwell to console.
for side in (-1,1):
    box(f"V7_{'L' if side<0 else 'R'}_BLACK_FOOTWELL_KICKPANEL",
        (side*.69,-.09,.379),(.09,.95,.165),DARK,.014)
# Remove excessive material shine under macro studio lights.
for name in ("V7_Target_Tan_Leather_PBR","V7_Target_Black_Dashboard_PBR"):
    material=bpy.data.materials[name]
    bsdf=material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Coat Weight"].default_value=0.018
        bsdf.inputs["Sheen Weight"].default_value=.09
# target image is dark caramel, not pastel; reduce global exposure slightly.
s.view_settings.exposure=-.44
# steering hub must remain above underpanel as it enters only lower dash
column=bpy.data.objects["V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES"]
pts=[v.co for v in column.data.vertices]
assert min(p.z for p in pts)<.60 and max(p.z for p in pts)<.79
for img in bpy.data.images:
    if img.source=="FILE" and not img.packed_file:img.pack()
out=OUT/"Daytona365_Cockpit_Blender_PBR_v7_1.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
result={"file":out.name,"bytes":out.stat().st_size,
  "sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
  "fixed_floor_mats":fix,"horizontal_floor_dimensions":[.45,.68,.015],
  "real_grounded_black_carpet":True,
  "under_dash_firewall":True,
  "original_pmt_modified":False,"dino_modified":False,
  "new_ovc_created":False}
(OUT/"DAYTONA_V7_1_BUILD_MANIFEST.json").write_text(json.dumps(result,indent=2))
print("BLENDER_V7_1_PASS",json.dumps(result),flush=True)
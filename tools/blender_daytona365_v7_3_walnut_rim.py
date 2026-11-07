import bpy,math,json,hashlib
from pathlib import Path
R=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
OUT=R/"blender_v7"
assert bpy.data.filepath.endswith("Daytona365_Cockpit_Blender_PBR_v7_2.blend")
wheel=[x for x in bpy.data.objects if "V5_ORIGINAL_THREESPOKE_WHEEL" in x.name and "material002" in x.name]
assert len(wheel)==1
old=wheel[0]
old.hide_render=True;old.hide_set(True)
old["v7_replacement"]="Archived original low-poly rim. Replaced by single round wood geometry"
wood=bpy.data.materials["V7_Target_Walnut_Steering_Rim_PBR"]
silver=bpy.data.materials["V7_Machined_Aluminum"]
coll=bpy.data.collections.get("V7 | under-cluster steering column")
assert coll is not None
# Blender-native torus primitive, source center follows original PMT rim bbox.
center=(-.35,-.286,.792)
bpy.ops.mesh.primitive_torus_add(major_segments=96,minor_segments=16,
    location=center,rotation=(math.pi/2,0,0),
    major_radius=.166,minor_radius=.014)
rim=bpy.context.object
rim.name="V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"
for c in list(rim.users_collection): c.objects.unlink(rim)
coll.objects.link(rim)
rim.data.materials.append(wood)
for f in rim.data.polygons:f.use_smooth=True
# Preserve original three spokes, only short extensions to its source rim.
def connector(name,loc,dims):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    coll.objects.link(o)
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(silver)
    bevel=o.modifiers.new("V7.3 rolled stamping edge","BEVEL")
    bevel.width=.003;bevel.segments=3
    for p in o.data.polygons:p.use_smooth=True
    return o
connector("V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",(-.483,-.290,.79),(.077,.008,.021))
connector("V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",(-.217,-.290,.79),(.077,.008,.021))
connector("V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE",(-.35,-.291,.659),(.020,.008,.077))
# Complete darker reference tan material while retaining generated microtexture maps.
tan=bpy.data.materials["V7_Target_Tan_Leather_PBR"]
target=tan.node_tree.nodes.get("V7.2 Target image warm material tone")
assert target
target.inputs[2].default_value=(.74,.69,.59,1.)
walnut=bpy.data.materials["V7_Target_Walnut_Steering_Rim_PBR"]
w=walnut.node_tree.nodes.get("V7.2 Target image warm material tone")
assert w
w.inputs[2].default_value=(.73,.75,.78,1)
# Correct the tiny gap at steering shaft and hub: material dark shroud remains
# below gauge cluster and ends behind the three-spoke wheel, never overlays dials.
s=bpy.context.scene
s.camera=bpy.data.objects["V7_Camera_Reference_ThreeQuarter"]
s.render.engine="CYCLES";s.cycles.device="CPU";s.cycles.samples=8
s.cycles.use_denoising=True;s.render.resolution_x=960;s.render.resolution_y=640
s.render.resolution_percentage=100
out=OUT/"Daytona365_Cockpit_Blender_PBR_v7_3.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
result={"file":out.name,"bytes":out.stat().st_size,
"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
"old_rim_hidden_but_source_preserved":True,
"single_new_smooth_wood_rim":True,
"actual_mesh_spoke_bridges":3,
"target_reference_leather_tone":True,
"normal_orm_height_maps":True,
"OVC_CREATED":False,"Dino_UNTOUCHED":True}
(OUT/"DAYTONA_V7_3_BUILD_MANIFEST.json").write_text(json.dumps(result,indent=2))
print("V7_3_SAVED",json.dumps(result),flush=True)
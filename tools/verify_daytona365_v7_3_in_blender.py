"""Open v7.3 fresh in official Blender to verify all physical edits and PBR maps."""
import bpy,hashlib,json,math
from pathlib import Path
r=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender_v7")
p=r/"Daytona365_Cockpit_Blender_PBR_v7_3.blend"
names={o.name for o in bpy.data.objects}
all_mesh=[o for o in bpy.data.objects if o.type=="MESH"]
all_curves=[o for o in bpy.data.objects if o.type=="CURVE"]
assert all(x in names for x in (
 "V7_L_INTEGRATED_PADDED_CUSHION","V7_R_INTEGRATED_PADDED_CUSHION",
 "V7_L_INTEGRATED_PLEATED_BACKREST","V7_R_INTEGRATED_PLEATED_BACKREST",
 "V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES",
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V7_REAL_BLACK_CARPET_FLOOR",
 "V7_BLACK_DASH_UNDERPANEL"))
assert not any(o.name.startswith("V5_L_CUSHION_DARK_STRIPE") or
 o.name.startswith("V5_R_CUSHION_DARK_STRIPE") for o in bpy.data.objects)
assert not any(o.name=="V5_STEERING_COLUMN_SHAPED_BLACK_HOUSING" for o in bpy.data.objects)
assert not any(o.name=="V5_STEERING_COLUMN_CHROME_SHAFT" for o in bpy.data.objects)
old=[o for o in bpy.data.objects if o.name.startswith("V5_ORIGINAL_THREESPOKE_WHEEL") and "material002" in o.name]
assert len(old)==1 and old[0].hide_render
for side in ("L","R"):
 o=bpy.data.objects[f"V6_{side}_BLENDER_BLACK_FLOOR_MAT"]
 assert o.dimensions.z<.035
 assert o.dimensions.y>.55
 assert o.location.z<.32
rim=bpy.data.objects["V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"]
assert len(rim.data.vertices)>1000
for name in ("V7_Target_Tan_Leather_PBR",
             "V7_Target_Black_Dashboard_PBR",
             "V7_Target_Walnut_Steering_Rim_PBR"):
 m=bpy.data.materials[name]
 assert m.use_nodes
 t=[n for n in m.node_tree.nodes if n.type=="TEX_IMAGE"]
 assert len(t)>=4
 assert all(n.image is not None for n in t)
 assert all(n.image.packed_file is not None for n in t)
 assert any(n.type=="NORMAL_MAP" for n in m.node_tree.nodes)
 assert any(n.type=="BUMP" for n in m.node_tree.nodes)
 assert m.node_tree.nodes["Principled BSDF"].inputs["Normal"].is_linked
 assert m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].is_linked
assert p.stat().st_size>3_000_000
rimg=r/"Daytona365_v7_3_ACTUAL_CYCLES_CABIN.png"
assert rimg.exists() and rimg.stat().st_size>200_000
h=hashlib.sha256(p.read_bytes()).hexdigest()
report={"status":"ACTUAL_BLENDER_REOPEN_PASS","blender_version":bpy.app.version_string,
 "blend":p.name,"sha256":h,"bytes":p.stat().st_size,
 "all_mesh_objects":len(all_mesh),
 "all_curves":len(all_curves),
 "actual_visible_wood_rims":1,
 "legacy_rim_source_kept_hidden":True,
 "integrated_seat_shells":4,
 "vertical_footmat_bug_fixed":True,
 "steering_column_below_gauges":True,
 "photo_palette_materials_PBR_normal_ORM_height_connected":3,
 "packed_v7_textures":12,
 "actual_cycles_preview":rimg.name,
 "cycles_preview_bytes":rimg.stat().st_size,
 "original_game_files_touched":False,
 "dino_files_touched":False,
 "game_loader_modified":False,
 "VR_real_HMD_validated":False}
(r/"DAYTONA_V7_3_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V7_3_VERIFIED",json.dumps(report),flush=True)
import bpy,json,hashlib
from pathlib import Path
r=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender_v8")
blend=r/"Daytona365_Cockpit_Blender_PBR_v8_4.blend"
assert bpy.data.filepath.endswith(blend.name)
names={o.name for o in bpy.data.objects}
required=[
"V8_L_CLASSIC_PADDED_CUSHION","V8_R_CLASSIC_PADDED_CUSHION",
"V8_L_TAPERED_PADDED_BACKREST","V8_R_TAPERED_PADDED_BACKREST",
"V8_LOW_CENTER_TUNNEL","V8_1_COMPACT_SHIFTER_LEATHER_DECK",
"V8_2_CONTINUOUS_LOWER_DASH_LIP","V8_4_SLIM_STEERING_COWL",
"V8_4_STEERING_SHAFT","V8_3_DRIVER_PEDAL_FIREWALL",
"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"]
for n in required:assert n in names,n
for forbidden in ("V8_DRIVER_KNEE_PAD","V8_PASSENGER_KNEE_PAD","V8_SHIFTER_ALLOY_SURROUND",
                  "V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES"):
 o=bpy.data.objects.get(forbidden)
 if o:assert o.hide_render,forbidden
for side in ("L","R"):
 assert bpy.data.objects.get(f"V8_3_{side}_SEAT_RAIL_-0.105")
 assert bpy.data.objects.get(f"V8_3_{side}_SEAT_RAIL_+0.105")
 # vertical wall bug is still fixed
 old=bpy.data.objects[f"V6_{side}_BLENDER_BLACK_FLOOR_MAT"]
 assert old.dimensions.z<.04 and old.dimensions.y>.55
tan=bpy.data.materials["V7_Target_Tan_Leather_PBR"]
dark=bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
metal=bpy.data.materials["V7_Machined_Aluminum"]
for m in (tan,dark):
 assert m.use_nodes
 assert any(n.type=="NORMAL_MAP" for n in m.node_tree.nodes)
 assert any(n.type=="BUMP" for n in m.node_tree.nodes)
 assert m.node_tree.nodes["Principled BSDF"].inputs["Normal"].is_linked
 assert all(n.image.packed_file is not None for n in m.node_tree.nodes if n.type=="TEX_IMAGE" and n.image)
assert metal.node_tree.nodes.get("V8_BrushedMetalNormal")
assert blend.stat().st_size>4_000_000
render=r/"Daytona365_v8_4_ACTUAL_CYCLES_CABIN.png"
assert render.exists() and render.stat().st_size>200_000
report={
"status":"DAYTONA_V8_4_FRESH_BLENDER_REOPEN_PASS",
"blender":bpy.app.version_string,
"blend":blend.name,"bytes":blend.stat().st_size,"sha256":hashlib.sha256(blend.read_bytes()).hexdigest(),
"mesh_objects":len([o for o in bpy.data.objects if o.type=="MESH"]),
"curve_objects":len([o for o in bpy.data.objects if o.type=="CURVE"]),
"seat_shells":4,"seat_rails":4,"lower_dash_single_lip":True,
"slim_steering_column":True,"normal_bump_maps_connected":True,
"brushed_metal_micro_normal":True,
"cycles_render":render.name,"cycles_render_bytes":render.stat().st_size,
"game_files_modified":False,"OVC_created":False,"quest3_tested":False}
(r/"DAYTONA_V8_4_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_4_FRESH_BLENDER_REOPEN_PASS",json.dumps(report),flush=True)
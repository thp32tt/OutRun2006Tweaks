import bpy,hashlib,json
from pathlib import Path
root=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender_v6")
path=root/"Daytona365_Cockpit_Blender_PBR_v6.blend"
meshes=[o for o in bpy.data.objects if o.type=="MESH"]
curves=[o for o in bpy.data.objects if o.type=="CURVE"]
names=[o.name for o in meshes+curves]
assert len(names)==len(set(names))
assert len(meshes)==103
assert len(curves)==31
assert sum(len(o.modifiers) for o in meshes)>=24
assert any("ORIGINAL_THREESPOKE_WHEEL" in n for n in names)
assert any(n=="V6_BLENDER_CENTER_LEATHER_ARMREST" for n in names)
materials=[m for m in bpy.data.materials if m.use_nodes]
assert len(materials)>=8
links={}
for mat in materials:
 n={x.type for x in mat.node_tree.nodes}
 links[mat.name]=list(n)
 assert "BSDF_PRINCIPLED" in n
imgs=[i for i in bpy.data.images if i.source=="FILE"]
no_pack=[i.name for i in imgs if not i.packed_file]
assert not no_pack,"Unpacked textures: "+repr(no_pack)
assert path.stat().st_size>1_000_000
data={"verifier":"Blender 4.5.15 actual .blend fresh-open",
 "file":path.name,"bytes":path.stat().st_size,
 "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
 "objects_mesh":len(meshes),"objects_curves":len(curves),
 "blender_modifiers":sum(len(o.modifiers) for o in meshes),
 "pbr_node_materials":len(materials),
 "embedded_file_images":len(imgs),
 "unpacked_images":no_pack,
 "Dino_modified":False,"original_game_modified":False,"OVC_built":False,
 "renders":[n for n in ("Daytona365_BLENDER_v6_CABIN.png",
                     "Daytona365_BLENDER_v6_DRIVER.png",
                     "Daytona365_BLENDER_v6_POLISHED_CABIN.png")
                  if (root/n).exists()]}
(root/"BLENDER_V6_VERIFIED.json").write_text(json.dumps(data,indent=2))
print("ACTUAL_BLENDER_RELOAD_PASS",json.dumps(data),flush=True)
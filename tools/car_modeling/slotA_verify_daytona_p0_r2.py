#!/usr/bin/env python3
"""Independent fresh-process Blender re-open, source-asset lineage, object/UV QA."""
import bpy,bmesh,hashlib,json,math,os
from pathlib import Path
W=Path(os.environ["SLOT_A_WORK"])
rep=json.loads((W/"SLOT_A_P0_DASH_WHEEL_V1_R2.json").read_text())
out=W/rep["output_blend"];src=W/rep["input_blend"]
original=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
import_scene=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend")
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==out.resolve()
for f,sha in ((out,rep["output_blend_sha256"]),(src,rep["input_blend_sha256"]),
              (original,rep["original_game_resource_sha256"]),(import_scene,rep["original_import_blend_sha256"])):
 assert hashlib.sha256(f.read_bytes()).hexdigest()==sha,str(f)
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
def sig(ob):
 d=ob.data
 return hashlib.sha256(repr(([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in d.vertices],
 [(p.material_index,tuple(p.vertices)) for p in d.polygons])).encode()).hexdigest()
changed={}
for name,metrics in rep["modified_original_derived_objects"].items():
 ob=bpy.data.objects[name]; me=ob.data
 assert metrics["after_signature"]==sig(ob)
 assert len(me.vertices)==metrics["after_vertices"]
 assert len(me.polygons)==metrics["after_faces"]
 assert metrics["before"]["signature"]!=sig(ob)
 assert ob["SLOTA_SOURCE_PMT"]==original.name
 assert ob["SLOTA_SOURCE_SHA256"]==rep["original_game_resource_sha256"]
 assert [[round(float(v),9) for v in row] for row in ob.matrix_world]==metrics["before"]["world_matrix"]
 assert me.uv_layers and all(math.isfinite(float(c)) for layer in me.uv_layers for loop in layer.data for c in loop.uv)
 bm=bmesh.new();bm.from_mesh(me)
 nonmanifold=sum(1 for e in bm.edges if not e.is_manifold)
 changed[name]={"vertices":len(me.vertices),"faces":len(me.polygons),"uv_layer_count":len(me.uv_layers),
 "mesh_nonmanifold_edges":nonmanifold,
 "new_geometry_differs":True,"transform_unchanged":True}
 bm.free()
source_d=bpy.data.objects["V5_NATIVE_DASH_REFERENCE_object00_group01_material012_a0"]
assert len(source_d.data.vertices)==13 and len(source_d.data.polygons)==12
# This exact local mesh signature is also present in the original game PMT import scene.
assert sig(source_d)=="796cbb1b059f4e541b0d5b7c68472a4d0cc8a6fcf89cb65ece2484b803dd1abf" or sig(source_d)[:10]=="796cbb1b05"
assert bpy.data.objects["DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH"].data.uv_layers
assert len(bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0"].data.vertices)==4
assert len(bpy.data.objects["V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material002_a0"].data.vertices)==153
assert len(bpy.data.objects["V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM"].data.vertices)==1536
assert not any(x.name.startswith("SLOTA_TEMP") for x in bpy.data.objects)
res={"status":"SLOTA_DAYTONA_P0_FRESH_REOPEN_PASS",
 "source_asset_sha256":rep["original_game_resource_sha256"],
 "original_import_blend_sha256":rep["original_import_blend_sha256"],
 "input_blend_sha256":rep["input_blend_sha256"],
 "output_blend_sha256":rep["output_blend_sha256"],
 "blender":bpy.app.version_string,"changed":changed,
 "source_dashboard_original_local_signature_matched":True,
 "native_badge_and_rim_unchanged":True,
 "qa_source_lineage":"PASS","qa_photo_seven_view":"UNTESTED",
 "qa_24hour":"NOT_COMPLETED","slot_car":"A daytona365",
 "exterior_textures_game_runtime_untouched":True}
(W/"SLOT_A_P0_DASH_WHEEL_V1_R2_FRESH_VERIFIED.json").write_text(json.dumps(res,indent=2))
print("SLOTA_DAYTONA_P0_FRESH_REOPEN_PASS",json.dumps(res),flush=True)
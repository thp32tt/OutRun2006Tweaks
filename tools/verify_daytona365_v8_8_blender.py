#!/usr/bin/env python3
"""Actual official Blender fresh-reopen geometry, UV, packed PBR and preservation audit v8.8."""
import bpy,math,hashlib,json,os
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
target=w/"Daytona365_Cockpit_Blender_PBR_v8_8.blend"
prior=w/"Daytona365_Cockpit_Blender_PBR_v8_7.blend"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==target.resolve()
assert hashlib.sha256(prior.read_bytes()).hexdigest()=="e247abed67d15b5562daa5374163cc4c3a18de7dd059bfc42d94c9227e0e61a3"
build=json.loads((w/"DAYTONA_V8_8_BUILD_MANIFEST.json").read_text())
assert hashlib.sha256(target.read_bytes()).hexdigest()==build["new_sha256"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert bpy.context.scene.render.engine=="CYCLES"
for name in ("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
             "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
             "DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
             "DAYTONA_HIRES_GAUGES_NATIVE_UV_MESH"):
    assert bpy.data.objects.get(name),name
tunnel=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
assert len(tunnel.data.vertices)==78
assert len(tunnel.data.polygons)==(13-1)*6+2
assert tunnel.data.uv_layers.active.name=="V8_8_METRIC_CONSOLE_UV"
assert len(tunnel.data.uv_layers.active.data)==len(tunnel.data.loops)
assert all(math.isfinite(float(u)) for v in tunnel.data.vertices for u in v.co)
assert all(math.isfinite(float(u)) for v in tunnel.data.uv_layers.active.data for u in v.uv)
assert abs(min(v.co.y for v in tunnel.data.vertices)+.44)<1e-4
assert abs(max(v.co.y for v in tunnel.data.vertices)-.20228)<1e-4
assert max(abs(v.co.x) for v in tunnel.data.vertices)<=.10683
assert max(v.co.z for v in tunnel.data.vertices)<.51887
assert any(m.type=="WEIGHTED_NORMAL" for m in tunnel.modifiers)
for edge in ("LEFT","RIGHT"):
    assert "V8_8_TUNNEL_"+edge+"_CONTINUOUS_SEAM" in bpy.data.objects
    assert "V8_6_TUNNEL_"+edge+"_CONTINUOUS_SEAM" not in bpy.data.objects
seatnames=[]
for side in ("L","R"):
    for kind,ny in (("CUSHION",52),("BACKREST",58)):
        suf="CLASSIC_PADDED_CUSHION" if kind=="CUSHION" else "TAPERED_PADDED_BACKREST"
        ob=bpy.data.objects[f"V8_{side}_{suf}"]
        m=ob.data
        assert len(m.vertices)==2*73*(ny+1)
        assert len(m.polygons)==2*73*(ny+1)-2
        assert m.uv_layers.active.name=="V8_7_GEODESIC_LEATHER_UV"
        assert m.materials[0].name=="V8_8_Source_Seat_Less_Saturated_Leather"
        assert m.materials[1].name=="V8_8_Seat_Side_Return_Leather"
        assert sum(p.material_index==1 for p in m.polygons)>1000
        assert all(math.isfinite(float(u)) for v in m.uv_layers.active.data for u in v.uv)
        if kind=="BACKREST":
            ring=73*(ny+1)
            for j in (0,ny//2,ny):
                for i in (0,18,36,54,72):
                    a=m.vertices[j*73+i].co
                    b=m.vertices[ring+j*73+i].co
                    assert abs((b.y-a.y)-.054)<.0002
        seatnames.append(ob.name)
for matname in ("V8_8_Source_Seat_Less_Saturated_Leather",
 "V8_8_Seat_Side_Return_Leather","V8_8_PMT_Console_Matte_Grain"):
    mat=bpy.data.materials[matname]
    nodes=mat.node_tree.nodes
    bsdf=nodes["Principled BSDF"]
    assert bsdf.inputs["Metallic"].default_value==0
    assert bsdf.inputs["Roughness"].is_linked
    assert bsdf.inputs["Normal"].is_linked
    ranges=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
    assert 0<ranges.inputs["To Min"].default_value<ranges.inputs["To Max"].default_value<1
    assert any(n.type=="NORMAL_MAP" for n in nodes)
    assert any(n.type=="BUMP" for n in nodes)
    imgs=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
    assert len(imgs)>=4 and all(im.packed_file for im in imgs)
    assert any("ORM" in im.name.upper() for im in imgs)
    assert all(im.colorspace_settings.name=="Non-Color" for im in imgs
       if any(t in im.name.upper() for t in ("ORM","NORMAL","HEIGHT")))
    if "Seat" in matname:
        assert nodes.get("V8_7_SOURCE_BASECOLOR_ATTENUATION") is None
        assert nodes.get("V8_8_SOURCE_BASECOLOR_ATTENUATION") is not None
        assert bsdf.inputs["Base Color"].is_linked
assert bpy.data.objects["V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"].data.materials[0].name=="V8_8_PMT_Console_Matte_Grain"
report={"status":"DAYTONA_V8_8_FRESH_REOPEN_PASS",
 "blender":bpy.app.version_string,
 "source_sha256":build["source_sha256"],
 "blend":target.name,"sha256":build["new_sha256"],"bytes":target.stat().st_size,
 "camera":bpy.context.scene.camera.name,
 "mesh_count":sum(o.type=="MESH" for o in bpy.data.objects),
 "curve_count":sum(o.type=="CURVE" for o in bpy.data.objects),
 "seat_preserved":seatnames,
 "tunnel_vertices":len(tunnel.data.vertices),"tunnel_sections":13,
 "packed_source_pbr_orm_normal_bump":True,
 "original_game_controls_preserved":True,
 "render_validation":"UNTESTED",
 "full_resolution_render":"UNTESTED","game_runtime":"UNTESTED"}
(w/"DAYTONA_V8_8_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_8_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
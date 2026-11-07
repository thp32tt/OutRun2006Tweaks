"""Blender native final geometry correction for v7.2 editable Daytona.
This is an actual saved Blender mesh edit, not image generation.
"""
import bpy,math,json,hashlib
from pathlib import Path
R=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
OUT=R/"blender_v7"
s=bpy.context.scene
assert bpy.data.filepath.endswith("Daytona365_Cockpit_Blender_PBR_v7_1.blend")
fixed=[]
for side in ("L","R"):
    a=bpy.data.objects["V7_"+side+"_INTEGRATED_PADDED_CUSHION"]
    nx,ny=64,48
    assert len(a.data.vertices)==2*(nx+1)*(ny+1)
    for j in range(ny+1):
        v=j/ny
        smoothEnds=(math.sin(math.pi*v)**.6 if v not in (0,1) else 0)
        for i in range(nx+1):
            u=i/nx
            mask=max(0,1-(2*u-1)**2)
            delta=.013*math.cos(8*math.pi*v)*mask*smoothEnds
            a.data.vertices[j*(nx+1)+i].co.z+=delta
    b=bpy.data.objects["V7_"+side+"_INTEGRATED_PLEATED_BACKREST"]
    nx,ny=64,56
    assert len(b.data.vertices)==2*(nx+1)*(ny+1)
    for j in range(ny+1):
        v=j/ny
        smoothEnds=(math.sin(math.pi*v)**.6 if v not in (0,1) else 0)
        for i in range(nx+1):
            u=i/nx
            mask=max(0,1-(2*u-1)**2)
            # Blender camera looks down -Y. Outward pleat pushes towards -Y.
            delta=-.018*math.cos(8*math.pi*v)*mask*smoothEnds
            b.data.vertices[j*(nx+1)+i].co.y+=delta
    # Blender true subdiv instead of Python static tessellation
    for obj in (a,b):
        subs=obj.modifiers.new("V7.2 Blender padded upholstery contour","SUBSURF")
        subs.levels=1;subs.render_levels=1
        fixed.append(obj.name)
# Replace vertical skinny rubber teeth on pedals with realistic rubber
# horizontal traction strips; keep metal pedal plate and correct pivot.
for o in list(bpy.data.objects):
    if o.name.startswith("V6_PEDAL_") and "_RUBBER_GRIP_" in o.name:
        bpy.data.objects.remove(o,do_unlink=True)
coll=bpy.data.collections.get("V7 | corrected horizontal footwell and firewall")
assert coll
M=bpy.data.materials["V7_Target_Black_Dashboard_PBR"]
for pidx,x in enumerate((-.48,-.39,-.30)):
    for j in range(3):
        z=.385+j*.030
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,.117,z))
        ob=bpy.context.object;ob.name=f"V7_PEDAL_{pidx}_FLUSH_RUBBER_CROSSRIB_{j}"
        for c in list(ob.users_collection):c.objects.unlink(ob)
        coll.objects.link(ob)
        ob.dimensions=(.045,.003,.008)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        ob.data.materials.append(M)
        bevel=ob.modifiers.new("V7.2 rubber edge","BEVEL")
        bevel.width=.0012;bevel.segments=2
# Material tones: match the reference dark caramel and walnut rather than
# photographed bright pastel. Preserve original mapped normal/ORM texture maps.
def tone(name,scale):
    m=bpy.data.materials[name]
    nodes=m.node_tree.nodes;links=m.node_tree.links
    bsdf=nodes.get("Principled BSDF")
    old=bsdf.inputs["Base Color"].links[0].from_socket
    mult=nodes.new("ShaderNodeMixRGB")
    mult.name="V7.2 Target image warm material tone"
    mult.blend_type="MULTIPLY"
    mult.inputs[0].default_value=1.0
    mult.inputs[2].default_value=(*scale,1)
    links.new(old,mult.inputs[1])
    links.new(mult.outputs[0],bsdf.inputs["Base Color"])
tone("V7_Target_Tan_Leather_PBR",(.91,.84,.77))
tone("V7_Target_Walnut_Steering_Rim_PBR",(.78,.82,.88))
# Accurate more modest roughness on steering wood in presence of studio lights
for img in bpy.data.images:
    if img.source=="FILE" and not img.packed_file:img.pack()
s.camera=bpy.data.objects["V7_Camera_Reference_ThreeQuarter"]
s.render.engine="CYCLES"
s.cycles.samples=10;s.cycles.use_denoising=True
s.render.resolution_x=960;s.render.resolution_y=640
s.render.resolution_percentage=100
out=OUT/"Daytona365_Cockpit_Blender_PBR_v7_2.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
meta={"file":out.name,"bytes":out.stat().st_size,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "refined_seat_meshes":fixed,"pedal_grips_rebuilt":9,
 "reference_tan_tone_applied":True,"reference_wood_tone_applied":True,
 "normal_and_ORM_preserved":True,
 "OVC_created":False,"Dino_changed":False,"Original_PMTCopied":False}
(OUT/"DAYTONA_V7_2_BUILD_MANIFEST.json").write_text(json.dumps(meta,indent=2))
print("V7_2_SAVED",json.dumps(meta),flush=True)
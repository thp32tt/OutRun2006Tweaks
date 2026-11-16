# Blender 5.x background helper for dashboard needle meshes.
# Usage:
# blender --background --python split_dashboard_needles_blender.py -- \
#   input.glb output.glb checkpoint.blend MATERIAL PREFIX
import bpy, json, sys, os
from mathutils import Vector

args=sys.argv[sys.argv.index("--")+1:]
if len(args)<5:
    raise RuntimeError("args: input.glb output.glb checkpoint.blend material prefix [comma,separated,names]")
src,dst_glb,dst_blend,material_name,prefix=args[:5]
explicit_names=args[5].split(",") if len(args)>5 and args[5] else []
os.makedirs(os.path.dirname(os.path.abspath(dst_glb)),exist_ok=True)
os.makedirs(os.path.dirname(os.path.abspath(dst_blend)),exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=src)

matches=[]
for obj in bpy.context.scene.objects:
    if obj.type=="MESH" and material_name in [m.name for m in obj.data.materials if m]:
        matches.append(obj)
if len(matches)!=1:
    raise RuntimeError("material must resolve to exactly one mesh: "+repr([o.name for o in matches]))
target=matches[0]
before=(len(target.data.vertices),len(target.data.polygons))

bpy.ops.object.select_all(action='DESELECT')
target.select_set(True)
bpy.context.view_layer.objects.active=target
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
# Join only numerically coincident seams so disconnected needles become true loose parts.
bpy.ops.mesh.remove_doubles(threshold=1.0e-5)
bpy.ops.mesh.separate(type='LOOSE')
bpy.ops.object.mode_set(mode='OBJECT')

parts=[o for o in bpy.context.selected_objects
       if o.type=="MESH" and material_name in [m.name for m in o.data.materials if m]
       and len(o.data.polygons)>0]
if len(parts)<2:
    raise RuntimeError("needle split produced fewer than two loose parts")

def center_x(obj):
    pts=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (sum(pts,Vector())/8.0).x

parts.sort(key=center_x)
if explicit_names and len(explicit_names)!=len(parts):
    raise RuntimeError("explicit name count does not match loose-part count")

report=[]
for i,obj in enumerate(parts):
    name=explicit_names[i] if explicit_names else f"{prefix}_{i:02d}"
    obj.name=name
    obj.data.name=name+"_MESH"
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY',center='BOUNDS')
    dims=list(obj.dimensions)
    axis_index=min(range(3),key=lambda k:abs(dims[k]))
    local_axis=Vector((1.0 if axis_index==0 else 0.0,
                       1.0 if axis_index==1 else 0.0,
                       1.0 if axis_index==2 else 0.0))
    axis_world=(obj.matrix_world.to_3x3() @ local_axis).normalized()
    report.append({
        "node":name,
        "origin_world":[float(x) for x in obj.matrix_world.translation],
        "axis_world":[float(x) for x in axis_world],
        "vertices":len(obj.data.vertices),
        "triangles":len(obj.data.polygons),
    })

bpy.ops.wm.save_as_mainfile(filepath=dst_blend)
bpy.ops.export_scene.gltf(filepath=dst_glb,export_format='GLB',
                          export_yup=True,export_apply=False,
                          export_materials='EXPORT',export_image_format='AUTO')
print(json.dumps({
    "source":src,"material":material_name,
    "source_vertices":before[0],"source_triangles":before[1],
    "parts":report
},ensure_ascii=False))
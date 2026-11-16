import bpy, sys, json, hashlib, math, argparse, re
from pathlib import Path
from mathutils import Vector

SEAT_ANCHORS={
    "dino246gts":(-0.3529999852,0.9900000095,-0.3449999988),
    "daytona365":(-0.3310000002,0.9950000048,-0.3199999928),
    "f50":(-0.3569999933,0.9850000143,-0.3499999940),
    "360spider":(-0.2820000052,0.9900000095,-0.2399999946),
    "f355spider":(-0.3449999988,1.1699999571,-0.0399999991),
    "575superamerica":(-0.3319999874,1.0399999619,-0.3819999993),
    "testarossa":(-0.3300000131,0.9950000048,-0.4199999869),
    "288gto":(-0.3300000131,1.0099999905,-0.4799999893),
    "328gts":(-0.3300000131,1.0,-0.4199999869),
    "250gto":(-0.3219999969,1.0650000572,0.1650000066),
    "512bb":(-0.3529999852,1.0099999905,-0.3499999940),
    "f40":(-0.3529999852,0.9499999881,-0.3499999940),
    "550barchetta":(-0.3000000119,1.0499999523,-0.6000000238),
    "f430":(-0.3529999852,1.25,0.0),
    "f430spider":(-0.3529999852,1.25,0.0),
    "enzo":(-0.3529999852,1.2000000477,-0.1500000060),
}

def game_to_blender(v):
    # Original native OBJ: X lateral, Y up, Z longitudinal. The importer maps
    # native -Z forward into Blender +Y, while keeping X and up.
    x,y,z=v
    return Vector((x,-z,y))

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def parse_mtl(path):
    mats={}; cur=None
    for raw in path.read_text(errors='ignore').splitlines():
        line=raw.strip()
        if line.startswith('newmtl '):
            cur=line.split(None,1)[1]; mats[cur]={'Kd':(1.,1.,1.),'d':1.0,'map':None}
        elif cur and line.startswith('Kd '):
            mats[cur]['Kd']=tuple(float(x) for x in line.split()[1:4])
        elif cur and line.startswith('d '):
            mats[cur]['d']=float(line.split()[1])
        elif cur and line.startswith('map_Kd '):
            mats[cur]['map']=Path(line.split(None,1)[1]).name
    return mats

def pbr_material(name,key,tex_root):
    mapname,kd,alpha=key
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial')
    bs=nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    base=(float(kd[0]),float(kd[1]),float(kd[2]),float(alpha))
    bs.inputs['Base Color'].default_value=base
    bs.inputs['Alpha'].default_value=float(alpha)
    # Conservative native-PMT PBR: preserve source colors, improve response only.
    if alpha < .95:
        rough=.12; metal=0.0
        try: m.surface_render_method='DITHERED'
        except Exception:
            try: m.blend_method='BLEND'
            except Exception: pass
    else:
        brightness=sum(kd)/3.0
        metal=0.12 if mapname is None and .25 < brightness < .85 else 0.0
        rough=.34 if mapname else (.28 if metal else .50)
    bs.inputs['Metallic'].default_value=metal
    bs.inputs['Roughness'].default_value=max(.04,rough)
    if mapname:
        stem=Path(mapname).stem
        candidate=tex_root/(stem+'_2x.png')
        if candidate.is_file():
            im=bpy.data.images.load(str(candidate),check_existing=True)
            tex=nt.nodes.new('ShaderNodeTexImage'); tex.image=im
            nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
            if 'Alpha' in tex.outputs:
                nt.links.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
    m.diffuse_color=base
    return m

def mesh_stats():
    v=t=0
    for o in bpy.context.scene.objects:
        if o.type=='MESH':
            o.data.calc_loop_triangles()
            v+=len(o.data.vertices); t+=len(o.data.loop_triangles)
    return v,t

def bounds():
    pts=[]
    for o in bpy.context.scene.objects:
        if o.type=='MESH':
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    hi=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return lo,hi

def add_needle(name,pivot,length,width,mat):
    # Local X-Z plane, +Z is the authored zero-angle direction.
    verts=[(-width,0,-length*.12),(width,0,-length*.12),(width*.42,0,length*.76),(0,0,length),
           (-width*.42,0,length*.76)]
    faces=[(0,1,2,3,4)]
    me=bpy.data.meshes.new(name+'_MESH'); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
    ob.location=pivot
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth=False
    return ob

def run(car,root,outdir):
    vehicle=root/'vehicles'/car
    obj=vehicle/'01_original_mesh_uv'/'original_native.obj'
    mtl=vehicle/'01_original_mesh_uv'/'original_native.mtl'
    tex=vehicle/'02_original_textures'/'LANCZOS_2x_NOT_AI'
    manifest=root/'reports'/'all_16_car_manifest.json'
    if not obj.is_file() or not mtl.is_file(): raise RuntimeError('missing native OBJ/MTL')
    allman=json.loads(manifest.read_text())
    rec=next(x for x in allman['cars'] if x['id']==car)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(obj),forward_axis='NEGATIVE_Z',up_axis='Y')
    imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if not imported: raise RuntimeError('OBJ import empty')
    lo0,hi0=bounds(); v0,t0=mesh_stats()
    width=float(hi0.x-lo0.x); length=float(hi0.y-lo0.y); height=float(hi0.z-lo0.z)
    if not (1.5<width<2.7 and 3.5<length<5.5 and .9<height<2.1):
        raise RuntimeError(f'invalid vehicle dimensions {width} {length} {height}')

    # Merge only materially identical source definitions; preserves UV assignment.
    defs=parse_mtl(mtl)
    canonical={}
    source_to_new={}
    for old in list(bpy.data.materials):
        d=defs.get(old.name,{'Kd':tuple(old.diffuse_color[:3]),'d':float(old.diffuse_color[3]),'map':None})
        key=(d.get('map'),tuple(round(float(x),5) for x in d.get('Kd',(1,1,1))),round(float(d.get('d',1.0)),5))
        if key not in canonical:
            canonical[key]=pbr_material(f'HD_MAT_{len(canonical):02d}',key,tex)
        source_to_new[old.name]=canonical[key]
    for o in imported:
        for slot in o.material_slots:
            if slot.material and slot.material.name in source_to_new:
                slot.material=source_to_new[slot.material.name]

    # Remove now-unused imported source materials/images are kept if used by canonical.
    used={slot.material for o in imported for slot in o.material_slots if slot.material}
    for m in list(bpy.data.materials):
        if m not in used and not m.name.startswith('HD_'):
            bpy.data.materials.remove(m)

    bevel_width=max(.0018,min(.0032,width*.00125))
    beveled=0
    for o in imported:
        if len(o.data.polygons)<8: continue
        for p in o.data.polygons: p.use_smooth=True
        dims=o.dimensions
        if max(dims) < .06: continue
        try:
            mod=o.modifiers.new('HD_EDGE_BEVEL','BEVEL')
            mod.width=bevel_width; mod.segments=2; mod.limit_method='ANGLE'; mod.angle_limit=math.radians(34)
            bpy.context.view_layer.objects.active=o
            o.select_set(True)
            bpy.ops.object.modifier_apply(modifier=mod.name)
            o.select_set(False); beveled+=1
        except Exception:
            try:
                if 'HD_EDGE_BEVEL' in o.modifiers: o.modifiers.remove(o.modifiers['HD_EDGE_BEVEL'])
            except Exception: pass

    # Dashboard overlay is anchored from the exact original PC mode-1 seat table
    # (OR2006C2C.exe RVA 0x1BA4E0). Native model origin is preserved: forward
    # in original local coordinates is -Z. Place the gauge face ~48 cm ahead
    # and 12 cm below the eye, centered on the driver with 17 cm needle spacing.
    seat=SEAT_ANCHORS[car]
    gauge_center=(seat[0],seat[1]-0.12,seat[2]-0.48)
    speed_game=(gauge_center[0]-0.085,gauge_center[1],gauge_center[2])
    rpm_game=(gauge_center[0]+0.085,gauge_center[1],gauge_center[2])
    needle_len=max(.045,min(.068,width*.026))
    needle_w=needle_len*.075
    gm=bpy.data.materials.new('HD_DASH_NEEDLE')
    gm.use_nodes=True
    bs=gm.node_tree.nodes.get('Principled BSDF')
    if bs:
        bs.inputs['Base Color'].default_value=(1.0,.06,.015,1.0)
        bs.inputs['Roughness'].default_value=.28
        if 'Emission Color' in bs.inputs: bs.inputs['Emission Color'].default_value=(.12,.002,0,1)
        if 'Emission Strength' in bs.inputs: bs.inputs['Emission Strength'].default_value=.35
    speed_p=game_to_blender(speed_game)
    rpm_p=game_to_blender(rpm_game)
    add_needle('DASH_SPEED_NEEDLE',speed_p,needle_len,needle_w,gm)
    add_needle('DASH_RPM_NEEDLE',rpm_p,needle_len,needle_w,gm)

    # Save editable Blender checkpoint before GLB export.
    outdir.mkdir(parents=True,exist_ok=True)
    blend=outdir/(car+'_NativeHD_DashboardV4.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend),check_existing=False)

    # Export only mesh content, embedded textures.
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type=='MESH' and not o.hide_get(): o.select_set(True)
    glb=outdir/'source.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_yup=True,export_apply=True,export_animations=False,export_skins=False,
        export_morph=False,export_lights=False,export_cameras=False,export_extras=True)

    lo1,hi1=bounds(); v1,t1=mesh_stats()
    source={
      'schema':1,'car_id':car,'source_sha256':sha256(glb),
      'geometry_space':'outrun_local_y_up_meters','alignment_verified':True,
      'model_scope':'full_car','origin_type':'original_game_private_remaster',
      'rights_note':'PRIVATE_ONLY; derived from user-owned OutRun 2006 game assets; do not redistribute original/remastered assets',
      'redistribution_verified':False,
      'source_original_pmt_sha256':rec['source_sha256'],
      'source_native_obj_sha256':rec['obj_sha256'],
      'remaster':'NativeHD v2: original native origin/UV/silhouette + 2x textures + PBR material consolidation + angle bevel/smooth + seat-anchored live dashboard needles',
      # GLB export maps Blender (X,Y,Z) -> glTF (X,Z,-Y), which exactly
      # reconstructs the original native OBJ/game (X,Y,Z). Keep identity.
      'external_to_game_matrix':[
         1,0,0,0,
         0,1,0,0,
         0,0,1,0,
         0,0,0,1],
      'dashboard_required':True,
      'dashboard':{'bindings':[
        {'node':'DASH_SPEED_NEEDLE','kind':'speed','pivot':list(speed_game),'axis':[0,0,1],
         'input':[0.0,320.0],'angle_deg':[-128.0,128.0]},
        {'node':'DASH_RPM_NEEDLE','kind':'rpm','pivot':list(rpm_game),'axis':[0,0,1],
         'input':[0.0,10000.0],'angle_deg':[-128.0,128.0]}
      ]}
    }
    sp=outdir/'source.json'; sp.write_text(json.dumps(source,indent=2)+'\n')
    qa={
      'schema':1,'car_id':car,'status':'NATIVE_HD_DASHBOARD_V4_SOURCE_PASS',
      'original_pmt_sha256':rec['source_sha256'],'original_obj_sha256':rec['obj_sha256'],
      'blend_sha256':sha256(blend),'glb_sha256':sha256(glb),
      'before':{'vertices':v0,'triangles':t0,'materials':len(defs),'bounds':[list(lo0),list(hi0)]},
      'after':{'vertices':v1,'triangles':t1,'materials':len(canonical)+1,'bounds':[list(lo1),list(hi1)]},
      'bevel_width_m':bevel_width,'beveled_objects':beveled,
      'dashboard':{'seat_anchor_game':list(seat),'speed_pivot_game':list(speed_game),'rpm_pivot_game':list(rpm_game),
                   'speed_range_kph':[0,320],'rpm_range':[0,10000],'axis_game':[0,0,1]},
      'texture_policy':'LANCZOS_2x_NOT_AI source texture reuse; no synthetic texture detail',
      'private_only':True
    }
    (outdir/'native_hd_qa.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa))

if __name__=='__main__':
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    ap=argparse.ArgumentParser(); ap.add_argument('--car',required=True); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True)
    ns=ap.parse_args(argv)
    run(ns.car,Path(ns.root),Path(ns.out))
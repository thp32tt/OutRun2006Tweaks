import hashlib
import io
import json
from pathlib import Path
import struct
import sys
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ferrari_batch_converter import (
    ConversionError, audit_entry, check_output, command_audit, convert_one,
    load_glb, encode_sidecar, accessor, rgba_dds, read_json,
)


def sample_png(color):
    im = Image.new('RGBA', (4, 4), color)
    b = io.BytesIO()
    im.save(b, format='PNG')
    return b.getvalue()


def fixture(tmp: Path, *, broken_sha=False):
    src = tmp / 'sources' / 'dino246gts'
    src.mkdir(parents=True)
    bin_data = bytearray()
    views=[]
    def blob(binary):
        while len(bin_data) % 4:
            bin_data.append(0)
        o=len(bin_data)
        bin_data.extend(binary)
        views.append({'buffer':0,'byteOffset':o,'byteLength':len(binary)})
        return len(views)-1
    pos = struct.pack('<12f', 0.,0.,0., 1.,0.,0., 0.,1.,0., 1.,1.,0.)
    normal = struct.pack('<12f', *(0.,0.,1.)*4)
    uv=struct.pack('<8f', 0.,0., 1.,0., 0.,1., 1.,1.)
    index=struct.pack('<6H', 0,1,2,1,3,2)
    bpos=blob(pos);bnorm=blob(normal);buv=blob(uv);bidx=blob(index)
    cimg=blob(sample_png((180,55,40,255)))
    ng=blob(sample_png((128,128,255,255)))
    mr=blob(sample_png((255,145,22,255)))
    images=[{'bufferView':x,'mimeType':'image/png'} for x in [cimg,ng,mr]]
    mats=[
       {'name':'opaque_paint','pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicRoughnessTexture':{'index':2},'roughnessFactor':0.65,'metallicFactor':0.5}, 'normalTexture':{'index':1}},
       {'name':'windscreen_glass','alphaMode':'BLEND','pbrMetallicRoughness':{'baseColorTexture':{'index':0},'baseColorFactor':[1,1,1,0.3]}},
    ]
    g={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(bin_data)}],
      'bufferViews':views,
      'accessors':[
        {'bufferView':bpos,'componentType':5126,'count':4,'type':'VEC3'},
        {'bufferView':bnorm,'componentType':5126,'count':4,'type':'VEC3'},
        {'bufferView':buv,'componentType':5126,'count':4,'type':'VEC2'},
        {'bufferView':bidx,'componentType':5123,'count':6,'type':'SCALAR'},
       ],
       'images':images,'textures':[{'source':i} for i in range(3)],'materials':mats,
       'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'TEXCOORD_0':2},'indices':3,'material':i} for i in range(2)]}],
       'nodes':[{'mesh':0}], 'scenes':[{'nodes':[0]}], 'scene':0}
    raw=json.dumps(g,separators=(',',':')).encode()
    raw +=b' ' *((-len(raw))%4)
    bin_data.extend(b'\0' *((-len(bin_data))%4))
    glb=b'glTF'+struct.pack('<2I',2,12+8+len(raw)+8+len(bin_data))+struct.pack('<I4s',len(raw),b'JSON')+raw+struct.pack('<I4s',len(bin_data),b'BIN\x00')+bin_data
    path=src/'source.glb'
    path.write_bytes(glb)
    meta={'car_id':'dino246gts','source_sha256':hashlib.sha256(glb).hexdigest() if not broken_sha else '0'*64,
          'origin_type':'user_authored','model_scope':'full_car','alignment_verified':True,
          'geometry_space':'outrun_local_y_up_meters',
          'external_to_game_matrix':[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]}
    (src/'source.json').write_text(json.dumps(meta))
    return g, path


def test_conversion(tmp_path):
    g, path = fixture(tmp_path)
    car={'id':'dino246gts','name':'Dino 246 GTS','native_source':'obj_plcar_dino_pmt.sz'}
    audit=audit_entry(tmp_path,car,True)
    assert audit['status']=='READY_PRIVATE_CONVERSION',audit
    result=convert_one(tmp_path,car)
    assert result['status']=='OVRCABH3_STATIC_CONVERSION_PASS_NOT_GAME_TESTED'
    assert result['triangles']==4 and result['materials']==2 and result['glass_triangles']==2
    assert result['normal_map_materials']==1
    assert result['game_bounds']==([0.,0.,0.],[1.,1.,0.])
    p=tmp_path/'outputs/dino246gts/dino246gts_External_Test.ovc'
    meta=check_output(p)
    assert meta['triangles']==4 and meta['vertices']==8
    try:convert_one(tmp_path,car)
    except ConversionError as e:assert 'already exists' in str(e)
    else:raise AssertionError('must not overwrite existing conversion')
    raw=bytearray(p.read_bytes());raw[-1]^=1
    corrupted=tmp_path/'corrupt.ovc';corrupted.write_bytes(raw)
    try:check_output(corrupted)
    except ConversionError as e:assert 'CRC' in str(e)
    else:raise AssertionError('corrupt sidecar accepted')


def test_source_fail_closed(tmp_path):
    _, path=fixture(tmp_path,broken_sha=True)
    car={'id':'dino246gts','name':'Dino'}
    assert audit_entry(tmp_path,car)['status']=='BLOCKED_SOURCE_QA'
    meta=path.with_name('source.json')
    data=read_json(meta);data['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();data['model_scope']='interior_only'
    meta.write_text(json.dumps(data))
    assert audit_entry(tmp_path,car)['status']=='BLOCKED_SOURCE_QA'


def test_dds_size():
    raw=rgba_dds(Image.new('RGBA',(16,8),(10,20,30,255)))
    assert raw[:4]==b'DDS '
    assert struct.unpack_from('<I',raw,28)[0]==5
    assert len(raw)==128+16*8*4+8*4*4+4*2*4+2*1*4+1*1*4
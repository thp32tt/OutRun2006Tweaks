#!/usr/bin/env python3
"""Validate standalone PMT-derived GLBs without modifying the model."""
import argparse, io, json, struct, sys
from pathlib import Path
from PIL import Image

COMPONENT_BYTES={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}
TYPE_COUNT={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT4":16}


def validate(path):
    data=Path(path).read_bytes()
    if len(data)<28 or data[:4]!=b'glTF':
        raise ValueError('missing GLB signature')
    version,total=struct.unpack_from('<II',data,4)
    if version!=2 or total!=len(data):
        raise ValueError('invalid GLB version/length')
    jo,jt=data[12:20][:4],data[16:20]
    njson=struct.unpack_from('<I',data,12)[0]
    if jt!=b'JSON' or njson%4 or 20+njson+8>len(data):
        raise ValueError('invalid JSON chunk')
    doc=json.loads(data[20:20+njson].decode('utf-8'))
    off=20+njson
    nbin=struct.unpack_from('<I',data,off)[0]
    if data[off+4:off+8]!=b'BIN'+bytes((0,)) or off+8+nbin!=len(data):
        raise ValueError('invalid BIN chunk')
    blob=data[off+8:]
    if len(doc['buffers'])!=1 or doc['buffers'][0]['byteLength']>len(blob):
        raise ValueError('invalid embedded buffer')
    view_data=[]
    for i,v in enumerate(doc['bufferViews']):
        b=v.get('byteOffset',0)
        e=b+v['byteLength']
        if v.get('buffer')!=0 or b<0 or b%4 or e>len(blob):
            raise ValueError('bufferView %d bounds' % i)
        view_data.append(memoryview(blob)[b:e])
    for i,a in enumerate(doc['accessors']):
        width=TYPE_COUNT[a['type']]*COMPONENT_BYTES[a['componentType']]
        view=doc['bufferViews'][a['bufferView']]
        start=a.get('byteOffset',0)
        if start+width*a['count']>view['byteLength']:
            raise ValueError('accessor %d overflow' % i)
    for i,m in enumerate(doc['meshes']):
        for p in m['primitives']:
            attrs=p['attributes']
            if not {'POSITION','NORMAL','TEXCOORD_0'}<=set(attrs):
                raise ValueError('mesh %d missing attributes' % i)
            a=doc['accessors'][attrs['POSITION']]
            normals=doc['accessors'][attrs['NORMAL']]
            uv=doc['accessors'][attrs['TEXCOORD_0']]
            idx=doc['accessors'][p['indices']]
            if a['count']!=normals['count'] or a['count']!=uv['count'] or idx['count']%3:
                raise ValueError('vertex attribute / index mismatch in mesh %d' % i)
    for i,image in enumerate(doc.get('images',[])):
        im=Image.open(io.BytesIO(view_data[image['bufferView']]))
        im.load()
        if im.width<1 or im.height<1:
            raise ValueError('empty texture %d' % i)
    if not doc['scenes'][doc['scene']]['nodes']:
        raise ValueError('empty scene')
    return {'path':str(path),'bytes':len(data),'meshCount':len(doc['meshes']),
            'textureCount':len(doc.get('images',[])),
            'triangles':sum(doc['accessors'][p['indices']]['count']//3
                for m in doc['meshes'] for p in m['primitives']),
            'valid':True}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('glbs',nargs='+',type=Path)
    args=ap.parse_args()
    for file in args.glbs:
        print(json.dumps(validate(file),ensure_ascii=False))


if __name__=='__main__':
    main()

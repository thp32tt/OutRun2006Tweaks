#!/usr/bin/env python3
"""Export original user-provided Dino HQ GLB as PMT-free native OVC2.

Requires: pip install trimesh numpy Pillow
OVC2: <8s7I> header (magic OVRCABH2, version 2, group/material counts,
vertices, triangles, body size, CRC32); per mesh <HHIII> for name bytes,
material id, vertex count, index count and index width (2 or 4); 8xf32 vertices
(XYZ + normal + UV), little-endian indices; per material u32 DDS length + DDS.
No native OutRun game PMT/EXE assets read or written. 1024/512 albedo retained.
Normal/metallic-roughness PBR GPU shading is not part of R26 fixed function.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import zipfile
import zlib

HQ_ENTRY="Dino_246_GTS_Cockpit_LHD_v15_HQ_TEXTURED.glb"
HQ_SHA256="4763b52df208ab51693e21d135fcc1e97c7afd93d0fd9ad270928eb9f971fb3d"
MAGIC=b"OVRCABH2"
MAX_BYTES=128*1024*1024

def arbg_dds(image):
    import numpy as np
    from PIL import Image
    img=image.convert("RGBA")
    width,height=img.size
    if (width==0 or height==0 or width>2048 or height>2048 or
        width&(width-1) or height&(height-1)):
        raise ValueError(f"Unsupported albedo texture dimensions {img.size}")
    mips=1
    for dim in (max(width,height),):
        while dim>1:
            dim>>=1;mips+=1
    header=bytearray(128)
    header[:4]=b"DDS "
    def u32(offset,value):struct.pack_into("<I",header,offset,value)
    u32(4,124)
    u32(8,0x0002100f) # caps/height/width/pitch/pixelformat/mips
    u32(12,height);u32(16,width);u32(20,width*4);u32(28,mips)
    u32(76,32);u32(80,0x41) # DDPF_RGB | DDPF_ALPHAPIXELS
    u32(88,32);u32(92,0x00ff0000);u32(96,0x0000ff00)
    u32(100,0x000000ff);u32(104,0xff000000)
    u32(108,0x00401008 if mips>1 else 0x1000)
    output=bytearray(header)
    for level in range(mips):
        target=(max(1,width>>level),max(1,height>>level))
        scaled=img if level==0 else img.resize(target,Image.Resampling.LANCZOS)
        rgba=np.asarray(scaled,dtype=np.uint8)
        # D3DFMT_A8R8G8B8 is stored as B,G,R,A on little-endian x86.
        output+=rgba[:,:,[2,1,0,3]].tobytes()
    return bytes(output)

def _material_rgba(material):
    from PIL import Image
    if material is None:
        return Image.new("RGBA",(4,4),(255,255,255,255))
    src=getattr(material,"baseColorTexture",None)
    factor=getattr(material,"baseColorFactor",None)
    if factor is None:factor=(255,255,255,255)
    else:factor=tuple(int(v) for v in factor)
    if src is None:
        return Image.new("RGBA",(4,4),factor)
    img=src.convert("RGBA")
    if factor!=(255,255,255,255):
        import numpy as np
        px=np.asarray(img,dtype=np.uint16)
        px=(px*np.asarray(factor,dtype=np.uint16)[None,None,:]+127)//255
        img=Image.fromarray(px.astype("uint8"),"RGBA")
    return img

def build(source_zip: Path, output: Path):
    import numpy as np
    import trimesh
    with zipfile.ZipFile(source_zip) as archive:
        glb=archive.read(HQ_ENTRY)
    if hashlib.sha256(glb).hexdigest()!=HQ_SHA256:
        raise ValueError("Unknown HQ model SHA256")
    scene=trimesh.load(io.BytesIO(glb),file_type="glb",
                       force="scene",process=False)
    items=list(scene.dump(concatenate=False)) # bake scene node transforms
    if not items or len(items)>512:
        raise ValueError("HQ mesh count is outside supported bounds")
    materials={}
    textures=[]
    body=bytearray()
    total_vertices=total_triangles=0
    material_names=[]
    mesh_diagnostics=[]
    for meshid,mesh in enumerate(items):
        if not isinstance(mesh,trimesh.Trimesh):
            raise ValueError(f"Nontriangular primitive {meshid}")
        material=getattr(mesh.visual,"material",None)
        key=str(getattr(material,"name",None) or f"material_{meshid}")
        if key not in materials:
            if len(materials)>=64:raise ValueError("Too many HQ materials")
            texture=arbg_dds(_material_rgba(material))
            materials[key]=len(materials)
            textures.append(texture)
            material_names.append(key)
        mat_index=materials[key]
        vertices=np.asarray(mesh.vertices,dtype="<f4")
        normals=np.asarray(mesh.vertex_normals,dtype="<f4")
        uv=getattr(mesh.visual,"uv",None)
        if uv is None:uv=np.zeros((len(vertices),2),dtype="<f4")
        else:uv=np.asarray(uv,dtype="<f4")
        faces=np.asarray(mesh.faces)
        if(len(vertices)<3 or len(vertices)>1_000_000 or
           len(faces)==0 or normals.shape!=vertices.shape or
           uv.shape!=(len(vertices),2) or faces.shape[1]!=3):
            raise ValueError(f"Broken HQ mesh {meshid}")
        if(not np.isfinite(vertices).all() or not np.isfinite(normals).all()
           or not np.isfinite(uv).all() or
           np.max(np.abs(vertices))>10000 or
           np.max(np.abs(normals))>10000 or
           np.max(np.abs(uv))>10000):
            raise ValueError(f"Nonfinite HQ vertex/UV {meshid}")
        if(faces.min()<0 or faces.max()>=len(vertices)):
            raise ValueError(f"Out of range HQ indices {meshid}")
        packed=np.column_stack((vertices,normals,uv)).astype("<f4").tobytes()
        indices=faces.reshape(-1)
        # OVC2 supports both DWORD and WORD D3D9 index formats.
        index_width=2 if len(vertices)<=65535 else 4
        index_dtype="<u2" if index_width==2 else "<u4"
        index_bytes=indices.astype(index_dtype).tobytes()
        name=(str(getattr(mesh,"metadata",{}).get("name","")) or
              f"HQ_{meshid:03d}").encode("utf-8")[:240]
        if not name:name=f"HQ_{meshid:03d}".encode("ascii")
        body+=struct.pack("<HHIII",len(name),mat_index,len(vertices),
                          len(indices),index_width)
        body+=name+packed+index_bytes
        total_vertices+=len(vertices)
        total_triangles+=len(faces)
        mesh_diagnostics.append((len(vertices),len(faces),index_width))
    for texture in textures:
        body+=struct.pack("<I",len(texture))+texture
    if (len(body)>MAX_BYTES-36 or total_vertices>1_000_000 or
        total_triangles>2_000_000):
        raise ValueError("HQ OVC2 exceeds bounded x86 VR loader")
    header=struct.pack("<8s7I",MAGIC,2,len(items),len(textures),
                       total_vertices,total_triangles,len(body),zlib.crc32(body))
    encoded=header+body
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(encoded)
    return {
        "status":"OVC2_HQ_GLTF_TO_D3D9_SIDECAR",
        "source_glb_sha256":HQ_SHA256,
        "sidecar_sha256":hashlib.sha256(encoded).hexdigest(),
        "sidecar_bytes":len(encoded),
        "meshes":len(items),"materials":len(textures),
        "vertices":total_vertices,"triangles":total_triangles,
        "material_names":material_names,
        "index32_meshes":sum(n[2]==4 for n in mesh_diagnostics),
        "texture_dimensions":[list((
            struct.unpack_from("<I",texture,16)[0],
            struct.unpack_from("<I",texture,12)[0])) for texture in textures],
        "preserves_native_pmt":True,
        "fixed_function_albedo_only":True,
        "pbr_normal_metal_rough_gpu":"NOT_IMPLEMENTED",
        "runtime_hmd":"UNTESTED"
    }
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-hq-zip",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--report",type=Path)
    args=parser.parse_args()
    result=build(args.source_hq_zip,args.output)
    if args.report:
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                               encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

#!/usr/bin/env python3
"""Audit user-supplied Dino v15 GLB <-> OVC2 geometry and albedo parity.
No original game PMT/EXE access. Run on the owner PC; GLB asset is not checked into Git.
Requires: numpy, trimesh, Pillow
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile
import zlib

GLB_ENTRY="Dino_246_GTS_Cockpit_LHD_v15_HQ_TEXTURED.glb"
SOURCE_SHA="4763b52df208ab51693e21d135fcc1e97c7afd93d0fd9ad270928eb9f971fb3d"

def audit(source_zip:Path,sidecar:Path):
    import numpy as np
    import trimesh
    from PIL import Image
    with zipfile.ZipFile(source_zip) as archive:
        glb=archive.read(GLB_ENTRY)
    if hashlib.sha256(glb).hexdigest()!=SOURCE_SHA:
        raise ValueError("GLB does not match the inspected HQ v15 source")
    with sidecar.open("rb") as f:
        blob=f.read()
    if len(blob)<36 or len(blob)>128*1024*1024:raise ValueError("OVC file length")
    magic,version,nmesh,nmat,nvertex,ntriangle,payload,crc=struct.unpack_from("<8s7I",blob,0)
    if (magic!=b"OVRCABH2" or version!=2 or payload!=len(blob)-36 or
        zlib.crc32(blob[36:])!=crc):
        raise ValueError("OVC2 header/CRC mismatch")
    meshes=list(trimesh.load(io.BytesIO(glb),file_type="glb",
                             force="scene",process=False).dump(concatenate=False))
    if nmesh!=len(meshes) or nmesh>512 or nmat>64:
        raise ValueError("GLB/OVC mesh or material count mismatch")
    pos=36
    observed_materials={}
    texture_sources={}
    vertex_sum=tri_sum=0
    lo=np.full(3,np.inf,dtype=np.float64)
    hi=np.full(3,-np.inf,dtype=np.float64)
    for i,mesh in enumerate(meshes):
        if pos+16>len(blob):raise ValueError(f"Mesh {i} header truncated")
        name_len,material,nv,ni,index_width=struct.unpack_from("<HHIII",blob,pos)
        pos+=16
        if index_width not in (2,4) or name_len<1 or pos+name_len>len(blob):
            raise ValueError(f"Mesh {i} index/name")
        name=blob[pos:pos+name_len].decode("utf-8")
        pos+=name_len
        if not (name and nv==len(mesh.vertices) and ni==len(mesh.faces)*3):
            raise ValueError(f"Mesh {i} vertex/triangle count")
        material_obj=getattr(mesh.visual,"material",None)
        key=str(getattr(material_obj,"name",None) or f"material_{i}")
        if key not in observed_materials:
            observed_materials[key]=len(observed_materials)
            texture_sources[material]=material_obj
        if material!=observed_materials[key]:
            raise ValueError(f"Mesh {i} material identity mismatch")
        uv=getattr(mesh.visual,"uv",None)
        if uv is None: uv=np.zeros((nv,2),dtype="<f4")
        vertex=np.column_stack((
            np.asarray(mesh.vertices,dtype="<f4"),
            np.asarray(mesh.vertex_normals,dtype="<f4"),
            np.asarray(uv,dtype="<f4"))).astype("<f4")
        vb=nv*32
        ib=ni*index_width
        if pos+vb+ib>len(blob):raise ValueError(f"Mesh {i} bounds")
        if vertex.tobytes()!=blob[pos:pos+vb]:
            raise ValueError(f"Mesh {i} geometry/normal/UV mismatch")
        pos+=vb
        expected=np.asarray(mesh.faces).reshape(-1).astype(
            "<u2" if index_width==2 else "<u4").tobytes()
        if expected!=blob[pos:pos+ib]:
            raise ValueError(f"Mesh {i} triangle index mismatch")
        pos+=ib
        vertex_sum+=nv
        tri_sum+=ni//3
        lo=np.minimum(lo,np.min(mesh.vertices,axis=0))
        hi=np.maximum(hi,np.max(mesh.vertices,axis=0))
    if (vertex_sum,tri_sum,len(observed_materials))!=(nvertex,ntriangle,nmat):
        raise ValueError("OVC aggregate count mismatch")
    textures=[]
    for i in range(nmat):
        if pos+4>len(blob):raise ValueError(f"Material {i} DDS length")
        length=struct.unpack_from("<I",blob,pos)[0]
        pos+=4
        if length<128 or pos+length>len(blob):
            raise ValueError(f"Material {i} DDS body")
        dds=blob[pos:pos+length]
        pos+=length
        if dds[:4]!=b"DDS ":raise ValueError(f"Material {i} DDS signature")
        width,height=struct.unpack_from("<II",dds,16)[0],struct.unpack_from("<I",dds,12)[0]
        original=texture_sources[i]
        image=getattr(original,"baseColorTexture",None)
        factor=getattr(original,"baseColorFactor",None)
        color=(255,255,255,255) if factor is None else tuple(int(v) for v in factor)
        if image is None: rgb=Image.new("RGBA",(4,4),color)
        else:
            rgb=image.convert("RGBA")
            if color!=(255,255,255,255):
                rgba=np.asarray(rgb,dtype=np.uint16)
                rgba=(rgba*np.asarray(color,dtype=np.uint16)[None,None,:]+127)//255
                rgb=Image.fromarray(rgba.astype("uint8"),"RGBA")
        if rgb.size!=(width,height):raise ValueError(f"Material {i} image size")
        reference=np.asarray(rgb,dtype=np.uint8)[:,:,[2,1,0,3]]
        if reference.tobytes()!=dds[128:128+width*height*4]:
            raise ValueError(f"Material {i} original albedo mismatch")
        textures.append({"index":i,"size":[width,height],"name":getattr(original,"name",None)})
    if pos!=len(blob):raise ValueError("OVC trailing data")
    return {
        "status":"PASS_EXACT_GLTF_OVC2_GEOMETRY_ALBEDO",
        "source_sha256":hashlib.sha256(glb).hexdigest(),
        "ovc_sha256":hashlib.sha256(blob).hexdigest(),
        "meshes_exact":nmesh,"material_ids_exact":nmat,
        "base_color_textures_exact":len(textures),
        "vertices_exact":nvertex,"triangles_exact":ntriangle,
        "bbox_min":[round(float(x),6) for x in lo],
        "bbox_max":[round(float(x),6) for x in hi],
        "texture_resolution_counts":{
            str(dim):sum(x["size"][0]==dim for x in textures)
            for dim in (4,512,1024,2048)},
        "original_game_pmt_modified":False,
        "hmd_runtime":"UNTESTED"
    }

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-hq-zip",type=Path,required=True)
    ap.add_argument("--sidecar",type=Path,required=True)
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()
    report=audit(args.source_hq_zip,args.sidecar)
    if args.report:
        args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

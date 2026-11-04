#!/usr/bin/env python3
"""Convert user-owned v15 R2 geometry to external OVC. Does not read any game PMT."""
import argparse
import hashlib
import json
import math
import pathlib
import struct
import zipfile
import zlib

SOURCE_SHA="3ea734229c9e0745d103e854ce949e5e24289a52987773712601837f591de282"
MAGIC=b"OVRCAB15"
def build(source, output):
    with zipfile.ZipFile(source) as z:
        dcm=z.read("Dino246_Cockpit_LHD_v15.dcm")
        if hashlib.sha256(dcm).hexdigest()!=SOURCE_SHA:raise ValueError("Unknown model hash")
        if dcm[:16]!=b"DINO_V15_LHD_L1\x00" or struct.unpack_from("<III",dcm,16)!=(70,21100,38992):
            raise ValueError("Unknown model header")
        raw=zlib.decompress(dcm[28:])
        if len(raw)>8*1024*1024:raise ValueError("Model exceeds memory budget")
        manifest=json.loads(z.read("DINO_V15_TEXTURE_MANIFEST.json"))
        materials=manifest["textures"]
        if [m["material_index"] for m in materials]!=list(range(19)):
            raise ValueError("Material table not complete")
        p=0;nv=0;nt=0
        for i in range(70):
            if p+12>len(raw):raise ValueError("Short geometry header")
            name,mat,vc,ic=struct.unpack_from("<HHII",raw,p);p+=12
            if not(0<name<=256 and mat<19 and 3<=vc<=8000 and 3<=ic<=40000 and ic%3==0):
                raise ValueError("Invalid geometry group")
            nbytes=name+vc*32+ic*2
            if p+nbytes>len(raw):raise ValueError("Truncated geometry")
            assert raw[p:p+3]==b"LHD"
            vertices=raw[p+name:p+name+vc*32]
            for v in struct.iter_unpack("<8f",vertices):
                if not all(math.isfinite(f) and abs(f)<=10000 for f in v):
                    raise ValueError("Invalid vertex")
            indices=struct.unpack_from("<%dH"%ic,raw,p+name+vc*32)
            if max(indices)>=vc:raise ValueError("Invalid index")
            p+=nbytes;nv+=vc;nt+=ic//3
        if p!=len(raw) or (nv,nt)!=(21100,38992):raise ValueError("Model size mismatch")
        body=bytearray(raw)
        for m in materials:
            filename=m["texture_file"]
            if "/" in filename or "\\" in filename or not filename.endswith(".dds"):
                raise ValueError("Unsafe DDS filename")
            data=z.read(filename)
            if hashlib.sha256(data).hexdigest()!=m["sha256"]:raise ValueError("DDS SHA")
            if len(data)!=11136 or data[:4]!=b"DDS " or data[84:88]!=b"DXT1":
                raise ValueError("Invalid DXT1 DDS")
            if struct.unpack_from("<III",data,12)!=(128,128,8192):
                raise ValueError("Invalid DDS dimensions")
            body+=struct.pack("<I",len(data))+data
        if len(body)>8*1024*1024:raise ValueError("OVC over budget")
        header=struct.pack("<8s7I",MAGIC,1,70,19,nv,nt,len(body),zlib.crc32(body))
        result=header+body
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes(result)
        return {"file":output.name,"sha256":hashlib.sha256(result).hexdigest(),
                "bytes":len(result),"groups":70,"materials":19,"vertices":nv,
                "triangles":nt,"game_assets_modified":False}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-r2-zip",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    a=p.parse_args()
    print(json.dumps(build(a.source_r2_zip,a.output),indent=2))

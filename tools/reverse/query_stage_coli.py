#!/usr/bin/env python3
"""Query an exact OutRun 2006 COLI0200 record from a user-owned Stage.zip."""
from __future__ import annotations
import argparse, json, re, struct, sys, zipfile, zlib

def stage_path(z: zipfile.ZipFile, stage: str) -> str:
    token=stage.upper().strip().strip("/")
    candidates=[
        n for n in z.namelist()
        if re.search(rf"/{re.escape(token)}/coli_CS_{re.escape(token)}_bin\.sz$", n, re.I)
    ]
    if not candidates:
        candidates=[
            n for n in z.namelist()
            if f"/{token.lower()}/" in n.lower() and "/coli_cs_" in n.lower() and n.lower().endswith("_bin.sz")
        ]
    if len(candidates)!=1:
        raise SystemExit(f"stage {stage!r}: expected one COLI0200 file, found {len(candidates)}")
    return candidates[0]

def read_record(data: bytes, index: int) -> dict:
    if data[4:12]!=b"COLI0200":
        raise SystemExit("selected collision file is not COLI0200")
    total=struct.unpack_from("<I",data,0x0c)[0]
    primary=struct.unpack_from("<I",data,0x10)[0]
    if not 0<=index<total:
        raise SystemExit(f"collisionIndex {index} outside 0..{total-1}")
    rel=list(struct.unpack_from("<9I",data,0x14))
    p=[4+x for x in rel]
    mid=data[p[2]+index]
    g=p[3]+index*64
    corners=[list(struct.unpack_from("<3f",data,g+j*12)) for j in range(4)]
    center=list(struct.unpack_from("<3f",data,g+48))
    flags,heading=struct.unpack_from("<Hh",data,g+60)
    n=p[4]+index*48
    normals=[list(struct.unpack_from("<3f",data,n+j*12)) for j in range(4)]
    subtype=data[p[5]+index]&0x0f
    road_section=struct.unpack_from("<H",data,p[6]+index*2)[0]
    light=list(data[p[8]+index*4:p[8]+index*4+4])
    return {
        "collisionIndex":index,
        "primaryRoadRecord":index<primary,
        "materialId":mid,
        "surfaceMask":f"0x{1<<mid:08X}",
        "collisionFlags":f"0x{flags:04X}",
        "localHeadingAngle":heading,
        "roadSection":road_section,
        "subtype":subtype,
        "corners":corners,
        "center":center,
        "normals":normals,
        "cornerLightingBytes":light
    }

def records_for_road_section(data: bytes, road_section: int) -> list[dict]:
    total=struct.unpack_from("<I",data,0x0c)[0]
    rel=list(struct.unpack_from("<9I",data,0x14)); p=[4+x for x in rel]
    return [
        read_record(data,i)
        for i in range(total)
        if struct.unpack_from("<H",data,p[6]+i*2)[0]==road_section
    ]

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("stage_zip")
    ap.add_argument("--stage",required=True,help="folder token, e.g. SNOW, SNOW_R, ALAS")
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--collision-index",type=int)
    group.add_argument("--road-section",type=int)
    ap.add_argument("--compact",action="store_true")
    args=ap.parse_args()
    with zipfile.ZipFile(args.stage_zip) as z:
        path=stage_path(z,args.stage)
        data=zlib.decompress(z.read(path))
    if args.collision_index is not None:
        result={"stage":args.stage.upper(),"path":path,"record":read_record(data,args.collision_index)}
    else:
        records=records_for_road_section(data,args.road_section)
        result={"stage":args.stage.upper(),"path":path,"roadSection":args.road_section,"records":records}
    json.dump(result,sys.stdout,ensure_ascii=False,indent=None if args.compact else 2)
    sys.stdout.write("\n")
    return 0

if __name__=="__main__":
    raise SystemExit(main())

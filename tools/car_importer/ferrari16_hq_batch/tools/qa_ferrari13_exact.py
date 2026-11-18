#!/usr/bin/env python3
"""Read-only, fail-closed Ferrari13 external-body + cockpit overlay audit.
No game file changes. Private asset data is not published to GitHub."""
from __future__ import annotations
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct
import sys
import time
import zlib

BASE = Path(".")
DELTA = Path(".")
RESULT = Path("FERRARI13_STRICT_READONLY_AUDIT.json")
EXACT_IDS = (0, 1, 2, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14)
MAX_FILE = 128 * 1024 * 1024
MAX_GPU = 112 * 1024 * 1024

def ensure(b, reason):
    if not b:
        raise ValueError(reason)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def validate_ovc(data, path):
    ensure(36 <= len(data) <= MAX_FILE, f"{path}: invalid file length")
    sig = bytes(data[:8])
    ensure(sig in (b"OVRCABH3", b"OVRCABH4"), f"{path}: unsupported signature {sig!r}")
    v, ng, nm, nv, nt, np, crc = struct.unpack_from("<7I", data, 8)
    ensure(v == (3 if sig.endswith(b"3") else 4), f"{path}: format mismatch")
    ensure(0 < ng <= 512 and 0 < nm <= 128 and 0 < nv <= 1000000 and 0 < nt <= 2000000, f"{path}: count limit")
    ensure(np == len(data)-36 and zlib.crc32(data[36:]) & 0xffffffff == crc, f"{path}: CRC")
    off, found_vertices, found_triangles, gpu = 36, 0, 0, 0
    material_used, glass = set(), 0
    def dds_at(start, n):
        ensure(n >= 128 and start+n <= len(data), f"{path}: DDS size")
        d = memoryview(data)[start:start+n]
        ensure(d[:4].tobytes() == b"DDS " and struct.unpack_from("<I", d, 4)[0] == 124, f"{path}: DDS magic")
        h,w,mips = struct.unpack_from("<I",d,12)[0],struct.unpack_from("<I",d,16)[0],struct.unpack_from("<I",d,28)[0]
        ensure(0 < w <= 2048 and 0 < h <= 2048 and 1<=mips<=12, f"{path}: DDS dimensions")
        code = d[84:88].tobytes()
        ensure(code in (b"DXT1",b"DXT5",b"\0\0\0\0"), f"{path}: DDS pixel format {code!r}")
        return (w,h,code.decode("ascii",errors="replace"))
    for _ in range(ng):
        ensure(off+16 <= len(data), f"{path}: group header")
        name_len,mat,vertices,indices,idx_width = struct.unpack_from("<HHIII",data,off)
        off += 16
        ensure(0<name_len<=256 and mat<nm and 0<vertices<=1000000 and indices>0 and indices%3==0 and idx_width in (2,4), f"{path}: group counts")
        length=name_len+vertices*32+indices*idx_width
        ensure(off+length <= len(data), f"{path}: group range")
        name=bytes(data[off:off+name_len]).decode("ascii")
        ensure(name.startswith(("EXT_OPAQUE_","EXT_GLASS_")) or (path.endswith("F50_External_Test.ovc") and name.startswith(("F50_HQ_","F50_GLASS_"))), f"{path}: group identifier {name}")
        if name.startswith(("EXT_GLASS_","F50_GLASS_")):glass+=indices//3
        material_used.add(mat)
        off+=length
        found_vertices+=vertices
        found_triangles+=indices//3
        gpu+=vertices*32+indices*idx_width
    ensure((found_vertices,found_triangles)==(nv,nt), f"{path}: group totals differ from header")
    textures = []
    for _ in range(nm):
        ensure(off+4 <= len(data), f"{path}: base DDS size header")
        n=struct.unpack_from("<I",data,off)[0];off+=4
        textures.append(dds_at(off,n))
        off+=n;gpu+=n
    ensure(data[off:off+8]==b"OVCPBR3!", f"{path}: PBR marker")
    off+=8
    normal_count,orm_count=0,0
    for _ in range(nm):
        ensure(off+12<=len(data),f"{path}: PBR factors")
        rough,metal,scale=struct.unpack_from("<fff",data,off);off+=12
        ensure(0.039<=rough<=1.00001 and 0<=metal<=1.00001 and 0<=scale<=2.00001,f"{path}: invalid PBR factors")
        for i in range(2):
            ensure(off+4<=len(data),f"{path}: PBR DDS header")
            n=struct.unpack_from("<I",data,off)[0];off+=4
            if n:
                dds_at(off,n)
                if i==0:normal_count+=1
                else:orm_count+=1
            off+=n;gpu+=n
    bindings={1:0,2:0,3:0}
    if v==4:
        ensure(data[off:off+8]==b"OVCDASH4", f"{path}: dashboard marker")
        off+=8
        n=struct.unpack_from("<I",data,off)[0];off+=4
        ensure(n<=ng,f"{path}: dashboard count")
        seen=set()
        for _ in range(n):
            ensure(off+56<=len(data),f"{path}: dashboard record")
            mesh,kind,gear,reserved,*vals=struct.unpack_from("<4I10f",data,off);off+=56
            ensure(mesh<ng and mesh not in seen and kind in bindings and reserved==0 and 0<=gear<=7,f"{path}: dashboard refs")
            seen.add(mesh);bindings[kind]+=1
    ensure(off==len(data), f"{path}: unconsumed/overrun trailer: {off} vs {len(data)}")
    ensure(gpu <= MAX_GPU,f"{path}: GPU budget")
    ensure(glass>=0 and len(material_used)<=nm,f"{path}: unexpected materials")
    return dict(format=sig.decode(),triangles=nt,vertices=nv,groups=ng,materials=nm,
                normal_map_materials=normal_count,orm_materials=orm_count,
                glass_triangles=glass,base_texture_formats=sorted(set(t[2] for t in textures)),
                largest_base_texture=max((t[0]*t[1] for t in textures),default=0),
                dashboard_bindings=dict(speed=bindings[1],rpm=bindings[2],gear=bindings[3]),
                gpu_bytes=gpu,size_bytes=len(data))

def audit_file(path, expected_bytes, expected_sha):
    ensure(path.stat().st_size==expected_bytes, f"{path}: wrong size")
    with path.open("rb") as handle:
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            view=memoryview(mapped)
            try:
                ensure(digest(view)==expected_sha,f"{path}: wrong SHA256")
                result=validate_ovc(view,str(path))
            finally:
                view.release()
    return result

def main():
    global BASE,DELTA,RESULT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base",required=True,type=Path,help="directory containing baseline Ferrari16 package manifest and payload")
    parser.add_argument("--delta",required=True,type=Path,help="directory containing integrated V4 asset delta with DLL and manifest")
    parser.add_argument("--report",required=True,type=Path,help="new JSON QA report path, outside supplied model pack")
    opts=parser.parse_args()
    BASE=opts.base.resolve();DELTA=opts.delta.resolve();RESULT=opts.report.resolve()
    ensure(BASE.is_dir() and DELTA.is_dir(), "base and delta must both exist")
    ensure(BASE!=DELTA and RESULT.parent!=BASE and RESULT.parent!=DELTA,"audit outputs must not overwrite original model packs")
    base=json.loads((BASE/"FERRARI16_EXTERNAL_DASHBOARD_MANIFEST.json").read_text())
    delta=json.loads((DELTA/"manifest.json").read_text())
    ensure(base["Scope"]["ExactExternalCount"]==13, "baseline count mismatch")
    ensure(len(base["BodyFiles"])==16 and len(base["DashboardFiles"])==16,"baseline count")
    mapping={int(f["Id"]):f for f in base["BodyFiles"]}
    overlay={int(f["Id"]):f for f in base["DashboardFiles"]}
    ensure(set(mapping)==set(overlay)==set(range(15))|{28},"non-canonical ID missing")
    exact={int(f["Id"]) for f in mapping.values() if f["SourceKind"]!="external_donor_rework"}
    ensure(exact==set(EXACT_IDS),f"wrong exact set {exact}")
    upgrades={int(f["id"]):f for f in delta["files"] if f["default_install"]}
    ensure(set(upgrades)=={4,10}, f"unexpected/default downgrade {upgrades}")
    dll=DELTA/"dinput8.dll"
    dll_bytes=dll.read_bytes()
    ensure(digest(dll_bytes)==delta["runtime"]["expected_dinput8_sha256"],"integrated DLL checksum")
    rows=[]
    for car in EXACT_IDS:
        b=mapping[car]
        selected=upgrades.get(car)
        if selected:
            rel=selected["path"];path=DELTA/rel;expect_sha=selected["sha256"];expect_bytes=selected["bytes"]
        else:
            rel=b["PayloadPath"];path=BASE/"QUEST_APK_COPYRUN_PAYLOAD"/rel
            expect_sha=b["Sha256"];expect_bytes=b["Bytes"]
        report=audit_file(path,expect_bytes,expect_sha)
        ensure(report["triangles"]==b["Triangles"] or car in upgrades,f"{car}: triangle contract")
        db=overlay[car]
        dpath=BASE/"QUEST_APK_COPYRUN_PAYLOAD"/db["PayloadPath"]
        overlay_report=audit_file(dpath,db["Bytes"],db["Sha256"])
        binds=overlay_report["dashboard_bindings"]
        ensure(binds["speed"]>=1 and binds["rpm"]>=1 and binds["gear"]>=1,f"{car}: missing live overlay control")
        rows.append(dict(id=car,car=b["Car"],source_kind=b["SourceKind"],
              body_source="latest_v4" if selected else "baseline_v3",
              sha256=expect_sha,body=report,
              dashboard_overlay_sha256=db["Sha256"],overlay=overlay_report,
              native_dashboard_has_speed_rpm=bool(report["dashboard_bindings"]["speed"] and report["dashboard_bindings"]["rpm"]),
              quest3_visual_tested=False))
    ids=[i for i in range(30)]
    route=lambda i: i-15 if 15<=i<=27 else 14 if i==29 else i
    mapped=[route(i) for i in ids]
    ensure(all(x in mapping for x in mapped),"retail alias coverage")
    report=dict(schema=2,task_id="FERRARI13-EXACT-PRIVATE-STRICT-AUDIT-20261118",
           status="STATIC_FILES_SHA_CRC_MATERIAL_DDS_DASHBOARD_ALIAS_PASS_NOT_QUEST3_LIVE_TESTED",
           generated_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
           source_base=str(BASE),source_delta=str(DELTA),
           integrated_dll_sha256=digest(dll_bytes),
           exact_count=len(rows),v4_needle_embedded=sum(r["native_dashboard_has_speed_rpm"] for r in rows),
           overlays_valid=len(rows),retail_alias_ids_checked=len(mapped),routed_canonical_ids=mapped,
           rows=rows,
           limitations=["No Windows/game runtime execution","No Quest3 visual, body floor alignment, steering or shader screenshot","External overlay does not prove exact in-cabin needle spatial alignment","Third-party model redistribution unauthorized as public package","Legacy F50 verified with this generic parser, not camera QA"])
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"exact_count":report["exact_count"],
          "native_dashboard_v4_count":report["v4_needle_embedded"],
          "overlays":len(rows),"aliases":len(mapped),
          "rows":[{"id":x["id"],"car":x["car"],"triangles":x["body"]["triangles"],
                   "normal_maps":x["body"]["normal_map_materials"],
                   "gear":x["overlay"]["dashboard_bindings"]["gear"],
                   "body_v4":x["body_source"]} for x in rows],
          "report":str(RESULT)},ensure_ascii=False))
if __name__=="__main__":
    try:main()
    except Exception as e:
        print(json.dumps({"status":"FAIL","error":str(e)},ensure_ascii=False))
        sys.exit(1)
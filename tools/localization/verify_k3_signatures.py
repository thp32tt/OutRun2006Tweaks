#!/usr/bin/env python3
import argparse
import json
import struct
from pathlib import Path

def read_pe(path):
    data=Path(path).read_bytes()
    if data[:2]!=b"MZ":
        raise ValueError("not MZ")
    pe_off=struct.unpack_from("<I",data,0x3C)[0]
    if data[pe_off:pe_off+4]!=b"PE\0\0":
        raise ValueError("not PE")
    coff=pe_off+4
    sections=struct.unpack_from("<H",data,coff+2)[0]
    opt_size=struct.unpack_from("<H",data,coff+16)[0]
    opt=coff+20
    magic=struct.unpack_from("<H",data,opt)[0]
    if magic!=0x10B:
        raise ValueError("expected PE32")
    image_base=struct.unpack_from("<I",data,opt+28)[0]
    sec=opt+opt_size
    table=[]
    for i in range(sections):
        off=sec+i*40
        name=data[off:off+8].split(b"\0",1)[0].decode("ascii","replace")
        vsize,va,rsize,raw=struct.unpack_from("<IIII",data,off+8)
        table.append((name,va,max(vsize,rsize),raw,rsize))
    return data,image_base,table

def rva_to_file(rva,sections):
    for name,va,span,raw,rsize in sections:
        if va<=rva<va+span:
            delta=rva-va
            if delta>=rsize:
                raise ValueError(f"RVA 0x{rva:X} is not backed by raw bytes in {name}")
            return raw+delta
    raise ValueError(f"RVA 0x{rva:X} not mapped")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--signatures",default="localization/font/k3_signatures.json")
    args=ap.parse_args()

    sig=json.loads(Path(args.signatures).read_text(encoding="utf-8"))
    data,image_base,sections=read_pe(args.exe)
    expected_base=int(sig["image_base_expected"],16)
    errors=[]
    if image_base!=expected_base:
        errors.append(f"image base 0x{image_base:08X} != 0x{expected_base:08X}")

    for fn in sig["functions"]:
        rva=int(fn["rva"],16)
        expected=bytes.fromhex(fn["bytes"])
        off=rva_to_file(rva,sections)
        actual=data[off:off+len(expected)]
        ok=actual==expected
        print(f"{fn['name']}: RVA=0x{rva:08X} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            errors.append(
                f"{fn['name']}: expected {expected.hex(' ')} got {actual.hex(' ')}"
            )

    if errors:
        print("K3_SIGNATURES_FAIL")
        for e in errors:
            print("-",e)
        raise SystemExit(1)
    print("K3_SIGNATURES_OK")

if __name__=="__main__":
    main()

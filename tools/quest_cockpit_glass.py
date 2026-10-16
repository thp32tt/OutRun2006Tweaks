#!/usr/bin/env python3
"""Non-destructive glass alpha modifier for user-owned OutRun 2006 PMT files.

Targets only player-car PMT materials whose original dark-gray color,
semi-transparent alpha and blend factors match the PC-origin Quest evidence.
Writes a new model copy; never changes the source or any D3D global state.
"""
import argparse
import math
from pathlib import Path
import re
import struct
import sys
import zlib

def read32(b, p):
    if p < 0 or p + 4 > len(b):
        raise ValueError("PMT offset outside file")
    return struct.unpack_from("<I", b, p)[0]

def unpack(data):
    if not data or len(data) > 32*1024*1024:
        raise ValueError("invalid compressed model size")
    if data[0] == 0x78:
        z=zlib.decompressobj()
        raw=z.decompress(data,64*1024*1024+1)
        if not z.eof or z.unused_data or len(raw)>64*1024*1024:
            raise ValueError("corrupt or oversize PMT")
        return raw,True
    return data,False

def find_glass(raw):
    if len(raw)<100:
        raise ValueError("short PMT")
    objs=read32(raw,0)
    if objs<1 or objs>80 or read32(raw,20)!=objs:
        raise ValueError("PMT/XMT object count mismatch")
    hits=[]
    for obj in range(objs):
        base=40+obj*60
        if base+60>len(raw):
            raise ValueError("short object table")
        header=16+read32(raw,base+24)
        materials=16+read32(raw,base+52)
        colors=16+read32(raw,base+56)
        if header+52>len(raw):
            raise ValueError("short object header")
        nm,nc=read32(raw,header+44),read32(raw,header+48)
        if not (0<nm<1024 and 0<nc<1024):
            raise ValueError("invalid material count")
        if materials+nm*88>len(raw) or colors+nc*72>len(raw):
            raise ValueError("truncated material/color table")
        refs=[read32(raw,materials+88*i) for i in range(nm)]
        for mid in range(nm):
            ci=refs[mid]
            if ci>=nc or refs.count(ci)!=1:
                continue
            attr=read32(raw,materials+88*mid+4)
            src,dst=(attr>>8)&15,(attr>>12)&15
            if (src,dst) not in ((1,5),(4,5)):
                continue
            off=colors+ci*72
            rgb=struct.unpack_from("<4f",raw,off)
            if not all(math.isfinite(x) for x in rgb):
                continue
            # Restrict to the strong repeated dark-tint signature from the
            # port's 31 player-car PMTs; skip black panels, 0.8 lamps/chrome.
            if (0.10<=rgb[0]<=0.42 and
                max(rgb[:3])-min(rgb[:3])<0.005 and
                0.39<=rgb[3]<=0.59):
                hits.append((obj,mid,ci,off+12,tuple(rgb),(src,dst)))
    return hits

def patch_bytes(payload, name, opacity, selection=None):
    if not re.fullmatch(r"obj_plcar_[a-z0-9_]+_pmt\.sz",name.lower()):
        raise ValueError("not a player-car PMT filename")
    if not math.isfinite(opacity) or not 0.10<=opacity<=0.90:
        raise ValueError("opacity must be 0.10 through 0.90")
    raw,packed=unpack(payload)
    hits=find_glass(raw)
    if selection is not None:
        hits=[h for h in hits if (h[0],h[1]) in selection]
    if not hits:
        raise ValueError("no verifiable glass signature; refusing edit")
    offsets=[h[3] for h in hits]
    if len(set(offsets))!=len(offsets):
        raise ValueError("duplicate glass color offset")
    modified=bytearray(raw)
    for off in offsets:
        struct.pack_into("<f",modified,off,opacity)
    unchanged=bytearray(modified)
    for off in offsets:
        unchanged[off:off+4]=raw[off:off+4]
    if unchanged!=raw:
        raise ValueError("non-glass data changed")
    return (zlib.compress(modified,9) if packed else bytes(modified)),hits

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("source",type=Path)
    a.add_argument("output",type=Path)
    a.add_argument("--opacity",type=float,default=0.30)
    a.add_argument("--only",action="append",default=[],help="object:material; repeat for verified glass")
    a.add_argument("--dry-run",action="store_true")
    opts=a.parse_args()
    if opts.source.resolve()==opts.output.resolve() or opts.output.exists():
        raise ValueError("will not overwrite original/existing output")
    select=None
    if opts.only:
        select=set()
        for s in opts.only:
            x=s.split(":")
            if len(x)!=2 or not all(v.isdigit() for v in x):
                raise ValueError("invalid --only object:material")
            select.add(tuple(map(int,x)))
    payload,hits=patch_bytes(opts.source.read_bytes(),opts.source.name,opts.opacity,select)
    for obj,mat,ci,_,rgba,blend in hits:
        print(f"glass candidate: object={obj} material={mat} color={ci} alpha={rgba[3]:.4f} blend={blend} -> {opts.opacity:.3f}")
    if not opts.dry_run:
        opts.output.parent.mkdir(parents=True,exist_ok=True)
        with opts.output.open("xb") as f:
            f.write(payload)
        print(f"created modified copy: {opts.output}")
    else:
        print("dry-run validation only; original unchanged")

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,zlib.error) as e:
        print("GLASS_PATCH_REFUSED:",e,file=sys.stderr)
        sys.exit(2)

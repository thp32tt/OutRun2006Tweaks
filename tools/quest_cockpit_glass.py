#!/usr/bin/env python3
"""Non-destructive glass alpha modifier for user-owned OutRun 2006 PMT files.

Targets only player-car PMT materials whose original dark-gray color,
semi-transparent alpha and blend factors match the PC-origin Quest evidence.
Writes a new model copy; never changes the source or any D3D global state.
"""
import argparse
import hashlib
import json
import os
import tempfile
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
        # Original PMTs can have material-free transform/LOD helpers.
        if nm == 0 and nc == 0:
            continue
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

def sha256(data):
    return hashlib.sha256(data).hexdigest()


def sidecars(source):
    # Sidecars intentionally live alongside the actual user-selected model,
    # never under game texture override directories or in the mod repository.
    return (source.with_name(source.name + ".outrun-glass-original.bak"),
            source.with_name(source.name + ".outrun-glass.json"))


def write_atomic(target, data):
    fd, tmp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def verified_original(source):
    if source.is_symlink() or not source.is_file():
        raise ValueError("source must be an existing regular non-symlink file")
    if not re.fullmatch(r"obj_plcar_[a-z0-9_]+_pmt\.sz", source.name.lower()):
        raise ValueError("refusing non-player-car model")
    backup, journal = sidecars(source)
    if backup.is_symlink() or journal.is_symlink():
        raise ValueError("unsafe backup/journal symlink")
    current = source.read_bytes()
    if backup.exists() != journal.exists():
        raise ValueError("incomplete earlier operation; preserve backup and inspect manually")
    if not backup.exists():
        # Never install if the source is not a known, safely patchable model.
        find_glass(unpack(current)[0])
        return current, current, backup, journal, None
    original = backup.read_bytes()
    try:
        record = json.loads(journal.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("unreadable glass journal") from exc
    if (record.get("model") != source.name or
        record.get("original_sha256") != sha256(original) or
        record.get("installed_sha256") != sha256(current)):
        raise ValueError("model, original backup or installed model changed; refusing overwrite")
    # A manual replacement is never treated as an existing patch, even if its
    # material colors appear identical. Always regenerate from pristine data.
    find_glass(unpack(original)[0])
    return original, current, backup, journal, record


def install_in_place(source, opacity, selection=None):
    original, current, backup, journal, record = verified_original(source)
    modified, hits = patch_bytes(original, source.name, opacity, selection)
    if record is None:
        # Only now that the source has passed every signature gate, preserve
        # its ORIGINAL bytes. Exclusive create refuses clobbering user backups.
        with backup.open("xb") as f:
            f.write(original)
            f.flush()
            os.fsync(f.fileno())
    record = {
        "schema": 1, "model": source.name, "original_sha256": sha256(original),
        "installed_sha256": sha256(modified), "opacity": opacity,
        "matched_materials": [(a,b) for a,b,*_ in hits],
    }
    if modified != current:
        write_atomic(source, modified)
    write_atomic(journal, json.dumps(record, indent=2, sort_keys=True).encode("utf-8"))
    return hits, backup


def restore_in_place(source):
    original, current, backup, journal, record = verified_original(source)
    if record is None:
        raise ValueError("no verified original backup/journal available")
    if original != current:
        write_atomic(source, original)
    record["installed_sha256"] = sha256(original)
    record["opacity"] = None
    write_atomic(journal, json.dumps(record, indent=2, sort_keys=True).encode("utf-8"))
    return backup


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("source",type=Path)
    a.add_argument("output",type=Path,nargs="?")
    mode=a.add_mutually_exclusive_group()
    mode.add_argument("--in-place",action="store_true",help="apply with original-byte backup and SHA journal")
    mode.add_argument("--restore",action="store_true",help="restore verified backup of in-place glass edit")
    a.add_argument("--opacity",type=float,default=0.30)
    a.add_argument("--only",action="append",default=[],help="object:material; repeat for verified glass")
    a.add_argument("--dry-run",action="store_true")
    opts=a.parse_args()
    if opts.in_place or opts.restore:
        if opts.output is not None:
            raise ValueError("in-place/restore must not specify an output file")
    else:
        if opts.output is None or opts.source.resolve()==opts.output.resolve() or opts.output.exists():
            raise ValueError("specify a new output file; never overwrite existing model")
    select=None
    if opts.only:
        select=set()
        for s in opts.only:
            x=s.split(":")
            if len(x)!=2 or not all(v.isdigit() for v in x):
                raise ValueError("invalid --only object:material")
            select.add(tuple(map(int,x)))
    if opts.restore:
        if opts.dry_run:
            verified_original(opts.source)
            print("restore preview only; no files changed")
        else:
            backup=restore_in_place(opts.source)
            print(f"restored original model; backup preserved: {backup}")
        return
    if opts.in_place:
        if opts.dry_run:
            original,_,_,_,_=verified_original(opts.source)
            _,hits=patch_bytes(original,opts.source.name,opts.opacity,select)
            print(f"validated {len(hits)} candidate materials; no files changed")
        else:
            hits,backup=install_in_place(opts.source,opts.opacity,select)
            print(f"installed glass alpha for {len(hits)} candidate materials; original backup: {backup}")
        return
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

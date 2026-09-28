#!/usr/bin/env python3
"""Fail-closed clean-generation orchestrator for OutRun Korean graphics.

This tool intentionally does NOT perform heuristic text erasure. It accepts an
explicit clean plate and masks produced/reviewed for the exact HD source, then
enforces provenance, containment and final DDS round-trip checks. Unsupported
compressed DDS encoding is stopped rather than silently converted.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, subprocess, sys
from pathlib import Path
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[2]
HEADER=128

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def img(p): return Image.open(p).convert("RGBA")
def binmask(p,size):
    m=Image.open(p).convert("L")
    if m.size!=size: raise SystemExit(f"FAIL mask size {m.size} != {size}")
    return m.point(lambda x:255 if x else 0)
def diffmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for q in bands[1:]: m=ImageChops.lighter(m,q)
    return m.point(lambda x:255 if x else 0)
def n(m): return sum(1 for x in m.getdata() if x)
def dds_info(p):
    b=Path(p).read_bytes()
    if len(b)<HEADER or b[:4]!=b"DDS ": raise SystemExit("FAIL invalid DDS")
    return {"width":struct.unpack_from("<I",b,16)[0],"height":struct.unpack_from("<I",b,12)[0],
      "mips":struct.unpack_from("<I",b,28)[0] or 1,"fourcc":b[84:88].decode("latin1"),
      "rgb_bits":struct.unpack_from("<I",b,88)[0],"sha256":hashlib.sha256(b).hexdigest(),
      "header_sha256":hashlib.sha256(b[:HEADER]).hexdigest()}
def decode_uncompressed(p):
    b=Path(p).read_bytes(); inf=dds_info(p)
    if inf["fourcc"]!="\x00\x00\x00\x00" or inf["rgb_bits"]!=32:
        raise SystemExit("FAIL compressed DDS needs approved external encoder/decoder round-trip; no silent format conversion")
    w,h=inf["width"],inf["height"]; payload=b[HEADER:HEADER+w*h*4]
    if len(payload)!=w*h*4: raise SystemExit("FAIL unsupported DDS payload/mips")
    out=bytearray(len(payload))
    for i in range(0,len(payload),4):
        B,G,R,A=payload[i:i+4]; out[i:i+4]=bytes((R,G,B,A))
    return Image.frombytes("RGBA",(w,h),bytes(out))
def write_bgra(source_dds, rgba, out):
    b=Path(source_dds).read_bytes(); inf=dds_info(source_dds)
    if inf["fourcc"]!="\x00\x00\x00\x00" or inf["rgb_bits"]!=32:
        raise SystemExit("FAIL writer supports exact-header uncompressed BGRA only")
    if rgba.size!=(inf["width"],inf["height"]): raise SystemExit("FAIL image/source dimensions differ")
    raw=rgba.tobytes(); bgra=bytearray(len(raw))
    for i in range(0,len(raw),4):
        R,G,B,A=raw[i:i+4]; bgra[i:i+4]=bytes((B,G,R,A))
    if len(b)!=HEADER+len(bgra): raise SystemExit("FAIL source has unsupported extra/mip payload")
    Path(out).write_bytes(b[:HEADER]+bgra)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-dds",required=True); ap.add_argument("--source-png",required=True)
    ap.add_argument("--clean-plate",required=True); ap.add_argument("--candidate-png",required=True)
    ap.add_argument("--edit-mask",required=True); ap.add_argument("--protected-mask")
    ap.add_argument("--output-dds",required=True); ap.add_argument("--report",required=True)
    ap.add_argument("--generation-id",required=True); ap.add_argument("--spec-id",required=True)
    a=ap.parse_args()
    source=img(a.source_png); clean=img(a.clean_plate); cand=img(a.candidate_png)
    if not(source.size==clean.size==cand.size): raise SystemExit("FAIL PNG dimensions differ")
    di=dds_info(a.source_dds)
    if source.size!=(di["width"],di["height"]): raise SystemExit("FAIL decoded source PNG != DDS dimensions")
    # Require supplied source PNG to be exact decode of uncompressed DDS.
    decoded=decode_uncompressed(a.source_dds)
    if ImageChops.difference(decoded,source).getbbox(): raise SystemExit("FAIL source PNG is not exact DDS decode")
    allowed=binmask(a.edit_mask,source.size); protected=binmask(a.protected_mask,source.size) if a.protected_mask else None
    cleanchg=diffmask(source,clean); finalchg=diffmask(source,cand)
    outside=n(ImageChops.multiply(finalchg,ImageChops.invert(allowed)))
    prot=n(ImageChops.multiply(finalchg,protected)) if protected else 0
    alpha=diffmask(source.getchannel("A").convert("RGBA"),cand.getchannel("A").convert("RGBA"))
    alphaout=n(ImageChops.multiply(alpha,ImageChops.invert(allowed)))
    if outside or prot or alphaout: raise SystemExit(f"FAIL containment outside={outside} protected={prot} alpha_outside={alphaout}")
    write_bgra(a.source_dds,cand,a.output_dds)
    roundtrip=decode_uncompressed(a.output_dds)
    if ImageChops.difference(roundtrip,cand).getbbox(): raise SystemExit("FAIL final DDS round-trip differs from candidate PNG")
    odi=dds_info(a.output_dds)
    if odi["header_sha256"]!=di["header_sha256"]: raise SystemExit("FAIL DDS header changed")
    report={"schema":"outrun-korean-clean-generation-v1","status":"PASS","generation_id":a.generation_id,
      "spec_id":a.spec_id,"source_dds":a.source_dds,"source_sha256":di["sha256"],
      "source_png_sha256":sha(a.source_png),"clean_plate_sha256":sha(a.clean_plate),
      "edit_mask_sha256":sha(a.edit_mask),"protected_mask_sha256":sha(a.protected_mask) if a.protected_mask else None,
      "candidate_png_sha256":sha(a.candidate_png),"candidate_dds_sha256":odi["sha256"],
      "width":di["width"],"height":di["height"],"mip_count":di["mips"],"fourcc":di["fourcc"],
      "clean_plate_changed_pixels":n(cleanchg),"changed_pixels":n(finalchg),
      "changed_pixels_outside_edit_mask":outside,"changed_pixels_in_protected_mask":prot,
      "alpha_changed_outside_edit_mask":alphaout,"dds_header_preserved":True,
      "dds_roundtrip_pixel_exact":True,"runtime_validation":"UNTESTED"}
    Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()

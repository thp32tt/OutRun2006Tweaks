#!/usr/bin/env python3
"""Non-destructive Daytona 365 GTS/4 original PMT BC1 texture repaint.

Unlike a GLB preview this creates a Cars/*.sz that the original game can use.
No original files are modified. Changes: only six existing DDS mip payloads,
with exactly the original XPR offsets, sizes, UVs, vertices and triangle lists.
The target of the upgrade is the Daytona native asset, never Dino.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import math
import struct
import zlib
from PIL import Image,ImageFilter,ImageEnhance,ImageChops
try:
    from pmt_export_base import open_pmt, decode_object, decode_dds
except ImportError:
    from dino_original_pmt_to_glb import open_pmt, decode_object, decode_dds

SOURCE=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
SHA="f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe"
TARGETS=(8,14,15,16,18,19)

def unpack565(c):
    return ((c>>11&31)*255//31,(c>>5&63)*255//63,(c&31)*255//31)
def pack565(c):
    return ((c[0]*31//255)<<11)|((c[1]*63//255)<<5)|(c[2]*31//255)
def bc1_block(block):
    rgb=[p[:3] for p in block]
    trans=any(p[3]<128 for p in block)
    opaque=[p for p in block if p[3]>=128]
    if not opaque:
        return struct.pack("<HHI",0,0,0xffffffff)
    # Use major-axis extrema for better saturation than luminance-only RGB5:6:5.
    avg=[sum(p[i] for p in opaque)/len(opaque) for i in range(3)]
    vari=[sum((p[i]-avg[i])**2 for p in opaque) for i in range(3)]
    ch=max(range(3),key=lambda i:vari[i])
    ordered=sorted(opaque,key=lambda c:c[ch])
    c0=pack565(ordered[-1]);c1=pack565(ordered[0])
    if trans:
        if c0>c1:c0,c1=c1,c0
        p0=unpack565(c0);p1=unpack565(c1)
        palette=[p0,p1,tuple((p0[i]+p1[i])//2 for i in range(3))]
    else:
        if c0==c1:
            if c0==0:c0=1
            else:c1=c0-1
        if c0<c1:c0,c1=c1,c0
        p0=unpack565(c0);p1=unpack565(c1)
        palette=[p0,p1,
          tuple((2*p0[i]+p1[i])//3 for i in range(3)),
          tuple((p0[i]+2*p1[i])//3 for i in range(3))]
    ix=0
    for i,p in enumerate(block):
        if trans and p[3]<128:choice=3
        else:choice=min(range(len(palette)),key=lambda k:sum((p[j]-palette[k][j])**2 for j in range(3)))
        ix|=choice<<(i*2)
    return struct.pack("<HHI",c0,c1,ix)

def encode_level(img):
    img=img.convert("RGBA")
    w,h=img.size
    dat=img.load()
    chunks=[]
    for y in range(0,h,4):
        for x in range(0,w,4):
            block=[dat[min(w-1,x+dx),min(h-1,y+dy)]
                   for dy in range(4) for dx in range(4)]
            chunks.append(bc1_block(block))
    return b"".join(chunks)

def make_repaint(original,index):
    # Strictly paint into original UV island layout; no imagined scene artwork.
    w,h=original.size
    im=original.convert("RGBA")
    alpha=im.getchannel("A")
    # Work at 4x for smooth metal trim edgework, then bake to the native DDS size.
    hr=im.resize((w*4,h*4),Image.Resampling.LANCZOS)
    if index in (8,15,16,18):
        rgb=ImageEnhance.Contrast(hr.convert("RGB")).enhance(1.23 if index==8 else 1.16)
        rgb=rgb.filter(ImageFilter.UnsharpMask(radius=1.0,percent=126,threshold=2))
        # Preserve color and layout. Lift source bright trim, suppress muddy midtones.
        orig=hr.convert("RGB")
        edge=orig.filter(ImageFilter.FIND_EDGES)
        edge=ImageEnhance.Contrast(edge).enhance(1.3)
        rgb=Image.blend(rgb,ImageChops.screen(rgb,edge),.085)
    else:
        # Leather/vinyl only: subtle source-aligned micrograin, no copied photos.
        rgb=hr.convert("RGB")
        rgb=ImageEnhance.Contrast(rgb).enhance(1.13)
        # generated geometry-aware wrinkle pattern with low amplitude
        noise=Image.new("RGB",rgb.size)
        q=noise.load()
        for y in range(rgb.height):
            for x in range(rgb.width):
                v=int(2.2*math.sin(x*.81+math.sin(y*.31))*math.sin(y*.69))
                q[x,y]=(127+v,127+v,127+v)
        rgb=Image.blend(rgb,ImageChops.screen(rgb,noise),.025)
    rgb=rgb.resize((w,h),Image.Resampling.LANCZOS)
    out=Image.merge("RGBA",(*rgb.split(),alpha))
    return out

def replace_dds(original_bytes,img):
    # KEEP header, pixel format, original mip count, total DDS span/offset.
    h=struct.unpack_from("<I",original_bytes,12)[0]
    w=struct.unpack_from("<I",original_bytes,16)[0]
    mip=struct.unpack_from("<I",original_bytes,28)[0]
    if original_bytes[:4]!=b"DDS " or original_bytes[84:88]!=b"DXT1" or img.size!=(w,h):
        raise ValueError("not an expected DXT1 DDS")
    b=bytearray(original_bytes)
    pos=128
    for level in range(mip):
        mw=max(1,w>>level);mh=max(1,h>>level)
        l=img.resize((mw,mh),Image.Resampling.LANCZOS)
        data=encode_level(l)
        expected=max(1,(mw+3)//4)*max(1,(mh+3)//4)*8
        assert len(data)==expected
        if pos+expected>len(b):raise ValueError("DDS mip beyond original")
        b[pos:pos+expected]=data
        pos+=expected
    return bytes(b)

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--source",type=Path,default=SOURCE)
    pa.add_argument("--output",type=Path,default=Path(__file__).resolve().parent/"runtime_v2")
    ar=pa.parse_args()
    raw=ar.source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SHA:raise SystemExit("Fail closed: source mismatch")
    ar.output.mkdir(parents=True,exist_ok=True)
    original=open_pmt(ar.source)
    packed=zlib.decompress(raw)
    oc,tc,syslen,vidlen=struct.unpack_from("<4I",packed,0)
    video=bytearray(original["video"])
    changes=[]
    for idx in TARGETS:
        off=original["offsets"][idx]
        end=min((n for n in original["offsets"] if n>off),default=original["data_size"])
        old=bytes(video[off:end])
        png,_,_=decode_dds(original,idx,1)
        image=Image.open(io.BytesIO(png)).convert("RGBA")
        after=make_repaint(image,idx)
        new=replace_dds(old,after)
        if len(old)!=len(new):raise ValueError("must preserve byte span")
        video[off:end]=new
        after.save(ar.output/f"Daytona365_NATIVE_tex{idx:02d}_repaint.png")
        changes.append({"texture":idx,"w":image.width,"h":image.height,
            "dds_span":len(old),"modified_bytes":sum(a!=b for a,b in zip(old,new))})
    new_uncompressed=packed[:16+syslen]+bytes(video)
    assert len(new_uncompressed)==len(packed)==16+syslen+vidlen
    destination=ar.output/"obj_plcar_dayts_pmt.sz"
    destination.write_bytes(zlib.compress(new_uncompressed,9))
    check=open_pmt(destination)
    assert check["obj_count"]==oc==original["obj_count"]
    assert check["tex_count"]==tc==original["tex_count"]
    assert check["system"]==original["system"]
    assert check["offsets"]==original["offsets"]
    for i in range(oc):
        # Game geometry/topology/UVs must not change one bit.
        assert decode_object(original,i)==decode_object(check,i),(i,"geometry changed")
    for i in range(tc):
        if i in TARGETS:continue
        start=original["offsets"][i]
        stop=min((n for n in original["offsets"] if n>start),default=original["data_size"])
        assert original["video"][start:stop]==check["video"][start:stop],("other texture changed",i)
    report={"status":"PASS_STATIC_PMT_COMPATIBLE","native_asset":destination.name,
      "path":str(destination),"sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
      "source_sha256":SHA,"objects":oc,"textures":tc,"changed_textures":changes,
      "same_system_header":True,"same_xpr_offsets":True,
      "same_object_geometry_uv":True,"other_dds_unchanged":True,
      "tested_in_actual_game":False,"dino_touched":False,
      "warning":"PRIVATE ORIGINAL GAME ASSET REPLACEMENT. BACKUP FIRST, do not redistribute."}
    (ar.output/"DAYTONA_NATIVE_PMT_REPAINT_REPORT.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()

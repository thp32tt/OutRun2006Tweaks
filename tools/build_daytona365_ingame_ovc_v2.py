#!/usr/bin/env python3
"""Build an actual OutRun VR D3D9Ex OVRCABH2 enhancement sidecar for Daytona 365 GTS/4.

Adds geometry to the verified original instrument-panel envelope rather than
inventing a full replacement cockpit. The game's original car still renders.
All input is read-only; this script NEVER modifies original PMT or Dino assets.

This is a runtime-compatible FORMAT candidate; live VR alignment is not proven.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import random
import struct
import zlib
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw
from pmt_export_base import open_pmt, decode_object

EXPECTED_SHA="f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe"
NAME="Daytona365_Cockpit_R26_v2.ovc"
SOURCE=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
OUT=Path(__file__).resolve().parent/"runtime_v2"
MAX_IMAGE=1024

def _texture_rgba(kind,size=256):
    img=Image.new("RGBA",(size,size))
    pix=img.load()
    noise=random.Random(0x36504)
    for y in range(size):
        for x in range(size):
            if kind=="chrome":
                # Explicit stylized metal reflection bands, valid fixed-function albedo.
                t=abs(math.sin((x/size)*math.pi*3))
                b=int(95+115*t)
                strip=int(23*math.sin((y/size)*40*math.pi))
                v=max(20,min(247,b+strip))
                pix[x,y]=(v,max(0,v-4),max(0,v-10),255)
            elif kind=="stitch":
                n=noise.randint(-9,9)
                b=max(0,min(255,150+n))
                pix[x,y]=(b,max(0,b-24),max(0,b-42),255)
            else:
                n=noise.randint(-13,13)
                val=max(0,min(255,42+n))
                pix[x,y]=(val,val-1 if val else 0,val+1,255)
    return img

def _dds_argb32(img):
    img=img.convert("RGBA")
    w,h=img.size
    if w<=0 or h<=0 or w>2048 or h>2048 or w&(w-1) or h&(h-1):
        raise ValueError("Invalid DDS dimensions")
    header=bytearray(128)
    header[:4]=b"DDS "
    struct.pack_into("<I",header,4,124)
    struct.pack_into("<I",header,8,0x0002100F)
    struct.pack_into("<I",header,12,h)
    struct.pack_into("<I",header,16,w)
    struct.pack_into("<I",header,20,w*4)
    struct.pack_into("<I",header,28,1)
    struct.pack_into("<I",header,76,32)
    struct.pack_into("<I",header,80,0x41)
    struct.pack_into("<I",header,84,0)
    struct.pack_into("<I",header,88,32)
    struct.pack_into("<4I",header,92,0x00ff0000,0x0000ff00,0x000000ff,0xff000000)
    struct.pack_into("<I",header,108,0x1000)
    return bytes(header)+img.tobytes("raw","BGRA")

def _empty(name, material):
    return {"name":name,"material":material,"v":[],"i":[]}

def _v(m,p,n,uv):
    if not all(math.isfinite(q) for q in (*p,*n,*uv)):
        raise ValueError("nonfinite")
    m["v"].append((*p,*n,*uv))
    return len(m["v"])-1

def _tri(m,a,b,c):
    if len({a,b,c})!=3:raise ValueError("degenerate index")
    m["i"].extend((a,b,c))

def add_panel_bezel(m, x,y,z,rx,ry,segments=64):
    """Raised curved chrome outline. The source DDS gauge plane is at z=-.166608."""
    if segments<12:raise ValueError("segments")
    # Circumferential three ridge loops. All vertices at/more positive z
    # than source gauge plane, so this ADDS geometry instead of co-planar Z fighting.
    cross_section=((1.012,z-0.001),(1.000,z+0.0025),(0.986,z+0.0031),
                   (0.977,z+0.0003))
    loops=[]
    for ri,(radius,dep) in enumerate(cross_section):
        ids=[]
        for i in range(segments+1):
            a=2*math.pi*i/segments
            px=x+rx*radius*math.cos(a)
            py=y+ry*radius*math.sin(a)
            normal=(math.cos(a)*.38,math.sin(a)*.38,.926)
            ids.append(_v(m,(px,py,dep),normal,(i/segments,ri/(len(cross_section)-1))))
        loops.append(ids)
    for left,right in zip(loops,loops[1:]):
        for i in range(segments):
            _tri(m,left[i],right[i],right[i+1])
            _tri(m,left[i],right[i+1],left[i+1])

def add_dash_stitch(m,start,end,n=48):
    """Actual raised short diagonal stitches in passenger dash area."""
    x0,y0,z0=start;x1,y1,z1=end
    if n<1:return
    for i in range(n):
        t=(i+.5)/n
        x=x0+(x1-x0)*t
        y=y0+(y1-y0)*t
        z=z0+(z1-z0)*t
        # Stitch material used for raised small quads (not a 2D decal).
        w=.0030;h=.00155
        a=_v(m,(x-w,y-h,z), (0,0,1),(0,0))
        b=_v(m,(x+w,y+h,z), (0,0,1),(1,1))
        c=_v(m,(x+w*.5,y+h*1.8,z), (0,0,1),(1,0))
        d=_v(m,(x-w*.5,y-h*1.8,z), (0,0,1),(0,1))
        _tri(m,a,b,c);_tri(m,a,c,d)

def add_chrome_switch(m,x,y,z,w=.006,h=.012):
    """Small physical switch outline for original center face, no new virtual console."""
    add_panel_bezel(m,x,y,z,w,h,segments=16)

def build_geometry(asset):
    parts=decode_object(asset,0)
    by_tex={p["tex_index"]:p for p in parts}
    # The source gauge cluster (tex 08) is a planar original game face.
    p=by_tex[8];vz=[v[2] for v in p["vertices"]]
    if not (len(vz)>=4 and max(vz)-min(vz)<.0001):
        raise ValueError("fail closed: source cluster geometry changed")
    xall=[v[0] for v in p["vertices"]];yall=[v[1] for v in p["vertices"]]
    xlo,xhi=min(xall),max(xall);ylo,yhi=min(yall),max(yall);z=vz[0]
    if not (-.67<xlo<-.55 and -.15<xhi<-.04 and .70<ylo<.78 and .88<yhi<.94 and -.19<z<-.13):
        raise ValueError("fail closed: unknown Daytona instrument position")
    cx=(xlo+xhi)*.5;cy=(ylo+yhi)*.5
    bez=_empty("DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY",0)
    add_panel_bezel(bez,cx,cy,z+.010,(xhi-xlo)*.494,(yhi-ylo)*.497,segments=96)
    # Two main gauge apertures: physically beveled chrome loops placed just
    # inside the verified original texture plane, not a generated fake dashboard.
    for x in (cx-.165,cx+.165):
        add_panel_bezel(bez,x,cy,z+.012,.066,.065,segments=64)
    stitches=_empty("DAYTONA_DASH_RAISED_STITCHING_ACTUAL_GEOMETRY",1)
    # Source panel's real top extends y=.909; stay on its x envelope.
    add_dash_stitch(stitches,(xlo+.015,yhi+.002,z+.018),
                    (xhi-.015,yhi+.002,z+.018),n=42)
    # Center console from original material 15 is centered x~0 and runs y .586..847.
    ctr=by_tex[15];q=[v for v in ctr["vertices"] if v[2]<-.167]
    if len(q)<3:raise ValueError("source center not found")
    switch=_empty("DAYTONA_CONSOLE_SWITCH_METAL_BEZELS_ACTUAL_GEOMETRY",0)
    for x in (-.053,-.018,.018,.053):
        add_chrome_switch(switch,x,.773,-.155,w=.006,h=.013)
    meshes=[bez,stitches,switch]
    for m in meshes:
        if not m["v"] or not m["i"] or max(m["i"])>=len(m["v"]):
            raise ValueError("generated empty or corrupt mesh")
    return meshes,{"cluster_bounds":[xlo,xhi,ylo,yhi,z],
                   "source_texture_index":8,
                   "original_untouched":True,
                   "new_mesh_groups":len(meshes)}

def write_ovc(meshes,images,target):
    materials=[_dds_argb32(im) for im in images]
    payload=bytearray()
    vertex_total=0;tri_total=0
    report=[]
    for m in meshes:
        bname=m["name"].encode("ascii")
        if not (0<len(bname)<=256 and len(m["v"])>=3 and len(m["i"])%3==0
                and len(m["v"])<65536):
            raise ValueError("group size")
        if not 0<=m["material"]<len(materials):raise ValueError("material")
        payload.extend(struct.pack("<HHIII",len(bname),m["material"],
            len(m["v"]),len(m["i"]),2))
        payload.extend(bname)
        for vertex in m["v"]:payload.extend(struct.pack("<8f",*vertex))
        payload.extend(struct.pack("<"+"H"*len(m["i"]),*m["i"]))
        vertex_total+=len(m["v"]);tri_total+=len(m["i"])//3
        report.append({"name":m["name"],"material":m["material"],"vertices":len(m["v"]),"triangles":len(m["i"])//3})
    for dds in materials:
        payload.extend(struct.pack("<I",len(dds)))
        payload.extend(dds)
    if len(payload)>112*1024*1024:raise ValueError("GPU limit")
    header=b"OVRCABH2"+struct.pack("<7I",2,len(meshes),len(materials),
        vertex_total,tri_total,len(payload),zlib.crc32(payload)&0xffffffff)
    assert len(header)==36
    target.write_bytes(header+payload)
    return {"file":target.name,"bytes":target.stat().st_size,
        "vertices":vertex_total,"triangles":tri_total,"materials":len(materials),
        "groups":report,"sha256":hashlib.sha256(target.read_bytes()).hexdigest()}

def validate_ovc(path):
    d=path.read_bytes()
    assert len(d)>36 and d[:8]==b"OVRCABH2"
    ver,groups,mats,nv,nt,payload_size,crc=struct.unpack_from("<7I",d,8)
    assert ver==2 and len(d)==payload_size+36 and crc==zlib.crc32(d[36:])&0xffffffff
    at=36;vs=ts=0
    for i in range(groups):
        namelen,mat,nverts,nidx,ixwidth=struct.unpack_from("<HHIII",d,at);at+=16
        assert 0<namelen<=256 and mat<mats and ixwidth==2 and nidx%3==0
        at+=namelen
        verts=struct.unpack_from("<"+"f"*(nverts*8),d,at)
        assert all(math.isfinite(v) and abs(v)<10000 for v in verts)
        at+=nverts*32
        ids=struct.unpack_from("<"+"H"*nidx,d,at)
        assert max(ids)<nverts
        at+=nidx*2
        vs+=nverts;ts+=nidx//3
    for i in range(mats):
        size=struct.unpack_from("<I",d,at)[0];at+=4
        hdr=d[at:at+128]
        assert hdr[:4]==b"DDS " and struct.unpack_from("<I",hdr,4)[0]==124
        assert struct.unpack_from("<I",hdr,76)[0]==32
        w,h=struct.unpack_from("<II",hdr,16)[0],struct.unpack_from("<I",hdr,12)[0]
        assert size==128+w*h*4
        at+=size
    assert at==len(d) and vs==nv and ts==nt
    return True

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--source",type=Path,default=SOURCE)
    pa.add_argument("--output",type=Path,default=OUT)
    args=pa.parse_args()
    if hashlib.sha256(args.source.read_bytes()).hexdigest()!=EXPECTED_SHA:
        raise SystemExit("Source SHA mismatch. No output generated.")
    args.output.mkdir(parents=True,exist_ok=True)
    asset=open_pmt(args.source)
    meshes,metadata=build_geometry(asset)
    textures=[_texture_rgba("chrome"),_texture_rgba("stitch")]
    name=args.output/NAME
    res=write_ovc(meshes,textures,name)
    validate_ovc(name)
    for im,kind in zip(textures,("chrome","stitch")):
        im.save(args.output/(f"Daytona365_{kind}_R26.png"))
    meta={**res,**metadata,"format":"OVRCABH2 v2 (D3D9Ex ARGB32, x86)",
        "runtime":"STATIC_FORMAT_PASS only; Quest 3/PC game not launched",
        "game_scope":"additive dashboard trim only: no duplicate full car",
        "dino":"untouched",
        "source_sha256":EXPECTED_SHA}
    (args.output/"Daytona365_OVC_V2_MANIFEST.json").write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2))
if __name__=="__main__":
    main()

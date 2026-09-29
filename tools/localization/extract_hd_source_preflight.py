#!/usr/bin/env python3
"""Extract exact HD DDS readable-orientation review PNGs and geometry.

Fail-closed scope: uncompressed 32-bit DDS only. The selected display transform
is explicit and signed slant is measured in readable/display coordinates.
"""
from __future__ import annotations
import argparse, hashlib, json, math, struct
from pathlib import Path
from PIL import Image

HEADER=128

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def bbox_alpha(im: Image.Image, threshold: int):
    a=im.getchannel("A")
    m=a.point(lambda v: 255 if (v >= threshold if threshold > 1 else v > 0) else 0)
    b=m.getbbox()
    return list(b) if b else None

def dds_info(p: Path):
    b=p.read_bytes()
    if len(b)<HEADER or b[:4]!=b"DDS ":
        raise SystemExit("invalid DDS")
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0] or 1
    fourcc=b[84:88]
    bits=struct.unpack_from("<I",b,88)[0]
    masks=[struct.unpack_from("<I",b,o)[0] for o in (92,96,100,104)]
    return b,{"width":w,"height":h,"mips":mips,"fourcc":fourcc.hex(),"rgb_bits":bits,
              "masks":{"r":masks[0],"g":masks[1],"b":masks[2],"a":masks[3]}}

def decode_bgra32(p: Path):
    b,info=dds_info(p)
    if info["fourcc"]!="00000000" or info["rgb_bits"]!=32:
        raise SystemExit("only exact uncompressed 32-bit DDS is supported")
    w,h=info["width"],info["height"]
    payload=b[HEADER:HEADER+w*h*4]
    if len(payload)!=w*h*4:
        raise SystemExit("unexpected mip/extra payload; fail closed")
    rgba=bytearray(len(payload))
    for i in range(0,len(payload),4):
        B,G,R,A=payload[i:i+4]
        rgba[i:i+4]=bytes((R,G,B,A))
    return Image.frombytes("RGBA",(w,h),bytes(rgba)),info

def transform(im: Image.Image, name: str):
    if name=="normal": return im.copy()
    if name=="flip_x": return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if name=="flip_y": return im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if name=="rotate_180": return im.transpose(Image.Transpose.ROTATE_180)
    raise SystemExit("invalid display transform")

def transform_rect(rect, canvas, name):
    x,y,w,h=rect; W,H=canvas
    if name=="normal": return [x,y,w,h]
    if name=="flip_x": return [W-(x+w),y,w,h]
    if name=="flip_y": return [x,H-(y+h),w,h]
    if name=="rotate_180": return [W-(x+w),H-(y+h),w,h]
    raise SystemExit("invalid display transform")

def measure_signed_slant(display: Image.Image, crop_rect):
    """Estimate italic shear by maximizing vertical-edge projection sharpness.

    Positive result means the glyph top is displaced right of its bottom in
    readable coordinates, matching the repository signed-slant convention.
    """
    x,y,w,h=crop_rect
    im=display.crop((x,y,x+w,y+h))
    a=im.getchannel("A")
    # Keep substantial glyph/effect pixels while rejecting faint fringe.
    pix=a.load()
    edge_rows=[]
    for yy in range(h):
        xs=[]
        for xx in range(1,w-1):
            if max(pix[xx-1,yy],pix[xx,yy],pix[xx+1,yy]) < 96:
                continue
            gx=abs(int(pix[xx+1,yy])-int(pix[xx-1,yy]))
            if gx >= 72:
                xs.append(xx)
        edge_rows.append(xs)
    best=None
    # x' = x + s*y deskews a right-leaning glyph for positive s.
    for step in range(-70,71):
        s=step/200.0
        cols={}
        count=0
        for yy,xs in enumerate(edge_rows):
            shift=s*yy
            for xx in xs:
                k=round(xx+shift)
                cols[k]=cols.get(k,0)+1
                count+=1
        if count < 32:
            continue
        score=sum(v*v for v in cols.values())/count
        if best is None or score>best[0]:
            best=(score,s,count)
    if best is None:
        raise SystemExit("insufficient vertical-edge evidence for signed slant")
    s=best[1]
    # Guard tiny estimates as visually upright.
    if abs(s)<0.025: s=0.0
    direction="right" if s>0 else "left" if s<0 else "none"
    angle=math.degrees(math.atan(s))
    return {
      "method":"alpha_vertical_edge_projection_v1",
      "slant_dx_per_dy":round(s,4),
      "slant_angle_deg":round(angle,3),
      "slant_direction":direction,
      "edge_samples":best[2],
      "score":round(best[0],6),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-dds",required=True)
    ap.add_argument("--output-dir",required=True)
    ap.add_argument("--asset-id",required=True)
    ap.add_argument("--git-blob-sha",required=True)
    ap.add_argument("--cell",nargs=4,type=int,metavar=("X","Y","W","H"),required=True)
    ap.add_argument("--display-transform",choices=("normal","flip_x","flip_y","rotate_180"),required=True)
    a=ap.parse_args()
    src=Path(a.source_dds)
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    raw,info=decode_bgra32(src)
    variants={
      "raw":raw,
      "flip_x":transform(raw,"flip_x"),
      "flip_y":transform(raw,"flip_y"),
      "rotate_180":transform(raw,"rotate_180"),
    }
    files={}
    for name,im in variants.items():
        p=out/f"preflight_{name}.png"; im.save(p,optimize=True); files[name]=str(p)
    display=transform(raw,a.display_transform)
    source_display=out/"source_display.png"
    display.save(source_display,optimize=True)

    x,y,w,h=a.cell
    if x<0 or y<0 or w<=0 or h<=0 or x+w>raw.width or y+h>raw.height:
        raise SystemExit("cell outside canvas")
    raw_cell=raw.crop((x,y,x+w,y+h))
    display_cell_rect=transform_rect([x,y,w,h],raw.size,a.display_transform)
    dx,dy,dw,dh=display_cell_rect
    display_cell=display.crop((dx,dy,dx+dw,dy+dh))
    cell={
      "raw_rect":[x,y,w,h],
      "display_rect":display_cell_rect,
      "alpha_gt0_bbox_canvas_raw":bbox_alpha(raw,1),
      "alpha_ge128_bbox_canvas_raw":bbox_alpha(raw,128),
      "alpha_gt0_bbox_cell_local_raw":bbox_alpha(raw_cell,1),
      "alpha_ge128_bbox_cell_local_raw":bbox_alpha(raw_cell,128),
      "alpha_gt0_bbox_cell_local_display":bbox_alpha(display_cell,1),
      "alpha_ge128_bbox_cell_local_display":bbox_alpha(display_cell,128),
    }
    slant=measure_signed_slant(display,display_cell_rect)
    report={
      "schema_version":2,
      "asset_id":a.asset_id,
      "source_dds":str(src),
      "source_git_blob_sha":a.git_blob_sha,
      "source_sha256":sha256(src),
      "dds":info,
      "cell":cell,
      "variants":files,
      "source_display":str(source_display),
      "display_transform":a.display_transform,
      "orientation_status":"PASS_EXPLICIT_DISPLAY_TRANSFORM",
      "orientation_decision_basis":"Exact HD source visually readable only under selected transform; raw/other variants retained beside source_display.png.",
      "signed_slant":slant,
      "signed_slant_status":"PASS_MEASURED_IN_READABLE_DISPLAY_COORDINATES",
      "runtime_validation":"UNTESTED"
    }
    (out/"preflight_metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()

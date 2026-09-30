#!/usr/bin/env python3
"""Deterministic source-only geometry audit for name-entry atlas 66743AA8.

This tool intentionally does not generate or modify a candidate DDS. It verifies
the exact canonical source, decodes it, applies the proven readable flip-Y view,
and records alpha-effect glyph geometry plus the alpha-clear lower atlas region.
Runtime selection-index / UV mapping remains a separate prerequisite.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
import numpy as np
from PIL import Image

SOURCE_SHA256 = "7aa21de138af2d7f2aae54022a08f0aca79093a2a34a2bd74a87a442efaa60aa"
EXPECTED_SIZE = (4096, 4096)
EXPECTED_FOURCC = b"DXT5"
LABEL_ROWS = [
    list("ABCDEFGHIJ"),
    list("KLMNOPQRST"),
    ["U","V","W","X","Y","Z","0","1","2","3"],
    ["4","5","6","7","8","9","!","%","&","+"],
    ["-",".","/","=","?","@","¥","*"],
]

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def runs(mask):
    out=[]; start=None
    for i,v in enumerate(mask):
        if bool(v) and start is None:
            start=i
        elif not bool(v) and start is not None:
            out.append((start,i)); start=None
    if start is not None:
        out.append((start,len(mask)))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source_dds")
    ap.add_argument("--out")
    args=ap.parse_args()
    p=Path(args.source_dds)
    digest=sha256(p)
    if digest != SOURCE_SHA256:
        raise SystemExit(f"FAIL source sha256 {digest} != {SOURCE_SHA256}")
    b=p.read_bytes()
    if b[:4] != b"DDS ":
        raise SystemExit("FAIL DDS magic")
    height,width,pitch,mips=struct.unpack_from("<IIII",b,12)
    mips=mips or 1
    fourcc=b[84:88]
    if (width,height) != EXPECTED_SIZE or fourcc != EXPECTED_FOURCC or mips != 1:
        raise SystemExit(f"FAIL DDS structure {(width,height,fourcc,mips)}")
    readable=Image.open(p).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    arr=np.asarray(readable)
    alpha=arr[:,:,3]
    mask=alpha>0
    row_runs=runs(mask.any(axis=1))
    if len(row_runs) != len(LABEL_ROWS):
        raise SystemExit(f"FAIL row count {len(row_runs)}")
    glyphs=[]
    for r,(y0,y1) in enumerate(row_runs):
        xruns=runs(mask[y0:y1,:].any(axis=0))
        if len(xruns) != len(LABEL_ROWS[r]):
            raise SystemExit(f"FAIL row {r} glyph runs {len(xruns)}")
        for c,(x0,x1) in enumerate(xruns):
            sub=mask[y0:y1,x0:x1]
            ys,xs=np.where(sub)
            bb=[int(x0+xs.min()),int(y0+ys.min()),int(x0+xs.max()+1),int(y0+ys.max()+1)]
            glyphs.append({
                "visual_label":LABEL_ROWS[r][c],
                "row":r,"col":c,
                "bbox_readable_half_open":bb,
                "bbox_raw_half_open":[bb[0],height-bb[3],bb[2],height-bb[1]],
                "alpha_nonzero_pixels":int(sub.sum())
            })
    clear_y=max(g["bbox_readable_half_open"][3] for g in glyphs)
    lower=arr[clear_y:,:,:]
    if int((lower[:,:,3]>0).sum()) != 0:
        raise SystemExit("FAIL lower region is not alpha-clear")
    report={
        "schema":"outrun-index24-name-entry-source-geometry-audit-v1",
        "source_sha256":digest,
        "dds":{"width":width,"height":height,"fourcc":fourcc.decode("ascii"),"mipmaps":mips,"pitch_or_linear_size":pitch},
        "raw_orientation":"mirror_y","readable_transform":"flip_y",
        "glyph_count":len(glyphs),
        "row_glyph_counts":[len(x) for x in LABEL_ROWS],
        "row_alpha_bands_readable_half_open":[list(x) for x in row_runs],
        "glyphs":glyphs,
        "alpha_clear_rect_readable_half_open":[0,clear_y,width,height],
        "alpha_clear_nonzero_alpha_pixels":int((lower[:,:,3]>0).sum()),
        "note":"visual_label is source visual classification; runtime selection index/UV mapping is not proven by this audit"
    }
    payload=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        Path(args.out).write_text(payload,encoding="utf-8")
    print(payload,end="")

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Photo-source color and source-UV-preserving PMT paint for actual game.
Re-encodes BC1 in the original byte span and all original geometry/UV exactly.
"""
import argparse,sys,json
from pathlib import Path
from PIL import Image,ImageOps
try:
    import patch_daytona_native_pmt_textures as previous
except ImportError:
    import patch_daytona365_native_pmt_textures as previous
try:
    from build_daytona_photo_mesh_v3 import OUT as OUT_V3
except ImportError:
    from build_daytona365_photo_mesh_v3 import OUT as OUT_V3

original_repaint=previous.make_repaint
def photographic_native(original,index):
    if index not in (16,18):
        return original_repaint(original,index)
    image=Image.open(OUT_V3/"Daytona365_PHOTO_tan_leather_v3.png").convert("RGBA")
    image=image.resize(original.size,Image.Resampling.LANCZOS)
    src=original.convert("RGBA")
    gray=ImageOps.autocontrast(src.convert("L"),cutoff=1)
    gv=list(gray.getdata());new=[]
    pix=list(image.getdata());alpha=list(src.getchannel("A").getdata())
    for col,shade,a in zip(pix,gv,alpha):
        # Preserve source highlights, folds, seams and native transparency.
        brightness=.66+.40*(shade/255.)
        new.append(tuple(int(min(255,c*brightness)) for c in col[:3])+(a,))
    out=Image.new("RGBA",original.size);out.putdata(new)
    return out
previous.make_repaint=photographic_native
def main():
    sys.argv=[sys.argv[0],"--output",str(OUT_V3)]
    previous.main()
if __name__=="__main__":main()
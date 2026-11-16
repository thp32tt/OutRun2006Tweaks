"""Fail-closed four-mip DXT5 existing-palette patch; TEST_ONLY, no C1/C3/game approval."""
import io,struct
from PIL import Image,ImageChops,ImageFilter,ImageOps
from hd_bc3_native_codec import bc3_header
from hd_bc3_index_patch import patch_mip1,BC3Hold

def read_levels(raw):
    shape=bc3_header(raw)
    if not shape or shape[2]!=4: raise BC3Hold("MIP4_REQUIRED")
    w,h,_=shape;result=[];start=128
    for i in range(4):
        x,y=max(1,w>>i),max(1,h>>i)
        if x%4 or y%4: raise BC3Hold("MIP_NOT_4PX_BLOCK_ALIGNED")
        end=start+x*y
        header=bytearray(raw[:128])
        for pos,value in ((12,y),(16,x),(20,x*y),(28,1)):
            struct.pack_into("<I",header,pos,value)
        sub=bytes(header)+raw[start:end]
        if len(sub)!=128+x*y: raise BC3Hold("MIP_TRUNCATED")
        with Image.open(io.BytesIO(sub)) as im:
            im.load();decoded=im.convert("RGBA")
        if decoded.size!=(x,y):raise BC3Hold("MIP_DIMENSION_MISMATCH")
        result.append((sub,start,end,decoded));start=end
    if start!=len(raw):raise BC3Hold("MIP_SIZE_EXCESS")
    return result

def ink(im):
    return im.point(lambda p:255 if p>15 else 0)

def safe_patch(raw,owner,text,boxes,orientation="RAW"):
    if orientation not in ("RAW","FLIPY"):raise BC3Hold("ORIENTATION_UNKNOWN")
    levels=read_levels(raw);base=levels[0][3]
    if orientation=="FLIPY":base=ImageOps.flip(base)
    if owner.mode!="L" or text.mode!="RGBA" or owner.size!=base.size or text.size!=base.size:
        raise BC3Hold("SOURCE_OWNER_TEXT_DIMENSIONS")
    foreign=ImageChops.subtract(ink(base.getchannel("A")),owner)
    if not owner.getbbox() or not text.getchannel("A").getbbox():
        raise BC3Hold("NO_NATIVE_OWNER_OR_KOREAN_INK")
    if ImageChops.multiply(owner,foreign).getbbox():
        raise BC3Hold("OWNER_TOUCHES_FOREIGN_ALPHA")
    allow=Image.new("L",base.size,0)
    for box in boxes:
        x0,y0,x1,y1=box
        if not 0<=x0<x1<=base.width or not 0<=y0<y1<=base.height:
            raise BC3Hold("INVALID_SOURCE_NATIVE_BOX")
        allow.paste(255,box)
    if ImageChops.subtract(owner,allow).getbbox() or ImageChops.subtract(ink(text.getchannel("A")),allow).getbbox():
        raise BC3Hold("EDIT_OUTSIDE_ORIGINAL_ROI")
    output=bytearray(raw);evidence=[]
    for index,(sub,start,end,decoded) in enumerate(levels):
        scale=1<<index; size=decoded.size
        src=ImageOps.flip(decoded) if orientation=="FLIPY" else decoded
        if index:
            o=owner.resize(size,Image.Resampling.BOX).point(lambda a:255 if a else 0)
            f=foreign.resize(size,Image.Resampling.BOX).point(lambda a:255 if a else 0)
            t=text.resize(size,Image.Resampling.BOX)
            if ImageChops.multiply(o,f).getbbox():
                raise BC3Hold("MIP_OWNER_FOREIGN_MIXED_PIXEL")
        else:o,f,t=owner,foreign,text
        if ImageChops.multiply(ink(t.getchannel("A")),f.filter(ImageFilter.MaxFilter(3))).getbbox():
            raise BC3Hold("MIP_KOREAN_TOUCHES_FOREIGN_ART")
        target=src.copy();target.paste((0,0,0,0),(0,0),o);target.alpha_composite(t)
        diff=ImageChops.difference(src,target)
        if any(ImageChops.multiply(ch,f).getbbox() for ch in diff.split()):
            raise BC3Hold("MIP_FOREIGN_ART_DAMAGED_BEFORE_COMPRESSION")
        if orientation=="FLIPY":target=ImageOps.flip(target)
        level_boxes=[]
        for x0,y0,x1,y1 in boxes:
            a,b=x0//scale,y0//scale;c,d=min(size[0],(x1+scale-1)//scale),min(size[1],(y1+scale-1)//scale)
            if orientation=="FLIPY":b,d=size[1]-d,size[1]-b
            if a<c and b<d:level_boxes.append((a,b,c,d))
        patched,proof=patch_mip1(sub,target,level_boxes,decoded)
        with Image.open(io.BytesIO(patched)) as im:
            im.load();saved=im.convert("RGBA")
        if orientation=="FLIPY":saved=ImageOps.flip(saved)
        diff=ImageChops.difference(src,saved)
        if any(ImageChops.multiply(ch,f).getbbox() for ch in diff.split()):
            raise BC3Hold("MIP_SAVED_FOREIGN_ART_DAMAGED")
        output[start:end]=patched[128:]
        evidence.append({"level":index,"pixels":proof["bc3_pixels_modified"],
                         "blocks":proof["bc3_blocks_modified"]})
    if output[:128]!=raw[:128] or len(output)!=len(raw) or output==raw:
        raise BC3Hold("MIP_SOURCE_FORMAT_OR_NOOP")
    return bytes(output),evidence

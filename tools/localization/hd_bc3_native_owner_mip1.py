"""One-mip DXT5 exact source-owner A/B PNG patch: test DDS only.

No mask erasure outside owner, no source endpoint re-encode and no C1/C3/game
approval. This is the narrow repair for false 4-mip classification of DXT5.
"""
import io
from PIL import Image,ImageChops,ImageFilter,ImageOps
from hd_bc3_index_patch import patch_mip1,bc3_shape,BC3Hold

def apply(original,source_crop,owned,ambiguous,text,box,orientation="RAW"):
    width,height=bc3_shape(original) # rejects *actual* multi mip, not FOURCC=4
    if orientation not in ("RAW","FLIPY"):
        raise BC3Hold("OWNER_DDS_ORIENTATION_UNPROVEN")
    with Image.open(io.BytesIO(original)) as im:
        im.load();native=im.convert("RGBA")
    source=ImageOps.flip(native) if orientation=="FLIPY" else native
    x0,y0,x1,y1=box
    if not (0<=x0<x1<=width and 0<=y0<y1<=height
            and owned.mode=="L" and ambiguous.mode=="L"
            and text.mode=="RGBA" and source_crop.mode=="RGBA"
            and owned.size==ambiguous.size==text.size==source_crop.size==(x1-x0,y1-y0)):
        raise BC3Hold("OWNER_NATIVE_ALPHA_OR_BBOX_INVALID")
    if ImageChops.difference(source.crop(tuple(box)),source_crop).getbbox():
        raise BC3Hold("OWNER_NATIVE_SOURCE_SHA_CROP_MISMATCH")
    if ambiguous.getbbox():
        raise BC3Hold("OWNER_COMPONENT_AMBIGUOUS")
    native_core=source_crop.getchannel("A").point(lambda a:255 if a>15 else 0)
    if ImageChops.subtract(owned,native_core).getbbox():
        raise BC3Hold("OWNER_MASK_NOT_NATIVE_SOURCE_CORE")
    protected=ImageChops.subtract(native_core,owned)
    if ImageChops.multiply(owned,protected).getbbox():
        raise BC3Hold("OWNER_PROTECTED_SOURCE_COLLISION")
    glyph=text.getchannel("A").point(lambda a:255 if a>15 else 0)
    if not glyph.getbbox() or ImageChops.multiply(
        glyph,protected.filter(ImageFilter.MaxFilter(3))).getbbox():
        raise BC3Hold("OWNER_TRANSLATED_ART_COLLISION_OR_EMPTY")
    if glyph.getbbox()[0]<2 or glyph.getbbox()[1]<2 or (
            glyph.getbbox()[2]>text.width-2 or glyph.getbbox()[3]>text.height-2):
        raise BC3Hold("OWNER_TRANSLATION_TOUCHES_CROP_EDGE")
    clean=source.copy()
    owner_full=Image.new("L",source.size,0)
    owner_full.paste(owned,(x0,y0))
    clean.paste((0,0,0,0),(0,0),owner_full)
    final=clean.copy()
    final.alpha_composite(text,(x0,y0))
    source_protected=ImageChops.subtract(
        source.getchannel("A").point(lambda a:255 if a>15 else 0),owner_full)
    for ch in ImageChops.difference(source,final).split():
        if ImageChops.multiply(ch,source_protected).getbbox():
            raise BC3Hold("OWNER_ORIGINAL_FOREIGN_ART_CHANGED")
    physical=ImageOps.flip(final) if orientation=="FLIPY" else final
    physbox=(x0,height-y1,x1,height-y0) if orientation=="FLIPY" else box
    output,proof=patch_mip1(original,physical,[physbox],native)
    with Image.open(io.BytesIO(output)) as im:
        im.load();saved=im.convert("RGBA")
    saved=ImageOps.flip(saved) if orientation=="FLIPY" else saved
    for ch in ImageChops.difference(saved,source).split():
        if ImageChops.multiply(ch,source_protected).getbbox():
            raise BC3Hold("OWNER_SAVED_DXT5_PROTECTED_ART_CHANGED")
    if output[:128]!=original[:128] or len(output)!=len(original):
        raise BC3Hold("OWNER_SOURCE_HEADER_CHANGED")
    return output,proof

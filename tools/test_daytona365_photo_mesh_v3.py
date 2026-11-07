#!/usr/bin/env python3
"""Offline fail-closed Daytona v3 additive mesh/texture regression tests.

Can run on GitHub CI WITHOUT any private user's PMT or Ferrari photographs.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
import hashlib, math
try:
    import build_daytona_photo_mesh_v3 as model
    import build_daytona_ingame_ovc_v2 as v2
except ImportError:
    import build_daytona365_photo_mesh_v3 as model
    import build_daytona365_ingame_ovc_v2 as v2

def synthetic_seat():
    v=[];n=[];uv=[];idx=[]
    for center in (-.353,.353):
        base=len(v)
        for z in (.11,.52):
            for x in (center-.18,center+.18):
                v.append((x,.44+z*.04,z))
                n.append((0.,1.,0.))
                uv.append((x,z))
        idx.extend((base,base+1,base+2,base+1,base+3,base+2))
    return {"vertices":v,"normals":n,"uvs":uv,"indices":idx}

def test_straps():
    m,bands=model.add_photo_seat_straps(synthetic_seat())
    assert bands==8
    assert len(m["v"])==304
    assert len(m["i"])==8*18*2*3
    assert max(m["i"])<len(m["v"])
    assert all(math.isfinite(x) for p in m["v"] for x in p)

def test_photo_crop_tiling():
    img=Image.new("RGB",(40,40),(181,139,88))
    for x in range(40):
        for y in range(40):
            img.putpixel((x,y),(180+x//3,137+y//4,83+(x+y)//8))
    result=model.photo_tile(img,(2,2,38,38),128,"tan_leather")
    assert result.size==(128,128)
    assert min(c[0] for c in result.getdata())>110
    assert max(c[0] for c in result.getdata())<240
    # Side edges match when the texture address mode wraps.
    for y in range(128):
        a=result.getpixel((0,y));b=result.getpixel((127,y))
        assert max(abs(a[i]-b[i]) for i in range(3))<=3
    for x in range(128):
        a=result.getpixel((x,0));b=result.getpixel((x,127))
        assert max(abs(a[i]-b[i]) for i in range(3))<=3

def test_refine():
    p={"vertices":[(0.,0.,0.),(1.,0.,0.),(0.,0.,1.)],
       "normals":[(0.,1.,0.)]*3,
       "uvs":[(0.,0.),(1.,0.),(0.,1.)],
       "indices":[0,1,2]}
    m=model.refine_surface(p,3,"seat",offset=.004,bulge=.002)
    assert len(m["i"])==12 and len(m["v"])==6
    assert max(m["i"])<len(m["v"])
    assert abs(m["v"][0][1]-.004)<1e-6

def test_real_ovc_compatibility():
    m=v2._empty("UNIT_TEST_DAYTONA_SOURCE_ALIGNED",0)
    a=v2._v(m,(0.,0.,0.),(0.,1.,0.),(0.,0.))
    b=v2._v(m,(1.,0.,0.),(0.,1.,0.),(1.,0.))
    c=v2._v(m,(0.,0.,1.),(0.,1.,0.),(0.,1.))
    v2._tri(m,a,b,c)
    with TemporaryDirectory() as d:
        p=Path(d)/"unit.ovc"
        v2.write_ovc([m],[Image.new("RGBA",(32,32),(172,142,89,255))],p)
        assert v2.validate_ovc(p)
        corrupt=bytearray(p.read_bytes())
        corrupt[-1]^=0x5a
        p.write_bytes(corrupt)
        try:v2.validate_ovc(p)
        except AssertionError:pass
        else:raise AssertionError("OVC CRC corruption accepted")

if __name__=="__main__":
    for fn in (test_straps,test_photo_crop_tiling,test_refine,
               test_real_ovc_compatibility):
        fn();print(fn.__name__,"PASS")
    print("DAYTONA v3 synthetic source-free tests PASS")
#!/usr/bin/env python3
"""Source-free geometry, photographic UV and OVRCABH2 regression for Daytona v4."""
import math, tempfile
from pathlib import Path
from PIL import Image
try:
    import build_daytona_photo_mesh_v4 as v4
    import build_daytona_photo_mesh_v3 as v3
    import build_daytona_ingame_ovc_v2 as v2
except ImportError:
    import build_daytona365_photo_mesh_v4 as v4
    import build_daytona365_photo_mesh_v3 as v3
    import build_daytona365_ingame_ovc_v2 as v2

def seat():
    vertex=[];normal=[];uv=[];indices=[]
    for cx in (-.353,.353):
        base=len(vertex)
        for z in (.11,.54):
            for x in (cx-.2,cx+.2):
                vertex.append((x,.45+.08*z,z))
                normal.append((0.,1.,0.))
                uv.append((x,z))
        indices.extend((base,base+1,base+2,base+1,base+3,base+2))
    return {"vertices":vertex,"normals":normal,"uvs":uv,"indices":indices}

def vec(p,q):return tuple(q[i]-p[i] for i in range(3))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def test_rounded_rectangle_front_and_outline():
    m=v2._empty("TEST_BOUND_RECT",0)
    v4.add_rounded_rectangle(m,0.,.75,.02,.06,-.15,-.164)
    assert len(m["i"])%3==0
    assert min(v[2] for v in m["v"])==-.164
    assert max(v[2] for v in m["v"])==-.15
    # Must have positive +Z facing center fan; no inverted front caps.
    idx=m["i"]
    a,b,c=[m["v"][n][:3] for n in idx[:3]]
    assert cross(vec(a,b),vec(a,c))[2]>0
    assert len(m["v"])>40
    assert max(m["i"])<len(m["v"])

def test_photo_switch_v4_mesh_bounds():
    meshes=v4.add_real_switch_hardware()
    assert len(meshes)==5
    required=set(v4.verify_hardware(meshes+[
         _fake_raised_stitches()
    ]))
    assert "DAYTONA_V4_3D_4_SLIDER_PHYSICAL_CAPS" in required
    faces=sum(len(m["i"])//3 for m in meshes)
    assert faces>2500
    assert all(any(v[2]>-.16 for v in m["v"]) for m in meshes[:3])
    # all new controls limited to native PMT switch panel, not door/steering.
    for m in meshes:
        for p in m["v"]:
            assert -.155<=p[0]<=.155
            assert .58<=p[1]<=.86
            assert -.242<=p[2]<=-.125

def _fake_raised_stitches():
    m=v2._empty("DAYTONA_V4_GENUINE_DOUBLE_STITCHED_SEAT_BANDS",1)
    a=v2._v(m,(0.,0.,0.),(0.,1.,0.),(0.,0.))
    b=v2._v(m,(0.,0.,1.),(0.,1.,0.),(0.,1.))
    c=v2._v(m,(1.,0.,0.),(0.,1.,0.),(1.,0.))
    v2._tri(m,a,b,c)
    return m

def test_stitched_native_surface():
    straps,n=v3.add_photo_seat_straps(seat())
    assert n==8
    stitch,segs=v4.stitch_outline_of_straps(straps)
    assert segs==8*2*18
    assert len(stitch["v"])==segs*4
    assert len(stitch["i"])==segs*6
    # Raised seams derive from actual source band and stay very close.
    ymin=min(v[1] for v in straps["v"])
    ymax=max(v[1] for v in straps["v"])
    assert min(v[1] for v in stitch["v"])>=ymin-.003
    assert max(v[1] for v in stitch["v"])<=ymax+.003

def test_photo_switch_uv_two_physical_regions():
    # Synthetic 900x600 photo with top chrome area blue and lower toggle red.
    # The actual user's photos are private N100 files and not on GitHub CI.
    with tempfile.TemporaryDirectory() as t:
        t=Path(t)
        filename="REF5_mecum_interior_03_722bdd5e4.jpg"
        im=Image.new("RGB",(900,600))
        for y in range(600):
            for x in range(900):
                im.putpixel((x,y),(15,35,200) if y<280 else (200,25,35))
        im.save(t/filename)
        oldref,oldout=v3.REF,v4.OUT
        try:
            v3.REF=t
            v4.OUT=t
            image=v4.photo_switch_atlas_v4(None)
            assert image.size==(1024,1024)
            assert image.getpixel((500,100))[2]>150
            assert image.getpixel((500,900))[0]>150
            assert (t/"Daytona365_PHOTO_SWITCHBANK_NATIVE_UV_v4.png").is_file()
        finally:
            v3.REF=oldref
            v4.OUT=oldout

def test_actual_format_crc():
    meshes=v4.add_real_switch_hardware()
    with tempfile.TemporaryDirectory() as t:
        p=Path(t)/v2.NAME
        textures=[
            Image.new("RGBA",(64,64),(128,128,128,255)),
            Image.new("RGBA",(64,64),(28,25,24,255)),
            Image.new("RGBA",(64,64),(8,8,10,255)),
            Image.new("RGBA",(64,64),(172,125,70,255)),
            Image.new("RGBA",(64,64),(24,24,23,255)),
            Image.new("RGBA",(64,64),(39,37,35,255)),
            Image.new("RGBA",(64,64),(100,100,100,255))]
        metadata=v2.write_ovc(meshes,textures,p)
        assert v2.validate_ovc(p)
        assert metadata["materials"]==7
        assert metadata["groups"][0]["name"]=="DAYTONA_V4_3D_4_SLIDER_CHROME_FRAMES"
        data=bytearray(p.read_bytes())
        data[-7]^=1;p.write_bytes(data)
        try:v2.validate_ovc(p)
        except AssertionError:pass
        else:raise AssertionError("CRC tamper accepted")

if __name__=="__main__":
    for t in (
        test_rounded_rectangle_front_and_outline,
        test_photo_switch_v4_mesh_bounds,
        test_stitched_native_surface,
        test_photo_switch_uv_two_physical_regions,
        test_actual_format_crc
    ):
        t()
        print(t.__name__,"PASS")
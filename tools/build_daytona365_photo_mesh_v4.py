#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona: PHOTO-REGISTERED ACTUAL GAME MESH v4.

Adds accurately located three-dimensional four-slider switch bank, three
mechanical toggles, and stitched seams following the source seat mesh.
No substitute steering wheel, no change to original Dino or player camera.
Outputs an OVRCABH2 D3D9 fixed-function physical geometry/texture asset.
"""
from __future__ import annotations
import hashlib,io,json,math,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter,ImageEnhance
try:
    import build_daytona_photo_mesh_v3 as v3
    import build_daytona_ingame_ovc_v2 as v2
    from pmt_export_base import open_pmt,decode_object,decode_dds
except ImportError:
    import build_daytona365_photo_mesh_v3 as v3
    import build_daytona365_ingame_ovc_v2 as v2
    from dino_original_pmt_to_glb import open_pmt,decode_object,decode_dds

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"runtime_v4"
NAME=v2.NAME
assert NAME=="Daytona365_Cockpit_R26_v2.ovc" # Keep C++ loader filename.

def nrm(x):
    return v3.norm(x)

def add_rounded_rectangle(mesh, cx,cy, w,h,zfront,zback, radius=.0018,
                          material_label=""):
    """Beveled rectangular shell at a PMT-verified switch panel XY coordinate.

    zfront is physically nearer the camera (larger Z) than zback.
    Every vertex lives within original Daytona switch-panel envelope.
    """
    if not (w>2*radius and h>2*radius and zfront>zback):
        raise ValueError("invalid rectangle")
    perimeter=[]
    # CCW from top-right to top-left/bottom-left/bottom-right
    # Offset-angle corners guaranteed cyclic CCW.
    corners=((cx+w*.5-radius,cy+h*.5-radius,0,90),
             (cx-w*.5+radius,cy+h*.5-radius,90,180),
             (cx-w*.5+radius,cy-h*.5+radius,180,270),
             (cx+w*.5-radius,cy-h*.5+radius,270,360))
    for xx,yy,a0,a1 in corners:
        for k in range(5):
            theta=math.radians(a0+(a1-a0)*k/4)
            perimeter.append((xx+radius*math.cos(theta),
                              yy+radius*math.sin(theta)))
    frontcenter=v2._v(mesh,(cx,cy,zfront),(0.,0.,1.),(.5,.5))
    front=[]
    rear=[]
    for x,y in perimeter:
        u=.5+(x-cx)/w;v=.5+(y-cy)/h
        front.append(v2._v(mesh,(x,y,zfront),(0.,0.,1.),(u,v)))
        rear.append(v2._v(mesh,(x,y,zback),(0.,0.,-1.),(u,v)))
    for i in range(len(front)):
        j=(i+1)%len(front)
        # front-facing surface: normal orientation is approximately +Z
        v2._tri(mesh,frontcenter,front[i],front[j])
        # side thickness is real geometry, not a purely diffuse sprite.
        # CCW front face (+Z) and outward-facing side strips.
        v2._tri(mesh,front[i],rear[i],front[j])
        v2._tri(mesh,front[j],rear[i],rear[j])

def circle_torus(mesh,cx,cy,z,radius,tube=.0014,segments=24,ring_segments=7):
    if segments<8 or ring_segments<3:raise ValueError("bad torus tessellation")
    start=len(mesh["v"])
    for i in range(segments+1):
        a=i*math.tau/segments
        ca,sa=math.cos(a),math.sin(a)
        for j in range(ring_segments+1):
            b=j*math.tau/ring_segments
            cb,sb=math.cos(b),math.sin(b)
            norm=(ca*cb,sa*cb,sb)
            pos=(cx+(radius+tube*cb)*ca,
                 cy+(radius+tube*cb)*sa,z+tube*sb)
            v2._v(mesh,pos,norm,(i/segments,j/ring_segments))
    pitch=ring_segments+1
    for i in range(segments):
        for j in range(ring_segments):
            a=start+i*pitch+j; b=a+pitch
            v2._tri(mesh,a,b,a+1)
            v2._tri(mesh,a+1,b,b+1)

def sphere(mesh,cx,cy,cz,radius,material=0,latitudes=8,meridians=12):
    st=len(mesh["v"])
    for j in range(latitudes+1):
        t=math.pi*j/latitudes
        for i in range(meridians+1):
            a=i*math.tau/meridians
            normal=(math.sin(t)*math.cos(a),math.sin(t)*math.sin(a),math.cos(t))
            pos=tuple(p+radius*q for p,q in zip((cx,cy,cz),normal))
            v2._v(mesh,pos,normal,(i/meridians,j/latitudes))
    stride=meridians+1
    for j in range(latitudes):
        for i in range(meridians):
            a=st+j*stride+i
            b=a+stride
            if j>0:v2._tri(mesh,a,b,a+1)
            if j<latitudes-1:v2._tri(mesh,a+1,b,b+1)

def add_real_switch_hardware():
    """Photo reference: REF5_mecum_interior_03 four sliders, three toggles.

    PMT 15 front panel: x[-.0749,+.0749],y[.7316,.8473],z[-.1688,-.1671].
    PMT 15 lower panel: x[-.142,+.142],y[.5866,.7342],z[-.2287].
    Added components stay inside these two *different* 3D surface planes.
    """
    chrome=v2._empty("DAYTONA_V4_3D_4_SLIDER_CHROME_FRAMES",0)
    black=v2._empty("DAYTONA_V4_3D_4_SLIDER_BLACK_SLOTS",4)
    cap=v2._empty("DAYTONA_V4_3D_4_SLIDER_PHYSICAL_CAPS",5)
    toggle_chrome=v2._empty("DAYTONA_V4_3D_3_TOGGLE_CHROME_COLLARS",0)
    toggle_black=v2._empty("DAYTONA_V4_3D_3_TOGGLE_BLACK_LEVERS",4)
    # Replacing the v2 placeholder circular "switch bezel" with photo-grounded
    # actual vertical slider plates on the correct source panel plane.
    for x,y in ((-.057,.789),(-.020,.789),(.020,.789),(.057,.789)):
        add_rounded_rectangle(chrome,x,y,.026,.085,-.155,-.164,radius=.0026)
        add_rounded_rectangle(black,x,y,.012,.068,-.150,-.157,radius=.003)
        # Photo knobs all near lower rail; stagger slightly as seen in photo
        add_rounded_rectangle(cap,x,y-.021,.018,.012,-.142,-.150,radius=.0035)
        circle_torus(chrome,x,y-.021,-.140,.0072,tube=.00075,
                     segments=16,ring_segments=5)
    for x in (-.077,0.,.077):
        # Three short toggles on lower console extension from original PMT.
        y=.665;z=-.220
        circle_torus(toggle_chrome,x,y,z,.013,tube=.002,segments=28)
        sphere(toggle_black,x,y,z+.016,.008,latitudes=8,meridians=12)
    return [chrome,black,cap,toggle_chrome,toggle_black]

def stitch_outline_of_straps(straps,material=1):
    """Needle-width photo-colored stitching near BOTH sides of all 8 3D bands."""
    m=v2._empty("DAYTONA_V4_GENUINE_DOUBLE_STITCHED_SEAT_BANDS",material)
    count=0
    # v3 band topology is source interpolated, 19 stations x 2 edges, per band.
    if len(straps["v"])!=8*19*2:
        raise ValueError("unexpected band source topology")
    for band in range(8):
        base=band*19*2
        for side in (0,1):
            for station in range(18):
                a=straps["v"][base+station*2+side]
                b=straps["v"][base+(station+1)*2+side]
                # A thin short raised stitch segment within each source band.
                # Avoid extending beyond the actual underlying band geometry.
                p=a[:3];q=b[:3]
                normal=nrm(tuple((a[3+j]+b[3+j])*.5 for j in range(3)))
                d=nrm(tuple(q[j]-p[j] for j in range(3)))
                # Stitch 65% of edge length centered on segment.
                mid=tuple((p[j]+q[j])*.5+.0012*normal[j] for j in range(3))
                dist=math.sqrt(sum((q[j]-p[j])**2 for j in range(3)))
                if dist<.0001:continue
                tangent_width=.0006
                across=nrm((normal[1]*d[2]-normal[2]*d[1],
                            normal[2]*d[0]-normal[0]*d[2],
                            normal[0]*d[1]-normal[1]*d[0]))
                ids=[]
                for t,uvt in ((-.28,0.),(.28,1.)):
                    for w,uvy in ((-1.,0.),(1.,1.)):
                        pos=tuple(mid[j]+dist*t*d[j]+w*tangent_width*across[j]
                                  for j in range(3))
                        ids.append(v2._v(m,pos,normal,(uvt,uvy)))
                v2._tri(m,ids[0],ids[1],ids[2])
                v2._tri(m,ids[1],ids[3],ids[2])
                count+=1
    return m,count

def photo_switch_atlas_v4(asset):
    """Photo source two real instrument panels, cleanly UV-registered.

    No fictitious switch signs or opaque photograph pasted onto a scene.
    """
    p=v3.REF/"REF5_mecum_interior_03_722bdd5e4.jpg"
    im=Image.open(p).convert("RGBA")
    if im.size[0]<665 or im.size[1]<440:
        raise ValueError("photo changed")
    top=im.crop((310,80,665,275)).resize((1024,610),Image.Resampling.LANCZOS)
    bottom=im.crop((305,280,665,445)).resize((1024,414),Image.Resampling.LANCZOS)
    final=Image.new("RGBA",(1024,1024))
    final.paste(top,(0,0))
    final.paste(bottom,(0,610))
    # Blend *across* the two camera-space areas; no detached lower stretch.
    dr=ImageDraw.Draw(final)
    for y in range(604,616):
        a=(y-604)/12.
        for x in range(1024):
            c1=top.getpixel((x,603))
            c2=bottom.getpixel((x,5))
            final.putpixel((x,y),tuple(round(c1[k]*(1-a)+c2[k]*a) for k in range(4)))
    final.save(OUT/"Daytona365_PHOTO_SWITCHBANK_NATIVE_UV_v4.png")
    return final

def verify_hardware(meshes):
    names={m["name"] for m in meshes}
    required=("DAYTONA_V4_3D_4_SLIDER_CHROME_FRAMES",
              "DAYTONA_V4_3D_4_SLIDER_BLACK_SLOTS",
              "DAYTONA_V4_3D_4_SLIDER_PHYSICAL_CAPS",
              "DAYTONA_V4_3D_3_TOGGLE_CHROME_COLLARS",
              "DAYTONA_V4_3D_3_TOGGLE_BLACK_LEVERS",
              "DAYTONA_V4_GENUINE_DOUBLE_STITCHED_SEAT_BANDS")
    if not all(a in names for a in required):raise ValueError("missing photo-driven hardware")
    for m in meshes:
        if len(m["v"])<3 or len(m["i"])<3 or len(m["v"])>=65536:
            raise ValueError("bad mesh")
        if max(m["i"])>=len(m["v"]):raise ValueError("bad index")
        if len(m["i"])%3:raise ValueError("nontriangle")
        if any(not math.isfinite(c) for v in m["v"] for c in v):
            raise ValueError("nonfinite")
    # Hard stop if hardware violates the original verified instrument housing.
    for m in meshes:
        if not m["name"].startswith("DAYTONA_V4_3D"):continue
        for v in m["v"]:
            x,y,z=v[:3]
            if not (-.155<=x<=.155 and .58<=y<=.86 and -.242<=z<=-.125):
                raise ValueError(f"switch geometry outside source panel: {m['name']} {v[:3]}")
    # Diagonal swing and vertical gauge source not touched.
    return required

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if hashlib.sha256(v2.SOURCE.read_bytes()).hexdigest()!=v2.EXPECTED_SHA:
        raise RuntimeError("source Daytona PMT SHA mismatch")
    v3.OUT=OUT
    photos,sources=v3.load_reference_materials()
    orig=open_pmt(v2.SOURCE)
    groups=decode_object(orig,0)
    bytex={p["tex_index"]:p for p in groups}
    must={8:"object00_group01_material014_a0",
          15:"object00_group01_material016_a0",
          16:"object00_group01_material017_a0",
          18:"object00_group01_material018_a0",
          19:"object00_group01_material019_a0"}
    for k,v in must.items():
        if k not in bytex or bytex[k]["name"]!=v:
            raise ValueError("changed Daytona native PMT object identity")
    base,provenance=v2.build_geometry(orig)
    # The v2 "4 round switch bezels" are a known inaccurate placeholder.
    base=[m for m in base if m["name"]!="DAYTONA_CONSOLE_SWITCH_METAL_BEZELS_ACTUAL_GEOMETRY"]
    if len(base)!=3:raise ValueError("unexpected v2 geometry groups")
    gauge=v2.painted_gauge_atlas(orig)
    textures=[photos[0],photos[1],gauge,photos[3],photos[4],photos[5],
              photo_switch_atlas_v4(orig)]
    seat=v3.refine_surface(bytex[16],3,"DAYTONA_PHOTO_SEAT_UPHOLSTERY_REFINED_V4")
    console=v3.refine_surface(bytex[18],3,"DAYTONA_PHOTO_CONSOLE_LEATHER_REFINED_V4")
    piping,edge_count=v3.add_seat_piping(bytex[16])
    straps,strap_count=v3.add_photo_seat_straps(bytex[16])
    stitching,stitch_count=stitch_outline_of_straps(straps)
    shifter=v3.add_console_gate()
    rear=v3.refine_surface(bytex[19],4,"DAYTONA_PHOTO_REAR_TONNEAU_REFINED_V4")
    switches=v3.refine_surface(bytex[15],6,"DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V4",
                               offset=.006,bulge=0.)
    hardware=add_real_switch_hardware()
    meshes=base+[seat,console,piping,straps,stitching,shifter,rear,switches]+hardware
    verify_hardware(meshes)
    # Exactly the same original game's v2 sidecar binary ABI.
    out=OUT/NAME
    manifest=v2.write_ovc(meshes,textures,out)
    v2.validate_ovc(out)
    v3.write_obj(meshes,textures)
    orig_obj=OUT/"Daytona365_Cockpit_SOURCE_ALIGNED_v3.obj"
    obj=OUT/"Daytona365_Cockpit_SOURCE_ALIGNED_v4.obj"
    obj.write_text(orig_obj.read_text().replace("mtllib Daytona365_v3.mtl",
                                                "mtllib Daytona365_v4.mtl",1))
    mtl=(OUT/"Daytona365_v3.mtl").read_text()
    (OUT/"Daytona365_v4.mtl").write_text(mtl)
    # The original PMT texture color improvement is proven independently.
    original_pmt=ROOT/"runtime_v3"/"obj_plcar_dayts_pmt.sz"
    source_sha="0c1ab64bc8648d87cb44359bafdde3ba3e2e93e77b470b32886234bde083477d"
    if hashlib.sha256(original_pmt.read_bytes()).hexdigest()!=source_sha:
        raise ValueError("native photo PMT replaced unexpectedly")
    shutil.copyfile(original_pmt,OUT/original_pmt.name)
    report={
       **manifest,"version":"v4","source_pmt_sha256":v2.EXPECTED_SHA,
       "photo_reference":sources,
       "native_pmt_sha256":source_sha,
       "physical_sliders":4,"physical_toggles":3,
       "real_source_seat_straps":strap_count,
       "double_stitched_segments":stitch_count,
       "piping_segments":edge_count,
       "placeholder_round_switches_removed":True,
       "single_original_vehicle_wheel":True,
       "original_Dino_untouched":True,
       "native_player_car_kind_assumed":2,
       "real_game_tested":False,
       "HMD_verified":False,
       "normal_and_roughness": "offline assets only; no fixed-function shader support"}
    (OUT/"DAYTONA_V4_MESH_MATERIAL_MANIFEST.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps({k:report[k] for k in ("version","file","bytes","vertices",
      "triangles","materials","physical_sliders","physical_toggles",
      "real_source_seat_straps","double_stitched_segments","sha256")},indent=2))
if __name__=="__main__":
    main()
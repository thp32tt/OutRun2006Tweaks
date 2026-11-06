#!/usr/bin/env python3
"""Ferrari Dino 246 cockpit v4: reference-detail authored real 3D meshes.

NO concept imagery or image-generation tools. Geometry and PBR material maps are
constructed offline from the verified user-owned original OutRun 2006 Dino PMT
coordinate basis, without modifying the game original. GLB is editable; OVC is
experimental R26 parser-only compatible, not a working drop-in mod.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import struct
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))

import dino_cockpit_hdgeometry_v3 as v3
from PIL import Image,ImageDraw,ImageFilter,ImageFont,ImageOps,ImageChops

v2=v3.v2
v1=v3.v1
PI=math.pi

def p(x,y,z):return (float(x),float(y),float(z))
def curve(name,material,points,width=.0035,sides=10):
    return v1.tube(name,material,[p(*a) for a in points],width,sides)
def strip_frame(name,material,x0,x1,y0,y1,z,r=.003):
    out=[]
    for tag,points in (
        ("upper",[(x0,y1,z),(x1,y1,z)]),
        ("lower",[(x0,y0,z),(x1,y0,z)]),
        ("left",[(x0,y0,z),(x0,y1,z)]),
        ("right",[(x1,y0,z),(x1,y1,z)])):
        out.append(curve(name+"_"+tag,material,points,r))
    return out

def cylinder_z(name,mat,x,y,z,r,depth=.014,n=32):
    """Actual sidewall+cap cylindrical hardware in the dash XY plane."""
    m=v1.Mesh(name,mat)
    rings=[]
    for zp in (z-depth/2,z+depth/2):
        ring=[]
        for i in range(n+1):
            a=2*PI*i/n
            ring.append(m.vert(p(x+r*math.cos(a),y+r*math.sin(a),zp),
                               ((math.cos(a)+1)/2,(math.sin(a)+1)/2)))
        rings.append(ring)
    first=m.vert(p(x,y,z-depth/2),(.5,.5))
    last=m.vert(p(x,y,z+depth/2),(.5,.5))
    for k in range(n):
        m.quad(rings[0][k],rings[0][k+1],rings[1][k+1],rings[1][k])
        m.tri(first,rings[0][k+1],rings[0][k])
        m.tri(last,rings[1][k],rings[1][k+1])
    return m

def curved_dashboard_top():
    """Continuous flowing hood instead of original flat polygon top strip."""
    def fn(u,v):
        x=-.680+1.36*u
        z=-.895+.413*v
        driver=math.exp(-((x+.337)/.250)**2)
        y=.773-.045*v + .052*driver*math.sin(PI*v)
        y+=.011*math.cos(PI*(u+.16))*math.sin(PI*v)
        return p(x,y,z)
    return v1.surface("dashboard_hand_sculpted_v4","vinyl",64,24,fn)

def gauge_hood():
    out=[]
    def fn(u,v):
        x=-.615+.558*u
        y=.805+.052*math.sin(PI*u)*(1-v)+.008*math.sin(2*PI*v)
        z=-.545+.185*v
        return p(x,y,z)
    out.append(v1.surface("driver_arched_instrument_sunhood_v4","leather",38,16,fn))
    out.append(curve("sunhood_chrome_base_lip","metal",
        [p(-.60+.53*i/70,.813+.052*math.sin(PI*i/70),-.498) for i in range(71)],.003))
    out.append(curve("sunhood_double_rolled_leather","leather",
        [p(-.59+.51*i/70,.811+.055*math.sin(PI*i/70),-.52) for i in range(71)],.009))
    return out

def minor_dials():
    """Two outboard mechanical auxiliary dials, depth, glass, tick, bezel."""
    out=[]
    for no,(cx,cy,rr,texture) in enumerate((
        (-.601,.699,.030,"dial0"),
        (-.071,.700,.028,"dial2")
    )):
        z=-.418
        out.append(cylinder_z("aux_gauge%02d_black_can"%no,"plastic",cx,cy,z-.017,rr+.007,.023))
        out.append(v1.disc("aux_gauge%02d_face"%no,texture,(cx,cy,z+.004),rr,64))
        out.append(v3.ring("aux_gauge%02d_chrome_bezel"%no,"metal",
                           p(cx,cy,z+.008),(0,0,1),rr+.003,.003,48,10))
        out.append(v3.ring("aux_gauge%02d_inner_black_bezel"%no,"plastic",
                           p(cx,cy,z+.009),(0,0,1),rr-.003,.0018,48,8))
        for i in range(16):
            theta=PI/2+2*PI*i/16
            a,b=(.68 if i%4==0 else .75)*rr,.84*rr
            out.append(curve("aux_gauge%02d_tick%02d"%(no,i),"metal",[
                p(cx+a*math.cos(theta),cy+a*math.sin(theta),z+.014),
                p(cx+b*math.cos(theta),cy+b*math.sin(theta),z+.014)],.0010))
        out.append(curve("aux_gauge%02d_needle"%no,"metal",
            [p(cx,cy,z+.019),p(cx+rr*.58,cy+rr*.17,z+.021)],.0017))
        out.append(cylinder_z("aux_gauge%02d_center_pin"%no,"metal",
            cx,cy,z+.022,.003,.003,12))
        for k,a in enumerate((PI/4,PI*5/4)):
            out.append(cylinder_z("aux_gauge%02d_case_screw%d"%(no,k),"metal",
                cx+(rr+.011)*math.cos(a),cy+(rr+.011)*math.sin(a),z+.011,
                .0028,.004,12))
    return out

def chromed_radio_and_vents():
    """3D vintage horizontal louver vents and real stereo knobs/buttons."""
    m=[]
    # Two recessed upper vent bays, black slots with chrome rectangular borders
    for bay,(x0,x1) in enumerate(((.075,.185),(.201,.311))):
        y0,y1=.679,.743
        m.append(v3.skin_box("upper_vent_%d_black_recess"%bay,"plastic",
                             x0,x1,y0,y1,-.475,-.449))
        m.extend(strip_frame("upper_vent_%d_chrome_edge"%bay,"metal",
                             x0-.005,x1+.005,y0-.005,y1+.005,-.437,.0034))
        for k in range(6):
            yy=y0+.009+k*.009
            m.append(v3.skin_box("upper_vent_%d_louver_%02d"%(bay,k),
                                "vinyl",x0+.005,x1-.005,yy,yy+.003,-.442,-.431))
        m.append(curve("upper_vent_%d_middle_divider"%bay,"metal",
                  [p((x0+x1)/2,y0,-.427),p((x0+x1)/2,y1,-.427)],.002))
    # Stereo should sit BELOW vents, not float next to steering wheel.
    m.append(v3.skin_box("period_radio_face_chassis","plastic",
          .075,.325,.534,.615,-.466,-.442))
    m.extend(strip_frame("period_radio_chrome_frame","metal",
          .072,.328,.532,.617,-.434,.0037))
    m.append(v3.skin_box("radio_analog_tuner_dark_glass","vinyl",
          .112,.285,.578,.605,-.434,-.427))
    m.append(curve("radio_tuner_frequency_slider","metal",
          [p(.122,.588,-.422),p(.277,.588,-.422)],.0018,8))
    for k in range(10):
        x=.129+k*.016
        m.append(curve("radio_frequency_tick_%02d"%k,"metal",
                 [p(x,.591,-.421),p(x,.600 if k%3==0 else .597,-.421)],.001))
    for k,x in enumerate((.096,.302)):
        m.append(cylinder_z("radio_outer_knob_%d"%k,"metal",x,.557,-.422,.017,.021,32))
        m.append(cylinder_z("radio_black_knob_insert_%d"%k,"plastic",x,.557,-.411,.013,.007,32))
        m.append(cylinder_z("radio_knob_chrome_nub_%d"%k,"metal",x,.557,-.406,.004,.004,24))
    for k in range(5):
        x=.129+k*.030
        m.append(v3.skin_box("radio_station_key_%d"%k,"plastic",
              x,x+.022,.538,.551,-.429,-.415))
        m.extend(strip_frame("radio_station_key_%d_metal_trim"%k,"metal",
              x,x+.022,.538,.551,-.413,.0015))
    # Stable lower fascia border, separates radio chassis and glove box
    m.append(curve("radio_full_lower_chrome_sill","metal",
        [p(.061,.520,-.448),p(.343,.520,-.448)],.004))
    return m

def logo_and_steering_badge():
    """Yellow wheel emblem + bright embossed passenger-side model signature."""
    m=[]
    # Historical Dino-style yellow circular center badge, separate from metal hub.
    m.append(cylinder_z("wheel_center_amber_logo_disc","badge",
              -.320,.708,-.232,.030,.006,48))
    m.append(v3.ring("wheel_logo_chromed_outer_ring","metal",
             (-.320,.708,-.232),(0,0,1),.0305,.0025,64,10))
    m.append(v1.surface("passenger_fascia_Dino246_signature","signature",10,4,
        lambda u,v:p(.385+.242*u,.624+.052*v,-.424)))
    # glove compartment under logo, rounded narrow stainless trim
    m.extend(strip_frame("passenger_glovebox_lid_piping","metal",
        .374,.640,.533,.602,-.455,.0024))
    m.append(cylinder_z("passenger_glovebox_open_button","metal",
                       .508,.543,-.430,.007,.008,24))
    return m

def perforated_pedal(name,x):
    """Pedal 3x5 genuine circular holes, no solid face behind the cutouts."""
    m=v1.Mesh(name,"metal")
    xmax=.038
    zmin,zmax=-.606,-.492
    yfront,yback=.248,.237
    nx,nz=3,5
    for row in range(nz):
        for col in range(nx):
            x0=x-xmax+(2*xmax*col/nx);x1=x-xmax+(2*xmax*(col+1)/nx)
            z0=zmin+(zmax-zmin)*row/nz
            z1=zmin+(zmax-zmin)*(row+1)/nz
            cx=(x0+x1)/2;cz=(z0+z1)/2
            rx=(x1-x0)*.29;rz=(z1-z0)*.27
            # 8 points around each cell perimeter pair to round 8-edge opening.
            outer=((x0,cz),(x0,z1),(cx,z1),(x1,z1),
                   (x1,cz),(x1,z0),(cx,z0),(x0,z0))
            interior=tuple((cx+rx*math.cos(PI/2+2*PI*i/8),
                            cz+rz*math.sin(PI/2+2*PI*i/8)) for i in range(8))
            # Use perimeter points ordered CCW from left-mid clockwise around top.
            # Map the interior in the same angular order as the outer perimeter:
            # outer angles: pi,3pi/4,pi/2,pi/4,0,-pi/4,-pi/2,-3pi/4
            interior=tuple((cx+rx*math.cos(PI-PI*i/4),
                             cz+rz*math.sin(PI-PI*i/4)) for i in range(8))
            ids=[]
            for yy in (yfront,yback):
                outerid=[];innerid=[]
                for ox,oz in outer:
                    outerid.append(m.vert(p(ox,yy,oz),(.5+(ox-x)/(2*xmax),(oz-zmin)/(zmax-zmin))))
                for ix,iz in interior:
                    innerid.append(m.vert(p(ix,yy,iz),(.5+(ix-x)/(2*xmax),(iz-zmin)/(zmax-zmin))))
                ids.append((outerid,innerid))
            for k in range(8):
                nxt=(k+1)%8
                a,b=ids[0];c,d=ids[1]
                m.quad(a[k],a[nxt],b[nxt],b[k])
                m.quad(c[nxt],c[k],d[k],d[nxt])
                # Inner tube walls follow the real open holes.
                m.quad(b[k],b[nxt],d[nxt],d[k])
                # Avoid duplicate tile exterior sidewalls; can be rendered double sided.
    return m

def pedal_set():
    out=[]
    for i,x in enumerate((-.540,-.410,-.255)):
        out.append(perforated_pedal("pedal_%d_15_open_holes"%i,x))
        out.append(v3.skin_box("pedal_%d_rear_linkage"%i,"plastic",
                       x-.010,x+.010,.191,.245,-.580,-.521))
        out.extend(strip_frame("pedal_%d_metal_raised_rim"%i,"metal",
             x-.040,x+.040,.244,.266,-.485,.002))
        out.append(curve("pedal_%d_lower_bracket"%i,"metal",[
                 p(x,.216,-.574),p(x,.203,-.636)],.006,12))
    return out

def seat_rolls():
    """Bespoke leather upholstery with crosswise physical padding and seam edges.

    Original v2 padded shell stays as substrate. Each of 8 raised cushion bands
    and 7 backrest bands has real changing 3D relief rather than line decals.
    """
    m=[]
    for name,cx in (("driver",-.343),("passenger",.343)):
        # Seat base z .069 -> .70; do not overlap front console.
        for idx in range(8):
            z0=.093+idx*.073;z1=z0+.066
            def cushion(u,v,cx=cx,z0=z0,z1=z1):
                x=cx-.217+.434*u
                z=z0+(z1-z0)*v
                underlying=.351+.063*math.sin(PI*u)**.85+.020*math.sin(PI*(z-.069)/.63)
                rise=.024*(math.sin(PI*v)**.8)*(.55+.45*math.sin(PI*u))
                return p(x,underlying+rise,z)
            m.append(v1.surface(name+"_seat_rib_%02d_padded"%idx,
                 "seat",24,10,cushion))
            # welt sewn leather: small bead following each rib boundary
            m.append(curve(name+"_seat_rib_%02d_front_seam"%idx,"leather",[
                p(cx-.209+.418*j/24,
                  .351+.063*math.sin(PI*j/24)**.85+.016,
                  z0) for j in range(25)],.0022,8))
        # Backrest y .40-> .99 and z .75->1.04. Bulge faces FORWARD -Z.
        for idx in range(7):
            v0=.06+idx*.124;v1n=min(.95,v0+.116)
            def back(u,v,cx=cx,v0=v0,v1n=v1n):
                h=v0+(v1n-v0)*v
                x=cx+.213*(2*u-1)*(1-.10*h)
                y=.408+.583*h
                base=.758+.278*h-.052*math.sin(PI*u)*math.sin(PI*h)
                protrude=.024*math.sin(PI*v)**.85*(.55+.45*math.sin(PI*u))
                return p(x,y,base-protrude)
            m.append(v1.surface(name+"_back_rib_%02d_padded"%idx,
                       "seat",24,12,back))
            m.append(curve(name+"_back_rib_%02d_upper_seam"%idx,"leather",[
              p(cx-.205+.410*j/24,.408+.583*v0,
                .758+.278*v0-.052*math.sin(PI*j/24)*math.sin(PI*v0)-.003)
              for j in range(25)],.0023,8))
    return m

def leather_handbrake():
    m=[]
    # Lever sits on RH side of driver center console.
    m.append(curve("central_handbrake_real_metal_rod","metal",
             [p(.153,.349,.419),p(.157,.386,.471),p(.181,.429,.536)],.012,16))
    m.append(curve("central_handbrake_black_leather_grip","leather",
             [p(.168,.405,.505),p(.182,.430,.545)],.019,20))
    m.append(v3.ring("central_handbrake_release_button","metal",
             p(.183,.435,.548),(0,.4,1),.011,.0035,44,10))
    m.append(v3.skin_box("central_handbrake_fascia_boot","leather",
                        .133,.182,.329,.369,.401,.471))
    return m

def new_textures(px):
    """Hand-authored procedural 2K maps; photo likeness needs real art later."""
    tex=v2.material_maps_v2(px)
    bg=Image.new("RGB",(px,px),(209,159,11))
    d=ImageDraw.Draw(bg)
    for i in range(11):
        rad=int(px*.48)-i*max(1,px//200)
        value=min(255,197+int(30*i/11))
        d.ellipse((px//2-rad,px//2-rad,px//2+rad,px//2+rad),
                  outline=(value,max(0,value-45),8),width=2)
    fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"
    try:font=ImageFont.truetype(fontfile,int(px*.22))
    except:font=ImageFont.load_default()
    d.text((px*.5,px*.51),"Dino",font=font,anchor="mm",fill=(13,17,25),
           stroke_width=max(1,px//320))
    tex["badge"]=bg
    mark=Image.new("RGB",(px,px//4),(29,30,32))
    md=ImageDraw.Draw(mark)
    try:mf=ImageFont.truetype(fontfile,int(px*.13))
    except:mf=ImageFont.load_default()
    md.text((px//2,px//8),"Dino 246",font=mf,anchor="mm",fill=(216,215,205),
             stroke_width=1)
    tex["signature"]=mark
    return tex

def apply_glb_normal_maps(path,materials):
    """Embed real glTF normalTexture slots, only GLB (R26 OVC is diffuse-only).

    Height-from-albedo normals are approximate geometry illusion,
    NOT photographs. Base color maps and geometry are unchanged.
    """
    old=path.read_bytes()
    if old[:4]!=b"glTF":raise ValueError("not a GLB")
    jslen=struct.unpack_from("<I",old,12)[0]
    doc=json.loads(old[20:20+jslen])
    boff=20+jslen
    if old[boff+4:boff+8]!=b"BIN"+bytes((0,)):raise ValueError("GLB has no BIN")
    binlen=struct.unpack_from("<I",old,boff)[0]
    payload=bytearray(old[boff+8:boff+8+binlen])
    supported=("leather","vinyl","plastic","metal","carpet","seat")
    for name in supported:
        if name not in materials:raise ValueError("missing material "+name)
        pic=materials[name].convert("RGB")
        if max(pic.size)>1024:
            pic.thumbnail((1024,1024),Image.Resampling.LANCZOS)
        grayscale=ImageOps.grayscale(pic).filter(ImageFilter.GaussianBlur(.6))
        # Height texture Sobel-like gradients in RGB tangent normal channels.
        dx=grayscale.filter(ImageFilter.Kernel((3,3),(-1,0,1,-2,0,2,-1,0,1),scale=8,offset=128))
        dy=grayscale.filter(ImageFilter.Kernel((3,3),(-1,-2,-1,0,0,0,1,2,1),scale=8,offset=128))
        nb=Image.merge("RGB",(dx,dy,Image.new("L",pic.size,245)))
        buf=io.BytesIO();nb.save(buf,"PNG",optimize=True)
        raw=buf.getvalue()
        payload.extend(bytes((-len(payload))%4))
        view={"buffer":0,"byteOffset":len(payload),"byteLength":len(raw)}
        doc["bufferViews"].append(view)
        payload.extend(raw)
        imgindex=len(doc["images"])
        doc["images"].append({"name":name+"_surface_normal","mimeType":"image/png",
                              "bufferView":len(doc["bufferViews"])-1})
        tx=len(doc["textures"])
        doc["textures"].append({"source":imgindex})
        for mat in doc["materials"]:
            if mat["name"]==name+"_PBR_preview":
                mat["normalTexture"]={"index":tx,"scale":0.30 if name!="metal" else .17}
    doc["buffers"][0]["byteLength"]=len(payload)
    doc.setdefault("extras",{})["v4NormalMaps"]="procedural albedo-derived; glTF preview only"
    j=json.dumps(doc,ensure_ascii=True,separators=(",",":")).encode()
    j+=b" "*(-len(j)%4)
    payload.extend(bytes((-len(payload))%4))
    out=(struct.pack("<4sII",b"glTF",2,12+8+len(j)+8+len(payload))
         +struct.pack("<I4s",len(j),b"JSON")+j
         +struct.pack("<I4s",len(payload),b"BIN"+bytes((0,)))+payload)
    path.write_bytes(out)

def build_v4():
    old=v3.build_v3()
    # The old simple switchplate, stereo-less dash and flat artificial seat
    # ribs would overlap photo-detail parts if they were merely added on top.
    remove_names={
        "dash_top_soft_curve","instrument_hood_curved",
        "LHD_horn_button_black",
        "glove_compartment_recess",
        "driver_backrest_upper_cushion_roll",
        "passenger_backrest_upper_cushion_roll",
    }
    remove_prefixes=(
        "switchplate_","toggle_pin_","toggle_grip_","vent_louver_",
        "driver_seat_stitch_rib_","passenger_seat_stitch_rib_",
        "driver_back_stitch_rib_","passenger_back_stitch_rib_",
        "driver_cushion_cross_stitch_","passenger_cushion_cross_stitch_",
        "driver_backrest_cross_stitch_","passenger_backrest_cross_stitch_",
        "pedal_0_plate","pedal_1_plate","pedal_2_plate",
        "pedal0_grip","pedal1_grip","pedal2_grip",
    )
    out=[m for m in old if m.name not in remove_names
         and not m.name.startswith(remove_prefixes)]
    out.extend([curved_dashboard_top()])
    out.extend(gauge_hood())
    out.extend(minor_dials())
    out.extend(chromed_radio_and_vents())
    out.extend(logo_and_steering_badge())
    out.extend(pedal_set())
    out.extend(seat_rolls())
    out.extend(leather_handbrake())
    names=[m.name for m in out]
    if len(names)!=len(set(names)):
        raise ValueError("duplicate mesh names")
    for m in out:m.normalise()
    if len(out)<380:raise ValueError("missing expected detailed model")
    if not 90000<sum(len(m.faces)//3 for m in out)<180000:
        raise ValueError("unexpected cockpit detail budget")
    v3.column_clearance() # fail closed if any column-to-gauge wall regression
    return out

def export_model(game_dir,outdir,glbpx=2048,ovcpx=1024,texture_dir=None):
    source=game_dir/"Cars"/"obj_plcar_dino_pmt.sz"
    if not source.is_file():raise FileNotFoundError(source)
    orig=v3.original.open_pmt(source)
    part=v3.original.decode_object(orig,0)
    pts=[v for p0 in part for v in p0["vertices"]]
    low=[min(x[k] for x in pts) for k in range(3)]
    high=[max(x[k] for x in pts) for k in range(3)]
    if orig["obj_count"]!=17 or not(-.95<low[0]<-.75 and .75<high[0]<.95
        and .08<low[1]<.22 and 1.0<high[1]<1.22
        and -2.3<low[2]<-1.9 and 1.9<high[2]<2.3):
        raise ValueError("wrong/unexpected original Dino source")
    meshes=build_v4()
    gpu=v2.merge_meshes_for_runtime(meshes)
    mats_glb=new_textures(glbpx)
    mats_ovc=new_textures(ovcpx)
    if texture_dir:
        replacement_glb=v2.material_maps_v2(glbpx,texture_dir)
        replacement_ovc=v2.material_maps_v2(ovcpx,texture_dir)
        mats_glb.update(replacement_glb);mats_ovc.update(replacement_ovc)
    outdir.mkdir(parents=True,exist_ok=True)
    glb=outdir/"Dino246_ConceptDetail_Cockpit_v4.glb"
    ovc=outdir/"Dino246_ConceptDetail_Cockpit_v4.ovc"
    v1.write_glb(meshes,mats_glb,glb)
    apply_glb_normal_maps(glb,mats_glb)
    v1.write_ovc(gpu,mats_ovc,ovc)
    tris=sum(len(m.faces)//3 for m in meshes)
    report={
      "model":"Dino246 HD cockpit v4 reference-detail authored rebuild",
      "source":source.name,"sourceSha256":hashlib.sha256(source.read_bytes()).hexdigest(),
      "sourceOriginalUnmodified":True,
      "meshes":len(meshes),"vertices":sum(len(m.vertices) for m in meshes),
      "triangles":tris,"runtimeBatches":len(gpu),
      "runtimeTriangles":sum(len(m.faces)//3 for m in gpu),
      "normalMapsGLB":6,
      "textureOrigin":"procedurally generated maps, not AI image generation",
      "referenceAchievement":"partial; geometric detail only, not photoreal parity",
      "geometryAdds":["two outboard mechanical instrument gauges and bezel ticks",
          "real vintage stereo/radio with tuner/knobs/buttons",
          "dual air vents with separate blades and chrome trims",
          "yellow wheel Dino badge and passenger Dino 246 signature",
          "three 3x5 perforated racing pedals with 45 physical holes total",
          "two seats with 8 cushion and 7 backrest inflated upholstery ribs each",
          "center leather handbrake assembly","hand-rounded upper dashboard/driver gauge sunhood"],
      "v3ColumnClearance":v3.column_clearance(),
      "glbBytes":glb.stat().st_size,"ovcBytes":ovc.stat().st_size,
      "runtimeValidation":"UNTESTED","safeToInstallOverWorkingR26":False,
      "remaining":["scoped stock wheel/dashboard R26 draw suppression",
          "Quest APK driver coordinate alignment","Quest3 two-eye test",
          "photo-level textured material art + original car structure fitting",
          "fit of door cards, stereo and seat in native body/clipping"]}
    (outdir/"Dino246_ConceptDetail_Cockpit_v4_report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--game-dir",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--glb-texture",type=int,choices=(256,512,1024,2048),default=2048)
    ap.add_argument("--ovc-texture",type=int,choices=(256,512,1024),default=1024)
    ap.add_argument("--texture-dir",type=Path,default=None)
    a=ap.parse_args()
    export_model(a.game_dir,a.output_dir,a.glb_texture,a.ovc_texture,a.texture_dir)

if __name__=="__main__":
    main()
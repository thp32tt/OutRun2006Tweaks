#!/usr/bin/env python3
"""Dino 246 HD cockpit v2 - authored geometry refinement.

Separate opt-in non-installed proof-of-concept for OutRun 2006 R26.
The original Dino PMT is strictly read-only and used only for 3D basis checks.
New topology replaces v1 flat seats and cylindrical steering spokes with
thick upholstery shells and perforated metal spoke plates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import struct
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dino_cockpit_hdgeometry_v1 as v1
from PIL import Image, ImageOps

PI = math.pi
Vec = tuple[float, float, float]


def pos(x, y, z): return (float(x), float(y), float(z))


def radial(center, rad, t, z=0.0, width=0.0):
    a = 2 * PI * t
    return pos(center[0] + (rad + width) * math.cos(a),
               center[1] + (rad + width) * math.sin(a),
               center[2] + z - 0.18 * rad * math.sin(a))


def make_spoke(angle, number):
    """One thin stamped 3D triangular spoke with TWO actual open slots.

    Perforations are missing triangles, not dark painted fake texture spots.
    Swept 140 radial steps keep hole contours smooth and bevel small.
    """
    out = v1.Mesh("wheel_spoke_%d_perforated_stamped_metal" % number, "metal")
    n = 140
    radius0 = 0.046
    radius1 = 0.170
    depth = (-0.268, -0.271)
    sections = []
    for step in range(n+1):
        t = step/n
        r = radius0 + (radius1-radius0)*t
        w = (0.027*(1-t) + 0.017*t) * (0.90 + 0.10*math.sin(PI*t))
        # two pill-like openings, ending in rounded ellipses
        hole = 0.0
        for center, span in ((0.36, 0.12), (0.69, 0.11)):
            e = (t-center)/span
            if abs(e) < 1:
                hole = max(hole, 0.60*w*math.sqrt(1-e*e))
        sections.append((t, r, w, hole))
    # Point order left outer, left hole, right hole, right outer
    rings = []
    ca, sa = math.cos(angle), math.sin(angle)
    for t, r, w, hole in sections:
        q = []
        for plane in depth:
            pts = []
            for lateral in (-w, -hole, hole, w):
                x = -.320 + r*ca - lateral*sa
                y = .708 + r*sa + lateral*ca
                z = plane - 0.18*r*sa
                pts.append(out.vert(pos(x,y,z), (t, lateral/(2*w)+.5)))
            q.append(pts)
        rings.append(q)
    for i in range(n):
        for surface in (0,1):
            left0, left1, right1, right0 = rings[i][surface]
            L0, L1, R1, R0 = rings[i+1][surface]
            # shoulder strips
            if surface==0:
                out.quad(left0,L0,L1,left1)
                out.quad(right1,R1,R0,right0)
            else:
                out.quad(left1,L1,L0,left0)
                out.quad(right0,R0,R1,right1)
            # For no-hole sections the two shoulder strips share their center
            # seam exactly. A separate center quad collapses to zero area, so
            # omit it. Cutouts remain fully open where hole>0.
        # long outer walls and inside of open perforation slots
        for lateral in (0,3):
            a,b = rings[i][0][lateral],rings[i+1][0][lateral]
            c,d = rings[i+1][1][lateral],rings[i][1][lateral]
            if lateral==0:out.quad(a,d,c,b)
            else:out.quad(a,b,c,d)
        if sections[i][3]>1e-9 or sections[i+1][3]>1e-9:
            for lateral in (1,2):
                a,b=rings[i][0][lateral],rings[i+1][0][lateral]
                c,d=rings[i+1][1][lateral],rings[i][1][lateral]
                if lateral==1:out.quad(a,b,c,d)
                else:out.quad(a,d,c,b)
    for end in (0,n):
        a,b,c,d=rings[end][0]
        A,B,C,D=rings[end][1]
        out.quad(a,b,B,A)
        out.quad(c,d,D,C)
    return out


def add_trim_tube(name, material, path, radius=0.0035, sides=10):
    return v1.tube(name,material,path,radius,sides)


def seat_shell(label, cx, is_backrest):
    """Thick sewn-upholstery volume with outside/inside/edge faces.

    All placement uses native model-local basis: original Dino x+/-0.34 seat
    and z=~0.06..1.05, NOT independently guessed GLB re-import scaling.
    """
    nu,nv=30,36
    mat="seat" if is_backrest else "leather"
    mesh=v1.Mesh(label + ("_backrest_thick_shell" if is_backrest else "_cushion_thick_shell"),mat)
    a,b = [],[]
    def shape(u,v):
        x=cx + 0.245*(2*u-1)*(1.0-(.10*v if is_backrest else .02*v))
        if is_backrest:
            y=.408+.583*v
            z=.758+.278*v-.052*math.sin(PI*u)*math.sin(PI*v)
            # curved back is offset away from driver's head
            return pos(x,y,z)
        y=.351+.063*math.sin(PI*u)**.85+.020*math.sin(PI*v)
        z=.069+.63*v + .026*math.sin(PI*u)
        return pos(x,y,z)
    for i in range(nu+1):
        u=i/nu; ar=[];br=[]
        for j in range(nv+1):
            v=j/nv;p=shape(u,v)
            bpos=pos(p[0],p[1],p[2]+.062) if is_backrest else pos(p[0],p[1]-.061,p[2])
            ar.append(mesh.vert(p,(u,v)))
            br.append(mesh.vert(bpos,(u,v)))
        a.append(ar);b.append(br)
    for i in range(nu):
        for j in range(nv):
            mesh.quad(a[i][j],a[i+1][j],a[i+1][j+1],a[i][j+1])
            mesh.quad(b[i][j+1],b[i+1][j+1],b[i+1][j],b[i][j])
    for i in range(nu):
        for j in (0,nv):
            mesh.quad(a[i][j],b[i][j],b[i+1][j],a[i+1][j])
    for j in range(nv):
        for i in (0,nu):
            mesh.quad(a[i][j],a[i][j+1],b[i][j+1],b[i][j])
    return mesh


def curved_door(name, sx):
    """Replacement door trim body with a rounded horizontal seam."""
    return v1.surface(name+"_interior_card","leather",10,24,lambda u,v:
       pos(sx*(.655+.008*math.sin(PI*v)),
           .326+.455*u,
           -.68+1.70*v))


def add_details(meshes):
    append = meshes.append
    # Dashboard vinyl overhang seam, instrument panel horizontal stitching
    append(add_trim_tube("dash_double_stitch_outer_1","seat",
        [pos(-.65+1.30*i/80,.768+.037*math.sin(PI*i/80),-.846) for i in range(81)],.0027))
    append(add_trim_tube("dash_double_stitch_outer_2","seat",
        [pos(-.65+1.30*i/80,.765+.036*math.sin(PI*i/80),-.833) for i in range(81)],.0026))
    # Gauge bezel internals, raised tick marks, dial mounting screws
    for idx,(x,y,r) in enumerate(((-.447,.726,.065),(-.324,.735,.079),(-.196,.726,.065))):
        for layer,delta,material in (("trim",.94,"metal"),("shadow",.885,"plastic")):
            append(add_trim_tube("gauge%02d_%s_ring"%(idx,layer),material,
                [pos(x+r*delta*math.cos(2*PI*j/72),
                     y+r*delta*math.sin(2*PI*j/72),-.409) for j in range(73)],.0025))
        for k in range(20):
            theta=PI/2+2*PI*k/20
            inner=(.68 if k%5==0 else .75)*r
            outer=.81*r
            append(add_trim_tube("gauge%02d_tick%02d"%(idx,k),"metal",
                [pos(x+inner*math.cos(theta),y+inner*math.sin(theta),-.410),
                 pos(x+outer*math.cos(theta),y+outer*math.sin(theta),-.410)],
                .00155,6))
        append(v1.disc("gauge%02d_center_pin"%idx,"metal",pos(x,y,-.400),.006,20))
    # Wheel rim stitching two continuous circumferential seams and spoke root screws.
    for band,dz in (("inner",.018),("outer",-.019)):
        append(add_trim_tube("wheel_rim_%s_stitch_trace"%band,"seat",
            [radial((-.320,.708,-.289),.180,j/128,dz) for j in range(129)],.0026,7))
    for spoke,angle in enumerate((PI/2,PI*7/6,PI*11/6)):
        for j,r in enumerate((.055,.158)):
            x=-.320+r*math.cos(angle)
            y=.708+r*math.sin(angle)
            z=-.263-.18*r*math.sin(angle)
            append(v1.disc("wheel_spoke%d_rivet%d"%(spoke,j),"plastic",pos(x,y,z),.0065,16))
            append(v1.disc("wheel_spoke%d_chrome_pin%d"%(spoke,j),"metal",pos(x,y,z+.002),.0028,16))
    # Two sculpted door cards; associated manual-window winders and pull loops.
    for tag,sgn in (("door_left",-1),("door_right",1)):
        append(curved_door(tag,sgn))
        x=sgn*.643
        append(add_trim_tube(tag+"_chrome_upper_sill","metal",
            [pos(x,.779,-.67+1.69*j/45) for j in range(46)],.0037))
        append(add_trim_tube(tag+"_door_panel_lower_seam","seat",
            [pos(x,.377,-.66+1.67*j/45) for j in range(46)],.0030))
        append(add_trim_tube(tag+"_handle_metal_curve","metal",[
            pos(x-sgn*.034,.615,.21),pos(x-sgn*.064,.605,.21),
            pos(x-sgn*.066,.587,.25),pos(x-sgn*.035,.585,.28)],.011))
        append(add_trim_tube(tag+"_window_crank_spindle","metal",
            [pos(x-sgn*.006,.520,-.30),pos(x-sgn*.050,.522,-.28)],.009))
        append(add_trim_tube(tag+"_window_crank_arm","metal",
            [pos(x-sgn*.05,.522,-.28),pos(x-sgn*.052,.603,-.28)],.008))
        append(add_trim_tube(tag+"_window_crank_knob","plastic",
            [pos(x-sgn*.052,.603,-.28),pos(x-sgn*.05,.618,-.28)],.012))
        append(v1.disc(tag+"_door_lock_button","metal",pos(x-sgn*.006,.788,.63),.008,16))
    # Seat bolsters 3D curved tubes and additional true seams on shaped cushion
    for label,cx in (("driver",-.343),("passenger",.343)):
        for s in (-1,1):
            append(add_trim_tube("%s_cushion_side_bolster_%d"%(label,s),"leather",
                [pos(cx+s*.223,.363+.043*math.sin(PI*k/36),.10+.59*k/36)
                 for k in range(37)],.024,12))
            append(add_trim_tube("%s_backrest_side_bolster_%d"%(label,s),"leather",
                [pos(cx+s*(.23-.028*k/36),.432+.54*k/36,.775+.26*k/36)
                 for k in range(37)],.021,12))
        # head side pads below roof level, integrated seats do not grow tall
        append(v1.surface(label+"_backrest_upper_cushion_roll","leather",14,10,
            lambda u,v,cx=cx:
                pos(cx+.20*(2*u-1),.976+.024*math.sin(PI*u)*math.cos(PI*v),
                    1.028+.035*v)))
        for i in range(7):
            z=.135+.083*i
            append(add_trim_tube(label+"_cushion_cross_stitch_%d"%i,"seat",
                [pos(cx-.182+.364*k/24,
                     .353+.063*math.sin(PI*k/24)+.016*math.sin(PI*i/8),z)
                 for k in range(25)],.0020,7))
        for i in range(7):
            y=.466+.073*i
            v=i/8
            append(add_trim_tube(label+"_backrest_cross_stitch_%d"%i,"seat",
                [pos(cx-.174+.348*k/24,y,
                     .758+.278*v-.052*math.sin(PI*k/24)*math.sin(PI*v))
                 for k in range(25)],.0019,7))
        # Seat mounting rails, keep under surface and away from road-level chassis.
        for s in (-1,1):
            append(v1.box(label+"_seat_floor_rail_%d"%s,"metal",
                pos(cx+s*.16,.255,.48),(.020,.027,.54)))
    # Door hinges, footwell and gauge screws are not left as untextured planes.
    for x in (-.535,.535):
        append(add_trim_tube("footwell_chrome_rail_%s"%str(x),"metal",
            [pos(x,.203,-.70),pos(x,.203,-.16)],.004))
    # Improved H shift-gate raised rails and frame screws.
    for i,x in enumerate((-.013,.035,.085)):
        append(add_trim_tube("gear_selector_gate_ridge_%d"%i,"metal",
            [pos(x,.420,-.02),pos(x,.420,.120)],.0032))
    for k,z in enumerate((-.025,.060,.124)):
        append(add_trim_tube("gear_selector_cross_link_%d"%k,"metal",
            [pos(-.014,.420,z),pos(.087,.420,z)],.0027))
    for i,(x,z) in enumerate(((-.015,-.030),(.091,-.030),(-.015,.13),(.091,.13))):
        append(v1.disc("gear_gate_mounting_screw_%d"%i,"metal",pos(x,.424,z),.006,16))
    # Door and center control stitching. No duplicate old original parts emitted.
    append(add_trim_tube("center_console_front_edge_piping","seat",
        [pos(-.135+.27*j/30,.385,-.255) for j in range(31)],.0038))
    return meshes


def build_v2():
    original=v1.generate_cockpit()
    discarded={
      "driver_seat_pad_sculpted","passenger_seat_pad_sculpted",
      "driver_backrest_sculpted","passenger_backrest_sculpted"
    }
    # Remove v1 round spaghetti spokes; replace them with stamped perforated plates.
    result=[m for m in original
            if m.name not in discarded
            and not m.name.startswith("steering_spoke_")
            and not m.name.startswith("spoke_rivet_")]
    for number,angle in enumerate((PI/2,PI*7/6,PI*11/6)):
        result.append(make_spoke(angle,number))
    for name,x in (("driver",-.343),("passenger",.343)):
        result.append(seat_shell(name,x,False))
        result.append(seat_shell(name,x,True))
    add_details(result)
    names=[m.name for m in result]
    if len(names)!=len(set(names)):
        raise ValueError("duplicate mesh identities")
    for mesh in result:mesh.normalise()
    return result


def merge_meshes_for_runtime(meshes, max_vertices=60000):
    """Batch same-material objects to cut fixed-function D3D9 Draw calls.

    GLB retains all named editable objects; R26 OVC is a separate low-draw-call
    staging export. Original world/view/projection still belongs to R26.
    """
    result=[]
    materials=sorted(set(m.material for m in meshes))
    for mat in materials:
        bucket=v1.Mesh("DINO_V2_" + mat + "_0",mat)
        batch=0
        def flush():
            nonlocal bucket,batch
            if bucket.vertices:
                bucket.normalise()
                result.append(bucket)
                batch+=1
                bucket=v1.Mesh("DINO_V2_" + mat + "_%d"%batch,mat)
        for part in [p for p in meshes if p.material==mat]:
            if len(part.vertices)>max_vertices:
                raise ValueError("single mesh too large for safe D3D9 batch")
            if len(bucket.vertices)+len(part.vertices)>max_vertices:
                flush()
            base=len(bucket.vertices)
            bucket.vertices.extend(part.vertices)
            bucket.uvs.extend(part.uvs)
            bucket.normals.extend(part.normals)
            bucket.faces.extend(base+i for i in part.faces)
        flush()
    return result


def material_maps_v2(size, texture_dir=None):
    """Default deterministic maps or explicit PNG material override.

    All six diffuse material PNGs must exist in the supplied directory; this
    ensures no silently mismatched textures. Dial gauges remain reproducible
    procedural artwork. A PNG path does not prove that it came from an AI.
    """
    maps=v1.material_maps(size)
    if texture_dir is None:
        return maps
    folder=Path(texture_dir)
    required=("leather","vinyl","plastic","metal","carpet","seat")
    for material in required:
        path=folder/(material+".png")
        if not path.is_file() or path.stat().st_size>20*1024*1024:
            raise ValueError("missing or oversized HD material: "+str(path))
        with Image.open(path) as opened:
            if opened.format!="PNG":
                raise ValueError("expected PNG material: "+str(path))
            w,h=opened.size
            if not 256<=w<=8192 or not 256<=h<=8192:
                raise ValueError("unsupported PNG dimensions: "+str(path))
            opened.load()
            im=ImageOps.fit(opened.convert("RGB"),(size,size),
                            method=Image.Resampling.LANCZOS)
        maps[material]=im
    return maps


def output_files(game_dir,outdir,glbsize,ovcsize,texture_dir=None):
    file=game_dir/"Cars"/"obj_plcar_dino_pmt.sz"
    if not file.is_file():raise FileNotFoundError(file)
    # Re-use original source PMT validation including entry count and size basis.
    import dino_original_pmt_to_glb as original
    asset=original.open_pmt(file)
    parts=original.decode_object(asset,0)
    if asset["obj_count"]!=17 or len(parts)<20:
        raise ValueError("unexpected original Dino object")
    p=[v for part in parts for v in part["vertices"]]
    lo=[min(x[i] for x in p) for i in range(3)]
    hi=[max(x[i] for x in p) for i in range(3)]
    if not (-.95<lo[0]<-.75 and .75<hi[0]<.95
            and .08<lo[1]<.22 and 1.0<hi[1]<1.22
            and -2.3<lo[2]<-1.9 and 1.9<hi[2]<2.3):
        raise ValueError("original Dino dimensions changed: fail closed")
    models=build_v2()
    outdir.mkdir(parents=True,exist_ok=True)
    glb=outdir/"Dino246_OriginalDim_Cockpit_HDGeometry_v2.glb"
    ovc=outdir/"Dino246_OriginalDim_Cockpit_HDGeometry_v2.ovc"
    v1.write_glb(models,material_maps_v2(glbsize,texture_dir),glb)
    gpu_models=merge_meshes_for_runtime(models)
    v1.write_ovc(gpu_models,material_maps_v2(ovcsize,texture_dir),ovc)
    info={"source":"obj_plcar_dino_pmt.sz",
          "sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
          "originalModelBounds":{"min":lo,"max":hi},
          "sourceUnmodified":True,
          "meshes":len(models),
          "vertices":sum(len(m.vertices) for m in models),
          "triangles":sum(len(m.faces)//3 for m in models),
          "runtimeBatchedGroups":len(gpu_models),
          "runtimeVertices":sum(len(m.vertices) for m in gpu_models),
          "runtimeTriangles":sum(len(m.faces)//3 for m in gpu_models),
          "v1TriangleCount":sum(len(m.faces)//3 for m in v1.generate_cockpit()),
          "v1MeshCount":len(v1.generate_cockpit()),
          "features":[
             "Stamped perforated three-spoke wheel (real holes) and bright rivets",
             "Thick sculpted seat-shell mesh, seam piping and bolsters",
             "Three refined gauge bezels with raised ticks and center pivots",
             "Door cards, manual window cranks and opening handles",
             "H-pattern shift gate metal rails and screws",
             "Cabin trim, fine stitching and seat mounting rails"],
          "glbBytes":glb.stat().st_size,
          "ovcBytes":ovc.stat().st_size,
          "glbTexturePx":glbsize,
          "ovcTexturePx":ovcsize,
          "textureProvenance":("user-supplied PNG materials (origin unverified)" if texture_dir
             else "deterministic procedural texture, NOT AI generated"),
          "validation":"UNTESTED until independent GLB and native R26 OVC parsing",
          "runtimeValidation":"UNTESTED", "safeToInstall":False,
          "remaining":["original cockpit draw hide","R26 loader opt-in",
                       "APK seat camera parity","AI image-generated UV textures",
                       "Quest 3 runtime HMD"]}
    (outdir/"Dino246_HDGeometry_v2_report.json").write_text(
        json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(info,ensure_ascii=False,indent=2))
    return info


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game-dir",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--glb-texture",type=int,choices=(512,1024,2048),default=1024)
    ap.add_argument("--texture-dir",type=Path,default=None,
        help="Optional directory containing all six named PNG material maps")
    ap.add_argument("--ovc-texture",type=int,choices=(256,512,1024),default=512)
    ar=ap.parse_args()
    output_files(ar.game_dir,ar.output_dir,ar.glb_texture,ar.ovc_texture,ar.texture_dir)


if __name__=="__main__":
    main()
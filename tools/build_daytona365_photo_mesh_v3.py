#!/usr/bin/env python3
"""Build real, source-registered Ferrari Daytona D3D9Ex external cockpit v3.

Uses LOCAL Ferrari 365 GTS/4 reference photographs for photographic material
patches. Produces OVRCABH2, not a simulated picture. No edits to Dino.
Maintains original steering geometry/controls and all gameplay matrices.
"""
from __future__ import annotations
import argparse,hashlib,io,json,math,struct,collections
from pathlib import Path
from PIL import Image,ImageEnhance,ImageFilter,ImageStat,ImageOps
try:
    import build_daytona_ingame_ovc_v2 as v2
except ImportError:
    import build_daytona365_ingame_ovc_v2 as v2
try:
    from pmt_export_base import open_pmt,decode_object,decode_dds
except ImportError:
    from dino_original_pmt_to_glb import open_pmt,decode_object,decode_dds

ROOT=Path(__file__).resolve().parent
REF=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona")
OUT=ROOT/"runtime_v3"
SOURCE=v2.SOURCE
EXPECTED=v2.EXPECTED_SHA
MATERIALS=[
    ("chrome_refined","REF11_steering_instrument_closeup_5769d1ef1b.jpg",(240,380,465,440),256),
    ("seam_thread","REF9_transmission_01_b09482c09.jpg",(24,160,86,222),256),
    ("gauge_panel","REF11_steering_instrument_closeup_5769d1ef1b.jpg",(225,115,650,410),1024),
    ("tan_leather","REF9_transmission_01_b09482c09.jpg",(24,160,86,222),512),
    ("black_dash","REF5_mecum_interior_03_722bdd5e4.jpg",(670,48,850,235),512),
    ("dark_piping","REF5_mecum_interior_03_722bdd5e4.jpg",(670,48,850,235),256)
]

def photo_tile(image, box, size, kind):
    """Mirror quadrants to make a wrap-compatible tile (no pasted scene photos)."""
    src=image.convert("RGB").crop(box)
    if src.width<15 or src.height<15: raise ValueError("photo crop too small")
    half=size//2
    src=src.resize((half,half),Image.Resampling.LANCZOS)
    tile=Image.new("RGB",(size,size))
    tile.paste(src,(0,0))
    tile.paste(ImageOps.mirror(src),(half,0))
    tile.paste(ImageOps.flip(src),(0,half))
    tile.paste(ImageOps.flip(ImageOps.mirror(src)),(half,half))
    # Material illumination is leveled to avoid baking directional photo shadows.
    if kind=="tan_leather":
        tile=ImageEnhance.Color(tile).enhance(.76)
        tile=ImageEnhance.Contrast(tile).enhance(.78)
        tile=ImageEnhance.Brightness(tile).enhance(.90)
    elif kind=="black_dash":
        tile=ImageEnhance.Brightness(tile).enhance(.78)
        tile=ImageEnhance.Contrast(tile).enhance(.55)
    elif kind=="seam_thread":
        tile=ImageEnhance.Color(tile).enhance(.62)
        tile=ImageEnhance.Contrast(tile).enhance(.40)
        tile=ImageEnhance.Brightness(tile).enhance(.82)
    elif kind=="dark_piping":
        tile=ImageEnhance.Brightness(tile).enhance(.62)
        tile=ImageEnhance.Color(tile).enhance(.50)
    elif kind=="chrome_refined":
        # Photographic chrome lightness comes from the reference's metallic
        # highlights, but discard captured symbols, gauges and reflections:
        # only luminance statistics feed a tileable brushed-metal material.
        pix=list(image.convert("RGB").crop(box).getdata())
        neutral=[p for p in pix if max(p)-min(p)<55 and 85<sum(p)/3<225]
        if len(neutral)<100:raise ValueError("insufficient photo chrome samples")
        values=sorted(sum(p)/3 for p in neutral)
        lo=values[len(values)//4]
        hi=values[3*len(values)//4]
        lo=max(85,min(180,lo));hi=max(lo+8,min(235,hi))
        im=Image.new("RGB",(size,size))
        pixels=im.load()
        for y in range(size):
            yy=y/size*2*math.pi
            shade=lo+(hi-lo)*(.55+.32*math.sin(yy)+.10*math.sin(3*yy))
            for x in range(size):
                xx=x/size*2*math.pi
                v=int(max(0,min(255,shade+2.5*math.sin(11*xx+5*yy))))
                pixels[x,y]=(v,min(255,v+1),min(255,v+2))
        tile=im
    return tile.filter(ImageFilter.GaussianBlur(.38)).convert("RGBA")

def photo_auxiliary_maps(tile,out,kind):
    """Photo-derived PBR backups for a future shader path (NOT used in D3D9 FFP)."""
    im=tile.convert("RGB")
    w,h=im.size
    gray=im.convert("L")
    # Photo micrograin only; remove lighting gradients so tangent normals do
    # not encode directional shadows of the original reference photograph.
    blurred=gray.filter(ImageFilter.GaussianBlur(radius=6))
    strength=.18 if kind in ("tan_leather","seam_thread") else .12
    pixels=gray.load(); blur=blurred.load()
    delta=[[max(-16,min(16,pixels[x,y]-blur[x,y])) for x in range(w)] for y in range(h)]
    n=Image.new("RGB",(w,h));pix=n.load()
    for y in range(h):
        for x in range(w):
            dx=(delta[y][(x+1)%w]-delta[y][(x-1)%w])*strength
            dy=(delta[(y+1)%h][x]-delta[(y-1)%h][x])*strength
            length=math.sqrt(dx*dx+dy*dy+255*255)
            pix[x,y]=(int(127.5-127.5*dx/length),
                       int(127.5-127.5*dy/length),
                       int(127.5+127.5*255/length))
    n.save(out/f"Daytona365_PHOTO_{kind}_normal_OFFLINE.png")
    rough={"chrome_refined":78,"seam_thread":218,"gauge_panel":120,
           "tan_leather":199,"black_dash":223,"dark_piping":214}[kind]
    Image.new("L",(w,h),rough).save(out/f"Daytona365_PHOTO_{kind}_roughness_OFFLINE.png")

def load_reference_materials():
    OUT.mkdir(parents=True,exist_ok=True)
    images=[];sources=[]
    for kind,filename,region,size in MATERIALS:
        p=REF/filename
        data=p.read_bytes()
        image=Image.open(io.BytesIO(data))
        l,t,r,b=region
        if r>image.width or b>image.height:
            raise ValueError("reference changed dimensions "+filename)
        tile=photo_tile(image,region,size,kind)
        tile.save(OUT/f"Daytona365_PHOTO_{kind}_v3.png",optimize=True)
        images.append(tile)
        photo_auxiliary_maps(tile,OUT,kind)
        sources.append({"material":kind,"reference_file":filename,
             "reference_sha256":hashlib.sha256(data).hexdigest(),
             "crop":region,"output_resolution":size})
    # The gauge texture still follows the actual source PMT island UVs.
    # A generated fake concept cockpit is NOT used as texture data.
    return images,sources

def norm(v):
    m=math.sqrt(sum(x*x for x in v))
    return tuple(x/m for x in v) if m>1e-8 else (0.,1.,0.)

def refine_surface(part,material,name,offset=.004,bulge=.002):
    """Geometric subdivision of original seat/console. Keep UV mapping and silhouette."""
    raw=part["vertices"];ns=part["normals"];uv=part["uvs"];ids=part["indices"]
    mesh=v2._empty(name,material)
    for pos,n,tex in zip(raw,ns,uv):
        n=norm(n)
        v2._v(mesh,tuple(pos[i]+offset*n[i] for i in range(3)),n,tex)
    edges={}
    def midway(a,b):
        k=(a,b) if a<b else (b,a)
        if k in edges:return edges[k]
        na,nb=norm(ns[a]),norm(ns[b])
        nn=norm(tuple(na[i]+nb[i] for i in range(3)))
        agreement=sum(na[i]*nb[i] for i in range(3))
        bend=bulge*max(0.,min(1.,(agreement-.65)/.35))
        p=tuple((raw[a][i]+raw[b][i])*.5+(offset+bend)*nn[i] for i in range(3))
        t=tuple((uv[a][i]+uv[b][i])*.5 for i in range(2))
        nidx=v2._v(mesh,p,nn,t)
        edges[k]=nidx
        return nidx
    for q in range(0,len(ids),3):
        a,b,c=ids[q:q+3]
        x,y,z=midway(a,b),midway(b,c),midway(c,a)
        for tr in ((a,x,z),(x,b,y),(z,y,c),(x,y,z)):
            v2._tri(mesh,*tr)
    return mesh

def add_seat_piping(seat,material=5):
    """Tubular-looking physical edge strips from the actual source seat boundaries."""
    m=v2._empty("DAYTONA_PHOTO_SEAT_CONTOUR_PIPING_V3",material)
    ecount=collections.Counter()
    idx=seat["indices"];raw=seat["vertices"];ns=seat["normals"]
    for k in range(0,len(idx),3):
        a,b,c=idx[k:k+3]
        for u,v in ((a,b),(b,c),(c,a)):
            ecount[tuple(sorted((u,v)))]+=1
    accepted=0
    for (a,b),count in sorted(ecount.items()):
        if count!=1:continue
        p,q=raw[a],raw[b]
        # Seat-back boundary is source-grounded: z>0.12 behind the dash and
        # y>0.45. Skip long hard side/seat underbody edges and mirrored midline.
        if min(p[1],q[1])<.47 or min(p[2],q[2])<.13:continue
        if p[0]*q[0]<=0:continue
        dist=math.sqrt(sum((p[i]-q[i])**2 for i in range(3)))
        if dist<.007 or dist>.28:continue
        tangent=norm(tuple(q[i]-p[i] for i in range(3)))
        na,nb=norm(ns[a]),norm(ns[b])
        avgn=norm(tuple(na[i]+nb[i] for i in range(3)))
        across=norm((tangent[1]*avgn[2]-tangent[2]*avgn[1],
                     tangent[2]*avgn[0]-tangent[0]*avgn[2],
                     tangent[0]*avgn[1]-tangent[1]*avgn[0]))
        width=.0027
        vertices=[]
        for endpoint,normal,t in ((p,na,0.),(q,nb,1.)):
            for sign,vtex in ((-1.,0.),(1.,1.)):
                xyz=tuple(endpoint[i]+.009*normal[i]+sign*width*across[i] for i in range(3))
                vertices.append(v2._v(m,xyz,normal,(t,vtex)))
        v2._tri(m,vertices[0],vertices[1],vertices[2])
        v2._tri(m,vertices[1],vertices[3],vertices[2])
        accepted+=1
    return m,accepted

def add_photo_seat_straps(seat,material=5):
    """Eight real 3D black straps matched to x-z seat surface from native PMT.

    Photo ref: REF5_mecum_interior_01. This is physically curved geometry
    following the upper cushion; it is NOT a screen-space flat ribbon.
    """
    m=v2._empty("DAYTONA_PHOTO_BLACK_SEAT_BANDS_ON_SOURCE_SURFACE_V3",material)
    v=seat["vertices"];n=seat["normals"];inds=seat["indices"]
    tris=[inds[i:i+3] for i in range(0,len(inds),3)]
    def top_at(x,z):
        best=None
        for a,b,c in tris:
            pa,pb,pc=v[a],v[b],v[c]
            d=(pb[2]-pc[2])*(pa[0]-pc[0])+(pc[0]-pb[0])*(pa[2]-pc[2])
            if abs(d)<1e-10:continue
            aa=((pb[2]-pc[2])*(x-pc[0])+(pc[0]-pb[0])*(z-pc[2]))/d
            bb=((pc[2]-pa[2])*(x-pc[0])+(pa[0]-pc[0])*(z-pc[2]))/d
            cc=1-aa-bb
            if min(aa,bb,cc)<-.0005:continue
            yy=aa*pa[1]+bb*pb[1]+cc*pc[1]
            nn=norm(tuple(aa*n[a][j]+bb*n[b][j]+cc*n[c][j] for j in range(3)))
            if nn[1]<.44:continue
            if best is None or yy>best[0]:best=(yy,nn)
        return best
    straps=0
    for center in (-.353,.353):
        for zz in (.18,.26,.34,.42):
            # side edges at x≈centre±0.135, 18 sample points follow true
            # curved source seat surface. Black leather covers ~24mm in Z.
            ids=[]
            for i in range(19):
                x=center-.137+.274*i/18
                for side,vt in ((-1.,0.),(1.,1.)):
                    z=zz+side*.012
                    at=top_at(x,z)
                    if at is None:raise ValueError(
                        f"source seat lacks anchor x={x} z={z}; refusing flat approximation")
                    y,nn=at
                    xyz=(x+.011*nn[0],y+.011*nn[1],z+.011*nn[2])
                    ids.append(v2._v(m,xyz,nn,(i/18.,vt)))
            for i in range(18):
                a,b,c,d=ids[2*i],ids[2*i+1],ids[2*i+2],ids[2*i+3]
                v2._tri(m,a,b,c)
                v2._tri(m,b,d,c)
            straps+=1
    return m,straps

def add_console_gate(material=0):
    """Native-console-plane aligned beveled chrome guide, NO duplicate shifter."""
    m=v2._empty("DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",material)
    # Native material18 top face: y=0.4583 at z=0.0059 and
    # y=0.416 at z=0.1985; normal ~ (0, 0.979, 0.205).
    def surface_y(z):
        return .4583+(.416-.4583)*((z-.0059)/(.1985-.0059))
    def bar(a,b,width=.004):
        dx=b[0]-a[0];dz=b[1]-a[1]
        inv=1./max(1e-6,math.hypot(dx,dz))
        perp=(-dz*inv,dx*inv)
        ids=[]
        for x,z,t in ((a[0],a[1],0.),(b[0],b[1],1.)):
            for side,vtex in ((-1.,0.),(1.,1.)):
                xx=x+perp[0]*side*width
                zz=z+perp[1]*side*width
                yy=surface_y(zz)+.011
                ids.append(v2._v(m,(xx,yy,zz),(0,.977,.213),(t,vtex)))
        v2._tri(m,ids[0],ids[1],ids[2]);v2._tri(m,ids[1],ids[3],ids[2])
    # Geometry restrained inside native center tunnel x±.10, z≈.02..18.
    for a,b in (((-.073,.025),(.073,.025)),((.073,.025),(.073,.156)),
                ((.073,.156),(-.073,.156)),((-.073,.156),(-.073,.025))):
        bar(a,b)
    # Short gate bars follow the original 5-speed gated transmission reference.
    for x in (-.041,-.013,.015,.043):
        bar((x,.044),(x,.121),width=.002)
    return m

def photo_switch_atlas(asset):
    """Real 365 Daytona switch photo registered into tex15 original UV island."""
    source=Image.open(REF/"REF5_mecum_interior_03_722bdd5e4.jpg").convert("RGB")
    # Photo includes the native four-slide bank. Keep lower original atlas UV
    # to avoid painting gauges/shifter where the reference was not photographed.
    detail=source.crop((305,85,625,348)).resize((1024,610),Image.Resampling.LANCZOS)
    png,_,_=decode_dds(asset,15,1)
    base=Image.open(io.BytesIO(png)).convert("RGBA")
    base=base.resize((1024,1024),Image.Resampling.LANCZOS)
    base.paste(detail.convert("RGBA"),(0,0))
    # Avoid hard photographic seam at v=0.4 atlas boundary.
    seam=Image.new("RGBA",(1024,38))
    for y in range(38):
        alpha=y/38
        for x in range(1024):
            a=base.getpixel((x,590))
            b=base.getpixel((x,610+y))
            seam.putpixel((x,y),tuple(int(a[i]*(1-alpha)+b[i]*alpha) for i in range(4)))
    base.paste(seam,(0,590))
    base.save(OUT/"Daytona365_PHOTO_SWITCHBANK_SOURCE_UV_v3.png")
    return base

def verify_meshes(meshes,orig_seat,orig_console):
    assert all(m["v"] and m["i"] and max(m["i"])<len(m["v"]) for m in meshes)
    assert all(len(m["i"])%3==0 and len(m["v"])<65536 for m in meshes)
    for m in meshes:
        for v in m["v"]:
            assert all(math.isfinite(c) and abs(c)<10000 for c in v)
    # Photo seat & console anchor must remain within original native envelope
    # plus only the specified millimetric normal offsets.
    for nm,p in (("DAYTONA_PHOTO_SEAT_UPHOLSTERY_REFINED_V3",orig_seat),
                 ("DAYTONA_PHOTO_CONSOLE_LEATHER_REFINED_V3",orig_console)):
        m=next(q for q in meshes if q["name"]==nm)
        src=p["vertices"];out=[x[:3] for x in m["v"]]
        for i in range(3):
            assert min(v[i] for v in out)>=min(v[i] for v in src)-.014
            assert max(v[i] for v in out)<=max(v[i] for v in src)+.014

def write_obj(meshes,images):
    # Separate OBJ for geometry review in Blender (not the live game loader).
    obj=["# Daytona365 v3 source registered actual external geometry",
         "mtllib Daytona365_v3.mtl"]
    mtl=[];start=1
    for i,m in enumerate(meshes):
        name=f"PHOTO_MATERIAL_{m['material']}"
        obj.extend((f"o {m['name']}",f"usemtl {name}"))
        for vert in m["v"]:obj.append("v %.7f %.7f %.7f"%vert[:3])
        for vert in m["v"]:obj.append("vt %.7f %.7f"%vert[6:])
        for vert in m["v"]:obj.append("vn %.7f %.7f %.7f"%vert[3:6])
        for j in range(0,len(m["i"]),3):
            ids=[start+t for t in m["i"][j:j+3]]
            obj.append("f "+" ".join(f"{t}/{t}/{t}" for t in ids))
        start+=len(m["v"])
    for i,img in enumerate(images):
        name=f"PHOTO_MATERIAL_{i}"
        mtl.extend((f"newmtl {name}","Ka 1 1 1","Kd 1 1 1","Ks 0.05 0.05 0.05",
                    f"map_Kd Daytona365_PHOTO_MAT_{i}.png",""))
        img.save(OUT/f"Daytona365_PHOTO_MAT_{i}.png",optimize=True)
    (OUT/"Daytona365_Cockpit_SOURCE_ALIGNED_v3.obj").write_text("\n".join(obj)+"\n")
    (OUT/"Daytona365_v3.mtl").write_text("\n".join(mtl)+"\n")

def build():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=EXPECTED:
        raise RuntimeError("Original Daytona PMT SHA changed")
    materials,sources=load_reference_materials()
    # Gauge material #2 keeps exact UV from original high-res repaint.
    a=open_pmt(SOURCE);p=decode_object(a,0)
    bytex={q["tex_index"]:q for q in p}
    assert bytex[16]["name"]=="object00_group01_material017_a0"
    assert bytex[18]["name"]=="object00_group01_material018_a0"
    assert bytex[15]["name"]=="object00_group01_material016_a0"
    assert bytex[19]["name"]=="object00_group01_material019_a0"
    assert bytex[8]["name"]=="object00_group01_material014_a0"
    base,geometry_source=v2.build_geometry(a)
    gauge=v2.painted_gauge_atlas(a)
    # 0 chrome from original photograph; 1 tan dashboard stitches sourced from
    # reference; 2 source-template instrument UV; 3 tan leather;
    # 4 black leather; 5 black piping; 6 real photo four-slider bank.
    images=[materials[0],materials[1],gauge,materials[3],materials[4],materials[5],photo_switch_atlas(a)]
    # The 1st 4 groups are the already source-verified v2 gauge, metal, stitches.
    seat=refine_surface(bytex[16],3,"DAYTONA_PHOTO_SEAT_UPHOLSTERY_REFINED_V3")
    console=refine_surface(bytex[18],3,"DAYTONA_PHOTO_CONSOLE_LEATHER_REFINED_V3")
    piping,edges=add_seat_piping(bytex[16],5)
    shift=add_console_gate()
    black_bands,bands=add_photo_seat_straps(bytex[16])
    # Original Daytona rear leather tonneau source texture19; repaint at same
    # native-space positions using the documented black dashboard fabric photo.
    rear=refine_surface(bytex[19],4,"DAYTONA_PHOTO_REAR_TONNEAU_REFINED_V3")
    switches=refine_surface(bytex[15],6,"DAYTONA_PHOTO_NATIVE_SWITCHBANK_REFINED_V3",
                            offset=.006,bulge=0.)
    meshes=base+[seat,console,piping,black_bands,shift,rear,switches]
    verify_meshes(meshes,bytex[16],bytex[18])
    outfile=OUT/v2.NAME
    meta=v2.write_ovc(meshes,images,outfile)
    v2.validate_ovc(outfile)
    write_obj(meshes,images)
    result={**meta,"version":"v3",
      "reference_textures":sources,"native_uv_gauges":True,
      "seat_source_texture_index":16,"console_source_texture_index":18,
      "seat_boundary_piping_edges":edges,"source_surface_seat_bands":bands,
      "source_game_pmts_unchanged":True,
      "runtime_source":"PMT object0",
      "game_runtime":"STATIC_DDS_OVC_V2_PARSE_PASS / Quest HMD NOT TESTED",
      "duplicate_steering_wheel":False,
      "car_kind":2,
      "dino_untouched":True,
      "source_sha256":EXPECTED}
    (OUT/"DAYTONA_V3_PHOTO_MODEL_MANIFEST.json").write_text(json.dumps(result,indent=2))
    return result

if __name__=="__main__":
    print(json.dumps(build(),indent=2))
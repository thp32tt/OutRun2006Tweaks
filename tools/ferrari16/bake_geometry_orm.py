#!/usr/bin/env python3
"""Offline geometry-derived AO into missing OVC3/4 ORM slots.

Pillow only. No original asset changes; no authored maps overwritten.
R=voxel hemisphere occlusion, G=B=255 (neutral multipliers for authored
scalar roughness/metallic in the current SM3 shader). This is an approximate
bake, not source-authored spatial roughness or metalness.
"""
import argparse
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

CAR_IDS = dict(zip(("dino246gts","daytona365","f50","360spider","f355spider",
    "575superamerica","testarossa","288gto","328gts","250gto","512bb","f40",
    "550barchetta","f430","enzo","f430spider"), (*range(15),28)))
def sha(b): return hashlib.sha256(b).hexdigest()
def add(a,b): return (a[0]+b[0],a[1]+b[1],a[2]+b[2])
def sub(a,b): return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def scale(a,s): return (a[0]*s,a[1]*s,a[2]*s)
def dot(a,b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):
    n=math.sqrt(dot(a,a))
    return scale(a,1/n) if n>1e-10 else None
def u32(b,i): return struct.unpack_from("<I",b,i)[0]
def blob(b,i):
    n=u32(b,i); end=i+4+n
    if end>len(b): raise ValueError("truncated map")
    return b[i+4:end],end
def parse(b):
    if not 36<=len(b)<=128*1024**2: raise ValueError("size")
    ver,ng,nm,nv,nt,payload,crc=struct.unpack_from("<7I",b,8)
    if (b[:8],ver) not in ((b"OVRCABH3",3),(b"OVRCABH4",4)) or payload!=len(b)-36 or zlib.crc32(b[36:])!=crc:
        raise ValueError("header/CRC")
    if not 0<ng<=512 or not 0<nm<=128 or not 0<nv<=1000000 or not 0<nt<=2000000:
        raise ValueError("envelope")
    pos=36; meshes=[]; actual_v=actual_t=0
    for _ in range(ng):
        ln,mat,v,i,w=struct.unpack_from("<HHIII",b,pos); pos+=16
        if not 0<ln<=256 or mat>=nm or not 3<=v<=nv or not 3<=i<=nt*3 or i%3 or w not in (2,4): raise ValueError("group")
        name=b[pos:pos+ln]; pos+=ln
        verts=list(struct.iter_unpack("<8f",b[pos:pos+v*32]));pos+=v*32
        indices=struct.unpack_from("<"+str(i)+("H" if w==2 else "I"),b,pos);pos+=i*w
        if len(verts)!=v or max(indices)>=v or any(not math.isfinite(x) or abs(x)>10000 for a in verts for x in a): raise ValueError("vertex/index")
        actual_v+=v;actual_t+=i//3
        if not name.startswith((b"F50_GLASS_",b"EXT_GLASS_")):meshes.append((mat,verts,indices))
    if (actual_v,actual_t)!=(nv,nt):raise ValueError("totals")
    for _ in range(nm): _,pos=blob(b,pos)
    if b[pos:pos+8]!=b"OVCPBR3!":raise ValueError("PBR")
    pos+=8; start=pos; records=[]
    for _ in range(nm):
        begin=pos; factors=struct.unpack_from("<3f",b,pos);pos+=12
        if not all(map(math.isfinite,factors)) or not 0.0399<=factors[0]<=1 or not 0<=factors[1]<=1 or not 0<=factors[2]<=2:raise ValueError("factors")
        _,pos=blob(b,pos); normal_end=pos; orm,pos=blob(b,pos)
        records.append((begin,normal_end,pos,orm))
    return meshes,start,records,pos
def triangles(meshes):
    for mat,vs,ids in meshes:
        for i in range(0,len(ids),3):
            a,c,d=(vs[ids[i+j]] for j in range(3))
            p,q,r=(x[:3] for x in (a,c,d))
            geom=unit(cross(sub(q,p),sub(r,p)))
            if geom is None:continue
            normal=unit(add(add(a[3:6],c[3:6]),d[3:6])) or geom
            yield mat,p,q,r,normal,(a[6:8],c[6:8],d[6:8])
def ao_at(p,n,occupied,cell):
    # Six fixed hemisphere directions, bounded ray length. Start outside
    # the containing voxel to reduce self-occlusion from the sampled face.
    t=unit(cross(n,(1,0,0) if abs(n[0])<.8 else (0,1,0)))
    b=cross(n,t);hits=0
    px,py,pz=p
    for ca,sa in ((1.,0.),(.5,.8660254),(-.5,.8660254),(-1.,0.),(-.5,-.8660254),(.5,-.8660254)):
        dx,dy,dz=add(scale(n,.8),add(scale(t,.6*ca),scale(b,.6*sa)))
        for step in (1.5,2.5,3.5,4.5,5.5):
            if (math.floor(px+dx*step),math.floor(py+dy*step),math.floor(pz+dz*step)) in occupied:
                hits+=1;break
    return round(255*(1-.55*hits/6))
def dds(ao):
    w,h=ao.size; n=max(w,h).bit_length()
    # DDS_HEADER with uncompressed A8R8G8B8; full mip chain.
    header=[124,0x2100f,h,w,w*4,0,n]+[0]*11+[32,0x41,0,32,0x00ff0000,0x0000ff00,0x000000ff,0xff000000]+[0x401008,0,0,0,0]
    assert len(header)==31
    out=bytearray(b"DDS "+struct.pack("<31I",*header))
    while True:
        neutral=Image.new("L",ao.size,255)
        rgba=Image.merge("RGBA",(ao,neutral,neutral,neutral))
        out.extend(rgba.tobytes("raw","BGRA"))
        if ao.size==(1,1):break
        ao=ao.resize((max(1,ao.width//2),max(1,ao.height//2)),Image.Resampling.BOX)
    return bytes(out)
def bake(data,size=128):
    meshes,start,records,tail=parse(data)
    missing={i for i,r in enumerate(records) if not r[3]}
    tris=list(triangles(meshes))
    if not tris:raise ValueError("no opaque triangles")
    xyz=[p for _,a,b,c,_,_ in tris for p in (a,b,c)]
    lo=[min(p[k] for p in xyz) for k in range(3)]
    extent=max(max(p[k] for p in xyz)-lo[k] for k in range(3))
    if extent<=1e-6:raise ValueError("degenerate bounds")
    voxel=extent/48
    def normalized(p):return tuple((p[k]-lo[k])/voxel for k in range(3))
    def cell(p):return (math.floor(p[0]),math.floor(p[1]),math.floor(p[2]))
    occupied=set()
    norm_tris=[]
    for mat,a,b,c,n,uv in tris:
        a,b,c=map(normalized,(a,b,c))
        e,f=sub(b,a),sub(c,a)
        steps=min(48,max(1,math.ceil(max(math.sqrt(dot(e,e)),math.sqrt(dot(f,f)),math.sqrt(dot(sub(c,b),sub(c,b)))))))
        for i in range(steps+1):
            for j in range(steps+1-i):
                occupied.add(cell(add(a,add(scale(e,i/steps),scale(f,j/steps)))))
        norm_tris.append((mat,a,b,c,n,uv))
    atlases={}
    skipped=0
    for mat,a,b,c,n,uv in norm_tris:
        if mat not in missing:continue
        if abs((uv[1][0]-uv[0][0])*(uv[2][1]-uv[0][1])-(uv[1][1]-uv[0][1])*(uv[2][0]-uv[0][0]))<1e-10:
            skipped+=1;continue
        x0,x1=math.floor(min(p[0] for p in uv)),math.floor(max(p[0] for p in uv))
        y0,y1=math.floor(min(p[1] for p in uv)),math.floor(max(p[1] for p in uv))
        if x1-x0>4 or y1-y0>4:skipped+=1;continue
        if mat not in atlases:
            im=Image.new("L",(size,size),255);mask=Image.new("L",(size,size),0)
            atlases[mat]=(im,mask,ImageDraw.Draw(im),ImageDraw.Draw(mask))
        im,mask,draw,cover=atlases[mat]
        center=scale(add(add(a,b),c),1/3)
        shade=ao_at(center,n,occupied,cell)
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):
                poly=[((u-x)*size,(v-y)*size) for u,v in uv]
                draw.polygon(poly,fill=shade);cover.polygon(poly,fill=255)
    out=bytearray(data[:start]); report=[]
    for i,(begin,end,stop,orm) in enumerate(records):
        out.extend(data[begin:end])
        if orm:
            out.extend(data[end:stop]);continue
        if i not in atlases or not atlases[i][1].getbbox():
            out.extend(struct.pack("<I",0));continue
        im,mask,_,_=atlases[i]
        pixels=mask.histogram()[255]
        # Two-pixel UV island padding, leave remaining background neutral.
        for _ in range(2):
            expanded=mask.filter(ImageFilter.MaxFilter(3))
            ring=ImageChops.subtract(expanded,mask)
            im.paste(im.filter(ImageFilter.MinFilter(3)),mask=ring)
            mask=expanded
        packed=dds(im);out.extend(struct.pack("<I",len(packed)));out.extend(packed)
        report.append({"material":i,"covered_pixels":pixels,"ao_range":list(im.getextrema())})
    out.extend(data[tail:])
    if len(out)>128*1024**2:raise ValueError("output size")
    struct.pack_into("<II",out,28,len(out)-36,zlib.crc32(out[36:]))
    result=bytes(out)
    # Reparse and prove no mesh/albedo/normal/dashboard bytes changed.
    _,newstart,newrecords,newtail=parse(result)
    assert result[:28]==data[:28] and result[36:newstart]==data[36:start] and result[newtail:]==data[tail:]
    for (a,b,c,m),(x,y,z,k) in zip(records,newrecords):
        assert data[a:b]==result[x:y]
        if m:assert data[b:c]==result[y:z]
    return result,{"generated":len(report),"existing":len(records)-len(missing),"missing_after":len(missing)-len(report),"skipped_uv_triangles":skipped,"materials":report,"geometry_voxels":len(occupied)}
def verify_existing(source, output):
    _,a,old,end_a=parse(source); _,b,new,end_b=parse(output)
    if source[:28]!=output[:28] or source[36:a]!=output[36:b] or source[end_a:]!=output[end_b:] or len(old)!=len(new):
        raise ValueError("existing output geometry/albedo/tail mismatch")
    report=[]
    existing=missing=0
    for i,((x,y,z,orm),(p,q,r,packed)) in enumerate(zip(old,new)):
        if source[x:y]!=output[p:q] or (orm and source[y:z]!=output[q:r]):
            raise ValueError("existing output source material mismatch")
        if orm: existing+=1;continue
        if not packed:missing+=1;continue
        if packed[:4]!=b"DDS " or u32(packed,84)!=0 or u32(packed,88)!=32:
            raise ValueError("existing output unexpected DDS")
        width,height=u32(packed,16),u32(packed,12)
        if width!=height or width not in (64,128,256) or u32(packed,28)!=width.bit_length():
            raise ValueError("existing output mip shape")
        expected=128;dim=width
        while dim:
            expected+=dim*dim*4;dim//=2
        if expected!=len(packed) or any(v!=255 for offset in (0,1,3) for v in packed[128+offset::4]):
            raise ValueError("existing output neutral channels/size")
        pixels=packed[130:128+width*height*4:4]
        report.append({"material":i,"covered_pixels":None,"ao_range":[min(pixels),max(pixels)]})
    return {"generated":len(report),"existing":existing,"missing_after":missing,
        "skipped_uv_triangles":None,"materials":report,"geometry_voxels":None,
        "resumed_verified":True}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--size",type=int,choices=(64,128,256),default=128);ap.add_argument("--car",choices=sorted(CAR_IDS));ap.add_argument("--resume",action="store_true")
    args=ap.parse_args()
    if args.out.exists() and not args.resume:raise SystemExit("output directory must be new")
    args.out.mkdir(parents=True,exist_ok=args.resume)
    results=[]
    for name,id in CAR_IDS.items():
        if args.car and args.car!=name:continue
        paths=list((args.root/name).glob("*.ovc"))
        if len(paths)!=1:raise ValueError("ambiguous/missing source "+name)
        source=paths[0].read_bytes();target=args.out/("car_id_%02d.ovc"%id)
        if target.exists():
            if not args.resume:raise ValueError("output already exists")
            output=target.read_bytes();report=verify_existing(source,output)
        else:
            output,report=bake(source,args.size)
            temp=target.with_suffix(".ovc.part")
            temp.write_bytes(output);temp.replace(target)
        result={"car":name,"car_id":id,"input_sha256":sha(source),"output_sha256":sha(output),"bytes":len(output),**report}
        results.append(result)
        print(name,"ORM",report["generated"],"unresolved",report["missing_after"],flush=True)
        partial=args.out/"geometry_orm_progress.json"
        temp=partial.with_suffix(".json.part")
        temp.write_text(json.dumps(results,indent=2)+"\n");temp.replace(partial)
    manifest={"method":"GEOMETRY_VOXEL_AO_APPROXIMATION","size":args.size,"roughness_metallic":"AUTHORED_SCALAR_FACTORS_NEUTRAL_MAP_MULTIPLIERS","source_quality":"NOT_PROMOTED","cars":results}
    (args.out/"geometry_orm_report.json").write_text(json.dumps(manifest,indent=2)+"\n")
if __name__=="__main__":main()

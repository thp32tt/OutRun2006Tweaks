#!/usr/bin/env python3
"""Offline geometry-derived UV generation for untextured OVC3/4 material groups.
Only uniform ARGB albedo, no authored PBR maps and entirely absent UV qualify.
Preserve indexed source corner positions/normals and material/dashboard bytes.
Usage: python3 this.py src.ovc dst.ovc
This deliberately uses disjoint per-triangle charts, not authored texture UVs.
"""
import hashlib,json,math,pathlib,struct,sys,zlib
from collections import defaultdict
HEAD=struct.Struct("<8s7I")
GROUP=struct.Struct("<HHIII")
VERT=struct.Struct("<8f")
UV=struct.Struct("<2f")
def paired_charts(entries, groups):
    """Pair adjacent consistently wound, nearly planar triangles without overlap.
    Use exact shared vertex indices; leave seams, curved and unmatched faces separate.
    Each chart occupies one disjoint tile; all original corner bytes are preserved.
    """
    from math import sqrt
    def sub(a,b):return tuple(x-y for x,y in zip(a,b))
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    def unit(a):
        l=sqrt(dot(a,a))
        return tuple(x/l for x in a) if l>1e-15 else None
    vertices={i:list(VERT.iter_unpack(groups[i]["vb"])) for i in {e[0] for e in entries}}
    edge_map={}
    faces={}
    for gi,t,coords in entries:
        ids=groups[gi]["idx"][t:t+3]
        faces[gi,t]=(ids,coords)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            key=(gi,min(a,b),max(a,b))
            edge_map.setdefault(key,[]).append(t)
    done=set()
    charts=[]
    for gi,t,coords in entries:
        if (gi,t) in done:continue
        ids,_=faces[gi,t]
        v=vertices[gi]
        normal=unit(cross(sub(v[ids[1]][:3],v[ids[0]][:3]),sub(v[ids[2]][:3],v[ids[0]][:3])))
        paired=False
        if normal is not None:
            for a,b in zip(ids,ids[1:]+ids[:1]):
                neighbors=edge_map[gi,min(a,b),max(a,b)]
                if len(neighbors)!=2:continue
                other=neighbors[0] if neighbors[1]==t else neighbors[1]
                if other==t or (gi,other) in done:continue
                ids2,_=faces[gi,other]
                if len(set(ids+ids2))!=4:continue
                if not any(x==b and y==a for x,y in zip(ids2,ids2[1:]+ids2[:1])):continue
                normal2=unit(cross(sub(v[ids2[1]][:3],v[ids2[0]][:3]),sub(v[ids2[2]][:3],v[ids2[0]][:3])))
                if normal2 is None or dot(normal,normal2)<.995:continue
                origin=v[a][:3];axis=unit(sub(v[b][:3],origin))
                if axis is None:continue
                vertical=cross(normal,axis)
                points={}
                for i in set(ids+ids2):
                    delta=sub(v[i][:3],origin)
                    points[i]=(dot(delta,axis),dot(delta,vertical))
                third=next(i for i in ids if i not in (a,b))
                third2=next(i for i in ids2 if i not in (a,b))
                # Opposite halfplanes prove no projected interior overlap.
                if points[third][1]*points[third2][1]>=-1e-24:continue
                lo=[min(x[k] for x in points.values()) for k in range(2)]
                span=[max(x[k] for x in points.values())-lo[k] for k in range(2)]
                scale=max(span)
                if scale<=1e-15:continue
                uv={i:tuple((p[k]-lo[k])/scale for k in range(2)) for i,p in points.items()}
                charts.append([(gi,t,[uv[i] for i in ids]),(gi,other,[uv[i] for i in ids2])])
                done.update(((gi,t),(gi,other)));paired=True;break
        if not paired:
            charts.append([(gi,t,coords)]);done.add((gi,t))
    return charts

def planar_patches(entries,groups):
    """Grow bounded, connected, nonoverlapping charts in one local plane.
    An edge must be shared with reverse winding. Every accepted face has
    compatible orientation and disjoint projected interior. Retain seams.
    """
    def sub(a,b):return tuple(x-y for x,y in zip(a,b))
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    def unit(a):
        length=math.sqrt(dot(a,a))
        return tuple(x/length for x in a) if length>1e-15 else None
    def interior_overlap(a,b):
        # Separating-axis theorem, touching edges/vertices are allowed.
        for tri in (a,b):
            for p,q in zip(tri,tri[1:]+tri[:1]):
                axis=(p[1]-q[1],q[0]-p[0])
                x=[dot(v,axis) for v in a];y=[dot(v,axis) for v in b]
                if min(max(x),max(y))-max(min(x),min(y))<=1e-12*max(max(x)-min(x),max(y)-min(y),1e-30):
                    return False
        return True
    vertices={i:list(VERT.iter_unpack(groups[i]["vb"])) for i in {e[0] for e in entries}}
    faces={};edges=defaultdict(list)
    for gi,t,coords in entries:
        ids=groups[gi]["idx"][t:t+3];v=vertices[gi]
        n=unit(cross(sub(v[ids[1]][:3],v[ids[0]][:3]),sub(v[ids[2]][:3],v[ids[0]][:3])))
        faces[gi,t]=(ids,coords,n)
        for a,b in zip(ids,ids[1:]+ids[:1]):edges[gi,min(a,b),max(a,b)].append((t,a,b))
    done=set();charts=[]
    for gi,t,coords in entries:
        if (gi,t) in done:continue
        ids,_,normal=faces[gi,t];v=vertices[gi]
        if normal is None:
            charts.append([(gi,t,coords)]);done.add((gi,t));continue
        origin=v[ids[0]][:3]
        axis=unit(sub(v[ids[1]][:3],origin))
        if axis is None:
            charts.append([(gi,t,coords)]);done.add((gi,t));continue
        vertical=cross(normal,axis)
        def project(i):
            d=sub(v[i][:3],origin);return (dot(d,axis),dot(d,vertical))
        accepted=[t];polys=[[project(i) for i in ids]]
        done.add((gi,t));cursor=0
        while cursor<len(accepted) and len(accepted)<8:
            face=accepted[cursor];cursor+=1
            boundary=faces[gi,face][0]
            for a,b in zip(boundary,boundary[1:]+boundary[:1]):
                if len(accepted)>=8:break
                neighbors=edges[gi,min(a,b),max(a,b)]
                if len(neighbors)!=2:continue
                other,oa,ob=neighbors[0] if neighbors[1][0]==face else neighbors[1]
                if (gi,other) in done or oa!=b or ob!=a:continue
                ids2,_,n2=faces[gi,other]
                if n2 is None or dot(normal,n2)<.995:continue
                poly=[project(i) for i in ids2]
                e=sub(poly[1],poly[0]);h=sub(poly[2],poly[0])
                if e[0]*h[1]-e[1]*h[0]<=1e-24:continue
                if any(interior_overlap(poly,old) for old in polys):continue
                accepted.append(other);polys.append(poly);done.add((gi,other))
        points=[p for poly in polys for p in poly]
        lo=[min(p[k] for p in points) for k in range(2)]
        scale=max(max(p[k] for p in points)-lo[k] for k in range(2))
        charts.append([(gi,face,[tuple((p[k]-lo[k])/scale for k in range(2)) for p in poly])
                       for face,poly in zip(accepted,polys)])
    return charts

def main(src,dst,mode="triangle"):
    if mode not in ("triangle","paired","patch"):raise ValueError("mode must be triangle, paired or patch")
    src,dst=pathlib.Path(src),pathlib.Path(dst)
    raw=src.read_bytes()
    magic,version,ng,nm,nv,nt,size,crc=HEAD.unpack_from(raw)
    if (magic,version) not in ((b"OVRCABH3",3),(b"OVRCABH4",4)) or size!=len(raw)-36 or zlib.crc32(raw[36:])!=crc:
        raise ValueError("source envelope")
    if not (0<ng<=512 and 0<nm<=128 and nv<=1000000 and nt<=2000000) or dst.exists() or len(raw)>128*1024*1024:
        raise ValueError("source counts or output exists")
    p=36;groups=[];opaque=defaultdict(list);glass=set()
    for i in range(ng):
        nlen,mat,n,ic,w=GROUP.unpack_from(raw,p);p+=16
        name=raw[p:p+nlen];p+=nlen
        vb=raw[p:p+n*32];p+=n*32
        ib=raw[p:p+ic*w];p+=ic*w
        if mat>=nm or not nlen or len(vb)!=n*32 or len(ib)!=ic*w or w not in (2,4) or not ic or ic%3 or not n:
            raise ValueError("group bounds")
        idx=[v[0] for v in struct.iter_unpack("<H" if w==2 else "<I",ib)]
        if max(idx)>=n:raise ValueError("indices")
        groups.append(dict(name=name,mat=mat,n=n,ic=ic,w=w,vb=vb,ib=ib,idx=idx))
        if name.startswith((b"F50_GLASS_",b"EXT_GLASS_")):glass.add(mat)
        else:opaque[mat].append(i)
    if sum(g["n"] for g in groups)!=nv or sum(g["ic"]//3 for g in groups)!=nt:raise ValueError("source totals")
    tail=p;eligible=[]
    for mat in range(nm):
        n=struct.unpack_from("<I",raw,p)[0];p+=4
        dds=raw[p:p+n];p+=n
        if mat not in opaque or mat in glass:continue
        if len(dds)<132 or dds[:4]!=b"DDS " or struct.unpack_from("<6I",dds,84)!=(0,32,0xff0000,0xff00,0xff,0xff000000) or len(dds[128:])%4 or dds[128:]!=dds[128:132]*((len(dds)-128)//4):continue
        if all(all(v[6]==0 and v[7]==0 for v in VERT.iter_unpack(groups[i]["vb"])) for i in opaque[mat]):eligible.append(mat)
    if raw[p:p+8]!=b"OVCPBR3!":raise ValueError("PBR magic")
    p+=8
    for mat in range(nm):
        p+=12
        for _ in range(2):
            n=struct.unpack_from("<I",raw,p)[0];p+=4+n
            if n and mat in eligible:eligible.remove(mat)
    if not eligible:raise ValueError("no eligible untextured material")
    report=[]
    for mat in eligible:
        # Each nondegenerate source triangle owns its own padded atlas tile.
        # Project in its geometric plane, selecting the longest edge for
        # numerical stability. No source texture coordinates are overwritten
        # and no overlap between unrelated faces can corrupt generated AO.
        # This is a diagnostic UV atlas, not a production hand-authored unwrap.
        entries=[];degenerate=0
        for gi in opaque[mat]:
            g=groups[gi];verts=list(VERT.iter_unpack(g["vb"]))
            for t in range(0,g["ic"],3):
                p=[verts[i][:3] for i in g["idx"][t:t+3]]
                edges=[sum((p[(i+1)%3][k]-p[i][k])**2 for k in range(3)) for i in range(3)]
                i=max(range(3),key=edges.__getitem__);j=(i+1)%3;k=(i+2)%3
                length=math.sqrt(edges[i])
                if length<=1e-15:degenerate+=1;continue
                e=[(p[j][axis]-p[i][axis])/length for axis in range(3)]
                q=[p[k][axis]-p[i][axis] for axis in range(3)]
                x=sum(a*b for a,b in zip(e,q))
                h=math.sqrt(sum((q[axis]-e[axis]*x)**2 for axis in range(3)))
                if h<=1e-15:degenerate+=1;continue
                # Longest edge gives x in [0,length] and h <= length.
                # Keep true triangle aspect and leave a 12.5% gutter.
                coords=[None]*3
                coords[i]=(0.,0.);coords[j]=(1.,0.);coords[k]=(x/length,h/length)
                entries.append((gi,t,coords))
        if not entries:continue
        # Retain the same face-count grid as the original triangle atlas.
        # This lets the baker independently reconstruct and validate tile ownership.
        tiles=math.ceil(math.sqrt(len(entries)))
        charts=planar_patches(entries,groups) if mode=="patch" else paired_charts(entries,groups) if mode=="paired" else [[e] for e in entries]
        pergroup=defaultdict(dict);valid=invalid=0
        for ordinal,chart in enumerate(charts):
            row,col=divmod(ordinal,tiles)
            for gi,t,coords in chart:
                uv=[UV.pack((col+.125+.75*u)/tiles,(row+.125+.75*v)/tiles) for u,v in coords]
                a,b,c=[UV.unpack(x) for x in uv];det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                if det:valid+=1
                else:invalid+=1
                pergroup[gi][t]=uv
        if invalid:raise ValueError("projected UV collapsed")
        for gi in opaque[mat]:
            g=groups[gi];old=g["vb"];out=[old[i*32:(i+1)*32] for i in range(g["n"])]
            remap={};first=set();newidx=[]
            for t in range(0,g["ic"],3):
                coords=pergroup[gi].get(t,[b"\0"*8]*3)
                for orig,packed in zip(g["idx"][t:t+3],coords):
                    key=(orig,packed)
                    if key not in remap:
                        dest=orig if orig not in first else len(out);first.add(orig)
                        value=old[orig*32:orig*32+24]+packed
                        if dest==len(out):out.append(value)
                        else:out[dest]=value
                        remap[key]=dest
                    newidx.append(remap[key])
            vb=b"".join(out)
            if len(newidx)!=len(g["idx"]):raise ValueError("corner count")
            for i,orig in enumerate(g["idx"]):
                dest=newidx[i]
                if vb[dest*32:dest*32+24]!=old[orig*32:orig*32+24]:raise ValueError("corner position/normal")
            width=4 if g["w"]==4 or len(out)>65535 else 2
            fmt=struct.Struct("<I" if width==4 else "<H")
            g.update(n=len(out),vb=vb,w=width,ib=b"".join(fmt.pack(v) for v in newidx))
        report.append(dict(material=mat,valid_uv_triangles=valid,collapsed_nondegenerate_triangles=invalid,source_zero_area_triangles=degenerate,atlas_tiles_per_axis=tiles,charts=len(charts),paired_charts=sum(len(c)==2 for c in charts),max_chart_faces=max(map(len,charts))))
        print("UV_MATERIAL",mat,valid,invalid,flush=True)
    vertices=sum(g["n"] for g in groups)
    body=b"".join(GROUP.pack(len(g["name"]),g["mat"],g["n"],g["ic"],g["w"])+g["name"]+g["vb"]+g["ib"] for g in groups)+raw[tail:]
    if vertices>1000000 or len(body)>112*1024*1024-36 or not report:raise ValueError("output budget or no charts")
    output=HEAD.pack(magic,version,ng,nm,vertices,nt,len(body),zlib.crc32(body))+body
    tmp=dst.with_suffix(dst.suffix+".part")
    if tmp.exists():raise ValueError("temporary exists")
    tmp.write_bytes(output);tmp.replace(dst)
    details=dict(source_sha256=hashlib.sha256(raw).hexdigest(),output_sha256=hashlib.sha256(output).hexdigest(),groups=ng,materials=nm,triangles=nt,source_vertices=nv,output_vertices=vertices,generated_uv_materials=len(report),materials_detail=report,source_geometry_corner_bytes_preserved=True,material_tail_preserved=True,authored_uv=False,chart_method="connected_planar_patches" if mode=="patch" else "paired_nearplanar_geometric_projection" if mode=="paired" else "per_triangle_geometric_projection",release_install=False)
    dst.with_suffix(dst.suffix+".json").write_text(json.dumps(details,indent=2)+"\n")
    print("UV_REBUILD",json.dumps(details),flush=True)
if __name__=="__main__":
    main(*sys.argv[1:])

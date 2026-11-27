#!/usr/bin/env python3
"""Offline Blender UV generation for untextured OVC3/4 material groups.
Only uniform ARGB albedo, no authored PBR maps and entirely absent UV qualify.
Preserve indexed source corner positions/normals and material/dashboard bytes.
Usage: blender -b -t 2 --python-exit-code 1 --python this.py -- src.ovc dst.ovc
"""
import bpy,hashlib,json,math,pathlib,struct,sys,zlib
from collections import defaultdict
HEAD=struct.Struct("<8s7I")
GROUP=struct.Struct("<HHIII")
VERT=struct.Struct("<8f")
UV=struct.Struct("<2f")
def main(src,dst):
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
        positions=[];faces=[];meta=[]
        for gi in opaque[mat]:
            g=groups[gi];base=len(positions);positions.extend(v[:3] for v in VERT.iter_unpack(g["vb"]))
            seen=set()
            for t in range(0,g["ic"],3):
                a,b,c=g["idx"][t:t+3]
                pa,pb,pc=(positions[base+i] for i in (a,b,c))
                u=[pb[k]-pa[k] for k in range(3)];v=[pc[k]-pa[k] for k in range(3)]
                cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
                # Preserve zero-area source triangles unchanged; they do not rasterize.
                if sum(x*x for x in cross)<=1e-30:continue
                key=tuple(sorted((a,b,c)))
                face=tuple(base+i for i in (a,b,c))
                if key in seen:
                    # BMesh may remove duplicate faces; keep each as a separate chart.
                    start=len(positions);positions.extend((pa,pb,pc));face=(start,start+1,start+2)
                seen.add(key);faces.append(face);meta.append((gi,t,(a,b,c)))
        if not faces:continue
        # Blender's island packing can become quadratic on fragmented 60k+
        # triangle materials. Unwrap bounded chunks, place them in disjoint
        # padded tiles, and never decimate or discard the source geometry.
        max_faces=2048
        chunk_count=(len(faces)+max_faces-1)//max_faces
        tiles=math.ceil(math.sqrt(chunk_count))
        pergroup=defaultdict(dict);valid=invalid=0
        for chunk,start in enumerate(range(0,len(faces),max_faces)):
            end=min(start+max_faces,len(faces))
            local_positions=[];local_map={};local_faces=[]
            for face in faces[start:end]:
                local=[]
                for vi in face:
                    if vi not in local_map:
                        local_map[vi]=len(local_positions);local_positions.append(positions[vi])
                    local.append(local_map[vi])
                local_faces.append(tuple(local))
            mesh=bpy.data.meshes.new("uv_material");mesh.from_pydata(local_positions,[],local_faces);mesh.update()
            attr=mesh.attributes.new("source_face","INT","FACE")
            for i,item in enumerate(attr.data):item.value=i
            obj=bpy.data.objects.new("uv_material",mesh);bpy.context.collection.objects.link(obj)
            bpy.ops.object.select_all(action="DESELECT");obj.select_set(True);bpy.context.view_layer.objects.active=obj
            bpy.ops.object.mode_set(mode="EDIT");bpy.ops.mesh.select_all(action="SELECT")
            result=bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.002)
            bpy.ops.object.mode_set(mode="OBJECT")
            if "FINISHED" not in result or not mesh.uv_layers.active or len(mesh.polygons)!=len(local_faces):raise ValueError("unwrap face count")
            ids=mesh.attributes["source_face"].data;uv=mesh.uv_layers.active.data
            row,col=divmod(chunk,tiles)
            for poly in mesh.polygons:
                i=ids[poly.index].value
                if i<0 or i>=len(local_faces):raise ValueError("face id")
                gi,t,orig=meta[start+i]
                loops=list(poly.loop_indices)
                expected=local_faces[i]
                if len(loops)!=3:raise ValueError("triangle shape")
                coords=[None]*3
                for li in loops:
                    vi=mesh.loops[li].vertex_index
                    if vi not in expected:raise ValueError("face topology changed")
                    u,v=map(float,uv[li].uv)
                    if not all(math.isfinite(x) and -.001<=x<=1.001 for x in (u,v)):raise ValueError("UV range")
                    # Per-chunk tile padding prevents cross-chunk overlap.
                    u=(col+.003+.994*min(1.,max(0.,u)))/tiles
                    v=(row+.003+.994*min(1.,max(0.,1.-v)))/tiles
                    coords[expected.index(vi)]=UV.pack(u,v)
                if any(x is None for x in coords) or t in pergroup[gi]:raise ValueError("face mapping")
                pergroup[gi][t]=coords
                a,b,c=[UV.unpack(x) for x in coords];det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                if abs(det)>1e-12:valid+=1
                else:invalid+=1
            bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
        if sum(len(v) for v in pergroup.values())!=len(meta):raise ValueError("lost chart face")
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
        report.append(dict(material=mat,valid_uv_triangles=valid,collapsed_nondegenerate_triangles=invalid,source_zero_area_triangles=sum(groups[i]["ic"]//3 for i in opaque[mat])-len(meta)))
        print("UV_MATERIAL",mat,valid,invalid,flush=True)
    vertices=sum(g["n"] for g in groups)
    body=b"".join(GROUP.pack(len(g["name"]),g["mat"],g["n"],g["ic"],g["w"])+g["name"]+g["vb"]+g["ib"] for g in groups)+raw[tail:]
    if vertices>1000000 or len(body)>112*1024*1024-36 or not report:raise ValueError("output budget or no charts")
    output=HEAD.pack(magic,version,ng,nm,vertices,nt,len(body),zlib.crc32(body))+body
    tmp=dst.with_suffix(dst.suffix+".part")
    if tmp.exists():raise ValueError("temporary exists")
    tmp.write_bytes(output);tmp.replace(dst)
    details=dict(source_sha256=hashlib.sha256(raw).hexdigest(),output_sha256=hashlib.sha256(output).hexdigest(),groups=ng,materials=nm,triangles=nt,source_vertices=nv,output_vertices=vertices,generated_uv_materials=len(report),materials_detail=report,source_geometry_corner_bytes_preserved=True,material_tail_preserved=True,authored_uv=False,release_install=False)
    dst.with_suffix(dst.suffix+".json").write_text(json.dumps(details,indent=2)+"\n")
    print("UV_REBUILD",json.dumps(details),flush=True)
if __name__=="__main__":
    main(*sys.argv[sys.argv.index("--")+1:])

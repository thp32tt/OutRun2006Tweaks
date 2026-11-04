#!/usr/bin/env python3
"""Experimental OutRun 2006 Dino cockpit v12 PMT add-on. User-owned original only.
Create a model-only payload from the CABIN_ nodes of the v12 GLB, then
reversibly install it into an *exactly verified* original Cars PMT.
Python 3 standard library only; no executable/DLL/hook changes.
"""
import argparse,hashlib,json,math,os,pathlib,struct,sys,tempfile,zlib

ORIGINAL_SHA="1f8dfcb7b875d46bd58f110518c1a8815355162d4412fa4a0d4e2e2301d86284"
GAME_REL=pathlib.Path("Cars/obj_plcar_dino_pmt.sz")
MAGIC=b"DINO_CABIN_V12\x00\x00"
FORMAT="<8f"
def sha(data): return hashlib.sha256(data).hexdigest()
def u(b,o): return struct.unpack_from("<I",b,o)[0]
def packu(*a): return struct.pack("<%dI"%len(a),*a)
def model_only(glb,out):
    b=pathlib.Path(glb).read_bytes()
    assert b[:4]==b"glTF" and u(b,4)==2 and u(b,8)==len(b),"GLB header invalid"
    jlen=u(b,12);assert b[16:20]==b"JSON"
    d=json.loads(b[20:20+jlen]);p=20+jlen
    assert b[p+4:p+8]==b"BIN\x00"
    raw=b[p+8:p+8+u(b,p)]
    def accessor(ai):
        a=d["accessors"][ai];v=d["bufferViews"][a["bufferView"]]
        ct=a["componentType"];ts=a["type"];n={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}[ts]
        typ={5121:"B",5123:"H",5125:"I",5126:"f"}[ct];size=struct.calcsize("<"+str(n)+typ)
        stride=v.get("byteStride",size);assert stride>=size and not a.get("sparse")
        start=v.get("byteOffset",0)+a.get("byteOffset",0)
        assert start+(a["count"]-1)*stride+size<=len(raw),"GLB accessor out of range"
        return [struct.unpack_from("<"+str(n)+typ,raw,start+i*stride) for i in range(a["count"])]
    groups=[]
    for node in d["nodes"]:
        if not node.get("name","").startswith("CABIN_"):continue
        if any(k in node for k in ("matrix","translation","rotation","scale","skin")):raise ValueError("Unexpected transformed cabin node")
        for pr in d["meshes"][node["mesh"]]["primitives"]:
            assert pr.get("mode",4)==4
            a=pr["attributes"];P=accessor(a["POSITION"]);N=accessor(a["NORMAL"]);UV=accessor(a["TEXCOORD_0"])
            indices=[int(x[0]) for x in accessor(pr["indices"])]
            assert len(indices)%3==0 and len(P)==len(N)==len(UV) and max(indices)<len(P)
            mat=d["materials"][pr["material"]];name=mat.get("name","CABIN")
            assert name.startswith("CABIN_")
            color=mat.get("pbrMetallicRoughness",{}).get("baseColorFactor",[0.5,0.4,0.3,1])
            assert len(color)==4 and all(math.isfinite(x) and 0<=x<=1 for x in color)
            # Preserve model winding and game-space coordinates. Game textures
            # are intentionally not distributed; colors are approximated.
            vertices=[tuple(float(x) for x in P[i]+N[i]+UV[i]) for i in range(len(P))]
            assert all(math.isfinite(x) and abs(x)<10000 for v in vertices for x in v)
            groups.append((name,color,vertices,indices))
    assert len(groups)>=20 and sum(len(g[3]) for g in groups)//3==17506
    assert sum(len(g[2]) for g in groups)<65535
    body=bytearray(packu(len(groups)))
    for name,col,verts,idx in groups:
        name=name.encode("utf-8");assert len(name)<255
        body+=struct.pack("<B",len(name))+name+struct.pack("<4f2I",*col,len(verts),len(idx))
        for v in verts:body+=struct.pack(FORMAT,*v)
        body+=struct.pack("<%dH"%len(idx),*idx)
    encoded=MAGIC+zlib.compress(body,9)
    pathlib.Path(out).write_bytes(encoded)
    return {"status":"MODEL_ONLY_EXPORTED","groups":len(groups),"triangles":sum(len(g[3])//3 for g in groups),"vertices":sum(len(g[2]) for g in groups),"sha256":sha(encoded),"bytes":len(encoded)}
def parse_payload(path):
    encoded=pathlib.Path(path).read_bytes()
    assert encoded[:len(MAGIC)]==MAGIC,"Unknown cockpit payload version"
    b=zlib.decompress(encoded[len(MAGIC):]);groups=[];o=0;cnt=u(b,o);o+=4
    assert 20<=cnt<=100
    for _ in range(cnt):
        n=b[o];o+=1;name=b[o:o+n].decode("utf-8");o+=n
        col=struct.unpack_from("<4f",b,o);o+=16
        vc,ic=struct.unpack_from("<2I",b,o);o+=8
        assert name.startswith("CABIN_") and 0<vc<=40000 and 0<ic<=150000 and ic%3==0
        vertices=b[o:o+vc*32];o+=vc*32
        indices=struct.unpack_from("<%dH"%ic,b,o);o+=ic*2
        assert len(vertices)==vc*32 and max(indices)<vc
        groups.append((name,col,vertices,indices,vc))
    assert o==len(b)
    assert sum(len(g[3]) for g in groups)//3==17506
    return groups
def build_pmt(original,payload):
    if sha(original)!=ORIGINAL_SHA:raise ValueError("Original PMT SHA256 mismatch; no change made")
    r=zlib.decompress(original);n,t,ss,vs=struct.unpack_from("<4I",r)
    assert n==17 and 16+ss+vs==len(r)
    S0=bytearray(r[16:16+ss]);V0=r[16+ss:];S=bytearray(S0);V=bytearray(V0)
    q=[u(S,24+i*4) for i in range(15)]
    h=[u(S,q[5]+i*4) for i in range(13)]
    assert q[5]==q[6] and h[9:13]==[2,34,34,21] and (q[10]-q[9])%20==0
    ng=len(payload);orig_prims=max(u(S,q[10]+i*32+8)+u(S,q[10]+i*32+12) for i in range(h[10]))
    assert orig_prims>0 and ng<=80
    def put(dat):
        while len(S)%4:S.append(0)
        p=len(S);S.extend(dat);return p
    # Exactly one additional GPU vertex/index format; all cabin material groups
    # share it. Preserve preexisting vertex GPU bytes and all 16 other objects.
    vertices=bytearray();indices=[];matgroups=[];prims=[];materials=[];colors=[]
    for name,col,vbytes,local_idx,vc in payload:
        base_v=len(vertices)//32;start_idx=len(indices)
        assert base_v+vc<=65535 and all(base_v+i<=65535 for i in local_idx)
        vertices+=vbytes
        indices.extend(base_v+i for i in local_idx)
        new_mat=h[11]+len(materials)
        new_prim=orig_prims+len(prims)
        first=list(struct.unpack_from("<8f",vbytes,0))
        xs=[];ys=[];zs=[]
        for off in range(0,len(vbytes),32):
            x,y,z=struct.unpack_from("<3f",vbytes,off)
            xs.append(x);ys.append(y);zs.append(z)
        cx=(max(xs)+min(xs))/2;cy=(max(ys)+min(ys))/2;cz=(max(zs)+min(zs))/2
        radius=math.sqrt((max(xs)-cx)**2+(max(ys)-cy)**2+(max(zs)-cz)**2)+.001
        matgroups.append(struct.pack("<4I4f",0,new_mat,new_prim,1,cx,cy,cz,radius))
        prims.append(struct.pack("<4I",5,start_idx,len(local_idx)//3,len(local_idx)//3))
        mt=bytearray(S0[q[13]+18*88:q[13]+19*88])
        assert [struct.unpack_from("<i",mt,24+20*j)[0] for j in range(4)]==[-1]*4
        struct.pack_into("<I",mt,0,h[12]+len(colors));materials.append(mt)
        co=bytearray(S0[q[14]+18*72:q[14]+19*72])
        # Tinted untextured original game material, physically distinguishable
        # leather, black dashboard, chrome, dials, stitching and controls.
        rgba=[max(0.025,min(1.,float(x))) for x in col];rgba[3]=1.
        struct.pack_into("<4f",co,0,*rgba)
        struct.pack_into("<4f",co,16,*(v*.6 for v in rgba[:3]),1.0)
        colors.append(co)
    ib=struct.pack("<%dH"%len(indices),*indices)
    ioff=put(ib);voff=len(V);V+=vertices
    ibdesc=bytearray(S0[u(S0,q[1]):u(S0,q[1])+12]);struct.pack_into("<I",ibdesc,4,ioff);ip=put(ibdesc)
    vbdesc=bytearray(S0[u(S0,q[2]+16):u(S0,q[2]+16)+12]);struct.pack_into("<I",vbdesc,4,voff);vp=put(vbdesc)
    p1=put(S0[q[1]:q[1]+h[9]*4]+packu(ip))
    p2=put(S0[q[2]:q[2]+h[9]*16]+packu(vp,0,0,0))
    old_vgs=(q[10]-q[9])//20
    p9=put(S0[q[9]:q[10]]+packu(h[9],h[10],0,ng,0))
    p10=put(S0[q[10]:q[10]+h[10]*32]+b"".join(matgroups))
    p11=put(S0[q[11]:q[11]+orig_prims*16]+b"".join(prims))
    fmt=bytearray(S0[q[12]+44:q[12]+88])
    struct.pack_into("<5I",fmt,24,len(ib),len(vertices),0x112,32,0)
    p12=put(S0[q[12]:q[12]+h[9]*44]+fmt)
    p13=put(S0[q[13]:q[13]+h[11]*88]+b"".join(materials))
    p14=put(S0[q[14]:q[14]+h[12]*72]+b"".join(colors))
    nq=q[:];nq[1]=p1;nq[2]=p2;nq[9:15]=[p9,p10,p11,p12,p13,p14]
    nh=h[:];nh[9:13]=[h[9]+1,h[10]+ng,h[11]+ng,h[12]+ng]
    for j,k in enumerate((0,2,3,4,5,6,7,8)):nh[k]=nq[7+j]
    nq[5]=put(packu(*nh));nq[6]=nq[5]
    struct.pack_into("<15I",S,24,*nq)
    assert S[24+60:len(S0)]==S0[24+60:] and V[:len(V0)]==V0
    assert (len(S)-len(S0))<250000 and (len(V)-len(V0))<1000000
    assert (nq[10]-nq[9])//20==old_vgs+1
    assert u(S,nq[12]+h[9]*44+32)==0x112
    for i in range(ng):
        mg=nq[10]+(h[10]+i)*32
        fmtindex=u(S,nq[9]+old_vgs*20)
        assert fmtindex==2 and u(S,mg+4)==h[11]+i
        assert u(S,nq[11]+(orig_prims+i)*16)==5
    encoded=zlib.compress(struct.pack("<4I",n,t,len(S),len(V))+S+V,9)
    assert zlib.decompress(encoded)[16:16+len(S0)]!=S0
    return encoded,{"original_sha256":sha(original),"patched_sha256":sha(encoded),"original_bytes":len(original),"patched_bytes":len(encoded),"object0_formats":nh[9],"object0_materials":nh[11],"material_groups_added":ng,"triangles_added":len(indices)//3,"vertices_added":len(vertices)//32,"existing_all_other_objects_byte_preserved":True,"game_runtime":"UNTESTED"}
def atomic(p,data):
    p=pathlib.Path(p)
    f=tempfile.NamedTemporaryFile(dir=p.parent,prefix=".dino-v12-",delete=False)
    try:
        with f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(f.name,p)
    finally:
        if os.path.exists(f.name):os.unlink(f.name)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=["export","install","restore","validate"])
    p.add_argument("--glb")
    p.add_argument("--payload",default="Dino246_CabinOnly_v12.dcm")
    p.add_argument("--game",default=".")
    p.add_argument("--source")
    a=p.parse_args()
    if a.action=="export":
        assert a.glb
        print(json.dumps(model_only(a.glb,a.payload),indent=2));return
    path=pathlib.Path(a.source) if a.source else pathlib.Path(a.game)/GAME_REL
    backup=path.with_suffix(path.suffix+".dino-v12-original.bak")
    if a.action=="restore":
        if not backup.exists():raise FileNotFoundError("Original backup missing")
        data=backup.read_bytes()
        if sha(data)!=ORIGINAL_SHA:raise ValueError("Backup original hash mismatch")
        if not path.is_file():raise FileNotFoundError("Target missing; refusing restore overwrite")
        atomic(path,data);print("RESTORED original SHA256",sha(data));return
    original=path.read_bytes()
    if a.action=="validate":
        patched,info=build_pmt(original,parse_payload(a.payload))
        print(json.dumps(info,indent=2));return
    if backup.exists():raise FileExistsError("Backup already exists; restore or remove old mod explicitly")
    patched,info=build_pmt(original,parse_payload(a.payload))
    # Refuse hardlinks: the game original must remain unique and recoverable.
    if path.stat().st_nlink!=1:raise ValueError("Hardlinked original refused")
    with backup.open("xb") as f:f.write(original);f.flush();os.fsync(f.fileno())
    try:atomic(path,patched)
    except BaseException:
        atomic(path,original);raise
    print(json.dumps(info,indent=2))
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("FAILED, file unchanged if hash/validation rejected:",str(exc),file=sys.stderr)
        sys.exit(2)
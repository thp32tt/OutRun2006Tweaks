#!/usr/bin/env python3
"""V15 Dino cockpit test installer using the previously reviewed v13 PMT serializer."""
import os,sys,json,hashlib,struct,zlib,pathlib,math
PAYLOAD_SHA="3ea734229c9e0745d103e854ce949e5e24289a52987773712601837f591de282"
MODEL_SHA="92b6bc2eab00daffd9269323660937d1160efc379ec019f18fbe163c05509a48"
MANIFEST_SHA="04fb781657c42273bae8a3e18f9d5682dfbdb86d62b32defef76eb8c851b4a41"
MAGIC=b"DINO_V15_LHD_L1\x00"
V13_SHA="83199d4f62519d8c0d77ed9944926d279832a1f9ee78cf04963d6218211e15ad"
def sha(b):return hashlib.sha256(b).hexdigest()
def model_payload(path):
    b=pathlib.Path(path).read_bytes()
    if sha(b)!=PAYLOAD_SHA or not b.startswith(MAGIC):raise ValueError("V15 model SHA/magic mismatch")
    ng,nv,nt=struct.unpack_from("<III",b,len(MAGIC))
    if (ng,nv,nt)!=(70,21100,38992):raise ValueError("V15 model primitive count mismatch")
    p=zlib.decompress(b[len(MAGIC)+12:]);g=[];o=0
    for _ in range(ng):
        if o+12>len(p):raise ValueError("Truncated V15 payload")
        n,mat,vc,ic=struct.unpack_from("<HHII",p,o);o+=12
        if not(0<n<=255 and 0<=mat<19 and 3<=vc<=10000 and 3<=ic<=40000 and ic%3==0):
            raise ValueError("Bad V15 primitive header")
        name=p[o:o+n].decode("utf8");o+=n
        verts=p[o:o+vc*32];o+=vc*32
        indices=struct.unpack_from("<%dH"%ic,p,o);o+=ic*2
        if not name.startswith("LHD") or len(verts)!=vc*32 or max(indices)>=vc:
            raise ValueError("V15 group/indices invalid")
        if any(not math.isfinite(x) or abs(x)>10000 for a in struct.iter_unpack("<8f",verts) for x in a):
            raise ValueError("V15 non-finite vertex")
        g.append((name,mat,verts,indices,vc))
    if o!=len(p) or sum(x[4] for x in g)!=nv or sum(len(x[3])//3 for x in g)!=nt:
        raise ValueError("V15 payload sum mismatch")
    return g
def patch_v13_source(s):
    pairs=[
        ("if len(dds)!=2 or any(len(a)!=11136 for a in dds):",
         "if len(dds)!=19 or any(len(a)!=11136 for a in dds):"),
        ("assert sysdelta==4*len(dds)+20*len(dds)==48",
         "assert sysdelta==4*len(dds)+20*len(dds)==456"),
        ("for name,col,vbytes,local_idx,vc in payload:",
         "for name,texture_material,vbytes,local_idx,vc in payload:"),
        ("assert orig_prims>0 and ng<=80","assert orig_prims>0 and ng==70"),
        ("assert (len(S)-len(S0))<250000 and (len(V)-len(V0))<1000000",
         "assert (len(S)-len(S0))<550000 and (len(V)-len(V0))<1000000"),
        ('"textures_installed":2','"textures_installed":19'),
        ("sha(original) not in (OLD_V12_SHA,ORIGINAL_SHA)",
         'sha(original) not in (OLD_V12_SHA,ORIGINAL_SHA,"'+V13_SHA+'")')
    ]
    for a,b in pairs:
        if s.count(a)!=1:raise RuntimeError("Unknown v13 PMT format contract: "+a)
        s=s.replace(a,b,1)
    a=s.index("        # Select actual shader texture path only for textured materials.")
    b=s.index("        colors.append(co)",a)
    material='''        tex_index=41+texture_material
        mt=bytearray(S0[q[13]+15*88:q[13]+16*88])
        assert struct.unpack_from("<i",mt,24)[0]==5
        assert all(struct.unpack_from("<i",mt,24+20*j)[0]==-1 for j in range(1,4))
        struct.pack_into("<i",mt,24,tex_index)
        struct.pack_into("<I",mt,0,h[12]+len(colors))
        materials.append(mt)
        co=bytearray(S0[q[14]+18*72:q[14]+19*72])
        struct.pack_into("<4f",co,0,1.,1.,1.,1.)
        struct.pack_into("<4f",co,16,.6,.6,.6,1.)
'''
    patched=s[:a]+material+s[b:]
    marker='    encoded=zlib.compress(struct.pack("<4I",n,t,len(S),len(V))+S+V,9)'
    guarded='''    raw_size=16+len(S)+len(V)
    if raw_size>=1900000:
        raise ValueError("DINO_R2_RAW_PMT_SIZE_GUARD: raw PMT %d >= 1900000" % raw_size)
    encoded=zlib.compress(struct.pack("<4I",n,t,len(S),len(V))+S+V,9)'''
    if patched.count(marker)!=1:
        raise ValueError("DINO_R2_SOURCE_DRIFT: PMT compressor target unavailable")
    # R3: preserve original shader records and link new draw into root mesh.
    # Derived from original loader's format-major shader cache (42E4F0).
    rewrites=[
      (
        '    p2=put(S0[q[2]:q[2]+h[9]*16]+packu(vp,0,0,0))',
        '''    p2=put(S0[q[2]:q[2]+h[9]*16]+packu(vp,0,0,0))
    old_shader_bytes=S0[q[3]:q[3]+h[9]*h[11]*24]
    assert len(old_shader_bytes)==h[9]*h[11]*24
    assert q[3]+len(old_shader_bytes)==q[2]
    shader_count=h[9]+1
    material_count=h[11]+ng
    shader_records=bytearray(shader_count*material_count*24)
    for fi in range(h[9]):
        source=fi*h[11]*24
        dest=fi*material_count*24
        shader_records[dest:dest+h[11]*24]=old_shader_bytes[source:source+h[11]*24]
    p3=put(shader_records)'''
      ),
      (
        'nq=q[:];nq[1]=p1;nq[2]=p2;nq[9:15]=[p9,p10,p11,p12,p13,p14]',
        'nq=q[:];nq[1]=p1;nq[2]=p2;nq[3]=p3;nq[9:15]=[p9,p10,p11,p12,p13,p14]'
      ),
      (
        '    struct.pack_into("<15I",S,24,*nq)',
        '''    struct.pack_into("<15I",S,24,*nq)
    # Root node references mesh0. Mesh0 currently contains the original two
    # primitives: extend its reference to the new third primitive.
    assert (q[9]-q[8])//8==1 and orig_prims==2
    assert u(S0,q[7]+0x28)==0 and u(S0,q[7]+0x20)==0xffffffff
    assert u(S0,q[8])==0 and u(S0,q[8]+4)==2
    struct.pack_into("<I",S,q[8]+4,orig_prims+1)
    assert len(shader_records)==nh[9]*nh[11]*24
    assert S[p3:p3+len(shader_records)]==shader_records'''
      ),
      (
        '    assert S[24+60:len(S0)]==S0[24+60:] and V[:len(V0)]==V0',
        '''    assert S[24+60:q[8]+4]==S0[24+60:q[8]+4]
    assert S[q[8]+8:len(S0)]==S0[q[8]+8:]
    assert V[:len(V0)]==V0'''
      )
    ]
    for old,new in rewrites:
        if patched.count(old)!=1:
            raise ValueError("DINO_R3_SOURCE_DRIFT: "+old[:70])
        patched=patched.replace(old,new,1)
    return patched.replace(marker,guarded)
def main():
    home=pathlib.Path(getattr(sys,"_MEIPASS",pathlib.Path(__file__).resolve().parent))
    s=(home/"dino_cockpit_pmt_patch_v13.py").read_text(encoding="utf8")
    scope={"__name__":"v13_lib"}
    exec(compile(patch_v13_source(s),"dino_v13_pmt.py","exec"),scope)
    scope["parse_payload"]=model_payload
    def textures(directory=None):
        base=pathlib.Path(directory) if directory else pathlib.Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else pathlib.Path(__file__).resolve().parent
        manifest=(base/"DINO_V15_TEXTURE_MANIFEST.json").read_bytes()
        if sha(manifest)!=MANIFEST_SHA:raise ValueError("V15 texture manifest SHA mismatch")
        info=json.loads(manifest)
        if info["model_source_sha256"]!=MODEL_SHA or info["payload_sha256"]!=PAYLOAD_SHA:
            raise ValueError("V15 source manifest mismatch")
        mats=info["textures"]
        if len(mats)!=19 or [m["material_index"] for m in mats]!=list(range(19)):
            raise ValueError("V15 textures incomplete")
        out=[]
        for m in mats:
            name=m["texture_file"]
            if "/" in name or "\\" in name or not name.endswith(".dds"):
                raise ValueError("Invalid DDS path")
            data=(base/name).read_bytes()
            if sha(data)!=m["sha256"] or len(data)!=11136 or data[:4]!=b"DDS " or data[84:88]!=b"DXT1":
                raise ValueError("V15 texture SHA/DXT1 failure: "+name)
            out.append(data)
        return out
    scope["load_texture_data"]=textures
    scope["main"]()
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("DINO_V15_INSTALL_FAILED:",str(exc),file=sys.stderr)
        sys.exit(2)

#!/usr/bin/env python3
"""Exercise the actual native AO baker, including invalid UV and shared glass."""
import pathlib, struct, subprocess, tempfile, zlib
ROOT=pathlib.Path(__file__).resolve().parents[1]

def make(group_specs, existing=False):
 dds=bytearray(132);dds[:4]=b"DDS "
 for offset,val in {4:124,12:1,16:1,28:1,76:32,80:0x41,88:32,
                    92:0xff0000,96:0xff00,100:0xff,104:0xff000000}.items():
  struct.pack_into("<I",dds,offset,val)
 dds[128:]=b"\xff\xff\xff\xff"
 payload=bytearray()
 for name,uv in group_specs:
  vertices=[(0,0,0,0,0,1,*uv[0]),(1,0,0,0,0,1,*uv[1]),(0,1,0,0,0,1,*uv[2])]
  payload.extend(struct.pack("<HHIII",len(name),0,3,3,2)+name)
  payload.extend(b"".join(struct.pack("<8f",*v) for v in vertices)+struct.pack("<3H",0,1,2))
 payload.extend(struct.pack("<I",len(dds))+dds+b"OVCPBR3!"+struct.pack("<3fI",.5,0,1,0))
 orm_offset=36+len(payload)
 payload.extend(struct.pack("<I",len(dds) if existing else 0))
 if existing:payload.extend(dds)
 payload.extend(b"OVCDASH4"+struct.pack("<I",0))
 ng=len(group_specs)
 data=b"OVRCABH4"+struct.pack("<7I",4,ng,1,3*ng,ng,len(payload),zlib.crc32(payload))+payload
 return data,orm_offset

with tempfile.TemporaryDirectory() as tmp:
 root=pathlib.Path(tmp);exe=root/"bake"
 subprocess.run(["g++","-std=c++17","-O2",str(ROOT/"tools/ferrari16/bake_external_ao.cpp"),"-o",str(exe)],check=True)
 for kind,specs,existing,expected in [
  ("valid",[(b"EXT_OPAQUE_00",((0,0),(1,0),(0,1)))],False,True),
  ("degenerate",[(b"EXT_OPAQUE_00",((0,0),(0,0),(0,0)))],False,False),
  ("mixed_valid_first",[(b"EXT_OPAQUE_00",((0,0),(1,0),(0,1))),(b"EXT_OPAQUE_01",((0,0),(0,0),(0,0)))],False,False),
  ("mixed_invalid_first",[(b"EXT_OPAQUE_00",((0,0),(0,0),(0,0))),(b"EXT_OPAQUE_01",((0,0),(1,0),(0,1)))],False,False),
  ("mixed_excessive_wrap",[(b"EXT_OPAQUE_00",((0,0),(1,0),(0,1))),(b"EXT_OPAQUE_01",((0,0),(6,0),(0,1)))],False,False),
  ("wrapped_valid",[(b"EXT_OPAQUE_00",((-1,-1),(0,-1),(-1,0)))],False,True),
  ("tiny_orthogonal",[(b"EXT_OPAQUE_00",((0,0),(1e-5,0),(0,1e-5)))],False,True),
  ("near_parallel",[(b"EXT_OPAQUE_00",((0,0),(1,0),(1,1e-6)))],False,False),
  ("shared",[(b"EXT_OPAQUE_00",((0,0),(1,0),(0,1))),(b"EXT_GLASS_00",((0,0),(1,0),(0,1)))],False,False),
  ("authored",[(b"EXT_OPAQUE_00",((0,0),(1,0),(0,1)))],True,False),
 ]:
  data,off=make(specs,existing)
  src=root/(kind+".ovc");dst=root/(kind+"_out.ovc");src.write_bytes(data)
  subprocess.run([str(exe),str(src),str(dst),"64"],check=True)
  result=dst.read_bytes()
  assert src.read_bytes()==data
  assert result[:28]==data[:28] and result[36:off]==data[36:off]
  assert struct.unpack_from("<II",result,28)==(len(result)-36,zlib.crc32(result[36:]))
  n=struct.unpack_from("<I",result,off)[0]
  if expected:
   assert n==128+sum((64>>k)**2*4 for k in range(7))
   d=result[off+4:off+4+n]
   assert d[:4]==b"DDS " and struct.unpack_from("<II",d,12)==(64,64)
   assert all(v==255 for j in (0,1,3) for v in d[128+j::4])
   assert result[off+4+n:]==data[off+4:]
  else:assert result==data
  assert subprocess.run([str(exe),str(src),str(dst),"64"],capture_output=True).returncode!=0
  assert dst.read_bytes()==result
 # Generated atlas mode only accepts the actual one-face-per-tile layout.
 for kind,uvs,expected in [
  ("atlas_good",[((.125,.125),(.875,.125),(.125,.875))],True),
  ("atlas_bad",[((0,0),(1,0),(0,1))],False),
  ("atlas_overlap",[((.0625,.0625),(.4375,.0625),(.0625,.4375))]*2,False),
  ("atlas_two",[((.0625,.0625),(.4375,.0625),(.0625,.4375)),
                 ((.5625,.0625),(.9375,.0625),(.5625,.4375))],True),
 ]:
  data,off=make([(b"EXT_OPAQUE_00",uv) for uv in uvs])
  src=root/(kind+".ovc");dst=root/(kind+"_out.ovc");src.write_bytes(data)
  subprocess.run([str(exe),str(src),str(dst),"triangle-atlas"],check=True)
  result=dst.read_bytes()
  assert src.read_bytes()==data and result[36:off]==data[36:off]
  if expected:assert struct.unpack_from("<I",result,off)[0]>0
  else:assert result==data
 # A zero-area helper in an otherwise drawable mesh is not a UV failure.
 raw,off=make([(b"EXT_OPAQUE_00",((0,0),(1,0),(0,1)))])
 nlen=struct.unpack_from("<H",raw,36)[0];start=52+nlen
 payload=bytearray(raw[36:start+3*32+6]+struct.pack("<3H",0,0,0)+raw[start+3*32+6:])
 struct.pack_into("<I",payload,8,6)
 raw=b"OVRCABH4"+struct.pack("<7I",4,1,1,3,2,len(payload),zlib.crc32(payload))+payload
 src=root/"helper_triangle.ovc";dst=root/"helper_triangle_ao.ovc";src.write_bytes(raw)
 subprocess.run([str(exe),str(src),str(dst),"64"],check=True)
 assert dst.stat().st_size>src.stat().st_size
 assert src.read_bytes()==raw
 # Real two-face chart from a planar indexed quad; preserve vertex sharing,
 # reject overlap in the paired baker and keep the default triangle mode.
 raw,off=make([(b"EXT_OPAQUE_00",((0,0),(0,0),(0,0)))])
 nlen=struct.unpack_from("<H",raw,36)[0]
 start=52+nlen
 vertices=[(0,0,0,0,0,1,0,0),(1,0,0,0,0,1,0,0),
           (0,1,0,0,0,1,0,0),(1,1,0,0,0,1,0,0)]
 tail=raw[start+3*32+6:]
 payload=struct.pack("<HHIII",nlen,0,4,6,2)+raw[52:start]+b"".join(
     struct.pack("<8f",*v) for v in vertices)+struct.pack("<6H",0,1,2,1,3,2)+tail
 raw=b"OVRCABH4"+struct.pack("<7I",4,1,1,4,2,len(payload),zlib.crc32(payload))+payload
 quad=root/"quad.ovc";quad.write_bytes(raw)
 for mode,expected_vertices in (("triangle",6),("paired",4),("patch",4),("hybrid",4)):
  uv=root/(mode+"_quad.ovc");ao=root/(mode+"_quad_ao.ovc")
  subprocess.run(["python3",str(ROOT/"tools/ferrari16/unwrap_untextured_ovc.py"),
                  str(quad),str(uv),mode],check=True)
  u=uv.read_bytes()
  assert struct.unpack_from("<II",u,20)==(expected_vertices,2)
  subprocess.run([str(exe),str(uv),str(ao),("patch" if mode=="hybrid" else mode)+"-atlas"],check=True)
  assert ao.stat().st_size>uv.stat().st_size
  assert quad.read_bytes()==raw
  if mode=="paired":
   # Force second triangle's third corner across the shared UV edge.
   broken=bytearray(u)
   idx=start+3*32+24
   first=broken[start+24:start+32]
   broken[idx:idx+8]=first
   struct.pack_into("<I",broken,32,zlib.crc32(broken[36:]))
   bad=root/"bad_pair.ovc";bad.write_bytes(broken)
   out=root/"bad_pair_ao.ovc"
   subprocess.run([str(exe),str(bad),str(out),"paired-atlas"],check=True)
   assert out.read_bytes()==broken
 # Four coplanar triangles sharing edges, should remain six vertices in
 # patch mode (pairing alone must split the shared inter-pair boundary).
 vertices=[(x,y,0,0,0,1,0,0) for y in range(2) for x in range(3)]
 indices=(0,1,3,1,4,3,1,2,4,2,5,4)
 payload=struct.pack("<HHIII",nlen,0,6,12,2)+raw[52:start]+b"".join(
     struct.pack("<8f",*v) for v in vertices)+struct.pack("<12H",*indices)+tail
 strip=b"OVRCABH4"+struct.pack("<7I",4,1,1,6,4,len(payload),zlib.crc32(payload))+payload
 src=root/"strip.ovc";src.write_bytes(strip)
 uv=root/"patch_strip.ovc";ao=root/"patch_strip_ao.ovc"
 subprocess.run(["python3",str(ROOT/"tools/ferrari16/unwrap_untextured_ovc.py"),str(src),str(uv),"patch"],check=True)
 assert struct.unpack_from("<II",uv.read_bytes(),20)==(6,4)
 subprocess.run([str(exe),str(uv),str(ao),"patch-atlas"],check=True)
 assert ao.stat().st_size>uv.stat().st_size
 assert src.read_bytes()==strip
 # The source may encode a solid color as BC3; all mip blocks must
 # remain byte-identical and all UVs must be constant before rebuilding.
 raw,off=make([(b"EXT_OPAQUE_00",((0,1),(0,1),(0,1)))])
 nlen=struct.unpack_from("<H",raw,36)[0];start=52+nlen+3*32+6
 oldlen=struct.unpack_from("<I",raw,start)[0]
 bc=bytearray(raw[start+4:start+4+128])
 struct.pack_into("<II",bc,12,4,4)
 struct.pack_into("<I",bc,80,4)
 bc[84:88]=b"DXT5";bc[88:108]=bytes(20)
 bc.extend(bytes.fromhex("ffffffffffffffff8a528a5200000000"))
 payload=raw[36:start]+struct.pack("<I",len(bc))+bc+raw[start+4+oldlen:]
 raw=b"OVRCABH4"+struct.pack("<7I",4,1,1,3,1,len(payload),zlib.crc32(payload))+payload
 src=root/"constant_bc3.ovc";uv=root/"constant_bc3_uv.ovc";ao=root/"constant_bc3_ao.ovc";src.write_bytes(raw)
 subprocess.run(["python3",str(ROOT/"tools/ferrari16/unwrap_untextured_ovc.py"),
                 str(src),str(uv),"paired"],check=True)
 assert uv.read_bytes()[start:]==raw[start:]
 subprocess.run([str(exe),str(uv),str(ao),"paired-atlas"],check=True)
 assert ao.stat().st_size>uv.stat().st_size and src.read_bytes()==raw
 # A varying alpha selector in a constant-endpoint block is NOT uniform.
 invalid=bytearray(raw);invalid[start+4+128]=128;invalid[start+4+129]=128;invalid[start+4+130]=248
 struct.pack_into("<I",invalid,32,zlib.crc32(invalid[36:]))
 bad=root/"nonuniform_bc3.ovc";bad.write_bytes(invalid)
 assert subprocess.run(["python3",str(ROOT/"tools/ferrari16/unwrap_untextured_ovc.py"),
     str(bad),str(root/"bad_bc3_uv.ovc"),"paired"],capture_output=True).returncode!=0
 # Actual 16x16 BC3 flat gray mip chain with transparent out-of-bounds
 # selectors in the 2x2 and 1x1 levels, matching private car assets.
 padded=bytearray(bc[:128]);struct.pack_into("<II",padded,12,16,16);struct.pack_into("<I",padded,28,5)
 padded.extend(bytes.fromhex("ffffffffffffffff8a528a5200000000")*21)
 padded.extend(bytes.fromhex("ffffbffddbb66ddb8a528a5200000000ffffb76ddbb66ddb8a528a5200000000"))
 payload=raw[36:start]+struct.pack("<I",len(padded))+padded+raw[start+4+len(bc):]
 fixture=b"OVRCABH4"+struct.pack("<7I",4,1,1,3,1,len(payload),zlib.crc32(payload))+payload
 src=root/"padded_bc3.ovc";uv=root/"padded_bc3_uv.ovc";ao=root/"padded_bc3_ao.ovc";src.write_bytes(fixture)
 subprocess.run(["python3",str(ROOT/"tools/ferrari16/unwrap_untextured_ovc.py"),str(src),str(uv),"patch"],check=True)
 subprocess.run([str(exe),str(uv),str(ao),"patch-atlas"],check=True)
 assert ao.stat().st_size>uv.stat().st_size and src.read_bytes()==fixture
 # Compile the same production baker with a small test-only budget.
 # No giant synthetic OVC or memory-heavy GPU test is needed.
 harness=root/"budget.cpp"
 harness.write_text('#define main original_baker_main\n#include "'+
                    str(ROOT/"tools/ferrari16/bake_external_ao.cpp")+
                    '"\n#undef main\n'
                    'int main(int argc,char**argv){if(argc!=4)return 2;'
                    'auto b=read(argv[1]);auto out=bake(b,64,std::stoull(argv[3]));'
                    'std::ofstream f(argv[2],std::ios::binary);'
                    'f.write(reinterpret_cast<const char*>(out.data()),out.size());'
                    'return f?0:1;}\n')
 budget_exe=root/"budget"
 subprocess.run(["g++","-std=c++17","-O2",str(harness),"-o",str(budget_exe)],check=True)
 data,off=make([(b"EXT_OPAQUE_00",((0,0),(1,0),(0,1)))])
 src=root/"budget_src.ovc";src.write_bytes(data)
 source_gpu=3*32+3*2+132
 map_gpu=128+sum((64>>k)**2*4 for k in range(7))
 for delta in (-1,0,1):
  out=root/("budget_"+str(delta)+".ovc")
  subprocess.run([str(budget_exe),str(src),str(out),str(source_gpu+map_gpu+delta)],check=True)
  result=out.read_bytes()
  if delta<0:assert result==data
  else:assert struct.unpack_from("<I",result,off)[0]==map_gpu
  assert src.read_bytes()==data
print("EXTERNAL_AO_BAKE_PASS valid/degenerate/mixed/wrapped/shared/authored and no-overwrite")

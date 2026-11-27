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
print("EXTERNAL_AO_BAKE_PASS valid/degenerate/shared/authored and no-overwrite")

#!/usr/bin/env python3
"""Read-only original PC event display ABI + ROB01/ROB02 scene-mask proof.
This script never writes the user game EXE or bundles game assets."""
from pathlib import Path
import hashlib
import struct
import sys
p=Path(sys.argv[1])
a=p.read_bytes()
sha=hashlib.sha256(a).hexdigest()
assert sha=="68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3",sha
u16=lambda offset:struct.unpack_from("<H",a,offset)[0]
u32=lambda offset:struct.unpack_from("<I",a,offset)[0]
pe=u32(0x3c)
assert a[pe:pe+4]==bytes.fromhex("50450000") and u16(pe+24)==0x10b
base=u32(pe+24+28)
assert base==0x400000
table=pe+24+u16(pe+20)
sections=[(u32(table+i*40+12),u32(table+i*40+16),u32(table+i*40+20)) for i in range(u16(pe+6))]
def read(va,count):
 rva=va-base
 for r,sz,offset in sections:
  if r<=rva and rva+count<=r+sz:
   return a[offset+rva-r:offset+rva-r+count]
 raise RuntimeError(hex(va))
for va,count in [(0x43fb40,48),(0x4879b0,28),(0x487880,28)]:
 print("ORIGINAL EXE %08X %s"%(va,read(va,count).hex(" ")))
for i in (0x16a,0x16b):
 va=0x599808+i*0x18
 d=read(va,24)
 print("ORIGINAL EVENT %03X source descriptor=%s sceneMask=0x%08X"%(i,d.hex(" "),struct.unpack_from("<I",d,0x14)[0]))
print("PASS original SHA256, PE32 RVA mapping and event data")

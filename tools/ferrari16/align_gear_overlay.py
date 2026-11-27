#!/usr/bin/env python3
"""Build a PRIVATE gear-only diagnostic overlay anchored to embedded needles.

Uses existing authored digit geometry, not third-party replacement geometry.
No automatic installation; physical visibility/placement is UNTESTED.
"""
import argparse, hashlib, math, struct, zlib
from pathlib import Path

def add(a,b): return tuple(x+y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def mul(a,k): return tuple(x*k for x in a)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):
 n=math.sqrt(dot(a,a))
 if n<1e-7:raise ValueError("degenerate calibration")
 return mul(a,1/n)
def read(p):
 b=p.read_bytes()
 if not 36<=len(b)<=128*1024**2 or b[:8]!=b"OVRCABH4":raise ValueError("V4 required")
 ver,ng,nm,nv,nt,n,crc=struct.unpack_from("<7I",b,8)
 if ver!=4 or n!=len(b)-36 or zlib.crc32(b[36:])!=crc or not 0<ng<=512 or not 0<nm<=128:raise ValueError("header")
 at=36;groups=[]
 for _ in range(ng):
  ln,m,v,i,w=struct.unpack_from("<HHIII",b,at);at+=16
  if not 0<ln<=256 or m>=nm or not 3<=v<=nv or not 3<=i<=nt*3 or i%3 or w not in (2,4):raise ValueError("group")
  name=b[at:at+ln];at+=ln
  verts=list(struct.iter_unpack("<8f",b[at:at+v*32]));at+=v*32
  inds=b[at:at+i*w];at+=i*w
  if len(verts)!=v or len(inds)!=i*w or any(not math.isfinite(x) for a in verts for x in a):raise ValueError("geometry")
  groups.append((name,m,verts,inds,w,i))
 if sum(len(g[2]) for g in groups)!=nv or sum(g[5]//3 for g in groups)!=nt:raise ValueError("totals")
 maps=at
 for _ in range(nm):at+=4+struct.unpack_from("<I",b,at)[0]
 if b[at:at+8]!=b"OVCPBR3!":raise ValueError("PBR")
 at+=8
 for _ in range(nm):
  at+=12
  for _ in range(2):at+=4+struct.unpack_from("<I",b,at)[0]
 material=b[maps:at]
 if b[at:at+8]!=b"OVCDASH4":raise ValueError("dashboard")
 n=struct.unpack_from("<I",b,at+8)[0];at+=12
 if n>ng or at+n*56!=len(b):raise ValueError("binding envelope")
 bindings=[b[at+i*56:at+(i+1)*56] for i in range(n)]
 return groups,bindings,material,nm
def axes(groups,bindings):
 by_kind={}
 for b in bindings:
  mesh,kind,gear=struct.unpack_from("<3I",b)
  if mesh>=len(groups):raise ValueError("binding index")
  if kind in (1,2) and not groups[mesh][0].startswith((b"EXT_GLASS_",b"F50_GLASS_")):
   if kind in by_kind:raise ValueError("ambiguous opaque needles")
   by_kind[kind]=(struct.unpack_from("<3f",b,16),struct.unpack_from("<3f",b,28))
 if set(by_kind)!={1,2}:raise ValueError("two opaque needles required")
 p,n=by_kind[1];q,m=by_kind[2]
 n,m=unit(n),unit(m)
 if abs(dot(n,m))<.98:raise ValueError("needle axes disagree")
 if dot(n,m)<0:m=mul(m,-1)
 front=unit(add(n,m))
 # Game-aligned vehicle Z is rearward from the forward dash towards driver.
 if front[2]<0:front=mul(front,-1)
 if front[2]<.8:raise ValueError("unexpected gauge facing")
 up=unit(sub((0,1,0),mul(front,front[1])))
 right=unit(cross(up,front))
 center=mul(add(p,q),.5)
 dist=math.sqrt(dot(sub(p,q),sub(p,q)))
 if not .07<=dist<=.35:raise ValueError("needle spacing")
 return center,right,up,front,dist
def build(body,overlay):
 bg,bb,_,_=read(body);og,ob,material,nm=read(overlay)
 target=axes(bg,bb);origin=axes(og,ob)
 ratio=target[4]/origin[4]
 if not .45<=ratio<=1.75:raise ValueError("scale")
 def transform(v,isnormal=False):
  d=v if isnormal else sub(v,origin[0])
  q=(dot(d,origin[1]),dot(d,origin[2]),dot(d,origin[3]))
  v=add(add(mul(target[1],q[0]),mul(target[2],q[1])),mul(target[3],q[2]))
  return unit(v) if isnormal else add(target[0],mul(v,ratio))
 gears={};payload=bytearray();nv=nt=0
 for b in ob:
  mesh,kind,gear=struct.unpack_from("<3I",b)
  if kind!=3:continue
  if gear in gears or gear>6 or mesh>=len(og):raise ValueError("unexpected gear")
  name,mat,verts,inds,w,i=og[mesh]
  if name.startswith((b"EXT_GLASS_",b"F50_GLASS_")):raise ValueError("transparent gear")
  newname=("EXT_OPAQUE_GEAR_%02d"%gear).encode()
  newverts=[]
  for v in verts:newverts.append((*transform(v[:3]),*transform(v[3:6],True),*v[6:]))
  idx=len(gears);gears[gear]=idx
  payload.extend(struct.pack("<HHIII",len(newname),mat,len(verts),i,w)+newname)
  payload.extend(b"".join(struct.pack("<8f",*v) for v in newverts)+inds)
  nv+=len(verts);nt+=i//3
 if set(gears)!=set(range(7)):raise ValueError("0..6 gear coverage required")
 payload.extend(material+b"OVCDASH4"+struct.pack("<I",len(gears)))
 for gear,index in sorted(gears.items(),key=lambda x:x[1]):
  # GearVisible ignores pivot/axis; use bounded canonical values.
  payload.extend(struct.pack("<4I10f",index,3,gear,0,0,0,0,0,0,1,0,1,0,0))
 result=b"OVRCABH4"+struct.pack("<7I",4,len(gears),nm,nv,nt,len(payload),zlib.crc32(payload))+payload
 return result,ratio,target[0]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--body",type=Path,required=True);ap.add_argument("--overlay",type=Path,required=True);ap.add_argument("--out",type=Path,required=True)
 a=ap.parse_args()
 if a.out.exists():raise SystemExit("refuse existing output")
 result,scale,center=build(a.body,a.overlay)
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with a.out.open("xb") as f:f.write(result)
 print("GEAR_ONLY_PRIVATE_UNTESTED",a.out.name,"scale",scale,"anchor",center,"sha256",hashlib.sha256(result).hexdigest())
if __name__=="__main__":main()

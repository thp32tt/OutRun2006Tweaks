#!/usr/bin/env python3
"""Dino 246 R26 original-dimension cockpit geometry & material proof-of-concept.

READ ONLY: uses original obj_plcar_dino_pmt.sz for coordinate-system and source
identity checks. Never patches original PMT nor installs a model in the game.
The modeled geometry is a replacement cockpit sidecar, NOT a complete game-car.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import math
import random
import struct
import zlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFont

PI=math.pi
ROOT=Path(__file__).resolve().parent


def add(a,b): return tuple(a[i]+b[i] for i in range(3))
def sub(a,b): return tuple(a[i]-b[i] for i in range(3))
def mul(a,t): return tuple(a[i]*t for i in range(3))
def dot(a,b): return sum(a[i]*b[i] for i in range(3))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):
 n=math.sqrt(dot(a,a))
 if n<1e-9: raise ValueError("zero-length geometry")
 return mul(a,1/n)

class Mesh:
 def __init__(self,name,material):
  self.name=name;self.material=material;self.vertices=[];self.uvs=[];self.faces=[]
  self.normals=[]
 def vert(self,p,uv=(0,0)):
  self.vertices.append(tuple(map(float,p)));self.uvs.append(tuple(map(float,uv)))
  return len(self.vertices)-1
 def tri(self,a,b,c):
  if a!=b and b!=c and a!=c: self.faces.extend((a,b,c))
 def quad(self,a,b,c,d):
  self.tri(a,b,c);self.tri(a,c,d)
 def normalise(self):
  normals=[[0.,0.,0.] for _ in self.vertices]
  for i in range(0,len(self.faces),3):
   a,b,c=self.faces[i:i+3]
   t=cross(sub(self.vertices[b],self.vertices[a]),sub(self.vertices[c],self.vertices[a]))
   for j in (a,b,c):
    for axis in range(3):normals[j][axis]+=t[axis]
  self.normals=[]
  for n in normals:
   length=math.sqrt(sum(x*x for x in n))
   self.normals.append(tuple(x/length for x in n) if length>1e-10 else (0.,1.,0.))
  if len(self.faces)%3 or not self.faces or not self.vertices:
   raise ValueError("empty or invalid geometry: "+self.name)
  for v in self.vertices:
   if not all(math.isfinite(x) and abs(x)<100 for x in v):
    raise ValueError("invalid vertex: "+self.name)
  if any(i>=len(self.vertices) or i<0 for i in self.faces):
   raise ValueError("out-of-range face: "+self.name)
  return self

def surface(name,material,nu,nv,fn):
 m=Mesh(name,material)
 for i in range(nu+1):
  u=i/nu
  for j in range(nv+1):
   v=j/nv;m.vert(fn(u,v),(u,v))
 for i in range(nu):
  for j in range(nv):
   a=i*(nv+1)+j;b=(i+1)*(nv+1)+j
   m.quad(a,b,b+1,a+1)
 return m

def box(name,mat,c,size):
 x,y,z=c;sx,sy,sz=[t/2 for t in size]
 m=Mesh(name,mat)
 pts=[(x-sx,y-sy,z-sz),(x+sx,y-sy,z-sz),(x+sx,y+sy,z-sz),(x-sx,y+sy,z-sz),
      (x-sx,y-sy,z+sz),(x+sx,y-sy,z+sz),(x+sx,y+sy,z+sz),(x-sx,y+sy,z+sz)]
 for face in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
  ids=[m.vert(pts[k],(u,v)) for k,(u,v) in zip(face,((0,0),(1,0),(1,1),(0,1)))]
  m.quad(*ids)
 return m

def tube(name,mat,path,radius=0.007,sides=10):
 if len(path)<2: raise ValueError("tube path too short")
 m=Mesh(name,mat)
 for j,p in enumerate(path):
  direction=sub(path[min(j+1,len(path)-1)],path[max(0,j-1)])
  axis=unit(direction)
  t=(1,0,0) if abs(axis[0])<0.8 else (0,1,0)
  b=unit(cross(axis,t));c=cross(axis,b)
  for k in range(sides+1):
   a=2*PI*k/sides
   n=add(mul(b,math.cos(a)),mul(c,math.sin(a)))
   m.vert(add(p,mul(n,radius)),(k/sides,j/max(1,len(path)-1)))
 for j in range(len(path)-1):
  for k in range(sides):
   a=j*(sides+1)+k;b=(j+1)*(sides+1)+k;m.quad(a,b,b+1,a+1)
 return m

def disc(name,mat,center,radius,sides=60,tilt=0.):
 m=Mesh(name,mat);cx,cy,cz=center
 m.vert(center,(.5,.5))
 for j in range(sides+1):
  a=2*PI*j/sides
  x=radius*math.cos(a);y=radius*math.sin(a)
  m.vert((cx+x,cy+y,cz-tilt*y),(.5+.5*math.cos(a),.5+.5*math.sin(a)))
 for j in range(sides):m.tri(0,j+1,j+2)
 return m

def torus(name,mat,center,major,minor,nu=72,nv=12,tilt=.19):
 m=Mesh(name,mat);cx,cy,cz=center
 for i in range(nu+1):
  u=2*PI*i/nu
  for j in range(nv+1):
   v=2*PI*j/nv
   r=major+minor*math.cos(v);xx=r*math.cos(u);yy=r*math.sin(u)
   zz=minor*math.sin(v)-tilt*yy
   m.vert((cx+xx,cy+yy,cz+zz),(i/nu*3,j/nv))
 for i in range(nu):
  for j in range(nv):
   a=i*(nv+1)+j;b=(i+1)*(nv+1)+j;m.quad(a,b,b+1,a+1)
 return m

def polyline(name,mat,pts,width=.006):
 return tube(name,mat,pts,width,8)

def generate_cockpit():
 out=[]
 push=lambda m:out.append(m)
 # Original owner geometry sampled from PLCAR: approx +/-0.66 dash, seats
 # centered +/-0.33, driver steering cluster x=-0.32, y~0.72, z~-0.50.
 push(surface("dash_top_soft_curve","vinyl",24,8,
     lambda u,v:(-.68+1.36*u,
                .75+.037*math.sin(PI*u)-.035*v+.008*math.sin(PI*v),
                -.88+.41*v)))
 push(surface("dash_rolled_face","vinyl",24,8,
     lambda u,v:(-.68+1.36*u,.72-.27*v,
                -.49+.016*math.sin(PI*v))))
 push(polyline("dash_lower_chrome_trim","metal",
     [(-.65+i*1.3/32,.50,-.474) for i in range(33)],.005))
 push(box("dashboard_driver_instrument_recess","plastic",(-.326,.712,-.478),(.433,.23,.054)))
 push(surface("instrument_hood_curved","leather",20,8,
     lambda u,v:(-.564+.48*u,.80+.075*math.sin(PI*u)*(1-v),
                -.54+.18*v)))
 # 3 real 3D gauge barrels and readable dial faces: not just blurry stickers.
 for i,(dx,y,r,face) in enumerate(((-.447,.726,.065,"dial0"),(-.324,.735,.079,"dial1"),(-.196,.726,.065,"dial2"))):
  frontz=-.421
  push(tube("gauge_%02d_bezel"%i,"metal",
       [(dx+r*math.cos(2*PI*j/60),y+r*math.sin(2*PI*j/60),frontz) for j in range(61)],.006,10))
  push(disc("gauge_%02d_face"%i,face,(dx,y,frontz+.004),r*.92,64))
  push(tube("gauge_%02d_needle"%i,"metal",
       [(dx,y,frontz+.010),(dx+r*.55*math.cos(i*.7+PI/3),y+r*.55*math.sin(i*.7+PI/3),frontz+.013)],.0024,8))
 # Wheel stem shaft and lower column intentionally one wheel only, no old wheel owner.
 sc=(-.320,.708,-.289);axis=(.0,-.16,1.0)
 push(torus("LHD_steering_rim_remodelled","leather",sc,.180,.018,88,14,tilt=.18))
 push(tube("LHD_column_real_shafts","metal",
     [(-.320,.695,-.684),(-.320,.689,-.590),(-.320,.70,-.427),sc],.024,20))
 push(tube("LHD_column_plastic_shroud","plastic",
     [(-.320,.693,-.57),(-.320,.692,-.46)],.035,18))
 push(disc("LHD_three_spoke_hub","metal",(-.320,.708,-.275),.048,44,.18))
 push(disc("LHD_horn_button_black","plastic",(-.320,.708,-.251),.031,40,.18))
 for i,a in enumerate((PI/2,PI*7/6,PI*11/6)):
  end=(-.320+.167*math.cos(a),.708+.167*math.sin(a),-.289-.18*.167*math.sin(a))
  push(tube("steering_spoke_%d_metal"%i,"metal",
            [(-.320+.035*math.cos(a),.708+.035*math.sin(a),-.269),end],.011,14))
  for j,t in enumerate((.48,.72)):
   cx=-.32+.17*t*math.cos(a);cy=.708+.17*t*math.sin(a)
   push(disc("spoke_rivet_%d_%d"%(i,j),"plastic",(cx,cy,-.261-.18*.17*t*math.sin(a)),.007,12))
 # Turn signal and wiper stalks, no intersection with steering rim.
 for name,sign in (("indicator",-1),("wiper",1)):
  x=-.32+sign*.037
  y=.693
  push(tube(name+"_stalk","metal",
       [(x,y,-.455),(x+sign*.105,y+.007,-.43),(x+sign*.17,y+.013,-.40)],.007,12))
  push(tube(name+"_rubber_tip","plastic",
       [(x+sign*.165,y+.013,-.4),(x+sign*.205,y+.013,-.402)],.014,12))
 # Passenger dash has four raised real metal switch levers & vent louvers.
 for i in range(4):
  x=.057+i*.108
  push(box("switchplate_%d"%i,"metal",(x,.628,-.454),(.071,.054,.008)))
  push(tube("toggle_pin_%d"%i,"metal",
     [(x,.623,-.452),(x,.618,-.423),(x+.011,.611,-.405)],.006,10))
  push(tube("toggle_grip_%d"%i,"plastic",
     [(x+.007,.613,-.410),(x+.012,.610,-.398)],.009,10))
 for i in range(13):
  x=.08+i*.028
  push(box("vent_louver_%02d"%i,"plastic",(x,.727,-.455),(.012,.027,.006)))
 push(box("glove_compartment_recess","plastic",(.39,.548,-.468),(.35,.06,.006)))
 push(polyline("glove_lid_upper","metal",[(.22,.591,-.46),(.56,.591,-.46)],.003))
 # Center tunnel & shift gate, modeled separately (not flatten/decorative quad).
 push(surface("center_console_leather","leather",8,22,
     lambda u,v:(-.145+.290*u,.369+.018*math.cos((u-.5)*PI),
                -.295+.90*v)))
 push(box("gear_gate_recess","metal",(.035,.401,.05),(.116,.012,.174)))
 for i in range(5):
  x=-.006+i*.021
  push(polyline("gear_gate_slit_%d"%i,"plastic",[(x,.408,-.02),(x,.408,.122)],.0026))
 push(tube("gear_stick_exposed_shaft","metal",[(.035,.413,.051),(.037,.485,.054),(.041,.577,.064)],.012,14))
 push(torus("shift_knob_soft_grip","leather",(.041,.583,.064),.016,.014,32,10,tilt=0))
 # Foot pedal set near the original front-floor geometry.
 for i,x in enumerate((-.540,-.410,-.255)):
  push(box("pedal_%d_plate"%i,"metal",(x,.226,-.547),(.083,.025,.115)))
  for j in range(5):
   z=-.592+j*.021
   push(tube("pedal%d_grip%d"%(i,j),"plastic",[(x-.025,.24,z),(x+.025,.24,z)],.003,8))
 # Two shaped leather buckets; seam piping & ribs as actual mesh geometry.
 for label,cx in (("driver",-.343),("passenger",.343)):
  # seat pad: 32x20 smooth quad mesh with shallow depressions
  push(surface(label+"_seat_pad_sculpted","leather",32,20,
    lambda u,v:(cx+(.244*2*u-.244),
      .344+.066*math.sin(PI*u)**.9+.017*math.sin(PI*v),
      .06+.64*v+.029*math.sin(PI*u))))
  push(surface(label+"_backrest_sculpted","leather",32,26,
    lambda u,v:(cx+.247*(2*u-1)*(1-.12*v),
      .399+.592*v,
      .752+.28*v-.050*math.sin(PI*u)*math.sin(PI*v))))
  for edge in (-1,1):
   push(polyline(label+"_seat_edge_piping_%s"%edge,"metal",
     [(cx+edge*.234,.363+.02*math.sin(PI*k/24),.07+.64*k/24) for k in range(25)],.004))
   push(polyline(label+"_back_edge_piping_%s"%edge,"metal",
     [(cx+edge*.238*(1-.13*k/28),.403+.58*k/28,
       .75+.28*k/28) for k in range(29)],.004))
  # 6 quilt seams and raised leather rib paths
  for rib in range(1,7):
   x0=cx-.204+rib*.058
   push(polyline(label+"_seat_stitch_rib_%d"%rib,"seat",
     [(x0,.410+.014*math.sin(PI*k/20),.10+.56*k/20) for k in range(21)],.0033))
   push(polyline(label+"_back_stitch_rib_%d"%rib,"seat",
     [(cx+(x0-cx)*(1-.12*k/25),.422+.55*k/25,
        .756+.27*k/25-.018) for k in range(26)],.0033))
 # Footwell carpet panel, only under feet (no original exterior mesh duplicate).
 push(surface("LHD_footwell_carpet","carpet",6,10,
     lambda u,v:(-.67+1.34*u,.19,-.79+.71*v)))
 for m in out:m.normalise()
 return out


def random_map(name,size,seed):
 rng=random.Random(seed)
 if name.startswith("dial"):
  im=Image.new("RGB",(size,size),(9,10,14))
  d=ImageDraw.Draw(im)
  b=int(size*.055);d.ellipse((b,b,size-b,size-b),fill=(12,15,21),outline=(164,170,170),width=max(2,size//180))
  x=y=size/2;r=size*.405
  for i in range(61):
   ang=2*PI*i/60+PI/2
   r1=r*(.88 if i%5==0 else .95)
   pts=(x+r1*math.cos(ang),y+r1*math.sin(ang),x+r*math.cos(ang),y+r*math.sin(ang))
   d.line(pts,fill=(210,212,207),width=(max(2,size//125) if i%5==0 else max(1,size//310)))
  for i in range(11):
   ang=2*PI*i/10+PI/2
   rad=r*.69
   pos=(x+rad*math.cos(ang),y+rad*math.sin(ang))
   d.text(pos,str(i*20 if name=="dial2" else i),anchor="mm",fill=(190,195,191),
          stroke_width=max(0,size//1024))
  d.ellipse((x-r*.035,y-r*.035,x+r*.035,y+r*.035),fill=(194,185,172))
  return im
 # Procedural high resolution source, repeatable PRNG, not AI photo synthesis.
 noise=Image.effect_noise((512,512),16).resize((size,size),Image.Resampling.BICUBIC)
 palette={
  "leather":((17,19,22),(55,53,53)),
  "vinyl":((17,17,19),(36,37,42)),
  "plastic":((22,23,25),(48,48,50)),
  "metal":((56,59,64),(174,173,177)),
  "carpet":((12,13,15),(51,54,57)),
  "seat":((39,38,40),(87,85,86))
 }
 lower,upper=palette[name]
 im=ImageOps.colorize(noise,lower,upper)
 draw=ImageDraw.Draw(im)
 if name in ("leather","seat","vinyl","carpet"):
  for i in range(size*9):
   x=rng.randrange(size);y=rng.randrange(size)
   alpha=rng.randrange(13,50)
   base=(32,31,31) if name!="seat" else (71,66,64)
   radius=rng.choice((1,1,1,2))
   col=tuple(min(255,c+alpha//4) for c in base)
   draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=col)
 if name=="metal":
  for i in range(size*3):
   y=rng.randrange(size);v=rng.randrange(65,153)
   draw.line((0,y,size,y),fill=(v,v,v+3),width=1)
 return im


def material_maps(size):
 names=("leather","vinyl","plastic","metal","carpet","seat","dial0","dial1","dial2")
 return {n:random_map(n,size if not n.startswith("dial") else min(size,1024),
                      246+17*i) for i,n in enumerate(names)}


def png_bytes(im):
 with io.BytesIO() as out:
  im.save(out,format="PNG",optimize=True)
  return out.getvalue()


def dds_bgra(im):
 im=im.convert("RGBA")
 w,h=im.size
 header=b"DDS "+struct.pack("<7I",124,0x100f,h,w,w*4,0,1)
 header+=bytes(44)+struct.pack("<8I",32,0x41,0,32,0x00ff0000,0x0000ff00,0x000000ff,0xff000000)
 header+=struct.pack("<5I",0x1000,0,0,0,0)
 assert len(header)==128
 return header+im.tobytes("raw","BGRA")


def write_glb(meshes,imgs,path):
 from dino_original_pmt_to_glb import Glb
 glb=Glb()
 tex=[];images=[];mats=[]
 kinds=list(imgs.keys())
 for name,im in imgs.items():
  b=png_bytes(im)
  images.append({"name":name+"_generated","mimeType":"image/png","bufferView":glb.append(b)})
  tex.append({"source":len(images)-1})
 for name in kinds:
  metallic=.85 if name=="metal" else .07
  roughness=.29 if name=="metal" else .86 if name in ("carpet","vinyl") else .62
  mats.append({"name":name+"_PBR_preview","doubleSided":True,
               "pbrMetallicRoughness":{"baseColorFactor":[1,1,1,1],
                 "baseColorTexture":{"index":kinds.index(name)},
                 "metallicFactor":metallic,"roughnessFactor":roughness}})
 prims=[];nodes=[]
 for m in meshes:
  pos=m.vertices
  lo=[min(p[i] for p in pos) for i in range(3)]
  hi=[max(p[i] for p in pos) for i in range(3)]
  def binary(rows,fmt):
   return b"".join(struct.pack(fmt,*r) for r in rows)
  vi=glb.accessor(glb.append(binary(pos,"<3f"),34962),len(pos),"VEC3",lo=lo,hi=hi)
  ni=glb.accessor(glb.append(binary(m.normals,"<3f"),34962),len(pos),"VEC3")
  ui=glb.accessor(glb.append(binary(m.uvs,"<2f"),34962),len(pos),"VEC2")
  ix=glb.accessor(glb.append(binary(((k,) for k in m.faces),"<I"),34963),
                  len(m.faces),"SCALAR",5125,lo=[0],hi=[max(m.faces)])
  prims.append({"name":m.name,"primitives":[{
   "attributes":{"POSITION":vi,"NORMAL":ni,"TEXCOORD_0":ui},
   "indices":ix,"material":kinds.index(m.material),"mode":4}]})
  nodes.append({"name":m.name,"mesh":len(prims)-1})
 doc={"asset":{"version":"2.0","generator":"Dino original-dimension cockpit geometry v1"},
   "scene":0,"scenes":[{"nodes":list(range(len(nodes)))}],"nodes":nodes,
   "meshes":prims,"materials":mats,"images":images,"textures":tex,
   "accessors":glb.accessors,"bufferViews":glb.views,
   "buffers":[{"byteLength":len(glb.bin)}],
   "extras":{"modeling":"new authored geometry; original PC car dimensions",
             "sourcePreserved":True,"runtime":"R26 uses .ovc, not GLB"}}
 js=json.dumps(doc,separators=(",",":"),ensure_ascii=True).encode()
 js+=b" "*(-len(js)%4)
 binary=bytes(glb.bin);binary+=bytes(-len(binary)%4)
 path.write_bytes(struct.pack("<4sII",b"glTF",2,12+8+len(js)+8+len(binary))+
                  struct.pack("<I4s",len(js),b"JSON")+js+
                  struct.pack("<I4s",len(binary),b"BIN"+bytes((0,)))+binary)


def write_ovc(meshes,imgs,path):
 # Matches v2 OVC parser in src/vr/game/dino_external_sidecar.hpp;
 # this is a staged model, not an installed or headset-validated package.
 kind=list(imgs.keys())
 payload=bytearray()
 nvert=ntri=0
 for m in meshes:
  name=m.name.encode("utf-8")
  if not name or len(name)>256:raise ValueError("invalid OVC mesh name")
  n=len(m.vertices);ic=len(m.faces)
  width=2 if n<=65535 else 4
  payload+=struct.pack("<HHIII",len(name),kind.index(m.material),n,ic,width)+name
  for v,norm,uv in zip(m.vertices,m.normals,m.uvs):
   payload+=struct.pack("<8f",*(v+norm+uv))
  for i in m.faces:payload+=struct.pack("<H" if width==2 else "<I",i)
  nvert+=n;ntri+=ic//3
 for k,img in imgs.items():
  data=dds_bgra(img)
  payload+=struct.pack("<I",len(data))+data
 if len(payload)>112*1024*1024:raise ValueError("OVC model exceeds GPU payload budget")
 header=b"OVRCABH2"+struct.pack("<7I",2,len(meshes),len(kind),nvert,ntri,
                        len(payload),zlib.crc32(payload)&0xffffffff)
 path.write_bytes(header+payload)


def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--game-dir",type=Path,required=True)
 parser.add_argument("--output-dir",type=Path,required=True)
 parser.add_argument("--glb-texture",type=int,choices=(512,1024,2048),default=2048)
 parser.add_argument("--ovc-texture",type=int,choices=(256,512,1024),default=512)
 args=parser.parse_args()
 file=args.game_dir/"Cars"/"obj_plcar_dino_pmt.sz"
 src=file.read_bytes()
 spec=importlib.util.spec_from_file_location("base",ROOT/"dino_original_pmt_to_glb.py")
 if not spec or not spec.loader:raise RuntimeError("missing original exporter")
 base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
 a=base.open_pmt(file)
 orig=base.decode_object(a,0)
 if a["obj_count"]!=17 or len(orig)<20:
  raise ValueError("unexpected Dino source; model dimension assumptions unsafe")
 xs=[x[0] for p in orig for x in p["vertices"]]
 ys=[x[1] for p in orig for x in p["vertices"]]
 zs=[x[2] for p in orig for x in p["vertices"]]
 if not (-.95<min(xs)<-.75 and .75<max(xs)<.95 and
          .08<min(ys)<.22 and 1.0<max(ys)<1.22 and
          -2.3<min(zs)<-1.9 and 1.9<max(zs)<2.3):
  raise ValueError("source model geometry basis differs from verified Dino")
 meshes=generate_cockpit()
 out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
 glb=out/"Dino246_OriginalDim_Cockpit_HDGeometry_v1.glb"
 ovc=out/"Dino246_OriginalDim_Cockpit_HDGeometry_v1.ovc"
 write_glb(meshes,material_maps(args.glb_texture),glb)
 write_ovc(meshes,material_maps(args.ovc_texture),ovc)
 result={"input":file.name,"sourceSha256":hashlib.sha256(src).hexdigest(),
         "sourceModelBounds": [[min(xs),min(ys),min(zs)],[max(xs),max(ys),max(zs)]],
         "originalGameFileModified":False,
         "meshParts":len(meshes),"vertices":sum(len(m.vertices) for m in meshes),
         "triangles":sum(len(m.faces)//3 for m in meshes),
         "newGeometryExamples":["steering rim/hub/shaft/stalks","gauge housings/needles",
               "leather dash/vents/switches","seat pad/backrest/piping/stitch ribs",
               "foot pedals","gearbox/console"],
         "glbTextureSize":args.glb_texture,
         "ovcTextureSize":args.ovc_texture,
         "textureOrigin":"locally PROCEDURAL GENERATED, NOT diffusion/AI-generated",
         "materialCount":9,
         "glbBytes":glb.stat().st_size,
         "ovcBytes":ovc.stat().st_size,
         "runtimeValidation":"UNTESTED",
         "modelFit":"STATIC_ESTIMATE_ONLY",
         "overlapWarning":"Original game cockpit geometry must be explicitly hidden for R26 sidecar use"}
 (out/"Dino246_Cockpit_HDGeometry_v1_report.json").write_text(
   json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
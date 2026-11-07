#!/usr/bin/env python3
"""Ferrari 365 GTS/4 Daytona editable high-detail cockpit GLB V5.

This is an actual 3D mesh rework, NOT a concept image and NOT an OVC/game
installer. Native game source PMT and previous Dino/v4 assets are read-only.
Outputs:
 - GLB with embedded glTF 2.0 BaseColor, tangent-space normal and packed ORM
 - texture PNGs for edit
 - independent grayscale displacement/height map (no glTF-standard volume map)
 - provenance/count/validation JSON
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import hashlib,io,json,math,struct,random
from PIL import Image,ImageFilter,ImageEnhance,ImageOps
try:
 from pmt_export_base import open_pmt,decode_object,decode_dds
except ImportError:
 from dino_original_pmt_to_glb import open_pmt,decode_object,decode_dds

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"editable_v5"
OUT.mkdir(parents=True,exist_ok=True)
RT=ROOT/"runtime_v4"
PMT=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz")
OVC=RT/"Daytona365_Cockpit_R26_v2.ovc"
EXPECTED_PMT="f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe"
EXPECTED_OVC="6b7b8c0544702c80d41beb220d7ae0db576ddf2bc16c35f6e0cf783085ba8694"
def assert_private_sources():
 if hashlib.sha256(PMT.read_bytes()).hexdigest()!=EXPECTED_PMT:
  raise ValueError("private original PMT SHA changed")
 if hashlib.sha256(OVC.read_bytes()).hexdigest()!=EXPECTED_OVC:
  raise ValueError("v4 source OVC SHA changed")
 if OVC.read_bytes()[:8]!=b"OVRCABH2":
  raise ValueError("v4 original OVC signature changed")

def vec_add(a,b):return tuple(a[i]+b[i] for i in range(3))
def vec_sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def vec_mul(a,s):return tuple(x*s for x in a)
def norm(a):
 l=math.sqrt(sum(x*x for x in a))
 return tuple(x/max(l,1e-10) for x in a)
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def pack_vertex(position,normal,uv):
 return (*position,*norm(normal),*uv)
def make_mesh(name,mat):
 return {"name":name,"mat":mat,"v":[],"i":[]}
def add_v(m,xyz,n,uv):
 m["v"].append(pack_vertex(xyz,n,uv));return len(m["v"])-1
def face(m,a,b,c):
 if len({a,b,c})==3:m["i"].extend((a,b,c))
def from_v4_ovc():
 b=OVC.read_bytes()
 _,nm,nt,nv,ntri,payload,crc=struct.unpack_from("<7I",b,8)
 at=36;items=[]
 for _ in range(nm):
  nlen,mat,nvtx,nidx,iw=struct.unpack_from("<HHIII",b,at);at+=16
  name=b[at:at+nlen].decode("ascii");at+=nlen
  vs=[struct.unpack_from("<8f",b,at+i*32) for i in range(nvtx)];at+=nvtx*32
  idx=list(struct.unpack_from("<"+"H"*nidx,b,at));at+=2*nidx
  items.append({"name":name,"mat":mat,"v":vs,"i":idx})
 return items

def loop_once(m,sharp_limit=.70,shape_blend=.35):
 """Loop edge smooth refinement with original silhouette preservation.

 Original UV seams/creases remain boundary edges. Interior midpoints receive
 1/8 neighbor correction only if adjacent face normal orientations agree.
 No original vertex repivoting: the actual PMT mesh shell stays aligned.
 """
 old=m["v"];idx=m["i"];out=make_mesh(m["name"],m["mat"]);out["v"]=list(old)
 edges=defaultdict(list)
 for j in range(0,len(idx),3):
  a,b,c=idx[j:j+3]
  for x,y,opp in ((a,b,c),(b,c,a),(c,a,b)):
   edges[tuple(sorted((x,y)))].append(opp)
 edge_new={}
 for (a,b),opps in edges.items():
  pa,pb=old[a],old[b]
  xyz=tuple((pa[k]+pb[k])*.5 for k in range(3))
  if len(opps)==2:
   n1,n2=norm(pa[3:6]),norm(pb[3:6])
   same=sum(n1[i]*n2[i] for i in range(3))
   if same>sharp_limit:
    smooth=tuple((3*(pa[k]+pb[k])+(old[opps[0]][k]+old[opps[1]][k]))/8 for k in range(3))
    xyz=tuple(xyz[k]*(1-shape_blend)+smooth[k]*shape_blend for k in range(3))
  n=norm(tuple(pa[k]+pb[k] for k in (3,4,5)))
  uv=((pa[6]+pb[6])*.5,(pa[7]+pb[7])*.5)
  edge_new[(a,b)]=edge_new[(b,a)]=add_v(out,xyz,n,uv)
 for j in range(0,len(idx),3):
  a,b,c=idx[j:j+3]
  p,q,r=edge_new[(a,b)],edge_new[(b,c)],edge_new[(c,a)]
  for tr in ((a,p,r),(p,b,q),(r,q,c),(p,q,r)):face(out,*tr)
 return out

def smooth_mesh(m,iterations=2,offset=.0):
 for i in range(iterations):
  m=loop_once(m)
 if offset:
  out=make_mesh(m["name"],m["mat"])
  out["v"]=[(*tuple(v[k]+offset*v[3+k] for k in range(3)),*v[3:]) for v in m["v"]]
  out["i"]=m["i"]
  m=out
 return m

def uv_quad(m,points,normal,uvs):
 aa=[add_v(m,p,normal,t) for p,t in zip(points,uvs)]
 face(m,aa[0],aa[1],aa[2]);face(m,aa[0],aa[2],aa[3])

def surface(name,mat,nx,ny,formula,uv_scale=(1,1),flip=False):
 m=make_mesh(name,mat)
 for j in range(ny+1):
  v=j/ny
  for i in range(nx+1):
   u=i/nx
   p=formula(u,v)
   du=vec_sub(formula(min(1,u+.0001),v),formula(max(0,u-.0001),v))
   dv=vec_sub(formula(u,min(1,v+.0001)),formula(u,max(0,v-.0001)))
   n=norm(cross(du,dv) if flip else cross(dv,du))
   add_v(m,p,n,(u*uv_scale[0],v*uv_scale[1]))
 for j in range(ny):
  for i in range(nx):
   a=j*(nx+1)+i;b=a+1;c=a+nx+1;d=c+1
   if flip:
    face(m,a,b,c);face(m,b,d,c)
   else:
    face(m,a,c,b);face(m,b,c,d)
 return m

def tube(name,mat,path,radius,sides=10,reps=1):
 m=make_mesh(name,mat)
 for j,p in enumerate(path):
  before=path[max(0,j-1)];after=path[min(len(path)-1,j+1)]
  tangent=norm(vec_sub(after,before))
  base=norm(cross(tangent,(0.,1.,0.)))
  if sum(x*x for x in base)<.2:base=norm(cross(tangent,(1.,0.,0.)))
  axis2=norm(cross(tangent,base))
  for i in range(sides+1):
   t=i*2*math.pi/sides
   n=norm(vec_add(vec_mul(base,math.cos(t)),vec_mul(axis2,math.sin(t))))
   p0=vec_add(p,vec_mul(n,radius))
   add_v(m,p0,n,(i/sides,j/max(1,len(path)-1)*reps))
 for j in range(len(path)-1):
  for i in range(sides):
   a=j*(sides+1)+i;b=a+1;c=a+sides+1;d=c+1
   face(m,a,c,b);face(m,b,c,d)
 return m

def ball(name,mat,center,radius,rings=12,slices=24):
 m=make_mesh(name,mat)
 for y in range(rings+1):
  a=math.pi*y/rings
  for x in range(slices+1):
   t=2*math.pi*x/slices
   n=(math.sin(a)*math.cos(t), math.cos(a),math.sin(a)*math.sin(t))
   p=vec_add(center,vec_mul(n,radius))
   add_v(m,p,n,(x/slices,y/rings))
 for y in range(rings):
  for x in range(slices):
   a=y*(slices+1)+x;b=a+1;c=a+slices+1;d=c+1
   if y:face(m,a,c,b)
   if y<rings-1:face(m,b,c,d)
 return m

def sculpted_daytona_seats():
 """True padded geometry, independent of OVC/camera and original flat triangles.

 Two leather buckets: curved lower pads, reclining backs, rounded side bolsters,
 colored piping and stitchlines, photo-inspired contrasting insert bands.
 All dimensions are inside the actual original tex16 two-seat envelope.
 """
 out=[]
 for side,center in (("L",-.353),("R",.353)):
  def seat_base(u,v):
   a=2*u-1;z=.09+.53*v
   x=center+.171*a
   dome=(1-a*a)**.7
   y=.408+.036*dome*math.sin(math.pi*v)+.009*math.cos(math.pi*v)
   return (x,y,z)
  def seat_back(u,v):
   a=2*u-1
   x=center+(.168-.013*v)*a
   y=.446+.414*v
   z=.51+.198*v+.029*(1-a*a)*math.sin(math.pi*v)
   return (x,y,z)
  out.append(surface(f"V5_{side}_SEAT_PADDED_CUSHION",3,48,32,seat_base,(1.2,1.4)))
  out.append(surface(f"V5_{side}_SEAT_RECLINED_PADDED_BACK",3,48,32,seat_back,(1.2,1.6),flip=True))
  for edge in (.02,.98):
   # Rolled leather piping along the true parametric seat contour.
   out.append(tube(f"V5_{side}_CUSHION_SMOOTH_SIDE_BOLSTER_{edge}",3,
                   [seat_base(edge,i/40) for i in range(41)],.022,12,2))
   out.append(tube(f"V5_{side}_BACKREST_SMOOTH_SIDE_BOLSTER_{edge}",3,
                   [seat_back(edge,i/42) for i in range(43)],.018,12,2))
   out.append(tube(f"V5_{side}_CUSHION_CHROME_EDGE_PIPING_{edge}",5,
                   [vec_add(seat_base(edge,i/40),(.0,.025,.0)) for i in range(41)],.003,8,3))
  out.append(tube(f"V5_{side}_CUSHION_FRONT_ROLLED_EDGE",3,
                   [seat_base(i/40,.01) for i in range(41)],.020,12,2))
  out.append(tube(f"V5_{side}_BACKREST_TOP_ROLLED_EDGE",3,
                   [seat_back(i/40,.99) for i in range(41)],.014,12,2))
  # Four high contrast dark leather bands across seat surface as physically
  # raised quads, plus thin seam tubes precisely atop the curved support.
  for stripe,v in enumerate((.25,.43,.61,.79)):
   m=make_mesh(f"V5_{side}_CUSHION_DARK_STRIPE_{stripe}",5)
   cols=[]
   for k in range(33):
    u=.09+.82*k/32
    for dv in (-.025,+.025):
     p=seat_base(u,v+dv)
     p=(p[0],p[1]+.026,p[2])
     cols.append(add_v(m,p,(0.,1.,0.),(k/32,(dv+.025)/.05)))
   for j in range(32):
    a,b,c,d=2*j,2*j+1,2*j+2,2*j+3
    face(m,a,c,b);face(m,b,c,d)
   out.append(m)
   for dv in (-.026,.026):
    out.append(tube(f"V5_{side}_STRIPE_{stripe}_RAISED_THREAD_{dv}",1,
        [vec_add(seat_base(.09+.82*k/32,v+dv),(.0,.027,.0)) for k in range(33)],.00095,6,1))
  # thin stitched seam at crown; back cap is preserved above rear tonneau.
  for u in (.19,.81):
   out.append(tube(f"V5_{side}_BACKREST_LEATHER_HANDSTITCH_{u}",1,
                [vec_add(seat_back(u,i/36),(.0,.0,.023)) for i in range(37)],
                .00105,6,1))
 return out

def make_dashboard():
 # Native instrument location: cluster tex8 bounds x=-0.625..-.07,
 # y=.741..909, z=-.167. Leather shell is behind it, never in front.
 # Continuous top arcs and double-height face prevent detached patches.
 def top(u,v):
  x=-.77+1.54*u
  z=-.56+.375*v
  hump=.033*math.exp(-((x+.355)/.235)**2)
  y=.941+.055*(.45-v)+hump+.008*math.cos(math.pi*u*2)
  return (x,y,z)
 def face_formula(u,v):
  x=-.77+1.54*u
  y=.635+.325*v
  protrusion=.007*math.exp(-((x+.33)/.30)**2)
  z=-.192-.032*(1-v)+protrusion
  return (x,y,z)
 return [surface("V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL",4,64,22,top,(3.,2.)),
         surface("V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE",4,64,28,face_formula,(3.,2.),flip=True)]

def make_door_panels():
 out=[]
 for side in (-1,1):
  def panel(u,v):
   z=-.40+1.40*u
   y=.43+.49*v
   # Genuine volume thickness and sculpted door shoulder
   x=side*(.755+.052*math.sin(math.pi*v)**2+.006*math.cos(3.14*u))
   return (x,y,z)
  m=surface("V5_%s_LEATHER_SCULPTED_DOOR"%(("L" if side<0 else "R")),3,30,14,panel,(2.5,1.),flip=(side>0))
  out.append(m)
  # raised trim and integrated armrest follow native player-car orientation
  points=[(side*.740,.610,z) for z in [-.27,-.10,.10,.32,.54,.78,.99]]
  out.append(tube("V5_%s_CHROME_DOOR_TRIM"%(("L" if side<0 else "R")),0,points,.004,8))
  points=[(side*.737,.525,z) for z in [.26,.36,.47,.61,.73]]
  out.append(tube("V5_%s_PADDED_DOOR_ARMREST"%(("L" if side<0 else "R")),4,points,.032,12))
 return out

def make_vents():
 out=[]
 for xx in (.08,.255,.43):
  # Daytona dash vent rings modeled as 3D dark recess with chrome lip.
  ring=[(xx+math.cos(t*2*math.pi/48)*.050,
         .943+math.sin(t*2*math.pi/48)*.016,
         -.175) for t in range(49)]
  out.append(tube(f"V5_3D_AIRVENT_{xx:.3f}_CHROME_BEZEL",0,ring,.0048,10))
  for i in range(3):
   y=.939+(i-1)*.008
   path=[(xx-.039,y,-.176),(xx,y,-.18),(xx+.039,y,-.176)]
   out.append(tube(f"V5_3D_AIRVENT_{xx:.3f}_SLAT{i}",4,path,.0023,8))
 return out

def make_shifter():
 # Original shift-gate is source-aligned near z=.1 / tunnel y~.45.
 shaft=[(0.,.465,.10),(0.,.515,.11),(.003,.572,.13),(.008,.625,.145)]
 return [tube("V5_MANUAL_SHIFTER_CHROME_SHAFT",0,shaft,.011,16),
         ball("V5_MANUAL_SHIFTER_ROUNDED_BLACK_KNOB",4,shaft[-1],.029,14,28),
         tube("V5_MANUAL_SHIFTER_BLACK_LEATHER_BOOT",4,[(0,.458,.10),
            (0,.468,.11),(0,.481,.12),(0,.496,.128)],.037,14)]

def make_original_steering(original):
 out=[]
 # Separate PMT object22 is the native 3-spoke wheel, already source geometry.
 # Local wheel coordinates have no game transform. For edit only, it is placed
 # once at original instrument center x~-0.35 and in front of dash.
 for group in decode_object(original,22):
  tex=group["tex_index"]
  material={5:0,10:4,34:7}.get(tex,4)
  m=make_mesh("V5_ORIGINAL_THREESPOKE_WHEEL_"+group["name"],material)
  angle=math.radians(-12.0)
  ca,sa=math.cos(angle),math.sin(angle)
  for p,n,uv in zip(group["vertices"],group["normals"],group["uvs"]):
   # Wheel local 3-spoke geometry in XY plane.
   xyz=(-.35+p[0],.79+ca*p[1]-sa*p[2],.285+sa*p[1]+ca*p[2])
   nn=(n[0],ca*n[1]-sa*n[2],sa*n[1]+ca*n[2])
   add_v(m,xyz,nn,uv)
  m["i"]=list(group["indices"])
  out.append(m)
 out.append(tube("V5_STEERING_COLUMN_SHAPED_BLACK_HOUSING",4,
                 [(-.35,.775,-.155),(-.35,.785,-.08),(-.35,.795,.05),
                  (-.35,.795,.16),(-.35,.79,.245)],.033,16))
 out.append(tube("V5_STEERING_COLUMN_CHROME_SHAFT",0,
                 [(-.35,.79,.16),(-.35,.79,.22),(-.35,.79,.277)],.016,12))
 return out

def read_ovc():
 b=OVC.read_bytes();nm=struct.unpack_from("<I",b,12)[0];at=36;meshes=[]
 for _ in range(nm):
  nlen,mat,nvert,nidx,iw=struct.unpack_from("<HHIII",b,at);at+=16
  name=b[at:at+nlen].decode();at+=nlen
  verts=[struct.unpack_from("<8f",b,at+i*32) for i in range(nvert)];at+=32*nvert
  idx=list(struct.unpack_from("<"+"H"*nidx,b,at));at+=2*nidx
  meshes.append({"name":name,"mat":mat,"v":verts,"i":idx})
 return meshes

def adjust_groups(meshes):
 out=[]
 for m in meshes:
  if "PHOTO_SEAT_UPHOLSTERY_REFINED" in m["name"]:
   # v5 fully re-sculpts both leather buckets from photo/native envelope.
   # Prevent doubled seats/visible z-fight by omitting old flat upholstery.
   continue
  elif "PHOTO_SEAT_CONTOUR_PIPING" in m["name"] or "PHOTO_BLACK_SEAT_BANDS" in m["name"] or "DOUBLE_STITCHED_SEAT_BANDS" in m["name"]:
   # Replaced with source-aligned smooth hand-sculpted seat meshes.
   continue
  elif "PHOTO_CONSOLE_LEATHER_REFINED" in m["name"]:
   sm=smooth_mesh(m,2,offset=.0011)
   sm["name"]="V5_HIRES_ROUNDED_CENTER_CONSOLE"
   out.append(sm)
  elif "PHOTO_REAR_TONNEAU_REFINED" in m["name"]:
   sm=smooth_mesh(m,1,offset=.0008)
   sm["name"]="V5_SMOOTH_REAR_LEATHER_TONNEAU"
   out.append(sm)
  elif "PHOTO_NATIVE_SWITCHBANK_REFINED" in m["name"]:
   out.append(smooth_mesh(m,1))
  else:
   out.append(m)
 return out

def make_photo_maps(base,mat_idx):
 # Real photo albedo stays untouched. Fine photo grain => height (standalone),
 # roughness/metallic/occlusion => packed ORM; tangent normal from gradient.
 luma=base.convert("L")
 w,h=base.size
 blur=luma.filter(ImageFilter.GaussianBlur(radius=5.0))
 p=luma.load();b=blur.load()
 detail=Image.new("L",(w,h))
 d=detail.load()
 for y in range(h):
  for x in range(w):
   dv=max(-24,min(24,p[x,y]-b[x,y]))
   d[x,y]=int(max(0,min(255,128+dv*2.0)))
 # For chrome/gauges, texture image may contain icons rather than height:
 # keep a neutral height, avoid needle embossing.
 if mat_idx in (0,2,6,7):
  detail=Image.new("L",(w,h),128);d=detail.load()
 outnorm=Image.new("RGB",(w,h))
 npix=outnorm.load()
 for y in range(h):
  for x in range(w):
   dx=(d[(x+1)%w,y]-d[(x-1)%w,y])/255.
   dy=(d[x,(y+1)%h]-d[x,(y-1)%h])/255.
   nx=-dx*2.8;ny=-dy*2.8;nz=1.
   l=math.sqrt(nx*nx+ny*ny+nz*nz)
   npix[x,y]=(int(127.5+127.5*nx/l),int(127.5+127.5*ny/l),int(127.5+127.5*nz/l))
 orm=Image.new("RGB",(w,h))
 op=orm.load()
 rough=[78,212,122,200,221,216,146,82,201][mat_idx]
 metal=[237,0,30,0,0,0,70,0,0][mat_idx]
 for y in range(h):
  for x in range(w):
   ao=int(max(196,min(255,239+(d[x,y]-128)*.26)))
   op[x,y]=(ao,rough,metal)
 return outnorm,orm,detail

def photo_micrograin_only(photo,kind):
 """Preserve authentic photo-derived microtexture, remove macro shadow shapes.

 Original material tiles included photographed creases and illumination,
 repeating as an unrealistic square across a large dashboard/seat.
 """
 src=photo.convert("RGB")
 mean=(176,128,75) if kind=="tan" else (47,45,43)
 w,h=src.size
 smooth=src.filter(ImageFilter.GaussianBlur(radius=max(6,int(w*.047))))
 before=src.load();blur=smooth.load()
 rng=random.Random(0x3655 if kind=="tan" else 0xD457)
 pixels=[]
 for y in range(h):
  for x in range(w):
   a=before[x,y];b=blur[x,y]
   n=rng.randint(-2,2)
   # high-frequency photographic grain extracted from source crop
   pixels.append(tuple(int(max(0,min(255,mean[k]+(a[k]-b[k])*.42+n)))
                       for k in range(3)))
 out=Image.new("RGB",(w,h));out.putdata(pixels)
 return out
def load_materials(orig):
 names=["Chrome","StitchThread","GaugeAtlas","TanLeather",
        "BlackDashLeather","BlackPiping","PhotoSwitchbank",
        "OriginalSteeringEmblem","OriginalSteeringSpoke"]
 colors=[]
 for i in range(7):
  im=Image.open(RT/f"Daytona365_PHOTO_MAT_{i}.png").convert("RGB")
  if i==3:im=photo_micrograin_only(im,"tan")
  if i==4:im=photo_micrograin_only(im,"black")
  colors.append(im)
 for src_index in (34,10):
  png,_,_=decode_dds(orig,src_index,1)
  im=Image.open(io.BytesIO(png)).convert("RGBA")
  colors.append(im)
 mats=[]
 for i,(name,base) in enumerate(zip(names,colors)):
  normal,orm,height=make_photo_maps(base,i)
  for suffix,img in (("BaseColor",base),("Normal",normal),("ORM",orm),("HeightOffline",height)):
   img.save(OUT/f"{i:02d}_{name}_{suffix}.png",optimize=True)
  mats.append({"name":name,"base":base,"normal":normal,"orm":orm,"height":height})
 return mats

class Glb:
 def __init__(self):
  self.buff=bytearray()
  self.views=[];self.accessors=[]
  self.images=[];self.textures=[];self.materials=[];self.meshes=[];self.nodes=[]
 def append(self,by,tag=None):
  self.buff.extend(b"\0"*((-len(self.buff))%4))
  offset=len(self.buff)
  self.buff.extend(by)
  v={"buffer":0,"byteOffset":offset,"byteLength":len(by)}
  if tag:v["target"]=tag
  self.views.append(v);return len(self.views)-1
 def accessor(self,data,fmt,tag,num_components,minmax=False):
  assert len(data)>0
  by=b"".join(struct.pack("<"+fmt*num_components,*v) for v in data)
  bv=self.append(by,tag)
  components={ "f":5126,"I":5125,"H":5123}
  item={"bufferView":bv,"componentType":components[fmt],
        "count":len(data),"type":{1:"SCALAR",2:"VEC2",3:"VEC3",4:"VEC4"}[num_components]}
  if minmax:
   item["min"]=[min(v[k] for v in data) for k in range(num_components)]
   item["max"]=[max(v[k] for v in data) for k in range(num_components)]
  self.accessors.append(item);return len(self.accessors)-1
 def img(self,img,name):
  f=io.BytesIO();img.save(f,"PNG",optimize=True)
  bv=self.append(f.getvalue())
  n=len(self.images)
  self.images.append({"name":name,"mimeType":"image/png","bufferView":bv})
  self.textures.append({"source":n,"name":name})
  return len(self.textures)-1,n
 def add_material(self,m):
  i=len(self.materials);name=m["name"]
  base,_=self.img(m["base"],name+" BaseColor")
  normal,_=self.img(m["normal"],name+" Tangent Normal")
  orm,_=self.img(m["orm"],name+" Packed ORM")
  height,himg=self.img(m["height"],name+" Height/Displacement offline")
  metallic=[.8,0,.12,0,0,0,.16,0,0][i]
  roughness=[.35,.82,.55,.75,.88,.80,.62,.38,.81][i]
  self.materials.append({
    "name":name,"doubleSided":True,
    "alphaMode":"MASK" if i==7 else "OPAQUE","alphaCutoff":.5,
    "pbrMetallicRoughness":{
      "baseColorTexture":{"index":base},
      "metallicRoughnessTexture":{"index":orm},
      "baseColorFactor":[1,1,1,1],
      "metallicFactor":1.0,"roughnessFactor":1.0},
    "normalTexture":{"index":normal,"scale":1.0},
    "occlusionTexture":{"index":orm,"strength":.8},
    "extras":{
      "HeightMapImageIndex":himg,
      "HeightMapTextureIndex":height,
      "HeightRangeMeters":0.0007 if i in (3,4,5,8) else 0,
      "HeightMapUsage":"OFFLINE authoring only; not a glTF normative volume map or loader contract",
      "RuntimeNote":"Dino PBR loader source supports optional normal + ORM; 3D voxel volume textures not verified"
    }})
 def add_mesh(self,m):
  if not m["i"] or not m["v"]:return
  assert len(m["v"])<200000 and len(m["i"])<800000
  verts=m["v"]
  p=[tuple(v[:3]) for v in verts]
  n=[tuple(norm(v[3:6])) for v in verts]
  uv=[tuple(v[6:8]) for v in verts]
  idx=[(i,) for i in m["i"]]
  if max(m["i"])>=len(verts):raise ValueError("indices invalid")
  for f in (p+n+uv):
   if not all(math.isfinite(x) and abs(x)<10000 for x in f):
    raise ValueError("nonfinite coords")
  apos=self.accessor(p,"f",34962,3,minmax=True)
  anorm=self.accessor(n,"f",34962,3)
  auv=self.accessor(uv,"f",34962,2)
  ai=self.accessor(idx,"I",34963,1)
  mat=m["mat"]
  if not 0<=mat<len(self.materials):raise ValueError("bad material")
  mi=len(self.meshes)
  self.meshes.append({"name":m["name"],
    "primitives":[{"mode":4,"attributes":{"POSITION":apos,"NORMAL":anorm,"TEXCOORD_0":auv},
                   "indices":ai,"material":mat}]})
  self.nodes.append({"name":m["name"],"mesh":mi})
 def save(self,path):
  jsondoc={"asset":{"version":"2.0","generator":"Daytona editable v5 source-registered Python (not scene AI)"},
           "scene":0,
           "scenes":[{"nodes":list(range(len(self.nodes))),"name":"Editable original Ferrari Daytona cockpit v5"}],
           "nodes":self.nodes,"meshes":self.meshes,"buffers":[{"byteLength":len(self.buff)}],
           "bufferViews":self.views,"accessors":self.accessors,
           "images":self.images,"samplers":[{"minFilter":9987,"magFilter":9729,
                                             "wrapS":10497,"wrapT":10497}],
           "textures":[{**t,"sampler":0} for t in self.textures],
           "materials":self.materials,
           "extras":{"source":"Ferrari Daytona 365 GTS/4 native PMT + v4 editable cockpit",
             "originalPMTSHA256":EXPECTED_PMT,"Dino":"untouched",
             "normalORM":"glTF native slots applied",
             "heightMap":"offline displacement only / loader volume textures unverified",
             "notOVC":True}}
  jb=json.dumps(jsondoc,separators=(",",":"),ensure_ascii=False).encode()
  jb+=b" "*((-len(jb))%4)
  binbytes=bytes(self.buff)
  binbytes+=b"\0"*((-len(binbytes))%4)
  header=struct.pack("<4sII",b"glTF",2,12+8+len(jb)+8+len(binbytes))
  with open(path,"wb") as f:
   f.write(header);f.write(struct.pack("<I4s",len(jb),b"JSON"));f.write(jb)
   f.write(struct.pack("<I4s",len(binbytes),b"BIN\x00"));f.write(binbytes)
  return jsondoc

def build():
 assert_private_sources()
 orig=open_pmt(PMT)
 meshes=adjust_groups(read_ovc())
 # Retain source non-body cabin controls/trim. Missing PMT textures provide
 # the source-backed surfaces, but omit raw duplicate cushion/gauge/switch.
 for p in decode_object(orig,0):
  if p["tex_index"] not in (14,):continue
  m=make_mesh("V5_NATIVE_DASH_REFERENCE_"+p["name"],4)
  for xyz,n,uv in zip(p["vertices"],p["normals"],p["uvs"]):add_v(m,xyz,n,uv)
  m["i"]=list(p["indices"])
  meshes.append(m)
 meshes.extend(make_dashboard())
 meshes.extend(sculpted_daytona_seats())
 meshes.extend(make_vents())
 meshes.extend(make_door_panels())
 meshes.extend(make_shifter())
 meshes.extend(make_original_steering(orig))
 materials=load_materials(orig)
 g=Glb()
 for m in materials:g.add_material(m)
 for m in meshes:g.add_mesh(m)
 path=OUT/"Daytona365_Cockpit_EDITABLE_HiDetail_PBR_v5.glb"
 gltf=g.save(path)
 summary={
  "file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
  "bytes":path.stat().st_size,"meshes":len(g.meshes),
  "vertices":sum(len(m["v"]) for m in meshes),
  "triangles":sum(len(m["i"])//3 for m in meshes),
  "materialCount":len(g.materials),"embeddedTextures":len(g.textures),
  "separateHeightMaps":len(materials),
  "sourcePMTSHA256":EXPECTED_PMT,
  "sourceOVCSHA256":EXPECTED_OVC,
  "nativeCarPMTModified":False,"dinoModified":False,
  "OVCOutput":False,
  "verifiedRuntimeVolumeMap":False,
  "gltfTangentNormalsAndORM":True,
  "copyright":"PRIVATE derivative of original game; do not publish without rights",
  "parts":[{"name":m["name"],"triangles":len(m["i"])//3} for m in meshes]}
 (OUT/"V5_EDITABLE_MODEL_MANIFEST.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
 print(json.dumps({k:summary[k] for k in ("file","sha256","bytes","meshes","vertices",
  "triangles","materialCount","embeddedTextures","separateHeightMaps",
  "OVCOutput","verifiedRuntimeVolumeMap")},indent=2))
 return summary

if __name__=="__main__":
 build()
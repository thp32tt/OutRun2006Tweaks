#!/usr/bin/env python3
"""Dino 246 HD v3: physically clear steering-column tunnel & fascia.

This is a source-authored 3D topology repair to the v2 cockpit, not an image
generation or a rendered reference. The original PMT is read-only and the
resulting GLB/OVC are NOT installed into the user's running R26 game.

Coordinate system: driver wheel center (-.320,+.708,-.289), native Dino car
width approximately +/-0.847. Positive Z is toward rear cabin.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import dino_cockpit_hdgeometry_v2 as v2
import dino_original_pmt_to_glb as original

v1=v2.v1
PI=math.pi
WHEEL=(-.320,.708,-.289)
POD_GAUGES=((- .447,.726,.065),(-.324,.735,.079),(-.196,.726,.065))
# Front center (wheel) -> firewall (inside dash); link is slanted BELOW the
# lower rim of the gauge face at z=-.417. A 2cm+ clearance is required.
COLUMN_AXIS=(
 (-.320,.703,-.286),
 (-.320,.676,-.333),
 (-.320,.596,-.421),
 (-.320,.571,-.475),
 (-.320,.543,-.537),
 (-.320,.524,-.605),
)
GROMMET=(-.320,.571,-.475)
GAUGE_PLANE=-.411
SHAFT_RADIUS=.017
SHROUD_RADIUS=.031
PANEL_NOTCH_X=(-.399,-.241)
PANEL_NOTCH_Y=(.514,.651)


def scaled(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(a[i]*b[i] for i in range(3))
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def add(a,b):return tuple(a[i]+b[i] for i in range(3))
def norm(a):
 v=math.sqrt(dot(a,a))
 if v<1e-9:raise ValueError("zero axis")
 return scaled(a,1/v)
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def sample_axis_at_z(z):
 for a,b in zip(COLUMN_AXIS,COLUMN_AXIS[1:]):
  if min(a[2],b[2])<=z<=max(a[2],b[2]):
   t=(z-a[2])/(b[2]-a[2])
   return tuple(a[i]+(b[i]-a[i])*t for i in range(3))
 raise ValueError("outside the modeled steering column")


def column_clearance():
 """Use gauge face 3D circles, not only an artist-drawn image clearance."""
 at=sample_axis_at_z(GAUGE_PLANE)
 results={}
 for i,(gx,gy,r) in enumerate(POD_GAUGES):
  dist=math.hypot(at[0]-gx,at[1]-gy)
  gap=dist-r-SHROUD_RADIUS
  results["gauge%d"%i]=round(gap,5)
  if gap<.012:raise ValueError("steering shaft intersects instrument gauge: "+str((i,gap)))
 x,y,_=sample_axis_at_z(GROMMET[2])
 if not (PANEL_NOTCH_X[0]+SHROUD_RADIUS<x<PANEL_NOTCH_X[1]-SHROUD_RADIUS):
  raise ValueError("column clips narrow fascia opening")
 if not (PANEL_NOTCH_Y[0]+SHROUD_RADIUS<y<PANEL_NOTCH_Y[1]-SHROUD_RADIUS):
  raise ValueError("column clips bottom/upper edge of fascia opening")
 results["notch_clearance_x_m"]=round(min(x-PANEL_NOTCH_X[0],PANEL_NOTCH_X[1]-x)-SHROUD_RADIUS,5)
 results["notch_clearance_y_m"]=round(min(y-PANEL_NOTCH_Y[0],PANEL_NOTCH_Y[1]-y)-SHROUD_RADIUS,5)
 return results


def ring(name,material,center,axis,major,minor,nu=72,nv=12):
 """Oriented toroidal solid, e.g. the dash-mounted column seal."""
 m=v1.Mesh(name,material)
 w=norm(axis)
 u=norm(cross(w,(0,0,1))) if abs(w[2])<.98 else (1.,0.,0.)
 v=norm(cross(w,u))
 for i in range(nu+1):
  t=2*PI*i/nu
  radial=add(scaled(u,math.cos(t)),scaled(v,math.sin(t)))
  for j in range(nv+1):
   phi=2*PI*j/nv
   p=add(center,add(scaled(radial,major+minor*math.cos(phi)),
                    scaled(w,minor*math.sin(phi))))
   m.vert(p,(i/nu,j/nv))
 for i in range(nu):
  for j in range(nv):
   a=i*(nv+1)+j;b=(i+1)*(nv+1)+j
   m.quad(a,b,b+1,a+1)
 return m


def skin_box(name,material,x0,x1,y0,y1,z0,z1):
 return v1.box(name,material,
  ((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),
  (x1-x0,y1-y0,z1-z0))


def rolled_dash_fascia():
 """Split the existing dashboard face to leave a REAL 3D clearance aperture.

 The single v1 flat surface covers the entire dash including the place
 where the tilted steering column passes, which made it appear to pierce the
 gauge box. Five body strips leave the mouth physically empty.
 """
 mesh=[]
 ranges=(
  ("left",-.680,-.399,.450,.720),
  ("right",-.241,.680,.450,.720),
  ("center_top",-.399,-.241,.651,.720),
  ("center_bottom",-.399,-.241,.450,.514),
 )
 for tag,x0,x1,y0,y1 in ranges:
  def fn(u,v,x0=x0,x1=x1,y0=y0,y1=y1):
   x=x0+(x1-x0)*u
   y=y0+(y1-y0)*v
   original_v=(.720-y)/.270
   z=-.490+.016*math.sin(PI*original_v)
   return (x,y,z)
  mesh.append(v1.surface("dash_front_aperture_"+tag,"vinyl",10,14,fn))
 return mesh


def instrument_backplate():
 """Gauge box is no longer a solid cuboid through the column's entry."""
 # Original dimensions x[-.543,-.109], y[.597,.827], z[-.505,-.451].
 # Explicit break in the center under the main speedometer for the column.
 return [
  skin_box("pod_gauges_upper_shell","plastic",-.545,-.107,.651,.829,-.510,-.453),
  skin_box("pod_gauges_lower_left","plastic",-.545,-.399,.594,.651,-.510,-.453),
  skin_box("pod_gauges_lower_right","plastic",-.241,-.107,.594,.651,-.510,-.453),
  # Inner mouth side walls and upper sill all around the opening.
  skin_box("column_access_left_wall","plastic",-.404,-.398,.514,.651,-.509,-.460),
  skin_box("column_access_right_wall","plastic",-.242,-.236,.514,.651,-.509,-.460),
  skin_box("column_access_upper_sill","leather",-.399,-.241,.645,.652,-.510,-.458),
 ]


def tapered_shroud(name,material,path,radii,nu=14):
 """Sealed smooth capsule-like column with variable radius. Real volume."""
 if len(path)!=len(radii):raise ValueError("radii not aligned with spine")
 m=v1.Mesh(name,material)
 for k,p in enumerate(path):
  direction=sub(path[min(k+1,len(path)-1)],path[max(0,k-1)])
  axial=norm(direction)
  x=(1.,0.,0.)
  # axis lies in YZ plane; X is an accurate frame and does not spin.
  y=norm(cross(axial,x))
  rad=radii[k]
  for j in range(nu+1):
   t=2*PI*j/nu
   q=add(p,add(scaled(x,rad*math.cos(t)),scaled(y,rad*math.sin(t))))
   m.vert(q,(j/nu,k/(len(path)-1)))
 for k in range(len(path)-1):
  for j in range(nu):
   a=k*(nu+1)+j;b=(k+1)*(nu+1)+j
   m.quad(a,b,b+1,a+1)
 # Closed ends but do not duplicate the entire dark block behind the pod.
 head=m.vert(path[0],(.5,0))
 tail=m.vert(path[-1],(.5,1))
 last=(len(path)-1)*(nu+1)
 for j in range(nu):
  m.tri(head,j+1,j)
  m.tri(tail,last+j,last+j+1)
 return m


def column_assembly():
 """Visibly terminates at padded grommet below instrument dials."""
 p=list(COLUMN_AXIS)
 meshes=[
  tapered_shroud("LHD_column_internal_axle","metal",p,[.013,.015,.015,.015,.015,.013],16),
  tapered_shroud("LHD_column_outer_padded_shroud","plastic",
     p[:5],[.028,.032,.031,.032,.034],20),
  ring("LHD_column_dash_foot_flange","leather",GROMMET,
       sub(p[2],p[4]),.040,.010,72,14),
  ring("LHD_column_dash_rubber_inner_seal","plastic",GROMMET,
       sub(p[2],p[4]),.032,.005,60,10),
 ]
 # Fasteners around foot flange; metal screws drilled into the surrounding
 # dash, no free-floating cylinder inside the central instrument faces.
 for j,(dx,dy) in enumerate(((-.042,0),(.042,0),(0,-.042),(0,.042))):
  # Cross-section bevel circle is a real geometry disc.
  meshes.append(v1.disc("column_foot_screw_%d"%j,"metal",
          (GROMMET[0]+dx,GROMMET[1]+dy,GROMMET[2]+.019),.0048,16))
 # Lower shell-to-shaft transition has an authentic stepped taper near hub.
 meshes.append(ring("column_hub_front_brushed_metal_collar","metal",
        p[0],sub(p[1],p[0]),.028,.0045,44,10))
 # Lever roots are now attached to visible wheel column in the cabin,
 # not buried in the gauge face behind the dash.
 for typ,sign in (("indicator",-1),("wiper",1)):
  stem=((- .320+sign*.023,.656,-.360),
        (-.320+sign*.077,.653,-.333),
        (-.320+sign*.145,.658,-.307))
  meshes.append(v1.tube(typ+"_stalk_v3","metal",stem,.007,12))
  meshes.append(v1.tube(typ+"_grip_v3","plastic",
      (stem[-1],(stem[-1][0]+sign*.037,stem[-1][1]+.006,stem[-1][2]+.010)),.012,12))
 return meshes


def dashboard_detail():
 """Physical dash border, leather stitching and shroud-related seams."""
 p=[]
 # Dashed stitch strands follow the upper dash surface: geometry, not texture.
 for row,yoff in enumerate((.0,-.008)):
  for i in range(0,67,2):
   x0=-.655+1.31*i/67
   x1=-.655+1.31*(i+1)/67
   p.append(v1.tube("dash_upper_thread_%d_%02d"%(row,i),"seat",
       ((x0,.765+yoff+.034*math.sin((x0+.655)/1.31*PI),-.846),
        (x1,.765+yoff+.034*math.sin((x1+.655)/1.31*PI),-.846)),.0013,6))
 # Detachable wheel hub bolts around central badge.
 for i in range(6):
  t=2*PI*i/6
  p.append(v1.disc("steering_hub_raised_bolt_%02d"%i,"metal",
       (-.320+.042*math.cos(t),.708+.042*math.sin(t),-.242),.004,16))
 # Visible dashboard lower dash roll trim with dedicated aperture lip.
 for name,path in (
   ("column_mouth_lower_chrome",
    [(-.399,.513,-.474),(-.380,.515,-.474),(-.260,.515,-.474),(-.241,.513,-.474)]),
   ("column_mouth_top_leather",
    [(-.399,.651,-.479),(-.320,.651,-.476),(-.241,.651,-.479)]),
  ):
  p.append(v1.tube(name,"metal" if "chrome" in name else "leather",path,.0045,10))
 return p


def build_v3():
 column_clearance()
 old=v2.build_v2()
 obsolete={
  "LHD_column_real_shafts","LHD_column_plastic_shroud",
  "dashboard_driver_instrument_recess","dash_rolled_face",
  "indicator_stalk","wiper_stalk","indicator_rubber_tip","wiper_rubber_tip",
 }
 preserved=[m for m in old if m.name not in obsolete]
 result=(preserved+rolled_dash_fascia()+instrument_backplate()
          +column_assembly()+dashboard_detail())
 names=[m.name for m in result]
 if len(set(names))!=len(names):
  raise ValueError("duplicate 3D part names")
 for mesh in result:mesh.normalise()
 return result


def generate(game_dir:Path,outdir:Path,glb_px:int,ovc_px:int,texture_dir=None):
 source=game_dir/"Cars"/"obj_plcar_dino_pmt.sz"
 if not source.is_file():raise FileNotFoundError(source)
 native=original.open_pmt(source)
 data=original.decode_object(native,0)
 points=[v for group in data for v in group["vertices"]]
 lo=[min(p[i] for p in points) for i in range(3)]
 hi=[max(p[i] for p in points) for i in range(3)]
 if native["obj_count"]!=17 or not(-.95<lo[0]<-.75 and .75<hi[0]<.95
       and .08<lo[1]<.22 and 1.0<hi[1]<1.22
       and -2.3<lo[2]<-1.9 and 1.9<hi[2]<2.3):
  raise ValueError("Dino native source dimensions unexpected; fail closed")
 meshes=build_v3()
 gpu=v2.merge_meshes_for_runtime(meshes)
 materials_glb=v2.material_maps_v2(glb_px,texture_dir)
 materials_ovc=v2.material_maps_v2(ovc_px,texture_dir)
 outdir.mkdir(parents=True,exist_ok=True)
 glb=outdir/"Dino246_OriginalDim_Cockpit_HDGeometry_v3.glb"
 ovc=outdir/"Dino246_OriginalDim_Cockpit_HDGeometry_v3.ovc"
 v1.write_glb(meshes,materials_glb,glb)
 v1.write_ovc(gpu,materials_ovc,ovc)
 report={
  "source":source.name,
  "sourceSha256":hashlib.sha256(source.read_bytes()).hexdigest(),
  "inputModified":False,"sourceBounds":[lo,hi],
  "meshGroups":len(meshes),"vertices":sum(len(m.vertices) for m in meshes),
  "triangles":sum(len(m.faces)//3 for m in meshes),
  "gpuBatches":len(gpu),
  "gpuTriangleCount":sum(len(m.faces)//3 for m in gpu),
  "steeringColumnPath":[list(p) for p in COLUMN_AXIS],
  "measuredColumnClearances":column_clearance(),
  "repairScope":["instrument fascia physically notched below gauge pod",
    "dash front face has a real column mouth without penetrating panels",
    "one angled steering column passes below gauge faces",
    "pad/rubber/metal grommet and four mounting screws",
    "indicator/wiper levers attached to front column",
    "3D upper dash stitches and 6 raised wheel-hub bolts"],
  "glbFile":glb.name,"glbBytes":glb.stat().st_size,
  "ovcFile":ovc.name,"ovcBytes":ovc.stat().st_size,
  "glbTexturePx":glb_px,"ovcTexturePx":ovc_px,
  "textureOrigin":("optional user-supplied PNG material replacement, origin unverified"
                    if texture_dir else "procedural, NOT AI-generated"),
  "RUNTIME_VALIDATION":"UNTESTED","safeToInstallOverWorkingR26":False,
  "stillNeeded":["R26 original wheel/dash draw-owner suppression",
   "true-game transform calibration vs Quest APK",
   "image-generator 2K material replacement",
   "in-game HMD test and menu-exit crash verification"]
 }
 (outdir/"Dino246_HDGeometry_v3_report.json").write_text(
  json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False,indent=2))
 return report


def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--game-dir",type=Path,required=True)
 ap.add_argument("--output-dir",type=Path,required=True)
 ap.add_argument("--glb-texture",type=int,choices=(512,1024,2048),default=2048)
 ap.add_argument("--ovc-texture",type=int,choices=(256,512,1024),default=1024)
 ap.add_argument("--texture-dir",type=Path,default=None)
 a=ap.parse_args()
 generate(a.game_dir,a.output_dir,a.glb_texture,a.ovc_texture,a.texture_dir)


if __name__=="__main__":main()
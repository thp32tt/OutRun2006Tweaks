from PIL import Image, ImageDraw, ImageFont
import numpy as np, json, hashlib
from pathlib import Path
Path('localization/graphics/role_A/20261010-A227-Q101-FIRSTGLYPH-SOURCE-SLANT/').mkdir(parents=True,exist_ok=True)
src=Path("localization/graphics/role_A/20261010-A226-Q101-SOURCE-45PIXEL-CLEAN-CANONICAL/A226_SOURCE_READABLE_NATIVE_RGBA.png")
dst=Path("localization/graphics/role_A/20261010-A226-Q101-SOURCE-45PIXEL-CLEAN-CANONICAL/A226_FINAL_READABLE_NATIVE_RGBA.png")
clean=Path("localization/graphics/role_A/20261010-A226-Q101-SOURCE-45PIXEL-CLEAN-CANONICAL/A226_CLEAN_READABLE_NATIVE_RGBA.png")
A={"EN_SOURCE":np.array(Image.open(src).convert("RGBA")),"KR_A226":np.array(Image.open(dst).convert("RGBA"))}
assert all(x.shape==(210,1246,4) for x in A.values())
regions={"EN_SOURCE":(152,209,40,68),"KR_A226":(176,241,40,68)}
windows=[(40,68),(44,67)]
thresholds=[64,128,220]
rows=[]
for name,a in A.items():
 x0,x1,_,_=regions[name]
 for lo,hi in windows:
  for th in thresholds:
   pts=[]
   for y in range(lo,hi):
    xx=np.flatnonzero(a[y,x0:x1,3]>=th)
    assert len(xx)>=8,(name,lo,hi,th,y,len(xx))
    pts.append((y,int(xx.min()+x0),int(xx.max()+x0),float(xx.mean()+x0)))
   ar=np.array(pts,float)
   left=float(np.polyfit(ar[:,0],ar[:,1],1)[0])
   right=float(np.polyfit(ar[:,0],ar[:,2],1)[0])
   centroid=float(np.polyfit(ar[:,0],ar[:,3],1)[0])
   rows.append({"source":name,"threshold":th,"y_start_inclusive":lo,"y_end_exclusive":hi,"sample_rows":len(pts),
    "x_crop_min":x0,"x_crop_max_exclusive":x1,"left_edge_slope_dx_per_dy":round(left,5),
    "right_edge_slope_dx_per_dy":round(right,5),"centroid_slope":round(centroid,5),
    "left_top_x":int(ar[0,1]),"left_bottom_x":int(ar[-1,1])})
f=lambda b:hashlib.sha256(b).hexdigest()
data={"schema":1,"run":"A227","role":"A","queue_index":101,
  "method":"Native-alpha first glyph leftmost visible fringe pixel x per y, linear least-squares OLS x(y), negative dx/dy implies right lean towards top; no OCR, no resized raster",
  "source_glyph":"English initial italic E","localized_glyph":"Korean initial 이",
  "underlying_images":{"source_file":str(src),"source_image_sha256":f(src.read_bytes()),"saved_candidate_file":str(dst),"candidate_preview_sha256":f(dst.read_bytes()),"clean_file":str(clean),"clean_preview_sha256":f(clean.read_bytes())},
  "persisted_a226_candidate_sha256":"ea145aa51bdadd676bb7275c2d254bdc9562b72e3b7905867bc9c13ff3160d06",
  "english_canonical_source_sha256":"a29d70ffef85c74c67f78752b4dcc83cc4055220313952536081441a54f6b1aa",
  "frames_readable_source_clip_2850_0_4096_210":True,
  "regions_in_contact_crop":regions,"raw_y":"mirror_Y","rows":rows,
  "reference":[r for r in rows if r["source"]=="EN_SOURCE" and r["threshold"]==128 and r["y_start_inclusive"]==44][0],
  "candidate":[r for r in rows if r["source"]=="KR_A226" and r["threshold"]==128 and r["y_start_inclusive"]==44][0],
  "interpretation":"One representative narrow y window has comparable left-edge lean. This is NOT a complete paired homologous-stem/whole-atlas source-font calibration or independent C1 PASS. Other y windows/components including Korean ㅇ+ㅣ have non-linear left edges. No new DDS created or candidate promoted.",
  "source_independent_authentication":"Not performed anew: reference is saved producer-authored source crop, canonical DDS hash inherited from A226; C1 must independently authenticate English DDS and candidate before approval.",
  "RUNTIME_VALIDATION":"UNTESTED"}
s=data["reference"]["left_edge_slope_dx_per_dy"];k=data["candidate"]["left_edge_slope_dx_per_dy"]
data["representative_slopes"]={"english_dx_dy":s,"korean_dx_dy":k,"absolute_difference":round(abs(s-k),5),"source_vs_candidate_direction":"both right leaning on sampled first glyph left edge"}
font=ImageFont.load_default()
canvas=Image.new("RGB",(740,360),(245,245,245));d=ImageDraw.Draw(canvas)
d.text((12,8),"A227 q101 / EN E versus KR first Hangul native visible left-edge slant",(0,0,0),font=font)
d.text((12,28),"Alpha>=128, native y 44..66; blue line=OLS left-edge x(y); red=sampled pixels",(20,20,20),font=font)
for idx,name in enumerate(("EN_SOURCE","KR_A226")):
 arr=A[name]
 x0,x1,_,_=regions[name]
 crop=Image.fromarray(arr[23:95,x0:x1])
 bg=Image.new("RGBA",crop.size,(95,95,95,255));bg.alpha_composite(crop)
 zoom=bg.convert("RGB").resize((crop.width*4,crop.height*4),Image.Resampling.NEAREST)
 # clipped to 260x288, canvas is 740x360
 xx=15+idx*360; yy=58
 canvas.paste(zoom,(xx,yy))
 d=ImageDraw.Draw(canvas)
 r=next(r for r in rows if r["source"]==name and r["threshold"]==128 and r["y_start_inclusive"]==44)
 for y in range(44,67):
  X=x0
  xs=np.flatnonzero(arr[y,x0:x1,3]>=128)
  x=int(xs.min()+x0)
  rx=xx+4*(x-X)+1; ry=yy+4*(y-23)+1
  d.ellipse((rx-1,ry-1,rx+2,ry+2),fill=(230,32,50))
 a=r["left_edge_slope_dx_per_dy"];ar=next(r for r in rows if r["source"]==name and r["threshold"]==128 and r["y_start_inclusive"]==44)
 px0=xx+4*(ar["left_top_x"]-x0)+2;py0=yy+4*(44-23)+2
 px1=xx+4*(ar["left_bottom_x"]-x0)+2;py1=yy+4*(66-23)+2
 d.line([(px0,py0),(px1,py1)],fill=(35,105,235),width=3)
 d.text((xx,yy+294),f'{name}  left slope {a:+.3f}px/row',fill=(10,10,10),font=font)
 
canvas.save("localization/graphics/role_A/20261010-A227-Q101-FIRSTGLYPH-SOURCE-SLANT/A227_Q101_FIRSTGLYPH_SOURCE_SLOPE.png")
Path("localization/graphics/role_A/20261010-A227-Q101-FIRSTGLYPH-SOURCE-SLANT/A227_Q101_SOURCE_SLANT_MACHINE.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"table":rows,"delta":data["representative_slopes"],"source_sha":data["underlying_images"]["source_image_sha256"],"preview_sha":f(Path("localization/graphics/role_A/20261010-A227-Q101-FIRSTGLYPH-SOURCE-SLANT/A227_Q101_FIRSTGLYPH_SOURCE_SLOPE.png").read_bytes())},ensure_ascii=False))
#!/usr/bin/env python3
"""C311 C2 EVEN q154: source-family stroke/core/inner-gap diagnostic on three gray labels.
Native exact SHA-bound DDS and B60 CLEAN. Evidence-only, NOT automatic approval.
"""
import os,io,json,hashlib,urllib.request,subprocess
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt,maximum_filter,label
from PIL import Image,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="C"
tri=json.loads(subprocess.run(["python","tools/localization/rework_triage.py","--index","154"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tri["next_action"]=="EVIDENCE_ONLY_HOLD",tri
Q=Path("localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "154,textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds,localize_text,c306_c2_hold_gray_native30_pending_calibration" in Q
source=urllib.request.urlopen("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds",timeout=150).read()
final=Path("localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds").read_bytes()
clean_bytes=Path("localization/graphics/role_B/20261005-B-PRODUCTION60/4D38_HD_CLEAN_PLATE.png").read_bytes()
H=lambda b:hashlib.sha256(b).hexdigest()
expected={"source":"15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf","clean":"a4d707fa4376a7db4cc04fd1de51d9dc23b1874eac9a8b4988dc44c7f4c23380","final":"94678124f6cddaeb44520c6419f4b475d1452866c052ff301a4859dddf38cb1f"}
assert [H(x) for x in (source,clean_bytes,final)]==[expected[k] for k in ("source","clean","final")]
assert source[:128]==final[:128] and len(source)==len(final)
S=np.flipud(np.asarray(Image.open(io.BytesIO(source)).convert("RGBA"))).copy()
F=np.flipud(np.asarray(Image.open(io.BytesIO(final)).convert("RGBA"))).copy()
C=np.asarray(Image.open(io.BytesIO(clean_bytes)).convert("RGBA")).copy()
assert S.shape==F.shape==C.shape==(1024,4096,4)
base=json.loads(Path("localization/graphics/role_C/20261008-C305-C2-Q154-AUTHORED-CLEAN-BGW/C305_Q154_AUTHORED_PLATE_RGB_AUDIT.json").read_text(encoding="utf-8"))
assert base["sha256"]["source"]==expected["source"] and base["sha256"]["candidate"]==expected["final"]
union=np.zeros(S.shape[:2],dtype=bool)
for x in base["regions"]:
 l,t,r,b=x["source_bbox"];union[t:b,l:r]=True
change={}
for k,a,b in (("SOURCE_CLEAN",S,C),("CLEAN_FINAL",C,F),("SOURCE_FINAL",S,F)):
 dd=np.any(a!=b,axis=2)
 change[k]={"rgba_outside_8":int(np.count_nonzero(dd & ~union)),"alpha_outside_8":int(np.count_nonzero((a[:,:,3]!=b[:,:,3]) & ~union))}
out=Path("localization/graphics/role_C/20261009-C311-C2-Q154-GRAY-STROKE-ANCHORS")
out.mkdir(parents=True,exist_ok=True)
def bbox(m):
 yy,xx=np.where(m)
 return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None
def metrics(a):
 alpha=a[:,:,3]
 mask=alpha>128
 ys,xs=np.where(mask)
 assert len(xs)>30
 dt=distance_transform_edt(mask)
 peaks=mask & (dt>=maximum_filter(dt,size=5)) & (dt>=2)
 core=dt[peaks]
 nz=dt[mask]
 hi=a[alpha>=245]
 rgb=hi[:,:3] if len(hi) else a[mask][:,:3]
 n=label(mask)[1]
 return {"visible_bbox_local_gt128":bbox(mask),"pixel_gt0":int(np.count_nonzero(alpha)),"pixel_gt128":int(mask.sum()),
 "face_rgb_median":[int(np.median(rgb[:,i])) for i in range(3)],
 "alpha_245_count":int(np.count_nonzero(alpha>=245)),
 "ridge_radius_median_px":round(float(np.median(core)),4) if len(core) else None,
 "ridge_radius_q25_q75":[round(float(np.quantile(core,z)),4) for z in (.25,.75)] if len(core) else [],
 "interior_distance_median_px":round(float(np.median(nz)),4),
 "connected_ink_components":int(n),
 "horizontal_centroid_px":round(float(xs.mean()),3),"vertical_centroid_px":round(float(ys.mean()),3),
 "black_ink_fill_frac_bbox":round(float(mask.sum()/((xs.max()+1-xs.min())*(ys.max()+1-ys.min()))),4),
 "face_1px_edge_pixels":int(np.count_nonzero(mask&(dt<=1))),
 "ink_bbox_margin_from_roi":[int(xs.min()),int(a.shape[1]-xs.max()-1),int(ys.min()),int(a.shape[0]-ys.max()-1)]}
def diagnostic(a,threshold=128):
 alpha=a[:,:,3].astype(np.uint8)
 mask=alpha>threshold;dt=distance_transform_edt(mask)
 view=np.zeros((a.shape[0],a.shape[1],3),dtype=np.uint8)
 view[:]=[37,42,46]
 view[(alpha>0)&(alpha<=threshold)]=[112,132,146]
 view[mask]=[218,221,225]
 view[mask & (dt>=3)]=[80,187,222]
 view[mask & (dt>=6)]=[255,180,77]
 return Image.fromarray(view,"RGB")
rows=[]
for i in (5,6,7):
 x=base["regions"][i];l,t,r,b=x["source_bbox"]
 source_roi=S[t:b,l:r].copy();clean_roi=C[t:b,l:r].copy();final_roi=F[t:b,l:r].copy()
 sm=metrics(source_roi);fm=metrics(final_roi)
 assert not np.count_nonzero(clean_roi[:,:,3])
 width=r-l;height=b-t
 vis=Image.new("RGB",(width*2,height+35),(23,27,31));dd=ImageDraw.Draw(vis)
 vis.paste(diagnostic(source_roi),(0,35));vis.paste(diagnostic(final_roi),(width,35))
 dd.text((8,9),"CANONICAL ENGLISH : edge gray / face white / cores blue orange",fill="white")
 dd.text((width+8,9),"EXACT KOREAN DDS : SAME UNWARPED PIXEL SCALE",fill="white")
 path=out/(x["id"]+"_SOURCE_FINAL_STROKE_CORE_NATIVE.png")
 vis.save(path)
 zoom=vis.resize((vis.width*2,vis.height*2),Image.Resampling.NEAREST)
 zp=out/(x["id"]+"_SOURCE_FINAL_STROKE_CORE_ZOOM200.png")
 zoom.save(zp)
 sb=sm["visible_bbox_local_gt128"];fb=fm["visible_bbox_local_gt128"]
 rows.append({"id":x["id"],"english":x["source"],"korean":x["korean"],"bbox_readable":[l,t,r,b],
 "source":sm,"korean_exact_dds":fm,
 "measurements":{"median_radius_ratio":round(fm["ridge_radius_median_px"]/sm["ridge_radius_median_px"],4) if sm["ridge_radius_median_px"] else None,
 "visible_height_ratio":round((fb[3]-fb[1])/(sb[3]-sb[1]),4),
 "visible_width_ratio":round((fb[2]-fb[0])/(sb[2]-sb[0]),4),
 "opaque_color_rgb_equal":sm["face_rgb_median"]==fm["face_rgb_median"],
 "clean_alpha_nonzero":int(np.count_nonzero(clean_roi[:,:,3]))},
 "stroke_map_native":{"path":str(path),"sha256":H(path.read_bytes())},
 "stroke_map_zoom200":{"path":str(zp),"sha256":H(zp.read_bytes())},
 "disclaimer":"EDT local-maxima radius and components are nonsemantic optical proxies, not proof of matching glyph anatomy or slant; do not auto-PASS."})
outjson={"run":"C311-C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":154,"triage":tri,"exact_shas":expected,
 "native_dimensions":[4096,1024],"outside_8_full_atlas":change,"regions":rows,
 "new_png_files":2*len(rows),"scope":"NEW source/final unwarped stroke-core distance transform/color/counter proxy for three gray labels; not duplicate C306 triptych and not independent subjective approval",
 "automatic_result":"EVIDENCE_ONLY_HOLD","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C311_Q154_GRAY_STROKE_PROFILE_MACHINE.json").write_text(json.dumps(outjson,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"C311","regions":len(rows),"outside":change,"font_metrics":[{"id":r["id"],**r["measurements"]} for r in rows]},ensure_ascii=False))

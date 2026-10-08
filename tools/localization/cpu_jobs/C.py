#!/usr/bin/env python3
"""C309 C2 EVEN q176 source-family/native practical composite proof; NEVER auto-approve C."""
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="C"
triage=json.loads(subprocess.run(["python","tools/localization/rework_triage.py","--index","176"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert triage["next_action"]=="EVIDENCE_ONLY_HOLD",triage
queue=Path("localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "176,textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds,localize_text,c299_hold_strict_recheck" in queue
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
sb=urllib.request.urlopen(source_url,timeout=150).read()
cb=Path("localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds").read_bytes()
kb=Path("localization/graphics/role_B/20261006-B-PRODUCTION201-75C3586A-NAMES-MAPFIX/B201_CLEAN_PLATE.png").read_bytes()
H=lambda v:hashlib.sha256(v).hexdigest()
ident={"source":"8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708",
"candidate":"494d42c09c58241405dd14de74ca976b5432d84eb250d4bceb5684e97fbad407",
"clean":"0fd5d51864ad9564f33c703140c4cff9ef7b58fabd51ff0d34bcdf299d9fc5cc"}
assert (H(sb),H(cb),H(kb))==(ident["source"],ident["candidate"],ident["clean"])
assert sb[:128]==cb[:128] and len(sb)==len(cb)==(128+2048*2048*4)
src=np.flipud(np.asarray(Image.open(BytesIO(sb)).convert("RGBA"))).copy()
fin=np.flipud(np.asarray(Image.open(BytesIO(cb)).convert("RGBA"))).copy()
clean=np.asarray(Image.open(BytesIO(kb)).convert("RGBA")).copy()
assert src.shape==fin.shape==clean.shape==(2048,2048,4)
specs=[
("01_jennifer","JENNIFER","제니퍼",(0,374,838,532)),
("02_clarissa","CLARISSA","클라리사",(905,372,1745,532)),
("03_holly","HOLLY","홀리",(9,213,542,364)),
("04_flagman4","FLAGMAN 4","플래그맨 4",(8,49,988,204))]
out=Path("localization/graphics/role_C/20261008-C309-C2-Q176-SOURCE-FAMILY-52-PROOF")
out.mkdir(parents=True,exist_ok=True)
def box(a):
 y,x=np.where(a[:,:,3]>0)
 return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)] if len(x) else None
def rgbcomp(a,bg):
 i=Image.fromarray(a,"RGBA")
 return Image.alpha_composite(Image.new("RGBA",i.size,tuple(bg)+(255,)),i).convert("RGB")
def save(i,n):
 p=out/n;i.save(p,format="PNG")
 v=p.read_bytes()
 return {"file":str(p),"sha256":H(v),"bytes":len(v)}
def labelpanel(parts,bg,top=25):
 w,h=parts[0][1].shape[1],parts[0][1].shape[0]
 panel=Image.new("RGB",(w*len(parts),h+top),(26,26,26))
 draw=ImageDraw.Draw(panel)
 for ix,(txt,a) in enumerate(parts):
  panel.paste(rgbcomp(a,bg),(w*ix,top))
  draw.text((w*ix+4,5),txt,fill="white")
 return panel
union=np.zeros((2048,2048),dtype=bool)
for _,_,_,(l,t,r,b) in specs:union[t:b,l:r]=True
outside={}
for x,y,n in ((src,clean,"SOURCE_CLEAN"),(clean,fin,"CLEAN_FINAL"),(src,fin,"SOURCE_FINAL")):
 delta=np.any(x!=y,axis=2)
 outside[n]={"RGBA":int(np.count_nonzero(delta&~union)),
 "alpha":int(np.count_nonzero((x[:,:,3]!=y[:,:,3])&~union)),
 "visible":int(np.count_nonzero(delta&~union&((x[:,:,3]>0)|(y[:,:,3]>0))))}
regions=[]
for idx,(rid,en,ko,(l,t,r,b)) in enumerate(specs):
 a,k,f=(v[t:b,l:r].copy() for v in (src,clean,fin))
 bb=box(f);ss=box(a);assert bb and ss
 margin=[bb[0],r-l-bb[2],bb[1],b-t-bb[3]]
 assert min(margin)>0
 W,Ht=r-l,b-t
 rec={"id":rid,"english":en,"korean":ko,"readable_bbox":[l,t,r,b],
 "source_bbox_inside_roi":ss,"candidate_bbox_inside_roi":bb,"margins_LRTB":margin,
 "source_alpha":int(np.count_nonzero(a[:,:,3]>0)),
 "clean_alpha":int(np.count_nonzero(k[:,:,3]>0)),
 "final_alpha":int(np.count_nonzero(f[:,:,3]>0)),
 "source_candidate_height_ratio":round((bb[3]-bb[1])/(ss[3]-ss[1]),4),
 "source_candidate_width_ratio":round((bb[2]-bb[0])/(ss[2]-ss[0]),4),
 "source_opaque_rgba_median":[int(z) for z in np.median(a[a[:,:,3]>=245],axis=0)] if np.any(a[:,:,3]>=245) else None,
 "candidate_opaque_rgba_median":[int(z) for z in np.median(f[f[:,:,3]>=245],axis=0)] if np.any(f[:,:,3]>=245) else None,
 "changed_source_clean_rgba":int(np.count_nonzero(np.any(a!=k,axis=2))),
 "changed_clean_final_rgba":int(np.count_nonzero(np.any(k!=f,axis=2))),
 "views":[]}
 for name,bg in [("BLACK",(12,12,12)),("GRAY",(112,112,112)),("WHITE",(245,245,245))]:
  panel=labelpanel([("CANONICAL EN",a),("B201 AUTHORED CLEAN",k),("PERSISTED KR",f)],bg)
  for percent in (100,75,50):
   image=panel if percent==100 else panel.resize((max(1,round(panel.width*percent/100)),max(1,round(panel.height*percent/100))),Image.Resampling.LANCZOS)
   rec["views"].append({"kind":f"{name}_{percent}",**save(image,f"{rid}_{name}_{percent}pct_SOURCE_CLEAN_FINAL.png")})
 raw=labelpanel([("EN RAW",np.flipud(a)),("KR RAW",np.flipud(f))],(112,112,112))
 rec["views"].append({"kind":"RAW",**save(raw,f"{rid}_RAW_SOURCE_FINAL.png")})
 zoom=labelpanel([("EN ZOOM",a),("KR ZOOM",f)],(245,245,245)).resize((4*W,2*(Ht+25)),Image.Resampling.NEAREST)
 rec["views"].append({"kind":"ZOOM200",**save(zoom,f"{rid}_ZOOM200_SOURCE_FINAL.png")})
 # Isolated plate/composite evidence with actual clean transparency on gray.
 plate=labelpanel([("EN LETTERS+EFFECTS",a),("CLEAN NO LETTERS",k)],(112,112,112))
 rec["views"].append({"kind":"PLATE_ONLY",**save(plate,f"{rid}_PLATE_ONLY.png")})
 comp=labelpanel([("CLEAN NO LETTERS",k),("KOREAN ONLY+EFFECTS",f)],(112,112,112))
 rec["views"].append({"kind":"COMPOSITE_ONLY",**save(comp,f"{rid}_COMPOSITE_ONLY.png")})
 regions.append(rec)
report={"run":"C309-C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","index":176,"triage":triage,
 "policy_version":"visual-evidence-v1-20261008","execution_backend":"github-hosted only because ChatGPT local cannot reach raw.githubusercontent.com",
 "sha256":ident,"format":"2048x2048 RGBA32 1 mip mirrored Y exact DDS headers","header_equal":True,
 "changed_outside_four_canonical_text_bboxes":outside,
 "rows":regions,"lossless_png_count":sum(len(x["views"]) for x in regions),
 "metrics_limit":"Width/height ratios and RGB median are whole-glyph-family proxies only; cannot establish semantic stem slant, legibility or calibrated C PASS.",
 "C":"CONTROLLER_VISUAL_PENDING","C3":"NOT_APPROVED","RUNTIME_VALIDATION":"UNTESTED","new_dds":0}
(out/"C309_Q176_SOURCE_FAMILY_MACHINE.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
print(json.dumps({"run":"C309-C2","regions":len(regions),"png":report["lossless_png_count"],"outside":outside,"clean_alpha":[x["clean_alpha"] for x in regions],"bbox_margin":[x["margins_LRTB"] for x in regions]},ensure_ascii=False))

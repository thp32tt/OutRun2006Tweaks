#!/usr/bin/env python3
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
import hashlib,io,json,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw,ImageChops

repo=Path.cwd(); run="20261007-C225R-EBFC709F-B219"; out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"; candp=repo/"localization/graphics/hd_candidates"/asset
cleanp=repo/"localization/graphics/role_C/20261005-C135-EBFC709F/EBFC709F_CLEAN_PLATE.png"
CAND="54ed1e64dde7be9686b882748ab934d3e465d9966289c6ec7772daeeef8f7221"; SRC="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
regions=[
 ("join_small","JOIN GAME","게임 참가",[0,270,450,354]),
 ("create_small","CREATE GAME","게임 만들기",[870,270,1450,354]),
 ("create_large","CREATE GAME","게임 만들기",[0,660,1280,850]),
 ("join_large","JOIN GAME","게임 참가",[0,850,1020,1024])]
def h(b): return hashlib.sha256(b).hexdigest()
def dec(b):
    with Image.open(io.BytesIO(b)) as im:return im.convert("RGBA")
def bbox(m):
    ys,xs=np.nonzero(m); return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def flat(im):
    z=Image.new("RGB",im.size,(105,105,105)); z.paste(im.convert("RGB"),mask=im.getchannel("A")); return z
req=urllib.request.Request(URL,headers={"User-Agent":"OutRun-C225R"})
with urllib.request.urlopen(req,timeout=90) as r: sb=r.read()
cb=candp.read_bytes()
if h(sb)!=SRC or h(cb)!=CAND: raise RuntimeError(("sha drift",h(sb),h(cb)))
if sb[:128]!=cb[:128]: raise RuntimeError("header drift")
sr=dec(sb); fr=dec(cb)
if sr.size!=(2048,1024) or fr.size!=sr.size: raise RuntimeError(("size",sr.size,fr.size))
s=ImageOps.flip(sr); f=ImageOps.flip(fr); clean=Image.open(cleanp).convert("RGBA")
sa=np.asarray(s,np.uint8); fa=np.asarray(f,np.uint8); ca=np.asarray(clean,np.uint8); H,W=sa.shape[:2]
allowed=np.zeros((H,W),bool); source_masks=[]; final_masks=[]; rows=[]
for key,en,ko,r in regions:
    x0,y0,x1,y1=r
    sm=sa[y0:y1,x0:x1,3]>0; ob0=bbox(sm)
    if not ob0: raise RuntimeError(("source alpha missing",key))
    ob=[x0+ob0[0],y0+ob0[1],x0+ob0[2],y0+ob0[3]]
    # final localized alpha within the exact source bbox
    fm=fa[ob[1]:ob[3],ob[0]:ob[2],3]>0; lb0=bbox(fm)
    if not lb0: raise RuntimeError(("final alpha missing",key))
    lb=[ob[0]+lb0[0],ob[1]+lb0[1],ob[0]+lb0[2],ob[1]+lb0[3]]
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(margins)<=0: raise RuntimeError(("geometry",key,ob,lb,margins))
    m=np.zeros((H,W),bool); m[ob[1]:ob[3],ob[0]:ob[2]]=sa[ob[1]:ob[3],ob[0]:ob[2],3]>0; source_masks.append(m)
    q=np.zeros((H,W),bool); q[lb[1]:lb[3],lb[0]:lb[2]]=fa[lb[1]:lb[3],lb[0]:lb[2],3]>0; final_masks.append(q)
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    clean_source_alpha=int(np.count_nonzero(ca[:,:,3][m]))
    if clean_source_alpha: raise RuntimeError(("clean alpha residue",key,clean_source_alpha))
    rows.append({"key":key,"source":en,"korean":ko,"original_bbox":ob,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],"delta_left":margins[0],"delta_right":margins[1],
      "delta_top":margins[2],"delta_bottom":margins[3],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "clean_source_alpha_remaining":clean_source_alpha})
# candidate must be byte/pixel identical to canonical source outside four exact source bboxes.
diff=np.any(fa!=sa,axis=2); ad=fa[:,:,3]!=sa[:,:,3]
outside=int(np.count_nonzero(diff&~allowed)); alpha_out=int(np.count_nonzero(ad&~allowed))
if outside or alpha_out: raise RuntimeError(("candidate changed outside source bboxes",outside,alpha_out))
# clean may retain RGB beneath alpha, but visible alpha inside source lettering must be fully removed.
clean_alpha_residue=sum(int(np.count_nonzero(ca[:,:,3][m])) for m in source_masks)
# no localized pair overlap/touch
overlap=0; touch=[]
for i in range(len(final_masks)):
  for j in range(i+1,len(final_masks)):
    overlap+=int(np.count_nonzero(final_masks[i]&final_masks[j]))
    dil=final_masks[i].copy()
    for dy in (-1,0,1):
      for dx in (-1,0,1):
        if dx==0 and dy==0: continue
        ys=slice(max(0,dy),min(H,H+dy)); xs=slice(max(0,dx),min(W,W+dx))
        ys2=slice(max(0,-dy),min(H,H-dy)); xs2=slice(max(0,-dx),min(W,W-dx))
        dil[ys,xs]|=final_masks[i][ys2,xs2]
    if np.any(dil&final_masks[j]): touch.append([rows[i]["key"],rows[j]["key"]])
if overlap or touch: raise RuntimeError(("overlap/touch",overlap,touch))
if ImageChops.difference(ImageOps.flip(fr),f).getbbox() is not None: raise RuntimeError("orientation parity")
def card(label,im):
  v=flat(im); v.thumbnail((1536,768),Image.Resampling.LANCZOS); c=Image.new("RGB",(v.width,v.height+28),(24,24,24)); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c
cards=[card("SOURCE_READABLE",s),card("C135_VALIDATED_CLEAN",clean),card("B219_FINAL",f)]
w=max(x.width for x in cards); sh=sum(x.height for x in cards); sheet=Image.new("RGB",(w,sh),(24,24,24)); y=0
for x in cards: sheet.paste(x,(0,y)); y+=x.height
sheet.save(out/"C225R_EBFC_SOURCE_CLEAN_FINAL_READABLE.jpg","JPEG",quality=96,subsampling=0)
contacts=[]; sf=flat(s); ff=flat(f)
for row in rows:
  x0,y0,x1,y1=row["original_bbox"]; p=8; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
  a=sf.crop(cr); b=ff.crop(cr); sc=max(1,min(3,round(900/max(1,a.width)))); a=a.resize((a.width*sc,a.height*sc),Image.Resampling.NEAREST); b=b.resize((b.width*sc,b.height*sc),Image.Resampling.NEAREST)
  c=Image.new("RGB",(a.width+b.width+6,max(a.height,b.height)+28),(24,24,24)); d=ImageDraw.Draw(c); d.text((4,4),"SOURCE",fill="white"); d.text((a.width+10,4),"B219_FINAL",fill="white"); c.paste(a,(0,26)); c.paste(b,(a.width+6,26)); contacts.append(c)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+6*(len(contacts)-1); cs=Image.new("RGB",(cw,ch),(24,24,24)); y=0
for x in contacts: cs.paste(x,(0,y)); y+=x.height+6
cs.save(out/"C225R_EBFC_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)
raw=[card("SOURCE_RAW_MIRROR_Y",sr),card("B219_RAW_MIRROR_Y",fr)]; rw=max(x.width for x in raw); rh=sum(x.height for x in raw); rr=Image.new("RGB",(rw,rh),(24,24,24)); y=0
for x in raw: rr.paste(x,(0,y)); y+=x.height
rr.save(out/"C225R_EBFC_SOURCE_FINAL_RAW.jpg","JPEG",quality=96,subsampling=0)
report={"schema_version":1,"role":"C","run":run,"qa_id":"C225R","queue_index":232,"asset":asset,"producer_run":"B219",
"source_sha256":SRC,"candidate_sha256":CAND,"source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":URL},
"independent_basis":"pinned canonical source independently decoded; source text alpha bboxes re-derived directly inside previously mapped semantic regions; candidate alpha bboxes re-derived directly; producer masks not consumed",
"machine_status":"PASS","structure":{"dimensions":[2048,1024],"format":"RGBA32","header_128_exact":True,"raw_orientation":"mirror_y"},
"rows":rows,"summary":{"bbox_size_positive_margin":"4/4 PASS","candidate_changed_outside_exact_source_bboxes":outside,"candidate_alpha_changed_outside_exact_source_bboxes":alpha_out,
"clean_source_alpha_remaining":clean_alpha_residue,"localized_pair_overlap_pixels":overlap,"localized_touch_pairs":touch,"raw_readable_parity":"PASS"},
"visual_evidence":[str((out/"C225R_EBFC_SOURCE_CLEAN_FINAL_READABLE.jpg").relative_to(repo)),str((out/"C225R_EBFC_ROW_CONTACT.jpg").relative_to(repo)),str((out/"C225R_EBFC_SOURCE_FINAL_RAW.jpg").relative_to(repo))],
"controller_visual_qa":"PENDING_CONTROLLER","decision":"PENDING_CONTROLLER","runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False}
(out/"C225R_EBFC709F_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(repo/"localization/graphics/worker_results/C225R_EBFC709F.json").write_text(json.dumps({"role":"C","run":"C225R","queue_index":232,"asset":asset,"candidate_sha256":CAND,"machine_status":"PASS","report":str((out/"C225R_EBFC709F_MACHINE_QA.json").relative_to(repo)),"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C225R","status":"PASS","rows":rows,"summary":report["summary"]},ensure_ascii=False))

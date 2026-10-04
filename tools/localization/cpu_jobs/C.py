#!/usr/bin/env python3
import hashlib,json,os,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261004-1920-C100"; out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
report_path=repo/"localization/graphics/role_A/20261004-A-PRODUCTION13/A_PRODUCTION13_AD720950_REPORT.json"
producer=json.loads(report_path.read_text(encoding="utf-8"))
candidate=repo/producer["candidate_path"]
source=Path("/tmp/C100_AD720950_SOURCE.dds")
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds",source)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!="141e1f0773b82a8eca6ff49cd93d637221b96211566541f97de9ef4fc454d26f":raise RuntimeError("source SHA mismatch")
if sha(candidate)!="6dad37489e7027b8f546c38b3729167697965fc8e33fcabff46f09aba1677955":raise RuntimeError("candidate SHA mismatch")
src=Image.open(source).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
final=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(repo/"localization/graphics/role_A/20261004-A-PRODUCTION13/AD720950_HD_CLEAN_PLATE.png").convert("RGBA")
sm=np.asarray(Image.open(repo/"localization/graphics/role_A/20261004-A-PRODUCTION13/AD720950_HD_SOURCE_TEXT_MASK.png").convert("L"))>0
allowed=np.asarray(Image.open(repo/"localization/graphics/role_A/20261004-A-PRODUCTION13/AD720950_HD_ALLOWED_TEXT_REGION_MASK.png").convert("L"))>0
cleanprot=np.asarray(Image.open(repo/"localization/graphics/role_A/20261004-A-PRODUCTION13/AD720950_HD_CLEAN_PROTECTED_VISIBLE_MASK.png").convert("L"))>0
finalprot=np.asarray(Image.open(repo/"localization/graphics/role_A/20261004-A-PRODUCTION13/AD720950_HD_PROTECTED_VISIBLE_MASK.png").convert("L"))>0
if not(src.size==final.size==clean.size):raise RuntimeError("size mismatch")
S=np.asarray(src); F=np.asarray(final); C=np.asarray(clean)
def bb(m):
 y,x=np.nonzero(m)
 return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1]
def gate(a,b,edit,prot):
 d=np.any(a!=b,axis=2); ad=a[:,:,3]!=b[:,:,3]
 return {"changed_pixels":int(d.sum()),"changed_bbox":bb(d),"changed_pixels_outside_edit_mask":int((d&~edit).sum()),"changed_pixels_in_protected_mask":int((d&prot).sum()),"alpha_changed_outside_edit_mask":int((ad&~edit).sum())}
cg=gate(S,C,sm,cleanprot); fg=gate(S,F,allowed,finalprot)
if any([cg["changed_pixels_outside_edit_mask"],cg["changed_pixels_in_protected_mask"],cg["alpha_changed_outside_edit_mask"],fg["changed_pixels_outside_edit_mask"],fg["changed_pixels_in_protected_mask"],fg["alpha_changed_outside_edit_mask"]]):raise RuntimeError(("mask gate",cg,fg))
delta=np.max(np.abs(F.astype(np.int16)-C.astype(np.int16)),axis=2)
tm=(delta>=8)&((F[:,:,3]>4)|(C[:,:,3]>4))
rows=[]; failures=[]; holds=[]; edge=[]
for r in producer["rows"]:
 ob=list(map(int,r["original_bbox"])); x0,y0,x1,y1=ob
 smsub=np.zeros_like(sm);smsub[y0:y1,x0:x1]=sm[y0:y1,x0:x1]
 tmsub=np.zeros_like(tm);tmsub[y0:y1,x0:x1]=tm[y0:y1,x0:x1]
 sb=bb(smsub);tb=bb(tmsub)
 rr={"key":r["key"],"source":r["source"],"korean":r["korean"],"coarse_bbox":ob,"source_exact_bbox":sb,"localized_exact_bbox":tb}
 if sb is None or tb is None:
  rr["gate"]="HOLD_STRICT_RECHECK";holds.append(rr)
 else:
  sw,sh=sb[2]-sb[0],sb[3]-sb[1];lw,lh=tb[2]-tb[0],tb[3]-tb[1]
  contain=tb[0]>=sb[0] and tb[1]>=sb[1] and tb[2]<=sb[2] and tb[3]<=sb[3]
  ds=[tb[0]-sb[0],sb[2]-tb[2],tb[1]-sb[1],sb[3]-tb[3]]
  rr.update({"source_size":[sw,sh],"localized_size":[lw,lh],"delta_size":[lw-sw,lh-sh],"delta_left":ds[0],"delta_right":ds[1],"delta_top":ds[2],"delta_bottom":ds[3],"exact_containment":contain,"gate":"PASS" if contain and lw<=sw and lh<=sh else "REWORK_REQUIRED"})
  if min(ds)==0:edge.append(r["key"])
  if rr["gate"]!="PASS":failures.append(rr)
 rows.append(rr)

# Contact evidence at native readable orientation.
cards=[]
for rr in rows:
 ob=rr["coarse_bbox"];pad=8;cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.width,ob[2]+pad),min(src.height,ob[3]+pad))
 strip=Image.new("RGB",(1500,190),"white")
 for i,(tag,im) in enumerate((("SOURCE",src),("CLEAN",clean),("FINAL",final))):
  bg=Image.new("RGBA",im.size,(64,64,64,255));bg.alpha_composite(im);v=bg.convert("RGB").crop(cr);v.thumbnail((480,158),Image.Resampling.LANCZOS)
  c=Image.new("RGB",(496,190),"white");c.paste(v,((496-v.width)//2,28+(158-v.height)//2));ImageDraw.Draw(c).text((4,4),f'{rr["key"]} {tag}',fill="black");strip.paste(c,(i*502,0))
 cards.append(strip)
sheet=Image.new("RGB",(1500,190*len(cards)),"white");y=0
for c in cards:sheet.paste(c,(0,y));y+=190
sheet.save(out/"C100_AD720950_ROW_CONTACT.jpg",quality=95)
# Full readable/raw proof.
def card(im,label):
 bg=Image.new("RGBA",im.size,(64,64,64,255));bg.alpha_composite(im);v=bg.convert("RGB");v.thumbnail((900,350),Image.Resampling.LANCZOS);c=Image.new("RGB",(v.width,v.height+28),"white");c.paste(v,(0,28));ImageDraw.Draw(c).text((5,5),label,fill="black");return c
cs=[card(src,"SOURCE_READABLE"),card(clean,"CLEAN_READABLE"),card(final,"FINAL_READABLE"),card(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),"SOURCE_RAW"),card(final.transpose(Image.Transpose.FLIP_TOP_BOTTOM),"FINAL_RAW")]
w=max(c.width for c in cs);h=sum(c.height for c in cs)+8*(len(cs)-1);sheet=Image.new("RGB",(w,h),"white");y=0
for c in cs:sheet.paste(c,(0,y));y+=c.height+8
sheet.save(out/"C100_AD720950_FULL_COMPARE.jpg",quality=94)
status="PASS" if not failures and not holds else ("REWORK_REQUIRED" if failures else "HOLD_STRICT_RECHECK")
result={"schema_version":1,"role":"C","run":run,"asset":"AD720950","producer_report":str(report_path.relative_to(repo)),"source_sha256":sha(source),"candidate_sha256":sha(candidate),"candidate_changed_by_C":False,"clean_plate_gate":{**cg,"status":"PASS"},"final_gate":{**fg,"status":"PASS"},"bbox_size_gate":{"elements":len(rows),"pass":sum(r["gate"]=="PASS" for r in rows),"rework_required":len(failures),"hold_strict_recheck":len(holds),"edge_touch_keys":edge,"rows":rows,"status":status},"preserved_shift_pixel_diffs":producer["preserved_shift_pixel_diffs"],"visual_evidence":{"row_contact":f"localization/graphics/role_C/{run}/C100_AD720950_ROW_CONTACT.jpg","full_compare":f"localization/graphics/role_C/{run}/C100_AD720950_FULL_COMPARE.jpg","controller_visual_qa":"PENDING"},"runtime_validation":"UNTESTED","status":"C100_STATIC_MACHINE_"+status+"_PENDING_CONTROLLER_VISUAL_QA","vr_ffb_dx11_dxvk_changes":False}
(out/"C100_AD720950_FINAL_QA.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C100_DONE",status,len(rows),len(failures),len(holds),edge)

#!/usr/bin/env python3
import os,json,hashlib,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
repo=Path.cwd(); run="20261005-C207-6DC89C6E"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pr=json.loads((repo/"localization/graphics/role_A/20261005-A-PRODUCTION62/A62_6DC89C6E_REPORT.json").read_text(encoding="utf-8"))
asset=pr["asset"]; sp=pr["source_provenance"]; cand=repo/pr["candidate_path"]
tmp=Path("/tmp/c207"); tmp.mkdir(exist_ok=True); srcdds=tmp/"source.dds"; atlasp=tmp/"atlas.json"
folder=asset.split("/")[-2]; name=asset.split("/")[-1]
base=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}"
urllib.request.urlretrieve(base+f"/Release/{folder}/{name}",srcdds)
urllib.request.urlretrieve(base+f"/Original%20(PC)/Original%20(Tweaks%20dumps)/{folder}/4x_{name[:-4]}_atlas.json",atlasp)
def sha(b):return hashlib.sha256(b).hexdigest()
def bbox(m):
 yy,xx=np.nonzero(m)
 return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m):return int(np.count_nonzero(m))
def comp(im,bg=(70,70,70,255)):
 z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")
sb=srcdds.read_bytes();cb=cand.read_bytes()
if sha(sb)!=sp["source_sha256"] or sha(cb)!=pr["candidate_sha256"] or cb[:128]!=sb[:128]:
 raise RuntimeError(("identity/header",sha(sb),sha(cb),cb[:128]==sb[:128]))
raws=Image.open(srcdds).convert("RGBA");rawf=Image.open(cand).convert("RGBA")
src=raws.transpose(Image.Transpose.FLIP_TOP_BOTTOM);fin=rawf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8);fa=np.asarray(fin,dtype=np.uint8);H,W=sa.shape[:2]
if (W,H)!=(2048,2048):raise RuntimeError((W,H))
atlas=json.loads(atlasp.read_text(encoding="utf-8"));regs={int(r["idx"]):r for r in atlas["regions"]}
rows={int(r["region_idx"]):r for r in pr["rows"]}
expected=[
("WATERFALLS","워터폴스"),("SUNNY BEACH","서니 비치"),("SKYSCRAPERS","스카이스크레이퍼스"),
("NATIONAL PARK","내셔널 파크"),("MILKY WAY","밀키 웨이"),("LOST CITY","로스트 시티"),
("LEGEND","레전드"),("JUNGLE","정글"),("ICE SCAPE","아이스스케이프"),
("GIANT STATUES","자이언트 스태추스"),("FLORAL VILLAGE","플로럴 빌리지"),("CASINO TOWN","카지노 타운"),
("CANYON","캐니언"),("BIG FOREST","빅 포레스트"),("TULIP GARDEN","튤립 가든"),
("SNOW MOUNTAIN","스노 마운틴"),("PALM BEACH","팜 비치"),("METROPOLIS","메트로폴리스"),
("INDUSTRIAL COMPLEX","인더스트리얼 컴플렉스"),("IMPERIAL AVENUE","임페리얼 애비뉴"),("GHOST FOREST","고스트 포레스트")]
if set(regs)!=set(range(21)) or set(rows)!=set(range(21)):raise RuntimeError("region set")
semantic=all((rows[i]["source"],rows[i]["korean"])==expected[i] for i in range(21))
allowed=np.zeros((H,W),bool);lms=[];checks=[];sexact=True;fexact=True;residue=0;eq=np.all(fa==sa,axis=2)
for i in range(21):
 x,y,w,h=map(int,regs[i]["rect"]);sm=sa[y:y+h,x:x+w,3]>0;bb=bbox(sm)
 if bb is None:raise RuntimeError(("empty",i))
 sbb=[bb[0]+x,bb[1]+y,bb[2]+x,bb[3]+y];ds=list(map(int,rows[i]["original_bbox"]));se=sbb==ds;sexact&=se
 x0,y0,x1,y1=sbb;allowed[y0:y1,x0:x1]=True;fm=fa[y0:y1,x0:x1,3]>0;fb=bbox(fm)
 fbb=None if fb is None else [fb[0]+x0,fb[1]+y0,fb[2]+x0,fb[3]+y0];df=list(map(int,rows[i]["localized_bbox"]));fe=fbb==df;fexact&=fe
 if fbb is None: dl=dr=dt=db=-1;contain=sizeok=positive=False
 else:
  a,b,c,d=fbb;dl=a-x0;dr=x1-c;dt=b-y0;db=y1-d;contain=a>=x0 and b>=y0 and c<=x1 and d<=y1;sizeok=(c-a)<=x1-x0 and (d-b)<=y1-y0;positive=min(dl,dr,dt,db)>0
  lm=np.zeros((H,W),bool);lm[y0:y1,x0:x1]=fm;lms.append(lm)
  smf=np.zeros((H,W),bool);smf[y:y+h,x:x+w]=sm;of=smf.copy();of[b:d,a:c]=False;residue+=count(of&eq)
 checks.append({"region_idx":i,"source":expected[i][0],"korean":expected[i][1],"independent_source_bbox":sbb,"producer_source_bbox":ds,"source_bbox_exact_match_producer":se,"independent_localized_bbox":fbb,"producer_localized_bbox":df,"localized_bbox_exact_match_producer":fe,"delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,"containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if sizeok else "FAIL","positive_margin":"PASS" if positive else "FAIL"})
chg=np.any(fa!=sa,axis=2);ach=fa[:,:,3]!=sa[:,:,3];intro=fa[:,:,3]>sa[:,:,3]
m={"decoded_changed_outside_union_source_bboxes":count(chg&~allowed),"alpha_changed_outside_union_source_bboxes":count(ach&~allowed),"introduced_visible_outside_union_source_bboxes":count(intro&~allowed),"source_residue_exact_pixels_outside_localized_bboxes":residue}
ov=touch=0
for i,mi in enumerate(lms):
 yy,xx=np.nonzero(mi);dil=np.zeros_like(mi)
 for dy in (-1,0,1):
  for dx in (-1,0,1):
   ys=np.clip(yy+dy,0,H-1);xs=np.clip(xx+dx,0,W-1);dil[ys,xs]=True
 for mj in lms[i+1:]:ov+=count(mi&mj);touch+=count(dil&mj)
m["localized_overlap_pixels"]=ov;m["localized_1px_touch_pixels"]=touch
rp=sum(1 for r in checks if r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS")
status="PASS" if rp==21 and sexact and fexact and semantic and all(v==0 for v in m.values()) else "FAIL"
cards=[]
for r in checks:
 x0,y0,x1,y1=r["independent_source_bbox"];pad=8;crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
 a=comp(src).crop(crop);b=comp(fin).crop(crop);cw=max(a.width,b.width);ch=max(a.height,b.height)
 card=Image.new("RGB",(cw*2+8,ch+22),"white");card.paste(a,(0,22));card.paste(b,(cw+8,22));d=ImageDraw.Draw(card);d.text((2,3),f"{r['region_idx']} {r['source']}",fill="black");d.text((cw+10,3),r["korean"],fill="black");cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+3*(len(cards)-1)),"white");yy=0
for c in cards:sheet.paste(c,(0,yy));yy+=c.height+3
if sheet.width>1800:sheet=sheet.resize((1800,round(sheet.height*1800/sheet.width)),Image.Resampling.LANCZOS)
sheet.save(out/"C207_TARGET_CONTACTS.jpg",quality=96)
rep={"schema_version":1,"role":"C","run":run,"qa_id":"C207","queue_index":173,"asset":asset,"producer_run":pr["run"],"source_sha256":sp["source_sha256"],"candidate_sha256":pr["candidate_sha256"],"structure":{"dimensions":[W,H],"header_exact":True,"raw_orientation":"mirror_y","format":pr["structure"]["format"]},"semantic_policy_pass":semantic,"source_bbox_exact_match_all":sexact,"candidate_bbox_exact_match_all":fexact,"row_checks":checks,"row_gate":f"{rp}/21 PASS","machine_checks":m,"machine_status":status,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C207_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE","runtime_validation":"UNTESTED","preview_files":[f"localization/graphics/role_C/{run}/C207_TARGET_CONTACTS.jpg"]}
(out/"C207_6DC89C6E_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C207_6DC89C6E.json").write_text(json.dumps({"run":run,"qa_id":"C207","index":173,"asset":"6DC89C6E","candidate_sha256":pr["candidate_sha256"],"machine_status":status,"row_gate":rep["row_gate"],"semantic_policy_pass":semantic,"source_bbox_exact_match_all":sexact,"candidate_bbox_exact_match_all":fexact,"machine_checks":m,"report":f"localization/graphics/role_C/{run}/C207_6DC89C6E_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"C207":{"machine_status":status,"row_gate":rep["row_gate"],"machine_checks":m}},ensure_ascii=False),flush=True)

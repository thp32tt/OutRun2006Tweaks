#!/usr/bin/env python3
# C268 C2 q154 evidence-gate native-DDS recheck. Evidence only; no shared state writes.
import hashlib, io, json, os, secrets, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

ROOT=Path(".")
OUT=ROOT/"localization/graphics/role_C/20261008-C268-C2-Q154-EVIDENCE"
CAL=OUT/"calibration"
OUT.mkdir(parents=True,exist_ok=True); CAL.mkdir(parents=True,exist_ok=True)
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
SOURCE_SHA="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
CAND=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
CAND_SHA="815f0112c772ef1a99b5cb86639415701582301edaaf3ac5bec276e69a475288"
CLEAN=ROOT/"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_EXACT_CLEAN_PLATE.png"
PROT=ROOT/"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_PROTECTED_VISIBLE_MASK.png"
ROWS=[
("create_new_license","CREATE NEW LICENSE","새 라이선스 만들기","red",[13,548,1954,696]),
("select_license","SELECT LICENSE","라이선스 선택","red",[2007,541,3468,689]),
("single_player_red","SINGLE PLAYER","싱글 플레이","red",[12,374,1388,522]),
("default_license","DEFAULT LICENSE","기본 라이선스","red",[1772,374,3316,522]),
("multiplayer_red","MULTIPLAYER","멀티플레이","red",[15,203,1235,347]),
("single_player_gray","SINGLE PLAYER","싱글 플레이","gray",[1610,286,2197,350]),
("showroom_gray","SHOWROOM","쇼룸","gray",[2674,288,3094,350]),
("multiplayer_gray","MULTIPLAYER","멀티플레이","gray",[2566,952,3086,1014])]
def sha(b): return hashlib.sha256(b).hexdigest()
def arr(b): return np.array(Image.open(io.BytesIO(b)).convert("RGBA"))
def neutral(a,bg=128):
    rgb=a[...,:3].astype(np.float32); al=a[...,3:4].astype(np.float32)/255
    return np.clip(rgb*al+bg*(1-al),0,255).astype(np.uint8)
def bb(m):
    y,x=np.where(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
with urllib.request.urlopen(SOURCE_URL,timeout=120) as r: sb=r.read()
cb=CAND.read_bytes()
assert sha(sb)==SOURCE_SHA,(sha(sb),SOURCE_SHA)
assert sha(cb)==CAND_SHA,(sha(cb),CAND_SHA)
assert sb[:128]==cb[:128]
src_raw=arr(sb); cur_raw=arr(cb)
src=np.flipud(src_raw).copy(); cur=np.flipud(cur_raw).copy()
clean=np.array(Image.open(CLEAN).convert("RGBA"))
prot=np.array(Image.open(PROT).convert("L"))>0
assert src.shape==cur.shape==clean.shape
delta=np.any(cur!=clean,axis=2); src_delta=np.any(cur!=src,axis=2); alpha_delta=cur[...,3]!=clean[...,3]
allow=np.zeros(cur.shape[:2],bool)
rowrep=[]
for key,en,ko,kind,b in ROWS:
    x0,y0,x1,y1=b; allow[y0:y1,x0:x1]=1
    z=bb(delta[y0:y1,x0:x1])
    if z:z=[z[0]+x0,z[1]+y0,z[2]+x0,z[3]+y0]
    a=src[y0:y1,x0:x1,3]>0; k=cur[y0:y1,x0:x1,3]>0
    rowrep.append({"id":key,"source":en,"korean":ko,"kind":kind,"original_bbox":b,"localized_bbox":z,
      "source_alpha_fraction":round(float(a.mean()),6),"candidate_alpha_fraction":round(float(k.mean()),6),
      "source_alpha_pixels":int(a.sum()),"candidate_alpha_pixels":int(k.sum()),
      "delta_left":z[0]-x0 if z else None,"delta_right":x1-z[2] if z else None,
      "delta_top":z[1]-y0 if z else None,"delta_bottom":y1-z[3] if z else None})
rep={"schema_version":1,"run":"C268","role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "policy_version":"visual-evidence-v1-20261008","queue_index":154,
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds",
 "candidate_sha256":sha(cb),"source_sha256":sha(sb),"header_128_exact":sb[:128]==cb[:128],
 "dimensions":[int(cur.shape[1]),int(cur.shape[0])],"raw_orientation":"mirror_y","rows":rowrep,
 "changed_outside":int(np.count_nonzero(delta&~allow)),"alpha_outside":int(np.count_nonzero(alpha_delta&~allow)),
 "protected_changed":int(np.count_nonzero(src_delta&prot)),
 "machine_result":"PASS" if int(np.count_nonzero(delta&~allow))==0 and int(np.count_nonzero(alpha_delta&~allow))==0 and int(np.count_nonzero(src_delta&prot))==0 else "FAIL",
 "controller_visual_qa":"PENDING_NATIVE_EVIDENCE_REVIEW","runtime_validation":"UNTESTED"}
(OUT/"C268_Q154_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# Full decoded persisted candidate/source/clean evidence.
Image.fromarray(src).save(OUT/"C268_Q154_SOURCE_READABLE.png")
Image.fromarray(clean).save(OUT/"C268_Q154_CLEAN.png")
Image.fromarray(cur).save(OUT/"C268_Q154_DECODED_FINAL_READABLE.png")
Image.fromarray(src_raw).save(OUT/"C268_Q154_SOURCE_RAW.png")
Image.fromarray(cur_raw).save(OUT/"C268_Q154_FINAL_RAW.png")

# Gray-family native contacts: SOURCE | CLEAN | FINAL on neutral backgrounds and 4x nearest high zoom.
cards=[]
for key,en,ko,kind,b in ROWS:
    if kind!="gray": continue
    x0,y0,x1,y1=b; pad=10
    x0=max(0,x0-pad); y0=max(0,y0-pad); x1=min(src.shape[1],x1+pad); y1=min(src.shape[0],y1+pad)
    ims=[Image.fromarray(neutral(a[y0:y1,x0:x1])) for a in (src,clean,cur)]
    w=max(i.width for i in ims); h=max(i.height for i in ims)
    c=Image.new("RGB",(w*3,h+28),(96,96,96)); d=ImageDraw.Draw(c)
    d.text((3,3),f"{key}: SOURCE | CLEAN | FINAL",fill="white")
    for j,im in enumerate(ims): c.paste(im,(j*w,26))
    cards.append(c)
W=max(c.width for c in cards); H=sum(c.height for c in cards)
sheet=Image.new("RGB",(W,H),(96,96,96)); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height
sheet.save(OUT/"C268_Q154_GRAY_NATIVE_CONTACT.png")
sheet.resize((sheet.width*2,sheet.height*2),Image.Resampling.NEAREST).save(OUT/"C268_Q154_GRAY_2X_CONTACT.png")

# Practical native display comparison, source|final.
for pct in (100,75,50):
    ims=[]
    for a in (src,cur):
        im=Image.fromarray(neutral(a))
        if pct!=100: im=im.resize((round(im.width*pct/100),round(im.height*pct/100)),Image.Resampling.LANCZOS)
        ims.append(im)
    out=Image.new("RGB",(ims[0].width*2,ims[0].height),(96,96,96)); out.paste(ims[0],(0,0));out.paste(ims[1],(ims[0].width,0))
    out.save(OUT/f"C268_Q154_PRACTICAL_{pct}.png")

# Blind calibration controls. Each case shows SOURCE(left) and TEST(right); answer key stays separate.
font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F=ImageFont.truetype(font,64)
def cal_base(stroke=1):
    im=Image.new("RGBA",(430,140),(96,96,96,255))
    ImageDraw.Draw(im).text((70,28),"MENU",font=F,fill=(235,235,235,255),stroke_width=stroke,stroke_fill=(25,25,25,255))
    return im
def cal_shear(im,k):
    pad=60
    c=Image.new("RGBA",(im.width+2*pad,im.height),(96,96,96,255)); c.paste(im,(pad,0))
    return c.transform(c.size,Image.Transform.AFFINE,(1,k,-k*c.height/2,0,1,0),Image.Resampling.BICUBIC).crop((pad,0,pad+im.width,im.height))
cal_src=cal_shear(cal_base(),-0.16)
normal=cal_src.copy()
opp=cal_shear(cal_base(),0.16)
a=np.array(normal); mm=np.any(a[:,:,:3]!=96,axis=2); yy,xx=np.where(mm); bg=np.array([96,96,96,255],dtype=np.uint8)
a[yy.max()-8:yy.max()+1,xx.min():xx.max()+1]=bg; a[yy.min():yy.max()+1,xx.max()-5:xx.max()+1]=bg
clip=Image.fromarray(a)
ghost=Image.new("RGBA",normal.size,(96,96,96,255)); gd=ImageDraw.Draw(ghost)
gd.text((84,39),"MENU",font=F,fill=(150,150,150,160),stroke_width=1,stroke_fill=(35,35,35,130))
gd.text((70,28),"MENU",font=F,fill=(235,235,235,255),stroke_width=1,stroke_fill=(25,25,25,255))
res=cal_shear(ghost,-0.16)
heavy=cal_shear(cal_base(stroke=9),-0.16)
items=[("normal",normal),("opposite_slant",opp),("clipped_stroke",clip),("residue",res),("excessive_weight",heavy)]
secrets.SystemRandom().shuffle(items)
answer={}
for i,(kind,test) in enumerate(items):
    card=Image.new("RGB",(cal_src.width*2,cal_src.height+26),(80,80,80)); d=ImageDraw.Draw(card)
    d.text((4,4),"SOURCE",fill="white"); d.text((cal_src.width+4,4),"TEST",fill="white")
    card.paste(cal_src.convert("RGB"),(0,24)); card.paste(test.convert("RGB"),(cal_src.width,24))
    name=f"case_{i:02d}.png"; card.save(CAL/name); answer[name]=kind
(CAL/"ANSWER_KEY_DO_NOT_READ_BEFORE_FIRST_LOOK.json").write_text(json.dumps(answer,indent=2)+"\n")
(OUT/"C268_EVIDENCE_SUMMARY.json").write_text(json.dumps({"run":"C268","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":154,"machine_result":rep["machine_result"],"calibration_cases":5,"answer_key_separate":True,"runtime_validation":"UNTESTED"},indent=2)+"\n")
print(json.dumps({"q154_machine":rep["machine_result"],"candidate_sha":rep["candidate_sha256"],"source_sha":rep["source_sha256"],"gray_rows":[r for r in rowrep if r["kind"]=="gray"]},ensure_ascii=False))

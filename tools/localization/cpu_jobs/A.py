#!/usr/bin/env python3
"""A256 q099: source-conditioned native Hangul italic & BC3 isolated trial only."""
import csv,hashlib,io,json,os,struct,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw,ImageFilter
R=Path.cwd()
OUT=R/"localization/graphics/role_A/20261012-A256-Q099-NATIVE-ITALIC-BC3"
RUN="OUTRUN-KOR-A256-Q099-NATIVE-ITALIC-TWO-LINE-BC3-20261012-1000"
SRC_SHA="d97206d8ab5e0898c81d9cc0d6562db1a381894b0fa3e2d9fa75303867a638e2"
OLD_SHA="70970da7653bd75e259d39319c4792c2f95558b7cea79bd20bc9c60ebe1bb612"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds"
OLD=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds"
C383=R/"localization/graphics/role_C/20261011-C383-C1-Q099-NATIVE-STYLE-VISUAL-REWORK/C383_Q099_CONTROLLER_C1_VISUAL_REWORK.json"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
W,H=2048,256
B=(514,37,1614,219)
LINES=("고스트 카와 달리며","코스 기록에 도전하세요!")
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="A"
def sha(b):return hashlib.sha256(b).hexdigest()
def ok(x,msg):
    if not x:raise RuntimeError("A256_FAIL_CLOSED "+msg)
def decode(b):
    ok(b[:4]==b"DDS " and len(b)==128+W*H,"BC3_SIZE")
    ok(struct.unpack_from("<II",b,12)==(H,W) and struct.unpack_from("<I",b,28)[0]==1 and b[84:88]==b"DXT5","BC3_HEADER")
    with Image.open(io.BytesIO(b)) as im:
        im.load()
        return np.asarray(im.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
def png(name,im):
    p=OUT/(name+".png");im.save(p)
    return {"path":str(p.relative_to(R)),"sha256":sha(p.read_bytes())}
def js(name,data):
    p=OUT/(name+".json");p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"path":str(p.relative_to(R)),"sha256":sha(p.read_bytes())}
def color565(c):
    r,g,b=(int(x) for x in c)
    return ((r*31+127)//255<<11)|((g*63+127)//255<<5)|((b*31+127)//255)
def rgb8(i):return np.array([((i>>11)&31)*255//31,((i>>5)&63)*255//63,(i&31)*255//31],dtype=np.int16)
def bc3(p):
    a=p[:,:,3].reshape(16).astype(np.int16)
    hi,lo=int(a.max()),int(a.min())
    if hi==lo:lo=max(0,lo-1)
    ap=np.array([hi,lo]+[int(round(((7-i)*hi+i*lo)/7)) for i in range(1,7)],dtype=np.int16)
    ai=np.argmin(abs(a[:,None]-ap[None,:]),axis=1)
    ab=bytes([hi,lo])+sum(int(ai[i])<<(3*i) for i in range(16)).to_bytes(6,"little")
    c=p[:,:,:3].reshape(16,3).astype(np.int16)
    used=c[a>16] if (a>16).any() else c
    d=((used[:,None,:].astype(np.int32)-used[None,:,:].astype(np.int32))**2).sum(2)
    i,j=np.unravel_index(int(d.argmax()),d.shape)
    c0,c1=color565(used[i]),color565(used[j])
    if c0<c1:c0,c1=c1,c0
    if c0==c1:
        if c0<65535:c0+=1
        else:c1-=1
    e0,e1=rgb8(c0),rgb8(c1)
    pal=np.stack((e0,e1,(2*e0+e1)//3,(e0+2*e1)//3))
    diff=((c[:,None,:].astype(np.int32)-pal[None,:,:].astype(np.int32))**2).sum(2)
    ids=diff.argmin(1)
    return ab+struct.pack("<HHI",c0,c1,sum(int(ids[i])<<(2*i) for i in range(16)))
with (R/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
    q=next(x for x in csv.DictReader(f) if x["index"]=="99")
ok(q["action"]=="localize_text" and "rework" in q["artwork_status"].lower(),"QUEUE_NOT_REWORK")
review=json.loads(C383.read_text(encoding="utf-8"))
ok(review["C1"]=="REWORK_REQUIRED" and review["candidate_dds_sha256"]==OLD_SHA and review["source_dds_sha256"]==SRC_SHA,"C383_SHA_REWORK_NOT_MATCHED")
tri=json.loads(subprocess.check_output([sys.executable,"tools/localization/rework_triage.py","--index","99"],text=True))
action=tri["assets"][0]["next_action"]
ok(action in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED","EVIDENCE_ONLY_HOLD","NORMAL_QUEUE_SELECTION"),"TRIAGE_"+action)
if action!="EVIDENCE_ONLY_HOLD":
    subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","99","--require-safe-rerender"],check=True,capture_output=True)
old=OLD.read_bytes();ok(sha(old)==OLD_SHA,"CURRENT_SHA_DRIFT")
with urllib.request.urlopen(urllib.request.Request(SRC_URL,headers={"User-Agent":"OutRun-A256"}),timeout=90) as resp: source_data=resp.read()
ok(sha(source_data)==SRC_SHA,"CANONICAL_SHA_DRIFT")
original=decode(source_data);prev=decode(old)
x0,y0,x1,y1=B;rw,rh=x1-x0,y1-y0
en=original[y0:y1,x0:x1]; prior=prev[y0:y1,x0:x1]
ok(int((en[:,:,3]>0).sum())>2000,"ENGLISH_MISSING")
font=ImageFont.truetype(str(FONT),65,index=1)
glyph=Image.new("L",(rw,rh),0)
line_recipe=[]
for i,t in enumerate(LINES):
    tmp=Image.new("L",(1500,95),0)
    ImageDraw.Draw(tmp).text((6,0),t,font=font,fill=255)
    b=tmp.getbbox();ok(b is not None,"EMPTY_GLYPH")
    g=tmp.crop(b)
    scale=min(1,(rw-50)/g.width,72/g.height)
    if scale<1:g=g.resize((round(g.width*scale),round(g.height*scale)),Image.Resampling.LANCZOS)
    gw,gh=g.size;s=0.44
    sw=gw+round(s*gh)+4
    tilted=g.transform((sw,gh),Image.Transform.AFFINE,(1,s,-s*(gh-1),0,1,0),resample=Image.Resampling.BICUBIC)
    px=(rw-sw)//2;py=22 if i==0 else 106
    ok(px>=6 and py+gh<=rh-6,"LINE_OVERFLOW")
    glyph.paste(tilted,(px,py))
    line_recipe.append({"korean":t,"font_native_ppem":65,"uniform_fit_only":round(scale,5),"right_italic_top_delta":round(s*(gh-1),2),"bbox_start":[px,py]})
rgba=en[:,:,:3].astype(np.int16);alpha=en[:,:,3]
mask=(alpha>100)&(rgba.min(2)>160)&((rgba.max(2)-rgba.min(2))<90)
ok(int(mask.sum())>100,"SOURCE_FACE_COLOR_NOT_IDENTIFIED")
face_rgb=np.median(rgba[mask],axis=0).astype(np.uint8)
def lay(a,c):
    p=Image.new("RGBA",(rw,rh),tuple(map(int,c))+(0,))
    p.putalpha(a)
    return p
outer=lay(glyph.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(1.2)),(129,156,198))
rim=lay(glyph.filter(ImageFilter.MaxFilter(5)),(14,28,73))
face=lay(glyph,face_rgb)
letter=Image.alpha_composite(Image.alpha_composite(outer,rim),face)
newletter=np.asarray(letter).copy()
ys,xs=np.nonzero(newletter[:,:,3]>0)
ok(len(xs)>3000,"GLYPH_EMPTY")
bb=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
margins=[bb[0],bb[1],rw-bb[2],rh-bb[3]]
ok(min(margins)>=3,"SOURCE_BBOX_TOUCH")
intent=prev.copy();intent[y0:y1,x0:x1]=newletter
raw=np.flip(intent,0)
xa=((x0+3)//4)*4;xb=(x1//4)*4
ya=((H-y1+3)//4)*4;yb=((H-y0)//4)*4
safe=(xa,H-yb,xb,H-ya)
bd=np.ones((rh,rw),bool)
bd[safe[1]-y0:safe[3]-y0,safe[0]-x0:safe[2]-x0]=False
ok(not np.any((prior[:,:,3]>16)&bd),"OLD_VISIBLE_GLYPH_IN_UNWRITABLE_EDGE")
result=bytearray(old);count=0
for y in range(ya,yb,4):
    for x in range(xa,xb,4):
        k=128+((y//4)*(W//4)+(x//4))*16
        block=bc3(raw[y:y+4,x:x+4])
        if result[k:k+16]!=block:
            result[k:k+16]=block;count+=1
saved=bytes(result)
ok(saved[:128]==old[:128] and len(saved)==len(old),"HEADER_MISMATCH")
decoded=decode(saved)
change=np.any(prev!=decoded,axis=2)
allowed=np.zeros((H,W),bool);allowed[y0:y1,x0:x1]=True
outside=int((change&~allowed).sum());delta=int(change.sum())
ok(outside==0 and delta>3500,"DDS_OUTSIDE_CHANGED_OR_NO_MATERIAL_DIFF")
OUT.mkdir(parents=True,exist_ok=True)
ddspath=OUT/"A256_Q099_TWO_LINE_ITALIC_BC3_UNPROMOTED.dds"
ddspath.write_bytes(saved);ok(sha(ddspath.read_bytes())==sha(saved),"PERSISTENCE_MISMATCH")
crop=decoded[y0:y1,x0:x1]
ev={"source":png("A256_ORIGINAL_SOURCE",Image.fromarray(en,"RGBA")),
    "previous":png("A256_C383_REJECTED",Image.fromarray(prior,"RGBA")),
    "clean":png("A256_SOURCE_DERIVED_EMPTY_CLEAN",Image.new("RGBA",(rw,rh))),
    "face":png("A256_NATIVE_HANGUL_FACE",face),
    "rim":png("A256_NATIVE_NAVY_RIM",rim),
    "letter":png("A256_COMPOSITE_TRANSPARENT_LETTER",letter),
    "saved":png("A256_PERSISTED_FLIPY",Image.fromarray(crop,"RGBA")),
    "raw":png("A256_PERSISTED_RAW",Image.fromarray(crop,"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))}
for n,col,scale in [("GRAY100",(112,112,112),1),("WHITE75",(255,255,255),.75),("BLACK50",(0,0,0),.5)]:
    pw,ph=round(rw*scale),round(rh*scale)
    contact=Image.new("RGB",(pw*4,ph),col)
    for i,arr in enumerate((en,np.zeros_like(en),prior,crop)):
        tile=Image.alpha_composite(Image.new("RGBA",(rw,rh),(*col,255)),Image.fromarray(arr,"RGBA"))
        contact.paste(tile.convert("RGB").resize((pw,ph),Image.Resampling.LANCZOS),(pw*i,0))
    ev[n]=png("A256_"+n+"_SOURCE_CLEAN_PREVIOUS_SAVED",contact)
recipe=js("A256_SEPARATE_FACE_AND_RIM_RECIPE",{
    "run_key":RUN,"source_sha256":SRC_SHA,"previous_sha256":OLD_SHA,
    "original_source_bbox":B,"lines":line_recipe,"font_sha256":sha(FONT.read_bytes()),
    "font_face_index":1,"face_RGB":face_rgb.tolist(),
    "method":"native 65ppem CJK face with per-line source-directed forward italic, separated sampled silver/white and navy effect layers; unlike prior A119R flat + uniform glow, no word-width stretch",
    "new_decoded_glyph_bbox":[x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3]]})
report={"run_key":RUN,"role":"A","queue_index":99,
    "canonical_source_sha256":SRC_SHA,"prior_C383_rework_sha256":OLD_SHA,
    "triage_next_action":action,"new_unpromoted_trial_dds_path":str(ddspath.relative_to(R)),
    "new_unpromoted_trial_dds_sha256":sha(saved),"new_saved_trial_dds":1,"official_promoted":0,
    "decoded_rgba_changed_inside_source":delta,"decoded_rgba_changed_outside_source":outside,
    "blocks_recompressed":count,"bbox_margins_ltrb":margins,
    "header_format":"DDS BC3 DXT5 2048x256 mip1 RAW mirror-Y",
    "independent_C2":"NOT_RUN_NEW_SHA","C3":"NOT_RUN",
    "RUNTIME_VALIDATION":"UNTESTED","producer_visual":"PENDING_FIRSTHAND_REVIEW",
    "evidence":ev,"lettering_recipe":recipe,"excluded":["VR","FFB","DX11","DXVK"]}
js("A256_MACHINE_HANDOFF",report)
print(json.dumps({"run_key":RUN,"sha256":sha(saved),"changed":delta,"outside":outside,"blocks":count,"margins":margins},ensure_ascii=False),flush=True)

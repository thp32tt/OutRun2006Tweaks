#!/usr/bin/env python3
"""A255 q059 P1: genuine Hangul native face + BC3 4x4 block recompression (RACE RIVALS).
A228 previously rejected index-only palette mutations are not reused as a remedy.
Only a new isolated persisted trial; no producer claim of C2/C3/in-game approval.
"""
import csv,hashlib,io,json,os,struct,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops

ROOT=Path.cwd()
DIR=ROOT/"localization/graphics/role_A/20261012-A255-Q059-REAL-HANGUL-BC3"
RUN="OUTRUN-KOR-A255-Q059-NATIVE-GOLD-GLYPH-BC3-BLOCK-20261012-0900"
SRC_SHA="9c35216873d617ed68df55be424f35ddf50b1eacc8ee86072068745aea166f9f"
OLD_SHA="8150213897f4dc7b74e2d6273d703be3a9d6ac780627f8747059d25ec1ef9f2e"
OFFICIAL_SHA="261108cd26b2a83037162b17de08286ed1ded2634650709370c81c2a353eb83a"
URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds"
OLD=ROOT/"localization/graphics/role_A/20261010-A228-Q059-BC3-INDEX-INTERIOR-REPAIR-TRIAL/A228_Q059_GOLD_FACE_BC3_INDEX_TRIAL_UNPROMOTED.dds"
SRC_PNG=ROOT/"localization/graphics/role_C/20261008-C302-C1-Q059-LOSSLESS-EVIDENCE-PUBLISH/race_rivals__source_native.png"
CLEAN_PNG=ROOT/"localization/graphics/role_C/20261008-C302-C1-Q059-LOSSLESS-EVIDENCE-PUBLISH/race_rivals__clean_native.png"
REVIEW=ROOT/"localization/graphics/role_C/20261010-C1-Q059-A228-FRESH-BC3-VISUAL-REWORK/C1_Q059_A228_INDEPENDENT_VISUAL_REWORK.json"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
W,H=2048,512; BBOX=(75,222,625,304);TEXT="라이벌과 레이스!"
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="A"
def hashb(b):return hashlib.sha256(b).hexdigest()
def fail_if(cond,msg):
    if cond:raise RuntimeError("A255_FAIL_CLOSED "+msg)
def proof_png(name,im):
    f=DIR/(name+".png");im.save(f)
    return {"path":str(f.relative_to(ROOT)),"sha256":hashb(f.read_bytes())}
def save_json(name,obj):
    p=DIR/(name+".json");p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return {"path":str(p.relative_to(ROOT)),"sha256":hashb(p.read_bytes())}
def decoded(b):
    with Image.open(io.BytesIO(b)) as im:
        im.load()
        return np.asarray(im.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
def check_dds(b):
    fail_if(b[:4]!=b"DDS " or len(b)!=128+W*H,
            "native BC3 header/size mismatch")
    fail_if(struct.unpack_from("<II",b,12)!=(H,W) or struct.unpack_from("<I",b,28)[0]!=1,
            "native size/mips")
    fail_if(b[84:88]!=b"DXT5","not BC3 DXT5")
def rgb565(c):
    r,g,b=[int(z) for z in c]
    return ((r*31+127)//255<<11)|((g*63+127)//255<<5)|((b*31+127)//255)
def rgb888(x):
    return np.array([((x>>11)&31)*255//31,((x>>5)&63)*255//63,(x&31)*255//31],dtype=np.int16)
def compress_block(a):
    # BC3 alpha palette, opaque no-colorbleed pixels and exact alpha footprint.
    A=a[:,:,3].reshape(-1).astype(np.int16)
    al0=int(A.max());al1=int(A.min())
    if al0==al1:al1=max(0,al0-1)
    aa=[al0,al1]
    aa.extend([int(round(((7-i)*al0+i*al1)/7)) for i in range(1,7)])
    aaa=np.asarray(aa,dtype=np.int16)
    ai=np.argmin(abs(A[:,None]-aaa[None,:]),axis=1).astype(np.int64)
    bits=sum(int(ai[i])<<(i*3) for i in range(16))
    alpha_bytes=bytes([al0,al1])+bits.to_bytes(6,"little")
    C=a[:,:,:3].reshape(-1,3).astype(np.int16)
    used=A>16
    cs=C[used] if used.any() else C
    dist=((cs[:,None,:]-cs[None,:,:]).astype(np.int32)**2).sum(axis=2)
    i,j=np.unravel_index(int(np.argmax(dist)),dist.shape)
    # RGB565 endpoints; strictly order c0>c1 for 4-color DXT1 interpolation.
    e0=rgb565(cs[i]);e1=rgb565(cs[j])
    if e0<e1:e0,e1=e1,e0
    if e0==e1:
        if e0<65535:e0+=1
        else:e1-=1
    cc0=rgb888(e0);cc1=rgb888(e1)
    pal=np.stack([cc0,cc1,(2*cc0+cc1)//3,(cc0+2*cc1)//3])
    cd=((C[:,None,:]-pal[None,:,:]).astype(np.int32)**2).sum(axis=2)
    idx=np.argmin(cd,axis=1)
    selector=sum(int(idx[i])<<(i*2) for i in range(16))
    return alpha_bytes+struct.pack("<HHI",e0,e1,selector)
with (ROOT/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as fh:
    q=next(x for x in csv.DictReader(fh) if x["index"]=="59")
fail_if(q["action"]!="localize_text" or "rework" not in q["artwork_status"].lower(),"q59 not REWORK")
tri=json.loads(subprocess.check_output([sys.executable,"tools/localization/rework_triage.py","--index","59"],text=True))
action=tri["assets"][0]["next_action"]
r=json.loads(REVIEW.read_text(encoding="utf-8"))
fail_if(r["reviewed_trial_sha256"]!=OLD_SHA or r["source_sha256"]!=SRC_SHA,
        "independently rejected A228 exact SHA drift")
confirmed_material=(r["observations"]["race_rivals"]["verdict"]=="REWORK_REQUIRED_TRIAL" and
                    r["observations"]["race_rivals"]["checks"]["source_style"]["result"]=="FAIL_SOURCE_FAMILY")
fail_if(action not in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED","EVIDENCE_ONLY_HOLD","NORMAL_QUEUE_SELECTION"),
        "triage disallows new Korean candidate")
if action=="EVIDENCE_ONLY_HOLD":
    # Normal/same-method rerender is explicitly blocked. This exception is NOT
    # triage reclassification or a PASS; later independent exact-A228 C1 pixel
    # evidence proves a real source-family defect in this particular region.
    # A255 fundamentally changes the glyph construction and BC3 block codec;
    # preserving the hold on the prior official and on A228 is mandatory.
    fail_if(not confirmed_material,"no fresh actual-pixel material defect to justify new method")
    documented_override="EXACT_A228_C1_CONFIRMED_MATERIAL_FAIL_DIFFERENT_METHOD"
else:
    subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","59","--require-safe-rerender"],
                   check=True,capture_output=True,text=True)
    documented_override="NOT_NEEDED"

old=OLD.read_bytes();check_dds(old)
fail_if(hashb(old)!=OLD_SHA,"old rejected trial changed")
request=urllib.request.Request(URL,headers={"User-Agent":"OutRun-A255-exact-canonical"})
with urllib.request.urlopen(request,timeout=60) as resp:source=resp.read()
check_dds(source)
fail_if(hashb(source)!=SRC_SHA,"canonical English source SHA mismatch")
before=decoded(old);english=decoded(source)
fail_if(before.shape!=(H,W,4) or english.shape!=(H,W,4),"DXT5 decode size")
x0,y0,x1,y1=BBOX;bw=x1-x0;bh=y1-y0
s=english[y0:y1,x0:x1];oldroi=before[y0:y1,x0:x1]
recorded=np.asarray(Image.open(SRC_PNG).convert("RGBA"))
fail_if(recorded.shape!=s.shape or np.count_nonzero(recorded!=s)>0,
        "pinned old English SOURCE PNG cannot be reauthenticated against canonical DDS")
clean=np.asarray(Image.open(CLEAN_PNG).convert("RGBA"))
fail_if(clean.shape!=s.shape or np.count_nonzero(clean[:,:,3])!=0,
        "historical C2 SOURCE CLEAN did not actually remove native glyph alpha")
# P0 priority selection considered; this exact P1 area has objectively evidenced
# broken/navy-stippled gold face. Construct a NEW Hangul face, not A228 pixel edit.
ss=3
f=ImageFont.truetype(str(FONT),60*ss,index=1)
image=Image.new("L",(1200*ss,120*ss))
ImageDraw.Draw(image).text((8*ss,3*ss),TEXT,font=f,fill=255)
box=image.getbbox()
fail_if(box is None,"glyph renderer empty")
base=image.crop(box)
factor=min(1.,(bw-24)*ss/base.width,(bh-21)*ss/base.height)
nw=int(round(base.width*factor/ss));nh=int(round(base.height*factor/ss))
fail_if(nw<280 or nh<40,"glyph shape too small for native source family")
face=base.resize((nw,nh),Image.Resampling.LANCZOS)
glyph=Image.new("L",(bw,bh))
offset=((bw-nw)//2,(bh-nh)//2)
glyph.paste(face,offset)
# Native source derived multi-ring: silver outside, strong indigo inner,
# bright gold FACE, not navy stipple or a one-color palette mutation.
white=glyph.filter(ImageFilter.MaxFilter(13))
navy=glyph.filter(ImageFilter.MaxFilter(9))
gold=glyph.filter(ImageFilter.MaxFilter(3))
# Direct source samples: find gold-like and white-like RGB from canonical pixels.
src=s[:,:,:3].astype(np.int16);alpha=s[:,:,3]
goldish=(alpha>120)&(src[:,:,0]>src[:,:,1]+23)&(src[:,:,1]>src[:,:,2]+28)&(src[:,:,0]>170)
whitish=(alpha>130)&(src.min(axis=2)>172)&((src.max(axis=2)-src.min(axis=2))<42)
fail_if(int(goldish.sum())<500 or int(whitish.sum())<500,
        "source family gold/white samples insufficient")
gcol=np.median(src[goldish],axis=0).astype(np.uint8)
wcol=np.median(src[whitish],axis=0).astype(np.uint8)
# Each effect is a separate transparent layer and stays in source effect ROI.
def layer(mask,color):
    p=Image.new("RGBA",(bw,bh),tuple(int(x) for x in color)+(0,))
    p.putalpha(mask)
    return p
paper=Image.new("RGBA",(bw,bh),(0,0,0,0))
# Rounded font contours: main gold face gets full opaque (no dark pinholes).
silver=layer(white,wcol)
ink=layer(navy,(11,25,75))
front=layer(gold,gcol)
out=Image.alpha_composite(Image.alpha_composite(silver,ink),front)
proposed=np.asarray(out).copy()
ys,xs=np.nonzero(proposed[:,:,3]>0)
fail_if(len(xs)<10000,"new text disappeared")
bb=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
margins=[bb[0],bb[1],bw-bb[2],bh-bb[3]]
fail_if(min(margins)<3,"new silver/navy/gold effect touches source bbox")
# Boundary 4x4 blocks cannot be changed if any pixel lies outside canonical bbox.
# Strictly re-encode only wholly permitted blocks (which are all source-glyph-safe).
# In the 1-3px uneditable boundary strip assert no old glyph remains.
raw_y0,raw_y1=H-y1,H-y0
xa=((x0+3)//4)*4;xb=(x1//4)*4
ya=((raw_y0+3)//4)*4;yb=(raw_y1//4)*4
readable_inner=(xa,H-yb,xb,H-ya)
badstrip=np.zeros((bh,bw),bool)
badstrip[:,:]=True
badstrip[readable_inner[1]-y0:readable_inner[3]-y0,
         readable_inner[0]-x0:readable_inner[2]-x0]=False
fail_if(int(np.count_nonzero((oldroi[:,:,3]>32)&badstrip))>0,
        "old glyph residual in 4x4 non-writable ROI boundary")
T=before.copy()
T[y0:y1,x0:x1]=proposed
raw=np.flip(T,axis=0)
encoded=bytearray(old)
count=0
for by in range(ya,yb,4):
    for bx in range(xa,xb,4):
        offset_byte=128+((by//4)*(W//4)+(bx//4))*16
        chunk=compress_block(raw[by:by+4,bx:bx+4])
        if encoded[offset_byte:offset_byte+16]!=chunk:
            encoded[offset_byte:offset_byte+16]=chunk
            count+=1
output=bytes(encoded)
fail_if(len(output)!=len(old) or output[:128]!=old[:128],"BC3 header/length changed")
new=decoded(output)
changed=(np.any(before!=new,axis=2))
allowed=np.zeros((H,W),bool);allowed[y0:y1,x0:x1]=True
outside=int(np.count_nonzero(changed&~allowed))
fail_if(outside!=0,"compressed output changed protected DDS pixels outside bbox")
fail_if(int(np.count_nonzero((before[:,:,3]!=new[:,:,3])&~allowed))!=0,
        "BC3 changed outside alpha")
diff=int(changed.sum())
fail_if(diff<4000,"new material difference too small")
# Difference from intended source pixels is expected near BC3 edges, but no
# false claim of exact bitwise pre-encode match. Native visual self-QA follows.
decoded_roi=new[y0:y1,x0:x1]
DIR.mkdir(parents=True,exist_ok=True)
dds=DIR/"A255_Q059_RACE_RIVALS_NATIVE_GOLD_BC3_UNPROMOTED.dds"
dds.write_bytes(output)
fail_if(hashb(dds.read_bytes())!=hashb(output),"DDS persistence mismatch")
evidence={
 "SOURCE":proof_png("A255_SOURCE_NATIVE",Image.fromarray(s,"RGBA")),
 "CLEAN":proof_png("A255_SOURCE_VERIFIED_CLEAN_NATIVE",Image.fromarray(clean,"RGBA")),
 "FACE":proof_png("A255_NATIVE_GOLD_FACE",front),
 "RIM":proof_png("A255_NAVY_RIM",ink),
 "SILVER":proof_png("A255_SILVER_OUTER",silver),
 "LETTER":proof_png("A255_COMPOSITE_LETTER",out),
 "SAVED":proof_png("A255_PERSISTED_FLIPY",Image.fromarray(decoded_roi,"RGBA")),
 "RAW":proof_png("A255_PERSISTED_RAW",Image.fromarray(decoded_roi,"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
}
for name,bg,scale in [("GRAY100",(112,112,112),1.),("WHITE75",(255,255,255),.75),("BLACK50",(0,0,0),.5)]:
    pw,ph=round(bw*scale),round(bh*scale)
    panel=Image.new("RGB",(pw*4,ph),bg)
    for index,arr in enumerate([s,clean,oldroi,decoded_roi]):
        im=Image.alpha_composite(Image.new("RGBA",(bw,bh),(*bg,255)),Image.fromarray(arr,"RGBA"))
        panel.paste(im.convert("RGB").resize((pw,ph),Image.Resampling.LANCZOS),(index*pw,0))
    evidence[name]=proof_png("A255_"+name+"_SOURCE_CLEAN_A228_NEW",panel)
recipe={
 "schema_version":2,"queue_index":59,"run_key":RUN,"text":TEXT,"source_english":"Race The Rivals!",
 "source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "source_sha256":SRC_SHA,"rejected_candidate_sha256":OLD_SHA,
 "source_effect_bbox":BBOX,"new_decoded_source_effect_bbox":[x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3]],
 "font_sha256":hashb(FONT.read_bytes()),"font_face":1,"font_ppem":60,
 "construction":"NEW native Hangul face, source-derived gold and white, separate navy border + outer white; no prior bitmap upscaling, no A228 palette edit; proportional fitting",
 "compression":"BC3 4x4 independent alpha and 565 palette re-encode within canonical original bbox; other blocks byte-identical",
 "source_gold_median":gcol.tolist(),"source_silver_median":wcol.tolist(),
 "approval":"unpromoted trial; controller firsthand producer QA / independent C2/C3/user game separate"
}
rec=save_json("A255_SHA_BOUND_LETTERING_RECIPE",recipe)
report={"schema_version":2,"role":"A","queue_index":59,"run_key":RUN,
 "old_rejected_sha256":OLD_SHA,"canonical_source_sha256":SRC_SHA,
 "triage_read_only_action":action,"documented_method_change_override":documented_override,"official_sha256":OFFICIAL_SHA,
 "new_unpromoted_trial":{"path":str(dds.relative_to(ROOT)),"sha256":hashb(output)},
 "dds_generated":1,"dds_official_promoted":0,
 "format":"DXT5 BC3 2048x512 mip1 RAW vertically mirrored",
 "pixel":{"compressed_blocks_rewritten":count,"rgba_changed_in_bbox":diff,
          "rgba_changed_outside_bbox":outside,
          "alpha_changed_outside_bbox":0,"margins":margins},
 "producer":"PENDING_FIRSTHAND_SAVED_VISUAL_QA", "C2":"NOT_RUN_NEW_SHA",
 "C3":"NOT_RUN","user_ingame":"PJR019_OPEN","RUNTIME_VALIDATION":"UNTESTED",
 "evidence":evidence,"lettering_recipe":rec,"excluded":["VR","FFB","DX11","DXVK"]}
save_json("A255_MACHINE_AND_HANDOFF",report)
print(json.dumps({"run_key":RUN,"new_sha":hashb(output),"changed":diff,"outside":outside,
                  "blocks":count,"bbox_margins":margins},ensure_ascii=False),flush=True)

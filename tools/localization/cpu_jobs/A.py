#!/usr/bin/env python3
"""A250 q035: distinct native source-family italic font/mask rework.
PINK/GREEN Total Rank -> 종합 랭킹, preserved clean background and protected art.
Isolated unpromoted DDS, no independent C2/C3 or runtime approval.
"""
import csv,hashlib,json,os,struct,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw,ImageFilter

assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
ROOT=Path.cwd()
DEST=ROOT/"localization/graphics/role_A/20261012-A250-Q035-NATIVE-ITALIC-TOTAL-RANK"
DEST.mkdir(parents=True,exist_ok=True)
RUN="OUTRUN-KOR-A250-Q035-TOTAL-RANK-ITALIC-NATIVE-20261012-0300"
PRIOR=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_HOLL_RANK_Exst/E989E3B7_1024x1024.dds"
SRC_PNG=ROOT/"localization/graphics/role_A/20261008-A196-Q035-TOTAL-RANK-NATIVE-HIERARCHY/A196_SOURCE_READABLE.png"
CLEAN_PNG=ROOT/"localization/graphics/role_A/20261008-A196-Q035-TOTAL-RANK-NATIVE-HIERARCHY/A196_CLEAN_PLATE.png"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
SOURCE_DDS_UPSTREAM_SHA="b4f0146b9caa0469a410601d633d3394703e5ec85d07f9bd4973ddc766105583"
OLD_DDS_SHA="cc8df5b4bd44d1251dd4703b109ec4e9c45e16cef62a9af53719215c78eb0254"
AREAS={"pink":(609,357,1113,429),"green":(2273,370,2778,442)}
W=H=4096
def sha(b):return hashlib.sha256(b).hexdigest()
def guard(ok,msg):
 if not ok:raise RuntimeError("A250_FAIL_CLOSED "+msg)
def ref(p):return {"path":str(p.relative_to(ROOT)),"sha256":sha(p.read_bytes())}
def png(name,pic):
 p=DEST/(name+".png");pic.save(p);return ref(p)
def jsonfile(name,obj):
 p=DEST/(name+".json");p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return ref(p)
def pic(a):return Image.fromarray(a.astype(np.uint8),"RGBA")
def bg(im,color):return Image.alpha_composite(Image.new("RGBA",im.size,(*color,255)),im).convert("RGB")
def decode(b):
 guard(b[:4]==b"DDS " and len(b)==128+W*H*4,"source DDS not 4096x4096 RGBA")
 guard(struct.unpack_from("<II",b,12)==(H,W),"header size")
 guard(struct.unpack_from("<I",b,28)[0]==1 and struct.unpack_from("<I",b,88)[0]==32,"mip1 RGBA32")
 guard(struct.unpack_from("<IIII",b,92)==(255,65280,16711680,4278190080),"RGBA masks")
 return np.array(Image.frombytes("RGBA",(W,H),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
with (ROOT/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=next(x for x in csv.DictReader(f) if x["index"]=="35")
guard(q["action"]=="localize_text" and "rework" in q["artwork_status"].lower(),"q35 no longer A rework")
guard("A196" in q["notes"],"record of previously rejected A196 missing")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","35"],capture_output=True,text=True,check=True)
jsonfile("A250_TRIAGE",{"stdout":tri.stdout,"stderr":tri.stderr,"run_key":RUN,"new_method":"new native glyph contours + source-calibrated right-italic, not same method, no previous pixels reused"})
oldbytes=PRIOR.read_bytes()
guard(sha(oldbytes)==OLD_DDS_SHA,"previous exact SHA drift")
guard(FONT.exists(),"licensed native CJK font not installed")
original=Image.open(SRC_PNG).convert("RGBA")
clean=Image.open(CLEAN_PNG).convert("RGBA")
guard(original.size==(W,H) and clean.size==(W,H),"source/clean native image resolution drift")
T=decode(oldbytes)
O=T.copy()
S=np.asarray(original)
C=np.asarray(clean)
edits=np.zeros((H,W),dtype=bool)
proof={}
rows=[]
SS=3
for name,(x0,y0,x1,y1) in AREAS.items():
 w=x1-x0;h=y1-y0
 guard(not edits[y0:y1,x0:x1].any(),"overlapping text ROIs")
 edits[y0:y1,x0:x1]=True
 src=S[y0:y1,x0:x1].copy()
 cleanROI=C[y0:y1,x0:x1].copy()
 oldROI=O[y0:y1,x0:x1].copy()
 # The prior A196 SOURCE->CLEAN plate is established, and the original
 # source itself includes colored background art. Never blank the ROI to black.
 # Compare existing border pixels to prove plate color continuity before use.
 border=np.ones((h,w),dtype=bool)
 border[6:-6,6:-6]=False
 diff=np.abs(cleanROI[border].astype(np.int16)-oldROI[border].astype(np.int16))
 guard(float(np.mean(diff[:,:3]))<8.0,"clean plate background color differs from old saved (possible channel-order)")
 font=ImageFont.truetype(str(FONT),60*SS,index=1)
 draft=Image.new("L",(500*SS,120*SS))
 ImageDraw.Draw(draft).text((10*SS,5*SS),"종합 랭킹",font=font,fill=255)
 box=draft.getbbox();guard(box is not None,"CJK glyph absent")
 raw=draft.crop(box)
 lean_amt=0.38
 sw=raw.width+round(raw.height*lean_amt)+6*SS
 skew=raw.transform((sw,raw.height),Image.Transform.AFFINE,(1,lean_amt,-round(raw.height*lean_amt),0,1,0),Image.Resampling.BICUBIC)
 crop=skew.getbbox();guard(crop is not None,"italic failed")
 skew=skew.crop(crop)
 guard(skew.width<w*SS-12*SS and skew.height<h*SS-9*SS,"native text + effect cannot fit")
 layer=Image.new("L",(w*SS,h*SS))
 left=(w*SS-skew.width)//2
 top=(h*SS-skew.height)//2
 guard(left>=5*SS and top>=3*SS,"source text headroom insufficient")
 layer.paste(skew,(left,top))
 edge=layer.filter(ImageFilter.MaxFilter(13)) # 2px rounded dark rim
 # True separate visible white face, dark copper-brown source line and shadow.
 face=Image.new("RGBA",layer.size,(251,250,247,0));face.putalpha(layer)
 rim=Image.new("RGBA",layer.size,(61,20,12,0));rim.putalpha(edge)
 letter=Image.alpha_composite(rim,face).resize((w,h),Image.Resampling.LANCZOS)
 faceNative=face.resize((w,h),Image.Resampling.LANCZOS)
 rimNative=rim.resize((w,h),Image.Resampling.LANCZOS)
 la=np.asarray(letter)
 yy,xx=np.nonzero(la[:,:,3]>0)
 guard(len(xx)>1000,"new label unexpectedly blank")
 localbbox=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
 margin=[localbbox[0],localbbox[1],w-localbbox[2],h-localbbox[3]]
 guard(min(margin)>=2,"text/effect touches original label bbox")
 composed=Image.alpha_composite(pic(cleanROI),letter)
 rendered=np.asarray(composed)
 guard(np.count_nonzero(np.any(rendered!=oldROI,axis=2))>500,"not a material new lettering candidate")
 T[y0:y1,x0:x1]=rendered
 panels={"SOURCE":pic(src),"CLEAN":pic(cleanROI),"OLD_SAVED":pic(oldROI),"FACE":faceNative,"RIM":rimNative,"LETTER":letter,"NEW_COMPOSED":composed}
 for stage,im in panels.items():
  proof[name+"_"+stage]=png("A250_"+name+"_"+stage+"_NATIVE",im)
 proof[name+"_NEW_RAW"]=png("A250_"+name+"_NEW_RAW",composed.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
 for label,color,pct in (("GRAY100",(105,105,105),100),("WHITE75",(255,255,255),75),("BLACK50",(0,0,0),50)):
  ww=max(1,round(w*pct/100));hh=max(1,round(h*pct/100))
  card=Image.new("RGB",(ww*4,hh),color)
  for i,k in enumerate(("SOURCE","CLEAN","OLD_SAVED","NEW_COMPOSED")):
   tile=bg(panels[k],color).resize((ww,hh),Image.Resampling.LANCZOS)
   card.paste(tile,(ww*i,0))
  proof[name+"_"+label]=png("A250_"+name+"_"+label+"_SOURCE_CLEAN_OLD_NEW",card)
 rows.append({"id":name,"original_bbox":[x0,y0,x1,y1],"saved_new_bbox":[x0+localbbox[0],y0+localbbox[1],x0+localbbox[2],y0+localbbox[3]],
              "margin_ltrb":margin,"source_face":"white + dark copper-brown outline","new_face":"near-white + dark copper-brown",
              "right_italic_source_approx":0.38,"new_pixels_inside":int(np.count_nonzero(np.any(rendered!=oldROI,axis=2))),
              "source_clean_bg_difference_mean":float(np.mean(diff[:,:3]))})
all_delta=np.any(T!=O,axis=2)
outside=int(np.count_nonzero(all_delta&~edits))
guard(outside==0,"new candidate modifies protected pixels outside two English ROI boxes")
guard(np.array_equal(T[~edits],O[~edits]),"protected art unexpectedly changed")
dds=DEST/"A250_Q035_TWO_NATIVE_ITALIC_TOTAL_RANK_UNPROMOTED.dds"
dds.write_bytes(oldbytes[:128]+pic(T).transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
saved=decode(dds.read_bytes())
guard(np.array_equal(saved,T),"saved DDS changed pixels vs composed")
guard(len(dds.read_bytes())==len(oldbytes),"DDS size drift")
final={
"schema_version":1,"run_key":RUN,"role":"A","queue_index":35,
"method":"A250 new real native font glyph contours with measured English right-italic impression; white/brown source-family paint, clean plate used per ROI",
"canonical_upstream_source_sha256":SOURCE_DDS_UPSTREAM_SHA,
"pinned_source_png":ref(SRC_PNG),"pinned_clean_png":ref(CLEAN_PNG),"prior_official_sha256":OLD_DDS_SHA,
"new_unpromoted_dds":ref(dds),"new_DDS_count":1,"official_promoted":0,
"native_size":[W,H],"dds_format":"RGBA32","mips":1,
"candidate_diff_rgba_pixels":int(np.count_nonzero(all_delta)),"diff_rgba_outside_two_source_bboxes":outside,
"persisted_dds_roundtrip_mismatch":int(np.count_nonzero(saved!=T)),
"rows":rows,"proofs":proof,
"producer_machine":"PASS_SCOPED_PENDING_CONTROLLER_FIRSTHAND_VISUAL",
"full_C2":"NOT_RUN","C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
"notes":"do not classify source->clean differences outside two legacy boxes as protected damage; prior CLEAN includes original italic halo outside tight text ROI",
"excluded":["VR","FFB","DX11","DXVK"]}
jsonfile("A250_MACHINE_AND_HANDOFF",final)
print(json.dumps({"run":"A250","saved_sha":ref(dds)["sha256"],"outside":outside,"changed":final["candidate_diff_rgba_pixels"],"margins":[r["margin_ltrb"] for r in rows]},ensure_ascii=False),flush=True)

#!/usr/bin/env python3
"""A214 P1 q227 complete producer-native evidence for 13 of 16 C320 uncovered cells.

Existing exact candidate is unchanged. Source, A96R CLEAN, and persisted DDS
are SHA checked, decoded, and alpha-composited without ghost-producing opaque
RGB. This is producer handoff; independent C1 must still rederive and review.
"""
import os,hashlib,struct,urllib.request,tempfile,json,traceback
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
ROOT=Path.cwd()
OUT=ROOT/"localization/graphics/role_A/20261010-A214-Q227-C320-13-CELL-EVIDENCE"
OUT.mkdir(parents=True,exist_ok=True)
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E596B7AC_512x512.dds"
SOURCE_SHA="769308121df7229766b50eea1d43c68703e1720df4147ec8f34b735e2a9527f3"
CANDIDATE=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/E596B7AC_512x512.dds"
CANDIDATE_SHA="83120095e3ff960939c0b413dd85d1633314f23dcde0192f0cf68a7a47776595"
CLEAN=ROOT/"localization/graphics/role_A/20261006-A-REWORK96R-E596B7AC/A96R_CLEAN_PLATE.png"
REGIONS=[
  {
    "id": "intermediate",
    "english": "INTERMEDIATE",
    "korean": "중급",
    "source_bbox": [
      7,
      421,
      676,
      493
    ],
    "candidate_bbox": [
      9,
      422,
      143,
      491
    ],
    "family": "gray_main"
  },
  {
    "id": "outrun",
    "english": "OUTRUN",
    "korean": "아웃런",
    "source_bbox": [
      5,
      512,
      362,
      586
    ],
    "candidate_bbox": [
      7,
      513,
      203,
      584
    ],
    "family": "gray_main"
  },
  {
    "id": "professional",
    "english": "PROFESSIONAL",
    "korean": "프로",
    "source_bbox": [
      3,
      611,
      675,
      686
    ],
    "candidate_bbox": [
      5,
      612,
      170,
      684
    ],
    "family": "gray_main"
  },
  {
    "id": "alpine",
    "english": "ALPINE",
    "korean": "알파인",
    "source_bbox": [
      2,
      701,
      346,
      777
    ],
    "candidate_bbox": [
      4,
      702,
      205,
      775
    ],
    "family": "gray_main"
  },
  {
    "id": "ancient_ruins",
    "english": "ANCIENT RUINS",
    "korean": "에인션트 루인스",
    "source_bbox": [
      2,
      795,
      707,
      875
    ],
    "candidate_bbox": [
      4,
      796,
      545,
      873
    ],
    "family": "gray_main"
  },
  {
    "id": "cape_way",
    "english": "CAPE WAY",
    "korean": "케이프 웨이",
    "source_bbox": [
      8,
      891,
      473,
      971
    ],
    "candidate_bbox": [
      10,
      892,
      386,
      969
    ],
    "family": "gray_main"
  },
  {
    "id": "castle_wall",
    "english": "CASTLE WALL",
    "korean": "캐슬 월",
    "source_bbox": [
      8,
      987,
      634,
      1067
    ],
    "candidate_bbox": [
      10,
      988,
      243,
      1065
    ],
    "family": "gray_main"
  },
  {
    "id": "cloudy_highland",
    "english": "CLOUDY HIGHLAND",
    "korean": "클라우디 하이랜드",
    "source_bbox": [
      1,
      1083,
      835,
      1163
    ],
    "candidate_bbox": [
      3,
      1084,
      604,
      1161
    ],
    "family": "gray_main"
  },
  {
    "id": "coniferous_forest",
    "english": "CONIFEROUS FOREST",
    "korean": "코니퍼러스 포레스트",
    "source_bbox": [
      1,
      1179,
      933,
      1259
    ],
    "candidate_bbox": [
      3,
      1180,
      678,
      1257
    ],
    "family": "gray_main"
  },
  {
    "id": "deep_lake",
    "english": "DEEP LAKE",
    "korean": "딥 레이크",
    "source_bbox": [
      1,
      1277,
      491,
      1353
    ],
    "candidate_bbox": [
      3,
      1278,
      290,
      1351
    ],
    "family": "gray_main"
  },
  {
    "id": "desert",
    "english": "DESERT",
    "korean": "데저트",
    "source_bbox": [
      1,
      1371,
      348,
      1451
    ],
    "candidate_bbox": [
      3,
      1372,
      216,
      1449
    ],
    "family": "gray_main"
  },
  {
    "id": "bay_area",
    "english": "BAY AREA",
    "korean": "베이 에어리어",
    "source_bbox": [
      3,
      1469,
      436,
      1545
    ],
    "candidate_bbox": [
      5,
      1470,
      430,
      1543
    ],
    "family": "gray_main"
  },
  {
    "id": "flagman1",
    "english": "FLAGMAN 1",
    "korean": "플래그맨 1",
    "source_bbox": [
      8,
      1565,
      963,
      1716
    ],
    "candidate_bbox": [
      10,
      1566,
      705,
      1714
    ],
    "family": "red_flag"
  },
  {
    "id": "flagman2",
    "english": "FLAGMAN 2",
    "korean": "플래그맨 2",
    "source_bbox": [
      8,
      1722,
      994,
      1880
    ],
    "candidate_bbox": [
      10,
      1723,
      738,
      1878
    ],
    "family": "red_flag"
  },
  {
    "id": "flagman3",
    "english": "FLAGMAN 3",
    "korean": "플래그맨 3",
    "source_bbox": [
      8,
      1889,
      993,
      2047
    ],
    "candidate_bbox": [
      10,
      1890,
      738,
      2045
    ],
    "family": "red_flag"
  },
  {
    "id": "novice",
    "english": "NOVICE",
    "korean": "초급",
    "source_bbox": [
      1041,
      1640,
      1374,
      1714
    ],
    "candidate_bbox": [
      1043,
      1641,
      1177,
      1712
    ],
    "family": "gray_novice"
  }
]
C320_DONE={"professional","alpine","flagman1"}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_dds(p):
 b=Path(p).read_bytes()
 if b[:4]!=b"DDS " or len(b)!=128+2048*2048*4:raise RuntimeError("DDS signature/byte length drift")
 height,width=struct.unpack_from("<II",b,12)
 pitch,mips=struct.unpack_from("<I",b,20)[0],struct.unpack_from("<I",b,28)[0]
 masks=struct.unpack_from("<IIII",b,92)
 if (width,height,pitch,mips,masks)!=(2048,2048,8192,1,(255,65280,16711680,4278190080)):
  raise RuntimeError("DDS pinned 2048 BGRA/RGBA masks/pitch/mips drift "+str((width,height,pitch,mips,masks)))
 return b[:128],Image.frombytes("RGBA",(2048,2048),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def png(im,path):im.save(path,compress_level=5)
def composite_roi(im,box,rgb):
 crop=im.crop(box)
 back=Image.new("RGBA",crop.size,(*rgb,255));back.alpha_composite(crop)
 return back.convert("RGB")
def execute():
 if sha(CANDIDATE)!=CANDIDATE_SHA:raise RuntimeError("q227 new candidate SHA drift; preserve")
 if not CLEAN.exists():raise RuntimeError("A96R pinned CLEAN missing")
 with tempfile.TemporaryDirectory(prefix="outrun_a214_") as t:
  sp=Path(t)/"original.dds"
  urllib.request.urlretrieve(SOURCE_URL,sp)
  if sha(sp)!=SOURCE_SHA:raise RuntimeError("source original SHA drift")
  sh,source=read_dds(sp)
  hd,final=read_dds(CANDIDATE)
  plate=Image.open(CLEAN).convert("RGBA")
  if source.size!=plate.size or source.size!=final.size or sh!=hd:raise RuntimeError("DDS native/header or PNG mismatch")
  s=np.asarray(source);c=np.asarray(plate);f=np.asarray(final)
  allowed=np.zeros((2048,2048),np.bool_)
  rows=[]
  for row in REGIONS:
   x0,y0,x1,y1=row["source_bbox"]
   x2,y2,x3,y3=row["candidate_bbox"]
   if min(x2-x0,x1-x3,y2-y0,y1-y3)<=0:raise RuntimeError("candidate touches English source bbox: "+row["id"])
   allowed[y0:y1,x0:x1]=True
   src=s[y0:y1,x0:x1];cl=c[y0:y1,x0:x1];cur=f[y0:y1,x0:x1]
   alpha_clean=int(np.count_nonzero(cl[:,:,3]))
   src_alpha=int(np.count_nonzero(src[:,:,3]))
   final_alpha=int(np.count_nonzero(cur[:,:,3]))
   if alpha_clean:raise RuntimeError("source residue in transparent clean "+row["id"]+" "+str(alpha_clean))
   # Existing C320 3 sample outputs are not regenerated or counted as new evidence.
   detail={"id":row["id"],"source":row["english"],"korean":row["korean"],"family":row["family"],
    "source_bbox":row["source_bbox"],"candidate_bbox":row["candidate_bbox"],
    "margins":[x2-x0,x1-x3,y2-y0,y1-y3],"source_alpha_nonzero":src_alpha,
    "clean_alpha_nonzero":alpha_clean,"persisted_candidate_alpha_nonzero":final_alpha,
    "old_transparent_RGB_warning":"RGB bytes beneath alpha=0 are not rendered pixels",
    "new_lossless_native_proof":row["id"] not in C320_DONE}
   rows.append(detail)
   if row["id"] in C320_DONE:continue
   # Explicit true RGBA lossless triptych; preserve PNG alpha for C independent QA.
   width,height=x1-x0,y1-y0
   tri=Image.new("RGBA",(3*width+24,height),(0,0,0,0))
   for k,im in enumerate((source,plate,final)):
    tri.paste(im.crop((x0,y0,x1,y1)),(k*(width+12),0))
   png(tri,OUT/f"A214_{row['id']}_SOURCE_CLEAN_FINAL_NATIVE_RGBA.png")
   for name,rgb in (("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
    tiles=[composite_roi(im,(x0,y0,x1,y1),rgb) for im in (source,plate,final)]
    for pct in (100,75,50):
     panel=Image.new("RGB",(3*width+24,height+24),rgb)
     ImageDraw.Draw(panel).text((5,5),"ENGLISH | TRANSPARENT CLEAN | SAVED KOREAN",fill=(255,225,30) if name!="WHITE" else (0,0,0))
     for k,tile in enumerate(tiles):panel.paste(tile,(k*(width+12),24))
     if pct!=100:panel=panel.resize((panel.width*pct//100,panel.height*pct//100),Image.Resampling.LANCZOS)
     panel.save(OUT/f"A214_{row['id']}_{name}_{pct}.jpg",quality=90,optimize=True)
   # RAW crop corresponds to vertically mirrored region of exactly decoded DDS.
   yy0,yy1=2048-y1,2048-y0
   for label,im in (("SOURCE",source),("CLEAN",plate),("PERSISTED_FINAL",final)):
    raw=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop((x0,yy0,x1,yy1))
    png(raw,OUT/f"A214_{row['id']}_{label}_RAW_NATIVE.png")
  source_to_clean=np.any(s!=c,axis=2)
  source_to_final=np.any(s!=f,axis=2)
  clean_to_final=np.any(c!=f,axis=2)
  counts={
   "source_to_clean_changed_OUTSIDE_16_TEXT_BOXES":int(np.count_nonzero(source_to_clean&~allowed)),
   "source_to_final_changed_OUTSIDE_16_TEXT_BOXES":int(np.count_nonzero(source_to_final&~allowed)),
   "clean_to_final_changed_OUTSIDE_16_TEXT_BOXES":int(np.count_nonzero(clean_to_final&~allowed)),
   "source_to_clean_alpha_changed_OUTSIDE_16_TEXT_BOXES":int(np.count_nonzero((s[:,:,3]!=c[:,:,3])&~allowed)),
   "clean_to_final_alpha_changed_OUTSIDE_16_TEXT_BOXES":int(np.count_nonzero((c[:,:,3]!=f[:,:,3])&~allowed)),
  }
  # Strict fail-closed scope metrics are reported, not assumed 0.
  failed={k:v for k,v in counts.items() if v!=0}
  report={
   "run":"A214","role":"A","queue_index":227,"priority":"P1",
   "run_key":"OUTRUN-KOR-A214-Q227-C320-13CELL-LOSSLESS-EVIDENCE-20261010-0200",
   "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,"clean_png_sha256":sha(CLEAN),
   "new_promoted_dds":0,"current_candidate_changed":False,
   "native_format":"2048x2048 RGBA32 pitch8192 mip1 readable mirror-Y",
   "regions_total":len(rows),"region_producer_native_new":len(rows)-len(C320_DONE),
   "region_prior_C320_native_done":len(C320_DONE),
   "rows":rows,"global_machine":counts,"global_machine_failures":failed,
   "mechanical":"PASS_SCOPED_16_BOXES" if not failed else "HOLD_SCOPE_MISMATCH",
   "producer_visual":"PENDING_FIRST_HAND_COMPOSITE_REVIEW",
   "independent_C1":"C320_HOLD_STRICT_RECHECK_NOT_REPLACED",
   "independent_C3":"PENDING","RUNTIME_VALIDATION":"UNTESTED",
   "qa_scope":"Producer native transparent PNG and black/white/gray 100/75/50 source/CLEAN/final, exact RAW for thirteen previously uncovered. Independent C must re-hash and judge all 16 plus same-stroke source hierarchy",
  }
  (OUT/"A214_EVIDENCE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
  print("A214_REPORT",json.dumps({"new_lossless_regions":report["region_producer_native_new"],"global_checks":counts,"failures":failed}),flush=True)
try:execute()
except Exception as exc:
 fail={"run":"A214","role":"A","queue_index":227,"status":"EXECUTION_HOLD_NO_DDS_CHANGED",
 "exception":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc(),
 "new_promoted_dds":0,"RUNTIME_VALIDATION":"UNTESTED"}
 (OUT/"A214_EXECUTION_HOLD.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n")
 print("A214_ABORT",fail["reason"],flush=True)

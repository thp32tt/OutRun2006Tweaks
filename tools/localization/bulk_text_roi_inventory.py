#!/usr/bin/env python3
"""Prepare complete-HD sources & per-phrase ROI intake; no legacy tile inputs to ImageGen.
Requires separately verified atlas reassembly evidence for recovery sources.
Never invents coordinates or auto-approves multi-phrase text without glyph masks.
"""
import csv,hashlib,json,shutil
from pathlib import Path
from collections import Counter,defaultdict
from PIL import Image

ROOT=Path("work")
M=ROOT/"image-src/inputs/A/HD_EN_TILES_20261014"
ATLAS=ROOT/"text_roi_bulk_20261015/atlases"
OUT=ROOT/"image-src/text_roi_batches"
PILOT=ROOT/"c_salvage_text_roi/output_pilot_20261015/Q104-outrun_mode"
def csvrows(name):
 with (M/name).open(encoding="utf-8-sig",newline="") as fp:return list(csv.DictReader(fp))
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as fp:
  for part in iter(lambda:fp.read(1024*1024),b""):h.update(part)
 return h.hexdigest()
sources=csvrows("SOURCE_MANIFEST_108.csv")
trans=csvrows("OUTRUN_HD_FULL_TRANSLATION_MAPPING_20261013.csv")
bydds=defaultdict(list)
for v in trans:bydds[v["source_dds_path"]].append(v)
proof={}
for d in ATLAS.iterdir():
 if not d.is_dir():continue
 p=d/"atlas_manifest.json"
 if not p.is_file():continue
 e=json.loads(p.read_text(encoding="utf-8"))
 proof[(e["source_png"],e["source_dds_path"],e["source_png_sha256_declared"])]=(d,e)
OUT.mkdir(parents=True,exist_ok=True)
(OUT/"inputs").mkdir(exist_ok=True)
inventory=[]
num=Counter()
review_entries=[]
for r in sources:
 key=(r["png_filename"],r["source_dds_path"],r["png_sha256"])
 rec={"source_png":r["png_filename"],"source_dds_path":r["source_dds_path"],
      "source_dds_sha256":r["dds_sha256"],"expected_full_source_sha256":r["png_sha256"],
      "source_dimensions":[int(r["width"]),int(r["height"])],"queue_indexes":r["queue_indexes"]}
 match=proof.get(key)
 if match:
  d,ev=match
  png=d/"source_reassembled_readable.png"
  if png.exists() and sha(png)==ev["output_sha256"] and ev["tile_count"]>0:
   rec["png_path"]=str(png)
   rec["png_sha256"]=ev["output_sha256"]
   rec["provenance"]="SHA_PINNED_TILE_REASSEMBLY_TEST_ONLY"
   rec["native_dds_equivalence"]="UNVERIFIED"
   rec["atlas_tile_count"]=ev["tile_count"]
   num["full_rebuilt_verified_tiles"]+=1
  else:rec["status"]="HOLD_ATLAS_OUTPUT_CORRUPT";num["hold"]+=1
 else:rec["status"]="HOLD_FULL_SOURCE_MISSING_OR_CORRUPT";num["hold"]+=1
 entries=bydds.get(r["source_dds_path"],[])
 rec["translated_phrases"]=[{"english":v["english_source"],"korean":v["korean_approved"],
                              "status":"HOLD_TEXT_ROI_MAPPING_NOT_VISUALLY_VERIFIED"} for v in entries
                             if v["english_source"] and v["korean_approved"] and v["english_source"]!=v["korean_approved"]]
 if not entries:
  rec["translation_status"]="HOLD_PLATFORM_VARIANT_TRANSLATION_UNBOUND"
  num["platform_unbound"]+=1
 else:num["translation_mapped_sources"]+=1
 if rec.get("png_path") and len(rec["translated_phrases"])==1:
  # Alpha bounding proves all visible alpha, not that all pixels are text.
  src=Path(rec["png_path"])
  with Image.open(src) as im:
   if im.format=="PNG" and im.mode=="RGBA" and tuple(im.size)==tuple(rec["source_dimensions"]):
    alpha=im.getchannel("A")
    bbox=alpha.getbbox()
    if bbox and 0<bbox[0] and 0<bbox[1] and bbox[2]<im.width and bbox[3]<im.height:
     gap=max(5,min(14,int(min(im.size)*0.035)))
     roi=(max(0,bbox[0]-gap),max(0,bbox[1]-gap),min(im.width,bbox[2]+gap),min(im.height,bbox[3]+gap))
     w,h=roi[2]-roi[0],roi[3]-roi[1]
     z=min(4,2048//w,2048//h)
     if z>=1 and w<=2048 and h<=2048:
      name=r["png_filename"][:-4]+"__unreviewed_phrase.png"
      target=OUT/"proposals"/name
      target.parent.mkdir(exist_ok=True)
      crop=im.crop(roi)
      crop=crop.resize((w*z,h*z),Image.Resampling.LANCZOS) if z>1 else crop
      crop.save(target,format="PNG")
      rec["candidate_roi"]={"source_bbox_xyxy":list(roi),"imagegen_candidate_path":str(target),
                             "candidate_sha256":sha(target),"scale":z,
                             "status":"ROI_PROPOSAL_TEXT_CONTENT_NOT_REVIEWED"}
      num["single_phrase_crop_proposals"]+=1
     else:num["single_phrase_size_hold"]+=1
    else:num["single_phrase_alpha_margin_hold"]+=1
 inventory.append(rec)
# Source derived from a separately distributed pinned original HD FULL PNG, not split tiles.
q=next(x for x in sources if x["png_filename"]=="Q104_62BEBF33_BASE_READABLE_FLIPY.png")
qsrc=ROOT/"c_salvage_text_roi/source_full_20261012/q104_62BEBF33_READABLE_FLIPY.png"
qmeta=json.loads((PILOT/"roi_manifest.json").read_text(encoding="utf-8"))
outname="Q104_OutRunMode_FullHD_TextROI_2x.png"
target=OUT/"inputs"/outname
if not target.exists():shutil.copyfile(PILOT/"imagegen_input_upscaled.png",target)
assert sha(qsrc)==qmeta["source_png_sha256"],"pilot full source changed"
assert sha(target)==qmeta["imagegen_input_sha256"],"pilot PNG differs"
assert qmeta["alpha_crop_margin_checked"] is True
ready=[{"id":"Q104_OutRunMode_fullhd","role":"A","queue_index":"104",
        "status":"ROI_APPROVED_FOR_IMAGEGEN","source_provenance":"DIRECT_FULL_HD_PNG",
        "source_dds_path":q["source_dds_path"],"source_dds_sha256":q["dds_sha256"],
        "source_png_sha256":qmeta["source_png_sha256"],"bbox_xyxy":qmeta["bbox_xyxy"],
        "imagegen_input_png":outname,"imagegen_input_sha256":qmeta["imagegen_input_sha256"],
        "alpha_crop_margin_checked":True,"english":"OutRun Mode","korean":"아웃런 모드"}]
prod={"schema":"outrun-text-roi-production-v1","source_manifest":"SOURCE_MANIFEST_108.csv",
      "workflow":"verified full HD source → text ROI → independent ImageGen → QA",
      "legacy_tiles_disabled":True,"items":ready}
(OUT/"production_manifest.json").write_text(json.dumps(prod,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(OUT/"full_source_inventory.json").write_text(json.dumps({"schema":"outrun-hd-source-inventory-v1",
 "sources":inventory,"registered_source_count":len(sources),
 "translation_table_rows":len(trans),"statistics":dict(num)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"sources":len(sources),"translation_rows":len(trans),"stats":dict(num),
                  "registered_input_ready":len(ready),"imagegen_input":str(target),
                  "source_inventory":str(OUT/"full_source_inventory.json"),
                  "production_manifest":str(OUT/"production_manifest.json"),
                  "runtime_validation":"UNTESTED"},ensure_ascii=False))
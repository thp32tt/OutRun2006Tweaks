#!/usr/bin/env python3
"""OutRun Korean ImageGen: two source-native DDS *test-only* exports.

Q089/Q104 only. Preserves original 32-bit BGRA DDS headers, dimensions,
orientation and every pixel outside original text alpha bounding boxes.
No game installation, container rebuild, C1/C3 approval or runtime release.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import struct
import zipfile
from pathlib import Path
from PIL import Image, ImageOps, ImageChops, ImageDraw

ROOT = Path("/home/chatgpt-runner2")
BASE = ROOT / "work/image-src/text_roi_batches"
HD = ROOT / "work/c_salvage_text_roi/c_original_hd_crop_only/hd_original_108_verified"
V4 = BASE / "ab_imagegen_composite_v4_test_only_20261102"
GAME = ROOT / "outrun_2006_pc_or/outrun2006"
SPECS = {
 "Q089": {"source_sha": "0a2c9a32070771338dabc04a7bda67d9b474fd21d6a3456f60d9e1221fc8a96c", "english": "Game Over", "korean": "게임 오버", "roi_id": "Q089_bc7eeb2a41b011ad", "candidate_sha": "9c92ed8dc87c06c7bff1f7a71f89446f02de1a6aa73c8a7160a571433bc5b604", "composed_sha": "6a27bfea1ce6b9c18a230246b9a420fb50ecb469134692dae3cbde6eb1d32f22", "min_iou": 0.90, "max_alpha_mae": 12.0},
 "Q104": {"source_sha": "60454d0080e328e7139f10f69c080a1b2c0a3e959ced3bcdd8b22fb04e1758b4", "english": "OutRun Mode", "korean": "아웃런 모드", "roi_id": "Q104_01e25aa25a681d26", "candidate_sha": "adb42264e5efca13af5ec9429eb9f1de5c5250e01f58a0398a6f224863c97898", "composed_sha": "5ebdf1caa9601431f5d9b078d23bd555b94340f737b15533c974500c9bd7d0f4", "min_iou": 0.90, "max_alpha_mae": 5.0},
}
DEFAULT_OUT = BASE / "ab_imagegen_native_q089_q104_test_only_20261102"
ZIPNAME = "OUTRUN_AB_Q089_Q104_NATIVE_2DDS_TEST_ONLY.zip"

def verify(cond, why):
 if not cond: raise ValueError(why)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def file_sha(path): return digest(path.read_bytes())
def json_bytes(obj): return (json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
def zip_write(z, name, payload):
 zi=zipfile.ZipInfo(name,(1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o100644<<16
 z.writestr(zi,payload,compress_type=zipfile.ZIP_DEFLATED,compresslevel=3)
def metric(a,b):
 from PIL import ImageChops
 import numpy as np
 ap=np.asarray(a.getchannel("A"),dtype=np.int16)
 bp=np.asarray(b.getchannel("A"),dtype=np.int16)
 overlap=((ap>20)&(bp>20)).sum()
 union=((ap>20)|(bp>20)).sum()
 return float(overlap/max(1,union)),float(abs(ap-bp).mean())
def build_one(q,spec):
 report_path=V4/q/"report.json"
 r=json.loads(report_path.read_text(encoding="utf8"))
 verify(r["status"]=="TEST_ONLY_PIXEL_GUARDS_PASS_VISUAL_QA_REQUIRED","REPORT_NOT_STATIC_PASS:"+q)
 verify(r["runtime_validation"]=="UNTESTED" and r["orientation"]=="FLIPY","ORIENTATION_STATUS:"+q)
 verify(len(r["details"])==1 and r["details"][0]["roi_id"]==spec["roi_id"],"ROI_OWNER:"+q)
 detail=r["details"][0]
 verify(detail["english"]==spec["english"] and detail["korean"]==spec["korean"],"TRANSLATION_MISMATCH:"+q)
 verify(detail["candidate_sha256"]==spec["candidate_sha"] and not detail["candidate_border_touch"],"CANDIDATE_FAILED:"+q)
 candidate=BASE/detail["candidate"]
 verify(candidate.is_file() and file_sha(candidate)==spec["candidate_sha"],"CANDIDATE_SHA:"+q)
 source=GAME/r["target_path"]
 native=source.read_bytes()
 verify(digest(native)==spec["source_sha"],"SOURCE_SHA:"+q)
 with Image.open(source) as im: storage=im.convert("RGBA")
 w,h=storage.size
 verify(native[:4]==b"DDS " and len(native)==128+w*h*4,"DDS_NATIVE_LAYOUT:"+q)
 verify(struct.unpack_from("<I",native,28)[0]==1 and struct.unpack_from("<I",native,80)[0]==0x41,"DDS_NATIVE_FLAGS:"+q)
 verify(struct.unpack_from("<I",native,88)[0]==32 and native[84:88]==bytes(4),"DDS_PIXEL_FORMAT:"+q)
 verify(struct.unpack_from("<IIII",native,92)==(0xff0000,0xff00,0xff,0xff000000),"DDS_BGRA_MASKS:"+q)
 verify(native[128:]==storage.tobytes("raw","BGRA"),"DDS_SOURCE_ROUNDTRIP_DIFFERENT:"+q)
 source_hd=HD/r["source"]
 verify(file_sha(source_hd)==r["source_sha256"],"HD_SHA:"+q)
 with Image.open(source_hd) as im: hd=im.convert("RGBA")
 verify(hd.size==(w*4,h*4),"HD_RATIO:"+q)
 readable=ImageOps.flip(storage)
 hd_small=hd.resize((w,h),Image.Resampling.LANCZOS)
 iou,mae=metric(readable,hd_small)
 verify(iou>=spec["min_iou"] and mae<=spec["max_alpha_mae"],f"HD_DDS_ALIGNMENT:{q}:{iou}:{mae}")
 composed=V4/q/"IMAGEGEN_COMPOSED_READABLE_TEST_ONLY.png"
 verify(file_sha(composed)==spec["composed_sha"]==r["output_png_sha256"],"COMPOSED_SHA:"+q)
 with Image.open(composed) as im: edited=im.convert("RGBA")
 verify(edited.size==hd.size,"COMPOSED_HD_DIMENSIONS:"+q)
 glyph_box=edited.getchannel("A").getbbox()
 source_box=readable.getchannel("A").getbbox()
 verify(glyph_box is not None and source_box is not None,"NO_ALPHA:"+q)
 glyph=edited.crop(glyph_box)
 sw=source_box[2]-source_box[0]; sh=source_box[3]-source_box[1]
 gw,gh=glyph.size
 factor=min(sw/gw,sh/gh)
 nw=max(1,min(sw,round(gw*factor)))
 nh=max(1,min(sh,round(gh*factor)))
 ink=glyph.resize((nw,nh),Image.Resampling.LANCZOS)
 ix=source_box[0]+(sw-nw)//2
 iy=source_box[1]+(sh-nh)//2
 clear=readable.copy()
 clear.paste((0,0,0,0),source_box)
 layer=Image.new("RGBA",(w,h),(0,0,0,0))
 layer.paste(ink,(ix,iy))
 final=Image.alpha_composite(clear,layer)
 # Enforce exact no changes outside the native source-alpha bounds, not just HD ROI bands.
 mask=Image.new("L",(w,h),0)
 ImageDraw.Draw(mask).rectangle((source_box[0],source_box[1],source_box[2]-1,source_box[3]-1),fill=255)
 outside=ImageChops.difference(readable,final)
 verify(all(ImageChops.multiply(c,ImageOps.invert(mask)).getbbox() is None for c in outside.split()),"PROTECTED_PIXEL_CHANGED:"+q)
 new_box=final.getchannel("A").getbbox()
 verify(new_box is not None and new_box[0]>=source_box[0] and new_box[1]>=source_box[1] and new_box[2]<=source_box[2] and new_box[3]<=source_box[3],"GLYPH_OUTSIDE_ORIGINAL:"+q)
 encoded=ImageOps.flip(final)
 payload=native[:128]+encoded.tobytes("raw","BGRA")
 verify(payload[:128]==native[:128] and len(payload)==len(native),"DDS_HEADER_OR_LENGTH_CHANGED:"+q)
 with Image.open(io.BytesIO(payload)) as im: decoded=im.convert("RGBA")
 verify(ImageChops.difference(decoded,encoded).getbbox() is None,"DDS_REDECODE_BAD:"+q)
 verify(ImageChops.difference(ImageOps.flip(decoded),final).getbbox() is None,"DDS_FLIPY_BAD:"+q)
 verify(payload!=native,"NO_TEXT_CHANGE:"+q)
 receipt={"status":"TEST_ONLY_NATIVE_BGRA_STATIC_PIXEL_GUARDS_PASS","runtime_validation":"UNTESTED","visual_qa":"REVIEW_REQUIRED","candidate_qa":"UNVERIFIED","q":q,"target_path":r["target_path"],"source_sha256":spec["source_sha"],"source_hd_sha256":r["source_sha256"],"candidate_sha256":spec["candidate_sha"],"composed_hd_sha256":spec["composed_sha"],"output_dds_sha256":digest(payload),"old_native_dimensions":[w,h],"hd_dimensions":list(hd.size),"source_native_ink_box":list(source_box),"new_native_ink_box":list(new_box),"orientation":"FLIPY","alpha_iou_original_vs_hd":round(iou,5),"alpha_mae_original_vs_hd":round(mae,5),"outside_source_ink_bbox_changes":0,"preserve_original_dds_header":True,"preserve_original_dds_mips":True,"english":spec["english"],"korean":spec["korean"],"engine_runtime":"NOT_TESTED"}
 return payload,receipt,final

def run(output):
 output=Path(output).resolve()
 verify(output.is_relative_to(BASE.resolve()),"OUTPUT_MUST_BE_IN_BATCH_ROOT")
 for forbidden in (BASE/"candidate_outputs",BASE/"offline_overlap_v3_ink_test_only",V4,GAME):
  verify(not output.is_relative_to(forbidden.resolve()),"PROTECTED_OUTPUT")
 verify(not output.exists(),"REFUSE_EXISTING_OUTPUT")
 blobs={};receipts={};previews={}
 for q,s in SPECS.items():
  data,rec,preview=build_one(q,s)
  verify(rec["target_path"] not in blobs,"DUPLICATE_TARGET")
  blobs[rec["target_path"]]=data;receipts[q]=rec;previews[q]=preview
 output.mkdir(parents=True)
 for q,preview in previews.items():
  preview.save(output/(q+"_native_readable_preview.png"))
  (output/(q+"_receipt.json")).write_bytes(json_bytes(receipts[q]))
 m={"status":"TEST_ONLY_NOT_RUNTIME_APPROVED","dds_count":len(blobs),"original_files_changed":False,"game_files_written":False,"runtime_validation":"UNTESTED","entries":{q:{"target_path":x["target_path"],"dds_sha256":x["output_dds_sha256"],"native_dimensions":x["old_native_dimensions"]} for q,x in receipts.items()}}
 zp=output/ZIPNAME
 with zipfile.ZipFile(zp,"w") as z:
  for path,data in sorted(blobs.items()):zip_write(z,path,data)
  for q,rec in sorted(receipts.items()):zip_write(z,"qa_receipts/"+q+".json",json_bytes(rec))
  zip_write(z,"TEST_ONLY_MANIFEST.json",json_bytes(m))
 with zipfile.ZipFile(zp) as z:
  verify(z.testzip() is None,"ZIP_CRC_FAIL")
  for path,data in blobs.items():verify(z.read(path)==data,"ZIP_DDS_MISMATCH")
 summary={"status":m["status"],"dds_count":len(blobs),"runtime_validation":"UNTESTED","zip_sha256":file_sha(zp),"zip_bytes":zp.stat().st_size,"entries":m["entries"]}
 (output/"summary.json").write_bytes(json_bytes(summary))
 print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--output",default=str(DEFAULT_OUT))
 a=p.parse_args();run(a.output)

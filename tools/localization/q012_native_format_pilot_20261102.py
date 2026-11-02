#!/usr/bin/env python3
"""Fail-closed Q012 source-format-preserving ImageGen DDS test pilot.
No game/Portainer writes, no paid API, no overwrite, no A/B/C1 changes.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import struct
import zipfile
from pathlib import Path
from PIL import Image, ImageChops

ROOT=Path("/home/chatgpt-runner2")
BASE=ROOT/"work/image-src/text_roi_batches"
SOURCE=ROOT/"outrun_2006_pc_or/outrun2006/textures/load/spr_etc_xst/D6DC1380_256x64.dds"
HD=ROOT/"work/c_salvage_text_roi/c_original_hd_crop_only/hd_original_108_verified/Q012_D6DC1380_BASE_READABLE_NORMAL.png"
CANDIDATE=BASE/"candidate_outputs/B/Q012_0909e9d5397ec72e_source_k.png"
COMPOSED=BASE/"ab_imagegen_composite_v4_test_only_20261102/Q012/IMAGEGEN_COMPOSED_READABLE_TEST_ONLY.png"
REPORT=BASE/"ab_imagegen_composite_v4_test_only_20261102/Q012/report.json"
DEFAULT_OUT=BASE/"ab_imagegen_q012_native_format_test_only_20261102"
TARGET="textures/load/spr_etc_xst/D6DC1380_256x64.dds"
ZIPNAME="OUTRUN_Q012_IMAGEGEN_NATIVE_FORMAT_1DDS_TEST_ONLY.zip"
PIN={
 "original_dds":"42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352",
 "hd":"bfabe98fb448814401f1c4c5bb6ae0cbb2c8ef81bbf9ec4b6457fdcc795ab2e8",
 "candidate":"f88974af1876c6cf4ef21339dcd7c61ec1203165890773033b66c131e82ca75b",
 "composed":"9a84d2ea1dd5d553f4e026af690ebbc20c8253456f526f11d6c90fa6e80a86b5"
}
def sha(b):return hashlib.sha256(b).hexdigest()
def sha_file(p):return sha(p.read_bytes())
def check(condition,message):
 if not condition:raise ValueError(message)
def deterministic(z,name,payload):
 info=zipfile.ZipInfo(name,(1980,1,1,0,0,0))
 info.compress_type=zipfile.ZIP_DEFLATED
 info.external_attr=0o100644<<16
 z.writestr(info,payload,compress_type=zipfile.ZIP_DEFLATED,compresslevel=3)
def run(output):
 output=Path(output)
 forbidden=[SOURCE,HD,CANDIDATE,COMPOSED,REPORT]
 check(not any(output.resolve()==p.resolve() or output.resolve().is_relative_to(p.resolve()) for p in forbidden),"INVALID_OUTPUT")
 check(not output.resolve().is_relative_to((BASE/"candidate_outputs").resolve()),"CANDIDATE_WRITE_FORBIDDEN")
 check(not output.resolve().is_relative_to((BASE/"offline_overlap_v3_ink_test_only").resolve()),"V3_WRITE_FORBIDDEN")
 check(not output.resolve().is_relative_to((ROOT/"outrun_2006_pc_or").resolve()),"GAME_WRITE_FORBIDDEN")
 check(not output.exists(),"REFUSE_EXISTING_OUTPUT")
 for key,path in [("original_dds",SOURCE),("hd",HD),("candidate",CANDIDATE),("composed",COMPOSED)]:
  check(path.is_file() and sha_file(path)==PIN[key],f"PIN_MISMATCH:{key}")
 r=json.loads(REPORT.read_text())
 check(r["status"]=="TEST_ONLY_PIXEL_GUARDS_PASS_VISUAL_QA_REQUIRED","REPORT_STATUS")
 check(r["source_sha256"]==PIN["hd"] and r["target_path"]==TARGET and r["orientation"]=="NORMAL","REPORT_SOURCE")
 check(len(r["details"])==1 and r["details"][0]["candidate_sha256"]==PIN["candidate"],"REPORT_CANDIDATE")
 check(r["details"][0]["english"]=="Continue?" and r["details"][0]["korean"]=="계속?","TEXT_MISMATCH")
 check(r["details"][0]["original_ink_box"]==[8,10,248,44],"ORIGINAL_BOX_CHANGED")
 check(r["outside_text_row_changes"]==0,"EXISTING_GUARD_FAILED")
 with Image.open(HD) as im:hd=im.convert("RGBA")
 with Image.open(SOURCE) as im:original=im.convert("RGBA")
 with Image.open(COMPOSED) as im:composed=im.convert("RGBA")
 check(original.size==hd.size==composed.size==(256,64),"DIMENSION_MISMATCH")
 check(ImageChops.difference(original,hd).getbbox() is None,"HD_NOT_EXACT_ORIGINAL_DDS_DECODE")
 original_data=SOURCE.read_bytes()
 check(original_data[:4]==b"DDS " and len(original_data)==128+256*64*4,"ORIGINAL_DDS_LAYOUT")
 check(struct.unpack_from("<I",original_data,76)[0]==32,"PIXELFORMAT_SIZE")
 check(struct.unpack_from("<I",original_data,80)[0]==0x41,"UNCOMPRESSED_ALPHA_FLAGS")
 check(struct.unpack_from("<I",original_data,88)[0]==32,"BPP")
 check(struct.unpack_from("<IIII",original_data,92)==(0xff0000,0xff00,0xff,0xff000000),"BGRA_MASKS")
 check(struct.unpack_from("<I",original_data,28)[0]==1,"MIP_COUNT")
 check(original_data[84:88]==bytes(4),"FOURCC_NOT_EMPTY")
 # The original header and pixel masks are preserved byte-for-byte.
 # BGRA matches original source's R/G/B masks; unlike the previous RGBA DDS writer.
 native_dds=original_data[:128]+composed.tobytes("raw","BGRA")
 check(len(native_dds)==len(original_data),"DDS_SIZE_MISMATCH")
 with Image.open(io.BytesIO(native_dds)) as im:roundtrip=im.convert("RGBA")
 check(ImageChops.difference(roundtrip,composed).getbbox() is None,"DDS_REDECODE_FAILED")
 check(native_dds[:128]==original_data[:128],"HEADER_CHANGED")
 # Outside the approved English glyph's exact bounding rectangle, no pixel may change.
 box=(8,10,248,44)
 diff=ImageChops.difference(original,roundtrip)
 check(diff.getbbox()==box,"DIFF_BOUNDING_BOX_CHANGED")
 from PIL import ImageDraw
 mask=Image.new("L",original.size,0)
 ImageDraw.Draw(mask).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=255)
 outside=ImageChops.difference(original,roundtrip)
 protected=ImageChops.invert(mask)
 check(all(ImageChops.multiply(channel,protected).getbbox() is None for channel in outside.split()),"PROTECTED_PIXEL_CHANGED")
 # Source glyph alpha entirely lies inside the permitted box: English CLEAN region is isolated.
 check(original.getchannel("A").getbbox()==box,"SOURCE_ALPHA_OUTSIDE_CLEAN_BOX")
 check(composed.getchannel("A").getbbox() is not None,"COMPOSED_INK_MISSING")
 check(r["details"][0]["candidate_border_touch"] is False,"CANDIDATE_BORDER_TOUCH")
 receipt={
  "status":"TEST_ONLY_NATIVE_BGRA_FORMAT_AND_PIXEL_GUARDS_PASS",
  "runtime_validation":"UNTESTED",
  "visual_review":"Q012 single-line Korean 계속? manually reviewed; gameplay not tested",
  "target_path":TARGET,
  "original_dds_sha256":PIN["original_dds"],
  "source_hd_png_sha256":PIN["hd"],
  "candidate_png_sha256":PIN["candidate"],
  "composed_png_sha256":PIN["composed"],
  "output_dds_sha256":sha(native_dds),
  "dimensions":[256,64],
  "original_and_output_pixel_masks":["0x00ff0000","0x0000ff00","0x000000ff","0xff000000"],
  "header_identical":True,
  "mipmaps":1,
  "orientation":"NORMAL",
  "english":"Continue?",
  "korean":"계속?",
  "approved_clean_box":list(box),
  "outside_box_pixel_changes":0,
  "dds_save_redecode_exact":True,
  "protected_art_preserved":True,
  "warnings":["single-source isolated text only","manual user gameplay test required","not a runtime release","original file remains unchanged"]
 }
 receipt_data=(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode()
 manifest_data=(json.dumps({"status":"TEST_ONLY_NOT_RUNTIME_APPROVED","dds_count":1,"paths":[TARGET],"original_dds_sha256":PIN["original_dds"],"output_dds_sha256":sha(native_dds),"game_files_written":False},ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode()
 output.mkdir(parents=True)
 (output/"Q012_native_format_test_only.dds").write_bytes(native_dds)
 (output/"Q012_receipt.json").write_bytes(receipt_data)
 zip_path=output/ZIPNAME
 with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
  for n,p in [(TARGET,native_dds),("qa_receipts/Q012_native_format.json",receipt_data),("TEST_ONLY_MANIFEST.json",manifest_data)]:
   deterministic(z,n,p)
 with zipfile.ZipFile(zip_path) as z:
  check(z.testzip() is None,"ZIP_CRC_FAILED")
  check(z.read(TARGET)==native_dds,"ZIP_DDS_MISMATCH")
 summary={"status":receipt["status"],"zip_sha256":sha_file(zip_path),"zip_bytes":zip_path.stat().st_size,"dds_sha256":sha(native_dds),"original_dds_sha256":PIN["original_dds"],"output":str(output),"runtime_validation":"UNTESTED"}
 (output/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
 print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--output",default=str(DEFAULT_OUT))
 args=p.parse_args()
 run(args.output)
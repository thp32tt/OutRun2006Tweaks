#!/usr/bin/env python3
"""Q051 native DDS no-op rgba round trip (isolated F0 artifact; no game modifications)."""
from pathlib import Path
from PIL import Image
import hashlib,io,json,struct,datetime
BASE=Path("/home/chatgpt-runner2/work/c_salvage_text_roi")
OUT=BASE/"F0_Q051_NATIVE_DDS_20261016"
SRC=BASE/"source_full_20261012"/"q051_FF2462BB_GITHUB_HD_SOURCE_20261015.dds"
PNG=BASE/"source_full_20261012"/"q051_FF2462BB_FLIPY_CHECK_ORIENTATION.png"
EXPECTED_SOURCE_SHA="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
EXPECTED_READABLE_SHA="2da1b6f01219356ddc6ea925bd8fcd4afd37d9040eb48081a40861cc649da6f0"
def sha(b):return hashlib.sha256(b).hexdigest()
raw=SRC.read_bytes()
if sha(raw)!=EXPECTED_SOURCE_SHA:raise RuntimeError("PINNED_SOURCE_DDS_MISMATCH")
if sha(PNG.read_bytes())!=EXPECTED_READABLE_SHA:raise RuntimeError("PINNED_READABLE_PNG_MISMATCH")
u=lambda x:struct.unpack_from("<I",raw,x)[0]
if (raw[:4]!=b"DDS " or u(4)!=124 or u(76)!=32 or
   u(12)!=2048 or u(16)!=4096 or u(20)!=16384 or u(28)!=1 or
   u(80)!=0x41 or u(88)!=32 or
   tuple(u(x) for x in (92,96,100,104))!=(0xFF,0xFF00,0xFF0000,0xFF000000) or
   len(raw)!=(128+4096*2048*4)):
    raise RuntimeError("UNSUPPORTED_DDS_LAYOUT_HOLD")
with Image.open(SRC) as source:
    native=source.convert("RGBA")
    pixels=native.tobytes()
assert len(pixels)==len(raw)-128
payload_eq=(pixels==raw[128:])
if not payload_eq:raise RuntimeError("DDS_NATIVE_RGBA_PAYLOAD_ROUNDTRIP_NOT_BYTE_EXACT")
header=raw[:128]
reencoded=header+pixels
p=OUT/"Q051_FF2462BB_F0_NOOP_RGBA32_TEST_ONLY.dds"
if p.exists():
    if sha(p.read_bytes())!=sha(raw): raise RuntimeError("OLD_TEST_ARTIFACT_MISMATCH_NO_OVERWRITE")
else:p.write_bytes(reencoded)
assert p.read_bytes()==raw
with Image.open(p) as trial:
    final=trial.convert("RGBA")
    decoded_equal=(final.tobytes()==pixels)
assert decoded_equal
with Image.open(PNG) as readable:
    # PIL flip is full image, but atlas elements can require additional per-sprite transforms.
    readable_equal=(native.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()==readable.convert("RGBA").tobytes())
assert readable_equal
report={
"schema":"outrun-q051-f0-noop-v1","date_kst":"2026-10-16","source_dds_path":str(SRC),
"source_readable_png_path":str(PNG),"source_dds_sha256":sha(raw),"readable_png_sha256":sha(PNG.read_bytes()),
"output_dds_path":str(p),"test_dds_sha256":sha(p.read_bytes()),
"source_size_bytes":len(raw),"dds_header_size":128,"width":4096,"height":2048,
"pixel_layout":"DDS_LEGACY_RGB32_RGBA8888_MASKS","mips":1,"row_pitch":16384,
"header_bytes_exact":True,"encoded_pixel_payload_exact":payload_eq,
"redecoded_rgba_pixels_exact":decoded_equal,"readable_png_full_flip_y_pixels_exact":readable_equal,
"opaque_roi_is_letter_layer":False,
"source_original_untouched":True,"runtime_validation":"UNTESTED",
"no_op_static":"PASS","F0_overall":"HOLD_UNTIL_CLEAN_AND_GAME_BASELINE",
"qa_c1":"NOT_RUN","qa_c3":"NOT_RUN",
"note":"Original was not mutated; isolated byte-identical DDS test output. No real game was run; no auto-promotion."}
m=OUT/"Q051_F0_NOOP_REPORT.json"
m.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False,indent=2))
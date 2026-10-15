#!/usr/bin/env python3
"""Isolated manual Q051 five-label image-generation reference sheet. No controllers."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json, hashlib, io, zipfile, datetime, os
SRC=Path("/home/chatgpt-runner2/work/c_salvage_text_roi/original_hd_phrase_crops_20261016/DELIVERABLE_V3_20261016")
OUT=Path("/home/chatgpt-runner2/work/c_salvage_text_roi/manual_batch_sheet_pilot_20261016/Q051_HUD_YELLOW_5")
BATCH=[
 ("A1","031_Q051_TOTAL_TIME_EN_NATIVE.png","TOTAL TIME","총 시간"),
 ("A2","032_Q051_LAP_TIME_EN_NATIVE.png","LAP TIME","랩 타임"),
 ("B1","033_Q051_HEARTS_EN_NATIVE.png","HEARTS","하트"),
 ("B2","034_Q051_SCORE_HUD_EN_NATIVE.png","SCORE","점수"),
 ("C1","035_Q051_TIME_HUD_EN_NATIVE.png","TIME","시간"),
]
def hash_bytes(s):return hashlib.sha256(s).hexdigest()
def save_new(filename,contents):
    p=OUT/filename
    if p.exists():raise RuntimeError("existing output preserved, no overwrite: "+str(p))
    p.write_bytes(contents)
    return {"path":str(p),"sha256":hash_bytes(contents),"bytes":len(contents)}
def png_bytes(im):
    b=io.BytesIO();im.save(b,format="PNG",compress_level=6);return b.getvalue()
canvas=Image.new("RGBA",(1280,768),(18,22,35,255))
review=Image.new("RGBA",(1280,768),(18,22,35,255))
draw=ImageDraw.Draw(review)
items=[]
for i,(slot,file,en,kr) in enumerate(BATCH):
    source=SRC/file
    raw=source.read_bytes()
    with Image.open(io.BytesIO(raw)) as z:
        if z.format!="PNG" or z.mode!="RGBA":raise RuntimeError("unexpected source type: "+file)
        crop=z.copy()
    w,h=crop.size
    col=i%2; row=i//2
    cw,ch=640,256
    if w>cw-80 or h>ch-72:raise RuntimeError("source too big, no resizing: "+file)
    x=col*cw+(cw-w)//2
    y=row*ch+75+(ch-75-h)//2
    rect=[x,y,x+w,y+h]
    for prev in items:
        a=prev["slot_xyxy"]
        if max(a[0],x)<min(a[2],x+w) and max(a[1],y)<min(a[3],y+h):raise RuntimeError("overlap")
    canvas.paste(crop,(x,y))
    review.paste(crop,(x,y))
    draw.text((col*cw+17,row*ch+15),f"{slot}: {en} -> {kr}",fill=(226,232,240,255))
    checked=canvas.crop(tuple(rect))
    assert checked.tobytes()==crop.tobytes(),"pixel fidelity failure"
    items.append({"slot":slot,"index":i+1,"english":en,"korean_trial_only":kr,"source_filename":file,
      "source_path":str(source),"source_png_sha256":hash_bytes(raw),"source_width":w,"source_height":h,
      "slot_xyxy":rect,"cropped_region_raw_rgba_exact":True,
      "source_orientation":"unchanged original readable crop",
      "plate_state":"OPAQUE_SOURCE_ART_INCLUDED_REFERENCE_ONLY","CLEAN":"NOT_RUN",
      "edge_neighbor_overlap_visual_review":"PENDING_MANUAL_VISUAL_REVIEW"})
res={}
res["sheet_reference.png"]=save_new("sheet_reference.png",png_bytes(canvas))
res["sheet_review.png"]=save_new("sheet_review.png",png_bytes(review))
prompt="""OutRun 2006 Korean image reference sheet, five independent label slots. Edit the provided IMAGE, not a new imagined image. Replace only the yellow/navy italic English lettering in the five source ROIs with EXACT Hangul:
upper-left TOTAL TIME -> 총 시간; upper-right LAP TIME -> 랩 타임;
middle-left HEARTS -> 하트; middle-right SCORE -> 점수;
lower-left TIME -> 시간.
Keep all five slots in their respective positions, separated by generous blank spacing. Maintain the yellow italic letter shapes, dark navy outline/shadow, and relative sizes. Never omit, duplicate or reorder a slot, never generate fake Hangul, numbers, icons or unrelated graphics. Do not change neighboring colored backgrounds, borders or protected artwork. Prefer a transparent Korean lettering-only output if reliable, else an obviously marked reference-only sheet for review. This request is a TEST_ONLY trial. Exact original UI dimensions, alphas, DDS and in-game behavior are NOT approved.
"""
res["GENERATION_PROMPT.txt"]=save_new("GENERATION_PROMPT.txt",prompt.encode("utf-8"))
manifest={"schema":"outrun-manual-static-batch-sheet-pilot-v1",
 "batch_id":"Q051_HUD_YELLOW_5_20261016","created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "workflow":"ISOLATED_USER_AUTHORIZED_STATIC_SHEET_TEST_ONLY",
 "controller_restart":False,"A_B_C_C1_state":"UNCHANGED","source_policy":"READ_EXISTING_NATIVE_Q051_CROPS_NO_REASSEMBLY_NO_LEGACY_986_TILES",
 "sheet_canvas":[1280,768],"sheet_pixels":"Native source ROIs pasted without resize/rotation/transparency extraction",
 "input_quality":"REFERENCE_ONLY_OPAQUE_SOURCE_CROPS; not approved for CLEAN/DDS",
 "items":items,"outputs":res,"imagegen":"NOT_RUN","dds":"NOT_RUN",
 "C1_C3_QA":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED"}
res["manifest.json"]=save_new("manifest.json",json.dumps(manifest,ensure_ascii=False,indent=2).encode("utf-8"))
zbuf=io.BytesIO()
with zipfile.ZipFile(zbuf,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for filename in ["sheet_reference.png","sheet_review.png","GENERATION_PROMPT.txt","manifest.json"]:
        z.write(OUT/filename,arcname=filename)
res["Q051_HUD_YELLOW_5_TEST_ONLY.zip"]=save_new("Q051_HUD_YELLOW_5_TEST_ONLY.zip",zbuf.getvalue())
audit={"passed":True,"items":len(items),"canvas":list(canvas.size),"source_pasted_native_pixels_exact":True,
 "outputs":res,"important_hold":"Original opaque plate/neighbor pixels included, not isolated letter layers"}
print(json.dumps(audit,ensure_ascii=False,indent=2))

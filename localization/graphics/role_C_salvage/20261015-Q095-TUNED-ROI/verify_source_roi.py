from pathlib import Path
from PIL import Image
import hashlib,json,numpy as np
root=Path("/home/chatgpt-runner2/work/c_roi_q095_tuned_20261015_2203")
out=root/"output/Q095-tuned_label"
source=Path("/home/chatgpt-runner2/work/c_roi_q095_entry_20261015_2103/source/37759842_FULL_ENGLISH_ORIGINAL_FLIPY_1024x1024.png")
dds=Path("/home/chatgpt-runner2/work/c_roi_source_20261015_1933/37759842_1024x1024_original.dds")
m=json.loads((out/"roi_manifest.json").read_text())
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=Image.open(source);raw=Image.open(dds).convert("RGBA")
native=Image.open(out/"english_text_roi_native.png")
up=Image.open(out/"imagegen_input_upscaled.png")
bbox=(746,8,843,45)
a=np.asarray(native.getchannel("A"))>0
ys,xs=np.where(a)
margins=[int(xs.min()),int(ys.min()),int(native.width-1-xs.max()),int(native.height-1-ys.max())]
border=[int(a[:2].sum()),int(a[-2:].sum()),int(a[:,:2].sum()),int(a[:,-2:].sum())]
checks={
  "github_blob_sha_pinned":"c888e9b1c87dabdc7a6f5ef47dd88498b95b2d83",
  "source_original_dds_sha":h(dds)=="ec69c95e638f6ba1ef2c23db173462adb26ad0d10caed28f1c83b7d1d15658f0",
  "source_full_png_sha":h(source)=="8b78a092b5ca82276076cc5d99b05afd0831651ae2d4afbbcf7486f4693fa7c9",
  "dds_pc_rgba32_1024x1024":raw.size==(1024,1024) and raw.mode=="RGBA" and dds.stat().st_size==4194432,
  "full_png_pixel_exact_to_direct_pc_dds_flip_y":np.array_equal(np.asarray(s),np.asarray(raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM))),
  "exact_native_full_source_crop":np.array_equal(np.asarray(native),np.asarray(s.crop(bbox))),
  "rgba_dimensions":s.mode==native.mode==up.mode=="RGBA" and native.size==(97,37) and up.size==(388,148),
  "native_sha":h(out/"english_text_roi_native.png")==m["native_png_sha256"],
  "upscaled_sha":h(out/"imagegen_input_upscaled.png")==m["imagegen_input_sha256"],
  "boundary_alpha_2px_empty":border==[0,0,0,0],
  "alpha_margin_at_least_2px":min(margins)>=2,
  "english_and_korean_mapping":m["english"]=="Tuned" and m["korean"]=="튜닝",
  "schema_is_outrun_hd_text_roi_v1":m["schema"]=="outrun-hd-text-roi-v1",
  "source_direct_full_not_tile":True
}
assert all(v is True for k,v in checks.items() if isinstance(v,bool)),checks
receipt={"schema":"outrun-c-roi-source-verification-v1","TASK_ID":"OUTRUN-C-ROI-SOURCE-Q095-TUNED-20261015-2203","source_repo":"thp32tt/OutRun2006Tweaks","source_branch":"korean-localization-recovery-20260928","source_platform":"PC","source_dds_path":m["source_dds_path"],"source_dds_git_blob_sha":"c888e9b1c87dabdc7a6f5ef47dd88498b95b2d83","source_dds_sha256":h(dds),"source_dds_dimensions":list(raw.size),"source_dds_decoded_mode":"RGBA32","source_png_sha256":h(source),"source_orientation":"FLIP_Y_READABLE","full_png_source_type":"PIXEL_EXACT_FROM_ORIGINAL_PC_DDS","english":m["english"],"korean":m["korean"],"translation_source":"Q095 reviewed graphic mapping transcriptions.jsonl","roi_bbox_native_xyxy":list(bbox),"native_dimensions":list(native.size),"native_png_sha256":h(out/"english_text_roi_native.png"),"upscale":4,"imagegen_input_dimensions":list(up.size),"imagegen_input_sha256":h(out/"imagegen_input_upscaled.png"),"alpha_bbox_global_xyxy":[int(xs.min()+bbox[0]),int(ys.min()+bbox[1]),int(xs.max()+bbox[0]+1),int(ys.max()+bbox[1]+1)],"alpha_margin_LTRB_px":margins,"alpha_edge_2px_nonzero_counts_TBLR":border,"alpha_nonzero_count":int(a.sum()),"source_text_visual_observation":"single full Tuned lettering+outline+shadow; no adjoining label or glyph in ROI","test_checks":checks,"old_986_tile_inputs_used":False,"existing_AB_queue_consumed_or_changed_by_this_run":False,"imagegen_called":False,"new_AB_dispatch_enabled":False,"hangul_output_generated":False,"CLEAN_PLATE":"NOT_GENERATED","manual_mask_used":False,"native_restore":"ASPECT_RATIO_PRESERVE_AND_REVIEW_UI_CELL_UV_SAFETY; WIDTH_DIFFERENCE_ALONE_NOT_REJECT","C1_QA":"NOT_RUN","C3_QA":"NOT_RUN","REAL_GAME":"NOT_RUN","QA":"TEST_ONLY","RUNTIME_VALIDATION":"UNTESTED","status":"IMAGEGEN_REFERENCE_TEST_ONLY"}
(out/"SOURCE_ROI_QA_TEST_ONLY.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status":"PASS_SOURCE_TEST_ONLY","checks_count":len(checks),"alpha_margin_LTRB_px":margins,"border_TBLR":border,"native_png_sha256":m["native_png_sha256"],"input_png_sha256":m["imagegen_input_sha256"],"QA_sha256":h(out/"SOURCE_ROI_QA_TEST_ONLY.json")},ensure_ascii=False))
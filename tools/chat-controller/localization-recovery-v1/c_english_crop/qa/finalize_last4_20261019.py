#!/usr/bin/env python3
"""Verify non-destructive C slot last-four handoff. Read-only audit, report writes only."""
import hashlib,json,datetime
from pathlib import Path
B=Path("/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only")
Q=B/"qa_review_20261018"
s=json.loads((Q/"LAST4_20261019_SUMMARY.json").read_text(encoding="utf-8"))
hold=json.loads((Q/"REWORK_REMAINING_2_20261019.json").read_text(encoding="utf-8"))
assert s["new_native_pixel_candidates"]==2 and len(s["items"])==4
assert len(hold["items"])==2
assert [h["index"] for h in hold["items"]]==[36,59]
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
all_new=[p for p in Q.rglob("english_native_rework_candidate.png")]
old_src=[p for p in (B/"hd108_outputs").rglob("english_original_native_crop.png")]
assert len(all_new)==44,("44 expected, found",len(all_new))
assert len(old_src)==242
for item in s["items"]:
 if "candidate_path" not in item:continue
 p=Path(item["candidate_path"])
 assert p.is_file() and sha(p)==item["candidate_sha256"]
master=Path("/home/chatgpt-runner2/work/c_salvage_text_roi/original_hd_phrase_crops_20261016/MASTER_255_V2_20261016/MASTER_CROP_MANIFEST_255.json")
j=json.loads(master.read_text(encoding="utf-8"))
assert len(j.get("items",[]))==255
curr={
 "state":"LAST4_HANDOFF_READY_SOURCE_PIXEL_QA_ONLY",
 "date_kst":"2026-10-19",
 "original_full_hd_png":108,
 "original_native_roi_png":242,
 "historic_master_items":255,
 "historic_master_sha256_current":sha(master),
 "prior_native_rework_candidates":42,
 "last4_completed_new_crop_candidates":2,
 "total_native_rework_test_only":44,
 "unsolved_without_layer_separation":2,
 "holds":[{"index":i["index"],"phrase":i["english_official_reference"],"reason":i["reason"]} for i in hold["items"]],
 "no_original_png_or_existing_crop_modified":True,
 "qa_verification":"44/44 SHA TEST_ONLY",
 "korean_composite":"NOT_RUN",
 "A_B":"UNTOUCHED",
 "gameplay":"UNTESTED",
 "not_promoted_to_release":True
}
(Q/"FINAL_LAST4_20261019_QA.json").write_text(json.dumps(curr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
info="""# OutRun 2006 native-HD source English crop: last four, 2026-10-19

## Scope
Existing GitOps C slot: `thp32tt/OutRun2006Tweaks` branch
`localization-controller-recovery-20260928`, service `outrun-c-english-native-crop`.

Input is SHA-pinned, original, unsplit N100 full HD PNG. This handoff runs
**no OCR redo, no ImageGen, no PSD import/compositing, no DDS write** and makes
no C1/C3 or game success claim. The active GitOps C container needs no redeploy
for these **separately generated QA artifacts**.

## Final four outcomes
| QA index | Original phrase | Resolution |
|:---|:---|:---|
| 012 | Leader! (official transcription) | Re-cropped native pixels at [3145,870,3604,977]. Adjacent left-side black UI rule excluded; original glyph and punctuation preserved. **Visual punctuation resembles colon rather than official exclamation; semantic approval pending.** |
| 049 | SELECT LICENSE | Re-cropped at [1955,548,3520,674]. Previous top duplicated text and lower UI bar excluded. |
| 036 | HARD | **HOLD.** Original word outline shares the white/green plate edge. A tighter rectangle removes glyph/outline pixels; cannot crop away backing art while preserving all original text pixels. |
| 059 | CONIFEROUS FOREST | **HOLD.** Neighboring STAGES sprite abuts the final T; moving the right edge cuts the glyph. |

The two new test-only native crops were verified against the original atlas
SHA256 and original region RGBA byte-for-byte. Their N100 location:
`qa_review_20261018/reworked_last4_20261019_test_only/`.

All four old and alternative preview images:
`LAST4_VISUAL_PROTOTYPE_012.jpg`,
`LAST4_VISUAL_PROTOTYPE_036.jpg`,
`LAST4_VISUAL_PROTOTYPE_049.jpg`,
`LAST4_VISUAL_PROTOTYPE_059.jpg`.

Two remaining HOLD items: `REWORK_REMAINING_2_20261019.json`.
All metadata: `LAST4_20261019_SUMMARY.json` and `FINAL_LAST4_20261019_QA.json`.

## Downstream safe next actions
- HARD: upstream `Sonic-TV/OR2006Sprites` PSD index reports
  `OutRun2SP Mode UI/spr_sprani_loading_cvt_Exst/33491F83_512x256.psd`,
  revision `3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6`; index states PSD
  is **not copied into the branch**. Examine original separate editable
  layers only with a new approved workflow. It is not part of these C outputs.
- CONIFEROUS FOREST: distinct Q147 original atlas also has a recorded
  phrase, but **font/style/assets are different**, so its crop is not a
  pixel-faithful substitute for Q201. Original layer separation is needed.
- Neither HOLD item may be auto-approved or have its source pixels/mask
  silently edited.

## Verified cumulative state
- Original full HD PNGs: **108/108**.
- Existing original C pixel crops: **242/242**, untouched.
- Rework test-only native crops: **44/44** manifest+SHA-checked, including
  two from this pass.
- Historic `MASTER_255` crop archive: **255 items**, untouched.
- Need separate visual/semantic review before Korean generation or
  game acceptance. A/B, controller scheduling, DDS and game files untouched.
"""
(Q/"LAST4_C_NATIVE_QA_REPORT_20261019.md").write_text(info,encoding="utf-8")
print(json.dumps({"result":curr,"report_path":str(Q/"LAST4_C_NATIVE_QA_REPORT_20261019.md")},ensure_ascii=False))
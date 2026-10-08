#!/usr/bin/env python3
"""B296 q060 P0 IGR-044: promote ONLY source-proven white material partial repair.
Stage and gold OUTRUN MILES remain explicit REWORK_REQUIRED.
"""
import hashlib,os,json,io
from pathlib import Path
import numpy as np
from PIL import Image
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
g=Path("localization/graphics")
p=g/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
d=g/"role_B/20261009-B295-Q060-P0-SOURCE-CLEAN-GLYPH-PLATE/A064FDFC_B295_TRIAL_NOT_PROMOTED.dds"
out=g/"role_B/20261009-B296-Q060-P0-WHITE-MATERIAL-PARTIAL-PRODUCTION"
out.mkdir(parents=True,exist_ok=True)
oldsha="457f29f6e3a42b674411baae993c6660addca8e6aa4c0f3904af60ec4e0a20e2"
newsha="d938fdd1c92e43bd9fe2f51e3f0ba87c60662c39aaea41e8905e8f850901c2f2"
sha=lambda b:hashlib.sha256(b).hexdigest()
old=p.read_bytes();new=d.read_bytes()
assert sha(old)==oldsha,("current concurrently moved",sha(old))
assert sha(new)==newsha
assert len(old)==len(new)==128+4096*2048*4 and old[:128]==new[:128]
def dec(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
a=dec(old);b=dec(new)
assert a.shape==b.shape==(2048,4096,4)
changed=np.any(a!=b,axis=2)
allowed=np.zeros((2048,4096),bool);allowed[245:385,1090:1930]=True
outside=int(np.count_nonzero(changed&~allowed))
assert changed.any() and outside==0,("protected outside current english effect bbox",outside)
# A full-atlas alpha mask test ensures no fake opaque background was inserted.
opaque_increase=int(np.count_nonzero((b[:,:,3]>a[:,:,3])&allowed))
opaque_decrease=int(np.count_nonzero((b[:,:,3]<a[:,:,3])&allowed))
assert not np.any(a[~allowed]!=b[~allowed])
assert not np.any(a[:245]!=b[:245])
assert not np.any(a[385:]!=b[385:])
# q060 Stage and gold are separate source glyph rows, never copy/alter them.
for key,(l,t,r,bb) in {
 "stage":(455,245,690,350),
 "gold":(2081,250,2860,370),
 "ranking":(120,245,455,350),
 "rank":(690,245,875,350),
 "heart_adjacent":(2500,0,4096,245)
}.items():
 assert np.array_equal(a[t:bb,l:r],b[t:bb,l:r]),("OTHER_ART_CHANGED",key)
assert np.array_equal(dec(new),b)
# Prior machine QA source vs SOURCE_CLEAN: removes 61502 pixels, native
# alpha=0, outside canonical source mask untouched; SOURCE/CLEAN/CURRENT/TRIAL
# 100/75/50 and RAW proofs: B295. ChatGPT controller visual: white face PASS
# for partial area ONLY; no claim that remaining Stage/gold passed.
p.write_bytes(new)
assert sha(p.read_bytes())==newsha
qa={"schema_version":2,"role":"B","run":"B296",
 "run_key":"OUTRUN-KOR-B296-Q060-IGR044-PARTIAL-WHITE-FACE-20261009",
 "index":60,"priority":"P0","regression":"IGR-044_OPEN_USER_INGAME_FAIL",
 "source_sha256":"6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc",
 "old_candidate_sha256":oldsha,"new_candidate_sha256":newsha,
 "candidate_path":str(p),"origin_trial_path":str(d),
 "method":"EXISTING_NATIVE_HANGUL_GLYPH_SHA_PINNED_WHITE_MATERIAL_PLUS_SOURCE_DERIVED_PLATE",
 "partial_repair_region":"outrun_miles_white",
 "source_original_text_mask_upper_y238_245_reconstructed_as_CLEAN_ONLY_PROTECTED_IN_FINAL":True,
 "source_clean_english_alpha":"SOURCE_CLEAN_NATIVE_RGBA_AND_GRAY_100_75_50_CONFIRMED_ZERO_IN_MASK",
 "source_clean_composite_visual":"DIRECT_CONTROLLER_REVIEWED_NATIVE_100_75_50_AND_RAW",
 "source_style_change":"hollow/chrome Korean -> fully white source-family softened fill",
 "source_effect_bbox":[1090,245,1930,385],
 "candidate_dimensions":[4096,2048],"dds_format":"RGBA32","mip_count":1,"orientation":"RAW_mirror_y",
 "header_exact":True,"persisted_decode_exact":True,
 "changed_pixels_total":int(changed.sum()),"changed_outside_source_bbox":outside,
 "alpha_increased_within_source_bbox":opaque_increase,
 "alpha_decreased_within_source_bbox":opaque_decrease,
 "other_approved_glyphs_and_protected_art":"EXACT_UNCHANGED",
 "other_open_defects":["stage_SOURCE_STYLE_REWORK","outrun_miles_gold_BEVEL_SLANT_REWORK"],
 "producer_visual":"PARTIAL_PASS_WHITE_ONLY_NOT_FULL_ASSET",
 "production_dds_changed":True,"new_production_candidate_dds":1,
 "C":"NEW_C2_REQUIRED_AFTER_STAGE_GOLD_REPAIR",
 "C3":"BLOCKED","EVIDENCE_APPROVAL":False,
 "USER_IN_GAME":"OPEN_USER_INGAME_FAIL",
 "RUNTIME_VALIDATION":"UNTESTED",
 "execution_backend":"GITHUB_ACTIONS_COMPUTE",
 "exclusions":["VR","FFB","DX11","DXVK"],
 "visual_proof_dir":"localization/graphics/role_B/20261009-B295-Q060-P0-SOURCE-CLEAN-GLYPH-PLATE"}
(out/"B296_PRODUCER_SELF_QA_PARTIAL.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"index":60,"candidate":newsha,"outside":outside,"changed":int(changed.sum()),"result":"PARTIAL_WHITE_PASS_STAGE_GOLD_REWORK"},ensure_ascii=False))

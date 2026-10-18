#!/usr/bin/env python3
"""Final bookkeeping for source-English second-stage C QA, no game approval."""
import csv,hashlib,json
from pathlib import Path
from collections import Counter
B=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
Q=B/'qa_review_20261018'
allitems=json.loads((Q/'visual_triage_76.json').read_text(encoding='utf-8'))
q057={(r['source_png'],r['english']) for r in allitems if r['source_png'].startswith('Q057_') and r['english'] in {'SPECIAL REQUEST','Target','Technical Bonus'}}
assert len(q057)==15
r12=json.loads((Q/'REWORK_12_SUMMARY.json').read_text(encoding='utf-8'))
r15=json.loads((Q/'REWORK_FOLLOWUP_15_SUMMARY.json').read_text(encoding='utf-8'))
idx12={x['index'] for x in r12['details']}
idx15={x['visual_index'] for x in r15['items']}
assert len(idx12)==12 and len(idx15)==15 and not(idx12&idx15)
fixed={r['visual_sheet_index'] for r in allitems if (r['source_png'],r['english']) in q057}|idx12|idx15
assert len(fixed)==42
rework=[r for r in allitems if r['visual_triage'].startswith('REWORK_')]
remaining=[r for r in rework if r['visual_sheet_index'] not in fixed]
assert len(rework)==46 and len(remaining)==4,[(x['visual_sheet_index'],x['english']) for x in remaining]
def sha(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):d.update(b)
 return d.hexdigest()
all_crops=[]
for root in (Q/'reworked_q057_test_only',Q/'reworked_12_test_only',Q/'reworked_15_followup_test_only'):
 for p in root.rglob('english_native_rework_candidate.png'):
  j=json.loads((p.parent/'rework_manifest.json').read_text(encoding='utf-8'))
  expected=j.get('new_crop_sha256') or j.get('crop_sha256') or j.get('output_sha256')
  assert expected==sha(p),(p,'HASH_MISMATCH')
  all_crops.append(str(p))
assert len(all_crops)==42
count=Counter(r['visual_triage'] for r in allitems)
assert count['VISUAL_LEGIBLE_CANDIDATE_QA_REQUIRED']==10
assert count['PLATE_UNDERLINE_REVIEW_REQUIRED']==20
assert count['REWORK_NEIGHBOR_ART_INCLUDED']==39
assert count['REWORK_CLIPPED_OR_LABEL_MISMATCH']==7
report={
 'status':'ORIGINAL_HD_C_CROP_2ND_STAGE_REVIEW_COMPLETE',
 'original_sources_sha_verified':108,'original_crops':242,'original_crop_sha_source_pixel_pass':242,
 'edge_review_count':76,'visual_categories':dict(count),
 'initial_rework_count':46,'candidate_rework_count':42,'remaining_rework_count':4,
 'candidate_sha_pass':42,'candidate_source_byte_equality_pass':42,
 'existing_outputs_mutated':False,'original_master_255_mutated':False,
 'A_B':'UNCHANGED','C1_C3':'NOT_APPROVED','GAME_RUNTIME':'UNTESTED',
 'CROP_TEST_ONLY':'YES',
 'still_need_review':['original plate/underline separation','manual approval of 42 rework candidates','4 unresolvable by simple crop']
}
(Q/'STAGE_COMPLETE_20261018.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
(Q/'rework_remaining_4.json').write_text(json.dumps({
 'status':'MANUAL_MASK_OR_REVIEW_NEEDED_NOT_AUTO_DISPATCHED','count':4,
 'items':[{'visual_sheet_index':v['visual_sheet_index'],'english':v['english'],
           'source_png':v['source_png'],'bbox_xyxy':v['original_box'],
           'reason':v['visual_triage_reason']} for v in remaining]},indent=2,ensure_ascii=False)+'\n')
with (Q/'triage_for_github_76.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['index','source_png','english','visual_category','reason','native_bbox','rework_candidate','game_approved'])
 for r in allitems:
  num=r['visual_sheet_index']
  if num in fixed:
   stage='TEST_ONLY_REWORK_CANDIDATE_SHA_VERIFIED'
  elif r['visual_triage'].startswith('REWORK_'):
   stage='UNRESOLVED_REWORK'
  else:
   stage='VISUAL_REVIEW_PENDING'
  w.writerow([num,r['source_png'],r['english'],r['visual_triage'],r['visual_triage_reason'],r['original_box'],stage,'NO'])
md=f"""# OutRun 2006 C GitOps — native HD English crop QA and source-only rework
Date: 2026-10-18 KST. **Do not treat any QA result below as a released Korean DDS.**

## Verified inputs and technical QA
- Native, unsplit source HD PNG: 108 originals across 5 SHA-pinned ZIPs; all 108 source-record scans finished.
- Existing original-native crop files: **242**. All crop SHA256, source SHA256, dimensions and original-region RGBA equality **242/242 PASS**.
- The original 242, 255 historic master, 108 full-source images, active C queue, A/B/C1/C3 state are **untouched**.
- Visual QA on 76 edge-flagged crops, with six N100 contact sheets; 10 legible candidates, 20 plate/underline-review cases, **39 obvious neighboring-art cases and 7 punctuation/truncation risk cases**.
- Thus 46/76 originally needed native rework; text completeness for index 041 is correct (contact sheet displayed only shortened label); corrected in the recorded triage.

## Performed: 42 non-destructive native rework candidates
1. Q057 five platforms x [SPECIAL REQUEST, Target, Technical Bonus]: **15** outputs. Preview `Q057_REWORK_15_CANDIDATES.jpg`.
2. Additional punctuation, stray graphics and UI-neighbor fixes: **12** outputs. Preview `MORE_REWORK_PROTOTYPES.jpg`.
3. More native crop bboxes from original atlas (Ranking, Sector4, FRIEND REQUEST, Rival, Start, Goal, INTERMEDIATE B, SELECT LICENSE, COMPLETE, DRIVE TIME, VS RANK, WIN RATIO, GIANT STATUES, SETUP): **15** outputs. Previews `FINAL_REWORK_PROTOTYPE_01.jpg` and `_02.jpg`.
- **42/42** original SHA and saved output SHA verified; every output copied from the exact native original RGBA bbox, no generated pixels, source modification, rescaling, or alpha redraw.
- Stored on N100 in `qa_review_20261018/reworked_q057_test_only/`, `reworked_12_test_only/`, `reworked_15_followup_test_only/`.
- Every output is **CROP_TEST_ONLY_VISUAL_QA_REQUIRED**, not automatic C1/C3/game PASS.

## Four still unresolved by rectangular native crop alone
"""
for r in remaining:
 md+=f"- QA #{r['visual_sheet_index']:03d}: **{r['english']}** ({r['source_png']}) — {r['visual_triage_reason']}.\n"
md+="""

Those cases need manual glyph isolation or carefully protected sprite/art separation.
Do not release or replace existing PNG/DDS while full visual QA or game proof is absent.

## Artifacts and handoff
N100 base: `/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/qa_review_20261018/`.
- `STAGE_COMPLETE_20261018.json` — deterministic final source/crop counts.
- `triage_for_github_76.csv` — every visual judgment and rework candidate state.
- `rework_remaining_4.json` — remaining highest-risk crops.
- `EDGE_REVIEW_CONTACT_01_of_06.jpg` through `06_of_06.jpg` — original crop/source context comparisons.
- `Q057_REWORK_15_CANDIDATES.jpg`, `MORE_REWORK_PROTOTYPES.jpg`,
  `FINAL_REWORK_PROTOTYPE_01.jpg`, `FINAL_REWORK_PROTOTYPE_02.jpg`.

**Next gate:** Native-size detailed QA for 42 candidates plus 10 text-legible and 20 text/plate candidates; isolate four unresolved title/UI sprites; never assume runtime game pass.
"""
(Q/'QA_REPORT_20261018.md').write_text(md,encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
#!/usr/bin/env python3
"""Review bookkeeping for 27 produced native pixel-exact original-HD repair candidates."""
from pathlib import Path
import csv,json,hashlib,collections
from PIL import Image
B=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
Q=B/'qa_review_20261018'
triage=json.loads((Q/'visual_triage_76.json').read_text(encoding='utf-8'))
fixed15={(v['source_png'],v['english']) for v in triage
 if v['source_png'].startswith('Q057_') and v['english'] in {'SPECIAL REQUEST','Target','Technical Bonus'}}
fixed12={2,5,6,16,37,38,39,42,44,45,47,58}
assert len(fixed15)==15 and len(fixed12)==12
done=[v for v in triage if (v['source_png'],v['english']) in fixed15 or v['visual_sheet_index'] in fixed12]
assert len(done)==27 and len({v['visual_sheet_index'] for v in done})==27
remaining=[v for v in triage if v['visual_triage'].startswith('REWORK_') and v not in done]
assert len(remaining)==20
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
crops=[]
for root in (Q/'reworked_q057_test_only',Q/'reworked_12_test_only'):
 for p in root.rglob('english_native_rework_candidate.png'):
  m=p.parent/'rework_manifest.json'
  data=json.loads(m.read_text())
  hashpin=data.get('new_crop_sha256',data.get('crop_sha256'))
  assert digest(p)==hashpin,(p,'SHA_FAILED')
  crops.append(p)
assert len(crops)==27
report={'status':'C_SECOND_STAGE_QA_27_REWORK_CANDIDATES_COMPLETE','original_crops':242,
 'original_pixel_qa_pass':242,'original_edge_candidates':76,
 'visual_legible_candidates':9,'plate_underline_review':20,
 'rework_total':47,'rework_candidates_prepared':27,'remaining_rework':20,
 'rework_candidate_sha_pass':len(crops),
 'original_108_source_scan_completed':True,
 'original_sources_mutated':False,'C1_C3':'NOT_APPROVED',
 'game_runtime':'UNTESTED','A_B':'UNTOUCHED'}
(Q/'STAGE2_FINAL_STATUS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(Q/'rework_remaining_20.json').write_text(json.dumps({
 'status':'REWORK_OUTSTANDING_MANUAL_NATIVE_CROP_REQUIRED','count':20,
 'items':[{k:v[k] for k in ['visual_sheet_index','source_png','english','original_box','visual_triage','visual_triage_reason']} for v in remaining]},indent=2,ensure_ascii=False)+'\n')
with (Q/'triage_for_github_76.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f)
 w.writerow(['index','source_png','english','category','visual_reason','bbox_xyxy','rework_test_candidate','final_user_approval'])
 for r in triage:
  new=('Q057_15_TEST_ONLY' if (r['source_png'],r['english']) in fixed15
       else 'ADDITIONAL_12_TEST_ONLY' if r['visual_sheet_index'] in fixed12 else 'NO')
  w.writerow([r['visual_sheet_index'],r['source_png'],r['english'],
              r['visual_triage'],r['visual_triage_reason'],r['original_box'],new,'NOT_GRANTED'])
md=Q/'QA_REPORT_20261018.md'
s=md.read_text(encoding='utf-8')
if '## Additional 12 rework candidates' not in s:
 s+="""

## Additional 12 rework candidates, source-only
- Individually visually compared native crop versus narrowed/expanded original-HD region.
- 12 exact pixel crops stored in N100 `qa_review_20261018/reworked_12_test_only/`.
- Fixed IDs from six-sheet visual triage: 002, 005, 006, 016, 037, 038, 039, 042, 044, 045, 047, 058.
- Restored punctuation, removed neighboring UI fragments when isolation is possible.
- Native RGBA byte equality and original source SHA **12/12 PASS**, output SHA **12/12 PASS**.
- Comparison `qa_review_20261018/MORE_REWORK_PROTOTYPES.jpg`.
- Aggregate Q057 15 + additional 12 = **27 unapproved rework candidates**, **20 still require rework**.
- All 242 previous original crops and 255 legacy baseline remain immutable; zero DDS/image generation.
- Neither visual candidate nor technical crop proof is an in-game PASS.
"""
md.write_text(s,encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
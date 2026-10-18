#!/usr/bin/env python3
"""Package C-only TEST artifacts for next team; never overwrite source or game data."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,hashlib
Q=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/qa_review_20261018')
out=Q/'C_NATIVE_HD_EN_REWORK_44_TEST_ONLY_20261019.zip'
roots=['reworked_q057_test_only','reworked_12_test_only','reworked_15_followup_test_only','reworked_last4_20261019_test_only']
files=[]
for n in roots:
 d=Q/n
 for p in d.rglob('*'):
  if p.is_file():files.append(p)
cropped=[p for p in files if p.name=='english_native_rework_candidate.png']
assert len(cropped)==44,len(cropped)
docs=['FINAL_LAST4_20261019_QA.json','LAST4_20261019_SUMMARY.json','REWORK_REMAINING_2_20261019.json',
      'LAST4_C_NATIVE_QA_REPORT_20261019.md',
      'STAGE_COMPLETE_20261018.json','visual_triage_76.csv','triage_for_github_76.csv',
      'EDGE_REVIEW_CONTACT_01_of_06.jpg','EDGE_REVIEW_CONTACT_02_of_06.jpg',
      'EDGE_REVIEW_CONTACT_03_of_06.jpg','EDGE_REVIEW_CONTACT_04_of_06.jpg',
      'EDGE_REVIEW_CONTACT_05_of_06.jpg','EDGE_REVIEW_CONTACT_06_of_06.jpg',
      'Q057_REWORK_15_CANDIDATES.jpg','MORE_REWORK_PROTOTYPES.jpg',
      'FINAL_REWORK_PROTOTYPE_01.jpg','FINAL_REWORK_PROTOTYPE_02.jpg',
      'LAST4_VISUAL_PROTOTYPE_012.jpg','LAST4_VISUAL_PROTOTYPE_036.jpg',
      'LAST4_VISUAL_PROTOTYPE_049.jpg','LAST4_VISUAL_PROTOTYPE_059.jpg']
for n in docs:
 p=Q/n
 if p.exists():files.append(p)
readme='''OutRun 2006 Korean Localization — C Slot Native Original English Crops

THIS ZIP IS TEST ONLY. Contains 44 rewritten native bboxes with PNG raw original
RGBA pixels unchanged, manifests and visual QA sheets. 46 visual rework needs:
44 candidate source crops, 2 HOLD (HARD/Q062 and CONIFEROUS FOREST/Q201).
NOT an approved game or DDS release. No alpha mask, background removal,
pixel retouching, resizing, ImageGen, translation or asset replacement.
See LAST4_C_NATIVE_QA_REPORT_20261019.md.
'''
with ZipFile(out,'w',compression=ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
 z.writestr('README_FIRST.txt',readme)
 seen=set()
 for p in sorted(files):
  arc=p.relative_to(Q).as_posix()
  assert arc not in seen
  seen.add(arc)
  z.write(p,arc)
with ZipFile(out) as z:
 assert z.testzip() is None,'ZIP_CRC_FAIL'
 assert len([x for x in z.namelist() if x.endswith('/english_native_rework_candidate.png')])==44
def hashfile(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
receipt={'status':'ARCHIVE_TEST_ONLY_VERIFIED','filename':out.name,'bytes':out.stat().st_size,
         'sha256':hashfile(out),'cropped_native_candidates':44,
         'source_HD_png_pinned':108,'original_hd_crops_retained':242,
         'remaining_holds':2,'all_original_and_DDS_mutated':False,
         'game_validation':'UNTESTED'}
(Q/'C_NATIVE_HD_EN_REWORK_44_PACKAGE_RECEIPT_20261019.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
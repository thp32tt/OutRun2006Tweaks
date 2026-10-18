#!/usr/bin/env python3
"""Non-destructive 46-item native-English C-slot QA package.
Provenance pin is essential: 45 byte-identical original source crops,
one Photoshop raster-layer extraction which is not source-pixel identical.
"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from PIL import Image
import csv,hashlib,json,io
Q=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/qa_review_20261018')
BASE=Q.parent
roots=['reworked_q057_test_only','reworked_12_test_only',
       'reworked_15_followup_test_only','reworked_last4_20261019_test_only',
       'reworked_final2_test_only_20261019']
files=[]
for name in roots:
 d=Q/name
 assert d.is_dir(),('MISSING_CROP_DIR',name)
 files.extend(p for p in d.rglob('*') if p.is_file())
cropfiles=[p for p in files if p.suffix.lower()=='.png' and (
    p.name.endswith('candidate.png'))]
assert len(cropfiles)==46,('CROP_COUNT',len(cropfiles))
native=[p for p in cropfiles if p.name!='english_psd_layer_test_candidate.png']
psd=[p for p in cropfiles if p.name=='english_psd_layer_test_candidate.png']
assert len(native)==45 and len(psd)==1
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
checks=[]
for p in sorted(cropfiles):
 m=p.parent/'rework_manifest.json'
 if not m.exists():m=p.parent/'manifest.json'
 assert m.is_file(),('MISSING_CROP_MANIFEST',p)
 spec=json.loads(m.read_text())
 checkshas=[spec.get(k) for k in ('output_sha256','crop_sha256','new_crop_sha256','candidate_sha256',
                               'destination_sha256') if spec.get(k)]
 assert len(checkshas)==1 and checkshas[0]==sha(p),('WRONG_SHA',p,checkshas)
 with Image.open(p) as im:
  assert im.format=='PNG' and im.mode=='RGBA'
  size=list(im.size)
 checks.append({'id':p.relative_to(Q).as_posix(),'sha256':sha(p),
                'size':size,'provenance':'PSD_RASTERIZED_LAYER_NOT_NATIVE_PIXEL_EQUAL' if p in psd
                else 'EXACT_NATIVE_SOURCE_PIXELS','status':'TEST_ONLY_NOT_RELEASED'})
# Evidence docs and previews
docs=['FINAL_2_LAYER_EXTRACTION_20261019.json','FINAL2_SOURCE_VS_EXTRACTED_20261019.jpg',
      'FINAL_LAST4_20261019_QA.json','LAST4_C_NATIVE_QA_REPORT_20261019.md',
      'QA_REPORT_20261018.md','STAGE_COMPLETE_20261018.json',
      'LAST4_20261019_SUMMARY.json','REWORK_REMAINING_2_20261019.json',
      'LAST4_VISUAL_PROTOTYPE_012.jpg','LAST4_VISUAL_PROTOTYPE_036.jpg',
      'LAST4_VISUAL_PROTOTYPE_049.jpg','LAST4_VISUAL_PROTOTYPE_059.jpg',
      'EDGE_REVIEW_CONTACT_01_of_06.jpg','EDGE_REVIEW_CONTACT_02_of_06.jpg',
      'EDGE_REVIEW_CONTACT_03_of_06.jpg','EDGE_REVIEW_CONTACT_04_of_06.jpg',
      'EDGE_REVIEW_CONTACT_05_of_06.jpg','EDGE_REVIEW_CONTACT_06_of_06.jpg',
      'Q057_REWORK_15_CANDIDATES.jpg','MORE_REWORK_PROTOTYPES.jpg',
      'FINAL_REWORK_PROTOTYPE_01.jpg','FINAL_REWORK_PROTOTYPE_02.jpg',
      'triage_for_github_76.csv']
for n in docs:
 p=Q/n
 if p.is_file():files.append(p)
# Source attribution only, not distributing original PSD by default.
for n in ['hard_psd_upstream_receipt.json','hard_layer_index.json',
          'psd_tools_hard_layer_map.json']:
 p=Q/'upstream_psd_evidence'/n
 if p.is_file():files.append(p)
# QA manifest csv and README
index=Q/'C_NATIVE_ENGLISH_46_PROVENANCE_INDEX.csv'
with index.open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=['id','sha256','size','provenance','status'])
 w.writeheader()
 for row in checks:w.writerow({**row,'size':str(row['size'])})
files.append(index)
readme='''OutRun 2006 — N100 C GitOps original HD English crop, 46 review-only candidates
Status: TEST_ONLY, NOT game-validated, NOT composed into DDS, NOT approved Korean translation.

45 crops are byte-for-byte native source PNG regions; original atlas verified by
SHA against the 108-original-source full-HD manifest.
1 crop, HARD, is isolated from separate rasterized PSD layer in
Sonic-TV/OR2006Sprites commit 3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6,
PSD blob sha1 e22ed4d6b9f7d8464fc40d724dd0b1d37e306104.
It is NOT pixel-identical to the original flat source PNG.
CONIFEROUS FOREST was isolated at the empty-alpha gap before STAGES
with its original RGBA bytes unmodified.
Outputs have their manifest plus complete QA provenance. All previous crops
and original sources remain unchanged. No VR/FFB/DX11/DXVK work.
'''
zipfile=Q/'OUTRUN_C_NATIVE_ENGLISH_46_TEST_ONLY_20261019.zip'
with ZipFile(zipfile,'w',compression=ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
 z.writestr('README_FIRST.txt',readme)
 seen=set()
 for p in sorted(set(files)):
  name=p.relative_to(Q).as_posix()
  assert name not in seen
  seen.add(name)
  z.write(p,name)
with ZipFile(zipfile) as z:
 assert z.testzip() is None
 assert len([x for x in z.namelist() if x.endswith('candidate.png')])==46
assert len(list((BASE/'hd108_outputs').rglob('english_original_native_crop.png')))==242
receipt={
 'status':'46_NATIVE_ENGLISH_CANDIDATES_PACKAGED_TEST_ONLY',
 'file':str(zipfile),'bytes':zipfile.stat().st_size,
 'sha256':sha(zipfile),
 'candidate_count':46,
 'source_pixel_exact_count':45,
 'upstream_PSD_layer_count_not_source_pixel_exact':1,
 'C_original_crop_retained':242,
 'legacy_master_255_retained':True,
 'original_assets_108_retained':True,
 'DDS_or_game_replacements':False,
 'A_B_unchanged':True,
 'game_acceptance':'UNTESTED',
 'semantic_and_visual_signoff':'PENDING'}
(Q/'FINAL_46_PACKAGE_RECEIPT_20261019.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
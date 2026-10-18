#!/usr/bin/env python3
"""Non-destructive 12 native-HD OCR crop coordinate repairs after visual comparison.
C GitOps pipeline QA output only; never writes live DDS, A/B, queue, old 242.
"""
from pathlib import Path
from PIL import Image
import csv,hashlib,io,json,zipfile
BASE=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
QA=BASE/'qa_review_20261018'
SRC=BASE/'hd_original_108_verified'
TGT=QA/'reworked_12_test_only'
TGT.mkdir(exist_ok=True)
edge=json.loads((QA/'visual_triage_76.json').read_text(encoding='utf-8'))
FIXED={
 2:[508,1408,716,1489],
 5:[246,461,415,521],
 6:[1486,461,1655,521],
 16:[2000,857,2547,994],
 37:[3448,1033,3916,1100],
 38:[1223,65,1583,149],
 39:[3429,859,3835,940],
 42:[1127,207,1811,310],
 44:[3473,379,3757,449],
 45:[2205,1380,2954,1491],
 47:[1740,36,1980,93],
 58:[383,566,1081,677]
}
with zipfile.ZipFile(BASE/'hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip') as z:
 rows=list(csv.DictReader(io.StringIO(z.read('01_DDS_PNG_MANIFEST_108.csv').decode('utf-8-sig'))))
pins={r['png_filename']:r for r in rows}
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for part in iter(lambda:f.read(1048576),b''):h.update(part)
 return h.hexdigest()
records=[]
for n,bb in FIXED.items():
 r=edge[n-1];name=r['source_png']
 spec=pins[name];src=SRC/name
 assert digest(src)==spec['png_sha256'],('ORIGINAL_SOURCE_SHA_FAIL',name)
 with Image.open(src) as im:
  assert im.format=='PNG' and im.mode=='RGBA'
  assert 0<=bb[0]<bb[2]<=im.width and 0<=bb[1]<bb[3]<=im.height
  crop=im.crop(bb)
 out=TGT/('%03d'%n)/'english_native_rework_candidate.png'
 out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():
  with Image.open(out) as old:
   assert old.mode=='RGBA' and old.size==crop.size and old.tobytes()==crop.tobytes()
 else:crop.save(out)
 with Image.open(out) as check:
  assert check.mode=='RGBA' and check.size==crop.size and check.tobytes()==crop.tobytes()
 manifest={'status':'CROP_TEST_ONLY_VISUAL_QA_REQUIRED',
  'visual_index':n,'source_png':name,'source_sha256':spec['png_sha256'],
  'english':r['english'],'original_bbox':r['original_box'],'updated_bbox':bb,
  'crop_dimensions':list(crop.size),'crop_sha256':digest(out),
  'preview_sheet':'MORE_REWORK_PROTOTYPES.jpg','visual_triage':'CANDIDATE_REPAIRED_BBOX',
  'source_region_exact_pixels':True,'operator_final_approval':'NOT_GRANTED',
  'source_alteration':False,'A_B':'UNTOUCHED','DDS':'NOT_WRITTEN','game':'UNTESTED'}
 (out.parent/'rework_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 records.append({'index':n,'english':r['english'],'source_png':name,'path':str(out),
                 'updated_bbox':bb,'sha256':manifest['crop_sha256']})
summary={'status':'REWORK_12_NATIVE_TEST_ONLY_READY','rework_candidates':len(records),
         'source_sha_pass':len(records),'pixel_identical_to_source':len(records),
         'original_unmodified':True,'docs':['MORE_REWORK_PROTOTYPES.jpg'],
         'game':'UNTESTED','details':records}
(QA/'REWORK_12_SUMMARY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='details'},ensure_ascii=False))
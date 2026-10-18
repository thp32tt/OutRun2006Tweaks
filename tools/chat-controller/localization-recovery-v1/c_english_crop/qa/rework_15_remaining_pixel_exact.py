#!/usr/bin/env python3
"""15 additional visually compared Q-asset native original English crops.
Save test-only alternatives without overwriting any previous crop or game DDS.
"""
import csv,hashlib,io,json,zipfile
from pathlib import Path
from PIL import Image
B=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
QA=B/'qa_review_20261018'
SRC=B/'hd_original_108_verified'
OUT=QA/'reworked_15_followup_test_only'
OUT.mkdir(parents=True,exist_ok=True)
TRIAGE=json.loads((QA/'visual_triage_76.json').read_text())
FIXES={
 1:[260,186,574,269],
 4:[203,336,379,396],
 10:[635,1002,1380,1091],
 15:[2328,539,2470,601],
 17:[1324,731,1460,778],
 18:[1412,300,1535,346],
 19:[788,301,921,347],
 46:[801,109,1402,187],
 52:[587,565,1526,660],
 53:[399,1551,694,1618],
 54:[402,1824,723,1889],
 55:[399,1642,640,1709],
 56:[400,1732,692,1799],
 60:[179,1678,1066,1801],
 74:[967,501,1201,584],
}
with zipfile.ZipFile(B/'hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip') as z:
 rows=list(csv.DictReader(io.StringIO(z.read('01_DDS_PNG_MANIFEST_108.csv').decode('utf-8-sig'))))
SPECS={x['png_filename']:x for x in rows}
def sha(f):
 h=hashlib.sha256()
 with f.open('rb') as fd:
  for chunk in iter(lambda:fd.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
results=[]
for num,box in FIXES.items():
 r=TRIAGE[num-1]
 assert r['visual_sheet_index']==num
 name=r['source_png']
 spec=SPECS[name];src=SRC/name
 assert src.is_file() and not src.is_symlink()
 originalhash=sha(src)
 assert originalhash==spec['png_sha256']
 with Image.open(src) as im:
  assert im.format=='PNG' and im.mode=='RGBA'
  assert 0<=box[0]<box[2]<=im.width and 0<=box[1]<box[3]<=im.height
  sourcecrop=im.crop(box)
 target=OUT/('%03d'%num)/'english_native_rework_candidate.png'
 target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists():sourcecrop.save(target)
 with Image.open(target) as verify:
  assert verify.format=='PNG' and verify.mode=='RGBA'
  assert verify.size==sourcecrop.size
  assert verify.tobytes()==sourcecrop.tobytes()
 data={
 'status':'CROP_TEST_ONLY_VISUAL_QA_REQUIRED',
 'source_png':name,'source_sha256':originalhash,
 'english':r['english'],'visual_triage_index':num,
 'old_bbox_xyxy':r['original_box'],'native_rework_bbox_xyxy':box,
 'output_dimensions':list(sourcecrop.size),
 'output_sha256':sha(target),
 'pixel_identical_to_source_native_region':True,
 'previous_original_crop_not_changed':True,
 'source_dds_path_reference_only':spec['source_dds_path'],
 'human_quality_signoff':'NOT_GRANTED',
 'game_runtime_validation':'UNTESTED','A_B':'UNTOUCHED',
 'original_986_tiles':'NOT_USED','dds_compose':'NOT_RUN'}
 (target.parent/'rework_manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 results.append({'visual_index':num,'english':r['english'],
                 'source_png':name,'output':str(target),'sha256':data['output_sha256']})
summary={'status':'FOLLOWUP_15_REWORK_TEST_ONLY_VERIFIED',
         'outputs':15,'source_sha_pass':15,'pixel_roundtrip_pass':15,
         'candidate_pixels_differ_from_original_source':False,
         'original_crops_immutable':True,'validation':'VISUAL_CANDIDATE_NOT_GAME_PASS',
         'preview_pages':['FINAL_REWORK_PROTOTYPE_01.jpg','FINAL_REWORK_PROTOTYPE_02.jpg'],
         'items':results}
(QA/'REWORK_FOLLOWUP_15_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='items'},ensure_ascii=False))
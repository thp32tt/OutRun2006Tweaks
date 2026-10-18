#!/usr/bin/env python3
"""C-only source-faithful rework for the last four original-HD ROI problems.

Only two rectangles are safely separable from original native-HD pixels;
other two are explicit HOLD. No masking, alpha editing, clean plate, DDS
composition, generation, source change, queue writes or automatic approval.
"""
from pathlib import Path
from PIL import Image
import csv
import hashlib
import io
import json
import zipfile

BASE=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
QA=BASE/'qa_review_20261018'
INPUT=BASE/'hd_original_108_verified'
OUT=QA/'reworked_last4_20261019_test_only'
OUT.mkdir(parents=True,exist_ok=True)
REMAIN=json.loads((QA/'rework_remaining_4.json').read_text(encoding='utf-8'))['items']
assert sorted(r['visual_sheet_index'] for r in REMAIN)==[12,36,49,59]
with zipfile.ZipFile(BASE/'hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip') as z:
 rows=list(csv.DictReader(io.StringIO(z.read('01_DDS_PNG_MANIFEST_108.csv').decode('utf-8-sig'))))
pinned={r['png_filename']:r for r in rows}
assert len(pinned)==108
def sha(p):
 digest=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):
   digest.update(chunk)
 return digest.hexdigest()
# Boxes verified against native source plus comparative visual contact sheet.
# Q051 shows a punctuation visual ambiguity (two dots/colon-like versus official !).
# Keep official transcription reference but do NOT assert punctuation QA PASS.
CROPS={
 12: {'bbox':[3145,870,3604,977],
      'visual_reason':'Excludes adjacent black vertical separator while retaining full word and visible punctuation',
      'semantic_warning':'Source punctuation visually resembles colon; official transcription is Leader!; reviewer must resolve before translation.'},
 49: {'bbox':[1955,548,3520,674],
      'visual_reason':'Isolates full red SELECT LICENSE glyphs while removing top duplicated row and bottom striped UI',
      'semantic_warning':None}
}
HOLDS={
 36: {'reason':'HARD text outline touches white-green background plate and left gray border. Tight rectangle would cut top glyph/outline. Native source pixel-only separation cannot remove attached art.',
      'alternative':'Keep original atlas crop as evidence; require separately approved PSD/native-layer extraction or explicit alpha edit scope.'},
 59: {'reason':'CONIFEROUS FOREST final T meets next STAGES sprite within same native bbox; right cropping cuts final glyph.',
      'alternative':'Q147 has another instance of same phrase but is a different source atlas/style, so cannot substitute it for Q201 without cross-style QA. Require sprite-layer separation or original PSD.'}
}
results=[]
for record in REMAIN:
 ix=record['visual_sheet_index']
 name=record['source_png']
 assert name in pinned
 spec=pinned[name]
 src=INPUT/name
 assert src.is_file() and not src.is_symlink()
 assert sha(src)==spec['png_sha256'],(name,'SOURCE_SHA_MISMATCH')
 with Image.open(src) as im:
  assert im.format=='PNG' and im.mode=='RGBA'
  assert im.size==(int(spec['width']),int(spec['height']))
  if ix in CROPS:
   obj=CROPS[ix]
   x0,y0,x1,y1=obj['bbox']
   assert 0<=x0<x1<=im.width and 0<=y0<y1<=im.height
   cut=im.crop((x0,y0,x1,y1))
   directory=OUT/('%03d'%ix)
   directory.mkdir(parents=True,exist_ok=True)
   dest=directory/'english_native_rework_candidate.png'
   if dest.exists():
    with Image.open(dest) as old:
     assert old.mode=='RGBA' and old.size==cut.size and old.tobytes()==cut.tobytes(),'NONIDEMPOTENT_EXISTING_CROP'
   else:cut.save(dest,'PNG')
   with Image.open(dest) as audit:
    assert audit.mode=='RGBA' and audit.size==cut.size
    assert audit.tobytes()==cut.tobytes(),'NATIVE_SOURCE_PIXEL_DIFF'
   result={
    'index':ix,'status':'CROP_TEST_ONLY_VISUAL_QA_REQUIRED',
    'source_png':name,'source_png_sha256':spec['png_sha256'],
    'dds_reference_path':spec['source_dds_path'],
    'dds_sha256_REFERENCE_NOT_PIXEL_VERIFIED':spec['dds_sha256'],
    'english_official_reference':record['english'],
    'original_bbox_xyxy':record['bbox_xyxy'],'revised_bbox_xyxy':obj['bbox'],
    'crop_size':[cut.width,cut.height],
    'candidate_path':str(dest),'candidate_sha256':sha(dest),
    'visual_reason':obj['visual_reason'],
    'semantic_warning':obj['semantic_warning'],
    'native_rgba_pixel_identical':True,'imagegen':'NOT_USED',
    'original_file_unchanged':True,'A_B':'UNTOUCHED',
    'game_runtime':'UNTESTED','manual_qa':'NOT_GRANTED'}
   (directory/'rework_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  else:
   assert ix in HOLDS
   obj=HOLDS[ix]
   result={
    'index':ix,'status':'HOLD_NOT_SEPARABLE_BY_NATIVE_RECTANGULAR_CROP',
    'english_official_reference':record['english'],'source_png':name,
    'source_png_sha256':spec['png_sha256'],
    'original_bbox_xyxy':record['bbox_xyxy'],
    'reason':obj['reason'],'safe_next_action':obj['alternative'],
    'any_output_generated':False,'game_runtime':'UNTESTED'}
  results.append(result)
assert len(results)==4 and sum('candidate_path' in r for r in results)==2
summary={
 'status':'C_NATIVE_LAST4_REWORK_EXECUTED_TEST_ONLY',
 'source_count':4,'source_sha_pass':4,'new_native_pixel_candidates':2,
 'new_pixel_validation_pass':2,'holds_nonrectangular':2,
 'already_prepared_rework_candidates':42,
 'total_rework_candidates_now':44,
 'initial_visual_rework_count':46,
 'remaining_hold_count':2,
 'original_crops_modified':False,'old_master_255_modified':False,
 'A_B_changed':False,'C1_C3_GAME':'UNTESTED',
 'items':results}
(QA/'LAST4_20261019_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(QA/'REWORK_REMAINING_2_20261019.json').write_text(json.dumps({
 'status':'HOLD_MANUAL_LAYER_SEPARATION_REQUIRED','count':2,
 'items':[r for r in results if r['status'].startswith('HOLD_')]
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='items'},ensure_ascii=False))
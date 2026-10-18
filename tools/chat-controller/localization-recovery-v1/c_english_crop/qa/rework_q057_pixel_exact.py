#!/usr/bin/env python3
"""15 non-destructive native Q057 English crop rework candidates.
Five platform originals x 3 validated visual-reviewed bboxes.
Outputs TEST_ONLY, not C1/C3/in-game accepted.
"""
import csv, hashlib, io, json, zipfile, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops
BASE=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
OUT=BASE/'qa_review_20261018/reworked_q057_test_only'
OUT.mkdir(parents=True,exist_ok=True)
SOURCES=BASE/'hd_original_108_verified'
with zipfile.ZipFile(BASE/'hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip') as z:
 manifest=list(csv.DictReader(io.StringIO(z.read('01_DDS_PNG_MANIFEST_108.csv').decode('utf-8-sig'))))
SPEC={r['png_filename']:r for r in manifest}
# Match only the 3 example English phrases previously visually inspected
BOXES={
 'SPECIAL REQUEST':[2210,377,3215,485],
 'Target':[2631,541,2810,598],
 'Technical Bonus':[2400,118,3630,267],
}
original=json.loads((BASE/'qa_review_20261018/visual_triage_76.json').read_text())
review=[r for r in original if r['source_png'].startswith('Q057_') and r['english'] in BOXES]
assert len(review)==15 and len(set(r['source_png'] for r in review))==5
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
results=[]
for rec in sorted(review,key=lambda x:(x['source_png'],x['english'])):
 name=rec['source_png']
 original_src=SOURCES/name
 assert original_src.exists() and not original_src.is_symlink()
 spec=SPEC[name]
 original_sha=sha(original_src)
 assert original_sha==spec['png_sha256']
 with Image.open(original_src) as im:
  assert im.format=='PNG' and im.mode=='RGBA'
  b=BOXES[rec['english']]
  assert 0<=b[0]<b[2]<=im.width and 0<=b[1]<b[3]<=im.height
  original_rgba=im.copy()
  cut=original_rgba.crop(tuple(b))
 slug={'SPECIAL REQUEST':'special-request','Target':'target','Technical Bonus':'technical-bonus'}[rec['english']]
 folder=OUT/Path(name).stem/slug
 folder.mkdir(parents=True,exist_ok=True)
 png=folder/'english_native_rework_candidate.png'
 if png.exists():
  with Image.open(png) as prev:
   assert prev.mode=='RGBA' and prev.size==cut.size and prev.tobytes()==cut.tobytes()
 else:cut.save(png,format='PNG')
 with Image.open(png) as cmp:
  assert cmp.mode=='RGBA' and cmp.size==cut.size and cmp.tobytes()==cut.tobytes()
 artifact={
  'status':'CROP_TEST_ONLY_VISUAL_QA_REQUIRED',
  'source_png':name,'source_sha256':original_sha,
  'source_dds_path':spec['source_dds_path'],'source_dds_sha256_reference_only':spec['dds_sha256'],
  'english':rec['english'],'old_bbox_xyxy':rec['original_box'],'new_bbox_xyxy':b,
  'new_dimensions':list(cut.size),'new_crop_sha256':sha(png),
  'visual_inspection':'VISUAL_PROTOTYPE_REDUCES_NEIGHBOR_ART',
  'manual_final_approval':'NOT_GRANTED',
  'pixel_identical_to_unmodified_original_region':True,
  'platform':name.split('_')[2] if len(name.split('_'))>3 else 'unknown',
  'alpha_preserved':True,'in_game':'UNTESTED',
  'A_B':'UNTOUCHED','old_original_crop':'PRESERVED_UNMODIFIED'}
 m=folder/'rework_manifest.json'
 m.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n')
 results.append({'english':rec['english'],'source':name,
                 'path':str(png),'original_box':rec['original_box'],
                 'rework_box':b,'sha256':artifact['new_crop_sha256']})
# Layout 5 x 3 text-only candidates for visual confirmation.
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
canvas=Image.new('RGB',(1480,5*235),(231,235,239))
draw=ImageDraw.Draw(canvas)
for i,r in enumerate(results):
 col=i%3;row=i//3
 x=col*493;y=row*235
 draw.rounded_rectangle((x+6,y+6,x+485,y+229),radius=8,fill=(255,255,255),outline=(196,202,207),width=2)
 draw.text((x+16,y+15),r['english']+'  '+r['source'].split('_')[2][:20],font=font,fill=(29,40,54))
 with Image.open(r['path']) as crop:
  bg=Image.new('RGBA',(461,150),(231,235,239,255))
  squares=ImageDraw.Draw(bg)
  for sy in range(0,150,18):
   for sx in range(0,461,18):
    if (sx//18+sy//18)%2==0:
     squares.rectangle((sx,sy,sx+17,sy+17),fill=(247,248,251))
  view=crop.copy()
  view.thumbnail((451,134),Image.Resampling.LANCZOS)
  bg.alpha_composite(view,((461-view.width)//2,(150-view.height)//2))
 canvas.paste(bg.convert('RGB'),(x+16,y+50))
 draw.text((x+16,y+207),'pixel-exact / TEST ONLY',font=font,fill=(73,81,89))
sheet=BASE/'qa_review_20261018/Q057_REWORK_15_CANDIDATES.jpg'
canvas.save(sheet,quality=94)
summary={
 'status':'Q057_15_NATIVE_REWORK_CANDIDATES_READY_NOT_APPROVED',
 'source_atlases':5,'phrases_per_atlas':3,'crop_candidates':len(results),
 'qa_full_original_sha':15,'qa_exact_pixels':15,'qa_manifest':15,
 'preview':str(sheet),'rework_root':str(OUT),
 'originals_untouched':True,'game_runtime':'UNTESTED'}
(BASE/'qa_review_20261018/Q057_REWORK_SUMMARY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(summary,ensure_ascii=False))
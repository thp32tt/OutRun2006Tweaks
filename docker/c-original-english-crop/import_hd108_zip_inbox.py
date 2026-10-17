#!/usr/bin/env python3
"""Import 108 original full-size source PNGs from the five exact 2026-10-13 ZIPs.

Never derives PNGs from obsolete 986 split tiles. Never modifies A/B/C queues.
Input archives are copied to N100 inbox out of band; this tool never guesses that
files were transferred. Output is immutable C-only full HD source input.
"""
import csv,hashlib,io,json,os,re,sys,tempfile,zipfile
from pathlib import Path
from PIL import Image
BASE=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
INBOX=BASE/'hd_original_108_zip_inbox'
TARGET=BASE/'hd_original_108_verified'
FILES=[
('OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip','31403fc5af3a5b3029b307dede7ec389f7d8ef3212fb85a6731ceda4b2a5f40a'),
('OutRun_ALL_HD_Korean_Source_PNG_PART02_of_05_20261013.zip','ddd10594308efb1099d547208cf5754c239188fba1139b5373ad4d8aadb7b936'),
('OutRun_ALL_HD_Korean_Source_PNG_PART03_of_05_20261013.zip','3daae8e75d6f21d73bca49979349ae91fa1fc0c92fb3777f572e83855055c364'),
('OutRun_ALL_HD_Korean_Source_PNG_PART04_of_05_20261013.zip','639201713a26ce6179f3cd013131da4e0b78f84f9a859ffc5fb9eb0d8c141778'),
('OutRun_ALL_HD_Korean_Source_PNG_PART05_of_05_20261013.zip','ff4e767bfd69bcd3800238970b7022bae2f0ee1c62674b00ae1a6f9a30f793bd')]
def shabytes(v):return hashlib.sha256(v).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for v in iter(lambda:f.read(1<<20),b''):h.update(v)
 return h.hexdigest()
def main():
 missing=[a for a,_ in FILES if not (INBOX/a).is_file()]
 if missing:
  print(json.dumps({'status':'WAITING_FOR_5_ORIGINAL_ZIPS','inbox':str(INBOX),'missing':missing,
                     'present':5-len(missing)},ensure_ascii=False))
  return 2
 for name,digest in FILES:
  p=INBOX/name
  if sha(p)!=digest:raise RuntimeError('ZIP_SHA_MISMATCH_'+name)
 with zipfile.ZipFile(INBOX/FILES[0][0]) as z:
  manifest=list(csv.DictReader(io.StringIO(z.read('01_DDS_PNG_MANIFEST_108.csv').decode('utf-8-sig'))))
 if len(manifest)!=108:raise RuntimeError('MANIFEST_COUNT_NOT_108')
 expected={r['png_filename']:r for r in manifest}
 if len(expected)!=108:raise RuntimeError('MANIFEST_DUPLICATE_PNG')
 staging=BASE/'hd_original_108_verify_staging'
 staging.mkdir(exist_ok=True)
 seen=set()
 for fname,_ in FILES:
  with zipfile.ZipFile(INBOX/fname) as z:
   if z.testzip() is not None:raise RuntimeError('ZIP_CRC_FAILED_'+fname)
   for member in z.infolist():
    name=member.filename
    if not name.lower().endswith('.png'):continue
    if name not in expected or name in seen or Path(name).name!=name:raise RuntimeError('UNSAFE_OR_DUPLICATE_PNG_'+name)
    data=z.read(name)
    spec=expected[name]
    if (shabytes(data)!=spec['png_sha256'] or len(data)!=int(spec['png_size_bytes'])):
     raise RuntimeError('MANIFEST_PNG_SHA_SIZE_MISMATCH_'+name)
    with Image.open(io.BytesIO(data)) as im:
     im.verify()
    with Image.open(io.BytesIO(data)) as im:
     if im.format!='PNG' or list(im.size)!=[int(spec['width']),int(spec['height'])]:
      raise RuntimeError('SOURCE_PNG_DIMENSIONS_MISMATCH_'+name)
    p=staging/name
    if p.exists():
     if sha(p)!=shabytes(data):raise RuntimeError('STAGING_FILE_COLLISION_'+name)
    else:p.write_bytes(data)
    seen.add(name)
 if seen!=set(expected):raise RuntimeError('COVERAGE_NOT_108')
 if TARGET.exists():
  if sum(1 for _ in TARGET.glob('*.png'))!=108:raise RuntimeError('TARGET_EXISTS_INCOMPLETE')
  for name,row in expected.items():
   if sha(TARGET/name)!=row['png_sha256']:raise RuntimeError('TARGET_HASH_CHANGED_'+name)
  status='ALREADY_PRESENT_VERIFIED'
 else:
  os.replace(staging,TARGET)
  status='IMPORTED_VERIFIED'
 receipt={'status':status,'original_full_hd_png':108,'zip_files':5,
          'source_kind':'LIBRARY_ORIGINAL_UNSPLIT_HD_PNG','mode':'C_EN_CROP_ONLY',
          'file_sha_verified':108,'manifest_matched':108,'folder':str(TARGET),
          'old_tiles_reused':False,'imagegen':False,'dds_compose':False}
 (BASE/'hd108_import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(receipt,ensure_ascii=False))
 return 0
if __name__=='__main__':sys.exit(main())
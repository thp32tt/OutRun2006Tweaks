#!/usr/bin/env python3
"""F3 source-only native crop collection; never draws Korean art into DDS."""
from pathlib import Path
import hashlib,json,zipfile,io
import numpy as np
from PIL import Image,ImageDraw
base=Path('/home/chatgpt-runner2/work/c_salvage_text_roi')
root=base/'F3_TWO_STYLES_20261016'
master=base/'original_hd_phrase_crops_20261016/MASTER_255_V2_20261016'
source=master/'crops'
manifest=json.loads((master/'MASTER_CROP_MANIFEST_255.json').read_text())
mapid={x['id']:x for x in manifest['items']}
families={
'Q053_MISSION_YELLOW_NAVY':[
('Q053-HIT_THE_CARS','차량을 들이받아!'),
('Q053-DODGE_THE_BOMBS','폭탄을 피해라!'),
('Q053-AVOID_ABDUCTION','납치를 피해라!'),
('Q053-AVOID_METEORS','운석을 피해라!'),
('Q053-DRIBBLE_BEACH_BALL','비치볼을 드리블해!'),
('Q053-PHOTOGRAPH_SIGHTS','명소를 촬영해!'),
('Q053-HIT_THE_DUCKS','오리를 맞혀라!'),
('Q053-SEE_THE_SIGHTS','명소를 구경해!')],
'Q060_METALLIC_GRADIENT':[
('Q060-CONTINUE_QUESTION','계속?'),
('Q060-RETRY','재시도'),
('Q060-PLEASE_WAIT','잠시 대기'),
('Q060-TRY_AGAIN_QUESTION','다시 시도?'),
('Q060-STAGE_CLEAR','스테이지 클리어'),
('Q060-PASS','통과!'),
('Q060-DUMPED_BIG','차였어!')]}
dds_info={
'Q053_MISSION_YELLOW_NAVY':{'dds':'q053_verified_original_568D3696_1024x1024.dds','format':'DXT5','mip_count':13,'dds_size':[4096,4096],'sha256':'65bc5e88e7b01f8148bcbbb2dc4b2225bf53c8501801e329c51ecb274e8cd813'},
'Q060_METALLIC_GRADIENT':{'dds':'Q060_A064FDFC_GITHUB_PINNED_ORIGINAL_20261016.dds','format':'RGBA32','mip_count':1,'dds_size':[4096,2048],'sha256':'6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc'}}
SHA=lambda b:hashlib.sha256(b).hexdigest()
out={'schema':'outrun-f3-source-two-family-v1','task_id':'OUTRUN-KR-Q053-Q060-F3-20261016','mode':'STATIC_MANUAL_PREPARATION_NO_DOCKER','planned_assets':15,'translation':'DRAFT_UNAPPROVED_VERIFY_WITH_TRANSLATION_SSOT','families':{},'F3_STATIC':'NOT_RUN','CLEAN':'NOT_RUN','DDS':'NOT_RUN','RUNTIME_VALIDATION':'UNTESTED'}
for fam,targets in families.items():
 rows=[]; fullpath=base/'source_full_20261012'/('q053_568D3696_FLIPY_CHECK_ORIENTATION.png' if fam.startswith('Q053') else 'q060_A064FDFC_FLIPY_CHECK_ORIENTATION.png')
 assert fullpath.is_file()
 with Image.open(fullpath) as fd: im=fd.convert('RGBA'); im.load()
 expected_sha='0893c0676397aee9cdf12b436f8d1e18eff55eccac55f1e4349e744c34b0478f' if fam.startswith('Q053') else 'c9600e9c77067b64b6e57d67ceb8e1ab58359479b5520fcdb44a042be5d19731'
 assert SHA(fullpath.read_bytes())==expected_sha,'SOURCE_PNG_SHA'
 sheet=Image.new('RGB',(1400,len(targets)*185),(24,29,42));d=ImageDraw.Draw(sheet)
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for i,(ident,ko) in enumerate(targets):
   src=mapid[ident];p=source/Path(src['file']).name;data=p.read_bytes()
   assert SHA(data)==src['roi_sha256'],ident+'_CROP_SHA'
   with Image.open(p) as pic: crop=pic.convert('RGBA')
   box=src['bbox_xyxy'];assert np.array_equal(np.asarray(crop),np.asarray(im.crop(box))),ident+'_PIXEL_EXACT'
   a=np.asarray(crop.getchannel('A'));nonzero=a>0
   # Reference crops can contain surrounding background art, so never assume mask==English characters.
   touch=bool(nonzero[0].any() or nonzero[-1].any() or nonzero[:,0].any() or nonzero[:,-1].any())
   rows.append({'asset_id':ident,'en':ident.split('-',1)[1].replace('_',' '),'ko_draft':ko,'native_crop':p.name,
      'sha256':src['roi_sha256'],'bbox_readable_xyxy':box,'size':list(crop.size),'alpha_nonzero':int(nonzero.sum()),'alpha_border_touched':touch,'background_art_mixed':'UNKNOWN_REVIEW_REQUIRED',
      'translation_approved':False,'sprite':'NOT_GENERATED','clean':'NOT_RUN','dds':'NOT_RUN'})
   z.writestr('native_crops/'+p.name,data)
   bg=Image.new('RGBA',crop.size,(23,35,61,255));bg.alpha_composite(crop)
   view=bg.convert('RGB');view.thumbnail((1350,142),Image.Resampling.LANCZOS)
   y=185*i
   d.text((14,y+6),f'{i+1}. {ident}  |  native {crop.size[0]}x{crop.size[1]}  |  alpha border={touch}',fill=(245,246,255))
   sheet.paste(view,(14,y+28))
  z.writestr('MAPPING_DRAFT.json',json.dumps(rows,ensure_ascii=False,indent=2))
 dds=dds_info[fam]
 out['families'][fam]={'source_readable_png_sha256':expected_sha,'source_dds':dds,'rows':rows,
  'source_sheet':fam+'_EN_NATIVE_REFERENCE.jpg'}
 ref=root/(fam+'_EN_NATIVE_REFERENCE.jpg');sheet.save(ref,quality=85)
 zpath=root/(fam+'_NATIVE_CROPS.zip')
 zpath.write_bytes(buf.getvalue())
 out['families'][fam]['source_sheet_sha256']=SHA(ref.read_bytes())
 out['families'][fam]['native_bundle_sha256']=SHA(zpath.read_bytes())
root.mkdir(exist_ok=True,parents=True)
m=root/'F3_INPUT_PREFLIGHT.json';m.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'manifest':str(m),'count':sum(len(x['rows']) for x in out['families'].values()),'families':{x:{'rows':len(y['rows']),'border_touch':sum(z['alpha_border_touched'] for z in y['rows']),'format':y['source_dds']['format'],'sha':y['native_bundle_sha256']} for x,y in out['families'].items()}},ensure_ascii=False))
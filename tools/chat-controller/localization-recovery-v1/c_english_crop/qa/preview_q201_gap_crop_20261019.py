from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import numpy as np,json,hashlib
BASE=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
SRC=BASE/'hd_original_108_verified/Q201_A9ABD877_BASE_READABLE_FLIPY.png'
OUT=BASE/'qa_review_20261018/next_last2'
out=OUT/'Q201_045?'
with Image.open(SRC) as im:
 a=np.asarray(im)
 y0,y1=1924,2036
 # Find nonempty vertical-column gap (full target region), separating glyph T and next STAGES.
 gaps=[(x,int((a[y0:y1,x,3]>24).sum())) for x in range(1140,1180)]
 candidate=(89,1924,1167,2036)
 original=im.crop((89,1924,1186,2036)).convert('RGBA')
 fixed=im.crop(candidate).convert('RGBA')
 file=OUT/'q201_coniferous_20261019_native_rgba.png'
 fixed.save(file)
 with Image.open(file) as r:
  assert r.mode=='RGBA' and r.tobytes()==fixed.tobytes()
 board=Image.new('RGB',(1600,500),(233,236,240))
 d=ImageDraw.Draw(board)
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
 for i,(x,raw,desc) in enumerate([(0,original,'OLD: right neighbor STAGES cuts in'),(0,fixed,'NEW: gap between final T and STAGES')]):
  y=i*245
  d.text((12,y+12),desc,font=font,fill=(25,33,45))
  bg=Image.new('RGBA',(1570,168),(227,230,235,255))
  sq=ImageDraw.Draw(bg)
  for ix in range(0,1570,24):
   for iy in range(0,168,24):
    if ((ix//24+iy//24)%2)==0:sq.rectangle((ix,iy,ix+23,iy+23),fill=(251,252,253,255))
  cp=raw.copy()
  cp.thumbnail((1550,155),Image.Resampling.LANCZOS)
  bg.alpha_composite(cp,((bg.width-cp.width)//2,(bg.height-cp.height)//2))
  board.paste(bg.convert('RGB'),(12,y+57))
  d.text((12,y+228),str((89,1924,1186,2036) if i==0 else candidate),font=font,fill=(82,91,103))
 preview=OUT/'Q201_NATIVE_GAP_BEFORE_AFTER_20261019.jpg'
 board.save(preview,quality=93)
 edge_cols={x:v for x,v in gaps}
 print(json.dumps({'candidate_bbox':candidate,
   'gap_alpha_counts':{str(k):v for k,v in edge_cols.items() if 1153<=k<=1176},
   'candidate_rightmost_5px_alpha_counts':[sum(fixed.getchannel('A').crop((fixed.width-j-1,0,fixed.width-j,fixed.height)).getdata()) for j in range(5)],
   'source_png_file':str(file),'preview':str(preview),
   'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}))
from pathlib import Path
from PIL import Image
import json,hashlib,io
import numpy as np
root=Path("/home/chatgpt-runner2/work/c_salvage_text_roi/F3_TWO_STYLES_20261016")
cropdir=Path("/home/chatgpt-runner2/work/c_salvage_text_roi/original_hd_phrase_crops_20261016/MASTER_255_V2_20261016/crops")
original=json.loads((root/"F3_INPUT_PREFLIGHT.json").read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
out={"schema":"F3_IMAGEGEN_BATCH_LAYOUT_V1","source_status":"15_NATIVE_PIXEL_EXACT","instructions":"Return Korean transparent RGBA in identical independent slots","families":{}}
for family, group in original["families"].items():
 rows=group["rows"];n=len(rows)
 if family.startswith("Q053"):
  columns=2
  widths=[max(rows[i]["size"][0] for i in range(j,n,2)) for j in range(2)]
  heights=[max(x["size"][1] for x in rows[i:i+2]) for i in range(0,n,2)]
  pad=45;gapx=64;gapy=38
 else:
  columns=1;widths=[max(x["size"][0] for x in rows)];heights=[x["size"][1] for x in rows]
  pad=42;gapx=0;gapy=32
 w=sum(widths)+2*pad+gapx*(columns-1);h=sum(heights)+2*pad+gapy*(len(heights)-1)
 assert w<=2048 and h<=2048,(family,w,h)
 sheet=Image.new("RGBA",(w,h),(0,0,0,0))
 info=[];y=pad
 for ri,rh in enumerate(heights):
  x=pad
  for ci in range(columns):
   idx=ri*columns+ci
   if idx>=n:continue
   entry=rows[idx];p=cropdir/entry["native_crop"]
   bs=p.read_bytes()
   assert sha(bs)==entry["sha256"],entry["asset_id"]
   with Image.open(io.BytesIO(bs)) as im: tile=im.convert("RGBA")
   assert list(tile.size)==entry["size"]
   yy=y+(rh-tile.height)//2
   sheet.paste(tile,(x,yy))
   card={"slot":idx+1,"row":ri+1,"column":ci+1,"id":entry["asset_id"],"en":entry["en"],"ko_draft":entry["ko_draft"],"bbox":[x,yy,x+tile.width,yy+tile.height],"original_sha256":entry["sha256"]}
   info.append(card)
   x+=widths[ci]+gapx
  y+=rh+gapy
 for rec in info:
  with Image.open(cropdir/rows[rec["slot"]-1]["native_crop"]) as o: a=np.asarray(o.convert("RGBA"))
  b=np.asarray(sheet.crop(rec["bbox"]))
  assert np.array_equal(a,b),rec["id"]
 outfile=root/(family+"_IMAGEGEN_BATCH_INPUT.png")
 sheet.save(outfile,optimize=True)
 bg=Image.new("RGBA",(w,h),(9,19,47,255));bg.alpha_composite(sheet)
 review=root/(family+"_IMAGEGEN_BATCH_REVIEW.jpg")
 bg.convert("RGB").save(review,quality=87)
 out["families"][family]={"filename":outfile.name,"width":w,"height":h,"sha256":sha(outfile.read_bytes()),"slots":info,"review":review.name,"review_sha256":sha(review.read_bytes())}
(root/"F3_BATCH_INPUT_LAYOUT.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"images":[{"family":k,"file":v["filename"],"width":v["width"],"height":v["height"],"sha256":v["sha256"],"count":len(v["slots"])} for k,v in out["families"].items()]},ensure_ascii=False))
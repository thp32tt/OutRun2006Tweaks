#!/usr/bin/env python3
"""Seed distinct, never-generated native original HD source sheets, one per queued task.
Use SHA-verified 255 reference crop manifest and reviewed transcription index.
Does not modify legacy A/B queues; does not generate or compose Korean DDS.
"""
import argparse,hashlib,json,io,os
from pathlib import Path
from PIL import Image
import numpy as np

SOURCE_MAP={
'Q054':[("MATCH_TOTAL","Match the total!"),("COUNT_GIFTS","Count the gifts!"),
 ("HIT_THE_BOOST","Hit the boost!"),("KEEP_CONTROL","Keep control!"),
 ("HOLD_THE_LINE","Hold the line!"),("HONK_THE_HORN","Honk the horn!"),
 ("DO_THE_MATH","Do the math!"),("GUESS_THE_SOUND","Guess the sound!"),
 ("COUNT_GREEN_CARS","Count Green Cars!"),("COUNT_BLUE_CARS","Count Blue Cars!"),
 ("COUNT_SHEEP","Count the sheep!"),("COUNT_RED_CARS","Count Red Cars!"),
 ("MEMORIZE_SEQUENCE","Memorize the sequence!"),("DRIVE_ABOVE_SPEED","Drive above the speed!"),
 ("SPOT_ODD_ONE_OUT","Spot the odd one out!"),("SLIPSTREAM_CARS","Slipstream the cars!"),
 ("RUN_THROUGH_GREEN","Run through green!")],
'Q060':[("KNOCKOUT_SMALL","KNOCKOUT!"),("RANKING","Ranking"),("STAGE","Stage"),
 ("RANK","Rank"),("OUTRUN_MILES","OUTRUN MILES:"),("BEST_TIME","BEST TIME:"),("EASY","EASY")],
'Q057':[("HEARTS","Hearts"),("TECHNICAL_BONUS","Technical Bonus"),
 ("STORING_ONLINE_RECORD","STORING ONLINE RECORD..."),
 ("SPECIAL_REQUEST","SPECIAL REQUEST"),("HIT_THE_GHOST","Hit the ghost!"),
 ("EXIT","EXIT"),("COLLECT_THE_STARS","Collect the stars!")],
'Q053':[("END","END"),("ANSWER","ANSWER"),("QUESTION","QUESTION"),
 ("START","START"),("HIT_THE_ZIPPERS","Hit the zippers!"),("FEED_THE_GRILL","Feed the girl!")]
}
# Split work evenly: A 6+6+6 = 3, B 4+3+7 = 3 batches.
GROUPS=[('A','Q054',slice(0,6)),('A','Q054',slice(6,12)),('A','Q053',slice(0,6)),
 ('B','Q060',slice(0,4)),('B','Q060',slice(4,7)),('B','Q057',slice(0,7))]

sha=lambda d:hashlib.sha256(d).hexdigest()
def save_no_overwrite(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert path.read_bytes()==data, 'EXISTING_DIFFERENT_FILE '+str(path)
    else:path.write_bytes(data)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-root',required=True)
    ap.add_argument('--out',required=True)
    ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args();source=Path(a.source_root);out=Path(a.out)
    manifest=json.loads((source/'original_hd_phrase_crops_20261016/MASTER_255_V2_20261016/MASTER_CROP_MANIFEST_255.json').read_text())
    registry={x['id']:x for x in manifest['items']}
    crops=source/'original_hd_phrase_crops_20261016/MASTER_255_V2_20261016/crops'
    transcripts=[json.loads(line) for line in (source/'source_full_20261012/transcriptions.jsonl').read_text().splitlines() if line.strip()]
    trans={int(x['index']):{t['source'].casefold().strip():t['korean'] for t in x.get('segments',[])} for x in transcripts}
    result=[]
    for idx,(role,atlas,part) in enumerate(GROUPS,1):
        seq=SOURCE_MAP[atlas][part]
        columns=2 if atlas=='Q054' else 1
        tiles=[]
        for key,en in seq:
            crop_id=atlas+'-'+key
            assert crop_id in registry,crop_id
            entry=registry[crop_id]
            assert entry['status']=='SOURCE_CROP_REFERENCE',crop_id
            t=trans[int(atlas[1:])];ko=t.get(en.casefold().strip())
            assert ko and any('\uac00'<=c<='\ud7a3' for c in ko),'REVIEWED_TRANSLATION_MISSING '+en
            p=crops/Path(entry['file']).name
            raw=p.read_bytes()
            assert sha(raw)==entry['roi_sha256'],'CROP_SHA_MISMATCH '+crop_id
            with Image.open(io.BytesIO(raw)) as im:
                tile=im.convert('RGBA')
            assert list(tile.size)==[entry['bbox_xyxy'][2]-entry['bbox_xyxy'][0],entry['bbox_xyxy'][3]-entry['bbox_xyxy'][1]]
            tiles.append((crop_id,en,ko,tile,entry))
        widths=[max(tiles[i][3].width for i in range(c,len(tiles),columns)) for c in range(columns)]
        heights=[max(tiles[i][3].height for i in range(r,min(len(tiles),r+columns))) for r in range(0,len(tiles),columns)]
        padding=35;sep_x=54;sep_y=35
        w=sum(widths)+padding*2+sep_x*(columns-1)
        h=sum(heights)+padding*2+sep_y*(len(heights)-1)
        if w>2048 or h>2048:
            raise RuntimeError(f'SHEET_TOO_BIG {atlas} {w}x{h}: must split without resizing, no crop')
        sheet=Image.new('RGBA',(w,h),(0,0,0,0))
        slots=[];y=padding
        for row,height in enumerate(heights):
            x=padding
            for col in range(columns):
                k=row*columns+col
                if k>=len(tiles):break
                ident,en,ko,img,meta=tiles[k]
                yy=y+(height-img.height)//2
                sheet.paste(img,(x,yy))
                assert np.array_equal(np.asarray(img),np.asarray(sheet.crop((x,yy,x+img.width,yy+img.height))))
                slots.append({'index':k+1,'asset_id':ident,'english':en,'korean':ko,'native_source_sha256':meta['roi_sha256'],'source_bbox_xyxy':meta['bbox_xyxy'],'sheet_bbox_xyxy':[x,yy,x+img.width,yy+img.height],'reference_only_not_clean_mask':True})
                x+=widths[col]+sep_x
            y+=height+sep_y
        task=f'OUTRUN-KR-IMAGEONLY-{role}-{atlas}-{part.start+1:02d}-{part.stop:02d}-20261017'
        pngname=task+'_EN_SHEET.png'; promptname=task+'_PROMPT.txt'; jobname=task+'.json'
        buff=io.BytesIO();sheet.save(buff,format='PNG',optimize=True);png_bytes=buff.getvalue()
        prompt='@이미지 생성\n\nAttached ONE source sheet of OutRun 2006 original HD English glyphs. '
        prompt+='Generate exactly ONE new Korean RGBA PNG with all '+str(len(slots))+' slots in exactly the same relative positions ('+str(columns)+' columns). '
        prompt+='Match each source phrase color/metallic shine/yellow fill/outline/slant/shadow independently; do not alter the exact Korean strings.\n'
        for s in slots:prompt+=f"Slot {s['index']}: {s['english']} → {s['korean']}\n"
        prompt+=('\nOutput one single transparent PNG containing only Korean text/effects. No original English, scenes, UI, numbers, panel rectangles, labels, infographic or explanation. '
                 'Keep all slots separate with their original order and gutters; do not crop strokes or create fake Hangul. '
                 'Do not attempt DDS recomposition or clean plate; other work will handle that later.\n')
        pb=prompt.encode('utf-8')
        payload={'task_id':task,'role':role,'status':'READY' if not a.dry_run else 'DRY_RUN','atlas':atlas,'input_file':pngname,'input_sha256':sha(png_bytes),'prompt_file':promptname,'prompt_sha256':sha(pb),'expected_slots':len(slots),'slots':slots,'source_policy':'OFFICIAL_TRANSCRIPT_REVIEWED_KOREAN','legacy_queue_touched':False}
        if not a.dry_run:
            save_no_overwrite(out/'inputs'/role/pngname,png_bytes)
            save_no_overwrite(out/'prompts'/promptname,pb)
            save_no_overwrite(out/'inputs'/role/jobname,(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode())
        result.append({'task_id':task,'role':role,'slots':len(slots),'size':sheet.size,'input_sha256':sha(png_bytes),'preview':(slots[0]['english'],slots[0]['korean'])})
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
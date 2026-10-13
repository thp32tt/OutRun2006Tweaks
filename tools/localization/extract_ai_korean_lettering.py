#!/usr/bin/env python3
"""Extract AI lettering only; compose only on a separately QA-accepted HD clean plate.

No DDS is emitted here. Use build_clean_graphics_candidate.py after independent review.
Coordinates are [left, top, right, bottom] and are intentionally manual, not OCR.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(manifest, sheets, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    opened = {}
    for key, cfg in manifest['sheets'].items():
        path = Path(sheets[key])
        if sha(path) != cfg['sha256']:
            raise ValueError(f'SOURCE_SHA_MISMATCH: {key}')
        opened[key] = Image.open(path).convert('RGBA')
        if list(opened[key].size) != cfg['canvas']:
            raise ValueError(f'CANVAS_MISMATCH: {key}')
    report = {'asset_id': manifest['asset_id'], 'stage':'AI_LETTERING_EXTRACT_ONLY',
              'runtime_validation':'UNTESTED', 'candidates':[]}
    for item in manifest['elements']:
        l,t,r,b = item['sheet_crop_ltrb']
        src=opened[item['sheet']]
        if not (0 <= l < r <= src.width and 0 <= t < b <= src.height):
            raise ValueError(f'INVALID_CROP: {item["id"]}')
        layer=src.crop((l,t,r,b))
        # Remove nearly transparent hallucinated edge pixels only; never erase opaque effects.
        pix=layer.load()
        for y in range(layer.height):
            for x in range(layer.width):
                rr,gg,bb,a = pix[x,y]
                if a < 10:
                    pix[x,y]=(0,0,0,0)
        bb=layer.getchannel('A').getbbox()
        if bb is None: raise ValueError(f'EMPTY_TEXT_LAYER: {item["id"]}')
        layer=layer.crop(bb)
        output=out_dir/(item['id'] + '.png')
        layer.save(output, optimize=True)
        report['candidates'].append({'id':item['id'], 'text':item['canonical_korean'],
           'sprite':item['sprite'], 'layer_png':output.name,'sha256':sha(output),
           'layer_size':list(layer.size),'cell_hd_ltrb':item['hd_cell_ltrb'],
           'no_ai_panel_composited':True,'source_sheet':item['sheet'],
           'status':'EXTRACTED_PENDING_CLEAN_PLATE_AND_NATIVE_FONT_SIZE_QA'})
    (out_dir/'extraction_qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


def compose(manifest, layers_dir, plate, plate_qa, output, preview_only=False):
    """Fail closed when exact clean plate is missing; never upscale flattened AI raster."""
    qa=json.loads(plate_qa.read_text(encoding='utf-8'))
    if qa.get('schema')!='outrun-clean-plate-qa-v1' or qa.get('asset_id')!=manifest['asset_id']:
        raise ValueError('UNVERIFIED_CLEAN_PLATE_QA')
    if qa.get('clean_plate_sha256')!=sha(plate):
        raise ValueError('CLEAN_PLATE_SHA_MISMATCH')
    mandatory=['no_source_text_residue','no_box_or_seam','protected_artwork_unchanged',
               'alpha_continuity','native_resolution_review']
    if any(qa.get('checks',{}).get(k) is not True for k in mandatory):
        raise ValueError('CLEAN_PLATE_QA_NOT_PASSED')
    base=Image.open(plate).convert('RGBA')
    if list(base.size)!=manifest['hd_canvas']:
        raise ValueError('NONCANONICAL_HD_CANVAS')
    dst=base.copy(); evidence=[]
    for item in manifest['elements']:
        layer=Image.open(layers_dir/(item['id']+'.png')).convert('RGBA')
        l,t,r,b=item['hd_cell_ltrb']; inset=2
        if not(0<=l<r<=base.width and 0<=t<b<=base.height):
            raise ValueError('HD_CELL_OUT_OF_BOUNDS')
        if layer.width>r-l-inset*2 or layer.height>b-t-inset*2:
            raise ValueError('LETTERING_1PX_OVERFLOW_RISK')
        # Never fabricate native HD sharpness by enlarging a flattened AI raster.
        if not preview_only and layer.width < (r-l)*0.50:
            raise ValueError('LOW_RES_AI_GLYPH_HOLD_NO_UPSCALE')
        x=l+(r-l-layer.width)//2; y=t+(b-t-layer.height)//2
        if x<l+inset or y<t+inset or x+layer.width>r-inset or y+layer.height>b-inset:
            raise ValueError('STRICT_INSET_FAILED')
        dst.alpha_composite(layer,(x,y))
        evidence.append({'id':item['id'],'bbox_ltrb':[x,y,x+layer.width,y+layer.height]})
    mask=Image.new('L',base.size,0)
    from PIL import ImageDraw
    dr=ImageDraw.Draw(mask)
    for item in manifest['elements']:
        l,t,r,b=item['hd_cell_ltrb']; dr.rectangle((l,t,r-1,b-1),fill=255)
    d=ImageChops.difference(base,dst)
    combined=d.getchannel('R')
    for channel in d.split()[1:]:combined=ImageChops.lighter(combined,channel)
    leak=ImageChops.multiply(combined,ImageChops.invert(mask)).getbbox()
    if leak:raise ValueError('OUTSIDE_CELL_CHANGED')
    output.parent.mkdir(parents=True,exist_ok=True);dst.save(output)
    return {'stage':'PREVIEW_ONLY' if preview_only else 'PENDING_INDEPENDENT_QA',
            'elements':evidence,'changed_pixels_outside_cell':0,'runtime_validation':'UNTESTED'}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',required=True,type=Path)
    ap.add_argument('--ai-sheet',type=Path); ap.add_argument('--reference-sheet',type=Path)
    ap.add_argument('--extract-dir',type=Path)
    ap.add_argument('--clean-plate',type=Path); ap.add_argument('--clean-plate-qa',type=Path)
    ap.add_argument('--compose-png',type=Path); ap.add_argument('--preview-only',action='store_true')
    args=ap.parse_args(); m=json.loads(args.manifest.read_text(encoding='utf-8'))
    if args.extract_dir is None:ap.error('--extract-dir required')
    if args.ai_sheet or args.reference_sheet:
        if not(args.ai_sheet and args.reference_sheet):ap.error('both sheets required')
        result=extract(m,{'ai':args.ai_sheet,'reference':args.reference_sheet},args.extract_dir)
        print(json.dumps(result,ensure_ascii=False))
    if args.compose_png:
        if not(args.clean_plate and args.clean_plate_qa):
            ap.error('--clean-plate and --clean-plate-qa required to compose')
        print(json.dumps(compose(m,args.extract_dir,args.clean_plate,args.clean_plate_qa,
              args.compose_png,args.preview_only),ensure_ascii=False))
if __name__=='__main__': main()

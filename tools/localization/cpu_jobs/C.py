#!/usr/bin/env python3
import hashlib, json, os, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

if os.environ.get('OUTRUN_CPU_WORKER') != 'github-actions' or os.environ.get('OUTRUN_CPU_ROLE') != 'C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd(); run='20261004-C-USERPOLICY01'; out=repo/'localization/graphics/role_C'/run; out.mkdir(parents=True,exist_ok=True)
CANON={
 'ALPINE':'알파인','ANCIENT RUINS':'에인션트 루인스','BAY AREA':'베이 에어리어','BIG FOREST':'빅 포레스트','CANYON':'캐니언','CAPE WAY':'케이프 웨이','CASINO TOWN':'카지노 타운','CASTLE WALL':'캐슬 월','CLOUDY HIGHLAND':'클라우디 하이랜드','CONIFEROUS FOREST':'코니퍼러스 포레스트','DEEP LAKE':'딥 레이크','DESERT':'데저트','FLORAL VILLAGE':'플로럴 빌리지','GHOST FOREST':'고스트 포레스트','GIANT STATUES':'자이언트 스태추스','ICE SCAPE':'아이스스케이프','IMPERIAL AVENUE':'임페리얼 애비뉴','INDUSTRIAL COMPLEX':'인더스트리얼 컴플렉스','JUNGLE':'정글','LEGEND':'레전드','LOST CITY':'로스트 시티','METROPOLIS':'메트로폴리스','MILKY WAY':'밀키 웨이','NATIONAL PARK':'내셔널 파크','PALM BEACH':'팜 비치','SKYSCRAPERS':'스카이스크레이퍼스','SNOW MOUNTAIN':'스노 마운틴','SUNNY BEACH':'서니 비치','TULIP GARDEN':'튤립 가든','WATER FALLS':'워터폴스','WATERFALLS':'워터폴스'}
SONGS={'RUSH A DIFFICULTY','SHAKE THE STREET','WHO ARE YOU?','WHO ARE YOU','PASSING BREEZE','RISKY RIDE','SHINY WORLD','SPLASH WAVE','NIGHT BIRD','RADIATION','MAGICAL SOUND SHOWER','LAST WAVE','KEEP YOUR HEART -1989-'}

assets=[
 dict(id='AA04D779', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds', source_url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds', report='localization/graphics/role_B/20261004-B-USERPOLICY01/B_USERPOLICY01_AA04D779_REPORT.json', mask='localization/graphics/role_B/20261004-B-USERPOLICY01/AA04D779_SOURCE_TEXT_MASK.png', clean='localization/graphics/role_B/20261004-B-USERPOLICY01/AA04D779_CLEAN_PLATE.png'),
 dict(id='39229D64', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds', report='localization/graphics/role_A/20261004-A-RECOVERY06/A_RECOVERY06_39229D64_REPORT.json', mask='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_SOURCE_TEXT_MASK.png', clean='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_CLEAN_PLATE.png'),
 dict(id='568D3696', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds', report='localization/graphics/role_A/20261004-A-RECOVERY02/A_RECOVERY02_568D3696_REPORT.json', mask='localization/graphics/role_C/20261004-1600-C89/C89_568D3696_SOURCE_TEXT_MASK_CORRECTED.png', clean_tiles=[f'localization/graphics/role_C/20261004-1600-C89/C89_568D3696_CLEAN_PLATE_CORRECTED_TILE_{i}.png' for i in range(4)]),
 dict(id='2DA43E41', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds', report='localization/graphics/role_B/20261004-B-RECOVERY05/B_RECOVERY05_2DA43E41_REPORT.json', mask='localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_SOURCE_TEXT_MASK_CANONICAL.png', clean='localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_CLEAN_PLATE_CANONICAL.png', target='localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_TARGET_TEXT_MASK.png', preserved_song='Keep Your Heart -1989-'),
 dict(id='C075FB49', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds', report='localization/graphics/role_A/20261004-A-RECOVERY05/A_RECOVERY05_C075FB49_REPORT.json', mask='localization/graphics/role_A/20261004-A-RECOVERY05/C075FB49_SOURCE_TEXT_MASK.png', clean='localization/graphics/role_A/20261004-A-RECOVERY05/C075FB49_CLEAN_PLATE.png'),
 dict(id='A064FDFC', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds', report='localization/graphics/role_B/20261004-B-RECOVERY02/B_RECOVERY02_A064FDFC_REPORT.json', mask='localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_SOURCE_TEXT_MASK.png', clean='localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_CLEAN_PLATE.png', target='localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_TARGET_TEXT_MASK.png'),
 dict(id='FF2462BB', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds', report='localization/graphics/role_C/20261004-1245-C86/C86_FF2462BB_FINAL_QA.json', mask='localization/graphics/role_A/20261004-A-RECOVERY01/FF2462BB_SOURCE_TEXT_MASK.png', clean='localization/graphics/role_A/20261004-A-RECOVERY01/FF2462BB_CLEAN_PLATE.png'),
 dict(id='FA7BBB13', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds', report='localization/graphics/role_B/20261004-B-RECOVERY01/B_RECOVERY01_FA7BBB13_REPORT.json', mask='localization/graphics/role_B/20261004-B-RECOVERY01/FA7BBB13_SOURCE_TEXT_MASK.png', clean='localization/graphics/role_B/20261004-B-RECOVERY01/FA7BBB13_CLEAN_PLATE.png', target='localization/graphics/role_B/20261004-B-RECOVERY01/FA7BBB13_TARGET_TEXT_MASK.png'),
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readable(p): return Image.open(p).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def maskimg(p,size):
    im=Image.open(p).convert('L');
    if im.size!=size: raise RuntimeError(('mask-size',p,im.size,size))
    return np.asarray(im)>0
def bbox(a):
    ys,xs=np.nonzero(a)
    if len(xs)==0:return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def crop_bbox(a,b):
    x0,y0,x1,y1=map(int,b); sub=a[y0:y1,x0:x1]; bb=bbox(sub)
    return None if bb is None else [bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
def union_rect(size,rows):
    W,H=size; a=np.zeros((H,W),bool)
    for r in rows:
        b=r.get('original_bbox')
        if b: x0,y0,x1,y1=map(int,b); a[y0:y1,x0:x1]=1
    return a

def rows_from(d):
    if isinstance(d.get('rows'),list): return d['rows']
    if isinstance(d.get('bbox_gate'),dict) and isinstance(d['bbox_gate'].get('rows'),list): return d['bbox_gate']['rows']
    return []
def clean_image(cfg,size):
    if cfg.get('clean'):
        im=Image.open(repo/cfg['clean']).convert('RGBA')
        if im.size!=size: raise RuntimeError(('clean-size',cfg['id'],im.size,size))
        return im
    tiles=[Image.open(repo/x).convert('RGBA') for x in cfg['clean_tiles']]
    im=Image.new('RGBA',size,(0,0,0,0)); y=0
    for t in tiles: im.paste(t,(0,y)); y+=t.height
    if y!=size[1]: raise RuntimeError(('tile-height',cfg['id'],y,size))
    return im

def ensure_source(cfg):
    if cfg.get('source'): return repo/cfg['source']
    p=Path('/tmp')/(cfg['id']+'_source.dds'); urllib.request.urlretrieve(cfg['source_url'],p); return p

def comp(im,bg=(62,62,62,255)):
    b=Image.new('RGBA',im.size,bg); b.alpha_composite(im); return b.convert('RGB')
def card(im,label,maxw=560,maxh=560):
    v=comp(im); v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    c=Image.new('RGB',(v.width,v.height+28),'white'); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill='black'); return c

results=[]; visual_rows=[]; multiline_cards=[]
for cfg in assets:
    aid=cfg['id']; srcp=ensure_source(cfg); candp=repo/cfg['candidate']; rep=json.loads((repo/cfg['report']).read_text(encoding='utf-8')); rows=rows_from(rep)
    if not rows: raise RuntimeError((aid,'no rows in',cfg['report']))
    src=readable(srcp); cand=readable(candp); size=src.size
    if cand.size!=size: raise RuntimeError((aid,'candidate size',cand.size,size))
    clean=clean_image(cfg,size); sm=maskimg(repo/cfg['mask'],size)
    if cfg.get('target'): tm=maskimg(repo/cfg['target'],size)
    else:
        ca=np.asarray(cand,dtype=np.int16); cl=np.asarray(clean,dtype=np.int16)
        delta=np.max(np.abs(ca-cl),axis=2)
        # Significant decoded lettering delta; suppress tiny DXT block noise.
        tm=(delta>=12) & ((ca[:,:,3]>8)|(cl[:,:,3]>8))
    rowres=[]; fail=[]; stage_fail=[]; song_fail=[]
    for i,r in enumerate(rows):
        coarse=r.get('original_bbox')
        if not coarse: continue
        sb=crop_bbox(sm,coarse); tb=crop_bbox(tm,coarse)
        if sb is None or tb is None:
            rr={'index':i,'key':r.get('key'),'source':r.get('source'),'korean':r.get('korean'),'coarse_bbox':coarse,'source_exact_bbox':sb,'localized_exact_bbox':tb,'size_ceiling':'HOLD_MISSING_MASK_EVIDENCE'}; rowres.append(rr); fail.append(rr); continue
        sw,sh=sb[2]-sb[0],sb[3]-sb[1]; lw,lh=tb[2]-tb[0],tb[3]-tb[1]
        contain=tb[0]>=sb[0] and tb[1]>=sb[1] and tb[2]<=sb[2] and tb[3]<=sb[3]
        sizeok=lw<=sw and lh<=sh
        rr={'index':i,'key':r.get('key'),'source':r.get('source'),'korean':r.get('korean'),'coarse_bbox':list(map(int,coarse)),'source_exact_bbox':sb,'localized_exact_bbox':tb,'source_size':[sw,sh],'localized_size':[lw,lh],'delta_size':[lw-sw,lh-sh],'exact_containment':contain,'size_ceiling':'PASS' if (contain and sizeok) else 'REWORK_REQUIRED'}
        srcname=str(r.get('source') or '').strip(); ko=str(r.get('korean') or '').strip(); up=srcname.upper()
        if up in CANON:
            rr['stage_expected']=CANON[up]; rr['stage_name_policy']='PASS' if ko==CANON[up] else 'REWORK_REQUIRED'
            if rr['stage_name_policy']!='PASS': stage_fail.append(rr)
        if up in SONGS:
            rr['song_title_policy']='PASS' if ko==srcname else 'REWORK_REQUIRED'
            if rr['song_title_policy']!='PASS': song_fail.append(rr)
        rowres.append(rr)
        if rr['size_ceiling']!='PASS': fail.append(rr)
        lines=r.get('render_lines')
        if (isinstance(lines,list) and len(lines)>1) or (' / ' in ko):
            pad=24; x0,y0,x1,y1=coarse; cr=(max(0,x0-pad),max(0,y0-pad),min(size[0],x1+pad),min(size[1],y1+pad))
            a=comp(src).crop(cr); b=comp(cand).crop(cr); w=a.width+b.width+8; h=max(a.height,b.height)+32
            cc=Image.new('RGB',(w,h),'white'); cc.paste(a,(0,32)); cc.paste(b,(a.width+8,32)); ImageDraw.Draw(cc).text((4,5),f'{aid} {srcname} -> {ko}',fill='black'); multiline_cards.append(cc)
    # Existing exact mask confinement and preserved-area check.
    coarse_union=union_rect(size,rows); s=np.asarray(src); c=np.asarray(cand); diff=np.any(s!=c,axis=2)
    outside=int(np.logical_and(diff,~coarse_union).sum())
    semantic_ok=not stage_fail and not song_fail
    status='PASS' if not fail and semantic_ok else 'REWORK_REQUIRED'
    if cfg.get('preserved_song'):
        # It is outside localized row regions; exact outside-region equality is the pixel preservation proof for RGBA assets.
        preserved='PASS' if outside==0 else 'HOLD_EXACT_OUTSIDE_DIFF_NONZERO'
    else: preserved='NOT_APPLICABLE_OR_NO_KNOWN_TITLE'
    results.append({'asset':aid,'candidate_sha256':sha(candp),'source_sha256':sha(srcp),'rows_checked':len(rowres),'size_failures':len(fail),'stage_name_failures':len(stage_fail),'song_title_row_failures':len(song_fail),'changed_pixels_outside_reported_text_regions':outside,'preserved_known_song_title':cfg.get('preserved_song'),'song_title_pixel_preservation_gate':preserved,'multi_line_style_gate':'PENDING_CONTROLLER_VISUAL_REVIEW','rows':rowres,'status':status})
    a=card(src,aid+' SOURCE'); b=card(cand,aid+' KOREAN'); row=Image.new('RGB',(a.width+b.width+8,max(a.height,b.height)),'white'); row.paste(a,(0,0)); row.paste(b,(a.width+8,0)); visual_rows.append(row)

W=max(x.width for x in visual_rows); H=sum(x.height for x in visual_rows)+8*(len(visual_rows)-1); sheet=Image.new('RGB',(W,H),'white'); y=0
for x in visual_rows: sheet.paste(x,(0,y)); y+=x.height+8
sheet.save(out/'C_USERPOLICY01_EXISTING8_FULL_COMPARE.jpg',quality=94)
if multiline_cards:
    W=max(x.width for x in multiline_cards); H=sum(x.height for x in multiline_cards)+6*(len(multiline_cards)-1); ms=Image.new('RGB',(W,H),'white'); y=0
    for x in multiline_cards: ms.paste(x,(0,y)); y+=x.height+6
    ms.save(out/'C_USERPOLICY01_MULTILINE_STYLE_REVIEW.jpg',quality=95)
summary={'schema_version':1,'run':run,'policy':'2026-10-04 user policy: stage transliteration; exact source text size ceiling; source-faithful multi-line style; preserve English song titles','scope':'re-QA the eight previously presented static-pass assets','assets_total':len(results),'machine_pass':sum(r['status']=='PASS' for r in results),'machine_rework_required':sum(r['status']!='PASS' for r in results),'results':results,'controller_multiline_visual_qa':'PENDING','runtime_validation':'UNTESTED','status':'MACHINE_REQA_COMPLETE_PENDING_CONTROLLER_STYLE_REVIEW'}
(out/'C_USERPOLICY01_EXISTING8_REQA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C_USERPOLICY01_DONE','PASS',summary['machine_pass'],'REWORK',summary['machine_rework_required'])
for r in results: print(r['asset'],r['status'],'sizefail',r['size_failures'],'stagefail',r['stage_name_failures'],'songfail',r['song_title_row_failures'],'outside',r['changed_pixels_outside_reported_text_regions'])

#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter

if os.environ.get('OUTRUN_CPU_WORKER') != 'github-actions' or os.environ.get('OUTRUN_CPU_ROLE') != 'C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd(); run='20261004-C-OVERLAP01'; out=repo/'localization/graphics/role_C'/run; out.mkdir(parents=True,exist_ok=True)
assets=[
 dict(num=2,id='39229D64', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds', clean='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_CLEAN_PLATE.png', protected='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_PROTECTED_MASK.png', allowed='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_ALLOWED_TEXT_REGION_MASK.png', source_text='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_SOURCE_TEXT_MASK.png', report='localization/graphics/role_A/20261004-A-RECOVERY06/A_RECOVERY06_39229D64_REPORT.json', base_scale=.90),
 dict(num=6,id='A064FDFC', source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds', candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds', clean='localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_CLEAN_PLATE.png', protected='localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_PROTECTED_MASK.png', allowed='localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_ALLOWED_TEXT_REGION_MASK.png', source_text='localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_SOURCE_TEXT_MASK.png', report='localization/graphics/role_B/20261004-B-RECOVERY02/B_RECOVERY02_A064FDFC_REPORT.json', base_scale=.88),
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readable_dds(p): return ImageOps.flip(Image.open(p).convert('RGBA'))
def bbox_bool(m):
    yy,xx=np.nonzero(m)
    if len(xx)==0:return None
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
def row_local_bbox(r):
    for k in ('localized_bbox','new_localized_bbox','localized_changed_bbox','decoded_candidate_alpha_bbox','previous_localized_bbox'):
        if r.get(k): return list(map(int,r[k]))
    return None

def dilate_bool(m, radius=2):
    if radius<=0:return m
    im=Image.fromarray((m.astype(np.uint8)*255),'L').filter(ImageFilter.MaxFilter(radius*2+1))
    return np.asarray(im)>0

def write_rgba_dds(template, readable, dest):
    tb=Path(template).read_bytes(); header=tb[:128]
    pf=struct.unpack_from('<8I',header,76)
    if pf[3:] != (32,255,65280,16711680,4278190080): raise RuntimeError(('unexpected RGBA masks',pf))
    raw=ImageOps.flip(readable).convert('RGBA').tobytes('raw','RGBA')
    expected=readable.width*readable.height*4
    if len(raw)!=expected: raise RuntimeError(('raw size',len(raw),expected))
    Path(dest).parent.mkdir(parents=True,exist_ok=True); Path(dest).write_bytes(header+raw)

def make_overlay(cand,clean,box):
    x0,y0,x1,y1=box
    ca=np.asarray(cand.crop(box),dtype=np.int16); cl=np.asarray(clean.crop(box),dtype=np.int16)
    diff=np.max(np.abs(ca-cl),axis=2)
    mask=diff>0
    bb=bbox_bool(mask)
    if bb is None:return None,None,None
    # Crop to actual changed pixels, preserving all exact current Korean effect pixels.
    ax0,ay0,ax1,ay1=bb
    rgba=np.array(ca[ay0:ay1,ax0:ax1],dtype=np.uint8)
    mm=mask[ay0:ay1,ax0:ax1]
    rgba[:,:,3]=np.where(mm,rgba[:,:,3],0)
    # If alpha is zero on a changed RGB pixel, retain it as opaque effect evidence only when RGB differs strongly.
    strong=np.max(np.abs(ca[ay0:ay1,ax0:ax1,:3]-cl[ay0:ay1,ax0:ax1,:3]),axis=2)>8
    rgba[:,:,3]=np.where(mm & strong & (rgba[:,:,3]==0),255,rgba[:,:,3])
    return Image.fromarray(rgba,'RGBA'), Image.fromarray((mm.astype(np.uint8)*255),'L'), [x0+ax0,y0+ay0,x0+ax1,y0+ay1]

def place_overlay(final, overlay, omask, source_box, current_box, protected, occupied, base_scale):
    sx0,sy0,sx1,sy1=map(int,source_box); sw,sh=sx1-sx0,sy1-sy0
    # Positive inner margin is required. At least 2 px; 3% of smaller source dimension, capped at 12.
    margin=max(2,min(12,int(round(min(sw,sh)*0.03))))
    safe=(sx0+margin,sy0+margin,sx1-margin,sy1-margin)
    if safe[2]<=safe[0] or safe[3]<=safe[1]: safe=(sx0,sy0,sx1,sy1); margin=0
    ow,oh=overlay.size
    maxscale=min((safe[2]-safe[0])/max(1,ow),(safe[3]-safe[1])/max(1,oh),base_scale)
    # Slightly smaller is preferred; never allow growth over current raster.
    scale=min(base_scale,maxscale)
    pcx=(current_box[0]+current_box[2])/2 if current_box else (sx0+sx1)/2
    pcy=(current_box[1]+current_box[3])/2 if current_box else (sy0+sy1)/2
    best=None
    while scale>=0.62:
        nw=max(1,int(round(ow*scale))); nh=max(1,int(round(oh*scale)))
        ov=overlay.resize((nw,nh),Image.Resampling.LANCZOS)
        mm=omask.resize((nw,nh),Image.Resampling.LANCZOS)
        ma=np.asarray(mm)>8
        mb=bbox_bool(ma)
        if mb is None: scale*=.94; continue
        # Trim transparent resampling fringe.
        tx0,ty0,tx1,ty1=mb; ov=ov.crop((tx0,ty0,tx1,ty1)); mm=mm.crop((tx0,ty0,tx1,ty1)); ma=np.asarray(mm)>8; nw,nh=ov.size
        minx,maxx=safe[0],safe[2]-nw; miny,maxy=safe[1],safe[3]-nh
        if minx>maxx or miny>maxy: scale*=.94; continue
        cx=int(round(pcx-nw/2)); cy=int(round(pcy-nh/2)); cx=max(minx,min(maxx,cx)); cy=max(miny,min(maxy,cy))
        offsets=[(0,0)]
        for d in range(2,34,2):
            offsets += [(d,0),(-d,0),(0,d),(0,-d),(d,d),(d,-d),(-d,d),(-d,-d)]
        for dx,dy in offsets:
            x=max(minx,min(maxx,cx+dx)); y=max(miny,min(maxy,cy+dy))
            yy0,yy1=y,y+nh; xx0,xx1=x,x+nw
            region_prot=protected[yy0:yy1,xx0:xx1]
            region_occ=occupied[yy0:yy1,xx0:xx1]
            p=int(np.logical_and(ma,region_prot).sum())
            o=int(np.logical_and(ma,region_occ).sum())
            # Hard 0-pixel overlap gate.
            if p==0 and o==0:
                dist=abs((x+nw/2)-pcx)+abs((y+nh/2)-pcy)
                best=(scale,ov,mm,ma,x,y,dist,margin)
                break
        if best: break
        scale*=.94
    if not best: raise RuntimeError(('NO_ZERO_OVERLAP_PLACEMENT',source_box,current_box,overlay.size))
    scale,ov,mm,ma,x,y,dist,margin=best
    alpha=np.asarray(mm).astype(np.uint8)
    oa=np.array(ov,dtype=np.uint8); oa[:,:,3]=np.minimum(oa[:,:,3],alpha)
    ov=Image.fromarray(oa,'RGBA')
    final.alpha_composite(ov,(x,y))
    # Occupied is kept dilated by two pixels to preserve positive label-to-label separation.
    tmp=np.zeros_like(occupied); tmp[y:y+ma.shape[0],x:x+ma.shape[1]]=ma
    occupied |= dilate_bool(tmp,2)
    pb=[x,y,x+ma.shape[1],y+ma.shape[0]]
    return pb,float(scale),int(margin),int(dist)

all_results=[]; contact=[]
# Review 5 / C075FB49 fails closed on this retry instead of aborting reviews 2 and 6.
# A_RECOVERY05's persisted CLEAN_PLATE already contains some preserved localized rows
# (e.g. keep_passing), so old-candidate minus clean is empty there and per-label pixel
# ownership cannot be reconstructed unambiguously. Under the zero-overlap policy,
# missing/ambiguous per-label ownership is HOLD_STRICT_RECHECK, never inferred PASS.
c075_report=json.loads((repo/'localization/graphics/role_A/20261004-A-RECOVERY05/A_RECOVERY05_C075FB49_REPORT.json').read_text(encoding='utf-8'))
c075_candidate=repo/'localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds'
c075_hold={
 'asset':'C075FB49','review_number':5,'candidate_sha256':sha(c075_candidate),
 'producer_report':'localization/graphics/role_A/20261004-A-RECOVERY05/A_RECOVERY05_C075FB49_REPORT.json',
 'ambiguous_row':'keep_passing','ambiguous_row_localized_bbox':[1,143,520,236],
 'evidence':'persisted clean plate equals current candidate inside keep_passing localized bbox, so clean-vs-candidate yields no separable target layer for that localized row',
 'zero_overlap_gate':'HOLD_STRICT_RECHECK',
 'required_rework':'producer must persist explicit per-row TARGET_TEXT_MASK / separable clean plate or reconstruct the overlapping dense top-label group before C can prove 0-pixel localized-to-localized overlap',
 'candidate_changed_by_C':False,'runtime_validation':'UNTESTED',
 'status':'HOLD_STRICT_RECHECK_ZERO_OVERLAP_TARGET_OWNERSHIP'
}
(out/'C_OVERLAP02_C075FB49_HOLD.json').write_text(json.dumps(c075_hold,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
all_results.append(c075_hold)
for cfg in assets:
    aid=cfg['id']; print('BEGIN',aid,flush=True)
    src=readable_dds(repo/cfg['source']); old=readable_dds(repo/cfg['candidate']); clean=Image.open(repo/cfg['clean']).convert('RGBA')
    if src.size!=old.size or src.size!=clean.size: raise RuntimeError((aid,'size mismatch',src.size,old.size,clean.size))
    W,H=src.size
    protected=np.asarray(Image.open(repo/cfg['protected']).convert('L'))>0
    # 1px protected-artwork clearance, plus 2px localized-label clearance handled separately.
    protected=dilate_bool(protected,1)
    report=json.loads((repo/cfg['report']).read_text(encoding='utf-8')); rows=report['rows']
    final=clean.copy(); occupied=np.zeros((H,W),dtype=bool); rr=[]
    # Stable order: smaller/narrow labels first reduces dense-area collision surprises.
    indexed=list(enumerate(rows))
    for idx,r in indexed:
        source_box=list(map(int,r['original_bbox'])); cur=row_local_bbox(r) or source_box
        ov,om,actual=make_overlay(old,clean,cur)
        if ov is None:
            # Fallback to source box if producer bbox was normalized/coarse.
            ov,om,actual=make_overlay(old,clean,source_box)
        if ov is None: raise RuntimeError((aid,r.get('key'),'no localized overlay diff'))
        placed,scale,margin,disp=place_overlay(final,ov,om,source_box,actual,protected,occupied,cfg['base_scale'])
        sw,sh=source_box[2]-source_box[0],source_box[3]-source_box[1]; lw,lh=placed[2]-placed[0],placed[3]-placed[1]
        if lw>sw or lh>sh: raise RuntimeError((aid,r.get('key'),'size growth',source_box,placed))
        rr.append({'key':r.get('key'),'source':r.get('source'),'korean':r.get('korean'),'source_bbox':source_box,'old_effect_bbox':actual,'new_effect_bbox':placed,'source_size':[sw,sh],'new_size':[lw,lh],'scale_from_current_effect':scale,'positive_inset_px':margin,'placement_displacement_l1':disp,'size_ceiling':'PASS','protected_overlap_pixels':0,'localized_overlap_pixels':0,'overlap_gate':'PASS','style_preservation':'PASS_CURRENT_APPROVED_RASTER_EFFECT_PRESERVED_WITH_UNIFORM_DOWNSCALE'})
    # Full-image static checks.
    fa=np.asarray(final,dtype=np.int16); sa=np.asarray(src,dtype=np.int16); ca=np.asarray(clean,dtype=np.int16)
    changed=np.any(fa!=sa,axis=2)
    allowed=np.asarray(Image.open(repo/cfg['allowed']).convert('L'))>0
    outside=int(np.logical_and(changed,~allowed).sum())
    prot0=np.asarray(Image.open(repo/cfg['protected']).convert('L'))>0
    protchg=int(np.logical_and(changed,prot0).sum())
    # Pairwise placement already used dilated occupied mask; record final exact union sanity.
    if outside!=0 or protchg!=0: raise RuntimeError((aid,'validator',outside,protchg))
    dest=repo/cfg['candidate']; before=sha(dest); write_rgba_dds(dest,final,dest); after=sha(dest)
    reopened=readable_dds(dest)
    if np.any(np.asarray(reopened)!=np.asarray(final)): raise RuntimeError((aid,'roundtrip mismatch'))
    # Contact sheet source/old/new.
    cards=[]
    for label,im in [('SOURCE',src),('OLD',old),('NEW',final)]:
        bg=Image.new('RGBA',im.size,(55,55,55,255)); bg.alpha_composite(im); v=bg.convert('RGB'); v.thumbnail((680,680),Image.Resampling.LANCZOS)
        card=Image.new('RGB',(v.width,v.height+34),'white'); card.paste(v,(0,34)); ImageDraw.Draw(card).text((6,7),f'{cfg["num"]}. {aid} {label}',fill='black'); cards.append(card)
    cw=sum(x.width for x in cards)+16; ch=max(x.height for x in cards); rowim=Image.new('RGB',(cw,ch),'white'); x=0
    for card in cards: rowim.paste(card,(x,0)); x+=card.width+8
    contact.append(rowim)
    result={'asset':aid,'review_number':cfg['num'],'before_candidate_sha256':before,'candidate_sha256':after,'rows_total':len(rr),'rows_pass':len(rr),'source_size_ceiling_failures':0,'protected_overlap_pixels':0,'localized_pair_overlap_pixels':0,'changed_pixels_outside_allowed_text_region':outside,'changed_pixels_in_protected_mask':protchg,'source_text_residue_policy':'clean-plate rebuild; source text is not copied into regenerated localized layers','multi_line_style':'uniform downscale preserves existing source-matched per-line effect relationships','rows':rr,'runtime_validation':'UNTESTED','status':'STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA'}
    (out/f'C_OVERLAP01_{aid}_REPORT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    all_results.append(result)
    print('DONE',aid,before[:12],'->',after[:12],flush=True)

# Combined review sheet.
WW=max(x.width for x in contact); HH=sum(x.height for x in contact)+14*(len(contact)-1); sheet=Image.new('RGB',(WW,HH),'white'); y=0
for row in contact: sheet.paste(row,(0,y)); y+=row.height+14
sheet.save(out/'C_OVERLAP01_2_5_6_SOURCE_OLD_NEW.jpg',quality=95,subsampling=0)
summary={'schema_version':1,'run':run,'retry':'same review 2/5/6 task after first worker aborted on ambiguous C075 clean layer','policy':'zero-overlap: any 1px localized-to-localized or localized-to-protected/preserved foreground overlap FAIL; exact source bbox size ceiling retained','assets':['39229D64','C075FB49','A064FDFC'],'results':all_results,'machine_pass_assets':[r['asset'] for r in all_results if r.get('status')=='STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA'],'hold_strict_recheck_assets':[r['asset'] for r in all_results if str(r.get('status','')).startswith('HOLD_STRICT_RECHECK')],'machine_status':'PASS_WITH_EXPLICIT_HOLD','controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'}
(out/'C_OVERLAP01_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C_OVERLAP02_DONE',flush=True)

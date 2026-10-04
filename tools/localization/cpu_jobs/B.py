#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request, zipfile
from collections import Counter, deque
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter
import numpy as np

if os.environ.get('OUTRUN_CPU_WORKER') != 'github-actions' or os.environ.get('OUTRUN_CPU_ROLE') != 'B':
    raise SystemExit('Run only in GitHub-hosted localization CPU worker as role B.')

repo=Path.cwd(); run='20261004-B-RECOVERY07'
outdir=repo/'localization/graphics/role_B'/run; outdir.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'
candidate=repo/'localization/graphics/hd_candidates'/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/outrun_B_recovery07'); work.mkdir(parents=True,exist_ok=True)
source=work/'B1696633_HD.dds'
source_url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'
source_sha_expected='3c58bf9587d0454e5bb8733bd35c5b2613b11c7fd52c49a428f0fa5fb4cea12d'
zip_orig=repo/'localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip'
zip_draft=repo/'localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip'
translations=[
 ('NAME','이름'),('STATUS','상태'),('Stage','스테이지'),('Next Stage','다음 스테이지'),('Ghost','고스트'),
 ('Total Time','총 시간'),('Slipstream','슬립스트림'),('NEW Record!!','신기록!!'),('Extend Time','시간 연장')]

urllib.request.urlretrieve(source_url,source)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=source_sha_expected: raise RuntimeError('HD source SHA mismatch')

def resolve_font(style):
    pat=f'Noto Sans CJK KR:style={style}'
    try: fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
    except Exception: fp=''
    if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
        subprocess.run(['sudo','apt-get','update','-qq'],check=True)
        subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True)
        fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
    if not fp or not Path(fp).exists(): raise RuntimeError('Noto CJK font unavailable')
    return fp
FONT_BLACK=resolve_font('Black'); FONT_BOLD=resolve_font('Bold')

def load_rgba_dds_bytes(b):
    if b[:4]!=b'DDS ': raise RuntimeError('not DDS')
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]; pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92); pf=struct.unpack_from('<I',b,80)[0]
    if not(fourcc==b'\0\0\0\0' and bpp==32 and pitch==w*4 and mips==1 and len(b)==128+w*h*4):
        raise RuntimeError((h,w,pitch,mips,fourcc,bpp,masks,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000):
        raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
    elif masks==(0xff0000,0xff00,0xff,0xff000000):
        raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','BGRA')
    else:
        raise RuntimeError(('unsupported masks',masks))
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{'width':w,'height':h,'pitch':pitch,'mips':mips,'pf_flags':pf,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}
def load_rgba_dds(p): return load_rgba_dds_bytes(Path(p).read_bytes())
def write_dds(srcp, readable, outp):
    b=Path(srcp).read_bytes(); raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=b[:128]+raw.tobytes('raw','RGBA'); Path(outp).write_bytes(payload); return hashlib.sha256(payload).hexdigest()
def bin_alpha(im): return im.getchannel('A').point(lambda v:255 if v else 0)
def count(m): return int(np.count_nonzero(np.asarray(m,dtype=np.uint8)))
def rectmask(size,boxes):
    m=Image.new('L',size,0); d=ImageDraw.Draw(m)
    for b in boxes: d.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
    return m

def extract_old(z):
    with zipfile.ZipFile(z) as Z: return Z.read(asset_rel)
old_head,old_src,old_info=load_rgba_dds_bytes(extract_old(zip_orig))
_,old_draft,draft_info=load_rgba_dds_bytes(extract_old(zip_draft))
if old_info!=draft_info or (old_info['width'],old_info['height'])!=(512,512): raise RuntimeError('unexpected historical draft structure')
# Historical FULL-DRAFT is discovery-only. Use its changed alpha-visible footprint to identify the nine semantic text regions; no historical Korean pixels are reused.
a=np.asarray(old_src,dtype=np.uint8); b=np.asarray(old_draft,dtype=np.uint8)
visible=(a[:,:,3]>0)|(b[:,:,3]>0)
diff=(np.any(a!=b,axis=2)&visible).astype(np.uint8)*255
diff_img=Image.fromarray(diff,'L').filter(ImageFilter.MaxFilter(13))
mask=np.asarray(diff_img)>0; H,W=mask.shape; seen=np.zeros_like(mask,dtype=bool); boxes=[]
for y in range(H):
    for x in range(W):
        if not mask[y,x] or seen[y,x]: continue
        q=[(x,y)]; seen[y,x]=1; xs=[]; ys=[]
        while q:
            xx,yy=q.pop(); xs.append(xx); ys.append(yy)
            for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
                if 0<=nx<W and 0<=ny<H and mask[ny,nx] and not seen[ny,nx]: seen[ny,nx]=1; q.append((nx,ny))
        if len(xs)>=20: boxes.append([min(xs),min(ys),max(xs)+1,max(ys)+1,len(xs)])
# Merge nearest regions if dilation leaves split multi-word labels. Fail closed if it cannot deterministically reach nine.
def gap_score(A,B):
    ax0,ay0,ax1,ay1,_=A; bx0,by0,bx1,by1,_=B
    dx=max(0,max(ax0,bx0)-min(ax1,bx1)); dy=max(0,max(ay0,by0)-min(ay1,by1))
    xov=max(0,min(ax1,bx1)-max(ax0,bx0)); yov=max(0,min(ay1,by1)-max(ay0,by0))
    # Strongly prefer same-row fragments; then same-column wrapped lines.
    if yov>0: return dx + 0.15*dy
    if xov>0: return 1.5*dy + 0.15*dx
    return dx+dy+50
while len(boxes)>9:
    best=None
    for i in range(len(boxes)):
        for j in range(i+1,len(boxes)):
            s=gap_score(boxes[i],boxes[j])
            if best is None or s<best[0]: best=(s,i,j)
    if best is None or best[0]>45: break
    _,i,j=best; A=boxes[i];B=boxes[j]
    M=[min(A[0],B[0]),min(A[1],B[1]),max(A[2],B[2]),max(A[3],B[3]),A[4]+B[4]]
    boxes=[v for k,v in enumerate(boxes) if k not in (i,j)]+[M]
# If dilation merged vertically stacked one-line labels, split them using the undilated historical diff row gaps.
if len(boxes)<9:
    refined=[]
    for A in boxes:
        x0,y0,x1,y1,_=A
        sub=diff[y0:y1,x0:x1]>0
        active=np.any(sub,axis=1)
        bands=[]; st=None
        for yy,on in enumerate(active):
            if on and st is None: st=yy
            if st is not None and (not on or yy==len(active)-1):
                en=yy if not on else yy+1
                if en-st>=2: bands.append((st,en))
                st=None
        # Only treat clearly separated multiple source/draft rows as independent labels.
        if len(bands)>1:
            for by0,by1 in bands:
                pts=np.argwhere(sub[by0:by1])
                if pts.size==0: continue
                yymin,xxmin=pts.min(axis=0); yymax,xxmax=pts.max(axis=0)
                pad=6
                rx0=max(0,x0+int(xxmin)-pad); ry0=max(0,y0+by0+int(yymin)-pad)
                rx1=min(W,x0+int(xxmax)+1+pad); ry1=min(H,y0+by0+int(yymax)+1+pad)
                refined.append([rx0,ry0,rx1,ry1,int(np.count_nonzero(sub[by0:by1]))])
        else:
            refined.append(A)
    if len(refined)>=len(boxes): boxes=refined
# If the row-gap split creates more than nine fragments, merge nearest same-line fragments deterministically.
while len(boxes)>9:
    best=None
    for i in range(len(boxes)):
        for j in range(i+1,len(boxes)):
            s=gap_score(boxes[i],boxes[j])
            if best is None or s<best[0]: best=(s,i,j)
    if best is None or best[0]>45: break
    _,i,j=best; A=boxes[i];B=boxes[j]
    M=[min(A[0],B[0]),min(A[1],B[1]),max(A[2],B[2]),max(A[3],B[3]),A[4]+B[4]]
    boxes=[v for k,v in enumerate(boxes) if k not in (i,j)]+[M]
if len(boxes)!=9:
    boxes=sorted(boxes,key=lambda r:(r[1]//12,r[0],r[1]))
    # Persist hosted diagnostic evidence rather than guessing a ninth semantic region. This is intermediate evidence only.
    def mark(im,title):
        bg=Image.new('RGBA',im.size,(72,72,72,255)); bg.alpha_composite(im); v=bg.convert('RGB'); d=ImageDraw.Draw(v); f=ImageFont.truetype(FONT_BOLD,14)
        for n,B in enumerate(boxes,1):
            d.rectangle(B[:4],outline=(255,0,255),width=2); d.text((B[0]+2,max(0,B[1]-15)),str(n),font=f,fill=(255,0,255))
        canvas=Image.new('RGB',(v.width,v.height+24),'white'); canvas.paste(v,(0,24)); ImageDraw.Draw(canvas).text((4,2),title,font=f,fill='black'); return canvas
    A=mark(old_src,'HISTORICAL SOURCE / DISCOVERY BOXES'); B=mark(old_draft,'HISTORICAL DRAFT / DISCOVERY BOXES')
    diag=Image.new('RGB',(A.width+B.width+8,max(A.height,B.height)),'white');diag.paste(A,(0,0));diag.paste(B,(A.width+8,0));diag.resize((diag.width*2,diag.height*2)).save(outdir/'B_RECOVERY07_B1696633_DISCOVERY_DIAGNOSTIC.jpg',quality=95)
    (outdir/'B_RECOVERY07_DISCOVERY_DIAGNOSTIC.json').write_text(json.dumps({'status':'PREFLIGHT_DIAGNOSTIC_NEEDS_NINTH_REGION_RESOLUTION','region_count':len(boxes),'regions':[x[:4] for x in boxes],'source_sha256':source_sha_expected,'candidate_written':False},indent=2)+'\n')
    print('B_RECOVERY07_DIAGNOSTIC_ONLY',len(boxes),boxes)
    raise SystemExit(0)
boxes=sorted(boxes,key=lambda r:(r[1]//12,r[0],r[1]))
# Discovery regions are expanded slightly before exact-HD source-alpha measurement.
_,src,info=load_rgba_dds(source); header=Path(source).read_bytes()[:128]
if (info['width'],info['height'])!=(2048,2048): raise RuntimeError(info)
scale=4; hd_regions=[]; source_masks={}; source_bboxes={}; source_alpha=bin_alpha(src)
for (source_text,ko),bb in zip(translations,boxes):
    x0=max(0,bb[0]*scale-20); y0=max(0,bb[1]*scale-20); x1=min(src.width,bb[2]*scale+20); y1=min(src.height,bb[3]*scale+20)
    region=(x0,y0,x1,y1)
    m=Image.new('L',src.size,0); m.paste(source_alpha.crop(region),(x0,y0)); sb=m.getbbox()
    if not sb: raise RuntimeError('empty exact-HD source region '+source_text)
    margins=(sb[0]-x0,sb[1]-y0,x1-sb[2],y1-sb[3])
    if min(margins)<=0: raise RuntimeError(f'HD region clips alpha for {source_text}: region={region} bbox={sb}')
    area=(sb[2]-sb[0])*(sb[3]-sb[1]); density=count(m.crop(sb))/area
    if density>0.72: raise RuntimeError(f'HD region suspiciously dense/non-text for {source_text}: {density}')
    hd_regions.append({'source':source_text,'korean':ko,'historical_discovery_bbox':bb[:4],'search_region':region,'source_bbox':sb,'alpha_density':density})
    source_masks[source_text]=m; source_bboxes[source_text]=sb

source_text_mask=Image.new('L',src.size,0)
for m in source_masks.values(): source_text_mask=ImageChops.lighter(source_text_mask,m)
allowed=rectmask(src.size,list(source_bboxes.values())); protected=ImageChops.invert(allowed)
clean=src.copy(); arr=np.asarray(clean).copy(); sm=np.asarray(source_text_mask)>0; arr[sm]=0; clean=Image.fromarray(arr,'RGBA')

def palette_for(bb):
    crop=src.crop(bb); pix=[p for p in crop.getdata() if p[3]>=160]
    if not pix: return (255,255,255,255),(0,8,57,255)
    common=Counter((r,g,b) for r,g,b,a in pix).most_common(24)
    colors=[c for c,n in common]
    lum=lambda c:0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
    fill=max(colors,key=lum); outline=min(colors,key=lum)
    # Avoid near-black fill from unusual palettes by using brightest frequent source color.
    return (*fill,255),(*outline,255)

def shear(glyph,slant=0.08):
    shift=max(0,int(round(slant*(glyph.height-1)))); out=Image.new('RGBA',(glyph.width+shift,glyph.height),(0,0,0,0))
    for y in range(glyph.height):
        dx=int(round(slant*(glyph.height-1-y))); out.alpha_composite(glyph.crop((0,y,glyph.width,y+1)),(dx,y))
    return out

def render_fit(text,bb,fill,outline):
    x0,y0,x1,y1=bb; W=x1-x0;H=y1-y0; d0=ImageDraw.Draw(Image.new('L',(8,8)))
    maxfs=min(180,max(12,int(H*0.9)))
    for fs in range(maxfs,9,-1):
        font=ImageFont.truetype(FONT_BLACK,fs); sw=max(2,round(fs*0.075)); tb=d0.textbbox((0,0),text,font=font,stroke_width=sw); tw=tb[2]-tb[0];th=tb[3]-tb[1]; pad=sw+4
        g=Image.new('RGBA',(tw+2*pad,th+2*pad),(0,0,0,0)); d=ImageDraw.Draw(g); d.text((pad-tb[0],pad-tb[1]),text,font=font,fill=fill,stroke_width=sw,stroke_fill=outline)
        gb=g.getchannel('A').getbbox(); g=shear(g.crop(gb),0.06)
        if g.width<=W-2 and g.height<=H-2:
            layer=Image.new('RGBA',src.size,(0,0,0,0)); px=x0+(W-g.width)//2;py=y0+(H-g.height)//2;layer.alpha_composite(g,(px,py)); lb=layer.getchannel('A').getbbox()
            if lb and lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1: return layer,fs,sw,lb,fill,outline
    raise RuntimeError('cannot fit '+text+' '+repr(bb))

final=clean.copy(); layers={}; render_meta={}
for row in hd_regions:
    fill,outline=palette_for(row['source_bbox']); layer,fs,sw,lb,fill,outline=render_fit(row['korean'],row['source_bbox'],fill,outline)
    layers[row['source']]=layer; final.alpha_composite(layer); render_meta[row['source']]={'font_size':fs,'stroke_width':sw,'localized_bbox':lb,'fill':fill,'outline':outline}

candidate_sha=write_dds(source,final,candidate)
chead,decoded,cinfo=load_rgba_dds(candidate)
if chead!=header or cinfo!=info or ImageChops.difference(final,decoded).getbbox() is not None: raise RuntimeError('DDS roundtrip mismatch')
# Exhaustive static QA.
target=Image.new('L',src.size,0)
for l in layers.values(): target=ImageChops.lighter(target,bin_alpha(l))
for row in hd_regions:
    ob=row['source_bbox']; lb=render_meta[row['source']]['localized_bbox']
    if not(lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]): raise RuntimeError(('bbox',row['source'],ob,lb))
diff=ImageChops.difference(src,decoded); bands=diff.split(); dm=bands[0]
for z in bands[1:]: dm=ImageChops.lighter(dm,z)
dm=dm.point(lambda v:255 if v else 0)
outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed))); protected_changes=count(ImageChops.multiply(dm,protected))
ad=ImageChops.difference(src.getchannel('A'),decoded.getchannel('A')).point(lambda v:255 if v else 0); alpha_out=count(ImageChops.multiply(ad,ImageChops.invert(allowed)))
cd=ImageChops.difference(src,clean); bands=cd.split(); cm=bands[0]
for z in bands[1:]: cm=ImageChops.lighter(cm,z)
cm=cm.point(lambda v:255 if v else 0); clean_out=count(ImageChops.multiply(cm,ImageChops.invert(source_text_mask))); residue=count(ImageChops.multiply(bin_alpha(clean),source_text_mask))
if any((outside,protected_changes,alpha_out,clean_out,residue)): raise RuntimeError(('static',outside,protected_changes,alpha_out,clean_out,residue))
overlap=[]; ks=list(layers)
for i in range(len(ks)):
    for j in range(i+1,len(ks)):
        n=count(ImageChops.multiply(bin_alpha(layers[ks[i]]),bin_alpha(layers[ks[j]])))
        if n: overlap.append([ks[i],ks[j],n])
if overlap: raise RuntimeError(('overlap',overlap))
# Evidence.
source_text_mask.save(outdir/'B1696633_SOURCE_TEXT_MASK.png'); allowed.save(outdir/'B1696633_ALLOWED_TEXT_REGION_MASK.png'); protected.save(outdir/'B1696633_PROTECTED_MASK.png'); clean.save(outdir/'B1696633_CLEAN_PLATE.png'); target.save(outdir/'B1696633_TARGET_TEXT_MASK.png')
srcpng=work/'source.png';cleanpng=work/'clean.png';finalpng=work/'final.png';src.save(srcpng);clean.save(cleanpng);decoded.save(finalpng)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(cleanpng),str(outdir/'B1696633_SOURCE_TEXT_MASK.png'),'--report',str(outdir/'B_RECOVERY07_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(finalpng),str(outdir/'B1696633_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(outdir/'B1696633_PROTECTED_MASK.png'),'--report',str(outdir/'B_RECOVERY07_FINAL_MASK_VALIDATION.json')],check=True)
# Human QA evidence with numbered source-to-translation mapping.
label_font=ImageFont.truetype(FONT_BOLD,24)
def comp(im,bg): q=Image.new('RGBA',im.size,bg);q.alpha_composite(im);return q.convert('RGB')
def panel(title,im,bg):
    v=comp(im,bg); v.thumbnail((850,850)); c=Image.new('RGB',(v.width,v.height+42),'white');c.paste(v,(0,42));ImageDraw.Draw(c).text((8,5),title,font=label_font,fill='black');return c
cards=[panel('SOURCE',src,(72,72,72,255)),panel('CLEAN',clean,(72,72,72,255)),panel('FINAL',decoded,(72,72,72,255)),panel('FINAL_WHITE',decoded,(255,255,255,255))]
W=cards[0].width+cards[1].width+10;H=cards[0].height+cards[2].height+10;sheet=Image.new('RGB',(W,H),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+10,0));sheet.paste(cards[2],(0,cards[0].height+10));sheet.paste(cards[3],(cards[2].width+10,cards[1].height+10));sheet.save(outdir/'B_RECOVERY07_B1696633_COMPARE.jpg',quality=94)
# Row-contact crops: source and final side by side per mapped element.
rows=[]
for n,row in enumerate(hd_regions,1):
    ob=row['source_bbox']; pad=20; cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.width,ob[2]+pad),min(src.height,ob[3]+pad))
    s=comp(src,(72,72,72,255)).crop(cr); f=comp(decoded,(72,72,72,255)).crop(cr); scale=min(1.0,760/max(1,s.width));
    if scale<1: s=s.resize((round(s.width*scale),round(s.height*scale)));f=f.resize(s.size)
    h=max(s.height,f.height)+38; card=Image.new('RGB',(s.width+f.width+10,h),'white');card.paste(s,(0,38));card.paste(f,(s.width+10,38));ImageDraw.Draw(card).text((5,4),f'{n}. {row["source"]} -> {row["korean"]}',font=label_font,fill='black');rows.append(card)
RW=max(x.width for x in rows); RH=sum(x.height for x in rows)+8*(len(rows)-1); contact=Image.new('RGB',(RW,RH),'white'); yy=0
for card in rows: contact.paste(card,(0,yy)); yy+=card.height+8
contact.save(outdir/'B_RECOVERY07_B1696633_ROW_CONTACT.jpg',quality=95)
raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rc1=panel('SOURCE_RAW',raws,(72,72,72,255));rc2=panel('FINAL_RAW',rawf,(72,72,72,255));rs=Image.new('RGB',(rc1.width+rc2.width+10,max(rc1.height,rc2.height)),'white');rs.paste(rc1,(0,0));rs.paste(rc2,(rc1.width+10,0));rs.save(outdir/'B_RECOVERY07_B1696633_RAW_COMPARE.jpg',quality=92)

rowsrep=[]
for row in hd_regions:
    ob=list(row['source_bbox']); rm=render_meta[row['source']]; lb=list(rm['localized_bbox'])
    rowsrep.append({'source':row['source'],'korean':row['korean'],'historical_discovery_bbox':row['historical_discovery_bbox'],'original_bbox':ob,'localized_bbox':lb,'delta_left':lb[0]-ob[0],'delta_right':ob[2]-lb[2],'delta_top':lb[1]-ob[1],'delta_bottom':ob[3]-lb[3],'containment':'PASS','rework_status':'NEW_CANDIDATE','native_font_size':rm['font_size'],'stroke_width':rm['stroke_width'],'sampled_fill_rgba':rm['fill'],'sampled_outline_rgba':rm['outline'],'alpha_density':row['alpha_density'],'historical_localized_raster_reused':False})
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':48,'asset':asset_rel,'readiness_tier':'ONE_STAGE_TO_RENDER','source_upstream_repo':'Sonic-TV/OR2006Sprites','source_upstream_commit':'a95efe01d1f136514cef94b0d9e9fd61df021754','source_url':source_url,'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'candidate_path':str(candidate.relative_to(repo)),'construction_note':'historical low-res FULL-DRAFT used only as placement discovery; all final pixels rebuilt from exact pinned HD source; no historical localized raster reuse or upscale','mapping_order':[{'source':a,'korean':b} for a,b in translations],'historical_discovery_boxes':[x[:4] for x in boxes],'structure':{**info,'header_128_exact':True,'raw_orientation':'mirror_y','channel_layout':'RGBA masks preserved'},'segments_total':9,'segments_rendered':9,'clean_plate':{'changed_pixels_outside_source_text_mask':clean_out,'source_text_residue_pixels':residue,'status':'PASS'},'containment':{'elements_total':9,'elements_pass':9,'elements_fail':0,'changed_pixels_outside_permitted_source_bboxes':outside,'alpha_changed_outside_permitted_source_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':overlap,'status':'PASS'},'rows':rowsrep,'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY07_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(outdir/'B_RECOVERY07_B1696633_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(outdir/'B_RECOVERY07_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'historical_discovery_region_count':len(boxes),'bbox_pass':'9/9','clean_plate_residue_pixels':residue,'outside_permitted_bboxes':outside,'alpha_outside_permitted_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':0,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_RECOVERY07_DONE',candidate_sha,'bbox=9/9','boxes',boxes)

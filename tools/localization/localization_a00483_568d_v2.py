from __future__ import annotations
import os, io, json, math, hashlib, struct
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
import numpy as np

TASK_ID='LOCALIZATION-LOCALIZATION_A-00483'
ASSET='568D3696'
QUEUE_INDEX=53
EXPECTED_SOURCE_SHA='65bc5e88e7b01f8148bcbbb2dc4b2225bf53c8501801e329c51ecb274e8cd813'
EXPECTED_FONT_SHA='61fd37816a1ee1a9336876742392d80bdafd340e5124a088aeda20446e2e15de'
EXPECTED_CANDIDATE_SHA='25600c9081b311fcc887dc146bd28dfc5dd8d3627de9a516d94a872f15668b64'
SOURCE=Path(os.environ.get('SOURCE_OVERRIDE','localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds'))
CAND=Path(os.environ.get('CANDIDATE_OVERRIDE','localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds'))
REPORT_DIR=Path(os.environ.get('REPORT_DIR_OVERRIDE',f'localization/graphics/role_A/{TASK_ID}'))
REPORT=REPORT_DIR/f'{TASK_ID}_568D3696_SELF_QA.json'
COMPARE=REPORT_DIR/'568D3696_english_vs_korean.png'
CLEAN_PROOF=REPORT_DIR/'568D3696_clean_plate_proof.png'
FONT=Path('/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf')

ROWS=[
 dict(key='r1',source='Hit the zippers!',korean='지퍼를 맞히세요!',cell=(3100,8,3628,112),source_bbox=(3117,16,3613,109)),
 dict(key='r2',source='Hit the cars!',korean='차를 맞히세요!',cell=(545,2056,974,2160),source_bbox=(556,2068,962,2144)),
 dict(key='r3',source='Dodge the bombs!',korean='폭탄을 피하세요!',cell=(1140,2054,1775,2165),source_bbox=(1147,2061,1760,2165)),
 dict(key='r4',source='Feed the girl!',korean='여자친구에게 먹여 주세요!',cell=(1988,2053,2445,2164),source_bbox=(1998,2061,2433,2160)),
 dict(key='r5',source='Avoid abduction!',korean='납치를 피하세요!',cell=(2826,2064,3410,2165),source_bbox=(2839,2073,3396,2156)),
 dict(key='r6',source='Avoid the meteors!',korean='운석을 피하세요!',cell=(1695,2298,2330,2398),source_bbox=(1703,2302,2327,2398)),
 dict(key='r7',source='Dribble the beach ball!',korean='비치볼을 드리블하세요!',cell=(2328,2298,3080,2400),source_bbox=(2334,2312,3067,2388)),
 dict(key='r8',source='Photograph the sights!',korean='명소를 촬영하세요!',cell=(3160,2298,3700,2490),source_bbox=(3172,2313,3685,2474),layout='명소를\n촬영하세요!'),
 dict(key='r9',source='Hit the ducks!',korean='오리를 맞히세요!',cell=(3090,3200,3570,3294),source_bbox=(3101,3212,3558,3288)),
 dict(key='r10',source='See the sights!',korean='명소를 구경하세요!',cell=(2968,3296,3510,3395),source_bbox=(2998,3299,3494,3392)),
 dict(key='r11',source='END',korean='종료',cell=(920,2548,1510,2818),source_bbox=(945,2567,1487,2793),family='end'),
 dict(key='r12',source='ANSWER',korean='정답',cell=(2120,2548,3255,2820),source_bbox=(2158,2566,3216,2796),family='answer'),
 dict(key='r13',source='QUESTION',korean='문제',cell=(748,2880,2070,3180),source_bbox=(779,2907,2039,3160),family='question'),
 dict(key='r14',source='START',korean='시작',cell=(2570,2880,3490,3180),source_bbox=(2607,2913,3455,3143),family='start'),
]

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def u32(b:bytes,o:int)->int:return struct.unpack_from('<I',b,o)[0]
def layout(b:bytes):
    w0,h0,mips=u32(b,16),u32(b,12),u32(b,28); out=[]; off=128
    for level in range(mips):
        w=max(1,w0>>level);h=max(1,h0>>level);bx=max(1,(w+3)//4);by=max(1,(h+3)//4);sz=bx*by*16
        out.append((level,w,h,bx,by,off,sz));off+=sz
    if off!=len(b):raise SystemExit(f'DDS payload mismatch {off} != {len(b)}')
    return out

def decode_mip(b:bytes,level:int)->Image.Image:
    l=layout(b)[level];_,w,h,bx,by,off,sz=l; hdr=bytearray(b[:128]);struct.pack_into('<I',hdr,12,h);struct.pack_into('<I',hdr,16,w);struct.pack_into('<I',hdr,20,sz);struct.pack_into('<I',hdr,28,1)
    return Image.open(io.BytesIO(bytes(hdr)+b[off:off+sz])).convert('RGBA')

def encode_dxt5_payload(im:Image.Image)->bytes:
    bio=io.BytesIO();im.save(bio,format='DDS',pixel_format='DXT5');out=bio.getvalue()
    if out[:4]!=b'DDS ':raise SystemExit('Pillow DXT5 encoder failed')
    return out[128:]

def inset(bb,n):return (bb[0]+n,bb[1]+n,bb[2]-n,bb[3]-n)

def text_dimensions(lines,font,outer,spacing):
    d=ImageDraw.Draw(Image.new('L',(4,4),0)); dims=[]
    for line in lines:
        bb=d.textbbox((0,0),line,font=font,stroke_width=outer);dims.append((bb,bb[2]-bb[0],bb[3]-bb[1]))
    return dims,max(x[1] for x in dims),sum(x[2] for x in dims)+spacing*(len(lines)-1)

def make_overlay(text:str,box:tuple[int,int,int,int],family:str,target_size:int):
    cw,ch=box[2]-box[0],box[3]-box[1]; lines=text.split('\n'); size=target_size
    while size>=18:
        font=ImageFont.truetype(str(FONT),size)
        if family=='mission':outer,inner,spacing=7,4,max(4,round(size*.18));glow=0
        else:outer,inner,spacing=max(12,round(size*.075)),max(7,round(size*.045)),max(4,round(size*.1));glow=max(0,round(size*.035))
        dims,maxw,totalh=text_dimensions(lines,font,outer,spacing)
        if maxw+glow*2<=cw and totalh+glow*2<=ch:break
        size-=1
    if size<18:raise SystemExit(f'fit failure {text} {box}')
    layer=Image.new('RGBA',(cw,ch),(0,0,0,0));dims,maxw,totalh=text_dimensions(lines,font,outer,spacing);y=(ch-totalh)/2;poses=[]
    for line,(bb,tw,th) in zip(lines,dims):
        x=(cw-tw)/2-bb[0];ty=y-bb[1];poses.append((line,x,ty));y+=th+spacing
    if family=='mission':
        d=ImageDraw.Draw(layer)
        for line,x,ty in poses:
            d.text((x,ty),line,font=font,fill=(255,195,30,255),stroke_width=outer,stroke_fill=(245,245,245,255))
            d.text((x,ty),line,font=font,fill=(255,195,30,255),stroke_width=inner,stroke_fill=(3,22,70,255))
        mask=Image.new('L',(cw,ch),0);md=ImageDraw.Draw(mask)
        for line,x,ty in poses:md.text((x,ty),line,font=font,fill=255)
        ga=np.zeros((ch,cw,4),dtype=np.uint8);top=(255,226,60);bot=(255,166,12)
        for yy in range(ch):
            t=yy/max(1,ch-1)
            for cc in range(3):ga[yy,:,cc]=int(top[cc]*(1-t)+bot[cc]*t)
            ga[yy,:,3]=255
        layer.alpha_composite(Image.composite(Image.fromarray(ga,'RGBA'),Image.new('RGBA',(cw,ch)),mask))
    else:
        fill,inn,out={'end':((245,45,45),(135,0,0),(255,210,210)),'answer':((255,210,25),(100,75,0),(255,245,150)),'question':((70,165,255),(0,42,125),(180,225,255)),'start':((45,205,70),(0,95,35),(175,255,185))}[family]
        omask=Image.new('L',(cw,ch),0);od=ImageDraw.Draw(omask)
        for line,x,ty in poses:od.text((x,ty),line,font=font,fill=255,stroke_width=outer,stroke_fill=255)
        blur=omask.filter(ImageFilter.GaussianBlur(glow));gl=Image.new('RGBA',(cw,ch),out+(0,));gl.putalpha(blur.point(lambda p:int(p*.5)));layer.alpha_composite(gl)
        d=ImageDraw.Draw(layer)
        for line,x,ty in poses:
            d.text((x,ty),line,font=font,fill=fill+(255,),stroke_width=outer,stroke_fill=out+(255,));d.text((x,ty),line,font=font,fill=fill+(255,),stroke_width=inner,stroke_fill=inn+(255,))
        mask=Image.new('L',(cw,ch),0);md=ImageDraw.Draw(mask)
        for line,x,ty in poses:md.text((x,ty),line,font=font,fill=255)
        top=tuple(min(255,c+45) for c in fill);bot=tuple(max(0,c-35) for c in fill);ga=np.zeros((ch,cw,4),dtype=np.uint8)
        for yy in range(ch):
            t=yy/max(1,ch-1)
            for cc in range(3):ga[yy,:,cc]=int(top[cc]*(1-t)+bot[cc]*t)
            ga[yy,:,3]=255
        layer.alpha_composite(Image.composite(Image.fromarray(ga,'RGBA'),Image.new('RGBA',(cw,ch)),mask))
    return layer,size,(outer,inner,spacing),layer.getchannel('A').getbbox()

def make_sheet(a,b,left,right,path):
    panels=[]
    for r in ROWS:
        s=a.crop(r['cell']);c=b.crop(r['cell']);scale=min(1,600/max(s.width,1))
        if scale<1:
            sz=(round(s.width*scale),round(s.height*scale));s=s.resize(sz,Image.Resampling.LANCZOS);c=c.resize(sz,Image.Resampling.LANCZOS)
        panels.append((r['key'],s,c))
    W=max(x[1].width for x in panels)*2+100;H=sum(max(x[1].height,x[2].height)+28 for x in panels)+40;sheet=Image.new('RGBA',(W,H),(28,28,28,255));d=ImageDraw.Draw(sheet);d.text((20,8),left,fill='white');d.text((W//2+20,8),right,fill='white');y=32
    for k,s,c in panels:d.text((2,y),k,fill='white');sheet.alpha_composite(s,(30,y));sheet.alpha_composite(c,(W//2+30,y));y+=max(s.height,c.height)+28
    path.parent.mkdir(parents=True,exist_ok=True);sheet.save(path,optimize=True)

def build_dds(source:bytes,target:Image.Image,mask_img:Image.Image):
    out=bytearray(source);ls=layout(source);stats=[]
    for level,w,h,bx,by,off,sz in ls:
        src_read=ImageOps.flip(decode_mip(source,level))
        if level==0:tgt,m=target,mask_img
        else:tgt=target.resize((w,h),Image.Resampling.LANCZOS);m=mask_img.resize((w,h),Image.Resampling.BOX).point(lambda p:255 if p>0 else 0)
        comp=src_read.copy();comp.paste(tgt,(0,0),m);payload=encode_dxt5_payload(ImageOps.flip(comp));ma=np.array(ImageOps.flip(m))>0;sel=chg=0
        for yy in range(by):
            y0=yy*4;y1=min(h,y0+4)
            for xx in range(bx):
                x0=xx*4;x1=min(w,x0+4)
                if ma[y0:y1,x0:x1].any():
                    sel+=1;idx=yy*bx+xx;a=off+idx*16;new=payload[idx*16:(idx+1)*16]
                    if out[a:a+16]!=new:out[a:a+16]=new;chg+=1
        stats.append({'level':level,'width':w,'height':h,'selected_blocks':sel,'changed_blocks':chg})
    return bytes(out),stats

def main():
    source=SOURCE.read_bytes()
    if sha(source)!=EXPECTED_SOURCE_SHA:raise SystemExit(f'source SHA mismatch {sha(source)}')
    if source[:4]!=b'DDS ' or u32(source,16)!=4096 or u32(source,12)!=4096 or source[84:88]!=b'DXT5' or u32(source,28)!=13:raise SystemExit('source DDS identity mismatch')
    if sha(FONT.read_bytes())!=EXPECTED_FONT_SHA:raise SystemExit(f'font SHA mismatch {sha(FONT.read_bytes())}')
    src=ImageOps.flip(decode_mip(source,0));arr=np.array(src);H,W=arr.shape[:2];sem=np.zeros((H,W),dtype=bool)
    for r in ROWS:
        x0,y0,x1,y1=r['source_bbox'];crop=arr[y0:y1,x0:x1];alpha=crop[...,3]>4
        if int(r['key'][1:])<=10:
            rgb=crop[...,:3].astype(np.int16);green=(rgb[...,1]>rgb[...,0]+12)&(rgb[...,1]>=rgb[...,2]-10)&(rgb[...,0]<140);sel=alpha&~green
        else:sel=alpha
        sem[y0:y1,x0:x1]=sel
    clean_arr=arr.copy();clean_arr[sem]=0;clean=Image.fromarray(clean_arr,'RGBA');cand=clean.copy();overlay=np.zeros_like(sem);meta={}
    for r in ROWS:
        n=int(r['key'][1:]);text=r.get('layout',r['korean']);safe=inset(r['source_bbox'],2);render=inset(r['source_bbox'],6 if n<=10 else 14);family=r.get('family','mission');target=60 if n<=10 else 200;ov,size,style,ab=make_overlay(text,render,family,target);cand.alpha_composite(ov,(render[0],render[1]));overlay[render[1]:render[3],render[0]:render[2]]|=np.array(ov.getchannel('A'))>0;meta[r['key']]={'actual_font_size':size,'family_target_font_size':target,'candidate_safe_bbox':list(safe),'render_inset_bbox':list(render),'text_layout':text,'source_effect_bbox':list(r['source_bbox'])}
    clean_diff=np.any(np.array(clean)!=arr,axis=2)
    if not np.array_equal(clean_diff,sem):raise SystemExit('clean plate changed pixels outside semantic mask')
    edit=sem|overlay;edit_img=Image.fromarray((edit*255).astype(np.uint8),'L');candidate,levels=build_dds(source,cand,edit_img);clean_same,_=build_dds(source,clean,edit_img)
    cand_sha=sha(candidate)
    if cand_sha!=EXPECTED_CANDIDATE_SHA:raise SystemExit(f'candidate SHA drift {cand_sha} != {EXPECTED_CANDIDATE_SHA}')
    if candidate[:128]!=source[:128] or len(candidate)!=len(source):raise SystemExit('DDS header/size drift')
    decoded=ImageOps.flip(decode_mip(candidate,0));decoded_clean=ImageOps.flip(decode_mip(clean_same,0));d=np.array(decoded);c=np.array(decoded_clean);row_reports=[]
    for r in ROWS:
        x0,y0,x1,y1=r['cell'];diff=np.any(d[y0:y1,x0:x1]!=c[y0:y1,x0:x1],axis=2);loc=diff&(d[y0:y1,x0:x1,3]>0);ys,xs=np.where(loc)
        if not len(xs):raise SystemExit(f"{r['key']} no localized pixels")
        bb=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max()+1),y0+int(ys.max()+1)];safe=meta[r['key']]['candidate_safe_bbox'];ok=bb[0]>=safe[0] and bb[1]>=safe[1] and bb[2]<=safe[2] and bb[3]<=safe[3]
        if not ok:raise SystemExit(f"{r['key']} zero-pixel containment fail {bb} !<= {safe}")
        srcbb=meta[r['key']]['source_effect_bbox'];row_reports.append({'key':r['key'],'source':r['source'],'korean':r['korean'],'text_layout':meta[r['key']]['text_layout'],'sprite_cell':list(r['cell']),'source_effect_bbox':srcbb,'candidate_safe_bbox':safe,'render_inset_bbox':meta[r['key']]['render_inset_bbox'],'decoded_localized_bbox':bb,'delta_left':bb[0]-srcbb[0],'delta_top':bb[1]-srcbb[1],'delta_right':bb[2]-srcbb[2],'delta_bottom':bb[3]-srcbb[3],'containment':'PASS','family_target_font_size':meta[r['key']]['family_target_font_size'],'actual_font_size':meta[r['key']]['actual_font_size'],'fit_reduction_px':meta[r['key']]['family_target_font_size']-meta[r['key']]['actual_font_size'],'font_family':'NanumSquareRound Bold'})
    REPORT_DIR.mkdir(parents=True,exist_ok=True);CAND.parent.mkdir(parents=True,exist_ok=True);CAND.write_bytes(candidate);make_sheet(src,decoded,'ENGLISH SOURCE','KOREAN CANDIDATE (DECODED DDS)',COMPARE);make_sheet(src,clean,'ENGLISH SOURCE','VERIFIED CLEAN PLATE',CLEAN_PROOF)
    report={'schema_version':2,'task_id':TASK_ID,'lane':'LOCALIZATION_A','role':'A','queue_index':QUEUE_INDEX,'asset':ASSET,'path':'textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds','result':'SELF_QA_PASS_PENDING_C','automation_validation':'PENDING','validation_mode':'C_BATCH_GATE','runtime_validation':'UNTESTED','generation_lineage':{'mode':'POST_RESET_EXACT_ENGLISH_SOURCE_RECONSTRUCTION','canonical_source_transport':'GITHUB_EXACT_CANONICAL_BLOB_ALREADY_PRESENT','source_sha256':EXPECTED_SOURCE_SHA,'source_git_blob_sha':'3d6bedf9c66d6c43c4ca16483a0f447137b39c3a','prior_korean_candidate_pixels_used':False,'fresh_lettering':'deterministic NanumSquareRound Bold render from canonical translations','font_sha256':EXPECTED_FONT_SHA},'clean_plate_qa':{'semantic_removed_pixels':int(sem.sum()),'changes_outside_semantic_removal_mask':0,'alpha_changes_outside_semantic_removal_mask':0,'source_language_residue_visual_review':'PASS_BY_PINNED_OUTPUT_IDENTITY','protected_artwork_visual_review':'PASS_BY_PINNED_OUTPUT_IDENTITY'},'candidate':{'sha256':cand_sha,'bytes':len(candidate),'header_128_exact_source':True,'dds':{'width':4096,'height':4096,'mips':13,'fourcc':'DXT5','bytes':len(candidate)},'changed_bytes_vs_source':sum(a!=bb for a,bb in zip(source,candidate)),'mip_generation':'all 13 mips rebuilt from exact English source mip + fresh localized edit mask; no prior Korean mip payload reused','changed_blocks_total':sum(x['changed_blocks'] for x in levels),'levels':levels},'rows':row_reports,'comparison':{'english_left_korean_right':str(COMPARE),'clean_plate_proof':str(CLEAN_PROOF),'same_crop_zoom_orientation':True,'decoded_dds_review':'PASS_BY_PINNED_OUTPUT_IDENTITY','english_residue':'NONE_OBSERVED','clipping':'NONE_OBSERVED','opaque_boxes':'NONE_OBSERVED','protected_artwork_intrusion':'NONE_OBSERVED'},'notes':['A shard is odd under current controller_roles schema.','Index 53 is odd and current DIRECT_REWORK_REQUIRED generation-reset work.','Output identity is pinned to the manually reviewed candidate SHA.','RUNTIME_VALIDATION=UNTESTED because no real-game test was performed.']}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':report['result'],'candidate_sha256':cand_sha,'report':str(REPORT),'comparison':str(COMPARE)},ensure_ascii=False))

if __name__=='__main__':main()

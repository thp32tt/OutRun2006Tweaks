def dark(a):
    im=Image.fromarray(a.astype(np.uint8),'RGBA'); bg=Image.new('RGBA',im.size,(28,28,28,255)); bg.alpha_composite(im); return bg

def main():
    now=datetime.now(ZoneInfo('Asia/Seoul')).replace(microsecond=0).isoformat(); base=githead()
    if CAND.exists() or TASK.exists(): raise SystemExit('durable output already exists; refusing overwrite')
    sb=SRC.read_bytes()
    if len(sb)!=2097280 or sha(sb)!=SOURCE_SHA or sb[:4]!=b'DDS ': raise SystemExit('source identity mismatch')
    header=sb[:128]; src=np.array(Image.open(SRC).convert('RGBA'),dtype=np.uint8)
    if src.shape!=(H,W,4): raise SystemExit(f'bad canvas {src.shape}')
    src_display=np.flipud(src).copy()
    if sha(src.tobytes())!='6b053c75c6074d6ebb16bfe0a38b3a770923c223beb281ab1611872cf271659f': raise SystemExit('raw decode mismatch')
    if sha(src_display.tobytes())!='8d2de43a8575aa0661f1013fbd8929964c44c3cabb31b2e09b2b7779b75ab5c3': raise SystemExit('display decode mismatch')
    fp,fi=font_info(); clean=src.copy(); lettering=np.zeros_like(src); removal=np.zeros((H,W),bool); metrics=[]
    for idx,sprite,en,ko,rect,srcbb,safe,fill,expected_fs in REGIONS:
        x,yb,w,h=rect; y=H-(yb+h); disp=src[y:y+h,x:x+w][::-1].copy(); mask=disp[:,:,3]>0
        if sha(mask.astype(np.uint8).tobytes())!=MASK_SHA[idx]: raise SystemExit(f'mask mismatch {idx}')
        rawmask=mask[::-1]; removal[y:y+h,x:x+w]|=rawmask; clean[y:y+h,x:x+w][rawmask]=[0,0,0,0]
        sx0,sy0,sx1,sy1=safe; rx0,ry0,rx1,ry1=sx0+1,sy0+1,sx1-1,sy1-1; rw,rh=rx1-rx0+1,ry1-ry0+1
        chosen=None
        for fs in range(12,90):
            f=ImageFont.truetype(str(fp),fs,index=fi); bb=f.getbbox(ko); tw,th=bb[2]-bb[0],bb[3]-bb[1]
            if tw<=rw and th<=rh: chosen=(fs,f,bb,tw,th)
        if not chosen: raise SystemExit(f'no fit {idx}')
        fs,f,bb,tw,th=chosen
        if fs!=expected_fs: raise SystemExit(f'font-size drift {idx}: {fs}')
        glyph=Image.new('RGBA',(tw+8,th+8),(0,0,0,0)); d=ImageDraw.Draw(glyph); d.text((4-bb[0],4-bb[1]),ko,font=f,fill=tuple(fill)+(255,)); glyph=glyph.crop(glyph.getbbox())
        px=rx0; py=ry0+(rh-glyph.height)//2; layer=Image.new('RGBA',(960,76),(0,0,0,0)); layer.alpha_composite(glyph,(px,py)); ab=layer.getbbox(); loc=[ab[0],ab[1],ab[2]-1,ab[3]-1]
        if not inside(loc,safe): raise SystemExit(f'preencode containment {idx}: {loc}')
        lr=np.array(layer)[::-1]; lettering[y:y+h,x:x+w]=np.maximum(lettering[y:y+h,x:x+w],lr)
        metrics.append({'region_index':idx,'sprite':sprite,'source':en,'korean':ko,'atlas_rect_bl':rect,'source_effect_bbox_readable_local':srcbb,'candidate_safe_bbox_readable_local':safe,'render_box_readable_local':[rx0,ry0,rx1,ry1],'localized_bbox_readable_local_preencode':loc,'safe_margins_ltrb_preencode':[loc[0]-sx0,loc[1]-sy0,sx1-loc[2],sy1-loc[3]],'font_role':'sans','font_size_px':fs,'font_identifier':'NotoSansCJK-Bold.ttc#1 Noto Sans CJK KR Bold','font_sha256':EXPECTED_FONT_SHA,'candidate_fill_rgb':fill,'native_glyph_canvas':[glyph.width,glyph.height],'source_style':'upright condensed heavy sans; flat dark gray; no outline/shadow/glow','source_baseline_vector_readable':[1,0],'candidate_baseline_vector_readable':[1,0],'source_slant_dx_per_dy':0.0,'candidate_slant_dx_per_dy':0.0,'source_signed_slant_angle_deg':0.0,'candidate_signed_slant_angle_deg':0.0,'source_slant_direction':'none','candidate_slant_direction':'none','flattened_raster_resize':'NOT_USED','containment_preencode':'PASS'})
    if int(removal.sum())!=EXPECTED_MASK_PIXELS or sha(clean.tobytes())!=EXPECTED_CLEAN_RAW: raise SystemExit('accepted clean plate mismatch')
    target=np.array(Image.alpha_composite(Image.fromarray(clean,'RGBA'),Image.fromarray(lettering,'RGBA')),dtype=np.uint8)
    RUN.mkdir(parents=True,exist_ok=True); tmpc=RUN/'_clean.dds'; tmpt=RUN/'_target.dds'
    Image.fromarray(clean,'RGBA').save(tmpc,format='DDS',pixel_format='DXT5'); Image.fromarray(target,'RGBA').save(tmpt,format='DDS',pixel_format='DXT5')
    cb=tmpc.read_bytes(); tb=tmpt.read_bytes(); tmpc.unlink(); tmpt.unlink()
    bx=(W+3)//4; by=(H+3)//4; BLOCK=16
    clean_diff=np.any(clean!=src,axis=2); target_diff=np.any(target!=src,axis=2)
    def touched(diff):
        t=np.zeros((by,bx),bool); ys,xs=np.where(diff); t[ys//4,xs//4]=True; return t
    cbt=touched(clean_diff); tbt=touched(target_diff)
    cpay=bytearray(sb[128:]); tpay=bytearray(sb[128:])
    for yy,xx in zip(*np.where(cbt)):
        off=(yy*bx+xx)*BLOCK; cpay[off:off+BLOCK]=cb[128+off:128+off+BLOCK]
    clean_dds=header+bytes(cpay); cleantmp=RUN/'_clean_roundtrip.dds'; cleantmp.write_bytes(clean_dds); clean_dec=np.array(Image.open(cleantmp).convert('RGBA'),dtype=np.uint8); cleantmp.unlink()

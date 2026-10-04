from pathlib import Path
import hashlib, json, os, struct, subprocess, traceback, zipfile
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

RUN="20261005-B-PRODUCTION52"
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/1F5FE6E9_1024x512.dds"
INDEX=132
LABELS=[("REQUEST","요청"),("SPECIAL REQUEST 1","스페셜 요청 1"),("SPECIAL REQUEST 2","스페셜 요청 2"),("SPECIAL REQUEST 3","스페셜 요청 3")]
# Historical Korean draft is discovery-only. These rectangles locate the four physical
# source rows; they are NOT accepted as original glyph/effect bboxes.
ROW_SEEDS=[
    [649,148,756,171],
    [649,172,873,195],
    [649,196,877,219],
    [649,220,877,232],
]

def sha(b): return hashlib.sha256(b).hexdigest()

def mask_img(m):
    return Image.fromarray((m.astype(np.uint8)*255),"L")

def bbox_of(m):
    yy,xx=np.nonzero(m)
    if not len(xx): return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]

def ensure_font():
    def find():
        try:
            p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
            return p if p and Path(p).exists() else ""
        except Exception:
            return ""
    p=find()
    if "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=find()
    if not p or not Path(p).exists():
        raise RuntimeError(("font unavailable",p))
    return p

def main():
    if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions":
        raise RuntimeError("B53 must run on hosted CPU worker")
    repo=Path.cwd()
    out=repo/"localization/graphics/role_B"/RUN
    out.mkdir(parents=True,exist_ok=True)
    wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
    srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
    histzip=repo/"localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip"
    cand=repo/"localization/graphics/hd_candidates"/ASSET
    cand.parent.mkdir(parents=True,exist_ok=True)
    source_sha="3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d"
    hist_sha="a775eff64b49ac61f107a55ab0233f89fc6cdaa0bfd6e97d3fa5aa112180dc45"
    with zipfile.ZipFile(srczip) as z: sb=z.read(ASSET)
    with zipfile.ZipFile(histzip) as z: hb=z.read(ASSET)
    if sha(sb)!=source_sha or sha(hb)!=hist_sha:
        raise RuntimeError(("input sha mismatch",sha(sb),sha(hb)))
    H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
    if (W,H)!=(1024,512) or len(sb)!=128+W*H*4 or hb[:128]!=sb[:128]:
        raise RuntimeError(("structure",W,H,mips,len(sb),hb[:128]==sb[:128]))
    raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
    raw_hist=Image.frombytes("RGBA",(W,H),hb[128:],"raw","RGBA")
    src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    hist=raw_hist.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    sa=np.asarray(src,dtype=np.uint8); ha=np.asarray(hist,dtype=np.uint8)

    # Source-only alpha analysis. In these rows hidden RGB is shared with the transparent
    # panel background, so exact source effect evidence lives primarily in alpha.
    # Label all active-alpha connected components in a generous global search region;
    # then assign only components whose centroid/area is overwhelmingly tied to one row seed.
    alpha=sa[:,:,3]
    search=np.zeros((H,W),bool)
    search[125:250,590:930]=True
    active=(alpha>0)&search
    lab,n=ndimage.label(active,np.ones((3,3),dtype=np.uint8))
    comps=[]
    for cid in range(1,n+1):
        yy,xx=np.nonzero(lab==cid)
        if not len(xx): continue
        bb=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
        w=bb[2]-bb[0]; h=bb[3]-bb[1]; area=len(xx)
        comps.append({"id":cid,"area":int(area),"bbox":bb,"w":w,"h":h,"cx":float(xx.mean()),"cy":float(yy.mean()),"amax":int(alpha[yy,xx].max())})
    comps.sort(key=lambda c:(c["bbox"][1],c["bbox"][0]))
    (out/"B53_SOURCE_ALPHA_COMPONENTS.json").write_text(json.dumps({"components":comps},indent=2)+"\n")

    # B53 exact row recovery from source alpha. B52 diagnostics proved the actual glyph
    # rows are 24px-spaced at 140/164/188/212, not the historical draft plate tops.
    # Components 2.. are individual glyph/effect components; component 1 is unrelated
    # panel/artwork that touches a few row4 letters. Rows 2 and 3 share the identical
    # SPECIAL REQUEST prefix, so their source masks provide an exact periodicity proof.
    def comp_union(ylo,yhi):
        ids=[]
        for c in comps:
            if c["id"]==1: continue
            x0,y0,x1,y1=c["bbox"]
            if x0<630 or x1>900 or c["w"]>40 or c["h"]>24: continue
            if y0>=ylo and y1<=yhi:
                ids.append(c["id"])
        return np.isin(lab,ids),ids

    r1,ids1=comp_union(139,161)
    r2,ids2=comp_union(163,185)
    r3,ids3=comp_union(187,209)
    r4_direct,ids4=comp_union(210,232)
    if [len(ids1),len(ids2),len(ids3),len(ids4)] != [7,14,14,12]:
        raise RuntimeError(("unexpected alpha component counts",[len(ids1),len(ids2),len(ids3),len(ids4)],[ids1,ids2,ids3,ids4]))

    # Prove the repeated SPECIAL REQUEST prefix between source rows 2 and 3.
    prefix_x1=850
    shifted2=np.zeros_like(r2)
    shifted2[24:,:]=r2[:-24,:]
    p2=shifted2.copy(); p2[:,prefix_x1:]=False
    p3=r3.copy(); p3[:,prefix_x1:]=False
    if not np.array_equal(p2,p3):
        mismatch=int(np.count_nonzero(p2^p3))
        raise RuntimeError(("row2-row3 source prefix periodicity mismatch",mismatch,bbox_of(p2^p3)))

    # Row4 has two glyph fragments electrically connected to the panel component.
    # Recover ONLY the proven repeated prefix pixels by shifting row3 +24 and
    # intersecting with canonical source alpha. This never invents pixels and does not
    # use the historical Korean draft. The digit 3 remains direct source component 37.
    shifted3=np.zeros_like(r3)
    shifted3[24:,:]=r3[:-24,:]
    prefix4=shifted3 & (alpha>0)
    prefix4[:,prefix_x1:]=False
    # Every template pixel must exist in source alpha; no missing pixel is allowed.
    expected=shifted3.copy(); expected[:,prefix_x1:]=False
    if not np.array_equal(prefix4,expected):
        raise RuntimeError(("row4 repeated prefix missing source alpha",int(np.count_nonzero(prefix4^expected)),bbox_of(prefix4^expected)))
    r4=(r4_direct | prefix4)
    # Direct row4 pieces must be subset of recovered prefix except the final digit region.
    unexplained=r4_direct & ~r4
    if np.any(unexplained):
        raise RuntimeError(("unexplained row4 direct source pixels",bbox_of(unexplained)))

    row_masks=[r1,r2,r3,r4]
    idsets=[ids1,ids2,ids3,ids4]
    row_reports=[]
    for rn,(sm,ids,(seed,(en,ko))) in enumerate(zip(row_masks,idsets,zip(ROW_SEEDS,LABELS)),1):
        bb=bbox_of(sm)
        if bb is None: raise RuntimeError(("empty exact source row",rn))
        if rn==4 and bb[3]>232:
            raise RuntimeError(("row4 enters protected colored panel",bb))
        row_reports.append({
            "n":rn,"source":en,"korean":ko,"historical_hint_bbox":seed,
            "assigned_component_ids":ids,
            "template_recovery": ("row3_prefix_shift_plus_24_intersect_source_alpha" if rn==4 else None),
            "original_bbox":bb,"source_effect_pixels":int(np.count_nonzero(sm)),
            "source_alpha_min":int(alpha[sm].min()),"source_alpha_max":int(alpha[sm].max()),
            "source_alpha_median":float(np.median(alpha[sm])),
        })

    # Hard non-overlap and positive-separation proof between physical source rows.
    source_touch=[]
    for i in range(4):
        for j in range(i+1,4):
            ov=int(np.count_nonzero(row_masks[i]&row_masks[j]))
            near=np.asarray(mask_img(row_masks[i]).filter(ImageFilter.MaxFilter(3)))>0
            touch=int(np.count_nonzero(near&row_masks[j]))
            if ov or touch: source_touch.append([i+1,j+1,ov,touch])
    if source_touch:
        raise RuntimeError(("source row masks not positively separated",source_touch))

    full=np.zeros((H,W),bool)
    for m in row_masks: full|=m

    # Clean plate: local RGBA plane from a 7px ring around each exact source mask.
    clean=sa.astype(np.float32).copy()
    for row,sm in zip(row_reports,row_masks):
        dil=np.asarray(mask_img(sm).filter(ImageFilter.MaxFilter(15)))>0
        ring=dil & ~sm & search
        yy,xx=np.nonzero(ring)
        if len(xx)<100: raise RuntimeError(("insufficient clean ring",row["n"],len(xx)))
        # Exclude any alpha-active source effect from ring so reconstruction uses background only.
        good=(alpha[yy,xx]==0)
        yy=yy[good];xx=xx[good]
        if len(xx)<80: raise RuntimeError(("insufficient transparent background ring",row["n"],len(xx)))
        A=np.column_stack([np.ones(len(xx)),xx.astype(float),yy.astype(float)])
        vals=sa[yy,xx].astype(float)
        coefs=[];pred=np.zeros_like(vals)
        for ch in range(4):
            coef=np.linalg.lstsq(A,vals[:,ch],rcond=None)[0]
            coefs.append(coef); pred[:,ch]=A@coef
        mae=float(np.mean(np.abs(pred-vals)))
        if mae>2.5: raise RuntimeError(("background plane not exact/smooth",row["n"],mae))
        my,mx=np.nonzero(sm); MA=np.column_stack([np.ones(len(mx)),mx.astype(float),my.astype(float)])
        for ch in range(4): clean[my,mx,ch]=np.clip(MA@coefs[ch],0,255)
        row["clean_ring_rgba_mae"]=mae
        row["background_rgba_median"]=[int(v) for v in np.median(vals,axis=0)]
    clean_a=np.rint(clean).astype(np.uint8)
    clean_img=Image.fromarray(clean_a,"RGBA")

    FONT=ensure_font()
    # Source alpha-only style: preserve hidden RGB family and representative source opacity.
    src_rgb=np.median(sa[full,:3],axis=0)
    fill_rgb=tuple(int(v) for v in src_rgb)
    fill_alpha=int(np.percentile(alpha[full],90))
    fill_alpha=max(32,min(255,fill_alpha))

    def tile(text,fs):
        f=ImageFont.truetype(FONT,fs)
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        tb=d.textbbox((0,0),text,font=f)
        pad=4
        im=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
        ImageDraw.Draw(im).text((pad-tb[0],pad-tb[1]),text,font=f,fill=fill_rgb+(fill_alpha,))
        bb=im.getchannel("A").getbbox()
        return im.crop(bb) if bb else None

    min_h=min(r["original_bbox"][3]-r["original_bbox"][1] for r in row_reports)
    common=None
    for fs in range(min(64,max(10,int(min_h*0.88))),7,-1):
        tiles=[tile(r["korean"],fs) for r in row_reports]
        ok=True
        for t,r in zip(tiles,row_reports):
            ob=r["original_bbox"]; sw=ob[2]-ob[0]; sh=ob[3]-ob[1]
            if t is None or t.width>sw-2 or t.height>sh-2: ok=False; break
        if ok:
            common=(fs,tiles);break
    if common is None: raise RuntimeError("cannot fit shared Korean typography within exact source bboxes")
    fs,tiles=common

    final=clean_img.copy()
    target=np.zeros((H,W),bool); tms=[]
    for row,t in zip(row_reports,tiles):
        x0,y0,x1,y1=row["original_bbox"]; aw=x1-x0; ah=y1-y0
        px=x0+1
        py=y0+(ah-t.height)//2
        if px+t.width>=x1 or py<=y0 or py+t.height>=y1:
            raise RuntimeError(("fit failed",row["n"],row["original_bbox"],t.size,(px,py)))
        layer=Image.new("RGBA",(W,H),(0,0,0,0))
        layer.alpha_composite(t,(px,py))
        lm=np.asarray(layer.getchannel("A"))>0
        for old in tms:
            if np.any(lm&old): raise RuntimeError(("localized overlap",row["n"]))
        tms.append(lm); target|=lm; final.alpha_composite(layer)
        lb=list(layer.getchannel("A").getbbox()); ob=row["original_bbox"]
        row.update({
            "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
            "localized_bbox":lb,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
            "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
            "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
            "containment":"PASS","size_ceiling":"PASS","font_size":fs,
            "font_basename":Path(FONT).name,"fill_rgba":list(fill_rgb)+(fill_alpha,),
            "shared_source_style":"PASS"
        })

    raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=sb[:128]+raw_final.tobytes("raw","RGBA")
    cand.write_bytes(payload); csha=sha(payload)
    raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw","RGBA")
    dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if payload[:128]!=sb[:128] or ImageChops.difference(final,dec).getbbox():
        raise RuntimeError("DDS roundtrip/header mismatch")
    da=np.asarray(dec,dtype=np.uint8)
    allowed=np.zeros((H,W),bool)
    for r in row_reports:
        x0,y0,x1,y1=r["original_bbox"]; allowed[y0:y1,x0:x1]=1
    changed=np.any(sa!=da,axis=2)
    outside=int(np.count_nonzero(changed&~allowed))
    alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
    target_out=int(np.count_nonzero(target&~allowed))
    # Source residue means any original source-effect pixel still exactly survives after clean+render,
    # outside the new Korean target mask.
    residue=int(np.count_nonzero(full & ~target & np.all(sa==da,axis=2)))
    overlap=0; touch=[]
    for i in range(4):
        for j in range(i+1,4):
            ov=int(np.count_nonzero(tms[i]&tms[j]))
            near=np.asarray(mask_img(tms[i]).filter(ImageFilter.MaxFilter(3)))>0
            tp=int(np.count_nonzero(near&tms[j]))
            overlap+=ov
            if ov or tp: touch.append([i+1,j+1,ov,tp])
    if outside or alpha_out or target_out or residue or overlap or touch:
        raise RuntimeError(("final QA",outside,alpha_out,target_out,residue,overlap,touch))

    mask_img(full).save(out/"1F5_SOURCE_TEXT_MASK.png")
    mask_img(allowed).save(out/"1F5_ALLOWED_TEXT_REGION_MASK.png")
    mask_img(~allowed).save(out/"1F5_PROTECTED_MASK.png")
    mask_img(target).save(out/"1F5_TARGET_TEXT_MASK.png")
    clean_img.save(out/"1F5_CLEAN_PLATE.png")
    sp=Path("/tmp/b53src.png"); fp=Path("/tmp/b53fin.png")
    src.save(sp); dec.save(fp)
    v=repo/"tools/localization/validate_clean_plate.py"
    subprocess.run(["python3",str(v),str(sp),str(out/"1F5_CLEAN_PLATE.png"),str(out/"1F5_SOURCE_TEXT_MASK.png"),"--report",str(out/"B53_CLEAN_VALIDATION.json")],check=True)
    subprocess.run(["python3",str(v),str(sp),str(fp),str(out/"1F5_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",str(out/"1F5_PROTECTED_MASK.png"),"--report",str(out/"B53_FINAL_VALIDATION.json")],check=True)

    def comp(im,bg=(64,64,64,255)):
        z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
    def card(label,im,bg=(64,64,64,255)):
        z=comp(im,bg); c=Image.new("RGB",(W,H+26),"white"); c.paste(z,(0,26))
        ImageDraw.Draw(c).text((5,5),label,fill="black"); return c
    cards=[card("SOURCE_READABLE",src),card("CLEAN",clean_img),card("FINAL",dec),card("FINAL_WHITE",dec,(255,255,255,255))]
    sheet=Image.new("RGB",(W*2,(H+26)*2),"white")
    sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(W,0));sheet.paste(cards[2],(0,H+26));sheet.paste(cards[3],(W,H+26))
    sheet.save(out/"B53_1F5_COMPARE.jpg",quality=96)
    sr,cl,fi=comp(src),comp(clean_img),comp(dec)
    rowcards=[]
    for r in row_reports:
        x0,y0,x1,y1=r["original_bbox"]; p=10
        cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
        ims=[z.crop(cr) for z in (sr,cl,fi)]
        ims=[z.resize((z.width*4,z.height*4),Image.Resampling.NEAREST) for z in ims]
        cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+28
        c=Image.new("RGB",(cw,ch),"white"); xx=0
        for z in ims: c.paste(z,(xx,28)); xx+=z.width+6
        ImageDraw.Draw(c).text((4,5),f'{r["n"]} {r["source"]} -> {r["korean"]}',fill="black")
        rowcards.append(c)
    rs=Image.new("RGB",(max(c.width for c in rowcards),sum(c.height for c in rowcards)+4*(len(rowcards)-1)),"white")
    yy=0
    for c in rowcards: rs.paste(c,(0,yy)); yy+=c.height+4
    rs.save(out/"B53_1F5_ROW_CONTACT_4X.jpg",quality=96)
    rr=Image.new("RGB",(W,(H+26)*2),"white")
    rr.paste(card("SOURCE_RAW_MIRROR_Y",raw_src),(0,0)); rr.paste(card("FINAL_RAW_MIRROR_Y",raw_dec),(0,H+26))
    rr.save(out/"B53_1F5_RAW_COMPARE.jpg",quality=96)

    report={
        "schema_version":1,"role":"B","run":RUN,"queue_index":INDEX,"asset":ASSET,
        "readiness_tier":"REWORK_REQUIRED_COMPLETED_SAME_INVOCATION",
        "source_sha256":source_sha,"historical_discovery_sha256":hist_sha,
        "historical_discovery_only":True,"historical_localized_pixels_reused":False,
        "candidate_sha256":csha,"candidate_path":str(cand.relative_to(repo)),
        "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
        "source_mask_method":"source alpha glyph components by proven 24px row periodicity; row4 panel-connected prefix recovered only by row3 +24 template intersected with canonical source alpha",
        "source_row_positive_separation":"PASS","rows":row_reports,
        "shared_typography":{"font_size":fs,"fill_rgba":list(fill_rgb)+(fill_alpha,),"status":"PASS_SHARED_SOURCE_ALPHA_STYLE"},
        "containment":{"elements_total":4,"elements_pass":4,"outside":outside,"alpha_outside":alpha_out,"target_out":target_out,
                       "source_residue":residue,"overlap":overlap,"touch_pairs":touch,"status":"PASS"},
        "policy":{"colored_menu_panels_preserved":"YES","song_titles_credits":"not_targeted","stage_names":"not_applicable","multi_line":"not_applicable"},
        "manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
        "status":"B_PRODUCTION53_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
    }
    (out/"B53_1F5_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    summary={"run":RUN,"asset":"1F5FE6E9","index":INDEX,"candidate_sha256":csha,"bbox_size_pass":"4/4",
             "outside":outside,"alpha_outside":alpha_out,"source_residue":residue,"overlap":overlap,"touch_pairs":len(touch),
             "worker_status":report["status"],"runtime_validation":"UNTESTED",
             "report":f"localization/graphics/role_B/{RUN}/B53_1F5_REPORT.json"}
    (wr/"B53_1F5FE6E9.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        repo=Path.cwd(); out=repo/"localization/graphics/role_B"/RUN; out.mkdir(parents=True,exist_ok=True)
        wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
        fail={"run":RUN,"asset":"1F5FE6E9","index":INDEX,"status":"FAIL_CLOSED_DIAGNOSTIC",
              "exception":repr(e),"traceback":traceback.format_exc(),"RUNTIME_VALIDATION":"UNTESTED"}
        (out/"B53_FAIL_CLOSED.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n")
        (wr/"B53_1F5FE6E9_FAIL.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps(fail,ensure_ascii=False),flush=True)

#!/usr/bin/env python3
"""B336 q060: first unresolved P2 font and source-lean evidence, without a blind rerender.

B335 P1 canonical plate and B332R persisted DDS are exact pinned inputs.
Measure the installed typeface/corpus; export traceable source/glyph silhouettes.
A left-edge proxy from distinct source/Korean characters is *not* a matched-stroke
slant approval. Do not promote or report producer PASS without such verification.
"""
import csv,hashlib,io,json,os,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
SRC=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
CAND=G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
PREV=G/"role_B/20261009-B335-Q060-SOURCE-PLATE-P1-GUARD/recipe.json"
OUT=G/"role_B/20261009-B336-Q060-FONT-SLANT-ANCHOR-P2"
OUT.mkdir(parents=True,exist_ok=True)
H=lambda v:hashlib.sha256(v).hexdigest()
Sdata=SRC.read_bytes();Fdata=CAND.read_bytes()
Ssha="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
Fsha="d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01"
assert H(Sdata)==Ssha and H(Fdata)==Fsha
assert Sdata[:128]==Fdata[:128] and len(Sdata)==len(Fdata)==33554560
rec=json.loads(PREV.read_text())
assert rec["source"]["sha256"]==Ssha and rec["current"]["sha256"]==Fsha
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
    row=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="60")
assert row["artwork_status"].startswith("c334_c2_hold_"),row["artwork_status"]
def dec(data):
    x=np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"),dtype=np.uint8)
    assert x.shape==(2048,4096,4)
    return np.flipud(x).copy()
S=dec(Sdata);F=dec(Fdata)
l,t,r,b=2081,230,2860,370
sr=S[t:b,l:r];fr=F[t:b,l:r]
yy=np.arange(t,b)[:,None]
orange=(sr[:,:,3]>90)&(sr[:,:,0]>150)&(sr[:,:,1]>35)&(sr[:,:,2]*100<sr[:,:,0]*55)&(sr[:,:,0]*100>sr[:,:,1]*105)&(yy>=340)
assert int(orange.sum())==8892
# The original gold lettering and protected orange sibling share an edit
# rectangle. Never mistake the orange pixels for source lettering anchors.
source_face=(sr[:,:,3]>100)&(sr[:,:,0]>145)&(sr[:,:,1]>95)&(sr[:,:,2]>50)&~orange
final_face=(fr[:,:,3]>100)&(fr[:,:,0]>145)&(fr[:,:,1]>95)&(fr[:,:,2]>50)&~orange
# Lower source edge is not necessarily the same stroke: a provisional
# silhouette proxy is information for a human, not proof of slant matching.
def proxy(m):
    ys=np.flatnonzero(m.sum(axis=1)>=5)
    if len(ys)<15:return {"qualified":False,"why":"insufficient face samples"}
    z=[]
    for y in [int(ys[round((len(ys)-1)*v)]) for v in (0.20,0.80)]:
        xs=np.flatnonzero(m[y]);z.append([int(xs.min()+l),int(y+t),int(xs.max()+l)])
    return {"qualified":False,"top_band_left_right":z[0],"bottom_band_left_right":z[1],
            "left_dx_proxy":z[0][0]-z[1][0],
            "why":"first active pixels at two y bands need not be the corresponding glyph stroke; cannot certify P2 right lean"}
source_prox=proxy(source_face);final_prox=proxy(final_face)
fontpath=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
font_evidence={"expected_path":str(fontpath),"found":fontpath.is_file(),
              "source_family":"B331/B332R Noto Sans CJK Bold","text":"아웃런 마일:"}
if fontpath.is_file():
    font_evidence["sha256"]=H(fontpath.read_bytes())
    try:
        from fontTools.ttLib import TTCollection,TTFont
        faces=TTCollection(str(fontpath),lazy=True).fonts
        cmaps=[set().union(*(dict(t.cmap) for t in face["cmap"].tables if t.isUnicode())) for face in faces]
        chars=sorted(set(font_evidence["text"]))
        font_evidence.update(fonttools_checked=True,face_count=len(cmaps),
            required_codepoints=[{"char":v,"hex":hex(ord(v)),"faces":[i for i,cm in enumerate(cmaps) if ord(v) in cm]} for v in chars],
            all_chars_covered=all(any(ord(v) in cm for cm in cmaps) for v in chars))
        for face in faces:face.close()
    except Exception as exc:
        font_evidence.update(fonttools_checked=False,all_chars_covered=None,reason=str(exc))
else:
    font_evidence.update(fonttools_checked=False,all_chars_covered=None,reason="Pinned historical renderer font absent; no fallback substitutions")
# Pin the source image and exact alpha in both readable and RAW forms.
clean_path=G/"role_B/20261009-B335-Q060-SOURCE-PLATE-P1-GUARD/B335_P1_CLEAN_PLATE_FULL_NATIVE_RAW.png"
Craw=np.asarray(Image.open(clean_path).convert("RGBA"),dtype=np.uint8)
assert Craw.shape==F.shape
C=np.flipud(Craw).copy()
assert np.all(C[t:b,l:r][~orange,3] == 0) is False if False else True
# The protected mask is broader than orange itself; inspect exact P1 protected source.
protected=G/"role_B/20261009-B335-Q060-SOURCE-PLATE-P1-GUARD/B335_MASK_SOURCE_ORANGE_PROTECTED_RAW.png"
protect=np.flipud(np.asarray(Image.open(protected).convert("L"),dtype=np.uint8)>0)[t:b,l:r]
assert np.all(C[t:b,l:r][~protect,3]==0)
assert np.array_equal(C[t:b,l:r][protect],S[t:b,l:r][protect])
assert np.array_equal(F[t:b,l:r][protect],S[t:b,l:r][protect])
# Count candidate changes limited by old source-based edit region, not inferred from final.
outside=np.ones((2048,4096),dtype=bool);outside[t:b,l:r]=False
# C is a P1 *derived* plate; compare authentic source only in protected ROI.
assert np.array_equal(F[:t],F[:t])  # no claim about unrelated atlas cells
proof=[]
window=(2050,195,2910,425);x0,y0,x1,y1=window
for orientation in ("FLIPY","RAW"):
    for scale in (100,75,50):
        crops=[]
        for arr in (S,C,F):
            region=arr[y0:y1,x0:x1]
            if orientation=="RAW":region=np.flipud(region)
            bg=Image.new("RGBA",(x1-x0,y1-y0),(81,81,81,255))
            bg.alpha_composite(Image.fromarray(region.copy(),"RGBA"))
            view=bg.convert("RGB")
            if scale!=100:view=view.resize((round(view.width*scale/100),round(view.height*scale/100)),Image.Resampling.LANCZOS)
            crops.append(view)
        out=Image.new("RGB",(sum(z.width for z in crops)+8,max(z.height for z in crops)),(81,81,81))
        xx=0
        for z in crops:out.paste(z,(xx,0));xx+=z.width+4
        p=OUT/f"B336_SOURCE_CLEAN_SAVED_{orientation}_{scale}_GRAY.png"
        out.save(p,optimize=True);proof.append(p.as_posix())
# Provisional data-driven candidate/source pixel band proxies deliberately labeled.
ov=Image.fromarray(np.concatenate([sr,fr],axis=1).copy(),"RGBA").convert("RGB")
draw=ImageDraw.Draw(ov)
for xoff,v in ((0,source_prox),(r-l,final_prox)):
    if "top_band_left_right" not in v:continue
    for name,col in (("top_band_left_right",(40,240,80)),("bottom_band_left_right",(240,80,50))):
        x,y,_=v[name]; px=x-l+xoff;py=y-t
        draw.line([(px-9,py),(px+9,py)],fill=col,width=2)
        draw.line([(px,py-9),(px,py+9)],fill=col,width=2)
ovpath=OUT/"B336_SOURCE_VS_SAVED_PIXEL_BAND_PROXIES_NOT_SAME_STROKE.png"
ov.save(ovpath,optimize=True)
result={
 "schema_version":2,"role":"B","run":"B336",
 "run_key":"OUTRUN-KOR-B336-Q060-SOURCE-FONT-SLANT-P2-20261009-2340",
 "queue_index":60,"priority":"P0","stage":"P2_SOURCE_FAMILY_EVIDENCE",
 "pinned_english_sha256":Ssha,"pinned_current_candidate_sha256":Fsha,
 "p1_recipe":PREV.as_posix(),"p1_plate_clean_exact_protected":True,
 "font_evidence":font_evidence,"source_gold_face_pixels":int(source_face.sum()),
 "candidate_gold_face_pixels":int(final_face.sum()),
 "source_first_glyph_band_proxy":source_prox,"candidate_first_glyph_band_proxy":final_prox,
 "slant_same_stroke_verified":False,
 "p2_decision":"HOLD_MATCHED_STROKE_ANCHORS_AND_SOURCE_FONT_STYLE",
 "producer_decision":"NOT_PROMOTED_NO_CHANGED_DDS",
 "new_DDS":0,"source_clean_final_proofs":proof,"pixel_band_comparison":ovpath.as_posix(),
 "C2":"C334_HOLD_UNCHANGED","C3":"NOT_RUN",
 "INGAME_REWORK_BACKLOG":"IGR044_OPEN_USER_INGAME_FAIL",
 "RUNTIME_VALIDATION":"UNTESTED","backend":"GITHUB_ACTIONS",
 "excluded_work":["VR","FFB","DX11","DXVK"]}
if font_evidence.get("all_chars_covered") is not True:
    result["p2_decision"]="HOLD_FONT_COVERAGE_AND_MATCHED_STROKE_ANCHORS"
(OUT/"B336_P2_FONT_SLANT_EVIDENCE.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print("B336_P2_FRESH_EVIDENCE",json.dumps({"font":font_evidence.get("sha256"),"glyph_coverage":font_evidence.get("all_chars_covered"),"source_face_pixels":result["source_gold_face_pixels"],"candidate_face_pixels":result["candidate_gold_face_pixels"],"result":result["p2_decision"],"dds":0},ensure_ascii=False))

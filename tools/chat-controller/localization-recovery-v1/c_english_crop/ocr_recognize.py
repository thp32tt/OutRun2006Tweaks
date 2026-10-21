#!/usr/bin/env python3
"""Conservative, completely offline English OCR auto-enqueue for verified native HD atlases.

Only genuinely DDS-pixel-identical PNGs from the approved registry are eligible.
Tesseract must read exact official English transcription with high confidence.
Unknown art or ambiguous/clipped candidates are HOLD with evidence, not crops.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import difflib
from PIL import Image, ImageOps
import numpy as np
import discover

BASE=discover.BASE
SOURCE=discover.SRC
AUDIT=BASE/"auto_discovery"
TESS_TIMEOUT=95
OCR_STRATEGY_COUNT=12

def norm(t):
    return "".join(ch for ch in str(t).upper() if ch.isalnum())


def searchable_phrase(t):
    # Transcript placeholders such as [ENTER-KEY ICON] describe protected art,
    # not literal glyphs. OCR the surrounding real text only.
    return re.sub(r"\[[^\]]+\]"," ",str(t))


def is_english_source_phrase(t):
    """Only English UI source text belongs to the C crop coverage target."""
    if not isinstance(t,str) or not t.strip():
        return False
    visible=searchable_phrase(t)
    # Require at least one ASCII Latin letter and reject any non-ASCII alphabetic
    # script (Japanese/Korean/etc.). Digits and punctuation remain valid.
    if not re.search(r"[A-Za-z]",visible):
        return False
    return not any(ch.isalpha() and not ch.isascii() for ch in visible)

def approved_phrases(q):
    path=SOURCE/"transcriptions.jsonl"
    if not path.exists():return {}
    trans={}
    for ln in path.read_text(encoding="utf-8").splitlines():
        try: entry=json.loads(ln)
        except ValueError: continue
        if str(entry.get("index","")).zfill(3)!=q[1:]:continue
        if entry.get("status")!="transcribed_reviewed":continue
        for seg in entry.get("segments",[]):
            phrase=seg.get("source","")
            if (not isinstance(phrase,str) or not phrase.strip() or len(phrase)>180 or
                not is_english_source_phrase(phrase)):
                continue
            canonical=norm(searchable_phrase(phrase))
            if len(canonical)>=2 and all((ch.isprintable() or ch.isspace()) for ch in phrase):
                trans.setdefault(canonical,phrase)
    return trans

def ocr_words(image, strategy=0, languages="eng"):
    """Run one deterministic OCR strategy; repeated coverage scans rotate strategies."""
    strategy=int(strategy)%OCR_STRATEGY_COUNT
    # Alternate native and 2x recovery immediately instead of spending the
    # first six attempts repeating only native-resolution OCR.
    variant=(0,6,1,7,2,8,3,9,4,10,5,11)[strategy]
    rgba=image.convert("RGBA")
    composed=Image.alpha_composite(Image.new("RGBA",rgba.size,"black"),rgba).convert("L")
    base_strategy=variant%6
    scale=2 if variant>=6 else 1
    psm=(11,6,12,11,6,12)[base_strategy]
    if base_strategy < 3:
        prepared=ImageOps.autocontrast(ImageOps.invert(composed))
    else:
        # Some outlined/dark UI text is read better without polarity inversion.
        prepared=ImageOps.autocontrast(composed)
    if scale==2:
        prepared=prepared.resize((prepared.width*2,prepared.height*2),Image.Resampling.LANCZOS)
    with tempfile.TemporaryDirectory(prefix="outrun-ocr-") as td:
        test=Path(td)/"source.png"
        prepared.save(test)
        env={**os.environ,"OMP_THREAD_LIMIT":"1","TESSDATA_PREFIX":"/usr/share/tesseract-ocr/5/tessdata"}
        run=subprocess.run(["tesseract",str(test),"stdout","-l",languages,"--psm",str(psm),"tsv"],
                           capture_output=True,text=True,timeout=TESS_TIMEOUT,env=env)
    if run.returncode: raise RuntimeError("TESSERACT_ERROR:"+run.stderr[-500:])
    groups={}
    for row in csv.DictReader(io.StringIO(run.stdout),delimiter="\t"):
        if row.get("level")!="5" or not row.get("text","").strip():continue
        try:
            txt=row["text"].strip()
            conf=float(row["conf"])
            x,y,w,h=[int(row[k]) for k in ("left","top","width","height")]
            if not 0<=conf<=100 or w<=1 or h<=1 or x<0 or y<0:continue
            if scale==2:
                x0=x//2; y0=y//2
                x1=(x+w+1)//2; y1=(y+h+1)//2
            else:
                x0,y0,x1,y1=x,y,x+w,y+h
            line=(row["page_num"],row["block_num"],row["par_num"],row["line_num"])
            groups.setdefault(line,[]).append({"word":txt,"confidence":conf,"bbox":[x0,y0,x1,y1]})
        except (ValueError,KeyError,TypeError):continue
    return list(groups.values())

def margin_check(im,box):
    a=np.asarray(im.getchannel("A").crop(tuple(box)),dtype=np.uint8)
    if a.size==0 or (a>20).sum()<16:return "EMPTY_ORIGINAL_ALPHA"
    # Boundary pixels with meaningful alpha indicate potential clipped glyph/effect.
    k=min(4,a.shape[0]//6,a.shape[1]//6)
    if k<2:return "CROP_TOO_SMALL"
    edge=np.concatenate([a[:k,:].ravel(),a[-k:,:].ravel(),a[:, :k].ravel(),a[:, -k:].ravel()])
    if np.any(edge>120):
        return "ALPHA_TOUCHES_CROP_BORDER_REVIEW"
    return None

def opaque_context_border(im,box,threshold=.88):
    """True when crop boundary is overwhelmingly opaque context, not isolated glyph alpha."""
    a=np.asarray(im.getchannel("A").crop(tuple(box)),dtype=np.uint8)
    if a.size==0:return False
    k=min(4,a.shape[0]//6,a.shape[1]//6)
    if k<2:return False
    edges=(a[:k,:],a[-k:,:],a[:,:k],a[:,-k:])
    ratios=[float((e>120).mean()) for e in edges]
    return min(ratios)>=threshold


def unique_regions(words,phrasemap,w,h,allow_fuzzy=False):
    raw=[]
    keys=list(phrasemap)
    for line in words:
        for begin in range(len(line)):
            for end in range(begin+1,min(begin+10,len(line)+1)):
                ws=line[begin:end]
                code=norm(" ".join(x["word"] for x in ws))
                matched=code if code in phrasemap else None
                mode="EXACT"
                similarity=1.0
                if matched is None and allow_fuzzy and len(code)>=6:
                    ranked=[]
                    for candidate in keys:
                        if abs(len(candidate)-len(code)) > max(3,int(len(candidate)*.25)):
                            continue
                        ratio=difflib.SequenceMatcher(None,code,candidate).ratio()
                        if ratio>=.90:
                            ranked.append((ratio,candidate))
                    ranked.sort(reverse=True)
                    if ranked and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=.035):
                        similarity,matched=ranked[0]
                        mode="FUZZY_STRONG"
                if matched is None:continue
                conf=min(x["confidence"] for x in ws)
                avg=sum(x["confidence"] for x in ws)/len(ws)
                if mode=="EXACT" and len(matched)<4:
                    min_required,avg_required=92,95
                else:
                    min_required=83 if mode=="EXACT" else 86
                    avg_required=88 if mode=="EXACT" else 91
                if conf<min_required or avg<avg_required:continue
                x0=min(x["bbox"][0] for x in ws)
                y0=min(x["bbox"][1] for x in ws)
                x1=max(x["bbox"][2] for x in ws)
                y1=max(x["bbox"][3] for x in ws)
                # Enough native padding for outlined text; borderline candidates held.
                pady=max(12,int((y1-y0)*.17))
                padx=max(18,int((y1-y0)*.36))
                box=[max(0,x0-padx),max(0,y0-pady),min(w,x1+padx),min(h,y1+pady)]
                if box[0]==0 or box[1]==0 or box[2]>=w or box[3]>=h:continue
                if box[2]-box[0]<28 or box[3]-box[1]<20:continue
                raw.append({"english":phrasemap[matched],"bbox_xyxy":box,
                            "ocr_exact_normalized":matched,"ocr_text":" ".join(x["word"] for x in ws),
                            "ocr_match_mode":mode,"ocr_similarity":round(similarity,4),
                            "min_confidence":round(conf,2),"mean_confidence":round(avg,2)})
    filtered=[]
    for candidate in sorted(raw,key=lambda r:-r["min_confidence"]):
        if any(discover.overlap(candidate["bbox_xyxy"],f["bbox_xyxy"])>.65 and
               norm(f["english"])==norm(candidate["english"]) for f in filtered):continue
        filtered.append(candidate)
    return filtered

def scan(verified,check_original,max_new=10,max_sources=4):
    if not shutil_which_tesseract():return {"status":"OCR_HOLD_TESSERACT_MISSING"}
    master=json.loads(discover.MASTER.read_text(encoding="utf-8"))
    if len(master.get("items",[]))!=255:raise ValueError("ARCHIVE_NOT_255")
    keys=sorted(verified)
    if not keys:return {"status":"OCR_IDLE_NO_VERIFIED_SOURCE"}
    # Rotate through native-HD source groups instead of repeatedly analyzing only
    # the first six. Cursor is persisted after every scan and never affects A/B.
    cursorfile=AUDIT/"ocr_source_cursor.json"
    try: cursor=int(json.loads(cursorfile.read_text()).get("cursor",0))
    except (ValueError,KeyError,OSError,TypeError):cursor=0
    # Cursor points to the NEXT lexicographic source key. This remains stable
    # when more validated original sources are appended between scans.
    selected=[keys[(cursor+i)%len(keys)] for i in range(min(max_sources,len(keys)))]
    result={"status":"OCR_SCAN","verified_source_count":len(keys),"selected":selected,
            "verified_sources_scanned":0,"ocr_matched":0,
            "queued":0,"skipped_existing":0,"held":0,"details":[]}
    for q in selected:
        rec=verified[q]
        if result["queued"]>=max_new:break
        meta={"queue_id":q,"source_kind":"N100_DDS_VERIFIED_READABLE_FULL_HD_PNG",
              "source_png":rec["png"],"source_sha256":rec["png_sha256"],
              "source_dimensions":rec["size"],"source_dds_path":rec["dds_repo_path"],
              "source_dds_sha256":rec["dds_sha256"]}
        try:
            check_original(meta)
            phrases=approved_phrases(q)
            if not phrases:continue
            with Image.open(SOURCE/rec["png"]) as src:
                full=src.copy()
            words=ocr_words(full)
            matches=unique_regions(words,phrases,full.width,full.height)
            used=[entry["bbox_xyxy"] for entry in master["items"]
                  if entry.get("id","").upper().startswith(q+"-") and len(entry.get("bbox_xyxy",[]))==4]
            for sf in sorted((BASE/"queue_specs").glob("*.json")):
                try:
                    spec=json.loads(sf.read_text(encoding="utf-8"))
                    if spec.get("queue_id")==q:
                        used.extend(reg["bbox_xyxy"] for reg in spec.get("regions",[]))
                except (ValueError,KeyError,TypeError):pass
            receipt={"source":rec["png"],"source_sha256":rec["png_sha256"],
                     "ocr_model":"tesseract-5-eng","matched":[],
                     "unmatched_word_groups":len(words),
                     "status":"TEST_ONLY_AUTO_OCR"}
            for m in matches:
                result["ocr_matched"]+=1
                bb=m["bbox_xyxy"]
                if any(discover.overlap(bb,u)>.38 for u in used):
                    result["skipped_existing"]+=1
                    receipt["matched"].append({**m,"decision":"SKIP_EXISTING"});continue
                bad=margin_check(full,bb)
                if bad:
                    result["held"]+=1
                    receipt["matched"].append({**m,"decision":"HOLD","reason":bad});continue
                fingerprint=hashlib.sha256((rec["png"]+"|"+m["ocr_exact_normalized"]+"|"+
                                            ",".join(map(str,bb))).encode()).hexdigest()[:12]
                rid="ocr-"+re.sub("[^a-z0-9]+","-",m["english"].lower()).strip("-")[:26]+"-"+fingerprint
                sf=BASE/"queue_specs"/(q+"_OCR_"+rid+".json")
                if sf.exists() or (BASE/"outputs"/(q+"-"+rid)).exists():
                    result["skipped_existing"]+=1;continue
                if result["queued"]>=max_new:break
                spec=dict(meta,schema=discover.SCHEMA,
                          regions=[{"id":rid,"english":m["english"],"bbox_xyxy":bb}],
                          ocr_evidence={"engine":"tesseract-5-eng","exact_official_text":True,
                                        "min_confidence":m["min_confidence"],
                                        "mean_confidence":m["mean_confidence"],
                                        "auto_qa":"OCR_SOURCE_ONLY_TEST_REQUIRED"})
                discover.save_json_atomic(sf,spec)
                result["queued"]+=1
                used.append(bb)
                receipt["matched"].append({**m,"decision":"QUEUED_TEST_ONLY","spec":sf.name})
            report=AUDIT/(q+"_ocr_results.json")
            discover.save_json_atomic(report,receipt)
            result["verified_sources_scanned"]+=1
            result["details"].append({"source":q,"ocr_words":sum(map(len,words)),
                                      "approved_phrases":len(phrases),"matched":len(matches),
                                      "report":str(report)})
        except Exception as e:
            result["held"]+=1
            result["details"].append({"source":q,"status":"OCR_HOLD","reason":str(e)[:300]})
    discover.save_json_atomic(AUDIT/"ocr_last_scan.json",result)
    discover.save_json_atomic(cursorfile,{"cursor":(cursor+len(selected))%len(keys),"after":selected[-1],
                                            "verified_source_count":len(keys)})
    return result

def shutil_which_tesseract():
    from shutil import which
    return which("tesseract") is not None
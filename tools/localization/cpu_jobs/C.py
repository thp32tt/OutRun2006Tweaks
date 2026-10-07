#!/usr/bin/env python3
# C261 diagnostic retry after first hosted compute failed before output commit.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, json, hashlib, tempfile, urllib.request, traceback
from PIL import Image

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
OUT="localization/graphics/role_C/20261008-C261-C2-Q102-Q062-Q024"
os.makedirs(OUT,exist_ok=True)

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def check_image(p):
    im=Image.open(p); im.load()
    return {"path":p,"mode":im.mode,"size":list(im.size)}

checks={}
tests=[
("q102_source","localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds"),
("q102_candidate","localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds"),
("q102_clean","localization/graphics/role_C/20261004-1720-C91/C91_571E78F3_CLEAN_PLATE.png"),
("q62_candidate","localization/graphics/hd_candidates/textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"),
("q62_a132_clean","localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN/A132_CLEAN_PLATE.png"),
("q62_b244_clean","localization/graphics/role_B/20261008-B244-Q062-PSD-L43-CLEAN/B244_Q062_CLEAN_PLATE.png"),
("q24_candidate","localization/graphics/hd_candidates/textures/load/spr_name_entry_xst/66743AA8_1024x1024.dds"),
("q24_clean","localization/graphics/role_B/20261006-B-PRODUCTION209-NAMEENTRY-JAMO-KEYCAPS/B209_CLEAN_PLATE.png"),
]
for name,p in tests:
    try:
        d=check_image(p); d["sha256"]=sha256(p); checks[name]={"ok":True,**d}
    except Exception as e:
        checks[name]={"ok":False,"path":p,"error":repr(e),"traceback":traceback.format_exc()}

with tempfile.TemporaryDirectory() as td:
    for name,url,expect in [
      ("q62_source","https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds","796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"),
      ("q24_source","https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_name_entry_xst/66743AA8_1024x1024.dds","8e18676ac303b07a56d81d1d21c5e025e0baf46da49b16ae9d2e411960181f73")
    ]:
      p=os.path.join(td,name+".dds")
      try:
        urllib.request.urlretrieve(url,p)
        d=check_image(p); d["sha256"]=sha256(p); d["expected_sha256"]=expect; d["sha_match"]=d["sha256"]==expect
        checks[name]={"ok":True,**d}
      except Exception as e:
        checks[name]={"ok":False,"url":url,"error":repr(e),"traceback":traceback.format_exc()}

for name,p in [
("b212_report","localization/graphics/role_B/20261006-B-MANUALQA212-SELECTOR-SLANT/B212_571E78F3_REPORT.json"),
("a132_report","localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN/A132_33491F83_REPORT.json"),
("b209_report","localization/graphics/role_B/20261006-B-PRODUCTION209-NAMEENTRY-JAMO-KEYCAPS/B209_JAMO_KEYCAP_REPORT.json")]:
    try:
      with open(p,"r",encoding="utf-8-sig") as f: j=json.load(f)
      checks[name]={"ok":True,"path":p,"keys":list(j.keys())[:30]}
    except Exception as e:
      checks[name]={"ok":False,"path":p,"error":repr(e),"traceback":traceback.format_exc()}

with open(os.path.join(OUT,"C261_DIAGNOSTIC.json"),"w",encoding="utf-8") as f:
    json.dump({"run":"20261008-C261-C2-Q102-Q062-Q024","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","checks":checks},f,ensure_ascii=False,indent=2)
print(json.dumps(checks,ensure_ascii=False,indent=2))

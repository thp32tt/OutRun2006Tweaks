#!/usr/bin/env python3
"""Build an independently verifiable, non-installing Q032/Q241 DDS pilot ZIP."""
from pathlib import Path
import zipfile,json,hashlib,io,os
BASE=Path("/home/chatgpt-runner2/work/image-src/text_roi_batches")
ORIGINAL=BASE/"offline_overlap_v3_ink_test_only/OUTRUN_OFFLINE_KOREAN_TEST_ONLY_96e9372fb718.zip"
OUT=BASE/"korean_test_delivery_20261102"
DEST=OUT/"OUTRUN_KOR_Q032_Q241_DDS_TEST_ONLY.zip"
EXPECTED="84d92c22ff957ebeaa3156165b9ed7ef769802756ddc183d18bd586ff5c1ddf3"
def hashbytes(b):return hashlib.sha256(b).hexdigest()
def hashfile(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
assert hashfile(ORIGINAL)==EXPECTED,"source sha mismatch"
OUT.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(ORIGINAL) as z:
 manifest=json.loads(z.read("TEST_ONLY_MANIFEST.json"))
 picked={k:v for k,v in manifest["source_reports"].items() if k.startswith(("Q032_","Q241_"))}
 assert len(picked)==2,("expected exactly 2",list(picked))
 entries={}
 for key,v in picked.items():
  target=v["target"]
  assert target.startswith("textures/load/") and target.endswith(".dds") and ".." not in target
  raw=z.read(target)
  assert hashbytes(raw)==v["sha256"]
  entries[key]={"target":target,"sha256":v["sha256"],"source":v["source"],"bytes":len(raw)}
 if DEST.exists():raise SystemExit("REFUSE_OVERWRITE_EXISTING")
 with zipfile.ZipFile(DEST,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=2) as out:
  for key,v in sorted(picked.items()):
   out.writestr(v["target"],z.read(v["target"]))
   receipt="qa_receipts/"+key+".json"
   assert receipt in z.namelist(),receipt
   out.writestr(receipt,z.read(receipt))
  pilot_manifest={"status":"TEST_ONLY_NOT_GAME_APPROVED","original_zip_sha256":EXPECTED,"sources":entries,
   "included_dds":2,"runtime_validation":"UNTESTED","manual_install_only":True}
  out.writestr("PILOT_MANIFEST.json",json.dumps(pilot_manifest,ensure_ascii=False,indent=2)+"\n")
  out.writestr("README_TEST_ONLY_KO.txt","OutRun 2006 Korean Q032 ranking + Q241 loading pilot DDS\\n"+
  "TEST_ONLY, NOT RUNTIME APPROVED. This ZIP is NOT a game installer.\\n"+
  "Do not place these DDS in the original game without an independent backup.\\n"+
  "To preview: extract to a NEW isolated folder first, check textures/load/...DDS file paths.\\n"+
  "Installed HD texture mod may use different paths. Verify with the game build.\\n"+
  "Uncompressed DDS can increase VRAM; actual gameplay performance untested.\\n")
with zipfile.ZipFile(DEST) as zz:
 assert zz.testzip() is None
 assert len([x for x in zz.namelist() if x.endswith(".dds")])==2
print(json.dumps({"status":"PILOT_ZIP_VERIFIED", "path":str(DEST),"bytes":DEST.stat().st_size,"sha256":hashfile(DEST),"dds":len(entries),"items":entries},ensure_ascii=False))
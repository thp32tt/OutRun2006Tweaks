#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, html, json, re, sys, urllib.request, zipfile
from pathlib import Path

USER_AGENT="Mozilla/5.0 (GitHub Actions private conversion audit)"
HARD_BLOCK_PATTERNS={
 "do_not_share":r"\bdo\s+not\s+share\b",
 "do_not_redistribute":r"\bdo\s+not\s+(?:re-?)?distribut(?:e|ion)\b",
 "no_redistribution":r"\bno\s+(?:re-?)?distribution\b",
 "do_not_reupload":r"\bdo\s+not\s+re-?upload\b",
 "no_reupload":r"\bno\s+re-?upload(?:ing)?\b",
 "do_not_convert":r"\bdo\s+not\s+convert\b",
 "no_conversion":r"\bno\s+conversion\b",
 "no_porting":r"\bno\s+port(?:ing)?\b",
 "do_not_port":r"\bdo\s+not\s+port\b",
 "ripping_forbidden":r"\bripp(?:ing|ed).*?(?:not\s+allowed|forbidden|prohibited)\b",
 "base_use_forbidden":r"\b(?:not\s+allowed|forbidden|prohibited).*?\buse(?:d)?\s+as\s+(?:a\s+)?base\b",
 "personal_use_only":r"\bpersonal\s+use\s+only\b",
}
TEXT_SUFFIXES={"",".txt",".md",".markdown",".nfo",".ini",".cfg",".json",".xml",".html",".htm",".license",".readme",".rtf"}

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
 return h.hexdigest()

def download(url:str,out:Path,referer:str|None=None):
 headers={"User-Agent":USER_AGENT}
 if referer: headers["Referer"]=referer
 req=urllib.request.Request(url,headers=headers)
 with urllib.request.urlopen(req,timeout=120) as src,out.open("wb") as dst:
  for chunk in iter(lambda:src.read(1024*1024),b""): dst.write(chunk)

def extract_signed_url(page_text:str)->tuple[str,str]:
 normalized=html.unescape(page_text).replace("\\u0026","&").replace("\\/","/")
 patterns=[
  r'\\?"file\\?"\s*:\s*\\?"(https://storage\.dlcfun\.com/dlcfun-private/files/addons/[^"\\]+?\.zip\?[^"\\]+)',
  r'(https://storage\.dlcfun\.com/dlcfun-private/files/addons/[^"<> ]+?\.zip\?[^"<> ]+)',
 ]
 for pattern in patterns:
  m=re.search(pattern,normalized,re.I)
  if m:
   url=m.group(1).replace("\\u0026","&").replace("\\/","/")
   nm=re.search(r'file_name\\?"\s*:\s*\\?"([^"\\]+\.zip)',normalized,re.I)
   return url,(nm.group(1) if nm else "source.zip")
 raise RuntimeError("Could not locate current signed source ZIP URL on DLCFun page")

def decode_text(raw:bytes)->str|None:
 for enc in ("utf-8-sig","cp1252","latin1"):
  try:return raw.decode(enc)
  except UnicodeDecodeError:pass
 return None

def rights_audit(root:Path)->dict:
 scanned=[];hits=[]
 for p in sorted(x for x in root.rglob("*") if x.is_file()):
  nl=p.name.lower(); suffix=p.suffix.lower()
  if not (suffix in TEXT_SUFFIXES or "readme" in nl or "license" in nl or "credit" in nl): continue
  if p.stat().st_size>2*1024*1024: continue
  txt=decode_text(p.read_bytes())
  if txt is None: continue
  scanned.append(str(p.relative_to(root))); compact=re.sub(r"\s+"," ",txt)
  for key,pat in HARD_BLOCK_PATTERNS.items():
   m=re.search(pat,compact,re.I)
   if m:
    hits.append({"rule":key,"file":str(p.relative_to(root)),
      "context":compact[max(0,m.start()-180):min(len(compact),m.end()+220)]})
 return {"policy":"fail_closed_for_public_artifact_or_explicit_conversion_restriction",
   "scanned_text_files":scanned,"restriction_hits":hits,
   "private_conversion_allowed":not hits,"redistribution_verified":False,
   "rights_note":"PRIVATE_TEST_ONLY_NO_REDISTRIBUTION_ASSERTION; no explicit restriction phrase found in bundled text"
      if not hits else "BLOCKED_BY_BUNDLED_RIGHTS_TEXT"}

def choose_car_root(extract_dir:Path,tokens:list[str])->Path:
 candidates=[]
 for lod in extract_dir.rglob("data/lods.ini"):
  root=lod.parent.parent.resolve()
  s=str(root).lower()
  score=sum(10 for t in tokens if t and t.lower() in s)
  candidates.append((score,root))
 if candidates:
  candidates.sort(key=lambda x:(-x[0],len(str(x[1]))))
  return candidates[0][1]
 kn5_dirs={}
 for p in extract_dir.rglob("*.kn5"):
  if p.is_file():
   root=p.parent.resolve(); kn5_dirs[root]=kn5_dirs.get(root,0)+p.stat().st_size
 if not kn5_dirs: raise RuntimeError("Downloaded archive contains no KN5 files")
 return max(kn5_dirs,key=kn5_dirs.get)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--work",type=Path,required=True)
 ap.add_argument("--page-url",required=True)
 ap.add_argument("--token",action="append",default=[])
 ns=ap.parse_args()
 work=ns.work.resolve();work.mkdir(parents=True,exist_ok=True)
 page=work/"dlcfun_page.html"; download(ns.page_url,page)
 signed_url,filename=extract_signed_url(page.read_text(encoding="utf-8",errors="ignore"))
 archive=work/Path(filename).name; download(signed_url,archive,ns.page_url)
 extract_dir=work/"source";extract_dir.mkdir(exist_ok=True)
 with zipfile.ZipFile(archive) as zf:
  bad=zf.testzip()
  if bad: raise RuntimeError(f"ZIP CRC failure at {bad}")
  zf.extractall(extract_dir)
  entries=[{"name":i.filename,"bytes":i.file_size} for i in zf.infolist() if not i.is_dir()]
 rights=rights_audit(extract_dir)
 car_root=choose_car_root(extract_dir,[t.lower() for t in ns.token])
 report={"page_url":ns.page_url,"archive_name":archive.name,"archive_bytes":archive.stat().st_size,
   "archive_sha256":sha256(archive),"archive_entries":entries,"car_root":str(car_root),"rights":rights}
 (work/"source_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False,indent=2))
 print(f"CAR_ROOT={car_root}")
 if not rights["private_conversion_allowed"]:
  print("BLOCKED: bundled text contains explicit sharing/conversion/porting restriction",file=sys.stderr)
  return 20
 return 0

if __name__=="__main__": raise SystemExit(main())

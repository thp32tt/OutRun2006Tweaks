#!/usr/bin/env python3
"""Pull read-only original upstream HARD PSD from pinned upstream commit.
Only stores in isolated QA subdirectory; verifies Git object SHA and size.
"""
from pathlib import Path
import urllib.parse,urllib.request,hashlib,json,os
B=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/qa_review_20261018')
targetdir=B/'upstream_psd_evidence'
targetdir.mkdir(parents=True,exist_ok=True)
name='33491F83_512x256.psd'
p=targetdir/name
sha='3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6'
git_blob_sha='e22ed4d6b9f7d8464fc40d724dd0b1d37e306104'
url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/'+sha+'/'+urllib.parse.quote('PSDs, XCFs, SVGs, and other Working Source Assets/OutRun2SP Mode UI/spr_sprani_loading_cvt_Exst/'+name)
if p.is_file():
 content=p.read_bytes()
else:
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'OutRun-SourceQA/1.0'}),timeout=90) as f:content=f.read()
 assert len(content)==8669875,('UNEXPECTED_UPSTREAM_BYTES',len(content))
 tmp=targetdir/(name+'.part')
 tmp.write_bytes(content)
 os.replace(tmp,p)
digest=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\x00'+content).hexdigest()
assert digest==git_blob_sha,(digest,git_blob_sha)
res={'status':'UPSTREAM_PSD_GIT_BLOB_VERIFIED','file':str(p),'bytes':len(content),
     'source_commit':sha,'git_blob_sha1':digest,
     'file_sha256':hashlib.sha256(content).hexdigest(),
     'QA_only':True,'no_live_original_change':True}
(targetdir/'hard_psd_upstream_receipt.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(res,ensure_ascii=False))
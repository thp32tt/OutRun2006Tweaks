#!/usr/bin/env python3
"""Reconstruct *ciphertext only* from public Git blobs, validate complete SHA."""
import argparse
import hashlib
import json
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for data in iter(lambda:f.read(1024*1024),b""):h.update(data)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--slot",choices=("A","C"),required=True)
    p.add_argument("--manifest-dir",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    folder=Path(a.manifest_dir).resolve()
    manifest=json.loads((folder/"manifest.json").read_text())
    if manifest.get("slot")!=a.slot or manifest.get("encrypted") is not True:
        raise SystemExit("BLOCKED_INPUT: wrong encrypted slot manifest")
    parts=manifest.get("parts",[])
    if not parts or len(parts)>256:
        raise SystemExit("BLOCKED_INPUT: invalid encrypted part count")
    out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    total=0
    with out.open("wb") as w:
        for index,name in enumerate(parts):
            expected=f"part_{index:03d}.encbin"
            if name!=expected:raise SystemExit("BLOCKED_INPUT: ciphertext part order mismatch")
            raw=(folder/name)
            if not raw.is_file():raise SystemExit("BLOCKED_INPUT: missing ciphertext part")
            with raw.open("rb") as r:
                while True:
                    buf=r.read(1024*1024)
                    if not buf:break
                    total+=len(buf)
                    if total>256*1024*1024:raise SystemExit("BLOCKED_SIZE")
                    w.write(buf)
    if total!=manifest["expected_ciphertext_size"] or sha(out)!=manifest["ciphertext_sha256"]:
        out.unlink(missing_ok=True)
        raise SystemExit("BLOCKED_INPUT: ciphertext SHA256 mismatch")
    print(json.dumps({"status":"CIPHERTEXT_REASSEMBLY_VERIFIED","slot":a.slot,
                      "bytes":total,"sha256":manifest["ciphertext_sha256"]}))
if __name__=="__main__":main()

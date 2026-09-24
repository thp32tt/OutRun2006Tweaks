#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

def add_hangul(text, out):
    for ch in text or "":
        if "\uac00" <= ch <= "\ud7a3":
            out.add(ch)

def collect(text_jsonl, graphics_jsonl):
    chars=set()
    for line in Path(text_jsonl).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        add_hangul(json.loads(line).get("korean",""), chars)
    for line in Path(graphics_jsonl).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row=json.loads(line)
        for seg in row.get("segments",[]):
            add_hangul(seg.get("korean",""), chars)
    return chars

def main():
    ap=argparse.ArgumentParser(description="Build stable Hangul glyph manifest for Korean localization.")
    ap.add_argument("text_jsonl")
    ap.add_argument("graphics_jsonl")
    ap.add_argument("output_json")
    ap.add_argument("--existing", help="Existing manifest whose assigned indices should be preserved")
    args=ap.parse_args()

    active=collect(args.text_jsonl,args.graphics_jsonl)
    entries=[]
    assigned=set()

    if args.existing and Path(args.existing).exists():
        old=json.loads(Path(args.existing).read_text(encoding="utf-8"))
        for e in old.get("entries",[]):
            ch=e["char"]
            entries.append({"char":ch,"index":int(e["index"])})
            assigned.add(ch)

    next_index=max((e["index"] for e in entries),default=-1)+1
    for ch in sorted(active-assigned):
        entries.append({"char":ch,"index":next_index})
        next_index+=1

    entries.sort(key=lambda e:e["index"])
    for e in entries:
        i=e["index"]
        e.update({
            "codepoint":f"U+{ord(e['char']):04X}",
            "page":i//256,
            "cell":i%256,
            "row":(i%256)//16,
            "col":(i%256)%16,
            "active":e["char"] in active,
        })

    result={
        "schema_version":1,
        "glyph_count":len(entries),
        "active_glyph_count":sum(1 for e in entries if e["active"]),
        "page_capacity":256,
        "page_count":math.ceil(len(entries)/256) if entries else 0,
        "grid":{"columns":16,"rows":16},
        "entries":entries,
    }
    Path(args.output_json).write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    print(f"glyphs={result['glyph_count']} active={result['active_glyph_count']} pages={result['page_count']}")

if __name__=="__main__":
    main()

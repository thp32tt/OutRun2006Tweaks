#!/usr/bin/env python3
import argparse
import csv
import glob
import hashlib
import json
import re
import struct
from pathlib import Path

MAGIC = b"txet"
PLACEHOLDER_RE = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?)?[a-zA-Z%]')


def parse_txet(path: Path):
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != MAGIC:
        raise ValueError("not a txet file")
    declared = struct.unpack_from('<I', data, 4)[0]
    if declared != len(data):
        raise ValueError(f"size mismatch: header={declared} actual={len(data)}")
    first = struct.unpack_from('<I', data, 8)[0]
    if first < 8 or (first - 8) % 4:
        raise ValueError(f"invalid first payload offset: 0x{first:X}")
    count = (first - 8) // 4
    offsets = list(struct.unpack_from(f'<{count}I', data, 8))
    records=[]
    for i, off in enumerate(offsets):
        if not off:
            records.append(None)
            continue
        end=len(data)
        for nxt in offsets[i+1:]:
            if nxt:
                end=nxt
                break
        records.append(data[off:end])
    return data, records


def first_utf16_segment(raw: bytes):
    if raw is None:
        return None, None
    for pos in range(0, len(raw)-1, 2):
        if raw[pos:pos+2] == b'\x00\x00':
            return raw[:pos].decode('utf-16le'), pos+2
    raise ValueError('record has no aligned UTF-16 NUL terminator')


def load_translations(directory: Path):
    items={}
    canonical = directory / 'korean_all.jsonl'
    files = [canonical] if canonical.exists() else sorted(p for p in directory.glob('korean_*.jsonl') if p.name != 'korean_all.jsonl')
    for filename in files:
        for line_no, line in enumerate(filename.read_text(encoding='utf-8').splitlines(),1):
            if not line.strip():
                continue
            obj=json.loads(line)
            idx=int(obj['id'])
            if idx in items:
                raise ValueError(f'duplicate id {idx} in {filename}:{line_no}')
            items[idx]=obj
    return items


def build(records, translations, special):
    out_records=[]
    qa=[]
    for idx, raw in enumerate(records):
        item=translations.get(idx)
        if raw is None:
            if item and item.get('status') != 'blocked_null':
                raise ValueError(f'id {idx}: source is NULL but translation status is not blocked_null')
            out_records.append(None)
            continue
        if item is None:
            raise ValueError(f'id {idx}: missing translation row')
        expected=item['source_hash']
        actual=hashlib.sha256(raw).hexdigest()[:16]
        if actual != expected:
            raise ValueError(f'id {idx}: source hash mismatch expected={expected} actual={actual}')
        source, tail_at=first_utf16_segment(raw)
        korean=item.get('korean','')
        source_ph=PLACEHOLDER_RE.findall(source or '')
        korean_ph=PLACEHOLDER_RE.findall(korean)
        if source_ph != korean_ph:
            raise ValueError(f'id {idx}: placeholder mismatch {source_ph} != {korean_ph}')
        if str(idx) in special:
            if special[str(idx)].get('tail_policy') != 'preserve_raw_after_first_nul':
                raise ValueError(f'id {idx}: unsupported special tail policy')
            replacement=special[str(idx)]['korean_segment0'].encode('utf-16le')+b'\x00\x00'
            replacement += raw[tail_at:]
        else:
            # Normal records must consist of exactly one UTF-16 string + terminator.
            if tail_at != len(raw):
                raise ValueError(f'id {idx}: special/multi record missing special policy')
            replacement=korean.encode('utf-16le')+b'\x00\x00'
        out_records.append(replacement)
        qa.append((idx,item.get('status','')))
    count=len(out_records)
    header_size=8+4*count
    offsets=[]
    payload=bytearray()
    for raw in out_records:
        if raw is None:
            offsets.append(0)
        else:
            offsets.append(header_size+len(payload))
            payload += raw
    total=header_size+len(payload)
    data=bytearray(MAGIC)+struct.pack('<I',total)+struct.pack(f'<{count}I',*offsets)+payload
    return bytes(data), qa


def main():
    ap=argparse.ArgumentParser(description='Build OutRun 2006 Korean txet draft from resumable translation chunks.')
    ap.add_argument('source_bin', type=Path)
    ap.add_argument('translation_dir', type=Path)
    ap.add_argument('output_bin', type=Path)
    args=ap.parse_args()
    original, records=parse_txet(args.source_bin)
    translations=load_translations(args.translation_dir)
    special_path=args.translation_dir/'special_records.json'
    special=json.loads(special_path.read_text(encoding='utf-8')) if special_path.exists() else {}
    if len(translations) != len(records):
        missing=sorted(set(range(len(records)))-set(translations))
        extra=sorted(set(translations)-set(range(len(records))))
        raise SystemExit(f'translation coverage mismatch: rows={len(translations)} records={len(records)} missing={missing[:20]} extra={extra[:20]}')
    built, qa=build(records,translations,special)
    args.output_bin.write_bytes(built)
    statuses={}
    for _,status in qa: statuses[status]=statuses.get(status,0)+1
    print(f'entries={len(records)} source_size={len(original)} output_size={len(built)}')
    print(f'output_sha256={hashlib.sha256(built).hexdigest()}')
    print('statuses='+json.dumps(statuses,ensure_ascii=False,sort_keys=True))
    print('NOTE: resource build passed; stock runtime still cannot render Hangul until Unicode/glyph hooks are enabled.')

if __name__ == '__main__':
    main()
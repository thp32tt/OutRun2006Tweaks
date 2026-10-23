#!/usr/bin/env python3
"""Query the OR2006C2C executable knowledge map by RVA/VA, text, or semantic tag."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path


def hx(v): return None if v is None else f"0x{v:08X}"

def parse_addr(text: str):
    t = text.strip()
    if not re.fullmatch(r"(?:0x)?[0-9a-fA-F]{4,16}", t): return None
    return int(t, 16)


def image_base(con):
    row = con.execute("SELECT value FROM meta WHERE key='image_base'").fetchone()
    if not row: return 0x400000
    try: return int(json.loads(row[0]), 0)
    except Exception: return int(row[0], 0)


def normalize_rva(con, value):
    base = image_base(con)
    return value - base if value >= base else value


def show_address(con, raw, context):
    rva = normalize_rva(con, raw)
    f = con.execute("SELECT * FROM functions WHERE body_min_rva<=? AND body_max_rva>=? ORDER BY size ASC LIMIT 1", (rva,rva)).fetchone()
    print(f"ADDRESS RVA={hx(rva)} VA={hx(rva+image_base(con))}")
    if f:
        print(f"FUNCTION {hx(f['entry_rva'])} {f['namespace']}::{f['name']} size={f['size']}")
        entry = f["entry_rva"]
        callers = con.execute(
            """SELECT c.caller_rva, fn.name, count(*) AS n
               FROM calls c LEFT JOIN functions fn ON fn.entry_rva=c.caller_rva
               WHERE c.callee_function_rva=?
               GROUP BY c.caller_rva, fn.name ORDER BY n DESC, c.caller_rva LIMIT 40""",
            (entry,),
        ).fetchall()
        callees = con.execute(
            """SELECT c.callee_function_rva, c.callee_rva, fn.name, count(*) AS n
               FROM calls c LEFT JOIN functions fn ON fn.entry_rva=c.callee_function_rva
               WHERE c.caller_rva=?
               GROUP BY c.callee_function_rva, c.callee_rva, fn.name
               ORDER BY n DESC LIMIT 60""",
            (entry,),
        ).fetchall()
        string_refs = con.execute(
            """SELECT s.rva, s.value, count(*) AS n
               FROM xrefs x JOIN strings s ON s.rva=x.to_rva
               WHERE x.from_function_rva=?
               GROUP BY s.rva, s.value ORDER BY n DESC, s.rva LIMIT 40""",
            (entry,),
        ).fetchall()
        if callers:
            print("CALLERS")
            for x in callers:
                print(f"  {hx(x['caller_rva'])} {x['name'] or '<unknown>'} refs={x['n']}")
        if callees:
            print("CALLEES")
            for x in callees:
                target = x["callee_function_rva"] if x["callee_function_rva"] is not None else x["callee_rva"]
                print(f"  {hx(target)} {x['name'] or '<unknown/external>'} calls={x['n']}")
        if string_refs:
            print("STRING_REFS")
            for x in string_refs:
                value = str(x["value"]).replace("\\n", "\\\\n")
                print(f"  {hx(x['rva'])} refs={x['n']} {value[:180]}")
    sem = con.execute("SELECT * FROM semantics WHERE rva BETWEEN ? AND ? ORDER BY rva", (max(0,rva-context*16), rva+context*16)).fetchall()
    for s in sem:
        print(f"SEMANTIC {s['id']} {hx(s['rva'])} [{s['tags']}] confidence={s['confidence']} :: {s['notes']}")
    rows = con.execute("SELECT * FROM instructions WHERE rva BETWEEN ? AND ? ORDER BY rva", (max(0,rva-context*16), rva+context*16)).fetchall()
    for x in rows:
        mark = ">" if x['rva'] == rva else " "
        print(f"{mark} {hx(x['rva'])}  {x['bytes']:<24} {x['text']}")
    incoming = con.execute("SELECT from_rva,from_function_rva,type FROM xrefs WHERE to_rva=? ORDER BY from_rva LIMIT 40", (rva,)).fetchall()
    outgoing = con.execute("SELECT to_rva,to_function_rva,type FROM xrefs WHERE from_rva=? ORDER BY to_rva LIMIT 40", (rva,)).fetchall()
    if incoming:
        print("XREF_IN")
        for x in incoming: print(f"  {hx(x['from_rva'])} func={hx(x['from_function_rva'])} {x['type']}")
    if outgoing:
        print("XREF_OUT")
        for x in outgoing: print(f"  {hx(x['to_rva'])} func={hx(x['to_function_rva'])} {x['type']}")


def plain_search(con, q, limit):
    like = f"%{q}%"
    sections = [
        ("SEMANTICS", "SELECT id,rva,name,tags,notes FROM semantics WHERE id LIKE ? OR name LIKE ? OR tags LIKE ? OR notes LIKE ? LIMIT ?", (like,like,like,like,limit)),
        ("FUNCTIONS", "SELECT entry_rva,name,namespace,size FROM functions WHERE name LIKE ? OR namespace LIKE ? LIMIT ?", (like,like,limit)),
        ("STRINGS", "SELECT rva,value,datatype FROM strings WHERE value LIKE ? LIMIT ?", (like,limit)),
        ("INSTRUCTIONS", "SELECT rva,function_rva,text FROM instructions WHERE text LIKE ? LIMIT ?", (like,limit)),
        ("IMPORTS", "SELECT entry_rva,name,namespace FROM imports WHERE name LIKE ? OR namespace LIKE ? LIMIT ?", (like,like,limit)),
    ]
    for title, sql, params in sections:
        rows = con.execute(sql, params).fetchall()
        if not rows: continue
        print(title)
        for r in rows:
            print("  " + " | ".join(f"{k}={hx(r[k]) if k.endswith('rva') and r[k] is not None else r[k]}" for k in r.keys()))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--db", default="reverse/OR2006C2C/exe_map.sqlite", type=Path)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--context", type=int, default=10)
    args=ap.parse_args()
    con=sqlite3.connect(args.db)
    con.row_factory=sqlite3.Row
    try:
        addr=parse_addr(args.query)
        if addr is not None: show_address(con, addr, args.context)
        else: plain_search(con, args.query, args.limit)
    finally: con.close()

if __name__ == "__main__": main()

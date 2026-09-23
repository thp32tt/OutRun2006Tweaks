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
    kind = "auto"
    m = re.fullmatch(r"(?:(rva|va):)?((?:0x)?[0-9a-fA-F]{4,16})", t, re.IGNORECASE)
    if not m:
        return None
    if m.group(1):
        kind = m.group(1).lower()
    return kind, int(m.group(2), 16)


def image_base(con):
    row = con.execute("SELECT value FROM meta WHERE key='image_base'").fetchone()
    if not row: return 0x400000
    try: return int(json.loads(row[0]), 0)
    except Exception: return int(row[0], 0)


def normalize_rva(con, value, kind="auto"):
    base = image_base(con)
    if kind == "rva":
        return value
    if kind == "va":
        if value < base:
            raise ValueError(f"VA 0x{value:X} is below image base 0x{base:X}")
        return value - base
    return value - base if value >= base else value


def show_address(con, raw, context, address_kind="auto"):
    rva = normalize_rva(con, raw, address_kind)
    owner_source = None
    insn = con.execute(
        "SELECT function_rva FROM instructions WHERE rva=? LIMIT 1", (rva,)
    ).fetchone()
    f = None
    if insn and insn["function_rva"] is not None:
        f = con.execute(
            "SELECT * FROM functions WHERE entry_rva=? LIMIT 1",
            (insn["function_rva"],),
        ).fetchone()
        if f:
            owner_source = "exact-instruction"
    if not f:
        f = con.execute(
            "SELECT * FROM functions WHERE body_min_rva<=? AND body_max_rva>=? ORDER BY size ASC LIMIT 1",
            (rva, rva),
        ).fetchone()
        if f:
            owner_source = "range-fallback"
    print(f"ADDRESS RVA={hx(rva)} VA={hx(rva+image_base(con))}")
    if f:
        print(f"FUNCTION_OWNER {owner_source}")
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


def fts_enabled(con):
    row = con.execute("SELECT value FROM meta WHERE key='fts5'").fetchone()
    if not row:
        return False
    return str(row[0]).strip().lower() in ("true", "1", '"true"')


def display_value(key, value):
    if value is None:
        return value
    if key.endswith("rva"):
        if isinstance(value, int):
            return hx(value)
        return str(value)
    return value


def plain_search(con, q, limit):
    like = f"%{q}%"
    used_fts = fts_enabled(con)
    rows_by_section = []
    if used_fts:
        phrase = '"' + q.replace('"', '""') + '"'
        try:
            rows_by_section.extend([
                ("SEMANTICS", con.execute(
                    "SELECT id,rva,name,tags,notes FROM fts_semantics WHERE fts_semantics MATCH ? LIMIT ?",
                    (phrase, limit)).fetchall()),
                ("FUNCTIONS", con.execute(
                    "SELECT entry_rva,name,namespace,NULL AS size FROM fts_functions WHERE fts_functions MATCH ? LIMIT ?",
                    (phrase, limit)).fetchall()),
                ("STRINGS", con.execute(
                    "SELECT rva,value,datatype FROM fts_strings WHERE fts_strings MATCH ? LIMIT ?",
                    (phrase, limit)).fetchall()),
                ("INSTRUCTIONS", con.execute(
                    "SELECT rva,function_rva,text FROM fts_instructions WHERE fts_instructions MATCH ? LIMIT ?",
                    (phrase, limit)).fetchall()),
            ])
        except sqlite3.OperationalError:
            rows_by_section = []
            used_fts = False

    if not used_fts:
        sections = [
            ("SEMANTICS", "SELECT id,rva,name,tags,notes FROM semantics WHERE id LIKE ? OR name LIKE ? OR tags LIKE ? OR notes LIKE ? LIMIT ?", (like,like,like,like,limit)),
            ("FUNCTIONS", "SELECT entry_rva,name,namespace,size FROM functions WHERE name LIKE ? OR namespace LIKE ? LIMIT ?", (like,like,limit)),
            ("STRINGS", "SELECT rva,value,datatype FROM strings WHERE value LIKE ? LIMIT ?", (like,limit)),
            ("INSTRUCTIONS", "SELECT rva,function_rva,text FROM instructions WHERE text LIKE ? LIMIT ?", (like,limit)),
        ]
        rows_by_section.extend(
            (title, con.execute(sql, params).fetchall())
            for title, sql, params in sections
        )

    rows_by_section.append((
        "IMPORTS",
        con.execute(
            "SELECT entry_rva,name,namespace FROM imports WHERE name LIKE ? OR namespace LIKE ? LIMIT ?",
            (like, like, limit),
        ).fetchall(),
    ))
    for title, rows in rows_by_section:
        if not rows:
            continue
        print(title + (" [FTS5]" if used_fts and title != "IMPORTS" else ""))
        for r in rows:
            print("  " + " | ".join(
                f"{k}={display_value(k, r[k])}" for k in r.keys()
            ))


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
        if addr is not None:
            address_kind, address_value = addr
            show_address(con, address_value, args.context, address_kind)
        else:
            plain_search(con, args.query, args.limit)
    finally: con.close()

if __name__ == "__main__": main()

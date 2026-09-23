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
    m = re.fullmatch(r"(?:(rva|va):)?((?:0x)?[0-9a-fA-F]{4,16})", t, re.IGNORECASE)
    if not m:
        return None
    return (m.group(1).lower() if m.group(1) else "auto", int(m.group(2), 16))


def image_base(con):
    row = con.execute("SELECT value FROM meta WHERE key='image_base'").fetchone()
    if not row: return 0x400000
    try: return int(json.loads(row[0]), 0)
    except Exception: return int(row[0], 0)


def table_exists(con, name):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def address_exists(con, rva):
    checks = [
        ("instructions", "rva"),
        ("functions", "entry_rva"),
        ("strings", "rva"),
        ("semantics", "rva"),
    ]
    for table, column in checks:
        if con.execute(f"SELECT 1 FROM {table} WHERE {column}=? LIMIT 1", (rva,)).fetchone():
            return True
    if table_exists(con, "function_ranges"):
        if con.execute("SELECT 1 FROM function_ranges WHERE start_rva<=? AND end_rva>=? LIMIT 1", (rva, rva)).fetchone():
            return True
    for sql in (
        "SELECT 1 FROM xrefs WHERE from_rva=? OR to_rva=? LIMIT 1",
        "SELECT 1 FROM calls WHERE callsite_rva=? OR callee_rva=? LIMIT 1",
    ):
        if con.execute(sql, (rva, rva)).fetchone():
            return True
    return False


def normalize_rva(con, kind, value):
    base = image_base(con)
    if kind == "rva":
        return value
    if kind == "va":
        if value < base:
            raise SystemExit(f"VA {hx(value)} is below image base {hx(base)}")
        return value - base
    if value < base:
        return value

    raw_rva = value
    va_rva = value - base
    raw_exists = address_exists(con, raw_rva)
    va_exists = address_exists(con, va_rva)
    if raw_exists and va_exists:
        raise SystemExit(
            f"Ambiguous address {hx(value)}: both rva:{hx(raw_rva)} and va:{hx(value)} -> rva:{hx(va_rva)} exist; "
            "use an explicit rva: or va: prefix"
        )
    if raw_exists:
        return raw_rva
    if va_exists:
        return va_rva
    raise SystemExit(
        f"Address {hx(value)} is >= image base and cannot be inferred safely; use rva:{hx(value)} or va:{hx(value)} explicitly"
    )


def function_for_rva(con, rva):
    ins = con.execute("SELECT function_rva FROM instructions WHERE rva=?", (rva,)).fetchone()
    if ins and ins["function_rva"] is not None:
        return con.execute("SELECT * FROM functions WHERE entry_rva=?", (ins["function_rva"],)).fetchone()
    if table_exists(con, "function_ranges"):
        return con.execute(
            """SELECT f.* FROM function_ranges fr
               JOIN functions f ON f.entry_rva=fr.entry_rva
               WHERE fr.start_rva<=? AND fr.end_rva>=?
               ORDER BY (fr.end_rva-fr.start_rva) ASC LIMIT 1""",
            (rva, rva),
        ).fetchone()
    return con.execute(
        "SELECT * FROM functions WHERE body_min_rva<=? AND body_max_rva>=? ORDER BY size ASC LIMIT 1",
        (rva, rva),
    ).fetchone()


def show_address(con, kind, raw, context):
    rva = normalize_rva(con, kind, raw)
    f = function_for_rva(con, rva)
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


def _print_rows(title, rows):
    if not rows:
        return False
    print(title)
    for r in rows:
        print("  " + " | ".join(
            f"{k}={hx(r[k]) if k.endswith('rva') and r[k] is not None and isinstance(r[k], int) else r[k]}"
            for k in r.keys()
        ))
    return True


def plain_search(con, q, limit):
    used_fts = False
    fts_row = con.execute("SELECT value FROM meta WHERE key='fts5'").fetchone()
    if fts_row and str(fts_row[0]).lower() == "true":
        term = '"' + q.replace('"', '""') + '"'
        try:
            fts_sections = [
                ("SEMANTICS", "SELECT id,rva,name,tags,notes FROM fts_semantics WHERE fts_semantics MATCH ? LIMIT ?", (term, limit)),
                ("FUNCTIONS", "SELECT entry_rva,name,namespace,return_type FROM fts_functions WHERE fts_functions MATCH ? LIMIT ?", (term, limit)),
                ("STRINGS", "SELECT rva,value,datatype FROM fts_strings WHERE fts_strings MATCH ? LIMIT ?", (term, limit)),
                ("INSTRUCTIONS", "SELECT rva,function_rva,text,mnemonic FROM fts_instructions WHERE fts_instructions MATCH ? LIMIT ?", (term, limit)),
            ]
            for title, sql, params in fts_sections:
                used_fts = _print_rows(title, con.execute(sql, params).fetchall()) or used_fts
        except sqlite3.OperationalError:
            used_fts = False
    if used_fts:
        return

    like = f"%{q}%"
    sections = [
        ("SEMANTICS", "SELECT id,rva,name,tags,notes FROM semantics WHERE id LIKE ? OR name LIKE ? OR tags LIKE ? OR notes LIKE ? LIMIT ?", (like,like,like,like,limit)),
        ("FUNCTIONS", "SELECT entry_rva,name,namespace,size FROM functions WHERE name LIKE ? OR namespace LIKE ? LIMIT ?", (like,like,limit)),
        ("STRINGS", "SELECT rva,value,datatype FROM strings WHERE value LIKE ? LIMIT ?", (like,limit)),
        ("INSTRUCTIONS", "SELECT rva,function_rva,text FROM instructions WHERE text LIKE ? LIMIT ?", (like,limit)),
        ("IMPORTS", "SELECT entry_rva,name,namespace FROM imports WHERE name LIKE ? OR namespace LIKE ? LIMIT ?", (like,like,limit)),
    ]
    for title, sql, params in sections:
        _print_rows(title, con.execute(sql, params).fetchall())


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
            kind, value = addr
            show_address(con, kind, value, args.context)
        else:
            plain_search(con, args.query, args.limit)
    finally: con.close()

if __name__ == "__main__": main()

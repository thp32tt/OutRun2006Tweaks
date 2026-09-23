#!/usr/bin/env python3
"""Query the OutRun whole-EXE SQLite knowledge map."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from typing import Iterable


HEX_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{4,8}$")


def parse_rva(text: str) -> int | None:
    value = text.strip()
    if not HEX_RE.match(value):
        return None
    if not value.lower().startswith("0x"):
        value = "0x" + value
    return int(value, 16)


def rows(conn: sqlite3.Connection, sql: str, params: Iterable[object] = ()) -> list[dict]:
    cur = conn.execute(sql, tuple(params))
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def format_rva(value: int | None) -> str:
    return "-" if value is None else f"0x{value:08X}"


def print_json(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def normalize_address(conn: sqlite3.Connection, value: int) -> int:
    row = conn.execute(
        "SELECT value FROM meta WHERE key IN ('contract.imageBase','export.imageBase') "
        "ORDER BY CASE key WHEN 'contract.imageBase' THEN 0 ELSE 1 END LIMIT 1"
    ).fetchone()
    if not row:
        return value
    try:
        base = int(str(row[0]), 0)
    except (TypeError, ValueError):
        return value
    return value - base if value >= base else value


def query_rva(conn: sqlite3.Connection, rva: int) -> dict:
    exact_instruction = rows(
        conn,
        "SELECT function_rva FROM instructions WHERE rva=? AND function_rva IS NOT NULL LIMIT 1",
        (rva,),
    )
    if exact_instruction:
        fn = rows(conn, "SELECT * FROM functions WHERE rva=?", (exact_instruction[0]["function_rva"],))
    else:
        fn = rows(
            conn,
            """SELECT * FROM functions
               WHERE min_rva IS NOT NULL AND max_rva IS NOT NULL
                 AND min_rva <= ? AND ? <= max_rva
               ORDER BY (max_rva - min_rva) ASC, rva DESC LIMIT 1""",
            (rva, rva),
        )
    exact_fn = rows(conn, "SELECT * FROM functions WHERE rva=?", (rva,))
    ins = rows(
        conn,
        """SELECT rva,rva_hex,address,function_rva,mnemonic,text,bytes
           FROM instructions WHERE rva BETWEEN ? AND ?
           ORDER BY rva LIMIT 25""",
        (max(0, rva - 32), rva + 96),
    )
    incoming_calls = rows(
        conn,
        """SELECT site_rva,caller_rva,target_rva,target_name
           FROM calls WHERE target_rva=? ORDER BY site_rva LIMIT 50""",
        (rva,),
    )
    owner_rva = exact_fn[0]["rva"] if exact_fn else (fn[0]["rva"] if fn else rva)
    outgoing_calls = rows(
        conn,
        """SELECT site_rva,caller_rva,target_rva,target_name
           FROM calls WHERE caller_rva=?
           ORDER BY site_rva LIMIT 100""",
        (owner_rva,),
    )
    xrefs_in = rows(
        conn,
        "SELECT from_rva,to_rva,type,source FROM xrefs WHERE to_rva=? ORDER BY from_rva LIMIT 100",
        (rva,),
    )
    xrefs_out = rows(
        conn,
        "SELECT from_rva,to_rva,type,source FROM xrefs WHERE from_rva=? ORDER BY to_rva LIMIT 100",
        (rva,),
    )
    strings = rows(
        conn,
        "SELECT rva,rva_hex,address,length,value FROM strings WHERE rva BETWEEN ? AND ? ORDER BY rva",
        (max(0, rva - 64), rva + 128),
    )
    ann = rows(conn, "SELECT * FROM annotations WHERE rva=?", (rva,))
    bindings = rows(conn, "SELECT * FROM source_bindings WHERE rva=?", (rva,))

    return {
        "queryRva": format_rva(rva),
        "exactFunction": exact_fn,
        "containingFunction": fn,
        "instructions": ins,
        "incomingCalls": incoming_calls,
        "outgoingCalls": outgoing_calls,
        "incomingXrefs": xrefs_in,
        "outgoingXrefs": xrefs_out,
        "nearbyStrings": strings,
        "annotations": ann,
        "sourceBindings": bindings,
    }


def quote_fts_terms(text: str) -> str:
    terms = [t for t in re.split(r"\s+", text.strip()) if t]
    return " AND ".join('"' + t.replace('"', '""') + '"' for t in terms)


def query_text(conn: sqlite3.Connection, text: str, limit: int) -> list[dict]:
    has_fts = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='search_fts'"
    ).fetchone()
    if has_fts:
        try:
            return rows(
                conn,
                """SELECT kind,rva,name,
                          snippet(search_fts,3,'[',']',' … ',18) AS snippet
                   FROM search_fts
                   WHERE search_fts MATCH ?
                   LIMIT ?""",
                (quote_fts_terms(text), limit),
            )
        except sqlite3.OperationalError:
            pass
    like = "%" + text + "%"
    return rows(
        conn,
        """SELECT kind,rva,name,substr(content,1,500) AS snippet
           FROM search_docs
           WHERE content LIKE ? OR name LIKE ?
           LIMIT ?""",
        (like, like, limit),
    )


def print_human_rva(result: dict) -> None:
    print(f"RVA {result['queryRva']}")
    fn = result["exactFunction"] or result["containingFunction"]
    if fn:
        f = fn[0]
        print(f"function: {f.get('name')} @ {f.get('rva_hex')}  {f.get('signature') or ''}")
        if f.get("decompile_c"):
            text = f["decompile_c"].strip()
            if len(text) > 3500:
                text = text[:3500] + "\n... <truncated; use --json or SQLite for full decompile>"
            print("\n[decompile]\n" + text)

    for title, key in (
        ("annotations", "annotations"),
        ("source bindings", "sourceBindings"),
        ("incoming calls", "incomingCalls"),
        ("outgoing calls", "outgoingCalls"),
        ("incoming xrefs", "incomingXrefs"),
        ("outgoing xrefs", "outgoingXrefs"),
        ("nearby strings", "nearbyStrings"),
    ):
        vals = result[key]
        if vals:
            print(f"\n[{title}]")
            for row in vals[:25]:
                print(json.dumps(row, ensure_ascii=False))

    if result["instructions"]:
        print("\n[instructions]")
        for row in result["instructions"]:
            marker = ">" if row["rva"] == int(result["queryRva"], 16) else " "
            print(f"{marker} {row['rva_hex']}  {row['text']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("query", nargs="+", help="RVA/address-like hex or search words")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    query = " ".join(args.query).strip()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        rva = parse_rva(query)
        if rva is not None:
            rva = normalize_address(conn, rva)
            result = query_rva(conn, rva)
            if args.json:
                print_json(result)
            else:
                print_human_rva(result)
            return 0

        result = query_text(conn, query, args.limit)
        if args.json:
            print_json(result)
            return 0

        print(f"search: {query}")
        for row in result:
            print(
                f"{row['kind']:<10} {format_rva(row['rva']):<12} "
                f"{(row['name'] or ''):<40} {row['snippet'] or ''}"
            )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

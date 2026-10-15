#!/usr/bin/env python3
"""Build a searchable SQLite knowledge map from Ghidra JSONL exports."""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
from typing import Iterable

SCHEMA_VERSION = 1


def parse_int(v):
    if v is None or v == "":
        return None
    if isinstance(v, int):
        return v
    return int(str(v), 0)


def read_jsonl(path: pathlib.Path) -> Iterable[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}") from exc


def connect(path: pathlib.Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(
        """
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE functions(
          entry_rva INTEGER PRIMARY KEY, entry_va INTEGER, name TEXT, namespace TEXT,
          size INTEGER, body_min_rva INTEGER, body_max_rva INTEGER,
          thunk INTEGER, external INTEGER, calling_convention TEXT,
          parameter_count INTEGER, return_type TEXT
        );
        CREATE TABLE instructions(
          rva INTEGER PRIMARY KEY, va INTEGER, function_rva INTEGER,
          mnemonic TEXT, text TEXT, bytes TEXT
        );
        CREATE TABLE calls(
          id INTEGER PRIMARY KEY, callsite_rva INTEGER, caller_rva INTEGER,
          callee_va INTEGER, callee_rva INTEGER, callee_function_rva INTEGER, type TEXT
        );
        CREATE TABLE xrefs(
          id INTEGER PRIMARY KEY, from_rva INTEGER, from_function_rva INTEGER,
          to_va INTEGER, to_rva INTEGER, to_function_rva INTEGER, type TEXT, primary_ref INTEGER
        );
        CREATE TABLE strings(
          rva INTEGER PRIMARY KEY, va INTEGER, function_rva INTEGER,
          datatype TEXT, length INTEGER, value TEXT
        );
        CREATE TABLE imports(
          id INTEGER PRIMARY KEY, name TEXT, namespace TEXT, entry_va INTEGER,
          entry_rva INTEGER, calling_convention TEXT
        );
        CREATE TABLE semantics(
          id TEXT PRIMARY KEY, rva INTEGER, kind TEXT, name TEXT,
          tags TEXT, confidence TEXT, evidence TEXT, notes TEXT, source TEXT
        );
        CREATE INDEX idx_instr_function ON instructions(function_rva, rva);
        CREATE INDEX idx_calls_caller ON calls(caller_rva);
        CREATE INDEX idx_calls_callee ON calls(callee_function_rva, callee_rva);
        CREATE INDEX idx_xrefs_from ON xrefs(from_rva, from_function_rva);
        CREATE INDEX idx_xrefs_to ON xrefs(to_rva, to_function_rva);
        CREATE INDEX idx_strings_function ON strings(function_rva);
        CREATE INDEX idx_semantics_rva ON semantics(rva);
        """
    )
    return con


def insert_export(con: sqlite3.Connection, export_dir: pathlib.Path) -> dict:
    program = next(iter(read_jsonl(export_dir / "program.jsonl")), {})
    for k, v in program.items():
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (str(k), json.dumps(v, ensure_ascii=False)))
    con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))

    for r in read_jsonl(export_dir / "functions.jsonl"):
        con.execute("INSERT INTO functions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
            parse_int(r.get("entry_rva")), parse_int(r.get("entry_va")), r.get("name"), r.get("namespace"),
            r.get("size"), parse_int(r.get("body_min_rva")), parse_int(r.get("body_max_rva")),
            int(bool(r.get("thunk"))), int(bool(r.get("external"))), r.get("calling_convention"),
            r.get("parameter_count"), r.get("return_type")))

    for r in read_jsonl(export_dir / "instructions.jsonl"):
        con.execute("INSERT INTO instructions VALUES(?,?,?,?,?,?)", (
            parse_int(r.get("rva")), parse_int(r.get("va")), parse_int(r.get("function_rva")),
            r.get("mnemonic"), r.get("text"), r.get("bytes")))

    for r in read_jsonl(export_dir / "calls.jsonl"):
        con.execute("INSERT INTO calls(callsite_rva,caller_rva,callee_va,callee_rva,callee_function_rva,type) VALUES(?,?,?,?,?,?)", (
            parse_int(r.get("callsite_rva")), parse_int(r.get("caller_rva")), parse_int(r.get("callee_va")),
            parse_int(r.get("callee_rva")), parse_int(r.get("callee_function_rva")), r.get("type")))

    for r in read_jsonl(export_dir / "xrefs.jsonl"):
        con.execute("INSERT INTO xrefs(from_rva,from_function_rva,to_va,to_rva,to_function_rva,type,primary_ref) VALUES(?,?,?,?,?,?,?)", (
            parse_int(r.get("from_rva")), parse_int(r.get("from_function_rva")), parse_int(r.get("to_va")),
            parse_int(r.get("to_rva")), parse_int(r.get("to_function_rva")), r.get("type"), int(bool(r.get("primary")))))

    for r in read_jsonl(export_dir / "strings.jsonl"):
        con.execute("INSERT INTO strings VALUES(?,?,?,?,?,?)", (
            parse_int(r.get("rva")), parse_int(r.get("va")), parse_int(r.get("function_rva")),
            r.get("datatype"), r.get("length"), r.get("value")))

    for r in read_jsonl(export_dir / "imports.jsonl"):
        con.execute("INSERT INTO imports(name,namespace,entry_va,entry_rva,calling_convention) VALUES(?,?,?,?,?)", (
            r.get("name"), r.get("namespace"), parse_int(r.get("entry_va")), parse_int(r.get("entry_rva")), r.get("calling_convention")))
    return program


def insert_semantics(con: sqlite3.Connection, path: pathlib.Path | None):
    if not path or not path.exists():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    for r in doc.get("records", []):
        con.execute("INSERT OR REPLACE INTO semantics VALUES(?,?,?,?,?,?,?,?,?)", (
            r["id"], parse_int(r.get("rva")), r.get("kind", ""), r.get("name", ""),
            " ".join(r.get("tags", [])), r.get("confidence", ""), r.get("evidence", ""),
            r.get("notes", ""), str(path)))


def insert_binary_contract(con: sqlite3.Connection, path: pathlib.Path | None):
    if not path or not path.exists():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    canonical = doc.get("canonicalExe", {})
    expected = str(canonical.get("sha256", "")).lower()
    actual = json.loads(con.execute("SELECT value FROM meta WHERE key='sha256'").fetchone()[0] or 'null')
    if expected and actual and expected != str(actual).lower():
        raise SystemExit(f"binary-contract SHA mismatch: map={actual} contract={expected}")
    for r in doc.get("contracts", []):
        con.execute("INSERT OR IGNORE INTO semantics VALUES(?,?,?,?,?,?,?,?,?)", (
            r["id"], parse_int(r.get("rva")), "binary-contract", r["id"], "contract rva hook",
            "verified", "exact RVA + byte signature", r.get("purpose", ""), str(path)))


def build_fts(con: sqlite3.Connection):
    try:
        con.executescript(
            """
            CREATE VIRTUAL TABLE fts_functions USING fts5(entry_rva UNINDEXED, name, namespace, return_type);
            INSERT INTO fts_functions SELECT printf('0x%08X',entry_rva),name,namespace,return_type FROM functions;
            CREATE VIRTUAL TABLE fts_strings USING fts5(rva UNINDEXED, value, datatype);
            INSERT INTO fts_strings SELECT printf('0x%08X',rva),value,datatype FROM strings;
            CREATE VIRTUAL TABLE fts_instructions USING fts5(rva UNINDEXED, function_rva UNINDEXED, text, mnemonic);
            INSERT INTO fts_instructions SELECT printf('0x%08X',rva),printf('0x%08X',function_rva),text,mnemonic FROM instructions;
            CREATE VIRTUAL TABLE fts_semantics USING fts5(id, rva UNINDEXED, name, tags, evidence, notes);
            INSERT INTO fts_semantics SELECT id,printf('0x%08X',rva),name,tags,evidence,notes FROM semantics;
            """
        )
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('fts5','true')")
    except sqlite3.OperationalError:
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('fts5','false')")


def write_summary(con: sqlite3.Connection, out: pathlib.Path):
    def count(table): return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    meta = {k: json.loads(v) if (v.startswith('"') or v in ('null','true','false') or v[:1].isdigit()) else v
            for k, v in con.execute("SELECT key,value FROM meta")}
    summary = {
        "schemaVersion": SCHEMA_VERSION,
        "program": meta,
        "counts": {t: count(t) for t in ("functions","instructions","calls","xrefs","strings","imports","semantics")},
    }
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-dir", required=True, type=pathlib.Path)
    ap.add_argument("--db", required=True, type=pathlib.Path)
    ap.add_argument("--summary", type=pathlib.Path)
    ap.add_argument("--semantics", type=pathlib.Path)
    ap.add_argument("--binary-contract", type=pathlib.Path)
    args = ap.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    con = connect(args.db)
    try:
        insert_export(con, args.export_dir)
        insert_semantics(con, args.semantics)
        insert_binary_contract(con, args.binary_contract)
        build_fts(con)
        con.commit()
        if args.summary:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            write_summary(con, args.summary)
        print(f"EXE_MAP_DB={args.db}")
    finally:
        con.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

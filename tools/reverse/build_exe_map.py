#!/usr/bin/env python3
"""Build a compact SQLite knowledge map from ExportOutRunMap.java output."""

from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
from typing import Iterable


SCHEMA = """
PRAGMA journal_mode=OFF;
PRAGMA synchronous=OFF;
PRAGMA temp_store=MEMORY;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS functions (
    rva INTEGER PRIMARY KEY,
    rva_hex TEXT NOT NULL,
    entry TEXT NOT NULL,
    name TEXT NOT NULL,
    namespace TEXT,
    min_address TEXT,
    min_rva INTEGER,
    max_address TEXT,
    max_rva INTEGER,
    body_size INTEGER,
    is_thunk INTEGER,
    is_external INTEGER,
    signature TEXT,
    decompile_complete INTEGER DEFAULT 0,
    decompile_c TEXT
);

CREATE TABLE IF NOT EXISTS instructions (
    rva INTEGER PRIMARY KEY,
    rva_hex TEXT NOT NULL,
    address TEXT NOT NULL,
    function_rva INTEGER,
    mnemonic TEXT,
    text TEXT,
    bytes TEXT
);
CREATE INDEX IF NOT EXISTS idx_instructions_function ON instructions(function_rva);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_rva INTEGER,
    caller_rva INTEGER,
    target_rva INTEGER,
    site TEXT,
    target TEXT,
    target_name TEXT
);
CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_rva);
CREATE INDEX IF NOT EXISTS idx_calls_target ON calls(target_rva);

CREATE TABLE IF NOT EXISTS xrefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_rva INTEGER,
    to_rva INTEGER,
    from_address TEXT,
    to_address TEXT,
    type TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_xrefs_from ON xrefs(from_rva);
CREATE INDEX IF NOT EXISTS idx_xrefs_to ON xrefs(to_rva);

CREATE TABLE IF NOT EXISTS strings (
    rva INTEGER PRIMARY KEY,
    rva_hex TEXT NOT NULL,
    address TEXT NOT NULL,
    length INTEGER,
    value TEXT
);

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rva INTEGER,
    rva_hex TEXT,
    address TEXT,
    name TEXT,
    type TEXT,
    namespace TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_symbols_rva ON symbols(rva);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);

CREATE TABLE IF NOT EXISTS annotations (
    id TEXT PRIMARY KEY,
    rva INTEGER,
    rva_hex TEXT,
    kind TEXT,
    name TEXT,
    tags TEXT,
    confidence TEXT,
    note TEXT,
    evidence TEXT
);
CREATE INDEX IF NOT EXISTS idx_annotations_rva ON annotations(rva);

CREATE TABLE IF NOT EXISTS source_bindings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id TEXT,
    rva INTEGER,
    rva_hex TEXT,
    purpose TEXT,
    path TEXT,
    needle TEXT
);
CREATE INDEX IF NOT EXISTS idx_bindings_rva ON source_bindings(rva);

CREATE TABLE IF NOT EXISTS search_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    rva INTEGER,
    name TEXT,
    content TEXT NOT NULL
);
"""


def parse_rva(value: object | None) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    return int(str(value), 0)


def read_jsonl(path: pathlib.Path) -> Iterable[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {e}") from e


def add_search_doc(conn: sqlite3.Connection, kind: str, rva: int | None, name: str | None, content: str) -> None:
    conn.execute(
        "INSERT INTO search_docs(kind,rva,name,content) VALUES(?,?,?,?)",
        (kind, rva, name, content),
    )


def import_export(conn: sqlite3.Connection, export_dir: pathlib.Path) -> None:
    manifest_path = export_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key, value in manifest.items():
        conn.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
            (f"export.{key}", json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value),
        )

    for row in read_jsonl(export_dir / "functions.jsonl") or ():
        rva = parse_rva(row["rva"])
        conn.execute(
            """INSERT OR REPLACE INTO functions
               (rva,rva_hex,entry,name,namespace,min_address,min_rva,max_address,max_rva,body_size,is_thunk,is_external,signature)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rva, row["rva"], row["entry"], row["name"], row.get("namespace"),
                row.get("min"), parse_rva(row.get("minRva")),
                row.get("max"), parse_rva(row.get("maxRva")), row.get("bodySize"),
                int(bool(row.get("thunk"))), int(bool(row.get("external"))), row.get("signature"),
            ),
        )
        add_search_doc(
            conn, "function", rva, row["name"],
            " ".join(filter(None, [row.get("name"), row.get("namespace"), row.get("signature")])),
        )

    for row in read_jsonl(export_dir / "decompile.jsonl") or ():
        rva = parse_rva(row["rva"])
        conn.execute(
            "UPDATE functions SET decompile_complete=?, decompile_c=? WHERE rva=?",
            (int(bool(row.get("complete"))), row.get("c", ""), rva),
        )
        add_search_doc(conn, "decompile", rva, row.get("name"), row.get("c", ""))

    for row in read_jsonl(export_dir / "instructions.jsonl") or ():
        rva = parse_rva(row["rva"])
        conn.execute(
            """INSERT OR REPLACE INTO instructions
               (rva,rva_hex,address,function_rva,mnemonic,text,bytes)
               VALUES(?,?,?,?,?,?,?)""",
            (
                rva, row["rva"], row["address"], parse_rva(row.get("functionRva")),
                row.get("mnemonic"), row.get("text"), row.get("bytes"),
            ),
        )

    for row in read_jsonl(export_dir / "calls.jsonl") or ():
        conn.execute(
            """INSERT INTO calls(site_rva,caller_rva,target_rva,site,target,target_name)
               VALUES(?,?,?,?,?,?)""",
            (
                parse_rva(row.get("siteRva")), parse_rva(row.get("callerRva")),
                parse_rva(row.get("targetRva")), row.get("site"), row.get("target"),
                row.get("targetName"),
            ),
        )

    for row in read_jsonl(export_dir / "xrefs.jsonl") or ():
        conn.execute(
            """INSERT INTO xrefs(from_rva,to_rva,from_address,to_address,type,source)
               VALUES(?,?,?,?,?,?)""",
            (
                parse_rva(row.get("fromRva")), parse_rva(row.get("toRva")),
                row.get("from"), row.get("to"), row.get("type"), row.get("source"),
            ),
        )

    for row in read_jsonl(export_dir / "strings.jsonl") or ():
        rva = parse_rva(row["rva"])
        conn.execute(
            "INSERT OR REPLACE INTO strings(rva,rva_hex,address,length,value) VALUES(?,?,?,?,?)",
            (rva, row["rva"], row["address"], row.get("length"), row.get("value")),
        )
        add_search_doc(conn, "string", rva, None, row.get("value", ""))

    for row in read_jsonl(export_dir / "symbols.jsonl") or ():
        rva = parse_rva(row.get("rva"))
        conn.execute(
            """INSERT INTO symbols(rva,rva_hex,address,name,type,namespace,source)
               VALUES(?,?,?,?,?,?,?)""",
            (
                rva, row.get("rva"), row.get("address"), row.get("name"),
                row.get("type"), row.get("namespace"), row.get("source"),
            ),
        )
        add_search_doc(
            conn, "symbol", rva, row.get("name"),
            " ".join(filter(None, [row.get("name"), row.get("namespace"), row.get("type")])),
        )


def import_semantics(conn: sqlite3.Connection, path: pathlib.Path | None) -> None:
    if path is None or not path.exists():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    for row in doc.get("annotations", []):
        rva = parse_rva(row.get("rva"))
        tags = row.get("tags", [])
        evidence = row.get("evidence", [])
        conn.execute(
            """INSERT OR REPLACE INTO annotations
               (id,rva,rva_hex,kind,name,tags,confidence,note,evidence)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                row["id"], rva, row.get("rva"), row.get("kind"), row.get("name"),
                json.dumps(tags, ensure_ascii=False), row.get("confidence"),
                row.get("note"), json.dumps(evidence, ensure_ascii=False),
            ),
        )
        add_search_doc(
            conn, "annotation", rva, row.get("name"),
            " ".join(
                filter(
                    None,
                    [
                        row.get("id"), row.get("name"), row.get("kind"),
                        " ".join(tags), row.get("note"), " ".join(evidence),
                    ],
                )
            ),
        )


def import_binary_contract(conn: sqlite3.Connection, path: pathlib.Path | None) -> None:
    if path is None or not path.exists():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    canonical = doc.get("canonicalExe", {})
    for key in ("name", "sha256", "imageBase", "size", "provenance"):
        if key in canonical:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                (f"contract.{key}", str(canonical[key])),
            )

    for contract in doc.get("contracts", []):
        rva = parse_rva(contract.get("rva"))
        bindings = contract.get("sourceBindings", []) or [{}]
        for binding in bindings:
            conn.execute(
                """INSERT INTO source_bindings(contract_id,rva,rva_hex,purpose,path,needle)
                   VALUES(?,?,?,?,?,?)""",
                (
                    contract.get("id"), rva, contract.get("rva"), contract.get("purpose"),
                    binding.get("path"), binding.get("needle"),
                ),
            )
        add_search_doc(
            conn, "contract", rva, contract.get("id"),
            " ".join(
                filter(None, [contract.get("id"), contract.get("purpose"), contract.get("rva")])
            ),
        )


def build_fts(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("DROP TABLE IF EXISTS search_fts")
        conn.execute(
            "CREATE VIRTUAL TABLE search_fts USING fts5(kind UNINDEXED, rva UNINDEXED, name, content)"
        )
        conn.execute(
            "INSERT INTO search_fts(kind,rva,name,content) SELECT kind,rva,name,content FROM search_docs"
        )
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('search.fts5','true')")
        return True
    except sqlite3.OperationalError:
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('search.fts5','false')")
        return False


def validate_identity(conn: sqlite3.Connection) -> None:
    values = dict(conn.execute("SELECT key,value FROM meta"))
    exported = values.get("export.sha256", "").lower()
    expected = values.get("contract.sha256", "").lower()
    if expected and exported and exported != expected:
        raise SystemExit(
            f"refusing to build map: export SHA256 {exported} != canonical contract {expected}"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-dir", required=True, type=pathlib.Path)
    ap.add_argument("--db", required=True, type=pathlib.Path)
    ap.add_argument("--semantics", type=pathlib.Path)
    ap.add_argument("--contract", type=pathlib.Path)
    args = ap.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.db.exists():
        args.db.unlink()

    conn = sqlite3.connect(args.db)
    try:
        conn.executescript(SCHEMA)
        import_export(conn, args.export_dir)
        import_semantics(conn, args.semantics)
        import_binary_contract(conn, args.contract)
        validate_identity(conn)
        fts = build_fts(conn)
        conn.execute("ANALYZE")
        conn.commit()

        counts = {}
        for table in ("functions", "instructions", "calls", "xrefs", "strings", "symbols", "annotations", "source_bindings"):
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(json.dumps({"database": str(args.db), "fts5": fts, "counts": counts}, indent=2))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

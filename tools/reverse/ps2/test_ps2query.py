#!/usr/bin/env python3
"""Regression test for the compact build_ps2_map.py schema."""
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
QUERY = ROOT / "tools/reverse/ps2/ps2query.py"

with tempfile.TemporaryDirectory(prefix="ps2query-compact-") as tmp:
    db = pathlib.Path(tmp) / "ps2_knowledge_map.sqlite"
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE strings(va INTEGER PRIMARY KEY,file_offset INTEGER,section TEXT,length INTEGER,value TEXT);
    CREATE TABLE anchors(va INTEGER PRIMARY KEY,reasons TEXT,name TEXT);
    CREATE TABLE instructions(va INTEGER PRIMARY KEY,section TEXT,bytes TEXT,mnemonic TEXT,operands TEXT,text TEXT);
    CREATE TABLE calls(id INTEGER PRIMARY KEY,from_va INTEGER,to_va INTEGER,type TEXT);
    INSERT INTO anchors VALUES(0x1354B0,'call_target','sub_001354B0');
    INSERT INTO instructions VALUES(0x1354B0,'.text','00000000','nop','','nop');
    INSERT INTO strings VALUES(0x400000,0,'.rodata',11,'ForceEffect');
    """)
    con.commit()
    con.close()

    address = subprocess.run(
        [sys.executable, str(QUERY), "--db", str(db), "0x1354B0"],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if "ADDRESS 0x001354B0" not in address.stdout:
        raise SystemExit("compact address query did not return the requested address")
    if "STRING_REFS unavailable in compact map" not in address.stdout:
        raise SystemExit("compact address query did not report optional XREF absence")

    text_query = subprocess.run(
        [sys.executable, str(QUERY), "--db", str(db), "ForceEffect"],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if "STRINGS" not in text_query.stdout or "ForceEffect" not in text_query.stdout:
        raise SystemExit("compact text query did not search available string data")

    con = sqlite3.connect(db)
    con.execute("CREATE TABLE semantics(va INTEGER PRIMARY KEY,name TEXT,tags TEXT,confidence TEXT,evidence TEXT)")
    con.execute(
        "INSERT INTO semantics VALUES(?,?,?,?,?)",
        (0x1330F0, "WheelRuntime_SpringConditionUpdate", "PS2,FFB,SPRING", "high", "retail test"))
    con.commit()
    con.close()
    semantic_query = subprocess.run(
        [sys.executable, str(QUERY), "--db", str(db), "SpringCondition"],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if "SEMANTICS" not in semantic_query.stdout or "WheelRuntime_SpringConditionUpdate" not in semantic_query.stdout:
        raise SystemExit("semantic query did not consume optional curated semantics table")

print("OK: compact PS2 query works with optional semantics and without full-map string_xrefs")

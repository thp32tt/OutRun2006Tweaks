#!/usr/bin/env python3
"""Deterministic synthetic self-test for the EXE knowledge-map Python tools."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile


HERE = pathlib.Path(__file__).resolve().parent
BUILDER = HERE / "build_exe_map.py"
QUERY = HERE / "exequery.py"
CANONICAL_SHA = "68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3"


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def run(*args: str) -> str:
    cp = subprocess.run(
        [sys.executable, *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return cp.stdout


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        export = root / "export"
        export.mkdir()
        db = root / "map.sqlite"

        (export / "manifest.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "program": "OR2006C2C.EXE",
                    "sha256": CANONICAL_SHA,
                    "imageBase": "0x00400000",
                    "decompiled": True,
                }
            ),
            encoding="utf-8",
        )
        write_jsonl(
            export / "functions.jsonl",
            [
                {
                    "entry": "0x00401000",
                    "rva": "0x00001000",
                    "name": "FUN_demo",
                    "namespace": "Global",
                    "min": "0x00401000",
                    "minRva": "0x00001000",
                    "max": "0x00401020",
                    "maxRva": "0x00001020",
                    "bodySize": 17,
                    "thunk": False,
                    "external": False,
                    "signature": "void FUN_demo(void)",
                }
            ],
        )
        write_jsonl(
            export / "decompile.jsonl",
            [
                {
                    "entry": "0x00401000",
                    "rva": "0x00001000",
                    "name": "FUN_demo",
                    "complete": True,
                    "c": "void FUN_demo(void) { demo_marker(); }",
                }
            ],
        )
        write_jsonl(
            export / "instructions.jsonl",
            [
                {
                    "address": "0x00401004",
                    "rva": "0x00001004",
                    "functionRva": "0x00001000",
                    "mnemonic": "CALL",
                    "text": "CALL 0x00402000",
                    "bytes": "e8f70f0000",
                }
            ],
        )
        write_jsonl(
            export / "calls.jsonl",
            [
                {
                    "site": "0x00401004",
                    "siteRva": "0x00001004",
                    "callerRva": "0x00001000",
                    "target": "0x00402000",
                    "targetRva": "0x00002000",
                    "targetName": "demo_marker",
                }
            ],
        )
        write_jsonl(
            export / "xrefs.jsonl",
            [
                {
                    "from": "0x00401004",
                    "fromRva": "0x00001004",
                    "to": "0x00402000",
                    "toRva": "0x00002000",
                    "type": "UNCONDITIONAL_CALL",
                    "source": "ANALYSIS",
                }
            ],
        )
        write_jsonl(
            export / "strings.jsonl",
            [
                {
                    "address": "0x00403000",
                    "rva": "0x00003000",
                    "length": 11,
                    "value": "demo marker",
                }
            ],
        )
        write_jsonl(
            export / "symbols.jsonl",
            [
                {
                    "name": "FUN_demo",
                    "address": "0x00401000",
                    "rva": "0x00001000",
                    "type": "Function",
                    "namespace": "Global",
                    "source": "ANALYSIS",
                }
            ],
        )

        semantics = root / "semantics.json"
        semantics.write_text(
            json.dumps(
                {
                    "annotations": [
                        {
                            "id": "DEMO",
                            "rva": "0x00001004",
                            "kind": "test",
                            "name": "demo marker",
                            "tags": ["HUD", "TEST"],
                            "confidence": "high",
                            "note": "synthetic demo marker",
                            "evidence": ["self-test"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        contract = root / "contract.json"
        contract.write_text(
            json.dumps(
                {
                    "canonicalExe": {
                        "name": "OR2006C2C.EXE",
                        "sha256": CANONICAL_SHA,
                        "imageBase": "0x00400000",
                        "size": 1,
                        "provenance": "synthetic",
                    },
                    "contracts": [
                        {
                            "id": "DEMO-CONTRACT",
                            "rva": "0x00001004",
                            "purpose": "self-test",
                            "sourceBindings": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        run(
            str(BUILDER),
            "--export-dir", str(export),
            "--db", str(db),
            "--semantics", str(semantics),
            "--contract", str(contract),
        )

        rva_result = json.loads(run(str(QUERY), "--db", str(db), "0x1004", "--json"))
        assert rva_result["containingFunction"][0]["name"] == "FUN_demo"
        assert rva_result["annotations"][0]["id"] == "DEMO"

        va_result = json.loads(run(str(QUERY), "--db", str(db), "0x401004", "--json"))
        assert va_result["queryRva"] == "0x00001004"
        assert va_result["containingFunction"][0]["name"] == "FUN_demo"

        text_result = json.loads(
            run(str(QUERY), "--db", str(db), "demo", "marker", "--json")
        )
        assert any(row["kind"] in {"annotation", "decompile", "string"} for row in text_result)

    print("EXE knowledge-map self-test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

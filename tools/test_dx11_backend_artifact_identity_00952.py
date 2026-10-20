#!/usr/bin/env python3
"""Source-only regression for feature branches with slash-containing refs."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
marker = "      - uses: actions/upload-artifact@v4\n"
assert workflow.count(marker) == 1, "backend artifact upload must be unambiguous"
upload = workflow.split(marker, 1)[1].split("\n      - ", 1)[0]
name = re.search(r"^\s+name:\s*(.+?)\s*$", upload, re.MULTILINE)
assert name, "backend artifact name missing"
template = name.group(1)
assert template == "backend-autovalidated-${{ github.sha }}", template
synthetic_sha = "a" * 40
safe_name = template.replace("${{ github.sha }}", synthetic_sha)
assert re.fullmatch(r"[A-Za-z0-9_.-]+", safe_name), safe_name
unsafe_name = f"backend-autovalidated-feature/dx11-00952-{synthetic_sha}"
assert re.fullmatch(r"[A-Za-z0-9_.-]+", unsafe_name) is None
print("DX11 backend artifact exact-SHA and safe-name regression: PASS")

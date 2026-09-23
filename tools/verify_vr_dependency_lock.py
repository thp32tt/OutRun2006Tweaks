#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs/VR_DEPENDENCY_LOCK.json"
CMAKE = ROOT / "cmake.toml"


def fail(message: str) -> None:
    raise SystemExit(message)


lock = json.loads(LOCK.read_text(encoding="utf-8"))
cmake = CMAKE.read_text(encoding="utf-8")
expected = {item["name"]: item["commit"].lower() for item in lock["dependencies"]}

for name, commit in expected.items():
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        fail(f"dependency lock is not an immutable commit: {name}={commit}")
    if name == "safetyhook":
        section = re.search(
            r"(?ms)^\[fetch-content\.safetyhook\]\s*(.*?)(?=^\[|\Z)", cmake
        )
        if not section:
            fail("cmake.toml missing fetch-content.safetyhook")
        match = re.search(r'(?m)^tag\s*=\s*"([^"]+)"', section.group(1))
    else:
        match = re.search(
            rf'(?m)^{re.escape(name)}\s*=\s*\{{[^\n]*\btag\s*=\s*"([^"]+)"',
            cmake,
        )
    if not match:
        fail(f"cmake.toml missing dependency pin: {name}")
    actual = match.group(1).lower()
    if actual != commit:
        fail(f"dependency pin mismatch: {name}: cmake={actual} lock={commit}")

all_tags = re.findall(r'(?m)\btag\s*=\s*"([^"]+)"', cmake)
mutable = [tag for tag in all_tags if not re.fullmatch(r"[0-9a-fA-F]{40}", tag)]
if mutable:
    fail("mutable FetchContent refs remain: " + ", ".join(mutable))

print(f"VR dependency lock: PASS ({len(expected)} immutable dependencies)")

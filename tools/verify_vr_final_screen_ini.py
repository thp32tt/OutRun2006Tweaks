#!/usr/bin/env python3
"""Validate R26 final-test INI and protect against silent settings fallback.

The released 2026-10-24 DX9Ex test INI had duplicate VR.DriverSeatCarSpaceBasis.
The game's INI parser rejected the complete config and loaded defaults.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def parse_ini(text: str) -> dict[tuple[str, str], str]:
    section = ""
    found: dict[tuple[str, str], str] = {}
    for no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and "]" in line:
            section = line[1:line.index("]")].strip().lower()
            continue
        m = re.match(r"([A-Za-z_][\w.]*)\s*=\s*(.*)", line)
        if m:
            pair = (section, m[1].lower())
            if pair in found:
                raise ValueError(f"duplicate INI setting [{section}] {m[1]} at line {no}")
            found[pair] = m[2].strip()
    return found


def verify(text: str) -> None:
    cfg = parse_ini(text)
    for setting, expected in {
        "driverseatview": "false",
        "driverseatcarspacebasis": "false",
        "followgameresolution": "false",
        "unifiedeyemenusource": "true",
        "cullingunionmargin degrees": "8.0",
        "hud1080preference": "true",
        "hudscale": "0.55",
    }.items():
        key = setting.replace(" ", "")
        assert cfg[("vr", key)].lower() == expected, f"[VR] {key} expected {expected}"
    assert cfg[("graphics", "disablestageculling")].lower() == "true"
    runner = (ROOT / "tools/Run-FinalScreenTest.ps1").read_text(encoding="utf-8-sig")
    assert "INI_DUPLICATE_KEY" in runner
    assert "INI_PARSE_FAILED" in runner
    assert "'-DriverSeatView=false'" in runner


if __name__ == "__main__":
    source = (ROOT / "OutRun2006Tweaks.ini").read_text(encoding="utf-8-sig")
    verify(source)
    try:
        verify(source + "\n[VR]\nDriverSeatCarSpaceBasis = false\n")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate-key negative control escaped")
    print("PASS final R26 test INI, known cockpit rollback and duplicate-key negative regression; HMD UNTESTED")

#!/usr/bin/env python3
"""
DX11 conversion lane static surface contract checker.

This offline analyzer validates source text for common conversion hazards:
- accidental native draw-path activation while evidence gates are closed
- high-risk render-surface format/color-space changes without explicit
  provenance, alpha-preservation, and source-format fallback evidence
- runtime validation claims mixed into static reports

It intentionally performs static checks only. It does not claim GPU/runtime validation.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


FORBIDDEN_ACTIVATION_TOKENS = (
    "NativeDrawPathActive = true",
    "native_draw_path_active = true",
)

REQUIRED_RUNTIME_LABEL = "UNTESTED"

HIGH_RISK_SURFACE_FORMATS = (
    "DXGI_FORMAT_R16G16B16A16_FLOAT",
    "DXGI_FORMAT_R32G32B32A32_FLOAT",
    "DXGI_FORMAT_R11G11B10_FLOAT",
    "DXGI_FORMAT_B8G8R8A8_UNORM_SRGB",
    "DXGI_FORMAT_R8G8B8A8_UNORM_SRGB",
)

FORMAT_GUARD_RE = re.compile(
    r"DX11_SURFACE_FORMAT_PROVENANCE:\s*"
    r"role=(?:SCENE_COLOR|EFFECT_COLOR)\s+"
    r"alpha=PRESERVED\s+fallback=SOURCE_FORMAT"
)

GUARD_WINDOW_LINES = 6
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inl"}


def _iter_files(paths: list[Path]):
    for path in paths:
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in SOURCE_SUFFIXES:
                    yield child
        elif path.is_file():
            yield path


def _format_guarded(lines: list[str], index: int) -> bool:
    start = max(0, index - GUARD_WINDOW_LINES)
    end = min(len(lines), index + GUARD_WINDOW_LINES + 1)
    return any(FORMAT_GUARD_RE.search(line) for line in lines[start:end])


def scan_text(text: str, label: str = "<memory>") -> list[str]:
    failures: list[str] = []

    for token in FORBIDDEN_ACTIVATION_TOKENS:
        if token in text:
            failures.append(f"{label}: activation token found: {token}")

    if "runtime_validation" in text and REQUIRED_RUNTIME_LABEL not in text:
        failures.append(
            f"{label}: runtime_validation report lacks UNTESTED/static separation"
        )

    lines = text.splitlines()
    for index, line in enumerate(lines):
        for fmt in HIGH_RISK_SURFACE_FORMATS:
            if fmt not in line:
                continue
            if not _format_guarded(lines, index):
                failures.append(
                    f"{label}:{index + 1}: high-risk surface format {fmt} lacks "
                    "DX11_SURFACE_FORMAT_PROVENANCE role=SCENE_COLOR|EFFECT_COLOR "
                    "alpha=PRESERVED fallback=SOURCE_FORMAT guard"
                )

    return failures


def collect_failures(paths: list[Path]) -> list[str]:
    failures: list[str] = []
    seen: set[Path] = set()

    for path in _iter_files(paths):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        text = path.read_text(encoding="utf-8", errors="replace")
        failures.extend(scan_text(text, str(path)))

    return failures


def scan(paths: list[Path]) -> int:
    failures = collect_failures(paths)

    if failures:
        print("DX11_STATIC_SURFACE_CONTRACT_FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("DX11_STATIC_SURFACE_CONTRACT_PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    return scan(args.paths)


if __name__ == "__main__":
    raise SystemExit(main())

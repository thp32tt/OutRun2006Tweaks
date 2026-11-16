#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import urllib.request
import zipfile

PAGE_URL = "https://dlcfun.com/en/assetto-corsa/ferrari-dino-246-gts-mod"
USER_AGENT = "Mozilla/5.0 (GitHub Actions private conversion audit)"

HARD_BLOCK_PATTERNS = {
    "do_not_share": r"\bdo\s+not\s+share\b",
    "do_not_redistribute": r"\bdo\s+not\s+(?:re-?)?distribut(?:e|ion)\b",
    "no_redistribution": r"\bno\s+(?:re-?)?distribution\b",
    "do_not_reupload": r"\bdo\s+not\s+re-?upload\b",
    "no_reupload": r"\bno\s+re-?upload(?:ing)?\b",
    "do_not_convert": r"\bdo\s+not\s+convert\b",
    "no_conversion": r"\bno\s+conversion\b",
    "no_porting": r"\bno\s+port(?:ing)?\b",
    "do_not_port": r"\bdo\s+not\s+port\b",
    "ripping_forbidden": r"\bripp(?:ing|ed).*?(?:not\s+allowed|forbidden|prohibited)\b",
    "base_use_forbidden": r"\b(?:not\s+allowed|forbidden|prohibited).*?\buse(?:d)?\s+as\s+(?:a\s+)?base\b",
    "personal_use_only": r"\bpersonal\s+use\s+only\b",
}

TEXT_SUFFIXES = {
    "", ".txt", ".md", ".markdown", ".nfo", ".ini", ".cfg", ".json",
    ".xml", ".html", ".htm", ".license", ".readme", ".rtf",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, out: Path, referer: str | None = None) -> None:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as src, out.open("wb") as dst:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            dst.write(chunk)


def extract_signed_url(page_text: str) -> tuple[str, str]:
    normalized = html.unescape(page_text).replace("\\u0026", "&").replace("\\/", "/")
    patterns = [
        r'\\?"file\\?"\s*:\s*\\?"(https://storage\.dlcfun\.com/dlcfun-private/files/addons/[^"\\]+?\.zip\?[^"\\]+)',
        r'(https://storage\.dlcfun\.com/dlcfun-private/files/addons/[^"<> ]+?\.zip\?[^"<> ]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, re.I)
        if match:
            url = match.group(1).replace("\\u0026", "&").replace("\\/", "/")
            name_match = re.search(r'file_name\\?"\s*:\s*\\?"([^"\\]+\.zip)', normalized, re.I)
            return url, (name_match.group(1) if name_match else "dino246gts_source.zip")
    raise RuntimeError("Could not locate current signed source ZIP URL on DLCFun page")


def decode_text(raw: bytes) -> str | None:
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return None


def rights_audit(extract_dir: Path) -> dict:
    scanned = []
    hits = []
    for path in sorted(p for p in extract_dir.rglob("*") if p.is_file()):
        suffix = path.suffix.lower()
        name_l = path.name.lower()
        textish = suffix in TEXT_SUFFIXES or "readme" in name_l or "license" in name_l or "credit" in name_l
        if not textish or path.stat().st_size > 2 * 1024 * 1024:
            continue
        raw = path.read_bytes()
        text = decode_text(raw)
        if text is None:
            continue
        scanned.append(str(path.relative_to(extract_dir)))
        compact = re.sub(r"\s+", " ", text)
        for key, pattern in HARD_BLOCK_PATTERNS.items():
            m = re.search(pattern, compact, re.I)
            if m:
                start = max(0, m.start() - 180)
                end = min(len(compact), m.end() + 220)
                hits.append({
                    "rule": key,
                    "file": str(path.relative_to(extract_dir)),
                    "context": compact[start:end],
                })
    return {
        "policy": "fail_closed_for_public_artifact_or_explicit_conversion_restriction",
        "scanned_text_files": scanned,
        "restriction_hits": hits,
        "private_conversion_allowed": len(hits) == 0,
        "redistribution_verified": False,
        "rights_note": (
            "PRIVATE_TEST_ONLY_NO_REDISTRIBUTION_ASSERTION; no explicit restriction phrase found in bundled text"
            if not hits else
            "BLOCKED_BY_BUNDLED_RIGHTS_TEXT"
        ),
    }


def choose_car_root(extract_dir: Path) -> Path:
    lods = list(extract_dir.rglob("data/lods.ini"))
    if lods:
        dino = [p.parent.parent for p in lods if "dino" in str(p).lower() or "246" in str(p).lower()]
        roots = dino or [p.parent.parent for p in lods]
        roots = sorted(set(p.resolve() for p in roots), key=lambda p: len(str(p)))
        return roots[0]
    kn5_dirs = {}
    for p in extract_dir.rglob("*.kn5"):
        if p.is_file():
            kn5_dirs.setdefault(p.parent.resolve(), 0)
            kn5_dirs[p.parent.resolve()] += p.stat().st_size
    if not kn5_dirs:
        raise RuntimeError("Downloaded archive contains no KN5 files")
    return max(kn5_dirs, key=kn5_dirs.get)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ns = ap.parse_args()
    work = ns.work.resolve()
    work.mkdir(parents=True, exist_ok=True)

    page = work / "dlcfun_dino_page.html"
    download(PAGE_URL, page)
    page_text = page.read_text(encoding="utf-8", errors="ignore")
    signed_url, filename = extract_signed_url(page_text)

    archive = work / Path(filename).name
    download(signed_url, archive, PAGE_URL)

    extract_dir = work / "source"
    extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"ZIP CRC failure at {bad}")
        zf.extractall(extract_dir)
        entries = [
            {"name": info.filename, "bytes": info.file_size}
            for info in zf.infolist() if not info.is_dir()
        ]

    rights = rights_audit(extract_dir)
    car_root = choose_car_root(extract_dir)
    report = {
        "page_url": PAGE_URL,
        "archive_name": archive.name,
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": sha256(archive),
        "archive_entries": entries,
        "car_root": str(car_root),
        "rights": rights,
    }
    (work / "source_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"CAR_ROOT={car_root}")

    if not rights["private_conversion_allowed"]:
        print("BLOCKED: bundled text contains an explicit sharing/conversion/porting restriction", file=sys.stderr)
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fail-closed, source-pinned Ferrari16 test-copy package. No game/vehicle assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import zipfile

LAUNCHERS = (
    "RUN-FERRARI16-V003-ALL-CARS.cmd",
    "RUN-FERRARI16-V003-ALL-CARS-TRACE.cmd",
    "RUN-FERRARI16-V003-MODEL-OFF.cmd",
    "RUN-FERRARI16-V003-PBR-TRACE.cmd",
)
SCRIPTS = (
    "PREPARE-FERRARI16-ISOLATED.ps1",
    "INSTALL-FERRARI16-ISOLATED.ps1",
    "RESTORE-FERRARI16-ISOLATED.ps1",
)
LICENSES = ("COPYING.GPL3", "THIRD_PARTY_NOTICES.md")
SOURCE_SHA_RE = re.compile(r"[a-f0-9]{40}\Z")
PAYLOAD = ("PAYLOAD/dinput8.dll", "PAYLOAD/outrun-vr-host.exe")
STATIC_FILES = tuple(f"LAUNCHERS/{name}" for name in LAUNCHERS) + SCRIPTS + LICENSES
README = """Ferrari16 EXT16-005 - ISOLATED TEST COPY ONLY
DO NOT place this ZIP directly into the working v0.03 release.
Contains a same-source Windows x86 game DLL and x64 OpenXR host, no game EXE,
no original PMT and no third-party GLB/OVC/DDS models.
1. Run PREPARE-FERRARI16-ISOLATED.ps1 -SourceRoot <working v0.03 path> -TestRoot <new empty path>.
2. From extracted package: INSTALL-FERRARI16-ISOLATED.ps1 -GameRoot <test path> (verify only).
3. After verifying QA.json SHA256 hashes, re-run with -Install.
4. Launch from the isolated game folder using RUN-FERRARI16-V003-MODEL-OFF.cmd,
   then RUN-FERRARI16-V003-ALL-CARS-TRACE.cmd. Car assets must be supplied
   privately by the user with valid rights and preflight checks.
5. Restore using RESTORE-FERRARI16-ISOLATED.ps1 -GameRoot <test path> -BackupPath <printed backup>.
Keep logs private and review SOURCE SHA, PBR map counts, stereo receipt/fallback.
Static CI != Quest3 or VDXR stereo/framerate validation. HMD=UNTESTED.
"""

def digest(data):
    return hashlib.sha256(data).hexdigest()

def pe_machine(data):
    if len(data) < 0x88 or data[:2] != b"MZ":
        raise ValueError("not a PE file")
    offset = struct.unpack_from("<I", data, 0x3c)[0]
    if offset > len(data) - 6 or data[offset:offset + 4] != b"PE\x00\x00":
        raise ValueError("invalid PE header")
    return struct.unpack_from("<H", data, offset + 4)[0]

def assert_binaries(items):
    if pe_machine(items[PAYLOAD[0]]) != 0x14c:
        raise ValueError("game DLL must be PE x86")
    if pe_machine(items[PAYLOAD[1]]) != 0x8664:
        raise ValueError("OpenXR host must be PE x64")

def source_items(root, dll, host):
    root = Path(root)
    result = {PAYLOAD[0]: Path(dll).read_bytes(),
              PAYLOAD[1]: Path(host).read_bytes()}
    for name in LAUNCHERS:
        result[f"LAUNCHERS/{name}"] = (root / "tools/ferrari16" / name).read_bytes()
    for name in SCRIPTS:
        result[name] = (root / "tools/ferrari16" / name).read_bytes()
    for name in LICENSES:
        result[name] = (root / name).read_bytes()
    result["README_FIRST_KO.txt"] = README.encode("utf-8")
    return result

def contents_sha(items):
    return "".join(f"{digest(data)}  {name}\n"
                   for name, data in sorted(items.items())).encode("ascii")

def build_package(root, dll, host, source_sha, output):
    if not SOURCE_SHA_RE.fullmatch(source_sha):
        raise ValueError("source must be exact 40-char Git commit SHA")
    items = source_items(root, dll, host)
    assert_binaries(items)
    qa = {
        "Schema": 1, "TaskId": "EXT16-005", "BuildSourceSha": source_sha,
        "PackageType": "FERRARI16_ISOLATED_STATIC_TEST_ONLY",
        "RuntimeValidation": "UNTESTED", "Quest3HardwarePass": False,
        "Real16ModelAssetsValidated": False, "ThirdPartyModelsBundled": False,
        "ContentSha256": {name: digest(data) for name, data in sorted(items.items())},
    }
    items["QA.json"] = (json.dumps(qa, ensure_ascii=False, sort_keys=True, indent=2)
                        + "\n").encode("utf-8")
    items["SHA256SUMS.txt"] = contents_sha(
        {name: data for name, data in items.items() if name != "QA.json"})
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in sorted(items.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    verify_package(output, source_sha)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest(output.read_bytes())}  {output.name}\n", encoding="ascii")
    return qa

def verify_package(path, source_sha=None):
    allowed = set(PAYLOAD) | set(STATIC_FILES) | {
        "README_FIRST_KO.txt", "QA.json", "SHA256SUMS.txt"}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != allowed:
            raise ValueError("missing, duplicate, or unauthorized package file")
        if archive.testzip() is not None:
            raise ValueError("corrupt ZIP member")
        items = {name: archive.read(name) for name in names}
    qa = json.loads(items["QA.json"])
    sha = qa.get("BuildSourceSha", "")
    if (qa.get("Schema") != 1 or qa.get("TaskId") != "EXT16-005" or
            qa.get("PackageType") != "FERRARI16_ISOLATED_STATIC_TEST_ONLY" or
            not SOURCE_SHA_RE.fullmatch(sha) or
            (source_sha is not None and source_sha != sha) or
            qa.get("RuntimeValidation") != "UNTESTED" or
            qa.get("Quest3HardwarePass") is not False or
            qa.get("Real16ModelAssetsValidated") is not False or
            qa.get("ThirdPartyModelsBundled") is not False):
        raise ValueError("unsafe or mismatched QA identity")
    hashed = {name: data for name, data in items.items()
              if name not in ("QA.json", "SHA256SUMS.txt")}
    expected = {name: digest(data) for name, data in sorted(hashed.items())}
    if qa.get("ContentSha256") != expected:
        raise ValueError("payload SHA256 mismatch")
    if items["SHA256SUMS.txt"] != contents_sha(hashed):
        raise ValueError("SHA256SUMS.txt mismatch")
    assert_binaries(items)
    return qa

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="operation", required=True)
    make = sub.add_parser("build")
    for flag in ("root", "dll", "host", "source-sha", "output"):
        make.add_argument("--" + flag, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--package", required=True)
    verify.add_argument("--source-sha")
    args = parser.parse_args()
    if args.operation == "build":
        qa = build_package(args.root, args.dll, args.host, args.source_sha, args.output)
    else:
        qa = verify_package(args.package, args.source_sha)
    print("FERRARI16_PACKAGE_STATIC_PASS", qa["BuildSourceSha"],
          qa["RuntimeValidation"], "NO_PRIVATE_ASSETS")

if __name__ == "__main__":
    main()

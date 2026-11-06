#!/usr/bin/env python3
"""Build a no-overwrite OutRun Dino OVC3 copy-and-run test ZIP.

Use only the complete, exact-SHA GitHub Actions artifact from
dino-external-pbr.yml and a separately generated validated OVC3 sidecar.
No original game EXE, PMT, XPR, FFB/driver data or top-level DLL is included.
Extracting the ZIP does not install/activate anything; the user runs
RUN-QUEST-APK-DINO-PBR.cmd to verify, backup, activate and launch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

STABLE_NAME = "Dino246_Cockpit_LHD_v15.ovc"
PBR_NAME = "Dino246_Cockpit_LHD_v15_PBR.ovc"
VARIANT = "ACTIVE_R26_R43_R44"
ROOT_FILES = (
    "QuestCockpit-CopyRun.ps1",
    "QuestCockpit-CopyRestore.ps1",
    "RUN-QUEST-APK-DINO-PBR.cmd",
    "RESTORE-QUEST-APK-COCKPIT.cmd",
)
SCRIPT_FILES = (
    "Run-OutRunVRTest.ps1",
    "Select-OutRunVRBackend.ps1",
    "OutRunVR-TestProfiles.ps1",
    "Collect-OutRunVRLogs.ps1",
    "Collect-OutRunVRLogs.cmd",
    "Analyze-OutRunVRSession.ps1",
    "Run-QuestCockpitV2-CrashDiag.ps1",
    "analyze_outrun_assets.py",
)
DEFAULT_FILES = ("OutRun2006Tweaks.ini", "OutRun2006Tweaks.lods.ini")
BACKEND_FILES = (
    "dinput8.dll", "outrun-vr-host.exe", "SOURCE_SHA.txt",
    "HOST_BUILD_SOURCE_SHA.txt", "VARIANT_ID.txt",
)
MAX_OVC3_BYTES = 128 * 1024 * 1024


def required(root: Path, relative: str) -> Path:
    src = root / relative
    if not src.is_file() or src.is_symlink():
        raise ValueError(f"missing or unsafe exact-artifact file: {relative}")
    return src


def sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def machine(path: Path, expected: int) -> None:
    with path.open("rb") as src:
        mz = src.read(64)
        if len(mz) != 64 or mz[:2] != b"MZ":
            raise ValueError(f"not a Windows PE: {path.name}")
        offset = struct.unpack_from("<I", mz, 0x3C)[0]
        if offset < 64 or offset > 1 << 20:
            raise ValueError(f"invalid PE offset: {path.name}")
        src.seek(offset)
        pe = src.read(6)
        if len(pe) != 6 or pe[:4] != b"PE\x00\x00" or struct.unpack_from("<H",pe,4)[0] != expected:
            raise ValueError(f"incorrect x86/x64 architecture: {path.name}")


def validate_ovc3(path: Path) -> None:
    length = path.stat().st_size
    if length < 36 or length > MAX_OVC3_BYTES:
        raise ValueError("OVC3 size outside parser bounds")
    with path.open("rb") as stream:
        header = stream.read(36)
        if header[:8] != b"OVRCABH3":
            raise ValueError("model is not an OVC3 PBR sidecar")
        version, groups, mats, vertices, triangles, body_size, checksum = struct.unpack_from(
            "<7I", header, 8
        )
        if version != 3 or not 1 <= groups <= 512 or not 1 <= mats <= 64 or (
            vertices > 1000000 or triangles > 2000000 or body_size != length - 36
        ):
            raise ValueError("bad OVC3 header/counts")
        crc = 0
        while data := stream.read(1 << 20):
            crc = zlib.crc32(data, crc)
        if crc != checksum:
            raise ValueError("OVC3 body CRC32 mismatch")


def prepare_payload(artifact: Path, ovc3: Path) -> dict[str, bytes]:
    source = required(artifact, "SOURCE_SHA.txt").read_text(encoding="ascii").strip().lower()
    host_source = required(artifact, "HOST_BUILD_SOURCE_SHA.txt").read_text(
        encoding="ascii"
    ).strip().lower()
    variant = required(artifact, "VARIANT_ID.txt").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}",source) or host_source != source or variant != VARIANT:
        raise ValueError("Win32 DLL/Win64 OpenXR host source SHA or variant mismatch")
    dll = required(artifact,"dinput8.dll")
    host = required(artifact,"outrun-vr-host.exe")
    machine(dll,0x14C)
    machine(host,0x8664)
    validate_ovc3(ovc3)
    contents: dict[str, bytes] = {}
    for name in ROOT_FILES:
        contents[name] = required(artifact,name).read_bytes()
    for name in SCRIPT_FILES:
        contents[f"QUEST_APK_COPYRUN_PAYLOAD/scripts/{name}"] = required(
            artifact,f"scripts/{name}").read_bytes()
    for name in DEFAULT_FILES:
        contents[f"QUEST_APK_COPYRUN_PAYLOAD/defaults/{name}"] = required(
            artifact,f"defaults/{name}").read_bytes()
    for name in BACKEND_FILES:
        contents[f"QUEST_APK_COPYRUN_PAYLOAD/backend/{name}"] = required(
            artifact,name).read_bytes()
    contents[f"QUEST_APK_COPYRUN_PAYLOAD/model/{PBR_NAME}"] = ovc3.read_bytes()
    manifest = {
        "SourceSha":source,
        "HostSourceSha":host_source,
        "VariantId":variant,
        "GameDllSha256":sha256(dll),
        "HostExeSha256":sha256(host),
        "DinoPbrModelSha256":sha256(ovc3),
    }
    contents["QUEST_APK_COPYRUN_PAYLOAD/IDENTITY.json"] = (
        json.dumps(manifest,indent=2,ensure_ascii=True)+"\n"
    ).encode("utf-8")
    contents["DINO-PBR-TEST-README.txt"] = (
        "OutRun 2006 R26 Dino OVC3 PBR - development-only copy and run\n"
        f"Source SHA: {source}\n"
        "Keep the original game folder untouched and use a copied game folder.\n"
        "1. Extract every file next to the copied OR2006C2C.EXE.\n"
        "2. Run: powershell -NoProfile -ExecutionPolicy Bypass -File "
        "QuestCockpit-CopyRun.ps1 -Mode PBR -VerifyOnly\n"
        "3. Close the game and host; double-click RUN-QUEST-APK-DINO-PBR.cmd.\n"
        "4. To roll back, run RESTORE-QUEST-APK-COCKPIT.cmd.\n"
        "Unzipping changes no installed DLL, host, original EXE/PMT or user INI.\n"
        f"Stable {STABLE_NAME} is NOT replaced.\n"
        "HMD stereo, display parity and crash freedom remain UNTESTED.\n"
    ).encode("utf-8")
    # No executable or mod DLL may be written at the ZIP root.
    for name in contents:
        if name.lower() in ("dinput8.dll","outrun-vr-host.exe","or2006c2c.exe"):
            raise AssertionError("unsafe root executable in archive")
    return contents


def write_zip(contents: dict[str,bytes], output: Path) -> None:
    if output.exists():
        raise FileExistsError("refusing to overwrite an existing test package")
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=output.name+".",suffix=".pending",dir=output.parent,delete=False
    ) as pending:
        staged=Path(pending.name)
    try:
        with zipfile.ZipFile(staged,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for filename in sorted(contents):
                info=zipfile.ZipInfo(filename,date_time=(2026,11,7,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o644 << 16
                archive.writestr(info,contents[filename])
        with zipfile.ZipFile(staged) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP CRC verification failed")
            if sorted(archive.namelist()) != sorted(contents):
                raise ValueError("ZIP entries do not match package manifest")
        # Hard-link publication refuses an existing output, even if another
        # packager created it during ZIP staging. The staged inode is then
        # unlinked; never replace an earlier valid package.
        os.link(staged,output)
    finally:
        staged.unlink(missing_ok=True)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir",required=True,type=Path,
                        help="Extracted complete matching-SHA GitHub Actions artifact")
    parser.add_argument("--ovc3",required=True,type=Path,help="Operator-built Dino OVC3 PBR model")
    parser.add_argument("--out-zip",required=True,type=Path)
    args=parser.parse_args()
    if not args.ovc3.is_file() or args.ovc3.is_symlink():
        parser.error("PBR OVC3 model is missing")
    contents=prepare_payload(args.artifact_dir,args.ovc3)
    write_zip(contents,args.out_zip)
    print(json.dumps({"output":str(args.out_zip),
                      "sha256":sha256(args.out_zip),
                      "files":len(contents),
                      "source_sha":contents["QUEST_APK_COPYRUN_PAYLOAD/IDENTITY.json"].decode()}))


if __name__=="__main__":
    main()

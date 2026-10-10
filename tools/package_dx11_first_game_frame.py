#!/usr/bin/env python3
"""Opt-in DX11 first-game-frame test bundle with real game + host binaries.

CI construction is not evidence of a running game or Quest3 validation.
"""
import argparse
import hashlib
import io
import json
import struct
import zipfile
from pathlib import Path

MARKER = b"DX11 FIRST_GAME_DRAW_FRAME progress:"
REQUIRED = ("dinput8.dll", "outrun-vr-host.exe", "OutRun2006Tweaks.ini",
            "OutRun2006Tweaks.lods.ini", "Run-DX9ExFocusTest.ps1",
            "RUN_DX11_FIRST_GAME_FRAME.cmd", "RUN_DX9EX_CONTROL.cmd",
            "DX9EX_VARIANT.txt", "DX11_TEST_README.txt", "BUILD_IDENTITY.json")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pe_machine(blob):
    if len(blob) < 512 or blob[:2] != b"MZ":
        raise ValueError("missing MZ")
    at = struct.unpack_from("<I", blob, 0x3c)[0]
    if at + 6 > len(blob) or blob[at:at+4] != b"PE\x00\x00":
        raise ValueError("invalid PE offset")
    return struct.unpack_from("<H", blob, at+4)[0]


def construct(game, host, ini, lods, runner, build_sha, feature_sha):
    if pe_machine(game) != 0x14c or len(game) < 1000000 or MARKER not in game:
        raise ValueError("missing valid x86 game DLL with native diagnostic")
    if pe_machine(host) != 0x8664 or len(host) < 10000:
        raise ValueError("missing valid x64 host")
    for value in (build_sha, feature_sha):
        if len(value) != 40 or any(c not in "0123456789abcdef" for c in value.lower()):
            raise ValueError("invalid Git SHA")
    if b"PreferD3D9Ex" not in ini:
        raise ValueError("game config must retain DX9Ex")
    def launcher(opt_in):
        value = "1" if opt_in else ""
        return ("\r\n".join((
            "@echo off", "setlocal", 'cd /d "%~dp0"',
            'set "OUTRUN_DX11_FIRST_GAME_FRAME=' + value + '"',
            'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-DX9ExFocusTest.ps1"',
            "exit /b %ERRORLEVEL%", ""
        ))).encode("ascii")
    identity = dict(task_id="CONVERSION-DX11-00537",
        feature_id="DX11:FIRST_GAME_DRAW_FRAME",
        build_source_sha=build_sha, feature_head_sha=feature_sha,
        build_source_is_feature_head=(build_sha == feature_sha),
        default_backend="DX9Ex", diagnostic_opt_in="OUTRUN_DX11_FIRST_GAME_FRAME=1",
        runtime_validation="UNTESTED", feature_ready=False)
    return {
        "dinput8.dll": game, "outrun-vr-host.exe": host,
        "OutRun2006Tweaks.ini": ini, "OutRun2006Tweaks.lods.ini": lods,
        "Run-DX9ExFocusTest.ps1": runner,
        "RUN_DX11_FIRST_GAME_FRAME.cmd": launcher(True),
        "RUN_DX9EX_CONTROL.cmd": launcher(False),
        "DX9EX_VARIANT.txt": ("variant=DX11_FIRST_GAME_FRAME_DIAGNOSTIC\n"
            "buildSourceSha=" + build_sha + "\nfeatureHeadSha=" + feature_sha +
            "\nruntime=PreferD3D9Ex=true\n").encode("ascii"),
        "DX11_TEST_README.txt": (
            "DX11 FIRST_GAME_DRAW_FRAME - DIAGNOSTIC ONLY\n"
            "Extract all files beside your own OR2006C2C.EXE (not bundled).\n"
            "Run RUN_DX9EX_CONTROL.cmd for default DX9Ex and then\n"
            "RUN_DX11_FIRST_GAME_FRAME.cmd for explicit native diagnostic.\n"
            "Keep the same gameplay section, then exit normally.\n"
            "Both launchers call Run-DX9ExFocusTest.ps1 and automatically collect\n"
            "the session log archive in DX9EX_LOGS. Compare both archives.\n"
            "Look for game_tri_draws, native_draws, desktop_insets counters.\n"
            "Only untextured XYZRHW+DIFFUSE triangles are admitted.\n"
            "An inset does not prove HMD rendering or full native gameplay.\n"
            "Runtime validation remains UNTESTED; do not promote this build.\n"
        ).encode("utf-8"),
        "BUILD_IDENTITY.json": (json.dumps(identity, indent=2)+"\n").encode("utf-8"),
    }


def verify(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = set(z.namelist())
        expected = set(REQUIRED) | {"SHA256SUMS.txt"}
        if names != expected:
            raise ValueError("missing or unexpected package files")
        lines = z.read("SHA256SUMS.txt").decode("ascii").splitlines()
        checks = dict(line.split("  ", 1) for line in lines)
        if set(checks) != set(REQUIRED) or any(
            checks[name] != sha(z.read(name)) for name in REQUIRED
        ):
            raise ValueError("SHA256 integrity mismatch")
        meta = json.loads(z.read("BUILD_IDENTITY.json"))
        if meta["runtime_validation"] != "UNTESTED" or meta["feature_ready"]:
            raise ValueError("false hardware validation claim")
        if pe_machine(z.read("dinput8.dll")) != 0x14c or \
           pe_machine(z.read("outrun-vr-host.exe")) != 0x8664:
            raise ValueError("PE machine mismatch")


def pack(payload):
    if set(payload) != set(REQUIRED):
        raise ValueError("missing package inputs")
    sums = "".join(sha(payload[name]) + "  " + name + "\n"
                   for name in sorted(REQUIRED)).encode("ascii")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(REQUIRED):
            z.writestr(name, payload[name])
        z.writestr("SHA256SUMS.txt", sums)
    data = out.getvalue()
    verify(data)
    return data


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--game", type=Path, required=True)
    p.add_argument("--host", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--build-sha", required=True)
    p.add_argument("--feature-sha", required=True)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    payload = construct(
        a.game.read_bytes(), a.host.read_bytes(),
        (root / "OutRun2006Tweaks.ini").read_bytes(),
        (root / "OutRun2006Tweaks.lods.ini").read_bytes(),
        (root / "tools/Run-DX9ExFocusTest.ps1").read_bytes(),
        a.build_sha, a.feature_sha)
    archive = pack(payload)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(archive)
    print("DX11 FIRST_GAME_FRAME bundle SHA256=" + sha(archive) +
          " game=" + sha(payload["dinput8.dll"]) +
          " host=" + sha(payload["outrun-vr-host.exe"]) +
          " RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()

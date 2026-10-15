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


def session_labeled_runner(runner):
    """Label packaged control/diagnostic log ZIPs without touching the shared runner."""
    anchor = b"$variant = ($variantLine -split '=',2)[1].Trim()"
    if runner.count(anchor) != 1:
        raise ValueError("DX9Ex log collector variant anchor changed")
    suffix = (
        b"\n$dx11TestCase = $env:OUTRUN_DX11_TEST_CASE\n"
        b"if ($dx11TestCase -ne 'CONTROL' -and "
        b"$dx11TestCase -ne 'DIAGNOSTIC') { "
        b"throw 'DX11 test session selector missing or invalid' }\n"
        b'$variant = "${variant}-${dx11TestCase}"'
    )
    staged = runner.replace(anchor, anchor + suffix, 1)
    archiver = b"Compress-Archive -Path (Join-Path $session '*') -DestinationPath $zip -Force"
    if staged.count(archiver) != 1:
        raise ValueError("session log archive anchor changed")
    # Fail the *test session*, not the game. Always archive logs before a failed
    # verdict, and leave the stock D3D9 game renderer completely untouched.
    evidence = r"""
$nativeFrameEvidenceOk = $false
if ($dx11TestCase -eq 'NATIVE_FULL_FRAME') {
    $seen = $false
    $gameDraws = 0L
    $nativeDraws = 0L
    $published = 0L
    foreach ($file in @(Get-ChildItem -Path $session -Filter 'OutRun2006Tweaks*.log' -File -ErrorAction SilentlyContinue)) {
        foreach ($line in [System.IO.File]::ReadLines($file.FullName)) {
            $hit = [regex]::Match($line, 'DX11 FIRST_GAME_DRAW_FRAME progress: game_tri_draws=(\d+) native_draws=(\d+) desktop_insets=(\d+)')
            if (!$hit.Success) { continue }
            $seen = $true
            $gameDraws = [Math]::Max($gameDraws, [long]$hit.Groups[1].Value)
            $nativeDraws = [Math]::Max($nativeDraws, [long]$hit.Groups[2].Value)
            $published = [Math]::Max($published, [long]$hit.Groups[3].Value)
        }
    }
    $nativeFrameEvidenceOk = $env:OUTRUN_DX11_FIRST_GAME_FRAME -eq '1' -and
        $env:OUTRUN_DX11_FULL_GAME_FRAME -eq '1' -and $seen -and
        $gameDraws -gt 0 -and $nativeDraws -gt 0 -and $published -gt 0
    $verdict = if ($nativeFrameEvidenceOk) { 'NATIVE_FULL_FRAME_GPU_COPYBACK_OBSERVED' } else { 'NO_NATIVE_FULL_FRAME_EVIDENCE' }
    @(
        "verdict=$verdict",
        "gameDraws=$gameDraws",
        "nativeDraws=$nativeDraws",
        "publishedBackbufferFrames=$published",
        "nativeModeRequested=$($env:OUTRUN_DX11_FULL_GAME_FRAME)",
        "outputRoute=D3D11_GPU_TO_CPU_TO_D3D9_BACKBUFFER",
        "menuVehicleRaceVisualParity=UNTESTED",
        "quest3Stereo=UNTESTED",
        "note=Nonzero counters do not prove menu, vehicle, race or stereo parity"
    ) | Set-Content (Join-Path $session 'DX11_NATIVE_EVIDENCE.txt') -Encoding UTF8
}
""".encode("ascii")
    failure = b"\nif ($dx11TestCase -eq 'NATIVE_FULL_FRAME' -and -not $nativeFrameEvidenceOk) { throw 'DX11 full native game frame NOT observed; examine DX11_NATIVE_EVIDENCE.txt inside the saved log ZIP.' }\n"
    return staged.replace(archiver, evidence + b"\n" + archiver + failure, 1)


def construct(game, host, ini, lods, runner, build_sha, feature_sha):
    # D3D11 full-frame opt-in is a UTF-16 Windows environment-variable literal.
    # Reject stale binaries that only implement the old 256x144 inset path.
    full_frame_marker = "OUTRUN_DX11_FULL_GAME_FRAME".encode("utf-16-le")
    if (pe_machine(game) != 0x14c or len(game) < 1000000 or
            MARKER not in game or full_frame_marker not in game):
        raise ValueError("missing x86 native full-frame game implementation")
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
            'set "OUTRUN_DX11_FULL_GAME_FRAME=' + value + '"',
            'set "OUTRUN_DX11_TEST_CASE=' +
            ("NATIVE_FULL_FRAME" if opt_in else "CONTROL") + '"',
            'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-DX9ExFocusTest.ps1"',
            "exit /b %ERRORLEVEL%", ""
        ))).encode("ascii")
    identity = dict(task_id="CONVERSION-DX11-00537",
        feature_id="DX11:FIRST_GAME_DRAW_FRAME",
        build_source_sha=build_sha, feature_head_sha=feature_sha,
        build_source_is_feature_head=(build_sha == feature_sha),
        default_backend="DX9Ex",
        test_mode="NATIVE_FULL_FRAME_D3D11_GPU_COPYBACK_D3D9",
        native_test_environment=["OUTRUN_DX11_FIRST_GAME_FRAME=1",
                                 "OUTRUN_DX11_FULL_GAME_FRAME=1"],
        runtime_validation="UNTESTED", feature_ready=False)
    return {
        "dinput8.dll": game, "outrun-vr-host.exe": host,
        "OutRun2006Tweaks.ini": ini, "OutRun2006Tweaks.lods.ini": lods,
        "Run-DX9ExFocusTest.ps1": session_labeled_runner(runner),
        "RUN_DX11_FIRST_GAME_FRAME.cmd": launcher(True),
        "RUN_DX9EX_CONTROL.cmd": launcher(False),
        "DX9EX_VARIANT.txt": ("variant=DX11_NATIVE_FULL_FRAME\n"
            "buildSourceSha=" + build_sha + "\nfeatureHeadSha=" + feature_sha +
            "\nruntime=PreferD3D9Ex=true\n").encode("ascii"),
        "DX11_TEST_README.txt": (
            "DX11 NATIVE FULL GAME FRAME - EXPERIMENTAL TEST\n"
            "Extract all files beside your OWN OR2006C2C.EXE (not bundled).\n"
            "RUN_DX9EX_CONTROL.cmd: stock D3D9/DX9Ex reference, native OFF.\n"
            "RUN_DX11_FIRST_GAME_FRAME.cmd: EXPLICITLY enables both native\n"
            "D3D11 first game draw AND full-game-size frame on every run.\n"
            "No automatic DX11 production promotion; unsupported drawings\n"
            "retain original D3D9/gamepad fallback to avoid blank screens.\n"
            "On exit the log ZIP contains DX11_NATIVE_EVIDENCE.txt.\n"
            "The DX11 runner returns FAILURE if the captured log has no\n"
            "game Draw, native Draw and published backbuffer frame evidence.\n"
            "Allow 300+ Present calls before exiting (several seconds).\n"
            "A PASS proves only some GPU-drawn pixels copied back into the\n"
            "D3D9 backbuffer. It does NOT prove full scene completeness,\n"
            "menu/vehicle/race visual parity, native OpenXR L/R eyes or 72Hz.\n"
            "Compare the same menu, vehicle and racing sections against\n"
            "CONTROL. Keep both ZIPs and screenshots for manual inspection.\n"
            "Native output is currently D3D11 -> CPU -> D3D9 Present,\n"
            "not direct D3D11 OpenXR swapchain presentation.\n"
            "Runtime validation remains UNTESTED until actual game/HMD run.\n"
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
        checks = {filename: digest for digest, filename in
                  (line.split("  ", 1) for line in lines)}
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

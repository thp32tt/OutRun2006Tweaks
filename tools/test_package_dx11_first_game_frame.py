#!/usr/bin/env python3
"""Synthetic packaging negatives, not a live GPU test."""
import io
import json
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_dx11_first_game_frame import MARKER, construct, pack, verify


def fake_pe(machine, size, marker=b""):
    data = bytearray(size)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 128)
    data[128:132] = b"PE\x00\x00"
    struct.pack_into("<H", data, 132, machine)
    data[512:512+len(marker)] = marker
    return bytes(data)


def must_fail(f, label):
    try:
        f()
    except (ValueError, KeyError):
        return
    raise AssertionError("unsafe package accepted: " + label)



def verify_bundle_ci_route(workflow):
    """Check PR and target-push admission, real binary inputs, and SHA identity.

    Static workflow test; not a running game or HMD test.
    """
    tag = "  dx11-first-game-frame-bundle:"
    if workflow.count(tag) != 1:
        raise ValueError("DX11 diagnostic bundle job missing or ambiguous")
    job = workflow.split(tag, 1)[1]
    if "    if: >-" not in job or "    needs: [game-x86-r26-hud-safe, host-x64]" not in job:
        raise ValueError("CI admission or binary dependencies missing")
    guard = job.split("    if: >-", 1)[1].split("    needs:", 1)[0]
    normalized = "".join(guard.split())
    for required in (
        "github.event_name=='pull_request'&&github.head_ref=='vr-d3d9ex-review-feature-dx11-00537'",
        "github.event_name=='push'&&github.ref=='refs/heads/vr-dx11-native-r71'",
        "||",
    ):
        if required not in normalized:
            raise ValueError("target push or feature PR admission missing")
    if "branches: [ vr-openxr, vr-dx11-native-r71 ]" not in workflow.split("  pull_request:", 1)[0]:
        raise ValueError("OpenXR target push trigger missing")
    for required in (
        "name: outrun2006-vr-x86-r26-hud-safe",
        "name: outrun-vr-host-x64",
        "--game payload/game/dinput8.dll",
        "--host payload/host/outrun-vr-host.exe",
        "Feature acceptance: DX11-TEST-BUNDLE",
    ):
        if required not in job:
            raise ValueError("bundle binary input or acceptance step missing: " + required)
    # The PR property is empty on push; the fallback must identify the exact
    # target SHA in output, feature metadata and uploaded artifact.
    if job.count("github.event.pull_request.head.sha || github.sha") != 3:
        raise ValueError("push SHA fallback missing in ZIP, metadata or artifact")
    if "--build-sha" not in job or "github.sha" not in job:
        raise ValueError("actual checked-out binary build identity missing")


def test_bundle_ci_route():
    workflow = (Path(__file__).resolve().parents[1] /
                ".github" / "workflows" / "vr-openxr.yml").read_text(encoding="utf-8")
    verify_bundle_ci_route(workflow)
    for old, bad, reason in (
        ("github.event_name == 'push'", "github.event_name == 'schedule'",
         "PR-only regression"),
        ("github.ref == 'refs/heads/vr-dx11-native-r71'",
         "github.ref == 'refs/heads/other'", "wrong target ref"),
        ("github.event.pull_request.head.sha || github.sha",
         "github.event.pull_request.head.sha", "push SHA identity lost"),
        ("needs: [game-x86-r26-hud-safe, host-x64]",
         "needs: [host-x64]", "missing game build dependency"),
    ):
        assert old in workflow, "negative test fixture absent: " + reason
        must_fail(lambda old=old, bad=bad: verify_bundle_ci_route(
            workflow.replace(old, bad, 1)), reason)


def main():
    a = "a" * 40
    game = fake_pe(0x14c, 1000500, MARKER)
    host = fake_pe(0x8664, 12000)
    runner = b"$variant = ($variantLine -split '=',2)[1].Trim()\n"
    args = (game, host, b"PreferD3D9Ex=true", b"LOD", runner, a, a)
    payload = construct(*args)
    data = pack(payload)
    verify(data)
    must_fail(lambda: construct(host, game, *args[2:]), "reversed architectures")
    must_fail(lambda: construct(game.replace(MARKER, b"x"*len(MARKER)), *args[1:]), "marker absent")
    must_fail(lambda: construct(*args[:-1], "bad"), "invalid identity")
    must_fail(lambda: construct(*args[:4], b"renamed collector", *args[5:]),
              "changed log collector cannot silently lose session labels")
    must_fail(lambda: construct(*args[:4], runner + runner, *args[5:]),
              "ambiguous log collector anchor")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        content = {name:z.read(name) for name in z.namelist()}
    content["DX9EX_VARIANT.txt"] += b"tamper"
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as z:
        for name, value in content.items():
            z.writestr(name, value)
    must_fail(lambda: verify(result.getvalue()), "tampered payload")
    assert json.loads(payload["BUILD_IDENTITY.json"])["runtime_validation"] == "UNTESTED"
    assert b"OUTRUN_DX11_FIRST_GAME_FRAME=1" in payload["RUN_DX11_FIRST_GAME_FRAME.cmd"]
    assert b'OUTRUN_DX11_FIRST_GAME_FRAME="' in payload["RUN_DX9EX_CONTROL.cmd"]
    assert b"OUTRUN_DX11_TEST_CASE=CONTROL" in payload["RUN_DX9EX_CONTROL.cmd"]
    assert b"OUTRUN_DX11_TEST_CASE=DIAGNOSTIC" in payload["RUN_DX11_FIRST_GAME_FRAME.cmd"]
    packaged_runner = payload["Run-DX9ExFocusTest.ps1"]
    assert packaged_runner.count(b'$variant = "${variant}-${dx11TestCase}"') == 1
    assert b"OUTRUN_DX11_TEST_CASE" in packaged_runner
    assert b"XYZ+DIFFUSE" in payload["DX11_TEST_README.txt"]
    assert b"-CONTROL or -DIAGNOSTIC" in payload["DX11_TEST_README.txt"]
    test_bundle_ci_route()
    print("DX11 first-game-frame packaging PE/SHA/tamper/opt-in tests: PASS (synthetic)")


if __name__ == "__main__":
    main()

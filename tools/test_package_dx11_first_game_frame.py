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
    # Validate the target branch as a *list entry*, not by exact literal
    # equality with a historical two-branch YAML list. Other approved
    # feature branches may coexist without disabling the target push Gate.
    push_part = workflow.split("  pull_request:", 1)[0]
    branch_lines = [line for line in push_part.splitlines()
                    if line.lstrip().startswith("branches:")]
    if len(branch_lines) != 1 or "[" not in branch_lines[0] or "]" not in branch_lines[0]:
        raise ValueError("OpenXR target push trigger missing or ambiguous")
    branch_list = branch_lines[0].split("[", 1)[1].split("]", 1)[0]
    branches = [entry.strip().strip("'\\\"") for entry in branch_list.split(",")]
    if "vr-dx11-native-r71" not in branches:
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
    # A removed/renamed target branch must still fail, even when other
    # legitimate push branches are present.
    must_fail(lambda: verify_bundle_ci_route(
        workflow.replace(
            "branches: [ vr-openxr, vr-dx11-native-r71,",
            "branches: [ vr-openxr, vr-dx11-disabled,",
            1)), "target push branch removed")
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
        # Mutate the exact bundle job, not an unrelated prior push gate.
        # The negative fixture must prove this job rejects PR-only, foreign
        # branch, missing build identity and missing game binary dependencies.
        # A global first occurrence can hit another job and falsely PASS.
        prefix, marker, bundle_job = workflow.partition(
            "  dx11-first-game-frame-bundle:")
        assert marker and old in bundle_job, (
            "bundle negative fixture missing: " + reason)
        must_fail(lambda old=old, bad=bad: verify_bundle_ci_route(
            prefix + marker + bundle_job.replace(old, bad, 1)), reason)


def verify_native_mono_shadow_capture_source(source):
    """Mono DX11 must arm VB/IB source capture independently of stereo XYZRHW."""
    method = "void R30ArmDx11NativeMonoBufferCapture() noexcept"
    if source.count(method) != 1:
        raise ValueError("missing/ambiguous DX11 mono buffer capture arm")
    helper = source.split(method, 1)[1].split(
        "void R30InstallBufferCreationHooks(", 1)[0]
    for required in ("Settings::VRStereo",
                     "live_game_frame::diagnostic_enabled()",
                     "R30BufferShadowCaptureArmed.exchange("):
        if required not in helper:
            raise ValueError("native mono capture is not restricted to opt-in")
    install = source.split("void R30InstallBufferCreationHooks(", 1)[1].split(
        "void R30RollbackBufferShadowHooks(", 1)[0]
    if "R30ArmDx11NativeMonoBufferCapture();" not in install:
        raise ValueError("DX11 buffer capture not armed at resource setup")
    reset = source.split("HRESULT __stdcall ResetDestR30(", 1)[1].split(
        "float R30HudScaleValue()", 1)[0]
    if "if (SUCCEEDED(hr))\n                R30ArmDx11NativeMonoBufferCapture();" not in reset:
        raise ValueError("DX11 mono capture not rearmed after successful Reset")


def test_native_mono_shadow_capture_source():
    source = (Path(__file__).resolve().parents[1] / "src" / "vr" / "d3d9" /
              "stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8")
    verify_native_mono_shadow_capture_source(source)
    for old, bad, reason in (
        ("Settings::VRStereo", "false", "stereo guard removed"),
        ("live_game_frame::diagnostic_enabled()", "true", "opt-in guard removed"),
        ("if (SUCCEEDED(hr))\n                R30ArmDx11NativeMonoBufferCapture();",
         "if (false)\n                R30ArmDx11NativeMonoBufferCapture();",
         "post-Reset rearm disabled"),
    ):
        assert old in source, "missing fixture: " + reason
        must_fail(lambda old=old, bad=bad:
                  verify_native_mono_shadow_capture_source(
                      source.replace(old, bad, 1)), reason)


def verify_native_sm3_reject_diagnostics(source):
    """Stage buckets identify live SM3 failures without counting D3D9 as DX11."""
    state = "std::array<std::uint64_t, 11> liveSm3RejectStages{};"
    if source.count(state) != 1:
        raise ValueError("missing SM3 stage diagnostics")
    name = "bool submit_live_sm3_game_draw("
    if source.count(name) != 1:
        raise ValueError("missing game SM3 native conversion function")
    body = source.split(name, 1)[1].split(
        "// Reuse geometric growth buffers", 1)[0]
    for required in ("struct RejectionAudit",
                     "rejectionAudit{s.liveSm3RejectStages, rejectionStage, submitted}",
                     "if (!succeeded) ++counters[",
                     "submitted = true;"):
        if required not in body:
            raise ValueError("SM3 failure instrumentation incomplete")
    for n in range(1, 11):
        if body.count("rejectionStage = %du;" % n) != 1:
            raise ValueError("missing or duplicate SM3 conversion failure stage")
    if "sm3_reject=[source:{}" not in source:
        raise ValueError("SM3 rejection counters absent from game log")
    if "sm3_state_reject=[query:{}" not in source:
        raise ValueError("detailed SM3 state failure reasons absent from log")
    if "std::array<std::uint64_t, 8> liveSm3StateRejectReasons{};" not in source:
        raise ValueError("detailed SM3 state counters missing")
    for n in range(8):
        if "++s.liveSm3StateRejectReasons[%d];" % n not in source:
            raise ValueError("SM3 state guard no longer accounts for reason")
    if "skipped_poisoned_draws={}" not in source:
        raise ValueError("native poison short-circuit evidence absent")
    if "if (fullMode && s.frameBatch.stopped) {" not in source:
        raise ValueError("failed frame still submits redundant SM3 conversions")


def test_native_sm3_reject_diagnostics():
    source = (Path(__file__).resolve().parents[1] / "src" / "vr" /
              "d3d11" / "live_game_frame_bridge.cpp").read_text(encoding="utf-8")
    verify_native_sm3_reject_diagnostics(source)
    for old, bad, reason in (
        ("submitted = true;", "submitted = false;", "native success is never counted"),
        ("sm3_reject=[source:{}", "sm3_reject=[absent:{}", "no runtime failure evidence"),
        ("if (fullMode && s.frameBatch.stopped) {",
         "if (false && s.frameBatch.stopped) {", "redundant poisoned-frame conversions"),
    ):
        assert old in source, "missing negative fixture: " + reason
        must_fail(lambda old=old, bad=bad: verify_native_sm3_reject_diagnostics(
            source.replace(old, bad, 1)), reason)


def main():
    a = "a" * 40
    game = fake_pe(0x14c, 1000500, MARKER + "OUTRUN_DX11_FULL_GAME_FRAME".encode("utf-16-le"))
    host = fake_pe(0x8664, 12000)
    runner = (b"$variant = ($variantLine -split '=',2)[1].Trim()\n"
              b"Set-Content (Join-Path $session 'RUN_ARGS.txt') ($gameArgs -join ' ') -Encoding UTF8\n"
              b"Compress-Archive -Path (Join-Path $session '*') -DestinationPath $zip -Force\n")
    args = (game, host, b"PreferD3D9Ex=true", b"LOD", runner, a, a)
    payload = construct(*args)
    data = pack(payload)
    verify(data)
    must_fail(lambda: construct(host, game, *args[2:]), "reversed architectures")
    must_fail(lambda: construct(game.replace(MARKER, b"x"*len(MARKER)), *args[1:]), "marker absent")
    must_fail(lambda: construct(game.replace("OUTRUN_DX11_FULL_GAME_FRAME".encode("utf-16-le"),
                                             b"x"*len("OUTRUN_DX11_FULL_GAME_FRAME".encode("utf-16-le"))),
                                *args[1:]), "full-frame marker absent")
    must_fail(lambda: construct(*args[:-1], "bad"), "invalid identity")
    must_fail(lambda: construct(*args[:4], b"renamed collector", *args[5:]),
              "changed log collector cannot silently lose session labels")
    must_fail(lambda: construct(*args[:4], runner + runner, *args[5:]),
              "ambiguous log collector anchor")
    must_fail(lambda: construct(*args[:4], runner.replace(b"Compress-Archive", b"Archive-Other"),
                                *args[5:]), "missing log ZIP anchor")
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
    assert b"OUTRUN_DX11_FULL_GAME_FRAME=1" in payload["RUN_DX11_FIRST_GAME_FRAME.cmd"]
    assert b'OUTRUN_DX11_GPU_SHARED_DESKTOP=1' in payload["RUN_DX11_GPU_DESKTOP.cmd"]
    assert b'OUTRUN_DX11_TEST_CASE=NATIVE_GPU_DESKTOP' in payload["RUN_DX11_GPU_DESKTOP.cmd"]
    assert b'OUTRUN_DX11_GPU_SHARED_DESKTOP="' in payload["RUN_DX11_FIRST_GAME_FRAME.cmd"]
    assert b'OUTRUN_DX11_GPU_SHARED_DESKTOP="' in payload["RUN_DX9EX_CONTROL.cmd"]
    assert b'OUTRUN_DX11_FULL_GAME_FRAME="' in payload["RUN_DX9EX_CONTROL.cmd"]
    assert b'OUTRUN_DX11_FIRST_GAME_FRAME="' in payload["RUN_DX9EX_CONTROL.cmd"]
    assert b"OUTRUN_DX11_TEST_CASE=CONTROL" in payload["RUN_DX9EX_CONTROL.cmd"]
    assert b"OUTRUN_DX11_TEST_CASE=NATIVE_FULL_FRAME" in payload["RUN_DX11_FIRST_GAME_FRAME.cmd"]
    packaged_runner = payload["Run-DX9ExFocusTest.ps1"]
    assert packaged_runner.count(b'$variant = "${variant}-${dx11TestCase}"') == 1
    assert b"OUTRUN_DX11_TEST_CASE" in packaged_runner
    assert b"DX11_NATIVE_EVIDENCE.txt" in packaged_runner
    assert b"$dx11TestCase -ne 'NATIVE_FULL_FRAME'" in packaged_runner
    assert b"$dx11TestCase -ne 'NATIVE_GPU_DESKTOP'" in packaged_runner
    assert b"gpuDesktopFrames -gt 0" in packaged_runner
    assert b"$gameArgs += '-Stereo=false'" in packaged_runner
    assert b"$gameArgs += '-antialiasing 0'" in packaged_runner
    assert b"$gameArgs += '-nofog'" in packaged_runner
    assert b"noFogDiagnosticRequested=" in packaged_runner
    assert b"nativeBootstrapCompatibleObserved" in packaged_runner
    assert b"if ($dx11TestCase -ne 'CONTROL')" in packaged_runner
    assert b"monoStereoObserved" in packaged_runner
    assert b"D3D11_GPU_TO_D3D9EX_SHARED_DESKTOP" in packaged_runner
    assert b"fullFrameModeObserved" in packaged_runner
    assert b"gameDraws -gt 0" in packaged_runner
    assert b"nativeDraws -gt 0" in packaged_runner
    assert b"published -gt 0" in packaged_runner
    assert b"throw 'DX11 full native game frame NOT observed" in packaged_runner
    assert b"D3D11 -> CPU -> D3D9 Present" in payload["DX11_TEST_README.txt"]
    assert b"D3D11 -> shared resource -> D3D9Ex Present" in payload["DX11_TEST_README.txt"]
    assert b"-Stereo=false" in payload["DX11_TEST_README.txt"]
    assert b"-antialiasing 0" in payload["DX11_TEST_README.txt"]
    assert b"-nofog" in payload["DX11_TEST_README.txt"]
    assert b"Fog/full visual parity is therefore NOT VALIDATED" in payload["DX11_TEST_README.txt"]
    assert json.loads(payload["BUILD_IDENTITY.json"])["native_desktop_fog_disabled_diagnostic"] is True
    assert json.loads(payload["BUILD_IDENTITY.json"])["native_desktop_single_sample_required"] is True
    assert json.loads(payload["BUILD_IDENTITY.json"])["native_desktop_mono_required"] is True
    mono = runner.replace(b"Set-Content (Join-Path $session 'RUN_ARGS.txt') ($gameArgs -join ' ') -Encoding UTF8", b"missing anchor")
    must_fail(lambda: construct(*args[:4], mono, *args[5:]), "missing game runner args anchor")
    assert json.loads(payload["BUILD_IDENTITY.json"])["test_mode"] == "NATIVE_FULL_FRAME_D3D11_GPU_COPYBACK_D3D9"
    test_bundle_ci_route()
    test_native_mono_shadow_capture_source()
    test_native_sm3_reject_diagnostics()
    print("DX11 first-game-frame packaging PE/SHA/tamper/opt-in tests: PASS (synthetic)")


if __name__ == "__main__":
    main()

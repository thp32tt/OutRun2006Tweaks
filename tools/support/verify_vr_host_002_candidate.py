#!/usr/bin/env python3
"""Deterministic Role-C checks for the VR-HOST-002 reconciliation candidate.

This verifier does not claim HMD correctness.  It checks the source contract,
models the stale-run/bootstrap rejection truth tables, and optionally inspects
the immutable DX9Ex package produced for the exact candidate SHA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


REQUIRED_SOURCE_MARKERS = {
    "src/vr/ipc/protocol.hpp": (
        "RenderFrameRunGenerationIndex = 11",
        "RenderFrameRunIdentityMatches(",
        "frame.clientPid == ring.clientPid",
        "frame.reserved[RenderFrameRunGenerationIndex] == ring.reserved0",
        "static_assert(sizeof(SharedRenderFrameState) == 256)",
        "static_assert(sizeof(SharedRenderFrameRing) == 1056)",
    ),
    "src/vr/d3d9/stereo_renderer_r7.inc": (
        "ClaimRenderFrameRingForCurrentRun()",
        "RenderFrameRing->reserved0 = RenderFrameRunGeneration",
        "std::memset(&slot, 0, sizeof(slot))",
        "frame.reserved[OutRunVR::RenderFrameRunGenerationIndex]=RenderFrameRunGeneration",
    ),
    "vrhost/src/main.cpp": (
        "OutRunVR::RenderFrameRunIdentityMatches(*state_, out)",
        "ringBefore == ringAfter",
    ),
    "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp": (
        "OutRunVR::RenderFrameRunIdentityMatches(*FrameRing, candidate)",
        "ringBefore == ringAfter",
    ),
    "vrhost/src/runtime/openxr_api_compat.hpp": (
        "OutRunVR::RenderFrameRunIdentityMatches(*FrameRing, out)",
    ),
    "src/vr/ipc/shadow_legacy_v2.hpp": (
        "RenderFrameRunIdentityMatches(ring, out)",
    ),
    "vrhost/src/main_r23.cpp": (
        "R23UsableGameplayBootstrapFrame(",
        "frame.presentationMode != OutRunVR::PresentationGameplay",
        "frame.state != OutRunVR::StereoSbsActive",
        "frame.failureReason != OutRunVR::StereoFailureNone",
        "(frame.flags & OutRunVR::RenderFramePresentInFlight) != 0",
        "width == frame.backbufferWidth",
        "height == frame.backbufferHeight",
        "const bool cachedHold = cachedProjectionValid",
        "awaitingFirstGameplayStereo = false",
        "finalLayerKind = \"gameplay-bootstrap-menu-hold\"",
    ),
}

REQUIRED_PACKAGE_FILES = {
    "BUILD_INPUTS.json",
    "BUILD_MATRIX_ID.txt",
    "Collect-OutRunVRLogs.ps1",
    "OutRun2006Tweaks.ini",
    "OutRunVR-Backend-Selector.ps1",
    "OutRunVR-TestProfiles.ps1",
    "Run-OutRunVRTest.ps1",
    "SHA256SUMS.txt",
    "backends/d3d9/SOURCE_SHA.txt",
    "backends/d3d9/dinput8.dll",
    "backends/d3d9/outrun-vr-host.exe",
}

FORBIDDEN_PACKAGE_BASENAMES = {
    "d3d9.dll",
    "multiviewpatcher.dll",
    "outrun-vr-host-dx12.exe",
}


def git_text(repo: Path, sha: str, rel: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{sha}:{rel}"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.decode("utf-8")


def require_markers(repo: Path, sha: str) -> None:
    for rel, markers in REQUIRED_SOURCE_MARKERS.items():
        text = git_text(repo, sha, rel)
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise AssertionError(f"{rel}: missing source contract markers: {missing}")


def identity_matches(ring_pid: int, ring_generation: int,
                     frame_pid: int, frame_generation: int) -> bool:
    return (
        ring_pid != 0
        and ring_generation != 0
        and frame_pid == ring_pid
        and frame_generation == ring_generation
    )


def usable_bootstrap(frame: dict[str, int | bool]) -> bool:
    required = 0x01 | 0x02 | 0x04 | 0x08
    if (
        not frame["frame_id"]
        or not frame["pose_id"]
        or frame["presentation"] != 1
        or frame["state"] != 1
        or frame["failure"] != 0
        or frame["present_qpc"] <= 0
        or not frame["backbuffer_width"]
        or not frame["backbuffer_height"]
        or (frame["flags"] & 0x10) != 0
        or (frame["flags"] & required) != required
    ):
        return False
    if (frame["flags"] & 0x20) == 0:
        return True
    return (
        0 <= frame["slot"] < 4
        and frame["transport_generation"] != 0
        and frame["left_handle"] != 0
        and frame["right_handle"] != 0
        and frame["direct_width"] != 0
        and frame["direct_height"] != 0
        and frame["direct_width"] == frame["backbuffer_width"]
        and frame["direct_height"] == frame["backbuffer_height"]
    )


def test_failure_truth_tables() -> None:
    identity_cases = (
        ((10, 20, 10, 20), True, "same run"),
        ((10, 20, 11, 20), False, "stale PID"),
        ((10, 20, 10, 21), False, "stale generation"),
        ((0, 20, 0, 20), False, "unclaimed ring PID"),
        ((10, 0, 10, 0), False, "unclaimed generation"),
    )
    for args, expected, label in identity_cases:
        assert identity_matches(*args) is expected, label

    base = {
        "frame_id": 9,
        "pose_id": 12,
        "presentation": 1,
        "state": 1,
        "failure": 0,
        "present_qpc": 123,
        "backbuffer_width": 3440,
        "backbuffer_height": 1440,
        "flags": 0x01 | 0x02 | 0x04 | 0x08,
        "slot": 0,
        "transport_generation": 0,
        "left_handle": 0,
        "right_handle": 0,
        "direct_width": 0,
        "direct_height": 0,
    }
    assert usable_bootstrap(base), "valid classic SBS frame must release gameplay"
    for field, bad in (
        ("frame_id", 0),
        ("pose_id", 0),
        ("presentation", 2),
        ("state", 0),
        ("failure", 1),
        ("present_qpc", 0),
        ("backbuffer_width", 0),
    ):
        candidate = dict(base)
        candidate[field] = bad
        assert not usable_bootstrap(candidate), f"must reject bad {field}"
    for bit in (0x01, 0x02, 0x04, 0x08):
        candidate = dict(base)
        candidate["flags"] &= ~bit
        assert not usable_bootstrap(candidate), f"must reject missing flag {bit:#x}"
    in_flight = dict(base)
    in_flight["flags"] |= 0x10
    assert not usable_bootstrap(in_flight), "must reject in-flight producer frame"

    direct = dict(base)
    direct.update({
        "flags": base["flags"] | 0x20,
        "slot": 2,
        "transport_generation": 7,
        "left_handle": 101,
        "right_handle": 102,
        "direct_width": 3440,
        "direct_height": 1440,
    })
    assert usable_bootstrap(direct), "valid DirectGPU frame must release gameplay"
    for field, bad in (
        ("slot", 4),
        ("transport_generation", 0),
        ("left_handle", 0),
        ("right_handle", 0),
        ("direct_width", 3439),
        ("direct_height", 1439),
    ):
        candidate = dict(direct)
        candidate[field] = bad
        assert not usable_bootstrap(candidate), f"must reject bad direct {field}"


def normalized_name(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).as_posix().lstrip("./")


def pe_machine(payload: bytes) -> int:
    if payload[:2] != b"MZ":
        raise AssertionError("not a PE image")
    pe_offset = struct.unpack_from("<I", payload, 0x3C)[0]
    if payload[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise AssertionError("invalid PE signature")
    return struct.unpack_from("<H", payload, pe_offset + 4)[0]


def validate_package(package: Path, expected_sha: str) -> dict[str, str]:
    with zipfile.ZipFile(package) as archive:
        names = {normalized_name(name): name for name in archive.namelist() if not name.endswith("/")}
        missing = sorted(REQUIRED_PACKAGE_FILES - names.keys())
        if missing:
            raise AssertionError(f"package missing files: {missing}")
        forbidden = sorted(
            name for name in names
            if PurePosixPath(name).name.lower() in FORBIDDEN_PACKAGE_BASENAMES
            or "dxvk" in name.lower()
            or "d3d9on12" in name.lower()
        )
        if forbidden:
            raise AssertionError(f"package contains forbidden backend payloads: {forbidden}")

        inputs = json.loads(archive.read(names["BUILD_INPUTS.json"]).decode("utf-8-sig"))
        assert inputs["IntegrationSha"] == expected_sha
        assert inputs["VariantId"] == "ACTIVE_FULL_R34"
        assert inputs["DefaultTestProfile"] == "CORRECTNESS"
        assert inputs["Profiles"] == ["CONTROL", "CORRECTNESS", "PERFORMANCE"]
        assert inputs["UserRuntimeVerified"] is False
        source_sha = archive.read(names["backends/d3d9/SOURCE_SHA.txt"]).decode().strip()
        assert source_sha == expected_sha

        sums = archive.read(names["SHA256SUMS.txt"]).decode("ascii")
        checked = 0
        for line in sums.splitlines():
            if not line.strip():
                continue
            digest, rel = re.split(r"\s{2,}", line.strip(), maxsplit=1)
            rel = normalized_name(rel)
            if rel == "SHA256SUMS.txt":
                continue
            if rel not in names:
                raise AssertionError(f"checksum references missing file: {rel}")
            actual = hashlib.sha256(archive.read(names[rel])).hexdigest()
            if actual.lower() != digest.lower():
                raise AssertionError(f"checksum mismatch: {rel}")
            checked += 1
        assert checked == len(names) - 1, (checked, len(names))

        game_machine = pe_machine(archive.read(names["backends/d3d9/dinput8.dll"]))
        host_machine = pe_machine(archive.read(names["backends/d3d9/outrun-vr-host.exe"]))
        assert game_machine == 0x014C, f"game DLL machine={game_machine:#x}, expected x86"
        assert host_machine == 0x8664, f"host machine={host_machine:#x}, expected x64"

        profiles = archive.read(names["OutRunVR-TestProfiles.ps1"]).decode("utf-8-sig")
        for marker in (
            "'-PreferD3D9Ex=true'",
            "'-DirectGpuOnly=false'",
            "'-DisableDesktopDuplication=false'",
            "'-TargetRefreshRateHz=0'",
            "'-SkyGlowFactor=1'",
            "'-FrameCadenceTargetHz=0'",
            "OUTRUN_VR_TEST_PROFILE='CORRECTNESS'",
            "OUTRUN_VR_PERFORMANCE_PROFILE='0'",
        ):
            assert marker in profiles, f"profile contract missing: {marker}"

        runner = archive.read(names["Run-OutRunVRTest.ps1"]).decode("utf-8-sig")
        collector = archive.read(names["Collect-OutRunVRLogs.ps1"]).decode("utf-8-sig")
        for marker in (
            "OUTRUN_VR_SESSION_ID",
            "OUTRUN_VR_VARIANT_ID",
            "OUTRUN_VR_MATRIX_ID",
            "OUTRUN_VR_CONFIG_SHA256",
            "RUN_OVERRIDES.txt",
        ):
            assert marker in runner, f"runner identity contract missing: {marker}"
        for marker in (
            "$variant/$profile/$session",
            "CURRENT_VR_SESSION.json",
            "CollectedCaptures",
            "ConfigSha256",
            "TEST_PROFILE=$profile",
        ):
            assert marker in collector, f"collector contract missing: {marker}"

    return {
        "packageSha256": hashlib.sha256(package.read_bytes()).hexdigest(),
        "gameMachine": "PE32-x86",
        "hostMachine": "PE32+-x64",
        "checkedFiles": str(len(names)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()

    require_markers(args.repo, args.candidate_sha)
    test_failure_truth_tables()
    result = {
        "candidateSha": args.candidate_sha,
        "sourceContract": "pass",
        "failureTruthTables": "pass",
        "runtimeClaim": "not-tested",
    }
    if args.package:
        result["package"] = validate_package(args.package, args.candidate_sha)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, OSError, subprocess.CalledProcessError,
            zipfile.BadZipFile) as error:
        print(f"VR-HOST-002 validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)

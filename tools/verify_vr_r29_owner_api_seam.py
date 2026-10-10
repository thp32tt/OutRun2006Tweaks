#!/usr/bin/env python3
"""Guard the R29 -> R30 owner seam against accidental private-state reuse.

Includes mutation checks: replacing each real R29 owner delegation with a
no-op/wrong result must cause verification failure. This is an interim static
check; Win32 compile/link and HMD acceptance remain separate gates.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9"
CORE = ROOT / "src/vr/core"


def body(source: str, signature: str) -> str:
    pos = source.find(signature)
    if pos < 0:
        raise AssertionError(f"definition missing: {signature}")
    start = source.find("{", pos)
    if start < 0:
        raise AssertionError(f"body missing: {signature}")
    depth = 0
    for idx in range(start, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:idx]
    raise AssertionError(f"unclosed body: {signature}")


OWNER_CALLS = {
    "bool R29OwnerStableStereoBase(": "return R29StableStereoBase(device);",
    "bool R29OwnerFragileEffectCached(": "return R29FragileEffectCached(device, fragile);",
    "void R29OwnerArmMonoSafety(": "R29ArmMonoSafety(extraPresents);",
    "void R29OwnerNoteStableTwoEyeDraw(": "R29TelemetryNoteStableTwoEyeDraw();",
    "R29OwnerInstallStatus() noexcept": "R29StereoInstallState.load(std::memory_order_acquire);",
}



FRAME_DELEGATIONS = {
    "view.width": "BackBufferDesc.Width",
    "view.height": "BackBufferDesc.Height",
    "view.backBuffer": "BackBuffer",
    "view.rightEyeSurface": "RightEyeSurface",
    "view.rightEyeDepth": "RightEyeDepth",
    "view.trackedDepthStencil": "TrackedDepthStencil",
    "view.presentEpoch": "PresentEpoch",
    "view.poseSequence": "FrameStereoPoseSequence",
    "view.hadWorldStereo": "FrameHadWorldStereo",
    "view.hadDuplicatedDraw": "FrameHadDuplicatedDraw",
    "view.rightDrawFailed": "FrameRightDrawFailed",
    "view.stereoIncomplete": "FrameStereoIncomplete",
    "view.rightDepthSynchronized": "RightDepthSynchronized",
    "view.rightStencilSynchronized": "RightStencilSynchronized",
}


LOWER_SERVICES = {
    "R29OwnerEnsureStereoResources(": "return EnsureStereoResources(device);",
    "R29OwnerTryBootstrapRightDepth(": "return TryBootstrapRightDepthFromRecentClear(device);",
    "R29OwnerDepthTestActive(": "return DepthTestActive(device);",
    "R29OwnerStencilTestActive(": "return StencilTestActive(device);",
    "R29OwnerLeftDrawMayWriteDepth(": "return LeftDrawMayWriteDepth(device);",
    "R29OwnerLeftDrawMayWriteStencil(": "return LeftDrawMayWriteStencil(device);",
    "R29OwnerNoteMainDepthContentWrite(": "R9NoteMainDepthContentWrite();",
    "R29OwnerNoteStereoDrawWithoutMonoBackup(": "R9NoteStereoDrawWithoutMonoBackup();",
    "R29OwnerUndoStereoDrawCount(": "R9UndoStereoDrawCount();",
    "R29OwnerBorrowTrackedRenderTarget(": "return TrackedRenderTarget;",
    "R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(": "InvalidateRightDepthStencilIfLeftMayWrite(device);",
    "R29OwnerNoteRestoreFailure(": "NoteRestoreFailure(site);",
}


def check(r29: str, r30: str, header: str) -> None:
    for signature, delegation in OWNER_CALLS.items():
        implementation = body(r29, signature)
        assert delegation in implementation, f"R29 delegation changed: {signature}"
        exported = signature.split("R29Owner", 1)[1].split("(", 1)[0]
        assert "R29Owner" + exported in header, f"header missing {exported}"
    snapshot = body(r29, "R29OwnerCaptureFrameSnapshot() noexcept")
    for field, provider in FRAME_DELEGATIONS.items():
        assert f"{field} = {provider};" in snapshot, (
            f"R29 frame snapshot changed: {field}"
        )
        assert field.split(".", 1)[1] in header, (
            f"R29 frame ABI declaration lost: {field}"
        )
    for method, required in {
        "R29OwnerStereoWanted() noexcept": "return StereoWanted();",
        "R29OwnerTargetIsBackBuffer() noexcept": "return TargetIsBackBuffer();",
        "R29OwnerExchangeInternalStereoPass(bool active) noexcept":
            "InternalStereoPass = active;",
    }.items():
        assert required in body(r29, method), f"R29 owner method broken: {method}"
    extent = body(r29, "R29OwnerRecommendedEyeExtent(")
    for token in (
        "eye >= 2", "SharedState->magic != OutRunVR::SharedMagic",
        "SharedState->protocolVersion != OutRunVR::SharedProtocolVersion",
        "SharedState->recommendedWidth[eye]",
        "SharedState->recommendedHeight[eye]",
        "return width != 0 && height != 0;",
    ):
        assert token in extent, f"R29 eye extent guard lost: {token}"
    identity = body(r29, "R29OwnerTryGetDirectTransportIdentity(")
    for token in (
        "out = {};", "!SharedState || !DirectInteropVerified",
        "out.hostPid = SharedState->hostPid;",
        "out.hostAdapterLuidLow = SharedState->hostAdapterLuidLow;",
        "out.hostAdapterLuidHigh = SharedState->hostAdapterLuidHigh;",
    ):
        assert token in identity, f"R29 transport identity guard lost: {token}"
    for api in ("R29OwnerRecommendedEyeExtent",
                "R29OwnerTryGetDirectTransportIdentity",
                "R29OwnerTransportIdentity"):
        assert api in header, f"R29 owner header missing: {api}"
        assert api in r30, f"R30 missing lower owner ABI use: {api}"
    assert not re.search(r"\bSharedState\b", r30), "R30 still owns lower shared IPC pointer"
    for signature, forwarding in LOWER_SERVICES.items():
        assert signature in header, f"R29 header lacks lower service: {signature}"
        assert signature in r30, f"R30 retained lower-symbol dependency: {signature}"
        assert forwarding in body(r29, signature), (
            f"R29 lower service delegation lost: {signature}"
        )
    assert "R30ScopedInternalPass" in r30
    assert "R29OwnerExchangeInternalStereoPass(previous_)" in r30
    assert "R29OwnerCaptureFrameSnapshot().backBuffer" in r30
    assert "R29OwnerCaptureFrameSnapshot().rightEyeSurface" in r30
    assert "R29OwnerCaptureFrameSnapshot().presentEpoch" in r30
    assert '#include "../core/r29_owner_api.hpp"' in r29
    assert '#include "../core/r29_owner_api.hpp"' in r30
    for pattern in (
        r"(?<!Owner)\bR29StableStereoBase\(",
        r"(?<!Owner)\bR29FragileEffectCached\(",
        r"(?<!Owner)\bR29ArmMonoSafety\(",
        r"\bR29TelemetryNoteStableTwoEyeDraw\(",
        r"\bR29StereoInstallState\b",
        r"\bR29StableTwoEyeDraws\b",
    ):
        assert not re.search(pattern, r30), f"R30 private R29 leak: {pattern}"
    for interface in (
        "R29OwnerStableStereoBase", "R29OwnerFragileEffectCached",
        "R29OwnerArmMonoSafety", "R29OwnerNoteStableTwoEyeDraw",
        "R29OwnerInstallStatus",
    ):
        assert interface + "(" in r30, f"R30 does not use {interface}"


def main() -> None:
    r29 = (SRC / "stereo_renderer_r29.cpp").read_text(encoding="utf-8")
    r30 = (SRC / "stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    header = (CORE / "r29_owner_api.hpp").read_text(encoding="utf-8")
    check(r29, r30, header)
    for signature, delegation in OWNER_CALLS.items():
        # Mutate the exported owner definition, not an earlier lower-owner
        # call with the same spelling elsewhere in the R29 translation unit.
        pos = r29.find(signature)
        assert pos >= 0
        mutated = r29[:pos] + r29[pos:].replace(
            delegation, "/* poisoned delegation */", 1
        )
        try:
            check(mutated, r30, header)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"negative mutation unexpectedly PASS: {signature}")

    for field, provider in FRAME_DELEGATIONS.items():
        old = f"{field} = {provider};"
        mutated = r29.replace(old, "/* snapshot poison */", 1)
        assert mutated != r29, f"missing snapshot mutation target: {field}"
        try:
            check(mutated, r30, header)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"negative mutation unexpectedly PASS: {field}")
    for marker, poison in (
        ("R29OwnerRecommendedEyeExtent(",
         "SharedState->magic != OutRunVR::SharedMagic"),
        ("R29OwnerTryGetDirectTransportIdentity(",
         "!SharedState || !DirectInteropVerified"),
    ):
        pos = r29.find(marker)
        assert pos >= 0
        mutated = r29[:pos] + r29[pos:].replace(
            poison, "/* removed owner guard */ false", 1)
        assert mutated != r29
        try:
            check(mutated, r30, header)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"negative mutation unexpectedly PASS: {marker}")
    for signature, delegation in LOWER_SERVICES.items():
        pos = r29.find(signature)
        assert pos >= 0
        mutated = r29[:pos] + r29[pos:].replace(
            delegation, "/* lost lower service delegation */", 1)
        assert mutated != r29
        try:
            check(mutated, r30, header)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"negative mutation unexpectedly PASS: {signature}")
    print("R29/R30 owner ABI regression PASS (33 negative mutations)")


if __name__ == "__main__":
    main()

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, markers: tuple[str, ...]) -> None:
    source = text(path)
    missing = [marker for marker in markers if marker not in source]
    if missing:
        raise SystemExit(f"{path}: missing markers: {missing}")


require("src/vr_shared.hpp", (
    "SharedProtocolVersion = 2",
    "RenderFrameProtocolVersion = 2",
    "RenderFrameRingSize = 4",
    "HostAdapterLuidValid",
    "clientAdapterLuidLow",
    "clientInteropProbeHandle",
    "hostInteropProbeAckToken",
    "hostDirectConsumedFrameId",
    "RenderFrameDirectSlotIndex",
    "SharedRenderFrameRing",
    "static_assert(sizeof(SharedPoseState) == 280)",
    "static_assert(sizeof(SharedRenderFrameState) == 256)",
    "static_assert(sizeof(SharedRenderFrameRing) == 1056)",
))

require("src/vr_stereo.cpp", (
    "QueryGameAdapterLuid",
    "IDirect3DDevice9Ex",
    "GetAdapterLUID",
    "EnsureDirectInteropProbe",
    "D3DCOLOR_ARGB(0xFF, 0x7B, 0x7B, 0x7B)",
    "DirectTransportSlots",
    "RenderFrameRingSize",
    "hostDirectConsumedFrameId",
    "ResolveDirectTransport(device, pendingFrameId)",
    "SBS/Desktop Duplication fallback",
    "PublishRenderFrame",
    "SharedRenderFrameRing",
))

require("vrhost/main_stereo.cpp", (
    "SharedWriter(req.adapterLuid)",
    "ServiceInteropProbe",
    "OpenSharedResource",
    "clientAdapterLuidLow",
    "hostInteropProbeAckToken",
    "AckDirectFrame",
    "RenderFrameDirectSlotIndex",
    "SharedRenderFrameRing",
    "recommendedImageRectWidth",
    "ReadRenderScale",
    "OUTRUN_VR_RENDER_SCALE",
    "CommitDirectStereoSource",
))

host = text("vrhost/main_stereo.cpp")
for bad in (r"\n        bool ServiceInteropProbe", r"\n        void AckDirectFrame"):
    if bad in host:
        raise SystemExit(f"vrhost/main_stereo.cpp: literal structural escape remains: {bad!r}")

stereo = text("src/vr_stereo.cpp")
for forbidden in ("Game::ModeControl()", "Game::EventControl()", "WheelFFB_ServiceSafety"):
    if forbidden in stereo:
        raise SystemExit(f"src/vr_stereo.cpp: simulation/input/FFB replay forbidden: {forbidden}")

renderer = text("src/vr_renderer_probe.cpp")
anchor = "Frame.v2 positions are OpenXR LOCAL-space metres"
if anchor not in renderer:
    raise SystemExit("src/vr_renderer_probe.cpp: Frame.v2 metre-space contract missing")
start = renderer.index(anchor)
end = renderer.find("const float w =", start)
if end < 0:
    raise SystemExit("src/vr_renderer_probe.cpp: effective-pose block not found")
if "* Settings::VRWorldScale" in renderer[start:end]:
    raise SystemExit("src/vr_renderer_probe.cpp: OpenXR effective pose must remain in metres")

print("VR reference hardening verifier: PASS")

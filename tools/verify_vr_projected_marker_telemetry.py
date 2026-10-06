#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
SEM = ROOT / "src/vr/game/render_semantics.hpp"

def fail(msg: str) -> None:
    raise SystemExit("VR projected-marker telemetry contract FAILED\n - " + msg)

def read(p: Path) -> str:
    if not p.is_file():
        fail(f"missing {p.relative_to(ROOT)}")
    return p.read_text(encoding="utf-8")

r30 = read(R30)
sem = read(SEM)

# The next HMD CORRECTNESS pass must be able to distinguish:
# 1) exact projected semantic observed,
# 2) semantic observed but payload missing,
# 3) per-eye projected delta build attempted/succeeded/failed,
# 4) shared semantic registry publication/consumption/stale cleanup.
for marker in (
    "R57ProjectedSemanticObserved",
    "R57ProjectedPayloadMissing",
    "R57ProjectedBuildAttempts",
    "R57ProjectedBuildSuccesses",
    "R57ProjectedBuildFailures",
    "R57ProjectedRankSprani",
    "R57ProjectedRankClip",
    "R57ProjectedRival",
):
    if marker not in r30:
        fail(f"missing projected-marker counter: {marker}")

for marker in (
    "SpriteNodeSemanticPublishedCount.load",
    "SpriteNodeSemanticRegistered.load",
    "SpriteNodeSemanticConsumed.load",
    "SpriteNodeSemanticStaleCleared.load",
):
    if marker not in r30:
        fail(f"telemetry does not expose semantic-registry state: {marker}")

for marker in (
    "projected[semantic={},missingPayload={},buildAttempts={},buildOk={},buildFail={},rankSprani={},rankClip={},rival={}]",
    "registry[published={},registered={},consumed={},staleCleared={}]",
):
    if marker not in r30:
        fail(f"5s telemetry format missing: {marker}")

# Rendering classification must remain RenderScope/payload-authoritative.
classify_start = r30.find("R30ScreenSpaceKind R30ClassifyScreenSpacePass(")
classify_end = r30.find("bool R30BuildScreenSpaceEyeConstants(", classify_start)
if classify_start < 0 or classify_end <= classify_start:
    fail("cannot isolate R30 classifier")
classify = r30[classify_start:classify_end]
for marker in (
    "CorroboratesProjectedWorldMarker(",
    "CurrentProjectedMarker()",
    "R30ScreenSpaceKind::ProjectedWorldMarker2D",
):
    if marker not in classify:
        fail(f"projected classification contract changed: {marker}")

for token in (
    "ProducerToken::RankMarkerSprani",
    "ProducerToken::RankMarkerClipSprite",
    "ProducerToken::RivalMarkerSprani",
):
    # Tokens may be used only under VRTelemetry diagnostics, never to grant ownership.
    pos = classify.find(token)
    if pos >= 0:
        window = classify[max(0, pos - 500):pos + 500]
        if "Settings::VRTelemetry" not in window:
            fail(f"producer token escaped diagnostic-only scope: {token}")

# Existing registry counters must stay atomic/shared.
for marker in (
    "std::atomic<std::size_t> SpriteNodeSemanticPublishedCount",
    "std::atomic<std::uint64_t> SpriteNodeSemanticRegistered",
    "std::atomic<std::uint64_t> SpriteNodeSemanticConsumed",
    "std::atomic<std::uint64_t> SpriteNodeSemanticStaleCleared",
):
    if marker not in sem:
        fail(f"shared registry counter contract changed: {marker}")

print("VR projected-marker telemetry contract PASS")

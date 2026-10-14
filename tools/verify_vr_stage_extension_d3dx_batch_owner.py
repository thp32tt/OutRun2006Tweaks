#!/usr/bin/env python3
"""Changed-area +TIME D3DX semantic-batch boundary contract and mutation guards.

This verifies exact upstream ownership and fail-closed hook wiring; it does
not claim Quest3/VDXR visual verification or simulate real D3D execution.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/hooks_uiscaling.cpp"


def check(code: str) -> list[str]:
    errors: list[str] = []
    def need(ok: bool, name: str) -> None:
        if not ok:
            errors.append(name)
    start = code.find("class VRProjectedD3DXSpriteIsolationR64 : public Hook")
    end = code.find("// VR semantic bridge for the game's canonical queued 2D renderer.", start)
    need(start >= 0 and end > start, "R64 exact sprite-hook owner missing")
    if start < 0 or end < start:
        return errors
    hook = code[start:end]
    queue = code[end:]
    source = code[:start]
    need("StageExtensionSpraniCalls[]" in source and
         "0x9898E, 0x98A36, 0x98AC6" in source and
         "StageExtensionPrintCalls[]" in source and
         "0x989AD, 0x98A10, 0x98A89" in source,
         "six original source edges are not preserved")
    need("ScopedExactProducerSemantic" in source and
         "ProducerToken::StageExtensionTime" in source and
         "TagAppendedNodes(StageExtensionBefore" in source,
         "immediate print and queued sprite producer owners missing")
    for method, number in (("BeginDest", 8), ("DrawDest", 9),
                           ("FlushDest", 10), ("EndDest", 11)):
        need(f"static HRESULT __stdcall {method}(" in hook,
             f"{method} hook callback missing")
        need(f"vtable[{number}]" in hook,
             f"{method} vtable slot missing")
    need("BatchActive = SUCCEEDED(hr)" in hook and
         "BatchActive = false" in hook and
         "ForgetBatch();" in hook,
         "Begin/End/failed-Flush state invalidation missing")
    need("PendingHomogeneous = false" in hook and
         "!PendingHomogeneous" in hook and
         "!QueueRenderActive()" in hook,
         "mixed/unknown owner fail-closed fallback missing")
    need("PendingScope != EffectiveScope()" in hook and
         "PendingProducer != CurrentRenderProducerToken()" in hook,
         "previous owner provenance is not compared")
    need("PeekSpriteNodeScope(nextNode, RenderScope::None, &nextProducer)" in hook and
         "StageOwner(nextScope, nextProducer)" in hook,
         "next node must have exact +TIME tag before promotion")
    need("StageOwner(scope, source) && PendingHomogeneous" in hook and
         "queuedStageIsolated || directStageIsolated" in hook and
         "FlushTracked(self)" in hook,
         "+TIME submission must flush only under proven ScreenHud producer")
    need("StageBoundaryReady = false" in hook and
         "StageFallbacks.fetch_add" in hook,
         "failed preboundary should never promote an unknown batch")
    need("queuedSource == ProducerToken::RankMarkerSprani" in hook and
         "queuedSource == ProducerToken::RankMarkerClipSprite" in hook and
         "queuedSource == ProducerToken::DispRankFirst" in hook and
         "queuedSource == ProducerToken::DispRankClipSprite" in hook,
         "HMD-proven R64 rank ownership must be retained")
    need("VRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);" in queue and
         "VRProjectedD3DXSpriteIsolationR64::BeforeQueueEnd();" in queue,
         "stage batch boundaries not connected to canonical queue")
    node = queue.find("VRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);")
    select = queue.find("OutRunVR::GameSemantic::SelectSpriteQueueNode(node);")
    leave = queue.find("VRProjectedD3DXSpriteIsolationR64::BeforeQueueEnd();")
    finish = queue.find("OutRunVR::GameSemantic::EndSpriteQueueRender();")
    need(0 <= node < select and 0 <= leave < finish,
         "prior producer must flush BEFORE queue ownership is replaced")
    need("QueueRenderActive() && StageBoundaryReady" in hook and
         "!QueueRenderActive() && PendingDraws == 1u" in hook and
         "if (FlushTracked(self))" in hook,
         "post-Draw +TIME flush not constrained to queue-owned proof")
    return errors


def main() -> int:
    code = SOURCE.read_text(encoding="utf-8")
    errors = check(code)
    if errors:
        print("DX9Ex +TIME D3DX FAIL: " + "; ".join(errors))
        return 1
    mutations = {
        "wrong-before-after-node-order":
            code.replace(
                "VRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);\n"
                "\t\tOutRunVR::GameSemantic::SelectSpriteQueueNode(node);",
                "OutRunVR::GameSemantic::SelectSpriteQueueNode(node);\n"
                "\t\tVRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);",
                1),
        "stale-shared-batch":
            code.replace("PendingHomogeneous = false;", "PendingHomogeneous = true;", 1),
        "missing-old-owner-proof":
            code.replace("PendingProducer != CurrentRenderProducerToken()",
                         "PendingProducer == CurrentRenderProducerToken()", 1),
        "unproven-direct-batch":
            code.replace("!QueueRenderActive() && PendingDraws == 1u",
                         "false", 1),
        "missing-end-boundary":
            code.replace("VRProjectedD3DXSpriteIsolationR64::BeforeQueueEnd();",
                         "// no end flush", 1),
        "lost-rank-exact-source":
            code.replace("queuedSource == ProducerToken::DispRankClipSprite",
                         "queuedSource == ProducerToken::None", 1),
    }
    for label, mutated in mutations.items():
        if mutated == code or not check(mutated):
            print("DX9Ex +TIME D3DX FAIL: mutation not detected:", label)
            return 1
    print("DX9Ex +TIME D3DX batch boundary and 6 negative regressions PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

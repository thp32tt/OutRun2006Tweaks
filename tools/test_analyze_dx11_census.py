#!/usr/bin/env python3
"""Regression tests for R72/R73/R74/R75 DX11 census analyzer compatibility."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "analyze_dx11_census.py"


def run_case(log_text: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        session = Path(tmp) / "session"
        session.mkdir()
        (session / "OutRun2006Tweaks.log").write_text(log_text, encoding="utf-8")
        output = Path(tmp) / "report.json"
        subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--session-dir",
                str(session),
                "--output",
                str(output),
            ],
            check=True,
        )
        return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    r73 = run_case(
        "VR DX11 R73 signature#1: primitive=4 fixedFn=1\n"
        "VR DX11 R73 census: samples=64 exact=0 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=64 "
        "texturedSamples=64 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=64,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r73["SchemaVersion"] == 2
    assert r73["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r73["NativeDrawPathActivationAllowed"] is False
    assert r73["LatestSummary"]["mutationTelemetryRequired"] == 64
    assert r73["LatestSummary"]["mutationWriteUnlocks"] == 0
    assert r73["UniqueSignaturesCaptured"] == 1

    r74 = run_case(
        "VR DX11 R74 signature#1: primitive=4 fixedFn=1\n"
        "VR DX11 R74 census: samples=64 exact=0 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=64 "
        "texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=64,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=5,readOnlyUnlocks=2,discardWriteUnlocks=3,"
        "noOverwriteWriteUnlocks=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r74["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r74["NativeDrawPathActivationAllowed"] is False
    assert r74["LatestSummary"]["mutationTelemetryRequired"] == 64
    assert r74["LatestSummary"]["mutationWriteUnlocks"] == 5
    assert r74["LatestSummary"]["mutationReadOnlyUnlocks"] == 2
    assert r74["LatestSummary"]["mutationDiscardWriteUnlocks"] == 3
    assert r74["LatestSummary"]["mutationNoOverwriteWriteUnlocks"] == 1

    r75 = run_case(
        "VR DX11 R75 signature#1: primitive=4 fixedFn=1\n"
        "VR DX11 R75 census: samples=64 exact=0 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=64 "
        "texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=64,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=7,readOnlyUnlocks=2,discardWriteUnlocks=2,"
        "noOverwriteWriteUnlocks=1] "
        "mutationPlan[exact=5,unsupported=1,managedShadow=3,mapWrite=1,"
        "mapDiscard=2,mapNoOverwrite=1,updateSubresource=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r75["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r75["NativeDrawPathActivationAllowed"] is False
    assert r75["LatestSummary"]["mutationPlanExact"] == 5
    assert r75["LatestSummary"]["mutationPlanUnsupported"] == 1
    assert r75["LatestSummary"]["mutationPlanManagedShadow"] == 3
    assert r75["LatestSummary"]["mutationPlanMapWrite"] == 1
    assert r75["LatestSummary"]["mutationPlanMapDiscard"] == 2
    assert r75["LatestSummary"]["mutationPlanMapNoOverwrite"] == 1
    assert r75["LatestSummary"]["mutationPlanUpdateSubresource"] == 1

    r72 = run_case(
        "VR DX11 R72 signature#1: primitive=4 fixedFn=1\n"
        "VR DX11 R72 census: samples=64 exact=64 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
        "texturedSamples=0 "
        "resourceExact[introspectionFailure=0,indexUnsupported=0,"
        "textureUnsupported=0,colorUnsupported=0,depthUnsupported=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r72["Status"] == "OBSERVED_SAMPLE_TRANSLATION_EXACT"
    assert r72["LatestSummary"]["behaviorUnsupported"] == 0
    assert r72["LatestSummary"]["mutationTelemetryRequired"] == 0
    assert r72["LatestSummary"]["managedShadowRequired"] == 0

    print("DX11 census analyzer regression: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

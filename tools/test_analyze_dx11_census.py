#!/usr/bin/env python3
"""Regression tests for R72/R73/R74/R75/R76/R77/R78 DX11 census analyzer compatibility."""

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

    r76 = run_case(
        "VR DX11 R76 signature#1: primitive=4 fixedFn=1\n"
        "VR DX11 R76 census: samples=64 exact=0 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=64 "
        "texturedSamples=64 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=64,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=7,readOnlyUnlocks=2,discardWriteUnlocks=2,"
        "noOverwriteWriteUnlocks=1] "
        "mutationPlan[exact=5,unsupported=1,managedShadow=3,mapWrite=1,"
        "mapDiscard=2,mapNoOverwrite=1,updateSubresource=1] "
        "textureMutation[writeUnlocks=9,readOnlyUnlocks=2,descriptorFailures=1,"
        "updateTextureSuccesses=4,updateTextureFailures=1,"
        "updateSurfaceSuccesses=3,updateSurfaceFailures=2] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r76["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r76["NativeDrawPathActivationAllowed"] is False
    assert r76["LatestSummary"]["textureMutationWriteUnlocks"] == 9
    assert r76["LatestSummary"]["textureMutationReadOnlyUnlocks"] == 2
    assert r76["LatestSummary"]["textureMutationDescriptorFailures"] == 1
    assert r76["LatestSummary"]["textureUpdateTextureSuccesses"] == 4
    assert r76["LatestSummary"]["textureUpdateTextureFailures"] == 1
    assert r76["LatestSummary"]["textureUpdateSurfaceSuccesses"] == 3
    assert r76["LatestSummary"]["textureUpdateSurfaceFailures"] == 2

    r77 = run_case(
        "VR DX11 R77 signature#1: primitive=4 fixedFn=1\n"
        "VR DX11 R77 census: samples=64 exact=0 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=64 "
        "texturedSamples=64 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=64,managedShadowRequired=64,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=7,readOnlyUnlocks=2,discardWriteUnlocks=2,"
        "noOverwriteWriteUnlocks=1] "
        "mutationPlan[exact=5,unsupported=1,managedShadow=3,mapWrite=1,"
        "mapDiscard=2,mapNoOverwrite=1,updateSubresource=1] "
        "textureMutation[writeUnlocks=9,readOnlyUnlocks=2,descriptorFailures=0,"
        "updateTextureSuccesses=4,updateTextureFailures=1,"
        "updateSurfaceSuccesses=3,updateSurfaceFailures=2] "
        "managedLifetime[shadowWrites=6,shadowReads=2,resetSuccesses=3,"
        "shadowPreserved=3,deviceGeneration=4,shadowVersion=6,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r77["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r77["NativeDrawPathActivationAllowed"] is False
    assert r77["LatestSummary"]["managedShadowWrites"] == 6
    assert r77["LatestSummary"]["managedShadowReads"] == 2
    assert r77["LatestSummary"]["managedResetSuccesses"] == 3
    assert r77["LatestSummary"]["managedResetShadowPreserved"] == 3
    assert r77["LatestSummary"]["managedDeviceGeneration"] == 4
    assert r77["LatestSummary"]["managedShadowVersion"] == 6
    assert r77["LatestSummary"]["managedMirrorReady"] == 0

    r78 = run_case(
        "VR DX11 R78 signature#1: primitive=4 fixedFn=0 fvf=0x00000000 "
        "decl=1 declHash=0x0000000000000001 declElems=3 "
        "inputLayout[exact=1,elements=2,fvfPending=0]\n"
        "VR DX11 R78 census: samples=64 exact=0 fixedFn=0 programmable=64 "
        "topologyUnsupported=0 signatures=1 declSamples=64 indexedSamples=64 "
        "texturedSamples=64 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=64,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=7,readOnlyUnlocks=2,discardWriteUnlocks=2,"
        "noOverwriteWriteUnlocks=1] "
        "mutationPlan[exact=5,unsupported=1,managedShadow=0,mapWrite=1,"
        "mapDiscard=2,mapNoOverwrite=1,updateSubresource=1] "
        "textureMutation[writeUnlocks=9,readOnlyUnlocks=2,descriptorFailures=0,"
        "updateTextureSuccesses=4,updateTextureFailures=1,"
        "updateSurfaceSuccesses=3,updateSurfaceFailures=2] "
        "managedLifetime[shadowWrites=6,shadowReads=2,resetSuccesses=3,"
        "shadowPreserved=3,deviceGeneration=4,shadowVersion=6,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "inputLayout[exact=63,unsupported=1,fvfPending=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r78["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r78["NativeDrawPathActivationAllowed"] is False
    assert r78["LatestSummary"]["inputLayoutExact"] == 63
    assert r78["LatestSummary"]["inputLayoutUnsupported"] == 1
    assert r78["LatestSummary"]["inputLayoutFvfPending"] == 1

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

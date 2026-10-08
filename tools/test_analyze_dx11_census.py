#!/usr/bin/env python3
"""Regression tests for R72-R85 compatibility plus R106/R107/R113/R114 exhaustive evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "analyze_dx11_census.py"


def run_cases(logs: dict[str, str]) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        session = Path(tmp) / "session"
        session.mkdir()
        for name, log_text in logs.items():
            (session / name).write_text(log_text, encoding="utf-8")
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


def run_case(log_text: str) -> dict:
    return run_cases({"OutRun2006Tweaks.log": log_text})


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
    assert r78["LatestSummary"]["inputLayoutFvfExact"] == 0
    assert r78["LatestSummary"]["inputLayoutFvfPending"] == 1

    r79 = run_case(
        "VR DX11 R79 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=1,elements=4,fvfExact=1,fvfPending=0]\n"
        "VR DX11 R79 census: samples=64 exact=0 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=64 "
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
        "inputLayout[exact=62,unsupported=2,fvfExact=12,fvfPending=2] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r79["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r79["NativeDrawPathActivationAllowed"] is False
    assert r79["LatestSummary"]["inputLayoutExact"] == 62
    assert r79["LatestSummary"]["inputLayoutUnsupported"] == 2
    assert r79["LatestSummary"]["inputLayoutFvfExact"] == 12
    assert r79["LatestSummary"]["inputLayoutFvfPending"] == 2

    r80 = run_case(
        "VR DX11 R80 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=1,elements=4,fvfExact=1,fvfPending=0] "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=0,vsBytes=0,"
        "vsVersion=0x00000000,vsHash=0x0000000000000000,psPresent=0,"
        "psBytes=0,psVersion=0x00000000,psHash=0x0000000000000000]\n"
        "VR DX11 R80 census: samples=64 exact=0 fixedFn=60 programmable=4 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=64 "
        "texturedSamples=64 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=7,readOnlyUnlocks=2,discardWriteUnlocks=2,"
        "noOverwriteWriteUnlocks=1] "
        "mutationPlan[exact=5,unsupported=0,managedShadow=0,mapWrite=1,"
        "mapDiscard=2,mapNoOverwrite=1,updateSubresource=1] "
        "textureMutation[writeUnlocks=9,readOnlyUnlocks=2,descriptorFailures=0,"
        "updateTextureSuccesses=4,updateTextureFailures=1,"
        "updateSurfaceSuccesses=3,updateSurfaceFailures=2] "
        "managedLifetime[shadowWrites=6,shadowReads=2,resetSuccesses=3,"
        "shadowPreserved=3,deviceGeneration=4,shadowVersion=6,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "inputLayout[exact=64,unsupported=0,fvfExact=60,fvfPending=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,"
        "translationExact=0,fixedFunctionPending=60,programmablePending=4] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r80["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r80["NativeDrawPathActivationAllowed"] is False
    assert r80["LatestSummary"]["shaderIntrospectionFailure"] == 0
    assert r80["LatestSummary"]["shaderMixedPair"] == 0
    assert r80["LatestSummary"]["shaderTranslationExact"] == 0
    assert r80["LatestSummary"]["shaderFixedFunctionPending"] == 60
    assert r80["LatestSummary"]["shaderProgrammablePending"] == 4
    assert r80["LatestSummary"]["inputLayoutUnsupported"] == 0
    assert r80["LatestSummary"]["inputLayoutFvfPending"] == 0

    r81 = run_case(
        "VR DX11 R81 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=1,elements=4,fvfExact=1,fvfPending=0] "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=0,vsBytes=0,"
        "vsVersion=0x00000000,vsHash=0x0000000000000000,psPresent=0,"
        "psBytes=0,psVersion=0x00000000,psHash=0x0000000000000000] "
        "ffpCoverage[exact=0]\n"
        "VR DX11 R81 ffp signature#1 stage#7: "
        "color[op=4,arg1=0x00000002,arg2=0x00000001] "
        "alpha[op=4,arg1=0x00000002,arg2=0x00000001] "
        "texCoord=0x00000007 texTransform=0x00000000 "
        "sampler[min=2,mag=2,mip=2,u=1,v=1]\n"
        "VR DX11 R81 census: samples=1 exact=0 fixedFn=1 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
        "texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=0,readOnlyUnlocks=0,discardWriteUnlocks=0,"
        "noOverwriteWriteUnlocks=0] "
        "mutationPlan[exact=0,unsupported=0,managedShadow=0,mapWrite=0,"
        "mapDiscard=0,mapNoOverwrite=0,updateSubresource=0] "
        "textureMutation[writeUnlocks=0,readOnlyUnlocks=0,descriptorFailures=0,"
        "updateTextureSuccesses=0,updateTextureFailures=0,"
        "updateSurfaceSuccesses=0,updateSurfaceFailures=0] "
        "managedLifetime[shadowWrites=0,shadowReads=0,resetSuccesses=0,"
        "shadowPreserved=0,deviceGeneration=1,shadowVersion=0,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "inputLayout[exact=1,unsupported=0,fvfExact=1,fvfPending=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,"
        "fixedFunctionPending=0,programmablePending=0] "
        "ffpCoverage[exact=0,queryFailure=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r81["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r81["UnsupportedTotalLatest"] == 1
    assert r81["NativeDrawPathActivationAllowed"] is False
    assert r81["LatestSummary"]["fixedFunctionCoverageExact"] == 0
    assert r81["LatestSummary"]["fixedFunctionQueryFailure"] == 1
    assert r81["Signatures"][0]["fixed_function_stages"][0]["stage"] == 7
    assert r81["Signatures"][0]["fixed_function_stages"][0]["samplerMin"] == 2
    assert r81["Signatures"][0]["fixed_function_stages"][0]["samplerAddressV"] == 1

    r82 = run_case(
        "VR DX11 R82 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=1,elements=4,fvfExact=1,fvfPending=0] "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=0,vsBytes=0,"
        "vsVersion=0x00000000,vsHash=0x0000000000000000,psPresent=0,"
        "psBytes=0,psVersion=0x00000000,psHash=0x0000000000000000] "
        "ffpCoverage[exact=1] ffpReadiness[ready=0,mask=0x00000004,"
        "activeStages=3]\n"
        "VR DX11 R173 ffp signature#1 stage#2: "
        "color[op=4,arg1=0x00000002,arg2=0x00000001] "
        "alpha[op=4,arg1=0x00000002,arg2=0x00000001] "
        "resultArg=0x00000005 texCoord=0x00000002 texTransform=0x00000000 "
        "sampler[min=2,mag=2,mip=2,u=1,v=3,border=0x80402010,srgb=1]\n"
        "VR DX11 R82 census: samples=1 exact=0 fixedFn=1 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
        "texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=0,readOnlyUnlocks=0,discardWriteUnlocks=0,"
        "noOverwriteWriteUnlocks=0] "
        "mutationPlan[exact=0,unsupported=0,managedShadow=0,mapWrite=0,"
        "mapDiscard=0,mapNoOverwrite=0,updateSubresource=0] "
        "textureMutation[writeUnlocks=0,readOnlyUnlocks=0,descriptorFailures=0,"
        "updateTextureSuccesses=0,updateTextureFailures=0,"
        "updateSurfaceSuccesses=0,updateSurfaceFailures=0] "
        "managedLifetime[shadowWrites=0,shadowReads=0,resetSuccesses=0,"
        "shadowPreserved=0,deviceGeneration=1,shadowVersion=0,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "inputLayout[exact=1,unsupported=0,fvfExact=1,fvfPending=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,"
        "fixedFunctionPending=0,programmablePending=0] "
        "ffpCoverage[exact=1,queryFailure=0] "
        "ffpReadiness[ready=0,pending=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r82["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r82["UnsupportedTotalLatest"] == 1
    assert r82["NativeDrawPathActivationAllowed"] is False
    assert r82["LatestSummary"]["fixedFunctionReadinessReady"] == 0
    assert r82["LatestSummary"]["fixedFunctionReadinessPending"] == 1
    assert r82["Signatures"][0]["fixed_function_stages"][0]["stage"] == 2
    assert r82["Signatures"][0]["fixed_function_stages"][0]["samplerAddressV"] == 3
    assert r82["Signatures"][0]["fixed_function_stages"][0]["samplerBorderColor"] == 0x80402010
    assert r82["Signatures"][0]["fixed_function_stages"][0]["samplerSrgb"] == 1
    assert r82["Signatures"][0]["fixed_function_stages"][0]["resultArg"] == 5

    r83 = run_case(
        "VR DX11 R83 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=1,elements=4,fvfExact=1,fvfPending=0] "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=0,vsBytes=0,"
        "vsVersion=0x00000000,vsHash=0x0000000000000000,psPresent=0,"
        "psBytes=0,psVersion=0x00000000,psHash=0x0000000000000000] "
        "ffpCoverage[exact=1] ffpReadiness[ready=1,mask=0x00000000,"
        "activeStages=3] texMask[present=0x87,exact=0x87]\n"
        "VR DX11 R83 texture signature#1 stage#7: observed=1 type=3 pool=1 "
        "usage=0x00000000 fmt=21 exact=1\n"
        "VR DX11 R83 ffp signature#1 stage#2: "
        "color[op=4,arg1=0x00000002,arg2=0x00000001] "
        "alpha[op=4,arg1=0x00000002,arg2=0x00000001] "
        "texCoord=0x00000002 texTransform=0x00000000 "
        "sampler[min=2,mag=2,mip=2,u=1,v=1]\n"
        "VR DX11 R83 census: samples=1 exact=0 fixedFn=1 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
        "texturedSamples=1 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=0,readOnlyUnlocks=0,discardWriteUnlocks=0,"
        "noOverwriteWriteUnlocks=0] "
        "mutationPlan[exact=0,unsupported=0,managedShadow=0,mapWrite=0,"
        "mapDiscard=0,mapNoOverwrite=0,updateSubresource=0] "
        "textureMutation[writeUnlocks=0,readOnlyUnlocks=0,descriptorFailures=0,"
        "updateTextureSuccesses=0,updateTextureFailures=0,"
        "updateSurfaceSuccesses=0,updateSurfaceFailures=0] "
        "managedLifetime[shadowWrites=0,shadowReads=0,resetSuccesses=0,"
        "shadowPreserved=0,deviceGeneration=1,shadowVersion=0,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "inputLayout[exact=1,unsupported=0,fvfExact=1,fvfPending=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,"
        "fixedFunctionPending=1,programmablePending=0] "
        "ffpCoverage[exact=1,queryFailure=0] "
        "ffpReadiness[ready=1,pending=0] "
        "textureStageResource[bound=4,exact=4,pending=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r83["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r83["NativeDrawPathActivationAllowed"] is False
    assert r83["LatestSummary"]["textureStageBound"] == 4
    assert r83["LatestSummary"]["textureStageExact"] == 4
    assert r83["LatestSummary"]["textureStagePending"] == 0
    assert r83["LatestSummary"]["fixedFunctionReadinessReady"] == 1
    assert r83["Signatures"][0]["texture_stages"][0]["stage"] == 7
    assert r83["Signatures"][0]["texture_stages"][0]["exact"] == 1
    assert r83["Signatures"][0]["texture_stages"][0]["format"] == 21

    r84 = run_case(
        "VR DX11 R84 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=1,elements=4,fvfExact=1,fvfPending=0] "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=0,vsBytes=0,"
        "vsVersion=0x00000000,vsHash=0x0000000000000000,psPresent=0,"
        "psBytes=0,psVersion=0x00000000,psHash=0x0000000000000000] "
        "ffpCoverage[exact=1] ffpReadiness[ready=1,mask=0x00000000,"
        "activeStages=2] texMask[present=0x03,exact=0x03]\n"
        "VR DX11 R84 ffp shader prototype#1: generated=1 mask=0x00000000 "
        "hash=0x0123456789ABCDEF bytes=768 activeStages=2\n"
        "VR DX11 R84 texture signature#1 stage#1: observed=1 type=3 pool=1 "
        "usage=0x00000000 fmt=21 exact=1\n"
        "VR DX11 R84 census: samples=1 exact=0 fixedFn=1 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
        "texturedSamples=1 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=0,readOnlyUnlocks=0,discardWriteUnlocks=0,"
        "noOverwriteWriteUnlocks=0] "
        "mutationPlan[exact=0,unsupported=0,managedShadow=0,mapWrite=0,"
        "mapDiscard=0,mapNoOverwrite=0,updateSubresource=0] "
        "textureMutation[writeUnlocks=0,readOnlyUnlocks=0,descriptorFailures=0,"
        "updateTextureSuccesses=0,updateTextureFailures=0,"
        "updateSurfaceSuccesses=0,updateSurfaceFailures=0] "
        "managedLifetime[shadowWrites=0,shadowReads=0,resetSuccesses=0,"
        "shadowPreserved=0,deviceGeneration=1,shadowVersion=0,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "inputLayout[exact=1,unsupported=0,fvfExact=1,fvfPending=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,"
        "fixedFunctionPending=1,programmablePending=0] "
        "ffpCoverage[exact=1,queryFailure=0] "
        "ffpReadiness[ready=1,pending=0] "
        "ffpShaderPrototype[generated=1,pending=0] "
        "textureStageResource[bound=2,exact=2,pending=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r84["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r84["NativeDrawPathActivationAllowed"] is False
    assert r84["LatestSummary"]["fixedFunctionShaderPrototypeGenerated"] == 1
    assert r84["LatestSummary"]["fixedFunctionShaderPrototypePending"] == 0
    proto = r84["Signatures"][0]["fixed_function_shader_prototype"]
    assert proto["generated"] is True
    assert proto["unsupported_mask"] == 0
    assert proto["source_hash_hex"] == "0x0123456789ABCDEF"
    assert proto["bytes"] == 768
    assert proto["active_stages"] == 2

    r85 = run_case(
        "VR DX11 R85 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=1,elements=4,fvfExact=1,fvfPending=0] "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=0,vsBytes=0,"
        "vsVersion=0x00000000,vsHash=0x0000000000000000,psPresent=0,"
        "psBytes=0,psVersion=0x00000000,psHash=0x0000000000000000] "
        "ffpCoverage[exact=1] ffpReadiness[ready=1,mask=0x00000000,"
        "activeStages=2] texMask[present=0x03,exact=0x03]\n"
        "VR DX11 R85 ffp shader prototype#1: generated=1 mask=0x00000000 "
        "hash=0x0123456789ABCDEF bytes=768 activeStages=2\n"
        "VR DX11 R85 ffp shader compile#1: attempted=1 succeeded=1 "
        "hr=0x00000000 bytecodeHash=0xA1B2C3D4E5F60718 bytecodeBytes=512 "
        "diagnosticsHash=0x0000000000000000 diagnosticsBytes=0 profile=ps_4_0\n"
        "VR DX11 R223 ffp vertex shader compile#1: attempted=1 succeeded=1 "
        "hr=0x00000000 bytecodeHash=0x1122334455667788 bytecodeBytes=640 "
        "diagnosticsHash=0x0000000000000000 diagnosticsBytes=0 profile=vs_4_0\n"
        "VR DX11 R85 texture signature#1 stage#1: observed=1 type=3 pool=1 "
        "usage=0x00000000 fmt=21 exact=1\n"
        "VR DX11 R85 census: samples=1 exact=0 fixedFn=1 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
        "texturedSamples=1 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=0,readOnlyUnlocks=0,discardWriteUnlocks=0,"
        "noOverwriteWriteUnlocks=0] "
        "mutationPlan[exact=0,unsupported=0,managedShadow=0,mapWrite=0,"
        "mapDiscard=0,mapNoOverwrite=0,updateSubresource=0] "
        "textureMutation[writeUnlocks=0,readOnlyUnlocks=0,descriptorFailures=0,"
        "updateTextureSuccesses=0,updateTextureFailures=0,"
        "updateSurfaceSuccesses=0,updateSurfaceFailures=0] "
        "managedLifetime[shadowWrites=0,shadowReads=0,resetSuccesses=0,"
        "shadowPreserved=0,deviceGeneration=1,shadowVersion=0,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "inputLayout[exact=1,unsupported=0,fvfExact=1,fvfPending=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,"
        "fixedFunctionPending=1,programmablePending=0] "
        "ffpCoverage[exact=1,queryFailure=0] "
        "ffpReadiness[ready=1,pending=0] "
        "ffpShaderPrototype[generated=1,pending=0] "
        "ffpShaderCompile[succeeded=1,failed=0,skippedCap=0] "
        "textureStageResource[bound=2,exact=2,pending=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r85["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r85["NativeDrawPathActivationAllowed"] is False
    assert r85["LatestSummary"]["fixedFunctionShaderCompileSucceeded"] == 1
    assert r85["LatestSummary"]["fixedFunctionShaderCompileFailed"] == 0
    assert r85["LatestSummary"]["fixedFunctionShaderCompileSkippedCap"] == 0
    compile_probe = r85["Signatures"][0]["fixed_function_shader_compile"]
    assert compile_probe["attempted"] is True
    assert compile_probe["succeeded"] is True
    assert compile_probe["result_hex"] == "0x00000000"
    assert compile_probe["bytecode_hash_hex"] == "0xA1B2C3D4E5F60718"
    assert compile_probe["bytecode_bytes"] == 512
    assert compile_probe["diagnostics_bytes"] == 0
    assert compile_probe["profile"] == "ps_4_0"
    vertex_compile_probe = r85["Signatures"][0].get(
        "fixed_function_vertex_shader_compile"
    )
    assert vertex_compile_probe is not None
    assert vertex_compile_probe["attempted"] is True
    assert vertex_compile_probe["succeeded"] is True
    assert vertex_compile_probe["result_hex"] == "0x00000000"
    assert vertex_compile_probe["bytecode_hash_hex"] == "0x1122334455667788"
    assert vertex_compile_probe["bytecode_bytes"] == 640
    assert vertex_compile_probe["diagnostics_bytes"] == 0
    assert vertex_compile_probe["profile"] == "vs_4_0"

    r225_multi_log = run_cases(
        {
            "session-a.log": (
                "VR DX11 R85 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4\n"
                "VR DX11 R72 decl signature#1 elem#0: stream=0 offset=0 type=2 "
                "method=0 usage=0 usageIndex=0\n"
                "VR DX11 R85 texture signature#1 stage#0: observed=1 type=3 pool=1 "
                "usage=0x00000000 fmt=21 exact=1\n"
                "VR DX11 R191 ffp texture-factor state#1: observed=1 argb=0x11223344\n"
                "VR DX11 R85 ffp shader compile#1: attempted=1 succeeded=1 "
                "hr=0x00000000 bytecodeHash=0xAAAAAAAAAAAAAAAA bytecodeBytes=512 "
                "diagnosticsHash=0x0000000000000000 diagnosticsBytes=0 profile=ps_4_0\n"
                "VR DX11 R223 ffp vertex shader compile#1: attempted=1 succeeded=1 "
                "hr=0x00000000 bytecodeHash=0x1111111111111111 bytecodeBytes=640 "
                "diagnosticsHash=0x0000000000000000 diagnosticsBytes=0 profile=vs_4_0\n"
            ),
            "session-b.log": (
                "VR DX11 R85 signature#1: primitive=5 fixedFn=1 fvf=0x000002C4\n"
                "VR DX11 R72 decl signature#1 elem#0: stream=1 offset=16 type=3 "
                "method=0 usage=3 usageIndex=1\n"
                "VR DX11 R85 texture signature#1 stage#0: observed=1 type=4 pool=0 "
                "usage=0x00000001 fmt=22 exact=0\n"
                "VR DX11 R191 ffp texture-factor state#1: observed=1 argb=0xAABBCCDD\n"
                "VR DX11 R85 ffp shader compile#1: attempted=1 succeeded=1 "
                "hr=0x00000000 bytecodeHash=0xBBBBBBBBBBBBBBBB bytecodeBytes=768 "
                "diagnosticsHash=0x0000000000000000 diagnosticsBytes=0 profile=ps_4_0\n"
                "VR DX11 R223 ffp vertex shader compile#1: attempted=1 succeeded=1 "
                "hr=0x00000000 bytecodeHash=0x2222222222222222 bytecodeBytes=896 "
                "diagnosticsHash=0x0000000000000000 diagnosticsBytes=0 profile=vs_4_0\n"
            ),
        }
    )
    assert r225_multi_log["UniqueSignaturesCaptured"] == 2
    r225_signatures = {
        signature["source_log"]: signature
        for signature in r225_multi_log["Signatures"]
    }
    assert set(r225_signatures) == {"session-a.log", "session-b.log"}
    assert r225_signatures["session-a.log"]["id"] == 1
    assert r225_signatures["session-a.log"]["declaration"][0]["stream"] == 0
    assert r225_signatures["session-a.log"]["declaration"][0]["offset"] == 0
    assert r225_signatures["session-a.log"]["texture_stages"][0]["format"] == 21
    assert (
        r225_signatures["session-a.log"]["fixed_function_texture_factor"]["argb_hex"]
        == "0x11223344"
    )
    assert (
        r225_signatures["session-a.log"]["fixed_function_shader_compile"][
            "bytecode_hash_hex"
        ]
        == "0xAAAAAAAAAAAAAAAA"
    )
    assert (
        r225_signatures["session-a.log"]["fixed_function_vertex_shader_compile"][
            "bytecode_hash_hex"
        ]
        == "0x1111111111111111"
    )
    assert r225_signatures["session-b.log"]["id"] == 1
    assert r225_signatures["session-b.log"]["declaration"][0]["stream"] == 1
    assert r225_signatures["session-b.log"]["declaration"][0]["offset"] == 16
    assert r225_signatures["session-b.log"]["texture_stages"][0]["format"] == 22
    assert (
        r225_signatures["session-b.log"]["fixed_function_texture_factor"]["argb_hex"]
        == "0xAABBCCDD"
    )
    assert (
        r225_signatures["session-b.log"]["fixed_function_shader_compile"][
            "bytecode_hash_hex"
        ]
        == "0xBBBBBBBBBBBBBBBB"
    )
    assert (
        r225_signatures["session-b.log"]["fixed_function_vertex_shader_compile"][
            "bytecode_hash_hex"
        ]
        == "0x2222222222222222"
    )

    r226_multi_log_summary = run_cases(
        {
            "session-a-unsupported.log": (
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
            ),
            "session-b-exact.log": (
                "VR DX11 R120 census: samples=4 exact=4 fixedFn=4 programmable=0 "
                "topologyUnsupported=0 signatures=4 "
                "sampling[drawsSeen=4,stride=1,scheme=2] "
                "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,"
                "detailSkipped=0] "
                "declSamples=0 indexedSamples=0 texturedSamples=0 "
                "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
                "mutationTelemetryRequired=0,managedShadowRequired=0,"
                "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
                "depthUnsupported=0] "
                "dualSourceBlend[any=0,rgbSrc=0,rgbDst=0,alphaSrc=0,alphaDst=0] "
                "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
                "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
                "depthCmp=0,cull=0]\n"
            ),
        }
    )
    assert r226_multi_log_summary["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r226_multi_log_summary["UnsupportedTotalLatest"] == 64
    assert (
        r226_multi_log_summary["ActivationEvidence"]["CensusExactness"]["Samples"]
        == 68
    )
    assert (
        r226_multi_log_summary["ActivationEvidence"]["CensusExactness"]["ExactSamples"]
        == 4
    )
    assert (
        r226_multi_log_summary["ActivationEvidence"]["CensusExactness"]["AllSampledExact"]
        is False
    )
    assert r226_multi_log_summary["SummaryCoverage"] == {
        "SourceLogs": 2,
        "LogsWithPeriodicSummary": 2,
        "AllSourceLogsHavePeriodicSummary": True,
        "LogsWithCurrentPeriodicSummary": 2,
        "CurrentSummaryMissingLogs": [],
        "AllSourceLogsHaveCurrentPeriodicSummary": True,
        "LogsWithLatestStartupSummary": 0,
        "LatestStartupMissingSummaryLogs": [],
        "AllLogsWithStartupHaveLatestSummary": True,
    }
    assert set(r226_multi_log_summary["LatestSummariesByLog"]) == {
        "session-a-unsupported.log",
        "session-b-exact.log",
    }
    assert (
        r226_multi_log_summary["LatestSummariesByLog"][
            "session-a-unsupported.log"
        ]["mutationTelemetryRequired"]
        == 64
    )
    assert (
        r226_multi_log_summary["LatestSummariesByLog"]["session-b-exact.log"][
            "samplingScheme"
        ]
        == 2
    )

    r226_partial_summary = run_cases(
        {
            "session-a-no-summary.log": (
                "VR DX11 R85 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4\n"
            ),
            "session-b-exact.log": (
                "VR DX11 R120 census: samples=4 exact=4 fixedFn=4 programmable=0 "
                "topologyUnsupported=0 signatures=4 "
                "sampling[drawsSeen=4,stride=1,scheme=2] "
                "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,"
                "detailSkipped=0] "
                "declSamples=0 indexedSamples=0 texturedSamples=0 "
                "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
                "mutationTelemetryRequired=0,managedShadowRequired=0,"
                "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
                "depthUnsupported=0] "
                "dualSourceBlend[any=0,rgbSrc=0,rgbDst=0,alphaSrc=0,alphaDst=0] "
                "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
                "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
                "depthCmp=0,cull=0]\n"
            ),
        }
    )
    assert r226_partial_summary["Status"] == "TRANSLATION_EXACTNESS_PENDING"
    assert r226_partial_summary["SummaryCoverage"] == {
        "SourceLogs": 2,
        "LogsWithPeriodicSummary": 1,
        "AllSourceLogsHavePeriodicSummary": False,
        "LogsWithCurrentPeriodicSummary": 1,
        "CurrentSummaryMissingLogs": ["session-a-no-summary.log"],
        "AllSourceLogsHaveCurrentPeriodicSummary": False,
        "LogsWithLatestStartupSummary": 0,
        "LatestStartupMissingSummaryLogs": [],
        "AllLogsWithStartupHaveLatestSummary": True,
    }

    r227_multi_log_startup_bootstrap = run_cases(
        {
            "session-a-startup.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R72 bootstrap probe: ready=1 featureLevel=0xB000 "
                "selectedLuidValid=1 selectedLuid=AAAAAAAA:11111111\n"
            ),
            "session-b-startup.log": (
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=4 bootstrapCompatible=0\n"
                "VR DX11 R72 bootstrap probe: ready=0 featureLevel=0xA100 "
                "selectedLuidValid=1 selectedLuid=BBBBBBBB:22222222\n"
            ),
        }
    )
    assert [entry["source_log"] for entry in r227_multi_log_startup_bootstrap["Startup"]] == [
        "session-a-startup.log",
        "session-b-startup.log",
    ]
    assert r227_multi_log_startup_bootstrap["Startup"][0]["width"] == 1280
    assert r227_multi_log_startup_bootstrap["Startup"][1]["width"] == 1920
    assert [entry["source_log"] for entry in r227_multi_log_startup_bootstrap["Bootstrap"]] == [
        "session-a-startup.log",
        "session-b-startup.log",
    ]
    assert r227_multi_log_startup_bootstrap["Bootstrap"][0]["ready"] is True
    assert (
        r227_multi_log_startup_bootstrap["Bootstrap"][0]["selected_luid"]
        == "AAAAAAAA:11111111"
    )
    assert r227_multi_log_startup_bootstrap["Bootstrap"][1]["ready"] is False
    assert (
        r227_multi_log_startup_bootstrap["Bootstrap"][1]["selected_luid"]
        == "BBBBBBBB:22222222"
    )

    r228_startup_bootstrap_coverage = run_cases(
        {
            "session-a-complete.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R72 bootstrap probe: ready=0 featureLevel=0xA000 "
                "selectedLuidValid=1 selectedLuid=AAAAAAAA:11111111\n"
                "VR DX11 R72 bootstrap probe: ready=1 featureLevel=0xB000 "
                "selectedLuidValid=1 selectedLuid=AAAAAAAA:22222222\n"
            ),
            "session-b-missing-bootstrap.log": (
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=4 bootstrapCompatible=1\n"
            ),
        }
    )
    assert set(r228_startup_bootstrap_coverage["LatestStartupByLog"]) == {
        "session-a-complete.log",
        "session-b-missing-bootstrap.log",
    }
    assert set(r228_startup_bootstrap_coverage["LatestBootstrapByLog"]) == {
        "session-a-complete.log",
    }
    assert (
        r228_startup_bootstrap_coverage["LatestBootstrapByLog"][
            "session-a-complete.log"
        ]["selected_luid"]
        == "AAAAAAAA:22222222"
    )
    assert r228_startup_bootstrap_coverage["StartupBootstrapCoverage"] == {
        "SourceLogs": 2,
        "LogsWithStartup": 2,
        "LogsWithBootstrap": 1,
        "LogsWithBootstrapSkip": 0,
        "LogsWithBootstrapOutcome": 1,
        "LogsWithLatestStartupBootstrapOutcome": 1,
        "LatestStartupMissingBootstrapOutcomeLogs": ["session-b-missing-bootstrap.log"],
        "LogsWithLatestBootstrapProbe": 1,
        "LogsWithLatestBootstrapSkip": 0,
        "LogsWithBootstrapOutcomeHistoryConflict": 0,
        "BootstrapOutcomeHistoryConflictLogs": [],
        "AllSourceLogsHaveStartup": True,
        "AllSourceLogsHaveBootstrap": False,
        "AllSourceLogsHaveBootstrapOutcome": False,
        "AllSourceLogsLatestStartupHasBootstrapOutcome": False,
        "AllSourceLogsLatestBootstrapOutcomeIsProbe": False,
        "AllSourceLogsHaveStartupAndBootstrap": False,
        "AllSourceLogsHaveStartupAndBootstrapOutcome": False,
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }
    assert (
        r228_startup_bootstrap_coverage["ActivationEvidence"][
            "StartupBootstrapCoverage"
        ]["AllSourceLogsHaveStartupAndBootstrap"]
        is False
    )

    r229_bootstrap_skip_outcome = run_cases(
        {
            "session-a-ready.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R72 bootstrap probe: ready=1 featureLevel=0xB000 "
                "selectedLuidValid=1 selectedLuid=AAAAAAAA:11111111\n"
            ),
            "session-b-skipped.log": (
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=4 bootstrapCompatible=0\n"
                "VR DX11 R72 bootstrap probe skipped: compatible=0 adapterLuidValid=1\n"
            ),
        }
    )
    assert r229_bootstrap_skip_outcome["BootstrapSkipped"] == [
        {
            "compatible": False,
            "adapter_luid_valid": True,
            "source_log": "session-b-skipped.log",
        }
    ]
    assert set(r229_bootstrap_skip_outcome["LatestBootstrapSkipByLog"]) == {
        "session-b-skipped.log"
    }
    assert r229_bootstrap_skip_outcome["StartupBootstrapCoverage"] == {
        "SourceLogs": 2,
        "LogsWithStartup": 2,
        "LogsWithBootstrap": 1,
        "LogsWithBootstrapSkip": 1,
        "LogsWithBootstrapOutcome": 2,
        "LogsWithLatestStartupBootstrapOutcome": 2,
        "LatestStartupMissingBootstrapOutcomeLogs": [],
        "LogsWithLatestBootstrapProbe": 1,
        "LogsWithLatestBootstrapSkip": 1,
        "LogsWithBootstrapOutcomeHistoryConflict": 0,
        "BootstrapOutcomeHistoryConflictLogs": [],
        "AllSourceLogsHaveStartup": True,
        "AllSourceLogsHaveBootstrap": False,
        "AllSourceLogsHaveBootstrapOutcome": True,
        "AllSourceLogsLatestStartupHasBootstrapOutcome": True,
        "AllSourceLogsLatestBootstrapOutcomeIsProbe": False,
        "AllSourceLogsHaveStartupAndBootstrap": False,
        "AllSourceLogsHaveStartupAndBootstrapOutcome": True,
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }
    assert (
        r229_bootstrap_skip_outcome["ActivationEvidence"][
            "StartupBootstrapCoverage"
        ]["AllSourceLogsHaveBootstrapOutcome"]
        is True
    )

    r230_latest_bootstrap_outcome_order = run_cases(
        {
            "session-a-probe-then-skip.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R72 bootstrap probe: ready=1 featureLevel=0xB000 "
                "selectedLuidValid=1 selectedLuid=AAAAAAAA:11111111\n"
                "VR DX11 R72 bootstrap probe skipped: compatible=0 adapterLuidValid=1\n"
            ),
            "session-b-skip-then-probe.log": (
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=4 bootstrapCompatible=0\n"
                "VR DX11 R72 bootstrap probe skipped: compatible=0 adapterLuidValid=1\n"
                "VR DX11 R72 bootstrap probe: ready=1 featureLevel=0xB000 "
                "selectedLuidValid=1 selectedLuid=BBBBBBBB:22222222\n"
            ),
        }
    )
    assert r230_latest_bootstrap_outcome_order["LatestBootstrapOutcomeByLog"][
        "session-a-probe-then-skip.log"
    ]["kind"] == "skip"
    assert r230_latest_bootstrap_outcome_order["LatestBootstrapOutcomeByLog"][
        "session-b-skip-then-probe.log"
    ]["kind"] == "probe"
    assert r230_latest_bootstrap_outcome_order["StartupBootstrapCoverage"] == {
        "SourceLogs": 2,
        "LogsWithStartup": 2,
        "LogsWithBootstrap": 2,
        "LogsWithBootstrapSkip": 2,
        "LogsWithBootstrapOutcome": 2,
        "LogsWithLatestStartupBootstrapOutcome": 2,
        "LatestStartupMissingBootstrapOutcomeLogs": [],
        "LogsWithLatestBootstrapProbe": 1,
        "LogsWithLatestBootstrapSkip": 1,
        "LogsWithBootstrapOutcomeHistoryConflict": 2,
        "BootstrapOutcomeHistoryConflictLogs": [
            "session-a-probe-then-skip.log",
            "session-b-skip-then-probe.log",
        ],
        "AllSourceLogsHaveStartup": True,
        "AllSourceLogsHaveBootstrap": True,
        "AllSourceLogsHaveBootstrapOutcome": True,
        "AllSourceLogsLatestStartupHasBootstrapOutcome": True,
        "AllSourceLogsLatestBootstrapOutcomeIsProbe": False,
        "AllSourceLogsHaveStartupAndBootstrap": True,
        "AllSourceLogsHaveStartupAndBootstrapOutcome": True,
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }

    r231_latest_startup_bootstrap_pairing = run_cases(
        {
            "session-a-stale-outcome.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R72 bootstrap probe: ready=1 featureLevel=0xB000 "
                "selectedLuidValid=1 selectedLuid=AAAAAAAA:11111111\n"
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=0 bootstrapCompatible=1\n"
            ),
            "session-b-current-outcome.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R72 bootstrap probe: ready=1 featureLevel=0xB000 "
                "selectedLuidValid=1 selectedLuid=BBBBBBBB:11111111\n"
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=0 bootstrapCompatible=0\n"
                "VR DX11 R72 bootstrap probe skipped: compatible=0 adapterLuidValid=1\n"
            ),
        }
    )
    assert r231_latest_startup_bootstrap_pairing["LatestBootstrapOutcomeByLog"][
        "session-a-stale-outcome.log"
    ]["kind"] == "probe"
    assert "session-a-stale-outcome.log" not in (
        r231_latest_startup_bootstrap_pairing["LatestStartupBootstrapOutcomeByLog"]
    )
    assert r231_latest_startup_bootstrap_pairing[
        "LatestStartupBootstrapOutcomeByLog"
    ]["session-b-current-outcome.log"]["kind"] == "skip"
    assert r231_latest_startup_bootstrap_pairing["StartupBootstrapCoverage"] == {
        "SourceLogs": 2,
        "LogsWithStartup": 2,
        "LogsWithBootstrap": 2,
        "LogsWithBootstrapSkip": 1,
        "LogsWithBootstrapOutcome": 2,
        "LogsWithLatestStartupBootstrapOutcome": 1,
        "LatestStartupMissingBootstrapOutcomeLogs": [
            "session-a-stale-outcome.log",
        ],
        "LogsWithLatestBootstrapProbe": 1,
        "LogsWithLatestBootstrapSkip": 1,
        "LogsWithBootstrapOutcomeHistoryConflict": 1,
        "BootstrapOutcomeHistoryConflictLogs": [
            "session-b-current-outcome.log",
        ],
        "AllSourceLogsHaveStartup": True,
        "AllSourceLogsHaveBootstrap": True,
        "AllSourceLogsHaveBootstrapOutcome": True,
        "AllSourceLogsLatestStartupHasBootstrapOutcome": False,
        "AllSourceLogsLatestBootstrapOutcomeIsProbe": False,
        "AllSourceLogsHaveStartupAndBootstrap": True,
        "AllSourceLogsHaveStartupAndBootstrapOutcome": True,
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }


    r232_latest_startup_summary_pairing = run_cases(
        {
            "session-a-stale-summary.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R73 census: samples=4 exact=4 fixedFn=4 programmable=0 "
                "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
                "texturedSamples=0 "
                "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
                "mutationTelemetryRequired=0,managedShadowRequired=0,"
                "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
                "depthUnsupported=0] "
                "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
                "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
                "depthCmp=0,cull=0]\n"
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=0 bootstrapCompatible=1\n"
            ),
            "session-b-current-summary.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R73 census: samples=4 exact=4 fixedFn=4 programmable=0 "
                "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
                "texturedSamples=0 "
                "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
                "mutationTelemetryRequired=0,managedShadowRequired=0,"
                "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
                "depthUnsupported=0] "
                "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
                "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
                "depthCmp=0,cull=0]\n"
            ),
        }
    )
    assert set(r232_latest_startup_summary_pairing["LatestSummariesByLog"]) == {
        "session-a-stale-summary.log",
        "session-b-current-summary.log",
    }
    assert set(r232_latest_startup_summary_pairing["CurrentSummariesByLog"]) == {
        "session-b-current-summary.log",
    }
    assert set(r232_latest_startup_summary_pairing["LatestStartupSummaryByLog"]) == {
        "session-b-current-summary.log",
    }
    assert r232_latest_startup_summary_pairing["SummaryCoverage"] == {
        "SourceLogs": 2,
        "LogsWithPeriodicSummary": 2,
        "AllSourceLogsHavePeriodicSummary": True,
        "LogsWithCurrentPeriodicSummary": 1,
        "CurrentSummaryMissingLogs": ["session-a-stale-summary.log"],
        "AllSourceLogsHaveCurrentPeriodicSummary": False,
        "LogsWithLatestStartupSummary": 1,
        "LatestStartupMissingSummaryLogs": ["session-a-stale-summary.log"],
        "AllLogsWithStartupHaveLatestSummary": False,
    }
    assert r232_latest_startup_summary_pairing["Status"] == "TRANSLATION_EXACTNESS_PENDING"
    assert (
        r232_latest_startup_summary_pairing["ActivationEvidence"]["CensusExactness"][
            "Samples"
        ]
        == 4
    )
    assert (
        r232_latest_startup_summary_pairing["ActivationEvidence"]["CensusExactness"][
            "AllSampledExact"
        ]
        is False
    )

    r233_accumulated_log_signature_epoch = run_case(
        "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
        "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
        "VR DX11 R85 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4\n"
        "VR DX11 R72 decl signature#1 elem#0: stream=0 offset=0 type=2 "
        "method=0 usage=0 usageIndex=0\n"
        "VR DX11 R85 ffp shader compile#1: attempted=1 succeeded=1 "
        "hr=0x00000000 bytecodeHash=0xAAAAAAAAAAAAAAAA bytecodeBytes=512 "
        "diagnosticsHash=0x0000000000000000 diagnosticsBytes=0 profile=ps_4_0\n"
        "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
        "nativeFormat=29 msaa=0 bootstrapCompatible=1\n"
        "VR DX11 R85 signature#1: primitive=5 fixedFn=1 fvf=0x000002C4\n"
        "VR DX11 R72 decl signature#1 elem#0: stream=1 offset=16 type=3 "
        "method=0 usage=3 usageIndex=1\n"
        "VR DX11 R85 ffp shader compile#1: attempted=1 succeeded=1 "
        "hr=0x00000000 bytecodeHash=0xBBBBBBBBBBBBBBBB bytecodeBytes=768 "
        "diagnosticsHash=0x0000000000000000 diagnosticsBytes=0 profile=ps_4_0\n"
    )
    assert r233_accumulated_log_signature_epoch["UniqueSignaturesCaptured"] == 2
    r233_signatures = r233_accumulated_log_signature_epoch["Signatures"]
    assert [signature["startup_epoch"] for signature in r233_signatures] == [1, 2]
    assert [signature["id"] for signature in r233_signatures] == [1, 1]
    assert r233_signatures[0]["declaration"][0]["stream"] == 0
    assert r233_signatures[0]["declaration"][0]["offset"] == 0
    assert r233_signatures[1]["declaration"][0]["stream"] == 1
    assert r233_signatures[1]["declaration"][0]["offset"] == 16
    assert (
        r233_signatures[0]["fixed_function_shader_compile"]["bytecode_hash_hex"]
        == "0xAAAAAAAAAAAAAAAA"
    )
    assert (
        r233_signatures[1]["fixed_function_shader_compile"]["bytecode_hash_hex"]
        == "0xBBBBBBBBBBBBBBBB"
    )

    r234_current_startup_signature_scope = run_case(
        "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
        "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
        "VR DX11 R85 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4\n"
        "VR DX11 R194 ffp signature#1 stage#0: "
        "color[op=23,arg1=0x00000002,arg2=0x00000001] "
        "alpha[op=2,arg1=0x00000002,arg2=0x00000001] "
        "texCoord=0x00000000 texTransform=0x00000000\n"
        "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
        "nativeFormat=29 msaa=0 bootstrapCompatible=1\n"
        "VR DX11 R85 signature#1: primitive=5 fixedFn=1 fvf=0x000002C4\n"
        "VR DX11 R194 ffp signature#1 stage#0: "
        "color[op=4,arg1=0x00000002,arg2=0x00000001] "
        "alpha[op=4,arg1=0x00000002,arg2=0x00000001] "
        "texCoord=0x00000000 texTransform=0x00000000\n"
    )
    assert r234_current_startup_signature_scope["UniqueSignaturesCaptured"] == 2
    assert r234_current_startup_signature_scope["CurrentUniqueSignaturesCaptured"] == 1
    assert [
        signature["startup_epoch"]
        for signature in r234_current_startup_signature_scope["CurrentSignatures"]
    ] == [2]
    assert r234_current_startup_signature_scope["LatestStartupEpochByLog"] == {
        "OutRun2006Tweaks.log": 2
    }
    assert (
        r234_current_startup_signature_scope["ActivationEvidence"][
            "FixedFunctionDetailedStageDemand"
        ]["HasUnsupportedObservedSemantics"]
        is False
    )
    assert (
        r234_current_startup_signature_scope[
            "HistoricalFixedFunctionDetailedStageDemand"
        ]["HasUnsupportedObservedSemantics"]
        is True
    )

    r235_current_signature_evidence_reconciliation = run_cases(
        {
            "session-a-incomplete.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R85 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4\n"
                "VR DX11 R120 census: samples=4 exact=4 fixedFn=4 programmable=0 "
                "topologyUnsupported=0 signatures=2 "
                "sampling[drawsSeen=4,stride=1,scheme=2] "
                "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
                "declSamples=0 indexedSamples=0 texturedSamples=0 "
                "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
                "mutationTelemetryRequired=0,managedShadowRequired=0,"
                "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
                "depthUnsupported=0] "
                "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
                "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
                "depthCmp=0,cull=0]\n"
            ),
            "session-b-accounted.log": (
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R85 signature#1: primitive=5 fixedFn=1 fvf=0x000002C4\n"
                "VR DX11 R120 census: samples=4 exact=4 fixedFn=4 programmable=0 "
                "topologyUnsupported=0 signatures=2 "
                "sampling[drawsSeen=4,stride=1,scheme=2] "
                "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=1,detailSkipped=1] "
                "declSamples=0 indexedSamples=0 texturedSamples=0 "
                "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
                "mutationTelemetryRequired=0,managedShadowRequired=0,"
                "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
                "depthUnsupported=0] "
                "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
                "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
                "depthCmp=0,cull=0]\n"
            ),
        }
    )
    r235_coverage = r235_current_signature_evidence_reconciliation["SignatureCoverage"]
    assert r235_coverage["CurrentSignatureEvidenceMissingLogs"] == [
        "session-a-incomplete.log"
    ]
    assert r235_coverage["CurrentSignatureEvidenceOvercountLogs"] == []
    assert r235_coverage["AllCurrentSignatureEvidenceAccounted"] is False
    assert r235_coverage["CurrentSignatureEvidenceByLog"]["session-a-incomplete.log"] == {
        "ExpectedSignatures": 2,
        "CapturedSignatures": 1,
        "DetailSkippedSignatures": 0,
        "AccountedSignatures": 1,
        "HashCapHitSamples": 0,
        "HashCapSaturated": False,
        "AccountedComplete": False,
        "CoverageComplete": False,
        "Complete": False,
    }
    assert r235_coverage["CurrentSignatureEvidenceByLog"]["session-b-accounted.log"] == {
        "ExpectedSignatures": 2,
        "CapturedSignatures": 1,
        "DetailSkippedSignatures": 1,
        "AccountedSignatures": 2,
        "HashCapHitSamples": 0,
        "HashCapSaturated": False,
        "AccountedComplete": True,
        "CoverageComplete": True,
        "Complete": True,
    }
    assert (
        r235_current_signature_evidence_reconciliation["ActivationEvidence"]
        ["SignatureEvidenceCoverage"]["AllCurrentSignatureEvidenceAccounted"]
        is False
    )
    assert r235_coverage["CurrentSignatureHashCapSaturatedLogs"] == []
    assert r235_coverage["AllCurrentSignatureEvidenceCoverageComplete"] is False

    r236_current_signature_hash_cap_coverage_boundary = run_cases(
        {
            "session-a-saturated.log": (
                "VR DX11 R71 census: observed=1 size=1280x720 sourceFormat=21 "
                "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R85 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4\n"
                "VR DX11 R120 census: samples=4 exact=4 fixedFn=4 programmable=0 "
                "topologyUnsupported=0 signatures=1 "
                "sampling[drawsSeen=4,stride=1,scheme=2] "
                "signatureCaps[hashCap=1,hashCapHitSamples=3,detailCap=64,detailSkipped=0] "
                "declSamples=0 indexedSamples=0 texturedSamples=0 "
                "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
                "mutationTelemetryRequired=0,managedShadowRequired=0,"
                "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
                "depthUnsupported=0] "
                "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
                "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
                "depthCmp=0,cull=0]\n"
            ),
            "session-b-complete.log": (
                "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=22 "
                "nativeFormat=29 msaa=0 bootstrapCompatible=1\n"
                "VR DX11 R85 signature#1: primitive=5 fixedFn=1 fvf=0x000002C4\n"
                "VR DX11 R120 census: samples=4 exact=4 fixedFn=4 programmable=0 "
                "topologyUnsupported=0 signatures=1 "
                "sampling[drawsSeen=4,stride=1,scheme=2] "
                "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
                "declSamples=0 indexedSamples=0 texturedSamples=0 "
                "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
                "mutationTelemetryRequired=0,managedShadowRequired=0,"
                "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
                "depthUnsupported=0] "
                "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
                "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
                "depthCmp=0,cull=0]\n"
            ),
        }
    )
    r236_coverage = r236_current_signature_hash_cap_coverage_boundary[
        "SignatureCoverage"
    ]
    assert r236_coverage["CurrentSignatureEvidenceMissingLogs"] == []
    assert r236_coverage["CurrentSignatureEvidenceOvercountLogs"] == []
    assert r236_coverage["AllCurrentSignatureEvidenceAccounted"] is True
    assert r236_coverage["CurrentSignatureHashCapSaturatedLogs"] == [
        "session-a-saturated.log"
    ]
    assert r236_coverage["AllCurrentSignatureEvidenceCoverageComplete"] is False
    assert r236_coverage["CurrentSignatureEvidenceByLog"]["session-a-saturated.log"][
        "AccountedComplete"
    ] is True
    assert r236_coverage["CurrentSignatureEvidenceByLog"]["session-a-saturated.log"][
        "CoverageComplete"
    ] is False
    assert r236_coverage["CurrentSignatureEvidenceByLog"]["session-b-complete.log"][
        "CoverageComplete"
    ] is True
    assert (
        r236_current_signature_hash_cap_coverage_boundary["ActivationEvidence"]
        ["SignatureEvidenceCoverage"]["AllCurrentSignatureEvidenceCoverageComplete"]
        is False
    )

    # R237: even exhaustive draw sampling must not advertise the clean
    # exhaustive-exact status when the current signature universe is incomplete.
    r237_exhaustive_signature_evidence_status_boundary = (
        r236_current_signature_hash_cap_coverage_boundary
    )
    assert (
        r237_exhaustive_signature_evidence_status_boundary["Status"]
        == "OBSERVED_EXHAUSTIVE_TRANSLATION_EXACT_SIGNATURE_EVIDENCE_INCOMPLETE"
    )

    r238_programmable_shader_pair_inventory = run_case(
        "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=21 "
        "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
        "VR DX11 R85 signature#1: primitive=4 fixedFn=0 fvf=0x00000000 "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=1,vsBytes=128,"
        "vsVersion=0xFFFE0300,vsHash=0x1111111111111111,psPresent=1,psBytes=96,"
        "psVersion=0xFFFF0300,psHash=0x2222222222222222]\n"
        "VR DX11 R85 signature#2: primitive=5 fixedFn=0 fvf=0x00000000 "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=1,vsBytes=128,"
        "vsVersion=0xFFFE0300,vsHash=0x1111111111111111,psPresent=1,psBytes=96,"
        "psVersion=0xFFFF0300,psHash=0x2222222222222222]\n"
        "VR DX11 R85 signature#3: primitive=4 fixedFn=1 fvf=0x000001C4 "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=0,vsBytes=0,"
        "vsVersion=0x00000000,vsHash=0x0000000000000000,psPresent=0,psBytes=0,"
        "psVersion=0x00000000,psHash=0x0000000000000000]\n"
        "VR DX11 R120 census: samples=3 exact=0 fixedFn=1 programmable=2 "
        "topologyUnsupported=0 signatures=3 "
        "sampling[drawsSeen=3,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,translationExact=0,"
        "fixedFunctionPending=1,programmablePending=2] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    r238_inventory = r238_programmable_shader_pair_inventory[
        "ProgrammableShaderInventory"
    ]
    assert r238_inventory["CurrentSignatureRecords"] == 3
    assert r238_inventory["CurrentSignatureRecordsWithShaderIdentity"] == 3
    assert r238_inventory["CurrentProgrammableSignatures"] == 2
    assert r238_inventory["CurrentUniqueShaderPairs"] == 1
    assert r238_inventory["EvidenceLimitedBySignatureDetailCap"] is False
    assert r238_inventory["EvidenceCoverageComplete"] is True
    assert r238_inventory["TranslationImplemented"] is False
    assert r238_inventory["ActivationProof"] is False
    r238_pair = r238_inventory["Pairs"][0]
    assert r238_pair["VertexShader"]["ByteSize"] == 128
    assert r238_pair["VertexShader"]["VersionTokenHex"] == "0xFFFE0300"
    assert r238_pair["VertexShader"]["HashHex"] == "0x1111111111111111"
    assert r238_pair["PixelShader"]["ByteSize"] == 96
    assert r238_pair["PixelShader"]["VersionTokenHex"] == "0xFFFF0300"
    assert r238_pair["PixelShader"]["HashHex"] == "0x2222222222222222"
    assert len(r238_pair["SignatureRefs"]) == 2

    r238_programmable_shader_pair_detail_cap = run_case(
        "VR DX11 R71 census: observed=1 size=1920x1080 sourceFormat=21 "
        "nativeFormat=28 msaa=0 bootstrapCompatible=1\n"
        "VR DX11 R85 signature#1: primitive=4 fixedFn=0 fvf=0x00000000 "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=1,vsBytes=128,"
        "vsVersion=0xFFFE0300,vsHash=0x1111111111111111,psPresent=1,psBytes=96,"
        "psVersion=0xFFFF0300,psHash=0x2222222222222222]\n"
        "VR DX11 R120 census: samples=2 exact=0 fixedFn=0 programmable=2 "
        "topologyUnsupported=0 signatures=2 "
        "sampling[drawsSeen=2,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=1,detailSkipped=1] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,translationExact=0,"
        "fixedFunctionPending=0,programmablePending=2] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    r238_limited = r238_programmable_shader_pair_detail_cap[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    assert r238_limited["CurrentUniqueShaderPairs"] == 1
    assert r238_limited["EvidenceLimitedBySignatureDetailCap"] is True
    assert r238_limited["EvidenceCoverageComplete"] is False

    r106 = run_case(
        "VR DX11 R85 signature#1: primitive=4 fixedFn=1\n"
        "VR DX11 R85 texture signature#1 stage#0: observed=1 type=3 pool=1 "
        "usage=0x00000000 fmt=21 exact=0 managedShadowRequired=1 "
        "managedShadowReady=1\n"
        "VR DX11 R85 census: samples=1 exact=0 fixedFn=1 programmable=0 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
        "texturedSamples=1 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=1,managedShadowRequired=1,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "mutation[writeUnlocks=0,readOnlyUnlocks=0,discardWriteUnlocks=0,"
        "noOverwriteWriteUnlocks=0] "
        "mutationPlan[exact=0,unsupported=0,managedShadow=1,mapWrite=0,"
        "mapDiscard=0,mapNoOverwrite=0,updateSubresource=0] "
        "textureMutation[writeUnlocks=1,readOnlyUnlocks=0,descriptorFailures=0,"
        "updateTextureSuccesses=0,updateTextureFailures=0,"
        "updateSurfaceSuccesses=0,updateSurfaceFailures=0] "
        "managedLifetime[shadowWrites=1,shadowReads=0,resetSuccesses=0,"
        "shadowPreserved=0,deviceGeneration=0,shadowVersion=1,"
        "mirrorGeneration=0,mirrorVersion=0,mirrorReady=0] "
        "managedTextureShadow[requiredSamples=1,readySamples=1,pendingSamples=0] "
        "inputLayout[exact=1,unsupported=0,fvfExact=1,fvfPending=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,"
        "fixedFunctionPending=1,programmablePending=0] "
        "ffpCoverage[exact=1,queryFailure=0] "
        "ffpReadiness[ready=1,pending=0] "
        "ffpShaderPrototype[generated=1,pending=0] "
        "ffpShaderCompile[succeeded=1,failed=0,skippedCap=0] "
        "textureStageResource[bound=1,exact=0,pending=1] "
        "textureStageManagedShadow[required=1,ready=1,pending=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r106["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r106["NativeDrawPathActivationAllowed"] is False
    assert r106["LatestSummary"]["managedTextureShadowRequiredSamples"] == 1
    assert r106["LatestSummary"]["managedTextureShadowReadySamples"] == 1
    assert r106["LatestSummary"]["managedTextureShadowPendingSamples"] == 0
    assert r106["LatestSummary"]["textureStageManagedShadowRequired"] == 1
    assert r106["LatestSummary"]["textureStageManagedShadowReady"] == 1
    assert r106["LatestSummary"]["textureStageManagedShadowPending"] == 0
    assert r106["ActivationEvidence"]["ManagedTextureShadow"]["ObservedReady"] is True
    assert r106["Signatures"][0]["texture_stages"][0]["managedShadowRequired"] == 1
    assert r106["Signatures"][0]["texture_stages"][0]["managedShadowReady"] == 1

    r107 = run_case(
        "VR DX11 R85 census: samples=1 exact=0 fixedFn=1 programmable=0 "
        "topologyUnsupported=0 signatures=0 declSamples=0 indexedSamples=0 "
        "texturedSamples=1 "
        "resourceExact[indexUnsupported=0,textureUnsupported=0,"
        "colorUnsupported=0,depthUnsupported=0] "
        "managedTextureShadow[requiredSamples=1,readySamples=0,pendingSamples=1] "
        "managedTextureMutationSource[updateTextureInvalidations=1,"
        "updateSurfaceInvalidations=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r107["NativeDrawPathActivationAllowed"] is False
    assert r107["LatestSummary"]["managedTextureUpdateTextureInvalidations"] == 1
    assert r107["LatestSummary"]["managedTextureUpdateSurfaceInvalidations"] == 1
    assert (
        r107["ActivationEvidence"]["ManagedTextureShadow"][
            "ExternalMutationInvalidations"
        ]
        == 2
    )
    assert r107["ActivationEvidence"]["ManagedTextureShadow"]["ObservedReady"] is False

    r113_pending = run_case(
        "VR DX11 R72 census: samples=64 exact=0 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=0 declSamples=0 indexedSamples=0 "
        "texturedSamples=0 "
        "resourceExact[introspectionFailure=0,indexUnsupported=0,"
        "textureUnsupported=0,colorUnsupported=0,depthUnsupported=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r113_pending["Status"] == "TRANSLATION_EXACTNESS_PENDING"
    assert r113_pending["UnsupportedTotalLatest"] == 0
    assert r113_pending["ActivationEvidence"]["CensusExactness"]["Samples"] == 64
    assert r113_pending["ActivationEvidence"]["CensusExactness"]["ExactSamples"] == 0
    assert r113_pending["ActivationEvidence"]["CensusExactness"]["AllSampledExact"] is False
    assert r113_pending["ActivationEvidence"]["CensusExactness"]["DiagnosticOnly"] is True
    assert r113_pending["ActivationEvidence"]["CensusExactness"]["ExhaustiveDrawCoverage"] is False
    assert r113_pending["ActivationEvidence"]["CensusExactness"]["ActivationProof"] is False
    assert r113_pending["NativeDrawPathActivationAllowed"] is False

    r114_saturated = run_case(
        "VR DX11 R114 census: samples=64 exact=64 fixedFn=64 programmable=0 "
        "topologyUnsupported=0 signatures=512 "
        "sampling[drawsSeen=4096,stride=64,scheme=1] "
        "signatureCaps[hashCap=512,hashCapHitSamples=3,detailCap=64,detailSkipped=448] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,indexUnsupported=0,"
        "textureUnsupported=0,colorUnsupported=0,depthUnsupported=0] "
        "ffpShaderCompile[succeeded=64,failed=0,skippedCap=3] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert (
        r114_saturated["Status"]
        == "OBSERVED_SAMPLED_TRANSLATION_EXACT_COVERAGE_SATURATED"
    )
    assert r114_saturated["ActivationEvidence"]["CensusExactness"]["AllSampledExact"] is True
    r114_coverage = r114_saturated["ActivationEvidence"]["SamplingCoverage"]
    assert r114_coverage["DrawsSeen"] == 4096
    assert r114_coverage["Samples"] == 64
    assert r114_coverage["Stride"] == 64
    assert r114_coverage["SchemeId"] == 1
    assert r114_coverage["Scheme"] == "HASHED_ORDINAL_V1"
    assert r114_coverage["SignatureHashCap"] == 512
    assert r114_coverage["SignatureHashCapHitSamples"] == 3
    assert r114_coverage["DetailedSignatureLogCap"] == 64
    assert r114_coverage["DetailedSignatureLogSkippedSignatures"] == 448
    assert r114_coverage["SignatureHashCapSaturated"] is True
    assert r114_coverage["DetailedSignatureLogCapSaturated"] is True
    assert r114_coverage["ShaderCompileSkippedSignatureCap"] == 3
    assert r114_coverage["ShaderCompileCoverageComplete"] is False
    assert r114_coverage["NonExhaustive"] is True
    assert r114_coverage["ActivationProof"] is False
    assert r114_saturated["NativeDrawPathActivationAllowed"] is False

    exhaustive = run_case(
        "VR DX11 R85 signature#1: primitive=4 fixedFn=1 fvf=0x000001C4\n"
        "VR DX11 R85 signature#2: primitive=4 fixedFn=1 fvf=0x000001C4\n"
        "VR DX11 R85 signature#3: primitive=4 fixedFn=1 fvf=0x000001C4\n"
        "VR DX11 R85 signature#4: primitive=4 fixedFn=1 fvf=0x000001C4\n"
        "VR DX11 R120 census: samples=4 exact=4 fixedFn=4 programmable=0 "
        "topologyUnsupported=0 signatures=4 "
        "sampling[drawsSeen=4,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "dualSourceBlend[any=0,rgbSrc=0,rgbDst=0,alphaSrc=0,alphaDst=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert (
        exhaustive["Status"]
        == "OBSERVED_EXHAUSTIVE_TRANSLATION_EXACT_DIAGNOSTIC_ONLY"
    )
    exhaustive_exactness = exhaustive["ActivationEvidence"]["CensusExactness"]
    exhaustive_coverage = exhaustive["ActivationEvidence"]["SamplingCoverage"]
    assert exhaustive_exactness["AllSampledExact"] is True
    assert exhaustive_exactness["ExhaustiveDrawCoverage"] is True
    assert exhaustive_exactness["ActivationProof"] is False
    assert exhaustive_coverage["DrawsSeen"] == 4
    assert exhaustive_coverage["Samples"] == 4
    assert exhaustive_coverage["Stride"] == 1
    assert exhaustive_coverage["SchemeId"] == 2
    assert exhaustive_coverage["Scheme"] == "EXHAUSTIVE_V1"
    assert exhaustive_coverage["NonExhaustive"] is False
    assert exhaustive_coverage["ExhaustiveDrawCoverage"] is True
    assert exhaustive_coverage["ShaderCompileSkippedSignatureCap"] == 0
    assert exhaustive_coverage["ShaderCompileCoverageComplete"] is True
    assert exhaustive_coverage["ActivationProof"] is False
    exhaustive_dual_source = exhaustive["ActivationEvidence"]["DualSourceBlend"]
    assert exhaustive_dual_source["AnySamples"] == 0
    assert exhaustive_dual_source["ExhaustiveNoUsageObserved"] is True
    assert exhaustive_dual_source["TranslationStillFailClosed"] is True
    assert exhaustive_dual_source["ActivationProof"] is False
    assert exhaustive["NativeDrawPathActivationAllowed"] is False

    src1_demand = run_case(
        "VR DX11 R120 census: samples=4 exact=2 fixedFn=4 programmable=0 "
        "topologyUnsupported=0 signatures=4 "
        "sampling[drawsSeen=4,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "dualSourceBlend[any=2,rgbSrc=1,rgbDst=0,alphaSrc=1,alphaDst=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=2,"
        "depthCmp=0,cull=0]\n"
    )
    assert src1_demand["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    src1_evidence = src1_demand["ActivationEvidence"]["DualSourceBlend"]
    assert src1_evidence["AnySamples"] == 2
    assert src1_evidence["RgbSourceSamples"] == 1
    assert src1_evidence["RgbDestSamples"] == 0
    assert src1_evidence["AlphaSourceSamples"] == 1
    assert src1_evidence["AlphaDestSamples"] == 1
    assert src1_evidence["ExhaustiveNoUsageObserved"] is False
    assert src1_evidence["TranslationStillFailClosed"] is True
    assert src1_evidence["ActivationProof"] is False
    assert src1_demand["NativeDrawPathActivationAllowed"] is False

    extended_unsupported = run_case(
        "VR DX11 R120 census: samples=4 exact=0 fixedFn=4 programmable=0 "
        "topologyUnsupported=0 signatures=4 "
        "sampling[drawsSeen=4,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "dualSourceBlend[any=0,rgbSrc=0,rgbDst=0,alphaSrc=0,alphaDst=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0,dualSource=2,shadeMode=3,clipping=4,"
        "depthBias=5,vertexBlend=6,dither=7,texCoordWrap=0,"
        "mrtColorWrite=0,specular=8]\n"
    )
    assert extended_unsupported["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert extended_unsupported["UnsupportedTotalLatest"] == 35
    assert extended_unsupported["LatestSummary"]["dualSource"] == 2
    assert extended_unsupported["LatestSummary"]["shadeMode"] == 3
    assert extended_unsupported["LatestSummary"]["clipping"] == 4
    assert extended_unsupported["LatestSummary"]["depthBias"] == 5
    assert extended_unsupported["LatestSummary"]["vertexBlend"] == 6
    assert extended_unsupported["LatestSummary"]["dither"] == 7
    assert extended_unsupported["LatestSummary"]["texCoordWrap"] == 0
    assert extended_unsupported["LatestSummary"]["mrtColorWrite"] == 0
    assert extended_unsupported["LatestSummary"]["specular"] == 8
    assert extended_unsupported["NativeDrawPathActivationAllowed"] is False

    r174_source_mrt = run_case(
        "VR DX11 R120 census: samples=4 exact=2 fixedFn=4 programmable=0 "
        "topologyUnsupported=0 signatures=4 "
        "sampling[drawsSeen=4,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0,auxRenderTargetUnsupported=2] "
        "dualSourceBlend[any=0,rgbSrc=0,rgbDst=0,alphaSrc=0,alphaDst=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r174_source_mrt["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r174_source_mrt["UnsupportedTotalLatest"] == 2
    assert r174_source_mrt["LatestSummary"]["auxRenderTargetUnsupported"] == 2
    assert r174_source_mrt["NativeDrawPathActivationAllowed"] is False

    r170_wrap = run_case(
        "VR DX11 R120 census: samples=4 exact=0 fixedFn=4 programmable=0 "
        "topologyUnsupported=0 signatures=4 "
        "sampling[drawsSeen=4,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "dualSourceBlend[any=0,rgbSrc=0,rgbDst=0,alphaSrc=0,alphaDst=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0,dualSource=0,shadeMode=0,clipping=0,"
        "depthBias=0,vertexBlend=0,dither=0,texCoordWrap=8]\n"
    )
    assert r170_wrap["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r170_wrap["UnsupportedTotalLatest"] == 8
    assert r170_wrap["LatestSummary"]["texCoordWrap"] == 8
    assert r170_wrap["LatestSummary"]["mrtColorWrite"] == 0
    assert r170_wrap["NativeDrawPathActivationAllowed"] is False

    mrt_color_write = run_case(
        "VR DX11 R120 census: samples=4 exact=0 fixedFn=4 programmable=0 "
        "topologyUnsupported=0 signatures=4 "
        "sampling[drawsSeen=4,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0,auxRenderTargetUnsupported=0] "
        "dualSourceBlend[any=0,rgbSrc=0,rgbDst=0,alphaSrc=0,alphaDst=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0,dualSource=0,shadeMode=0,clipping=0,"
        "depthBias=0,vertexBlend=0,dither=0,texCoordWrap=0,"
        "mrtColorWrite=9]\n"
    )
    assert mrt_color_write["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert mrt_color_write["UnsupportedTotalLatest"] == 9
    assert mrt_color_write["LatestSummary"]["mrtColorWrite"] == 9
    assert mrt_color_write["NativeDrawPathActivationAllowed"] is False

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
    assert r72["Status"] == "OBSERVED_SAMPLED_TRANSLATION_EXACT_DIAGNOSTIC_ONLY"
    assert r72["ActivationEvidence"]["CensusExactness"]["AllSampledExact"] is True
    assert r72["ActivationEvidence"]["CensusExactness"]["DiagnosticOnly"] is True
    assert r72["ActivationEvidence"]["CensusExactness"]["ExhaustiveDrawCoverage"] is False
    assert r72["ActivationEvidence"]["CensusExactness"]["ActivationProof"] is False
    assert r72["NativeDrawPathActivationAllowed"] is False
    assert r72["LatestSummary"]["behaviorUnsupported"] == 0
    assert r72["LatestSummary"]["mutationTelemetryRequired"] == 0
    assert r72["LatestSummary"]["managedShadowRequired"] == 0

    r194_arg0 = run_case(
        "VR DX11 R72 signature#9: primitive=4 fixedFn=1\n"
        "VR DX11 R194 ffp signature#9 stage#0: "
        "color[op=25,arg0=0x00000002,arg1=0x00000000,arg2=0x00000003] "
        "alpha[op=25,arg0=0x00000001,arg1=0x00000002,arg2=0x00000000] "
        "resultArg=0x00000001 texCoord=0x00000000 texTransform=0x00000000 "
        "sampler[min=1,mag=1,mip=0,u=1,v=1,border=0x00000000,srgb=0]\n"
    )
    assert r194_arg0["SourceLogs"] == ["OutRun2006Tweaks.log"]
    assert r194_arg0["UniqueSignaturesCaptured"] == 1
    r194_stage = r194_arg0["Signatures"][0]["fixed_function_stages"][0]
    assert r194_stage["colorOp"] == 25
    assert r194_stage["colorArg0"] == 0x00000002
    assert r194_stage["colorArg0_hex"] == "0x00000002"
    assert r194_stage["colorArg1"] == 0x00000000
    assert r194_stage["colorArg2"] == 0x00000003
    assert r194_stage["alphaArg0"] == 0x00000001
    assert r194_stage["alphaArg0_hex"] == "0x00000001"
    assert r194_stage["alphaArg1"] == 0x00000002
    assert r194_stage["alphaArg2"] == 0x00000000
    assert r194_stage["resultArg"] == 0x00000001
    assert r194_arg0["NativeDrawPathActivationAllowed"] is False

    r197_stage_constant = run_case(
        "VR DX11 R72 signature#10: primitive=4 fixedFn=1\n"
        "VR DX11 R197 ffp signature#10 stage#3: "
        "color[op=2,arg0=0x00000001,arg1=0x00000006,arg2=0x00000001] "
        "alpha[op=2,arg0=0x00000001,arg1=0x00000006,arg2=0x00000001] "
        "constant=0x80402010 resultArg=0x00000001 "
        "texCoord=0x00000003 texTransform=0x00000000 "
        "sampler[min=1,mag=1,mip=0,u=1,v=1,border=0x00000000,srgb=0]\n"
    )
    assert r197_stage_constant["SourceLogs"] == ["OutRun2006Tweaks.log"]
    assert r197_stage_constant["UniqueSignaturesCaptured"] == 1
    r197_stage = r197_stage_constant["Signatures"][0]["fixed_function_stages"][0]
    assert r197_stage["stage"] == 3
    assert r197_stage["stageConstant"] == 0x80402010
    assert r197_stage["stageConstant_hex"] == "0x80402010"
    assert r197_stage["colorArg1"] == 0x00000006
    assert r197_stage["alphaArg1"] == 0x00000006
    assert r197_stage_constant["NativeDrawPathActivationAllowed"] is False

    r191_texture_factor = run_case(
        "VR DX11 R72 signature#7: primitive=4 fixedFn=1\n"
        "VR DX11 R191 ffp texture-factor state#7: observed=1 argb=0x80402010\n"
    )
    assert r191_texture_factor["SourceLogs"] == ["OutRun2006Tweaks.log"]
    assert r191_texture_factor["UniqueSignaturesCaptured"] == 1
    assert r191_texture_factor["Signatures"][0]["id"] == 7
    assert r191_texture_factor["Signatures"][0]["fixed_function_texture_factor"] == {
        "observed": True,
        "argb": 0x80402010,
        "argb_hex": "0x80402010",
    }
    assert r191_texture_factor["NativeDrawPathActivationAllowed"] is False


    r198_unsupported_demand = run_case(
        "VR DX11 R72 signature#11: primitive=4 fixedFn=1\n"
        "VR DX11 R197 ffp signature#11 stage#0: "
        "color[op=22,arg0=0x00000001,arg1=0x00000002,arg2=0x00000001] "
        "alpha[op=18,arg0=0x00000001,arg1=0x00000002,arg2=0x00000001] "
        "constant=0xFFFFFFFF resultArg=0x00000005 "
        "texCoord=0x00000000 texTransform=0x00000000 "
        "sampler[min=1,mag=1,mip=0,u=1,v=1,border=0x00000000,srgb=0]\n"
        "VR DX11 R197 ffp signature#11 stage#0: "
        "color[op=22,arg0=0x00000001,arg1=0x00000002,arg2=0x00000001] "
        "alpha[op=18,arg0=0x00000001,arg1=0x00000002,arg2=0x00000001] "
        "constant=0xFFFFFFFF resultArg=0x00000005 "
        "texCoord=0x00000000 texTransform=0x00000000 "
        "sampler[min=1,mag=1,mip=0,u=1,v=1,border=0x00000000,srgb=0]\n"
        "VR DX11 R197 ffp signature#11 stage#1: "
        "color[op=25,arg0=0x00000004,arg1=0x00000001,arg2=0x00000002] "
        "alpha[op=2,arg0=0x00000001,arg1=0x00000005,arg2=0x00000001] "
        "constant=0xFFFFFFFF resultArg=0x00000001 "
        "texCoord=0x00000001 texTransform=0x00000000 "
        "sampler[min=1,mag=1,mip=0,u=1,v=1,border=0x00000000,srgb=0]\n"
        "VR DX11 R197 ffp signature#11 stage#2: "
        "color[op=2,arg0=0x00000001,arg1=0x00000007,arg2=0x00000001] "
        "alpha[op=2,arg0=0x00000001,arg1=0x00000001,arg2=0x00000001] "
        "constant=0xFFFFFFFF resultArg=0x00000000 "
        "texCoord=0x00000002 texTransform=0x00000000 "
        "sampler[min=1,mag=1,mip=0,u=1,v=1,border=0x00000000,srgb=0]\n"
        "VR DX11 R197 ffp signature#11 stage#2: "
        "color[op=2,arg0=0x00000001,arg1=0x00000007,arg2=0x00000001] "
        "alpha[op=2,arg0=0x00000001,arg1=0x00000001,arg2=0x00000001] "
        "constant=0xFFFFFFFF resultArg=0x00000000 "
        "texCoord=0x00000002 texTransform=0x00000000 "
        "sampler[min=1,mag=1,mip=0,u=1,v=1,border=0x00000000,srgb=0]\n"
    )
    r198_demand = r198_unsupported_demand["ActivationEvidence"][
        "FixedFunctionDetailedStageDemand"
    ]
    assert r198_demand["DetailedStages"] == 3
    assert r198_demand["DuplicateDetailedStageRecordsDropped"] == 2
    assert r198_demand["UnsupportedColorOps"] == [
        {"value": 22, "name": "BUMPENVMAP", "count": 1}
    ]
    assert r198_demand["UnsupportedAlphaOps"] == [
        {"value": 18, "name": "MODULATEALPHA_ADDCOLOR", "count": 1}
    ]
    assert r198_demand["UnsupportedArgumentSelectors"] == [
        {"value": 7, "name": "UNKNOWN", "count": 1},
    ]
    assert r198_demand["UnsupportedArgumentValues"] == [
        {
            "value": 7,
            "value_hex": "0x00000007",
            "selector": 7,
            "selector_name": "UNKNOWN",
            "count": 1,
        },
    ]
    assert r198_demand["NonCurrentResultArgs"] == [
        {"value": 0, "name": "DIFFUSE", "count": 1},
        {"value": 5, "name": "TEMP", "count": 1},
    ]
    assert r198_demand["UnsupportedResultArgs"] == [
        {"value": 0, "name": "DIFFUSE", "count": 1}
    ]
    assert r198_demand["HasUnsupportedObservedSemantics"] is True
    assert r198_demand["CoverageLimitedByDetailCap"] is False
    assert r198_demand["DiagnosticOnly"] is True
    assert r198_demand["ActivationProof"] is False
    assert r198_unsupported_demand["NativeDrawPathActivationAllowed"] is False

    print("DX11 census analyzer regression R120/SRC1/R191/R194/R197/R198/R199/R200 demand: PASS")
    r211_raster_semantics = run_case(
        "VR DX11 R120 census: samples=3 exact=1 fixedFn=3 programmable=0 "
        "topologyUnsupported=0 "
        "rasterSemantics[pointUnsupported=1,lineUnsupported=1] signatures=3 "
        "sampling[drawsSeen=3,stride=1,scheme=2] "
        "signatureCaps[hashCap=512,hashCapHitSamples=0,detailCap=64,detailSkipped=0] "
        "declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[introspectionFailure=0,behaviorUnsupported=0,"
        "mutationTelemetryRequired=0,managedShadowRequired=0,"
        "indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,"
        "depthUnsupported=0] "
        "dualSourceBlend[any=0,rgbSrc=0,rgbDst=0,alphaSrc=0,alphaDst=0] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r211_raster_semantics["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r211_raster_semantics["LatestSummary"]["pointRasterUnsupported"] == 1
    assert r211_raster_semantics["LatestSummary"]["lineRasterUnsupported"] == 1
    assert r211_raster_semantics["UnsupportedTotalLatest"] == 2
    assert r211_raster_semantics["NativeDrawPathActivationAllowed"] is False

    r278_programmable_semantic = run_case(
        "VR DX11 R276 semanticTranslationPlan signature#1: exact=1 "
        "snapshot=0x1111111111111111 targetVS=0x2222222222222222 "
        "targetPS=0x3333333333333333 revision=0x4444444444444444 "
        "contract=0x5555555555555555\n"
        "VR DX11 R279 translationObjectPrerequisite signature#1: exact=1 "
        "cacheOwnerGen=1 slotGen=1 receiptGen=1 sameDevicePair=1 "
        "cacheSnapshot=1 slotSnapshot=1 cacheKey=0x6666666666666666 "
        "planSnapshot=0x1111111111111111 snapshot=0x7777777777777777\n"
        "VR DX11 R280 objectCreationHandoff signature#1: exact=1 "
        "vertexSource=1 pixelSource=1 ownershipPrerequisite=1 "
        "createAuthorized=0 cacheKey=0x6666666666666666 "
        "planSnapshot=0x1111111111111111 "
        "ownershipSnapshot=0x7777777777777777 "
        "snapshot=0x8888888888888888\n"
        "VR DX11 R281 translatedArtifactReceipt signature#1: exact=1 "
        "targetBytecodeRequired=1 materialized=0 createAuthorized=0 "
        "cacheKey=0x6666666666666666 "
        "vertexIdentity=0x9999999999999999 pixelIdentity=0xAAAAAAAAAAAAAAA1 "
        "handoffSnapshot=0x8888888888888888 "
        "planSnapshot=0x1111111111111111 snapshot=0xABABABABABABABAB\n"
        "VR DX11 R282 targetMaterializationContract signature#1: exact=1 "
        "targetRequired=1 materialized=0 compileAuthorized=0 createAuthorized=0 "
        "cacheKey=0x6666666666666666 "
        "vertexContract=0xBCBCBCBCBCBCBCB1 pixelContract=0xCDCDCDCDCDCDCDC2 "
        "entry=0x1010101010101010 vsProfile=0x2020202020202020 "
        "psProfile=0x3030303030303030 flags=0x00008001 "
        "artifactSnapshot=0xABABABABABABABAB "
        "planSnapshot=0x1111111111111111 snapshot=0xEFEFEFEFEFEFEFEF\n"
        "VR DX11 R283 targetBytecodeMaterialization signature#1: exact=1 "
        "vertexSubset=1 pixelSubset=1 vertexCompiled=1 pixelCompiled=1 "
        "materialized=1 createAuthorized=0 cacheKey=0x6666666666666666 "
        "vertexSourceBytes=320 pixelSourceBytes=160 "
        "vertexSource=0x4141414141414141 pixelSource=0x4242424242424242 "
        "vertexBytes=512 pixelBytes=384 "
        "vertexBytecode=0x5151515151515151 pixelBytecode=0x5252525252525252 "
        "vertexArtifact=0x6161616161616161 pixelArtifact=0x6262626262626262 "
        "contractSnapshot=0xEFEFEFEFEFEFEFEF "
        "artifactSnapshot=0xABABABABABABABAB "
        "planSnapshot=0x1111111111111111 snapshot=0xDEDEDEDEDEDEDEDE\n"
        "VR DX11 R275 translatedSemanticReceipt signature#1: exact=0 "
        "objectReady=0 snapshot=0x0000000000000000\n"
        "VR DX11 R85 signature#1: primitive=4 fixedFn=0 fvf=0x00000000 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=0,elements=0,fvfExact=0,fvfPending=0] "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=1,vsBytes=16,"
        "vsVersion=0xFFFE0300,vsHash=0xAAAAAAAAAAAAAAAA,psPresent=1,"
        "psBytes=16,psVersion=0xFFFF0300,psHash=0xBBBBBBBBBBBBBBBB] "
        "ffpCoverage[exact=0]\n"
        "VR DX11 R120 census: samples=1 exact=0 fixedFn=0 programmable=1 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,depthUnsupported=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,translationExact=0,"
        "fixedFunctionPending=0,programmablePending=1] "
        "programmableSemantic[planExact=1,planPending=0,receiptExact=0,receiptPending=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,stencil=0,"
        "fog=0,lighting=0,srgb=0,fill=0,blend=0,depthCmp=0,cull=0]\n"
    )
    r278_inventory = r278_programmable_semantic["ActivationEvidence"][
        "ProgrammableShaderInventory"
    ]
    assert r278_inventory["CurrentProgrammableSignatures"] == 1
    assert r278_inventory["CurrentUniqueShaderPairs"] == 1
    assert r278_inventory["SemanticPlanExactSignatures"] == 1
    assert r278_inventory["ObjectOwnershipPrerequisiteExactSignatures"] == 1
    assert r278_inventory["ObjectCreationHandoffExactSignatures"] == 1
    assert r278_inventory["TranslatedArtifactReceiptExactSignatures"] == 1
    assert r278_inventory["TargetMaterializationContractExactSignatures"] == 1
    assert r278_inventory["TargetBytecodeMaterializationExactSignatures"] == 1
    assert r278_inventory["SemanticReceiptExactSignatures"] == 0
    assert r278_inventory["SemanticEvidenceCoverageComplete"] is True
    assert r278_inventory["TargetBytecodeMaterializationMissingSignatures"] == []
    assert r278_inventory["TargetBytecodeMaterializationInexactSignatures"] == []
    assert r278_inventory["R242ObjectOwnershipMissingSignatures"] == [
        {"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}
    ]
    r278_pair_evidence = r278_inventory["Pairs"][0]["SemanticTranslationEvidence"][0]
    assert r278_pair_evidence["Plan"]["exact"] is True
    assert (
        r278_pair_evidence["ObjectOwnershipPrerequisite"]["exact"] is True
    )
    assert (
        r278_pair_evidence["ObjectOwnershipPrerequisite"][
            "cache_owner_generation_required"
        ] is True
    )
    assert (
        r278_pair_evidence["ObjectOwnershipPrerequisite"][
            "translation_slot_generation_required"
        ] is True
    )
    assert (
        r278_pair_evidence["ObjectOwnershipPrerequisite"][
            "translation_object_receipt_generation_required"
        ] is True
    )
    assert (
        r278_pair_evidence["ObjectOwnershipPrerequisite"][
            "same_device_object_pair_required"
        ] is True
    )
    assert r278_pair_evidence["ObjectCreationHandoff"]["exact"] is True
    assert (
        r278_pair_evidence["ObjectCreationHandoff"]["vertex_source_exact"]
        is True
    )
    assert (
        r278_pair_evidence["ObjectCreationHandoff"]["pixel_source_exact"]
        is True
    )
    assert (
        r278_pair_evidence["ObjectCreationHandoff"][
            "ownership_prerequisite_matches"
        ] is True
    )
    assert (
        r278_pair_evidence["ObjectCreationHandoff"]["creation_authorized"]
        is False
    )
    assert r278_pair_evidence["TranslatedArtifactReceipt"]["exact"] is True
    assert (
        r278_pair_evidence["TranslatedArtifactReceipt"]["target_bytecode_required"]
        is True
    )
    assert r278_pair_evidence["TranslatedArtifactReceipt"]["materialized"] is False
    assert (
        r278_pair_evidence["TranslatedArtifactReceipt"]["creation_authorized"]
        is False
    )
    assert (
        r278_pair_evidence["TranslatedArtifactReceipt"]["vertex_identity"]
        == 0x9999999999999999
    )
    assert (
        r278_pair_evidence["TranslatedArtifactReceipt"]["pixel_identity"]
        == 0xAAAAAAAAAAAAAAA1
    )
    assert r278_pair_evidence["TargetMaterializationContract"]["exact"] is True
    assert (
        r278_pair_evidence["TargetMaterializationContract"]["target_required"]
        is True
    )
    assert (
        r278_pair_evidence["TargetMaterializationContract"]["materialized"]
        is False
    )
    assert (
        r278_pair_evidence["TargetMaterializationContract"]["compile_authorized"]
        is False
    )
    assert (
        r278_pair_evidence["TargetMaterializationContract"]["creation_authorized"]
        is False
    )
    assert (
        r278_pair_evidence["TargetMaterializationContract"]["vertex_contract"]
        == 0xBCBCBCBCBCBCBCB1
    )
    assert (
        r278_pair_evidence["TargetMaterializationContract"]["pixel_contract"]
        == 0xCDCDCDCDCDCDCDC2
    )
    assert r278_pair_evidence["TargetBytecodeMaterialization"]["exact"] is True
    assert (
        r278_pair_evidence["TargetBytecodeMaterialization"]["vertex_subset"]
        is True
    )
    assert (
        r278_pair_evidence["TargetBytecodeMaterialization"]["pixel_subset"]
        is True
    )
    assert (
        r278_pair_evidence["TargetBytecodeMaterialization"]["vertex_compiled"]
        is True
    )
    assert (
        r278_pair_evidence["TargetBytecodeMaterialization"]["pixel_compiled"]
        is True
    )
    assert (
        r278_pair_evidence["TargetBytecodeMaterialization"]["materialized"]
        is True
    )
    assert (
        r278_pair_evidence["TargetBytecodeMaterialization"][
            "creation_authorized"
        ]
        is False
    )
    assert (
        r278_pair_evidence["TargetBytecodeMaterialization"][
            "vertex_bytecode_hash"
        ]
        == 0x5151515151515151
    )
    assert (
        r278_pair_evidence["TargetBytecodeMaterialization"][
            "pixel_bytecode_hash"
        ]
        == 0x5252525252525252
    )
    assert (
        r278_pair_evidence["Plan"]["target_vertex_semantic_hash"]
        == 0x2222222222222222
    )
    assert (
        r278_pair_evidence["Plan"]["target_pixel_semantic_hash"]
        == 0x3333333333333333
    )
    assert r278_pair_evidence["Receipt"]["exact"] is False
    assert r278_pair_evidence["Receipt"]["object_ready"] is False
    assert r278_pair_evidence["MissingPrerequisite"] == "R242_TRANSLATED_OBJECT_OWNERSHIP"
    assert r278_pair_evidence["ActivationProof"] is False
    assert r278_programmable_semantic["NativeDrawPathActivationAllowed"] is False

    r306_signature_tail = (
        "VR DX11 R85 signature#1: primitive=4 fixedFn=0 fvf=0x00000000 "
        "decl=0 declHash=0x0000000000000000 declElems=0 "
        "inputLayout[exact=0,elements=0,fvfExact=0,fvfPending=0] "
        "shader[introspection=1,mixed=0,exact=0,vsPresent=1,vsBytes=16,"
        "vsVersion=0xFFFE0300,vsHash=0xAAAAAAAAAAAAAAAA,psPresent=1,"
        "psBytes=16,psVersion=0xFFFF0300,psHash=0xBBBBBBBBBBBBBBBB] "
        "ffpCoverage[exact=0]\n"
        "VR DX11 R120 census: samples=1 exact=0 fixedFn=0 programmable=1 "
        "topologyUnsupported=0 signatures=1 declSamples=0 indexedSamples=0 "
        "texturedSamples=0 "
        "resourceExact[indexUnsupported=0,textureUnsupported=0,"
        "colorUnsupported=0,depthUnsupported=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,translationExact=0,"
        "fixedFunctionPending=0,programmablePending=1] "
        "programmableSemantic[planExact=0,planPending=1,receiptExact=0,"
        "receiptPending=1] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,stencil=0,"
        "fog=0,lighting=0,srgb=0,fill=0,blend=0,depthCmp=0,cull=0]\n"
    )
    r306_production_prerequisite = run_case(
        "VR DX11 R293 productionPrerequisiteCensus signature#1: "
        "sourceReceipt=0 resourceReceipt=0 r292Exact=0 staticSatisfied=0 "
        "boundaryPreserved=1 missingReceiptMask=0x00000003 "
        "snapshot=0x0000000000000000\n"
        + r306_signature_tail
    )
    r306_inventory = r306_production_prerequisite["ActivationEvidence"][
        "ProgrammableShaderInventory"
    ]
    assert r306_inventory["ProductionActivationPrerequisiteEvidenceSignatures"] == 1
    assert r306_inventory["ProductionActivationPrerequisiteExactSignatures"] == 0
    assert r306_inventory["ProductionActivationPrerequisiteFailClosedSignatures"] == 1
    assert (
        r306_inventory[
            "ProductionActivationPrerequisiteCorrelationInexactSignatures"
        ]
        == []
    )
    assert r306_inventory["ProductionActivationEvidenceCoverageComplete"] is True
    r306_evidence = r306_inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
        "ProductionActivationPrerequisite"
    ]
    assert r306_evidence["source_receipt_present"] is False
    assert r306_evidence["resource_receipt_present"] is False
    assert r306_evidence["missing_receipt_mask"] == 0x3
    assert r306_evidence["expected_missing_receipt_mask"] == 0x3
    assert r306_evidence["receipt_mask_matches"] is True
    assert r306_evidence["summary_correlation_exact"] is True
    assert r306_evidence["fail_closed"] is True
    assert r306_evidence["activation_proof"] is False
    assert r306_production_prerequisite["NativeDrawPathActivationAllowed"] is False

    r306_inconsistent_prerequisite = run_case(
        "VR DX11 R293 productionPrerequisiteCensus signature#1: "
        "sourceReceipt=0 resourceReceipt=0 r292Exact=0 staticSatisfied=0 "
        "boundaryPreserved=1 missingReceiptMask=0x00000000 "
        "snapshot=0x0000000000000000\n"
        + r306_signature_tail
    )
    r306_inconsistent_inventory = r306_inconsistent_prerequisite[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    assert r306_inconsistent_inventory[
        "ProductionActivationPrerequisiteCorrelationInexactSignatures"
    ] == [{"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}]
    assert (
        r306_inconsistent_inventory[
            "ProductionActivationEvidenceCoverageComplete"
        ]
        is False
    )
    assert (
        r306_inconsistent_inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
            "ProductionActivationPrerequisite"
        ]["summary_correlation_exact"]
        is False
    )
    assert r306_inconsistent_prerequisite["NativeDrawPathActivationAllowed"] is False

    r309_supporting_production_evidence = (
        "VR DX11 R283 targetBytecodeMaterialization signature#1: "
        "exact=1 vertexSubset=1 pixelSubset=1 vertexCompiled=1 "
        "pixelCompiled=1 materialized=1 createAuthorized=0 "
        "cacheKey=0x0102030405060708 "
        "vertexSourceBytes=16 pixelSourceBytes=16 "
        "vertexSource=0x1111111111111111 pixelSource=0x2222222222222222 "
        "vertexBytes=16 pixelBytes=16 "
        "vertexBytecode=0x3333333333333333 "
        "pixelBytecode=0x4444444444444444 "
        "vertexArtifact=0x5555555555555555 "
        "pixelArtifact=0x6666666666666666 "
        "contractSnapshot=0x7777777777777777 "
        "artifactSnapshot=0x8888888888888888 "
        "planSnapshot=0x9999999999999999 "
        "snapshot=0xAAAAAAAAAAAAAAAA\n"
        "VR DX11 R275 translatedSemanticReceipt signature#1: "
        "exact=1 objectReady=1 snapshot=0xBBBBBBBBBBBBBBBB\n"
    )
    r309_production_observation = run_case(
        r309_supporting_production_evidence
        + "VR DX11 R287 productionObservation signature#1: "
        "exact=1 ownerGeneration=7 materializationReused=0 objectReady=1 "
        "boundaryPreserved=1 handoffSnapshot=0xCCCCCCCCCCCCCCCC "
        "snapshot=0xDDDDDDDDDDDDDDDD\n"
        + r306_signature_tail
    )
    r309_inventory = r309_production_observation["ActivationEvidence"][
        "ProgrammableShaderInventory"
    ]
    assert r309_inventory["ProductionObservationEvidenceSignatures"] == 1
    assert r309_inventory["ProductionObservationExactSignatures"] == 1
    assert r309_inventory["ProductionObservationFailClosedSignatures"] == 1
    assert r309_inventory[
        "ProductionObservationCorrelationInexactSignatures"
    ] == []
    assert r309_inventory[
        "ProductionObservationEvidenceCoverageComplete"
    ] is True
    r309_evidence = r309_inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
        "ProductionObservation"
    ]
    assert r309_evidence["exact"] is True
    assert r309_evidence["owner_generation"] == 7
    assert r309_evidence["object_ready"] is True
    assert r309_evidence["boundary_preserved"] is True
    assert r309_evidence["snapshot_state_correlated"] is True
    assert r309_evidence["exact_state_correlated"] is True
    assert r309_evidence["target_materialization_correlated"] is True
    assert r309_evidence["translated_semantic_receipt_correlated"] is True
    assert r309_evidence["summary_correlation_exact"] is True
    assert r309_evidence["fail_closed"] is True
    assert r309_evidence["activation_proof"] is False
    assert r309_production_observation[
        "NativeDrawPathActivationAllowed"
    ] is False

    r309_inconsistent_production_observation = run_case(
        r309_supporting_production_evidence
        + "VR DX11 R287 productionObservation signature#1: "
        "exact=1 ownerGeneration=0 materializationReused=0 objectReady=0 "
        "boundaryPreserved=1 handoffSnapshot=0x0000000000000000 "
        "snapshot=0x0000000000000000\n"
        + r306_signature_tail
    )
    r309_inconsistent_inventory = r309_inconsistent_production_observation[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    assert r309_inconsistent_inventory[
        "ProductionObservationCorrelationInexactSignatures"
    ] == [{"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}]
    assert (
        r309_inconsistent_inventory[
            "ProductionObservationEvidenceCoverageComplete"
        ]
        is False
    )
    r309_inconsistent_evidence = r309_inconsistent_inventory["Pairs"][0][
        "SemanticTranslationEvidence"
    ][0]["ProductionObservation"]
    assert r309_inconsistent_evidence["snapshot_state_correlated"] is False
    assert r309_inconsistent_evidence["exact_state_correlated"] is False
    assert r309_inconsistent_evidence["summary_correlation_exact"] is False
    assert r309_inconsistent_evidence["fail_closed"] is False
    assert r309_inconsistent_evidence["activation_proof"] is False
    assert r309_inconsistent_production_observation[
        "NativeDrawPathActivationAllowed"
    ] is False


    r310_source_mapping_support = (
        "VR DX11 R271 sourceSemanticPair: exact=1 "
        "cacheKey=0x0102030405060708 pairHash=0x1111111111111111 "
        "vsRegisterHash=0x2222222222222222 "
        "psRegisterHash=0x3333333333333333 "
        "linkHash=0x4444444444444444 "
        "receiptRevision=0x5555555555555555 "
        "contract=0x6666666666666666\n"
        "VR DX11 R276 semanticTranslationPlan signature#1: "
        "exact=1 snapshot=0x7777777777777777 "
        "targetVS=0x8888888888888888 targetPS=0x9999999999999999 "
        "revision=0xAAAAAAAAAAAAAAAA contract=0xBBBBBBBBBBBBBBBB\n"
    )
    r310_source_semantic_pair = run_case(
        r310_source_mapping_support
        + "VR DX11 R279 translationObjectPrerequisite signature#1: "
        "exact=1 cacheOwnerGen=1 slotGen=1 receiptGen=1 sameDevicePair=1 "
        "cacheSnapshot=1 slotSnapshot=1 cacheKey=0x0102030405060708 "
        "planSnapshot=0x7777777777777777 "
        "snapshot=0xCCCCCCCCCCCCCCCC\n"
        + r306_signature_tail
    )
    r310_inventory = r310_source_semantic_pair["ActivationEvidence"][
        "ProgrammableShaderInventory"
    ]
    assert r310_inventory["SourceSemanticPairEvidenceSignatures"] == 1
    assert r310_inventory["SourceSemanticPairExactSignatures"] == 1
    assert r310_inventory["SourceSemanticPairFailClosedSignatures"] == 1
    assert r310_inventory["SourceSemanticPairCorrelationInexactSignatures"] == []
    assert r310_inventory["SourceSemanticPairEvidenceCoverageComplete"] is True
    r310_evidence = r310_inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
        "SourceSemanticPair"
    ]
    assert r310_evidence["exact"] is True
    assert r310_evidence["cache_key"] == 0x0102030405060708
    assert r310_evidence["pair_hash"] == 0x1111111111111111
    assert r310_evidence["exact_state_correlated"] is True
    assert r310_evidence["semantic_plan_correlated"] is True
    assert r310_evidence["object_prerequisite_correlated"] is True
    assert r310_evidence["summary_correlation_exact"] is True
    assert r310_evidence["fail_closed"] is True
    assert r310_evidence["activation_proof"] is False
    assert r310_source_semantic_pair["NativeDrawPathActivationAllowed"] is False

    r310_inconsistent_source_semantic_pair = run_case(
        r310_source_mapping_support
        + "VR DX11 R279 translationObjectPrerequisite signature#1: "
        "exact=1 cacheOwnerGen=1 slotGen=1 receiptGen=1 sameDevicePair=1 "
        "cacheSnapshot=1 slotSnapshot=1 cacheKey=0xDEADBEEFDEADBEEF "
        "planSnapshot=0x7777777777777777 "
        "snapshot=0xCCCCCCCCCCCCCCCC\n"
        + r306_signature_tail
    )
    r310_inconsistent_inventory = r310_inconsistent_source_semantic_pair[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    assert r310_inconsistent_inventory[
        "SourceSemanticPairCorrelationInexactSignatures"
    ] == [{"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}]
    assert (
        r310_inconsistent_inventory["SourceSemanticPairEvidenceCoverageComplete"]
        is False
    )
    r310_inconsistent_evidence = r310_inconsistent_inventory["Pairs"][0][
        "SemanticTranslationEvidence"
    ][0]["SourceSemanticPair"]
    assert r310_inconsistent_evidence["object_prerequisite_correlated"] is False
    assert r310_inconsistent_evidence["summary_correlation_exact"] is False
    assert r310_inconsistent_evidence["fail_closed"] is False
    assert r310_inconsistent_evidence["activation_proof"] is False
    assert r310_inconsistent_source_semantic_pair[
        "NativeDrawPathActivationAllowed"
    ] is False


    r311_register_mapping_support = (
        "VR DX11 R271 sourceSemanticPair: exact=1 "
        "cacheKey=0x0102030405060708 pairHash=0x1111111111111111 "
        "vsRegisterHash=0x2222222222222222 "
        "psRegisterHash=0x3333333333333333 "
        "linkHash=0x4444444444444444 "
        "receiptRevision=0x5555555555555555 "
        "contract=0x6666666666666666\n"
        "VR DX11 R272 registerMappingPlan: exact=1 constants=8 samplers=2 "
        "constantHash=0x1212121212121212 "
        "samplerHash=0x3434343434343434 "
        "planRevision=0x5656565656565656 "
        "contract=0x7878787878787878\n"
        "VR DX11 R276 semanticTranslationPlan signature#1: "
        "exact=1 snapshot=0x7777777777777777 "
        "targetVS=0x8888888888888888 targetPS=0x9999999999999999 "
        "revision=0xAAAAAAAAAAAAAAAA contract=0xBBBBBBBBBBBBBBBB\n"
    )
    r311_register_mapping_plan = run_case(
        r311_register_mapping_support
        + r306_signature_tail
    )
    r311_inventory = r311_register_mapping_plan["ActivationEvidence"][
        "ProgrammableShaderInventory"
    ]
    assert r311_inventory["RegisterMappingPlanEvidenceSignatures"] == 1
    assert r311_inventory["RegisterMappingPlanExactSignatures"] == 1
    assert r311_inventory["RegisterMappingPlanFailClosedSignatures"] == 1
    assert r311_inventory[
        "RegisterMappingPlanCorrelationInexactSignatures"
    ] == []
    assert r311_inventory[
        "RegisterMappingPlanEvidenceCoverageComplete"
    ] is True
    r311_evidence = r311_inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
        "RegisterMappingPlan"
    ]
    assert r311_evidence["exact"] is True
    assert r311_evidence["constant_mapping_count"] == 8
    assert r311_evidence["sampler_mapping_count"] == 2
    assert r311_evidence["mapping_identity_present"] is True
    assert r311_evidence["exact_state_correlated"] is True
    assert r311_evidence["source_semantic_pair_correlated"] is True
    assert r311_evidence["semantic_plan_correlated"] is True
    assert r311_evidence["summary_correlation_exact"] is True
    assert r311_evidence["fail_closed"] is True
    assert r311_evidence["activation_proof"] is False
    assert r311_register_mapping_plan["NativeDrawPathActivationAllowed"] is False

    r311_inconsistent_register_mapping = run_case(
        "VR DX11 R271 sourceSemanticPair: exact=1 "
        "cacheKey=0x0102030405060708 pairHash=0x1111111111111111 "
        "vsRegisterHash=0x2222222222222222 "
        "psRegisterHash=0x3333333333333333 "
        "linkHash=0x4444444444444444 "
        "receiptRevision=0x5555555555555555 "
        "contract=0x6666666666666666\n"
        "VR DX11 R272 registerMappingPlan: exact=1 constants=8 samplers=2 "
        "constantHash=0x1212121212121212 "
        "samplerHash=0x3434343434343434 "
        "planRevision=0x0000000000000000 "
        "contract=0x7878787878787878\n"
        "VR DX11 R276 semanticTranslationPlan signature#1: "
        "exact=1 snapshot=0x7777777777777777 "
        "targetVS=0x8888888888888888 targetPS=0x9999999999999999 "
        "revision=0xAAAAAAAAAAAAAAAA contract=0xBBBBBBBBBBBBBBBB\n"
        + r306_signature_tail
    )
    r311_inconsistent_inventory = r311_inconsistent_register_mapping[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    assert r311_inconsistent_inventory[
        "RegisterMappingPlanCorrelationInexactSignatures"
    ] == [{"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}]
    assert (
        r311_inconsistent_inventory[
            "RegisterMappingPlanEvidenceCoverageComplete"
        ]
        is False
    )
    r311_inconsistent_evidence = r311_inconsistent_inventory["Pairs"][0][
        "SemanticTranslationEvidence"
    ][0]["RegisterMappingPlan"]
    assert r311_inconsistent_evidence["mapping_identity_present"] is False
    assert r311_inconsistent_evidence["exact_state_correlated"] is False
    assert r311_inconsistent_evidence["summary_correlation_exact"] is False
    assert r311_inconsistent_evidence["fail_closed"] is False
    assert r311_inconsistent_evidence["activation_proof"] is False
    assert r311_inconsistent_register_mapping[
        "NativeDrawPathActivationAllowed"
    ] is False

    # R312: an exact R272 must have one adjacent R271 producer in the same
    # startup epoch. Duplicate or stale upstream mapping evidence is unsafe.
    r312_parts = r311_register_mapping_support.split(
        "VR DX11 R272 registerMappingPlan:", 1
    )
    r312_source = r312_parts[0]
    r312_rest = "VR DX11 R272 registerMappingPlan:" + r312_parts[1]
    r312_map_parts = r312_rest.split(
        "VR DX11 R276 semanticTranslationPlan signature#1:", 1
    )
    r312_mapping = r312_map_parts[0]
    r312_plan = (
        "VR DX11 R276 semanticTranslationPlan signature#1:"
        + r312_map_parts[1]
    )
    r312_ambiguous_register_mapping = run_case(
        r312_source + r312_mapping + r312_mapping
        + r312_plan + r306_signature_tail
    )
    r312_ambiguous_inventory = r312_ambiguous_register_mapping[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    r312_ambiguous_evidence = r312_ambiguous_inventory["Pairs"][0][
        "SemanticTranslationEvidence"
    ][0]["RegisterMappingPlan"]
    assert r312_ambiguous_evidence["producer_order_valid"] is False
    assert r312_ambiguous_evidence["summary_correlation_exact"] is False
    assert r312_ambiguous_evidence["fail_closed"] is False
    assert r312_ambiguous_inventory[
        "RegisterMappingPlanEvidenceCoverageComplete"
    ] is False
    assert r312_ambiguous_register_mapping[
        "NativeDrawPathActivationAllowed"
    ] is False

    r312_stale_register_mapping = run_case(
        r312_source + r312_mapping + r312_source
        + r312_plan + r306_signature_tail
    )
    r312_stale_inventory = r312_stale_register_mapping[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    assert r312_stale_inventory[
        "RegisterMappingPlanEvidenceMissingSignatures"
    ] == [{"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}]
    assert r312_stale_inventory[
        "RegisterMappingPlanEvidenceCoverageComplete"
    ] is False
    assert r312_stale_register_mapping["NativeDrawPathActivationAllowed"] is False

    # R313: consume the existing R273 diagnostic in producer order; none
    # of these analyzer receipts promotes NativeDrawPath or a Draw* call.
    r313_handoff_line = (
        "VR DX11 R273 sourceMappingHandoff: "
        "exact=1 snapshot=0x6AFFAF0E35D2F69B\n"
    )
    r313_support = r311_register_mapping_support.replace(
        "VR DX11 R276 semanticTranslationPlan signature#1:",
        r313_handoff_line
        + "VR DX11 R276 semanticTranslationPlan signature#1:",
    )
    r313_good = run_case(r313_support + r306_signature_tail)
    r313_inventory = r313_good["ActivationEvidence"]["ProgrammableShaderInventory"]
    assert r313_inventory["SourceMappingHandoffEvidenceSignatures"] == 1
    assert r313_inventory["SourceMappingHandoffExactSignatures"] == 1
    assert r313_inventory["SourceMappingHandoffFailClosedSignatures"] == 1
    assert r313_inventory["SourceMappingHandoffEvidenceCoverageComplete"] is True
    r313_evidence = r313_inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
        "SourceMappingHandoff"
    ]
    assert r313_evidence["producer_order_valid"] is True
    assert r313_evidence["snapshot"] == 0x6AFFAF0E35D2F69B
    assert r313_evidence["expected_snapshot"] == 0x6AFFAF0E35D2F69B
    assert r313_evidence["snapshot_matches_producer"] is True
    assert r313_evidence["summary_correlation_exact"] is True
    assert r313_evidence["identity_link_strength"] == "EXACT_RECONSTRUCTED_R273_SNAPSHOT"
    assert r313_evidence["diagnostic_only"] is True
    assert r313_evidence["activation_proof"] is False
    assert r313_good["NativeDrawPathActivationAllowed"] is False

    def check_r313_inexact(log: str, missing: bool = False) -> None:
        case = run_case(log + r306_signature_tail)
        inventory = case["ActivationEvidence"]["ProgrammableShaderInventory"]
        ref = {"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}
        evidence = inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
            "SourceMappingHandoff"
        ]
        if missing:
            assert evidence is None
            assert inventory["SourceMappingHandoffEvidenceMissingSignatures"] == [ref]
        else:
            assert evidence is not None
            assert evidence["summary_correlation_exact"] is False
            assert evidence["fail_closed"] is False
            assert inventory["SourceMappingHandoffCorrelationInexactSignatures"] == [ref]
        assert inventory["SourceMappingHandoffEvidenceCoverageComplete"] is False
        assert case["NativeDrawPathActivationAllowed"] is False

    check_r313_inexact(r313_support.replace(r313_handoff_line, ""), missing=True)
    check_r313_inexact(
        r313_support.replace(r313_handoff_line, r313_handoff_line * 2)
    )
    check_r313_inexact(
        r313_support.replace(
            "0x6AFFAF0E35D2F69B", "0x0000000000000000"
        )
    )
    # R314: counterfeit, altered R271/R272 identity and invalid ready bit
    # must all fail exact native R273 snapshot reconstruction.
    check_r313_inexact(
        r313_support.replace("0x6AFFAF0E35D2F69B", "0xDEADBEEF00000001")
    )
    check_r313_inexact(
        r313_support.replace("pairHash=0x1111111111111111",
                             "pairHash=0x1111111111111112")
    )
    check_r313_inexact(
        r313_support.replace("samplerHash=0x3434343434343434",
                             "samplerHash=0x3434343434343435")
    )
    check_r313_inexact(
        r313_support.replace("exact=1 snapshot=0x6AFFAF0E35D2F69B",
                             "exact=0 snapshot=0x6AFFAF0E35D2F69B")
    )
    # New R271 invalidates the handoff and R272; a later R276 cannot
    # consume stale evidence even when the signature ordinal is identical.
    check_r313_inexact(
        r313_support.replace(
            "VR DX11 R276 semanticTranslationPlan signature#1:",
            r312_source + "VR DX11 R276 semanticTranslationPlan signature#1:",
        ),
        missing=True,
    )
    # A second R272 invalidates the previous R273 handoff.
    check_r313_inexact(
        r313_support.replace(
            "VR DX11 R276 semanticTranslationPlan signature#1:",
            r312_mapping + "VR DX11 R276 semanticTranslationPlan signature#1:",
        ),
        missing=True,
    )
    # R273 without R272 is recorded, never treated as an exact producer.
    check_r313_inexact(r312_source + r313_handoff_line + r312_plan)


    # R315: independently computed from native R276 FNV literals + u64 mixer.
    # R313/R314's earlier made-up R276 identity never counted as source proof.
    r315_verified_plan = (
        "VR DX11 R276 semanticTranslationPlan signature#1: "
        "exact=1 snapshot=0x3EBF2A2588EB078C "
        "targetVS=0x85964F52DCEA7047 targetPS=0xF799FE0110D02702 "
        "revision=0x780383EB93D997F4 contract=0x19283E27A12954B5\n"
    )
    r315_original_plan = r312_plan
    r315_good_support = r313_support.replace(
        r315_original_plan, r315_verified_plan, 1
    )

    def r315_plan_evidence(log: str) -> tuple[dict, dict]:
        report = run_case(log + r306_signature_tail)
        inventory = report["ActivationEvidence"]["ProgrammableShaderInventory"]
        plan = inventory["Pairs"][0]["SemanticTranslationEvidence"][0]["Plan"]
        return report, plan

    r315_good, r315_plan = r315_plan_evidence(r315_good_support)
    assert r315_plan["producer_chain_exact"] is True
    assert r315_plan["scalar_identity_matches_producer"] is True
    assert r315_plan["expected_target_vertex_semantic_hash"] == 0x85964F52DCEA7047
    assert r315_plan["expected_target_pixel_semantic_hash"] == 0xF799FE0110D02702
    assert r315_plan["expected_translator_revision_hash"] == 0x780383EB93D997F4
    assert r315_plan["expected_semantic_contract_hash"] == 0x19283E27A12954B5
    assert r315_plan["expected_snapshot"] == 0x3EBF2A2588EB078C
    assert r315_plan["summary_correlation_exact"] is True
    assert r315_plan["fail_closed"] is True
    assert r315_plan["diagnostic_only"] is True
    assert r315_plan["activation_proof"] is False
    assert r315_good["NativeDrawPathActivationAllowed"] is False

    def r315_reject(log: str) -> None:
        report, plan = r315_plan_evidence(log)
        assert plan["summary_correlation_exact"] is False
        assert plan["fail_closed"] is False
        assert plan["activation_proof"] is False
        assert report["NativeDrawPathActivationAllowed"] is False

    # R276 counterfeit output, otherwise credible source producers.
    for source, forged in [
        ("0x3EBF2A2588EB078C", "0x3EBF2A2588EB078D"),
        ("0x85964F52DCEA7047", "0x85964F52DCEA7046"),
        ("0xF799FE0110D02702", "0xF799FE0110D02703"),
        ("0x780383EB93D997F4", "0x780383EB93D997F5"),
        ("0x19283E27A12954B5", "0x19283E27A12954B4"),
    ]:
        r315_reject(r315_good_support.replace(source, forged, 1))

    # Correct-looking R276 is not enough if source, mapping, handoff or
    # readiness identity is altered, missing or out of order.
    r315_reject(r315_good_support.replace(
        "pairHash=0x1111111111111111",
        "pairHash=0x1111111111111112", 1,
    ))
    r315_reject(r315_good_support.replace(
        "constantHash=0x1212121212121212",
        "constantHash=0x1212121212121213", 1,
    ))
    r315_reject(r315_good_support.replace(
        "R273 sourceMappingHandoff: exact=1",
        "R273 sourceMappingHandoff: exact=0", 1,
    ))
    r315_reject(r315_good_support.replace(
        "R276 semanticTranslationPlan signature#1: exact=1",
        "R276 semanticTranslationPlan signature#1: exact=0", 1,
    ))
    r315_reject(r315_good_support.replace(r313_handoff_line, "", 1))
    r315_reject(r315_good_support.replace(
        r315_verified_plan, r313_handoff_line + r315_verified_plan, 1,
    ))
    # Even a forged R275 readiness receipt cannot grant native draw authority.
    r315_receipt, r315_plan = r315_plan_evidence(
        r315_good_support
        + "VR DX11 R275 translatedSemanticReceipt signature#1: "
          "exact=1 objectReady=1 snapshot=0xDEADBEEF00000001\n"
    )
    assert r315_plan["summary_correlation_exact"] is True
    assert r315_plan["activation_proof"] is False
    assert r315_receipt["NativeDrawPathActivationAllowed"] is False

    # R316: the native composer hashes many fields absent from R275 logging.
    # A three-field receipt claim, even if nonzero and exact=1, cannot
    # authenticate object ownership or silently unlock programmable draws.
    native_backend = (ROOT / "src/vr/d3d11/native_backend.cpp").read_text(
        encoding="utf-8"
    )
    native_census = (ROOT / "src/vr/d3d11/runtime_census.cpp").read_text(
        encoding="utf-8"
    )
    receipt_composer = native_backend.split(
        "NativeProgrammableShaderTranslatedSemanticReceipt\n"
        "compose_programmable_shader_translated_semantic_receipt(", 1
    )[1].split(
        "validate_programmable_shader_translated_semantic_receipt_snapshot(", 1
    )[0]
    assert "mix_readiness_snapshot_token(token, out.cacheKey)" in receipt_composer
    assert "out.translationObjectSnapshotToken" in receipt_composer
    assert "out.sourceMappingHandoffSnapshotToken" in receipt_composer
    assert "out.translationPlanSnapshotToken" in receipt_composer
    assert "0x275276u" in receipt_composer
    assert (
        "R275 translatedSemanticReceipt signature#{}: exact={} "
        "objectReady={} snapshot=0x{:016X}"
    ) in native_census

    def r316_receipt_line(
        exact: int, ready: int, snapshot: str,
        source: str = r315_good_support,
    ) -> tuple[dict, dict]:
        report = run_case(
            source
            + "VR DX11 R275 translatedSemanticReceipt signature#1: "
              f"exact={exact} objectReady={ready} snapshot=0x{snapshot}\n"
            + r306_signature_tail
        )
        receipt = report["ActivationEvidence"]["ProgrammableShaderInventory"][
            "Pairs"
        ][0]["SemanticTranslationEvidence"][0]["Receipt"]
        return report, receipt

    r316_forged, r316_claim = r316_receipt_line(
        1, 1, "DEADBEEF00000001"
    )
    assert r316_claim["claim_shape_consistent"] is True
    assert r316_claim["producer_chain_correlated"] is True
    assert r316_claim["snapshot_independently_verified"] is False
    assert "translationObjectSnapshotToken" in (
        r316_claim["unlogged_receipt_bindings"]
    )
    assert r316_claim["provenance_status"] == (
        "UNVERIFIABLE_R275_UNLOGGED_BINDINGS"
    )
    assert r316_claim["activation_proof"] is False
    assert r316_forged["NativeDrawPathActivationAllowed"] is False

    for exact, ready, snapshot in (
        (1, 1, "0000000000000000"),
        (1, 0, "DEADBEEF00000001"),
        (0, 0, "DEADBEEF00000001"),
    ):
        report, receipt = r316_receipt_line(exact, ready, snapshot)
        assert receipt["claim_shape_consistent"] is False
        assert receipt["provenance_status"] == "CONTRADICTORY_R275_TELEMETRY"
        assert receipt["snapshot_independently_verified"] is False
        assert report["NativeDrawPathActivationAllowed"] is False

    # A not-ready receipt has a zero token, regardless of objectReady bit.
    for ready in (0, 1):
        report, receipt = r316_receipt_line(0, ready, "0000000000000000")
        assert receipt["claim_shape_consistent"] is True
        assert receipt["snapshot_independently_verified"] is False
        assert report["NativeDrawPathActivationAllowed"] is False

    r316_unbound, r316_claim = r316_receipt_line(
        1, 1, "DEADBEEF00000001",
        r315_good_support.replace(
            "R276 semanticTranslationPlan signature#1: exact=1",
            "R276 semanticTranslationPlan signature#1: exact=0", 1
        ),
    )
    assert r316_claim["producer_chain_correlated"] is False
    assert r316_claim["provenance_status"] == (
        "UNVERIFIABLE_R275_PRODUCER_CHAIN"
    )
    assert r316_unbound["NativeDrawPathActivationAllowed"] is False


    # R317: source-side scalar telemetry must permit an exact 64-bit hash
    # reconstruction but cannot by itself authenticate real D3D11 objects.
    from analyze_dx11_census import (
        R317_RECEIPT_HEX_FIELDS, R317_RECEIPT_BOOL_FIELDS,
        recompute_r275_receipt_scalar_snapshot,
    )
    r317_fields = {
        name: index + 0x100
        for index, name in enumerate(R317_RECEIPT_HEX_FIELDS)
    }
    r317_fields.update({name: 1 for name in R317_RECEIPT_BOOL_FIELDS})
    r317_snapshot = recompute_r275_receipt_scalar_snapshot(r317_fields)
    assert r317_snapshot != 0
    r317_prefix = (
        "VR DX11 R275 translatedSemanticReceipt signature#1: "
        f"exact=1 objectReady=1 snapshot=0x{r317_snapshot:016X}\\n"
    ).replace("\\\\n", "\\n")
    r317_inputs_line = (
        "VR DX11 R317 receiptInputs signature#1: "
        + " ".join(
            f"{name}=0x{r317_fields[name]:016X}"
            for name in R317_RECEIPT_HEX_FIELDS
        )
        + " "
        + " ".join(
            f"{name}={r317_fields[name]}"
            for name in R317_RECEIPT_BOOL_FIELDS
        )
        + "\\n"
    )
    def r317_case(snapshot_line: str, inputs_line: str) -> tuple[dict, dict]:
        report = run_case(
            "VR DX11 R73 signature#1: primitive=4 fixedFn=0\\n"
            + snapshot_line + inputs_line
        )
        receipt = report["ActivationEvidence"]["ProgrammableShaderInventory"][
            "Pairs"
        ][0]["SemanticTranslationEvidence"][0]["Receipt"]
        return report, receipt

    r317_good, r317_receipt = r317_case(r317_prefix, r317_inputs_line)
    assert r317_receipt["r317_inputs_present"] is True
    assert r317_receipt["r317_inputs_unique"] is True
    assert r317_receipt["r317_scalar_snapshot_matches"] is True
    assert r317_receipt["snapshot_independently_verified"] is False
    assert r317_receipt["activation_proof"] is False
    assert r317_good["NativeDrawPathActivationAllowed"] is False

    r317_wrong, r317_bad = r317_case(
        r317_prefix.replace(f"{r317_snapshot:016X}", "DEADBEEFDEADBEEF"),
        r317_inputs_line
    )
    assert r317_bad["r317_scalar_snapshot_matches"] is False
    assert r317_bad["provenance_status"] == "R275_SCALAR_HASH_MISMATCH"
    assert r317_wrong["NativeDrawPathActivationAllowed"] is False
    _, r317_duplicate = r317_case(
        r317_prefix, r317_inputs_line + r317_inputs_line
    )
    assert r317_duplicate["r317_inputs_unique"] is False
    assert r317_duplicate["provenance_status"] == "DUPLICATE_R317_RECEIPT_INPUTS"

    r308_production_semantic_review = run_case(
        "VR DX11 R291 productionSemanticReview signature#1: "
        "admissionExact=1 reviewExact=1 inputLayoutReady=1 "
        "inputLayoutReused=0 semanticReady=1 boundaryPreserved=1 "
        "admissionSnapshot=0x1111111111111111 "
        "inputLayoutSnapshot=0x2222222222222222 "
        "semanticSnapshot=0x3333333333333333 "
        "reviewSnapshot=0x4444444444444444\n"
        + r306_signature_tail
    )
    r308_inventory = r308_production_semantic_review["ActivationEvidence"][
        "ProgrammableShaderInventory"
    ]
    assert r308_inventory["ProductionSemanticReviewEvidenceSignatures"] == 1
    assert r308_inventory["ProductionSemanticReviewExactSignatures"] == 1
    assert r308_inventory["ProductionSemanticReviewFailClosedSignatures"] == 1
    assert r308_inventory[
        "ProductionSemanticReviewCorrelationInexactSignatures"
    ] == []
    assert r308_inventory[
        "ProductionSemanticReviewEvidenceCoverageComplete"
    ] is True
    r308_evidence = r308_inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
        "ProductionSemanticReview"
    ]
    assert r308_evidence["admission_exact"] is True
    assert r308_evidence["review_exact"] is True
    assert r308_evidence["input_layout_ready"] is True
    assert r308_evidence["semantic_ready"] is True
    assert r308_evidence["boundary_preserved"] is True
    assert r308_evidence["admission_snapshot_correlated"] is True
    assert r308_evidence["review_snapshot_correlated"] is True
    assert r308_evidence["review_state_correlated"] is True
    assert r308_evidence["summary_correlation_exact"] is True
    assert r308_evidence["fail_closed"] is True
    assert r308_evidence["activation_proof"] is False
    assert r308_production_semantic_review[
        "NativeDrawPathActivationAllowed"
    ] is False

    r308_inconsistent_semantic_review = run_case(
        "VR DX11 R291 productionSemanticReview signature#1: "
        "admissionExact=1 reviewExact=1 inputLayoutReady=1 "
        "inputLayoutReused=0 semanticReady=0 boundaryPreserved=1 "
        "admissionSnapshot=0x1111111111111111 "
        "inputLayoutSnapshot=0x2222222222222222 "
        "semanticSnapshot=0x0000000000000000 "
        "reviewSnapshot=0x4444444444444444\n"
        + r306_signature_tail
    )
    r308_inconsistent_inventory = r308_inconsistent_semantic_review[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    assert r308_inconsistent_inventory[
        "ProductionSemanticReviewCorrelationInexactSignatures"
    ] == [{"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}]
    assert (
        r308_inconsistent_inventory[
            "ProductionSemanticReviewEvidenceCoverageComplete"
        ]
        is False
    )
    r308_inconsistent_evidence = r308_inconsistent_inventory["Pairs"][0][
        "SemanticTranslationEvidence"
    ][0]["ProductionSemanticReview"]
    assert r308_inconsistent_evidence["review_state_correlated"] is False
    assert r308_inconsistent_evidence["summary_correlation_exact"] is False
    assert r308_inconsistent_evidence["fail_closed"] is False
    assert r308_inconsistent_evidence["activation_proof"] is False
    assert r308_inconsistent_semantic_review[
        "NativeDrawPathActivationAllowed"
    ] is False

    r307_production_source_revalidation = run_case(
        "VR DX11 R297 productionSourceRevalidation signature#1: "
        "drawExact=1 nativeBufferEligible=1 r258Present=0 r258Contract=0 "
        "kindMatch=0 startMatch=0 countDerivable=1 countMatch=0 "
        "elementCount=6 indexFormatKnown=1 indexFormatMatch=0 "
        "indexOffsetMatch=0 indexFormat=0 baseMatch=0 minMatch=0 "
        "numMatch=0 rangeMatch=0 cacheMatch=0 joinExact=0 "
        "boundaryPreserved=1 missingEvidenceMask=0x00000004 "
        "r258Snapshot=0x0000000000000000 "
        "joinSnapshot=0x1111111111111111\n"
        + r306_signature_tail
    )
    r307_inventory = r307_production_source_revalidation["ActivationEvidence"][
        "ProgrammableShaderInventory"
    ]
    assert r307_inventory["ProductionSourceRevalidationEvidenceSignatures"] == 1
    assert r307_inventory["ProductionSourceRevalidationJoinExactSignatures"] == 0
    assert r307_inventory["ProductionSourceRevalidationFailClosedSignatures"] == 1
    assert (
        r307_inventory["ProductionSourceRevalidationCorrelationInexactSignatures"]
        == []
    )
    assert r307_inventory[
        "ProductionSourceRevalidationEvidenceCoverageComplete"
    ] is True
    r307_evidence = r307_inventory["Pairs"][0]["SemanticTranslationEvidence"][0][
        "ProductionSourceRevalidation"
    ]
    assert r307_evidence["draw_identity_exact"] is True
    assert r307_evidence["native_buffer_eligible"] is True
    assert r307_evidence["r258_receipt_present"] is False
    assert r307_evidence["missing_evidence_mask"] == 0x4
    assert r307_evidence["expected_observable_missing_evidence_mask"] == 0x4
    assert r307_evidence["observable_mask_matches"] is True
    assert r307_evidence["join_snapshot_correlated"] is True
    assert r307_evidence["receipt_absence_fail_closed"] is True
    assert r307_evidence["summary_correlation_exact"] is True
    assert r307_evidence["fail_closed"] is True
    assert r307_evidence["activation_proof"] is False
    assert r307_production_source_revalidation[
        "NativeDrawPathActivationAllowed"
    ] is False

    r307_inconsistent_source_revalidation = run_case(
        "VR DX11 R297 productionSourceRevalidation signature#1: "
        "drawExact=1 nativeBufferEligible=1 r258Present=0 r258Contract=0 "
        "kindMatch=0 startMatch=0 countDerivable=1 countMatch=0 "
        "elementCount=6 indexFormatKnown=1 indexFormatMatch=0 "
        "indexOffsetMatch=0 indexFormat=0 baseMatch=0 minMatch=0 "
        "numMatch=0 rangeMatch=0 cacheMatch=0 joinExact=0 "
        "boundaryPreserved=1 missingEvidenceMask=0x00000000 "
        "r258Snapshot=0x2222222222222222 "
        "joinSnapshot=0x1111111111111111\n"
        + r306_signature_tail
    )
    r307_inconsistent_inventory = r307_inconsistent_source_revalidation[
        "ActivationEvidence"
    ]["ProgrammableShaderInventory"]
    assert r307_inconsistent_inventory[
        "ProductionSourceRevalidationCorrelationInexactSignatures"
    ] == [{"source_log": "OutRun2006Tweaks.log", "startup_epoch": 0, "id": 1}]
    assert (
        r307_inconsistent_inventory[
            "ProductionSourceRevalidationEvidenceCoverageComplete"
        ]
        is False
    )
    r307_inconsistent_evidence = r307_inconsistent_inventory["Pairs"][0][
        "SemanticTranslationEvidence"
    ][0]["ProductionSourceRevalidation"]
    assert r307_inconsistent_evidence["observable_mask_matches"] is False
    assert r307_inconsistent_evidence["receipt_absence_fail_closed"] is False
    assert r307_inconsistent_evidence["summary_correlation_exact"] is False
    assert r307_inconsistent_evidence["activation_proof"] is False
    assert r307_inconsistent_source_revalidation[
        "NativeDrawPathActivationAllowed"
    ] is False

    r277_programmable_semantic = run_case(
        "VR DX11 R120 census: samples=6 exact=0 fixedFn=0 programmable=6 "
        "topologyUnsupported=0 signatures=2 declSamples=0 indexedSamples=0 texturedSamples=0 "
        "resourceExact[indexUnsupported=0,textureUnsupported=0,colorUnsupported=0,depthUnsupported=0] "
        "shaderReadiness[introspectionFailure=0,mixedPair=0,translationExact=0,"
        "fixedFunctionPending=0,programmablePending=6] "
        "programmableSemantic[planExact=5,planPending=1,receiptExact=0,receiptPending=6] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,stencil=0,"
        "fog=0,lighting=0,srgb=0,fill=0,blend=0,depthCmp=0,cull=0]\n"
    )
    assert r277_programmable_semantic["LatestSummary"]["shaderSemanticPlanExact"] == 5
    assert r277_programmable_semantic["LatestSummary"]["shaderSemanticPlanPending"] == 1
    assert r277_programmable_semantic["LatestSummary"]["shaderSemanticReceiptExact"] == 0
    assert r277_programmable_semantic["LatestSummary"]["shaderSemanticReceiptPending"] == 6
    r277_evidence = r277_programmable_semantic["ActivationEvidence"][
        "ProgrammableSemanticTranslation"
    ]
    assert r277_evidence["PlanExactSamples"] == 5
    assert r277_evidence["PlanPendingSamples"] == 1
    assert r277_evidence["ReceiptExactSamples"] == 0
    assert r277_evidence["ReceiptPendingSamples"] == 6
    assert r277_evidence["TranslationImplemented"] is False
    assert r277_evidence["DiagnosticOnly"] is True
    assert r277_evidence["ActivationProof"] is False
    assert r277_programmable_semantic["NativeDrawPathActivationAllowed"] is False

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

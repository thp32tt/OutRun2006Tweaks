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
        "fixedFunctionPending=60,programmablePending=4] "
        "unsupported[incomplete=0,wbuffer=0,sepAlpha=0,alphaTest=0,"
        "stencil=0,fog=0,lighting=0,srgb=0,fill=0,blend=0,"
        "depthCmp=0,cull=0]\n"
    )
    assert r80["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert r80["NativeDrawPathActivationAllowed"] is False
    assert r80["LatestSummary"]["shaderIntrospectionFailure"] == 0
    assert r80["LatestSummary"]["shaderMixedPair"] == 0
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
        "VR DX11 R160 ffp signature#1 stage#2: "
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
    assert r114_coverage["NonExhaustive"] is True
    assert r114_coverage["ActivationProof"] is False
    assert r114_saturated["NativeDrawPathActivationAllowed"] is False

    exhaustive = run_case(
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
        "depthBias=5,vertexBlend=6,dither=7]\n"
    )
    assert extended_unsupported["Status"] == "UNSUPPORTED_BEHAVIOR_OBSERVED"
    assert extended_unsupported["UnsupportedTotalLatest"] == 27
    assert extended_unsupported["LatestSummary"]["dualSource"] == 2
    assert extended_unsupported["LatestSummary"]["shadeMode"] == 3
    assert extended_unsupported["LatestSummary"]["clipping"] == 4
    assert extended_unsupported["LatestSummary"]["depthBias"] == 5
    assert extended_unsupported["LatestSummary"]["vertexBlend"] == 6
    assert extended_unsupported["LatestSummary"]["dither"] == 7
    assert extended_unsupported["LatestSummary"]["texCoordWrap"] == 0
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
    assert r170_wrap["NativeDrawPathActivationAllowed"] is False

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

    print("DX11 census analyzer regression R120/SRC1 exhaustive-mode: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

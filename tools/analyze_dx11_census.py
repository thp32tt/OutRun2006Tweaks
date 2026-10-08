#!/usr/bin/env python3
"""Extract DX11 native-backend census evidence from one OutRun VR session."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

SUMMARY_RE = re.compile(
    r"VR DX11 R(?:7[23456789]|8[012345]|114|120) census: "
    r"samples=(?P<samples>\d+) exact=(?P<exact>\d+) "
    r"fixedFn=(?P<fixedFn>\d+) programmable=(?P<programmable>\d+) "
    r"topologyUnsupported=(?P<topologyUnsupported>\d+) "
    r"(?:rasterSemantics\[pointUnsupported=(?P<pointRasterUnsupported>\d+),"
    r"lineUnsupported=(?P<lineRasterUnsupported>\d+)\] )?"
    r"signatures=(?P<signatures>\d+) "
    r"(?:sampling\[drawsSeen=(?P<samplingDrawsSeen>\d+),"
    r"stride=(?P<samplingStride>\d+),scheme=(?P<samplingScheme>\d+)\] "
    r"signatureCaps\[hashCap=(?P<signatureHashCap>\d+),"
    r"hashCapHitSamples=(?P<signatureHashCapHitSamples>\d+),"
    r"detailCap=(?P<signatureDetailCap>\d+),"
    r"detailSkipped=(?P<signatureDetailSkipped>\d+)\] )?"
    r"declSamples=(?P<declSamples>\d+) "
    r"indexedSamples=(?P<indexedSamples>\d+) texturedSamples=(?P<texturedSamples>\d+) "
    r"resourceExact\[(?:introspectionFailure=(?P<introspectionFailure>\d+),)?"
    r"(?:(?:behaviorUnsupported=(?P<behaviorUnsupported>\d+),"
    r"mutationTelemetryRequired=(?P<mutationTelemetryRequired>\d+),"
    r"managedShadowRequired=(?P<managedShadowRequired>\d+),))?"
    r"indexUnsupported=(?P<indexUnsupported>\d+),"
    r"textureUnsupported=(?P<textureUnsupported>\d+),"
    r"colorUnsupported=(?P<colorUnsupported>\d+),"
    r"depthUnsupported=(?P<depthUnsupported>\d+)"
    r"(?:,auxRenderTargetUnsupported=(?P<auxRenderTargetUnsupported>\d+))?\] "
    r"(?:mutation\[writeUnlocks=(?P<mutationWriteUnlocks>\d+),"
    r"readOnlyUnlocks=(?P<mutationReadOnlyUnlocks>\d+),"
    r"discardWriteUnlocks=(?P<mutationDiscardWriteUnlocks>\d+),"
    r"noOverwriteWriteUnlocks=(?P<mutationNoOverwriteWriteUnlocks>\d+)\] )?"
    r"(?:mutationPlan\[exact=(?P<mutationPlanExact>\d+),"
    r"unsupported=(?P<mutationPlanUnsupported>\d+),"
    r"managedShadow=(?P<mutationPlanManagedShadow>\d+),"
    r"mapWrite=(?P<mutationPlanMapWrite>\d+),"
    r"mapDiscard=(?P<mutationPlanMapDiscard>\d+),"
    r"mapNoOverwrite=(?P<mutationPlanMapNoOverwrite>\d+),"
    r"updateSubresource=(?P<mutationPlanUpdateSubresource>\d+)\] )?"
    r"(?:textureMutation\[writeUnlocks=(?P<textureMutationWriteUnlocks>\d+),"
    r"readOnlyUnlocks=(?P<textureMutationReadOnlyUnlocks>\d+),"
    r"descriptorFailures=(?P<textureMutationDescriptorFailures>\d+),"
    r"updateTextureSuccesses=(?P<textureUpdateTextureSuccesses>\d+),"
    r"updateTextureFailures=(?P<textureUpdateTextureFailures>\d+),"
    r"updateSurfaceSuccesses=(?P<textureUpdateSurfaceSuccesses>\d+),"
    r"updateSurfaceFailures=(?P<textureUpdateSurfaceFailures>\d+)\] )?"
    r"(?:managedLifetime\[shadowWrites=(?P<managedShadowWrites>\d+),"
    r"shadowReads=(?P<managedShadowReads>\d+),"
    r"resetSuccesses=(?P<managedResetSuccesses>\d+),"
    r"shadowPreserved=(?P<managedResetShadowPreserved>\d+),"
    r"deviceGeneration=(?P<managedDeviceGeneration>\d+),"
    r"shadowVersion=(?P<managedShadowVersion>\d+),"
    r"mirrorGeneration=(?P<managedMirrorGeneration>\d+),"
    r"mirrorVersion=(?P<managedMirrorVersion>\d+),"
    r"mirrorReady=(?P<managedMirrorReady>\d+)\] )?"
    r"(?:managedTextureShadow\[requiredSamples=(?P<managedTextureShadowRequiredSamples>\d+),"
    r"readySamples=(?P<managedTextureShadowReadySamples>\d+),"
    r"pendingSamples=(?P<managedTextureShadowPendingSamples>\d+)\] )?"
    r"(?:managedTextureMutationSource\[updateTextureInvalidations=(?P<managedTextureUpdateTextureInvalidations>\d+),"
    r"updateSurfaceInvalidations=(?P<managedTextureUpdateSurfaceInvalidations>\d+)\] )?"
    r"(?:inputLayout\[exact=(?P<inputLayoutExact>\d+),"
    r"unsupported=(?P<inputLayoutUnsupported>\d+),"
    r"(?:fvfExact=(?P<inputLayoutFvfExact>\d+),)?"
    r"fvfPending=(?P<inputLayoutFvfPending>\d+)\] )?"
    r"(?:shaderReadiness\[introspectionFailure=(?P<shaderIntrospectionFailure>\d+),"
    r"mixedPair=(?P<shaderMixedPair>\d+),"
    r"(?:translationExact=(?P<shaderTranslationExact>\d+),)?"
    r"fixedFunctionPending=(?P<shaderFixedFunctionPending>\d+),"
    r"programmablePending=(?P<shaderProgrammablePending>\d+)\] )?"
    r"(?:programmableSemantic\[planExact=(?P<shaderSemanticPlanExact>\d+),"
    r"planPending=(?P<shaderSemanticPlanPending>\d+),"
    r"receiptExact=(?P<shaderSemanticReceiptExact>\d+),"
    r"receiptPending=(?P<shaderSemanticReceiptPending>\d+)\] )?"
    r"(?:ffpCoverage\[exact=(?P<fixedFunctionCoverageExact>\d+),"
    r"queryFailure=(?P<fixedFunctionQueryFailure>\d+)\] )?"
    r"(?:ffpReadiness\[ready=(?P<fixedFunctionReadinessReady>\d+),"
    r"pending=(?P<fixedFunctionReadinessPending>\d+)\] )?"
    r"(?:ffpShaderPrototype\[generated=(?P<fixedFunctionShaderPrototypeGenerated>\d+),"
    r"pending=(?P<fixedFunctionShaderPrototypePending>\d+)\] )?"
    r"(?:ffpShaderCompile\[succeeded=(?P<fixedFunctionShaderCompileSucceeded>\d+),"
    r"failed=(?P<fixedFunctionShaderCompileFailed>\d+),"
    r"skippedCap=(?P<fixedFunctionShaderCompileSkippedCap>\d+)\] )?"
    r"(?:textureStageResource\[bound=(?P<textureStageBound>\d+),"
    r"exact=(?P<textureStageExact>\d+),"
    r"pending=(?P<textureStagePending>\d+)\] )?"
    r"(?:textureStageManagedShadow\[required=(?P<textureStageManagedShadowRequired>\d+),"
    r"ready=(?P<textureStageManagedShadowReady>\d+),"
    r"pending=(?P<textureStageManagedShadowPending>\d+)\] )?"
    r"(?:dualSourceBlend\[any=(?P<dualSourceBlendAny>\d+),"
    r"rgbSrc=(?P<dualSourceBlendRgbSrc>\d+),"
    r"rgbDst=(?P<dualSourceBlendRgbDst>\d+),"
    r"alphaSrc=(?P<dualSourceBlendAlphaSrc>\d+),"
    r"alphaDst=(?P<dualSourceBlendAlphaDst>\d+)\] )?"
    r"unsupported\[incomplete=(?P<incomplete>\d+),"
    r"wbuffer=(?P<wbuffer>\d+),sepAlpha=(?P<sepAlpha>\d+),"
    r"alphaTest=(?P<alphaTest>\d+),stencil=(?P<stencil>\d+),"
    r"fog=(?P<fog>\d+),lighting=(?P<lighting>\d+),"
    r"srgb=(?P<srgb>\d+),fill=(?P<fill>\d+),"
    r"blend=(?P<blend>\d+),depthCmp=(?P<depthCmp>\d+),"
    r"cull=(?P<cull>\d+)"
    r"(?:,dualSource=(?P<dualSource>\d+),shadeMode=(?P<shadeMode>\d+),"
    r"clipping=(?P<clipping>\d+),depthBias=(?P<depthBias>\d+),"
    r"vertexBlend=(?P<vertexBlend>\d+),dither=(?P<dither>\d+)"
    r"(?:,texCoordWrap=(?P<texCoordWrap>\d+)"
    r"(?:,mrtColorWrite=(?P<mrtColorWrite>\d+)"
    r"(?:,specular=(?P<specular>\d+))?)?)?)?\]"
)

BOOTSTRAP_RE = re.compile(
    r"VR DX11 R72 bootstrap probe: ready=(?P<ready>[01]) "
    r"featureLevel=0x(?P<featureLevel>[0-9A-Fa-f]+) "
    r"selectedLuidValid=(?P<selectedLuidValid>[01]) "
    r"selectedLuid=(?P<luidHigh>[0-9A-Fa-f]{8}):(?P<luidLow>[0-9A-Fa-f]{8})"
)
BOOTSTRAP_SKIP_RE = re.compile(
    r"VR DX11 R72 bootstrap probe skipped: compatible=(?P<compatible>[01]) "
    r"adapterLuidValid=(?P<adapterLuidValid>[01])"
)

STARTUP_RE = re.compile(
    r"VR DX11 R71 census: observed=(?P<observed>[01]) "
    r"size=(?P<width>\d+)x(?P<height>\d+) "
    r"sourceFormat=(?P<sourceFormat>-?\d+) nativeFormat=(?P<nativeFormat>-?\d+) "
    r"msaa=(?P<msaa>-?\d+) bootstrapCompatible=(?P<bootstrapCompatible>[01])"
)

SIGNATURE_RE = re.compile(r"VR DX11 R(?:7[23456789]|8[012345]) signature#(?P<id>\d+): (?P<body>.*)")
SIGNATURE_SHADER_RE = re.compile(
    r"shader\[introspection=(?P<introspection>[01]),mixed=(?P<mixed>[01]),"
    r"exact=(?P<translationExact>[01]),"
    r"vsPresent=(?P<vsPresent>[01]),vsBytes=(?P<vsBytes>\d+),"
    r"vsVersion=0x(?P<vsVersion>[0-9A-Fa-f]+),"
    r"vsHash=0x(?P<vsHash>[0-9A-Fa-f]+),"
    r"psPresent=(?P<psPresent>[01]),psBytes=(?P<psBytes>\d+),"
    r"psVersion=0x(?P<psVersion>[0-9A-Fa-f]+),"
    r"psHash=0x(?P<psHash>[0-9A-Fa-f]+)\]"
)
R271_SOURCE_SEMANTIC_PAIR_RE = re.compile(
    r"VR DX11 R271 sourceSemanticPair: exact=(?P<exact>[01]) "
    r"cacheKey=0x(?P<cacheKey>[0-9A-Fa-f]+) "
    r"pairHash=0x(?P<pairHash>[0-9A-Fa-f]+) "
    r"vsRegisterHash=0x(?P<vsRegisterHash>[0-9A-Fa-f]+) "
    r"psRegisterHash=0x(?P<psRegisterHash>[0-9A-Fa-f]+) "
    r"linkHash=0x(?P<linkHash>[0-9A-Fa-f]+) "
    r"receiptRevision=0x(?P<receiptRevision>[0-9A-Fa-f]+) "
    r"contract=0x(?P<contract>[0-9A-Fa-f]+)"
)
R272_REGISTER_MAPPING_PLAN_RE = re.compile(
    r"VR DX11 R272 registerMappingPlan: exact=(?P<exact>[01]) "
    r"constants=(?P<constants>\d+) samplers=(?P<samplers>\d+) "
    r"constantHash=0x(?P<constantHash>[0-9A-Fa-f]+) "
    r"samplerHash=0x(?P<samplerHash>[0-9A-Fa-f]+) "
    r"planRevision=0x(?P<planRevision>[0-9A-Fa-f]+) "
    r"contract=0x(?P<contract>[0-9A-Fa-f]+)"
)
R273_SOURCE_MAPPING_HANDOFF_RE = re.compile(
    r"VR DX11 R273 sourceMappingHandoff: exact=(?P<exact>[01]) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)
def recompute_r273_handoff_snapshot(
    source_pair: dict, mapping_plan: dict
) -> int:
    """Mirror native_backend.cpp R273 uint64 snapshot mixing, not a draw gate."""
    if not source_pair["exact"] or not mapping_plan["exact"]:
        return 0
    mask = (1 << 64) - 1
    token = 0xCBF29CE484222325
    for value in (
        source_pair["cache_key"],
        source_pair["pair_hash"],
        source_pair["vertex_register_hash"],
        source_pair["pixel_register_hash"],
        mapping_plan["constant_mapping_hash"],
        mapping_plan["sampler_mapping_hash"],
        mapping_plan["plan_revision_hash"],
        mapping_plan["semantic_contract_hash"],
        0x273,
    ):
        token ^= (
            value + 0x9E3779B97F4A7C15
            + ((token << 6) & mask) + (token >> 2)
        ) & mask
        token &= mask
    return token or 1



def _r276_hash_literal(text: str) -> int:
    """Native R276 lambda uses the *short* FNV offset (not R273's offset)."""
    mask = (1 << 64) - 1
    token = 1469598103934665603
    for byte in text.encode("ascii"):
        token = ((token ^ byte) * 1099511628211) & mask
    return token or 1


def _r276_mix(*fields: int) -> int:
    """Native mix_readiness_snapshot_token, unsigned 64-bit after each mix."""
    mask = (1 << 64) - 1
    token = 0xCBF29CE484222325
    for value in fields:
        token ^= (
            value + 0x9E3779B97F4A7C15
            + ((token << 6) & mask) + (token >> 2)
        ) & mask
        token &= mask
    return token or 1


def recompute_r276_semantic_plan(
    source_pair: dict, mapping_plan: dict, handoff_snapshot: int
) -> dict:
    """R315 offline reconstruction of C++ R276 (diagnostic; no draw authority).

    This checks emitted scalar identities only. The R268 bytecode linkage and
    R275 object/lifetime ownership cannot be proven from the R271/R272/R273
    scalar logs and remain separate runtime/receipt gates.
    """
    revision = _r276_hash_literal(
        "R276_D3D9_SOURCE_DERIVED_SEMANTIC_TRANSLATION_PLAN_V1"
    )
    contract = _r276_hash_literal(
        "R276_R271_R268_R273_TARGET_SEMANTIC_IDENTITY_V1"
    )
    common = (
        source_pair["pair_hash"],
        source_pair["link_hash"],
        mapping_plan["constant_mapping_hash"],
        mapping_plan["sampler_mapping_hash"],
    )
    target_vs = _r276_mix(
        common[0], source_pair["vertex_register_hash"], *common[1:],
        revision, contract, 0x5653,
    )
    target_ps = _r276_mix(
        common[0], source_pair["pixel_register_hash"], *common[1:],
        revision, contract, 0x5053,
    )
    snapshot = _r276_mix(
        source_pair["cache_key"], common[0], *common[1:],
        target_vs, target_ps, revision, contract, handoff_snapshot, 0x276,
    )
    return {
        "target_vertex_semantic_hash": target_vs,
        "target_pixel_semantic_hash": target_ps,
        "translator_revision_hash": revision,
        "semantic_contract_hash": contract,
        "snapshot": snapshot,
    }


R276_SEMANTIC_PLAN_RE = re.compile(
    r"VR DX11 R276 semanticTranslationPlan signature#(?P<signature>\d+): "
    r"exact=(?P<exact>[01]) snapshot=0x(?P<snapshot>[0-9A-Fa-f]+) "
    r"targetVS=0x(?P<targetVS>[0-9A-Fa-f]+) "
    r"targetPS=0x(?P<targetPS>[0-9A-Fa-f]+) "
    r"revision=0x(?P<revision>[0-9A-Fa-f]+) "
    r"contract=0x(?P<contract>[0-9A-Fa-f]+)"
)
R279_OBJECT_PREREQUISITE_RE = re.compile(
    r"VR DX11 R279 translationObjectPrerequisite signature#(?P<signature>\d+): "
    r"exact=(?P<exact>[01]) cacheOwnerGen=(?P<cacheOwnerGen>[01]) "
    r"slotGen=(?P<slotGen>[01]) receiptGen=(?P<receiptGen>[01]) "
    r"sameDevicePair=(?P<sameDevicePair>[01]) "
    r"cacheSnapshot=(?P<cacheSnapshot>[01]) slotSnapshot=(?P<slotSnapshot>[01]) "
    r"cacheKey=0x(?P<cacheKey>[0-9A-Fa-f]+) "
    r"planSnapshot=0x(?P<planSnapshot>[0-9A-Fa-f]+) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)
R280_OBJECT_CREATION_HANDOFF_RE = re.compile(
    r"VR DX11 R280 objectCreationHandoff signature#(?P<signature>\d+): "
    r"exact=(?P<exact>[01]) vertexSource=(?P<vertexSource>[01]) "
    r"pixelSource=(?P<pixelSource>[01]) "
    r"ownershipPrerequisite=(?P<ownershipPrerequisite>[01]) "
    r"createAuthorized=(?P<createAuthorized>[01]) "
    r"cacheKey=0x(?P<cacheKey>[0-9A-Fa-f]+) "
    r"planSnapshot=0x(?P<planSnapshot>[0-9A-Fa-f]+) "
    r"ownershipSnapshot=0x(?P<ownershipSnapshot>[0-9A-Fa-f]+) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)
R281_TRANSLATED_ARTIFACT_RECEIPT_RE = re.compile(
    r"VR DX11 R281 translatedArtifactReceipt signature#(?P<signature>\d+): "
    r"exact=(?P<exact>[01]) targetBytecodeRequired=(?P<targetRequired>[01]) "
    r"materialized=(?P<materialized>[01]) createAuthorized=(?P<createAuthorized>[01]) "
    r"cacheKey=0x(?P<cacheKey>[0-9A-Fa-f]+) "
    r"vertexIdentity=0x(?P<vertexIdentity>[0-9A-Fa-f]+) "
    r"pixelIdentity=0x(?P<pixelIdentity>[0-9A-Fa-f]+) "
    r"handoffSnapshot=0x(?P<handoffSnapshot>[0-9A-Fa-f]+) "
    r"planSnapshot=0x(?P<planSnapshot>[0-9A-Fa-f]+) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)
R282_TARGET_MATERIALIZATION_CONTRACT_RE = re.compile(
    r"VR DX11 R282 targetMaterializationContract signature#(?P<signature>\d+): "
    r"exact=(?P<exact>[01]) targetRequired=(?P<targetRequired>[01]) "
    r"materialized=(?P<materialized>[01]) compileAuthorized=(?P<compileAuthorized>[01]) "
    r"createAuthorized=(?P<createAuthorized>[01]) "
    r"cacheKey=0x(?P<cacheKey>[0-9A-Fa-f]+) "
    r"vertexContract=0x(?P<vertexContract>[0-9A-Fa-f]+) "
    r"pixelContract=0x(?P<pixelContract>[0-9A-Fa-f]+) "
    r"entry=0x(?P<entry>[0-9A-Fa-f]+) "
    r"vsProfile=0x(?P<vsProfile>[0-9A-Fa-f]+) "
    r"psProfile=0x(?P<psProfile>[0-9A-Fa-f]+) "
    r"flags=0x(?P<flags>[0-9A-Fa-f]+) "
    r"artifactSnapshot=0x(?P<artifactSnapshot>[0-9A-Fa-f]+) "
    r"planSnapshot=0x(?P<planSnapshot>[0-9A-Fa-f]+) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)
R283_TARGET_BYTECODE_MATERIALIZATION_RE = re.compile(
    r"VR DX11 R283 targetBytecodeMaterialization signature#(?P<signature>\d+): "
    r"exact=(?P<exact>[01]) vertexSubset=(?P<vertexSubset>[01]) "
    r"pixelSubset=(?P<pixelSubset>[01]) vertexCompiled=(?P<vertexCompiled>[01]) "
    r"pixelCompiled=(?P<pixelCompiled>[01]) materialized=(?P<materialized>[01]) "
    r"createAuthorized=(?P<createAuthorized>[01]) "
    r"cacheKey=0x(?P<cacheKey>[0-9A-Fa-f]+) "
    r"vertexSourceBytes=(?P<vertexSourceBytes>\d+) "
    r"pixelSourceBytes=(?P<pixelSourceBytes>\d+) "
    r"vertexSource=0x(?P<vertexSource>[0-9A-Fa-f]+) "
    r"pixelSource=0x(?P<pixelSource>[0-9A-Fa-f]+) "
    r"vertexBytes=(?P<vertexBytes>\d+) pixelBytes=(?P<pixelBytes>\d+) "
    r"vertexBytecode=0x(?P<vertexBytecode>[0-9A-Fa-f]+) "
    r"pixelBytecode=0x(?P<pixelBytecode>[0-9A-Fa-f]+) "
    r"vertexArtifact=0x(?P<vertexArtifact>[0-9A-Fa-f]+) "
    r"pixelArtifact=0x(?P<pixelArtifact>[0-9A-Fa-f]+) "
    r"contractSnapshot=0x(?P<contractSnapshot>[0-9A-Fa-f]+) "
    r"artifactSnapshot=0x(?P<artifactSnapshot>[0-9A-Fa-f]+) "
    r"planSnapshot=0x(?P<planSnapshot>[0-9A-Fa-f]+) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)
R275_SEMANTIC_RECEIPT_RE = re.compile(
    r"VR DX11 R275 translatedSemanticReceipt signature#(?P<signature>\d+): "
    r"exact=(?P<exact>[01]) objectReady=(?P<objectReady>[01]) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)

R317_RECEIPT_HEX_FIELDS = ['cacheKey','vertexVersionToken','pixelVersionToken','vertexBytecodeHash','pixelBytecodeHash','translatedVertexSemanticHash','translatedPixelSemanticHash','translatorRevisionHash','semanticContractHash','sourcePairSemanticHash','sourceConstantMappingHash','sourceSamplerMappingHash','sourceMappingPlanRevisionHash','sourceMappingSemanticContractHash','translationObjectSnapshotToken','sourceMappingHandoffSnapshotToken','translationPlanSnapshotToken']
R317_RECEIPT_BOOL_FIELDS = ['vertexSemanticExact','pixelSemanticExact','constantRegisterMappingExact','samplerMappingExact']
R317_RECEIPT_INPUT_RE = re.compile(
    r"VR DX11 R317 receiptInputs signature#(?P<signature>\\d+): ".replace(r"\\d", r"\d")
    + " ".join(
        f"{name}=0x(?P<{name}>[0-9A-Fa-f]{{1,16}})"
        for name in R317_RECEIPT_HEX_FIELDS
    )
    + " "
    + " ".join(
        f"{name}=(?P<{name}>[01])"
        for name in R317_RECEIPT_BOOL_FIELDS
    )
    + r"(?=\\s|$)".replace(r"\\s", r"\s")
)


def recompute_r275_receipt_scalar_snapshot(fields: dict) -> int:
    """Replay native R275's 64-bit scalar mix, not object ownership proof."""
    mask = (1 << 64) - 1
    token = 0xCBF29CE484222325
    for name in (*R317_RECEIPT_HEX_FIELDS, *R317_RECEIPT_BOOL_FIELDS):
        value = fields[name]
        token ^= (
            value + 0x9E3779B97F4A7C15
            + ((token << 6) & mask) + (token >> 2)
        ) & mask
        token &= mask
    token ^= (
        0x275276 + 0x9E3779B97F4A7C15
        + ((token << 6) & mask) + (token >> 2)
    ) & mask
    return (token & mask) or 1


# R316: Legacy R275 logs exact/objectReady/snapshot only. Native R275's receipt
# hash binds source bytecode, the translation object and R273/R276 inputs.
# None of those object/provenance bindings is authenticated by the R275 line.
R275_UNLOGGED_RECEIPT_BINDINGS = (
    "cacheKey", "vertexVersionToken", "pixelVersionToken",
    "vertexBytecodeHash", "pixelBytecodeHash",
    "translationObjectSnapshotToken",
    "sourceMappingHandoffSnapshotToken", "translationPlanSnapshotToken",
    "vertexSemanticExact", "pixelSemanticExact",
    "constantRegisterMappingExact", "samplerMappingExact",
)


def annotate_r275_receipt_provenance(
    receipt: dict, plan: dict | None, handoff: dict | None,
    inputs: dict | None = None, source_pair: dict | None = None
) -> None:
    """Recompute R275 scalar digest without confusing it for device ownership."""
    exact = receipt["exact"]
    snapshot = receipt["snapshot"]
    shape_valid = (
        (snapshot != 0 and receipt["object_ready"]) if exact
        else snapshot == 0
    )
    producer_correlated = bool(
        plan is not None and plan.get("summary_correlation_exact")
        and handoff is not None and handoff.get("summary_correlation_exact")
    )
    inputs_unique = bool(inputs is not None and not inputs["duplicate"])
    calculated = (
        recompute_r275_receipt_scalar_snapshot(inputs["fields"])
        if inputs_unique else None
    )
    scalar_matches = bool(
        exact and inputs_unique and calculated == snapshot
    )
    bindings_correlated = bool(
        inputs_unique and plan is not None and handoff is not None
        and source_pair is not None
        and inputs["fields"]["cacheKey"] == source_pair["cache_key"]
        and inputs["fields"]["translatedVertexSemanticHash"]
            == plan["target_vertex_semantic_hash"]
        and inputs["fields"]["translatedPixelSemanticHash"]
            == plan["target_pixel_semantic_hash"]
        and inputs["fields"]["translatorRevisionHash"]
            == plan["translator_revision_hash"]
        and inputs["fields"]["semanticContractHash"]
            == plan["semantic_contract_hash"]
        and inputs["fields"]["sourceMappingHandoffSnapshotToken"]
            == handoff["snapshot"]
        and inputs["fields"]["translationPlanSnapshotToken"]
            == plan["snapshot"]
    )
    receipt.update({
        "claim_shape_consistent": shape_valid,
        "producer_chain_correlated": producer_correlated,
        "r317_inputs_present": inputs is not None,
        "r317_inputs_unique": inputs_unique,
        "r317_scalar_snapshot_calculated": calculated,
        "r317_scalar_snapshot_matches": scalar_matches,
        "r317_logged_producer_bindings_correlated": bindings_correlated,
        "unlogged_receipt_bindings": (
            [] if inputs_unique else list(R275_UNLOGGED_RECEIPT_BINDINGS)
        ),
        # Scalar evidence never authenticates native object/device lifetime.
        "snapshot_independently_verified": False,
        "provenance_status": (
            "CONTRADICTORY_R275_TELEMETRY" if not shape_valid
            else "DUPLICATE_R317_RECEIPT_INPUTS"
            if inputs is not None and not inputs_unique
            else "R275_SCALAR_HASH_MISMATCH"
            if exact and inputs_unique and not scalar_matches
            else "R317_PRODUCER_SCALAR_MISMATCH"
            if exact and inputs_unique and not bindings_correlated
            else "UNVERIFIABLE_R275_PRODUCER_CHAIN"
            if exact and not producer_correlated
            else "R275_SCALAR_HASH_RECONSTRUCTED_OBJECT_UNVERIFIED"
            if exact and scalar_matches
            else "UNVERIFIABLE_R275_UNLOGGED_BINDINGS"
        ),
        "diagnostic_only": True,
        "activation_proof": False,
    })


R287_PRODUCTION_OBSERVATION_RE = re.compile(
    r"VR DX11 R287 productionObservation signature#(?P<signature>\d+): "
    r"exact=(?P<exact>[01]) ownerGeneration=(?P<ownerGeneration>\d+) "
    r"materializationReused=(?P<materializationReused>[01]) "
    r"objectReady=(?P<objectReady>[01]) "
    r"boundaryPreserved=(?P<boundaryPreserved>[01]) "
    r"handoffSnapshot=0x(?P<handoffSnapshot>[0-9A-Fa-f]+) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)
R291_PRODUCTION_SEMANTIC_REVIEW_RE = re.compile(
    r"VR DX11 R291 productionSemanticReview signature#(?P<signature>\d+): "
    r"admissionExact=(?P<admissionExact>[01]) "
    r"reviewExact=(?P<reviewExact>[01]) "
    r"inputLayoutReady=(?P<inputLayoutReady>[01]) "
    r"inputLayoutReused=(?P<inputLayoutReused>[01]) "
    r"semanticReady=(?P<semanticReady>[01]) "
    r"boundaryPreserved=(?P<boundaryPreserved>[01]) "
    r"admissionSnapshot=0x(?P<admissionSnapshot>[0-9A-Fa-f]+) "
    r"inputLayoutSnapshot=0x(?P<inputLayoutSnapshot>[0-9A-Fa-f]+) "
    r"semanticSnapshot=0x(?P<semanticSnapshot>[0-9A-Fa-f]+) "
    r"reviewSnapshot=0x(?P<reviewSnapshot>[0-9A-Fa-f]+)"
)
R297_PRODUCTION_SOURCE_REVALIDATION_RE = re.compile(
    r"VR DX11 R297 productionSourceRevalidation signature#(?P<signature>\d+): "
    r"drawExact=(?P<drawExact>[01]) "
    r"nativeBufferEligible=(?P<nativeBufferEligible>[01]) "
    r"r258Present=(?P<r258Present>[01]) "
    r"r258Contract=(?P<r258Contract>[01]) "
    r"kindMatch=(?P<kindMatch>[01]) "
    r"startMatch=(?P<startMatch>[01]) "
    r"countDerivable=(?P<countDerivable>[01]) "
    r"countMatch=(?P<countMatch>[01]) "
    r"elementCount=(?P<elementCount>\d+) "
    r"indexFormatKnown=(?P<indexFormatKnown>[01]) "
    r"indexFormatMatch=(?P<indexFormatMatch>[01]) "
    r"indexOffsetMatch=(?P<indexOffsetMatch>[01]) "
    r"indexFormat=(?P<indexFormat>\d+) "
    r"baseMatch=(?P<baseMatch>[01]) "
    r"minMatch=(?P<minMatch>[01]) "
    r"numMatch=(?P<numMatch>[01]) "
    r"rangeMatch=(?P<rangeMatch>[01]) "
    r"cacheMatch=(?P<cacheMatch>[01]) "
    r"joinExact=(?P<joinExact>[01]) "
    r"boundaryPreserved=(?P<boundaryPreserved>[01]) "
    r"missingEvidenceMask=0x(?P<missingEvidenceMask>[0-9A-Fa-f]+) "
    r"r258Snapshot=0x(?P<r258Snapshot>[0-9A-Fa-f]+) "
    r"joinSnapshot=0x(?P<joinSnapshot>[0-9A-Fa-f]+)"
)
R293_PRODUCTION_PREREQUISITE_RE = re.compile(
    r"VR DX11 R293 productionPrerequisiteCensus signature#(?P<signature>\d+): "
    r"sourceReceipt=(?P<sourceReceipt>[01]) "
    r"resourceReceipt=(?P<resourceReceipt>[01]) "
    r"r292Exact=(?P<r292Exact>[01]) "
    r"staticSatisfied=(?P<staticSatisfied>[01]) "
    r"boundaryPreserved=(?P<boundaryPreserved>[01]) "
    r"missingReceiptMask=0x(?P<missingReceiptMask>[0-9A-Fa-f]+) "
    r"snapshot=0x(?P<snapshot>[0-9A-Fa-f]+)"
)
DECL_RE = re.compile(
    r"VR DX11 R72 decl signature#(?P<signature>\d+) elem#(?P<element>\d+): "
    r"stream=(?P<stream>\d+) offset=(?P<offset>\d+) type=(?P<type>\d+) "
    r"method=(?P<method>\d+) usage=(?P<usage>\d+) usageIndex=(?P<usageIndex>\d+)"
)
FFP_RE = re.compile(
    r"VR DX11 R(?:72|8[12345]|160|173|194|197) ffp signature#(?P<signature>\d+) stage#(?P<stage>\d+): "
    r"color\[op=(?P<colorOp>\d+),"
    r"(?:arg0=0x(?P<colorArg0>[0-9A-Fa-f]+),)?"
    r"arg1=0x(?P<colorArg1>[0-9A-Fa-f]+),"
    r"arg2=0x(?P<colorArg2>[0-9A-Fa-f]+)\] "
    r"alpha\[op=(?P<alphaOp>\d+),"
    r"(?:arg0=0x(?P<alphaArg0>[0-9A-Fa-f]+),)?"
    r"arg1=0x(?P<alphaArg1>[0-9A-Fa-f]+),"
    r"arg2=0x(?P<alphaArg2>[0-9A-Fa-f]+)\] "
    r"(?:constant=0x(?P<stageConstant>[0-9A-Fa-f]+) )?"
    r"(?:resultArg=0x(?P<resultArg>[0-9A-Fa-f]+) )?"
    r"texCoord=0x(?P<texCoord>[0-9A-Fa-f]+) "
    r"texTransform=0x(?P<texTransform>[0-9A-Fa-f]+)"
    r"(?: sampler\[min=(?P<samplerMin>\d+),mag=(?P<samplerMag>\d+),"
    r"mip=(?P<samplerMip>\d+),u=(?P<samplerAddressU>\d+),"
    r"v=(?P<samplerAddressV>\d+)"
    r"(?:,border=0x(?P<samplerBorderColor>[0-9A-Fa-f]+))?"
    r"(?:,srgb=(?P<samplerSrgb>\d+))?\])?"
)
FFP_TEXTURE_FACTOR_RE = re.compile(
    r"VR DX11 R191 ffp texture-factor state#(?P<signature>\d+): "
    r"observed=(?P<observed>[01]) argb=0x(?P<argb>[0-9A-Fa-f]{8})"
)
TEXTURE_RE = re.compile(
    r"VR DX11 R8[345] texture signature#(?P<signature>\d+) stage#(?P<stage>\d+): "
    r"observed=(?P<observed>[01]) type=(?P<type>-?\d+) "
    r"pool=(?P<pool>-?\d+) usage=0x(?P<usage>[0-9A-Fa-f]+) "
    r"fmt=(?P<format>-?\d+) exact=(?P<exact>[01])"
    r"(?: managedShadowRequired=(?P<managedShadowRequired>[01])"
    r" managedShadowReady=(?P<managedShadowReady>[01]))?"
)
FFP_SHADER_PROTOTYPE_RE = re.compile(
    r"VR DX11 R8[45] ffp shader prototype#(?P<signature>\d+): "
    r"generated=(?P<generated>[01]) mask=0x(?P<mask>[0-9A-Fa-f]+) "
    r"hash=0x(?P<hash>[0-9A-Fa-f]+) bytes=(?P<bytes>\d+) "
    r"activeStages=(?P<activeStages>\d+)"
)
FFP_SHADER_COMPILE_RE = re.compile(
    r"VR DX11 R85 ffp shader compile#(?P<signature>\d+): "
    r"attempted=(?P<attempted>[01]) succeeded=(?P<succeeded>[01]) "
    r"hr=0x(?P<hr>[0-9A-Fa-f]+) "
    r"bytecodeHash=0x(?P<bytecodeHash>[0-9A-Fa-f]+) "
    r"bytecodeBytes=(?P<bytecodeBytes>\d+) "
    r"diagnosticsHash=0x(?P<diagnosticsHash>[0-9A-Fa-f]+) "
    r"diagnosticsBytes=(?P<diagnosticsBytes>\d+) "
    r"profile=(?P<profile>[A-Za-z0-9_]+)"
)
FFP_VERTEX_SHADER_COMPILE_RE = re.compile(
    r"VR DX11 R223 ffp vertex shader compile#(?P<signature>\d+): "
    r"attempted=(?P<attempted>[01]) succeeded=(?P<succeeded>[01]) "
    r"hr=0x(?P<hr>[0-9A-Fa-f]+) "
    r"bytecodeHash=0x(?P<bytecodeHash>[0-9A-Fa-f]+) "
    r"bytecodeBytes=(?P<bytecodeBytes>\d+) "
    r"diagnosticsHash=0x(?P<diagnosticsHash>[0-9A-Fa-f]+) "
    r"diagnosticsBytes=(?P<diagnosticsBytes>\d+) "
    r"profile=(?P<profile>[A-Za-z0-9_]+)"
)



# Detailed-demand census: keep this support table aligned with the dormant translator.
# It does not promote native draw routing; it only turns detailed stage logs into
# actionable evidence for the remaining fixed-function semantic gaps.
FFP_COLOR_SUPPORTED_OPS = frozenset({
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    18, 19, 20, 21, 24, 25, 26,
})
FFP_ALPHA_SUPPORTED_OPS = frozenset({
    2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 24, 25, 26,
})
FFP_SUPPORTED_ARGUMENT_SELECTORS = frozenset({0, 1, 2, 3, 4, 5, 6})
FFP_ARGUMENT_SELECT_MASK = 0x0F
FFP_ARGUMENT_SUPPORTED_BITS = 0x3F
FFP_RESULTARG_CURRENT = 1
FFP_SUPPORTED_RESULT_ARGS = frozenset({1, 5})  # CURRENT, TEMP

FFP_OP_NAMES = {
    1: "DISABLE",
    2: "SELECTARG1",
    3: "SELECTARG2",
    4: "MODULATE",
    5: "MODULATE2X",
    6: "MODULATE4X",
    7: "ADD",
    8: "ADDSIGNED",
    9: "ADDSIGNED2X",
    10: "SUBTRACT",
    11: "ADDSMOOTH",
    12: "BLENDDIFFUSEALPHA",
    13: "BLENDTEXTUREALPHA",
    14: "BLENDFACTORALPHA",
    15: "BLENDTEXTUREALPHAPM",
    16: "BLENDCURRENTALPHA",
    17: "PREMODULATE",
    18: "MODULATEALPHA_ADDCOLOR",
    19: "MODULATECOLOR_ADDALPHA",
    20: "MODULATEINVALPHA_ADDCOLOR",
    21: "MODULATEINVCOLOR_ADDALPHA",
    22: "BUMPENVMAP",
    23: "BUMPENVMAPLUMINANCE",
    24: "DOTPRODUCT3",
    25: "MULTIPLYADD",
    26: "LERP",
}
SignatureKey = tuple[str, int, int]


FFP_ARGUMENT_NAMES = {
    0: "DIFFUSE",
    1: "CURRENT",
    2: "TEXTURE",
    3: "TFACTOR",
    4: "SPECULAR",
    5: "TEMP",
    6: "CONSTANT",
}


def fixed_function_used_argument_fields(op: int, prefix: str) -> tuple[str, ...]:
    if op in {2, 17}:
        return (prefix + "Arg1",)
    if op == 3:
        return (prefix + "Arg2",)
    if op in {25, 26}:
        return (prefix + "Arg0", prefix + "Arg1", prefix + "Arg2")
    return (prefix + "Arg1", prefix + "Arg2")


def summarize_fixed_function_detailed_stage_demand(
    fixed_function: dict[SignatureKey, list[dict]],
    latest: dict[str, int] | None,
) -> dict:
    color_ops: Counter[int] = Counter()
    alpha_ops: Counter[int] = Counter()
    argument_selectors: Counter[int] = Counter()
    argument_values: Counter[int] = Counter()
    result_args: Counter[int] = Counter()
    unsupported_result_args: Counter[int] = Counter()
    detailed_stages = 0
    duplicate_stage_records = 0
    # R199/R225/R233: detail lines may repeat, but runtime signature ids are
    # local to one process epoch. Drop true duplicates only inside the same
    # source-log/startup-epoch namespace; never merge unrelated signature#N
    # records across sessions or accumulated process restarts.
    seen_stage_records: set[
        tuple[SignatureKey, tuple[tuple[str, int], ...]]
    ] = set()

    def inspect_arguments(stage: dict, op: int, prefix: str) -> None:
        for key in fixed_function_used_argument_fields(op, prefix):
            value = stage.get(key)
            if value is None:
                continue
            selector = value & FFP_ARGUMENT_SELECT_MASK
            unknown_bits = value & ~FFP_ARGUMENT_SUPPORTED_BITS
            if unknown_bits or selector not in FFP_SUPPORTED_ARGUMENT_SELECTORS:
                argument_values[value] += 1
                argument_selectors[selector] += 1

    for signature_key, stages in fixed_function.items():
        for stage in stages:
            stage_record = (signature_key, tuple(sorted(stage.items())))
            if stage_record in seen_stage_records:
                duplicate_stage_records += 1
                continue
            seen_stage_records.add(stage_record)

            color_op = stage.get("colorOp")
            if color_op is None or color_op == 1:
                continue
            detailed_stages += 1

            if color_op not in FFP_COLOR_SUPPORTED_OPS:
                color_ops[color_op] += 1
            else:
                inspect_arguments(stage, color_op, "color")

            alpha_op = stage.get("alphaOp")
            if alpha_op not in FFP_ALPHA_SUPPORTED_OPS:
                alpha_ops[alpha_op] += 1
            else:
                inspect_arguments(stage, alpha_op, "alpha")

            result_arg = stage.get("resultArg", FFP_RESULTARG_CURRENT)
            if result_arg != FFP_RESULTARG_CURRENT:
                result_args[result_arg] += 1
            if result_arg not in FFP_SUPPORTED_RESULT_ARGS:
                unsupported_result_args[result_arg] += 1

    def enum_counts(counter: Counter[int], names: dict[int, str]) -> list[dict]:
        return [
            {"value": value, "name": names.get(value, "UNKNOWN"), "count": count}
            for value, count in sorted(counter.items())
        ]

    unsupported_argument_values = [
        {
            "value": value,
            "value_hex": f"0x{value:08X}",
            "selector": value & FFP_ARGUMENT_SELECT_MASK,
            "selector_name": FFP_ARGUMENT_NAMES.get(
                value & FFP_ARGUMENT_SELECT_MASK, "UNKNOWN"
            ),
            "count": count,
        }
        for value, count in sorted(argument_values.items())
    ]

    has_unsupported = bool(
        color_ops or alpha_ops or argument_values or unsupported_result_args
    )
    return {
        "DetailedStages": detailed_stages,
        "DuplicateDetailedStageRecordsDropped": duplicate_stage_records,
        "UnsupportedColorOps": enum_counts(color_ops, FFP_OP_NAMES),
        "UnsupportedAlphaOps": enum_counts(alpha_ops, FFP_OP_NAMES),
        "UnsupportedArgumentSelectors": enum_counts(
            argument_selectors, FFP_ARGUMENT_NAMES
        ),
        "UnsupportedArgumentValues": unsupported_argument_values,
        "NonCurrentResultArgs": enum_counts(result_args, FFP_ARGUMENT_NAMES),
        "UnsupportedResultArgs": enum_counts(
            unsupported_result_args, FFP_ARGUMENT_NAMES
        ),
        "HasUnsupportedObservedSemantics": has_unsupported,
        "CoverageLimitedByDetailCap": bool(
            latest and latest.get("signatureDetailSkipped", 0) > 0
        ),
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }


def int_fields(match: re.Match[str]) -> dict[str, int]:
    return {
        key: int(value) if value is not None else 0
        for key, value in match.groupdict().items()
    }


def parse_signature_shader_identity(body: str) -> dict | None:
    match = SIGNATURE_SHADER_RE.search(body)
    if not match:
        return None
    data = match.groupdict()
    return {
        "introspection_complete": bool(int(data["introspection"])),
        "mixed_pair": bool(int(data["mixed"])),
        "translation_exact": bool(int(data["translationExact"])),
        "vs_present": bool(int(data["vsPresent"])),
        "vs_bytes": int(data["vsBytes"]),
        "vs_version": int(data["vsVersion"], 16),
        "vs_version_hex": "0x" + data["vsVersion"].upper(),
        "vs_hash": int(data["vsHash"], 16),
        "vs_hash_hex": "0x" + data["vsHash"].upper(),
        "ps_present": bool(int(data["psPresent"])),
        "ps_bytes": int(data["psBytes"]),
        "ps_version": int(data["psVersion"], 16),
        "ps_version_hex": "0x" + data["psVersion"].upper(),
        "ps_hash": int(data["psHash"], 16),
        "ps_hash_hex": "0x" + data["psHash"].upper(),
    }


def summarize_programmable_shader_inventory(
    signatures: dict[SignatureKey, dict],
    signature_coverage_complete: bool,
    detail_cap_saturated: bool,
) -> dict:
    pair_map: dict[tuple[int, int, int, int, int, int], dict] = {}
    identity_missing: list[dict] = []
    identity_blocking: list[dict] = []
    source_semantic_pair_missing: list[dict] = []
    source_semantic_pair_correlation_inexact: list[dict] = []
    register_mapping_plan_missing: list[dict] = []
    source_mapping_handoff_missing: list[dict] = []
    source_mapping_handoff_correlation_inexact: list[dict] = []
    register_mapping_plan_correlation_inexact: list[dict] = []
    semantic_plan_missing: list[dict] = []
    semantic_receipt_missing: list[dict] = []
    production_activation_prerequisite_missing: list[dict] = []
    production_activation_prerequisite_correlation_inexact: list[dict] = []
    production_observation_missing: list[dict] = []
    production_observation_correlation_inexact: list[dict] = []
    production_semantic_review_missing: list[dict] = []
    production_semantic_review_correlation_inexact: list[dict] = []
    production_source_revalidation_missing: list[dict] = []
    production_source_revalidation_correlation_inexact: list[dict] = []
    semantic_plan_inexact: list[dict] = []
    object_prerequisite_missing: list[dict] = []
    object_prerequisite_inexact: list[dict] = []
    object_creation_handoff_missing: list[dict] = []
    object_creation_handoff_inexact: list[dict] = []
    translated_artifact_receipt_missing: list[dict] = []
    translated_artifact_receipt_inexact: list[dict] = []
    target_materialization_contract_missing: list[dict] = []
    target_materialization_contract_inexact: list[dict] = []
    target_bytecode_materialization_missing: list[dict] = []
    target_bytecode_materialization_inexact: list[dict] = []
    r242_object_ownership_missing: list[dict] = []
    source_semantic_pair_evidence_signatures = 0
    source_semantic_pair_exact_signatures = 0
    source_semantic_pair_fail_closed_signatures = 0
    register_mapping_plan_evidence_signatures = 0
    source_mapping_handoff_evidence_signatures = 0
    source_mapping_handoff_exact_signatures = 0
    source_mapping_handoff_fail_closed_signatures = 0
    register_mapping_plan_exact_signatures = 0
    register_mapping_plan_fail_closed_signatures = 0
    semantic_plan_exact_signatures = 0
    object_prerequisite_exact_signatures = 0
    object_creation_handoff_exact_signatures = 0
    translated_artifact_receipt_exact_signatures = 0
    target_materialization_contract_exact_signatures = 0
    target_bytecode_materialization_exact_signatures = 0
    semantic_receipt_exact_signatures = 0
    production_activation_prerequisite_evidence_signatures = 0
    production_activation_prerequisite_exact_signatures = 0
    production_activation_prerequisite_fail_closed_signatures = 0
    production_observation_evidence_signatures = 0
    production_observation_exact_signatures = 0
    production_observation_fail_closed_signatures = 0
    production_semantic_review_evidence_signatures = 0
    production_semantic_review_exact_signatures = 0
    production_semantic_review_fail_closed_signatures = 0
    production_source_revalidation_evidence_signatures = 0
    production_source_revalidation_join_exact_signatures = 0
    production_source_revalidation_fail_closed_signatures = 0
    records_with_identity = 0
    programmable_signatures = 0

    for signature_key in sorted(signatures):
        signature = signatures[signature_key]
        ref = {
            "source_log": signature["source_log"],
            "startup_epoch": signature["startup_epoch"],
            "id": signature["id"],
        }
        shader = signature.get("shader_identity")
        if shader is None:
            identity_missing.append(ref)
            continue

        records_with_identity += 1
        if not shader["introspection_complete"] or shader["mixed_pair"]:
            identity_blocking.append(ref)
            continue

        if not (shader["vs_present"] and shader["ps_present"]):
            continue

        programmable_signatures += 1
        if shader["vs_bytes"] < 4 or shader["ps_bytes"] < 4:
            identity_blocking.append(ref)
            continue

        pair_key = (
            shader["vs_bytes"], shader["vs_version"], shader["vs_hash"],
            shader["ps_bytes"], shader["ps_version"], shader["ps_hash"],
        )
        pair = pair_map.setdefault(
            pair_key,
            {
                "VertexShader": {
                    "ByteSize": shader["vs_bytes"],
                    "VersionToken": shader["vs_version"],
                    "VersionTokenHex": shader["vs_version_hex"],
                    "Hash": shader["vs_hash"],
                    "HashHex": shader["vs_hash_hex"],
                },
                "PixelShader": {
                    "ByteSize": shader["ps_bytes"],
                    "VersionToken": shader["ps_version"],
                    "VersionTokenHex": shader["ps_version_hex"],
                    "Hash": shader["ps_hash"],
                    "HashHex": shader["ps_hash_hex"],
                },
                "SignatureRefs": [],
                "TranslationImplemented": False,
            },
        )
        source_semantic_pair = signature.get("source_semantic_pair")
        register_mapping_plan = signature.get("register_mapping_plan")
        source_mapping_handoff = signature.get("source_mapping_handoff")
        plan = signature.get("semantic_translation_plan")
        object_prerequisite = signature.get("translation_object_prerequisite")
        object_creation_handoff = signature.get("object_creation_handoff")
        translated_artifact_receipt = signature.get("translated_artifact_receipt")
        target_materialization_contract = signature.get(
            "target_materialization_contract"
        )
        target_bytecode_materialization = signature.get(
            "target_bytecode_materialization"
        )
        receipt = signature.get("translated_semantic_receipt")
        production_activation_prerequisite = signature.get(
            "production_activation_prerequisite"
        )
        production_observation = signature.get(
            "production_observation"
        )
        production_semantic_review = signature.get(
            "production_semantic_review"
        )
        production_source_revalidation = signature.get(
            "production_source_revalidation"
        )
        missing_prerequisite = None
        if source_semantic_pair is None:
            source_semantic_pair_missing.append(ref)
        else:
            source_semantic_pair_evidence_signatures += 1
            if not source_semantic_pair["summary_correlation_exact"]:
                source_semantic_pair_correlation_inexact.append(ref)
            if source_semantic_pair["exact"]:
                source_semantic_pair_exact_signatures += 1
            if source_semantic_pair["fail_closed"]:
                source_semantic_pair_fail_closed_signatures += 1

        if register_mapping_plan is None:
            register_mapping_plan_missing.append(ref)
        else:
            register_mapping_plan_evidence_signatures += 1
            if not register_mapping_plan["summary_correlation_exact"]:
                register_mapping_plan_correlation_inexact.append(ref)
            if register_mapping_plan["exact"]:
                register_mapping_plan_exact_signatures += 1
            if register_mapping_plan["fail_closed"]:
                register_mapping_plan_fail_closed_signatures += 1

        if source_mapping_handoff is None:
            source_mapping_handoff_missing.append(ref)
        else:
            source_mapping_handoff_evidence_signatures += 1
            if not source_mapping_handoff["summary_correlation_exact"]:
                source_mapping_handoff_correlation_inexact.append(ref)
            if source_mapping_handoff["exact"]:
                source_mapping_handoff_exact_signatures += 1
            if source_mapping_handoff["fail_closed"]:
                source_mapping_handoff_fail_closed_signatures += 1

        if plan is None:
            semantic_plan_missing.append(ref)
            missing_prerequisite = "R276_SEMANTIC_PLAN_EVIDENCE"
        elif not plan["exact"]:
            semantic_plan_inexact.append(ref)
            missing_prerequisite = "R276_SEMANTIC_PLAN_EXACTNESS"
        else:
            semantic_plan_exact_signatures += 1

        if object_prerequisite is None:
            object_prerequisite_missing.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = (
                    "R279_TRANSLATION_OBJECT_PREREQUISITE_EVIDENCE"
                )
        elif not object_prerequisite["exact"]:
            object_prerequisite_inexact.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = (
                    "R279_TRANSLATION_OBJECT_PREREQUISITE_EXACTNESS"
                )
        else:
            object_prerequisite_exact_signatures += 1

        if object_creation_handoff is None:
            object_creation_handoff_missing.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = "R280_OBJECT_CREATION_HANDOFF_EVIDENCE"
        elif (
            not object_creation_handoff["exact"]
            or object_creation_handoff["creation_authorized"]
        ):
            object_creation_handoff_inexact.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = "R280_OBJECT_CREATION_HANDOFF_EXACTNESS"
        else:
            object_creation_handoff_exact_signatures += 1

        if translated_artifact_receipt is None:
            translated_artifact_receipt_missing.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = "R281_TRANSLATED_ARTIFACT_RECEIPT_EVIDENCE"
        elif (
            not translated_artifact_receipt["exact"]
            or not translated_artifact_receipt["target_bytecode_required"]
            or translated_artifact_receipt["materialized"]
            or translated_artifact_receipt["creation_authorized"]
        ):
            translated_artifact_receipt_inexact.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = "R281_TRANSLATED_ARTIFACT_RECEIPT_EXACTNESS"
        else:
            translated_artifact_receipt_exact_signatures += 1

        if target_materialization_contract is None:
            target_materialization_contract_missing.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = "R282_TARGET_MATERIALIZATION_CONTRACT_EVIDENCE"
        elif (
            not target_materialization_contract["exact"]
            or not target_materialization_contract["target_required"]
            or target_materialization_contract["materialized"]
            or target_materialization_contract["compile_authorized"]
            or target_materialization_contract["creation_authorized"]
        ):
            target_materialization_contract_inexact.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = "R282_TARGET_MATERIALIZATION_CONTRACT_EXACTNESS"
        else:
            target_materialization_contract_exact_signatures += 1

        if target_bytecode_materialization is None:
            target_bytecode_materialization_missing.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = "R283_TARGET_BYTECODE_MATERIALIZATION"
        elif (
            not target_bytecode_materialization["exact"]
            or not target_bytecode_materialization["vertex_subset"]
            or not target_bytecode_materialization["pixel_subset"]
            or not target_bytecode_materialization["vertex_compiled"]
            or not target_bytecode_materialization["pixel_compiled"]
            or not target_bytecode_materialization["materialized"]
            or target_bytecode_materialization["creation_authorized"]
            or target_bytecode_materialization["vertex_bytecode_hash"] == 0
            or target_bytecode_materialization["pixel_bytecode_hash"] == 0
            or target_bytecode_materialization["vertex_artifact"] == 0
            or target_bytecode_materialization["pixel_artifact"] == 0
        ):
            target_bytecode_materialization_inexact.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = (
                    "R283_TARGET_BYTECODE_MATERIALIZATION_EXACTNESS"
                )
        else:
            target_bytecode_materialization_exact_signatures += 1

        if receipt is None:
            semantic_receipt_missing.append(ref)
            if missing_prerequisite is None:
                missing_prerequisite = "R275_TRANSLATED_SEMANTIC_RECEIPT"
        else:
            if receipt["exact"]:
                semantic_receipt_exact_signatures += 1
            elif (
                not receipt["object_ready"]
                and plan is not None
                and plan["exact"]
                and object_prerequisite is not None
                and object_prerequisite["exact"]
                and object_creation_handoff is not None
                and object_creation_handoff["exact"]
                and not object_creation_handoff["creation_authorized"]
                and translated_artifact_receipt is not None
                and translated_artifact_receipt["exact"]
                and translated_artifact_receipt["target_bytecode_required"]
                and not translated_artifact_receipt["materialized"]
                and not translated_artifact_receipt["creation_authorized"]
                and target_materialization_contract is not None
                and target_materialization_contract["exact"]
                and target_materialization_contract["target_required"]
                and not target_materialization_contract["materialized"]
                and not target_materialization_contract["compile_authorized"]
                and not target_materialization_contract["creation_authorized"]
                and target_bytecode_materialization is not None
                and target_bytecode_materialization["exact"]
                and target_bytecode_materialization["vertex_subset"]
                and target_bytecode_materialization["pixel_subset"]
                and target_bytecode_materialization["vertex_compiled"]
                and target_bytecode_materialization["pixel_compiled"]
                and target_bytecode_materialization["materialized"]
                and not target_bytecode_materialization["creation_authorized"]
            ):
                r242_object_ownership_missing.append(ref)
                if missing_prerequisite is None:
                    missing_prerequisite = "R242_TRANSLATED_OBJECT_OWNERSHIP"
            elif missing_prerequisite is None:
                missing_prerequisite = "R275_TRANSLATED_SEMANTIC_RECEIPT_EXACTNESS"

        if production_activation_prerequisite is None:
            production_activation_prerequisite_missing.append(ref)
        else:
            production_activation_prerequisite_evidence_signatures += 1
            if not production_activation_prerequisite["summary_correlation_exact"]:
                production_activation_prerequisite_correlation_inexact.append(ref)
            if production_activation_prerequisite["r292_exact"]:
                production_activation_prerequisite_exact_signatures += 1
            if production_activation_prerequisite["fail_closed"]:
                production_activation_prerequisite_fail_closed_signatures += 1

        if production_observation is None:
            production_observation_missing.append(ref)
        else:
            production_observation_evidence_signatures += 1
            if not production_observation["summary_correlation_exact"]:
                production_observation_correlation_inexact.append(ref)
            if production_observation["exact"]:
                production_observation_exact_signatures += 1
            if production_observation["fail_closed"]:
                production_observation_fail_closed_signatures += 1

        if production_semantic_review is None:
            production_semantic_review_missing.append(ref)
        else:
            production_semantic_review_evidence_signatures += 1
            if not production_semantic_review["summary_correlation_exact"]:
                production_semantic_review_correlation_inexact.append(ref)
            if production_semantic_review["review_exact"]:
                production_semantic_review_exact_signatures += 1
            if production_semantic_review["fail_closed"]:
                production_semantic_review_fail_closed_signatures += 1

        if production_source_revalidation is None:
            production_source_revalidation_missing.append(ref)
        else:
            production_source_revalidation_evidence_signatures += 1
            if not production_source_revalidation["summary_correlation_exact"]:
                production_source_revalidation_correlation_inexact.append(ref)
            if production_source_revalidation["join_exact"]:
                production_source_revalidation_join_exact_signatures += 1
            if production_source_revalidation["fail_closed"]:
                production_source_revalidation_fail_closed_signatures += 1

        pair["SignatureRefs"].append(ref)
        pair.setdefault("SemanticTranslationEvidence", []).append(
            {
                "SignatureRef": ref,
                "SourceSemanticPair": source_semantic_pair,
                "RegisterMappingPlan": register_mapping_plan,
                "SourceMappingHandoff": source_mapping_handoff,
                "Plan": plan,
                "ObjectOwnershipPrerequisite": object_prerequisite,
                "ObjectCreationHandoff": object_creation_handoff,
                "TranslatedArtifactReceipt": translated_artifact_receipt,
                "TargetMaterializationContract": target_materialization_contract,
                "TargetBytecodeMaterialization": target_bytecode_materialization,
                "Receipt": receipt,
                "ProductionActivationPrerequisite":
                    production_activation_prerequisite,
                "ProductionObservation": production_observation,
                "ProductionSemanticReview": production_semantic_review,
                "ProductionSourceRevalidation": production_source_revalidation,
                "MissingPrerequisite": missing_prerequisite,
                "DiagnosticOnly": True,
                "ActivationProof": False,
            }
        )

    pairs = [pair_map[key] for key in sorted(pair_map)]
    evidence_coverage_complete = bool(
        signature_coverage_complete
        and not detail_cap_saturated
        and not identity_missing
        and not identity_blocking
    )
    source_semantic_pair_evidence_coverage_complete = bool(
        evidence_coverage_complete
        and programmable_signatures > 0
        and not source_semantic_pair_missing
        and not source_semantic_pair_correlation_inexact
    )
    register_mapping_plan_evidence_coverage_complete = bool(
        evidence_coverage_complete
        and programmable_signatures > 0
        and not register_mapping_plan_missing
        and not register_mapping_plan_correlation_inexact
    )
    source_mapping_handoff_evidence_coverage_complete = bool(
        evidence_coverage_complete
        and programmable_signatures > 0
        and not source_mapping_handoff_missing
        and not source_mapping_handoff_correlation_inexact
    )
    semantic_evidence_coverage_complete = bool(
        evidence_coverage_complete
        and programmable_signatures > 0
        and not semantic_plan_missing
        and not object_prerequisite_missing
        and not object_creation_handoff_missing
        and not translated_artifact_receipt_missing
        and not target_materialization_contract_missing
        and not target_bytecode_materialization_missing
        and not semantic_receipt_missing
    )
    production_activation_evidence_coverage_complete = bool(
        evidence_coverage_complete
        and programmable_signatures > 0
        and not production_activation_prerequisite_missing
        and not production_activation_prerequisite_correlation_inexact
    )
    production_observation_evidence_coverage_complete = bool(
        evidence_coverage_complete
        and programmable_signatures > 0
        and not production_observation_missing
        and not production_observation_correlation_inexact
    )
    production_semantic_review_evidence_coverage_complete = bool(
        evidence_coverage_complete
        and programmable_signatures > 0
        and not production_semantic_review_missing
        and not production_semantic_review_correlation_inexact
    )
    production_source_revalidation_evidence_coverage_complete = bool(
        evidence_coverage_complete
        and programmable_signatures > 0
        and not production_source_revalidation_missing
        and not production_source_revalidation_correlation_inexact
    )
    return {
        "CurrentSignatureRecords": len(signatures),
        "CurrentSignatureRecordsWithShaderIdentity": records_with_identity,
        "CurrentProgrammableSignatures": programmable_signatures,
        "CurrentUniqueShaderPairs": len(pairs),
        "ShaderIdentityMissingSignatures": identity_missing,
        "ShaderIdentityBlockingSignatures": identity_blocking,
        "SourceSemanticPairEvidenceMissingSignatures":
            source_semantic_pair_missing,
        "SourceSemanticPairCorrelationInexactSignatures":
            source_semantic_pair_correlation_inexact,
        "SourceSemanticPairEvidenceSignatures":
            source_semantic_pair_evidence_signatures,
        "SourceSemanticPairExactSignatures":
            source_semantic_pair_exact_signatures,
        "SourceSemanticPairFailClosedSignatures":
            source_semantic_pair_fail_closed_signatures,
        "SourceSemanticPairEvidenceCoverageComplete":
            source_semantic_pair_evidence_coverage_complete,
        "RegisterMappingPlanEvidenceMissingSignatures":
            register_mapping_plan_missing,
        "RegisterMappingPlanCorrelationInexactSignatures":
            register_mapping_plan_correlation_inexact,
        "RegisterMappingPlanEvidenceSignatures":
            register_mapping_plan_evidence_signatures,
        "RegisterMappingPlanExactSignatures":
            register_mapping_plan_exact_signatures,
        "RegisterMappingPlanFailClosedSignatures":
            register_mapping_plan_fail_closed_signatures,
        "RegisterMappingPlanEvidenceCoverageComplete":
            register_mapping_plan_evidence_coverage_complete,
        "SourceMappingHandoffEvidenceMissingSignatures":
            source_mapping_handoff_missing,
        "SourceMappingHandoffCorrelationInexactSignatures":
            source_mapping_handoff_correlation_inexact,
        "SourceMappingHandoffEvidenceSignatures":
            source_mapping_handoff_evidence_signatures,
        "SourceMappingHandoffExactSignatures":
            source_mapping_handoff_exact_signatures,
        "SourceMappingHandoffFailClosedSignatures":
            source_mapping_handoff_fail_closed_signatures,
        "SourceMappingHandoffEvidenceCoverageComplete":
            source_mapping_handoff_evidence_coverage_complete,
        "SemanticPlanEvidenceMissingSignatures": semantic_plan_missing,
        "SemanticPlanInexactSignatures": semantic_plan_inexact,
        "ObjectOwnershipPrerequisiteEvidenceMissingSignatures":
            object_prerequisite_missing,
        "ObjectOwnershipPrerequisiteInexactSignatures":
            object_prerequisite_inexact,
        "ObjectCreationHandoffEvidenceMissingSignatures":
            object_creation_handoff_missing,
        "ObjectCreationHandoffInexactSignatures":
            object_creation_handoff_inexact,
        "TranslatedArtifactReceiptEvidenceMissingSignatures":
            translated_artifact_receipt_missing,
        "TranslatedArtifactReceiptInexactSignatures":
            translated_artifact_receipt_inexact,
        "TargetMaterializationContractEvidenceMissingSignatures":
            target_materialization_contract_missing,
        "TargetMaterializationContractInexactSignatures":
            target_materialization_contract_inexact,
        "TargetBytecodeMaterializationMissingSignatures":
            target_bytecode_materialization_missing,
        "TargetBytecodeMaterializationInexactSignatures":
            target_bytecode_materialization_inexact,
        "SemanticReceiptEvidenceMissingSignatures": semantic_receipt_missing,
        "ProductionActivationPrerequisiteEvidenceMissingSignatures":
            production_activation_prerequisite_missing,
        "ProductionActivationPrerequisiteCorrelationInexactSignatures":
            production_activation_prerequisite_correlation_inexact,
        "R242ObjectOwnershipMissingSignatures": r242_object_ownership_missing,
        "SemanticPlanExactSignatures": semantic_plan_exact_signatures,
        "ObjectOwnershipPrerequisiteExactSignatures":
            object_prerequisite_exact_signatures,
        "ObjectCreationHandoffExactSignatures":
            object_creation_handoff_exact_signatures,
        "TranslatedArtifactReceiptExactSignatures":
            translated_artifact_receipt_exact_signatures,
        "TargetMaterializationContractExactSignatures":
            target_materialization_contract_exact_signatures,
        "TargetBytecodeMaterializationExactSignatures":
            target_bytecode_materialization_exact_signatures,
        "SemanticReceiptExactSignatures": semantic_receipt_exact_signatures,
        "ProductionActivationPrerequisiteEvidenceSignatures":
            production_activation_prerequisite_evidence_signatures,
        "ProductionActivationPrerequisiteExactSignatures":
            production_activation_prerequisite_exact_signatures,
        "ProductionActivationPrerequisiteFailClosedSignatures":
            production_activation_prerequisite_fail_closed_signatures,
        "ProductionActivationEvidenceCoverageComplete":
            production_activation_evidence_coverage_complete,
        "ProductionObservationEvidenceMissingSignatures":
            production_observation_missing,
        "ProductionObservationCorrelationInexactSignatures":
            production_observation_correlation_inexact,
        "ProductionObservationEvidenceSignatures":
            production_observation_evidence_signatures,
        "ProductionObservationExactSignatures":
            production_observation_exact_signatures,
        "ProductionObservationFailClosedSignatures":
            production_observation_fail_closed_signatures,
        "ProductionObservationEvidenceCoverageComplete":
            production_observation_evidence_coverage_complete,
        "ProductionSemanticReviewEvidenceMissingSignatures":
            production_semantic_review_missing,
        "ProductionSemanticReviewCorrelationInexactSignatures":
            production_semantic_review_correlation_inexact,
        "ProductionSemanticReviewEvidenceSignatures":
            production_semantic_review_evidence_signatures,
        "ProductionSemanticReviewExactSignatures":
            production_semantic_review_exact_signatures,
        "ProductionSemanticReviewFailClosedSignatures":
            production_semantic_review_fail_closed_signatures,
        "ProductionSemanticReviewEvidenceCoverageComplete":
            production_semantic_review_evidence_coverage_complete,
        "ProductionSourceRevalidationEvidenceMissingSignatures":
            production_source_revalidation_missing,
        "ProductionSourceRevalidationCorrelationInexactSignatures":
            production_source_revalidation_correlation_inexact,
        "ProductionSourceRevalidationEvidenceSignatures":
            production_source_revalidation_evidence_signatures,
        "ProductionSourceRevalidationJoinExactSignatures":
            production_source_revalidation_join_exact_signatures,
        "ProductionSourceRevalidationFailClosedSignatures":
            production_source_revalidation_fail_closed_signatures,
        "ProductionSourceRevalidationEvidenceCoverageComplete":
            production_source_revalidation_evidence_coverage_complete,
        "SemanticEvidenceCoverageComplete": semantic_evidence_coverage_complete,
        "EvidenceLimitedBySignatureDetailCap": detail_cap_saturated,
        "EvidenceCoverageComplete": evidence_coverage_complete,
        "TranslationImplemented": False,
        "Pairs": pairs,
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    session = Path(args.session_dir)
    output = Path(args.output)
    log_files = sorted(session.glob("*.log"))

    startup: list[dict] = []
    bootstrap: list[dict] = []
    bootstrap_skipped: list[dict] = []
    bootstrap_outcomes: list[dict] = []
    summaries: list[dict] = []
    # R225/R233: runtime signature ids are insertion-order ordinals and restart
    # for every process. Scope every detail/evidence record by source log and
    # startup epoch so separate files and accumulated process restarts cannot
    # overwrite an unrelated signature#N record.
    signatures: dict[SignatureKey, dict] = {}
    source_semantic_pairs: dict[SignatureKey, dict] = {}
    pending_source_semantic_pairs: dict[tuple[str, int], dict] = {}
    register_mapping_plans: dict[SignatureKey, dict] = {}
    pending_register_mapping_plans: dict[tuple[str, int], dict] = {}
    source_mapping_handoffs: dict[SignatureKey, dict] = {}
    pending_source_mapping_handoffs: dict[tuple[str, int], dict] = {}
    semantic_translation_plans: dict[SignatureKey, dict] = {}
    translation_object_prerequisites: dict[SignatureKey, dict] = {}
    object_creation_handoffs: dict[SignatureKey, dict] = {}
    translated_artifact_receipts: dict[SignatureKey, dict] = {}
    target_materialization_contracts: dict[SignatureKey, dict] = {}
    target_bytecode_materializations: dict[SignatureKey, dict] = {}
    translated_semantic_receipts: dict[SignatureKey, dict] = {}
    translated_receipt_inputs: dict[SignatureKey, dict] = {}
    production_activation_prerequisites: dict[SignatureKey, dict] = {}
    production_observations: dict[SignatureKey, dict] = {}
    production_semantic_reviews: dict[SignatureKey, dict] = {}
    production_source_revalidations: dict[SignatureKey, dict] = {}
    declarations: dict[SignatureKey, list[dict]] = {}
    fixed_function: dict[SignatureKey, list[dict]] = {}
    fixed_function_texture_factors: dict[SignatureKey, dict] = {}
    texture_stages: dict[SignatureKey, list[dict]] = {}
    fixed_function_shader_prototypes: dict[SignatureKey, dict] = {}
    fixed_function_shader_compiles: dict[SignatureKey, dict] = {}
    fixed_function_vertex_shader_compiles: dict[SignatureKey, dict] = {}
    source_logs: list[str] = []
    latest_startup_line_by_log: dict[str, int] = {}
    latest_startup_epoch_by_log: dict[str, int] = {}
    latest_bootstrap_outcome_line_by_log: dict[str, int] = {}
    latest_summary_line_by_log: dict[str, int] = {}

    for log_path in log_files:
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if (
            "VR DX11 R7" not in text
            and "VR DX11 R80" not in text
            and "VR DX11 R81" not in text
            and "VR DX11 R82" not in text
            and "VR DX11 R83" not in text
            and "VR DX11 R84" not in text
            and "VR DX11 R85" not in text
            and "VR DX11 R114" not in text
            and "VR DX11 R120" not in text
            and "VR DX11 R191" not in text
            and "VR DX11 R194" not in text
            and "VR DX11 R197" not in text
            and "VR DX11 R223" not in text
            and "VR DX11 R271" not in text
            and "VR DX11 R287" not in text
            and "VR DX11 R291" not in text
            and "VR DX11 R293" not in text
            and "VR DX11 R297" not in text
        ):
            continue
        source_logs.append(log_path.name)
        source_log = log_path.name
        startup_epoch = 0
        latest_startup_epoch_by_log[source_log] = startup_epoch

        for line_number, line in enumerate(text.splitlines(), start=1):
            match = STARTUP_RE.search(line)
            if match:
                startup_epoch += 1
                latest_startup_epoch_by_log[source_log] = startup_epoch
                startup_entry = int_fields(match)
                startup_entry["source_log"] = source_log
                startup.append(startup_entry)
                latest_startup_line_by_log[source_log] = line_number
                continue

            match = BOOTSTRAP_RE.search(line)
            if match:
                data = match.groupdict()
                bootstrap_entry = {
                    "ready": bool(int(data["ready"])),
                    "feature_level_hex": "0x" + data["featureLevel"].upper(),
                    "selected_luid_valid": bool(int(data["selectedLuidValid"])),
                    "selected_luid": (
                        data["luidHigh"].upper() + ":" + data["luidLow"].upper()
                    ),
                }
                bootstrap_entry["source_log"] = source_log
                bootstrap.append(bootstrap_entry)
                bootstrap_outcomes.append({"kind": "probe", **bootstrap_entry})
                latest_bootstrap_outcome_line_by_log[source_log] = line_number
                continue

            match = BOOTSTRAP_SKIP_RE.search(line)
            if match:
                data = match.groupdict()
                bootstrap_skip_entry = {
                    "compatible": bool(int(data["compatible"])),
                    "adapter_luid_valid": bool(int(data["adapterLuidValid"])),
                    "source_log": source_log,
                }
                bootstrap_skipped.append(bootstrap_skip_entry)
                bootstrap_outcomes.append({"kind": "skip", **bootstrap_skip_entry})
                latest_bootstrap_outcome_line_by_log[source_log] = line_number
                continue

            match = SUMMARY_RE.search(line)
            if match:
                summary = int_fields(match)
                summary["source_log"] = source_log
                summaries.append(summary)
                latest_summary_line_by_log[source_log] = line_number
                continue

            match = R271_SOURCE_SEMANTIC_PAIR_RE.search(line)
            if match:
                # A new R271 producer invalidates any earlier R272 in this epoch.
                # Otherwise a stale mapping can attach to the next R276 signature.
                pending_register_mapping_plans.pop((source_log, startup_epoch), None)
                pending_source_mapping_handoffs.pop(
                    (source_log, startup_epoch), None
                )
                data = match.groupdict()
                pending_source_semantic_pairs[(source_log, startup_epoch)] = {
                    "exact": bool(int(data["exact"])),
                    "cache_key": int(data["cacheKey"], 16),
                    "cache_key_hex": "0x" + data["cacheKey"].upper(),
                    "pair_hash": int(data["pairHash"], 16),
                    "pair_hash_hex": "0x" + data["pairHash"].upper(),
                    "vertex_register_hash": int(data["vsRegisterHash"], 16),
                    "vertex_register_hash_hex":
                        "0x" + data["vsRegisterHash"].upper(),
                    "pixel_register_hash": int(data["psRegisterHash"], 16),
                    "pixel_register_hash_hex":
                        "0x" + data["psRegisterHash"].upper(),
                    "link_hash": int(data["linkHash"], 16),
                    "link_hash_hex": "0x" + data["linkHash"].upper(),
                    "receipt_revision_hash": int(data["receiptRevision"], 16),
                    "receipt_revision_hash_hex":
                        "0x" + data["receiptRevision"].upper(),
                    "semantic_contract_hash": int(data["contract"], 16),
                    "semantic_contract_hash_hex":
                        "0x" + data["contract"].upper(),
                }
                continue

            match = R272_REGISTER_MAPPING_PLAN_RE.search(line)
            if match:
                pending_source_mapping_handoffs.pop(
                    (source_log, startup_epoch), None
                )
                # R272 must follow a unique R271 producer before R276. Do not
                # silently replace duplicate or orphan mapping evidence.
                producer_key = (source_log, startup_epoch)
                producer_order_valid = bool(
                    producer_key in pending_source_semantic_pairs
                    and producer_key not in pending_register_mapping_plans
                )
                data = match.groupdict()
                pending_register_mapping_plans[producer_key] = {
                    "producer_order_valid": producer_order_valid,
                    "exact": bool(int(data["exact"])),
                    "constant_mapping_count": int(data["constants"]),
                    "sampler_mapping_count": int(data["samplers"]),
                    "constant_mapping_hash": int(data["constantHash"], 16),
                    "constant_mapping_hash_hex":
                        "0x" + data["constantHash"].upper(),
                    "sampler_mapping_hash": int(data["samplerHash"], 16),
                    "sampler_mapping_hash_hex":
                        "0x" + data["samplerHash"].upper(),
                    "plan_revision_hash": int(data["planRevision"], 16),
                    "plan_revision_hash_hex":
                        "0x" + data["planRevision"].upper(),
                    "semantic_contract_hash": int(data["contract"], 16),
                    "semantic_contract_hash_hex":
                        "0x" + data["contract"].upper(),
                }
                continue

            match = R273_SOURCE_MAPPING_HANDOFF_RE.search(line)
            if match:
                # R273 has no signature ordinal: only one ordered R271/R272
                # producer chain can hand off to the following R276 in this
                # log/startup epoch. Duplicate/orphan records are diagnostic.
                producer_key = (source_log, startup_epoch)
                mapping = pending_register_mapping_plans.get(producer_key)
                producer_order_valid = bool(
                    producer_key in pending_source_semantic_pairs
                    and mapping is not None
                    and mapping["producer_order_valid"]
                    and producer_key not in pending_source_mapping_handoffs
                )
                data = match.groupdict()
                pending_source_mapping_handoffs[producer_key] = {
                    "producer_order_valid": producer_order_valid,
                    "exact": bool(int(data["exact"])),
                    "snapshot": int(data["snapshot"], 16),
                    "snapshot_hex": "0x" + data["snapshot"].upper(),
                }
                continue

            match = R276_SEMANTIC_PLAN_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                semantic_translation_plans[signature_key] = {
                    "exact": bool(int(data["exact"])),
                    "snapshot": int(data["snapshot"], 16),
                    "snapshot_hex": "0x" + data["snapshot"].upper(),
                    "target_vertex_semantic_hash": int(data["targetVS"], 16),
                    "target_vertex_semantic_hash_hex": "0x" + data["targetVS"].upper(),
                    "target_pixel_semantic_hash": int(data["targetPS"], 16),
                    "target_pixel_semantic_hash_hex": "0x" + data["targetPS"].upper(),
                    "translator_revision_hash": int(data["revision"], 16),
                    "translator_revision_hash_hex": "0x" + data["revision"].upper(),
                    "semantic_contract_hash": int(data["contract"], 16),
                    "semantic_contract_hash_hex": "0x" + data["contract"].upper(),
                }
                pending_source_semantic_pair = pending_source_semantic_pairs.pop(
                    (source_log, startup_epoch), None
                )
                if pending_source_semantic_pair is not None:
                    source_semantic_pairs[signature_key] = (
                        pending_source_semantic_pair
                    )
                pending_register_mapping_plan = pending_register_mapping_plans.pop(
                    (source_log, startup_epoch), None
                )
                if pending_register_mapping_plan is not None:
                    register_mapping_plans[signature_key] = (
                        pending_register_mapping_plan
                    )
                pending_source_mapping_handoff = (
                    pending_source_mapping_handoffs.pop(
                        (source_log, startup_epoch), None
                    )
                )
                if pending_source_mapping_handoff is not None:
                    source_mapping_handoffs[signature_key] = (
                        pending_source_mapping_handoff
                    )
                continue

            match = R279_OBJECT_PREREQUISITE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                translation_object_prerequisites[signature_key] = {
                    "exact": bool(int(data["exact"])),
                    "cache_owner_generation_required":
                        bool(int(data["cacheOwnerGen"])),
                    "translation_slot_generation_required":
                        bool(int(data["slotGen"])),
                    "translation_object_receipt_generation_required":
                        bool(int(data["receiptGen"])),
                    "same_device_object_pair_required":
                        bool(int(data["sameDevicePair"])),
                    "cache_snapshot_required":
                        bool(int(data["cacheSnapshot"])),
                    "slot_snapshot_required":
                        bool(int(data["slotSnapshot"])),
                    "cache_key": int(data["cacheKey"], 16),
                    "cache_key_hex": "0x" + data["cacheKey"].upper(),
                    "translation_plan_snapshot":
                        int(data["planSnapshot"], 16),
                    "translation_plan_snapshot_hex":
                        "0x" + data["planSnapshot"].upper(),
                    "snapshot": int(data["snapshot"], 16),
                    "snapshot_hex": "0x" + data["snapshot"].upper(),
                }
                continue

            match = R280_OBJECT_CREATION_HANDOFF_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                object_creation_handoffs[signature_key] = {
                    "exact": bool(int(data["exact"])),
                    "vertex_source_exact": bool(int(data["vertexSource"])),
                    "pixel_source_exact": bool(int(data["pixelSource"])),
                    "ownership_prerequisite_matches":
                        bool(int(data["ownershipPrerequisite"])),
                    "creation_authorized":
                        bool(int(data["createAuthorized"])),
                    "cache_key": int(data["cacheKey"], 16),
                    "cache_key_hex": "0x" + data["cacheKey"].upper(),
                    "translation_plan_snapshot":
                        int(data["planSnapshot"], 16),
                    "translation_plan_snapshot_hex":
                        "0x" + data["planSnapshot"].upper(),
                    "ownership_prerequisite_snapshot":
                        int(data["ownershipSnapshot"], 16),
                    "ownership_prerequisite_snapshot_hex":
                        "0x" + data["ownershipSnapshot"].upper(),
                    "snapshot": int(data["snapshot"], 16),
                    "snapshot_hex": "0x" + data["snapshot"].upper(),
                }
                continue

            match = R281_TRANSLATED_ARTIFACT_RECEIPT_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                translated_artifact_receipts[signature_key] = {
                    "exact": bool(int(data["exact"])),
                    "target_bytecode_required": bool(int(data["targetRequired"])),
                    "materialized": bool(int(data["materialized"])),
                    "creation_authorized": bool(int(data["createAuthorized"])),
                    "cache_key": int(data["cacheKey"], 16),
                    "cache_key_hex": "0x" + data["cacheKey"].upper(),
                    "vertex_identity": int(data["vertexIdentity"], 16),
                    "vertex_identity_hex": "0x" + data["vertexIdentity"].upper(),
                    "pixel_identity": int(data["pixelIdentity"], 16),
                    "pixel_identity_hex": "0x" + data["pixelIdentity"].upper(),
                    "object_creation_handoff_snapshot":
                        int(data["handoffSnapshot"], 16),
                    "object_creation_handoff_snapshot_hex":
                        "0x" + data["handoffSnapshot"].upper(),
                    "translation_plan_snapshot": int(data["planSnapshot"], 16),
                    "translation_plan_snapshot_hex":
                        "0x" + data["planSnapshot"].upper(),
                    "snapshot": int(data["snapshot"], 16),
                    "snapshot_hex": "0x" + data["snapshot"].upper(),
                }
                continue

            match = R282_TARGET_MATERIALIZATION_CONTRACT_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                target_materialization_contracts[signature_key] = {
                    "exact": bool(int(data["exact"])),
                    "target_required": bool(int(data["targetRequired"])),
                    "materialized": bool(int(data["materialized"])),
                    "compile_authorized": bool(int(data["compileAuthorized"])),
                    "creation_authorized": bool(int(data["createAuthorized"])),
                    "cache_key": int(data["cacheKey"], 16),
                    "cache_key_hex": "0x" + data["cacheKey"].upper(),
                    "vertex_contract": int(data["vertexContract"], 16),
                    "vertex_contract_hex": "0x" + data["vertexContract"].upper(),
                    "pixel_contract": int(data["pixelContract"], 16),
                    "pixel_contract_hex": "0x" + data["pixelContract"].upper(),
                    "entry_point_hash": int(data["entry"], 16),
                    "entry_point_hash_hex": "0x" + data["entry"].upper(),
                    "vertex_profile_hash": int(data["vsProfile"], 16),
                    "vertex_profile_hash_hex": "0x" + data["vsProfile"].upper(),
                    "pixel_profile_hash": int(data["psProfile"], 16),
                    "pixel_profile_hash_hex": "0x" + data["psProfile"].upper(),
                    "compile_flags": int(data["flags"], 16),
                    "compile_flags_hex": "0x" + data["flags"].upper(),
                    "artifact_receipt_snapshot": int(data["artifactSnapshot"], 16),
                    "artifact_receipt_snapshot_hex":
                        "0x" + data["artifactSnapshot"].upper(),
                    "translation_plan_snapshot": int(data["planSnapshot"], 16),
                    "translation_plan_snapshot_hex":
                        "0x" + data["planSnapshot"].upper(),
                    "snapshot": int(data["snapshot"], 16),
                    "snapshot_hex": "0x" + data["snapshot"].upper(),
                }
                continue

            match = R283_TARGET_BYTECODE_MATERIALIZATION_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                target_bytecode_materializations[signature_key] = {
                    "exact": bool(int(data["exact"])),
                    "vertex_subset": bool(int(data["vertexSubset"])),
                    "pixel_subset": bool(int(data["pixelSubset"])),
                    "vertex_compiled": bool(int(data["vertexCompiled"])),
                    "pixel_compiled": bool(int(data["pixelCompiled"])),
                    "materialized": bool(int(data["materialized"])),
                    "creation_authorized": bool(int(data["createAuthorized"])),
                    "cache_key": int(data["cacheKey"], 16),
                    "cache_key_hex": "0x" + data["cacheKey"].upper(),
                    "vertex_source_bytes": int(data["vertexSourceBytes"]),
                    "pixel_source_bytes": int(data["pixelSourceBytes"]),
                    "vertex_source_hash": int(data["vertexSource"], 16),
                    "vertex_source_hash_hex":
                        "0x" + data["vertexSource"].upper(),
                    "pixel_source_hash": int(data["pixelSource"], 16),
                    "pixel_source_hash_hex":
                        "0x" + data["pixelSource"].upper(),
                    "vertex_bytecode_bytes": int(data["vertexBytes"]),
                    "pixel_bytecode_bytes": int(data["pixelBytes"]),
                    "vertex_bytecode_hash": int(data["vertexBytecode"], 16),
                    "vertex_bytecode_hash_hex":
                        "0x" + data["vertexBytecode"].upper(),
                    "pixel_bytecode_hash": int(data["pixelBytecode"], 16),
                    "pixel_bytecode_hash_hex":
                        "0x" + data["pixelBytecode"].upper(),
                    "vertex_artifact": int(data["vertexArtifact"], 16),
                    "vertex_artifact_hex":
                        "0x" + data["vertexArtifact"].upper(),
                    "pixel_artifact": int(data["pixelArtifact"], 16),
                    "pixel_artifact_hex":
                        "0x" + data["pixelArtifact"].upper(),
                    "target_materialization_contract_snapshot":
                        int(data["contractSnapshot"], 16),
                    "target_materialization_contract_snapshot_hex":
                        "0x" + data["contractSnapshot"].upper(),
                    "artifact_receipt_snapshot":
                        int(data["artifactSnapshot"], 16),
                    "artifact_receipt_snapshot_hex":
                        "0x" + data["artifactSnapshot"].upper(),
                    "translation_plan_snapshot": int(data["planSnapshot"], 16),
                    "translation_plan_snapshot_hex":
                        "0x" + data["planSnapshot"].upper(),
                    "snapshot": int(data["snapshot"], 16),
                    "snapshot_hex": "0x" + data["snapshot"].upper(),
                }
                continue

            match = R317_RECEIPT_INPUT_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                fields = {
                    name: int(data[name], 16)
                    for name in R317_RECEIPT_HEX_FIELDS
                }
                fields.update({
                    name: int(data[name])
                    for name in R317_RECEIPT_BOOL_FIELDS
                })
                if signature_key in translated_receipt_inputs:
                    translated_receipt_inputs[signature_key]["duplicate"] = True
                else:
                    translated_receipt_inputs[signature_key] = {
                        "fields": fields, "duplicate": False
                    }
                continue

            match = R275_SEMANTIC_RECEIPT_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                translated_semantic_receipts[signature_key] = {
                    "exact": bool(int(data["exact"])),
                    "object_ready": bool(int(data["objectReady"])),
                    "snapshot": int(data["snapshot"], 16),
                    "snapshot_hex": "0x" + data["snapshot"].upper(),
                }
                continue

            match = R287_PRODUCTION_OBSERVATION_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                exact = bool(int(data["exact"]))
                owner_generation = int(data["ownerGeneration"])
                materialization_reused = bool(
                    int(data["materializationReused"])
                )
                object_ready = bool(int(data["objectReady"]))
                boundary_preserved = bool(int(data["boundaryPreserved"]))
                handoff_snapshot = int(data["handoffSnapshot"], 16)
                snapshot = int(data["snapshot"], 16)

                snapshot_state_correlated = (
                    (snapshot != 0) == exact
                )
                exact_state_correlated = bool(
                    not exact
                    or (
                        owner_generation != 0
                        and object_ready
                        and boundary_preserved
                        and handoff_snapshot != 0
                        and snapshot != 0
                    )
                )
                boundary_state_correlated = bool(
                    not boundary_preserved or exact
                )
                reuse_state_correlated = bool(
                    not materialization_reused or object_ready
                )
                target_materialization = target_bytecode_materializations.get(
                    signature_key
                )
                target_materialization_correlated = bool(
                    not exact
                    or (
                        target_materialization is not None
                        and target_materialization["exact"]
                        and target_materialization["materialized"]
                        and not target_materialization["creation_authorized"]
                        and target_materialization["snapshot"] != 0
                    )
                )
                translated_receipt = translated_semantic_receipts.get(
                    signature_key
                )
                translated_semantic_receipt_correlated = bool(
                    not exact
                    or (
                        translated_receipt is not None
                        and translated_receipt["exact"]
                        and translated_receipt["object_ready"]
                        and translated_receipt["snapshot"] != 0
                    )
                )
                summary_correlation_exact = bool(
                    snapshot_state_correlated
                    and exact_state_correlated
                    and boundary_state_correlated
                    and reuse_state_correlated
                    and target_materialization_correlated
                    and translated_semantic_receipt_correlated
                )
                production_observations[signature_key] = {
                    "exact": exact,
                    "owner_generation": owner_generation,
                    "materialization_reused": materialization_reused,
                    "object_ready": object_ready,
                    "boundary_preserved": boundary_preserved,
                    "handoff_snapshot": handoff_snapshot,
                    "handoff_snapshot_hex":
                        f"0x{handoff_snapshot:016X}",
                    "snapshot": snapshot,
                    "snapshot_hex": f"0x{snapshot:016X}",
                    "snapshot_state_correlated":
                        snapshot_state_correlated,
                    "exact_state_correlated": exact_state_correlated,
                    "boundary_state_correlated":
                        boundary_state_correlated,
                    "reuse_state_correlated": reuse_state_correlated,
                    "target_materialization_correlated":
                        target_materialization_correlated,
                    "translated_semantic_receipt_correlated":
                        translated_semantic_receipt_correlated,
                    "summary_correlation_exact":
                        summary_correlation_exact,
                    "fail_closed": bool(
                        summary_correlation_exact
                        and (not exact or boundary_preserved)
                    ),
                    "diagnostic_only": True,
                    "activation_proof": False,
                }
                continue

            match = R291_PRODUCTION_SEMANTIC_REVIEW_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                admission_exact = bool(int(data["admissionExact"]))
                review_exact = bool(int(data["reviewExact"]))
                input_layout_ready = bool(int(data["inputLayoutReady"]))
                input_layout_reused = bool(int(data["inputLayoutReused"]))
                semantic_ready = bool(int(data["semanticReady"]))
                boundary_preserved = bool(int(data["boundaryPreserved"]))
                admission_snapshot = int(data["admissionSnapshot"], 16)
                input_layout_snapshot = int(data["inputLayoutSnapshot"], 16)
                semantic_snapshot = int(data["semanticSnapshot"], 16)
                review_snapshot = int(data["reviewSnapshot"], 16)

                admission_snapshot_correlated = (
                    (admission_snapshot != 0) == admission_exact
                )
                review_snapshot_correlated = (
                    (review_snapshot != 0) == review_exact
                )
                input_layout_reuse_correlated = (
                    not input_layout_reused or input_layout_ready
                )
                if review_exact:
                    review_state_correlated = bool(
                        admission_exact
                        and input_layout_ready
                        and semantic_ready
                        and boundary_preserved
                        and admission_snapshot != 0
                        and input_layout_snapshot != 0
                        and semantic_snapshot != 0
                        and review_snapshot != 0
                    )
                else:
                    review_state_correlated = bool(
                        not input_layout_ready
                        and not input_layout_reused
                        and not semantic_ready
                        and not boundary_preserved
                        and input_layout_snapshot == 0
                        and semantic_snapshot == 0
                        and review_snapshot == 0
                    )
                summary_correlation_exact = bool(
                    admission_snapshot_correlated
                    and review_snapshot_correlated
                    and input_layout_reuse_correlated
                    and review_state_correlated
                )
                fail_closed = bool(
                    summary_correlation_exact
                    and (
                        (not review_exact and review_snapshot == 0)
                        or (review_exact and boundary_preserved)
                    )
                )
                production_semantic_reviews[signature_key] = {
                    "admission_exact": admission_exact,
                    "review_exact": review_exact,
                    "input_layout_ready": input_layout_ready,
                    "input_layout_reused": input_layout_reused,
                    "semantic_ready": semantic_ready,
                    "boundary_preserved": boundary_preserved,
                    "admission_snapshot": admission_snapshot,
                    "admission_snapshot_hex": f"0x{admission_snapshot:016X}",
                    "input_layout_snapshot": input_layout_snapshot,
                    "input_layout_snapshot_hex":
                        f"0x{input_layout_snapshot:016X}",
                    "semantic_snapshot": semantic_snapshot,
                    "semantic_snapshot_hex": f"0x{semantic_snapshot:016X}",
                    "review_snapshot": review_snapshot,
                    "review_snapshot_hex": f"0x{review_snapshot:016X}",
                    "admission_snapshot_correlated":
                        admission_snapshot_correlated,
                    "review_snapshot_correlated":
                        review_snapshot_correlated,
                    "input_layout_reuse_correlated":
                        input_layout_reuse_correlated,
                    "review_state_correlated": review_state_correlated,
                    "summary_correlation_exact": summary_correlation_exact,
                    "fail_closed": fail_closed,
                    "diagnostic_only": True,
                    "activation_proof": False,
                }
                continue

            match = R297_PRODUCTION_SOURCE_REVALIDATION_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                draw_exact = bool(int(data["drawExact"]))
                native_buffer_eligible = bool(int(data["nativeBufferEligible"]))
                r258_present = bool(int(data["r258Present"]))
                r258_contract = bool(int(data["r258Contract"]))
                kind_match = bool(int(data["kindMatch"]))
                start_match = bool(int(data["startMatch"]))
                count_derivable = bool(int(data["countDerivable"]))
                count_match = bool(int(data["countMatch"]))
                element_count = int(data["elementCount"])
                index_format_known = bool(int(data["indexFormatKnown"]))
                index_format_match = bool(int(data["indexFormatMatch"]))
                index_offset_match = bool(int(data["indexOffsetMatch"]))
                index_format = int(data["indexFormat"])
                base_match = bool(int(data["baseMatch"]))
                min_match = bool(int(data["minMatch"]))
                num_match = bool(int(data["numMatch"]))
                range_match = bool(int(data["rangeMatch"]))
                cache_match = bool(int(data["cacheMatch"]))
                join_exact = bool(int(data["joinExact"]))
                boundary_preserved = bool(int(data["boundaryPreserved"]))
                missing_evidence_mask = int(data["missingEvidenceMask"], 16)
                r258_snapshot = int(data["r258Snapshot"], 16)
                join_snapshot = int(data["joinSnapshot"], 16)

                expected_observable_mask = (
                    (0 if draw_exact else 0x01)
                    | (0 if native_buffer_eligible else 0x02)
                    | (0 if r258_present else 0x04)
                    | (0 if count_derivable else 0x10)
                    | (0 if index_format_known else 0x20)
                )
                observable_mask_matches = (
                    (missing_evidence_mask & ~0x08)
                    == expected_observable_mask
                )
                cache_missing = bool(missing_evidence_mask & 0x08)
                join_snapshot_correlated = (
                    (join_snapshot != 0)
                    == (draw_exact and not cache_missing)
                )
                receipt_absence_fail_closed = bool(
                    r258_present
                    or (
                        not r258_contract
                        and not kind_match
                        and not start_match
                        and not count_match
                        and not index_format_match
                        and not index_offset_match
                        and not base_match
                        and not min_match
                        and not num_match
                        and not range_match
                        and not cache_match
                        and not join_exact
                        and r258_snapshot == 0
                    )
                )
                exact_join_correlated = bool(
                    not join_exact
                    or (
                        draw_exact
                        and native_buffer_eligible
                        and r258_present
                        and r258_contract
                        and kind_match
                        and start_match
                        and count_derivable
                        and count_match
                        and index_format_known
                        and index_format_match
                        and index_offset_match
                        and base_match
                        and min_match
                        and num_match
                        and range_match
                        and cache_match
                        and missing_evidence_mask == 0
                        and r258_snapshot != 0
                        and join_snapshot != 0
                        and boundary_preserved
                    )
                )
                boundary_state_correlated = bool(
                    not boundary_preserved
                    or (
                        (r258_present and join_exact)
                        or (
                            not r258_present
                            and draw_exact
                            and native_buffer_eligible
                            and count_derivable
                            and index_format_known
                            and not cache_missing
                            and join_snapshot != 0
                        )
                    )
                )
                summary_correlation_exact = bool(
                    observable_mask_matches
                    and join_snapshot_correlated
                    and receipt_absence_fail_closed
                    and exact_join_correlated
                    and boundary_state_correlated
                )
                production_source_revalidations[signature_key] = {
                    "draw_identity_exact": draw_exact,
                    "native_buffer_eligible": native_buffer_eligible,
                    "r258_receipt_present": r258_present,
                    "r258_receipt_contract_ready": r258_contract,
                    "kind_matches": kind_match,
                    "start_matches": start_match,
                    "element_count_derivable": count_derivable,
                    "element_count_matches": count_match,
                    "element_count": element_count,
                    "index_format_known": index_format_known,
                    "index_format_matches": index_format_match,
                    "index_offset_matches": index_offset_match,
                    "index_format": index_format,
                    "base_vertex_matches": base_match,
                    "min_vertex_matches": min_match,
                    "num_vertices_matches": num_match,
                    "range_matches": range_match,
                    "cache_identity_matches": cache_match,
                    "join_exact": join_exact,
                    "boundary_preserved": boundary_preserved,
                    "missing_evidence_mask": missing_evidence_mask,
                    "missing_evidence_mask_hex":
                        f"0x{missing_evidence_mask:08X}",
                    "expected_observable_missing_evidence_mask":
                        expected_observable_mask,
                    "expected_observable_missing_evidence_mask_hex":
                        f"0x{expected_observable_mask:08X}",
                    "observable_mask_matches": observable_mask_matches,
                    "cache_identity_missing": cache_missing,
                    "join_snapshot_correlated": join_snapshot_correlated,
                    "receipt_absence_fail_closed": receipt_absence_fail_closed,
                    "exact_join_correlated": exact_join_correlated,
                    "boundary_state_correlated": boundary_state_correlated,
                    "summary_correlation_exact": summary_correlation_exact,
                    "r258_snapshot": r258_snapshot,
                    "r258_snapshot_hex": f"0x{r258_snapshot:016X}",
                    "join_snapshot": join_snapshot,
                    "join_snapshot_hex": f"0x{join_snapshot:016X}",
                    "fail_closed": bool(
                        not join_exact
                        and (
                            not r258_present
                            or missing_evidence_mask != 0
                        )
                    ),
                    "diagnostic_only": True,
                    "activation_proof": False,
                }
                continue

            match = R293_PRODUCTION_PREREQUISITE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                source_receipt = bool(int(data["sourceReceipt"]))
                resource_receipt = bool(int(data["resourceReceipt"]))
                r292_exact = bool(int(data["r292Exact"]))
                static_satisfied = bool(int(data["staticSatisfied"]))
                boundary_preserved = bool(int(data["boundaryPreserved"]))
                missing_receipt_mask = int(data["missingReceiptMask"], 16)
                snapshot = int(data["snapshot"], 16)
                expected_missing_receipt_mask = (
                    (0 if source_receipt else 0x1)
                    | (0 if resource_receipt else 0x2)
                )
                receipt_mask_matches = (
                    missing_receipt_mask == expected_missing_receipt_mask
                )
                exact_state_correlated = (
                    not r292_exact
                    or (
                        source_receipt
                        and resource_receipt
                        and missing_receipt_mask == 0
                        and static_satisfied
                        and boundary_preserved
                        and snapshot != 0
                    )
                )
                static_state_correlated = (
                    not static_satisfied
                    or (r292_exact and missing_receipt_mask == 0)
                )
                snapshot_state_correlated = snapshot == 0 or r292_exact
                missing_state_fail_closed = (
                    missing_receipt_mask == 0
                    or (
                        not r292_exact
                        and not static_satisfied
                        and snapshot == 0
                    )
                )
                boundary_state_correlated = (
                    not boundary_preserved
                    or missing_receipt_mask != 0
                    or (r292_exact and static_satisfied)
                )
                summary_correlation_exact = bool(
                    receipt_mask_matches
                    and exact_state_correlated
                    and static_state_correlated
                    and snapshot_state_correlated
                    and missing_state_fail_closed
                    and boundary_state_correlated
                )
                production_activation_prerequisites[signature_key] = {
                    "source_receipt_present": source_receipt,
                    "resource_receipt_present": resource_receipt,
                    "r292_exact": r292_exact,
                    "static_prerequisites_satisfied": static_satisfied,
                    "boundary_preserved": boundary_preserved,
                    "missing_receipt_mask": missing_receipt_mask,
                    "missing_receipt_mask_hex":
                        f"0x{missing_receipt_mask:08X}",
                    "expected_missing_receipt_mask":
                        expected_missing_receipt_mask,
                    "expected_missing_receipt_mask_hex":
                        f"0x{expected_missing_receipt_mask:08X}",
                    "receipt_mask_matches": receipt_mask_matches,
                    "summary_correlation_exact": summary_correlation_exact,
                    "fail_closed": bool(
                        not r292_exact
                        and not static_satisfied
                        and snapshot == 0
                    ),
                    "snapshot": snapshot,
                    "snapshot_hex": f"0x{snapshot:016X}",
                    "diagnostic_only": True,
                    "activation_proof": False,
                }
                continue

            match = SIGNATURE_RE.search(line)
            if match:
                signature_id = int(match.group("id"))
                signature_key = (source_log, startup_epoch, signature_id)
                body = match.group("body")
                signatures.setdefault(
                    signature_key,
                    {
                        "source_log": source_log,
                        "startup_epoch": startup_epoch,
                        "id": signature_id,
                        "raw": body,
                        "shader_identity": parse_signature_shader_identity(body),
                    },
                )
                continue

            match = DECL_RE.search(line)
            if match:
                data = int_fields(match)
                signature_id = data.pop("signature")
                signature_key = (source_log, startup_epoch, signature_id)
                declarations.setdefault(signature_key, []).append(data)
                continue

            match = FFP_SHADER_COMPILE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                fixed_function_shader_compiles[signature_key] = {
                    "attempted": bool(int(data["attempted"])),
                    "succeeded": bool(int(data["succeeded"])),
                    "result": int(data["hr"], 16),
                    "result_hex": "0x" + data["hr"].upper(),
                    "bytecode_hash": int(data["bytecodeHash"], 16),
                    "bytecode_hash_hex": "0x" + data["bytecodeHash"].upper(),
                    "bytecode_bytes": int(data["bytecodeBytes"]),
                    "diagnostics_hash": int(data["diagnosticsHash"], 16),
                    "diagnostics_hash_hex": "0x" + data["diagnosticsHash"].upper(),
                    "diagnostics_bytes": int(data["diagnosticsBytes"]),
                    "profile": data["profile"],
                }
                continue

            match = FFP_VERTEX_SHADER_COMPILE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                fixed_function_vertex_shader_compiles[signature_key] = {
                    "attempted": bool(int(data["attempted"])),
                    "succeeded": bool(int(data["succeeded"])),
                    "result": int(data["hr"], 16),
                    "result_hex": "0x" + data["hr"].upper(),
                    "bytecode_hash": int(data["bytecodeHash"], 16),
                    "bytecode_hash_hex": "0x" + data["bytecodeHash"].upper(),
                    "bytecode_bytes": int(data["bytecodeBytes"]),
                    "diagnostics_hash": int(data["diagnosticsHash"], 16),
                    "diagnostics_hash_hex": "0x" + data["diagnosticsHash"].upper(),
                    "diagnostics_bytes": int(data["diagnosticsBytes"]),
                    "profile": data["profile"],
                }
                continue

            match = FFP_SHADER_PROTOTYPE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                fixed_function_shader_prototypes[signature_key] = {
                    "generated": bool(int(data["generated"])),
                    "unsupported_mask": int(data["mask"], 16),
                    "unsupported_mask_hex": "0x" + data["mask"].upper(),
                    "source_hash": int(data["hash"], 16),
                    "source_hash_hex": "0x" + data["hash"].upper(),
                    "bytes": int(data["bytes"]),
                    "active_stages": int(data["activeStages"]),
                }
                continue

            match = FFP_TEXTURE_FACTOR_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data["signature"])
                signature_key = (source_log, startup_epoch, signature_id)
                fixed_function_texture_factors[signature_key] = {
                    "observed": bool(int(data["observed"])),
                    "argb": int(data["argb"], 16),
                    "argb_hex": "0x" + data["argb"].upper(),
                }
                continue

            match = TEXTURE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                stage = int(data.pop("stage"))
                parsed = {"stage": stage}
                for key, value in data.items():
                    if value is None:
                        continue
                    if key == "usage":
                        parsed[key] = int(value, 16)
                        parsed[key + "_hex"] = "0x" + value.upper()
                    else:
                        parsed[key] = int(value)
                texture_stages.setdefault(signature_key, []).append(parsed)
                continue

            match = FFP_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, startup_epoch, signature_id)
                stage = int(data.pop("stage"))
                parsed = {"stage": stage}
                for key, value in data.items():
                    if value is None:
                        continue
                    if key in {"colorArg0", "colorArg1", "colorArg2",
                               "alphaArg0", "alphaArg1", "alphaArg2",
                               "stageConstant", "texCoord", "texTransform",
                               "samplerBorderColor"}:
                        parsed[key] = int(value, 16)
                        parsed[key + "_hex"] = "0x" + value.upper()
                    else:
                        parsed[key] = int(value)
                fixed_function.setdefault(signature_key, []).append(parsed)

    for signature_key, signature in signatures.items():
        source_semantic_pair = source_semantic_pairs.get(signature_key)
        if source_semantic_pair is not None:
            semantic_plan = semantic_translation_plans.get(signature_key)
            object_prerequisite = translation_object_prerequisites.get(
                signature_key
            )
            exact_state_correlated = bool(
                not source_semantic_pair["exact"]
                or (
                    source_semantic_pair["cache_key"] != 0
                    and source_semantic_pair["pair_hash"] != 0
                    and source_semantic_pair["vertex_register_hash"] != 0
                    and source_semantic_pair["pixel_register_hash"] != 0
                    and source_semantic_pair["link_hash"] != 0
                    and source_semantic_pair["receipt_revision_hash"] != 0
                    and source_semantic_pair["semantic_contract_hash"] != 0
                )
            )
            semantic_plan_correlated = bool(
                not source_semantic_pair["exact"]
                or (
                    semantic_plan is not None
                    and semantic_plan["exact"]
                    and semantic_plan["snapshot"] != 0
                )
            )
            object_prerequisite_correlated = bool(
                not source_semantic_pair["exact"]
                or (
                    object_prerequisite is not None
                    and object_prerequisite["exact"]
                    and object_prerequisite["cache_key"]
                        == source_semantic_pair["cache_key"]
                    and semantic_plan is not None
                    and object_prerequisite["translation_plan_snapshot"]
                        == semantic_plan["snapshot"]
                )
            )
            summary_correlation_exact = bool(
                exact_state_correlated
                and semantic_plan_correlated
                and object_prerequisite_correlated
            )
            source_semantic_pair.update({
                "exact_state_correlated": exact_state_correlated,
                "semantic_plan_correlated": semantic_plan_correlated,
                "object_prerequisite_correlated":
                    object_prerequisite_correlated,
                "summary_correlation_exact": summary_correlation_exact,
                "fail_closed": bool(
                    summary_correlation_exact
                    and source_semantic_pair["exact"]
                ),
                "diagnostic_only": True,
                "activation_proof": False,
            })
        signature["source_semantic_pair"] = source_semantic_pair
        register_mapping_plan = register_mapping_plans.get(signature_key)
        if register_mapping_plan is not None:
            semantic_plan = semantic_translation_plans.get(signature_key)
            mapping_identity_present = bool(
                register_mapping_plan["constant_mapping_hash"] != 0
                and register_mapping_plan["sampler_mapping_hash"] != 0
                and register_mapping_plan["plan_revision_hash"] != 0
                and register_mapping_plan["semantic_contract_hash"] != 0
            )
            exact_state_correlated = bool(
                not register_mapping_plan["exact"]
                or (
                    mapping_identity_present
                    and register_mapping_plan["producer_order_valid"]
                )
            )
            source_semantic_pair_correlated = bool(
                not register_mapping_plan["exact"]
                or (
                    source_semantic_pair is not None
                    and source_semantic_pair["exact"]
                    and source_semantic_pair["exact_state_correlated"]
                )
            )
            semantic_plan_correlated = bool(
                not register_mapping_plan["exact"]
                or (
                    semantic_plan is not None
                    and semantic_plan["exact"]
                    and semantic_plan["snapshot"] != 0
                )
            )
            summary_correlation_exact = bool(
                exact_state_correlated
                and source_semantic_pair_correlated
                and semantic_plan_correlated
            )
            register_mapping_plan.update({
                "mapping_identity_present": mapping_identity_present,
                "exact_state_correlated": exact_state_correlated,
                "source_semantic_pair_correlated":
                    source_semantic_pair_correlated,
                "semantic_plan_correlated": semantic_plan_correlated,
                "summary_correlation_exact": summary_correlation_exact,
                "fail_closed": bool(
                    summary_correlation_exact
                    and register_mapping_plan["exact"]
                ),
                "diagnostic_only": True,
                "activation_proof": False,
            })
        signature["register_mapping_plan"] = register_mapping_plan
        source_mapping_handoff = source_mapping_handoffs.get(signature_key)
        if source_mapping_handoff is not None:
            semantic_plan = semantic_translation_plans.get(signature_key)
            source_pair_correlated = bool(
                source_semantic_pair is not None
                and source_semantic_pair["exact"]
                and source_semantic_pair["exact_state_correlated"]
            )
            mapping_correlated = bool(
                register_mapping_plan is not None
                and register_mapping_plan["exact"]
                and register_mapping_plan["summary_correlation_exact"]
            )
            semantic_plan_correlated = bool(
                semantic_plan is not None
                and semantic_plan["exact"]
                and semantic_plan["snapshot"] != 0
            )
            expected_snapshot = (
                recompute_r273_handoff_snapshot(
                    source_semantic_pair, register_mapping_plan
                )
                if source_semantic_pair is not None
                and register_mapping_plan is not None
                else 0
            )
            snapshot_matches_producer = bool(
                source_mapping_handoff["exact"]
                and expected_snapshot != 0
                and source_mapping_handoff["snapshot"] == expected_snapshot
            )
            summary_correlation_exact = bool(
                source_mapping_handoff["producer_order_valid"]
                and snapshot_matches_producer
                and source_pair_correlated
                and mapping_correlated
                and semantic_plan_correlated
            )
            # Reconstruct R273 from logged R271/R272 fields using the
            # native uint64 mixer; no downstream R276 hash is assumed.
            source_mapping_handoff.update({
                "expected_snapshot": expected_snapshot,
                "expected_snapshot_hex": f"0x{expected_snapshot:016X}",
                "snapshot_matches_producer": snapshot_matches_producer,
                "source_semantic_pair_correlated": source_pair_correlated,
                "register_mapping_plan_correlated": mapping_correlated,
                "semantic_plan_correlated": semantic_plan_correlated,
                "summary_correlation_exact": summary_correlation_exact,
                "fail_closed": bool(
                    summary_correlation_exact
                    and source_mapping_handoff["exact"]
                ),
                "identity_link_strength": (
                    "EXACT_RECONSTRUCTED_R273_SNAPSHOT"
                    if snapshot_matches_producer
                    else "MISMATCH_OR_MISSING_PRODUCER"
                ),
                "diagnostic_only": True,
                "activation_proof": False,
            })
        signature["source_mapping_handoff"] = source_mapping_handoff
        # R315: R276's emitted "exact=1" bit and nonzero token cannot
        # authenticate themselves. Independently reconstruct all R276 scalar
        # identities from the ordered R271/R272/R273 producer chain and native
        # revision/contract literals; preserve R275/object ownership as a
        # separate fail-closed requirement.
        semantic_plan = semantic_translation_plans.get(signature_key)
        if semantic_plan is not None:
            expected = (
                recompute_r276_semantic_plan(
                    source_semantic_pair,
                    register_mapping_plan,
                    source_mapping_handoff["expected_snapshot"],
                )
                if source_semantic_pair is not None
                and register_mapping_plan is not None
                and source_mapping_handoff is not None
                else None
            )
            identities_match = bool(
                expected is not None
                and all(
                    semantic_plan[key] == expected[key]
                    for key in (
                        "target_vertex_semantic_hash",
                        "target_pixel_semantic_hash",
                        "translator_revision_hash",
                        "semantic_contract_hash",
                        "snapshot",
                    )
                )
            )
            producer_chain_exact = bool(
                source_mapping_handoff is not None
                and source_mapping_handoff["fail_closed"]
                and source_semantic_pair is not None
                and source_semantic_pair["exact"]
                and register_mapping_plan is not None
                and register_mapping_plan["exact"]
            )
            semantic_plan.update({
                "expected_target_vertex_semantic_hash": (
                    expected["target_vertex_semantic_hash"] if expected else 0
                ),
                "expected_target_pixel_semantic_hash": (
                    expected["target_pixel_semantic_hash"] if expected else 0
                ),
                "expected_translator_revision_hash": (
                    expected["translator_revision_hash"] if expected else 0
                ),
                "expected_semantic_contract_hash": (
                    expected["semantic_contract_hash"] if expected else 0
                ),
                "expected_snapshot": expected["snapshot"] if expected else 0,
                "producer_chain_exact": producer_chain_exact,
                "scalar_identity_matches_producer": identities_match,
                "summary_correlation_exact": bool(
                    semantic_plan["exact"] and producer_chain_exact
                    and identities_match
                ),
                "diagnostic_only": True,
                "activation_proof": False,
            })
            semantic_plan["fail_closed"] = (
                semantic_plan["summary_correlation_exact"]
            )
        signature["semantic_translation_plan"] = semantic_plan
        signature["translation_object_prerequisite"] = (
            translation_object_prerequisites.get(signature_key)
        )
        signature["object_creation_handoff"] = (
            object_creation_handoffs.get(signature_key)
        )
        signature["translated_artifact_receipt"] = (
            translated_artifact_receipts.get(signature_key)
        )
        signature["target_materialization_contract"] = (
            target_materialization_contracts.get(signature_key)
        )
        signature["target_bytecode_materialization"] = (
            target_bytecode_materializations.get(signature_key)
        )
        # R316: an R275 exact=1 claim alone cannot prove its hash/object tuple.
        translated_semantic_receipt = translated_semantic_receipts.get(
            signature_key
        )
        if translated_semantic_receipt is not None:
            annotate_r275_receipt_provenance(
                translated_semantic_receipt, semantic_plan, source_mapping_handoff,
                translated_receipt_inputs.get(signature_key),
                source_semantic_pair,
            )
        signature["translated_semantic_receipt"] = translated_semantic_receipt
        signature["production_activation_prerequisite"] = (
            production_activation_prerequisites.get(signature_key)
        )
        signature["production_observation"] = (
            production_observations.get(signature_key)
        )
        signature["production_semantic_review"] = (
            production_semantic_reviews.get(signature_key)
        )
        signature["production_source_revalidation"] = (
            production_source_revalidations.get(signature_key)
        )
        signature["declaration"] = sorted(
            declarations.get(signature_key, []), key=lambda item: item["element"]
        )
        signature["fixed_function_stages"] = sorted(
            fixed_function.get(signature_key, []), key=lambda item: item["stage"]
        )
        signature["fixed_function_texture_factor"] = (
            fixed_function_texture_factors.get(signature_key)
        )
        signature["texture_stages"] = sorted(
            texture_stages.get(signature_key, []), key=lambda item: item["stage"]
        )
        signature["fixed_function_shader_prototype"] = (
            fixed_function_shader_prototypes.get(signature_key)
        )
        signature["fixed_function_shader_compile"] = (
            fixed_function_shader_compiles.get(signature_key)
        )
        signature["fixed_function_vertex_shader_compile"] = (
            fixed_function_vertex_shader_compiles.get(signature_key)
        )

    # R234: R233 prevents signature-id collisions across accumulated process
    # epochs, but historical signatures must not be presented as current
    # activation evidence. Preserve full history while deriving a current view
    # from the latest startup epoch in each source log. Legacy logs without an
    # R71 startup marker remain in epoch 0 and therefore remain current.
    current_signatures = {
        signature_key: signature
        for signature_key, signature in signatures.items()
        if signature_key[1] == latest_startup_epoch_by_log.get(signature_key[0], 0)
    }
    current_signatures_by_log = {
        source_log: [
            current_signatures[signature_key]
            for signature_key in sorted(current_signatures)
            if signature_key[0] == source_log
        ]
        for source_log in source_logs
    }
    current_fixed_function = {
        signature_key: stages
        for signature_key, stages in fixed_function.items()
        if signature_key[1] == latest_startup_epoch_by_log.get(signature_key[0], 0)
    }

    latest_summaries_by_log: dict[str, dict] = {}
    for summary in summaries:
        latest_summaries_by_log[summary["source_log"]] = summary
    latest_summaries = [
        latest_summaries_by_log[source_log]
        for source_log in source_logs
        if source_log in latest_summaries_by_log
    ]
    all_source_logs_have_periodic_summary = bool(source_logs) and (
        len(latest_summaries) == len(source_logs)
    )
    all_source_logs_have_summary = all_source_logs_have_periodic_summary
    latest = latest_summaries[-1] if latest_summaries else None

    # R228: R227 made startup/bootstrap entries attributable, but callers still
    # had to scan global lists to detect missing or repeated per-session evidence.
    # Preserve the latest record for each source log and expose completeness
    # explicitly. This remains diagnostic evidence only; native activation stays
    # fail-closed behind its independent gates.
    latest_startup_by_log: dict[str, dict] = {}
    for entry in startup:
        latest_startup_by_log[entry["source_log"]] = entry
    latest_bootstrap_by_log: dict[str, dict] = {}
    for entry in bootstrap:
        latest_bootstrap_by_log[entry["source_log"]] = entry
    # R229: a bootstrap skip is an explicit fail-closed runtime outcome, not
    # missing/truncated evidence. Preserve it separately so multi-log reports
    # can distinguish "probe skipped" from "no bootstrap outcome observed".
    latest_bootstrap_skip_by_log: dict[str, dict] = {}
    for entry in bootstrap_skipped:
        latest_bootstrap_skip_by_log[entry["source_log"]] = entry
    # R230: a source log may append multiple process sessions. Preserve the
    # interleaved probe/skip order so stale earlier evidence cannot masquerade
    # as the current outcome for that log. Historical per-kind maps remain
    # available for provenance, while LatestBootstrapOutcomeByLog is the
    # authoritative diagnostic view of the most recent observed outcome.
    latest_bootstrap_outcome_by_log: dict[str, dict] = {}
    for entry in bootstrap_outcomes:
        latest_bootstrap_outcome_by_log[entry["source_log"]] = entry
    latest_bootstrap_probe_logs = {
        source_log
        for source_log, entry in latest_bootstrap_outcome_by_log.items()
        if entry["kind"] == "probe"
    }
    latest_bootstrap_skip_logs = {
        source_log
        for source_log, entry in latest_bootstrap_outcome_by_log.items()
        if entry["kind"] == "skip"
    }
    bootstrap_outcome_history_conflict_logs = sorted(
        set(latest_bootstrap_by_log) & set(latest_bootstrap_skip_by_log)
    )
    bootstrap_outcome_logs = set(latest_bootstrap_outcome_by_log)
    # R231: R230 orders bootstrap outcomes, but an accumulated source log can
    # append a newer startup after an older outcome. Only an outcome observed
    # after the latest startup belongs to the current startup epoch.
    latest_startup_bootstrap_outcome_by_log = {
        source_log: latest_bootstrap_outcome_by_log[source_log]
        for source_log in source_logs
        if source_log in latest_startup_line_by_log
        and source_log in latest_bootstrap_outcome_line_by_log
        and latest_bootstrap_outcome_line_by_log[source_log]
        > latest_startup_line_by_log[source_log]
    }
    latest_startup_missing_bootstrap_outcome_logs = sorted(
        set(latest_startup_by_log) - set(latest_startup_bootstrap_outcome_by_log)
    )
    all_source_logs_latest_startup_has_bootstrap_outcome = bool(source_logs) and (
        len(latest_startup_bootstrap_outcome_by_log) == len(source_logs)
    )
    # R232: R226 isolates the latest periodic summary per source log, but an
    # accumulated log may append a newer startup after that summary. Preserve
    # historical LatestSummariesByLog for provenance while excluding a summary
    # that predates the latest startup from current exactness aggregation.
    latest_startup_summary_by_log = {
        source_log: latest_summaries_by_log[source_log]
        for source_log in source_logs
        if source_log in latest_startup_line_by_log
        and source_log in latest_summary_line_by_log
        and latest_summary_line_by_log[source_log] > latest_startup_line_by_log[source_log]
    }
    latest_startup_missing_summary_logs = sorted(
        set(latest_startup_by_log) - set(latest_startup_summary_by_log)
    )
    all_logs_with_startup_have_latest_summary = (
        len(latest_startup_summary_by_log) == len(latest_startup_by_log)
    )
    current_summaries_by_log = {
        source_log: latest_summaries_by_log[source_log]
        for source_log in source_logs
        if source_log in latest_summaries_by_log
        and (
            source_log not in latest_startup_line_by_log
            or (
                source_log in latest_summary_line_by_log
                and latest_summary_line_by_log[source_log]
                > latest_startup_line_by_log[source_log]
            )
        )
    }
    current_summary_missing_logs = sorted(
        set(source_logs) - set(current_summaries_by_log)
    )
    latest_summaries = [
        current_summaries_by_log[source_log]
        for source_log in source_logs
        if source_log in current_summaries_by_log
    ]
    all_source_logs_have_summary = bool(source_logs) and (
        len(latest_summaries) == len(source_logs)
    )
    latest = latest_summaries[-1] if latest_summaries else None

    # R235/R236: reconcile the current startup's emitted signature headers
    # with the current periodic summary. A detail-cap skip is explicit evidence,
    # while a silently missing header is not. R236 additionally separates
    # count-accounting completeness from hash-universe coverage: once the
    # signature hash cap is hit, the reported unique-signature count can still
    # reconcile exactly even though further unique signatures are suppressed.
    current_signature_evidence_by_log: dict[str, dict] = {}
    for source_log in source_logs:
        summary = current_summaries_by_log.get(source_log)
        if summary is None:
            continue
        expected = int(summary.get("signatures", 0))
        captured = len(current_signatures_by_log.get(source_log, []))
        detail_skipped = int(summary.get("signatureDetailSkipped", 0))
        hash_cap_hit_samples = int(summary.get("signatureHashCapHitSamples", 0))
        accounted = captured + detail_skipped
        accounted_complete = accounted == expected
        coverage_complete = accounted_complete and hash_cap_hit_samples == 0
        current_signature_evidence_by_log[source_log] = {
            "ExpectedSignatures": expected,
            "CapturedSignatures": captured,
            "DetailSkippedSignatures": detail_skipped,
            "AccountedSignatures": accounted,
            "HashCapHitSamples": hash_cap_hit_samples,
            "HashCapSaturated": hash_cap_hit_samples > 0,
            "AccountedComplete": accounted_complete,
            "CoverageComplete": coverage_complete,
            "Complete": accounted_complete,
        }
    current_signature_evidence_missing_logs = sorted(
        source_log
        for source_log, evidence in current_signature_evidence_by_log.items()
        if evidence["AccountedSignatures"] < evidence["ExpectedSignatures"]
    )
    current_signature_evidence_overcount_logs = sorted(
        source_log
        for source_log, evidence in current_signature_evidence_by_log.items()
        if evidence["AccountedSignatures"] > evidence["ExpectedSignatures"]
    )
    current_signature_hash_cap_saturated_logs = sorted(
        source_log
        for source_log, evidence in current_signature_evidence_by_log.items()
        if evidence["HashCapSaturated"]
    )
    all_current_signature_evidence_accounted = bool(source_logs) and (
        all_source_logs_have_summary
        and len(current_signature_evidence_by_log) == len(source_logs)
        and not current_signature_evidence_missing_logs
        and not current_signature_evidence_overcount_logs
    )
    all_current_signature_evidence_coverage_complete = bool(
        all_current_signature_evidence_accounted
        and not current_signature_hash_cap_saturated_logs
    )

    # R238: the detailed signature log already carries stable D3D9 VS/PS
    # bytecode identity. Extract a pair inventory for the dominant programmable
    # path without adding new draw-time instrumentation. Pair coverage is more
    # strict than signature count accounting: any detailed-signature cap, hash
    # cap, missing shader block, failed introspection or mixed pair keeps the
    # inventory explicitly incomplete. This is translation input only.
    programmable_shader_inventory = summarize_programmable_shader_inventory(
        current_signatures,
        all_current_signature_evidence_coverage_complete,
        any(
            summary.get("signatureDetailSkipped", 0) > 0
            for summary in latest_summaries
        ),
    )

    all_source_logs_have_startup = bool(source_logs) and (
        len(latest_startup_by_log) == len(source_logs)
    )
    all_source_logs_have_bootstrap = bool(source_logs) and (
        len(latest_bootstrap_by_log) == len(source_logs)
    )
    all_source_logs_have_bootstrap_outcome = bool(source_logs) and (
        len(bootstrap_outcome_logs) == len(source_logs)
    )
    all_source_logs_latest_bootstrap_outcome_is_probe = bool(source_logs) and (
        len(latest_bootstrap_probe_logs) == len(source_logs)
    )
    startup_bootstrap_coverage = {
        "SourceLogs": len(source_logs),
        "LogsWithStartup": len(latest_startup_by_log),
        "LogsWithBootstrap": len(latest_bootstrap_by_log),
        "LogsWithBootstrapSkip": len(latest_bootstrap_skip_by_log),
        "LogsWithBootstrapOutcome": len(bootstrap_outcome_logs),
        "LogsWithLatestStartupBootstrapOutcome": len(
            latest_startup_bootstrap_outcome_by_log
        ),
        "LatestStartupMissingBootstrapOutcomeLogs": (
            latest_startup_missing_bootstrap_outcome_logs
        ),
        "LogsWithLatestBootstrapProbe": len(latest_bootstrap_probe_logs),
        "LogsWithLatestBootstrapSkip": len(latest_bootstrap_skip_logs),
        "LogsWithBootstrapOutcomeHistoryConflict": len(
            bootstrap_outcome_history_conflict_logs
        ),
        "BootstrapOutcomeHistoryConflictLogs": bootstrap_outcome_history_conflict_logs,
        "AllSourceLogsHaveStartup": all_source_logs_have_startup,
        "AllSourceLogsHaveBootstrap": all_source_logs_have_bootstrap,
        "AllSourceLogsHaveBootstrapOutcome": all_source_logs_have_bootstrap_outcome,
        "AllSourceLogsLatestStartupHasBootstrapOutcome": (
            all_source_logs_latest_startup_has_bootstrap_outcome
        ),
        "AllSourceLogsLatestBootstrapOutcomeIsProbe": (
            all_source_logs_latest_bootstrap_outcome_is_probe
        ),
        "AllSourceLogsHaveStartupAndBootstrap": bool(
            all_source_logs_have_startup and all_source_logs_have_bootstrap
        ),
        "AllSourceLogsHaveStartupAndBootstrapOutcome": bool(
            all_source_logs_have_startup and all_source_logs_have_bootstrap_outcome
        ),
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }

    unsupported_total = None
    unsupported_keys: list[str] = []
    if latest_summaries:
        unsupported_keys = [
            "topologyUnsupported",
            "pointRasterUnsupported",
            "lineRasterUnsupported",
            "introspectionFailure",
            "behaviorUnsupported",
            "mutationTelemetryRequired",
            "managedShadowRequired",
            "mutationPlanUnsupported",
            "mutationPlanManagedShadow",
            "textureMutationDescriptorFailures",
            "inputLayoutUnsupported",
            "inputLayoutFvfPending",
            "shaderIntrospectionFailure",
            "shaderMixedPair",
            "shaderFixedFunctionPending",
            "shaderProgrammablePending",
            "fixedFunctionQueryFailure",
            "fixedFunctionReadinessPending",
            "fixedFunctionShaderCompileFailed",
            "indexUnsupported",
            "textureUnsupported",
            "colorUnsupported",
            "depthUnsupported",
            "auxRenderTargetUnsupported",
            "incomplete",
            "wbuffer",
            "sepAlpha",
            "alphaTest",
            "stencil",
            "fog",
            "lighting",
            "srgb",
            "fill",
            "blend",
            "depthCmp",
            "cull",
            "dualSource",
            "shadeMode",
            "clipping",
            "depthBias",
            "vertexBlend",
            "dither",
            "texCoordWrap",
            "mrtColorWrite",
            "specular",
        ]
        unsupported_total = sum(
            int(summary.get(key, 0))
            for summary in latest_summaries
            for key in unsupported_keys
        )

    def sum_latest(key: str) -> int:
        return sum(int(summary.get(key, 0)) for summary in latest_summaries)

    def shared_latest(key: str) -> int:
        values = {int(summary.get(key, 0)) for summary in latest_summaries}
        return next(iter(values)) if len(values) == 1 else 0

    def summary_unsupported_total(summary: dict) -> int:
        return sum(int(summary.get(key, 0)) for key in unsupported_keys)

    def summary_is_exhaustive(summary: dict) -> bool:
        return bool(
            summary["samplingScheme"] == 2
            and summary["samplingStride"] == 1
            and summary["samplingDrawsSeen"] > 0
            and summary["samples"] == summary["samplingDrawsSeen"]
        )

    exhaustive_draw_coverage = bool(
        all_source_logs_have_summary
        and all(summary_is_exhaustive(summary) for summary in latest_summaries)
    )
    latest_summary_exact = bool(
        latest and latest["exact"] == latest["samples"]
    )
    all_sampled_exact = bool(
        all_source_logs_have_summary
        and latest_summary_exact
        and all(
            summary["samples"] > 0
            and summary["exact"] == summary["samples"]
            and summary_unsupported_total(summary) == 0
            for summary in latest_summaries
        )
    )

    sampled_exactness = {
        "Samples": sum_latest("samples"),
        "ExactSamples": sum_latest("exact"),
        "UnsupportedTotal": unsupported_total,
        "AllSampledExact": all_sampled_exact,
        "DiagnosticOnly": True,
        "ExhaustiveDrawCoverage": exhaustive_draw_coverage,
        "ActivationProof": False,
    }

    sampling_scheme_ids = {
        int(summary.get("samplingScheme", 0)) for summary in latest_summaries
    }
    sampling_scheme_id = shared_latest("samplingScheme")
    sampling_scheme = (
        "MIXED"
        if len(sampling_scheme_ids) > 1
        else (
            "EXHAUSTIVE_V1"
            if sampling_scheme_id == 2
            else (
                "HASHED_ORDINAL_V1"
                if sampling_scheme_id == 1
                else "LEGACY_OR_UNSPECIFIED"
            )
        )
    )
    sampling_coverage = {
        "DrawsSeen": sum_latest("samplingDrawsSeen"),
        "Samples": sum_latest("samples"),
        "Stride": shared_latest("samplingStride"),
        "SchemeId": sampling_scheme_id,
        "Scheme": sampling_scheme,
        "SignatureHashCap": shared_latest("signatureHashCap"),
        "SignatureHashCapHitSamples": sum_latest("signatureHashCapHitSamples"),
        "DetailedSignatureLogCap": shared_latest("signatureDetailCap"),
        "DetailedSignatureLogSkippedSignatures": sum_latest("signatureDetailSkipped"),
        "SignatureHashCapSaturated": any(
            summary.get("signatureHashCapHitSamples", 0) > 0
            for summary in latest_summaries
        ),
        "DetailedSignatureLogCapSaturated": any(
            summary.get("signatureDetailSkipped", 0) > 0
            for summary in latest_summaries
        ),
        "ShaderCompileSkippedSignatureCap": sum_latest(
            "fixedFunctionShaderCompileSkippedCap"
        ),
        "ShaderCompileCoverageComplete": bool(
            all_source_logs_have_summary
            and all(
                summary.get("fixedFunctionShaderCompileSkippedCap", 0) == 0
                for summary in latest_summaries
            )
        ),
        "NonExhaustive": not exhaustive_draw_coverage,
        "ExhaustiveDrawCoverage": exhaustive_draw_coverage,
        "ActivationProof": False,
    }

    summary_coverage = {
        "SourceLogs": len(source_logs),
        "LogsWithPeriodicSummary": len(latest_summaries_by_log),
        "AllSourceLogsHavePeriodicSummary": all_source_logs_have_periodic_summary,
        "LogsWithCurrentPeriodicSummary": len(current_summaries_by_log),
        "CurrentSummaryMissingLogs": current_summary_missing_logs,
        "AllSourceLogsHaveCurrentPeriodicSummary": all_source_logs_have_summary,
        "LogsWithLatestStartupSummary": len(latest_startup_summary_by_log),
        "LatestStartupMissingSummaryLogs": latest_startup_missing_summary_logs,
        "AllLogsWithStartupHaveLatestSummary": all_logs_with_startup_have_latest_summary,
    }

    historical_fixed_function_detailed_stage_demand = (
        summarize_fixed_function_detailed_stage_demand(fixed_function, None)
    )
    fixed_function_detailed_stage_demand = summarize_fixed_function_detailed_stage_demand(
        current_fixed_function,
        (
            {"signatureDetailSkipped": sum_latest("signatureDetailSkipped")}
            if latest_summaries
            else None
        ),
    )

    if not source_logs:
        status = "NO_DX11_CENSUS_LOG"
    elif not summaries:
        status = "CENSUS_ACTIVE_NO_PERIODIC_SUMMARY"
    elif latest_summaries and unsupported_total != 0:
        status = "UNSUPPORTED_BEHAVIOR_OBSERVED"
    elif not all_source_logs_have_summary:
        status = "TRANSLATION_EXACTNESS_PENDING"
    # R237: exhaustive source-draw sampling does not imply complete signature
    # evidence. Keep the headline status fail-closed until the current startup's
    # signature universe is reconciled and the hash cap has not saturated.
    elif (
        sampled_exactness["AllSampledExact"]
        and exhaustive_draw_coverage
        and not all_current_signature_evidence_coverage_complete
    ):
        status = (
            "OBSERVED_EXHAUSTIVE_TRANSLATION_EXACT_"
            "SIGNATURE_EVIDENCE_INCOMPLETE"
        )
    elif sampled_exactness["AllSampledExact"] and exhaustive_draw_coverage:
        status = "OBSERVED_EXHAUSTIVE_TRANSLATION_EXACT_DIAGNOSTIC_ONLY"
    elif (
        sampled_exactness["AllSampledExact"]
        and sampling_coverage["SignatureHashCapSaturated"]
    ):
        status = "OBSERVED_SAMPLED_TRANSLATION_EXACT_COVERAGE_SATURATED"
    elif sampled_exactness["AllSampledExact"]:
        status = "OBSERVED_SAMPLED_TRANSLATION_EXACT_DIAGNOSTIC_ONLY"
    else:
        status = "TRANSLATION_EXACTNESS_PENDING"

    managed_texture_shadow_evidence = {
        "RequiredSamples": sum_latest("managedTextureShadowRequiredSamples"),
        "ReadySamples": sum_latest("managedTextureShadowReadySamples"),
        "PendingSamples": sum_latest("managedTextureShadowPendingSamples"),
        "RequiredStages": sum_latest("textureStageManagedShadowRequired"),
        "ReadyStages": sum_latest("textureStageManagedShadowReady"),
        "PendingStages": sum_latest("textureStageManagedShadowPending"),
        "UpdateTextureInvalidations": sum_latest(
            "managedTextureUpdateTextureInvalidations"
        ),
        "UpdateSurfaceInvalidations": sum_latest(
            "managedTextureUpdateSurfaceInvalidations"
        ),
    }
    managed_texture_shadow_evidence["ExternalMutationInvalidations"] = (
        managed_texture_shadow_evidence["UpdateTextureInvalidations"]
        + managed_texture_shadow_evidence["UpdateSurfaceInvalidations"]
    )
    managed_texture_shadow_evidence["ObservedReady"] = bool(
        managed_texture_shadow_evidence["RequiredSamples"] > 0
        and managed_texture_shadow_evidence["PendingSamples"] == 0
        and managed_texture_shadow_evidence["ReadySamples"]
        == managed_texture_shadow_evidence["RequiredSamples"]
    )

    programmable_semantic_evidence = {
        "PlanExactSamples": sum_latest("shaderSemanticPlanExact"),
        "PlanPendingSamples": sum_latest("shaderSemanticPlanPending"),
        "ReceiptExactSamples": sum_latest("shaderSemanticReceiptExact"),
        "ReceiptPendingSamples": sum_latest("shaderSemanticReceiptPending"),
        "TranslationImplemented": False,
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }

    dual_source_blend_evidence = {
        "AnySamples": sum_latest("dualSourceBlendAny"),
        "RgbSourceSamples": sum_latest("dualSourceBlendRgbSrc"),
        "RgbDestSamples": sum_latest("dualSourceBlendRgbDst"),
        "AlphaSourceSamples": sum_latest("dualSourceBlendAlphaSrc"),
        "AlphaDestSamples": sum_latest("dualSourceBlendAlphaDst"),
        "ExhaustiveNoUsageObserved": bool(
            exhaustive_draw_coverage and sum_latest("dualSourceBlendAny") == 0
        ),
        "TranslationStillFailClosed": True,
        "ActivationProof": False,
    }

    signature_coverage = {
        "HistoricalUniqueSignatures": len(signatures),
        "CurrentUniqueSignatures": len(current_signatures),
        "LogsWithCurrentSignatures": sum(
            1 for entries in current_signatures_by_log.values() if entries
        ),
        "CurrentSignatureEvidenceByLog": current_signature_evidence_by_log,
        "CurrentSignatureEvidenceMissingLogs": (
            current_signature_evidence_missing_logs
        ),
        "CurrentSignatureEvidenceOvercountLogs": (
            current_signature_evidence_overcount_logs
        ),
        "CurrentSignatureHashCapSaturatedLogs": (
            current_signature_hash_cap_saturated_logs
        ),
        "AllCurrentSignatureEvidenceAccounted": (
            all_current_signature_evidence_accounted
        ),
        "AllCurrentSignatureEvidenceCoverageComplete": (
            all_current_signature_evidence_coverage_complete
        ),
        "DiagnosticOnly": True,
        "ActivationProof": False,
    }

    report = {
        "SchemaVersion": 2,
        "Status": status,
        "NativeDrawPathActivationAllowed": False,
        "ActivationEvidence": {
            "CensusExactness": sampled_exactness,
            "SamplingCoverage": sampling_coverage,
            "SignatureEvidenceCoverage": signature_coverage,
            "ProgrammableShaderInventory": programmable_shader_inventory,
            "StartupBootstrapCoverage": startup_bootstrap_coverage,
            "ManagedTextureShadow": managed_texture_shadow_evidence,
            "ProgrammableSemanticTranslation": programmable_semantic_evidence,
            "DualSourceBlend": dual_source_blend_evidence,
            "FixedFunctionDetailedStageDemand": fixed_function_detailed_stage_demand,
        },
        "ActivationNote": (
            "R114 defaults to hashed-ordinal sampled diagnostics. "
            "When the runtime explicitly reports scheme=2, stride=1, and samples equal "
            "drawsSeen, the report records exhaustive source-draw census coverage. "
            "The 64-entry detailed-log cap no longer limits fixed-function D3DCompile probes; "
            "compile coverage is skipped only when the independent signature-hash cap is exceeded. "
            "Signature hash/detail caps remain separate diagnostic-detail evidence. "
            "R238 extracts programmable VS/PS pair identity from captured detailed signatures; "
            "any detail/hash cap or shader-introspection gap keeps that pair inventory incomplete. "
            "Even exhaustive exact census remains diagnostic only: ActivationProof and "
            "NativeDrawPathActivationAllowed stay false, and exact-build HMD graphics "
            "parity is still required before native draw routing. "
            "SRC1 dual-source blend remains fail-closed; zero demand is treated as "
            "absence evidence only under exhaustive draw coverage."
        ),
        "SourceLogs": source_logs,
        "Startup": startup,
        "Bootstrap": bootstrap,
        "BootstrapSkipped": bootstrap_skipped,
        "BootstrapOutcomes": bootstrap_outcomes,
        "LatestStartupByLog": latest_startup_by_log,
        "LatestStartupEpochByLog": latest_startup_epoch_by_log,
        "LatestBootstrapByLog": latest_bootstrap_by_log,
        "LatestBootstrapSkipByLog": latest_bootstrap_skip_by_log,
        "LatestBootstrapOutcomeByLog": latest_bootstrap_outcome_by_log,
        "LatestStartupBootstrapOutcomeByLog": (
            latest_startup_bootstrap_outcome_by_log
        ),
        "StartupBootstrapCoverage": startup_bootstrap_coverage,
        "LatestSummary": latest,
        "LatestSummariesByLog": latest_summaries_by_log,
        "CurrentSummariesByLog": current_summaries_by_log,
        "LatestStartupSummaryByLog": latest_startup_summary_by_log,
        "SummaryCoverage": summary_coverage,
        "AllSummaries": summaries,
        "UnsupportedTotalLatest": unsupported_total,
        "SignatureCoverage": signature_coverage,
        "ProgrammableShaderInventory": programmable_shader_inventory,
        "UniqueSignaturesCaptured": len(signatures),
        "CurrentUniqueSignaturesCaptured": len(current_signatures),
        "CurrentSignaturesByLog": current_signatures_by_log,
        "CurrentSignatures": [
            current_signatures[key] for key in sorted(current_signatures)
        ],
        "HistoricalFixedFunctionDetailedStageDemand": (
            historical_fixed_function_detailed_stage_demand
        ),
        "Signatures": [signatures[key] for key in sorted(signatures)],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"DX11 census extraction: status={status} "
        f"logs={len(source_logs)} signatures={len(signatures)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

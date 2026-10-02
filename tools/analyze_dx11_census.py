#!/usr/bin/env python3
"""Extract DX11 native-backend census evidence from one OutRun VR session."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SUMMARY_RE = re.compile(
    r"VR DX11 R(?:7[23456789]|8[012345]|114|120) census: "
    r"samples=(?P<samples>\d+) exact=(?P<exact>\d+) "
    r"fixedFn=(?P<fixedFn>\d+) programmable=(?P<programmable>\d+) "
    r"topologyUnsupported=(?P<topologyUnsupported>\d+) "
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
    r"depthUnsupported=(?P<depthUnsupported>\d+)\] "
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
    r"fixedFunctionPending=(?P<shaderFixedFunctionPending>\d+),"
    r"programmablePending=(?P<shaderProgrammablePending>\d+)\] )?"
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
    r"(?:,texCoordWrap=(?P<texCoordWrap>\d+))?)?\]"
)

BOOTSTRAP_RE = re.compile(
    r"VR DX11 R72 bootstrap probe: ready=(?P<ready>[01]) "
    r"featureLevel=0x(?P<featureLevel>[0-9A-Fa-f]+) "
    r"selectedLuidValid=(?P<selectedLuidValid>[01]) "
    r"selectedLuid=(?P<luidHigh>[0-9A-Fa-f]{8}):(?P<luidLow>[0-9A-Fa-f]{8})"
)

STARTUP_RE = re.compile(
    r"VR DX11 R71 census: observed=(?P<observed>[01]) "
    r"size=(?P<width>\d+)x(?P<height>\d+) "
    r"sourceFormat=(?P<sourceFormat>-?\d+) nativeFormat=(?P<nativeFormat>-?\d+) "
    r"msaa=(?P<msaa>-?\d+) bootstrapCompatible=(?P<bootstrapCompatible>[01])"
)

SIGNATURE_RE = re.compile(r"VR DX11 R(?:7[23456789]|8[012345]) signature#(?P<id>\d+): (?P<body>.*)")
DECL_RE = re.compile(
    r"VR DX11 R72 decl signature#(?P<signature>\d+) elem#(?P<element>\d+): "
    r"stream=(?P<stream>\d+) offset=(?P<offset>\d+) type=(?P<type>\d+) "
    r"method=(?P<method>\d+) usage=(?P<usage>\d+) usageIndex=(?P<usageIndex>\d+)"
)
FFP_RE = re.compile(
    r"VR DX11 R(?:72|8[12345]|160) ffp signature#(?P<signature>\d+) stage#(?P<stage>\d+): "
    r"color\[op=(?P<colorOp>\d+),arg1=0x(?P<colorArg1>[0-9A-Fa-f]+),"
    r"arg2=0x(?P<colorArg2>[0-9A-Fa-f]+)\] "
    r"alpha\[op=(?P<alphaOp>\d+),arg1=0x(?P<alphaArg1>[0-9A-Fa-f]+),"
    r"arg2=0x(?P<alphaArg2>[0-9A-Fa-f]+)\] "
    r"(?:resultArg=0x(?P<resultArg>[0-9A-Fa-f]+) )?"
    r"texCoord=0x(?P<texCoord>[0-9A-Fa-f]+) "
    r"texTransform=0x(?P<texTransform>[0-9A-Fa-f]+)"
    r"(?: sampler\[min=(?P<samplerMin>\d+),mag=(?P<samplerMag>\d+),"
    r"mip=(?P<samplerMip>\d+),u=(?P<samplerAddressU>\d+),"
    r"v=(?P<samplerAddressV>\d+)"
    r"(?:,border=0x(?P<samplerBorderColor>[0-9A-Fa-f]+))?"
    r"(?:,srgb=(?P<samplerSrgb>\d+))?\])?"
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


def int_fields(match: re.Match[str]) -> dict[str, int]:
    return {
        key: int(value) if value is not None else 0
        for key, value in match.groupdict().items()
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
    summaries: list[dict] = []
    signatures: dict[int, dict] = {}
    declarations: dict[int, list[dict]] = {}
    fixed_function: dict[int, list[dict]] = {}
    texture_stages: dict[int, list[dict]] = {}
    fixed_function_shader_prototypes: dict[int, dict] = {}
    fixed_function_shader_compiles: dict[int, dict] = {}
    source_logs: list[str] = []

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
        ):
            continue
        source_logs.append(log_path.name)

        for line in text.splitlines():
            match = STARTUP_RE.search(line)
            if match:
                startup.append(int_fields(match))
                continue

            match = BOOTSTRAP_RE.search(line)
            if match:
                data = match.groupdict()
                bootstrap.append(
                    {
                        "ready": bool(int(data["ready"])),
                        "feature_level_hex": "0x" + data["featureLevel"].upper(),
                        "selected_luid_valid": bool(int(data["selectedLuidValid"])),
                        "selected_luid": (
                            data["luidHigh"].upper() + ":" + data["luidLow"].upper()
                        ),
                    }
                )
                continue

            match = SUMMARY_RE.search(line)
            if match:
                summaries.append(int_fields(match))
                continue

            match = SIGNATURE_RE.search(line)
            if match:
                signature_id = int(match.group("id"))
                signatures.setdefault(
                    signature_id,
                    {"id": signature_id, "raw": match.group("body")},
                )
                continue

            match = DECL_RE.search(line)
            if match:
                data = int_fields(match)
                signature_id = data.pop("signature")
                declarations.setdefault(signature_id, []).append(data)
                continue

            match = FFP_SHADER_COMPILE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                fixed_function_shader_compiles[signature_id] = {
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
                fixed_function_shader_prototypes[signature_id] = {
                    "generated": bool(int(data["generated"])),
                    "unsupported_mask": int(data["mask"], 16),
                    "unsupported_mask_hex": "0x" + data["mask"].upper(),
                    "source_hash": int(data["hash"], 16),
                    "source_hash_hex": "0x" + data["hash"].upper(),
                    "bytes": int(data["bytes"]),
                    "active_stages": int(data["activeStages"]),
                }
                continue

            match = TEXTURE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
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
                texture_stages.setdefault(signature_id, []).append(parsed)
                continue

            match = FFP_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                stage = int(data.pop("stage"))
                parsed = {"stage": stage}
                for key, value in data.items():
                    if value is None:
                        continue
                    if key in {"colorArg1", "colorArg2", "alphaArg1", "alphaArg2",
                               "texCoord", "texTransform", "samplerBorderColor"}:
                        parsed[key] = int(value, 16)
                        parsed[key + "_hex"] = "0x" + value.upper()
                    else:
                        parsed[key] = int(value)
                fixed_function.setdefault(signature_id, []).append(parsed)

    for signature_id, signature in signatures.items():
        signature["declaration"] = sorted(
            declarations.get(signature_id, []), key=lambda item: item["element"]
        )
        signature["fixed_function_stages"] = sorted(
            fixed_function.get(signature_id, []), key=lambda item: item["stage"]
        )
        signature["texture_stages"] = sorted(
            texture_stages.get(signature_id, []), key=lambda item: item["stage"]
        )
        signature["fixed_function_shader_prototype"] = (
            fixed_function_shader_prototypes.get(signature_id)
        )
        signature["fixed_function_shader_compile"] = (
            fixed_function_shader_compiles.get(signature_id)
        )

    latest = summaries[-1] if summaries else None
    unsupported_total = None
    if latest:
        unsupported_keys = [
            "topologyUnsupported",
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
        ]
        unsupported_total = sum(latest[key] for key in unsupported_keys)

    exhaustive_draw_coverage = bool(
        latest
        and latest["samplingScheme"] == 2
        and latest["samplingStride"] == 1
        and latest["samplingDrawsSeen"] > 0
        and latest["samples"] == latest["samplingDrawsSeen"]
    )

    sampled_exactness = {
        "Samples": latest["samples"] if latest else 0,
        "ExactSamples": latest["exact"] if latest else 0,
        "UnsupportedTotal": unsupported_total,
        "AllSampledExact": bool(
            latest
            and latest["samples"] > 0
            and latest["exact"] == latest["samples"]
            and unsupported_total == 0
        ),
        "DiagnosticOnly": True,
        "ExhaustiveDrawCoverage": exhaustive_draw_coverage,
        "ActivationProof": False,
    }

    sampling_scheme_id = latest["samplingScheme"] if latest else 0
    sampling_coverage = {
        "DrawsSeen": latest["samplingDrawsSeen"] if latest else 0,
        "Samples": latest["samples"] if latest else 0,
        "Stride": latest["samplingStride"] if latest else 0,
        "SchemeId": sampling_scheme_id,
        "Scheme": (
            "EXHAUSTIVE_V1"
            if sampling_scheme_id == 2
            else (
                "HASHED_ORDINAL_V1"
                if sampling_scheme_id == 1
                else "LEGACY_OR_UNSPECIFIED"
            )
        ),
        "SignatureHashCap": latest["signatureHashCap"] if latest else 0,
        "SignatureHashCapHitSamples": (
            latest["signatureHashCapHitSamples"] if latest else 0
        ),
        "DetailedSignatureLogCap": (
            latest["signatureDetailCap"] if latest else 0
        ),
        "DetailedSignatureLogSkippedSignatures": (
            latest["signatureDetailSkipped"] if latest else 0
        ),
        "SignatureHashCapSaturated": bool(
            latest and latest["signatureHashCapHitSamples"] > 0
        ),
        "DetailedSignatureLogCapSaturated": bool(
            latest and latest["signatureDetailSkipped"] > 0
        ),
        "NonExhaustive": not exhaustive_draw_coverage,
        "ExhaustiveDrawCoverage": exhaustive_draw_coverage,
        "ActivationProof": False,
    }

    if not source_logs:
        status = "NO_DX11_CENSUS_LOG"
    elif not summaries:
        status = "CENSUS_ACTIVE_NO_PERIODIC_SUMMARY"
    elif unsupported_total != 0:
        status = "UNSUPPORTED_BEHAVIOR_OBSERVED"
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
        "RequiredSamples": (
            latest["managedTextureShadowRequiredSamples"] if latest else 0
        ),
        "ReadySamples": (
            latest["managedTextureShadowReadySamples"] if latest else 0
        ),
        "PendingSamples": (
            latest["managedTextureShadowPendingSamples"] if latest else 0
        ),
        "RequiredStages": (
            latest["textureStageManagedShadowRequired"] if latest else 0
        ),
        "ReadyStages": (
            latest["textureStageManagedShadowReady"] if latest else 0
        ),
        "PendingStages": (
            latest["textureStageManagedShadowPending"] if latest else 0
        ),
        "UpdateTextureInvalidations": (
            latest["managedTextureUpdateTextureInvalidations"] if latest else 0
        ),
        "UpdateSurfaceInvalidations": (
            latest["managedTextureUpdateSurfaceInvalidations"] if latest else 0
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

    dual_source_blend_evidence = {
        "AnySamples": latest["dualSourceBlendAny"] if latest else 0,
        "RgbSourceSamples": latest["dualSourceBlendRgbSrc"] if latest else 0,
        "RgbDestSamples": latest["dualSourceBlendRgbDst"] if latest else 0,
        "AlphaSourceSamples": latest["dualSourceBlendAlphaSrc"] if latest else 0,
        "AlphaDestSamples": latest["dualSourceBlendAlphaDst"] if latest else 0,
        "ExhaustiveNoUsageObserved": bool(
            exhaustive_draw_coverage
            and latest
            and latest["dualSourceBlendAny"] == 0
        ),
        "TranslationStillFailClosed": True,
        "ActivationProof": False,
    }

    report = {
        "SchemaVersion": 2,
        "Status": status,
        "NativeDrawPathActivationAllowed": False,
        "ActivationEvidence": {
            "CensusExactness": sampled_exactness,
            "SamplingCoverage": sampling_coverage,
            "ManagedTextureShadow": managed_texture_shadow_evidence,
            "DualSourceBlend": dual_source_blend_evidence,
        },
        "ActivationNote": (
            "R114 defaults to hashed-ordinal sampled diagnostics. "
            "When the runtime explicitly reports scheme=2, stride=1, and samples equal "
            "drawsSeen, the report records exhaustive source-draw census coverage. "
            "Signature hash/detail caps remain separate diagnostic-detail evidence. "
            "Even exhaustive exact census remains diagnostic only: ActivationProof and "
            "NativeDrawPathActivationAllowed stay false, and exact-build HMD graphics "
            "parity is still required before native draw routing. "
            "SRC1 dual-source blend remains fail-closed; zero demand is treated as "
            "absence evidence only under exhaustive draw coverage."
        ),
        "SourceLogs": source_logs,
        "Startup": startup,
        "Bootstrap": bootstrap,
        "LatestSummary": latest,
        "AllSummaries": summaries,
        "UnsupportedTotalLatest": unsupported_total,
        "UniqueSignaturesCaptured": len(signatures),
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

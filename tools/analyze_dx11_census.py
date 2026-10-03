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
SignatureKey = tuple[str, int]


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
    # R199/R225: detail lines may repeat, but runtime signature ids are local
    # to one process/log. Drop true duplicates only inside the same source-log
    # namespace; never merge unrelated signature#N records across sessions.
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
    summaries: list[dict] = []
    # R225: runtime signature ids are insertion-order ordinals and restart for
    # every process. Scope every detail/evidence record by source log so two
    # separate sessions' signature#1 records can never overwrite each other.
    signatures: dict[SignatureKey, dict] = {}
    declarations: dict[SignatureKey, list[dict]] = {}
    fixed_function: dict[SignatureKey, list[dict]] = {}
    fixed_function_texture_factors: dict[SignatureKey, dict] = {}
    texture_stages: dict[SignatureKey, list[dict]] = {}
    fixed_function_shader_prototypes: dict[SignatureKey, dict] = {}
    fixed_function_shader_compiles: dict[SignatureKey, dict] = {}
    fixed_function_vertex_shader_compiles: dict[SignatureKey, dict] = {}
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
            and "VR DX11 R191" not in text
            and "VR DX11 R194" not in text
            and "VR DX11 R197" not in text
            and "VR DX11 R223" not in text
        ):
            continue
        source_logs.append(log_path.name)
        source_log = log_path.name

        for line in text.splitlines():
            match = STARTUP_RE.search(line)
            if match:
                startup_entry = int_fields(match)
                startup_entry["source_log"] = source_log
                startup.append(startup_entry)
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
                continue

            match = SUMMARY_RE.search(line)
            if match:
                summary = int_fields(match)
                summary["source_log"] = source_log
                summaries.append(summary)
                continue

            match = SIGNATURE_RE.search(line)
            if match:
                signature_id = int(match.group("id"))
                signature_key = (source_log, signature_id)
                signatures.setdefault(
                    signature_key,
                    {
                        "source_log": source_log,
                        "id": signature_id,
                        "raw": match.group("body"),
                    },
                )
                continue

            match = DECL_RE.search(line)
            if match:
                data = int_fields(match)
                signature_id = data.pop("signature")
                signature_key = (source_log, signature_id)
                declarations.setdefault(signature_key, []).append(data)
                continue

            match = FFP_SHADER_COMPILE_RE.search(line)
            if match:
                data = match.groupdict()
                signature_id = int(data.pop("signature"))
                signature_key = (source_log, signature_id)
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
                signature_key = (source_log, signature_id)
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
                signature_key = (source_log, signature_id)
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
                signature_key = (source_log, signature_id)
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
                signature_key = (source_log, signature_id)
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
                signature_key = (source_log, signature_id)
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

    latest_summaries_by_log: dict[str, dict] = {}
    for summary in summaries:
        latest_summaries_by_log[summary["source_log"]] = summary
    latest_summaries = [
        latest_summaries_by_log[source_log]
        for source_log in source_logs
        if source_log in latest_summaries_by_log
    ]
    all_source_logs_have_summary = bool(source_logs) and (
        len(latest_summaries) == len(source_logs)
    )
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
    bootstrap_outcome_logs = set(latest_bootstrap_by_log) | set(
        latest_bootstrap_skip_by_log
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
    startup_bootstrap_coverage = {
        "SourceLogs": len(source_logs),
        "LogsWithStartup": len(latest_startup_by_log),
        "LogsWithBootstrap": len(latest_bootstrap_by_log),
        "LogsWithBootstrapSkip": len(latest_bootstrap_skip_by_log),
        "LogsWithBootstrapOutcome": len(bootstrap_outcome_logs),
        "AllSourceLogsHaveStartup": all_source_logs_have_startup,
        "AllSourceLogsHaveBootstrap": all_source_logs_have_bootstrap,
        "AllSourceLogsHaveBootstrapOutcome": all_source_logs_have_bootstrap_outcome,
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
        "AllSourceLogsHavePeriodicSummary": all_source_logs_have_summary,
    }

    fixed_function_detailed_stage_demand = summarize_fixed_function_detailed_stage_demand(
        fixed_function,
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
    elif unsupported_total != 0:
        status = "UNSUPPORTED_BEHAVIOR_OBSERVED"
    elif not all_source_logs_have_summary:
        status = "TRANSLATION_EXACTNESS_PENDING"
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

    report = {
        "SchemaVersion": 2,
        "Status": status,
        "NativeDrawPathActivationAllowed": False,
        "ActivationEvidence": {
            "CensusExactness": sampled_exactness,
            "SamplingCoverage": sampling_coverage,
            "StartupBootstrapCoverage": startup_bootstrap_coverage,
            "ManagedTextureShadow": managed_texture_shadow_evidence,
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
        "LatestStartupByLog": latest_startup_by_log,
        "LatestBootstrapByLog": latest_bootstrap_by_log,
        "LatestBootstrapSkipByLog": latest_bootstrap_skip_by_log,
        "StartupBootstrapCoverage": startup_bootstrap_coverage,
        "LatestSummary": latest,
        "LatestSummariesByLog": latest_summaries_by_log,
        "SummaryCoverage": summary_coverage,
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

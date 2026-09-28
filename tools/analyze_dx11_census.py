#!/usr/bin/env python3
"""Extract DX11 native-backend census evidence from one OutRun VR session."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SUMMARY_RE = re.compile(
    r"VR DX11 R(?:7[23456789]|8[012]) census: "
    r"samples=(?P<samples>\d+) exact=(?P<exact>\d+) "
    r"fixedFn=(?P<fixedFn>\d+) programmable=(?P<programmable>\d+) "
    r"topologyUnsupported=(?P<topologyUnsupported>\d+) "
    r"signatures=(?P<signatures>\d+) declSamples=(?P<declSamples>\d+) "
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
    r"unsupported\[incomplete=(?P<incomplete>\d+),"
    r"wbuffer=(?P<wbuffer>\d+),sepAlpha=(?P<sepAlpha>\d+),"
    r"alphaTest=(?P<alphaTest>\d+),stencil=(?P<stencil>\d+),"
    r"fog=(?P<fog>\d+),lighting=(?P<lighting>\d+),"
    r"srgb=(?P<srgb>\d+),fill=(?P<fill>\d+),"
    r"blend=(?P<blend>\d+),depthCmp=(?P<depthCmp>\d+),"
    r"cull=(?P<cull>\d+)\]"
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

SIGNATURE_RE = re.compile(r"VR DX11 R(?:7[23456789]|8[012]) signature#(?P<id>\d+): (?P<body>.*)")
DECL_RE = re.compile(
    r"VR DX11 R72 decl signature#(?P<signature>\d+) elem#(?P<element>\d+): "
    r"stream=(?P<stream>\d+) offset=(?P<offset>\d+) type=(?P<type>\d+) "
    r"method=(?P<method>\d+) usage=(?P<usage>\d+) usageIndex=(?P<usageIndex>\d+)"
)
FFP_RE = re.compile(
    r"VR DX11 R(?:72|8[12]) ffp signature#(?P<signature>\d+) stage#(?P<stage>\d+): "
    r"color\[op=(?P<colorOp>\d+),arg1=0x(?P<colorArg1>[0-9A-Fa-f]+),"
    r"arg2=0x(?P<colorArg2>[0-9A-Fa-f]+)\] "
    r"alpha\[op=(?P<alphaOp>\d+),arg1=0x(?P<alphaArg1>[0-9A-Fa-f]+),"
    r"arg2=0x(?P<alphaArg2>[0-9A-Fa-f]+)\] "
    r"texCoord=0x(?P<texCoord>[0-9A-Fa-f]+) "
    r"texTransform=0x(?P<texTransform>[0-9A-Fa-f]+)"
    r"(?: sampler\[min=(?P<samplerMin>\d+),mag=(?P<samplerMag>\d+),"
    r"mip=(?P<samplerMip>\d+),u=(?P<samplerAddressU>\d+),"
    r"v=(?P<samplerAddressV>\d+)\])?"
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
                               "texCoord", "texTransform"}:
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
        ]
        unsupported_total = sum(latest[key] for key in unsupported_keys)

    if not source_logs:
        status = "NO_DX11_CENSUS_LOG"
    elif not summaries:
        status = "CENSUS_ACTIVE_NO_PERIODIC_SUMMARY"
    elif unsupported_total == 0:
        status = "OBSERVED_SAMPLE_TRANSLATION_EXACT"
    else:
        status = "UNSUPPORTED_BEHAVIOR_OBSERVED"

    report = {
        "SchemaVersion": 2,
        "Status": status,
        "NativeDrawPathActivationAllowed": False,
        "ActivationNote": (
            "Census exactness is evidence only. Native D3D11 draw routing remains "
            "disabled until resource mutation classification/lifetime mirrors, shader/input "
            "translation and HMD graphics parity gates pass."
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

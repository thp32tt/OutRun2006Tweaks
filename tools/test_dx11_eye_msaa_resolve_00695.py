#!/usr/bin/env python3
"""Stereo game eye pair -> native DX11 single-sample ring, with fail-closed MSAA resolve."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root=Path(__file__).resolve().parents[1]
source=(root/"src/vr/d3d11/native_shared_eye_ring.cpp").read_text(encoding="utf-8")
header=(root/"src/vr/d3d11/native_game_eye_pair_sources.hpp").read_text(encoding="utf-8")
def connected(s,h):
    try:
        fn=s.split("bool NativeSharedEyeRing::submit_eye_pair(",1)[1].split(
            "bool NativeSharedEyeRing::signal_producer_fence(",1)[0]
    except IndexError:
        return False
    checks=[
        "exact_source(left_source, leftDesc)",
        "exact_source(right_source, rightDesc)",
        "desc.SampleDesc.Count == 0",
        "desc.SampleDesc.Count == 1 && desc.SampleDesc.Quality != 0",
        "producer_device_->CheckFormatSupport(format_, &formatSupport)",
        "formatSupport & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE",
        "native_game_eye_transfer(",
        "leftDesc.SampleDesc.Count, leftDesc.SampleDesc.Quality,",
        "rightDesc.SampleDesc.Count, rightDesc.SampleDesc.Quality,",
        "transfer == NativeGameEyeTransfer::Reject",
        "native_game_eye_pair_sources_admitted(",
        "transfer == NativeGameEyeTransfer::Resolve",
        "context->ResolveSubresource(entry.eye[0].Get(), 0u, left_source, 0u, format_);",
        "context->ResolveSubresource(entry.eye[1].Get(), 0u, right_source, 0u, format_);",
        "context->CopyResource(entry.eye[0].Get(), left_source);",
        "context->CopyResource(entry.eye[1].Get(), right_source);",
        "return signal_producer_fence(context, slot, frame_id);",
    ]
    hchecks=[
        "leftSamples == 0u || leftSamples > 32u",
        "leftSamples != rightSamples",
        "leftQuality != rightQuality",
        "leftSamples == 1u",
        "leftQuality == 0u",
        "return formatSupportsResolve",
    ]
    return all(x in fn for x in checks) and all(x in h for x in hchecks) and (
        fn.index("native_game_eye_transfer(") <
        fn.index("native_game_eye_pair_sources_admitted(") <
        fn.index("context->ResolveSubresource(") <
        fn.index("return signal_producer_fence(")
    )

assert connected(source,header), "native game MSAA eyes not linked to safe DX11 ring"
changes=0
for key in [
    "desc.SampleDesc.Count == 0",
    "exact_source(left_source, leftDesc)",
    "exact_source(right_source, rightDesc)",
    "producer_device_->CheckFormatSupport(format_, &formatSupport)",
    "formatSupport & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE",
    "native_game_eye_transfer(",
    "native_game_eye_pair_sources_admitted(",
    "transfer == NativeGameEyeTransfer::Resolve",
    "context->ResolveSubresource(entry.eye[0].Get(), 0u, left_source, 0u, format_);",
    "context->ResolveSubresource(entry.eye[1].Get(), 0u, right_source, 0u, format_);",
    "context->CopyResource(entry.eye[0].Get(), left_source);",
    "context->CopyResource(entry.eye[1].Get(), right_source);",
]:
    assert key in source and not connected(source.replace(key,"/* removed */",1),header),key
    changes+=1
for key in [
    "leftSamples == 0u || leftSamples > 32u",
        "leftSamples != rightSamples",
    "leftQuality != rightQuality",
    "leftQuality == 0u",
    "return formatSupportsResolve",
]:
    assert key in header and not connected(source,header.replace(key,"/* removed */",1)),key
    changes+=1
compiler=shutil.which("g++") or shutil.which("clang++")
assert compiler, "C++17 compiler required"
with TemporaryDirectory(prefix="dx11-eye-msaa-00695-") as temp:
    binary=Path(temp)/"eye_probe"
    result=subprocess.run([compiler,"-std=c++17","-O2","-Wall","-Wextra",
        "-Werror","-pedantic",str(root/"tools/dx11_eye_msaa_resolve_probe_00695.cpp"),
        "-o",str(binary)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    result=subprocess.run([str(binary)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
print(f"00695 PASS: per-eye native Resolve/Copy -> ring fence; {changes} destructive checks; HMD UNTESTED")

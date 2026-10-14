#!/usr/bin/env python3
"""R29 partial-WVP upload: bounded, fully initialized, zero-fill-free envelope.

The game uploads contiguous float4 shader constants. The widened request
is the union of an intersecting caller interval and c64..c67, hence no
register-sized gap can exist. Negative mutations protect each live source
invariant; this does not stand in for the Win32 build or Quest3 runtime.
"""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/game/outrun_renderer_r29.cpp"


def function(source: str, marker: str) -> str:
    pos = source.find(marker)
    assert pos >= 0, f"missing definition: {marker}"
    start = source.find("{", pos)
    assert start >= 0
    depth = 0
    for i in range(start, len(source)):
        depth += (source[i] == "{") - (source[i] == "}")
        if depth == 0:
            return source[pos:i + 1]
    raise AssertionError(f"unclosed definition: {marker}")


def contract(source: str) -> bool:
    build = function(source, "bool R29BuildCoherentUploadEnvelope(")
    upload = function(source, "HRESULT __stdcall SetVertexShaderConstantFDestR29(")
    keys = (
        "if (requestLast <= wvpFirst || requestFirst >= wvpLast)",
        "if (last <= first || last - first > 256 ||",
        "last > maxRegisterPlusOne)",
        "const UINT wvpOffset = OutRunWvpRegister - envelopeStart;",
        "std::memcpy(envelopeData + wvpOffset * 4, R28RawWvp,",
        "if (requestFirst < wvpFirst)",
        "if (requestLast > wvpLast)",
        "std::memcpy(envelopeData + destinationOffset * 4,",
        "std::memcpy(envelopeData +",
        "float envelopeData[256 * 4];",
        "R29BuildCoherentUploadEnvelope(startRegister,",
    )
    return (all((key in (upload if key in keys[-2:] else build))
                for key in keys)
            and "std::memset(envelopeData" not in build
            and "float envelopeData[256 * 4]{}" not in upload
            and build.find("if (requestLast <= wvpFirst") <
                build.find("envelopeCount = static_cast<UINT>(") <
                build.find("std::memcpy(envelopeData + wvpOffset * 4")
            and build.find("std::memcpy(envelopeData + wvpOffset * 4") <
                build.find("if (requestFirst < wvpFirst)") <
                build.find("if (requestLast > wvpLast)"))


def model(start: int, count: int) -> bool:
    wvp_first, wvp_last = 64, 68
    req_last = start + count
    if not count or count > 256 or req_last <= wvp_first or start >= wvp_last:
        return False
    first, last = min(start, wvp_first), max(req_last, wvp_last)
    if last <= first or last - first > 256 or last > 2**32:
        return False

    # None is poison, not zero: a surviving slot proves a read of
    # uninitialized scratch in the actual zero-fill-free implementation.
    buffer = [None] * (last - first)
    expected = [None] * (last - first)
    for register in range(start, req_last):
        expected[register - first] = ("original", register)
    for register in range(wvp_first, wvp_last):
        expected[register - first] = ("wvp", register)
        buffer[register - first] = ("wvp", register)
    if start < wvp_first:
        for register in range(start, min(req_last, wvp_first)):
            buffer[register - first] = ("original", register)
    if req_last > wvp_last:
        for register in range(max(start, wvp_last), req_last):
            buffer[register - first] = ("original", register)
    assert None not in buffer, (start, count, first, last)
    assert buffer == expected, (start, count)
    return True


source = SRC.read_text(encoding="utf-8")
assert contract(source), "R29 bounded zero-fill-free WVP envelope contract"
mutations = [
    ("no intersection guard",
     "if (requestLast <= wvpFirst || requestFirst >= wvpLast)",
     "if (false)"),
    ("no max envelope",
     "last - first > 256", "false"),
    ("no 32-bit upper bound",
     "last > maxRegisterPlusOne", "false"),
    ("no WVP copy",
     "std::memcpy(envelopeData + wvpOffset * 4, R28RawWvp,",
     "std::memcpy(envelopeData + (wvpOffset + 1) * 4, R28RawWvp,"),
    ("no prefix", "if (requestFirst < wvpFirst)", "if (false)"),
    ("no suffix", "if (requestLast > wvpLast)", "if (false)"),
    ("premature memset", "const UINT wvpOffset = OutRunWvpRegister - envelopeStart;",
     "std::memset(envelopeData, 0, sizeof(float) * envelopeCount * 4);\n            const UINT wvpOffset = OutRunWvpRegister - envelopeStart;"),
    ("premature array zero fill", "float envelopeData[256 * 4];",
     "float envelopeData[256 * 4]{};"),
]
for label, before, after in mutations:
    assert source.count(before) == 1, f"bad fixture: {label}"
    assert not contract(source.replace(before, after, 1)), f"escaped: {label}"

cases = 0
for start in range(0, 70):
    for count in range(1, 257):
        model(start, count)
        cases += 1
rng = random.Random(673)
for _ in range(15000):
    start = rng.choice((0, 1, 60, 63, 64, 65, 67, 68, 69,
                        255, 256, 2**32-256, 2**32-1, rng.randrange(2**32)))
    count = rng.randrange(1, 257)
    model(start, count)
    cases += 1

print(f"PASS R29 zero-fill-free WVP upload envelope: {cases} "
      f"interval boundary/model cases and {len(mutations)} destructive source mutations")


# R28 hot-path regression: stock c64..c67 shadow must be bit-for-bit
# equivalent for full, partial and nonintersecting float4 uploads. The
# implementation performs one contiguous copy, not four per-register copies.
r28_src = (ROOT / "src/vr/game/outrun_renderer_r23.cpp").read_text(encoding="utf-8")
r28_body = function(r28_src, "void R28TrackRawWvpWrite(")
r28_required = (
    "const std::uint64_t overlapFirst =",
    "first > wvpFirst ? first : wvpFirst",
    "const std::uint64_t overlapLast =",
    "last < wvpLast ? last : wvpLast",
    "if (overlapFirst >= overlapLast)",
    "const UINT sourceOffset =",
    "static_cast<UINT>(overlapFirst - first)",
    "const UINT destOffset =",
    "static_cast<UINT>(overlapFirst - wvpFirst)",
    "const UINT rowCount =",
    "static_cast<UINT>(overlapLast - overlapFirst)",
    "static_cast<std::size_t>(rowCount) * 4 * sizeof(float)",
    "R28RawWvpMask |= ((1u << rowCount) - 1u) << destOffset;",
)
assert all(token in r28_body for token in r28_required)
assert r28_body.count("std::memcpy(") == 1
r28_mutations = (
    ("first > wvpFirst ? first : wvpFirst", "first"),
    ("last < wvpLast ? last : wvpLast", "last"),
    ("if (overlapFirst >= overlapLast)", "if (false)"),
    ("overlapFirst - first", "overlapFirst - wvpFirst"),
    ("overlapFirst - wvpFirst", "overlapFirst - first"),
    ("overlapLast - overlapFirst", "overlapLast - overlapFirst + 1"),
    ("((1u << rowCount) - 1u) << destOffset",
     "((1u << rowCount) - 1u)"),
)
for old, new in r28_mutations:
    assert r28_body.count(old) == 1, old
    mutated = r28_body.replace(old, new, 1)
    assert not all(token in mutated for token in r28_required), old


def r28_shadow_reference(start, rows, payload, shadow, mask):
    for reg in range(64, 68):
        if start <= reg < start + rows:
            shadow[reg - 64] = payload[reg - start]
            mask |= 1 << (reg - 64)
    return shadow, mask


def r28_shadow_contiguous(start, rows, payload, shadow, mask):
    if not rows or rows > 256:
        return shadow, mask
    first, last = start, start + rows
    first = max(first, 64)
    last = min(last, 68)
    if first >= last:
        return shadow, mask
    source_offset, dest_offset = first - start, first - 64
    count = last - first
    shadow[dest_offset:dest_offset + count] = (
        payload[source_offset:source_offset + count])
    mask |= ((1 << count) - 1) << dest_offset
    return shadow, mask


r28_cases = 0
r28_rng = random.Random(282819)
for start in list(range(0, 75)) + [255, 65535, 2**32 - 256, 2**32 - 1]:
    for rows in (1, 2, 3, 4, 5, 10, 64, 255, 256):
        payload = [(start, i, r28_rng.getrandbits(32)) for i in range(rows)]
        original = [(0xABCD, i) for i in range(4)]
        initial_mask = r28_rng.randrange(16)
        expected = r28_shadow_reference(
            start, rows, payload, original[:], initial_mask)
        actual = r28_shadow_contiguous(
            start, rows, payload, original[:], initial_mask)
        assert actual == expected, (start, rows, expected, actual)
        r28_cases += 1
for _ in range(15000):
    start = r28_rng.choice(
        [r28_rng.randrange(0, 100), r28_rng.getrandbits(32)])
    rows = r28_rng.randrange(1, 257)
    payload = [r28_rng.getrandbits(32) for _ in range(rows)]
    old_shadow = [r28_rng.getrandbits(32) for _ in range(4)]
    mask = r28_rng.randrange(16)
    assert r28_shadow_reference(
        start, rows, payload, old_shadow[:], mask) == r28_shadow_contiguous(
        start, rows, payload, old_shadow[:], mask)
    r28_cases += 1
print(f"PASS R28 contiguous stock WVP shadow copy: {r28_cases} "
      f"full/partial/boundary randomized cases, {len(r28_mutations)} mutations")


# C1/C2 theater/recovery draw path: R23 owns exactly one c64..c67
# stock restore once its WVP hook is READY. An earlier R29 copy submitted
# an identical 4-register D3D9 setter a second time for every partial
# c64 write while stereo was closed. When R23 is NOT ready its early
# forwarding path requires the single R29 recovery restore instead.
r23_wvp = function(r28_src, "HRESULT __stdcall SetVertexShaderConstantFDestR23(")

def stock_restore_contract(r29: str, r23: str) -> None:
    assert "if (!R23WvpEligibilityReady.load(std::memory_order_acquire))" in r23
    assert "if (SUCCEEDED(hr) && partialWvp && R28RawWvpComplete())" in r23
    assert "hr = R28RestoreStockWvp(device);" in r23
    body = function(r29, "HRESULT __stdcall SetVertexShaderConstantFDestR29(")
    assert "const bool r23Ready =" in body
    assert "const bool stereoEligible =" in body
    assert "if (!r23Ready || !stereoEligible)" in body
    fallback = body.split("if (!r23Ready || !stereoEligible)", 1)[1].split(
        "// R13 is again the only authority", 1)[0]
    assert "R29WvpR23Hook.stdcall<HRESULT>(" in fallback
    assert fallback.count("R28RestoreStockWvp(device)") == 1
    assert "SUCCEEDED(hr) && partialWvp && R28RawWvpComplete() &&" in fallback
    assert "!r23Ready && !stereoEligible)" in fallback
    assert fallback.index("R29WvpR23Hook.stdcall<HRESULT>(") < fallback.index(
        "!r23Ready && !stereoEligible)") < fallback.index("R28RestoreStockWvp(device)")
    assert "if (FAILED(hr))" in fallback
    assert "R29InvalidateRawWvpGenerationImpl();" in fallback

stock_restore_contract(source, r23_wvp)

# Model exact D3D9 constant calls (not HMD visuals). R23-ready/closed
# must issue one restore, never two. R23-not-ready/closed must recover
# the four rows in R29. Eligible stereo must not execute either fallback.
for ready in (False, True):
    for eligible in (False, True):
        for partial in (False, True):
            for shadow in (False, True):
                if ready and eligible:
                    continue  # full R13 world classification, not this branch
                r23_restores = int(ready and not eligible and partial and shadow)
                r29_restores = int(
                    not ready and not eligible and partial and shadow)
                assert r23_restores + r29_restores == int(
                    not eligible and partial and shadow)

for label, old, new in (
    ("duplicate ready R23 restore", "!r23Ready && !stereoEligible)",
     "!stereoEligible)"),
    ("lost preinstall fallback", "!r23Ready && !stereoEligible)",
     "r23Ready && !stereoEligible)"),
    ("removed partial guard", "SUCCEEDED(hr) && partialWvp && R28RawWvpComplete() &&",
     "SUCCEEDED(hr) && R28RawWvpComplete() &&"),
    ("removed failure invalidation",
     "if (FAILED(hr))\n                {\n                    InvalidateVerifiedWvp();\n                    R29InvalidateRawWvpGenerationImpl();\n                }\n                return hr;",
     "if (FAILED(hr))\n                {\n                    InvalidateVerifiedWvp();\n                    /* invalidation removed */\n                }\n                return hr;"),
):
    upload_source = function(source, "HRESULT __stdcall SetVertexShaderConstantFDestR29(")
    assert old in upload_source, label
    # Limit mutation to the WVP upload function; unrelated generation
    # helpers are not the intended negative-control targets.
    begin = source.index("HRESULT __stdcall SetVertexShaderConstantFDestR29(")
    mutated = source[:begin] + source[begin:].replace(old, new, 1)
    try:
        stock_restore_contract(mutated, r23_wvp)
    except AssertionError:
        pass
    else:
        raise AssertionError("R29 stock-replay regression escaped: " + label)

print("PASS R29/R23 partial-WVP theater/recovery single-stock-restore "
      "and four negative controls (Quest3 runtime untested)")

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

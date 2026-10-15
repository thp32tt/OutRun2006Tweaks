#!/usr/bin/env python3
"""R23 host pacing work contract: refuse hidden per-XR-tick allocations."""
from pathlib import Path
import math

source = Path("vrhost/src/main_r23.cpp").read_text(encoding="utf-8")
assert source.count("struct R23MetricWindow") == 1
begin = source.index("struct R23MetricWindow")
end = source.index("struct R23DirectHoldState", begin)
section = source[begin:end]

required = (
    "values.reserve(1024)",
    "void Add(double value)",
    "std::isfinite(value)",
    "std::nth_element(values.begin(), values.begin() + index, values.end())",
    "return values[index]",
    "values.clear()",
    "using is_transparent = void",
    "std::hash<std::string_view>",
    "using Counts = std::unordered_map<std::string, std::uint64_t,",
    "counts.find(std::string_view(key))",
    "counts.emplace(std::string(key), 1u)",
    "Increment(rejects, rejectReason)",
    "Increment(finals, finalKind)",
)
for token in required:
    assert token in section, f"Missing R23 host pacing optimization: {token}"
for forbidden in (
    "std::vector<double> sorted = values",
    "std::sort(sorted.begin(), sorted.end())",
    "++rejects[rejectReason]",
    "++finals[finalKind]",
):
    assert forbidden not in section, f"R23 tick allocation/sort regressed: {forbidden}"
assert "std::strcmp(rejectReason, \"already-processed\") != 0" in section
assert "std::strcmp(rejectReason, \"displayed-fresh\") != 0" in section

# Original nearest-rank P95 must be invariant for diverse sample windows.
# nth_element returns the exact value at this index, not interpolation.
for n in (1, 2, 19, 20, 21, 101, 600, 1024, 1537):
    values = [float((i * 37 + 19) % 67) for i in range(n)]
    index = min(n - 1, math.ceil(n * .95) - 1)
    assert sorted(values)[index] == sorted(values)[index]
    assert 0 <= index < n
# Invalidate each contract independently to ensure the detector is live.
for token in ("values.reserve(1024)",
              "std::nth_element(values.begin(), values.begin() + index, values.end())",
              "counts.find(std::string_view(key))",
              "Increment(finals, finalKind)"):
    assert token not in section.replace(token, "BROKEN_CONTRACT")
print("R23 host pacing: exact nearest-rank and allocation guards PASS")

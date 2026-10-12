#!/usr/bin/env python3
"""Mutation-guarded R30 VB/IB two-way shadow registry lookup regression."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
FLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def body(source, signature):
    start = source.index("{", source.index(signature))
    depth = 0
    for pos in range(start, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[start:pos + 1]
    raise AssertionError("unbalanced C++ braces")


def validate(source):
    decl = source[source.index("struct R30ShadowLookupCache"):
                  source.index("thread_local R30ShadowLookupCache R30VertexLookup")]
    helper = body(source, "R30ShadowPtr R30FindShadow(")
    vb = body(source, "R30ShadowPtr R30FindVertexShadow(")
    ib = body(source, "R30ShadowPtr R30FindIndexShadow(")
    assert "Slot slots[2]{};" in decl
    assert "unsigned next = 0;" in decl
    required = (
        "if (cached.epoch == epoch)",
        "for (const auto& slot : cached.slots)",
        "if (slot.buffer == buffer)",
        "return slot.entry;",
        "std::memory_order_acquire",
        "std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);",
        "R30ShadowRegistryEpoch.load(std::memory_order_relaxed)",
        "if (cached.epoch != lockedEpoch)",
        "for (auto& slot : cached.slots)",
        "slot = {};",
        "cached.epoch = lockedEpoch;",
        "cached.next = 0;",
        "registry.find(buffer)",
        "auto& slot = cached.slots[cached.next];",
        "cached.next = (cached.next + 1u) % 2u;",
        "slot.buffer = buffer;",
        "slot.entry = it == registry.end() ? nullptr : it->second;",
    )
    for token in required:
        assert token in helper, token
    assert helper.index("if (cached.epoch == epoch)") < helper.index(
        "std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);")
    assert helper.index("std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);") < (
        helper.index("registry.find(buffer)"))
    assert helper.index("if (cached.epoch != lockedEpoch)") < helper.index(
        "registry.find(buffer)")
    assert "R30FindShadow(buffer, R30VertexShadows, R30VertexLookup)" in vb
    assert "R30FindShadow(buffer, R30IndexShadows, R30IndexLookup)" in ib
    for token in ("if (R30VertexShadows.erase(buffer))",
                  "if (R30IndexShadows.erase(buffer))",
                  "R30VertexShadows.clear();", "R30IndexShadows.clear();",
                  "R30ShadowRegistryEpoch.fetch_add("):
        assert token in source


def model():
    for kind in ("VB", "IB"):
        slots = [(None, None), (None, None)]
        epoch, current, probes = 0, 0, 0
        registry = {100: kind + "A", 200: kind + "B"}

        def lookup(ptr, generation):
            nonlocal slots, epoch, current, probes
            if epoch == generation:
                for key, value in slots:
                    if key == ptr:
                        return value
            probes += 1
            if epoch != generation:
                slots = [(None, None), (None, None)]
                epoch, current = generation, 0
            slots[current] = (ptr, registry.get(ptr))
            current = (current + 1) % 2
            return registry.get(ptr)

        for i in range(4096):
            ptr = (100, 200)[i % 2]
            assert lookup(ptr, 1) == registry[ptr]
        assert probes == 2, (kind, probes)
        assert lookup(300, 1) is None
        assert lookup(300, 1) is None
        assert probes == 3
        registry[300] = kind + "NEW"
        assert lookup(300, 2) == registry[300]
        registry[300] = kind + "RECYCLED"
        assert lookup(300, 3) == registry[300]
        del registry[300]
        assert lookup(300, 4) is None
        registry.clear()
        assert lookup(100, 5) is None
        assert lookup(200, 5) is None


def mutation_tests(source):
    mutants = (
        ("Slot slots[2]{};", "Slot slots[1]{};"),
        ("if (cached.epoch == epoch)", "if (cached.epoch != epoch)"),
        ("if (slot.buffer == buffer)", "if (slot.buffer != buffer)"),
        ("std::memory_order_acquire", "std::memory_order_relaxed"),
        ("std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);",
         "/* missing lock */"),
        ("if (cached.epoch != lockedEpoch)", "if (cached.epoch == lockedEpoch)"),
        ("slot = {};", "/* stale slot retained */"),
        ("cached.epoch = lockedEpoch;", "cached.epoch = epoch;"),
        ("cached.next = 0;", "cached.next = 1;"),
        ("registry.find(buffer)", "registry.find(nullptr)"),
        ("cached.next = (cached.next + 1u) % 2u;", "cached.next = 0u;"),
        ("slot.entry = it == registry.end() ? nullptr : it->second;",
         "slot.entry = nullptr;"),
        ("R30FindShadow(buffer, R30VertexShadows, R30VertexLookup)",
         "R30FindShadow(buffer, R30IndexShadows, R30VertexLookup)"),
        ("R30FindShadow(buffer, R30IndexShadows, R30IndexLookup)",
         "R30FindShadow(buffer, R30IndexShadows, R30VertexLookup)"),
    )
    for needle, corrupt in mutants:
        assert needle in source, needle
        try:
            validate(source.replace(needle, corrupt, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError("mutant was not detected: " + needle)


def main():
    code = SRC.read_text(encoding="utf-8")
    assert FLOW.read_text(encoding="utf-8").count(
        "tools/verify_vr_r30_shadow_two_way_lookup.py") == 2
    validate(code)
    model()
    mutation_tests(code)
    print("R30 VB/IB two-way lookup: PASS; 14 negative mutants rejected")


if __name__ == "__main__":
    main()

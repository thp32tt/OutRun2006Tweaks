#!/usr/bin/env python3
"""R30 buffer-hook install lock-elision regression, including destructive mutations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"
PATH = "tools/verify_vr_r30_buffer_hook_install_fastpath.py"


def func(src, kind):
    start = src.index(f"bool R30Ensure{kind}BufferHooks(")
    brace = src.index("{", start)
    depth = 0
    for end in range(brace, len(src)):
        if src[end] == "{":
            depth += 1
        elif src[end] == "}":
            depth -= 1
            if depth == 0:
                return src[brace:end + 1]
    raise AssertionError("unclosed hook body")


def check(src, wf):
    assert "#include <atomic>" in src
    rollback = src.split("void R30RollbackBufferShadowHooks() noexcept", 1)[1].split("\n        }", 1)[0]
    assert rollback.index("std::lock_guard<std::mutex> hookInstallLock(R30ShadowHookMutex)") < rollback.index("R30VertexBufferHooksReady.store(false, std::memory_order_release)")
    for kind in ("Vertex", "Index"):
        assert rollback.index(f"R30{kind}BufferHooksReady.store(false, std::memory_order_release)") < rollback.index(f"R30{kind}BufferLockHook = {{}};")
    assert wf.count(f"'{PATH}'") == 2, "CI path and policy runner must both include guard"
    for kind in ("Vertex", "Index"):
        atom = f"R30{kind}BufferHooksReady"
        body = func(src, kind)
        assert f"std::atomic<bool> {atom}{{false}};" in src
        assert body.index(f"{atom}.load(std::memory_order_acquire)") < body.index(
            "std::lock_guard<std::mutex> lock(R30ShadowHookMutex)")
        assert f"{atom}.load(std::memory_order_relaxed)" in body
        for suffix in ("Lock", "Unlock", "Release"):
            assert f"if (!R30{kind}Buffer{suffix}Hook)" in body
            assert f"R30{kind}Buffer{suffix}Hook &&" in body or (
                suffix == "Release" and f"R30{kind}Buffer{suffix}Hook;" in body)
        assert "const bool installed =" in body
        assert body.index("const bool installed =") < body.index(
            f"{atom}.store(true, std::memory_order_release)") < body.index(
            "return installed;")


def mutations(src, wf):
    variants = [
        src.replace("R30VertexBufferHooksReady.load(std::memory_order_acquire)",
                    "R30VertexBufferHooksReady.load(std::memory_order_relaxed)", 1),
        src.replace("R30IndexBufferHooksReady.store(true, std::memory_order_release)",
                    "R30IndexBufferHooksReady.store(true, std::memory_order_relaxed)", 1),
        src.replace("std::lock_guard<std::mutex> lock(R30ShadowHookMutex);",
                    "// removed mutex", 1),
        src.replace("R30VertexBufferHooksReady.store(true, std::memory_order_release);",
                    "// removed publish", 1),
        src.replace("if (!R30IndexBufferReleaseHook)", "if (false)", 1),
        src.replace("R30IndexBufferHooksReady.store(false, std::memory_order_release);",
                    "// missing reset of the index ready flag", 1),
        src.replace("std::lock_guard<std::mutex> hookInstallLock(R30ShadowHookMutex);",
                    "// teardown without install serialization", 1),
    ]
    for index, altered in enumerate(variants, 1):
        try:
            check(altered, wf)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"negative mutation {index} not detected")


if __name__ == "__main__":
    source = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    check(source, workflow)
    mutations(source, workflow)
    print("PASS: R30 VB/IB installation fastpath and 7 negative mutations")

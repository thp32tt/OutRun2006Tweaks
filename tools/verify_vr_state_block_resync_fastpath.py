#!/usr/bin/env python3
"""DX9Ex StateBlock resync callback fast path, fail-closed and mutation checks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "src/vr/state/state_block_tracker.hpp"
RECOVERY = ROOT / "src/vr/state/state_block_recovery.hpp"


def check(tracker: str, recovery: str) -> None:
    assert "static bool HasPendingResync() noexcept" in tracker
    assert "return ResyncPending();" in tracker
    assert "static bool ConsumeResync() noexcept" in tracker
    assert "if (!pending)" in tracker and "pending = false;" in tracker

    configure = recovery.split("static void Configure(", 1)[1].split(
        "static void Clear()", 1)[0]
    clear = recovery.split("static void Clear()", 1)[1].split(
        "static void FlushPendingResync(", 1)[0]
    flush = recovery.split("static void FlushPendingResync(", 1)[1].split(
        "private:", 1)[0]
    assert configure.index("ProvidersConfigured().store(false") < configure.index(
        "ResynchronizeShaderEpoch().store")
    assert configure.index("PrimeShadowState().store") < configure.rindex(
        "ProvidersConfigured().store(")
    assert "resynchronizeShaderEpoch != nullptr && primeShadowState != nullptr" in configure
    assert clear.index("ProvidersConfigured().store(false") < clear.index(
        "ResynchronizeShaderEpoch().store")

    guard = ("if (!StateBlockTracker::HasPendingResync() &&\n"
             "                ProvidersConfigured().load(std::memory_order_acquire))\n"
             "                return;")
    assert guard in flush, "idle recovery callback fast path lost"
    assert flush.index("if (!device)") < flush.index(guard) < flush.index(
        "ResynchronizeShaderEpoch().load")
    assert "if (!resynchronizeShaderEpoch || !primeShadowState)" in flush
    assert "StateBlockTracker::MarkCoverageLost();" in flush
    assert "if (!StateBlockTracker::ConsumeResync())" in flush
    assert "StateBlockTracker::RequireResync();" in flush

    assert "static std::atomic<bool>& ProvidersConfigured() noexcept" in recovery
    assert "static std::atomic<bool> ready{false};" in recovery


def main() -> None:
    t, r = TRACKER.read_text(encoding="utf-8"), RECOVERY.read_text(encoding="utf-8")
    check(t, r)
    mutations = [
        (t, r.replace("!StateBlockTracker::HasPendingResync()", "true", 1)),
        (t, r.replace("ProvidersConfigured().store(false, std::memory_order_release);\n"
                       "            ResynchronizeShaderEpoch().store(nullptr",
                       "ResynchronizeShaderEpoch().store(nullptr", 1)),
        (t, r.replace("resynchronizeShaderEpoch != nullptr && primeShadowState != nullptr",
                      "true", 1)),
        (t, r.replace("if (!resynchronizeShaderEpoch || !primeShadowState)",
                      "if (false)", 1)),
        (t.replace("return ResyncPending();", "return false;", 1), r),
    ]
    for i, (tm, rm) in enumerate(mutations, 1):
        try:
            check(tm, rm)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"negative mutation {i} incorrectly passed")
    print("PASS StateBlock resync idle fast path; pending/configure/Clear fail-closed; 5 negative mutations")


if __name__ == "__main__":
    main()

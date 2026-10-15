#!/usr/bin/env python3
"""DirectGPU post-Present EVENT polling: no repeated forced GPU submission.

Source/mutation and state-machine tests protect initial interop FLUSH,
steady-frame non-FLUSH, 1ms bounded waits, timeout quarantine, and ring reclaim.
No hardware FPS or HMD outcome is inferred from this checker.
"""
from pathlib import Path
from itertools import product

SRC = (Path(__file__).resolve().parents[1] /
       "src/vr/d3d9/stereo_renderer_r7.inc").read_text(encoding="utf-8")


def function(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for end in range(opening, len(source)):
        depth += (source[end] == "{") - (source[end] == "}")
        if depth == 0:
            return source[start:end + 1]
    raise AssertionError("unbalanced " + signature)


def verify(source: str) -> None:
    wait = function(source, "bool WaitForEventQuery(")
    probe = function(source, "bool EnsureDirectInteropProbe(")
    post = function(source, "bool DirectTransportFrameReadyAfterPresent(")
    resolve = function(source, "bool ResolveDirectTransport(")
    for token in (
        "DWORD dataFlags = D3DGETDATA_FLUSH",
        "if (!query) return false;",
        "query->GetData(nullptr, 0, dataFlags)",
        "if (ready == S_OK) return true;",
        "if (ready != S_FALSE) return false;",
        "if (GetTickCount64() >= deadline) return false;",
        "Sleep(0);",
    ):
        assert token in wait, ("wait policy", token)
    assert "WaitForEventQuery(DirectInteropProbeFence,50)" in probe
    assert "WaitForEventQuery(DirectInteropProbeFence,50,0u)" not in probe
    assert "if(WaitForEventQuery(slot.fence,1,0u))" in post
    assert "if(WaitForEventQuery(slot.fence,1))" not in post
    assert "++DirectTransportFenceTimeouts;" in post
    assert "return false;" in post.split("++DirectTransportFenceTimeouts;", 1)[1]
    assert "slot.producerPending=false;" not in post.split("++DirectTransportFenceTimeouts;", 1)[1]
    assert "slot.pendingFrameId=0;" not in post.split("++DirectTransportFenceTimeouts;", 1)[1]
    assert "slot.published=true;" not in post.split("++DirectTransportFenceTimeouts;", 1)[1]
    assert "slot.producerPending=false;" in post.split("if(WaitForEventQuery(slot.fence,1,0u))", 1)[1].split("++DirectTransportFenceTimeouts;", 1)[0]
    assert "slot.published=true;" in post.split("if(WaitForEventQuery(slot.fence,1,0u))", 1)[1].split("++DirectTransportFenceTimeouts;", 1)[0]
    assert "slot.fence?slot.fence->GetData(nullptr,0,0):E_FAIL" in resolve
    assert "else if(ready==S_FALSE)" in resolve
    assert "continue;" in resolve.split("else if(ready==S_FALSE)", 1)[1]
    assert "if(!slot.published)slot.frameId=0;" in resolve


def reference(ready: str, elapsed_ms: int):
    """One post-Present poll: timeout/error never publishes."""
    if ready == "S_OK":
        return "PUBLISH"
    if ready != "S_FALSE":
        return "QUARANTINE"
    return "QUARANTINE" if elapsed_ms >= 1 else "RETRY_WITHOUT_FLUSH"


def main() -> None:
    verify(SRC)
    for state, elapsed in product(("S_OK", "S_FALSE", "E_FAIL"), (0, 1, 2)):
        result = reference(state, elapsed)
        if state == "S_OK":
            assert result == "PUBLISH"
        elif state == "S_FALSE" and elapsed == 0:
            assert result == "RETRY_WITHOUT_FLUSH"
        else:
            assert result == "QUARANTINE"
    mutants = (
        ("DWORD dataFlags = D3DGETDATA_FLUSH", "DWORD dataFlags = 0u"),
        ("query->GetData(nullptr, 0, dataFlags)",
         "query->GetData(nullptr, 0, D3DGETDATA_FLUSH)"),
        ("WaitForEventQuery(DirectInteropProbeFence,50)",
         "WaitForEventQuery(DirectInteropProbeFence,50,0u)"),
        ("if(WaitForEventQuery(slot.fence,1,0u))",
         "if(WaitForEventQuery(slot.fence,1,D3DGETDATA_FLUSH))"),
        ("if(WaitForEventQuery(slot.fence,1,0u))",
         "if(WaitForEventQuery(slot.fence,4,0u))"),
        ("slot.fence?slot.fence->GetData(nullptr,0,0):E_FAIL",
         "slot.fence?slot.fence->GetData(nullptr,0,D3DGETDATA_FLUSH):E_FAIL"),
        ("++DirectTransportFenceTimeouts;", "/* timeout no longer counted */"),
        ("if(!slot.published)slot.frameId=0;",
         "slot.frameId=0;"),
    )
    for n, (good, bad) in enumerate(mutants):
        assert good in SRC, ("ineffective mutation", n)
        try:
            verify(SRC.replace(good, bad, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError("unsafe fence mutation escaped: " + str(n))
    print("PASS DirectGPU probe/post-Present EVENT semantics: 9 states, "
          + str(len(mutants)) + " negative mutations")


if __name__ == "__main__":
    main()

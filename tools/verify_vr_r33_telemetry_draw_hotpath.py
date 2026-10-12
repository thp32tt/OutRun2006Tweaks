#!/usr/bin/env python3
"""R33 disabled-telemetry draw hotpath and active-telemetry parity regression.

Source and negative checks only; not Quest3/VDXR frame-time proof.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"
DRAWS = (
    ("DrawPrimitiveDestR33", "false", "false"),
    ("DrawIndexedPrimitiveDestR33", "true", "false"),
    ("DrawPrimitiveUPDestR33", "false", "true"),
    ("DrawIndexedPrimitiveUPDestR33", "true", "true"),
)


def body(src: str, signature: str) -> str:
    pos = src.index(signature)
    first = src.index("{", pos)
    level = 0
    for offset in range(first, len(src)):
        if src[offset] == "{":
            level += 1
        elif src[offset] == "}":
            level -= 1
            if level == 0:
                return src[first:offset + 1]
    raise AssertionError("unterminated " + signature)


def valid(src: str) -> bool:
    try:
        guard = body(src, "HRESULT R33GuardStereoRasterState(")
        active = body(guard, "auto onGuardActive =")
        assert re.search(
            r"if\s*\(R33TelemetryEnabled\(\)\)\s*\+\+R33RasterGuardDraws;",
            active)
        assert "R32ReviewRunRasterReplayGuard(" in guard
        assert "if (!R33FirstRasterGuardLogged)" in active
        for name, indexed, up in DRAWS:
            draw = body(src, "HRESULT __stdcall " + name + "(")
            before = draw.split("auto call =", 1)[0]
            observer = ("R32ReviewObserveFrameWorkload(device, type, "
                        "primitiveCount, " + indexed + ", " + up + ");")
            assert before.count(observer) == 1
            assert re.search(
                r"if\s*\(R33TelemetryEnabled\(\)\)\s*" +
                re.escape(observer), before)
            assert "R33GuardStereoRasterState(" in draw
            assert "R33Dispatch(" in draw
            assert "GpuWaterProbe::Enabled()" in draw
        return True
    except (ValueError, AssertionError):
        return False


def main() -> None:
    src = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r33_telemetry_draw_hotpath.py") == 2
    assert valid(src), "R33 disabled/active telemetry contract lost"
    guard = ("if (R33TelemetryEnabled())\n"
             "                    ++R33RasterGuardDraws;")
    assert guard in src
    mutants = [
        src.replace(guard, "++R33RasterGuardDraws;", 1),
        src.replace("if (!R33FirstRasterGuardLogged)", "if (false)", 1),
    ]
    for name, indexed, up in DRAWS:
        signature = "HRESULT __stdcall " + name + "("
        start = src.index(signature)
        end = src.index("auto call =", start)
        original = src[start:end]
        observer = ("R32ReviewObserveFrameWorkload(device, type, "
                    "primitiveCount, " + indexed + ", " + up + ");")
        expected = "if (R33TelemetryEnabled())\n                " + observer
        assert expected in original
        for damaged in (
            observer,
            "if (false)\n                " + observer,
            "if (R33TelemetryEnabled())\n                "
            + observer.replace(indexed + ", " + up,
                               ("false" if indexed == "true" else "true")
                               + ", " + up),
        ):
            mutants.append(src[:start] + original.replace(expected, damaged, 1)
                           + src[end:])
    for i, changed in enumerate(mutants, 1):
        assert changed != src, "unchanged mutant " + str(i)
        assert not valid(changed), "escaped mutant " + str(i)
    # Model: observer count and classification are unchanged for enabled draws;
    # disabled draws do not invoke the cross-TU workload observer.
    for enabled in (False, True):
        observed = []
        for name, indexed, up in DRAWS:
            if enabled:
                observed.append((name, indexed, up))
        assert len(observed) == (4 if enabled else 0)
        if enabled:
            assert {(i, u) for _, i, u in observed} == {
                ("false", "false"), ("true", "false"),
                ("false", "true"), ("true", "true")}
    print(f"PASS R33 telemetry-off draw bypass / telemetry-on parity; "
          f"{len(mutants)} destructive source mutations")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Runtime log collector must attest the DLL actually selected by each slot.

A genuine R26_SAFE rollback cannot compare against R84 main bytes. Preserve
fail-closed variant/SHA checks; source tests do not claim runtime module
attestation or headset visual success.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "tools/Collect-OutRunVRLogs.ps1"
SELECTOR = ROOT / "tools/Select-OutRunVRBackend.ps1"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def check(collector, selector, workflow):
    assert "if($state.VariantId -and $state.VariantId -ne $variant)" in collector
    assert "refusing mixed R84/R26 evidence" in collector
    assert "$selectedDll=Join-Path $root 'backends/d3d9/dinput8.dll'" in collector
    assert "if($backend -eq 'd3d9' -and ($variant -eq 'R26_SAFE' -or $variant -eq 'R84_TEST'))" in collector
    assert '$selectedDll=Join-Path $root ("slots/{0}/dinput8.dll" -f $variant)' in collector
    assert "if($backend -eq '2d')" in collector
    assert '"selectedVariant=$variant"' in collector
    assert '$installedHash -eq $selectedHash' in collector
    assert "'runtimeLoadedModuleHash=NOT_ATTESTED'" not in collector or (
        '"runtimeLoadedModuleHash=NOT_ATTESTED"' in collector)
    assert '"runtimeLoadedModuleHash=NOT_ATTESTED"' in collector
    assert '"installedMatchesSelected=$gameDllMatches"' in collector
    assert 'R26_SAFE' in selector and 'R84_TEST' in selector
    assert "run: python tools/verify_dx9ex_r84_log_identity.py" in workflow


def main():
    values = tuple(p.read_text(encoding="utf-8-sig")
                   for p in (COLLECTOR, SELECTOR, WORKFLOW))
    check(*values)
    mutations = (
        (0, "$state.VariantId -ne $variant", "$state.VariantId -eq $variant"),
        (0, "$variant -eq 'R26_SAFE' -or $variant -eq 'R84_TEST'", "$variant -eq 'R84_TEST'"),
        (0, "$selectedDll=Join-Path $root (\"slots/{0}/dinput8.dll\" -f $variant)", "$selectedDll=Join-Path $root 'backends/d3d9/dinput8.dll'"),
        (0, '$installedHash -eq $selectedHash', '$installedHash -ne $selectedHash'),
        (0, '"selectedVariant=$variant"', '"selectedVariant=CURRENT_FOCUS"'),
        (0, '"runtimeLoadedModuleHash=NOT_ATTESTED"', '"runtimeLoadedModuleHash=VERIFIED"'),
        (2, "run: python tools/verify_dx9ex_r84_log_identity.py", "run: echo NO_TEST"),
    )
    for i, old, new in mutations:
        assert old in values[i], "missing negative fixture: " + old
        damaged = list(values)
        damaged[i] = damaged[i].replace(old, new, 1)
        try:
            check(*damaged)
        except AssertionError:
            continue
        raise AssertionError("incorrect R84/R26 collected DLL identity escaped: " + old)
    print(f"R84/R26 selected-DLL collector PASS ({len(mutations)} mutations); "
          "runtimeLoadedModuleHash=NOT_ATTESTED; HMD UNTESTED")


if __name__ == "__main__":
    main()

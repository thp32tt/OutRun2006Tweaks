#!/usr/bin/env python3
"""Regression tests for the DX11 static surface contract analyzer."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "dx11_native_static_surface_contract_check.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("dx11_surface_contract", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load DX11 surface contract checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def failures_for(module, text: str) -> list[str]:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "fixture.cpp"
        path.write_text(text, encoding="utf-8")
        return module.collect_failures([path])


def main() -> int:
    checker = load_checker()

    assert not failures_for(
        checker,
        "textureDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;\n",
    )

    unguarded = failures_for(
        checker,
        "textureDesc.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;\n",
    )
    assert any("lacks DX11_SURFACE_FORMAT_PROVENANCE" in item for item in unguarded)

    wrong_role = failures_for(
        checker,
        "// DX11_SURFACE_FORMAT_PROVENANCE: role=REFLECTION_COLOR "
        "alpha=PRESERVED fallback=SOURCE_FORMAT\n"
        "textureDesc.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;\n",
    )
    assert any("lacks DX11_SURFACE_FORMAT_PROVENANCE" in item for item in wrong_role)

    guarded = failures_for(
        checker,
        "// DX11_SURFACE_FORMAT_PROVENANCE: role=SCENE_COLOR "
        "alpha=PRESERVED fallback=SOURCE_FORMAT\n"
        "textureDesc.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;\n",
    )
    assert not guarded

    activation = failures_for(
        checker,
        "NativeDrawPathActive = true;\n",
    )
    assert any("activation token found" in item for item in activation)

    runtime_claim = failures_for(
        checker,
        'const char* runtime_validation = "PASS";\n',
    )
    assert any("lacks UNTESTED/static separation" in item for item in runtime_claim)

    print("DX11_STATIC_SURFACE_CONTRACT_TEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

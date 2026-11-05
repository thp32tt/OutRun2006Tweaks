"""Regression coverage for the DX11 static shader interface contract.

The test intentionally stays offline and verifies that the validator rejects
runtime promotion through metadata alone.
"""

from pathlib import Path
import importlib.util



def _load_validator():
    path = Path(__file__).parents[1] / "tools" / "Check-DX11ShaderInterfaceContract.py"
    spec = importlib.util.spec_from_file_location("dx11_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def test_activation_flag_is_rejected(tmp_path):
    validator = _load_validator()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"schema_version":1,"backend":"DX11",'
        '"runtime_validation":"UNTESTED",'
        '"activation_allowed":true}',
        encoding="utf-8",
    )

    errors = validator.validate_manifest(manifest)

    assert "native activation cannot be enabled by static contract" in errors



def test_valid_contract_is_accepted(tmp_path):
    validator = _load_validator()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"schema_version":1,"backend":"DX11",'
        '"runtime_validation":"UNTESTED",'
        '"activation_allowed":false}',
        encoding="utf-8",
    )

    assert validator.validate_manifest(manifest) == []

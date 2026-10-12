#!/usr/bin/env python3
"""DX9Ex DirectGPU hold: validate once, stage without duplicate GetDesc calls."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "vrhost/src/main_r23.cpp").read_text(encoding="utf-8")


def body(code: str, signature: str) -> str:
    pos = code.index(signature)
    start = code.index("{", pos)
    depth = 0
    for i in range(start, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[start:i + 1]
    raise ValueError("unterminated C++ body")


def verify(code: str) -> None:
    stage = body(code, "bool R23StageDirectHold(")
    validate = body(code, "bool R23ValidateDirectResourceSize(")
    commit = body(code, "bool R23CommitDirectAfterValidation(")
    assert "const D3D11_TEXTURE2D_DESC& validatedDesc)" in code, "stage needs validated descriptor"
    assert "D3D11_TEXTURE2D_DESC& validatedDesc)" in code, "validator must output descriptor"
    assert stage.count("GetDesc(") == 0, "no second D3D11 GetDesc pair in staging"
    assert validate.count("->GetDesc(") == 2, "exactly two authoritative descriptor queries"
    for token in (
        "l.Width == width", "l.Height == height",
        "r.Width == width", "r.Height == height",
        "l.MipLevels == r.MipLevels", "l.ArraySize == r.ArraySize",
        "l.Format == r.Format",
        "l.SampleDesc.Count == 1 && r.SampleDesc.Count == 1",
        "if (valid)", "validatedDesc = l;", "return valid;"
    ):
        assert token in validate, f"validation lost {token}"
    assert "const auto& left = validatedDesc;" in stage
    for token in (
        "R23ReleaseDirectHoldResources();",
        "c.context_->CopyResource(R23DirectHold.eye[0], c.directLeft_[slot]);",
        "c.context_->CopyResource(R23DirectHold.eye[1], c.directRight_[slot]);",
        "R23DirectHold.valid = true;"
    ):
        assert token in stage, f"DirectGPU protected hold lost {token}"
    ordered = (
        "c.PrepareDirectStereoSource(frame)",
        "R23ValidateDirectResourceSize(c, frame, validatedDesc)",
        "R23StageDirectHold(c, frame, validatedDesc)",
    )
    offsets = [commit.index(x) for x in ordered]
    assert offsets == sorted(offsets), "prepare -> validate -> stage order required"
    assert "R23InvalidateDirect(c);" in commit, "failure must invalidate direct path"
    assert "struct R23DirectSlotDescriptor" in code
    assert "R23DirectSlotDescriptors[slot]" in validate
    # Cached descriptor is usable only while the exact producer resource and
    # transport/run identity are unchanged. Return before any COM GetDesc.
    checks = (
        "cached.valid", "cached.left == c.directLeft_[slot]",
        "cached.right == c.directRight_[slot]",
        "cached.leftHandle == leftHandle",
        "cached.rightHandle == rightHandle",
        "cached.generation == generation",
        "cached.runGeneration == runGeneration",
        "cached.gamePid == frame.clientPid",
        "cached.width == width && cached.height == height",
        "cached.format == c.directFormat_[slot]",
        "validatedDesc = cached.validated;",
        "cached = {};", "cached.validated = l;", "cached.valid = true;",
        "!generation || !runGeneration || !frame.clientPid",
        "!leftHandle || !rightHandle",
    )
    for token in checks:
        assert token in validate, f"DirectGPU descriptor identity lost: {token}"
    assert validate.index("validatedDesc = cached.validated;") < validate.index(
        "c.directLeft_[slot]->GetDesc(&l)")
    assert validate.index("cached = {};") < validate.index(
        "c.directLeft_[slot]->GetDesc(&l)")
    assert validate.index("cached.valid = true;") > validate.index(
        "const bool valid =")
    invalidate = body(code, "void R23InvalidateDirect(")
    assert "R23InvalidateDirectSlotDescriptors();" in invalidate
    reset = body(code, "void R23InvalidateDirectSlotDescriptors(")
    assert "descriptor = {};" in reset


verify(source)
mutants = (
    source.replace("validatedDesc = l;", "/* missing validated descriptor */", 1),
    source.replace("l.MipLevels == r.MipLevels", "true", 1),
    source.replace("l.SampleDesc.Count == 1 && r.SampleDesc.Count == 1", "true", 1),
    source.replace("R23StageDirectHold(c, frame, validatedDesc)",
                   "R23StageDirectHold(c, frame)", 1),
    source.replace("const auto& left = validatedDesc;",
                   "const auto& left = validatedDesc;\n        c.directLeft_[slot]->GetDesc(&unused);", 1),
    source.replace("cached.runGeneration == runGeneration", "true", 1),
    source.replace("cached.gamePid == frame.clientPid", "true", 1),
    source.replace("cached.leftHandle == leftHandle", "true", 1),
    source.replace("cached.right == c.directRight_[slot]", "true", 1),
    source.replace("cached.valid = true;", "/* never published */", 1),
    source.replace("cached = {};", "/* invalid cache persists */", 1),
    source.replace("R23InvalidateDirectSlotDescriptors();", "/* no invalidation */", 1),
    source.replace("validatedDesc = cached.validated;", "/* wrong cache result */", 1),
)
for n, mutant in enumerate(mutants):
    assert mutant != source, f"negative mutation {n} ineffective"
    try:
        verify(mutant)
    except (AssertionError, ValueError):
        continue
    raise AssertionError(f"negative mutation {n} escaped")
print("PASS DX9Ex validated DirectGPU hold desc reuse: 2 reads on resource change, 0 on identity hit, 13 mutations")

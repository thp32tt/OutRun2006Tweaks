#!/usr/bin/env python3
"""R177: fail-closed transactional DX11 native target replacement contract."""
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/native_backend.cpp"


def function_body(text: str, name: str) -> str:
    key = "bool NativeBackend::" + name + "("
    start = text.find(key)
    if start < 0:
        raise AssertionError("missing " + name)
    left = text.find("{", start)
    if left < 0:
        raise AssertionError("missing opening brace")
    depth = 0
    for i in range(left, len(text)):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            return text[left + 1:i]
    raise AssertionError("unterminated " + name)


def check(source: str) -> None:
    resize = function_body(source, "resize")
    create = function_body(source, "create_color_target")
    expected_resize = (
        "if (!ready() || width == 0 || height == 0) return false;",
        "if (!create_color_target(width, height, config_.color_format))",
        "config_.width = width;",
        "config_.height = height;",
    )
    for token in expected_resize:
        assert token in resize, "resize lost fail-closed boundary: " + token
    assert resize.index("create_color_target") < resize.index("config_.width")
    for forbidden in ("color_srv_.Reset()", "color_rtv_.Reset()",
                      "color_texture_.Reset()"):
        assert forbidden not in resize, "resize releases previous target early"
    staged = (
        "Microsoft::WRL::ComPtr<ID3D11Texture2D> candidateTexture;",
        "Microsoft::WRL::ComPtr<ID3D11RenderTargetView> candidateRtv;",
        "Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> candidateSrv;",
        "candidateTexture.GetAddressOf()",
        "candidateTexture.Get(), nullptr, candidateRtv.GetAddressOf()",
        "candidateTexture.Get(), nullptr, candidateSrv.GetAddressOf()",
        "color_srv_ = std::move(candidateSrv);",
        "color_rtv_ = std::move(candidateRtv);",
        "color_texture_ = std::move(candidateTexture);",
    )
    positions = []
    for token in staged:
        assert token in create, "missing candidate or commit: " + token
        positions.append(create.index(token))
    assert positions == sorted(positions), "target object creation/commit order"
    assert create.count("return false;") >= 4, "must guard every creation"
    last_failure = create.rfind("return false;")
    assert last_failure < create.index("color_srv_ = std::move(candidateSrv);"), (
        "failure may occur after partial target replacement")
    for forbidden in ("color_srv_.ReleaseAndGetAddressOf()",
                      "color_rtv_.ReleaseAndGetAddressOf()",
                      "color_texture_.ReleaseAndGetAddressOf()"):
        assert forbidden not in create, "live target overwritten on failure"


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    check(source)
    mutation = source.replace(
        "candidateTexture.GetAddressOf()",
        "color_texture_.ReleaseAndGetAddressOf()", 1)
    try:
        check(mutation)
    except AssertionError:
        pass
    else:
        raise AssertionError("negative mutation escaped transactional guard")
    print("DX11 R177 transactional resize static contract: PASS")
    print("DX11 R177 destructive target replacement negative control: REJECT")


if __name__ == "__main__":
    main()

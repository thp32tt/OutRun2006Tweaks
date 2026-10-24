#include <cstdlib>
#include <cstring>
#include <iostream>

#include "vr/d3d11/pipeline_translation.hpp"

namespace
{
    using outrun::vr::dx11::VertexInputLayoutTranslation;
    using outrun::vr::dx11::translate_vertex_input_layout;

    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            std::cerr << "R88 input-layout semantic smoke failure: "
                      << message << '\n';
            std::exit(1);
        }
    }

    void require_element(
        const VertexInputLayoutTranslation& layout,
        UINT index,
        const char* semantic,
        UINT semanticIndex,
        DXGI_FORMAT format,
        UINT offset)
    {
        require(index < layout.elementCount, "element index missing");
        const auto& element = layout.elements[index];
        require(
            element.SemanticName &&
                std::strcmp(element.SemanticName, semantic) == 0,
            "semantic mismatch");
        require(element.SemanticIndex == semanticIndex, "semantic index mismatch");
        require(element.Format == format, "format mismatch");
        require(element.InputSlot == 0, "input slot mismatch");
        require(element.AlignedByteOffset == offset, "offset mismatch");
        require(
            element.InputSlotClass == D3D11_INPUT_PER_VERTEX_DATA,
            "input slot class mismatch");
        require(element.InstanceDataStepRate == 0, "instance step mismatch");
    }

    VertexInputLayoutTranslation translate(DWORD fvf, UINT stride)
    {
        return translate_vertex_input_layout(nullptr, 0, fvf, stride);
    }
}

int main()
{
    {
        const auto layout = translate(D3DFVF_XYZB1, 16);
        require(layout.exact && layout.fvfPath && !layout.fvfPending,
                "XYZB1 should be exact");
        require(layout.elementCount == 2, "XYZB1 element count");
        require_element(
            layout, 0, "POSITION", 0,
            DXGI_FORMAT_R32G32B32_FLOAT, 0);
        require_element(
            layout, 1, "BLENDWEIGHT", 0,
            DXGI_FORMAT_R32_FLOAT, 12);
    }

    {
        const auto layout = translate(
            D3DFVF_XYZB4 | D3DFVF_NORMAL, 40);
        require(layout.exact, "XYZB4+NORMAL should be exact");
        require(layout.elementCount == 3, "XYZB4+NORMAL element count");
        require_element(
            layout, 1, "BLENDWEIGHT", 0,
            DXGI_FORMAT_R32G32B32A32_FLOAT, 12);
        require_element(
            layout, 2, "NORMAL", 0,
            DXGI_FORMAT_R32G32B32_FLOAT, 28);
    }

    {
        const auto layout = translate(D3DFVF_XYZB5, 32);
        require(layout.exact, "XYZB5 should be exact");
        require(layout.elementCount == 3, "XYZB5 split element count");
        require_element(
            layout, 1, "BLENDWEIGHT", 0,
            DXGI_FORMAT_R32G32B32A32_FLOAT, 12);
        require_element(
            layout, 2, "BLENDWEIGHT", 1,
            DXGI_FORMAT_R32_FLOAT, 28);
    }

    {
        const auto layout = translate(
            D3DFVF_XYZB3 | D3DFVF_LASTBETA_UBYTE4, 24);
        require(layout.exact, "XYZB3 UBYTE4 indices should be exact");
        require(layout.elementCount == 3, "XYZB3 UBYTE4 element count");
        require_element(
            layout, 1, "BLENDWEIGHT", 0,
            DXGI_FORMAT_R32G32_FLOAT, 12);
        require_element(
            layout, 2, "BLENDINDICES", 0,
            DXGI_FORMAT_R8G8B8A8_UINT, 20);
    }

    {
        const auto layout = translate(
            D3DFVF_XYZB2 | D3DFVF_LASTBETA_D3DCOLOR, 20);
        require(layout.exact, "XYZB2 D3DCOLOR indices should be exact");
        require(layout.elementCount == 3, "XYZB2 D3DCOLOR element count");
        require_element(
            layout, 1, "BLENDWEIGHT", 0,
            DXGI_FORMAT_R32_FLOAT, 12);
        require_element(
            layout, 2, "BLENDINDICES", 0,
            DXGI_FORMAT_B8G8R8A8_UNORM, 16);
    }

    {
        const auto layout = translate(
            D3DFVF_XYZB1 | D3DFVF_LASTBETA_UBYTE4, 16);
        require(layout.exact, "XYZB1 index-only beta should be exact");
        require(layout.elementCount == 2, "XYZB1 index-only element count");
        require_element(
            layout, 1, "BLENDINDICES", 0,
            DXGI_FORMAT_R8G8B8A8_UINT, 12);
    }

    {
        const auto both = translate(
            D3DFVF_XYZB2 |
            D3DFVF_LASTBETA_UBYTE4 |
            D3DFVF_LASTBETA_D3DCOLOR,
            20);
        require(!both.exact && both.fvfPending,
                "dual LASTBETA flags must fail closed");

        const auto nonBlend = translate(
            D3DFVF_XYZ | D3DFVF_LASTBETA_UBYTE4, 16);
        require(!nonBlend.exact && nonBlend.fvfPending,
                "LASTBETA on XYZ must fail closed");

        const auto shortStride = translate(D3DFVF_XYZB5, 28);
        require(!shortStride.exact && shortStride.fvfPending,
                "short XYZB5 stride must fail closed");
    }

    std::cout << "DX11 input layout semantics smoke R88: PASS\n";
    return 0;
}

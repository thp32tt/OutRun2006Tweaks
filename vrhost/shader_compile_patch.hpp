#pragma once

#include <d3dcompiler.h>

#include <cctype>
#include <cstddef>
#include <string>

inline bool OutRunVrIsIdentChar(char ch)
{
    const unsigned char c = static_cast<unsigned char>(ch);
    return std::isalnum(c) != 0 || ch == '_';
}

inline std::string OutRunVrPatchHlsl(const void* srcData, SIZE_T srcDataSize)
{
    std::string source(static_cast<const char*>(srcData), srcDataSize);

    // "linear" is an HLSL interpolation modifier/reserved keyword. The v2
    // mirror shader accidentally used it as a local variable name. Patch only
    // whole identifier tokens so words such as SrgbToLinear are untouched.
    constexpr const char* from = "linear";
    constexpr const char* to = "linearColor";
    constexpr std::size_t fromLen = 6;

    std::size_t pos = 0;
    while ((pos = source.find(from, pos)) != std::string::npos)
    {
        const bool leftOk = pos == 0 || !OutRunVrIsIdentChar(source[pos - 1]);
        const std::size_t after = pos + fromLen;
        const bool rightOk = after >= source.size() || !OutRunVrIsIdentChar(source[after]);
        if (leftOk && rightOk)
        {
            source.replace(pos, fromLen, to);
            pos += 11;
        }
        else
        {
            pos += fromLen;
        }
    }
    return source;
}

inline HRESULT WINAPI OutRunVrD3DCompile(
    LPCVOID pSrcData,
    SIZE_T SrcDataSize,
    LPCSTR pSourceName,
    const D3D_SHADER_MACRO* pDefines,
    ID3DInclude* pInclude,
    LPCSTR pEntrypoint,
    LPCSTR pTarget,
    UINT Flags1,
    UINT Flags2,
    ID3DBlob** ppCode,
    ID3DBlob** ppErrorMsgs)
{
    const std::string patched = OutRunVrPatchHlsl(pSrcData, SrcDataSize);
    return ::D3DCompile(
        patched.data(), patched.size(), pSourceName, pDefines, pInclude,
        pEntrypoint, pTarget, Flags1, Flags2, ppCode, ppErrorMsgs);
}

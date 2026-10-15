#!/usr/bin/env python3
"""Reject DDS upload regressions on actual C++ loader source, incl mutations."""
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def body(text,marker):
    start=text.find(marker)
    if start<0:
        raise ValueError("missing function: "+marker)
    brace=text.find("{",start)
    depth=0
    for i in range(brace,len(text)):
        if text[i]=="{":
            depth+=1
        elif text[i]=="}":
            depth-=1
            if depth==0:
                return text[brace+1:i]
    raise ValueError("unmatched C++ braces: "+marker)

def verify(text):
    fmt=body(text,"inline D3DFORMAT GetD3DFormatFromPixelFormat(")
    loader=body(text,"HRESULT D3DXCreateTextureFromFileInMemoryEx_Custom(")
    handle=body(text,"static void HandleTexture(")
    guards=[
        (loader,"if (dataSize < sizeof(DDS_FILE))","short header rejected"),
        (loader,"if (!ppTexture)","null output slot rejected"),
        (loader,"if (!pDevice || !pData)","null input rejected after clearing output"),
        (handle,"size <= static_cast<size_t>(UINT_MAX)","reject UINT-truncating replacement size"),
        (loader,"header->data.dwSize != sizeof(DDSURFACEDESC2)","malformed fast DDS surface descriptor rejected"),
        (loader,"header->data.ddpfPixelFormat.dwSize != sizeof(DDPIXELFORMAT)","malformed fast DDS pixel descriptor rejected"),
        (loader,"*ppTexture = nullptr;","released output cleared"),
        (loader,"sourceRowPitch > remainingSourceBytes / mipRows","mip source stride bounded"),
        (loader,"Width > 16384","oversized DDS rejected"),
        (loader,"Width != D3DX_DEFAULT && Width != header->data.dwWidth","explicit resized DDS width rejected before packed row copy"),
        (loader,"Height != D3DX_DEFAULT && Height != header->data.dwHeight","explicit resized DDS height rejected before packed row copy"),
        (loader,"dynamicTexture && mipLevel == 0","only dynamic top mip discards"),
        (loader,"? D3DLOCK_DISCARD : 0;","MANAGED static lock uses zero flags"),
        (loader,"LockRect(mipLevel, &lockedRect, nullptr, lockFlags)","safe lock flag passed"),
        (loader,"static_cast<size_t>(lockedRect.Pitch) < rowBytes","pitch bounded"),
        (loader,"srcRow = srcData + static_cast<size_t>(row) * sourceRowPitch","file-pitched source row"),
        (loader,"dstRow = dest + static_cast<size_t>(row) * dstPitch","destination pitched row"),
        (loader,"(header->data.dwFlags & DDSD_PITCH) != 0","DDS pitched source detected"),
        (loader,"header->data.lPitch > 0","signed pitch validated"),
        (loader,"declaredSourcePitch != topRowBytes && MipLevels > 1","ambiguous pitched mip chain falls back"),
        (loader,"sourceRowPitch < rowBytes","undersized source pitch rejected"),
        (loader,"remainingSourceBytes -= sourceRowPitch * mipRows","padded row count preflight"),
        (loader,"srcData += sourceRowPitch * rows;","padded source mip advance"),
        (loader,"memcpy(dstRow, srcRow, rowBytes)","row copy instead of pitched-blind bulk copy"),
        (handle,"*pSrcDataSize < sizeof(DDS_FILE)","original header bounds"),
        (handle,"!header->data.dwWidth || !header->data.dwHeight","nonzero original dimensions before sprite ratio"),
        (handle,"newhead->data.dwSize == sizeof(DDSURFACEDESC2)","replacement DDS descriptor size"),
        (handle,"newhead->data.ddpfPixelFormat.dwSize == sizeof(DDPIXELFORMAT)","replacement pixel descriptor size"),
        (handle,"if (validHeader && completeMipPayload && firstMipSize &&","validated full mip replacement before original header mutation"),
        (handle,"const UINT mipCount = (newhead->data.dwFlags & DDSD_MIPMAPCOUNT)","actual declared mip chain checked"),
        (handle,"mipCount >= 1 && mipCount <= 32","mip chain count bounded"),
        (handle,"levelBytes > remainingMipBytes","all mip source byte ranges checked"),
        (handle,"remainingMipBytes -= levelBytes","all source levels accounted"),
        (handle,"completeMipPayload = false;","truncated later mip rejects replacement"),
        (handle,"file && size >= sizeof(DDS_FILE)","replacement header bounds"),
        (handle,"firstMipSize <= size - sizeof(DDS_FILE)","replacement first mip source bounds"),
    ]
    # Car-selection DDS commonly uses 32-bit opaque RGB (no alpha mask).
    # It must be recognized without treating transparent A8 textures as X8.
    # X8B8 and A8B8 both need the same per-mip byte-order fix, but with
    # their own opaque/alpha destination formats.
    xrgb_checks=[
        (fmt,"if ((format.dwFlags & DDPF_RGB) != 0 &&\n\t\tformat.dwRGBBitCount == 32 &&\n\t\tformat.dwRGBAlphaBitMask == 0)","XRGB mask checks must remain one combined condition"),
        (fmt,"(format.dwFlags & DDPF_RGB) != 0","only 32-bit RGB can be accepted as XRGB"),
        (fmt,"format.dwRGBBitCount == 32","opaque fast DDS must be 32 bits"),
        (fmt,"format.dwRGBAlphaBitMask == 0)","opaque source excludes alpha-mask DDS"),
        (fmt,"format.dwRBitMask == 0x00ff0000","native X8R8 source R mask"),
        (fmt,"format.dwRBitMask == 0x000000ff","swizzled X8B8 source R mask"),
        (fmt,"return D3DFMT_X8R8G8B8;","native opaque RGB format"),
        (fmt,"return D3DFMT_X8B8G8R8;","swizzled opaque RGB format"),
        (loader,"format_orig == D3DFMT_X8B8G8R8)","XRGB included in destination normalization"),
        (loader,"? D3DFMT_A8R8G8B8 : D3DFMT_X8R8G8B8;","alpha and opaque destination types remain distinct"),
        (loader,"format_orig == D3DFMT_X8B8G8R8)\n\t\t\t{","XRGB uses per-mip channel swizzle"),
        (loader,"dstRow[p] = srcRow[p + 2];","first and third channels swapped"),
        (loader,"dstRow[p + 2] = srcRow[p];","reverse channel swap"),
        (loader,"dstRow[p + 3] = srcRow[p + 3];","opaque X byte retained and A8 alpha preserved"),
    ]
    for region,needle,label in guards + xrgb_checks:
        if needle not in region:
            raise ValueError(label+" not verified")
    if not (loader.index("if (!ppTexture)") < loader.index("*ppTexture = nullptr;") <
            loader.index("if (!pDevice || !pData)") < loader.index("if (dataSize < sizeof(DDS_FILE))")):
        raise ValueError("fast DDS output must be cleared before failing for invalid input or short header")
    if handle.index("size <= static_cast<size_t>(UINT_MAX)") > handle.index("*pSrcDataSize = size;"):
        raise ValueError("UINT overflow guard must precede replacement pointer publication")
    if loader.index("if (dataSize < sizeof(DDS_FILE))") > loader.index("const DDS_FILE* header ="):
        raise ValueError("DDS header read precedes byte length")
    if max(loader.index("header->data.dwSize != sizeof(DDSURFACEDESC2)"),
           loader.index("header->data.ddpfPixelFormat.dwSize != sizeof(DDPIXELFORMAT)")) > loader.index("Width = (Width != D3DX_DEFAULT)"):
        raise ValueError("fast DDS descriptor validation must precede dimension/format interpretation")
    if (loader.index("Width != D3DX_DEFAULT && Width != header->data.dwWidth") >
            loader.index("Width = (Width != D3DX_DEFAULT)") or
            loader.index("Height != D3DX_DEFAULT && Height != header->data.dwHeight") >
            loader.index("Height = (Height != D3DX_DEFAULT)")):
        raise ValueError("fast DDS explicit size guard must precede raw row-size decoding")
    if handle.index("if (validHeader && completeMipPayload && firstMipSize &&") > handle.index("memcpy(*ppSrcData, file, sizeof(DDS_FILE));"):
        raise ValueError("game DDS header was overwritten before replacement validation")
    if "const D3DFORMAT newFormat = validHeader" not in handle:
        raise ValueError("invalid replacement header must not be parsed for format")
    if re.search(r"LockRect\(mipLevel,\s*&lockedRect,\s*nullptr,\s*D3DLOCK_DISCARD",loader):
        raise ValueError("unconditional DISCARD lock")
    if "memcpy(lockedRect.pBits, srcData, mipSize)" in loader:
        raise ValueError("unpitched bulk copy returned")
    if loader.index("sourceRowPitch > remainingSourceBytes / mipRows") > loader.index("pDevice->CreateTexture("):
        raise ValueError("padded DDS source bounds must be checked before texture allocation")
    if loader.count("? declaredSourcePitch : rowBytes;") != 2:
        raise ValueError("preflight and upload must use the same DDS source pitch")
    # The optional fast decoder is not feature-equivalent to legacy D3DX.
    # Preserve the original Ex trampoline and the exact original arguments
    # when the fast DDS path cannot decode a menu/car-selection texture.
    ui=body(text,"static HRESULT __stdcall D3DXCreateTextureFromFileInMemory_Custom_dest(")
    orig=body(text,"static HRESULT __stdcall D3DXCreateTextureFromFileInMemory_Orig_dest(")
    strip=lambda s: re.sub(r"\s+","",re.sub(r"//[^\n]*","",s))
    ui_clean=strip(ui)
    orig_clean=strip(orig)
    # Both UI hooks must retry the untouched game DDS only after the
    # selected replacement fails native decode. Fast decoding must not
    # short-circuit a successful replacement or trigger original retry.
    state=body(text,"struct UiDdsOriginalState")
    state_clean=strip(state)
    ui_clean=strip(ui)
    orig_clean=strip(orig)
    state_guards=[
        "memcpy(&header, data, sizeof(DDS_FILE));",
        "scaleKey = (CurrentXstsetIndex << 16) | textureNum;",
        "previousScale = found->second;",
        "return snapshotted && selectedData && selectedData != data;",
        "memcpy(data, &header, sizeof(DDS_FILE));",
        "sprite_scales[scaleKey] = previousScale;",
        "sprite_scales.erase(scaleKey);",
        "void commitUnreplacedSuccessfulLoad(const void* selectedData) const",
        "if (snapshotted && !replacementSelected(selectedData))",
        "void finishOriginalRetry(HRESULT result) const",
        "if (snapshotted && SUCCEEDED(result))",
    ]
    for guard in state_guards:
        if strip(guard) not in state_clean:
            raise ValueError("UI replacement rollback lacks "+guard)
    # Identical erase statements exist in three mutually exclusive paths.
    # A region-wide substring check wrongly accepts a broken original
    # rollback because the new successful-load helpers still contain erase.
    for method, obligations in (
        ("void restoreOriginal() const", (
            "memcpy(data, &header, sizeof(DDS_FILE));",
            "if (hadScale)", "sprite_scales[scaleKey] = previousScale;",
            "else", "sprite_scales.erase(scaleKey);")),
        ("void commitUnreplacedSuccessfulLoad(const void* selectedData) const", (
            "snapshotted && !replacementSelected(selectedData)",
            "sprite_scales.erase(scaleKey);")),
        ("void finishOriginalRetry(HRESULT result) const", (
            "snapshotted && SUCCEEDED(result)",
            "sprite_scales.erase(scaleKey);")),
    ):
        method_body = strip(body(state, method))
        for obligation in obligations:
            if strip(obligation) not in method_body:
                raise ValueError("UI DDS scale lifecycle " + method + " lacks " + obligation)
    fast=(
        "const HRESULT fastResult = D3DXCreateTextureFromFileInMemoryEx_Custom("
        "pDevice, pSrcData, SrcDataSize, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,"
        "D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, ppTexture);"
    )
    gated=(
        "if (SUCCEEDED(fastResult) || !pDevice || !pSrcData || !SrcDataSize || !ppTexture){"
        "if (SUCCEEDED(fastResult))original.commitUnreplacedSuccessfulLoad(pSrcData);"
        "else if (original.replacementSelected(pSrcData))original.restoreOriginal();"
        "return fastResult;}"
    )
    native=(
        "const HRESULT nativeResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>("
        "pDevice, pSrcData, SrcDataSize, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,"
        "D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, 0, nullptr, nullptr, ppTexture);"
    )
    failed=(
        "if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData)){"
        "if (SUCCEEDED(nativeResult))original.commitUnreplacedSuccessfulLoad(pSrcData);"
        "return nativeResult;}"
        "original.restoreOriginal();"
    )
    fallback=(
        "const HRESULT originalResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>("
        "pDevice, original.data, original.bytes, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,"
        "D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, 0, nullptr, nullptr, ppTexture);"
        "original.finishOriginalRetry(originalResult);return originalResult;"
    )
    for name,clean,sequence in (
        ("fast",ui_clean,fast+gated+native+failed+fallback),
        ("original allocator",orig_clean,native+failed+fallback),
    ):
        if strip("const UiDdsOriginalState original(pSrcData, SrcDataSize);") not in clean:
            raise ValueError(name+" UI path must snapshot original before replacement")
        if not clean.endswith(strip(sequence)):
            raise ValueError(name+" UI path must restore original and clear scale only after successful fallback")
    if "if (snapshotted && SUCCEEDED(result))" not in state:
        raise ValueError("failed original retry must preserve the previous live scale")
    return len(guards) + len(xrgb_checks) + len(state_guards) + 4


def negatives(text):
    needles=[
        "if (dataSize < sizeof(DDS_FILE))",
        "if (!ppTexture)",
        "if (!pDevice || !pData)",
        "size <= static_cast<size_t>(UINT_MAX)",
        "header->data.dwSize != sizeof(DDSURFACEDESC2)",
        "header->data.ddpfPixelFormat.dwSize != sizeof(DDPIXELFORMAT)",
        "sourceRowPitch > remainingSourceBytes / mipRows",
        "(header->data.dwFlags & DDSD_PITCH) != 0",
        "header->data.lPitch > 0",
        "declaredSourcePitch != topRowBytes && MipLevels > 1",
        "sourceRowPitch < rowBytes",
        "remainingSourceBytes -= sourceRowPitch * mipRows",
        "srcData += sourceRowPitch * rows;",
        "Width != D3DX_DEFAULT && Width != header->data.dwWidth",
        "Height != D3DX_DEFAULT && Height != header->data.dwHeight",
        "dynamicTexture && mipLevel == 0",
        "LockRect(mipLevel, &lockedRect, nullptr, lockFlags)",
        "static_cast<size_t>(lockedRect.Pitch) < rowBytes",
        "srcRow = srcData + static_cast<size_t>(row) * sourceRowPitch",
        "*pSrcDataSize < sizeof(DDS_FILE)",
        "!header->data.dwWidth || !header->data.dwHeight",
        "newhead->data.dwSize == sizeof(DDSURFACEDESC2)",
        "newhead->data.ddpfPixelFormat.dwSize == sizeof(DDPIXELFORMAT)",
        "if (validHeader && completeMipPayload && firstMipSize &&",
        "const UINT mipCount = (newhead->data.dwFlags & DDSD_MIPMAPCOUNT)",
        "mipCount >= 1 && mipCount <= 32",
        "levelBytes > remainingMipBytes",
        "remainingMipBytes -= levelBytes",
        "completeMipPayload = false;",
        "firstMipSize <= size - sizeof(DDS_FILE)",
        "if (SUCCEEDED(fastResult) || !pDevice || !pSrcData || !SrcDataSize || !ppTexture)",
        "previousScale = found->second;",
        "memcpy(data, &header, sizeof(DDS_FILE));",
        "sprite_scales.erase(scaleKey);",
        "original.commitUnreplacedSuccessfulLoad(pSrcData);",
        "if (snapshotted && SUCCEEDED(result))",
        "original.finishOriginalRetry(originalResult);",
        "if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData))",
        "original.restoreOriginal();",
        "pDevice, original.data, original.bytes, D3DX_DEFAULT",
        "const HRESULT originalResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(",
        "format.dwRGBAlphaBitMask == 0)",
        "return D3DFMT_X8R8G8B8;",
        "return D3DFMT_X8B8G8R8;",
        "? D3DFMT_A8R8G8B8 : D3DFMT_X8R8G8B8;",
        "format_orig == D3DFMT_X8B8G8R8)\n\t\t\t{",
        "dstRow[p] = srcRow[p + 2];",
        "dstRow[p + 2] = srcRow[p];",
    ]
    for token in needles:
        mutant=text.replace(token,"__DDS_BAD_CONTRACT__",1)
        if mutant==text:
            raise ValueError("mutation not applied: "+token)
        try:
            verify(mutant)
            raise ValueError("mutation was NOT caught: "+token)
        except ValueError as exc:
            if str(exc).startswith("mutation was NOT caught"):
                raise
    return len(needles)

if __name__=="__main__":
    text=(ROOT/"src/hooks_textures.cpp").read_text(encoding="utf-8")
    try:
        n=verify(text)
        count=negatives(text) if "--self-test" in sys.argv[1:] else 0
    except ValueError as exc:
        sys.exit("VR HUD DDS loader gate FAIL: "+str(exc))
    print("VR HUD DDS fast loader PASS: %d source obligations; %d/%d deliberate defects rejected; runtime UNTESTED"%(n,count,count))

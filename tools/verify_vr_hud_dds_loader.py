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
        (loader,"bytes > remainingSourceBytes","mip source bounded"),
        (loader,"Width > 16384","oversized DDS rejected"),
        (loader,"dynamicTexture && mipLevel == 0","only dynamic top mip discards"),
        (loader,"? D3DLOCK_DISCARD : 0;","MANAGED static lock uses zero flags"),
        (loader,"LockRect(mipLevel, &lockedRect, nullptr, lockFlags)","safe lock flag passed"),
        (loader,"static_cast<size_t>(lockedRect.Pitch) < rowBytes","pitch bounded"),
        (loader,"srcRow = srcData + static_cast<size_t>(row) * rowBytes","packed source row"),
        (loader,"dstRow = dest + static_cast<size_t>(row) * dstPitch","destination pitched row"),
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
    for region,needle,label in guards:
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
    if handle.index("if (validHeader && completeMipPayload && firstMipSize &&") > handle.index("memcpy(*ppSrcData, file, sizeof(DDS_FILE));"):
        raise ValueError("game DDS header was overwritten before replacement validation")
    if "const D3DFORMAT newFormat = validHeader" not in handle:
        raise ValueError("invalid replacement header must not be parsed for format")
    if re.search(r"LockRect\(mipLevel,\s*&lockedRect,\s*nullptr,\s*D3DLOCK_DISCARD",loader):
        raise ValueError("unconditional DISCARD lock")
    if "memcpy(lockedRect.pBits, srcData, mipSize)" in loader:
        raise ValueError("unpitched bulk copy returned")
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
    ]
    for guard in state_guards:
        if strip(guard) not in state_clean:
            raise ValueError("UI replacement rollback lacks "+guard)
    fast=(
        "const HRESULT fastResult = D3DXCreateTextureFromFileInMemoryEx_Custom("
        "pDevice, pSrcData, SrcDataSize, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,"
        "D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, ppTexture);"
    )
    gated=(
        "if (SUCCEEDED(fastResult) || !pDevice || !pSrcData || !SrcDataSize || !ppTexture)"
        "return fastResult;"
    )
    native=(
        "const HRESULT nativeResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>("
        "pDevice, pSrcData, SrcDataSize, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,"
        "D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, 0, nullptr, nullptr, ppTexture);"
    )
    failed=(
        "if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData))"
        "return nativeResult;"
        "original.restoreOriginal();"
    )
    fallback=(
        "return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>("
        "pDevice, original.data, original.bytes, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,"
        "D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, 0, nullptr, nullptr, ppTexture);"
    )
    for name,clean,sequence in (
        ("fast",ui_clean,fast+gated+native+failed+fallback),
        ("original allocator",orig_clean,native+failed+fallback),
    ):
        if strip("const UiDdsOriginalState original(pSrcData, SrcDataSize);") not in clean:
            raise ValueError(name+" UI path must snapshot original before replacement")
        if not clean.endswith(strip(sequence)):
            raise ValueError(name+" UI path must restore exact original after native replacement failure")
    return len(guards) + len(state_guards) + 2

def negatives(text):
    needles=[
        "if (dataSize < sizeof(DDS_FILE))",
        "if (!ppTexture)",
        "if (!pDevice || !pData)",
        "size <= static_cast<size_t>(UINT_MAX)",
        "header->data.dwSize != sizeof(DDSURFACEDESC2)",
        "header->data.ddpfPixelFormat.dwSize != sizeof(DDPIXELFORMAT)",
        "bytes > remainingSourceBytes",
        "dynamicTexture && mipLevel == 0",
        "LockRect(mipLevel, &lockedRect, nullptr, lockFlags)",
        "static_cast<size_t>(lockedRect.Pitch) < rowBytes",
        "srcRow = srcData + static_cast<size_t>(row) * rowBytes",
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
        "if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData))",
        "original.restoreOriginal();",
        "pDevice, original.data, original.bytes, D3DX_DEFAULT",
        "return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(",
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

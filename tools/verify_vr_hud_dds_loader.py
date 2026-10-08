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
        (handle,"file && size >= sizeof(DDS_FILE)","replacement header bounds"),
        (handle,"firstMipSize <= size - sizeof(DDS_FILE)","replacement first mip source bounds"),
    ]
    for region,needle,label in guards:
        if needle not in region:
            raise ValueError(label+" not verified")
    if loader.index("if (dataSize < sizeof(DDS_FILE))") > loader.index("const DDS_FILE* header ="):
        raise ValueError("DDS header read precedes byte length")
    if re.search(r"LockRect\(mipLevel,\s*&lockedRect,\s*nullptr,\s*D3DLOCK_DISCARD",loader):
        raise ValueError("unconditional DISCARD lock")
    if "memcpy(lockedRect.pBits, srcData, mipSize)" in loader:
        raise ValueError("unpitched bulk copy returned")
    return len(guards)

def negatives(text):
    needles=[
        "if (dataSize < sizeof(DDS_FILE))",
        "bytes > remainingSourceBytes",
        "dynamicTexture && mipLevel == 0",
        "LockRect(mipLevel, &lockedRect, nullptr, lockFlags)",
        "static_cast<size_t>(lockedRect.Pitch) < rowBytes",
        "srcRow = srcData + static_cast<size_t>(row) * rowBytes",
        "*pSrcDataSize < sizeof(DDS_FILE)",
        "firstMipSize <= size - sizeof(DDS_FILE)",
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
    print("VR HUD DDS fast loader PASS: %d source obligations; %d/8 deliberate defects rejected; runtime UNTESTED"%(n,count))

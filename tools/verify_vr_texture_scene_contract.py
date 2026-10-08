#!/usr/bin/env python3
"""Fail-closed source checks for D3D9 scene DDS/D3DX-Ex preservation.

The existing HUD contract protects UI fallback; this protects *scene* texture
fallback, output metadata and sampler state across HUD/world/shader boundaries.
"""
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def body(src,marker):
    i=src.find(marker)
    if i<0: raise ValueError("function missing: "+marker)
    b=src.find("{",i)
    level=0
    for j in range(b,len(src)):
        if src[j]=="{": level+=1
        elif src[j]=="}":
            level-=1
            if level==0:return src[b+1:j]
    raise ValueError("unterminated C++ function: "+marker)

def verify(src):
    fast=body(src,"HRESULT D3DXCreateTextureFromFileInMemoryEx_Custom(")
    scene=body(src,"static HRESULT __stdcall D3DXCreateTextureFromFileInMemoryEx_Custom_dest(")
    ui=body(src,"static HRESULT __stdcall D3DXCreateTextureFromFileInMemory_Custom_dest(")
    native=body(src,"static HRESULT __stdcall D3DXCreateTextureFromFileInMemoryEx_Orig_dest(")
    demanded=[
        ("fast may not override sampler state", "SetSamplerState(" not in fast),
        ("original scene owns transient replacement data", "std::shared_ptr<std::vector<uint8_t>> transientTextureData;" in scene),
        ("scene must precheck metadata outputs", "pSrcInfo != nullptr || pPalette != nullptr" in scene),
        ("scene must preserve color key", "ColorKey != 0" in scene),
        ("scene explicit format must use D3DX", "Format != D3DFMT_UNKNOWN" in scene),
        ("scene explicit dimensions must use D3DX", "Width != D3DX_DEFAULT || Height != D3DX_DEFAULT" in scene),
        ("scene exact mip semantics", "MipLevels != D3DX_DEFAULT && MipLevels != 1" in scene),
        ("scene zero usage+managed fast only", "Usage != 0 || Pool != D3DPOOL_MANAGED" in scene),
        ("scene filter semantics", "Filter != D3DX_FILTER_NONE && Filter != D3DX_DEFAULT" in scene),
        ("scene mip filtering semantics", "MipFilter != D3DX_FILTER_NONE && MipFilter != D3DX_DEFAULT" in scene),
        ("scene fast guarded", "if (!requiresLegacyD3DX && pDevice && pSrcData && SrcDataSize && ppTexture)" in scene),
        ("scene fallback after non-success", "if (SUCCEEDED(fastResult))" in scene),
        ("scene native trampoline present", "return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(" in scene),
        ("native scene preserves SrcInfo/Palette", "pSrcInfo, pPalette, ppTexture);" in scene),
        ("legacy wrapper still exists", "return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(" in native),
        ("UI fast branch remains intact", "const HRESULT fastResult = D3DXCreateTextureFromFileInMemoryEx_Custom(" in ui)]
    for label,valid in demanded:
        if not valid:raise ValueError(label)
    order=[scene.find("HandleTexture(&pSrcData"),scene.find("const bool requiresLegacyD3DX"),scene.find("const HRESULT fastResult"),scene.find("if (SUCCEEDED(fastResult))"),scene.find("return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(")]
    if any(x<0 for x in order) or order!=sorted(order):
        raise ValueError("scene transient/fast/legacy fallback order altered")
    return len(demanded)

def mutations(text):
    tokens=[
        ("scene out-info","pSrcInfo != nullptr || pPalette != nullptr"),
        ("scene color key","ColorKey != 0"),
        ("scene required explicit format","Format != D3DFMT_UNKNOWN"),
        ("scene dimensions","Width != D3DX_DEFAULT || Height != D3DX_DEFAULT"),
        ("scene mip guard","MipLevels != D3DX_DEFAULT && MipLevels != 1"),
        ("scene usage/pool","Usage != 0 || Pool != D3DPOOL_MANAGED"),
        ("scene filter","Filter != D3DX_FILTER_NONE && Filter != D3DX_DEFAULT"),
        ("scene mip filter","MipFilter != D3DX_FILTER_NONE && MipFilter != D3DX_DEFAULT"),
        ("scene guarded fast","if (!requiresLegacyD3DX && pDevice && pSrcData && SrcDataSize && ppTexture)"),
        ("scene result check","if (SUCCEEDED(fastResult))")]
    # The same identifier appears in the older fast helper as well as the
    # scene wrapper. Mutate ONLY the intended scene Ex API boundary.
    marker="static HRESULT __stdcall D3DXCreateTextureFromFileInMemoryEx_Custom_dest("
    final="static HRESULT __stdcall D3DXCreateTextureFromFileInMemoryEx_Orig_dest("
    begin=text.find(marker)
    finish=text.find(final,begin)
    if begin<0 or finish<0:raise ValueError("scene Ex boundaries missing")
    original=text[begin:finish]
    for label,token in tokens:
        mutated=original.replace(token,"__SCENE_EX_CORRUPTION__",1)
        if mutated==original:raise ValueError("failed to inject "+label)
        part=text[:begin]+mutated+text[finish:]
        try:verify(part)
        except ValueError:continue
        raise ValueError("missed negative test "+label)
    return len(tokens)

if __name__=="__main__":
    src=(ROOT/"src/hooks_textures.cpp").read_text(encoding="utf-8")
    try:
        count=verify(src)
        neg=mutations(src) if "--self-test" in sys.argv[1:] else 0
    except ValueError as exc:
        sys.exit("SCENE-TEXTURE-CONTRACT FAIL: "+str(exc))
    print(f"Scene D3DX contract PASS: {count} obligations; {neg}/10 mutated failures rejected; runtime UNTESTED")

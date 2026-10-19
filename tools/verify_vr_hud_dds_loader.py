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

def verify_texture_lookup_window(window_source):
    """Guard both the C++ one-shot state machine and its fail-closed identity checks."""
    normalized = "".join(window_source.split())
    def check(marker, meaning):
        if "".join(marker.split()) not in normalized:
            raise ValueError("vehicle selector lookup window lost " + meaning)
    for token, meaning in (
        ("constexpr bool SpriteMatches(Texture* submitted) const noexcept", "sprite match"),
        ("return submitted && sprite == submitted;", "non-null sprite identity"),
        ("constexpr bool MaskMatches(Texture* submitted) const noexcept", "mask match"),
        ("return submitted && mask == submitted;", "non-null mask identity"),
        ("if (!returned) { Clear(); return; }", "failed lookup invalidation"),
        ("pending_.mask = pending_.sprite;", "paired mask pointer"),
        ("pending_.maskId = pending_.spriteId;", "paired mask ID"),
        ("pending_.sprite = hasScale ? returned : nullptr;", "unscaled pointer fallback"),
        ("pending_.spriteId = hasScale ? id : 0;", "unscaled ID fallback"),
        ("const auto current = pending_;", "snapshot before consumption"),
        ("const auto current = pending_; Clear(); return current;", "consume-once invalidation"),
        ("static_assert(TextureLookupSubmissionGuards()", "compiled positive and negative cases"),
        ("window.Observe(nullptr, 9, false);", "failed lookup regression"),
        ("window.Clear();", "pack change regression"),
        ("paired.MaskMatches(&mask)", "parent/mask pair regression"),
        ("plain.maskId != 7", "unscaled parent mask regression"),
        ("reused.SpriteMatches(&sprite)", "one-shot reuse regression"),
    ):
        check(token, meaning)


def verify(text, window_source=None, mask_policy_source=None):
    # Inspect the actual runtime decoder with or without constexpr; either
    # spelling is a valid function, and both must meet identical strict guards.
    fmt_marker=("inline constexpr D3DFORMAT GetD3DFormatFromPixelFormat("
                if "inline constexpr D3DFORMAT GetD3DFormatFromPixelFormat(" in text
                else "inline D3DFORMAT GetD3DFormatFromPixelFormat(")
    fmt=body(text,fmt_marker)
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
        (loader,"static_cast<size_t>(lockedRect.Pitch) < destinationRowBytes","pitch bounded against actual destination bytes"),
        (loader,"const size_t destinationRowBytes = format_orig == D3DFMT_R8G8B8","24-bit source computes 32-bit GPU destination pitch"),
        (loader,"? static_cast<size_t>(mipWidth) * 4u : rowBytes","opaque RGB24 destination expands to four bytes"),
        (loader,"format_present = D3DFMT_X8R8G8B8;","RGB24 uses supported opaque D3D9 texture format"),
        (loader,"std::memcpy(dstRow + static_cast<size_t>(x) * 4u","per-pixel BGR24 conversion uses destination pitch"),
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
    # Reject historical inactive FourCC, unflagged RGB and 3D DDS payload
    # regressions as well as the existing row-pitch/opaque-alpha contracts.
    format_guards=[
        (fmt,"if ((format.dwFlags & DDPF_FOURCC) != 0)","compressed DDS requires declared FourCC"),
        (fmt,"if ((format.dwFlags & DDPF_RGB) != 0)","conflicting FourCC/RGB header is not fast-decoded"),
        (fmt,"if ((format.dwFlags & DDPF_RGB) == 0)","unflagged RGB bit masks cannot select fast RGB"),
        (fmt,"DdsAlphaMask::Classify16(","source-owned 16-bit DDS alpha classification"),
        (fmt,"case Rgb16Intent::Rgb565: return D3DFMT_R5G6B5;","RGB565 opaque texture path"),
        (fmt,"case Rgb16Intent::Opaque555: return D3DFMT_X1R5G5B5;","undeclared alpha-shaped RGB555 must be opaque"),
        (fmt,"case Rgb16Intent::Alpha1555: return D3DFMT_A1R5G5B5;","declared A1 source transparency retained"),
        (fmt,"case Rgb16Intent::Alpha4444: return D3DFMT_A4R4G4B4;","declared A4 source transparency retained"),
        (fmt,"(format.dwFlags & (DDPF_FOURCC | DDPF_ALPHAPIXELS))","opaque RGB24 rejects false alpha/FourCC"),

        (loader,"(DDSCAPS2_CUBEMAP | DDSCAPS2_VOLUME)","3D DDS faces/slices fall back to D3DX"),
        (text,"static_assert(VerifyDdsPixelIntentAndNativeFallback()","compiled positive/negative DDS metadata regression retained"),
    ]
    for region,needle,label in format_guards:
        if needle not in region:
            raise ValueError(label)
    if (fmt.index("if ((format.dwFlags & DDPF_FOURCC) != 0)") >
            fmt.index("format.dwFourCC == FOURCC_DXT1") or
        fmt.index("if ((format.dwFlags & DDPF_RGB) == 0)") >
            fmt.index("const auto rgb16 = OutRunVR::DdsAlphaMask::Classify16(")):
        raise ValueError("DDS format declaration guards must precede field use")
    # Inspect the real C++ header that classifies 16-bit source masks.
    # An alpha-shaped bit in a DDS RGB-only header is *not* declared alpha.
    pixel_policy = ((ROOT / "src/vr/game/dds_alpha_mask_policy.hpp")
                    .read_text(encoding="utf-8")
                    if mask_policy_source is None else mask_policy_source)
    mask16 = body(pixel_policy, "constexpr Rgb16Intent Classify16(")
    for needle in (
        "!(flags & RgbFlag)", "(flags & FourCcFlag)", "bits != 16u",
        "const bool declaredAlpha = (flags & AlphaFlag) != 0u",
        "alpha == 0u && !declaredAlpha",
        "return Rgb16Intent::Rgb565;",
        "if (!declaredAlpha)",
        "return Rgb16Intent::Opaque555;",
        "alpha == 0x8000u",
        "Rgb16Intent::Alpha1555",
        "alpha == 0xf000u && declaredAlpha",
        "return Rgb16Intent::Alpha4444;",
        "return Rgb16Intent::Unsupported;",
    ):
        if needle not in mask16:
            raise ValueError("16-bit DDS flag/mask admission missing: " + needle)
    # Alpha1555 is admitted in two places: the 555 bitmask guard AND
    # the branch choosing A1 rather than invalid. A mutation of either
    # comparison must not survive because the other still has that literal.
    if mask16.count("alpha == 0x8000u") != 2:
        raise ValueError("16-bit A1 alpha mask guard or selection missing")
    for original in (
        "Classify16(0x40u, 16, 0x7c00, 0x03e0, 0x001f, 0x8000)",
        "Classify16(0x41u, 16, 0x7c00, 0x03e0, 0x001f, 0x8000)",
        "Classify16(0x41u, 16, 0x0f00, 0x00f0, 0x000f, 0xf000)",
        "Classify16(0x40u, 16, 0x0f00, 0x00f0, 0x000f, 0xf000)",
        "Classify16(0x41u, 16, 0xf800, 0x07e0, 0x001f, 0)",
    ):
        if original not in pixel_policy:
            raise ValueError("16-bit DDS positive/negative constexpr case lost")
    # Both 24-bit opaque BGR rows and 32-bit XRGB must preserve their own
    # row pitch, channel order and explicit opaque target format.
    if ("static_assert(OpaqueBgr24Pixel(0x11, 0x22, 0x33) == 0xFF332211u" not in text or
            "static_assert(OpaqueBgr24Pixel(0x00, 0x00, 0x00) == 0xFF000000u" not in text):
        raise ValueError("24-bit BGR channel mapping / opaque alpha regression removed")
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
    # The masked RGB-only branch is a separate *live* format path.
    # Old X8 zero-mask checks alone cannot validate it. Require declared
    # alpha intent on both native and swizzled 32-bit A8 admission sites.
    if fmt.count("rgb32Intent == Rgb32Intent::Alpha") != 2:
        raise ValueError("both declared alpha format branches must verify DDS flags")
    masked_opaque = fmt.split("if (rgb32Intent == Rgb32Intent::Opaque &&", 1)
    if len(masked_opaque) != 2:
        raise ValueError("stale high-byte mask RGB-only branch missing")
    masked_opaque = masked_opaque[1].split("// Opaque 32-bit DDS", 1)[0]
    for required in (
        "format.dwRGBAlphaBitMask == 0xff000000u",
        "format.dwRBitMask == 0x00ff0000",
        "format.dwRBitMask == 0x000000ff",
        "resolvedFormat = D3DFMT_X8R8G8B8;",
        "resolvedFormat = D3DFMT_X8B8G8R8;",
        "if (resolvedFormat != D3DFMT_UNKNOWN)",
        "return resolvedFormat;",
    ):
        if required not in masked_opaque:
            raise ValueError("RGB-only masked DDS branch lacks " + required)
    if "const auto rgb32Intent = OutRunVR::DdsAlphaMask::Classify(" not in fmt or (
        "format.dwFlags, format.dwRGBBitCount, format.dwRGBAlphaBitMask" not in fmt):
        raise ValueError("DDS masks must be interpreted with actual alpha declaration")
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
    # Runtime UITextureReplacement toggle must revoke previous ratios for
    # BOTH sprite paths and their mask, and original DDS reloads must clear
    # a previously cached slot even while replacement is disabled.
    policy=body(text,"static constexpr bool ShouldApplyUIScale(")
    if "return enabled && matches;" not in policy:
        raise ValueError("live UI replacement preference is not authoritative")
    if ("static_assert(ShouldApplyUIScale(true, true)" not in text or
        "!ShouldApplyUIScale(false, true)" not in text or
        "!ShouldApplyUIScale(true, false)" not in text):
        raise ValueError("UI scale enable/disable and identity compile regressions missing")
    if "|| !Settings::UITextureReplacement" in state.split("memcpy(&header",1)[0]:
        raise ValueError("disabled replacement skipped old-slot scale retirement")
    lookup=body(text,"static void* __cdecl get_texture_dest(")
    spr2=body(text,"static int __cdecl put_sprite_ex2_dest(")
    spr1=body(text,"static int __cdecl put_sprite_ex_dest(")
    if window_source is None:
        window_source = (ROOT / "src/vr/game/ui_texture_lookup_window.hpp").read_text(encoding="utf-8")
    verify_texture_lookup_window(window_source)
    # Read the producer and consumer from the actual hook: a pointer alone
    # cannot authorize another frame, sprite family, or pack's UV scale.
    obligations = [
        (text, '#include "vr/game/ui_texture_lookup_window.hpp"'),
        (text, "TextureLookupWindow<void> pendingTextureLookups{};"),
        (lookup, "if (!Settings::UITextureReplacement)"),
        (lookup, "pendingTextureLookups.Clear();"),
        (lookup, "pendingTextureLookups.Observe(ret, textureId,"),
        (lookup, "sprite_scales.contains(textureId)"),
        (spr2, "const auto lookup = pendingTextureLookups.Consume();"),
        (spr2, "lookup.SpriteMatches(a1->d3dtexture_ptr_C)"),
        (spr2, "sprite_scales.find(lookup.spriteId)"),
        (spr2, "a1->child_B4 && *Module::exe_ptr<int>(0x586B28)"),
        (spr2, "lookup.MaskMatches(a1->child_B4->d3dtexture_ptr_C)"),
        (spr2, "sprite_scales.find(lookup.maskId)"),
        (spr2, "originalUv.Apply(a1,"),
        (spr2, "maskUv.Apply(a1->child_B4,"),
        (spr2, "maskUv.Restore();"),
        (spr2, "originalUv.Restore();"),
        (spr1, "pendingTextureLookups.Consume();"),
        (spr1, "ShouldApplyUIScale(Settings::UITextureReplacement, true)"),
        (spr1, "sprite_scales.find(xstnum)"),
    ]
    xstset = body(text, "static void LoadXstsetSprite_dest(")
    obligations += [(xstset, "pendingTextureLookups.Clear();")]
    for region, needle in obligations:
        if needle not in region:
            raise ValueError("UI runtime toggle or bounded-lookup guard missing: " + needle)
    normalized_sprite = "".join(spr2.split())
    if normalized_sprite.count("ShouldApplyUIScale(Settings::UITextureReplacement,") < 2:
        raise ValueError("sprite/mask UI toggle checks must be independent")
    if not (spr2.index("pendingTextureLookups.Consume()") <
            spr2.index("lookup.SpriteMatches(") <
            spr2.index("put_sprite_ex2.call<int>(") <
            spr2.index("maskUv.Restore()") <
            spr2.index("originalUv.Restore()")):
        raise ValueError("consume, draw and parent/mask UV restore lifetime drift")
    if any(x in spr2 + spr1 for x in (
        "sprite_scales[lookup.spriteId]", "sprite_scales[lookup.maskId]",
        "sprite_scales[xstnum]", "prevMaskTexture", "prevTextureId")):
        raise ValueError("old pointer owner or unchecked scale-map lookup returned")
    return len(guards) + len(xrgb_checks) + len(state_guards) + len(obligations)



def negatives(text):
    needles=[
        "if ((format.dwFlags & DDPF_FOURCC) != 0)",
        "if ((format.dwFlags & DDPF_RGB) != 0)",
        "if ((format.dwFlags & DDPF_RGB) == 0)",
        "DdsAlphaMask::Classify16(",
        "case Rgb16Intent::Opaque555: return D3DFMT_X1R5G5B5;",
        "case Rgb16Intent::Alpha1555: return D3DFMT_A1R5G5B5;",
        "case Rgb16Intent::Alpha4444: return D3DFMT_A4R4G4B4;",
        "case Rgb16Intent::Rgb565: return D3DFMT_R5G6B5;",
        "(format.dwFlags & (DDPF_FOURCC | DDPF_ALPHAPIXELS))",
        "(DDSCAPS2_CUBEMAP | DDSCAPS2_VOLUME)",
        "static_assert(VerifyDdsPixelIntentAndNativeFallback()",
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
        "static_cast<size_t>(lockedRect.Pitch) < destinationRowBytes",
        "const size_t destinationRowBytes = format_orig == D3DFMT_R8G8B8",
        "? static_cast<size_t>(mipWidth) * 4u : rowBytes",
        "format_present = D3DFMT_X8R8G8B8;",
        "std::memcpy(dstRow + static_cast<size_t>(x) * 4u",
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
        # New live RGB-only high-byte-mask handling; mutations must break
        # the verified source path, not only the older zero-mask path.
        "format.dwFlags, format.dwRGBBitCount, format.dwRGBAlphaBitMask",
        "rgb32Intent == Rgb32Intent::Alpha",
        "rgb32Intent == Rgb32Intent::Opaque",
        "format.dwRGBAlphaBitMask == 0xff000000u",
        "resolvedFormat = D3DFMT_X8R8G8B8;",
        "resolvedFormat = D3DFMT_X8B8G8R8;",
        "if (resolvedFormat != D3DFMT_UNKNOWN)",
        "format.dwRGBAlphaBitMask == 0)",
        "return D3DFMT_X8R8G8B8;",
        "return D3DFMT_X8B8G8R8;",
        "? D3DFMT_A8R8G8B8 : D3DFMT_X8R8G8B8;",
        "format_orig == D3DFMT_X8B8G8R8)\n\t\t\t{",
        "dstRow[p] = srcRow[p + 2];",
        "dstRow[p + 2] = srcRow[p];",
        "return enabled && matches;",
        "if (!Settings::UITextureReplacement)",
        "pendingTextureLookups.Observe(ret, textureId,",
        "pendingTextureLookups.Clear();",
        "const auto lookup = pendingTextureLookups.Consume();",
        "lookup.SpriteMatches(a1->d3dtexture_ptr_C)",
        "lookup.MaskMatches(a1->child_B4->d3dtexture_ptr_C)",
        "sprite_scales.find(lookup.spriteId)",
        "sprite_scales.find(lookup.maskId)",
        "a1->child_B4 && *Module::exe_ptr<int>(0x586B28)",
        "maskUv.Restore();",
        "originalUv.Restore();",
        "sprite_scales.find(xstnum)",
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
    # The source-only verifier can pass even if the shared C++ mask policy
    # is weakened. Intentionally corrupt its admission gates and ensure
    # each failure is caught before a Windows game/package acceptance.
    mask_policy = (ROOT / "src/vr/game/dds_alpha_mask_policy.hpp").read_text(
        encoding="utf-8")
    mask_policy_mutations = [
        "!(flags & RgbFlag)", "(flags & FourCcFlag)", "bits != 16u",
        "const bool declaredAlpha = (flags & AlphaFlag) != 0u",
        "alpha == 0u && !declaredAlpha",
        "return Rgb16Intent::Rgb565;",
        "if (!declaredAlpha)", "return Rgb16Intent::Opaque555;",
        "alpha == 0x8000u", "alpha == 0xf000u && declaredAlpha",
        "return Rgb16Intent::Alpha4444;",
        "Classify16(0x40u, 16, 0x0f00, 0x00f0, 0x000f, 0xf000)",
    ]
    class_start = mask_policy.find("constexpr Rgb16Intent Classify16(")
    if class_start < 0:
        raise ValueError("16-bit native DDS policy missing")
    for needle in mask_policy_mutations:
        # Some guards occur in the preceding RGB32 Classify too. Mutate
        # the actual 16-bit classifier (or its later static assertions),
        # not the unrelated earlier RGB32 owner.
        at = mask_policy.find(needle, class_start)
        if at < 0:
            raise ValueError("16-bit mask policy mutation not applied: " + needle)
        changed = (mask_policy[:at] + "__DDS_BAD_CONTRACT__" +
                   mask_policy[at + len(needle):])
        try:
            verify(text, mask_policy_source=changed)
            raise ValueError("mask policy mutation survived: " + needle)
        except ValueError as exc:
            if str(exc).startswith("mask policy mutation survived"):
                raise
    # Mutations of the actual standalone C++ state-machine must fail too:
    # no positive-only test that ignores NULL, reused pointers or mask IDs.
    header = (ROOT / "src/vr/game/ui_texture_lookup_window.hpp").read_text(encoding="utf-8")
    window_needles = [
        "return submitted && sprite == submitted;",
        "return submitted && mask == submitted;",
        "if (!returned) { Clear(); return; }",
        "pending_.mask = pending_.sprite;",
        "pending_.maskId = pending_.spriteId;",
        "pending_.sprite = hasScale ? returned : nullptr;",
        "pending_.spriteId = hasScale ? id : 0;",
        "const auto current = pending_;",
        "Clear();\n            return current;",
        "static_assert(TextureLookupSubmissionGuards()",
        "window.Observe(nullptr, 9, false);",
        "paired.MaskMatches(&mask)",
        "plain.maskId != 7",
        "reused.SpriteMatches(&sprite)",
    ]
    for token in window_needles:
        mutant = header.replace(token, "__DDS_BAD_CONTRACT__", 1)
        if mutant == header:
            raise ValueError("window mutation not applied: " + token)
        try:
            verify(text, mutant)
            raise ValueError("window mutation was NOT caught: " + token)
        except ValueError as exc:
            if str(exc).startswith("window mutation was NOT caught"):
                raise
    return len(needles) + len(window_needles) + len(mask_policy_mutations)

if __name__=="__main__":
    text=(ROOT/"src/hooks_textures.cpp").read_text(encoding="utf-8")
    try:
        n=verify(text)
        count=negatives(text) if "--self-test" in sys.argv[1:] else 0
    except ValueError as exc:
        sys.exit("VR HUD DDS loader gate FAIL: "+str(exc))
    print("VR HUD DDS fast loader PASS: %d source obligations; %d/%d deliberate defects rejected; runtime UNTESTED"%(n,count,count))

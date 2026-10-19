#!/usr/bin/env python3
"""DX9Ex original UI matrix safety, owner checks, and destructive regressions."""
from pathlib import Path
from math import isfinite

text = (Path(__file__).resolve().parents[1] / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")


def require_safe(source: str) -> None:
    start = source.index("static int __stdcall D3DXMatrixTransformation2D_dest(")
    end = source.index("static inline SafetyHookMid draw_sprite_custom_matrix_hk", start)
    # Active VR uses a bounded October-9 compatibility path BEFORE the
    # experimental front-end producer affine. Verify the modern R84 path
    # independently, rather than mistaking its earlier legacy return for
    # an unsafe early call in the current branch.
    s = source[start:end].split(
        "// D3DX treats these input vectors as read-only.", 1)[1]
    required = (
        "CanContainOriginalFullFrontEndVector(",
        "Game::screen_scale && Game::screen_resolution",
        "std::isfinite(sx) && std::isfinite(sy)",
        "sx > 1.0e-6f && sy > 1.0e-6f",
        "std::isfinite(pScaling->x)",
        "std::isfinite(pTranslation->y)",
        "std::isfinite(xScale) && std::isfinite(yScale)",
        "std::isfinite(centeredX) && std::isfinite(centeredY)",
        "std::isfinite(Game::screen_resolution->y)",
        "std::isfinite(Game::original_resolution.y)",
        "const auto affine = OutRunVrUiAspect::BuildFrontEndAffineContain(",
        "const float xScale = affine.ScaleX(pScaling->x);",
        "const float centeredY = affine.MapY(pTranslation->y);",
        "if (affine.valid && std::isfinite(xScale)",
    )
    for needle in required:
        if needle not in s:
            raise AssertionError(f"Missing UI matrix guard: {needle}")
    order = [
        "CanContainOriginalFullFrontEndVector(",
        "Game::screen_scale && Game::screen_resolution",
        "sx > 1.0e-6f && sy > 1.0e-6f",
        "const auto affine = OutRunVrUiAspect::BuildFrontEndAffineContain(",
        "std::isfinite(centeredX) && std::isfinite(centeredY)",
        "localScaling.x = xScale;",
        "forwardedScaling = &localScaling;",
        "forwardedTranslation = &localTranslation;",
        "D3DXMatrixTransformation2D.stdcall<int>",
    ]
    indices = [s.index(k) for k in order]
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise AssertionError("Null/finite/zero-scale checks must precede divide and writes")
    # D3DX reads these arguments; mutating the caller's vectors introduces
    # another scaling/centering pass if the native game reuses them.
    if "pScaling->x =" in s or "pScaling->y =" in s or \
       "pTranslation->x =" in s or "pTranslation->y =" in s:
        raise AssertionError("Original game menu matrix arguments mutated")
    for needle in ("D3DXVECTOR2 localScaling{};",
                   "D3DXVECTOR2 localTranslation{};",
                   "D3DXVECTOR2* forwardedScaling = pScaling;",
                   "D3DXVECTOR2* forwardedTranslation = pTranslation;",
                   "localScaling.x = xScale;", "localScaling.y = yScale;",
                   "localTranslation.x = centeredX;",
                   "localTranslation.y = centeredY;",
                   "forwardedScaling = &localScaling;",
                   "forwardedTranslation = &localTranslation;",
                   "forwardedScaling, pRotationCenter, Rotation, forwardedTranslation);"):
        if needle not in s:
            raise AssertionError("Staged menu matrix forwarding missing: " + needle)
    assert s.index("std::isfinite(centeredX) && std::isfinite(centeredY)") < \
        s.index("forwardedScaling = &localScaling;") < \
        s.index("D3DXMatrixTransformation2D.stdcall<int>")


require_safe(text)

# The user's R84 and R26_SAFE HMD sessions both reproduced the same
# misregistered quit-dialog text: the shared UI hook was the regression.
# Pin the older full-vector-only VR dispatch so a later refactor cannot
# silently expose partial/pivot source matrices to this broken mapping.
def require_vr_legacy_owner(source: str) -> None:
    block = source.split("static int __stdcall D3DXMatrixTransformation2D_dest(", 1)[1].split(
        "// D3DX treats these input vectors as read-only.", 1)[0]
    keys = (
        "if (Settings::VREnabled &&",
        "mode == ScalingMode::KeepCentered ||",
        "mode == ScalingMode::OnlineArcade))",
        "if (pScaling && pTranslation &&",
        "const float factor = (std::min)(sx, sy);",
        "(pScaling->x / sx) * factor;",
        "(pScaling->y / sy) * factor;",
        "(sw - ow * factor) * 0.5f;",
        "(pTranslation->y / sy) * factor;",
        "std::isfinite(legacyTranslation.y))",
        "inputScale = &legacyScale;",
        "inputTranslation = &legacyTranslation;",
        "return D3DXMatrixTransformation2D.stdcall<int>(",
    )
    for key in keys:
        assert key in block, "legacy VR compatibility missing: " + key
    assert block.index("if (Settings::VREnabled &&") < block.index(
        "if (pScaling && pTranslation &&") < block.index(
        "return D3DXMatrixTransformation2D.stdcall<int>(")
    assert "pScaling->x =" not in block and "pTranslation->x =" not in block
    assert "CanContainOriginalFullFrontEndVector" not in block
    assert "NeedsFrontEndAffineContain" not in block
    assert "BuildFrontEndAffineContain" not in block

require_vr_legacy_owner(text)
for old, broken in (
    ("if (Settings::VREnabled &&", "if (!Settings::VREnabled &&"),
    ("if (pScaling && pTranslation &&", "if (pScaling || pTranslation ||"),
    ("(sw - ow * factor) * 0.5f;", "(sw - ow * factor);"),
    ("inputScale = &legacyScale;", "inputScale = pScaling;"),
    ("inputTranslation = &legacyTranslation;", "inputTranslation = pTranslation;"),
):
    assert old in text
    try:
        require_vr_legacy_owner(text.replace(old, broken, 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("VR legacy UI rollback mutation escaped: " + old)
print("VR known-good full-vector matrix rollback PASS (5 destructive controls)")


# 01071: Enforce the new full-vector guard and its shared game-state snapshot.
# Never accept an unsafe full HUD transform just because a string was renamed.
def require_frontend_owner(source: str) -> None:
    predicate = source.split(
        "constexpr bool CanContainOriginalFullFrontEndVector(", 1)[1].split(
        "// The six +TIME caller tails", 1)[0]
    for required in (
        "return exactFrontEnd && containedMode &&",
        "hasScale && hasTranslation;",
        "static_assert(CanContainOriginalFullFrontEndVector(true, true, true, true)",
        "static_assert(!CanContainOriginalFullFrontEndVector(false, true, true, true)",
        "static_assert(!CanContainOriginalFullFrontEndVector(true, false, true, true)",
    ):
        assert required in predicate, "full-vector safety missing: " + required
    owner = source.split("const bool originalFrontEndProducer =", 1)[1].split(
        "const bool centredPhysicalMenuFill =", 1)[0]
    assert "Game::current_mode &&" in owner
    for state in ("TITLE", "MENU", "SELECTOR", "SELEXIT", "SELRESET"):
        assert "GameState::STATE_" + state in owner, "frontend missing: " + state
    for excluded in ("GOAL", "RACE"):
        assert "GameState::STATE_" + excluded not in owner, "foreign HUD owner: " + excluded
    hook = source.split(
        "static int __stdcall D3DXMatrixTransformation2D_dest(", 1)[1].split(
        "static inline SafetyHookMid draw_sprite_custom_matrix_hk", 1)[0]
    for required in (
        "mode == ScalingMode::KeepCentered && originalFrontEndProducer;",
        "const bool frontEndPivot = NeedsFrontEndAffineContain(\n            originalFrontEndProducer,",
        "if (!frontEndPivot && CanContainOriginalFullFrontEndVector(\n                originalFrontEndProducer,",
        "pScaling != nullptr, pTranslation != nullptr) &&",
        "const bool partialFrontEndMenu = originalFrontEndProducer;",
    ):
        assert required in hook, "source owner handoff missing: " + required
    assert hook.index("const bool originalFrontEndProducer =") < hook.index(
        "const bool frontEndPivot =") < hook.index(
        "if (!frontEndPivot && CanContainOriginalFullFrontEndVector(")

require_frontend_owner(text)
for good, bad in (
    ("hasScale && hasTranslation;", "hasScale || hasTranslation;"),
    ("const bool originalFrontEndProducer = Game::current_mode &&",
     "const bool originalFrontEndProducer = true &&"),
    ("*Game::current_mode == GameState::STATE_SELECTOR",
     "*Game::current_mode == GameState::STATE_GOAL"),
    ("if (!frontEndPivot && CanContainOriginalFullFrontEndVector(\n                originalFrontEndProducer,",
     "if (!frontEndPivot && CanContainOriginalFullFrontEndVector(\n                true,"),
    ("const bool partialFrontEndMenu = originalFrontEndProducer;",
     "const bool partialFrontEndMenu = true;"),
):
    assert good in text, "missing owner mutation anchor: " + good
    try:
        require_frontend_owner(text.replace(good, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("unsafe front-end owner mutation escaped: " + bad)
print("DX9Ex front-end full-vector exact-owner PASS (5 destructive controls)")

# Source owner introduced by 00961: preserve the physical viewport bound,
# finite offsets, and separate X/Y ratios for full/nullable/pivoted D3DX paths.
# Old exact expression assertions on the pre-affine hook are no longer valid.
frontend_affine = (Path(__file__).resolve().parents[1] /
                   "src/vr/ui/frontend_affine_contain.hpp").read_text(encoding="utf-8")

def require_frontend_affine(header: str) -> None:
    for required in (
        "BoundedMultiSpriteContainScale(",
        "sx,sy,width,height,srcWidth,srcHeight);",
        "if(!(contain>0.f))return {};",
        "const float rx=contain/sx,ry=contain/sy;",
        "const double ox=(double(width)-double(srcWidth)*contain)*0.5;",
        "const double oy=(double(height)-double(srcHeight)*contain)*0.5;",
        "if(!std::isfinite(rx)||!std::isfinite(ry)||",
        "if(!std::isfinite(x)||!std::isfinite(y))return {};",
        "return {rx,ry,x,y,true};",
    ):
        if required not in header:
            raise AssertionError("Unbounded or invalid D3DX frontend affine: " + required)

require_frontend_affine(frontend_affine)
for good, bad in (
    ("const float rx=contain/sx,ry=contain/sy;",
     "const float rx=contain/sx,ry=contain/sx;"),
    ("const double oy=(double(height)-double(srcHeight)*contain)*0.5;",
     "const double oy=(double(height)-double(srcWidth)*contain)*0.5;"),
    ("if(!(contain>0.f))return {};", "if(false)return {};"),
    ("return {rx,ry,x,y,true};", "return {rx,ry,x,y,false};"),
):
    assert good in frontend_affine
    try:
        require_frontend_affine(frontend_affine.replace(good, bad, 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("Frontend affine mutation escaped: " + bad)
print("DX9Ex frontend full/nullable/pivot physical affine PASS (4 negative controls)")

# The native sprite producer may reuse the SAME vector for several draws.
# Corrected matrix inputs must be derived from an immutable original on
# each invocation, including ultrawide and portrait viewport changes.
def staged_menu_matrix(screen, authored=(640.0, 480.0), scale=(1.0, 1.0),
                       translation=(200.0, 100.0)):
    width, height = screen
    sx, sy = width / authored[0], height / authored[1]
    contain = min(sx, sy)
    scaling = (scale[0] / sx * contain, scale[1] / sy * contain)
    position = (translation[0] / sx * contain +
                (width - authored[0] * contain) / 2,
                translation[1] / sy * contain +
                (height - authored[1] * contain) / 2)
    return scaling, position

for size in ((640, 480), (1024, 768), (1920, 1080),
             (3440, 1440), (2496, 2688)):
    source_scale, source_offset = (1.0, 1.0), (200.0, 100.0)
    first = staged_menu_matrix(size, scale=source_scale,
                               translation=source_offset)
    second = staged_menu_matrix(size, scale=source_scale,
                                translation=source_offset)
    assert first == second
    assert source_scale == (1.0, 1.0)
    assert source_offset == (200.0, 100.0)
    # The transform changes for a different output size, but the INPUT
    # remains the original asset. This protects reset/resize transitions.
    resized = staged_menu_matrix((1280, 960), scale=source_scale,
                                 translation=source_offset)
    assert resized[0] == source_scale
    assert source_scale == (1.0, 1.0)
    assert source_offset == (200.0, 100.0)

# Negative controls: old direct input mutation, missing local forwarding,
# and an invalid intermediate that must use the untouched legacy call.
def require_staged_inputs(code: str) -> None:
    require_safe(code)
    owner = code.split("static int __stdcall D3DXMatrixTransformation2D_dest(", 1)[1].split(
        "static inline SafetyHookMid draw_sprite_custom_matrix_hk", 1)[0]
    assert "forwardedScaling = &localScaling;" in owner
    assert "forwardedTranslation = &localTranslation;" in owner
    assert "pScaling->x = xScale;" not in owner
    assert "pTranslation->x = centeredX;" not in owner
    assert "D3DXVECTOR2* forwardedScaling = pScaling;" in owner
    assert "D3DXVECTOR2* forwardedTranslation = pTranslation;" in owner

for good, bad in (
    ("localScaling.x = xScale;", "pScaling->x = xScale;"),
    ("forwardedScaling = &localScaling;", "forwardedScaling = pScaling;"),
    ("forwardedTranslation = &localTranslation;", "forwardedTranslation = pTranslation;"),
    ("D3DXVECTOR2* forwardedScaling = pScaling;",
     "D3DXVECTOR2* forwardedScaling = nullptr;"),
):
    assert good in text, good
    try:
        require_staged_inputs(text.replace(good, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Reused menu-vector mutation escaped: " + bad)


def require_portrait_center(code):
    sprite = code.split("static void __cdecl draw_sprite_custom_matrix_mid(", 1)[1].split(
        "// Adjust positions of sprites in 3d space", 1)[0]
    # The previous verticalCenter expression was replaced by a single
    # physically bounded source->viewport affine. Pin all four X/Y vertices
    # instead: otherwise a stale game screen_scale after Reset clips the
    # original menu/car-selector artwork even though the other axis is safe.
    required = (
        "!std::isfinite(Game::screen_resolution->y)",
        "!std::isfinite(Game::original_resolution.y)",
        "const auto quadMap = precontained",
        "? OutRunVrMenuQuad::PixelMap{1.f, 1.f, 0.f, 0.f, true}",
        ": OutRunVrMenuQuad::BuildPixelMap(",
        "precontained = contained && frontEnd &&",
        "OutRunVrMenuQuad::ContainedMatrices.Contains(",
        "screenScaleX, screenScaleY,",
        "Game::screen_resolution->x, Game::screen_resolution->y);",
        "if (!quadMap.valid)",
        "quad[1] = OutRunVrMenuQuad::ProjectY(quadMap, topLeft.y);",
        "quad[8] = OutRunVrMenuQuad::ProjectY(quadMap, bottomLeft.y);",
        "quad[0xF] = OutRunVrMenuQuad::ProjectY(quadMap, topRight.y);",
        "quad[0x16] = OutRunVrMenuQuad::ProjectY(quadMap, bottomRight.y);",
        "quad[0] = OutRunVrMenuQuad::ProjectX(quadMap, topLeft.x);",
        "quad[7] = OutRunVrMenuQuad::ProjectX(quadMap, bottomLeft.x);",
        "quad[0xE] = OutRunVrMenuQuad::ProjectX(quadMap, topRight.x);",
        "quad[0x15] = OutRunVrMenuQuad::ProjectX(quadMap, bottomRight.x);",
    )
    for token in required:
        if token not in sprite:
            raise AssertionError(token)
    if sprite.index("const auto quadMap = precontained") > (
            sprite.index("quad[1] = OutRunVrMenuQuad::ProjectY(")):
        raise AssertionError("quad map must precede all transformed corners")


    # Original D3DX result is the sole provenance source. Never globally
    # bypass quad mapping based on a frontend mode/INI setting alone.
    producer = code.split("static int __stdcall D3DXMatrixTransformation2D_dest(", 1)[1].split(
        "static inline SafetyHookMid draw_sprite_custom_matrix_hk", 1)[0]
    for required in (
        "bool publishedPrecontainedMenuMatrix = false;",
        "publishedPrecontainedMenuMatrix = true;",
        "if (result && pOut && publishedPrecontainedMenuMatrix &&",
        "partialFrontEndMenu && Game::screen_scale &&",
        "OutRunVrMenuQuad::ContainedMatrices.Remember(",
        "std::memcpy(fingerprint.data(), pOut, sizeof(D3DMATRIX));",
    ):
        if required not in producer:
            raise AssertionError("menu matrix source provenance: " + required)
    if sprite.index("precontained = contained && frontEnd &&") > sprite.index(
        "const auto quadMap = precontained"):
        raise AssertionError("original matrix proof must precede custom quad map")
    if sprite.index("OutRunVrMenuQuad::ContainedMatrices.Contains(") > sprite.index(
        "const auto quadMap = precontained"):
        raise AssertionError("custom quad must verify exact D3DX matrix first")
    if sprite.index(": OutRunVrMenuQuad::BuildPixelMap(") > sprite.index(
        "if (!quadMap.valid)"):
        raise AssertionError("unproven quad fallback must remain live")



def require_physical_containment(header):
    body = header.split("inline PixelMap BuildPixelMap(", 1)[1].split(
        "inline float ProjectX(", 1)[0]
    required = (
        "if (!contained)",
        "const float physicalX = screenWidth / sourceWidth;",
        "const float physicalY = screenHeight / sourceHeight;",
        "!std::isfinite(physicalX) || !std::isfinite(physicalY)",
        "const float gameScale = screenScaleX < screenScaleY",
        "const float physicalScale = physicalX < physicalY",
        "bool physicalMenuFill = false) noexcept",
        "const float scale = physicalMenuFill ? physicalScale :",
        "(gameScale < physicalScale ? gameScale : physicalScale);",
        "(screenWidth - sourceWidth * scale) * 0.5f",
        "(screenHeight - sourceHeight * scale) * 0.5f",
        "return {scale, scale, offsetX, offsetY, true};",
    )
    for token in required:
        if token not in body:
            raise AssertionError("Live viewport containment missing: " + token)
    if not (body.index("const float physicalX") <
            body.index("const float scale = physicalMenuFill ? physicalScale :") <
            body.index("return {scale, scale, offsetX, offsetY, true};")):
        raise AssertionError("UI containment must use bounded scale")


require_portrait_center(text)

# 00977: pin positive exact D3DX provenance and negative unchanged fallback.
# Mutating the guard, identity map, matrix read or native map must be caught,
# in addition to the preexisting 6 X/Y vertex and physical geometry controls.
for before, after in (
    ("precontained = contained && frontEnd &&", "precontained = true &&"),
    ("OutRunVrMenuQuad::ContainedMatrices.Contains(", "OutRunVrMenuQuad::ContainedMatrices.WrongOwner("),
    ("? OutRunVrMenuQuad::PixelMap{1.f, 1.f, 0.f, 0.f, true}",
     "? OutRunVrMenuQuad::PixelMap{0.5f, 1.f, 0.f, 0.f, true}"),
    (": OutRunVrMenuQuad::BuildPixelMap(",
     ": OutRunVrMenuQuad::PixelMap{1.f,1.f,0.f,0.f,true} /* no physical fallback */("),
    ("if (result && pOut && publishedPrecontainedMenuMatrix &&",
     "if (result && pOut && true &&"),
    ("std::memcpy(fingerprint.data(), pOut, sizeof(D3DMATRIX));",
     "std::memcpy(fingerprint.data(), &sourceMatrix, sizeof(D3DMATRIX));"),
):
    assert before in text, "menu provenance mutation anchor: " + before
    mutant = text.replace(before, after, 1)
    try:
        require_portrait_center(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("double containment provenance mutant escaped: " + before)
print("DX9Ex exact native D3DX/custom quad menu containment PASS (6 negative controls)")


for w, h, margin in ((2496, 2688, 408), (3440, 1440, 0),
                     (1920, 1440, 0)):
    s = min(w / 640, h / 480)
    assert abs((h - 480 * s) / 2 - margin) < 1e-5

mutants = (
    ("CanContainOriginalFullFrontEndVector(\n                originalFrontEndProducer,",
     "CanContainOriginalFullFrontEndVector(\n                true,"),
    ("sx > 1.0e-6f && sy > 1.0e-6f", "sx >= 0.0f && sy >= 0.0f"),
    ("std::isfinite(centeredX) && std::isfinite(centeredY)",
     "std::isfinite(centeredX) || std::isfinite(centeredY)"),
)
for good, bad in mutants:
    # Mutate the R84 branch under test, not the earlier known-good VR
    # compatibility path which deliberately uses the same finite guard.
    legacy, boundary, modern = text.partition(
        "// D3DX treats these input vectors as read-only.")
    mutant = legacy + boundary + modern.replace(good, bad, 1)
    if mutant == text:
        raise AssertionError("No-op negative mutation: " + good)
    try:
        require_safe(mutant)
        require_frontend_owner(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("Escaped regression: " + bad)
# Source scale caching and viewport geometry must be tested together,
# including negative mutations of the new both-axis affine, not just an
# obsolete vertical-centre formula.
menu_quad = (Path(__file__).resolve().parents[1] /
             "src/vr/ui/menu_quad_transform.hpp").read_text()
require_physical_containment(menu_quad)
for old, bad in (
    ("const float centeredY = affine.MapY(pTranslation->y);",
     "const float centeredY = affine.MapY(pTranslation->x);"),
    ("quad[8] = OutRunVrMenuQuad::ProjectY(quadMap, bottomLeft.y);",
     "quad[8] = bottomLeft.y + 0.5f;"),
    ("quad[0xF] = OutRunVrMenuQuad::ProjectY(quadMap, topRight.y);",
     "quad[0xF] = OutRunVrMenuQuad::ProjectX(quadMap, topRight.y);"),
    ("quad[0] = OutRunVrMenuQuad::ProjectX(quadMap, topLeft.x);",
     "quad[0] = topLeft.x + 0.5f;"),
):
    assert old in text
    broken = text.replace(old, bad, 1)
    try:
        require_safe(broken)
        require_portrait_center(broken)
    except AssertionError:
        pass
    else:
        raise AssertionError("Quad XY containment mutation survived: " + bad)
for old, bad in (
    ("const float physicalY = screenHeight / sourceHeight;",
     "const float physicalY = screenHeight / sourceWidth;"),
    ("const float physicalScale = physicalX < physicalY",
     "const float physicalScale = physicalX > physicalY"),
    ("bool physicalMenuFill = false) noexcept",
     "bool physicalMenuFill = true) noexcept"),
    ("const float scale = physicalMenuFill ? physicalScale :",
     "const float scale = physicalMenuFill ? gameScale :"),
    ("(gameScale < physicalScale ? gameScale : physicalScale);",
     "(gameScale > physicalScale ? gameScale : physicalScale);"),
):
    assert old in menu_quad
    try:
        require_physical_containment(menu_quad.replace(old, bad, 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("Physical viewport cap mutation survived: " + bad)

# Regression: OutRun can retain and reuse the same source matrix values
# across menu -> car selection -> pause -> menu, even if the desktop mirror
# changes aspect between calls. Only the caller's raw source (not our prior
# forwarded D3DX scratch values) may be the starting point on the next draw.
source_scale = [1.25, 0.75]
source_offset = [187.0, 119.0]
source_bytes = (tuple(source_scale), tuple(source_offset))
cycle = ((640, 480), (3440, 1440), (2496, 2688),
         (1920, 1080), (640, 480))
for output in cycle:
    projected = staged_menu_matrix(output, scale=source_scale,
                                   translation=source_offset)
    assert projected == staged_menu_matrix(output,
        scale=source_scale, translation=source_offset)
    assert (tuple(source_scale), tuple(source_offset)) == source_bytes
assert staged_menu_matrix(cycle[0], scale=source_scale,
    translation=source_offset) == staged_menu_matrix(
        cycle[-1], scale=source_scale, translation=source_offset)

# An invalid/zero device scale and nonfinite original input have to retain
# untouched pointers for the original D3DX fallback; they must never cause
# partial source overwrites (or stage only one of scale and translation).
def would_stage_for_d3dx(screen, scaling, translation):
    if scaling is None or translation is None:
        return False
    if screen is None or not all(isfinite(v) and v > 0.0 for v in screen):
        return False
    sx, sy = screen[0] / 640.0, screen[1] / 480.0
    return (sx > 1.0e-6 and sy > 1.0e-6 and
            all(isfinite(v) for v in (*scaling, *translation)))

assert would_stage_for_d3dx((3440, 1440), source_scale, source_offset)
for size, scaling, offset in (
    (None, source_scale, source_offset),
    ((0, 1440), source_scale, source_offset),
    ((3440, 0), source_scale, source_offset),
    ((float("nan"), 1440), source_scale, source_offset),
    ((3440, 1440), None, source_offset),
    ((3440, 1440), source_scale, None),
    ((3440, 1440), [float("inf"), 0.75], source_offset),
    ((3440, 1440), source_scale, [187.0, float("nan")]),
):
    assert not would_stage_for_d3dx(size, scaling, offset)
assert (tuple(source_scale), tuple(source_offset)) == source_bytes
print("DX9Ex reusable menu source vectors and invalid D3DX fallback PASS")

print("DX9Ex UI matrix and portrait containment PASS (6 negative controls)")

# Original multi-sprite GUI vertex streams have three independently hooked
# stride layouts: one already-scaled X/Y pair at the start of every vertex.
# Ensure the main/car-selection screen preserves its authored XY ratio, not
# just X centre placement (which stretched Y on portrait XR render targets).
def require_multi_sprite_native_aspect(source: str) -> None:
    group = source.split("static void CenterMultiSpriteQuad(", 1)[1].split(
        "static void SpriteSpacingEnable(", 1)[0]
    for needle in (
        "if (sx == sy && originalWidth * sx == width &&",
        "originalHeight * sy == height)",
        "vertices[i * stride]",
        "vertices[i * stride + 1]",
        "OutRunVrUiAspect::BoundedMultiSpriteContainScale(",
        "sx, sy, width, height, originalWidth, originalHeight);",
        "if (!(contain > 0.0f))",
        "transformedX[i] = CenterMultiSpriteAxis(",
        "x, sx, contain, width, originalWidth);",
        "transformedY[i] = CenterMultiSpriteAxis(",
        "y, sy, contain, height, originalHeight);",
        "vertices[i * stride] = transformedX[i];",
        "vertices[i * stride + 1] = transformedY[i];",
        "if (!std::isfinite(transformedX[i]) ||",
        "!std::isfinite(transformedY[i]))",
        "mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade",
        "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.ecx), 9);",
        "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.esp + 0x80), 11);",
        "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.edx), 13);",
    ):
        if needle not in group:
            raise AssertionError("multi-sprite XY aspect: " + needle)
    # All four corners must be checked before any output vertex is touched.
    assert group.index("if (!std::isfinite(transformedX[i]) ||") < group.index(
        "vertices[i * stride] = transformedX[i];"
    )
    # Every stride owner must independently protect the same two UI modes;
    # finding one surviving guard must not hide mutation of another hook.
    assert group.count("mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade") == 3
    assert group.count("CenterMultiSpriteQuad(reinterpret_cast<float*>") == 3


require_multi_sprite_native_aspect(text)

def axis(pixel, axis_scale, contain, extent, authored_extent):
    return pixel / axis_scale * contain + (extent - authored_extent * contain) / 2.0

# Width/height-independent containment for full native 640x480 4:3 quads.
# 16:9 and 21:9 remain unchanged in Y, while 2496x2688 must letterbox Y
# rather than stretch an authored rectangle to the portrait eye height.
for width, height in ((1280, 960), (1920, 1080),
                      (2560, 1080), (2496, 2688)):
    sx, sy = width / 640, height / 480
    contain = min(sx, sy)
    x0 = axis(0, sx, contain, width, 640)
    x1 = axis(width, sx, contain, width, 640)
    y0 = axis(0, sy, contain, height, 480)
    y1 = axis(height, sy, contain, height, 480)
    assert abs((x1-x0)/(y1-y0) - 640/480) < 1e-6
    assert abs((x0+x1)/2 - width/2) < 1e-6
    assert abs((y0+y1)/2 - height/2) < 1e-6
assert axis(0, 5.6, 3.9, 2688, 480) == 408
assert axis(2688, 5.6, 3.9, 2688, 480) == 2280

for good, bad in (
    ("if (sx == sy && originalWidth * sx == width &&",
     "if (sx == sy && originalWidth * sx != width &&"),
    ("originalHeight * sy == height)",
     "originalHeight * sy != height)"),
    ("vertices[i * stride + 1] = transformedY[i];",
     "vertices[i * stride + 1] = vertices[i * stride + 1];"),
    ("y, sy, contain, height, originalHeight);",
     "y, sx, contain, height, originalHeight);"),
    ("CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.ecx), 9);",
     "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.ecx), 11);"),
    ("CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.esp + 0x80), 11);",
     "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.esp + 0x80), 9);"),
    ("CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.edx), 13);",
     "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.edx), 9);"),
    ("mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade",
     "mode == ScalingMode::Vanilla || mode == ScalingMode::OnlineArcade"),
    ("!std::isfinite(transformedY[i]))",
     "false)"),
):
    assert good in text, "mutation source anchor missing: " + good
    before, group = text.split("static void CenterMultiSpriteQuad(", 1)
    mutant = before + "static void CenterMultiSpriteQuad(" + group.replace(good, bad, 1)
    try:
        require_multi_sprite_native_aspect(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("undetected multi-sprite XY regression: " + bad)

# Zero-work path must cover exact native 4:3 and proportional 16:9 sources
# with a uniform authored coordinate scale; any rounded/anisotropic target
# still requires geometry normalization.
def exact_native_identity(sx, sy, src_width, src_height, width, height):
    return sx == sy and src_width * sx == width and src_height * sy == height

assert exact_native_identity(2.0, 2.0, 640, 480, 1280, 960)
assert exact_native_identity(1.0, 1.0, 640, 480, 640, 480)
assert not exact_native_identity(3.0, 2.25, 640, 480, 1920, 1080)
assert not exact_native_identity(3.9, 5.6, 640, 480, 2496, 2688)
assert not exact_native_identity(2.0, 2.0, 640, 480, 1280, 961)
assert not exact_native_identity(2.0, 2.0, 640, 480, 1279, 960)

print("DX9Ex menu multi-sprite native XY aspect PASS (9 negative controls, native fastpath)")


# The custom-matrix/menu path must never submit a half-mutated global quad
# when a device reset or malformed sprite matrix yields a bad vertex.
def require_atomic_custom_matrix(source: str) -> None:
    body = source.split("static void __cdecl draw_sprite_custom_matrix_mid(", 1)[1].split(
        "// Adjust positions of sprites in 3d space", 1)[0]
    for required in (
        "std::array<float, 28> quad{};",
        "if (!device)",
        "FAILED(descHr) || v25.Width == 0 || v25.Height == 0",
        "const std::size_t base = i * 7;",
        "!std::isfinite(quad[base])",
        "!std::isfinite(quad[base + 1]) ||",
        "!std::isfinite(quad[base + 2])",
        "!std::isfinite(quad[base + 5])",
        "!std::isfinite(quad[base + 6]))",
        "std::copy(quad.begin(), quad.end(), g_spriteVertexStream);",
        "device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2u, g_spriteVertexStream, 0x1Cu);",
    ):
        if required not in body:
            raise AssertionError("custom matrix atomic quad missing: " + required)
    assert "g_spriteVertexStream[" not in body
    assert body.index("FAILED(descHr)") < body.index("std::array<float, 28> quad{};")
    assert body.index("const std::size_t base = i * 7;") < body.index(
        "std::copy(quad.begin(), quad.end(), g_spriteVertexStream);")
    assert body.index("std::copy(quad.begin(), quad.end(), g_spriteVertexStream);") < body.index(
        "device->DrawPrimitiveUP(")
    assert body.count("quad[") >= 28

require_atomic_custom_matrix(text)
for good, bad in (
    ("std::copy(quad.begin(), quad.end(), g_spriteVertexStream);",
     "std::copy(quad.begin(), quad.begin(), g_spriteVertexStream);"),
    ("!std::isfinite(quad[base + 1])",
     "!std::isfinite(quad[base + 1]) && false"),
    ("!std::isfinite(quad[base + 6])",
     "!std::isfinite(quad[base + 6]) && false"),
    ("std::array<float, 28> quad{};",
     "std::array<float, 27> quad{};"),
):
    assert good in text
    try:
        require_atomic_custom_matrix(text.replace(good, bad, 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("unsafe custom matrix mutation escaped: " + bad)
print("DX9Ex custom matrix complete quad publishing PASS (4 negative controls)")


# 00880: D3DX specifies optional scaling and translation independently.
# Front-end sprites supplying only one must still get aspect containment,
# while gameplay/HUD and both-present/both-absent original routes stay intact.
def require_partial_menu_vectors(code: str) -> None:
    require_frontend_owner(code)
    # Constrain the check to this path, not the earlier pivot branch or
    # unrelated D3DX sprite consumers. The hook now saves the result first.
    body = code.split("const bool partialFrontEndMenu =", 1)[1].split(
        "const int result = D3DXMatrixTransformation2D.stdcall<int>", 1)[0]
    for required in (
        "originalFrontEndProducer;",
        "((pScaling == nullptr) != (pTranslation == nullptr))",
        "Game::screen_scale && Game::screen_resolution",
        "pScaling ? pScaling->x : 1.0f",
        "pTranslation ? pTranslation->x : 0.0f",
        "const auto affine = OutRunVrUiAspect::BuildFrontEndAffineContain(",
        "const float nextTx = affine.MapX(inputTx);",
        "const float nextTy = affine.MapY(inputTy);",
        "if (affine.valid && std::isfinite(nextSx)",
        "forwardedScaling = (&localScaling);",
        "forwardedTranslation = (&localTranslation);",
    ):
        assert required in body, "partial menu matrix path missing: " + required
    assert "GameState::STATE_GOAL" not in body, "GOAL must not become a menu owner"
    assert "GameState::STATE_RACE" not in body, "Gameplay must not become a menu owner"
    assert body.index("sourceSx > 1.0e-6f") < body.index(
        "const auto affine = OutRunVrUiAspect::BuildFrontEndAffineContain(") < body.index("forwardedScaling = (&localScaling);")

require_partial_menu_vectors(text)
for old, bad in (
    ("originalFrontEndProducer;", "true;"),
    ("((pScaling == nullptr) != (pTranslation == nullptr))",
     "(pScaling == nullptr && pTranslation == nullptr)"),
    ("pScaling ? pScaling->x : 1.0f", "pScaling->x"),
    ("pTranslation ? pTranslation->x : 0.0f", "pTranslation->x"),
    ("const float nextTx = affine.MapX(inputTx);",
     "const float nextTx = inputTx;"),
):
    # Mutate the exact producer under test. Global replace used to hit
    # frontEndPivot first after 00883 introduced its own state list, making
    # this negative test report a false failure on an unchanged partial path.
    prefix, rest = text.split("const bool partialFrontEndMenu =", 1)
    path_body, suffix = rest.split(
        "const int result = D3DXMatrixTransformation2D.stdcall<int>", 1)
    assert old in path_body, "missing scoped mutation anchor: " + old
    mutant = (prefix + "const bool partialFrontEndMenu =" +
              path_body.replace(old, bad, 1) +
              "const int result = D3DXMatrixTransformation2D.stdcall<int>" +
              suffix)
    try:
        require_partial_menu_vectors(mutant)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Optional menu D3DX mutant escaped: " + bad)

# 00883: rotated/pivoted front-end matrices are corrected only AFTER the
# original D3DX call. Pin the actual output rows, atomic finite publish and
# the specific title/car-selection state boundary independently of partial
# nullable vector staging.
def require_pivot_containment(source: str) -> None:
    block = source.split("const bool frontEndPivot =", 1)[1].split(
        "static inline SafetyHookMid draw_sprite_custom_matrix_hk", 1)[0]
    guard = block.split("if (!frontEndPivot", 1)[0]
    body = block.split("const int result = D3DXMatrixTransformation2D.stdcall<int>", 1)[1]
    require_frontend_owner(source)
    assert "originalFrontEndProducer," in guard, "pivot must use original mode"
    for required in (
        "if (frontEndPivot && result && pOut &&",
        "const auto affine = OutRunVrUiAspect::BuildFrontEndAffineContain(",
        "const float ratioX = affine.ratioX;",
        "const float ratioY = affine.ratioY;",
        "if (affine.valid && std::isfinite(mapped.m11)",
        "const UiMatrix2DRows raw{pOut->_11, pOut->_12,",
        "const auto mapped = ContainUiMatrixRows(",
        "std::isfinite(mapped.m11) && std::isfinite(mapped.m12)",
        "std::isfinite(mapped.tx) && std::isfinite(mapped.ty)",
        "pOut->_11 = mapped.m11;",
        "pOut->_12 = mapped.m12;",
        "pOut->_21 = mapped.m21;",
        "pOut->_22 = mapped.m22;",
        "pOut->_41 = mapped.tx;",
        "pOut->_42 = mapped.ty;",
    ):
        assert required in body, "pivot containment path missing: " + required
    assert body.index("std::isfinite(mapped.m11)") < body.index("pOut->_11 =")
    assert body.index("const float ratioY =") < body.index("pOut->_42 =")


require_pivot_containment(text)
for old, bad in (
    ("originalFrontEndProducer,", "true,"),
    ("const float ratioY = affine.ratioY;", "const float ratioY = affine.ratioX;"),
    ("pOut->_12 = mapped.m12;", "pOut->_12 = mapped.m11;"),
    ("std::isfinite(mapped.tx) && std::isfinite(mapped.ty)",
     "std::isfinite(mapped.tx) || std::isfinite(mapped.ty)"),
):
    prefix, rest = text.split("const bool frontEndPivot =", 1)
    path_body, suffix = rest.split(
        "static inline SafetyHookMid draw_sprite_custom_matrix_hk", 1)
    assert old in path_body, "pivot scoped mutation anchor missing: " + old
    mutant = (prefix + "const bool frontEndPivot =" +
              path_body.replace(old, bad, 1) +
              "static inline SafetyHookMid draw_sprite_custom_matrix_hk" +
              suffix)
    try:
        require_pivot_containment(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("Pivot containment mutant escaped: " + bad)


def partial_contain(viewport, scaling=None, translation=None):
    width, height = viewport
    sx, sy = width / 640.0, height / 480.0
    contain = min(sx, sy)
    ix, iy = (1.0, 1.0) if scaling is None else scaling
    tx, ty = (0.0, 0.0) if translation is None else translation
    return ((ix/sx*contain, iy/sy*contain),
            (tx/sx*contain+(width-640*contain)/2.0,
             ty/sy*contain+(height-480*contain)/2.0))

for viewport in ((640,480),(1920,1080),(3440,1440),(2496,2688)):
    for supplied_scale, supplied_translation in (
        ((1.25,0.75), None), (None,(120.0,70.0))):
        got=partial_contain(viewport,supplied_scale,supplied_translation)
        reference=partial_contain(viewport,
            supplied_scale if supplied_scale is not None else (1.0,1.0),
            supplied_translation if supplied_translation is not None else (0.0,0.0))
        assert got == reference
        assert all(isfinite(x) for pair in got for x in pair)
    if viewport[0]/viewport[1] > 640/480:
        scale, offset = partial_contain(viewport,(1.0,1.0),None)
        assert scale[0] == scale[1] or scale[0] < scale[1]
        assert offset[0] >= 0.0
print("PASS optional front-end D3DX scale/translation containment and five destructive controls")

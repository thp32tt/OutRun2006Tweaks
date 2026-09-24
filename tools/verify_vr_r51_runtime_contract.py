from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"missing R51 contract file: {rel}")
    return path.read_text(encoding="utf-8")


def require(rel: str, *markers: str) -> str:
    data = read(rel)
    for marker in markers:
        if marker not in data:
            raise SystemExit(f"missing protected R51 invariant: {rel} :: {marker}")
    return data


sem = require(
    "src/vr/game/render_semantics.hpp",
    "ScreenOverlay2D",
    "ScreenHud",
    "RegisterSpriteNodeScope",
    "ConsumeSpriteNodeScope",
    "SelectSpriteQueueNode",
    "EndSpriteQueueRender",
)

ui = require(
    "src/hooks_uiscaling.cpp",
    "VRHudQueueSemanticBridge",
    "Module::exe_ptr(0x2D762)",
    "Module::exe_ptr(0x2DCB4)",
)
if re.search(r"create_(?:mid|inline)\s*\([^;\n]*0x2D734", ui, re.IGNORECASE):
    raise SystemExit("protected R51 invariant violated: unsafe SpriteNode queue-entry hook 0x2D734 reintroduced")

require(
    "src/vr/game/outrun_renderer.cpp",
    "CorroboratesHud(semanticScope)",
    "CorroboratesScreenOverlay2D",
    "CorroboratesWorld(semanticScope)",
    "SemanticOverlayBypassCalls",
    "RecordGameWvpWrite",
)

require(
    "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
    "R30ConfigureXyzrhwWorldEffect",
    "R30ClassifyScreenSpacePass",
    "R47SemanticHudAccepted",
    "R50SemanticOverlay2DAccepted",
    "R30ScreenSpaceKind::WorldBillboard",
)

workflow = read(".github/workflows/vr-dx9ex-active.yml")
required_flag = "-DOUTRUN_VR_R26_HUD_COMPARE=ON"
if required_flag not in workflow:
    raise SystemExit(f"protected R51 build contract missing: {required_flag}")
if "-DOUTRUN_VR_R26_HUD_COMPARE=OFF" in workflow:
    raise SystemExit("protected R51 build contract regressed: active DX9Ex workflow contains R26_HUD_COMPARE=OFF")



# Exact SCREEN_HUD draw ownership is discovered after the game's c64 upload.
# Prevent the pre-draw world WVP verifier from vetoing the later exact HUD tag.
safe = read("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
hud_marker = "R51 HUD lifetime bridge: c64 is uploaded before the canonical"
if hud_marker not in safe:
    raise SystemExit("protected R51 HUD lifetime bridge missing")
hud_begin = safe.find("R51 HUD lifetime bridge:")
hud_end = safe.find("return R30ScreenSpaceKind::PerspectiveHud;", hud_begin)
if hud_begin < 0 or hud_end < 0:
    raise SystemExit("protected R51 HUD lifetime bridge malformed")
hud_block = safe[hud_begin:hud_end]
for forbidden in ("CurrentDrawMatchesVerifiedWorld(device)", "R28CanRebindVerifiedWorld("):
    if forbidden in hud_block:
        raise SystemExit(f"HUD lifetime regression: exact SCREEN_HUD is vetoed by pre-draw world gate: {forbidden}")

print("R51 protected runtime contract: PASS")

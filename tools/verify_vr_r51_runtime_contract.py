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



# Stereo SkyGlow ping-pong ownership: horizontal writes temp->reduced; the
# optional vertical pass writes reduced->temp. Composite the newest result.
safe = read("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
if "IDirect3DTexture9* compositeSource =\n                    R30SkyGlow.reduced[eye];" not in safe:
    raise SystemExit("SkyGlow regression: one-pass composite is not horizontal reduced result")
if "compositeSource = R30SkyGlow.temp[eye];" not in safe:
    raise SystemExit("SkyGlow regression: two-step composite is not vertical temp result")

print("R51 protected runtime contract: PASS")

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



# D3D9Ex Reset contract: ResetCompatDeviceR15 must replay fresh-device state
# explicitly and must never create/apply a pre-Reset D3DSBT_ALL state block.
r15 = read("src/vr/d3d9/ex_device_upgrade_r15.cpp")
reset_begin = r15.find("bool ResetCompatDeviceR15(")
reset_end = r15.find("void R15RollbackHooks()", reset_begin)
if reset_begin < 0 or reset_end < 0:
    raise SystemExit("R15 Reset contract missing")
reset_block = r15[reset_begin:reset_end]
for required in (
    "RestoreClassicResetState(device)",
    "R15RestoreClassicExtraBaseline(device)",
    "SetExternalSafetyBlock(!healthy)",
):
    if required not in reset_block:
        raise SystemExit(f"R15 Reset regression: missing explicit fresh-device replay/fail-close marker: {required}")
for forbidden in ("CreateStateBlock(", "stateBlock->Apply(", "D3DSBT_ALL, &"):
    if forbidden in reset_block:
        raise SystemExit(f"R15 Reset regression: pre/post Reset state-block replay reintroduced: {forbidden}")

print("R51 protected runtime contract: PASS")

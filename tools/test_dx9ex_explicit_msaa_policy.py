from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/hooks_graphics.cpp").read_text(encoding="utf-8")

required = (
    '"OUTRUN_VR_BACKEND"',
    'lstrcmpiA(backend, "d3d9") == 0',
    'D3DMULTISAMPLE_4_SAMPLES',
    'D3DMULTISAMPLE_2_SAMPLES',
    'CheckDeviceMultiSampleType',
    'params.MultiSampleType = sampleType',
    'params.MultiSampleQuality =',
    'explicit {}x MSAA selected',
    'replaces ambiguous NONMASKABLE game AA',
)
missing = [item for item in required if item not in source]
if missing:
    raise SystemExit(f"DX9Ex explicit MSAA policy missing markers: {missing}")

block_start = source.index("static void ConfigureReferenceVRMSAA()")
block_end = source.index("static void destination(safetyhook::Context& ctx)", block_start)
block = source[block_start:block_end]
if block.index("D3DMULTISAMPLE_4_SAMPLES") > block.index("D3DMULTISAMPLE_2_SAMPLES"):
    raise SystemExit("DX9Ex MSAA policy must try 4x before 2x")
if 'lstrcmpiA(backend, "d3d9") == 0' not in source:
    raise SystemExit("DX9Ex MSAA policy must be isolated to the d3d9 backend")
if "D3DSWAPEFFECT_DISCARD" not in block:
    raise SystemExit("DX9Ex MSAA policy must fail safe for non-DISCARD swap effects")

validate_start = source.index("bool validate() override", block_end)
validate_end = source.index("void declare_settings() override", validate_start)
validate_block = source[validate_start:validate_end]
if "IsNativeD3D9ReferenceLaunch()" not in validate_block:
    raise SystemExit(
        "DX9Ex explicit MSAA hook must install even when CORRECTNESS keeps default VSync"
    )

print("DX9Ex explicit 4x->2x MSAA policy: PASS")

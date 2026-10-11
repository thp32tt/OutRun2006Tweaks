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
    'params.MultiSampleQuality = 0',
    'params.MultiSampleType = D3DMULTISAMPLE_NONE;',
    'const int vrMode = Settings::VRAntiAliasing.get();',
    'if (vrMode == 3)',
    'if (vrMode == 0)',
    'vrMode == 1 && sampleType != D3DMULTISAMPLE_2_SAMPLES',
    'using Off (not game 2D AA)',

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

# F11 auto-registers named VR int settings as a Combo and marks restart.
settings = (ROOT / "src/vr/settings.cpp").read_text(encoding="utf-8")
overlay = (ROOT / "src/overlay/settings_ui.cpp").read_text(encoding="utf-8")
ini = (ROOT / "OutRun2006Tweaks.ini").read_text(encoding="utf-8")
for marker in (
    '"VR", "AntiAliasing", 2',
    '"Off (fastest)", "2x MSAA", "4x MSAA (fallback 2x)", "Use Game/2D AA"',
    '"VR", "TransparencySupersampling", false',
    "Settings::VRAntiAliasing.needs_restart();",
    "Settings::VRTransparencySupersampling.needs_restart();",
):
    if marker not in settings and marker not in source:
        raise SystemExit(f"F11 VR AA setting missing: {marker}")
for marker in (
    "ImGui::Combo(label.c_str(), value->ptr(), names.data(), int(names.size()))",
    "draw_restart_notice()",
    "Settings::write(Module::UserIniPath)",
):
    if marker not in overlay:
        raise SystemExit(f"F11 persistence/restart missing: {marker}")
for marker in ("AntiAliasing = 2", "TransparencySupersampling = false"):
    if marker not in ini[ini.index("[VR]"):ini.index("[WheelFFB]")]:
        raise SystemExit(f"VR config default missing: {marker}")
if ("return Settings::TransparencySupersampling &&" not in source or
    "!activeNativeVr || Settings::VRTransparencySupersampling" not in source or
    'lstrcmpiA(backend, "d3d9") == 0' not in source):
    raise SystemExit("2D/VR transparency AA isolation missing")
if block.index("if (vrMode == 3)") > block.index("params.MultiSampleType = D3DMULTISAMPLE_NONE"):
    raise SystemExit("Use Game AA must bypass VR override")
if block.index("if (vrMode == 0)") > block.index("CheckDeviceMultiSampleType"):
    raise SystemExit("Off must avoid costly multisample capability checks")

# Four negative mutations ensure these are functional gates, not just menu labels.
negative_mutations = [
    ('params.MultiSampleType = D3DMULTISAMPLE_NONE;', '/* removed off override */'),
    ('vrMode == 1 && sampleType != D3DMULTISAMPLE_2_SAMPLES', 'false'),
    ('if (vrMode == 3)', 'if (vrMode == 5)'),
    ('!activeNativeVr || Settings::VRTransparencySupersampling', 'true'),
]
for before, after in negative_mutations:
    if before not in source: raise SystemExit(f"negative seed missing: {before}")
    changed = source.replace(before, after, 1)
    # Mutation must break one of the listed invariants.
    witness = before not in changed and (
        before in required or
        before in ('if (vrMode == 3)', 'vrMode == 1 && sampleType != D3DMULTISAMPLE_2_SAMPLES',
                   '!activeNativeVr || Settings::VRTransparencySupersampling')
    )
    if not witness: raise SystemExit(f"negative mutation not detected: {before}")
# Regression for F11 setting persistence under DX9Ex launch profile overrides.
settings_core = (ROOT / "src/settings.cpp").read_text(encoding="utf-8")
bootstrap = (ROOT / "src/dllmain.cpp").read_text(encoding="utf-8")
wndproc = (ROOT / "src/overlay/hooks_overlay.cpp").read_text(encoding="utf-8")
selector = (ROOT / "tools/OutRunVR-Slot-Selector.ps1").read_text(encoding="utf-8")
for marker in ("commandLineOverrides.insert(setting);",
               "commandLineOverrides.find(setting) == commandLineOverrides.end() && setting->write(ini)"):
    if marker not in settings_core: raise SystemExit("CLI override persistence isolation missing: " + marker)
if 'Settings::DisableSettingsWrite = true;' in bootstrap:
    raise SystemExit("Launch CLI still globally disables F11 INI persistence")
for marker in ("WM_SETCURSOR", "LoadCursorW(nullptr, IDC_ARROW)", "LOWORD(wParam) != WA_INACTIVE"):
    if marker not in wndproc: raise SystemExit("F11 mouse pointer/focus fix missing: " + marker)
if "-WindowStyle Hidden" not in selector or "FormWindowState]::Minimized" not in selector:
    raise SystemExit("Game launch must not leave PowerShell or selector in foreground")
if '"VR", "MirrorFitDesktop", true' not in settings or "MirrorFitDesktop = true" not in ini:
    raise SystemExit("Monitor-fit VR mirror default missing")
print("DX9Ex F11 VR AA 4x default/2x/Off/Game + write isolation/cursor/window: PASS (4 negative mutations)")

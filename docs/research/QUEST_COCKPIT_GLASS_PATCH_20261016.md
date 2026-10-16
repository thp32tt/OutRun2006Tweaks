# Quest-derived cockpit glass material patch (2026-10-16)

## Direct APK evidence

The user's locally supplied OutRun 2006 Quest port contains 31 player-car PMT model variants. A bounded parser matched 48 distinct dark-gray semitransparent material instances, usually diffuse alpha around 0.55 (F40 0.42478), with D3D-style blend factors SRC=ZERO or SRCALPHA and DST=INVSRCALPHA. This is evidence for glass-like dark-tint materials, **not yet proof of each windshield/side window polygon or PC renderer parity**.

Separate Quest ARM64 disassembly showed `cockpit_glass_opacity` and `cockpit_glass_premultiplied` thread-local material states read by `Flush::draw_404700` and `GlD3D9Device::flush`. Do not change the entire game's D3DRS_ALPHABLENDENABLE, water, HUD or player-body alpha based on these states.

## Source implementation

`tools/quest_cockpit_glass.py` parses the user's own PMT model, with object/material/color table bounds and a strict **player-car filename + dark-tint RGBA + original blend mode + unshared material-color** filter. It changes only matched color-alpha floats to configurable `0.30` by default. It preserves all other raw binary bytes and writes a **separate output file only**; existing originals/outputs cannot be overwritten. Malformed or unknown model files are rejected.

Example:
```bash
python tools/quest_cockpit_glass.py /path/to/obj_plcar_360sp_pmt.sz /path/to/copied/obj_plcar_360sp_pmt.sz --dry-run
python tools/quest_cockpit_glass.py /path/to/obj_plcar_360sp_pmt.sz /path/to/copied/obj_plcar_360sp_pmt.sz --opacity 0.30
```

For a specific identified material add `--only 0:2` (object:material, can repeat). Dry-run first. Do not install output until confirming that the Windows installation uses the same PMT file format. Preserve game files and back up before replacement. No APK/PMT binary is redistributed in this repo.

## Tests and remaining integration

Local integration against 31/31 actual user APK PMT variants and 48 material instances passed; non-alpha raw bytes stayed identical and 93 negative tamper checks rejected. `tools/tests/test_quest_cockpit_glass.py` is a synthetic no-asset regression of selectivity, reject/recovery, blend/material mismatch and payload preservation.

**This patcher produces a modified player-car model file. It is not yet wired into OutRun2006Tweaks' in-game model loading.** Before claiming front + side windows visibly translucent: match actual PC installed PMT, identify glass polygon material group, integrate replacement via a verified game-model loader, test both eye render targets, alpha/Z blend and driver/passenger/dashboard visibility on Quest 3. RUNTIME_VALIDATION=UNTESTED. The existing DX9Ex camera and drivers remain unchanged.

from pathlib import Path
import sys

SOURCE = Path("src/vr/d3d9/stereo_renderer_r30.cpp")
text = SOURCE.read_text(encoding="utf-8")

start = text.find("bool R30ApplyStereoSkyGlow(IDirect3DDevice9* device)")
if start < 0:
    raise SystemExit("R30ApplyStereoSkyGlow not found")
end = text.find("HRESULT __stdcall PresentDestR30", start)
if end < 0:
    end = min(len(text), start + 24000)
body = text[start:end]

horizontal = "R30SkyGlow.temp[eye],\n                        R30SkyGlow.blur, horizontal, false)"
vertical = "R30SkyGlow.reduced[eye],\n                            R30SkyGlow.blur, vertical, false)"
fixed_one_step = "IDirect3DTexture9* compositeSource =\n                    R30SkyGlow.reduced[eye];"
fixed_two_step = "compositeSource = R30SkyGlow.temp[eye];"
buggy_one_step = "IDirect3DTexture9* compositeSource =\n                    R30SkyGlow.temp[eye];"
buggy_two_step = "compositeSource = R30SkyGlow.reduced[eye];"

checks = {
    "horizontal temp->reduced pass present": horizontal in body,
    "vertical reduced->temp pass present": vertical in body,
    "one-step composites horizontal output reduced": fixed_one_step in body,
    "two-step composites vertical output temp": fixed_two_step in body,
    "buggy one-step source removed": buggy_one_step not in body,
    "buggy two-step source removed": buggy_two_step not in body,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS" if ok else "FAIL") + ": " + name)
if failed:
    print("SkyGlow ping-pong verifier failed: " + "; ".join(failed), file=sys.stderr)
    raise SystemExit(1)
print("SkyGlow ping-pong source ownership verified.")

# Dino NoGlass FitV6 -- R26 sidecar test adapter

An original FitV6 GLB was previously generated in a separate conversation, but the actual file bytes are not committed to GitHub nor available in this conversation/N100.
Required exact filename: Dino246_NoGlass_FitV6_UniformProportions.glb.
The model already includes NoGlass and uniform 0.88 scale; never rescale it again.

New converter accepts exact GLB or containing ZIP, generates R26 OVC2 at the loader's stable filename Dino246_Cockpit_LHD_v15.ovc and records source/output SHA-256.
After original file is supplied, run: python tools/cockpit/dino_v15_external/convert_fitv6.py --v6 Dino246_NoGlass_FitV6_UniformProportions.glb --out-dir ./fitv6-test

The source is not included. Do not mislabel v15 as v6; a synthetic converter smoke test cannot validate the original FitV6 model.
Copy R26 verified dinput8.dll and generated OVC2 beside original game's EXE. Preserve original PMT and backing DLL; VR DriverSeatView=true and DinoExternalCockpit=true.
Quest 3 runtime: UNTESTED.

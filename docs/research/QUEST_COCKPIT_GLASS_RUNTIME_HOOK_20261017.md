# Canonical PC PMT material hook discovery — 2026-10-17

Verified original PC OR2006C2C.EXE (3,674,112 bytes, SHA256 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3), not the incompatible 962,560-byte Quest APK TestApp.EXE.

- Player/traffic vehicle renderer calls DrawObject_Internal (image VA 0x405360, EXE RVA 0x5360), repeatedly from DispCarModel_Common (e.g. VA 0x469831 and 0x469865).
- PMT model draw loop VA 0x4048F2 loads material base [esi+0x34]; 0x4048F5 multiplies material index by 0x58 (88-byte record); 0x4048FF adds base; 0x404901 PUSH EDX; 0x404902 CALL 0x408C80. Material apply reads packed attributes at [material+4] via VA 0x408CD2 and conditionally calls 0x408F90.
- The material's first DWORD is a possible color-table index; attr blend bits 8–11 and 12–15 permit Quest candidate blends (1,5) and (4,5). They do NOT prove this material is front or side window.
- Opt-in source hook VRDriverSeatGlassMaterialProbe performs exact six-byte signature check at EXE+0x4901, logs at most 32 unique candidate material addresses in cockpit gameplay and otherwise leaves PMT, D3D9, water, HUD, driver and vehicle alpha unchanged. Enable DriverSeatGlassMaterialTrace=true in INI before launch; the setting needs restart.
- GLASS PROBE logs can include WORLD and NPC materials (not a verified player vehicle ID). Correlate exact car model + PMT material/color table + draw scope with visual HMD tests before writing F11-adjustable live alpha override. The prior PMT file-edit tool remains independent and is not a live render hook.

RUNTIME_VALIDATION=UNTESTED for real game/Quest 3 until an actual run is observed. This step is hook-point discovery and bounded instrumentation, **not** completed glass opacity editing.

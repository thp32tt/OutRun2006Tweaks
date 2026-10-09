# OutRun 2006 DX9Ex VR: HUD / screen composition night test (2026-10-09)

**Quest 3/VDXR** • **Current candidate: HMD UNTESTED**. Package includes original 32-bit dinput8.dll and x64 OpenXR host.

Extract into the OR2006C2C.EXE folder. Double-click **OutRunVR-Slot-Selector.cmd**, select **B HUD** and click **설정 + 바로 실행**. Run **C FLARE / WORLD** separately only if checking flare/markers. Avoid changing two variables at once.

Test the following distinct visual cases without confusing source CI with HMD success:

1. Gameplay HUD scale, gear, score and **6th/6** stable in both eyes.
2. Ordinal 1–5 labels attached to cars under head yaw (4/5 previously known-good); rival icon remains attached.
3. **GOAL/time immediately before restart**: keep **both** course/stage label and record time (two original GOAL helpers). Check each for white/translucent doubled text and head-following.
4. **+TIME** transient after a checkpoint. Judge separately from GOAL and completed result screen.
5. Menu arrows and YES/NO, car-selection DDS, no white rectangles, no duplicate letters. Mono restart/TRYAGAIN is expected; F11 previously accepted.
6. C FLARE / WORLD: lens *centre dot* distinct from other discs, start shadow, world/road stereo.
7. Recenter and overall FPS/72Hz regression.

After closing the game, upload **OutRun2_VR_ANALYZE_*.zip** collected by the included scripts. Telemetry labels `VR P0 GOAL EARLY_GATE`, `VR P0 PRE_RESTART_HUD_FORM`, `VR P0 RESULT DRAW ROUTE`, `VR R51 DRAW FINGERPRINT`, `VR R62 FIXEDFN KIND0` distinguish the actual queue/Shader/XYZRHW/FVF0x142 path. This build fixes **diagnostic rearming on a second GOAL/TIMEUP episode**; it DOES NOT prove or claim an optical +TIME, GOAL or flare repair without a real headset test. Preserve original game timer and both GOAL sources.

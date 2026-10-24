---
name: outrun-vr-hud-optics
description: Debug OutRun 2006 VR HUD placement, menus, rank markers, lens flare, sun, +TIME, GOAL and stereo optics.
---

# HUD / Optics
1. Pin exact SHA and reproduce one screen defect; compare same scene/config on R26+HUD and R84_TEST without mixing baselines.
2. Determine owning original game producer or proven queue tag, then exact physical Draw and stereo eye route.
3. Keep lens centre separate from outer flare and SkyGlow; projected car rank separate from screen rank digits; F11 ImGui separate from native ESC.
4. +TIME and GOAL can contain sprite and glyph batches; never equate one producer with exactly one Draw.
5. Use Native, RotationOnly, WorldStereo, ZeroDisparity, FiniteHud and diagnostic Hidden as per-fingerprint reversible route probes only after positive identity.
6. Do not promote a family based on alpha/Z, texture or FVF alone; revert ineffective symptom stacking.
7. User's HMD result is the final gate; untested new SHA remains RUNTIME_VALIDATION=UNTESTED.

---
name: outrun-vr-draw-trace
description: Diagnose physical DX9Ex or DX11 GPU draws and provenance for OutRun 2006 VR; use for duplicate sun, lens flare, +TIME, GOAL, rank or unknown stereo draws.
---

# Physical Draw Diagnosis
1. Read AGENTS.md and active feature lease; choose current compiled backend, not obsolete R84-only owners.
2. Use R26+HUD as current focus, R84_TEST as controlled comparison; never edit DX11/DXVK lanes accidentally.
3. For telemetry, enable VRTelemetry explicitly and gather original producer, queue epoch, Draw API, shader/FVF, original transform, RT/viewport, route and eye results.
4. Treat UNKNOWN provenance, non-paired draws and absent events as UNKNOWN / NOT_OBSERVED, never automatically mono.
5. Prefer source-owned labels: the same texture/alpha/FVF does not identify the sun, lens, +TIME or menu.
6. Correlate R26 DRAW TRACE with HUD Inspector and captured HMD/host log by frame and build SHA.
7. If no physical per-eye evidence, say so; formulate one bounded probe, no broad renderer routing change.
8. Keep diagnostics opt-in; no synchronous GPU readbacks or per-draw log writing.

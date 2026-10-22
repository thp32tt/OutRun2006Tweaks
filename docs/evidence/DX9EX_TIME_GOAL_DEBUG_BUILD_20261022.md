# DX9Ex +TIME / GOAL debug test build — 2026-10-22

SOURCE_HEAD before trigger: `ff06fa03afe0347810a00e33fb60ee6aaf2f1e2a`

Purpose:
- Preserve current R26+HUD default renderer.
- Include current CABE projected-flare correction and native rival-marker restoration already in branch history.
- Use current +TIME exact source ownership (0x9898E, 0x98A36, 0x989AD, 0x98A10, 0x98A89).
- Preserve mode-2 0x98AC6 as a negative-control path; do not promote it to ScreenHud without runtime proof.
- Preserve safe GOAL result-progress and GOAL helper ownership.
- Keep the 19 unsafe B9200 E8+5 return-byte midhooks disabled because prior minidumps proved branch-into-detour crashes.
- Use the corrected F11 SOURCE-ASPECT telemetry field alignment already present in the current source.

Runtime capture request:
1. Enable VR telemetry/debug logging.
2. Drive until +TIME appears at least once.
3. Finish an OutRun mode run and keep the GOAL/result progress + record/time display visible.
4. Open F11 once in gameplay.
5. Exit normally so the diagnostic ZIP is sealed.

Expected useful records:
- VR P0 STAGE EXTENSION SOURCES
- producer STAGE_EXTENSION_TIME / STAGE_PLUS_TIME if physical ownership survives
- OUTRUN_RESULT_PROGRESS / GOAL_RESULT_TIMER
- RESULT_TEXT_B9200 if a safe proven child route owns the draw
- VR F11 SOURCE-ASPECT PROBE with dynamic mode + independent L/R HRESULT

RUNTIME_VALIDATION=UNTESTED until Quest3/VDXR run is completed.

Ferrari13 integrated Quest3 test build — 2026-11-19 (KST)
============================
1. Exit the game and VR host. Extract this entire ZIP DIRECTLY into the directory containing your original OR2006C2C.EXE.
2. Double click START-FERRARI13-VR.cmd (no separate install step).
3. On first start it SHA-checks 13 exact car bodies, 13 dashboard overlays and the integrated D3D9Ex DLL / host; backs up replaced game-folder files and copies matching assets.
4. It enables VR, stereo, QuestCockpitV2, external Ferrari loaders and diagnostic file logging. DirectGpuOnly=false allows fallback if D3D9Ex direct sharing isn't ready. It does NOT edit your INI or original game executable.
5. Enter a driving stage and select cockpit camera mode 1.
6. If WHITE SCREEN / freeze persists, run COLLECT-FERRARI13-LOGS.cmd from another window BEFORE killing the game. Share FERRARI13_DIAG/FERRARI13_LOGS_*.zip.
7. VERIFY-FERRARI13-VR.cmd checks payload without launching. On subsequent runs matching installed assets are reused, no repeated backups.
8. Logs are on for this troubleshooting build (OUTRUN_VR_FILE_LOG=1 and -FileLogging=true; bounded cockpit probe true, per-draw telemetry false). Diagnostic archive copies max 4MiB tail per log, 24MiB overall.
9. Existing FERRARI13_PRIVATE_BACKUP_* folders hold overwritten files for restoration using FERRARI13_PAYLOAD/RESTORE_FERRARI13.ps1.
10. No original OR2006C2C.EXE, original game PMT or any purchased game content is bundled. Private personal test only; third-party model public redistribution is not permitted.
11. Warning: visual/white-screen fix and headset cockpit rendering remain unverified until tested on Quest3. These logs should distinguish DLL loading from XR frame routing failures.
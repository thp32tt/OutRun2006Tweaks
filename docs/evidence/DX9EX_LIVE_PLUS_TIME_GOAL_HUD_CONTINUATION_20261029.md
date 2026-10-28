# DX9Ex live +TIME / GOAL / HUD continuation — 2026-10-29

BASE=444a490f7c521486363bc0d35adfa9598ef556eb

- Canonical live checkpoint +TIME remains EXE+0xBD217 -> 0x4B9320 with safe common leave at EXE+0xBD221.
- Historical 0x989xx result-panel hooks remain temporarily for GOAL compatibility, but telemetry now labels them GOAL_RESULT_PANEL_LEGACY instead of allowing them to be mistaken for the live popup.
- Exact GOAL B9200 provenance is 21 original callers, including 0x98D37 and 0xBE009.
- The existing 1920x1080 HUD side-spacing behavior remains 80 logical pixels in OnlineArcade mode. New bounded receipts log before/after X, scale and screen resolution so the next HMD run can prove whether the remaining centred HUD is producer coverage or geometry.
- F11, GOAL progress ownership, rival projection and menu pixel paths are unchanged by this telemetry patch.
RUNTIME_VALIDATION=UNTESTED_AFTER_PATCH.

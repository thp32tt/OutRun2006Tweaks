# DX9Ex HUD 1000-cycle review contract

A deterministic source/semantic/canonical EXE mutation audit, **not 1000 separate human visual reviews**.

- Run `python3 tools/audit_vr_hud_1000.py --cycles 1000 --batch 30` on an exact GitHub SHA.
- Each of the 1000 cycles checks all 10 source domains and the 71 CALL contract, then corrupts one rotating live source/contract anchor and requires rejection.
- Each 30 cycles save a JSON checkpoint with exact source digest, findings and mutation outcomes. Save final cycle 1000 too: **34 checkpoint files**, plus `summary.json`.
- The GitHub Actions run uploads the entire set even if a batch fails. Review/cycle data is durable in that run's retained artifact; logs show 30-cycle counters.
- This verifies contract drift/mutation rejection. Runtime/HMD remains **UNTESTED** and historical 00519 HUD/menu/lens visual FAIL stays open.
- Known unresolved evidence: F1 rank sprani 1-node assumption, F2 ScreenOverlay2D finite plane policy/documentation inconsistency, F3 actual DDS menu/car pixel/alpha/load proof.
- Investigate real failures, fix root cause on `vr-d3d9ex-focus` material commit and rerun exact-SHA CI. Never treat mere iteration count as repaired visual output.

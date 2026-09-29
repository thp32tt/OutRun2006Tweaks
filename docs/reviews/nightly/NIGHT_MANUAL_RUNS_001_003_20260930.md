# Manual morning runs 001-003 — 2026-09-30

Runtime reference: R73 `f437807922d7b9b32f9a7c7ced0442a5edab7c69`  
Policy: DISASSEMBLY-FIRST + RUNTIME-EVIDENCE-FIRST.

## Run 001 — R76 SkyGlow baseline validation recovery

- Candidate: `vr-d3d9ex-candidate/R76-SKYGLOW-BASELINE-RESTORE-20260930`.
- Previous source SHA: `19771aab468e79bd1dc9fdde17ccc74227da86e7`.
- GitHub run `36601827867`: host build PASS, game DLL compile/link PASS, final staging FAIL.
- Failure class: `STALE_PIPELINE_CONTRACT`, not product compile failure.
- Exact stale requirement: workflow still required the old R69 flare binary marker.
- Fix: update only `.github/workflows/vr-dx9ex-active.yml` to current R73 flare marker + R76 SkyGlow baseline marker and R76 variant ID.
- New SHA: `95ffeb2a8df11442d67489dd719313da334168e8`.
- Revalidation run: `36642615924` (running when checkpoint was written).
- RUNTIME_VALIDATION: UNTESTED.

## Run 002 — VR-HUD-SUMO-REPLAY-SEMANTIC-LOSS-001 diagnostic

- Candidate: `vr-d3d9ex-candidate/R77-HUD-REPLAY-TRACE-20260930`.
- Base: R74 exact result-progress candidate `a7bc1f1170d368b29e08f9e8d92ff1b4edb5ed8c`.
- Static defect reconfirmed: `SumoUISpriteReplay::Entry` previously copied priority/kind/SPRARGS/SPRARGS2 only and recreated a fresh node during `numUpdates==0` frames.
- Added diagnostic-only `PeekSpriteNodeScope` and bounded replay logs:
  - original node scope/owner/serial/payload hash at capture;
  - replayed fresh-node scope/owner/serial/payload hash after `put_sprite_ex`.
- No semantic is re-registered and no rendering behavior is changed.
- Commits:
  - `4e544ca7985c013a5bbef9c1737a15d5a79fbd65`
  - `1e5d3dbc2bb0dc20022dbe5d32c7b942dc46a2d7`
- Hosted validation run: `36642755369`.
- HUD Inspector run: `36642722342`.
- Falsification: if replayed nodes already retain the same exact scope as captured source nodes, replay semantic loss is not causal for the visible HUD defect.

## Run 003 — +TIME actual Sumo_Printf caller census

- Canonical EXE map artifact: workflow `36163825743`, artifact `10876509603`.
- Ghidra/SQLite map proves `FUN_0042CDD0` has exactly 31 direct callsites.
- Existing R71 assumptions `0x975EE/0x97727/0x977FB` are only 3 of the 31 and had zero R71 runtime HUD hits in the user's R73 session.
- Added diagnostic-only mid hook at RVA `0x2CDD6`, immediately after `SUB ESP,0x104`, where caller return address is recoverable from `ESP+0x104`.
- Diagnostic logs only in OutRun `game_mode=32`, reports exact call RVA, hit count, stage, state, and whether stage changed.
- No HUD ownership or drawing behavior is changed.
- Binary contract added:
  - RVA `0x2CDD6`
  - signature `a1005a73008b8c240801000056898424`.
- Commits:
  - `3868a50b1d9cb54d64ede010d6e9f47d082202ae`
  - `a8a1926de8eee961ac05582c181611847374091d`
- Next action: HMD log should identify which of the 31 real text callsites executes at checkpoint/+TIME onset, then map that exact caller back through Ghidra before any ownership patch.

## Regression boundaries

Do not regress R73 user-verified sky/menu-opacity/rival-marker/base-stereo/recenter/stage-transition behavior. No broad HUD promotion, flare scalar tuning, or selector budget increase was performed in runs 001-003.

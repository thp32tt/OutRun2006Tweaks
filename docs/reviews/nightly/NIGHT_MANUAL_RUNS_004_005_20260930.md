# Manual morning runs 004-005 — 2026-09-30

Runtime reference: R73 `f437807922d7b9b32f9a7c7ced0442a5edab7c69`.  
No HMD claim is made by these diagnostics.

## Run 004 — R79 lens-flare component ownership census

Candidate: `vr-d3d9ex-candidate/R79-FLARE-COMPONENT-TRACE-20260930`.

Canonical Ghidra evidence retained:
- `FUN_0040CBC0` calls `FUN_0040C9A0` at twelve exact parent edges:
  `0xD5F5,0xD624,0xD641,0xD65E,0xD68E,0xD6BA,0xD6E6,0xD712,0xD73E,0xD76A,0xD796,0xD7B4`.
- `0xCF4E` is the Calc3D2D anchor path.
- `0xCABE` is the exact DrawObjectAlpha_Internal edge.

Diagnostic changes:
- mid-hook at `0xC9A6`, after EBP frame setup, recovers the parent return callsite from `[EBP+4]`;
- exact `0xCABE` wrapper logs parent callsite, tick, objectId, alpha, work pointer and flags with power-of-two sampling;
- no transform/IPD/disparity or draw ownership behavior changes.

Binary contract:
- RVA `0xC9A6`
- signature `83ec58a168b589008b0d6cb58900403b`.

Commits:
- `d4875e8c4f8b0a59f18afa2bcc29237df3dd7907`
- `32b98afe0f94c06ad6b844707a29887c18587ae5`
- CI-contract alignment `ce6209536ba6cef82e2a8e70f1bafd4130c58899`.
- First validation failed only because the baseline verifier required the preserved R67 install marker. Classified `VERIFIER/PROVEN-MARKER CONTRACT`, not a product compile failure.
- Corrected by restoring the proven R67 marker in addition to the R79 diagnostic marker: `8576f5a025d9655ab2043f1ace2f78913dae7e41`.
- Revalidation run: `36643627546` (policy PASS; further jobs running at checkpoint time).

Falsification:
- If each logical flare tick shows only one relevant component/object and the duplicate appears only after stereo eye rendering, component multiplicity is not the root cause.
- If two or more stable component parent/object combinations overlap before stereo rendering, stop tuning eye disparity and isolate component semantics instead.

## Run 005 — R80 selector texture create/lock/bind correlation

Candidate: `vr-d3d9ex-candidate/R80-SELECTOR-TEXTURE-TRACE-20260930`.

Existing user runtime evidence:
- 2048x2048 fmt=21 DirectOnly cases;
- 2048x1024 fmt=21 selector companion reserve rejection / DirectOnly;
- DXT1 LockRect failure at level 1, descriptor 64x32, levels=4;
- level-1 64x32 is consistent with the existing level-0 128x64 DXT1 four-mip classifier.

Diagnostic changes:
- each translated MANAGED compatibility entry receives a monotonic `traceSerial`;
- exact known selector candidate resources log:
  - `VR R80 SELECTOR CREATE` with serial/pointer/mode/base descriptor;
  - `VR R80 SELECTOR LOCK` with serial/pointer/level/mode/flags/base descriptor;
  - `VR R80 SELECTOR BIND` from device vtable SetTexture index 65 with serial/pointer/stage/mode/base descriptor;
- SetTexture tracing is installed as part of the existing R14 resource hook transaction;
- no memory/shadow/cache budget is changed and no texture contents/state are modified.

Commits:
- source diagnostic `7fd124045d9ac6ea78cd4598353ed01cfe626de7`;
- CI marker alignment `eeef4ac5fb0c210267c571c3604d06cb19704800`.
- Hosted validation run: `36643551326` (policy PASS; game/host building at checkpoint time).

Decision gate:
Only if the same serial/pointer that failed or entered DirectOnly is later bound on the selector draw can MANAGED compatibility be promoted from correlation to a visible-material root cause. Otherwise sampler/sRGB/StateBlock state becomes the next diagnostic stage.

## Five-run status

- 001 R76 SkyGlow baseline recovery: validation run `36642615924` SUCCESS.
- 002 R77 replay semantic-loss runtime trace: diagnostic candidate created.
- 003 R78 exact OutRun Sumo_Printf caller census: all 31 canonical direct callers covered, new binary contract added.
- 004 R79 flare twelve-component census: diagnostic candidate created and verifier-contract correction applied.
- 005 R80 selector resource lifetime/bind correlation: diagnostic candidate created.

RUNTIME_VALIDATION for R77/R78/R79/R80: `UNTESTED / NEED_HMD_TEST`.

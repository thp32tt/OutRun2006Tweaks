# REA source-to-render scope correction — 2026-10-19 KST

Original executable SHA-256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.

## Proven original mode separation

REA+Ghidra original `0x00498670` mode switch and exact PE `E8 rel32` targets:

- `0x0049898E` → `0x00429530` (mode 1/9, `0x2C00B4`) = +TIME decoration
- `0x00498A36` → `0x00429530` (mode 0/7/8, `0x2C00B5`) = +TIME decoration
- `0x004989AD`, `0x00498A10`, `0x00498A89` = +TIME text/number support
- **`0x00498AC6` → `0x00429530` (mode 2, `0x2C006C`) is a different animation path** and does not belong to the two +TIME branches.

The original R84 `StageExtensionSpraniCalls` list labeled all three animations as `StageExtensionTime` / `ScreenHud`, with an exact source tag and D3DX batching owner. This changed the mode=2 sprite classification without an original producer justification. Narrow the list to the two proven extension parents; preserve all three true numeric/text source calls, the D3DX batch isolation, GOAL/Result hooks and the game’s original mode=2 rendering.

## Implementation and negative validation

- Changed source: `src/hooks_uiscaling.cpp`
- Regression: `tools/verify_vr_stage_extension_d3dx_batch_owner.py`
- REA evidence: original E8 opcode/target matches 6/6; stage animation membership 2, stage text parent membership 3
- Running current-ledger checker on proposed source: **0 errors**. Mutation reintroducing `0x98AC6` into stage owner: **1 detected error**.
- Do not re-hook `0x97C57+5` or `0x2D734`; preserve existing crash-tested ownership.
- `RUNTIME_VALIDATION=UNTESTED`: static/CI results do not prove a Quest3 optical bug was fixed.

Only the independent analysis and mod source/test are committed; original game binary, REA JSON and proprietary decompiled bodies remain on N100.

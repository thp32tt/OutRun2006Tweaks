# DX9Ex runtime visual repair — 2026-10-29

SOURCE_BASE=d3707b537436648924388d39894f392686d26d06
RUNTIME_INPUT=R26_VISUAL_OWNER_REPAIR_AA2_TEST-20261028-235426.zip

## Applied from runtime evidence
- Lens: the captured 43 sampled transactions all executed LEFT and RIGHT native Draw successfully, restored successfully, used distinct live RT0 surfaces, and reached fresh OpenXR projection. The former identical-L/R WVP fusion is replaced by one angular source ray projected separately through each eye's asymmetric OpenXR FOV. Physical draw cardinality is unchanged.
- Menu: physical 2496x2688 XR rendering stays untouched. The known-good full-vector VR UI rollback remains, while exact TITLE/MENU/SELECTOR partial or pivoted D3DX matrices are allowed to reach the already-guarded affine centering path instead of being returned early.
- SkyGlow: ordinary DX9Ex VR launch profiles now force factor 0. Explicit GPU-lab overrides remain available.
- F11 and the already-correct GOAL progress path are unchanged.

## +TIME source correction
Canonical original disassembly and r4dius/outrun2-decomp at e1e1c592b802a6f3f7020a676abd3ba1be479e62 show that the historical 0x9898E / 0x989AD / 0x98A10 / 0x98A36 / 0x98A89 group is inside GAD_PUB GOAL 0x498670:
- 0x9898E -> 0x429530 token 0x2C00B4
- 0x989AD -> 0x4973C0 result time
- 0x98A10 -> 0x4974E0 result score
- 0x98A36 -> 0x429530 token 0x2C00B5
- 0x98A89 -> 0x4973C0 result time

Therefore the existing StageExtensionTime name is historical/misattributed and is not evidence for the live in-race checkpoint +TIME popup. The runtime capture had zero StageExtension source hits. No speculative owner was added. Instead a bounded unique-signature trace records previously unowned GAME/GOAL queue nodes with kind, XST, texture, animation flags and queue epoch. The next popup capture can identify the real producer without altering rendering.

## GOAL disassembly completion
The original disassembly also has two B9200 result-text CALLs outside the prior 19-return allowlist:
- 0x98D37 -> 0x4B9200 (mission/result text)
- 0xBE009 -> 0x4B9200 (sector/banner helper)

The safe B9200 function-entry return-address allowlist is now 21 entries. The retired unsafe CALL+5 return-site hooks remain disabled. GOAL 0-99 progress ownership is unchanged.

RUNTIME_VALIDATION=UNTESTED_AFTER_PATCH.

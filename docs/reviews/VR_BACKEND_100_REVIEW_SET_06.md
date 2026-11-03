# VR Backend 100-Review Campaign — Set 06/10

Derived from Set 05. Set 06 reviews the stock-DXVK SAFE/provider boundary in ten distinct passes.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S06-R01 | Third-party/system D3D9 object mixing | PASS | Ex upgrade resolves Direct3DCreate9Ex from the same module that supplied Direct3DCreate9. A third-party provider without its own Ex export stays on its own classic path; it does not mix with system D3D9Ex. |
| S06-R02 | Provider-local D3D9Ex fallback | PASS | Provider-local Ex creation is attempted only when the same third-party module exports Direct3DCreate9Ex; failed Ex creation returns to that provider's classic CreateDevice path. |
| S06-R03 | Runtime provider location | PASS_WITH_SCOPE | Passive probe records system/non-system and exact game-directory locality. This is strong path evidence but not cryptographic module identity. |
| S06-R04 | Stock DXVK interop identity | PASS_WITH_SCOPE | QueryInterface for the stock ID3D9VkInteropDevice IID gives strong behavioral evidence that the loaded device is DXVK-compatible. A custom/forked provider could intentionally implement the same IID, so this alone does not prove official release bytes. |
| S06-R05 | SAFE vs multiview isolation | PASS | One-click target is dxvk-safe; selector removes multiviewpatcher.dll, package forbids experimental patcher payload, and the plan keeps historical multiview work blocked until visual parity. |
| S06-R06 | Vulkan implicit-layer isolation | PASS | DXVK launch disables implicit Vulkan layers, clears explicit instance layers, writes DXVK logs into the session directory, then restores the previous process environment in finally. |
| S06-R07 | Runtime version verdict | HIGH | analyze_dxvk_session marks STOCK_DXVK_PROVIDER_VERIFIED when provider locality+interop pass unless `version_match is False`. If no DXVK version line is detected, `version_match=None` and the same verified status is still emitted. Exact 3.1.1 runtime version is therefore not required for the “verified” verdict. |
| S06-R08 | One-shot device/provider census | MEDIUM | Provider census is connected to the existing one-shot game-device probe. Full device recreation after initial observation has no demonstrated provider/capability re-attestation. This carries Set 03 F12 forward. |
| S06-R09 | Acquisition/cache provenance | HIGH | Set 02 finding remains: cached d3d9.dll is accepted with PE32 validation only, and newly acquired bytes are hashed after download rather than checked against a pinned expected release hash/signature. |
| S06-R10 | Plan vs implementation atomicity statement | CLOSED | `VR_DXVK_R71_PLAN.md` now describes the actual bounded selector-owned snapshot/rollback/root-attestation transaction and explicitly says it is not a filesystem-wide atomic rename. The DXVK SAFE reactivation verifier binds that wording to the selector's Start/Restore/Remove transaction lifecycle and executable rollback/success-attestation behavior. |

## Findings carried forward

- **F24 HIGH DXVK:** provider analyzer can claim verified stock DXVK 3.1.1 without observing a runtime version line.
- **F25 CLOSED 2026-09-29:** `CONVERSION-DXVK-00033` replaces the ambiguous “atomically” wording with the actual bounded selector transaction: snapshot selector-owned mutable root files, restore/remove partial session on failure, persist `ROOT_PAYLOAD_ATTESTATION.json` before successful handoff, and clean transaction backup state with `Remove-BackendSwitchTransaction`. Attempt 2 identified the verifier's invented `Complete-BackendSwitchTransaction` marker; attempt 3 corrected it to the real lifecycle. Exact-SHA Backend Conversion Gate `36502258316`, Build `36502262877`, OpenXR architecture `36502262827`, and HUD Inspector `36502262924` all PASS on `8ffbe8d1ce14b978fc201c065872edf9705d5ee1`.
- F08/F09 remain open for provider provenance.
- F12 remains open for revalidation after full device recreation.
- Same-provider D3D9/D3D9Ex handling is accepted as a strong design and should be preserved.

## Set 07 direction derived from Set 06

Set 07 reviews **synchronization, frame transport and OpenXR host handoff**. Ten lenses: frame-ring slot state, producer fence, consumer ACK identity, generation changes, shared-handle ownership, hold-copy ordering, host heartbeat, stale-frame rejection, pose/frame identity, and shutdown/backpressure behavior. This directly follows the lifecycle/provider findings and avoids repeating provider checks.

No production source changes are made by this review commit.

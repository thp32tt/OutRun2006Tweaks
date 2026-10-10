# VR Backend 100-Review Campaign — Set 03/10

Derived from Set 02 execution-identity findings. Set 03 reviews device/reset/resource lifetime in ten distinct passes.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S03-R01 | D3D9Ex promotion transaction | PASS | R15 captures a fresh-device classic-state baseline and rejects/rolls back Ex promotion before game exposure if baseline capture or synchronous stereo-hook handoff fails. |
| S03-R02 | Reset pre-release ordering | PASS | R13 Reset common-pre releases mono/depth/stereo resources, clears shader/query identity and publishes stereo disabled before ResetEx ownership is exercised. |
| S03-R03 | Reset failure behavior | PASS | If compat ResetEx ownership is lost, the path returns failure rather than falling through to a competing Reset chain. If ResetEx itself fails, released resources remain released and stereo stays fail-closed. |
| S03-R04 | Post-Reset eligibility | PASS | R22 closes common eligibility and clears baseline/shadow tracking before delegating Reset; only a successful reset primes fresh viewport/scissor state, and stereo requires a new verified baseline. |
| S03-R05 | StateBlock lifetime/cache invalidation | PASS | Create/Begin/End StateBlock and StateBlock::Apply paths invalidate tracked render-state/shader/raster caches; unreliable Apply interception forces getter fallback instead of trusting stale shadow state. |
| S03-R06 | Host death and recovery | PASS_WITH_CAVEAT | R21 uses sequence-stable shared-state reads, heartbeat freshness, host PID and flags; stale host closes eligibility. A bounded transient grace intentionally keeps the last verified baseline for a brief invalid sample. |
| S03-R07 | Published DirectGPU slot lifetime | PASS | R13 prevents reuse of a published slot until producer GPU completion plus the dedicated consumer ACK identity permits reuse; unpublished copies do not require host ACK. |
| S03-R08 | NativeBackend resize failure semantics | MEDIUM_DX11_FUTURE | NativeBackend::resize releases current color SRV/RTV/texture before creating the replacement. If allocation fails, the object keeps its D3D11 device/context but loses the previous target. This is acceptable while dormant but needs an explicit fail-closed/recreate policy before native draw ownership. |
| S03-R09 | Native shared-eye generation/ACK ownership | BLOCKER_DX11_ACTIVATION | NativeSharedEyeRing creates shared eyes and EVENT queries, but the reviewed class itself has no transport generation, host-open confirmation, consumer ACK, slot publication state or reset-generation invalidation. Those semantics must be bound before the ring can become a live producer. |
| S03-R10 | DXVK device/provider lifecycle revalidation | MEDIUM_DXVK | The passive provider/device probe records the first observed game device/provider capability. Evidence reviewed here does not show a re-probe contract after full device recreation/provider lifecycle changes. Reset normally preserves the device, but full recreation needs explicit revalidation evidence. |

## Findings carried forward

- Set 02 F01/F03/F06 remain open and are not duplicated here.
- **F10 MEDIUM DX11 future:** resize can drop the last valid native target before replacement succeeds.
- **F11 BLOCKER DX11 activation:** shared-eye ring is resource-complete but not yet lifecycle-complete; publication generation and consumer ACK ownership must be explicit.
- **F12 MEDIUM DXVK:** provider/device identity census needs a defined revalidation point for full device recreation.
- Existing D3D9Ex Reset/eligibility/state-block path is a **strong reference implementation** for later DX11/DXVK lifecycle work.

## Set 04 direction derived from Set 03

Set 04 moves to **render semantic correctness** because lifecycle is strong on the reference path but backend activation can still corrupt HUD/world ownership. Ten lenses: disassembly address contract, SpriteNode queue boundaries, SCREEN_HUD producer map, WORLD_BILLBOARD producer map, c64-c67 WVP ownership, rank-marker callsites, projected effects/lens flare, menu arrows/goal text, classification fallback behavior, and contract drift between analyzer and runtime.

No production source changes are made by this review commit.

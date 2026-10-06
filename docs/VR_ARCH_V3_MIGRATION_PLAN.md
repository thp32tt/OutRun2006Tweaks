# VR Architecture v3 Migration Plan

Status: PLANNED / HMD-GATED
Integration branch: `vr-d3d9ex-focus`
Authority: `docs/VR_ARCHITECTURE.md` + this phase plan + `docs/VR_WORK_QUEUE.json`

## Purpose

Finish the architecture already scaffolded around `IGameAdapter`, `IStereoBackend`,
`IFrameProducer`, `IFrameConsumer`, `IVrRuntime`, and IPC v3 without mixing a
large architectural cutover into the current DX9Ex stabilization campaign.

This is not a rewrite of the verified OutRun behavior. The current DX9Ex runtime remains
the behavior oracle until an exact Quest 3 / VDXR baseline is accepted.

## Existing groundwork

The following already exists and must be reused rather than recreated:

- `src/vr/core/frame_types.hpp`
- `src/vr/core/transport.hpp` — `IFrameProducer` / `IFrameConsumer`
- `src/vr/game/game_adapter.hpp` — `IGameAdapter`
- `src/vr/d3d9/stereo_backend.hpp` — `IStereoBackend`
- `src/vr/ipc/protocol_v3.hpp` — HostState / ClientState / FrameRing / AckState
- `vrhost/src/runtime/vr_runtime.hpp` — `IVrRuntime`
- `vrhost/src/frame_source.hpp`
- v3 host/game shadow bridges and deterministic v2->v3 conversion smokes.

The presence of these files is scaffolding, not proof that the live runtime has completed
the v3 migration.

## Entry gate: ARCH-V3-GATE-001

Do not start live-authority migration while DX9Ex is still being stabilized.

The gate opens only when all of the following are true:

1. One exact DX9Ex CORRECTNESS build is accepted as the current Quest 3 / VDXR runtime baseline.
2. No open P0 crash/resource-lifetime/session/reset/recenter/direct-transport regression blocks that baseline.
3. Reset/ResetEx, recenter, game restart/host-survival, and normal shutdown have matching runtime evidence or are explicitly accepted as unchanged protected invariants.
4. Canonical DX9Ex Active Validation and Domain Isolation are green for the exact baseline SHA.
5. `RUNTIME_VALIDATION` is not promoted by CI alone; actual HMD evidence remains authoritative.

Until this gate opens:
- IPC v2 remains the live compatibility authority.
- IPC v3 may run only as deterministic test/shadow/equivalence infrastructure.
- Do not remove v2 paths, change camera mathematics, change draw classification semantics,
  or reopen DX11/DXVK as a substitute for completing the DX9Ex baseline.

## Migration sequence

### ARCH-V3-001 — live shadow equivalence

Extend the existing v3 shadow path so one real game/host session records bounded parity for:
- HostState pose/session/generation identity,
- ClientState game/presentation/interop identity,
- FrameRing frameId/renderPoseId/transport generation/slot/handles,
- AckState consumed frame/slot/probe identity.

v2 remains authoritative. Any mismatch is evidence; never coerce v3 to match by weakening
run/generation/PID validation.

Exit: deterministic smokes + exact-build shadow telemetry can prove equivalence or produce a
bounded mismatch reason without changing rendered behavior.

### ARCH-V3-002 — IGameAdapter live boundary

Route the verified OutRun camera/WVP and render-pose latch through `IGameAdapter`.
Preserve c64..c67 semantics, one render pose per presented game frame, and simulation/input/FFB
single execution. Keep a comparison path until exact equivalence is proven.

Exit: no upper transport/runtime layer needs OutRun camera globals directly.

### ARCH-V3-003 — IStereoBackend live boundary

Route draw classification and stereo GPU submission through `IStereoBackend` using the
owner APIs already extracted from R9/R22/R23/R29/R31/R32. Do not reintroduce direct private
state access or duplicate physical draw hooks.

Exit: stereo execution consumes adapter/frame contracts instead of transport/OpenXR internals.

### ARCH-V3-004 — IFrameProducer / IFrameConsumer live boundary

Put D3D9Ex shared transport behind the producer/consumer interfaces. Preserve all current
generation/PID/run identity, producer completion, ACK, slot reuse, and fail-closed rules.

Exit: the stereo backend no longer defines how a completed frame reaches the host.

### ARCH-V3-005 — IVrRuntime live boundary

Move OpenXR frame timing, session/reference-space lifecycle, view/pose ownership, swapchain
lifetime, and submission behind `IVrRuntime` without changing xrWaitFrame/xrBeginFrame/
xrEndFrame ordering or the current bounded resource-lifetime rules.

Exit: compositor/frame-source code does not own OpenXR lifecycle policy directly.

### ARCH-V3-006 — staged IPC v3 authority cutover

Cut over ownership domains one at a time, never all at once:
1. HostState,
2. ClientState,
3. FrameRing,
4. AckState.

Each cutover requires exact parity evidence and a rollback switch to the previous v2 authority.
A v3 field is not authoritative merely because the corresponding shared-memory object exists.

Exit: all four v3 domains are live-authoritative on one exact build, with v2 retained only as
an explicitly disabled rollback path.

### ARCH-V3-007 — v3 runtime acceptance

Quest 3 / VDXR validate the v3-primary exact build against the protected DX9Ex baseline:
world stereo, HUD/effects, recenter, reset/device loss, restart/host survival, DirectGPU,
frame pacing, and shutdown/recreate behavior.

Exit: matching USER_RUNTIME_VERIFIED evidence for the v3-primary build.

### ARCH-V3-008 — legacy retirement and downstream handoff

Only after ARCH-V3-007:
- delete v2 compatibility authority and semantic `reserved[]` transport use,
- remove dead migration shims and duplicate ownership paths,
- retain deterministic v3 ABI/equivalence/regression gates,
- freeze the v3 DX9Ex architecture as the reference contract for DX11 Native and DXVK ports.

DX11/DXVK implementation should consume the common adapter/stereo/runtime/transport boundaries
rather than copying the old R-series coupling.

## Controller transition rule

At every production cycle:

1. Complete any active immutable DX9Ex task first.
2. If ARCH-V3-GATE-001 is closed, continue only executable DX9Ex stabilization work.
3. If all remaining DX9Ex items are HMD-gated, do not manufacture filler changes; report the
   exact HMD gate.
4. When the user/runtime evidence opens ARCH-V3-GATE-001, D changes ARCH-V3-001 from BLOCKED to
   READY and executes the migration sequence in order.
5. Do not automatically reopen DX11/DXVK before ARCH-V3-007. After ARCH-V3-008, downstream
   porting may be reopened under the common architecture contract.

## Validation and rollback

Every ARCH-V3 step uses the normal C0..C6 record and exact-SHA CI evidence. Runtime-visible
claims remain HMD-gated. Each step must be independently revertible; do not combine interface
extraction, IPC authority cutover, and rendering-policy changes in one atomic task.

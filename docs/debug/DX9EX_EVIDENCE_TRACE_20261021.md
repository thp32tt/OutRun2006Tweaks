# DX9Ex EvidenceTrace debug profile — 2026-10-21

This branch is intentionally **not a performance build**. It exists to turn
review-only hypotheses into frame-linked runtime evidence.

## Branch

`vr-d3d9ex-evidence-debug`

The branch was forked from the current `vr-d3d9ex-focus` baseline. Normal
focus defaults are not changed.

## Default debug settings

The debug branch defaults these settings on:

```ini
[VR]
EvidenceTrace=true
EvidenceTraceMaxDrawsPerFrame=0
EvidenceTraceMatrices=true
EvidenceTraceFlushEveryPresent=true
Telemetry=true
```

`EvidenceTraceMaxDrawsPerFrame=0` means unlimited. Large log files and severe
stutter are expected.

Restart both the game and `outrun-vr-host.exe` before a capture. The host
inherits `OUTRUN_VR_EVIDENCE_TRACE=1` only when launched by the debug game
process.

## Evidence families

The game log records:

- `VR EVIDENCE DRAW BEGIN`: per-DP/DIP/DPUP/DIPUP ticket, Present epoch,
  semantic scope, stereo seed/failure state.
- `VR EVIDENCE DRAW STATE`: PRE/POST route, HRESULT, producer, queue node and
  epoch, viewport, scissor, RT0, depth, texture0, FVF, VS, PS, Z/blend/scissor
  state and DirectGPU backpressure.
- `VR EVIDENCE MATRIX`: full world/view/projection 4x4 matrices.
- `VR EVIDENCE PRESENT PRE/POST`: stereo eligibility, frame id, pose sequence,
  mono backup state, DirectGPU decision, HRESULT and failure reason.
- `VR EVIDENCE RESET PRE/POST`: backbuffer parameters, tracked depth and
  recovery state.
- `VR EVIDENCE D3DX`: Begin/Draw/Flush/End/LostDevice/ResetDevice with exact
  HUD batch owner, producer, queue node/epoch and generation.
- `VR EVIDENCE STATEBLOCK`: Create/Begin/End/Apply, hook target identity,
  reliability, coverage-loss and cached-raster validity.
- `VR EVIDENCE R14`: translated texture creation, shadow/direct-only tracking,
  Lock/Unlock, AddDirtyRect, mip generation, Release, replacement generation,
  budget and retirement state.
- `VR EVIDENCE R15`: Ex-install transaction, synchronous stereo handoff,
  exact-mip Unlock result, generated-mip invalidation and Reset health.
- `VR EVIDENCE COCKPIT`: eligibility reason, car matrix basis, seat anchor,
  fresh-vs-last-valid pose and resulting look vector.

The host additionally appends one line per `xrEndFrame` to:

`outrun-vr-evidence-host.log`

That line contains requested/final layer kind, candidate and actual frame ids,
pose sequence, rejection reason, capture/copy/render/wait/end timings, XR result,
both eye positions/orientations/FOVs and final sub-image rectangles.

Existing pipeline/pacing diagnostics remain independent and should be retained
when available.

## Recommended capture

A useful single run is:

1. Start clean game + host processes.
2. Enter a race and drive for 20-30 seconds.
3. Exercise straight acceleration, sharp steering, collision, sand/spray,
   checkpoint +TIME, pause/ESC, F11, and resume.
4. Finish or reach a GOAL/result screen.
5. If safe, trigger one resolution/device Reset path.
6. Exit normally.

For a cockpit issue also include a camera transition and at least one collision
or slope while DriverSeatView is enabled.

## Automated summary

```bash
python tools/analyze_vr_evidence_trace.py <game-log> outrun-vr-evidence-host.log
```

The analyzer summarizes draw routes/HRESULTs, Present failures, StateBlock
coverage, R14/R15 lifetime events, cockpit fallback reasons and host XR final
submission. It prints up to 200 suspicious records for direct review.

## Interpretation rule

EvidenceTrace does not itself change draw ownership, HUD classification,
resource lifetime policy, Reset recovery, OpenXR projection, culling, quality or
fallback behavior. It only adds observations and log flushing. A later source
patch should cite the exact EvidenceTrace event(s) that falsify or confirm an
automation review hypothesis.

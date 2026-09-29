# R81 frame-hitch trace — building streaming / sand-particle diagnosis

Date: 2026-09-30 KST  
Base: R76 validated SkyGlow restore `95ffeb2a8df11442d67489dd719313da334168e8`  
Candidate: `vr-d3d9ex-candidate/R81-FRAME-HITCH-TRACE-20260930`  
Current source SHA: `5ea084ba51ecc980f23ce5dd13e7dd4975eb33b8`  
RUNTIME_VALIDATION: `UNTESTED`

## User symptom

Intermittent frame drops appear more likely:
- when entering a section where many new buildings/objects become visible;
- when entering sand/beach terrain and visible sand/dust effects are emitted.

## Diagnostic design

R81 does not change render quality, pacing, culling, resource budgets, particle behavior, SkyGlow configuration or transport policy.

A frame-hitch event is detected only after 120 warm-up frames when:
- frame interval > max(18 ms, rolling EMA * 1.35), and
- frame interval > EMA + 2.5 ms.

Events are rate-limited to one per 500 ms. Each event emits:
- four frames before the hitch;
- the hitch frame;
- four frames after the hitch.

Main markers:
- `VR R81 FRAME HITCH:`
- `VR R81 FRAME PRE:`
- `VR R81 FRAME HIT:`
- `VR R81 FRAME POST:`

## Per-frame evidence

### Scene complexity

- logical top-level D3D9 draw calls;
- primitive count;
- indexed and UP draw count;
- SceneEffect / WorldParticle semantic draw counts.

These are counted before internal stereo replay so the metric measures game-scene workload rather than simply reporting the intentional L/R amplification.

### Particle load

The original game's NL particle system is sampled directly through `Game::nl_part_src`.

Across all 11 `TNLPartSource` entries the trace records:
- total `liveCount`;
- number of active particle sources;
- largest source liveCount.

This is the primary correlation signal for sand/dust/spray/smoke bursts.

### Asset/resource streaming

The D3D9Ex compatibility path records per-frame:
- translated MANAGED texture creations and estimated bytes;
- texture LockRect count;
- CPU-shadow texture uploads and bytes;
- upload CPU duration;
- vertex/index buffer creations and bytes;
- buffer locks and bytes;
- DISCARD / NOOVERWRITE dynamic-buffer lock counts.

In addition, the canonical `FileLoad_Ctrl` entry at RVA `0x4FBA0` is timed without changing its return value or scheduling. Per frame the trace reports:
- file-loader calls;
- calls that reported more pending work;
- total loader CPU time;
- maximum individual loader-call duration.

The timing wrapper reuses the already initialized QPC frequency instead of calling `QueryPerformanceFrequency` in the loader hot path.

### Postprocess / presentation

Each frame also records:
- restored R76 stereo SkyGlow CPU duration;
- lower D3D9Ex Present duration;
- stage/state/game tick.

Existing R23 host telemetry remains available in the same Analyze ZIP for capture/commit/render/endFrame and DirectGPU/fence/fallback evidence.

## Interpretation

**Building/object streaming candidate**
- high fileLoadUs/fileLoadMaxUs or busy loader count;
- simultaneous texture/VB/IB creation and upload spikes;
- draw/primitives increase after the streaming frame.

**Sand/dust particle candidate**
- large NL live-particle/source increase;
- dynamic VB/IB locks, especially DISCARD/NOOVERWRITE;
- SceneEffect/WorldParticle and primitive increases.

**SkyGlow candidate**
- skyGlowUs spikes while loading/particle/resource metrics stay flat.

**Present/transport candidate**
- presentUs spikes with otherwise flat game-side metrics;
- correlate with R23 host capture/commit/render/endFrame and DirectGPU wait/fence telemetry.

## Validation

Hosted DX9Ex validation run for final source:
`36647579231`

Status at document creation: pending/running. Build success is not a runtime/performance conclusion.

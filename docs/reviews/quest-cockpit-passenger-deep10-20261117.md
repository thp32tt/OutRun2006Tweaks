# QuestCockpitV2 passenger: ten independent native call-path debug passes

Date: 2026-11-17 KST. Parent baseline: `6888d425e432536f64151ee76a9cd6c911dcafc6`.
Source scope: native OutRun2006Tweaks test branch, original PC reference at
`r4dius/outrun2-decomp/src/platform/race_robots.cpp`, and the user's
`OutRun2_VR_ANALYZE_UNIFIED_LOCAL_CURRENT_FOCUS_CORRECTNESS_20261116T153439259Z-cb737397.zip`.
This is STATIC/CODE-TRACE evidence, **not Quest 3 visual confirmation**.

| Pass | Exact source path | Observed result | Action |
| --- | --- | --- | --- |
| 01 | PC original `440110` event table → `ROB01/ROB02` → `4879B0` | No synthetic event; original slot 363 owner, original callback pointer checked | Retain native provenance |
| 02 | `0x79FB48+0x16B` event flags → `ExactOriginalCockpitOccupant` | **BUG:** loose bit-1 check falsely admitted `0x03`; game event consumers use `(flags&3)==2` | Compare low two bits; regression for `0x03,0x0A,0x12` |
| 03 | player draw camera=0 vs 2/30 → `PassengerDrawTrace` | **BUG:** all non-1 cameras counted as camera 0; user log predominantly mode 2/30 | Split camera 0, camera 1 and other |
| 04 | camera 0 → original `4879B0` and `514E60` | Neither Follow nor Remove may alter camera 0 | Bypass gate stays mode-1 only |
| 05 | mode 1 / Follow / native car `0xC000` mask equals `0x4000` | Native `4879B0` must call `487880` once | No extra forced draw (avoid duplicates) |
| 06 | mode 1 / Follow / native car gate closed | Exact live slot 363 can invoke `487880`; without native render-frame/paired XR validity this was a risky extra draw | Require `NativeFrameTrace().Active()` and valid stereo pose before forcing |
| 07 | mode 1 / Remove → `ShouldSuppressOriginalPassenger` | Hide only exact live ROB02 during gameplay; driver/NPC unaffected | Retain original suppression path |
| 08 | `STATE_START` progress 65, `STATE_GAME`, GOAL, scene effect | GOAL/scene effects must use original renderer; event `0x0A/0x12` low-state remains valid | Keep race-only bounds |
| 09 | `487880` → `514E60` → pre-F0 snapshot → W×C → PMT `405015/40501D` | The correction and visibility RAII scopes are bounded; existing trace did not reveal whether final passenger model was displaced | Add opt-in original/corrected world-matrix translations |
| 10 | native detour install, recursion, F11 settings, CI and copy-run packaging | Exact original signatures + two exclusive F11 options preserved; no user-HMD display proof | Run exact-SHA isolated smoke and Win32/x64 package CI |

## Grounded user log reading (before the new gate hook)

- Camera mode 1 produced 45 `514E60` passenger callback entries in the first session and another 45 in the second, then no further mode-1 callback entries while `pFlag=0x02` remained live.
- `VR PASSENGER PMT NODE` showed both `nativeVisible=1` initially and `nativeVisible=0` later, with scoped override reported. These are **cull gate reports, not GPU draw confirmation**.
- `QuestCockpitV2OccupantLod0=false` and `QuestCockpitV2PassengerVisible=true` were active. The initial log **did not contain original car flags**. Thus the 4879B0 car-gate hypothesis cannot be declared proven from that session alone.
- Corrected `callbacksCam0` counts must not be compared numerically to old, mislabeled counters.
- The new 4879B0 native bypass's actual HMD results remain **UNTESTED** until a new user session.

## Audit definitions

The existing `tools/verify_quest_cockpit_passenger_static10.py` runs ten independent source-path checks;
the C++17 `tools/tests/quest_cockpit_v2_passenger_event_smoke.cpp` exhausts
64 Remove cases and 256 Follow gate states, plus native event flag edge cases.
Win32 and x64 GitHub Actions must pass on an exact SHA before packaging.
No v0.03 public release should be published from this experimental branch.

## Additional exact-original preflight and scene-mask recovery (2026-11-17)

- Canonical upstream v0.1 EXE SHA256 verified via exact PE32 mapping in a read-only GitHub Actions preflight.
- Exact original display routine `0x43FB40` starts `83 EC 10 83 3D 58 02 78 00 02 53 55 56 57` and takes cdecl mask, first, last. `0x4879B0` starts `A1 18 9D 79 00 ...` and has the stock car `0x4000` gate.
- Critically, the native `ROB01/362` and `ROB02/363` source event descriptors both use `display_scene=0x80`, not `0x40`. The decompiled PC frame renderer calls event_display with `1u<<layer` for layer 7, every game frame. Forcing another layer would be wrong and is prohibited.
- New guarded scene-pass wrapper first invokes original `43FB40`. It only recovers genuine existing `ROB02` after the exact `0x80` pass, only when driver has `0x80` but passenger's current scene mask does not, game/VR/stereo are active, and original real passenger wrapper was **not** reached in that same pass. Draws via the existing, native car-gate-aware passenger path. Does not write the original event table, flags, model or game state.
- If native `ROB02` field_C still has `0x80`, the new path **does not** produce a duplicate. The preexisting `4879B0` closed-car-gate bypass is the only recovery for that case. Original scene hook is signature verified and optional/fail-closed.
- No HMD test has yet shown actual visible passenger pixels; static/CI checks cannot prove visual correctness.

## Final risk closure: no alternate-layer duplication

- A missing `0x80` bit does not by itself mean the passenger has no other valid render scene. The scene recovery gate therefore requires `passengerScene==0` (completely disabled), rather than simply `(passengerScene&0x80)==0`; alternate `0x40` and `0x100` masks are negative regression cases.
- The pre/post original wrapper comparison uses a **thread-local** counter instead of the aggregate cross-thread diagnostic counter. This prevents eye/renderer thread traffic from suppressing a genuinely missing original event in the current scene pass.
- The regular original `0x4879B0` car display gate recovery still applies to any scene where the native event callback actually executes. No cross-layer re-render is attempted when event scenes differ from original `0x80`.

## Final test-debug lane 2026-11-18: missed native guest callback with intact 0x80 scene

- The last uploaded user runtime log predates all subsequent scene-hook builds. It shows a live original `ROB02` (`pFlag=0x02`, callback installed), but no further ROB02 native draw callbacks during a sustained camera-1 interval after the first ~45. That is evidence of a callback gap, not proof of its root cause or Quest 3 pixels.
- The earlier 0x80 scene fallback only admitted `passengerScene==0`. The original EXE descriptor for ROB02 is `0x80`, so a live event with unchanged original `0x80` and a missing callback would never be recovered.
- New narrowly scoped fallback admits the native `0x80` scene with `passengerScene==0x80` **only if** the exact native ROB01/362 `0x4879B0` wrapper was reached on the *same thread* in this same original `0x43FB40` display invocation but the original ROB02/363 wrapper was not. Thus a skipped passenger alone can be replayed exactly once while the original scene's state is live. The previous guestScene==0 recovery remains for a disabled native layer. Other masks, shared-layer masks, missing driver proof, zero XR pose, GOAL/menu, 3rd-person and Remove remain rejected.
- Added bounded `VR PASSENGER SCENE PASS` counters (driver/guest wrapper pair, source scene masks, current native epoch, stereo), useful if Quest3 still fails; does not claim GPU proof.
- The one-shot `RUN-QUEST-APK-PASSENGER-DIAG.cmd` keeps Follow Camera 0 forced on this diagnostic launch and collects logs automatically.
- Scope boundary: no new event, original game files untouched, no public v0.03, no live HMD result yet.

## 2026-11-19 user field-run follow-up: passenger pixel gap and low-speed sky double-image

- Uploaded session `20261118T165428567Z-5fc963ca`, exact source `5a56acf5c858b1e6c360bd6e56dbb8151c09e059`, original EXE SHA `68ceb386...`, correct DLL, game exit=0.
- While cockpit camera1 active the original ROB02 renderer was invoked **6413 times**, car-flag gate recovered **6368** genuine draws, original display-scene driver/guest 0x80, original guest wrapper reached=true, scene restores=0. Current root cause is NOT missing 4879B0/43FB40 callbacks.
- The model-space correction was applied on every observed ROB02 draw but yielded huge off-cockpit translation: native (3.620,-2.379,-254.995) -> W*C (2.931,-44.230,-250.776); later native (821.016,-7.100,-354.080) -> W*C (819.698,+49.760,-354.715). PMT forced-visible=1 LOD0=0 observed, not proof of GPU pixels. New guard rejects only ROB02 W*C displacements over 4 game units and forwards unmodified native work within existing scoped PMT visibility.
- Original `0x4521C0` naturally contains two sky layers. Programmable exact-sky drew using rotation-only head fallback; fixed-function rotationOnly could use the native Quest eye pair or fallback depending on pose readiness, so layers could disagree. Fixed rotation-only sky now ALWAYS uses the same head fallback as programmable sky; non-sky world native pair unchanged. No pixel-level low-speed cause is proven before HMD retest.
- PASSENGER-DIAG one-run enables bounded SKY probe, `VR SKY COHERENT BASIS`, `VR PASSENGER NATIVE MATRIX`, original PMT and game/host evidence. Release v0.03 remains rejected until live confirmation.


## 2026-11-19 pre-HMD deep re-debug of exact 9a0fbde3 session

Source reread: `20261118T171824402Z-38492e49`, build
`9a0fbde30697c8ab85a2ed50e742261a9242deb6`. This pass deliberately
reused the already-captured session; no new Quest 3 visual claim is made.

- **Sky window missed by bb62ff1b:** exact programmable 4521C0 sky is already
  active at 02:19:10.926 while the game camera is still mode 30/2. Mode 1 does
  not begin until 02:19:21.754. Therefore a camera==1-only sky workaround
  cannot cover the user's reported first-stage low-speed/start interval.
- **Layer/object transition evidence:** first-stage exact-sky draw counts move
  from about 268-272 per 90 Presents to 320 and then 360 while
  mixedEyes/modeSwitches/incomplete/rightFailed/poisoned remain zero. This
  supports an original two-layer/object transition issue more strongly than a
  stereo-eye failure. The safer render-only repair preserves original flags
  and alpha, but temporarily copies the destination layer rotation at
  work+0x50 to the fading old layer rotation at work+0xE0 only while both
  original layers are actually drawable. It applies in STATE_START/STATE_GAME,
  including camera 30/2, and restores all 64 bytes immediately after 4521C0.
- **Nested passenger visibility gap:** PMT diagnostics show nativeVisible=1 only
  for the first sampled nodes, then nativeVisible=0 from sample 180 onward.
  The old recursion bypass ran before ScopedOriginalOccupantLod0, so a nested
  genuine ROB02 could escape the forced visible scope. Nested ROB02 now enters
  the same scoped visible/LOD0 owner before forwarding the original renderer.
- **Dead threshold removed:** after the native passenger matrix lock, the old
  PassengerModelCorrectionNearNative 4-unit threshold and its tests were
  unreachable. They are removed; CI now checks that passenger 363 cannot
  re-enter the W*C threshold path.
- **Analyzer false positive fixed:** the session has gameExitCode=0 and a normal
  watchdog stop. CRASH_TEXT_PRESENT was caused solely by the informational
  phrase "VR P0 RESULT CRASH GUARD ... minidump EIPs". Crash detection now
  keys on non-zero game exit or concrete unhandled/access-violation/dump
  creation markers, not the generic word "crash".
- Other inspected transport evidence is healthy for the reported interval:
  shaderSkyNative=0/fallback-only is stable, mixedEyes=0, modeSwitches=0,
  incomplete=0, rightFailed=0, poisoned=0, and direct projection is active
  during gameplay. v3 poseLag/ackLag counters are shadow-parity diagnostics;
  the logged bridge explicitly states v2 remains render authority and
  poseMismatch=0.


## 2026-11-19 continued pre-HMD debug after 7f84cd4e

- The exact decomp implementation of PC `40A190 pc_matrix_load_rotation`
  consumes only the 3x3 orientation from each sky record's `+0x50` matrix.
  The previous render-only transition lock copied/restored all 16 floats.
  The lock is now narrowed to exactly nine orientation words; alpha, flags,
  translation-row words and all other sky work remain untouched.
- Added bounded `VR SKY TRANSITION PHASE` logging on phase changes
  (new-only / old-only / overlap) with flags, alpha and 3x3 rotation delta.
  This gives one-run proof of whether the reported blink coincides with the
  native 451E90 overlap rather than inferring it from aggregate draw counts.
- Re-read the 9a0fbde3 user session: sampled camera-1 ROB02 car-gate entries
  all had frameReady=true and stereoReady=true, but those logs are sampled
  and cannot prove every callback. Passenger visibility is therefore removed
  from NativeFrameTracker/XR readiness entirely: when an exact live ROB02
  callback already reaches 514E60 in active racing camera-1, its stock Windows
  matrix + scoped visible/LOD0 path executes before recursion or frame gates.
  This cannot create an extra passenger draw; the separate 4879B0 car-gate
  recovery still requires valid native frame + paired XR pose.
- Driver W*C remains strict: nested, frame-uncertain or pose-uncertain driver
  paths continue to fail closed to original rendering.


## 2026-11-19 camera-yaw diagnostic correction

- Exact decomp `race_camera_angles_484df0` computes yaw as
  `atan2(eye.x-target.x, eye.z-target.z)`. The existing probe used
  `target-eye`, which is exactly 180 degrees opposite. This explains the
  old log's impossible ~170-180 degree `maxVisualCarCameraGapDeg` values;
  it was a diagnostic bug, not a rendered-camera transform.
- Exact `pc_matrix_rotate_y` stores the car Z basis as
  `{sin(theta), *, cos(theta)}`, so `atan2(B0._31,B0._33)` is retained.
  New tested helpers encode both conventions and the probe also reports
  `maxCameraConventionGapDeg` against the game's native +0x12C yaw.
- No camera behavior was changed from this finding. The user's earlier
  “camera turns first” report must be re-evaluated with corrected diagnostics
  before altering the original mode-1 yaw producer.


## 2026-11-19 exact drawable sky overlap gate

The native 4521C0 display does not draw merely because a layer flag and alpha
are active: step0 also requires object 0 or 1 != 0xFFFFFFFF, and step1 requires
object 2 != 0xFFFFFFFF. race_sky_control_451b40 deliberately clears duplicate
old-layer IDs to None. The VR transition lock and phase diagnostics now mirror
those exact object-ID gates, preventing a non-drawing transition record from
being misclassified as a visible duplicate sky layer.


## 2026-11-19 GOAL matrix-scope audit

A further control-flow audit found a real scope mismatch. `IsPlayableCarGameplay`
includes `STATE_GOAL` for original game/render owners, but the cockpit matrix
experiments must not. The passenger Remove/Follow policy already used a
race-only boolean, yet a GOAL camera-1 callback could fall through and admit
driver/passenger W*C; the player callback could also stage F0=identity in GOAL.

A dedicated `IsCockpitRacePhase()` now admits only `STATE_GAME` or
`STATE_START` at progress 65. Exact ROB02 Follow remains handled before this
gate during the active racing phase; GOAL and results forward original ROB
rendering unchanged. Driver W*C and player F0 identity staging both explicitly
reject GOAL. Glass/original render ownership that intentionally uses the broader
gameplay helper is unchanged.


## 2026-11-19 GOAL FullCar/passenger-gate predicate cleanup

The same audit found `PlayerState` could still force the cockpit FullCar
candidate bits in GOAL because it used the GOAL-inclusive active helper.
That flag mutation is now race-only as well. The 4879B0 passenger car-gate
recovery and 43FB40 scene recovery had duplicated manual START/GAME predicates;
both now use the same `IsCockpitRacePhase()` helper. This removes three
independent definitions of the cockpit race boundary and prevents later
GOAL/START drift.


## 2026-11-19 non-exact programmable depth-off sky discriminator

The 9a0fbde3 field log consistently shows programmable depth-off world draws
exceeding exact 4521C0 sky draws by roughly one draw per Present (for example
358 vs 268, 362 vs 272). Aggregate counts alone cannot tell whether that extra
draw is a sun/lens world producer or another untagged sky-like layer.

SkyProbe now records a bounded `VR SKY NONEXACT DEPTH-OFF` receipt for only
those non-4521C0 programmable depth-off world draws: semantic scope, producer,
queue ownership, shader identity/serial, corrected world-view translation and
projection signature. The 90-Present summary also reports
`shaderNonSkyDepthOffDraws`. This is diagnostic-only and does not broaden or
change stereo routing. A next HMD log can therefore distinguish native two-sky
overlap from an independent depth-off producer without another instrumentation
build.


## 2026-11-19 exact 43FB40 scene owner replaces XR startup gate

A deeper call-order audit found one remaining passenger-startup gap. Original
PC `event_display_43fb40` synchronously invokes each live event callback for
the requested layer; canonical ROB01/ROB02 both use layer `0x80`. Therefore
when the hooked native `4879B0` ROB02 callback is reached inside that exact
43FB40 invocation, the game has already proven the frame-scene owner.

The previous car-gate recovery still additionally required
`NativeFrameTrace().Active()` and a published XR pose before forwarding the
existing live passenger to `487880`. During startup that can make the real
ROB02 callback return without ever reaching `514E60`, so the later native
matrix + visible/LOD0 lock cannot help.

A bounded thread-local top-of-stack RAII owner now tracks only the exact
43FB40 `0x80` pass whose range contains ROB02. A nested non-ROB scene does not
inherit the proof and stack overflow fails closed. The existing live-event,
callback pointer, native work pointer, mode-1, racing cockpit, Follow and
scene-effect checks remain. Frame/XR readiness is retained as diagnostics but
no longer grants or denies this already-native draw. The post-43FB40 scene
recovery uses the same exact owner. Camera 0, Remove, GOAL and non-ROB layers
remain original/fail-closed.

This specifically closes a path that could explain "passenger absent for the
first few seconds" even after the later 514E60 native-lock fix. HMD pixels are
still unverified.


## 2026-11-19 exact deferred 4521C0 sky provenance

The previous non-exact depth-off discriminator led to a stronger static
finding. Exact PC decomp shows `race_sky_object_452080` calls `4056D0`.
`4056D0` calls `405360`, which normally appends PMT node descriptors to
opaque queue `0x864EF8`; only when `8999B0` immediate mode is armed does
the queue flush before `4056D0` returns. Ordinary physical rendering occurs
later in `405890 -> 404700`.

Therefore a simple semantic scope around `4521C0` cannot cover every sky
GPU draw: the deferred queue outlives the scope and those nodes were necessarily
classified as generic world. This is a concrete lifetime bug independent of
the HMD hypothesis and is consistent with the prior session's roughly one
extra non-exact programmable depth-off world draw per Present.

The canonical replacement EXE SHA `68ceb386...` was re-read from the exact
successful build artifact. Original `4056D0` begins
`51 55 8B 6C 24 0C 83 FD FF 0F 84 3F 01 00 00 56 8B C5 C1 E8 10 8B F5 50`.
That signature is now checked before installing the source hook.

While and only while exact 4521C0 owns `WorldSky`, 4056D0 records newly
retained opaque entries by their real 0x3C descriptor identity, 64-byte matrix
hash, object id and original node pass mask. The already exact retail
405890->404700 call-edge wrapper then rejoins that identity and restores
`WorldSky` around the physical PMT draw. A mark retires after every pass
declared by the original node flags has been observed. Immediate 4056D0 draws
need no mark because they execute while the source scope is still live.

No queue descriptor, object flag, matrix or game state is modified. The repair
only preserves source provenance across the game's own deferred queue. Bounded
markers: `VR SKY OPAQUE QUEUE TAG` and `VR SKY OPAQUE QUEUE DRAW`.
Visual success remains UNTESTED pending Quest 3 confirmation.


### Fail-closed queue boundary follow-up

A post-commit self-audit caught one unsafe fallback in the first provenance
implementation: if the opaque queue header could not be read before 4056D0,
`beforeCount` remained zero, and a later successful read could have treated
older entries as newly appended. The source wrapper now carries an explicit
`queueSnapshotValid` bit and records deferred sky entries only when the exact
pre-call queue count was obtained. Unknown pre-state is never interpreted as
an empty queue.


### Optional 43FB40 hook fallback audit

The scene hook is deliberately optional because another plugin may already own
43FB40 or its signature may differ. A self-audit found that making
`ExactPassengerSceneOwnerActive()` the only car-gate owner would then silently
disable the previous 4879B0 recovery. The admission is now two-tiered:
when `PassengerSceneHook` exists, ONLY the exact top-of-stack 0x80 owner can
authorize recovery; when the hook itself is absent, the older
`NativeFrameTrace + paired XR pose` proof is allowed as the fallback owner.
Thus a weaker proof can never override an installed exact scene hook, while
optional-hook failure does not create a new passenger regression.


### Optional 4056D0 provenance hook audit

A further installation-order audit found the first provenance implementation
made the shared 4056D0 hook a prerequisite for the already-proven 4521C0 sky
owner. That would regress the core rotation-only/transition fixes whenever
another plugin owns 4056D0 or its bytes differ. The install order is now
strictly layered: exact 4521C0 must install first; 4056D0 signature/hook is
best-effort. If the optional leaf cannot be owned, only deferred provenance is
disabled and queued entries retain the pre-existing generic fallback. The
core sky owner is never rolled back by an optional shared-leaf conflict.


### Opaque provenance lifetime cleanup

Another self-audit covered queue entries whose expected PMT pass is globally
disabled and therefore never reaches the 404700 wrapper. Marks are now tied to
the current native opaque storage pointer. A storage replacement clears all
saved identities. Before each exact 4056D0 source call, every mark in the same
storage at a slot >= the exact pre-call queue count is removed because that
slot is inactive by definition. Active lower slots are preserved. This keeps
the provenance table bounded without guessing a frame lifetime or touching
game queue contents.

The earlier CI failure at this stage was also traced to a static verifier bug:
it parsed the first `bool apply()` in hooks_graphics.cpp rather than the
VrOriginalRaceSkyOwner class. The verifier is now class-scoped.


### Deferred-sky physical ownership diagnostics

The source/physical join now logs the render thread on both TAG and DRAW.
The DRAW receipt also records the actual `EffectiveScope()`, current producer
token and whether a SpriteNode queue is active after the WorldSky scope is
installed; TAG records the bounded active-mark count. These are diagnostic
only. They make the next HMD session sufficient to distinguish:
(1) source and physical draw on different renderer threads,
(2) a matched PMT entry whose WorldSky scope is overridden by a higher-priority
semantic, and (3) a successful exact WorldSky physical draw.


### Deferred physical semantic priority audit

A further renderer-level audit found that `EffectiveScope()` deliberately
prioritizes `CurrentQueueExactScope` (ScreenHud / WorldBillboard / projected
marker) over a plain `CurrentScope`. Therefore restoring deferred PMT sky
ownership with only `ScopedRenderSemantic(WorldSky)` could still be defeated
by stale selected SpriteNode provenance.

Matched 405890->404700 sky draws now use
`ScopedExactProducerSemantic(WorldSky, nullptr, true)`. This is the same
bounded pattern already used by exact nonqueued world producers: while
SpriteQueueDepth is zero it clears queue-exact scope, pending one-shot and
projected-marker state, installs WorldSky for exactly the physical PMT call,
then restores all prior semantic state. Unmatched PMT entries instantiate the
scope with None and remain unchanged. The existing DRAW diagnostic still
reports the resulting actual EffectiveScope so HMD evidence can catch any
unexpected higher-priority owner.


## 2026-11-19 transition-rotation hypothesis retired

The earlier render-only old/new 3x3 rotation lock was intentionally removed
before HMD testing. Exact race-area/sky decomp shows the two 0x90-byte records
carry previous-course and destination-course rotations during the native
451E90 cross-fade. Different layer rotations are therefore original game
state, not evidence of the reported VR bug by themselves.

A stronger and source-proven defect was found later: ordinary 4521C0
`4056D0` PMT nodes can outlive the WorldSky semantic through the opaque
queue and reach 405890->404700 as generic world. That route receives the full
world head/eye transform instead of the exact rotation-only sky path and
matches the field-log pattern of roughly one extra non-exact depth-off draw per
Present.

Accordingly the build now preserves the game's old/new rotation matrices and
alpha/flag/object transition byte-for-byte. `ScopedQuestSkyTransitionProbe`
is diagnostic only and reports `mutation=0 originalCrossfadePreserved=1`.
The active behavior fix is exact deferred WorldSky provenance, not a modified
course-sky crossfade.


### 4521C0 pending one-shot isolation

The same semantic-priority audit was extended to the source owner. The previous
4521C0 `ScopedExactProducerSemantic(WorldSky)` cleared selected queue scope
but left an unrelated `NextDrawScope` one-shot armed. A pending HUD/marker
token could therefore be consumed by an immediate sky GPU draw before the
deferred provenance logic is even involved.

The exact sky owner now uses
`ScopedExactProducerSemantic(WorldSky, nullptr, true)`, shielding and
restoring the pending one-shot for the complete original 4521C0 call.
`VR SKY SOURCE OWNER` reports the actual EffectiveScope, producer, queue
state, render thread and whether exact WorldSky ownership is visible at runtime.
This keeps both immediate and deferred sky submissions on source-proven
semantics without broad depth-state heuristics.


## 2026-11-19 release-launcher eye-resolution parity audit

The pre-HMD log proved the old release-parity launch drifted to VDXR's
2248x2432 recommendation when `AutoRenderResolution=true`. The diagnostic
runner was already corrected to the user-fixed Quest 3 eye target 2496x2688,
but the public `Start-OutRun.cmd` still carried the stale auto-resolution
flag. That would have reintroduced the same drift in a future v0.03 package.

The release launcher now explicitly uses `AutoRenderResolution=false`,
`RenderWidth=2496`, and `RenderHeight=2688`. Launcher verification,
isolated-core CI and the v0.03 packaging gate all reject a return to auto
resolution. This is release parity only; it does not claim HMD passenger/sky
validation.


## 2026-11-19 passenger pre-PMT gate and physical-entry proof

A further exact-original trace found one diagnostic blind spot between the
already-proven ROB02 callback and the PMT culling override. Canonical 514C30
reads `EvWorkRobot+4` before it queues any body mesh: bit 0x8000 must be set,
and a 0x08 state is rejected unless 0x04 is also set. The replacement EXE
prefix is now checked byte-for-byte in CI and the PASSENGER diagnostic reports
`workFlags` plus `robDisplayGateOpen`. This pass does **not** force those
native actor flags.

The original robot renderer then queues rigid/skinned meshes through 405360/
405580 and synchronously flushes through 405890->404700 before 514E60 returns.
While the exact ROB02 visibility scope is still active, the existing exact
404700 wrapper now emits bounded `VR PASSENGER PHYSICAL PMT` receipts
(object, pass, palette count, matrix/node/mesh pointers). This distinguishes
three cases in one HMD run: native actor gate rejected the draw, PMT traversal
failed to reach the physical entry, or physical PMT submission occurred and
the remaining problem lies below that boundary. No passenger coordinate,
event lifecycle, scene mask or render flag is mutated by this instrumentation.


### Per-43FB40 wrapper evidence instead of thread counters

The original post-pass recovery compared thread-local ROB01/ROB02 call counts
before and after 43FB40. That is normally sufficient, but it is not exact under
recursive/nested event-display calls: a nested scene could increment the same
thread counter and make the outer 0x80 pass look as if its own ROB02 wrapper
had already run.

Each `ScopedPassengerSceneOwner` stack frame now stores its own
`driverReached` and `guestReached` bits. The shared 4879B0 hook records the
resolved exact ROB01/ROB02 identity only into the current exact 0x80 frame.
Post-pass recovery consumes those frame-local bits; thread counters remain
telemetry only. A nested scene therefore cannot suppress or duplicate recovery
for its parent pass.


## 2026-11-19 v0.03 packaging version-gate audit

A static release-path audit found the public v0.03 packaging step still tested
`VR_RELEASE_VERSION.txt` against `v0.02` even though the version file is
already `OutRun 2006 VR v0.03 Beta`. On the dedicated release branch this
would make packaging fail deterministically before publication.

The packaging regex now requires `v0.03`. The launcher/release verifier also
checks both the version file and workflow text, and explicitly rejects the
stale `v0.02` predicate. This only repairs the dormant release gate; the
current debug branch still does not publish v0.03 and HMD passenger/sky
confirmation remains required first.

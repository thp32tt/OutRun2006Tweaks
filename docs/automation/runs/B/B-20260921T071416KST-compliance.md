# Role B handoff — DX9Ex same-SHA compliance companion

Base: `e5e35f483cf7f8d36f99a87807ba6cb9d4b7eccd`  
Candidate runtime/package workflow commit: `734d04f359d29ebce8951d93ed4f534a580b77b0`  
Branch: `vr-d3d9ex-candidate/DX9EX-COMPLIANCE-001-B-20260921T071416KST`

## Coherent change

The active DX9Ex workflow now emits a separate same-SHA GPL compliance ZIP while keeping the tester ZIP lean. The companion contains the GPL texts/notices, license scope, the adapted shader-fingerprint source, a full tracked corresponding-source archive, submodule identities, a manifest tied to the workflow SHA, and hashes. Runtime package publication depends on the compliance job, so a binary ZIP cannot be published by this workflow when its companion validation fails.

No game/host runtime source, profile, renderer behavior, refresh policy or backend payload changed.

## Evidence

- Workflow YAML parse and `git diff --check`: pass.
- Policy job: pass.
- Compliance assembly and validation job: pass.
- Win32 DX9Ex game, x64 D3D11 OpenXR host and compliance-gated runtime package jobs: pass.
- Actual artifact `10614663672` downloaded and opened.
- Outer artifact digest: `sha256:6e9b4d910d3d951fbdbeaa07fccd53a54f597b8dc5a8f6da6dd5adec4ebdcc05`.
- Runtime artifact `10615335705`: `sha256:f5639d8a53779c4a6886807ce81c4e6b9380d095bf18aab37a4f07c99bea13df`.
- Manifest and `SOURCE_SHA.txt`: exact candidate SHA `734d04f359d29ebce8951d93ed4f534a580b77b0`.
- `CORRESPONDING_SOURCE.zip` contains the root/host CMake inputs and exact `src/vr/d3d9/shader_fingerprint_gpl.hpp`.
- All 10 internal checksum entries matched; the source archive covered all 289 regular blobs from the candidate tree, with submodule gitlinks recorded separately.

Full run: https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/35541256724

## Independent next-finding review

`DX9EX-FINGERPRINT-001` remains separate. The only current game-side fingerprint call is below R33's successful HUD/fast-world early returns, while Ctrl+F9 capture is local to the host watchdog. R33 also lacks draw metadata parameters. The existing R33 Present hook is a viable once-per-frame place to edge-detect the same key in the game process without a protocol change or per-draw key polling. A separate candidate should then pass metadata from all four draw hooks, invalidate shader caches on successful Reset, buffer signatures during the bounded window, and flush outside draw dispatch. The current Role-A `--require-fixed` prototype also couples this finding with compliance, so C must validate this candidate's compliance subset independently.

## Next action

C validates the immutable SHA/artifact and the complete CI result. D alone may integrate these two paths. No HMD test is needed for this workflow-only change, and this build result makes no visual-runtime claim.

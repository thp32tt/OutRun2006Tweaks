# USER-DX9EX-LOG-FOLLOWTHROUGH-20261026 — uploaded log follow-through

- Source: connected GitHub `vr-d3d9ex-focus@92222985b9ebd81475bd52e59c923af241e6f59a`.
- Input: `DX9EX_LOG_R26_TIME_GOAL_RIVAL_TEST_20261026-000411(1).zip`; SHA256 `1e46f1d1a74c42a474f5aa76bed5f1226ece33d4766cccf290123f0144e18dce`; 8 files; game session 2026-10-26 00:04:11–00:07:59 KST; game PID 18932 / host PID 20460; variant R26_TIME_GOAL_RIVAL_TEST; gameBuild=unknown. No exact installed DLL/host SHA exists in this input, so it cannot prove current HEAD failure or success.
- User: unresolved rival/+TIME/final result/lens and newly small/doubled F11 after resolution changes. CHAT_DIRECT source repair authorized; automated DX9Ex remains REVIEW_ONLY.

## Corrected evidence

1. **CONFIRMED_RUNTIME:** 00:04:11 startup DESKTOP_AUTO=3440x1440 was superseded at 00:04:11.622 by XR source=2496x2688. At 00:04:49.858 DirectGPU stereo ring is 2496x2688. PC mirror is 1337x1440. Do not call desktop startup metadata the final VR render size.
2. **CONFIRMED_RUNTIME + STATIC:** 00:05:47.460 F11 actual raster uses game=2496x2688 but viewport=0,0,1337,1440 for LEFT and RIGHT. The R26 function reused Win32 client viewport for eye scissor and both draws. Thus at clip-space centre, raster centre is (668.5,720), not full-eye (1248,1344); apparent size is about 53.6% of the intended eye extent. This raster error does not by itself prove every binocular optical complaint.
3. Rival Calc/producer anchor valid; R51 projected counters remain zero and no RIVAL_MARKER_SPRANI fingerprint. This locates missing observed downstream evidence, **not proof of the particular queue-root hypothesis**. Current HEAD already has exact-rival root-chain exception + `VR RIVAL QUEUE PUBLICATION`, added after this session; no publication line exists in the input. Do not add another speculative queue exception.
4. The old warning `stock result graph preserved, stereo correction still pending` is followed immediately by `function-entry exact-parent ScreenHud wrapper installed`. Prior chat's inference that all B9200 correction was disabled was false. There are no B9200 ENTRY hit lines. Existing result-progress DIP has successful L/R HRESULT and restored projection. Post-session source also contains an unowned GOAL/FVF144 DPUP fallback, whose exact visual ownership remains unproven (review 01493); no claim it repairs the final graph.
5. +TIME hook-install line exists, but no StageExtensionTime/OUTRUN_STAGE_EXTENSION_TIME execution evidence. This does **not** establish the user never saw +TIME. Source entry/queue/D3DX/physical API chain remains the next discriminant; existing PR151 four-API implementation passes executable tests, HMD untested.
6. C993 eye draw success and old centre-eye fusion policy are observed; whole flare-family placement is not proven. Current source's two 570008 child suppression was added after input. Do not infer post-change optics from this ZIP.

## Material changes

- R26 external F11 keeps client orthographic source coordinates but maps output viewport and transformed scissor to full BackBufferDesc eye extent for BOTH draws; restores exact original viewport including MinZ/MaxZ on success and failures. Existing finite plane/FOV math and ordinary world/HUD routes unchanged.
- F11 software cursor uses VREnabled presentation, including menu, with same-frame visible predicate. Desktop/closed F11 remain excluded.
- Correct official DEBUG selector: allowed R26_FOCUS_OFFICIAL_DEBUG previously compared against impossible R26_FINAL_DEBUG, making GPU diagnostics always off.
- Official runner pins current XR/UI/AA/HUD test arguments and records actual DLL/host SHA256 and length in BINARY_IDENTITY.json. The input ZIP's missing exact build identity is not repeated by this runner.
- Replace misleading B9200 crash-guard warning with accurate distinction between disabled unsafe return-site hooks and separately installed entry wrapper.
- Fix inherited CI blocker `verify_vr_f11_toggle_frame.py` that demanded gameplay-only font gate after the prior XR/UI split promoted it to VR presentation. Historical failed Active run 40208658434, job 121214969986; no compile was reached.

## Validation

- Actual production R26 F11 preparation/draw functions compiled into recording D3D9 fake: FAIL before, PASS after. Cases: full-eye viewport/scissor for both targets; first-eye state failure permits zero-draw fallback; left draw failure; right viewport/draw failure without replay; exact viewport/projection/scissor/target restoration; native/non-stereo exclusion. GPU optics are not simulated as PASS.
- Official variant selector regression FAIL before (both TEST/DEBUG false), PASS after.
- Canonical Active static verifier list: 143/143 PASS in local environment before final docs/runner-only updates; relevant F11/+TIME/flare/source-split suites pass. Exact SHA Windows CI pending at material publication.
- RUNTIME_VALIDATION=UNTESTED. No current fixes promoted to HMD accepted baseline.

## Exact next evidence for unresolved items

Use packaged DEBUG with its included INI and launcher. Correlate RUN_CONFIG/SOURCE_SHA/BINARY_IDENTITY first; capture rival QUEUE PUBLICATION plus source/native/queue/physical probe stages, +TIME entry and four-API result eye traces, B9200 ENTRY vs final FVF144 DPUP, and whole flare-family events. Do not retry unchanged source/queue hypotheses from aggregate zeros. F11 full eyeViewport must read 2496x2688 (or current XR dimensions), while source viewport may remain client-sized.

## Input counters (bounded logs, not total event counts)

```json
{
  "VR RIVAL EXACT CALC EDGE:": 17,
  "VR RIVAL PHYSICAL PRODUCER:": 17,
  "RIVAL_MARKER_SPRANI": 0,
  "VR RIVAL QUEUE PUBLICATION:": 0,
  "VR P0 GOAL B9200: function-entry": 1,
  "VR P0 GOAL B9200 ENTRY:": 0,
  "OUTRUN_STAGE_EXTENSION_TIME": 0,
  "StageExtensionTime": 0,
  "VR R26 RESULT_HUD_EYES:": 17,
  "VR F11 SOURCE-ASPECT PROBE:": 12
}
```

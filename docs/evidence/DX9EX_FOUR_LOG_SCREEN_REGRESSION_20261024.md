# 2026-10-24 Quest 3 user four-run DX9Ex screen regression evidence

**Branch**: \`test/dx9ex-final-screen-20261024\` ONLY. \`vr-d3d9ex-focus\` not modified; DX9Ex automatic lane remains REVIEW_ONLY.
**Evidence**: user-uploaded ZIP logs, no game EXE or private user assets committed. Original test hashes pinned below. **Headset evidence**: user witnessed defects in Quest 3; debug traces have no per-GPU-draw binocular result-graph receipt. Do not confuse with successful optical HMD validation.

| Test ZIP | Input SHA-256 | Process exit | Key evidence |
|---|---|---|---|
| R26_REVIEW_COMBINED_225618 | \`2b698909c37ae3a9419dd890cd07cd37c134a90819e3940549fe84581e570b38\` | 0 | INI parse failed; 21 R28 low-FPS **warning samples**, median of only sampled warnings 78.5 ms; direct sharing disabled because non-D3D9Ex device; fallback SBS/Desktop Duplication |
| R26_REVIEW_COMBINED_225917 | \`788b109752668a9ab5b900434e156cb1762d37901c8f846782d284e566d01a2e\` | 0 | INI parse failed; 23 sampled R28 dips, median 76.1 ms; D3D9Ex sharing probe verified |
| R26_REVIEW_ALL_230322 | \`39fc95cd517b9dc9ad9214d1562328e512f64b350a873288ad7c0a8895f1764f\` | -1073741819 (\`0xC0000005\`) | INI parse failed; D3D9 Present failure \`hr=0x88760868\`; last R23 stereoAllowed=0, source baseline not established; NOT stable for promotion |
| R26_FINAL_TEST_230620 | \`b03b252161418dccd20f2c1a30b58169076d51c650254728655ca14a6cbfbb4c\` | 0 | INI parse failed; 36 sampled R28 dips, median of warning samples 77.5 ms; DX9Ex shared-resource probe verified; host process observed (not verified in HMD) |

## Confirmed regression root: shipped duplicate INI key

All four game logs print both:
- \`Settings::read - INI read failed! The file might not exist, or may have duplicate settings inside\`
- \`Settings::read - Launching game with default OR2006Tweaks INI settings!\`

ZIPs 225618/225917/230322 include the shipped \`OutRun2006Tweaks.ini\`: \`DriverSeatCarSpaceBasis = false\` appears **twice in the same [VR] section**, at lines 443 and 519. The repository test source contained that exact duplicate, and the FINAL_TEST used the same source INI (game log confirms parse failure; original ini not copied to its log ZIP).

The bad INI is a definite packaging/configuration defect, independent from any perceived graphics quality. **Do not over-attribute all rendering problems to INI**: even on defaults the game reports \`CullingUnionMarginDegrees=8\`, \`HudScale=0.55\` and \`FollowGameResolution=false\`. Those default printouts do NOT show that per-eye culling geometry, true 2D render source, or result producer is correct.

**Test-branch correction**:
- Remove only the earlier duplicate \`DriverSeatCarSpaceBasis\`; preserve the later documented native fallback.
- Set the *test-branch* \`DriverSeatView=false\` INI default; existing launcher also forces it at command line.
- Runtime launcher preflights duplicate keys in both base and user INIs; returns explicit failure instead of silently falling back to defaults.
- Runtime launcher checks post-launch \`INI read failed\`; reports \`INI_PARSE_FAILED\` rather than successfully proclaiming a VR test.
- CI regression \`tools/verify_vr_final_screen_ini.py\` protects against this failure.

## Still unresolved: must not advertise as fixed

1. **Result progress graph: different ownership during animation completion.** User reports elapsed time ascends inside HUD but the final static progress panel follows head and is doubled. Original owner \`0x004979E0\` is entered by exact parent E8 calls \`0x98924/0x992AC\`; inner fill \`0x97BE4/0x97DEC\` is a distinct draw source. \`src/hooks_uiscaling.cpp\` has exact result/progress producer scopes but late deferred sprite queue and D3DX \`Draw/Flush/End\` GPU submissions can outlive the parent. In supplied game logs no event-specific \`VR R26 RESULT_HUD_EYES\` receipt is visible for this graph. **Cannot conclude which draw failed** without paired stage-specific physical Draw+eye+pose log and native queue ownership. Do not globally classify all 2D result draws or restore old forbidden B9200 post-CALL+5 hooks (documented 0xC0000096 regression).
2. **Menu looks 4:3 but top/bottom blank portions are tall.** Logs report \`monitor=3440x1440 source=2496x2688 fittedWindow=1337x1440\`; the source is portrait eye extent, not independently verified landscape 4:3 original menu pixels. \`vrhost/src/main_r23.cpp\` has \`ProjectMenuCapturedAspect\` paths for cropped fragment vs full captured client. The exact observed letterbox cause still requires captured-pixel UV/source rectangle vs authored-original UI viewport evidence; do NOT guess by forcing global 4:3 scaling.
3. **2D follows in-game 2D resolution.** User reproduced dependence despite \`FollowGameResolution=false\` appearing in log; this is a **live source-policy/draw issue** that cannot be closed by toggling the INI without source-vs-XR capture evidence. Keep game/menu/UI source resolution distinct from OpenXR eye extent.
4. **Culling remains unexpectedly narrow.** Final log reports PMT \`mode=1 marginDeg=8.0\`; additional renderer log states wide FOV is \`isolated to the verified PMT result-gate call\`. The value 8 is present but does not prove all game-world culling is widened. No global culling hook change applied.
5. **FPS regression.** R28 warning samples have large frame spikes in all sessions; they are **only threshold-crossing warning events**, not representative full frame-time percentiles. COMBINED/ALL enable experimental reflection throttle/particle VB and profiler, while FINAL_TEST turns these off. Do not promote COMBINED/ALL to stable or infer comparative performance from unmatched scenes.
6. **1-5 rank markers were already corrected**; protect those and rival source XY binocular policy. Do not score them as a new fix.
7. **DriverSeatView=true cockpit severe oscillation** is user-observed and reproduced prior to this run; default disable avoids but does NOT repair cause.

### Next optical diagnostics (separate experiments, exact source SHA)

Collect stage result transitions around \`0x004979E0\` parent enters/leaves: producer token \`ResultProgress\`/time/GOAL glyph, original queue epoch+node, D3DX Begin/Draw/Flush/End, semantic owner on the **physical** native DIP/DP/UP, left/right HRESULT, pose and raw WVP, viewport, source/game extent and XR eye extent. Only make exact-source scoped optical edits once the failing final graph's draw is positively identified. Compare same scene/source against protected R26+HUD reference, never rebase R84. For menu, capture source actual pixel content bounds, crop plan and stereoscopic quad aspect on both eyes. For performance record frame-time p50/p95/p99, separate game render, presentation and XR host latency.

All corrections and new CI are confined to \`test/dx9ex-final-screen-20261024\`; no production promotion or exact headset PASS asserted.

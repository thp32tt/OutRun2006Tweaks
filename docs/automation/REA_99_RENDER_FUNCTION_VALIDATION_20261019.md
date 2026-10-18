# REA/Ghidra original OutRun rendering functions — completed 99/99

KST validation: 2026-10-19T01:22:32+09:00
Original game: `OR2006C2C.exe` SHA-256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.
Ghidra version: 12.1.4; REA version 6.5.0.

**Scope of evidence:** 2 prior individually verified functions + 97 new exact address/EXE SHA-matched REA JSON results. These were generated on the owner N100; not all were run again in this GitHub CI.
Original EXE, decompiled code, game assets and individual raw REA JSON remain N100-local. This table reports only VA, caller/callee counts, relationship coverage, and an independent source-role summary.

**Important limitations:** 99 targeted functions are not the entire 7,238-function native inventory. Static call-path coverage may be partial for function pointers/COM virtual calls. REA analyses do not prove DX9Ex LEFT/RIGHT GPU results or Quest3 optical output. All new HMD results remain `RUNTIME_VALIDATION=UNTESTED`.

## Targeted verified function matrix

| Original game VA | Source owner or evidence domain | REA result | Direct callees | Incoming refs | Coverage |
|---|---|---|---:|---:|---|
| `0x0042d710` | Priority queue consumer, type routing and sprite batch boundaries | PASS_EXACT_SHA | 7 | 2 | partial |
| `0x0042a800` | Mask/composite geometry and multiple native DrawPrimitiveUP paths | PASS_EXACT_SHA | 4 | 1 | partial |
| `0x00449050` | Normal main frame 9-priority render pass and queue consumer | PASS_EXACT_SHA | 19 | 6 | partial |
| `0x0040cbc0` | direct D3D9/D3DX renderer evidence | PASS_EXACT_SHA | 32 | 1 | partial |
| `0x004bad20` | direct D3D9/D3DX renderer evidence | PASS_EXACT_SHA | 16 | 4 | partial |
| `0x004b9d80` | rank_hud | PASS_EXACT_SHA | 9 | 2 | partial |
| `0x00429530` | SPRANI animation dispatch | PASS_EXACT_SHA | 2 | 145 | partial |
| `0x0042cfe0` | Glyph/sprite text queue record type=0, offsets +0x10 | PASS_EXACT_SHA | 2 | 9 | partial |
| `0x0042d0c0` | Animation quad queue record type=1, offsets +0x58 | PASS_EXACT_SHA | 2 | 6 | partial |
| `0x0042a3a0` | Native D3D9 DrawPrimitiveUP animation quad path | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x00429f60` | Original ID3DXSprite End per queue priority | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x0042a0a0` | ID3DXSprite Draw under D3DX2D transform; deferred GPU rasterization | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x0042c0f0` | Flagged direct glyph DrawPrimitiveUP path | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x0040c980` | direct D3D9/D3DX renderer evidence | PASS_EXACT_SHA | 1 | 4 | complete |
| `0x0040c9a0` | keyword_world_geometry | PASS_EXACT_SHA | 5 | 12 | complete |
| `0x00449940` | direct D3D9/D3DX renderer evidence | PASS_EXACT_SHA | 1 | 20 | partial |
| `0x004979e0` | Progression gate with side effects: draws percentage/glyph/sprites | PASS_EXACT_SHA | 21 | 2 | complete |
| `0x00498670` | Game-mode stage extension +TIME owner | PASS_PREVIOUS | — | — | prevalidated |
| `0x0042dd50` | Shared bounded SpriteNode allocator; 0x22F node cap | PASS_PREVIOUS | — | — | prevalidated |
| `0x00417b20` | Original Win32 message loop, Begin/EndScene/Present scheduling | PASS_EXACT_SHA | 27 | 1 | partial |
| `0x00421a90` | device_virtual_api | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x00401b80` | device_virtual_api | PASS_EXACT_SHA | 3 | 1 | partial |
| `0x004b9200` | Per-glyph emission | PASS_EXACT_SHA | 2 | 22 | complete |
| `0x0042c720` | Glyph atlas UV and quad construction | PASS_EXACT_SHA | 2 | 2 | complete |
| `0x00404700` | device_virtual_api | PASS_EXACT_SHA | 3 | 7 | partial |
| `0x00405cf0` | device_virtual_api | PASS_EXACT_SHA | 5 | 1 | partial |
| `0x00406a70` | device_virtual_api | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x00406af0` | device_virtual_api | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x004083f0` | device_virtual_api | PASS_EXACT_SHA | 3 | 1 | partial |
| `0x00408bb0` | device_virtual_api | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x00408c80` | device_virtual_api | PASS_EXACT_SHA | 7 | 2 | partial |
| `0x00408f90` | device_virtual_api | PASS_EXACT_SHA | 2 | 2 | partial |
| `0x0040aaf0` | device_virtual_api | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x0040ac60` | device_virtual_api | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x0040af80` | device_virtual_api | PASS_EXACT_SHA | 4 | 1 | partial |
| `0x0040bd10` | device_virtual_api | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x0040bf10` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 5 | 1 | partial |
| `0x0040c150` | device_virtual_api | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x0040c1b0` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 4 | 1 | partial |
| `0x0040c4a0` | device_virtual_api | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x0040c550` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 5 | 1 | partial |
| `0x0040c8d0` | device_virtual_api | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x0040e8f0` | device_virtual_api | PASS_EXACT_SHA | 8 | 1 | partial |
| `0x0040ec70` | device_virtual_api | PASS_EXACT_SHA | 0 | 2 | partial |
| `0x0040f650` | device_virtual_api | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x004103f0` | device_virtual_api | PASS_EXACT_SHA | 2 | 4 | partial |
| `0x00410680` | device_virtual_api | PASS_EXACT_SHA | 0 | 3 | partial |
| `0x004114e0` | device_virtual_api | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x004117d0` | device_virtual_api | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x00413fc0` | device_virtual_api | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x00414340` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 11 | 1 | partial |
| `0x00414790` | device_virtual_api | PASS_EXACT_SHA | 6 | 3 | partial |
| `0x00414c00` | keyword_texture_asset | PASS_EXACT_SHA | 1 | 2 | complete |
| `0x00414f00` | device_virtual_api | PASS_EXACT_SHA | 10 | 1 | partial |
| `0x004152e0` | device_virtual_api | PASS_EXACT_SHA | 4 | 1 | partial |
| `0x00415630` | device_virtual_api | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x00415ed0` | device_virtual_api | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x00416a40` | device_virtual_api | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x00418590` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x00418910` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x00418cf0` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x004197d0` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 4 | 1 | partial |
| `0x00419dc0` | device_virtual_api/keyword_world_geometry | PASS_EXACT_SHA | 4 | 1 | partial |
| `0x0041a6f0` | device_virtual_api | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x0041ae40` | device_virtual_api | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x0041b550` | device_virtual_api | PASS_EXACT_SHA | 0 | 3 | partial |
| `0x0041b7a0` | device_virtual_api | PASS_EXACT_SHA | 0 | 4 | partial |
| `0x004220f0` | device_virtual_api | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x00422550` | device_virtual_api | PASS_EXACT_SHA | 4 | 6 | partial |
| `0x00422740` | device_virtual_api | PASS_EXACT_SHA | 2 | 2 | partial |
| `0x004227c0` | device_virtual_api/keyword_texture_asset | PASS_EXACT_SHA | 1 | 2 | partial |
| `0x00422820` | device_virtual_api | PASS_EXACT_SHA | 3 | 1 | partial |
| `0x00422f20` | device_virtual_api | PASS_EXACT_SHA | 2 | 1 | partial |
| `0x00428170` | Active animation pool per-frame traversal | PASS_EXACT_SHA | 2 | 1 | complete |
| `0x00428a10` | Animation lookup and transform traversal | PASS_EXACT_SHA | 5 | 5 | complete |
| `0x00428bd0` | Animation sprite args, masks and quad queue producer | PASS_EXACT_SHA | 5 | 1 | complete |
| `0x00429220` | Animation pose/scale processing | PASS_EXACT_SHA | 6 | 1 | complete |
| `0x00429350` | Per-frame sprite construction | PASS_EXACT_SHA | 7 | 1 | complete |
| `0x00429460` | Animation child-frame recursion | PASS_EXACT_SHA | 2 | 3 | complete |
| `0x00429c60` | Original ID3DXSprite Begin per queue priority | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x0042a2b0` | Blend, render-state and texture-stage setup | PASS_EXACT_SHA | 0 | 4 | partial |
| `0x0042ccc0` | Glyph formatting dispatch | PASS_EXACT_SHA | 2 | 1 | complete |
| `0x0042cfa0` | Queue reset/counter clear | PASS_EXACT_SHA | 0 | 1 | complete |
| `0x0042dcc0` | Queue pool initialization | PASS_EXACT_SHA | 6 | 1 | complete |
| `0x0042e4f0` | device_virtual_api | PASS_EXACT_SHA | 1 | 1 | partial |
| `0x0042e8c0` | keyword_texture_asset | PASS_EXACT_SHA | 2 | 1 | complete |
| `0x00430120` | keyword_texture_asset | PASS_EXACT_SHA | 3 | 1 | complete |
| `0x004393f4` | keyword_texture_asset | PASS_EXACT_SHA | 0 | 5 | partial |
| `0x00439406` | keyword_texture_asset | PASS_EXACT_SHA | 0 | 1 | complete |
| `0x0043940c` | keyword_texture_asset | PASS_EXACT_SHA | 0 | 1 | complete |
| `0x00439412` | keyword_texture_asset | PASS_EXACT_SHA | 0 | 1 | complete |
| `0x00448e40` | device_virtual_api/frame_pipeline | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x00448ed0` | device_virtual_api | PASS_EXACT_SHA | 0 | 1 | partial |
| `0x00486450` | device_virtual_api | PASS_EXACT_SHA | 5 | 1 | partial |
| `0x004973c0` | Time-digit formatter | PASS_EXACT_SHA | 6 | 2 | complete |
| `0x004974e0` | Seven-digit formatter | PASS_EXACT_SHA | 7 | 1 | complete |
| `0x004c50a0` | Conditional additional queue consume at special mode | PASS_EXACT_SHA | 1 | 1 | complete |
| `0x005064e0` | device_virtual_api | PASS_EXACT_SHA | 13 | 1 | partial |
| `0x00507de0` | device_virtual_api | PASS_EXACT_SHA | 19 | 1 | partial |

## Using in actual R84 development

1. Fetch latest authenticated GitHub branch `vr-d3d9ex-focus`, active feature lease/TASK_ID and user-observed symptom. Never treat this document as a new production task or a reason to skip implementation.
2. For a candidate source VA, check N100 `rea-analysis/rendering_complete_20261018/REA_RENDER_BATCH_AUDITED.json`, and `rea_evidence/<VA-without-0x>.json` (prior 2 functions in `../rea_plus_time_20261018/`). Verify original EXE hash, direct callsite RVA vs callee VA, and Ghidra partial edges.
3. Map exact producer → original queue (`0x0042DD50` and `0x0042D710`) → R84 `hooks_textures.cpp`, `render_semantics.hpp`, R30/R33 four Draw routes → LEFT/RIGHT GPU results → host OpenXR presentation.
4. Prefer actual functional C++ fixes with positive/negative smoke and exact-SHA GitHub build gates over reviews/telemetry-only changes. D3DXSprite Draw/Flush/End may outlive a source callback; capture queue generation and batch ID.
5. Branches DX11 and frozen DXVK, R26_SAFE, FFB and user input are not changed by this REA analysis. Only source-backed optical owner attribution permits stereo correction. Quest3/HMD must be independently tested.

Local developer ZIP refreshed and integrity-checked at `/home/chatgpt-runner/rea-analysis/OUTRUN_REA_RENDERING_DEV_BUNDLE_20261018.zip`. Its 1,563,186 bytes contain independently authored development profiles, metadata and indices; raw original game binaries/textures/decompiler source are omitted.

GitHub documentation linking this data: `docs/automation/OUTRUN_REA_RENDERING_DEVELOPER_HANDOFF_20261018.md` and `docs/automation/OUTRUN_VR_REA_RESOURCE_EVIDENCE_20261018.md`.
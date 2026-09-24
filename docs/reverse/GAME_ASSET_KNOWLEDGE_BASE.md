# OutRun 2006 shared game-data reverse-engineering knowledge base

Baseline source branch: `vr-d3d9ex-focus`  
Analysis target source SHA: `8a312af992e4319aa5d101bfbfa97f271dd75203`  
Canonical executable SHA-256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`

This material is shared evidence for the VR, wheel/FFB and Korean-localization workstreams. It deliberately stores **metadata, hashes, offsets and structural findings only**; copyrighted game payloads are not committed.

## Evidence levels

- **CONFIRMED** — directly verified against the canonical EXE or supplied game bytes.
- **SOURCE-CONFIRMED** — directly verified in the current fork source.
- **STRONG INFERENCE** — multiple structural facts agree, but the runtime consumer has not yet been traced.
- **OPEN** — useful target that still needs static/runtime confirmation.

## Input identity

The supplied `OR2006C2C.exe` is byte-identical to the repository's canonical replacement EXE. The supplied v0.6.1 `dinput8.dll`/PDB is an old **release comparison baseline**, not current source truth. Current development/review must use the source SHA above (or a later explicitly recorded SHA).

## C2C SZ container

**CONFIRMED:** 1,160/1,160 supplied `.sz` files inflate successfully with ordinary zlib. Total sample size is 142,431,939 compressed bytes -> 465,581,958 inflated bytes (3.269x). This means the project can analyze shipped C2C assets directly without a mandatory offzip preprocessing stage.

`tools/reverse/analyze_game_data.py` implements bounded read-only SZ inflation and preserves the compressed path as provenance.

## Reusable asset families

The analyzer currently recognizes:

- XST sprite packages: 141 supplied files.
- Sprani top-level animation tables: 51 supplied files.
- `Scripts/bin` descriptor/fixup containers: 80 supplied files.
- `COLI0200` collision containers: 19 supplied files in the uploaded subset.
- canonical EXE localization/render anchors.
- `Text/*.bin` pointer/string containers when the actual files are available.

## Cross-project use

### VR

Use exact asset identity together with EXE producer/caller identity. Asset names alone must never promote a draw to `SCREEN_HUD`: world-projected rank markers also consume sprite assets. Lens flare is separately proven to use transformed 3D alpha objects from `obj_course_obj_common_pmt.sz`, not the canonical SpriteNode HUD queue.

### Wheel / FFB

The current wheel implementation already consumes original-game contact material state (`water_flag_24C[]`, `OnRoadPlace.loadColiType_0`) through the Xbox-derived `sub_1149C0`. Collision-file mapping should therefore be used to recover native material semantics rather than inventing additional stage-name heuristics.

### Korean localization

Language-specific XST families preserve identical system-memory geometry/metadata and change only video/texture payload. These are safe candidates for texture translation without re-authoring Sprani animation geometry. Dynamic strings are different: the canonical text loader is Unicode-shaped on disk but intentionally collapses each UTF-16LE code unit to its low byte, and the stock glyph renderer rejects bytes above `0x7F`. See `LOCALIZATION_MAP.md`.

## Generated versus curated material

- `reverse/game_assets/*.json` contains curated machine-readable facts that are small enough to review and reuse.
- `tools/reverse/analyze_game_data.py` can regenerate a detailed local map from a user-owned game directory.
- Full generated maps should remain build/research artifacts unless a particular snapshot is needed for a reproducible finding.

## Safety rule for semantic promotion

Do not convert numerical coincidence into meaning. A serialized dword that happens to look like an EXE VA is not a function pointer unless relocation/call evidence proves it. This rule is the reason the first TracksideCameras native-VA hypothesis was explicitly falsified and replaced with the relocation-container interpretation.

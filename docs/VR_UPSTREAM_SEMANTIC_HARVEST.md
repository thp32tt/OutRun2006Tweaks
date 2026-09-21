# VR Upstream Semantic Harvest

Source reviewed: `emoose/OutRun2006Tweaks@08e5efb4deea4066c440307ec009c868a30562d3`

The focus branch already contains that upstream commit in its ancestry. This
baseline therefore harvests game semantics and reverse-engineered file formats
rather than re-merging upstream code.

## Runtime policies now applied

- **Two-eye union culling FOV**: the render-phase culling projection is widened
  to the union of both OpenXR eye FOVs plus a configurable safety margin. The
  stock projection is saved and remains authoritative for actual eye rendering.
- **6DoF near plane**: while VR positional tracking is active, gameplay/goal
  cameras use `VR/NearPlane` instead of the 2D Z-precision policy's much larger
  near plane.
- **Reflection budget normalization**: cubemap-face work is time-normalized to
  the original 60 Hz budget so higher HMD refresh rates do not multiply
  reflection rendering cost.
- **Exact render semantics**: original game boundaries annotate SceneEffect and
  SkyGlow scopes. Known particle and attached-heart paths provide
  WORLD_PARTICLE / WORLD_BILLBOARD corroborating evidence. Existing verified
  WVP/depth/target gates remain authoritative and fail closed.

## Asset semantics

`tools/analyze_outrun_assets.py` turns the original file-format reverse
engineering into a machine-readable diagnostic inventory:

- XST: sprite/display tables, sprite IDs, UVs and source rectangles.
- XMT/PMT: object metadata, vertex-format class including XYZRHW, shader class,
  material flags and texture semantics (cubemap, sphere map, projection,
  Fresnel, Z bias, no-fog, double-sided).
- Runtime `OutRun2006Tweaks-xstmap.csv` records XST set index -> package name,
  linking HUD trace sprite IDs back to their source package.

The analyzer is diagnostic-only and never modifies game assets.

## Automated diagnostics

A `STAGE_DIAGNOSTIC` profile uses the original mod's `-SkipIntros`,
`-LevelSelect` and `-OuttaTime` switches to reduce manual traversal during
world/effect testing. Before launch, the runner best-effort inventories game
assets into the session as `VR_ASSET_SEMANTICS.json`.

Crash archives best-effort include current HUD/XST traces, session identity,
backend identity, build inputs and VR host/watchdog logs in addition to the
normal dump and game log.

## Scheduled-review rule

Treat these upstream-derived semantic boundaries as the preferred identity
source. D3D state/fingerprint heuristics remain fallback evidence for unmapped
draws. Do not promote a semantic hint past existing fail-closed stereo safety
gates without runtime evidence.

# DX9Ex final Quest recheck — 2026-10-31

Source baseline before diagnostic-only follow-up: `cb449af9c9505cf933cb029bdaae32e563d32b68`.

## Previous Quest runtime evidence

Input bundle: `DX9EX_LOG_R26_VISUAL_OWNER_REPAIR_AA2_TEST_20261031-000107.zip`.

- Lens: 104,142 `VR TRACE LENS PHYSICAL RESULT FULL` receipts; every receipt had `pairComplete=1`; no `pmtEntrySerial` occurred more than once.
- C993 problem route: `0x570002` reached the R7 lens fallback 6,939 times; `0x570006` reached it 8,933 times while only 210 physical receipts were owned by R30. This matches the isolated bright-lobe ghost/head-follow symptom rather than a duplicate same-eye PMT draw.
- Particle: 36 `VR TRACE WORLD PROJECTED SOURCE` records all reported `scope=WORLD_PARTICLE`, physical viewport `2496x2688`, but `gameCenter=1920,1080`. The PC `FixParticleRendering` hook halves generated screen coordinates, so the post-fix source centre must be `960,540`.
- Mirror: old runtime recorded `monitor=3440x1440 source=1920x1080 fittedWindow=2560x1440 origin=440,0`, proving the mirror fit used logical game dimensions rather than the physical XR/D3D9Ex backbuffer.
- Host: menu residency repeatedly submitted `menu-local-fixed-projection-fresh/cached`; therefore the OpenXR layer existed and was stable. The remaining upper-left menu symptom was source-raster placement inside the captured game client, not absence of the LOCAL-fixed layer.

## Current source cross-check

- Lens: the branch is a strict descendant of the exact projected-lens raw-WVP repair. `0x570002/0x570006` use same-source inline PMT/native-c64 ownership before R85 per-eye projection. Expected next-log marker: `VR LENS EXACT PROJECTED RAW WVP`.
- Particle: the world projected source centre is now `0.5 * Game::screen_resolution`, giving `960,540` for the observed `1920,1080` runtime values. Expected markers: `VR TRACE WORLD PROJECTED SOURCE` with `rawGameScreen=1920,1080 gameCenter=960,540`, followed by `VR TRACE WORLD PARTICLE XY FULL`.
- Menu/restart theater: title/menu/continue/gameover/game-exit/game-reset/try-again states crop the logical top-left `1920x1080` raster out of the portrait XR physical source before LOCAL-fixed optical placement. Ferrari selector/gameplay are excluded. Expected marker: `VR TRACE MENU LOGICAL CANVAS FULL ... applied=1 ... xrPhysical=2496x2688 ... logical=1920x1080`.
- Desktop exposure: mirror fitting now uses `D3DPresentParams.BackBufferWidth/Height`, while the black backdrop fills unused monitor area. Expected marker: `VR PC MIRROR ... logical=1920x1080 backbufferSource=2496x2688 ... backdrop=1`.
- Previously user-verified normal paths (ESC, rival marker, rank 1–5, +TIME, GOAL time) are intentionally untouched by these fixes.

## Runtime status

Static/source/CI verification can prove routing, bounds, ownership and compilation. Actual Quest optical placement remains `UNTESTED` until this final package is run in the HMD. No claim of runtime success is made before that test.

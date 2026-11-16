# Ferrari all-car source-ready private test package — 2026-11-16

## Confirmed package

- File: `OutRun2006_Ferrari_ALL_SOURCE_READY_2f69840b_20261116.zip`
- Bytes: **12,851,417**
- SHA-256: `a7bf99946d6d78e7ecddd5aa3917ea6c07585e324243f6602295be220576a7d9`
- Private Google Drive file ID: `1bFviotCUAswtk44HfKya8kl8qKtrvaoW`
- Drive raw readback: **12,851,417 bytes**, same SHA-256 after re-download.
- Runtime binary source: `2f69840b684a32f9656e2074689ca33789f8e8b3`
- Runtime verification commit: `259ba6b526a64fb13f3dad6f87c860f9da49861d`

## CI

- VR GitHub General Test Build run **43791201495**: SUCCESS. This built Win32 `dinput8.dll`, x64 `outrun-vr-host.exe`, packaged the exact copy-run payload, and exercised the user-facing launcher verification/fault-injection path.
- Build run **43791217292** at verification commit: SUCCESS.
- Ferrari External Installed-Only Floor Guard Unit CI run **43791217150**: SUCCESS.
- OutRun EXE HUD Inspector CI run **43791201562** for the exact runtime source: SUCCESS.
- QuestCockpitV2 Isolated Core Smoke run **43791201553** for the exact runtime source: SUCCESS.

## New runtime achievement

The installed-only external sidecar path is no longer hard-coded only to 288 GTO/F40 in addition to F50. It now supports the bounded retail player-car ID range **0..29**, with the exact retail ID mapping derived from `r4dius/outrun2-decomp@e1e1c592b802a6f3f7020a676abd3ba1be479e62`.

Existing package filenames stay backward compatible:
- F50: `F50_External_Test.ovc`
- 288 GTO IDs 7/22: `ExternalCars/288gto.ovc`
- F40 IDs 11/26: `ExternalCars/f40.ovc`
- Other IDs: `ExternalCars/car_id_XX.ovc`

All generic IDs remain fail-closed: fixed filename, expected player identity, gameplay/cockpit/stereo/device gates, parser/CRC/DDS/PBR/GPU checks, and stock-model fallback.

For new generic IDs, static floor lift uses requested lift 0 plus the validated model minimum local Y and 3.5 cm clearance, rather than inheriting F50's 0.22 m requested lift. Existing three converted cars retain their old configured lift behavior.

## Asset / rights boundary

New third-party car models bundled by this achievement: **0**.

Current other-game searches found useful exact or near-exact candidates (Dino, F355 Spider, 575 Superamerica, 250 GTO, 512 BB, F430, F430 Spider, Enzo), but rights/provenance are not adequate for bundled redistribution in this package. Recent 360 Spider and 550 Barchetta releases with attractive quality explicitly prohibit cross-game conversion in their published permissions, so they are excluded.

The audited GLB->OVRCABH3 converter and registry are carried on this branch under `tools/car_importer/ferrari16_hq_batch/`; use still requires an independently authorized source asset and explicit source SHA/transform metadata.

## Remaining physical QA

Quest 3 real-device rendering, texture appearance, dynamic road contact, and motion for newly supplied generic OVCs remain unverified until an authorized model is actually supplied and tested.

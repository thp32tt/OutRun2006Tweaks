# Ferrari external-model source-ready runtime — 2026-11-16

## Scope

This branch expands the already verified F50 / 288 GTO / F40 installed-only OVC path to every bounded retail player-car menu ID (0..29) while keeping the original game model as the fail-closed fallback.

It does **not** bundle newly found third-party car models. A public download page is not proof that cross-game conversion or redistribution is permitted. Models with explicit no-conversion / no-repack terms remain excluded.

## Retail car-ID mapping

The mapping is derived from the PC model/menu tables in
`r4dius/outrun2-decomp@e1e1c592b802a6f3f7020a676abd3ba1be479e62`,
`src/platform/frontend_vehicle_data.hpp`:
`VehicleMenuModels[car_id] -> VehicleResourcePaths[model]`.

| car_id | retail resource | source-ready target filename |
|---:|---|---|
| 0 | obj_plcar_dino_pmt.sz | ExternalCars/car_id_00.ovc |
| 1 | obj_plcar_dayts_pmt.sz | ExternalCars/car_id_01.ovc |
| 2 | obj_plcar_f50_pmt.sz | F50_External_Test.ovc when F50ExternalModel=ON; otherwise car_id_02.ovc |
| 3 | obj_plcar_360sp_pmt.sz | ExternalCars/car_id_03.ovc |
| 4 | obj_plcar_f355sp_pmt.sz | ExternalCars/car_id_04.ovc |
| 5 | obj_plcar_575sa_pmt.sz | ExternalCars/car_id_05.ovc |
| 6 | obj_plcar_testa_pmt.sz | ExternalCars/car_id_06.ovc |
| 7 | obj_plcar_gto_pmt.sz | ExternalCars/288gto.ovc (backward compatible) |
| 8 | obj_plcar_328gts_pmt.sz | ExternalCars/car_id_08.ovc |
| 9 | obj_plcar_250gto_pmt.sz | ExternalCars/car_id_09.ovc |
| 10 | obj_plcar_512bb_pmt.sz | ExternalCars/car_id_10.ovc |
| 11 | obj_plcar_f40_pmt.sz | ExternalCars/f40.ovc (backward compatible) |
| 12 | obj_plcar_550b_pmt.sz | ExternalCars/car_id_12.ovc |
| 13 | obj_plcar_f430_pmt.sz | ExternalCars/car_id_13.ovc |
| 14 | obj_plcar_fx_pmt.sz | ExternalCars/car_id_14.ovc |
| 15 | obj_plcar_dino_t_pmt.sz | ExternalCars/car_id_15.ovc |
| 16 | obj_plcar_dayts_t_pmt.sz | ExternalCars/car_id_16.ovc |
| 17 | obj_plcar_f50_t_pmt.sz | F50 slot when F50ExternalModel=ON; otherwise car_id_17.ovc |
| 18 | obj_plcar_360m_t_pmt.sz | ExternalCars/car_id_18.ovc |
| 19 | obj_plcar_f355sp_t_pmt.sz | ExternalCars/car_id_19.ovc |
| 20 | obj_plcar_575sa_t_pmt.sz | ExternalCars/car_id_20.ovc |
| 21 | obj_plcar_testa_t_pmt.sz | ExternalCars/car_id_21.ovc |
| 22 | obj_plcar_gto_t_pmt.sz | ExternalCars/288gto.ovc (backward compatible) |
| 23 | obj_plcar_328gts_t_pmt.sz | ExternalCars/car_id_23.ovc |
| 24 | obj_plcar_250gto_t_pmt.sz | ExternalCars/car_id_24.ovc |
| 25 | obj_plcar_512bb_t_pmt.sz | ExternalCars/car_id_25.ovc |
| 26 | obj_plcar_f40_t_pmt.sz | ExternalCars/f40.ovc (backward compatible) |
| 27 | obj_plcar_550b_t_pmt.sz | ExternalCars/car_id_27.ovc |
| 28 | obj_plcar_f430sp_t_pmt.sz | ExternalCars/car_id_28.ovc |
| 29 | obj_plcar_fx_t_pmt.sz | ExternalCars/car_id_29.ovc |

The special 288 GTO and F40 aliases preserve the previously shipped 3-car package. No arbitrary path is accepted and no directory scan is performed.

## Current other-game source search status

- **Dino 246 GTS:** exact Assetto Corsa GeroDa74 model remains downloadable. Rights for cross-game redistribution are not established.
- **365 GTS/4 Daytona:** exact downloadable candidates exist, but the common GTA V candidate traces through an older GTA-SA conversion and lacks dials; not accepted as an HQ replacement yet.
- **360 Spider:** recent high-quality GTA V release exists, but the corresponding Nexus release explicitly forbids conversion to other games. Excluded from bundled assets.
- **F355 Spider:** GTA V/FiveM Asyr0n build is live with HQ interior/dials; interior is adapted from Forza and redistribution/conversion rights are not established.
- **575 Superamerica:** Assetto Corsa 575 pack currently advertises a Superamerica version; exact included mesh and rights require local source inspection before conversion.
- **Testarossa Spider / 328 GTS:** no modern exact high-quality candidate with clear reusable rights verified in this pass.
- **250 GTO:** current GTA V candidate has a detailed cockpit, but credits include CSR2-derived material; blocked for bundled redistribution.
- **512 BB road car:** exact Assetto Corsa road-car candidate remains downloadable; rights still require author/source verification.
- **550 Barchetta:** recent high-quality GTA V release exists, but its Nexus permissions prohibit cross-game conversion. Excluded from bundled assets.
- **F430 coupe:** KingStriker Assetto Corsa F430 v1.0 remains available; cross-game redistribution rights not established.
- **F430 Spider:** large BeamNG candidate exists, but provenance/permission is unclear; the exact Nexus GTA V Enhanced model prohibits redistribution/conversion and is excluded.
- **Enzo:** GTA V KAFAROS model is still available but identifies the source as Forza Motorsport 4 AutoVista; no bundled redistribution without upstream permission.

## Runtime safety contract

- Only cockpit camera mode 1, owned player, active gameplay, valid stereo frame and ready D3D9 device can admit an external model.
- Fixed ID range is 0..29. Any other ID fails closed.
- Missing file, bad header/CRC, unsupported DDS, invalid PBR map, GPU budget failure or invalid static floor bounds => original game car.
- External pixels are never mixed with the full original car after a partial submission; failed resources are quarantined until reset.
- Original PMT/EXE data are not modified by the sidecar loader.
- Floor correction remains static local-space protection, not terrain raycast/suspension collision.

## Packaging rule

Existing verified F50 / F40 / 288 GTO OVCs may stay in the private test package. Every other slot is **source-ready only** until an exact model with acceptable rights is actually acquired, converted, reopened/validated, and runtime tested.

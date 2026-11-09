# SLOT C Ferrari F50 — driver_controls BLOCKED; next inner_door native upper rail v40 (2026-11-09 KST)

## Dispatch and evidence
- Strict queue: `active_by_slot.C=f50`, no changes to A, Dino, exterior, dashboard or steering.
- `driver_controls=BLOCKED_UNIDENTIFIED_NATIVE_STALK_PEDAL`: fresh official Blender inspection of all 42 existing PMT-derived objects did not positively identify an independently editable original F50 foot-pedal or lighting-stalk mesh. Original wheel `object21_group00_material000_a0` and `object21_group01_material002_a0` remain on P0 hold. No substitute synthesized and no driver_controls vertices moved.
- Per breadth-first fallback, advance immediately to `inner_door`. Existing native PMT ID **`object00_group01_material031_a0`**, 66 vertices / 40 faces, includes x-negative driver's inward door shoulder and x-positive opposing structure; isolated source render and private 1995 F50 cockpit comparison identify the driver-side upper-door region. No handle attribution asserted.

## Original, source-derived physical edit
- v39 input editable source: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CenterConsole_Shaft_v39.blend`, SHA256 `724df8bcd079299e8781726b25888243dbdcab7368d7d758f81ba8236666072f`.
- Original game read-only `obj_plcar_f50_pmt.sz` SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`; immutable original-import `F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Only **10 existing vertices** [26,27,30,31,32,33,34,36,37,62] of the **same original source mesh** reprofiled to shift the upper door inner shoulder inward, max actual displacement **26.495 mm**; 66 vertices/40 faces preserved, 41 other native meshes byte-fingerprint equivalent including wheel, dash, seats, shifter, all UV, materials and transforms. No new object/face/material.
- New independent editable Blender output N100 private `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_InnerDoor_UpperRail_v40.blend`, SHA256 **`03b96b1eb2293c151c60133919380055fa8393372b0acbf18045edf25faa949a`** (1,545,229 bytes).
- Private actual F50 photo `REF5_mecum_interior_01_f8afa7e2a.jpg`, SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`. Model same-camera Workbench BEFORE SHA256 `0872a6b7659dd48a0dc272750c5aa6cef4eaeab3fc838318f80cf4bb4d0e1e43`; AFTER `edd516bab87b3cd0f5431c3b6d0cfbfb9923d38d103c7c5bb4bb9faba828435e`. Actual image geometry differs; this is NOT calibrated original game driver-eye QA.
- Official Blender **4.5.15 LTS** executable verified against official Blender release SHA256 `0d2b8bb2efe97e6c8eb57de6b7322f8800e1984e3125b60decca5f6771e4773e`; independent fresh-process **v40 → v39 → v40 reopen PASS**; private `F50_InnerDoor_UpperRail_v40_Receipt.json` and `F50_InnerDoor_UpperRail_v40_IndependentReopen.json`.
- Reproducible script: `tools/car_modeling/slot_c/f50_inner_door_native_v40.py`, source SHA256 `9abb98fab0d074cbe9c5d61319431203934cc713963715551dab0b914fb97889`, source commit `7b7e9b514206b888a9728f54ab32ad5fba371fe5`.

## Coverage and exclusions
- `driver_controls=BLOCKED`, not PASS. `inner_door=COVERED_PARTIAL_QA` for upper rail only; original door handle not independently identified (`BLOCKED_UNIDENTIFIED_NATIVE_SOURCE`). Next `windshield_frame`; do not repeat driver_controls or door for cosmetics under this cycle.
- Vehicle stays `ACTIVE/PARTIAL_NEEDS_QA` with original 24-hour assignment starting 2026-11-08T04:35:52Z and independent final car QA gate. Exact in-game eye/photo seven views and native existing topology defects remain outstanding; **NOT whole-car QA PASS**.
- No new texture/PBR/normal, no PMT/OVC/OVC3 export, no gameplay integration, no external body or wheels, no Model2/Dino/DX11/DX9Ex/DXVK changes.

# OutRun 2006 Korean offline localization: actual DDS to PNG samples

Five PNG files in this folder were decoded from the **actual** SHA-verified
`OUTRUN_OFFLINE_KOREAN_TEST_ONLY_96e9372fb718.zip` DDS output, not created
with ImageGen or reconstructed illustrations.

Source: N100 `offline_overlap_v3_ink_test_only`
- Q032: rank header, 2048x1024
- Q051: HUD/menu atlas, 4096x2048
- Q054: mission prompt atlas, 4096x2048
- Q057: GOAL/game atlas, 4096x4096
- Q241: loading atlas, 1024x256

All 5 source DDS entries passed SHA-256 verification against their
independent QA receipts; decode was reoriented with the receipt's FLIPY
flag, and decoded RGBA pixels were confirmed pixel-exact against the
already verified `KOREAN_READABLE_TEST_ONLY.png`.

**TEST_ONLY / NOT_RUNTIME_APPROVED**: visible atlas defects, background
damage, English remnants, or text placement problems may still remain.
Do not interpret these PNGs as actual gameplay screenshots or a QA pass.

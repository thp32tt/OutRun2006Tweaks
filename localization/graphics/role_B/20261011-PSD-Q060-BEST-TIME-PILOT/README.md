# q060 external PSD source-layer test (unapproved)

q060 A064FDFC 4096x2048 RGBA32 DDS pilot only, not an official localized DDS.
External community Photoshop source Sonic-TV/OR2006Sprites A064FDFC_1024x512-v02.psd 44,136,566 bytes SHA256 cb03eb03f6515da0453c0e70d316a89955fa6da9690833354b869145c97a8024.
PSD has no isolated BEST TIME text layer, but BG Flat Colors / Flat Colors 0 supplies a source-matching native RGB clean background. Alpha=0 is preserved for the stripped English title.
Canonical English source DDS SHA256 6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc.
Previous official DDS SHA256 d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01.
New PSD-backed trial DDS SHA256 bab8dc25bc900d6806adf0462adb2046321353b78e29bdc82885ec9feef33255.
Edit only readable-original source bbox [2179,340,3028,474]. Korean trial text: 최고 주행 시간.
Static checks: unchanged DDS header, preserved 4096x2048 RGBA32 and one authored mip, RAW mirror-Y, exact persisted decode, change outside the English source bbox = 0 pixels.
First-look visual QA: original English shows stronger racing italic slant, condensed face and characteristic material; new Korean source-family fidelity remains UNQUALIFIED/REWORK. Source proof is scoped to tested ROI and current image comparison; not full-source approval.
C2 NOT_RUN; C3 NOT_RUN; IGR044 OPEN_USER_INGAME_FAIL; RUNTIME_VALIDATION=UNTESTED. Official hd_candidates and queue are unchanged.
Source PSD not bundled because it is an external community working asset and original-author provenance is unverified.

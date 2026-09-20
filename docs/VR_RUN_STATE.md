# VR Run State

Updated: 2026-09-20 21:56 KST

## Current checkpoint
- C0 RECOVER: complete
- C1 REVIEW: package contents reviewed
- C2 IMPLEMENT: complete
- C3 VALIDATE: static package-contract checks passed; CI observation remains
- C4 COMMIT: complete
- C5 PACKAGE: local slim repack produced from the frozen cbec700a30c4 artifact
- C6 STATE: complete

## Active development
- Branch: `vr-unified-backends`
- Packaging change commit: `840f52a9166d8a4921c4068f8c7ed3468d33e9e9`
- Existing frozen evening candidate: `cbec700a30c44a85292f396d37d6e24a77ed0b47` (do not mutate)

## Packaging decision
The tester ZIP is runtime/test-only. It keeps one visible selector entry point, `OutRunVR-Backend-Selector.cmd`, while retaining `Select-OutRunVRBackend.ps1` only as the internal backend-switch engine. The obsolete duplicate `Select-OutRunVRBackend.cmd` wrapper is excluded.

License/notice/corresponding-source material is excluded from the tester ZIP and generated as a separate compliance ZIP by CI. Runtime backends, INI files, selector engine/UI, launcher/log collector, build identity, source SHAs, checksums, and the test scenario remain in the tester ZIP.

## Local repack
- File: `OutRun2_VR_TEST_ONLY_cbec700a30c4.zip`
- SHA256: `5a920801db281bbdb7ac95bcd49b57166e92ecc725e0fa3b727f928b7f08022c`
- Visible selector CMD count: 1
- Removed from tester ZIP: `Select-OutRunVRBackend.cmd`, DXVK/RBR license text files
- Separate compliance file: `OutRun2_VR_COMPLIANCE_cbec700a30c4.zip`

## Resume cursor
Observe the unified workflow triggered by commit `840f52a...`; validate the resulting lean ZIP contents and the five-mode selector/log smoke test before replacing the frozen candidate.

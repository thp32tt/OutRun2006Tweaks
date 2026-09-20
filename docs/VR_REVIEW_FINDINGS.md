# VR Review Findings

## PKG-001 — Duplicate selector entry point
Status: FIXED

The unified test package exposed both `Select-OutRunVRBackend.cmd` and `OutRunVR-Backend-Selector.cmd`. The GUI selector is the intended tester entry point; the PowerShell backend engine remains internal. The duplicate CLI CMD wrapper is no longer copied to the tester ZIP.

## PKG-002 — Release/compliance files clutter tester ZIP
Status: FIXED IN WORKFLOW / CI VALIDATION PENDING

License/notice/corresponding-source files are no longer copied into the runtime tester ZIP. CI now creates a separate compliance ZIP so release obligations can be retained without mixing them into the user's test folder.

## PKG-003 — Lean package contract
Status: STATICALLY VALIDATED

The workflow now fails if the tester package contains the duplicate selector wrapper or license/notice/source-only files, and it verifies the required selector, launcher, collector, configuration, build identity, and test-scenario files.

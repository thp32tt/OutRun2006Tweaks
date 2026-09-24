# Domain Isolation Policy

Effective: 2026-09-24 KST

## Protected domains

- VR — branch vr-d3d9ex-focus — VR/OpenXR/DX9Ex/DXVK/DX12 runtime development.
- LOCALIZATION — branch korean-localization-prototype — Korean text/font/graphics localization.
- FFB — branch ffb-arcade-dd-research — standalone modern DD-wheel FFB development.

## Non-negotiable rule

VR ↔ LOCALIZATION ↔ FFB source merges are forbidden.

Do not merge one protected domain branch into another. Do not copy/cherry-pick executable/runtime source from another domain branch as a shortcut. Each product remains independently buildable and independently releasable.

Historical common ancestry is not approval for new cross-domain source changes.

## The only supported cross-domain transfer

Selected knowledge may be transferred through:

docs/shared-knowledge/

Examples:
- reverse-engineering facts and addresses;
- stage/material maps;
- file-format descriptions;
- object/stage identifiers;
- measurements and reproducible observations;
- provenance-only tables.

Allowed files are text/data only: Markdown, TXT, JSON/JSONL, CSV/TSV, YAML.

Do not place C/C++, Python, PowerShell, binaries, patches, DLLs, build scripts or generated executable payloads in the shared-knowledge area.

## Transfer procedure

1. Read source-domain evidence.
2. Copy only useful factual knowledge into docs/shared-knowledge/.
3. Record origin branch, exact origin SHA and source path.
4. Do not merge the origin branch.
5. Any target-domain implementation must be authored and reviewed in the target branch under that domain's own constraints.

A shared document is evidence, not source code.

## CI enforcement

.github/workflows/domain-isolation.yml runs tools/verify_domain_isolation.py.

The guard fails when:
- a protected branch has the wrong .project-domain marker;
- a merge commit brings a secondary parent from another marked domain;
- a commit changes a path owned by another domain;
- a shared-knowledge file is executable/source-like rather than text/data;
- a commit explicitly declares a different Domain trailer.

Recommended commit trailer for automated changes is one of:
Domain: VR
Domain: LOCALIZATION
Domain: FFB

## Existing-history note

The current korean-localization-prototype branch contains historical VR ancestry/files from before this policy. This policy does not rewrite that history. From the policy marker commit forward, foreign-domain-owned paths must not be modified there. A clean localization-baseline migration can be performed separately without merging VR source.

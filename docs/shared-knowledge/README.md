# Shared Knowledge Exchange

This directory is the only cross-domain exchange surface between VR, Korean localization and FFB.

It contains facts, maps and reverse-engineering evidence only. It must never become a shared source-code directory.

## Required provenance for every imported item

Record:
- originDomain: VR | LOCALIZATION | FFB
- originBranch
- originSha
- originPath
- importedKst
- factual claim/map being shared
- what is explicitly not being imported

## Good examples

- stage/material ID maps;
- executable RVA/function-role maps;
- object/file-format descriptions;
- measured force ranges or render-state observations;
- immutable hashes identifying analyzed game assets.

## Forbidden examples

- C/C++ source;
- Python/PowerShell/build scripts;
- patches or cherry-picked implementation diffs;
- DLL/EXE/binary payloads;
- entire branch merges.

Target-domain code must be implemented independently from shared facts.

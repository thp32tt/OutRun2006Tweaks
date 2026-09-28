# VR backend build checkpoint

Branch: `vr-dxvk-r71-disasm`

Purpose: one-click stock DXVK 3.1.1 SAFE/two-pass parity package checkpoint.

Required behavior:
- pinned x86 DXVK 3.1.1 provider is packaged under `backends/dxvk`;
- multiview/custom fork path remains disabled;
- runtime census reports whether the actually loaded d3d9 provider is game-local and exposes stock DXVK interop;
- one-click runtime preflight verifies provider version/hash before root payload mutation;
- DXVK provider logs are written into the exact test session directory.

Checkpoint refresh: stock DXVK 3.1.1 SAFE + game-local provider census + runtime preflight + session-local DXVK logs.


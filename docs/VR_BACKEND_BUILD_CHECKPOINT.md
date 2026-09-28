# VR backend build checkpoint

Branch: `vr-dx11-native-r71`

Purpose: one-click DX11-native observation package checkpoint.

Required behavior:
- native D3D11 draw ownership remains dormant;
- R72 passive census is enabled automatically by the branch target;
- adapter LUID, pipeline exactness, resource formats, vertex declarations and fixed-function texture-stage semantics are captured in one run;
- one-click runtime preflight must pass before root payload mutation;
- diagnostic ZIP retains target and preflight identities.

Checkpoint refresh: one-run census JSON extraction + resource/declaration/FFP census + runtime preflight.

Final one-run packaging checkpoint: machine-readable DX11 census summary wired into the diagnostic ZIP.

Identity-sealed checkpoint: BUILD_INPUTS, target metadata and backend SOURCE_SHA must agree before launch.

Code-freeze build checkpoint: one-click runtime, analyzers and syntax gates are wired; only build failures should change source after this point.

Final target-locked checkpoint: normal one-click execution cannot switch away from this branch target without explicit developer override.


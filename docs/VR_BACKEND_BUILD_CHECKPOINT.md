# VR backend build checkpoint

Branch: `vr-dx11-native-r71`

Purpose: one-click DX11-native observation package checkpoint.

Required behavior:
- native D3D11 draw ownership remains dormant;
- R72 passive census is enabled automatically by the branch target;
- adapter LUID, pipeline exactness, resource formats, vertex declarations and fixed-function texture-stage semantics are captured in one run;
- one-click runtime preflight must pass before root payload mutation;
- diagnostic ZIP retains target and preflight identities.

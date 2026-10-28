# Reflection 512 and R26 copy-cost review — 2026-10-28
TASK_ID=USER-DX9EX-REFLECTION512-20261028
Lane: DX9Ex C; attempt 1; target vr-d3d9ex-focus.
Base: fc08aa3d030a44680189d1dbafc7783bc4f43e70
User authorization: lower car reflection to 512; preserve MSAA and culling; review redundant code work.
Change: shipped INI and compiled missing-key default 1024 -> 512. Reflection frequency unchanged. This is a quality preference, not a proven runtime defect fix. Existing user INI/CLI overrides may retain 1024; restart is required.
Validation: exact replacement anchors, only reflection numeric default and its description changed in these two files. MSAA/culling lines unchanged. No build/package or performance claim; RUNTIME_VALIDATION=UNTESTED.
Reviewed active R26+HUD: src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp.
- R30CopyVertexShadow copies a proven locked shadow range into scratch.source. R30TransformXyzrhwVertices clones source separately for both eyes. Snapshot protects lifetime; removing it requires immutable ownership/generation or a safe combined transform, not unlocked raw pointers.
- The transform copies source again after failed full reprojection. R30TransformXyzrhwStereo then reruns BOTH eyes if leftFull != rightFull, even though one output already contains affine fallback. Candidate: redo only the successful-full eye as affine, retaining the already-computed fallback eye. Requires bitwise output/failure/reentrancy regression tests; not implemented here.
- Indexed VB path copies min..max referenced vertex span, zeros used mask and rebases indices. Sparse spans can copy unused vertices. Compact only if measured density justifies mapping overhead.
- R30ExecuteXyzrhwStereo switches RT/depth/viewport for each logical draw. Adjacent producer batching is a larger conditional optimization with blend/query/HRESULT boundaries; cannot just remove switches.
- Existing lazy buffer shadow capture and write-only reusable scratch already avoid some work; do not report as new changes.
Next: package the reflection preference after ordinary review; measure same scene. Prioritize targeted bilateral fallback recomputation regression before renderer change. This review does not authorize deleting native HUD/D3DX source boundaries or copying one eye to the other.

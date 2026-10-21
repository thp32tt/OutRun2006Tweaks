---
name: outrun-vr-openxr-debug
description: Investigate Quest 3 OpenXR frame and swapchain submission, double images, stereo and recenter problems.
---

# OpenXR / HMD
1. Distinguish D3D9 final Draw, x64 host shared texture transfer, xrAcquire/Wait/ReleaseSwapchainImage and xrEndFrame.
2. Verify physical host PID, session instance, exact ZIP SHA, eye target mapping, poseSequence and swapchain generation.
3. Require matching per-eye actual outcome and XR composition success; two Draw calls do not prove the headset shows a correct image.
4. Record aspect / FOV / source extent separately from eye swapchain extent.
5. Treat recenter, resize, reset and device loss as generation boundaries.
6. Headset-less preview is diagnostic; record RUNTIME_VALIDATION=UNTESTED until real Quest 3/VDXR verification.

# R51 Native View-2 Driver Seat Experiment

Base SHA: `17ad376bfdf7939f0851c0c629e4fa094a84f28a`

This branch intentionally removes the virtual fourth-view reconstruction.

- native raw mode 1 remains the camera owner
- no cam_mode rewriting
- no view-2 camera capture/reprojection through matrix_B0
- player car only is forced to full body render state 1
- driver/passenger robot rendering is not touched
- player car body scale is a draw-local visual transform only

Defaults from the final live tuning values in the prior runtime log:
Forward=-0.451, Right=-0.037, Up=0.015.

CarScale defaults to 1.12 and is live-adjustable in F11.

R51 validated render graph is preserved:
SAFE_DRAW_COMPARE=OFF, R26_HUD_COMPARE=ON.

# Daytona 365 GTS/4 — Blender v8.4 cockpit refinement

This is a **real editable Blender rework**, not an AI-generated finished image and not a game-runtime conversion.

## What changed from v7.3

- Rebuilt both driver/passenger cushion + backrest pairs into four cleaner continuous classic bucket-seat shells.
- Removed v7 floating/stacked seat details and reduced front bolster horns.
- Rebuilt the center tunnel and rear armrest as a lower/narrower shape.
- Removed redundant oversized H-gate geometry; kept the prior source-aligned chrome gate and shifter.
- Replaced the v8 floating lower-dash blocks with one narrow integrated lower dash lip.
- Lowered the pedals toward the footwell.
- Added four metal seat rails, seat mounts, and smaller lower seat skirts so the seats no longer appear unsupported.
- Added door top caps/lower pads and reduced their final thickness in v8.4.
- Replaced the thick steering-column cowl with a slimmer tapered black cowl plus short metal shaft, kept below the original gauge cluster.
- Added a small driver pedal firewall and removed the passenger-side block after render inspection.
- PBR target-image-derived leather/black/walnut BaseColor + tangent normal + ORM + local height/bump are retained.
- Added a subtle Blender procedural brushed-metal normal to the alloy shader.

## Private result

- N100: `/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender_v8/Daytona365_Cockpit_Blender_PBR_v8_4.blend`
- SHA-256: `97ff8618a4a16ac837e90e8aa9dd4434f41172c0b54c6894ec680aefa93025d4`
- Size: 6,181,557 bytes.
- Fresh official Blender 4.5.15 reopen PASS: 101 mesh objects / 31 curves, 4 seat shells, 4 seat rails, one integrated lower dash lip, slimmer steering column, normal/bump maps connected and brushed-metal micro-normal present.
- Actual Blender Cycles render: `docs/images/daytona365-v8/Daytona365_v8_4_ACTUAL_CYCLES_CABIN.png`.
- Actual original game PMT vs v8.4 same-camera comparison: `docs/images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_4_ACTUAL_RENDER_COMPARE.png`.
- Private ZIP: `Daytona365_BLENDER_REWORK_v8_4_PRIVATE.zip`, 8,168,685 bytes, ZIP verified; no PMT/DLL/EXE/OVC.

## Truth boundary

No game files, Dino files, PMT or runtime loader were modified. No Quest 3 play test and no game-ready model conversion were performed. v8.4 is still WIP: exact photorealistic target matching, high-detail dashboard underparts, more realistic seat side stitching, UV cleanup and dynamic in-game transform alignment remain incomplete.

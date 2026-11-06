# Dino 246 cockpit v4 — actual reference-detail 3D modeling

**Date:** 2026-11-06 KST  
**Scope:** original-sized Ferrari Dino 246 OutRun 2006 external cockpit prototype, R26 DX9Ex parser format. No changes to original game files or current working VR release.

## Outcome

### New real 3D geometry (not images)

- **Dashboard:** removed v3's simpler broad top and old gauge hood; rebuilt continuous, slightly asymmetric sculpted vinyl dashboard and new driver arched leather cowl, metal trim/lips and texture-ready surfaces.
- **Instruments:** retained three existing primary gauges and added **two separated auxiliary analog instruments** with independent cylindrical cans, glass-disc regions, chromed bezels, ticks, needles, pivots and mount screws.
- **Infotainment and vents:** replaced four generic toggle/switch and simple louver placeholders with **dual recessed 3D six-blade vents**, chromed framed vintage radio with a depth-separated display, tuner track, frequency ticks, 5 station buttons, 2 large rotary knobs and a lower chrome sill.
- **Cockpit signature:** 3D yellow wheel-hub badge and a separate 'Dino 246' glovebox logo material, with a modeled handle/trim. Logos are author-generated textures and are not guaranteed accurate vehicle badges.
- **Foot controls:** replaced three solid original low-detail pedal plates with **three metal pedal meshes having actual 3D through-holes**, 3x5 holes each (**45 total**). No solid faces cover the hole centers; original grip bars removed.
- **Seats:** retained v2 closed upholstered driver/passenger shells. Replaced decorative string/rib overlays with 8 real raised cushion ribs and 7 raised backrest ribs on EACH seat (30 sculpted padded bands total), seam beads and rounded leather contour edges.
- **Handbrake:** installed a modeled center brake lever, black leather grip, metallic pushbutton and gaiter.
- **Materials:** main diffuse maps 2K, with six **embedded GLB tangent-space normal textures** (derived procedurally from color texture, preview-only); 2D generated yellow wheel badge and script logo. **No image-generation/diffusion art was created or applied**. The R26 OVC diffuse path does not process GLB normal maps.

### Precise verified outputs

| version | author meshes | vertices | triangles | R26 OVC material batches |
| --- | ---: | ---: | ---: | ---: |
| v3 | 364 | 53,491 | 91,652 | 9 |
| v4 | 481 | 69,093 | 117,832 | 11 |

- GLB v4 **19,839,208 bytes** with 11 base/color textures + six linked PBR normal maps (**17** embedded images).
- OVC v4 **45,911,421 bytes** with 11 diffuse DDS textures, and grouped by material into **11** D3D9 draw groups. Geometry still has **117,832** triangles.
- Source-free Python geometric regression **PASS** for all 45 open pedal holes, 0 degenerate triangles, five total gauges, 30 physical rib surfaces, no duplicates of removed old dash/pedal/switch/wheel parts, intact v3 steering column clearance and source-coordinate bound check.
- Synthetic independent GLB normal-map link/byte-span regression **PASS**.
- Independent actual 2K glTF GLB binary/accessor/PNG validator **PASS** for 481 meshes/17 images.
- Actual native R26 C++ `OutRunVR::DinoSidecar::Parse` compiled and applied to final 1K-DDS v4 sidecar: **PASS groups=11 textures=11 vertices=69093 triangles=117832 HQ=1**.
- User-owned original PC `Cars/obj_plcar_dino_pmt.sz` SHA-256 `1f8dfcb7b875d46bd58f110518c1a8815355162d4412fa4a0d4e2e2301d86284` unchanged.

### Honest limitations and required next gates

This is an actual increment in **3D model detail**, not a rendered photoreal replacement or guaranteed photo parity. Shapes, surfaces and topology were authored from estimated Dino PMT-local anchors and visual reference, not directly reconstructed from photogrammetry. Original source's texture structure is not automatically upscaled into a high fidelity material map. The reference has finer chrome, leather pores, original instrument lettering, proportional body mounting and physically accurate cabin details that remain to be matched in a dedicated art/UV calibration pass.

**RUNTIME_VALIDATION=UNTESTED**: R26 original cockpit draw owner suppression/duplicate wheel removal has NOT been implemented here, Quest APK camera/window/frame parity is unverified, no Windows PC package or Quest 3 headset testing, no FPS performance proof. The v4 `.ovc` is only an experimental parser-compatible model file. **DO NOT overwrite a known-good v2/v3/FitV6 copy-run game installation with it.**

Source program is `tools/dino_cockpit_concept_detail_v4.py`; source-free geometry/pbr regression is `tools/tests/test_dino_cockpit_concept_detail_v4.py`.

Next target: align exterior cockpit frame and geometry to real original Dino photos/verified APK eye pose, convert reference photos into rights-cleared UV-located high-resolution albedo/normal/roughness maps (not naive flat projection), add exact R26 owner-based hide/restore, and produce opt-in paired rollback-safe Windows test build.

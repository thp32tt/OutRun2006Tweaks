# Dino 246 HD cockpit geometry v2 — verified source result

Date: 2026-11-06 KST
Branch: `feature/dino-hd-cockpit-geometry-v2-20261106`

## Implemented source

- `tools/dino_cockpit_hdgeometry_v2.py` extends the read-only native Dino original PMT coordinate/bounds contract from v1. It generates a sculpted separate cockpit, leaving the original PC game resource untouched.
- Replaces cylindrical three-spoke wheel struts with three stamped metal plates containing TWO actual open holes each (six in total). Fixes degenerate triangulation and retains a single steering shaft and rim.
- Thickens both passenger and driver cushions/backrests into closed shells. Adds lateral seat bolsters, stitch ribbons, rails, gauge ticks, needle pivot trim, door interior panels, manual window cranks and pulls, H-pattern shifter screws, and dashboard sewn trim.
- Editable GLB: 273 uniquely named meshes, 49,377 vertices, 85,448 nonzero-area triangles. Old v1: 123 meshes, 17,080 vertices and 28,320 triangles.
- Safe runtime OVC: merges 273 editable groups into **9 material batches** without losing vertices or triangles. This is a candidate optimization for per-eye R26 D3D9 Draw counts, *not a verified increase in frame rate*.
- High-resolution procedural diffuse maps GLB 2K and OVC 1K. `--texture-dir` optionally takes **all six** replacement PNG materials (leather, vinyl, plastic, metal, carpet, seat) for future AI-generated artwork. Synthetic/procedural textures are NOT represented as AI-generated images. The dial faces remain separately generated.
- The source PMT file `Cars/obj_plcar_dino_pmt.sz` was read only, SHA-256 `1f8dfcb7b875d46bd58f110518c1a8815355162d4412fa4a0d4e2e2301d86284`; no proprietary game mesh or texture is committed to public GitHub.

## Actual verification on local model assets

- `tools/tests/test_dino_cockpit_hdgeometry_v2.py`: PASS for source-free geometry invariants, six holes not textured illusions, three physical filled wheel regions, zero-area faces absent, source-bounded coordinates, nine material-batched R26 groups, and complete-or-reject external PNG map overrides.
- Independent glTF/GLB validator: PASS, 273 glTF nodes/meshes and 9 PNG material images, all accessor/buffer bounds valid.
- Native R26 C++ `OutRunVR::DinoSidecar::Parse` compiled and invoked against built OVC: PASS, 9 groups, 9 textures, 49,377 vertices, 85,448 triangles, high-quality v2 format.
- Source-original SHA verified unchanged after generation. **RUNTIME_VALIDATION=UNTESTED**; Quest 3 video, frame-time and compatibility are not proven.

## Outstanding before copy-run test package

1. Extract exact original PMT interior part ownership/draw path; hide only native overlapping wheel, seats and dashboard within the correct R26 VR car-draw scope. Preserve exterior car, glass, occupants and menus.
2. Align cockpit coordinates with native Quest APK per-car camera base and controller/head transforms, verify turning wheel and guest visibility; v2 remains a static coordinate estimate.
3. Add opt-in model source and correct SHA to an isolated paired R26 Windows x86 build, without overwriting v1/FitV6 or existing launch scripts. Validate crash on car selection and race→menu exit.
4. Replace six procedural materials with genuinely generated, vetted image textures and repack; `--texture-dir` is already available but has not been supplied such images.
5. HMD A/B per-eye geometry, alpha/glass, GPU 120 fps budget and screenshot verification.

**Safety:** exported OVC is a structurally valid **experimental input**, not a standalone runnable VR mod and must NOT be copied over the working game model.

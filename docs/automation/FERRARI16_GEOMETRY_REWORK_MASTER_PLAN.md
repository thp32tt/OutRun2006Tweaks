# OutRun 2006 Ferrari 16-entry geometry-only rework — automation SSOT
Updated: 2026-11-08 KST
Owner: AI 2 (ChatGPT2); only vehicle modeling automation slot A.
Repo/branch: `thp32tt/OutRun2006Tweaks@feature/ferrari16-geometry-rework-20261108`
Machine-readable queue: `docs/automation/FERRARI16_GEOMETRY_QUEUE.json`.
Previous Daytona v8 work: `docs/automation/DAYTONA365_CAR_MODEL_AUTODEV_MASTER_PLAN.md` (historical handoff only, material/texture steps superseded here).

## Operator override: narrow all automatic VR work to car geometry
1. Stop **Model2 VR C**, **DX11**, **DX9Ex**, **DXVK** and web-porting automatic dispatch in the Docker VR controller. Do NOT delete their work, score history, sessions or branches. Localization is a separate controller and must remain unchanged.
2. Only OutRun slot **A** sends new work, scoped to this plan and the queue above. Reuse the 60-minute chat rotation/checkpoint policy, and preserve existing worklogs and completed SHAs.
3. The only deliverable being improved now is **real 3D geometry**: silhouette, panel breakups, wheelbase/body proportion, hood, bumpers, vents, arches, wheels, cockpit dashboard/seat/steering/doors, face normals, smooth shading, manifold topology, origin and LOD. UV must not be destroyed, but **do not spend model hours on BaseColor, PBR, DDS, textures, ORM or normal map generation**. Existing textures may be retained only as inert baseline.
4. Never modify original commercial game assets, runtime VR branches, Model2VR-tools, localization or any secret; keep source game PMT/OVC, private .blend and game binaries out of the public repo. Publish independent Blender Python modeling scripts, geometric measurements, permitted references, output provenance and appropriately licensed previews.
5. No credit for repeated CI checks, previously completed car changes, or simply restarting a session.

## Sequential 24-hour model work policy
- Active vehicle starts as **365 GTS/4 Daytona** to preserve the actual v8.22-r2 cockpit handoff. All remaining entries are in the JSON queue order; two versions of F430 appear as separate candidate entries pending verification of the game's distinct original assets. The game's source asset index takes precedence over any public inventory listing.
- 24 hours means a **dedicated target calendar work window**, not one continuous GitHub VM or a claim of 24 CPU-hours. Track true elapsed interval from the first new material geometry commit and separately record actual tool/Blender job durations. Never fill a budget by sleeping or repeatedly auditing unchanged SHA.
- Work phases per vehicle: **0–4 h** provenance/source asset audit + multi-view genuine reference; **4–10 h** exterior silhouette/major body panel geometry; **10–16 h** cockpit, seats, wheel and dashboard geometry; **16–20 h** openings, badges, lamps, wheel arch/LOD/normal topology; **20–24 h** orthographic overlays, wireframes, rollback/regression and save–fresh-reopen. For Daytona continue from the verified v8 geometry rather than redoing completed interior steps.
- Save immutable versioned .blend checkpoints and commit independent editable geometry scripts with exact input/output SHA. Each useful work session checkpoints its changes. An hourly ChatGPT dispatch is for doing work, not a fixed promise of an entire car per hour.
- After 24 hours, **do not auto-advance** unless the current vehicle has a source-proven edit + independent Blender reopen + at least front, rear, sides, top and cockpit comparison + geometry QA PASS. If the original private scene or photo source is unavailable, mark `BLOCKED_INPUT`; after the budget with unresolved defects, mark `NEEDS_REWORK` and preserve ownership until approved. Only then activate the next queue row and record an audit trail with commit SHA.
- Source-of-truth acceptance: a created scene is not a finished car, a procedural test cube is not an OutRun model, GitHub CI pass is not game/Quest 3 validation, and archived/v8.22 geometry changes are not new work.

## Photography/reference accuracy
- First prefer licensed official Ferrari archives, marque restorers and established auction-house photo sets (e.g. RM Sotheby's and Joe Macari); explicitly identify **365 GTS/4 spider** versus 365 GTB/4 coupe/conversions, right/left-hand drive and trim years. For all cars collect at least front, rear, left/right side, 3/4 front/rear, top/roof, cabin and detail views.
- Log each reference URL, photographer/site, vehicle variant, year, lens/perspective risk, copyright/use permission and confidence. Use links and derived measurements; do not copy reference photos into the repository without permission.
- Side profile orthographic/aligned multi-view photos supply proportions; 3/4 marketing photos are corroboration, not proof of exact dimensions. Real game original mesh is the spatial base; photo-induced upgrades must preserve overall scale, wheel centers and cockpit mount for VR.
- No generative picture may count as photographic evidence or as an actual Blender render.

## GitHub-hosted Blender execution
- Use official **Blender 4.5.15 LTS** pinned (release 2026-10-22); `.github/workflows/ferrari-geometry-blender.yml` installs it on `ubuntu-24.04` or `windows-2025` and checks the downloaded release hash. Each GitHub hosted job gets a fresh VM and has a **6-hour maximum**; use short, version-pinned jobs plus persisted GitHub commits/artifacts and never describe it as one uninterrupted 24-hour VM.
- Workflow has an independent **toolchain smoke test** and a real-scene **geometry audit** mode. Smoke cannot count as progress on any Ferrari. Real-scene mode must fail closed when an authorized, source-backed .blend is missing. Blender needs to save and independently reopen candidate .blend, produce wireframe/photo overlays and write geometry counts/normal/nonmanifold reports. Do not claim such actual verification until the matching workflow run and artifacts are observed.
- A hosted VM does **not** automatically have the earlier private Daytona .blend on N100. Preferred path: stage a sanitized/editable, permission-cleared scene into controlled private asset storage / restricted Actions input, or keep a light one-time transfer from N100 only if actually authorized. Never make the public repository a distribution point for original game content.
- Workflow artifacts are **temporary checkpoints**, not a permanent source archive. Keep versioned scene and its SHA in the authorized private source store, and Git scripts/metadata in this branch.

## QA gate / reporting
Pass only when photo-view alignment and source mesh are both documented, Blender scene can be reopened, mesh components and face orientation are reasonable, object count/vertex/face counts are recorded, wheel/hub centers and cabin coordinate frame haven't drifted, and comparison renders exist for all required views. Check for accidental duplicates, nonmanifold/self-intersections and weighted normals, while protecting expected thin/open components.
Every work summary: `car_id`, 24h-window start/end KST, geometry edits + source SHA, Blender version and actual run ID, input/output .blend SHA and storage identity, 6 required photographic views/links, before/after actual geometry render, remaining discrepancies, `PASS|NEEDS_REWORK|BLOCKED_INPUT|UNTESTED` and next edit. Keep game integration and headset state explicitly UNTESTED unless separately verified.

## Controller deployment (separate from this production branch)
Controller source-of-truth branch: `chat-controller-downloads`; Portainer stack `tools/chat-controller/v0.4/docker-compose.portainer-vr.yml`. Rebuild/Pull and redeploy needed after controller change; source commit alone is not live deployment evidence. Leave the localization Portainer stack untouched.

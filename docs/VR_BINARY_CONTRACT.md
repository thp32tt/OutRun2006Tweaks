# VR Canonical EXE / Binary Contract

## Canonical executable

The reverse-engineering input is the replacement `OR2006C2C.EXE` distributed by
`emoose/OutRun2006Tweaks`. Upstream itself downloads the same v0.1 asset in its
build workflow.

The EXE is **not committed to this repository**. CI downloads it transiently,
checks the pinned SHA-256 and PE identity, then verifies reviewed RVA byte
signatures before source/build validation continues.

Manifest: `docs/VR_BINARY_CONTRACT.json`

Verifier: `tools/verify_vr_binary_contract.py`

## Why this is an integration gate

A source hook can compile while still crashing at runtime when any of these are
wrong:

- RVA/version identity;
- instruction boundary or overwritten-byte assumption;
- x86 calling convention/register/stack assumption;
- target lifetime/state assumption;
- a later source edit silently moving to a different executable anchor.

Therefore executable-RVA hooks are not accepted from source reasoning alone.
The original EXE contract is part of the evidence.

## Review roles

- **A**: compare lifecycle/control-flow hypotheses with the canonical
  disassembly before approving a new executable hook or reset/lifetime
  assumption.
- **B**: use canonical HUD/render call sites before adding screen/world
  heuristics.
- **C**: use canonical call-flow evidence when a synchronization/performance
  change depends on when the game issues a call.
- **D**: before integrating a candidate that adds or changes an executable-RVA
  hook, add/update a manifest contract, run strict verification, and revalidate
  matching entries in `docs/VR_CRASH_SIGNATURES.json`.

## Updating the manifest

Use discovery mode only to collect the identity/signature/disassembly of the
canonical EXE. Commit the resulting SHA-256, image base and byte signatures,
then switch CI back to strict mode. Discovery is never an integration pass.

For every new executable RVA hook, record:

1. stable contract ID;
2. canonical RVA;
3. exact byte signature length sufficient to detect drift;
4. short disassembly window;
5. source binding to the literal/address owner when practical;
6. purpose / recovered game semantics.

A changed EXE identity is a new binary baseline and requires deliberate review;
it must not be silently accepted.

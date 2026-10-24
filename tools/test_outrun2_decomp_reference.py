#!/usr/bin/env python3
"""Offline executable self-test for r4dius decomp provenance and OutRun VR hook isolation.
No network, game EXE, GPU or Quest3 required. Does not assert rendered parity.
"""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "src/vr/game/disasm_render_contract.hpp"
HOOK = ROOT / "src/hooks_uiscaling.cpp"
STAGE1 = ROOT / "src/vr/d3d11/live_game_stage1_factor.hpp"
REF = ROOT / "docs/references/outrun2_decomp_sources.json"
CALLS = (0xBB0FB,0xBB133,0xBB16C,0xBB1A5,0xBB21F,0xBB241,0xBB271,0xBB2BC,0xBB2D0)

class ReferenceContract(unittest.TestCase):
    def test_manifest_is_pinned_and_url_scoped(self):
        d = json.loads(REF.read_text(encoding="utf-8"))
        self.assertEqual(d["source_repo"], "r4dius/outrun2-decomp")
        self.assertRegex(d["source_commit"], r"^[0-9a-f]{40}$")
        self.assertGreaterEqual(len(d["sources"]), 15)
        for s in d["sources"]:
            self.assertRegex(s["blob_sha"], r"^[0-9a-f]{40}$")
            self.assertEqual(s["url"], "https://github.com/r4dius/outrun2-decomp/blob/main/"+s["path"])
        self.assertFalse(d["game_asset_code_imported"])
    def test_rank_hook_single_source_and_order(self):
        c = CONTRACT.read_text(encoding="utf-8")
        h = HOOK.read_text(encoding="utf-8")
        match = re.search(r"RankMarkerCallRvas\s*=\s*\{([^}]+)\}", c)
        self.assertIsNotNone(match)
        values = tuple(int(x,16) for x in re.findall(r"0x[0-9a-fA-F]+", match.group(1)))
        self.assertEqual(values, CALLS)
        self.assertNotIn("RankMarker_SpraniCalls[]",h)
        self.assertNotIn("RankMarker_ClipSpriteCalls[]",h)
        self.assertIn("RankMarkerCallRvas;",h)
        self.assertRegex(h,r"for \(std::size_t i = 0; i < 4; \+\+i\)[\s\S]{0,180}RankMarker_sprani")
        self.assertRegex(h,r"for \(std::size_t i = 4; i < rankCalls.size\(\); \+\+i\)[\s\S]{0,180}RankMarker_putClipSprite")
    def test_keep_proven_hmd_mode_and_world_fallback(self):
        hook = HOOK.read_text(encoding="utf-8")
        self.assertIn("return 6;",hook)
        self.assertIn("RenderScope::ProjectedWorldMarker2D;",hook)
        self.assertIn("RenderScope::WorldBillboard;",hook)
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("0x000BAD20u, 0x000BB320u, SpacePolicy::WorldBillboard",contract)
    def test_upstream_ffp_operator_ids_match_native_contract(self):
        c = STAGE1.read_text(encoding="utf-8")
        for name,n in {
            "kStage1Modulate":4, "kStage1AddSigned":8,
            "kStage1DotProduct3":24,"kStage1MultiplyAdd":25,"kStage1Lerp":26,
            "kStage1Texture":2,"kStage1Temp":5
        }.items():
            self.assertRegex(c, rf"constexpr std::uint32_t {name} = {n}u;")
        # GLSL's DP3 alpha special handling does not authorize D3D9 ALPHAOP DP3.
        self.assertIn("!stage1_dotproduct_color_operation(operation)",c)

if __name__=="__main__":
    unittest.main(verbosity=2)

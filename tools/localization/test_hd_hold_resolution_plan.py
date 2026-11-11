"""Regression for exact-source, fail-closed 640-HOLD resolution worklist."""
import unittest
from hd_hold_resolution_plan import action_for, make_worklist
from hd_source_protection_evidence import SCHEMA


def row(rid):
    return {
        "roi_id": rid, "source_dds_path": "textures/load/a.dds",
        "source_dds_sha256": "c" * 64, "_bbox": [0, 0, 100, 80],
        "english": "START", "korean": "시작",
    }


def mask(rid, owned, ambiguous, protected):
    return {
        "roi_id": rid, "source_dds_path": "textures/load/a.dds",
        "source_dds_sha256": "c" * 64, "bbox_xyxy": [0, 0, 100, 80],
        "exclusive_anchored_component_pixels": owned,
        "protected_or_unclaimed_pixels": protected,
        "ambiguous_component_pixels": ambiguous,
        "native_alpha_core_pixels": owned + protected,
        "mask_pngs": {"owned": "native_masks/" + rid + ".png"} if owned else {},
    }


class HoldResolutionWorklistTests(unittest.TestCase):
    def setUp(self):
        self.a = "Q043_0000000000000001"
        self.b = "Q205_0000000000000002"
        self.c = "Q044_0000000000000003"
        self.rows = [row(self.a), row(self.b), row(self.c)]
        self.held = {
            self.a: "ROI_OVERLAP_NEEDS_MANUAL_QA",
            self.b: "ROI_OVERLAP_NEEDS_MANUAL_QA",
            self.c: "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE",
        }
        self.evidence = {
            "schema": SCHEMA, "release_approved": False,
            "runtime_validation": "UNTESTED", "source_report_zip_sha256": "9" * 64,
            "tickets": [
                mask(self.a, 120, 0, 20),
                mask(self.b, 70, 20, 25),
            ],
        }

    def test_prioritizes_pixel_proven_child_but_never_auto_approves(self):
        plan = make_worklist(self.rows, self.held, set(), self.evidence, "9" * 64)
        self.assertEqual(plan["hold_total"], 3)
        self.assertEqual(plan["partial_mask_candidate_rows"], 2)
        lanes = {task["roi_id"]: task["repair_lane"] for task in plan["tasks"]}
        self.assertEqual(lanes[self.a], "SOURCE_CHILD_ALPHA_CLEAN_REVIEW")
        self.assertEqual(lanes[self.b], "MIXED_OWNER_ALPHA_SPLIT_REVIEW")
        self.assertEqual(lanes[self.c], "SOURCE_EDGE_REBIND")
        self.assertEqual(plan["tasks"][0]["roi_id"], self.a)
        self.assertTrue(all(t["auto_dds_approval"] is False for t in plan["tasks"]))
        self.assertEqual(plan["painted_test_only"], 0)

    def test_refuses_missing_alpha_proof_or_changed_source_sha(self):
        with self.assertRaisesRegex(ValueError, "OVERLAP_MASK_WORKLIST_NOT_COMPLETE"):
            make_worklist(self.rows, self.held, set(), {
                **self.evidence, "tickets": self.evidence["tickets"][:1]
            }, "9" * 64)
        broken = [*self.evidence["tickets"]]
        broken[0] = {**broken[0], "source_dds_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "MASK_CROSSWALK_SOURCE_PIN_CONFLICT"):
            make_worklist(self.rows, self.held, set(), {
                **self.evidence, "tickets": broken
            }, "9" * 64)
        with self.assertRaisesRegex(ValueError, "MASK_EVIDENCE_SOURCE_SHA_OR_QA_UNVERIFIED"):
            make_worklist(self.rows, self.held, set(), self.evidence, "x" * 64)

    def test_no_auto_pass_for_any_hold_lane(self):
        for reason in [
            "QA_BC3_MIP_CHAIN_REQUIRES_ORIGINAL_FORMAT_REBUILD",
            "QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT",
            "COARSE_ROI_CONTAINS_OTHER_TEXT_HOLD",
            "QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED",
        ]:
            lane, text = action_for(reason, None)
            self.assertTrue(lane)
            self.assertTrue(text)
        lane, _ = action_for("ROI_OVERLAP_NEEDS_MANUAL_QA",
                             mask(self.a, 0, 10, 30))
        self.assertEqual(lane, "AMBIGUOUS_SOURCE_COMPONENT_REVIEW")


if __name__ == "__main__":
    unittest.main()

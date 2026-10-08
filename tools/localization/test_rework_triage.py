"""Triage regression tests; these do NOT certify pixels or game rendering."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from rework_triage import repeated_defect, summarize


class TriageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        queue = self.repo / 'localization/graphics/asset_queue.csv'
        queue.parent.mkdir(parents=True)
        with queue.open('w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['index','path','action','artwork_status','transcription_status','notes'])
            writer.writerow([219,'test219.dds','localize_text','c280_rework_required_source_chrome_family_visual','',''])
            writer.writerow([172,'test172.dds','localize_text','b255_material_rework_hold_source_slant_anchor','',''])
            writer.writerow([154,'test154.dds','localize_text','c269_hold_strict_recheck_pixels_first','',''])
            writer.writerow([195,'test195.dds','localize_text','a152r_manual_visual_rework_self_qa_pass_pending_fresh_c','',''])
            writer.writerow([176,'test176.dds','localize_text','c279_hold_strict_recheck_native4of4_pass_evidence_gate_pending','',''])
            writer.writerow([220,'test220.dds','localize_text','c262_c3_strict_pass_pending_ingame','',''])
            writer.writerow([221,'test221.dds','localize_text','c213_preserve_original_policy_pass_no_candidate_required','',''])
        history = {'schema_version':1, 'cases':[{'queue_index':219,'rejections':[
            {'review_id':'C272','decision':'REWORK_REQUIRED','root_cause':'SOURCE_FAMILY_MISMATCH','evidence_ref':'resume_state.json'},
            {'review_id':'C280','decision':'REWORK_REQUIRED','root_cause':'SOURCE_FAMILY_MISMATCH','evidence_ref':'resume_state.json'}]}]}
        (self.repo/'localization/graphics/REWORK_ESCALATIONS.json').write_text(json.dumps(history))

    def test_repeat_forces_method_change(self):
        self.assertEqual('METHOD_CHANGE_REQUIRED',summarize(self.repo,219)['assets'][0]['next_action'])

    def test_hold_no_rerender(self):
        self.assertEqual('EVIDENCE_ONLY_HOLD',summarize(self.repo,154)['assets'][0]['next_action'])
        self.assertEqual('EVIDENCE_ONLY_HOLD',summarize(self.repo,176)['assets'][0]['next_action'])

    def test_self_qa_pass_beats_historical_rework(self):
        self.assertEqual('FRESH_C_REVIEW',summarize(self.repo,195)['assets'][0]['next_action'])

    def test_actual_rework_even_with_hold_word(self):
        self.assertEqual('MATERIAL_REWORK',summarize(self.repo,172)['assets'][0]['next_action'])

    def test_static_pass_not_runtime_completion(self):
        row = summarize(self.repo,220)['assets'][0]
        self.assertEqual('VALIDATION_ONLY',row['next_action'])
        self.assertEqual('UNTESTED',row['runtime_validation'])

    def test_preserve_before_historical_pass(self):
        self.assertEqual('PRESERVE_ORIGINAL',summarize(self.repo,221)['assets'][0]['next_action'])

    def test_one_review_does_not_trigger_breaker(self):
        case = {'rejections':[{'review_id':'C1','decision':'REWORK_REQUIRED','root_cause':'FONT','evidence_ref':'report'},
                              {'review_id':'C1','decision':'REWORK_REQUIRED','root_cause':'FONT','evidence_ref':'report'}]}
        self.assertEqual([],repeated_defect(case))

    def test_unrecognized_index_fails(self):
        with self.assertRaises(ValueError): summarize(self.repo,999)

    def test_summary_no_state_write(self):
        result = summarize(self.repo)
        self.assertEqual(7, len(result['assets']))
        self.assertEqual(7, sum(result['counts'].values()))


if __name__ == '__main__':
    unittest.main()

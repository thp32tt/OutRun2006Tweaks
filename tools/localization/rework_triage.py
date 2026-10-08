"""Read-only OutRun graphics rework triage; never infers visual PASS from notes.

Separates missing QA evidence from a material pixel defect and escalates repeated
independent rejects for the same verified root-cause family. No queue mutation.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

QUEUE = Path('localization/graphics/asset_queue.csv')
ESCALATIONS = Path('localization/graphics/REWORK_ESCALATIONS.json')


def load_rows(repo):
    with (Path(repo) / QUEUE).open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    # The queue contains occasional embedded UTF-8 BOMs in later index cells,
    # not just at the file start. Normalize before duplicate checks and int().
    for row in rows:
        row['index'] = row['index'].lstrip('\ufeff').strip()
    ids = [r['index'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate queue indexes')
    return rows


def load_escalations(repo):
    path = Path(repo) / ESCALATIONS
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError('Unknown rework escalation schema')
    return {str(item['queue_index']): item for item in data['cases']}


def repeated_defect(case):
    """Only distinct, explicitly cited C rejection reviews count."""
    by_cause = {}
    for failure in case.get('rejections', []):
        if failure.get('decision') != 'REWORK_REQUIRED':
            continue
        if not failure.get('review_id') or not failure.get('evidence_ref'):
            continue
        key = failure.get('root_cause')
        if not key:
            continue
        by_cause.setdefault(key, set()).add(failure['review_id'])
    return sorted(cause for cause, reviews in by_cause.items() if len(reviews) >= 2)


def triage(row, case=None):
    status = row['artwork_status'].lower()
    reason = 'No source-visible defect determined from queue state'
    # C/self-QA PASS must outrank historical "rework" text in the status label.
    if 'self_qa_pass' in status and ('pending_c' in status or 'pending_fresh_c' in status):
        action = 'FRESH_C_REVIEW'
        reason = 'Producer candidate exists; await independent pixels-first C'
    elif ('rework_required' in status or 'material_rework' in status
          or 'visual_fail' in status or 'manual_visual_rework' in status):
        action = 'MATERIAL_REWORK'
        reason = 'Current candidate has an actionable defect; rebuild the failed source-style stage'
    elif 'hold' in status:
        action = 'EVIDENCE_ONLY_HOLD'
        reason = 'Inspect unchanged DDS and complete exact-byte evidence; do not rerender without actual pixel defect'
    elif 'preserve_original' in status:
        action = 'PRESERVE_ORIGINAL'
        reason = 'Policy-preserved source; no localized DDS to generate'
    elif ('c3_strict_pass' in status or 'pixel_visual_policy_pass' in status
          or (status.startswith('c') and 'pass' in status)):
        action = 'VALIDATION_ONLY'
        reason = 'Historical static PASS is not final approval; verify current evidence / user / game'
    elif 'pending_c' in status or 'pending_fresh_c' in status:
        action = 'FRESH_C_REVIEW'
        reason = 'Independent C evidence pending; do not rerender accepted producer pixels'
    else:
        action = 'NORMAL_QUEUE_SELECTION'
    repeat = repeated_defect(case or {})
    if repeat and action == 'MATERIAL_REWORK':
        action = 'METHOD_CHANGE_REQUIRED'
        reason = ('Repeated independent C failures in one root-cause family: '
                  + ', '.join(repeat) + '. Stop same-method retries; make a new source-derived '
                  'family profile and construction method before creating another candidate.')
    return {'index': int(row['index']), 'path': row['path'],
            'current_status': row['artwork_status'], 'next_action': action,
            'repeated_root_causes': repeat, 'reason': reason,
            'runtime_validation': 'UNTESTED'}


def summarize(repo, index=None):
    rows = load_rows(repo)
    cases = load_escalations(repo)
    result = [triage(r, cases.get(r['index'])) for r in rows if r['action'] in
              {'localize_text', 'zoom_review', 'hangul_name_entry'}
              and (index is None or int(r['index']) == index)]
    if index is not None and not result:
        raise ValueError(f'Unrecognized queue index: {index}')
    return {'queue_file': str(QUEUE), 'escalation_file': str(ESCALATIONS),
            'counts': dict(Counter(x['next_action'] for x in result)), 'assets': result,
            'note': 'No state transition or game QA is inferred by this read-only diagnosis.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--index', type=int)
    parser.add_argument('--require-safe-rerender', action='store_true',
                        help='Exit 2 when rerender would duplicate QA work or requires a new method')
    args = parser.parse_args()
    if args.require_safe_rerender and args.index is None:
        parser.error('--require-safe-rerender requires --index')
    report = summarize(args.repo, args.index)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.require_safe_rerender and any(x['next_action'] not in
                                         {'MATERIAL_REWORK', 'NORMAL_QUEUE_SELECTION'}
                                         for x in report['assets']):
        raise SystemExit(2)


if __name__ == '__main__':
    main()

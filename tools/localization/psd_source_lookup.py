#!/usr/bin/env python3
"""Find SHA-pinned upstream PSD workbases actually mirrored inside this repository.

Only copied and Git-hash-verified PSDs are eligible; catalog entries by themselves
are NOT available files or independently approved CLEAN plates.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def lookup(repo: Path, index: int) -> dict:
    catalog_path = repo / 'localization/graphics/plate_library/PSD_IMPORT_CATALOG.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    entries = [v for v in catalog['entries'] if index in v['queue_indices']]
    result = []
    for item in entries:
        rel = Path(item['local_path'])
        path = (repo / rel).resolve()
        if not path.is_relative_to(repo.resolve()):
            raise ValueError('Unsafe catalog path')
        found = path.is_file()
        record = {
            'asset_hash': item['asset_hash'],
            'local_path': rel.as_posix(),
            'source_url': ('https://github.com/' + catalog['upstream_repo'] +
                           '/blob/' + catalog['upstream_commit'] + '/' +
                           item['upstream_path']),
            'bytes': item['bytes'],
            'git_blob_sha': item['github_blob_sha'],
            'status': 'NOT_COPIED',
            'clean_status': 'NOT_APPROVED',
        }
        if found:
            if path.stat().st_size != item['bytes']:
                raise ValueError('Source PSD file size mismatch: ' + str(rel))
            sha = subprocess.check_output(['git', 'hash-object', str(path)],
                                          cwd=repo, text=True).strip()
            if sha != item['github_blob_sha']:
                raise ValueError('Source PSD Git blob mismatch: ' + str(rel))
            if path.open('rb').read(4) != b'8BPS':
                raise ValueError('Source is not PSD: ' + str(rel))
            dig = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1 << 20), b''):
                    dig.update(chunk)
            record['status'] = 'COPIED_SOURCE_VERIFIED'
            record['sha256'] = dig.hexdigest()
        result.append(record)
    return {
        'queue_index': index, 'source_psd_revisions': len(result),
        'copied_revisions': sum(x['status'] == 'COPIED_SOURCE_VERIFIED' for x in result),
        'c2_plate_approved': False,
        'sources': result,
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path('.'))
    p.add_argument('--index', type=int, required=True)
    a = p.parse_args()
    print(json.dumps(lookup(a.repo.resolve(), a.index), ensure_ascii=False, indent=2))

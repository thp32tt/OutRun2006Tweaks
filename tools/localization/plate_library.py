"""Content-addressed CLEAN inputs shared by A/B; never a DDS approval gate."""
import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

LIB = Path('localization/graphics/plate_library')
VERSION = 'clean-plate-library-v1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def checked(root, ref):
    path = (root / ref['path']).resolve()
    if Path(ref['path']).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError('Unsafe library path')
    data = path.read_bytes()
    if digest(data) != ref['sha256']:
        raise ValueError('Corrupt input: ' + ref['path'])
    return data


def immutable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as f:
            f.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError('Immutable object collision: ' + str(path))


def put(root, data, suffix):
    path = LIB / 'objects' / (digest(data) + suffix)
    immutable(root / path, data)
    return {'path': path.as_posix(), 'sha256': digest(data)}


def load(root, path):
    data = path.read_bytes()
    m = json.loads(data)
    if m.get('schema') != VERSION or path.stem != digest(canonical(m)):
        raise ValueError('Manifest identity/schema mismatch')
    for key in ('source_sha256',):
        if len(m[key]) != 64 or any(c not in '0123456789abcdef' for c in m[key]):
            raise ValueError('Invalid source SHA')
    if m['orientation'] not in ('native_raw', 'readable_flip_y'):
        raise ValueError('Unknown coordinate transform')
    if not m['region_id'] or not isinstance(m['queue_index'], int):
        raise ValueError('Missing asset/region identity')
    for key in ('clean', 'removal', 'producer_evidence'):
        checked(root, m[key])
    size = tuple(m['size'])
    with Image.open(io.BytesIO(checked(root, m['clean']))) as im:
        if im.format != 'PNG' or im.mode != 'RGBA' or im.size != size:
            raise ValueError('CLEAN must be full-resolution RGBA PNG')
    with Image.open(io.BytesIO(checked(root, m['removal']))) as im:
        a = np.array(im)
        if im.format != 'PNG' or im.mode != 'L' or im.size != size or not np.all((a == 0) | (a == 255)) or not np.any(a):
            raise ValueError('Removal mask must be nonempty native binary PNG')
    return m


def resolve(root, index, source_sha, region, orientation, manifest_sha=None):
    matches = []
    for path in sorted((root / LIB / 'entries').glob('*.json')):
        if manifest_sha and path.stem != manifest_sha:
            continue
        m = load(root, path)
        if (m['queue_index'], m['source_sha256'], m['region_id'], m['orientation']) == (index, source_sha, region, orientation):
            matches.append((path, m))
    if len(matches) != 1:
        raise ValueError('Expected one exact plate; missing or ambiguous revision')
    return matches[0]


def verify_source(root, m, source):
    raw = source.read_bytes()
    if digest(raw) != m['source_sha256'] or raw[:4] != b'DDS ':
        raise ValueError('Canonical source DDS SHA mismatch')
    with Image.open(io.BytesIO(raw)) as im:
        s = np.array(im.convert('RGBA'))
    if m['orientation'] == 'readable_flip_y':
        s = s[::-1]
    c = np.array(Image.open(io.BytesIO(checked(root, m['clean']))))
    mask = np.array(Image.open(io.BytesIO(checked(root, m['removal'])))) != 0
    if s.shape != c.shape:
        raise ValueError('Native dimensions mismatch')
    outside = int(np.count_nonzero(np.any(s != c, axis=2) & ~mask))
    residue = int(np.count_nonzero(c[:, :, 3][mask])) if m['background'] == 'transparent' else None
    if outside or residue:
        raise ValueError(f'Plate pixel failure: outside={outside}, alpha_residue={residue}')
    return {'outside_removal_rgba': outside, 'transparent_alpha_residue': residue}


def review(root, path, m):
    identity = path.stem
    state_path = root / LIB / 'reviews' / (identity + '.json')
    if not state_path.exists():
        raise ValueError('HOLD: independent plate review absent; inspect stored plate, do not rebuild it')
    r = json.loads(state_path.read_text())
    lane = 'C1' if m['queue_index'] % 2 else 'C2'
    if r.get('manifest_sha256') != identity or r.get('reviewer') != lane or r.get('status') != 'PLATE_PASS':
        raise ValueError('HOLD: stale, revoked, wrong-shard or failed plate review')
    if not r.get('observations') or not r.get('evidence'):
        raise ValueError('HOLD: independent visual evidence missing')
    for ref in r['evidence']:
        checked(root, ref)
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    sub = p.add_subparsers(dest='command', required=True)
    audit = sub.add_parser('audit')
    audit.add_argument('--base', help='Reject modifications/deletions of immutable Git objects')
    for name in ('inspect', 'prepare'):
        q = sub.add_parser(name)
        q.add_argument('--index', type=int, required=True)
        q.add_argument('--source-sha', required=True)
        q.add_argument('--region', required=True)
        q.add_argument('--orientation', required=True, choices=['native_raw', 'readable_flip_y'])
        q.add_argument('--manifest-sha', help='Explicit recipe revision when more than one plate matches')
        if name == 'prepare':
            q.add_argument('--source-dds', type=Path, required=True)
            q.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'audit':
        if a.base and set(a.base) != {'0'}:
            changed = subprocess.check_output(['git', 'diff', '--name-status', '--no-renames', a.base, 'HEAD', '--',
                                               str(LIB / 'objects'), str(LIB / 'entries')], cwd=a.root, text=True)
            if any(line.split('\t')[0] != 'A' for line in changed.splitlines()):
                raise ValueError('Immutable library history was modified/deleted')
        paths = list((a.root / LIB / 'entries').glob('*.json'))
        for path in paths:
            load(a.root, path)
        print(json.dumps({'integrity': 'PASS', 'entries': len(paths), 'visual_approval': False}))
        return
    path, m = resolve(a.root, a.index, a.source_sha, a.region, a.orientation, a.manifest_sha)
    result = {'manifest_sha256': path.stem, 'manifest': str(path), 'clean': m['clean'], 'final_dds_approval': False}
    if a.command == 'prepare':
        result['pixels'] = verify_source(a.root, m, a.source_dds)
        review(a.root, path, m)
        immutable(a.output, checked(a.root, m['clean']))
        result['output'] = str(a.output)
    else:
        try:
            review(a.root, path, m)
            result['plate_review'] = 'PLATE_PASS'
        except ValueError as e:
            result['plate_review'] = str(e)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Build a reviewable native ImageGen request; never uploads, generates or deploys.

Input: mode atlas|roi, reference_png, reference_png_sha256, source_dds_sha256,
readable_transform, translations: [{source, korean}]. Relative PNG paths are
resolved against the input manifest. Source DDS/UV/CLEAN are checked downstream.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

VERSION = 'hd-imagegen-manual-v2'
TRANSFORMS = {'identity', 'flip_x', 'flip_y', 'rotate_180', 'rotate_90', 'rotate_270'}
PLACEHOLDER = re.compile(r'\{\{.*?\}\}|\[(?:승인|원문|한글|해당|정확한)[^\]]*\]')


def assemble(manifest, manifest_dir, template_dir=None):
    mode = manifest['mode']
    if mode not in ('atlas', 'roi'):
        raise ValueError('mode must be atlas or roi')
    for key in ('source_dds_sha256', 'reference_png_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', manifest[key]):
            raise ValueError(f'{key}: exact lowercase SHA-256 required')
    if manifest['readable_transform'] not in TRANSFORMS:
        raise ValueError('Mixed/unknown orientation: prepare separate readable sprite ROIs')
    rows = manifest['translations']
    if not isinstance(rows, list) or not rows or (mode == 'roi' and len(rows) != 1):
        raise ValueError('atlas needs translations; roi requires exactly one phrase')
    pairs = []
    seen = set()
    for row in rows:
        for key in ('source', 'korean'):
            value = row[key]
            if not isinstance(value, str) or not value.strip() or PLACEHOLDER.search(value):
                raise ValueError('Empty/unresolved translation placeholder')
        if row['source'] in seen:
            raise ValueError('Duplicate source phrase: consolidate or split ROI requests')
        seen.add(row['source'])
        pairs.append(json.dumps(row['source'], ensure_ascii=False) + ' → ' +
                     json.dumps(row['korean'], ensure_ascii=False))
    png = (Path(manifest_dir) / manifest['reference_png']).resolve()
    raw = png.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['reference_png_sha256']:
        raise ValueError('Reference PNG SHA mismatch')
    if len(raw) < 33 or raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
        raise ValueError('Reference is not a PNG with IHDR')
    width, height = struct.unpack('>II', raw[16:24])
    if not width or not height:
        raise ValueError('Invalid PNG dimensions')
    directory = Path(template_dir) if template_dir else Path(__file__).parent / 'imagegen_prompts'
    template = (directory / f'{mode}.txt').read_text(encoding='utf-8')
    prompt = template.replace('{{TRANSLATIONS}}', '\n'.join(pairs))
    if PLACEHOLDER.search(prompt):
        raise ValueError('Unresolved prompt placeholder')
    receipt = {
        'policy_version': VERSION, 'mode': mode,
        'status': 'PROMPT_PREPARED_NOT_GENERATED',
        'source_dds_sha256': manifest['source_dds_sha256'],
        'reference_png': str(png), 'reference_png_sha256': manifest['reference_png_sha256'],
        'reference_size': [width, height], 'readable_transform': manifest['readable_transform'],
        'template_sha256': hashlib.sha256(template.encode()).hexdigest(),
        'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'transparent_background': True if mode == 'roi' else 'PRESERVE_SOURCE_ALPHA',
        'attachment_verified': False, 'generation_id': None, 'generated_png_sha256': None,
        'RUNTIME_VALIDATION': 'UNTESTED',
    }
    return prompt, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prompt, receipt = assemble(json.loads(args.manifest.read_text(encoding='utf-8')), args.manifest.parent)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'prompt.txt').write_text(prompt, encoding='utf-8')
    (args.output / 'request.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PROMPT_PREPARED_NOT_GENERATED')


if __name__ == '__main__':
    main()

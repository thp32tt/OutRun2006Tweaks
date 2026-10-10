"""Extract an explicitly selected PSD layer as a full native canvas, never auto-approve it."""
import argparse
import hashlib
import json
from pathlib import Path


def extract(source, expected_sha, indices, output):
    from psd_tools import PSDImage
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('PSD SHA mismatch')
    psd = PSDImage.open(source)
    layer = psd
    names = []
    for index in indices:
        if index < 0 or index >= len(layer):
            raise ValueError('Invalid explicit layer index')
        layer = layer[index]
        names.append(layer.name)
    if not indices:
        raise ValueError('Explicit layer path required; merged PSD is not a CLEAN plate')
    image = layer.composite(viewport=(0, 0, psd.width, psd.height), force=True)
    if image is None or image.size != (psd.width, psd.height):
        raise ValueError('Layer cannot be composited at native canvas size')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError('Refuse to overwrite an extracted input')
    image.convert('RGBA').save(output)
    report = {'source_psd_sha256': expected_sha, 'indices': indices, 'layer_names': names,
              'size': list(image.size), 'orientation': 'psd_native',
              'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'status': 'EXTRACTED_UNVERIFIED', 'canonical_dds_match': 'NOT_TESTED',
              'plate_visual_approval': False, 'final_dds_approval': False}
    output.with_suffix('.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psd', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--layer-indices', required=True, help='Explicit zero-based path, e.g. 1/0/2/1/0')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(extract(a.psd, a.sha256, [int(i) for i in a.layer_indices.split('/')], a.output)))

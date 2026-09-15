from pathlib import Path

paths = [
    Path('src/vr/d3d9/stereo_renderer_r7.inc'),
    Path('src/vr/d3d9/stereo_renderer.cpp'),
]

for path in paths:
    text = path.read_text(encoding='utf-8')
    fixed_lines = []
    changed = 0
    for line in text.splitlines(keepends=True):
        prefix = ''
        rest = line
        while rest.startswith('\\t'):
            prefix += '\t'
            rest = rest[2:]
            changed += 1
        fixed_lines.append(prefix + rest)
    if not changed:
        raise SystemExit(f'no literal indentation escapes found in {path}')
    path.write_text(''.join(fixed_lines), encoding='utf-8', newline='\n')
    print(f'{path}: converted {changed} leading literal \\t escapes to real tabs')

# Fail if a line still begins with a literal backslash-t in either file.
for path in paths:
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.startswith('\\t'):
            raise SystemExit(f'literal indentation escape remains: {path}:{number}')

print('VR patch indentation cleanup complete')

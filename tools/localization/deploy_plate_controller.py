"""N100-only deployment: restore missing localization controller, preserve VR and state.

Run from an exact reviewed checkout. Refuses to replace an existing container.
Uses existing private stack settings in memory without logging secrets.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

NAME = 'outrun-chat-controller-localization-recovery'
BASE = 'outrun-kor-outrun-chat-controller-localization-recovery'
STACK = '/pdata/compose/54'
SUBDIR = 'tools/chat-controller/localization-recovery-v1'


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs).stdout


def deploy(root, revision):
    import yaml
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Exact Git commit required')
    exists = subprocess.run(['docker', 'inspect', NAME], capture_output=True)
    if exists.returncode == 0:
        raise ValueError('Controller already exists; inspect active work before replacement')
    code = f"""import pathlib,json
b=pathlib.Path({STACK!r}); env={{}}
for line in (b/'stack.env').read_text().splitlines():
 if '=' in line and not line.lstrip().startswith('#'):
  k,v=line.split('=',1);env[k]=v.strip().strip('\\\"').strip("'")
print(json.dumps({{'compose':(b/{SUBDIR!r}/'docker-compose.yml').read_text(),'env':env}}))
"""
    payload = json.loads(run(['docker', 'run', '--rm', '--entrypoint', 'python', '-v',
                             'portainer_data:/pdata:ro', BASE, '-c', code]))
    compose = yaml.safe_load(payload['compose'])
    service = compose['services'][NAME]
    environment = {}
    for key, value in service['environment'].items():
        def substitute(match):
            return payload['env'].get(match[1]) or (match[2] or '')
        environment[key] = re.sub(r'\$\{([^}:]+)(?::-([^}]*))?\}', substitute, str(value))
    if environment.get('AUTO_SEND') != 'true' or not environment.get('CHATGPT_PROJECT_URL'):
        raise ValueError('Existing stack must authorize automatic localization with project URL')
    # Do not copy GITHUB_TOKEN or any unrelated stack credentials into the controller.
    image = 'outrun-kor-plate-engine:' + revision[:12]
    prompt_dir = root / 'tools/localization/controller_prompts'
    hashes = {}
    with tempfile.TemporaryDirectory(prefix='outrun-plate-deploy-') as tmp:
        b = Path(tmp)
        for lane in ('A', 'B', 'C1', 'C2'):
            name = f'localization_{lane}.md'; raw = (prompt_dir / name).read_bytes()
            hashes[name] = hashlib.sha256(raw).hexdigest(); (b / name).write_bytes(raw)
        (b / 'production_revision').write_text(revision + '\n')
        (b / 'Dockerfile').write_text('FROM ' + BASE + '\nCOPY localization_*.md /opt/outrun/prompts/\nCOPY production_revision /opt/outrun/production_revision\n')
        run(['docker', 'build', '-t', image, str(b)], timeout=120)
    # Save prompt source in the existing Portainer build context for future rebuilds.
    encoded = json.dumps({name: (prompt_dir / name).read_text() for name in hashes})
    update = f"""import pathlib,json
b=pathlib.Path({(STACK+'/'+SUBDIR)!r})
for name,text in json.loads({encoded!r}).items():
 p=b/'prompts'/name
 backup=p.with_suffix('.md.before-plate-{revision[:12]}')
 if p.exists() and not backup.exists(): backup.write_bytes(p.read_bytes())
 p.write_text(text)
p=b/'docker-compose.yml';s=p.read_text(); marker='    image: {image}\\n'
if marker not in s:
 if '    image:' in s: raise RuntimeError('Unexpected existing image mapping; manual reconcile required')
 backup=p.with_suffix('.yml.before-plate-{revision[:12]}')
 if not backup.exists(): backup.write_text(s)
 p.write_text(s.replace('    build:',marker+'    build:',1))
"""
    run(['docker', 'run', '--rm', '--entrypoint', 'python', '-v', 'portainer_data:/pdata', BASE, '-c', update])
    cmd = ['docker', 'run', '-d', '--name', NAME, '--restart', 'unless-stopped', '--init',
           '--shm-size', str(service['shm_size']), '--memory', str(service['mem_limit']),
           '--memory-reservation', str(service['mem_reservation']), '--cpus', str(service['cpus'])]
    for key in environment:
        cmd += ['--env', key]
    for port in service['ports']:
        cmd += ['-p', str(port)]
    for mount in service['volumes']:
        volume, target = mount.split(':', 1)
        actual = compose['volumes'][volume].get('name', volume)
        cmd += ['-v', actual + ':' + target]
    cmd += ['--label', 'outrun.production-revision=' + revision,
            '--health-cmd', "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/status', timeout=5)\"",
            '--health-interval', '30s', '--health-start-period', '90s', '--health-retries', '3', image]
    container_id = run(cmd, env={**os.environ, **environment}).strip()
    return {'container': NAME, 'id': container_id, 'image': image, 'revision': revision,
            'prompt_sha256': hashes, 'status': 'STARTED_PENDING_HEALTH', 'game_validation': 'UNTESTED'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--revision', required=True)
    a = p.parse_args()
    print(json.dumps(deploy(a.root, a.revision), ensure_ascii=False))

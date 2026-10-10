"""Stage the reviewed localization image and prompts for a Portainer-managed stack.

Do not launch the application with docker run: that creates an unmanaged container
whose fixed name conflicts with a later Portainer / Compose deployment.
Preserve state volumes, VR services, and all private stack settings.
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
    existing = subprocess.run(['docker', 'inspect', NAME], capture_output=True, text=True)
    existing_meta = json.loads(existing.stdout)[0] if existing.returncode == 0 else None
    # The source image can contain inherited Compose labels. Only a
    # config-hash label identifies a real Compose-created container.
    compose_managed = bool(
        existing_meta
        and (existing_meta['Config'].get('Labels') or {}).get('com.docker.compose.config-hash')
    )
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
    # Portainer must be the only lifecycle owner. Image/prompt staging is
    # non-disruptive: never stop/remove the running controller here.
    if existing_meta and not compose_managed:
        status = 'STAGED_HANDOFF_REQUIRED'
        next_action = (
            'Existing standalone controller owns the fixed name. During a '
            'planned maintenance window, stop and remove ONLY that container '
            '(never use docker rm -v); then redeploy the Portainer stack. '
            'The existing /data and /logs named volumes remain intact.'
        )
    else:
        status = 'STAGED_PORTAINER_REDEPLOY_READY'
        next_action = 'Deploy or redeploy the existing Portainer localization stack.'
    return {'container': NAME, 'image': image, 'revision': revision,
            'prompt_sha256': hashes, 'status': status, 'next_action': next_action,
            'previous_image': existing_meta['Config']['Image'] if existing_meta else None,
            'previous_status': existing_meta['State']['Status'] if existing_meta else None,
            'preserved_volumes': ['outrun_chat_localization_recovery_data',
                                  'outrun_chat_localization_recovery_logs'],
            'game_validation': 'UNTESTED'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--revision', required=True)
    a = p.parse_args()
    print(json.dumps(deploy(a.root, a.revision), ensure_ascii=False))

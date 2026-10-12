"""Stage the reviewed localization image and prompts for a Portainer-managed stack.

Do not launch the application with docker run: that creates an unmanaged container
whose fixed name conflicts with a later Portainer / Compose deployment.
Preserve state volumes, VR services, and all private stack settings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from stage_controller_policy import render, validate_roles

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
    root = root.resolve()
    if run(['git', '-C', str(root), 'rev-parse', 'HEAD']).strip() != revision:
        raise ValueError('Checkout HEAD does not match requested revision')
    policy_path = root / 'localization/controller_roles.json'
    roles = json.loads(policy_path.read_text())
    validate_roles(roles)
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
    staged_compose = render(payload['compose'], revision)
    compose = yaml.safe_load(staged_compose)
    service = compose['services'][NAME]
    environment = {}
    for key, value in service['environment'].items():
        def substitute(match):
            return payload['env'].get(match[1]) or (match[2] or '')
        environment[key] = re.sub(r'\$\{([^}:]+)(?::-([^}]*))?\}', substitute, str(value))
    if not environment.get('CHATGPT_PROJECT_URL'):
        raise ValueError('Existing stack must provide project URL')
    # User explicitly requested AUTO_SEND=true; deployment remains manual.
    sources = list((root / 'tools/localization/controller_prompts').glob('localization_*.md'))
    sources += list((root / 'tools/localization/imagegen_prompts').glob('*.txt'))
    sources += [policy_path, root / 'docs/KOREAN_LOCALIZATION_HD_PNG_IMAGEGEN_AND_FAST_QA_20261012.md',
                root / 'tools/localization/build_imagegen_prompt.py',
                root / 'tools/localization/deploy_plate_controller.py',
                root / 'tools/localization/stage_controller_policy.py',
                root / 'tools/localization/controller_png_attach.py',
                root / 'tools/localization/patch_controller_png_upload.py']
    for source in sources:
        relative = source.relative_to(root).as_posix()
        committed = run(['git', '-C', str(root), 'show', revision + ':' + relative])
        if committed != source.read_text():
            raise ValueError('Uncommitted staged source: ' + relative)
    # Do not copy GITHUB_TOKEN or any unrelated stack credentials into the controller.
    image = 'outrun-kor-plate-engine:' + revision[:12]
    prompt_dir = root / 'tools/localization/controller_prompts'
    hashes = {}
    with tempfile.TemporaryDirectory(prefix='outrun-plate-deploy-') as tmp:
        b = Path(tmp)
        for lane in ('A', 'B', 'C1'):
            name = f'localization_{lane}.md'; raw = (prompt_dir / name).read_bytes()
            hashes[name] = hashlib.sha256(raw).hexdigest(); (b / name).write_bytes(raw)
            if lane == 'C1':
                hashes['localization_C.md'] = hashes[name]
                (b / 'localization_C.md').write_bytes(raw)
        (b / 'production_revision').write_text(revision + '\n')
        (b / 'controller_roles.json').write_bytes(policy_path.read_bytes())
        (b / 'imagegen_prompts').mkdir()
        for template in (root / 'tools/localization/imagegen_prompts').glob('*.txt'):
            (b / 'imagegen_prompts' / template.name).write_bytes(template.read_bytes())
        (b / 'build_imagegen_prompt.py').write_bytes((root / 'tools/localization/build_imagegen_prompt.py').read_bytes())
        (b / 'HD_IMAGEGEN_POLICY.md').write_bytes((root / 'docs/KOREAN_LOCALIZATION_HD_PNG_IMAGEGEN_AND_FAST_QA_20261012.md').read_bytes())
        (b / 'controller_png_attach.py').write_bytes((root / 'tools/localization/controller_png_attach.py').read_bytes())
        (b / 'patch_controller_png_upload.py').write_bytes((root / 'tools/localization/patch_controller_png_upload.py').read_bytes())
        (b / 'Dockerfile').write_text('FROM ' + BASE + '\nRUN rm -f /opt/outrun/prompts/localization_C2.md\nCOPY controller_png_attach.py /opt/outrun/app/controller_png_attach.py\nCOPY patch_controller_png_upload.py /opt/outrun/patch_controller_png_upload.py\nRUN python /opt/outrun/patch_controller_png_upload.py /opt/outrun/app/controller.py\nCOPY localization_*.md /opt/outrun/prompts/\nCOPY production_revision /opt/outrun/production_revision\nCOPY controller_roles.json HD_IMAGEGEN_POLICY.md build_imagegen_prompt.py /opt/outrun/\nCOPY imagegen_prompts /opt/outrun/imagegen_prompts/\n')
        run(['docker', 'build', '-t', image, str(b)], timeout=120)
    # Save prompt source in the existing Portainer build context for future rebuilds.
    encoded = json.dumps({name: (prompt_dir / ('localization_C1.md' if name == 'localization_C.md' else name)).read_text() for name in hashes})
    update = f"""import pathlib,json
b=pathlib.Path({(STACK+'/'+SUBDIR)!r})
p=b/'docker-compose.yml'; original=p.read_text()
if original != {payload['compose']!r}: raise RuntimeError('Compose changed during staging; retry from fresh snapshot')
(b/'prompts').mkdir(exist_ok=True)
for name,text in json.loads({encoded!r}).items():
 p=b/'prompts'/name
 backup=p.with_suffix('.md.before-plate-{revision[:12]}')
 if p.exists() and not backup.exists(): backup.write_bytes(p.read_bytes())
 p.write_text(text)
p=b/'docker-compose.yml'
updated={staged_compose!r}
if updated != original:
 backup=p.with_suffix('.yml.before-plate-{revision[:12]}')
 if not backup.exists(): backup.write_text(original)
 tmp=p.with_suffix('.yml.tmp');tmp.write_text(updated);tmp.replace(p)
# Remove retired prompt only after preserving a copy. No browser tabs are closed here.
p=b/'prompts'/'localization_C2.md'
if p.exists():
 backup=p.with_suffix('.md.retired-{revision[:12]}')
 if not backup.exists(): backup.write_bytes(p.read_bytes())
 p.unlink()

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
        next_action = ('Manually redeploy the existing Portainer localization stack with AUTO_SEND=true. '
                       'Verify A/B/C1 tabs, exact minute-to-role dispatch and source attachment/output '
                       'smoke after the manual deployment; these checks remain unverified.')
    return {'container': NAME, 'image': image, 'revision': revision,
            'prompt_sha256': hashes, 'status': status, 'next_action': next_action,
            'previous_image': existing_meta['Config']['Image'] if existing_meta else None,
            'previous_status': existing_meta['State']['Status'] if existing_meta else None,
            'preserved_volumes': ['outrun_chat_localization_recovery_data',
                                  'outrun_chat_localization_recovery_logs'],
            'auto_send': True, 'deployment_mode': 'MANUAL_ONLY',
            'runtime_schedule_verified': False, 'imagegen_e2e': 'UNTESTED',
            'game_validation': 'UNTESTED'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--revision', required=True)
    p.add_argument('--stage', action='store_true', help='Explicitly build image and stage Compose; never redeploys')
    a = p.parse_args()
    if not a.stage:
        p.error('--stage is required; this command never deploys/restarts the running controller')
    print(json.dumps(deploy(a.root, a.revision), ensure_ascii=False))


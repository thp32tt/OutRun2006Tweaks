"""Pure Compose policy transformation. Does not contact Docker or start containers."""
from copy import deepcopy
import json
import re

NAME = 'outrun-chat-controller-localization-recovery'
IMAGE_PREFIX = 'outrun-kor-plate-engine:'


def configure(compose, revision):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Exact Git commit required')
    result = deepcopy(compose)
    service = deepcopy(result['services'][NAME])
    result['services'][NAME] = service
    image = service.get('image')
    if image and not str(image).startswith(IMAGE_PREFIX):
        raise ValueError('Unexpected existing image mapping; manual reconcile required')
    env = deepcopy(service.get('environment', {}))
    if isinstance(env, list):
        mapped = {}
        for item in env:
            key, sep, value = item.partition('=')
            if key in mapped:
                raise ValueError('Duplicate environment key')
            mapped[key] = value if sep else None
        env = mapped
    if not isinstance(env, dict):
        raise ValueError('Environment must be mapping or list')
    env.update(CHAT_SLOTS='3', SCHEDULE_MINUTES='0,10,30,40', AUTO_SEND='true')
    service['environment'] = env
    service['image'] = IMAGE_PREFIX + revision[:12]
    return result


def render(compose_text, revision):
    import yaml
    return yaml.safe_dump(configure(yaml.safe_load(compose_text), revision),
                          allow_unicode=True, sort_keys=False)


def validate_roles(roles):
    expected = {'0': 'A', '10': 'C1', '30': 'B', '40': 'C1'}
    if roles['controller_tab_order'] != ['A', 'B', 'C1']:
        raise ValueError('Expected A/B/C1 tabs')
    if roles['schedule_dispatch']['minute_to_role'] != expected:
        raise ValueError('Explicit minute-to-role policy mismatch')
    if roles['deployment']['mode'] != 'MANUAL_ONLY' or roles['deployment']['stage_auto_send'] is not True:
        raise ValueError('Manual deployment and user-authorized AUTO_SEND=true required')
    if roles['lanes']['C1']['image_generation_enabled']:
        raise ValueError('C1 is independent QA only')

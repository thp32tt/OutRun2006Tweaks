from pathlib import Path

path = Path('tools/verify_wheel_ffb_current.py')
text = path.read_text(encoding='utf-8')
for line in (
    "discord_share = read('DISCORD_SHARE_v0.1.md')\n",
    "req(discord_share, 'Dynamic Damping 0.28', 'Discord share uses the current Physics damping')\n",
    "forbid(discord_share, 'Damping 0.42', 'Discord share has no obsolete damping value')\n",
):
    if line not in text:
        raise SystemExit(f'stale verifier line not found: {line!r}')
    text = text.replace(line, '', 1)
path.write_text(text, encoding='utf-8')
print('Removed stale verifier dependency on deleted DISCORD_SHARE_v0.1.md')

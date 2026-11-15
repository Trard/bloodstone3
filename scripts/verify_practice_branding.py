import json
import math
import subprocess
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
font = json.loads((root / 'assets/minecraft/font/practice_branding.json').read_text(encoding='utf-8'))
advances = {}
for provider in font['providers']:
    if provider['type'] == 'space':
        advances.update(provider['advances'])
        continue
    assert provider['ascent'] <= provider['height']
    namespace, filename = provider['file'].split(':')
    image = Image.open(root / 'assets' / namespace / 'textures' / filename).convert('RGBA')
    assert image.size == (255, 160)
    bounds = image.getchannel('A').getbbox()
    assert bounds is not None and bounds[2] <= 178 and bounds[3] <= 86
    advance = math.floor(.5 + bounds[2] * provider['height'] / image.height) + 1
    advances[provider['chars'][0]] = advance

prefix = '\uE9E4\uE9E1\uE9E5\uE9E2\uE9E5\uE9E3\uE9E6'
assert sum(advances[c] for c in prefix) == 0
assert advances['\uE9E1'] + advances['\uE9E5'] == 44.5
assert advances['\uE9E2'] + advances['\uE9E5'] == 44.5
for name in ['default', 'bot_training']:
    document = json.loads((root / ('assets/minecraft/font/' + name + '.json')).read_text(encoding='utf-8'))
    assert any(p.get('type') == 'reference' and p.get('id') == 'minecraft:practice_branding'
               for p in document['providers'])

checked = 0
for folder in ['practice_v4', 'bot_training']:
    for image in (root / 'assets/minecraft/textures/gui' / folder).glob('*.png'):
        relative = image.relative_to(root).as_posix()
        original = subprocess.check_output(['git', 'show', 'f69e30b7:' + relative], cwd=root)
        assert original == image.read_bytes(), relative
        checked += 1
print(json.dumps({'glyph_advances': {hex(ord(k)): v for k, v in advances.items()},
                  'prefix_advance': 0, 'unchanged_menu_images': checked}, indent=2))

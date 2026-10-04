"""Build the pixel-aligned inventory panels used only by BloodInvasion."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
TEXTURES = ROOT / 'assets/minecraft/textures/gui/invasion'
FONTS = ROOT / 'assets/minecraft/font/invasion_menu'
LINE_Y = [2, 24, 10, 34, 43, 52, 61, 88, 97, 41, 59, 77, 95]
ROSTER = [9, 14, 18, 23, 27, 32, 36, 41]
SHOP = [10, 12, 14, 16, 19, 21, 23, 25, 28, 31, 34]
CARDS = {1: [13], 2: [11, 15], 3: [2, 6, 31],
         4: [2, 6, 29, 33], 5: [1, 4, 7, 29, 33],
         6: [1, 4, 7, 28, 31, 34]}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def bevel(draw, box, fill='#EEEEEE'):
    x, y, r, b = box
    draw.rectangle((x+1, y, r-1, b), fill='#222222')
    draw.rectangle((x, y+1, r, b-1), fill='#222222')
    draw.rectangle((x+1, y+1, r-1, b-1), fill=fill)
    draw.line((x+2, b-2, x+2, y+2, r-2, y+2), fill='#FFFFFF')
    draw.line((r-2, y+3, r-2, b-2, x+3, b-2), fill='#888888')


class OffsetDraw:
    def __init__(self, image): self.draw = ImageDraw.Draw(image)
    def rectangle(self, box, **kw):
        x, y, r, b = box
        self.draw.rectangle((x, y+8, r, b+8), **kw)
    def line(self, points, **kw):
        self.draw.line(tuple(n+8 if i%2 else n for i,n in enumerate(points)), **kw)
    def point(self, point, **kw): self.draw.point((point[0], point[1]+8), **kw)


def card_boxes(count):
    for anchor in CARDS[count]:
        cx = 16 + anchor % 9 * 18
        top = 16 + anchor // 9 * 18
        half = 26 if count >= 5 else 32
        yield cx-half, top, cx+half, top+37


def build_panel(name, index):
    panel = Image.new('RGBA', (256, 256))
    mask = Image.new('RGBA', (256, 256))
    d, a = OffsetDraw(panel), OffsetDraw(mask)
    bevel(d, (0, -8, 175, 221), '#D4D4D4')
    bevel(d, (6, -4, 169, 13), '#E8E8E8')
    d.rectangle((5, 126, 170, 216), fill='#C6C6C6')
    d.line((6, 125, 169, 125), fill='#FFFFFF')
    for row in range(4):
        for col in range(9):
            x = 7 + col * 18
            y = 138 + row * 18 if row < 3 else 196
            d.rectangle((x, y, x+17, y+17), fill='#888888')
            d.line((x+1, y+16, x+16, y+16, x+16, y+1), fill='#FFFFFF')
            d.rectangle((x+1, y+1, x+15, y+15), fill='#B5B5B5')
    boxes = []
    if name.startswith('cards_'):
        boxes = list(card_boxes(int(name[-1])))
    elif name == 'roster':
        boxes = [(7 + slot % 9 * 18, 17 + slot // 9 * 18,
                  78 + slot % 9 * 18, 34 + slot // 9 * 18) for slot in ROSTER]
    elif name == 'factions':
        boxes = list(card_boxes(3))
    elif name == 'shop':
        for slot in SHOP:
            cx, y = 16 + slot % 9 * 18, 17 + slot // 9 * 18
            boxes.append((cx-16, y, cx+16, y+17))
        d.line((12, 92, 163, 92), fill='#AAAAAA')
    for box in boxes:
        bevel(d, box, '#EEEEEE')
        x, y, r, b = box
        a.line((x+3, y+3, x+3, b-3), fill='white')
    for slot in ([49] if name == 'shop' else []):
        x = 7 + slot % 9 * 18
        bevel(d, (x, 107, x+17, 124), '#EEEEEE')
    a.point((175, 221), fill=(255, 255, 255, 26))
    TEXTURES.mkdir(parents=True, exist_ok=True)
    panel.save(TEXTURES / f'{name}.png', optimize=True)
    mask.save(TEXTURES / f'{name}_accent.png', optimize=True)
    return [dict(type='bitmap', file=f'minecraft:gui/invasion/{name}{suffix}.png',
                 height=256, ascent=21, chars=[chr(0xE800 + index*2 + i)])
            for i, suffix in enumerate(['', '_accent'])]


def build_icons():
    folder = ROOT / 'assets/minecraft/textures/item/invasion/menu'
    folder.mkdir(parents=True, exist_ok=True)
    for name in ['close', 'previous', 'next', 'back', 'confirm', 'clear', 'locked', 'empty']:
        image = Image.new('RGBA', (16, 16))
        d = ImageDraw.Draw(image)
        if name != 'empty': bevel(d, (0, 0, 15, 15), '#EEEEEE')
        if name in ['close', 'clear']:
            d.line((4, 4, 11, 11), fill='#323C39', width=4)
            d.line((11, 4, 4, 11), fill='#323C39', width=4)
            d.line((4, 3, 11, 10), fill='#DF786B', width=2)
            d.line((11, 3, 4, 10), fill='#DF786B', width=2)
        elif name == 'confirm':
            d.line((3, 8, 6, 11, 13, 4), fill='#253D30', width=4)
            d.line((3, 7, 6, 10, 13, 3), fill='#75BB70', width=2)
        elif name == 'locked':
            d.rectangle((5, 3, 10, 8), outline='#52645C', width=2)
            d.rectangle((3, 7, 12, 13), fill='#52645C')
            d.rectangle((4, 8, 11, 12), fill='#A1AEA5')
            d.line((8, 9, 8, 11), fill='#52645C')
        elif name != 'empty':
            d.polygon([(2, 8), (8, 2), (8, 5), (14, 5), (14, 10), (8, 10), (8, 13)], fill='#35443F')
            d.polygon([(3, 7), (7, 3), (7, 6), (13, 6), (13, 8), (7, 8), (7, 11)], fill='#F1E2A7')
            if name == 'next': image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        path = folder / f'{name}.png'
        image.save(path, optimize=True)
        subprocess.run([sys.executable, str(ROOT / 'scripts/create_icon_from_png.py'), str(path),
                        '--assets-root', str(ROOT / 'assets'), '--namespace', 'minecraft',
                        '--group', 'invasion/menu', '--name', name, '--force'], check=True,
                       stdout=subprocess.DEVNULL)


def main():
    FONTS.mkdir(parents=True, exist_ok=True)
    wanted = {f'line_{y}.json' for y in LINE_Y}
    for path in FONTS.glob('line_*.json'):
        if path.name not in wanted:
            path.unlink()
    providers = []
    for i, name in enumerate([f'cards_{n}' for n in range(1, 7)] + ['roster', 'shop', 'factions']):
        providers.extend(build_panel(name, i))
    write_json(FONTS / 'panels.json', {'providers': providers})
    source = json.loads((ROOT / 'assets/minecraft/font/invasion_hud_top.json').read_text('utf-8'))
    for y in LINE_Y:
        font = deepcopy(source)
        for provider in font['providers']:
            if provider['type'] != 'bitmap': continue
            provider['ascent'] += 6-y
            if provider['ascent'] > provider['height']:
                texture = ROOT / 'assets/minecraft/textures' / provider['file'].split(':')[1]
                atlas = Image.open(texture).convert('RGBA')
                rows = provider['chars']
                w, h = atlas.width // len(rows[0]), atlas.height // len(rows)
                padded = Image.new('RGBA', (atlas.width, len(rows)*32))
                for row in range(len(rows)):
                    padded.paste(atlas.crop((0,row*h,atlas.width,(row+1)*h)), (0,row*32))
                target = TEXTURES / (texture.stem + '_header.png')
                padded.save(target, optimize=True)
                provider['file'] = 'minecraft:gui/invasion/' + target.name
                provider['height'] = 32
        write_json(FONTS / f'line_{y}.json', font)
    build_icons()
    print('Built 9 menu layouts, faction accents, text baselines and 8 control models.')


if __name__ == '__main__': main()

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
LINE_Y = [9, 24, 10, 40, 54, 58, 63, 76, 90, 99, 112]
ROSTER = [r*9+c for r in range(1,5) for c in range(1,8)]
SHOP = [10, 12, 14, 16, 19, 21, 23, 25, 28, 31, 34]
CARDS = {1: [13], 2: [11, 15], 3: [10, 13, 16],
         4: [11, 15, 29, 33], 5: [10, 13, 16, 29, 33],
         6: [10, 13, 16, 28, 31, 34]}
SPAWNS = {1: [13], 2: [13, 31], 3: [13, 29, 33], 4: [13, 29, 31, 33],
          5: [13, 28, 30, 32, 34], 6: [13, 27, 29, 31, 33, 35]}
PRACTICE = ROOT / 'assets/bloodstone/textures/ui/gui/practice/practice_menu_ru.png'
PLAYERS = ROOT / 'assets/duels/textures/gui/players.png'



def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def bevel(draw, box, fill='#D6D6D6'):
    x, y, r, b = box
    draw.rectangle((x+1, y, r-1, b), fill='#202020')
    draw.rectangle((x, y+1, r, b-1), fill='#202020')
    draw.rectangle((x+1, y+1, r-1, b-1), fill=fill)
    draw.line((x+2, b-2, x+2, y+2, r-2, y+2), fill='#FFFFFF')
    draw.line((r-2, y+3, r-2, b-2, x+3, b-2), fill='#858585')


def stretch_frame(tile, width, height):
    result = Image.new('RGBA', (width,height))
    sx, sy = [0,3,tile.width-3,tile.width], [0,3,tile.height-3,tile.height]
    dx, dy = [0,3,width-3,width], [0,3,height-3,height]
    for row in range(3):
        for col in range(3):
            patch = tile.crop((sx[col],sy[row],sx[col+1],sy[row+1]))
            patch = patch.resize((dx[col+1]-dx[col],dy[row+1]-dy[row]),Image.Resampling.NEAREST)
            result.paste(patch,(dx[col],dy[row]))
    return result


def build_panel(name, index):
    # Reuse the actual Bloodstone panel, header, button edges and inventory cells.
    practice = Image.open(PRACTICE).convert('RGBA')
    source = Image.open(PLAYERS).convert('RGBA')
    ImageDraw.Draw(source).rectangle((4,4,171,129),fill='#C6C6C6')
    rows = (6 if name in ('roster','shop','factions') else
            3 if name in ('cards_1','cards_2','cards_3','spawns_1') else 5)
    cut = (6-rows)*18
    height = 114+rows*18
    panel = Image.new('RGBA',(256,256))
    panel.paste(source.crop((0,0,176,126-cut)),(0,0))
    panel.paste(source.crop((0,126,176,222)),(0,126-cut))
    mask = Image.new('RGBA',(256,256)); a=ImageDraw.Draw(mask)
    heading = practice.crop((44,6,132,21))
    ImageDraw.Draw(heading).rectangle((4,3,83,11),fill='#C6C6C6')
    heading_width = 112 if name.startswith('spawns_') else 96 if name in ('roster','shop') else 88
    panel.paste(stretch_frame(heading,heading_width,15),((176-heading_width)//2,6))
    a.line(((176-heading_width)//2+5,21,(176+heading_width)//2-6,21),fill='white')
    cell = practice.crop((7,83,25,101))
    boxes=[]
    if name in ('roster','shop'):
        # Roster heads use ordinary slots; each shop offer gets its own button.
        for slot in ROSTER if name=='roster' else []:
            panel.paste(cell,(7+slot%9*18,18+slot//9*18))
        if name == 'shop':
            for slot in SHOP:
                x,y=7+slot%9*18,18+slot//9*18
                panel.paste(cell,(x,y))
            panel.paste(cell,(7+49%9*18,18+49//9*18))
    elif name == 'factions':
        for row in range(3):
            boxes.append((7,32+row*36,168,55+row*36))
    elif name.startswith('spawns_'):
        for choice,slot in enumerate(SPAWNS[int(name[-1])]):
            cx=16+slot%9*18
            top=27 if choice==0 else 68
            half=26 if choice==0 else (16 if int(name[-1]) < 6 else 13)
            boxes.append((cx-half,top,cx+half,top+37))
    else:
        count=3 if name=='factions' else int(name[-1])
        for slot in CARDS[count]:
            cx=16+slot%9*18
            top=27+(slot//9-1)*18
            half=25 if count>=3 else 32
            boxes.append((cx-half,top,cx+half,top+(44 if count==1 else 37)))
    for x,y,r,b in boxes:
        bevel(ImageDraw.Draw(panel),(x,y,r,b))
    a.point((175,height-1),fill=(255,255,255,26))
    TEXTURES.mkdir(parents=True,exist_ok=True)
    panel.save(TEXTURES/f'{name}.png',optimize=True)
    mask.save(TEXTURES/f'{name}_accent.png',optimize=True)
    return [dict(type='bitmap',file=f'minecraft:gui/invasion/{name}{suffix}.png',
                 height=256,ascent=14,chars=[chr(0xE800+index*2+i)])
            for i,suffix in enumerate(['','_accent'])]


def build_icons():
    folder = ROOT / 'assets/minecraft/textures/item/invasion/menu'
    folder.mkdir(parents=True, exist_ok=True)
    for name in ['close', 'previous', 'next', 'back', 'confirm', 'disabled', 'clear', 'locked', 'empty']:
        image = Image.new('RGBA', (16, 16))
        d = ImageDraw.Draw(image)
        if name != 'empty': bevel(d, (0, 0, 15, 15))
        if name in ['close', 'clear']:
            for x,y in [(4,4),(5,5),(6,6),(7,7),(8,8),(9,9),(10,10),
                        (10,4),(9,5),(8,6),(6,8),(5,9),(4,10)]:
                d.rectangle((x,y,x+1,y+1),fill='#AB403D')
        elif name in ('confirm','disabled'):
            color = '#397842' if name=='confirm' else '#969696'
            for x,y in [(3,7),(4,8),(5,9),(6,10),(7,9),(8,8),(9,7),(10,6),(11,5)]:
                d.rectangle((x,y,x+1,y+1),fill=color)
        elif name == 'locked':
            d.rectangle((5, 3, 10, 8), outline='#52645C', width=2)
            d.rectangle((3, 7, 12, 13), fill='#52645C')
            d.rectangle((4, 8, 11, 12), fill='#A1AEA5')
            d.line((8, 9, 8, 11), fill='#52645C')
        elif name != 'empty':
            d.polygon([(3,7),(7,3),(7,6),(12,6),(12,9),(7,9),(7,12)], fill='#484848')
            if name == 'next': image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if name in ('previous', 'next'):
            image = Image.new('RGBA', (32,32))
            d=ImageDraw.Draw(image)
            bevel(d,(2,9,29,22))
            d.polygon([(11,15),(16,11),(16,14),(21,14),(21,17),(16,17),(16,20)],fill='#484848')
            if name=='next':
                # Mirror only the arrow: lighting stays on the upper left.
                glyph=image.crop((10,11,22,21)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                image.paste(glyph,(10,11))
        path = folder / f'{name}.png'
        image.save(path, optimize=True)
        subprocess.run([sys.executable, str(ROOT / 'scripts/create_icon_from_png.py'), str(path),
                        '--assets-root', str(ROOT / 'assets'), '--namespace', 'minecraft',
                        '--group', 'invasion/menu', '--name', name, '--force'], check=True,
                       stdout=subprocess.DEVNULL)
        if name in ('previous', 'next'):
            model = ROOT / f'assets/minecraft/models/item/invasion/menu/{name}.json'
            data = json.loads(model.read_text('utf-8'))
            data['display'] = {'gui': {'scale': [2,2,2], 'translation': [2 if name=='previous' else -2,0,0]}}
            write_json(model, data)
            item = ROOT / f'assets/minecraft/items/invasion/menu/{name}.json'
            definition = json.loads(item.read_text('utf-8'))
            definition['oversized_in_gui'] = True
            write_json(item, definition)


def main():
    FONTS.mkdir(parents=True, exist_ok=True)
    wanted = {f'line_{y}.json' for y in LINE_Y}
    for path in FONTS.glob('line_*.json'):
        if path.name not in wanted:
            path.unlink()
    providers = []
    for i, name in enumerate([f'cards_{n}' for n in range(1, 7)] + ['roster', 'shop', 'factions'] + [f'spawns_{n}' for n in range(1,7)]):
        providers.extend(build_panel(name, i))
    assert len({p['chars'][0] for p in providers}) == len(providers)
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
    write_json(ROOT / 'assets/minecraft/models/item/invasion/menu/banner.json', {
        'parent': 'minecraft:item/template_banner',
        'gui_light': 'front',
        'display': {'gui': {'rotation': [0,0,0], 'translation': [0,-2.5,0], 'scale': [.4,.4,.4]}}
    })
    for dye in ['white','orange','magenta','light_blue','yellow','lime','pink','gray',
                'light_gray','cyan','purple','blue','brown','green','red','black']:
        write_json(ROOT / f'assets/minecraft/items/invasion/menu/banner/{dye}.json', {
            'model': {'type': 'minecraft:special', 'base': 'minecraft:item/invasion/menu/banner',
                      'model': {'type': 'minecraft:banner', 'color': dye}}
        })
    print('Built 15 menu layouts and upright banners; player heads and shop items remain native.')


if __name__ == '__main__': main()

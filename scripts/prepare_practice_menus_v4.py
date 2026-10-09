"""Prepare geometry and vanilla-sized title masks for native Blockbench rendering."""
import argparse
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-jar', type=Path)
    parser.add_argument('--layout-only', action='store_true')
    args = parser.parse_args()
    old = json.loads((ROOT/'sources/practice-menus/v3-layouts.json').read_text('utf-8'))
    layout = {'start': 0xE965, 'panels': old['panels']}
    for panel in layout['panels']:
        panel['heading'] = 144
        panel['labels'] = [label for label in panel['labels']
                           if panel['id'] == 14 and label['key'].startswith('bloodstone.practice_ui.slot.')]
        # Native item centres: x=16+18*column, y=26+18*row.
        panel['cards'] = []
        if panel['id'] < 6:
            continue
        slots = panel.get('slots', [])
        # The source manifest calls these interactive_slots in older versions.
        if not slots:
            slots = panel.get('interactive_slots', [])
        if panel['id'] == 6:
            panel['rows'] = 3
            slots = [11,12,13,14,15,22]
        if panel['id'] == 7: slots = [11,12,14,15]
        if panel['id'] == 9:
            panel['rows'] = 3
            slots = [11,15,22]
        if panel['id'] == 10: slots = [4,*range(18,27),*range(29,35)]
        if panel['id'] == 11: slots = [4,*range(18,26),45,49,53]
        # Only actual controls get a native-sized slot, never the empty grid.
        if panel['id'] in (6,7,9,10,11): panel['cells'] = slots.copy()
        if panel['id'] == 12: slots = [11,15]
        if panel['id'] == 8:
            slots = [1,3,5,7,11,13,15,19,21,23,25,29,31,33,37,39,41,43,45,49,50,53]
            panel['cells'] = list(range(54))
        if panel['id'] in (13,14): slots = []
        if panel['id'] == 14:
            panel['cells'] = sorted(set(panel.get('cells', [])) | set(range(45,54)))
        panel['slots'] = slots
        for slot in slots:
            if panel['id'] in (6,7,8,9,10,11): continue
            if slot == 8: continue
            size = 24 if panel['id'] in (6,7,9,12) and slot != 22 else 20
            cx, cy = 16+slot%9*18, 26+slot//9*18
            panel['cards'].append({'x':cx-size//2,'y':cy-size//2,'w':size,'h':size})
    write(ROOT/'sources/practice-menus/v4-layouts.json', layout)
    if args.layout_only:
        print('Updated layout: ordinary item positions, native slots only beneath controls.')
        return
    if not args.client_jar: parser.error('--client-jar is required unless --layout-only is set')
    alphabet=json.loads((ROOT/'sources/practice-menus/title-glyphs.json').read_text('utf-8'))['alphabet']
    glyphs={}
    with ZipFile(args.client_jar) as jar:
        for provider in json.loads(jar.read('assets/minecraft/font/include/default.json'))['providers']:
            if provider['type'] != 'bitmap': continue
            image=Image.open(BytesIO(jar.read('assets/minecraft/textures/'+provider['file'].split(':')[1]))).convert('RGBA')
            chars=provider['chars']; w=image.width//len(chars[0]); h=image.height//len(chars)
            for row,line in enumerate(chars):
                for col,char in enumerate(line):
                    if char not in alphabet or char in glyphs: continue
                    tile=image.crop((col*w,row*h,(col+1)*w,(row+1)*h))
                    bbox=tile.getbbox()
                    if not bbox: continue
                    tile=tile.crop(bbox)
                    assert tile.width <= 9 and tile.height <= 10, (char,tile.size)
                    pixels=tile.getchannel('A')
                    glyphs[char]=['0'*tile.width]*(10-tile.height)+[
                        ''.join('1' if pixels.getpixel((x,y)) else '0' for x in range(tile.width)) for y in range(tile.height)]
    assert set(alphabet) == set(glyphs), set(alphabet)-set(glyphs)
    advances=''.join(str(len(glyphs[c][0])+1) for c in alphabet)
    write(ROOT/'sources/practice-menus/title-glyphs-v4.json',
          {'alphabet':alphabet,'start':0xE985,'advances':advances,'glyphs':glyphs})
    print('Title advances:', advances)
    print('Prepared', len(layout['panels']), 'panels; font masks from vanilla 1.21.11.')

if __name__=='__main__': main()

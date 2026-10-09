"""Validate v4 glyph geometry, Java mapping and six isolated biome item families."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text('utf-8'))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rtp',type=Path,required=True)
    parser.add_argument('--ppk',type=Path,required=True)
    args=parser.parse_args()
    layout=read(ROOT/'sources/practice-menus/v4-layouts.json')
    glyphs=read(ROOT/'sources/practice-menus/title-glyphs-v4.json')
    small=read(ROOT/'sources/practice-menus/title-glyphs.json')
    small_advances=''.join(str(max(row.rfind('1') for row in small['glyphs'][c])+2) for c in small['alphabet'])
    atlas=Image.open(ROOT/'assets/minecraft/textures/gui/practice_v4/title_font.png').convert('RGBA')
    for i,c in enumerate(glyphs['alphabet']):
        tile=atlas.crop((i%16*12,i//16*12,i%16*12+12,i//16*12+12))
        assert tile.getbbox()[2]+1==int(glyphs['advances'][i]),c
    for panel in layout['panels']:
        for lang in ('ru','en'):
            image=Image.open(ROOT/f'assets/minecraft/textures/gui/practice_v4/{panel["name"]}_{lang}.png')
            assert image.size==(256,256)
            assert image.getbbox()==(0,0,176,114+18*panel['rows']),panel['name']
        if panel['id']==14:
            assert len(panel['labels'])==18, 'Kit and chest numbers must both be present'
            assert set(range(45,54)).issubset(panel['cells']), 'Utility-row slot outlines are missing'
            image=Image.open(ROOT/'assets/minecraft/textures/gui/practice_v4/ppk_home_ru.png').convert('RGBA')
            cell=image.crop((7,35,25,53))
            for slot in range(45,54):
                x,y=7+slot%9*18,17+slot//9*18
                assert image.crop((x,y,x+18,y+18)).tobytes()==cell.tobytes(), slot
            for y in (28,64):
                row=[label for label in panel['labels'] if label['y']==y]
                assert [label['ru'] for label in row]==list('123456789')
                assert [label['en'] for label in row]==list('123456789')
                assert [label['x'] for label in row]==list(range(16,161,18))
        else: assert not panel['labels'], 'Redundant baked labels returned'
        if panel['id'] in (6,7,9,10,11):
            assert not panel['cards'], 'Plain items must not have oversized card frames'
            expected={
                6:[11,12,13,14,15,22],
                7:[11,12,14,15],
                9:[11,15,22],
                10:[4,*range(18,27),*range(29,35)],
                11:[4,*range(18,26),45,49,53],
            }[panel['id']]
            assert panel['slots']==expected, 'Control positions must match the original layout'
            assert panel['cells']==expected, 'Only actual controls should have slot outlines'
            assert panel['rows']==(3 if panel['id'] in (6,7,9) else 6)
            image=Image.open(ROOT/f'assets/minecraft/textures/gui/practice_v4/{panel["name"]}_ru.png').convert('RGBA')
            # Compare to a player-inventory cell, independent of the button grid.
            y_inventory=30+18*panel['rows']
            cell=image.crop((7,y_inventory,25,y_inventory+18))
            assert len(set(cell.get_flattened_data()))>1
            for slot in range(9*panel['rows']):
                x,y=7+slot%9*18,17+slot//9*18
                tile=image.crop((x,y,x+18,y+18))
                if slot in expected:
                    assert tile.tobytes()==cell.tobytes(), (panel['name'],slot,'Misaligned slot')
                else:
                    assert set(tile.get_flattened_data())=={(198,198,198,255)}, (panel['name'],slot,'Unexpected empty-slot outline')
        if panel['id']==8:
            assert panel['slots']==[1,3,5,7,11,13,15,19,21,23,25,29,31,33,37,39,41,43,45,49,50,53]
            assert panel['cells']==list(range(54))
            assert not panel['cards']
            image=Image.open(ROOT/'assets/minecraft/textures/gui/practice_v4/queue_ru.png').convert('RGBA')
            cell=image.crop((7,17,25,35))
            assert len(set(cell.getdata()))>1, 'Queue slot outlines are missing'
            for slot in range(54):
                x,y=7+slot%9*18,17+slot//9*18
                assert image.crop((x,y,x+18,y+18)).tobytes()==cell.tobytes(), slot
        for card in panel['cards']:
            assert 3<=card['x'] and card['x']+card['w']<=173
            assert 17<=card['y'] and card['y']+card['h']<=18+18*panel['rows']
    for folder,relative in [(args.rtp,'src/main/java/ru/tukisg/rtp/MenuSkin.java'),
                            (args.ppk,'src/main/java/dev/noah/perplayerkit/util/MenuSkin.java')]:
        code=(folder/relative).read_text('utf-8')
        assert f'0x{layout["start"]:X}' in code
        assert '0xE265' in code
        assert small_advances in code
        assert 'return 144;' in code
    rtp_code=(args.rtp/'src/main/java/ru/tukisg/rtp/RTPCommand.java').read_text('utf-8')
    assert 'practice/biomes/' not in rtp_code, 'Biome buttons must use their ordinary materials'
    arena_code=(args.rtp/'src/main/java/ru/tukisg/rtp/arena/ArenaMenuCommand.java').read_text('utf-8')
    assert 'setItemModel(' not in arena_code and 'setCustomModelData(' not in arena_code
    total=0
    for name in ('plains','desert','badlands','mushroom','snowy_fields','hub'):
        ref=f'practice/biomes/{name}/default/{name}'
        item=read(ROOT/f'assets/minecraft/items/{ref}.json')
        assert item.get('oversized_in_gui') is True, 'Large menu icon would be clipped to 16px'
        assert item['model']=={'type':'minecraft:model','model':'minecraft:item/'+ref}
        model=read(ROOT/f'assets/minecraft/models/item/{ref}.json')
        assert len(model['elements'])==1, 'Each biome is exactly one block, without objects on top'
        for value in model['textures'].values():
            if value.startswith('#'):continue
            ns,path=value.split(':')
            image=Image.open(ROOT/f'assets/{ns}/textures/{path}.png')
            assert image.width==16
        for element in model['elements']:
            assert all(0<=a<=b<=32 for a,b in zip(element['from'],element['to']))
            assert 'rotation' not in element
            for face in element['faces'].values():
                assert face['texture'].lstrip('#') in model['textures']
        base=model['elements'][0]
        assert base['from']==[0,0,0] and base['to']==[16,16,16]
        gui=model['display']['gui']
        assert all(1.07<=scale<=1.08 for scale in gui['scale'])
        assert gui.get('translation',[0,0,0])==[0,0,0]
        angle_x,angle_y,_=map(math.radians,gui['rotation'])
        points=[]
        for element in model['elements']:
            for x in (element['from'][0],element['to'][0]):
                for y in (element['from'][1],element['to'][1]):
                    for z in (element['from'][2],element['to'][2]):
                        rx=math.cos(angle_y)*(x-8)+math.sin(angle_y)*(z-8)
                        rz=-math.sin(angle_y)*(x-8)+math.cos(angle_y)*(z-8)
                        ry=math.cos(angle_x)*(y-8)-math.sin(angle_x)*rz
                        translation=gui.get('translation',[0,0,0])
                        points.append((rx*gui['scale'][0]+translation[0],ry*gui['scale'][1]+translation[1]))
        assert all(abs(v)<=13.501 for point in points for v in point), (name,points)
        print(f'{name}: safe GUI bounds {min(p[0] for p in points):.2f}..{max(p[0] for p in points):.2f}, {min(p[1] for p in points):.2f}..{max(p[1] for p in points):.2f}')
        total+=len(model['elements'])
    print('OK: 30 panels, original control positions, slots only under controls, no oversized cards, vanilla items, 9 utility slots, small font, kit numbers and original queue preserved.')

if __name__=='__main__':main()

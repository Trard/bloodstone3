"""Verify the exported menu geometry, isolated title atlas and resource references."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
from build_practice_menu_assets import PANELS

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-jar',type=Path,required=True)
    parser.add_argument('--plugin-source',type=Path,action='append',default=[])
    args=parser.parse_args()
    source=Image.open(ROOT/'assets/bloodstone/textures/ui/gui/practice/practice_menu_ru.png').convert('RGBA')
    cell=source.crop((7,83,25,101))
    providers=json.loads((ROOT/'assets/minecraft/font/practice_menus.json').read_text('utf-8'))['providers']
    assert len(providers)==16
    for i,name in enumerate(PANELS):
        p=providers[i]
        im=Image.open(ROOT/'assets/minecraft/textures'/p['file'].split(':')[1]).convert('RGBA')
        rows=i+1 if i<6 else 3 if name in ('biomes','arenas','settings','presets') else 6
        assert im.size==(256,256)
        assert im.getchannel('A').getbbox()==(0,0,176,114+18*rows),(name,im.getbbox())
        assert p['ascent']==13 and p['height']==256 and p['chars']==[chr(0xe1a8+i)]
        # Paper 1.21.11 ChestMenu: item origins x=8+18c, y=31+18*rows+18r.
        for row in range(4):
            for col in range(9):
                x,y=7+col*18,30+rows*18+row*18+(4 if row==3 else 0)
                assert cell.tobytes()==im.crop((x,y,x+18,y+18)).tobytes(),(name,col,row)
    advances=providers[-1]['advances']
    assert advances['\ue1b6']+177+advances['\ue1b7']==0
    assert advances['\ue2e3']==3 and advances['\ue2e4']==1
    spec=json.loads((ROOT/'sources/practice-menus/title-glyphs.json').read_text('utf-8'))
    atlas=Image.open(ROOT/'assets/minecraft/textures/gui/practice/title_font.png').convert('RGBA')
    assert atlas.size==(128,48)
    p=providers[-2]
    assert p['ascent']==7 and p['height']==8 and len(p['chars'])==6
    expected_advances=''
    for i,letter in enumerate(spec['alphabet']):
        assert p['chars'][i//16][i%16]==chr(spec['start']+i)
        tile=atlas.crop((i%16*8,i//16*8,i%16*8+8,i//16*8+8))
        pattern=spec['glyphs'][letter]
        for y in range(8):
            for x in range(8):
                expected=y<5 and x<len(pattern[y]) and pattern[y][x]=='1'
                assert (tile.getpixel((x,y))[3]>0)==expected,(letter,x,y)
        expected_advances+=str(tile.getbbox()[2]+1)
    for source in args.plugin_source:
        java=source.read_text('utf-8')
        assert f'ALPHABET = "{spec["alphabet"]}"' in java,source
        assert f'ADVANCES = "{expected_advances}"' in java,source
        assert '0xE265' in java and 'headingWidth(panel) - 12' in java,source

    # Retained v1 icon files are compatibility-only, not overrides of vanilla item IDs.
    with ZipFile(args.client_jar) as jar:
        entries=set(jar.namelist())
        def exists(resource,kind,ext):
            ns,name=resource.split(':') if ':' in resource else ('minecraft',resource)
            path=f'assets/{ns}/{kind}/{name}{ext}'
            assert (ROOT/path).is_file() or path in entries,path
        def model(node):
            if isinstance(node,dict):
                for k,v in node.items():
                    if k in ('model','base') and isinstance(v,str):exists(v,'models','.json')
                    else:model(v)
            elif isinstance(node,list):
                for v in node:model(v)
        for path in (ROOT/'assets/minecraft/items/practice/menu').glob('*.json'):
            model(json.loads(path.read_text('utf-8')))
        for path in (ROOT/'assets/minecraft/models/item/practice/menu').glob('*.json'):
            data=json.loads(path.read_text('utf-8'))
            for tex in data.get('textures',{}).values():exists(tex,'textures','.png')
            if 'parent' in data:exists(data['parent'],'models','.json')
    print(f'OK: 14 panels; all 504 player-inventory cells pixel-aligned; {len(spec["alphabet"])} title glyphs/Java metrics; references valid.')


if __name__=='__main__':main()

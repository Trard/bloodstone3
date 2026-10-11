"""Check v3 layouts against actual slot geometry, localized labels and exported Blockbench PNGs."""
import argparse
import json
import re
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def intersects(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--practice-source',type=Path,required=True)
    parser.add_argument('--ppk-source',type=Path,required=True)
    args=parser.parse_args()
    data=json.loads((ROOT/'sources/practice-menus/v3-layouts.json').read_text('utf-8'))
    font=json.loads((ROOT/'sources/practice-menus/title-glyphs.json').read_text('utf-8'))
    providers=json.loads((ROOT/'assets/minecraft/font/practice_menus_v3.json').read_text('utf-8'))['providers']
    assert len(providers)==len(data['panels'])*2==30
    advance={c:max(r.rfind('1') for r in pattern)+2 for c,pattern in font['glyphs'].items()}
    advance[' ']=3
    reference=Image.open(ROOT/'assets/bloodstone/textures/ui/gui/practice/practice_menu_ru.png').convert('RGBA')
    cell=reference.crop((7,83,25,101)).tobytes()
    labels_checked=0
    for panel in data['panels']:
        controls=panel.get('slots',panel.get('cells',[]))
        assert len(controls)==len(set(controls)),panel['name']
        assert all(0<=s<panel['rows']*9 for s in controls)
        boxes=[(8+s%9*18,18+s//9*18,24+s%9*18,34+s//9*18) for s in controls]
        for lang_index,lang in enumerate(('ru','en')):
            i=panel['id']*2+lang_index
            provider=providers[i]
            assert provider['chars']==[chr(data['start']+i)]
            assert provider['ascent']==13 and provider['height']==256
            expected=f'minecraft:gui/practice_v3/{panel["name"]}_{lang}.png'
            assert provider['file']==expected
            image=Image.open(ROOT/'assets/minecraft/textures'/expected.split(':')[1]).convert('RGBA')
            assert image.size==(256,256)
            assert image.getchannel('A').getbbox()==(0,0,176,114+panel['rows']*18)
            for row in range(4):
                for col in range(9):
                    x,y=7+18*col,30+18*panel['rows']+row*18+(4 if row==3 else 0)
                    assert image.crop((x,y,x+18,y+18)).tobytes()==cell,(panel['name'],row,col)
            translations=json.loads((ROOT/f'assets/bloodstone/lang/{"ru_ru" if lang=="ru" else "en_us"}.json').read_text('utf-8'))
            drawn_labels=[]
            for label in panel['labels']:
                value=label[lang]
                assert translations[label['key']]==value
                width=sum(advance[c] for c in value)-1
                x=label['x']-(width//2 if label['align']=='center' else width if label['align']=='right' else 0)
                assert width<=label['maxWidth'] and 3<=x and x+width<=173,(panel['name'],value)
                rect=(x,label['y'],x+width,label['y']+5)
                assert not any(intersects(rect,b) for b in boxes),(panel['name'],value,'item overlap')
                assert not any(intersects(rect,b) for b in drawn_labels),(panel['name'],value,'label overlap')
                assert not intersects(rect,(8,20+18*panel['rows'],84,28+18*panel['rows'])),(value,'inventory label')
                drawn_labels.append(rect)
                # Every foreground pixel exported by Blockbench must match the source glyph masks.
                color=tuple(bytes.fromhex(label['shade'].lstrip('#')))+(255,)
                cursor=x
                for c in value:
                    if c!=' ':
                        for dy,row in enumerate(font['glyphs'][c]):
                            for dx,bit in enumerate(row):
                                if bit=='1':assert image.getpixel((cursor+dx,label['y']+dy))==color,(value,dx,dy)
                    cursor+=advance[c]
                labels_checked+=1

    rtp=(args.practice_source/'src/main/java/ru/tukisg/rtp/RTPCommand.java').read_text('utf-8')
    ppk=(args.ppk_source/'src/main/java/dev/noah/perplayerkit/gui/CombinedSettingsGUI.java').read_text('utf-8')
    def array(java,name):
        return [int(n) for n in re.search(r'\b'+name+r'\s*=\s*\{([^}]+)',java).group(1).split(',') if n.strip()]
    def integer(java,name):
        return int(re.search(r'\b'+name+r'\s*=\s*(\d+)',java).group(1))
    by_name={p['name']:p for p in data['panels']}
    assert array(rtp,'MENU_SLOTS')==by_name['biomes']['slots']
    queue=array(rtp,'QUEUE_KIT_SLOTS')+[integer(rtp,'OWN_QUEUE_SLOT'),integer(rtp,'QUEUE_CLOSE_SLOT'),45,53]
    assert set(queue)==set(by_name['queue']['slots'])
    kits=array(ppk,'KIT_TOGGLE_SLOTS')+[integer(ppk,n) for n in ['SLOT_RTP_KIT','SLOT_OPPONENT_REKIT','SLOT_SPEC_AUTO_ACCEPT','SLOT_NATURAL_REGENERATION','SLOT_INSTANT_RESPAWN','SLOT_DEATH_ANIMATION','SLOT_BACK']]
    assert set(kits)==set(by_name['kit_settings']['slots']) and len(kits)==len(set(kits))
    cds=[integer(ppk,n) for n in ['SLOT_COMBAT','SLOT_TNT','SLOT_PEARL','SLOT_RIPTIDE','SLOT_WIND','SLOT_ELYTRA','SLOT_COBWEB','SLOT_RESET_ON_KILL','SLOT_RESET_ACTIVE','SLOT_PRESETS','SLOT_RESET_CONFIGURED','SLOT_BACK']]
    assert set(cds)==set(by_name['cooldowns']['slots']) and len(cds)==len(set(cds))
    assert 'ChestMenu.builder(5).title(TITLE_COMPONENT)' in ppk
    assert 'createInventory(holder, 45, MenuSkin.title(player, MENU_TITLE, 45))' in rtp
    gui=(args.ppk_source/'src/main/java/dev/noah/perplayerkit/gui/GUI.java').read_text('utf-8').split('public void OpenMainMenu(Player player) {',1)[1].split('private ItemStack createTrimMenuItem',1)[0]
    assert 'for (int i = 9; i < 18; i++)' in gui and 'int kitIndex = i - 8;' in gui
    assert 'for (int i = 27; i < 36; i++)' in gui and 'int ecIndex = i - 26;' in gui
    assert set(map(int,re.findall(r'getSlot\((\d+)\)',gui)))=={45,46,47,48,50,51,52,53}
    for project,package in [(args.practice_source,'ru/tukisg/rtp'),(args.ppk_source,'dev/noah/perplayerkit/util')]:
        skin=(project/f'src/main/java/{package}/MenuSkin.java').read_text('utf-8')
        assert '0xE46E + panel * 2' in skin
        assert 'headingWidth(panel) - 12' in skin
        assert f'ALPHABET = "{font["alphabet"]}"' in skin
        widths=''.join(str(advance[c]) for c in font['alphabet'])
        assert f'ADVANCES = "{widths}"' in skin
    print(f'OK: 30 backgrounds, 1080 aligned player cells, {labels_checked} RU/EN labels with no item/text overlap, and source slot mappings.')

if __name__=='__main__':main()

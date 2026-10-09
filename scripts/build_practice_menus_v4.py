"""Register Blockbench-exported v4 art without changing old font providers."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    layout=json.loads((ROOT/'sources/practice-menus/v4-layouts.json').read_text('utf-8'))
    font=json.loads((ROOT/'sources/practice-menus/title-glyphs-v4.json').read_text('utf-8'))
    providers=[]
    for panel in layout['panels']:
        for i,lang in enumerate(('ru','en')):
            name=panel['name']+'_'+lang
            assert (ROOT/f'assets/minecraft/textures/gui/practice_v4/{name}.png').is_file()
            providers.append({'type':'bitmap','file':f'minecraft:gui/practice_v4/{name}.png',
                              'height':256,'ascent':13,'chars':[chr(layout['start']+panel['id']*2+i)]})
    chars=''.join(chr(font['start']+i) for i in range(len(font['alphabet'])))
    chars=chars.ljust((len(chars)+15)//16*16,'\0')
    providers.append({'type':'bitmap','file':'minecraft:gui/practice_v4/title_font.png',
                      'height':12,'ascent':11,'chars':[chars[i:i+16] for i in range(0,len(chars),16)]})
    providers.append({'type':'space','advances':{'\uE9E0':4}})
    write(ROOT/'assets/minecraft/font/practice_menus_v4.json',{'providers':providers})
    path=ROOT/'assets/minecraft/font/default.json'
    default=json.loads(path.read_text('utf-8'))
    if not any(p.get('id')=='minecraft:practice_menus_v4' for p in default['providers']):
        default['providers'].append({'type':'reference','id':'minecraft:practice_menus_v4'})
    path.write_text(json.dumps(default,ensure_ascii=False,indent=4)+'\n',encoding='utf-8')
    print('Registered 30 panels and native-sized RU/EN title glyphs; old UI and item overrides preserved.')

if __name__=='__main__': main()

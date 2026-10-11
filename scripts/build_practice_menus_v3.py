"""Register versioned v3 backgrounds and localized baked labels; retain v1/v2 assets."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    data=json.loads((ROOT/'sources/practice-menus/v3-layouts.json').read_text('utf-8'))
    providers=[];symbols=[]
    translations={'ru':{},'en':{}}
    for panel in data['panels']:
        for offset,lang in enumerate(('ru','en')):
            name=panel['name']+'_'+lang
            assert (ROOT/f'assets/minecraft/textures/gui/practice_v3/{name}.png').is_file(),name
            char=chr(data['start']+panel['id']*2+offset)
            providers.append(dict(type='bitmap',file=f'minecraft:gui/practice_v3/{name}.png',
                                  height=256,ascent=13,chars=[char]))
            symbols.append(f'U+{ord(char):04X}\t{char}\t{name}')
            for label in panel['labels']:
                key=label['key']
                assert key not in translations[lang] or translations[lang][key]==label[lang],key
                translations[lang][key]=label[lang]
    write(ROOT/'assets/minecraft/font/practice_menus_v3.json',dict(providers=providers))
    path=ROOT/'assets/minecraft/font/default.json'
    default=json.loads(path.read_text('utf-8'))
    if not any(p.get('type')=='reference' and p.get('id') in ('practice_menus_v3','minecraft:practice_menus_v3') for p in default['providers']):
        default['providers'].append(dict(type='reference',id='minecraft:practice_menus_v3'))
        write(path,default)
    for lang,name in [('ru','ru_ru'),('en','en_us')]:
        path=ROOT/f'assets/bloodstone/lang/{name}.json'
        original=json.loads(path.read_text('utf-8'))
        updated={**original,**translations[lang]}
        assert all(updated[k]==v for k,v in original.items() if not k.startswith('bloodstone.practice_ui.'))
        write(path,updated)
    (ROOT/'sources/practice-menus/symbols-v3.tsv').write_text('\n'.join(symbols)+'\n',encoding='utf-8')
    print(f'Built {len(providers)} versioned panels and {len(translations["ru"])} RU/EN translation keys; old panels preserved.')

if __name__=='__main__':main()

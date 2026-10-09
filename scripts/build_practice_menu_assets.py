"""Assemble background fonts from artwork exported by Blockbench MCP; no visible item overrides."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = [*(f'rows_{i}' for i in range(1, 7)), 'biomes', 'arenas', 'queue',
          'settings', 'kit_settings', 'cooldowns', 'presets', 'layout']
START = 0xE1A8


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    providers = []
    for i, name in enumerate(PANELS):
        texture = ROOT / f'assets/minecraft/textures/gui/practice/{name}.png'
        if not texture.is_file():
            raise SystemExit(f'Export this texture from Blockbench first: {texture}')
        providers.append(dict(type='bitmap', file=f'minecraft:gui/practice/{name}.png',
                              height=256, ascent=13, chars=[chr(START+i)]))
    data = json.loads((ROOT/'sources/practice-menus/title-glyphs.json').read_text('utf-8'))
    letters = ''.join(chr(data['start']+i) for i in range(len(data['alphabet'])))
    letters = letters.ljust(96, '\0')
    providers.append(dict(type='bitmap',file='minecraft:gui/practice/title_font.png',
                          height=8,ascent=7,chars=[letters[i:i+16] for i in range(0,96,16)]))
    providers.append(dict(type='space', advances={chr(START+14):-8, chr(START+15):-169,
                                                 '\ue2e3':3, '\ue2e4':1}))
    write(ROOT / 'assets/minecraft/font/practice_menus.json', {'providers': providers})
    # Keep a real locked filler in server slots. Only its invisible appearance is customized.
    write(ROOT / 'assets/minecraft/items/practice/menu/empty.json', {'model': {'type': 'minecraft:empty'}})
    # Old icon assets remain for compatibility with the previous JAR, but are not used or regenerated.
    symbols = [f'U+{START+i:04X}\t{chr(START+i)}\t{name}' for i, name in enumerate(PANELS)]
    symbols += [f'U+{START+14:04X}\t{chr(START+14)}\toffset_minus_8',
                f'U+{START+15:04X}\t{chr(START+15)}\toffset_minus_169']
    symbols += [f'U+{data["start"]+i:04X}\t{chr(data["start"]+i)}\ttitle_{letter}'
                for i,letter in enumerate(data['alphabet'])]
    symbols += ['U+E2E3\t\ue2e3\tword_space_3px', 'U+E2E4\t\ue2e4\talignment_1px']
    (ROOT / 'sources/practice-menus/symbols.tsv').write_text('\n'.join(symbols)+'\n', encoding='utf-8')
    print(f'Built {len(PANELS)} panels, an isolated 5px RU/EN title font and invisible locked filler. No visible custom items.')


if __name__ == '__main__':
    main()
